"""Tests for the FastAPI HTTP layer.

Test client choice: Starlette's `TestClient` (a thin sync wrapper around
httpx). It cleanly supports `client.stream(...)` for the SSE endpoint and
sidesteps any `pytest-asyncio` event-loop / `httpx.ASGITransport` plumbing
the Phase 5 spec leaves up to us.

Orchestrator dependency is overridden via `app.dependency_overrides`. No real
Gemini calls are ever made.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.data.eu_ai_act_taxonomy import ARTICLE_11_SECTIONS
from app.routers.analyze import (
    get_lobstertrap_policy_dir,
    get_orchestrator,
    get_pdf_dir,
)
from app.routers.enforcement import get_events_path
from app.schemas import (
    AgentDescriptor,
    Article11Section,
    ClassificationResult,
    ComplianceReport,
    EnforcementEvent,
    LobsterTrapPolicy,
    RiskTier,
    TechnicalFile,
)
from main import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
def _agent_payload() -> dict:
    return {
        "name": "ResumeRanker",
        "purpose": "Rank resumes",
        "domain": "HR",
        "inputs": ["resume_pdf"],
        "outputs": ["score"],
        "affects_humans": True,
        "sample_prompts": ["score this"],
        "tools": ["pdf_extractor"],
    }


def _canned_report() -> ComplianceReport:
    agent = AgentDescriptor(**_agent_payload())
    classification = ClassificationResult(
        tier=RiskTier.HIGH_RISK,
        confidence=0.92,
        triggered_articles=["Annex III(4)", "Article 6"],
        rationale="HR resume screening Annex III(4).",
        obligations=["Maintain Article 11 file"],
    )
    tech_file = TechnicalFile(
        agent_name=agent.name,
        risk_tier=RiskTier.HIGH_RISK,
        generated_at=datetime(2026, 5, 17, 12, 0, tzinfo=timezone.utc),
        sections=[
            Article11Section(heading=meta["heading"], body="body")
            for meta in ARTICLE_11_SECTIONS
        ],
        fria_summary="FRIA narrative under Article 27.",
        datasheet={
            "model_provider": "test",
            "intended_use": "test",
            "training_data_summary": "test",
            "performance_metrics": "test",
            "known_limitations": "test",
            "human_oversight": "test",
            "contact": "test",
        },
    )
    policy = LobsterTrapPolicy(
        name="complyforge-resumeranker",
        yaml="name: complyforge-resumeranker\nversion: 1\nrules: []\n",
        purpose="High-risk policy",
        rules_count=5,
    )
    return ComplianceReport(
        agent=agent,
        classification=classification,
        technical_file=tech_file,
        policy=policy,
        pdf_path="generated_pdfs/resumeranker.pdf",
    )


def _make_orchestrator_stub(report: ComplianceReport) -> object:
    """Lightweight async stand-in for ComplianceOrchestrator."""

    class _Stub:
        async def analyze(self, _agent: AgentDescriptor) -> ComplianceReport:
            return report

        async def analyze_stream(
            self, _agent: AgentDescriptor,
        ) -> AsyncIterator[dict]:
            yield {"step": "classifying", "status": "started"}
            yield {"step": "classifying", "status": "completed"}
            yield {"step": "generating_docs", "status": "started"}
            yield {"step": "generating_policy", "status": "started"}
            yield {"step": "generating_docs", "status": "completed"}
            yield {"step": "generating_policy", "status": "completed"}
            yield {"step": "rendering_pdf", "status": "started"}
            yield {"step": "rendering_pdf", "status": "completed"}
            yield {
                "step": "done",
                "status": "completed",
                "payload": report.model_dump(mode="json"),
            }

    return _Stub()


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    """TestClient with orchestrator + events path + filesystem overrides."""
    report = _canned_report()
    stub = _make_orchestrator_stub(report)
    events_path = tmp_path / "events.jsonl"
    pdf_dir = tmp_path / "generated_pdfs"
    pdf_dir.mkdir()
    policy_dir = tmp_path / "lobstertrap_agents"

    app.dependency_overrides[get_orchestrator] = lambda: stub
    app.dependency_overrides[get_events_path] = lambda: events_path
    app.dependency_overrides[get_pdf_dir] = lambda: pdf_dir
    app.dependency_overrides[get_lobstertrap_policy_dir] = lambda: policy_dir
    try:
        with TestClient(app) as c:
            # Stash the override paths so individual tests can read them back.
            c._events_path = events_path  # type: ignore[attr-defined]
            c._pdf_dir = pdf_dir  # type: ignore[attr-defined]
            c._policy_dir = policy_dir  # type: ignore[attr-defined]
            yield c
    finally:
        app.dependency_overrides.pop(get_orchestrator, None)
        app.dependency_overrides.pop(get_events_path, None)
        app.dependency_overrides.pop(get_pdf_dir, None)
        app.dependency_overrides.pop(get_lobstertrap_policy_dir, None)


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------
def test_root_returns_expected_shape(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "ComplyForge"
    assert body["version"] == "0.1.0"
    assert body["status"] == "ready"
    assert body["agents"] == ["classifier", "doc_agent", "policy_agent"]


# ---------------------------------------------------------------------------
# POST /api/analyze
# ---------------------------------------------------------------------------
def test_post_analyze_returns_full_compliance_report(client: TestClient) -> None:
    response = client.post("/api/analyze", json=_agent_payload())
    assert response.status_code == 200
    body = response.json()
    # Validate the full ComplianceReport shape via the Pydantic model itself.
    parsed = ComplianceReport.model_validate(body)
    assert parsed.agent.name == "ResumeRanker"
    assert parsed.classification.tier == RiskTier.HIGH_RISK
    assert len(parsed.technical_file.sections) == 9
    assert parsed.policy.rules_count == 5
    assert parsed.pdf_path == "generated_pdfs/resumeranker.pdf"


# ---------------------------------------------------------------------------
# GET /api/sample-agents
# ---------------------------------------------------------------------------
def test_get_sample_agents_returns_list(client: TestClient) -> None:
    response = client.get("/api/sample-agents")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    # Phase 5 doesn't ship sample_agents.json yet — empty list is acceptable.


# ---------------------------------------------------------------------------
# GET /api/pdf/{filename}
# ---------------------------------------------------------------------------
def test_get_pdf_missing_returns_404(client: TestClient) -> None:
    response = client.get("/api/pdf/nonexistent.pdf")
    assert response.status_code == 404


def test_get_pdf_rejects_path_traversal(client: TestClient) -> None:
    response = client.get("/api/pdf/..%2Fsomething.pdf")
    # FastAPI may normalise the URL; just assert non-200 and never 500.
    assert response.status_code in (400, 404)


# ---------------------------------------------------------------------------
# POST /api/enforcement/event  +  GET /api/enforcement/events
# ---------------------------------------------------------------------------
def test_enforcement_round_trip_writes_jsonl_and_reads_back(
    client: TestClient,
) -> None:
    event = EnforcementEvent(
        timestamp=datetime(2026, 5, 17, 13, 0, tzinfo=timezone.utc),
        agent_name="ResumeRanker",
        rule_triggered="pii_egress_human_review",
        action="HUMAN_REVIEW",
        request_snippet="redacted",
        metadata={"score": 0.91},
    )
    payload = event.model_dump(mode="json")

    post = client.post("/api/enforcement/event", json=payload)
    assert post.status_code == 201
    assert post.json() == {"ok": True}

    # Confirm JSONL on disk: exactly one line, parseable.
    events_path: Path = client._events_path  # type: ignore[attr-defined]
    assert events_path.exists()
    raw_lines = [ln for ln in events_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(raw_lines) == 1
    parsed = json.loads(raw_lines[0])
    assert parsed["agent_name"] == "ResumeRanker"
    assert parsed["action"] == "HUMAN_REVIEW"

    # GET round-trip.
    get = client.get("/api/enforcement/events?limit=10")
    assert get.status_code == 200
    listed = get.json()
    assert isinstance(listed, list)
    assert len(listed) == 1
    assert listed[0]["agent_name"] == "ResumeRanker"
    assert listed[0]["rule_triggered"] == "pii_egress_human_review"


def test_enforcement_events_returns_empty_when_file_missing(
    client: TestClient,
) -> None:
    # tmp_path is fresh per fixture invocation, so the file doesn't exist yet.
    response = client.get("/api/enforcement/events")
    assert response.status_code == 200
    assert response.json() == []


def test_enforcement_events_respects_limit(client: TestClient) -> None:
    base = EnforcementEvent(
        timestamp=datetime(2026, 5, 17, 13, 0, tzinfo=timezone.utc),
        agent_name="ResumeRanker",
        rule_triggered="rule",
        action="LOG",
        request_snippet="x",
    )
    for i in range(3):
        evt = base.model_copy(update={"rule_triggered": f"rule_{i}"})
        r = client.post("/api/enforcement/event", json=evt.model_dump(mode="json"))
        assert r.status_code == 201

    response = client.get("/api/enforcement/events?limit=2")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    # `limit` returns the LAST N events, so we expect rule_1 + rule_2.
    assert [e["rule_triggered"] for e in body] == ["rule_1", "rule_2"]


# ---------------------------------------------------------------------------
# POST /api/analyze/stream (SSE)
# ---------------------------------------------------------------------------
def test_analyze_stream_emits_done_event(client: TestClient) -> None:
    with client.stream("POST", "/api/analyze/stream", json=_agent_payload()) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        body = "".join(response.iter_text())

    # SSE frames are separated by a blank line; each frame starts with `data: `.
    frames = [f for f in body.split("\n\n") if f.strip()]
    assert frames, "SSE stream produced no frames"
    parsed_events: list[dict] = []
    for frame in frames:
        line = frame.strip()
        assert line.startswith("data: "), f"bad SSE frame: {frame!r}"
        parsed_events.append(json.loads(line[len("data: "):]))

    steps = [(e["step"], e["status"]) for e in parsed_events]
    assert steps[0] == ("classifying", "started")
    assert steps[-1] == ("done", "completed")

    final = parsed_events[-1]
    assert final["payload"]["agent"]["name"] == "ResumeRanker"
    assert final["payload"]["classification"]["tier"] == "high_risk"


# ---------------------------------------------------------------------------
# Phase 10: POST /api/deploy-policy/{agent_slug}
# ---------------------------------------------------------------------------
_REAL_LOBSTERTRAP_YAML = """\
version: "1.0"
policy_name: complyforge-resumeranker
default_action: ALLOW
ingress_rules:
  - name: prompt_injection_block
    description: Article 15 cybersecurity controls.
    priority: 100
    action: DENY
    deny_message: blocked
    conditions:
      - field: contains_injection_patterns
        match_type: boolean
        value: true
egress_rules:
  - name: pii_egress_human_review
    description: Article 10 data governance.
    priority: 90
    action: HUMAN_REVIEW
    conditions:
      - field: contains_pii
        match_type: boolean
        value: true
"""


def _seed_sidecar(client: TestClient, slug: str, *, policy_yaml: str | None = None) -> Path:
    """Write a ComplianceReport sidecar at <pdf_dir>/<slug>.json for tests."""
    sidecar = client._pdf_dir / f"{slug}.json"  # type: ignore[attr-defined]
    payload = {
        "agent": _agent_payload(),
        "classification": {
            "tier": "high_risk",
            "confidence": 0.92,
            "triggered_articles": ["Annex III(4)"],
            "rationale": "rationale",
            "obligations": [],
        },
        "technical_file": {
            "agent_name": "ResumeRanker",
            "risk_tier": "high_risk",
            "generated_at": "2026-05-17T12:00:00+00:00",
            "sections": [],
            "fria_summary": "",
            "datasheet": {},
        },
        "policy": {
            "name": "complyforge-resumeranker",
            "yaml": policy_yaml if policy_yaml is not None else _REAL_LOBSTERTRAP_YAML,
            "purpose": "p",
            "rules_count": 2,
        },
        "pdf_path": "generated_pdfs/resumeranker.pdf",
    }
    sidecar.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return sidecar


def test_deploy_policy_uses_sidecar_and_returns_expected_shape(
    client: TestClient,
) -> None:
    _seed_sidecar(client, "resumeranker")
    response = client.post("/api/deploy-policy/resumeranker", json={})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["deployed"] is True
    assert body["agent_slug"] == "resumeranker"
    assert body["reload_method"] == "manual_restart_required"
    assert body["rule_count"] == 2
    assert body["policy_path"].endswith("/resumeranker.yaml")

    # File actually written to the override policy dir.
    policy_dir: Path = client._policy_dir  # type: ignore[attr-defined]
    written = policy_dir / "resumeranker.yaml"
    assert written.exists()
    on_disk = written.read_text(encoding="utf-8")
    assert "policy_name: complyforge-resumeranker" in on_disk
    assert "ingress_rules" in on_disk


def test_deploy_policy_accepts_explicit_yaml_override(client: TestClient) -> None:
    explicit = _REAL_LOBSTERTRAP_YAML.replace(
        "complyforge-resumeranker", "complyforge-override"
    )
    response = client.post(
        "/api/deploy-policy/override-agent",
        json={"policy_yaml": explicit},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["agent_slug"] == "override-agent"
    written = client._policy_dir / "override-agent.yaml"  # type: ignore[attr-defined]
    assert written.exists()
    assert "complyforge-override" in written.read_text(encoding="utf-8")


def test_deploy_policy_returns_404_when_no_sidecar(client: TestClient) -> None:
    response = client.post("/api/deploy-policy/no-such-agent", json={})
    assert response.status_code == 404


def test_deploy_policy_returns_400_for_invalid_yaml(client: TestClient) -> None:
    response = client.post(
        "/api/deploy-policy/resumeranker",
        json={"policy_yaml": "this: is: not: valid: yaml: ["},
    )
    assert response.status_code == 400


def test_deploy_policy_returns_400_for_non_mapping_yaml(client: TestClient) -> None:
    response = client.post(
        "/api/deploy-policy/resumeranker",
        json={"policy_yaml": "- one\n- two\n"},
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Phase 10: GET /api/inventory/zip
# ---------------------------------------------------------------------------
import zipfile  # noqa: E402  (local import keeps top of file unchanged)
from io import BytesIO  # noqa: E402


def test_inventory_zip_returns_404_when_empty(client: TestClient) -> None:
    response = client.get("/api/inventory/zip")
    assert response.status_code == 404


def test_inventory_zip_streams_pdf_and_json_members(client: TestClient) -> None:
    pdf_dir: Path = client._pdf_dir  # type: ignore[attr-defined]
    (pdf_dir / "resumeranker.pdf").write_bytes(b"%PDF-1.4 fake")
    (pdf_dir / "resumeranker.json").write_text(
        json.dumps({"agent": {"name": "ResumeRanker"}}), encoding="utf-8"
    )
    # An unrelated file that must be excluded from the zip.
    (pdf_dir / "scratch.txt").write_text("ignore me", encoding="utf-8")

    response = client.get("/api/inventory/zip")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "complyforge-inventory.zip" in response.headers.get(
        "content-disposition", ""
    )

    with zipfile.ZipFile(BytesIO(response.content)) as zf:
        names = sorted(zf.namelist())
    assert names == ["resumeranker.json", "resumeranker.pdf"]


# ---------------------------------------------------------------------------
# v0.3.0: POST /api/extract-descriptor (Multimodal Intelligence track)
# ---------------------------------------------------------------------------
from app.routers import analyze as analyze_router  # noqa: E402


def _png_bytes() -> bytes:
    """Return the bytes of a 1x1 white PNG (no Pillow needed by callers)."""
    return bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
        "0000000d49444154789c63f8ffff3f0005fe02fea7c6e9930000000049454e44ae"
        "426082"
    )


def _canned_descriptor_dict() -> dict:
    return {
        "name": "ContractReviewer",
        "purpose": "Review and flag risky clauses in vendor contracts",
        "domain": "legal",
        "inputs": ["contract_text"],
        "outputs": ["risk_flags", "summary"],
        "affects_humans": True,
        "sample_prompts": [
            "Flag any auto-renewal clauses in this MSA.",
            "Summarise indemnity exposure in plain English.",
            "List GDPR data-processing obligations triggered.",
        ],
        "tools": ["pdf_reader", "diff_tool"],
    }


def test_extract_descriptor_returns_valid_agent_descriptor(
    client: TestClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Multimodal endpoint returns an AgentDescriptor when Gemini is mocked."""
    captured: dict = {}

    def fake_extract(content: bytes, content_type: str) -> dict:
        captured["content_type"] = content_type
        captured["bytes_len"] = len(content)
        return _canned_descriptor_dict()

    monkeypatch.setattr(analyze_router, "_extract_descriptor_sync", fake_extract)

    response = client.post(
        "/api/extract-descriptor",
        files={"file": ("agent.png", _png_bytes(), "image/png")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    parsed = AgentDescriptor.model_validate(body)
    assert parsed.name == "ContractReviewer"
    assert parsed.domain == "legal"
    assert len(parsed.sample_prompts) >= 3
    assert captured["content_type"] == "image/png"
    assert captured["bytes_len"] == len(_png_bytes())


def test_extract_descriptor_rejects_unsupported_file_type(
    client: TestClient,
) -> None:
    """Endpoint must return 400 for content types outside the allowed set."""
    response = client.post(
        "/api/extract-descriptor",
        files={"file": ("readme.txt", b"hello world", "text/plain")},
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_extract_descriptor_supports_pdf_upload(
    client: TestClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PDF content type takes the upload_file path (mocked here)."""
    def fake_extract(content: bytes, content_type: str) -> dict:
        assert content_type == "application/pdf"
        return _canned_descriptor_dict()

    monkeypatch.setattr(analyze_router, "_extract_descriptor_sync", fake_extract)

    response = client.post(
        "/api/extract-descriptor",
        files={"file": ("agent.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert response.status_code == 200
    AgentDescriptor.model_validate(response.json())


def test_extract_descriptor_returns_400_when_extraction_fails(
    client: TestClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Any exception from the extractor surfaces as a 400 with a useful detail."""
    def fake_extract(content: bytes, content_type: str) -> dict:
        raise RuntimeError("Gemini outage")

    monkeypatch.setattr(analyze_router, "_extract_descriptor_sync", fake_extract)

    response = client.post(
        "/api/extract-descriptor",
        files={"file": ("agent.png", _png_bytes(), "image/png")},
    )
    assert response.status_code == 400
    assert "Extraction failed" in response.json()["detail"]


def test_extract_descriptor_rejects_invalid_descriptor_json(
    client: TestClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If Gemini returns valid JSON that fails AgentDescriptor validation -> 400."""
    def fake_extract(content: bytes, content_type: str) -> dict:
        return {"unexpected": "shape"}

    monkeypatch.setattr(analyze_router, "_extract_descriptor_sync", fake_extract)

    response = client.post(
        "/api/extract-descriptor",
        files={"file": ("agent.png", _png_bytes(), "image/png")},
    )
    assert response.status_code == 400
    assert "AgentDescriptor" in response.json()["detail"]
