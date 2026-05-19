"""DocAgent — generates the Article 11 technical file via concurrent Gemini calls.

Concurrency contract (the locked architecture):
  All 9 Article 11 sections are generated in parallel via `asyncio.gather`.
  For HIGH_RISK agents the FRIA narrative is gathered alongside, giving 10
  concurrent Gemini calls. This is the only concurrent expansion in the
  whole project — no further fan-out beyond DocAgent.

Hallucinated section counts are auto-corrected: extras dropped, missing
padded with a labelled placeholder so the renderer can rely on the count.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from app.data.eu_ai_act_taxonomy import ARTICLE_11_SECTIONS, FRIA_SECTIONS
from app.schemas import (
    AgentDescriptor,
    Article11Section,
    ClassificationResult,
    RiskTier,
    TechnicalFile,
)
from app.services.gemini_client import GeminiClient, get_gemini

logger = logging.getLogger(__name__)

EXPECTED_SECTION_COUNT: int = len(ARTICLE_11_SECTIONS)  # 9


SECTION_PROMPT_TEMPLATE = """You are drafting Article 11 / Annex IV technical documentation for an enterprise AI agent under Regulation (EU) 2024/1689 (the "EU AI Act").

WRITE: Section {section_number} — {section_heading}
ANNEX IV GUIDANCE: {prompt_hint}

AGENT
  name: {name}
  purpose: {purpose}
  domain: {domain}
  inputs: {inputs}
  outputs: {outputs}
  affects_humans: {affects_humans}
  tools: {tools}

CLASSIFICATION
  tier: {tier}
  triggered_articles: {triggered_articles}
  rationale: {rationale}

MANDATORY RULES
  * Output 2-4 short paragraphs of body text only. No markdown headings, no bullet lists.
  * Cite at least one specific EU AI Act Article number (for example "in accordance with Article 9 risk management" or "under Article 14 human oversight"). Use only real Articles: 5, 6, 9, 10, 11, 14, 15, 27, 47, 50, 72, 73, 99 and Annex III/IV.
  * Ground every statement in the agent descriptor and classification rationale above. Do not invent vendor names, dataset names, or quantitative metrics.
  * Where a fact is not supplied, write "[to be supplied by the provider]" instead of fabricating.
  * Do not repeat the section heading inside the body.
"""


FRIA_PROMPT_TEMPLATE = """You are drafting a Fundamental Rights Impact Assessment (FRIA) under Article 27 of the EU AI Act for the high-risk AI agent described below. Cover all six FRIA sub-sections in order:

{fria_outline}

AGENT
  name: {name}
  purpose: {purpose}
  domain: {domain}
  inputs: {inputs}
  outputs: {outputs}

CLASSIFICATION
  tier: {tier}
  triggered_articles: {triggered_articles}
  rationale: {rationale}

MANDATORY RULES
  * Produce a single connected narrative organised under the six headings shown above. Use the heading text verbatim followed by 1-3 short paragraphs.
  * Cite Article 27 explicitly, plus at least one of Article 9, 10, 14, or 72 where appropriate.
  * Do not fabricate quantitative claims. Mark unknowns as "[to be supplied by the deployer]".
"""


_FRIA_NOT_REQUIRED_NOTE = (
    "Fundamental Rights Impact Assessment (FRIA) is not required for this agent. "
    "Article 27 of the EU AI Act mandates a FRIA only for high-risk systems "
    "deployed by public bodies or in specified Annex III areas (creditworthiness "
    "assessment, life/health insurance pricing, law enforcement, and similar). "
    "The agent has been classified as '{tier}', placing it outside the Article 27 "
    "scope. This determination must be re-evaluated if the system undergoes a "
    "substantial modification or its deployment context changes; refer to "
    "Article 27(2) for re-assessment triggers."
)


class DocAgent:
    """Generate a `TechnicalFile` from an `AgentDescriptor` + `ClassificationResult`."""

    def __init__(self, gemini: GeminiClient | None = None) -> None:
        self._gemini = gemini

    @property
    def gemini(self) -> GeminiClient:
        if self._gemini is None:
            self._gemini = get_gemini()
        return self._gemini

    async def generate(
        self,
        agent: AgentDescriptor,
        classification: ClassificationResult,
    ) -> TechnicalFile:
        section_coros = [
            self._generate_section(agent, classification, idx, meta)
            for idx, meta in enumerate(ARTICLE_11_SECTIONS, start=1)
        ]

        if classification.tier == RiskTier.HIGH_RISK:
            # 9 sections + 1 FRIA = 10 concurrent Gemini calls.
            results = await asyncio.gather(
                *section_coros, self._generate_fria(agent, classification),
            )
            section_results: list[Article11Section] = list(results[:-1])
            fria_summary: str = results[-1]
        else:
            section_results = list(await asyncio.gather(*section_coros))
            fria_summary = _FRIA_NOT_REQUIRED_NOTE.format(tier=classification.tier.value)

        return TechnicalFile(
            agent_name=agent.name,
            risk_tier=classification.tier,
            generated_at=datetime.now(timezone.utc),
            sections=self._normalise_sections(section_results),
            fria_summary=fria_summary,
            datasheet=self._build_datasheet(agent, classification),
        )

    # ------------------------------------------------------------------
    async def _generate_section(
        self,
        agent: AgentDescriptor,
        classification: ClassificationResult,
        section_number: int,
        meta: dict[str, Any],
    ) -> Article11Section:
        prompt = SECTION_PROMPT_TEMPLATE.format(
            section_number=section_number,
            section_heading=meta["heading"],
            prompt_hint=meta["prompt_hint"],
            name=agent.name, purpose=agent.purpose, domain=agent.domain,
            inputs=agent.inputs, outputs=agent.outputs,
            affects_humans=agent.affects_humans, tools=agent.tools,
            tier=classification.tier.value,
            triggered_articles=classification.triggered_articles,
            rationale=classification.rationale,
        )
        body = await self.gemini.generate_text(prompt)
        return Article11Section(heading=meta["heading"], body=(body or "").strip())

    async def _generate_fria(
        self, agent: AgentDescriptor, classification: ClassificationResult,
    ) -> str:
        outline = "\n".join(
            f"  {i}. {s['heading']} — {s['prompt_hint']}"
            for i, s in enumerate(FRIA_SECTIONS, start=1)
        )
        prompt = FRIA_PROMPT_TEMPLATE.format(
            fria_outline=outline,
            name=agent.name, purpose=agent.purpose, domain=agent.domain,
            inputs=agent.inputs, outputs=agent.outputs,
            tier=classification.tier.value,
            triggered_articles=classification.triggered_articles,
            rationale=classification.rationale,
        )
        body = await self.gemini.generate_text(prompt)
        return (body or "").strip()

    @staticmethod
    def _build_datasheet(
        agent: AgentDescriptor, classification: ClassificationResult,
    ) -> dict[str, Any]:
        inputs_str = ", ".join(agent.inputs) if agent.inputs else "unspecified"
        outputs_str = ", ".join(agent.outputs) if agent.outputs else "unspecified"
        return {
            "model_provider": "[to be supplied by the provider]",
            "intended_use": agent.purpose,
            "training_data_summary": (
                f"Inputs ingested by the agent: {inputs_str}. Detailed training "
                "corpus and provenance to be supplied by the underlying model "
                "provider in accordance with Article 10 data governance."
            ),
            "performance_metrics": (
                "Accuracy, robustness, and cybersecurity metrics to be supplied "
                "per Article 15 and continuously tracked under the Article 72 "
                "post-market monitoring plan."
            ),
            "known_limitations": (
                f"Use is restricted to the {agent.domain} domain; outputs "
                f"({outputs_str}) must not be relied upon outside this scope "
                "without re-classification under Article 6."
            ),
            "human_oversight": (
                "Article 14 oversight measures: deployer-side review of outputs "
                "that affect natural persons, with documented escalation paths "
                f"and triggered articles {classification.triggered_articles}."
            ),
            "contact": "[to be supplied by the provider]",
        }

    @staticmethod
    def _normalise_sections(
        section_results: list[Article11Section],
    ) -> list[Article11Section]:
        """Auto-correct hallucinated section counts."""
        n = EXPECTED_SECTION_COUNT
        if len(section_results) > n:
            logger.warning("DocAgent received %d sections, truncating to %d",
                           len(section_results), n)
            return list(section_results[:n])
        if len(section_results) < n:
            logger.warning("DocAgent received %d sections, padding to %d",
                           len(section_results), n)
            padded = list(section_results)
            for i in range(len(section_results), n):
                meta = ARTICLE_11_SECTIONS[i]
                padded.append(Article11Section(
                    heading=meta["heading"],
                    body=(
                        f"[Auto-generated placeholder for section {i + 1}: "
                        f"{meta['heading']}. Section text was not produced by "
                        "the upstream model and must be drafted by the provider "
                        "before regulatory submission, in accordance with "
                        "Article 11 and Annex IV.]"
                    ),
                ))
            return padded
        return list(section_results)


__all__ = [
    "DocAgent",
    "EXPECTED_SECTION_COUNT",
    "SECTION_PROMPT_TEMPLATE",
    "FRIA_PROMPT_TEMPLATE",
]
