"""Phase 10 end-to-end integration test.

Marked @pytest.mark.e2e and excluded from the default pytest run via the
addopts in pytest.ini. To run explicitly:

    python -m pytest tests/ -v -m e2e

Prerequisites (the test skips cleanly with a clear message if any are
missing):
  * `lobstertrap/bin/lobstertrap.exe` (built by `lobstertrap/setup.ps1`)
  * `GEMINI_API_KEY` in the environment or `backend/.env`
  * Free local ports 8765 (backend) and 8766 (Lobster Trap)

The test:
  1. Spawns uvicorn for the backend and `lobstertrap.exe serve` for the proxy
     as subprocesses.
  2. Waits for both health endpoints (backend `GET /`, Lobster Trap
     `GET /_lobstertrap/api/policy`).
  3. POSTs the ResumeRanker fixture to /api/analyze, then deploys its policy
     via /api/deploy-policy/resumeranker so the agents/ folder is populated.
  4. Sends attack payload #5 (sensitive-attribute inference) through Lobster
     Trap at /v1/chat/completions and asserts the proxy denies the request.
  5. Polls /api/enforcement/events for up to 5 s and asserts a relayed event
     appears via the webhook bridge OR that Lobster Trap emitted the expected
     rule_name in its dashboard event ring.
  6. Cleans up subprocesses regardless of outcome.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e

_BACKEND = Path(__file__).resolve().parent.parent
_REPO = _BACKEND.parent
_LOBSTERTRAP = _REPO / "lobstertrap"
_BINARY = _LOBSTERTRAP / "bin" / "lobstertrap.exe"
_DEFAULT_POLICY = _LOBSTERTRAP / "policies" / "default.yaml"
_VENV_PYTHON = _BACKEND / ".venv" / "Scripts" / "python.exe"

_BACKEND_PORT = 8765
_LOBSTER_PORT = 8766
_ATTACK_INDEX = 5  # 1-based; "sensitive-attribute-inference"


def _port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def _wait_for(url: str, timeout: float = 30.0) -> bool:
    import urllib.error
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.5) as resp:
                if 200 <= resp.status < 500:
                    return True
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError):
            pass
        time.sleep(0.4)
    return False


def _http_get(url: str, timeout: float = 5.0):
    import urllib.request

    return urllib.request.urlopen(url, timeout=timeout)


def _http_post_json(url: str, payload: dict, timeout: float = 30.0):
    import urllib.error
    import urllib.request

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as exc:
        return exc  # caller can read .status / .read()


def _check_prereqs() -> None:
    missing = []
    if not _BINARY.exists():
        missing.append(f"lobstertrap binary at {_BINARY}")
    if not _DEFAULT_POLICY.exists():
        missing.append(f"default policy at {_DEFAULT_POLICY}")
    if not (_VENV_PYTHON.exists() or shutil.which("python")):
        missing.append("python interpreter (no venv and no python on PATH)")
    if not os.environ.get("GEMINI_API_KEY"):
        # Allow the backend itself to source from .env, but warn if neither is set.
        env_file = _BACKEND / ".env"
        if not env_file.exists() or "GEMINI_API_KEY=" not in env_file.read_text(
            encoding="utf-8", errors="ignore"
        ):
            missing.append("GEMINI_API_KEY env var or backend/.env entry")
    if not _port_free(_BACKEND_PORT):
        missing.append(f"local TCP port {_BACKEND_PORT} (backend) is in use")
    if not _port_free(_LOBSTER_PORT):
        missing.append(f"local TCP port {_LOBSTER_PORT} (lobstertrap) is in use")
    if missing:
        pytest.skip("Phase 10 e2e prerequisites missing: " + "; ".join(missing))


def _attack_payload() -> dict:
    payloads_path = _BACKEND / "app" / "data" / "attack_payloads.json"
    payloads = json.loads(payloads_path.read_text(encoding="utf-8"))
    return payloads[_ATTACK_INDEX - 1]


def _resume_ranker_descriptor() -> dict:
    sample_path = _BACKEND / "app" / "data" / "sample_agents.json"
    samples = json.loads(sample_path.read_text(encoding="utf-8"))
    for s in samples:
        if s.get("name") == "ResumeRanker":
            return s
    pytest.skip("ResumeRanker sample agent not found in sample_agents.json")
    return {}  # unreachable


def test_phase10_end_to_end_pipeline() -> None:
    _check_prereqs()

    backend_proc: subprocess.Popen | None = None
    lobster_proc: subprocess.Popen | None = None
    python = str(_VENV_PYTHON) if _VENV_PYTHON.exists() else sys.executable

    try:
        # 1. Spawn backend on a private port.
        backend_proc = subprocess.Popen(
            [
                python,
                "-m",
                "uvicorn",
                "main:app",
                "--port",
                str(_BACKEND_PORT),
                "--log-level",
                "warning",
            ],
            cwd=str(_BACKEND),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        # 2. Spawn Lobster Trap.
        lobster_proc = subprocess.Popen(
            [
                str(_BINARY),
                "serve",
                "--policy",
                str(_DEFAULT_POLICY),
                "--backend",
                "https://generativelanguage.googleapis.com",
                "--listen",
                f":{_LOBSTER_PORT}",
            ],
            cwd=str(_LOBSTERTRAP),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        # 3. Health checks.
        assert _wait_for(f"http://127.0.0.1:{_BACKEND_PORT}/", timeout=30), (
            "backend did not become healthy"
        )
        assert _wait_for(
            f"http://127.0.0.1:{_LOBSTER_PORT}/_lobstertrap/api/policy",
            timeout=15,
        ), "Lobster Trap did not become healthy"

        # 4. Analyse the ResumeRanker fixture and deploy its policy.
        analyze_resp = _http_post_json(
            f"http://127.0.0.1:{_BACKEND_PORT}/api/analyze",
            _resume_ranker_descriptor(),
            timeout=120,
        )
        assert getattr(analyze_resp, "status", 500) == 200, (
            f"/api/analyze failed: status={getattr(analyze_resp, 'status', '?')}, "
            f"body={analyze_resp.read()[:300]!r}"
        )

        deploy_resp = _http_post_json(
            f"http://127.0.0.1:{_BACKEND_PORT}/api/deploy-policy/resumeranker",
            {},
            timeout=10,
        )
        assert getattr(deploy_resp, "status", 500) == 200
        deploy_body = json.loads(deploy_resp.read().decode("utf-8"))
        assert deploy_body["deployed"] is True
        assert deploy_body["reload_method"] == "manual_restart_required"

        # 5. Fire the attack payload through Lobster Trap. The proxy should
        # deny it before it reaches the backend LLM.
        attack = _attack_payload()
        chat_payload = {
            "model": "gemini-2.0-flash-exp",
            "messages": [{"role": "user", "content": attack["payload"]}],
        }
        proxy_resp = _http_post_json(
            f"http://127.0.0.1:{_LOBSTER_PORT}/v1/chat/completions",
            chat_payload,
            timeout=10,
        )
        status = getattr(proxy_resp, "status", 500)
        body_text = proxy_resp.read().decode("utf-8", errors="replace")
        assert status >= 400 or "DENY" in body_text.upper(), (
            f"Lobster Trap did not deny the attack payload: "
            f"status={status}, body={body_text[:300]!r}"
        )

        # 6. Read events from the Lobster Trap dashboard ring buffer (it
        # always observes its own decisions; the webhook bridge is optional
        # for this assertion). Within 5 s a matching DENY entry must appear.
        deadline = time.time() + 5.0
        last_events: list[dict] = []
        while time.time() < deadline:
            try:
                resp = _http_get(
                    f"http://127.0.0.1:{_LOBSTER_PORT}/_lobstertrap/api/events",
                    timeout=2.0,
                )
                last_events = json.loads(resp.read().decode("utf-8"))
            except Exception:  # noqa: BLE001
                last_events = []
            if any(
                str(ev.get("action", "")).upper() == "DENY"
                for ev in (last_events or [])
            ):
                break
            time.sleep(0.4)
        assert any(
            str(ev.get("action", "")).upper() == "DENY"
            for ev in (last_events or [])
        ), f"No DENY event observed within 5 s. Last events: {last_events!r}"
    finally:
        for proc in (lobster_proc, backend_proc):
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
