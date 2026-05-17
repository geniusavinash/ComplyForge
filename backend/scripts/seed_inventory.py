"""Seed the ComplyForge inventory by POSTing every sample agent to the live API.

For each entry in `backend/app/data/sample_agents.json`:
  1. POST the AgentDescriptor to <BASE_URL>/api/analyze.
  2. Save the full ComplianceReport JSON next to its PDF in
     `backend/generated_pdfs/<slug>.json` using the same slug helper the
     orchestrator uses, so the JSON sits beside `<slug>.pdf` written by the
     PDF render step.
  3. Print one line per agent (name, tier, rules_count, pdf_path, elapsed)
     and a final total elapsed.

Run from `backend/` with the venv active and the backend already running:

    uvicorn main:app --port 8000
    python scripts/seed_inventory.py

Configure the target backend with the ``COMPLYFORGE_BASE_URL`` env var if it
is not the default ``http://localhost:8000``.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import httpx

# Make `app` importable when invoked from backend/.
_HERE = Path(__file__).resolve().parent
_BACKEND = _HERE.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.agents.orchestrator import slug  # noqa: E402

DEFAULT_BASE_URL = "http://localhost:8000"
BASE_URL = os.environ.get("COMPLYFORGE_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
SAMPLE_AGENTS_PATH = _BACKEND / "app" / "data" / "sample_agents.json"
OUTPUT_DIR = _BACKEND / "generated_pdfs"
REQUEST_TIMEOUT = httpx.Timeout(120.0, connect=10.0)


def _load_sample_agents() -> list[dict]:
    with SAMPLE_AGENTS_PATH.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise RuntimeError(
            f"{SAMPLE_AGENTS_PATH} must contain a JSON array of agents."
        )
    return data


def _seed_one(client: httpx.Client, agent: dict) -> dict:
    name = agent.get("name", "agent")
    started = time.perf_counter()
    response = client.post(f"{BASE_URL}/api/analyze", json=agent)
    response.raise_for_status()
    elapsed = time.perf_counter() - started

    report = response.json()
    output_path = OUTPUT_DIR / f"{slug(name)}.json"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)

    classification = report.get("classification", {}) or {}
    policy = report.get("policy", {}) or {}
    return {
        "name": name,
        "tier": classification.get("tier", "unknown"),
        "rules_count": policy.get("rules_count", 0),
        "pdf_path": report.get("pdf_path", ""),
        "json_path": str(output_path),
        "elapsed_seconds": round(elapsed, 2),
    }


def main() -> int:
    agents = _load_sample_agents()
    print(f"ComplyForge seed: {len(agents)} agents -> {BASE_URL}/api/analyze")
    print("-" * 72)

    total_started = time.perf_counter()
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            for agent in agents:
                summary = _seed_one(client, agent)
                print(
                    f"  {summary['name']:<14} tier={summary['tier']:<13} "
                    f"rules={summary['rules_count']:<2} "
                    f"pdf={summary['pdf_path']} "
                    f"elapsed={summary['elapsed_seconds']}s"
                )
    except httpx.ConnectError:
        print(
            f"\nERROR: could not reach {BASE_URL}. Start the backend first:\n"
            "    uvicorn main:app --port 8000\n"
            "Then re-run: python scripts/seed_inventory.py",
            file=sys.stderr,
        )
        return 2
    except httpx.HTTPStatusError as exc:
        print(
            f"\nERROR: backend returned {exc.response.status_code} "
            f"for {exc.request.url}: {exc.response.text[:300]}",
            file=sys.stderr,
        )
        return 3

    total_elapsed = round(time.perf_counter() - total_started, 2)
    print("-" * 72)
    print(f"Done. Total elapsed: {total_elapsed}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
