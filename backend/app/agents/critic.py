"""CriticAgent — independent second-opinion review of the classifier output.

Why a critic agent (Intelligent Reasoning track):
  Single-shot classification under high-stakes regulation is fragile. The
  CriticAgent provides a counterfactual check: given the agent descriptor
  and the classifier's verdict, would an independent reviewer agree? It
  emits a `CriticReview` with agreement, a confidence delta, up to three
  concerns, and an optional alternative-tier suggestion. The orchestrator
  uses the review to annotate the rationale and surface uncertainty — it
  does NOT silently change tiers (out of scope for v0.3.0).

Robustness:
  Exactly one Gemini call per `review()`. If the Gemini call raises for any
  reason, the agent returns a safe-default review so the pipeline never
  blocks on critic outage.
"""

from __future__ import annotations

import logging
from typing import Final

from app.schemas import (
    AgentDescriptor,
    ClassificationResult,
    CriticReview,
)
from app.services.gemini_client import GeminiClient, GeminiClientError, get_gemini

logger = logging.getLogger(__name__)


_MAX_CONCERNS: Final[int] = 3
_UNAVAILABLE_REVIEW = CriticReview(
    agreed=True,
    confidence_delta=0.0,
    concerns=["critic unavailable"],
    suggestion=None,
)


CRITIC_PROMPT_TEMPLATE = """You are the ComplyForge independent CRITIC.
You are an EU AI Act compliance reviewer asked to second-guess another model's
risk classification of an enterprise AI agent under Regulation (EU) 2024/1689.

Read the AGENT and the CLASSIFIER VERDICT below, then return a JSON
CriticReview with:

  agreed (bool):
    True if the assigned tier ({tier}) looks correct for this agent under the
    EU AI Act. False if you have specific, defensible reasons to disagree.

  confidence_delta (float in [-1.0, 1.0]):
    How much should we adjust the classifier's confidence ({confidence})?
    Negative values lower confidence (you disagree or see reasons to doubt);
    positive values raise confidence (you strongly agree). Stay within
    [-1.0, 1.0]. Use 0.0 if you have no strong signal.

  concerns (list of up to 3 short strings):
    The most specific, actionable concerns you have about the classification.
    Each concern should reference an EU AI Act article, annex, or principle
    where possible. Empty list is fine if you have no concerns.

  suggestion (string or null):
    If your concerns are serious enough to warrant a different tier or a
    different article anchor, state that here in one sentence (e.g.
    "Consider promoting to HIGH_RISK under Annex III(4) given employment-
    decision impact"). Otherwise null.

You MUST NOT change the tier directly — that is the orchestrator's call. Your
job is to surface disagreement and uncertainty, not to override.

AGENT
  name: {name}
  purpose: {purpose}
  domain: {domain}
  affects_humans: {affects_humans}
  inputs: {inputs}
  outputs: {outputs}
  sample_prompts: {sample_prompts}
  tools: {tools}

CLASSIFIER VERDICT
  tier: {tier}
  confidence: {confidence}
  triggered_articles: {triggered_articles}
  rationale: {rationale}
  obligations: {obligations}
"""


def _trim_concerns(concerns: list[str] | None) -> list[str]:
    """Strip empty/whitespace entries and truncate to _MAX_CONCERNS items."""
    if not concerns:
        return []
    cleaned: list[str] = []
    for c in concerns:
        if isinstance(c, str) and c.strip():
            cleaned.append(c.strip())
        if len(cleaned) >= _MAX_CONCERNS:
            break
    return cleaned


def _clamp_delta(delta: float) -> float:
    """Clamp the confidence delta into the schema-valid [-1.0, 1.0] range."""
    try:
        d = float(delta)
    except (TypeError, ValueError):
        return 0.0
    if d != d:  # NaN
        return 0.0
    if d < -1.0:
        return -1.0
    if d > 1.0:
        return 1.0
    return d


def _normalize_suggestion(agreed: bool, suggestion: str | None) -> str | None:
    """When the critic agrees, drop any leftover suggestion text."""
    if agreed:
        return None
    if isinstance(suggestion, str) and suggestion.strip():
        return suggestion.strip()
    return None


def _post_process(review: CriticReview) -> CriticReview:
    """Trim concerns, clamp delta, drop suggestion when agreed."""
    return review.model_copy(
        update={
            "concerns": _trim_concerns(list(review.concerns)),
            "confidence_delta": _clamp_delta(review.confidence_delta),
            "suggestion": _normalize_suggestion(review.agreed, review.suggestion),
        }
    )


class CriticAgent:
    """One async Gemini call -> validated CriticReview, with safe fallback."""

    def __init__(self, gemini: GeminiClient | None = None) -> None:
        self._gemini = gemini

    @property
    def gemini(self) -> GeminiClient:
        if self._gemini is None:
            self._gemini = get_gemini()
        return self._gemini

    async def review(
        self,
        agent: AgentDescriptor,
        classification: ClassificationResult,
    ) -> CriticReview:
        prompt = self._build_prompt(agent, classification)
        try:
            raw = await self.gemini.generate_structured(prompt, CriticReview)
        except GeminiClientError as exc:
            logger.warning("CriticAgent Gemini call failed; returning safe default: %s", exc)
            return _UNAVAILABLE_REVIEW.model_copy()
        except Exception as exc:  # noqa: BLE001
            logger.warning("CriticAgent unexpected error; returning safe default: %s", exc)
            return _UNAVAILABLE_REVIEW.model_copy()
        return _post_process(raw)

    @staticmethod
    def _build_prompt(
        agent: AgentDescriptor,
        classification: ClassificationResult,
    ) -> str:
        return CRITIC_PROMPT_TEMPLATE.format(
            name=agent.name,
            purpose=agent.purpose,
            domain=agent.domain,
            affects_humans=agent.affects_humans,
            inputs=agent.inputs,
            outputs=agent.outputs,
            sample_prompts=agent.sample_prompts,
            tools=agent.tools,
            tier=classification.tier.value,
            confidence=classification.confidence,
            triggered_articles=classification.triggered_articles,
            rationale=classification.rationale,
            obligations=classification.obligations,
        )


__all__ = ["CriticAgent", "CRITIC_PROMPT_TEMPLATE"]
