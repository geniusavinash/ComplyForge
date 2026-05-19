"""ClassifierAgent — single async Gemini call mapping an AgentDescriptor to
an EU AI Act risk tier (Prohibited / High-Risk / Limited / Minimal).

Architecture note: this is ONE call per agent. Parallelism is reserved for
the build step (asyncio.gather across Article 11 sections) and the build step (Orchestrator
runs DocAgent and PolicyAgent concurrently). See the locked architecture.

Post-processing:
  * triggered_articles is filtered against the closed set of citations the
    EU AI Act actually contains (Articles 5, 6, 9, 11, 27, 50, 72, 99 and
    Annex III(1)-(8)). Hallucinated citations are silently dropped.
  * Precautionary principle: if confidence < 0.5 AND tier is not PROHIBITED,
    promote tier to HIGH_RISK and append a note to rationale.
"""

from __future__ import annotations

import logging
import re
from typing import Iterable

from app.data.eu_ai_act_taxonomy import (
    HIGH_RISK_DOMAINS,
    LIMITED_RISK_TRIGGERS,
    PROHIBITED_PRACTICES,
)
from app.schemas import AgentDescriptor, ClassificationResult, RiskTier
from app.services.gemini_client import GeminiClient, get_gemini

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prompt template (built once at import time)
# ---------------------------------------------------------------------------
def _format_prohibited() -> str:
    return "\n".join(
        f"  - [{e['article']}] {e['title']}: {e['description']}"
        f" Examples: {'; '.join(e['examples'])}"
        for e in PROHIBITED_PRACTICES
    )


def _format_high_risk() -> str:
    return "\n".join(
        f"  - [{e['annex_iii_point']}] {e['title']}: {e['description']}"
        f" Examples: {'; '.join(e['examples'])}"
        for e in HIGH_RISK_DOMAINS
    )


def _format_limited_risk() -> str:
    return "\n".join(
        f"  - [{e['article']}] {e['title']}: {e['description']}"
        for e in LIMITED_RISK_TRIGGERS
    )


CLASSIFIER_PROMPT_TEMPLATE = f"""You are the ComplyForge EU AI Act risk classifier.
Classify the AI agent below into exactly ONE of four tiers under
Regulation (EU) 2024/1689 ("EU AI Act"). Be conservative: when the agent
plausibly affects a person's rights, access, or opportunities, prefer the
higher tier.

============================================================
TIER 1 — PROHIBITED (Article 5)
Outright banned. If the agent matches ANY of these, tier MUST be "prohibited"
regardless of business intent. Maximum penalty: EUR 35M / 7% global turnover (Article 99).
{_format_prohibited()}

============================================================
TIER 2 — HIGH_RISK (Article 6 + Annex III)
Heavily regulated. Triggers obligations under Article 9 (risk management),
Article 10 (data governance), Article 11 + Annex IV (technical file),
Article 14 (human oversight), Article 27 (FRIA where applicable),
Article 72 (post-market monitoring). Maximum penalty: EUR 15M / 3% turnover.
{_format_high_risk()}

============================================================
TIER 3 — LIMITED_RISK (Article 50 transparency obligations)
Not high-risk, but must inform users of AI interaction or label synthetic
content. Includes:
{_format_limited_risk()}

============================================================
TIER 4 — MINIMAL_RISK
No specific obligations beyond voluntary codes of conduct (Article 95).
Examples: spam filters, recipe suggestion bots, recommender systems for
entertainment, productivity assistants without rights impact.

============================================================
CITATION RULE (mandatory)
Every entry in `triggered_articles` MUST be a real reference of one of these forms:
  * "Article 5"  or "Article 5(1)(a)" through "Article 5(1)(h)"
  * "Article 6"
  * "Article 9"
  * "Article 11"
  * "Article 27"
  * "Article 50"  or "Article 50(1)" / "Article 50(3)" / "Article 50(4)"
  * "Article 72"
  * "Article 99"
  * "Annex III(1)" through "Annex III(8)"
DO NOT invent article numbers, paragraphs, or annexes. If you are unsure of
the exact paragraph, cite the article alone (e.g. "Article 5"). Citations
that do not match the forms above will be rejected.

============================================================
OUTPUT (JSON only, matching the supplied schema)
  tier: "prohibited" | "high_risk" | "limited_risk" | "minimal_risk"
  confidence: float between 0.0 and 1.0
  triggered_articles: list of citation strings (see rule above)
  rationale: 2-4 sentence explanation tied to the agent's purpose / inputs / outputs
  obligations: list of operator-facing obligations (e.g. "Maintain Article 11
               technical file", "Conduct Article 27 FRIA", "Disclose AI
               interaction per Article 50")

============================================================
AGENT TO CLASSIFY
name: {{name}}
purpose: {{purpose}}
domain: {{domain}}
inputs: {{inputs}}
outputs: {{outputs}}
affects_humans: {{affects_humans}}
sample_prompts: {{sample_prompts}}
tools: {{tools}}
"""


# ---------------------------------------------------------------------------
# Citation validation
# ---------------------------------------------------------------------------
_VALID_ARTICLE_RE = re.compile(r"^\s*Article\s+(5|6|9|11|27|50|72|99)\b")
_VALID_ANNEX_RE = re.compile(r"^\s*Annex\s+III\(([1-8])\)")


def _is_valid_citation(citation: str) -> bool:
    if not isinstance(citation, str) or not citation.strip():
        return False
    return bool(_VALID_ARTICLE_RE.match(citation) or _VALID_ANNEX_RE.match(citation))


def _filter_citations(citations: Iterable[str]) -> list[str]:
    valid: list[str] = []
    for c in citations:
        if _is_valid_citation(c):
            valid.append(c.strip())
        else:
            logger.warning("ClassifierAgent dropped invalid citation: %r", c)
    return valid


_PRECAUTION_NOTE = (
    " [Precautionary principle: model confidence below 0.5; defaulted to "
    "HIGH_RISK pending human review per the architecture spec.]"
)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
class ClassifierAgent:
    """One async Gemini call -> validated ClassificationResult."""

    def __init__(self, gemini: GeminiClient | None = None) -> None:
        # Lazy resolution of the singleton so unit tests can avoid touching
        # google-generativeai at all.
        self._gemini = gemini

    @property
    def gemini(self) -> GeminiClient:
        if self._gemini is None:
            self._gemini = get_gemini()
        return self._gemini

    async def classify(self, agent: AgentDescriptor) -> ClassificationResult:
        prompt = self._build_prompt(agent)
        raw = await self.gemini.generate_structured(prompt, ClassificationResult)
        return self._post_process(raw)

    @staticmethod
    def _build_prompt(agent: AgentDescriptor) -> str:
        return CLASSIFIER_PROMPT_TEMPLATE.format(
            name=agent.name,
            purpose=agent.purpose,
            domain=agent.domain,
            inputs=agent.inputs,
            outputs=agent.outputs,
            affects_humans=agent.affects_humans,
            sample_prompts=agent.sample_prompts,
            tools=agent.tools,
        )

    @staticmethod
    def _post_process(result: ClassificationResult) -> ClassificationResult:
        cleaned = _filter_citations(result.triggered_articles)
        tier = result.tier
        rationale = result.rationale
        if result.confidence < 0.5 and tier != RiskTier.PROHIBITED:
            tier = RiskTier.HIGH_RISK
            if _PRECAUTION_NOTE.strip() not in rationale:
                rationale = rationale.rstrip() + _PRECAUTION_NOTE
        return result.model_copy(
            update={
                "tier": tier,
                "triggered_articles": cleaned,
                "rationale": rationale,
            }
        )


__all__ = ["ClassifierAgent", "CLASSIFIER_PROMPT_TEMPLATE"]
