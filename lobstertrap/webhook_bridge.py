"""ComplyForge webhook bridge.

Tails Veea Lobster Trap audit events and relays each one to the ComplyForge
backend at POST /api/enforcement/event so the dashboard's live enforcement
log gets populated.

Lobster Trap (verified by clone during the build) emits one event two ways:

  1. JSONL audit log written by `internal/audit/logger.go` — to stderr by
     default, or to a file when serve --audit-log <path> is set.
  2. The dashboard JSON REST endpoint at GET /_lobstertrap/api/events,
     served from `internal/dashboard/handler.go` (returns the in-memory
     ring buffer as a JSON array).

Both surfaces share the same field names. This bridge supports three input
shapes via the LOBSTERTRAP_EVENT_SOURCE env var:

  * http://host:port           ->  poll <host:port>/_lobstertrap/api/events
                                   for new events (recommended).
  * file:///path/to/audit.jsonl -> tail a JSONL audit file written by
                                   `serve --audit-log`.
  * -                          ->  read JSONL events from stdin.

Outbound POSTs use exponential backoff with jitter and infinite retry of
network errors (so the bridge survives backend restarts during a demo).

Configuration:
  COMPLYFORGE_URL           default http://localhost:8000
  LOBSTERTRAP_EVENT_SOURCE  default http://localhost:8080
  LOBSTERTRAP_POLL_INTERVAL default 1.0  (seconds, http source only)
  COMPLYFORGE_AGENT_NAME    default "lobstertrap"  (used when audit entry
                                                    has no agent_id)

Dependencies: httpx only (already in backend/requirements.txt).
"""

from __future__ import annotations

import json
import logging
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse

import httpx

logger = logging.getLogger("complyforge.webhook_bridge")


# --------------------------------------------------------------------------- #
# Field mapping                                                                #
# --------------------------------------------------------------------------- #
# Lobster Trap audit Entry  ->  ComplyForge EnforcementEvent
#   timestamp        ->  timestamp
#   agent_id         ->  agent_name (fallback: COMPLYFORGE_AGENT_NAME)
#   rule_name        ->  rule_triggered
#   action           ->  action
#   prompt           ->  request_snippet (truncated to 500 chars)
#   metadata + dir   ->  metadata (preserves direction, request_id, mismatches)
# --------------------------------------------------------------------------- #
_DEFAULT_AGENT_NAME = "lobstertrap"
_REQUEST_SNIPPET_MAX = 500


def _truncate(s: str, n: int) -> str:
    if not s:
        return ""
    return s if len(s) <= n else s[: n - 1] + "\u2026"


def _normalise_timestamp(value: Any) -> str:
    """ComplyForge expects an ISO-8601 datetime string. Pass through valid
    inputs; replace anything malformed with `now`."""
    if isinstance(value, str) and value:
        return value
    return datetime.now(timezone.utc).isoformat()


def map_event(audit_entry: dict[str, Any]) -> dict[str, Any]:
    """Translate one Lobster Trap audit entry into an EnforcementEvent dict."""
    metadata: dict[str, Any] = {
        "request_id": audit_entry.get("request_id"),
        "direction": audit_entry.get("direction"),
        "deny_message": audit_entry.get("deny_message"),
        "token_count": audit_entry.get("token_count"),
    }
    inspector_meta = audit_entry.get("metadata")
    if isinstance(inspector_meta, dict):
        metadata["inspector"] = inspector_meta
    mismatches = audit_entry.get("mismatches")
    if mismatches:
        metadata["mismatches"] = mismatches

    prompt = audit_entry.get("prompt") or ""
    if not prompt and isinstance(inspector_meta, dict):
        # Some Lobster Trap builds put the original text under metadata only.
        prompt = inspector_meta.get("prompt") or ""

    return {
        "timestamp": _normalise_timestamp(audit_entry.get("timestamp")),
        "agent_name": audit_entry.get("agent_id")
        or os.environ.get("COMPLYFORGE_AGENT_NAME", _DEFAULT_AGENT_NAME),
        "rule_triggered": audit_entry.get("rule_name") or "",
        "action": (audit_entry.get("action") or "LOG").upper(),
        "request_snippet": _truncate(str(prompt), _REQUEST_SNIPPET_MAX),
        "metadata": {k: v for k, v in metadata.items() if v is not None},
    }


# --------------------------------------------------------------------------- #
# Event sources                                                                #
# --------------------------------------------------------------------------- #
def _stdin_source() -> Iterator[dict[str, Any]]:
    """Read JSONL audit lines from stdin (Lobster Trap default audit sink)."""
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            yield json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.warning("Skipping malformed audit line: %s", exc)


def _file_source(path: Path) -> Iterator[dict[str, Any]]:
    """Tail a JSONL audit file. Polls for appended lines forever."""
    while not path.exists():
        logger.info("Waiting for audit file %s to appear...", path)
        time.sleep(1.0)
    with path.open("r", encoding="utf-8") as fh:
        # Start at end of file: only new events count.
        fh.seek(0, 2)
        while True:
            line = fh.readline()
            if not line:
                time.sleep(0.5)
                continue
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                logger.warning("Skipping malformed audit line: %s", exc)


def _http_source(base_url: str, poll_interval: float) -> Iterator[dict[str, Any]]:
    """Poll <base>/_lobstertrap/api/events. The dashboard ring buffer returns
    the most recent events; we deduplicate by request_id+direction."""
    endpoint = base_url.rstrip("/") + "/_lobstertrap/api/events"
    seen: set[tuple[str, str]] = set()
    backoff = poll_interval
    with httpx.Client(timeout=5.0) as client:
        while True:
            try:
                resp = client.get(endpoint)
                resp.raise_for_status()
                payload = resp.json()
                backoff = poll_interval  # reset on success
            except (httpx.HTTPError, ValueError) as exc:
                logger.warning(
                    "Lobster Trap dashboard at %s unreachable (%s); "
                    "retrying in %.1fs",
                    endpoint, exc, backoff,
                )
                time.sleep(backoff)
                backoff = min(backoff * 2.0, 30.0)
                continue

            events = payload if isinstance(payload, list) else []
            for raw in events:
                if not isinstance(raw, dict):
                    continue
                # Dashboard wraps PipelineEvent in {id, timestamp, direction,
                # request_id, action, rule_name, metadata, blocked, ...}.
                # Adapt to audit Entry shape that map_event expects.
                key = (
                    str(raw.get("request_id") or raw.get("id") or ""),
                    str(raw.get("direction") or ""),
                )
                if not key[0] or key in seen:
                    continue
                seen.add(key)
                yield {
                    "timestamp": raw.get("timestamp"),
                    "request_id": raw.get("request_id") or raw.get("id"),
                    "direction": raw.get("direction"),
                    "action": raw.get("action"),
                    "rule_name": raw.get("rule_name"),
                    "deny_message": raw.get("deny_message"),
                    "metadata": raw.get("metadata"),
                    # The dashboard event doesn't carry agent_id directly;
                    # leave None and let map_event fall back to env default.
                }
            time.sleep(poll_interval)


def open_event_source(spec: str) -> Iterator[dict[str, Any]]:
    """Strategy switch keyed on LOBSTERTRAP_EVENT_SOURCE."""
    if spec == "-" or spec == "stdin":
        logger.info("Reading Lobster Trap events from stdin (JSONL)")
        return _stdin_source()
    parsed = urlparse(spec)
    if parsed.scheme in {"http", "https"}:
        poll = float(os.environ.get("LOBSTERTRAP_POLL_INTERVAL", "1.0"))
        logger.info("Polling Lobster Trap dashboard at %s every %.1fs", spec, poll)
        return _http_source(spec, poll_interval=poll)
    if parsed.scheme == "file":
        path = Path(parsed.path.lstrip("/")) if os.name == "nt" else Path(parsed.path)
        logger.info("Tailing Lobster Trap audit file %s", path)
        return _file_source(path)
    # Fallback: treat as plain filesystem path.
    path = Path(spec)
    logger.info("Tailing Lobster Trap audit file %s", path)
    return _file_source(path)


# --------------------------------------------------------------------------- #
# POST relay                                                                   #
# --------------------------------------------------------------------------- #
def post_event(client: httpx.Client, complyforge_url: str, event: dict[str, Any]) -> None:
    """POST one EnforcementEvent with exponential backoff + jitter forever.

    The bridge intentionally never gives up: a hackathon demo backend may
    restart mid-stream and we want events to land once it's back.
    """
    endpoint = complyforge_url.rstrip("/") + "/api/enforcement/event"
    delay = 0.5
    while True:
        try:
            resp = client.post(endpoint, json=event, timeout=5.0)
            resp.raise_for_status()
            return
        except httpx.HTTPError as exc:
            sleep_for = delay + random.uniform(0.0, delay / 2.0)
            logger.warning(
                "POST %s failed (%s); retrying in %.2fs",
                endpoint, exc, sleep_for,
            )
            time.sleep(sleep_for)
            delay = min(delay * 2.0, 30.0)


def run() -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    complyforge_url = os.environ.get("COMPLYFORGE_URL", "http://localhost:8000")
    event_source = os.environ.get(
        "LOBSTERTRAP_EVENT_SOURCE", "http://localhost:8080",
    )
    logger.info(
        "ComplyForge webhook bridge starting (source=%s -> sink=%s)",
        event_source, complyforge_url,
    )
    relayed = 0
    with httpx.Client() as client:
        for raw in open_event_source(event_source):
            event = map_event(raw)
            post_event(client, complyforge_url, event)
            relayed += 1
            if relayed % 25 == 0:
                logger.info("Relayed %d enforcement events", relayed)


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        logger.info("Bridge interrupted; exiting cleanly.")
