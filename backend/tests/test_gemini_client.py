"""Tests for the Gemini client wrapper.

These tests never make real network calls — google-generativeai is mocked.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from app.config import Settings
from app.services.gemini_client import GeminiClient, GeminiClientError


class _Echo(BaseModel):
    message: str
    score: float


def _make_response(text: str) -> SimpleNamespace:
    """Build a minimal stand-in for google.generativeai's response object."""

    return SimpleNamespace(
        text=text,
        candidates=[],
        usage_metadata=SimpleNamespace(
            prompt_token_count=10,
            candidates_token_count=20,
            total_token_count=30,
        ),
    )


# ---------------------------------------------------------------------------
# Constructor behaviour
# ---------------------------------------------------------------------------
def test_instantiation_fails_when_api_key_missing() -> None:
    empty_settings = Settings(gemini_api_key="")
    with pytest.raises(GeminiClientError) as exc_info:
        GeminiClient(settings=empty_settings)
    assert "GEMINI_API_KEY" in str(exc_info.value)


def test_instantiation_succeeds_with_explicit_api_key() -> None:
    with patch("app.services.gemini_client.genai") as mock_genai:
        mock_genai.GenerativeModel.return_value = MagicMock()
        client = GeminiClient(api_key="test-key", model="gemini-test")
        mock_genai.configure.assert_called_once_with(api_key="test-key")
        mock_genai.GenerativeModel.assert_called_once_with("gemini-test")
        assert client is not None


# ---------------------------------------------------------------------------
# Retry behaviour
# ---------------------------------------------------------------------------
def test_generate_structured_retries_on_transient_error() -> None:
    with patch("app.services.gemini_client.genai") as mock_genai:
        model = MagicMock()
        # First two calls fail with a transient error; third succeeds.
        model.generate_content.side_effect = [
            RuntimeError("503 Service Unavailable"),
            RuntimeError("deadline exceeded"),
            _make_response('{"message": "ok", "score": 0.9}'),
        ]
        mock_genai.GenerativeModel.return_value = model

        client = GeminiClient(
            api_key="test-key",
            model="gemini-test",
            max_retries=2,
            base_backoff_seconds=0.0,
        )
        result = asyncio.run(client.generate_structured("hi", _Echo))

        assert isinstance(result, _Echo)
        assert result.message == "ok"
        assert result.score == pytest.approx(0.9)
        assert model.generate_content.call_count == 3


def test_generate_structured_raises_after_exhausting_retries() -> None:
    with patch("app.services.gemini_client.genai") as mock_genai:
        model = MagicMock()
        model.generate_content.side_effect = RuntimeError("503 Service Unavailable")
        mock_genai.GenerativeModel.return_value = model

        client = GeminiClient(
            api_key="test-key",
            model="gemini-test",
            max_retries=2,
            base_backoff_seconds=0.0,
        )

        with pytest.raises(GeminiClientError):
            asyncio.run(client.generate_structured("hi", _Echo))

        assert model.generate_content.call_count == 3  # initial + 2 retries


def test_non_transient_error_is_not_retried() -> None:
    with patch("app.services.gemini_client.genai") as mock_genai:
        model = MagicMock()
        model.generate_content.side_effect = ValueError("invalid prompt")
        mock_genai.GenerativeModel.return_value = model

        client = GeminiClient(
            api_key="test-key",
            model="gemini-test",
            max_retries=2,
            base_backoff_seconds=0.0,
        )

        with pytest.raises(GeminiClientError):
            asyncio.run(client.generate_text("hi"))

        assert model.generate_content.call_count == 1


# ---------------------------------------------------------------------------
# Plain text + structured parsing
# ---------------------------------------------------------------------------
def test_generate_text_returns_response_text() -> None:
    with patch("app.services.gemini_client.genai") as mock_genai:
        model = MagicMock()
        model.generate_content.return_value = _make_response("hello world")
        mock_genai.GenerativeModel.return_value = model

        client = GeminiClient(api_key="test-key", model="gemini-test")
        text = asyncio.run(client.generate_text("greet"))

        assert text == "hello world"


def test_generate_structured_validates_against_schema() -> None:
    with patch("app.services.gemini_client.genai") as mock_genai:
        model = MagicMock()
        model.generate_content.return_value = _make_response(
            '{"message": "hi", "score": 0.42}'
        )
        mock_genai.GenerativeModel.return_value = model

        client = GeminiClient(api_key="test-key", model="gemini-test")
        result = asyncio.run(client.generate_structured("prompt", _Echo))

        assert result == _Echo(message="hi", score=0.42)


def test_generate_structured_raises_on_bad_json() -> None:
    with patch("app.services.gemini_client.genai") as mock_genai:
        model = MagicMock()
        model.generate_content.return_value = _make_response("not json {")
        mock_genai.GenerativeModel.return_value = model

        client = GeminiClient(api_key="test-key", model="gemini-test")

        with pytest.raises(GeminiClientError):
            asyncio.run(client.generate_structured("prompt", _Echo))
