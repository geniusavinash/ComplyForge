"""HTTP routes for ComplianceOrchestrator.

Endpoints:
  POST /api/analyze              -> ComplianceReport
  POST /api/analyze/stream       -> Server-Sent Events stream of orchestrator events
  GET  /api/pdf/{filename}       -> streams a generated PDF
  GET  /api/sample-agents        -> demo agents from app/data/sample_agents.json
  POST /api/deploy-policy/{slug} -> writes the agent's Lobster Trap policy YAML
                                    to lobstertrap/policies/agents/<slug>.yaml
  GET  /api/inventory/zip        -> streams every PDF + JSON sidecar as a ZIP

The orchestrator is provided via FastAPI dependency injection so tests can
override it with `app.dependency_overrides[get_orchestrator] = ...`.
"""

from __future__ import annotations

import io
import json
import logging
import os
import tempfile
import zipfile
from pathlib import Path
from typing import AsyncIterator

import yaml
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, ValidationError

from app.agents.critic import CriticAgent
from app.agents.orchestrator import ComplianceOrchestrator, slug as slugify
from app.agents.planner import PlannerAgent
from app.config import get_settings
from app.schemas import AgentDescriptor, ComplianceReport
from app.services.gemini_client import build_gemini_schema

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["analyze"])

# `generated_pdfs/` lives under `backend/`; routes resolve from CWD because
# uvicorn is launched from `backend/` per the the architecture spec contract.
PDF_DIR = Path("generated_pdfs")
SAMPLE_AGENTS_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "sample_agents.json"
)

# Lobster Trap per-agent policy directory. Resolved relative to backend/ CWD
# so the demo can write to the sibling lobstertrap/policies/agents/ folder.
DEFAULT_LOBSTERTRAP_POLICY_DIR = Path("..") / "lobstertrap" / "policies" / "agents"


# ---------------------------------------------------------------------------
# Dependency providers (overridable in tests)
# ---------------------------------------------------------------------------
def get_orchestrator() -> ComplianceOrchestrator:
    """Default orchestrator dependency. Override via app.dependency_overrides.

    v0.3.0: wires PlannerAgent + CriticAgent so the live API exercises the
    upgraded plan -> classify -> critique -> generate -> render pipeline.
    """
    return ComplianceOrchestrator(
        planner=PlannerAgent(),
        critic=CriticAgent(),
    )


def get_pdf_dir() -> Path:
    """Default PDF/JSON sidecar directory. Override in tests via tmp_path."""
    return PDF_DIR


def get_lobstertrap_policy_dir() -> Path:
    """Default Lobster Trap per-agent policy directory. Override in tests."""
    return DEFAULT_LOBSTERTRAP_POLICY_DIR


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.post("/analyze", response_model=ComplianceReport)
async def analyze(
    agent: AgentDescriptor,
    orchestrator: ComplianceOrchestrator = Depends(get_orchestrator),
) -> ComplianceReport:
    return await orchestrator.analyze(agent)


@router.post("/analyze/stream")
async def analyze_stream(
    agent: AgentDescriptor,
    orchestrator: ComplianceOrchestrator = Depends(get_orchestrator),
) -> StreamingResponse:
    async def event_source() -> AsyncIterator[bytes]:
        async for event in orchestrator.analyze_stream(agent):
            yield f"data: {json.dumps(event)}\n\n".encode("utf-8")

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(
        event_source(), media_type="text/event-stream", headers=headers,
    )


@router.get("/pdf/{pdf_filename}")
async def get_pdf(
    pdf_filename: str,
    pdf_dir: Path = Depends(get_pdf_dir),
) -> FileResponse:
    # Reject path traversal and absolute paths up front.
    if (
        not pdf_filename
        or "/" in pdf_filename
        or "\\" in pdf_filename
        or ".." in pdf_filename
        or os.path.isabs(pdf_filename)
    ):
        raise HTTPException(status_code=400, detail="Invalid pdf filename")

    target = (pdf_dir / pdf_filename).resolve()
    pdf_root = pdf_dir.resolve()
    try:
        target.relative_to(pdf_root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid pdf path") from exc

    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="PDF not found")

    return FileResponse(
        path=str(target),
        media_type="application/pdf",
        filename=pdf_filename,
    )


@router.get("/sample-agents")
async def list_sample_agents() -> list[dict]:
    if not SAMPLE_AGENTS_PATH.exists():
        return []
    try:
        with SAMPLE_AGENTS_PATH.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return data


# ---------------------------------------------------------------------------
# v0.3.0: multimodal AgentDescriptor extraction (Multimodal Intelligence track)
# ---------------------------------------------------------------------------
_MULTIMODAL_FALLBACK_MODEL = "gemini-2.5-flash"
_EXTRACT_PROMPT = (
    "Extract an AgentDescriptor JSON describing the AI system depicted in this "
    "document. Required fields: name, purpose, domain, inputs, outputs, "
    "affects_humans, sample_prompts (3-5 realistic strings), tools (list of "
    "strings). Output strictly JSON matching the AgentDescriptor schema."
)
_SUPPORTED_EXTRACT_TYPES = {"image/png", "image/jpeg", "application/pdf"}


def _multimodal_model_name() -> str:
    name = get_settings().gemini_model or _MULTIMODAL_FALLBACK_MODEL
    # gemini-2.5-flash-lite does not support multimodal inputs reliably;
    # fall back to gemini-2.5-flash for image/PDF parts.
    if "lite" in name.lower():
        return _MULTIMODAL_FALLBACK_MODEL
    return name


def _extract_descriptor_sync(content: bytes, content_type: str) -> dict:
    """Blocking helper for genai multimodal call; runs in a thread."""
    import google.generativeai as genai  # local import keeps test isolation easy
    from PIL import Image

    model = genai.GenerativeModel(_multimodal_model_name())
    generation_config = {
        "response_mime_type": "application/json",
        "response_schema": build_gemini_schema(AgentDescriptor),
    }

    if content_type.startswith("image/"):
        image = Image.open(io.BytesIO(content))
        parts = [_EXTRACT_PROMPT, image]
    else:
        # application/pdf — write to a temp file and upload to Gemini Files.
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as fh:
            fh.write(content)
            tmp_path = fh.name
        uploaded = genai.upload_file(tmp_path, mime_type="application/pdf")
        parts = [_EXTRACT_PROMPT, uploaded]

    response = model.generate_content(parts, generation_config=generation_config)
    text = getattr(response, "text", None) or ""
    return json.loads(text)


@router.post("/extract-descriptor")
async def extract_descriptor(file: UploadFile = File(...)) -> JSONResponse:
    """Multimodal: turn an uploaded image/PDF into an AgentDescriptor JSON."""
    import asyncio  # local to keep header imports tidy

    content_type = (file.content_type or "").lower()
    if content_type not in _SUPPORTED_EXTRACT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type {content_type!r}; expected one of "
                f"{sorted(_SUPPORTED_EXTRACT_TYPES)}."
            ),
        )
    try:
        content = await file.read()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Could not read upload: {exc}") from exc
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        payload = await asyncio.to_thread(_extract_descriptor_sync, content, content_type)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Gemini returned non-JSON: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("extract-descriptor failed")
        raise HTTPException(status_code=400, detail=f"Extraction failed: {exc}") from exc

    try:
        descriptor = AgentDescriptor.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Extracted JSON did not match AgentDescriptor: {exc}",
        ) from exc

    return JSONResponse(content=descriptor.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# the build step: deploy a generated policy to Lobster Trap
# ---------------------------------------------------------------------------
class DeployPolicyRequest(BaseModel):
    """Optional override for the policy YAML.

    If `policy_yaml` is supplied, it is written verbatim. Otherwise the
    sidecar `<slug>.json` written by `seed_inventory.py` (or any prior call
    to /api/analyze that the operator persisted) is read and its
    `policy.yaml` field is used.
    """

    policy_yaml: str | None = Field(
        default=None,
        description="Raw Lobster Trap policy YAML; overrides the sidecar lookup.",
    )


def _safe_slug_segment(s: str) -> str:
    """Reuse the orchestrator's slug helper to constrain filename input."""
    return slugify(s)


def _read_sidecar(pdf_dir: Path, slug: str) -> dict | None:
    sidecar = pdf_dir / f"{slug}.json"
    if not sidecar.exists():
        return None
    try:
        with sidecar.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _count_rules(parsed: dict) -> int:
    ingress = parsed.get("ingress_rules") if isinstance(parsed, dict) else None
    egress = parsed.get("egress_rules") if isinstance(parsed, dict) else None
    return (len(ingress) if isinstance(ingress, list) else 0) + (
        len(egress) if isinstance(egress, list) else 0
    )


@router.post("/deploy-policy/{agent_slug}")
async def deploy_policy(
    agent_slug: str,
    body: DeployPolicyRequest | None = None,
    pdf_dir: Path = Depends(get_pdf_dir),
    policy_dir: Path = Depends(get_lobstertrap_policy_dir),
) -> dict:
    """Persist a Lobster Trap policy YAML for the given agent slug.

    Behavior:
      * If `body.policy_yaml` is supplied, it is written verbatim.
      * Otherwise the most recent ComplianceReport sidecar is read from
        `<pdf_dir>/<slug>.json` and its `policy.yaml` field is used.
      * Output: `<policy_dir>/<slug>.yaml`. The Lobster Trap binary loads
        policies once at startup and does not currently expose a reload
        mechanism (no SIGHUP, no admin endpoint, no file watcher — verified
        in `lobstertrap/src/cmd/serve.go` during the integration step). The response
        therefore reports `reload_method: "manual_restart_required"` so
        callers can surface the truth honestly.
    """
    slug = _safe_slug_segment(agent_slug)
    if not slug or slug == "agent":
        raise HTTPException(status_code=400, detail="Invalid agent slug")

    yaml_text: str | None = None
    if body is not None and body.policy_yaml is not None:
        yaml_text = body.policy_yaml
    else:
        sidecar = _read_sidecar(pdf_dir, slug)
        if sidecar is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"No ComplianceReport sidecar at "
                    f"{pdf_dir}/{slug}.json. Run /api/analyze for this agent "
                    f"first or POST {{ \"policy_yaml\": ... }} explicitly."
                ),
            )
        policy_block = sidecar.get("policy") if isinstance(sidecar, dict) else None
        if not isinstance(policy_block, dict):
            raise HTTPException(
                status_code=404,
                detail=f"Sidecar {slug}.json has no policy block.",
            )
        candidate = policy_block.get("yaml")
        if not isinstance(candidate, str) or not candidate.strip():
            raise HTTPException(
                status_code=404,
                detail=f"Sidecar {slug}.json has empty policy.yaml.",
            )
        yaml_text = candidate

    # Validate the YAML before persisting so a 400 is returned for malformed
    # input rather than silently writing a broken policy file Lobster Trap
    # would later reject.
    try:
        parsed = yaml.safe_load(yaml_text)
    except yaml.YAMLError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid policy YAML: {exc}",
        ) from exc
    if not isinstance(parsed, dict):
        raise HTTPException(
            status_code=400,
            detail="Policy YAML must be a mapping at the top level.",
        )

    rule_count = _count_rules(parsed)

    # Resolve the destination, create the directory, write the YAML.
    target_dir = policy_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{slug}.yaml"
    try:
        target_path.write_text(yaml_text, encoding="utf-8")
    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to write policy file: {exc}",
        ) from exc

    return {
        "deployed": True,
        "policy_path": str(target_path).replace("\\", "/"),
        "reload_method": "manual_restart_required",
        "reload_note": (
            "Lobster Trap loads policies once at startup; restart the "
            "binary to pick up the new policy. (Verified against "
            "lobstertrap/src/cmd/serve.go — no SIGHUP, no admin reload, "
            "no file watcher.)"
        ),
        "rule_count": rule_count,
        "agent_slug": slug,
    }


# ---------------------------------------------------------------------------
# the build step: bulk inventory ZIP
# ---------------------------------------------------------------------------
@router.get("/inventory/zip")
async def inventory_zip(
    pdf_dir: Path = Depends(get_pdf_dir),
) -> StreamingResponse:
    """Stream every generated PDF + ComplianceReport JSON sidecar as a ZIP.

    Returns 404 when the inventory is empty.
    """
    if not pdf_dir.exists() or not pdf_dir.is_dir():
        raise HTTPException(status_code=404, detail="No inventory yet")

    members: list[Path] = []
    for entry in sorted(pdf_dir.iterdir()):
        if not entry.is_file():
            continue
        if entry.suffix.lower() in {".pdf", ".json"}:
            members.append(entry)

    if not members:
        raise HTTPException(status_code=404, detail="No inventory yet")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for member in members:
            zf.write(member, arcname=member.name)
    buffer.seek(0)

    headers = {
        "Content-Disposition": 'attachment; filename="complyforge-inventory.zip"',
    }
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers=headers,
    )


__all__ = [
    "router",
    "get_orchestrator",
    "get_pdf_dir",
    "get_lobstertrap_policy_dir",
    "PDF_DIR",
    "SAMPLE_AGENTS_PATH",
    "DEFAULT_LOBSTERTRAP_POLICY_DIR",
]
