"""Tests for CriticAgent.

Gemini is fully mocked. We verify:
  * Calls gemini exactly once per review().
  * Returns a CriticReview with confidence_delta clamped to [-1.0, 1.0].
  * Fallback path when gemini raises: returns the documented safe-default
    (agreed=True, confidence_delta=0.0, concerns=["critic unavailable"],
    suggestion=None).
  * Post-processing truncates concerns to at most 3 entries.
  * Suggestion is dropped (set to None) whenever agreed=True, even if the
    underlying Gemini response contained one.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from app.agents.critic import CriticAgent
from app.schemas import (
    AgentDescriptor,
    ClassificationResult,
    CriticReview,
    RiskTier,
)
from app.services.gemini_client import GeminiClientError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
def _agent() -> AgentDescriptor:
    return AgentDescriptor(
        name="ResumeRanker",
        purpose="Rank resumes",
        domain="HR",
        inputs=["resume_pdf"],
        outputs=["score"],
        affects_humans=True,
        sample_prompts=["score this"],
        tools=["pdf_extractor"],
    )


def _classification() -> ClassificationResult:
    return ClassificationResult(
        tier=RiskTier.HIGH_RISK,
        confidence=0.85,
        triggered_articles=["Annex III(4)", "Article 6"],
        rationale="HR screening triggers Annex III(4).",
        obligations=["Maintain Article 11 file"],
    )


def _make_gemini(return_value: CriticReview) -> AsyncMock:
    mock = AsyncMock()
    mock.generate_structured = AsyncMock(return_value=return_value)
    return mock


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_review_calls_gemini_exactly_once() -> None:
    review = CriticReview(agreed=True, confidence_delta=0.1, concerns=[], suggestion=None)
    gemini = _make_gemini(review)
    critic = CriticAgent(gemini=gemini)
    asyncio.run(critic.review(_agent(), _classification()))

    assert gemini.generate_structured.await_count == 1


def test_review_returns_critic_review_with_valid_delta_range() -> None:
    # Build a review at the edge of the allowed range to prove the schema
    # constraint AND the agent's clamp path both accept it.
    review = CriticReview(
        agreed=False,
        confidence_delta=-1.0,
        concerns=["Annex III(4) likely under-weighted"],
        suggestion="Consider promoting to HIGH_RISK under Annex III(4).",
    )
    gemini = _make_gemini(review)
    critic = CriticAgent(gemini=gemini)
    result = asyncio.run(critic.review(_agent(), _classification()))

    assert isinstance(result, CriticReview)
    assert -1.0 <= result.confidence_delta <= 1.0
    assert result.agreed is False
    assert result.suggestion is not None  # preserved because agreed=False


def test_review_falls_back_when_gemini_raises() -> None:
    gemini = AsyncMock()
    gemini.generate_structured = AsyncMock(side_effect=GeminiClientError("boom"))
    critic = CriticAgent(gemini=gemini)
    result = asyncio.run(critic.review(_agent(), _classification()))

    assert result.agreed is True
    assert result.confidence_delta == 0.0
    assert result.concerns == ["critic unavailable"]
    assert result.suggestion is None
    assert gemini.generate_structured.await_count == 1


def test_review_falls_back_when_gemini_raises_unexpected_error() -> None:
    gemini = AsyncMock()
    gemini.generate_structured = AsyncMock(side_effect=RuntimeError("unexpected"))
    critic = CriticAgent(gemini=gemini)
    result = asyncio.run(critic.review(_agent(), _classification()))

    # Documented safe default applies for ANY exception, not just GeminiClientError.
    assert result.agreed is True
    assert result.confidence_delta == 0.0
    assert result.concerns == ["critic unavailable"]
    assert result.suggestion is None


def test_review_trims_concerns_to_max_three() -> None:
    review = CriticReview(
        agreed=False,
        confidence_delta=-0.4,
        concerns=[
            "concern one referencing Article 6",
            "concern two referencing Annex III(4)",
            "concern three referencing Article 9",
            "concern four — must be dropped",
            "concern five — must be dropped",
        ],
        suggestion="Re-anchor to Annex III(4).",
    )
    gemini = _make_gemini(review)
    critic = CriticAgent(gemini=gemini)
    result = asyncio.run(critic.review(_agent(), _classification()))

    assert len(result.concerns) <= 3
    assert result.concerns[0].startswith("concern one")
    assert result.concerns[-1].startswith("concern three")


def test_review_suggestion_is_none_when_agreed() -> None:
    # Even though Gemini returns a stray suggestion, the post-processor must
    # null it out when agreed=True (no actionable disagreement to surface).
    review = CriticReview(
        agreed=True,
        confidence_delta=0.2,
        concerns=["minor wording nit"],
        suggestion="this should be dropped because we agree",
    )
    gemini = _make_gemini(review)
    critic = CriticAgent(gemini=gemini)
    result = asyncio.run(critic.review(_agent(), _classification()))

    assert result.agreed is True
    assert result.suggestion is None
