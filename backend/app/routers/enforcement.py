"""HTTP routes for Lobster Trap enforcement events.

Endpoints:
  POST /api/enforcement/event       -> append one JSONL line
  GET  /api/enforcement/events      -> last `limit` events as JSON list

The events file path is provided through a FastAPI dependency
(`get_events_path`) so tests can override it via `app.dependency_overrides`
without polluting the real `backend/audit_logs/`.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, status

from app.schemas import EnforcementEvent

router = APIRouter(prefix="/api/enforcement", tags=["enforcement"])

DEFAULT_EVENTS_PATH = Path("audit_logs") / "events.jsonl"


def get_events_path() -> Path:
    """Default events path. Override via `app.dependency_overrides` in tests."""
    return DEFAULT_EVENTS_PATH


@router.post("/event", status_code=status.HTTP_201_CREATED)
async def append_event(
    event: EnforcementEvent,
    events_path: Path = Depends(get_events_path),
) -> dict:
    events_path = Path(events_path)
    events_path.parent.mkdir(parents=True, exist_ok=True)
    payload = event.model_dump(mode="json")
    line = json.dumps(payload, separators=(",", ":")) + "\n"
    # Crash-safe append: open in append mode, write, flush.
    with events_path.open("a", encoding="utf-8") as fh:
        fh.write(line)
        fh.flush()
    return {"ok": True}


@router.get("/events")
async def list_events(
    limit: int = 100,
    events_path: Path = Depends(get_events_path),
) -> list[dict]:
    events_path = Path(events_path)
    if not events_path.exists():
        return []
    if limit < 0:
        limit = 0
    with events_path.open("r", encoding="utf-8") as fh:
        lines = [ln for ln in fh.read().splitlines() if ln.strip()]
    if limit == 0:
        return []
    selected = lines[-limit:]
    out: list[dict] = []
    for raw in selected:
        try:
            out.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return out


__all__ = ["router", "get_events_path", "DEFAULT_EVENTS_PATH"]
