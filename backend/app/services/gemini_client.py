"""Async wrapper around google-generativeai for ComplyForge.

Surface area:
  * generate_structured(prompt, response_schema) -> validated Pydantic model
  * generate_text(prompt, system=None) -> str
  * get_gemini() module-level singleton

Retries transient errors twice with exponential backoff. Logs token usage.
"""

from __future__ import annotations

import asyncio
import json
import logging
from functools import lru_cache
from typing import Any, Type, TypeVar

import google.generativeai as genai
from pydantic import BaseModel, ValidationError

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

_TRANSIENT_ERROR_FRAGMENTS = (
    "deadline", "timeout", "unavailable", "503", "502", "500",
    "rate limit", "resource exhausted",
)

# Gemini's proto Schema only supports a subset of JSON Schema.
# Stripping unsupported keys avoids "Unknown field for Schema: maximum" etc.
_GEMINI_SUPPORTED_SCHEMA_KEYS = {
    "type", "nullable", "format", "description", "enum",
    "maxItems", "minItems", "properties", "required", "items",
    "propertyOrdering", "anyOf",
}


class GeminiClientError(RuntimeError):
    """Raised when the Gemini client cannot fulfil a request."""


def _is_transient(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return any(fragment in msg for fragment in _TRANSIENT_ERROR_FRAGMENTS)


def _inline_refs(schema: Any, defs: dict[str, Any]) -> Any:
    """Recursively resolve $ref pointers against the provided $defs map."""
    if isinstance(schema, dict):
        ref = schema.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/$defs/"):
            target = defs.get(ref.removeprefix("#/$defs/"), {})
            return _inline_refs(target, defs)
        return {k: _inline_refs(v, defs) for k, v in schema.items() if k != "$defs"}
    if isinstance(schema, list):
        return [_inline_refs(item, defs) for item in schema]
    return schema


def _strip_unsupported(schema: Any) -> Any:
    """Drop keys Gemini's Schema proto rejects (maximum, minimum, title, $defs, ...).

    `properties` and `enum` carry data whose keys/values are user-defined (not
    JSON Schema keywords) — only recurse into their sub-schemas, never filter
    their direct children.
    """
    if isinstance(schema, dict):
        cleaned: dict[str, Any] = {}
        for k, v in schema.items():
            if k not in _GEMINI_SUPPORTED_SCHEMA_KEYS:
                continue
            if k == "properties" and isinstance(v, dict):
                cleaned[k] = {pk: _strip_unsupported(pv) for pk, pv in v.items()}
            elif k in {"enum", "required"} and isinstance(v, list):
                cleaned[k] = list(v)
            else:
                cleaned[k] = _strip_unsupported(v)
        return cleaned
    if isinstance(schema, list):
        return [_strip_unsupported(item) for item in schema]
    return schema


def build_gemini_schema(pydantic_cls: Type[BaseModel]) -> dict[str, Any]:
    """Convert a Pydantic v2 model class into a Gemini-compatible schema dict."""
    raw = pydantic_cls.model_json_schema()
    defs = raw.get("$defs", {})
    inlined = _inline_refs(raw, defs)
    return _strip_unsupported(inlined)


class GeminiClient:
    """Thin async-friendly wrapper around google-generativeai."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        settings: Settings | None = None,
        max_retries: int = 2,
        base_backoff_seconds: float = 0.5,
    ) -> None:
        cfg = settings or get_settings()
        resolved_key = (api_key if api_key is not None else cfg.gemini_api_key) or ""
        if not resolved_key:
            raise GeminiClientError(
                "GEMINI_API_KEY is empty. Set it in backend/.env (see .env.example)."
            )
        self._api_key = resolved_key
        self._model_name = model or cfg.gemini_model
        self._max_retries = max(0, int(max_retries))
        self._base_backoff = float(base_backoff_seconds)
        genai.configure(api_key=self._api_key)
        self._model = genai.GenerativeModel(self._model_name)

    async def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system: str | None = None,
    ) -> T:
        """Call Gemini in JSON mode and validate against a Pydantic schema."""
        generation_config = {
            "response_mime_type": "application/json",
            "response_schema": build_gemini_schema(response_schema),
        }
        raw = await self._call_with_retry(prompt, system, generation_config)
        return self._parse_structured(raw, response_schema)

    async def generate_text(self, prompt: str, system: str | None = None) -> str:
        """Call Gemini in plain-text mode."""
        raw = await self._call_with_retry(prompt, system, None)
        return self._extract_text(raw)

    async def _call_with_retry(
        self,
        prompt: str,
        system: str | None,
        generation_config: dict[str, Any] | None,
    ) -> Any:
        attempt = 0
        last_exc: BaseException | None = None
        while attempt <= self._max_retries:
            try:
                response = await self._invoke(prompt, system, generation_config)
                self._log_usage(response)
                return response
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt >= self._max_retries or not _is_transient(exc):
                    logger.error("Gemini call failed (attempt %s/%s): %s",
                                 attempt + 1, self._max_retries + 1, exc)
                    raise GeminiClientError(str(exc)) from exc
                backoff = self._base_backoff * (2 ** attempt)
                logger.warning("Transient Gemini error (attempt %s/%s): %s — retry in %.2fs",
                               attempt + 1, self._max_retries + 1, exc, backoff)
                await asyncio.sleep(backoff)
                attempt += 1
        raise GeminiClientError(str(last_exc) if last_exc else "Unknown Gemini error")

    async def _invoke(
        self,
        prompt: str,
        system: str | None,
        generation_config: dict[str, Any] | None,
    ) -> Any:
        contents = prompt if system is None else f"{system}\n\n{prompt}"
        kwargs: dict[str, Any] = {}
        if generation_config is not None:
            kwargs["generation_config"] = generation_config
        return await asyncio.to_thread(self._model.generate_content, contents, **kwargs)

    @staticmethod
    def _extract_text(response: Any) -> str:
        text = getattr(response, "text", None)
        if isinstance(text, str) and text:
            return text
        for candidate in getattr(response, "candidates", None) or []:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", None) or []:
                part_text = getattr(part, "text", None)
                if isinstance(part_text, str) and part_text:
                    return part_text
        raise GeminiClientError("Gemini response did not contain any text.")

    @classmethod
    def _parse_structured(cls, response: Any, schema: Type[T]) -> T:
        text = cls._extract_text(response)
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise GeminiClientError(f"Gemini returned non-JSON output: {text[:200]}") from exc
        try:
            return schema.model_validate(payload)
        except ValidationError as exc:
            raise GeminiClientError(
                f"Gemini JSON did not match schema {schema.__name__}: {exc}"
            ) from exc

    @staticmethod
    def _log_usage(response: Any) -> None:
        usage = getattr(response, "usage_metadata", None)
        if usage is None:
            return
        logger.info(
            "Gemini usage — prompt=%s candidates=%s total=%s",
            getattr(usage, "prompt_token_count", None),
            getattr(usage, "candidates_token_count", None),
            getattr(usage, "total_token_count", None),
        )


@lru_cache
def get_gemini() -> GeminiClient:
    """Return a process-wide cached GeminiClient."""
    return GeminiClient()
