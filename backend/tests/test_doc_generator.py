"""Tests for DocAgent.

Mocks GeminiClient — no live API calls. Verifies:
  * HIGH_RISK fixture produces 9 sections, non-empty FRIA, datasheet with
    all 7 keys.
  * The 9 section calls + FRIA call run concurrently (10 calls under 0.3 s
    when each call sleeps 0.1 s — sequential would be ~1.0 s).
  * MINIMAL_RISK produces a short FRIA-not-required note and only 9 calls.
  * Hallucinated section counts auto-correct: extras dropped, missing padded.
"""

from __future__ import annotations

import asyncio
import time

import pytest

from app.agents.doc_generator import (
    EXPECTED_SECTION_COUNT,
    FRIA_PROMPT_TEMPLATE,
    SECTION_PROMPT_TEMPLATE,
    DocAgent,
)
from app.data.eu_ai_act_taxonomy import ARTICLE_11_SECTIONS
from app.schemas import (
    AgentDescriptor,
    Article11Section,
    ClassificationResult,
    RiskTier,
    TechnicalFile,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
def _high_risk_agent() -> AgentDescriptor:
    return AgentDescriptor(
        name="ResumeRanker",
        purpose="Score and rank inbound resumes for shortlisting",
        domain="HR",
        inputs=["resume_pdf", "job_description"],
        outputs=["score", "shortlist_recommendation"],
        affects_humans=True,
        sample_prompts=["Score this resume against the JD"],
        tools=["pdf_extractor"],
    )


def _high_risk_classification() -> ClassificationResult:
    return ClassificationResult(
        tier=RiskTier.HIGH_RISK,
        confidence=0.92,
        triggered_articles=["Annex III(4)", "Article 6"],
        rationale="HR resume screening is Annex III(4) employment use.",
        obligations=[
            "Maintain Article 11 technical file",
            "Conduct Article 27 FRIA",
        ],
    )


def _minimal_risk_agent() -> AgentDescriptor:
    return AgentDescriptor(
        name="RecipeBuddy",
        purpose="Suggest dinner recipes",
        domain="consumer-app",
        inputs=["pantry_items"],
        outputs=["recipe_suggestions"],
        affects_humans=False,
        sample_prompts=["What can I cook with chicken?"],
        tools=[],
    )


def _minimal_risk_classification() -> ClassificationResult:
    return ClassificationResult(
        tier=RiskTier.MINIMAL_RISK,
        confidence=0.9,
        triggered_articles=[],
        rationale="No rights impact, outside Annex III.",
        obligations=[],
    )


class _FakeGemini:
    """Stand-in GeminiClient for unit tests.

    Records every prompt and (optionally) sleeps `delay` seconds per call so
    we can assert concurrency. Returns a static response by default.
    """

    def __init__(self, delay: float = 0.0, response: str | None = None) -> None:
        self.delay = delay
        self.response = (
            response
            if response is not None
            else "Generated body in accordance with Article 11 and Article 9."
        )
        self.calls: list[str] = []

    async def generate_text(self, prompt: str, system: str | None = None) -> str:
        self.calls.append(prompt)
        if self.delay:
            await asyncio.sleep(self.delay)
        return self.response

    async def generate_structured(self, prompt, response_schema, system=None):  # pragma: no cover - unused
        raise AssertionError("DocAgent should not call generate_structured")


# ---------------------------------------------------------------------------
# Behaviour tests
# ---------------------------------------------------------------------------
def test_high_risk_returns_nine_sections_with_fria_and_full_datasheet() -> None:
    fake = _FakeGemini()
    tf = asyncio.run(DocAgent(gemini=fake).generate(
        _high_risk_agent(), _high_risk_classification(),
    ))

    assert isinstance(tf, TechnicalFile)
    assert len(tf.sections) == EXPECTED_SECTION_COUNT == 9
    for sec, meta in zip(tf.sections, ARTICLE_11_SECTIONS):
        assert sec.heading == meta["heading"]
        assert sec.body  # non-empty
    assert tf.fria_summary.strip() != ""
    assert len(fake.calls) == 10  # 9 sections + 1 FRIA
    expected_keys = {
        "model_provider", "intended_use", "training_data_summary",
        "performance_metrics", "known_limitations", "human_oversight", "contact",
    }
    assert set(tf.datasheet.keys()) == expected_keys


def test_high_risk_fans_out_ten_concurrent_calls_under_threshold() -> None:
    """Concurrency proof: 10 x 0.1 s sleeps must finish in well under 0.3 s."""
    fake = _FakeGemini(delay=0.1)
    agent = DocAgent(gemini=fake)

    start = time.perf_counter()
    asyncio.run(agent.generate(_high_risk_agent(), _high_risk_classification()))
    elapsed = time.perf_counter() - start

    assert len(fake.calls) == 10, (
        f"Expected 10 concurrent Gemini calls, observed {len(fake.calls)}"
    )
    assert elapsed < 0.3, (
        f"Concurrency contract violated: 10 x 0.1s sleeps took {elapsed:.3f}s "
        "(sequential would be ~1.0s, expected < 0.3s)"
    )


def test_minimal_risk_skips_fria_call_and_uses_canned_note() -> None:
    fake = _FakeGemini()
    tf = asyncio.run(DocAgent(gemini=fake).generate(
        _minimal_risk_agent(), _minimal_risk_classification(),
    ))

    assert len(tf.sections) == 9
    assert "not required" in tf.fria_summary.lower()
    assert "Article 27" in tf.fria_summary
    # Only 9 calls — no FRIA Gemini call for non-HIGH_RISK tiers.
    assert len(fake.calls) == 9


def test_section_prompt_template_demands_article_citation() -> None:
    assert "Article" in SECTION_PROMPT_TEMPLATE
    assert "Cite at least one specific EU AI Act Article number" in SECTION_PROMPT_TEMPLATE


def test_fria_prompt_template_cites_article_27() -> None:
    assert "Article 27" in FRIA_PROMPT_TEMPLATE


def test_normalise_sections_pads_when_too_few() -> None:
    short = [Article11Section(
        heading=ARTICLE_11_SECTIONS[0]["heading"], body="kept body",
    )]
    out = DocAgent._normalise_sections(short)

    assert len(out) == 9
    assert out[0].body == "kept body"
    for filled in out[1:]:
        assert "placeholder" in filled.body.lower()
        assert "Article 11" in filled.body


def test_normalise_sections_truncates_when_too_many() -> None:
    extras = [
        Article11Section(heading=f"Heading {i}", body=f"body {i}")
        for i in range(15)
    ]
    out = DocAgent._normalise_sections(extras)

    assert len(out) == 9
    assert out[0].heading == "Heading 0"
    assert out[8].heading == "Heading 8"


def test_normalise_sections_passes_exact_count_through_unchanged() -> None:
    exact = [
        Article11Section(heading=meta["heading"], body=f"body {i}")
        for i, meta in enumerate(ARTICLE_11_SECTIONS)
    ]
    out = DocAgent._normalise_sections(exact)

    assert len(out) == 9
    assert [s.body for s in out] == [s.body for s in exact]


def test_constructor_accepts_optional_gemini_for_dependency_injection() -> None:
    fake = _FakeGemini()
    agent = DocAgent(gemini=fake)
    assert agent.gemini is fake


def test_each_section_prompt_carries_classification_context() -> None:
    """Every prompt sent to Gemini must surface the agent + classification."""
    fake = _FakeGemini()
    asyncio.run(DocAgent(gemini=fake).generate(
        _high_risk_agent(), _high_risk_classification(),
    ))

    for prompt in fake.calls[:9]:
        assert "ResumeRanker" in prompt
        assert "high_risk" in prompt
        assert "Annex III(4)" in prompt
