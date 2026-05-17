"""Tests for ClassifierAgent.

All Gemini calls are mocked via unittest.mock.AsyncMock — no live API hits.
Three primary fixtures (high-risk HR screener, prohibited workplace emotion
analyzer, minimal-risk recipe recommender) plus post-processing tests for the
citation filter and the precautionary low-confidence promotion.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

from app.agents.classifier import CLASSIFIER_PROMPT_TEMPLATE, ClassifierAgent
from app.schemas import AgentDescriptor, ClassificationResult, RiskTier


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
def _hr_screener() -> AgentDescriptor:
    return AgentDescriptor(
        name="ResumeRanker",
        purpose="Rank inbound resumes for shortlisting by recruiters",
        domain="HR",
        inputs=["resume_pdf", "job_description"],
        outputs=["candidate_score", "shortlist_recommendation"],
        affects_humans=True,
        sample_prompts=["Score this resume against the JD"],
        tools=["pdf_extractor", "vector_db"],
    )


def _emotion_analyzer() -> AgentDescriptor:
    return AgentDescriptor(
        name="EmotionPulse",
        purpose="Detect employee mood from webcam feeds during work hours",
        domain="HR",
        inputs=["webcam_video"],
        outputs=["mood_label", "engagement_score"],
        affects_humans=True,
        sample_prompts=["Score the emotional state of this employee right now"],
        tools=["face_api"],
    )


def _recipe_recommender() -> AgentDescriptor:
    return AgentDescriptor(
        name="RecipeBuddy",
        purpose="Suggest dinner recipes based on pantry contents",
        domain="consumer-app",
        inputs=["pantry_items"],
        outputs=["recipe_suggestions"],
        affects_humans=False,
        sample_prompts=["What can I cook with chicken and rice?"],
        tools=["recipe_db"],
    )


def _mock_with(result: ClassificationResult) -> AsyncMock:
    """Return an AsyncMock GeminiClient whose generate_structured awaits to `result`."""
    mock = AsyncMock()
    mock.generate_structured = AsyncMock(return_value=result)
    return mock


# ---------------------------------------------------------------------------
# Prompt template — must cover all 4 tiers + the citation rule
# ---------------------------------------------------------------------------
def test_prompt_template_covers_all_four_tiers_and_citation_rule() -> None:
    template = CLASSIFIER_PROMPT_TEMPLATE
    for marker in ("PROHIBITED", "HIGH_RISK", "LIMITED_RISK", "MINIMAL_RISK"):
        assert marker in template, f"Tier marker {marker} missing from prompt template"
    assert "CITATION RULE" in template
    # Template must surface real citation forms the validator accepts
    assert "Article 5" in template
    assert "Article 6" in template
    assert "Article 11" in template
    assert "Article 50" in template
    assert "Annex III" in template


# ---------------------------------------------------------------------------
# Three required fixtures
# ---------------------------------------------------------------------------
def test_high_risk_hr_screener_returns_high_risk_with_annex_iii_4() -> None:
    canned = ClassificationResult(
        tier=RiskTier.HIGH_RISK,
        confidence=0.92,
        triggered_articles=["Annex III(4)", "Article 6"],
        rationale="HR resume screening is Annex III(4) employment, classified high-risk under Article 6.",
        obligations=[
            "Maintain Article 11 technical file",
            "Implement Article 14 human oversight",
            "Conduct Article 27 FRIA",
        ],
    )
    mock = _mock_with(canned)
    agent = ClassifierAgent(gemini=mock)

    result = asyncio.run(agent.classify(_hr_screener()))

    assert result.tier == RiskTier.HIGH_RISK
    assert "Annex III(4)" in result.triggered_articles
    assert mock.generate_structured.await_count == 1


def test_prohibited_workplace_emotion_returns_prohibited_with_article_5_1_f() -> None:
    canned = ClassificationResult(
        tier=RiskTier.PROHIBITED,
        confidence=0.97,
        triggered_articles=["Article 5(1)(f)"],
        rationale="Workplace emotion recognition is prohibited under Article 5(1)(f).",
        obligations=["Discontinue deployment immediately"],
    )
    mock = _mock_with(canned)
    agent = ClassifierAgent(gemini=mock)

    result = asyncio.run(agent.classify(_emotion_analyzer()))

    assert result.tier == RiskTier.PROHIBITED
    assert "Article 5(1)(f)" in result.triggered_articles


def test_minimal_risk_recipe_recommender_returns_minimal_risk() -> None:
    canned = ClassificationResult(
        tier=RiskTier.MINIMAL_RISK,
        confidence=0.88,
        triggered_articles=[],
        rationale="Recipe suggestion has no rights impact and is outside Annex III.",
        obligations=[],
    )
    mock = _mock_with(canned)
    agent = ClassifierAgent(gemini=mock)

    result = asyncio.run(agent.classify(_recipe_recommender()))

    assert result.tier == RiskTier.MINIMAL_RISK
    assert result.triggered_articles == []


# ---------------------------------------------------------------------------
# Post-processing rules
# ---------------------------------------------------------------------------
def test_post_processing_drops_hallucinated_citations() -> None:
    canned = ClassificationResult(
        tier=RiskTier.HIGH_RISK,
        confidence=0.85,
        triggered_articles=[
            "Annex III(4)",      # valid
            "Article 6",         # valid
            "Article 5(1)(a)",   # valid
            "Article 999",       # hallucinated
            "Annex VII(2)",      # wrong annex
            "GDPR Article 22",   # wrong regulation
            "",                  # empty
        ],
        rationale="Mixed-quality citations.",
        obligations=["Implement Article 14 oversight"],
    )
    mock = _mock_with(canned)
    agent = ClassifierAgent(gemini=mock)

    result = asyncio.run(agent.classify(_hr_screener()))

    assert "Annex III(4)" in result.triggered_articles
    assert "Article 6" in result.triggered_articles
    assert "Article 5(1)(a)" in result.triggered_articles
    assert "Article 999" not in result.triggered_articles
    assert "Annex VII(2)" not in result.triggered_articles
    assert "GDPR Article 22" not in result.triggered_articles
    assert "" not in result.triggered_articles
    assert len(result.triggered_articles) == 3


def test_precautionary_low_confidence_promotes_to_high_risk() -> None:
    canned = ClassificationResult(
        tier=RiskTier.MINIMAL_RISK,
        confidence=0.3,
        triggered_articles=[],
        rationale="Unclear from descriptor.",
        obligations=[],
    )
    mock = _mock_with(canned)
    agent = ClassifierAgent(gemini=mock)

    result = asyncio.run(agent.classify(_recipe_recommender()))

    assert result.tier == RiskTier.HIGH_RISK
    assert "precautionary" in result.rationale.lower()


def test_precautionary_does_not_override_prohibited_at_low_confidence() -> None:
    canned = ClassificationResult(
        tier=RiskTier.PROHIBITED,
        confidence=0.4,
        triggered_articles=["Article 5(1)(f)"],
        rationale="Low-confidence prohibited match.",
        obligations=["Discontinue deployment"],
    )
    mock = _mock_with(canned)
    agent = ClassifierAgent(gemini=mock)

    result = asyncio.run(agent.classify(_emotion_analyzer()))

    assert result.tier == RiskTier.PROHIBITED
    assert "precautionary" not in result.rationale.lower()


def test_classify_makes_exactly_one_gemini_call() -> None:
    canned = ClassificationResult(
        tier=RiskTier.MINIMAL_RISK,
        confidence=0.9,
        triggered_articles=[],
        rationale="No rights impact.",
        obligations=[],
    )
    mock = _mock_with(canned)
    agent = ClassifierAgent(gemini=mock)

    asyncio.run(agent.classify(_recipe_recommender()))

    assert mock.generate_structured.await_count == 1
