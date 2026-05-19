"""Tests for PolicyAgent — Lobster Trap YAML generation.

All Gemini calls mocked via unittest.mock.AsyncMock — no live API hits.

Real Lobster Trap schema (cloned from github.com/veeainc/lobstertrap during
the build step) is the reference. Per-tier rule counts (1 / 5 / 2 / 1) are preserved
from the the architecture plan; field names match the Go loader.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import yaml

from app.agents.policy_generator import (
    REASON_PROMPT_TEMPLATE,
    VALID_ACTIONS,
    PolicyAgent,
    _ReasonItem,
    _ReasonMap,
)
from app.schemas import (
    AgentDescriptor,
    ClassificationResult,
    LobsterTrapPolicy,
    RiskTier,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _mock_with(reasons: dict[str, str] | None = None) -> AsyncMock:
    """Build an AsyncMock GeminiClient whose generate_structured returns canned reasons."""
    items = [_ReasonItem(id=k, reason=v) for k, v in (reasons or {}).items()]
    mock = AsyncMock()
    mock.generate_structured = AsyncMock(return_value=_ReasonMap(reasons=items))
    return mock


def _run(agent: AgentDescriptor, classification: ClassificationResult,
         mock: AsyncMock) -> LobsterTrapPolicy:
    return asyncio.run(PolicyAgent(gemini=mock).generate(agent, classification))


def _all_rules(parsed: dict) -> list[dict]:
    """Concatenated ingress + egress rule list, in declared order."""
    return list(parsed.get("ingress_rules") or []) + list(parsed.get("egress_rules") or [])


# ---------------------------------------------------------------------------
# Per-tier fixtures
# ---------------------------------------------------------------------------
def _prohibited_pair() -> tuple[AgentDescriptor, ClassificationResult]:
    agent = AgentDescriptor(
        name="EmotionPulse",
        purpose="Detect employee mood from webcam feeds during work hours",
        domain="HR",
        inputs=["webcam_video"],
        outputs=["mood_label", "engagement_score"],
        affects_humans=True,
        sample_prompts=["Score the emotional state of this employee right now"],
        tools=["face_api"],
    )
    classification = ClassificationResult(
        tier=RiskTier.PROHIBITED,
        confidence=0.96,
        triggered_articles=["Article 5(1)(f)"],
        rationale="Workplace emotion recognition is prohibited under Article 5(1)(f).",
        obligations=["Discontinue deployment immediately"],
    )
    return agent, classification


def _high_risk_pair() -> tuple[AgentDescriptor, ClassificationResult]:
    agent = AgentDescriptor(
        name="ResumeRanker",
        purpose="Rank inbound resumes for shortlisting by recruiters",
        domain="HR",
        inputs=["resume_pdf", "job_description"],
        outputs=["candidate_score", "shortlist_recommendation"],
        affects_humans=True,
        sample_prompts=["Score this resume against the JD"],
        tools=["pdf_extractor", "vector_db"],
    )
    classification = ClassificationResult(
        tier=RiskTier.HIGH_RISK,
        confidence=0.92,
        triggered_articles=["Annex III(4)", "Article 6"],
        rationale="HR resume screening is Annex III(4) employment.",
        obligations=[
            "Maintain Article 11 technical file",
            "Conduct Article 27 FRIA",
        ],
    )
    return agent, classification


def _limited_risk_pair() -> tuple[AgentDescriptor, ClassificationResult]:
    agent = AgentDescriptor(
        name="SupportBot",
        purpose="Customer support chatbot with order-tracking handoff",
        domain="customer-service",
        inputs=["user_message"],
        outputs=["reply_text"],
        affects_humans=True,
        sample_prompts=["Where is my order?"],
        tools=["order_api"],
    )
    classification = ClassificationResult(
        tier=RiskTier.LIMITED_RISK,
        confidence=0.85,
        triggered_articles=["Article 50(1)"],
        rationale="Direct-to-user chatbot must disclose AI interaction per Article 50(1).",
        obligations=["Disclose AI interaction"],
    )
    return agent, classification


def _minimal_risk_pair() -> tuple[AgentDescriptor, ClassificationResult]:
    agent = AgentDescriptor(
        name="RecipeBuddy",
        purpose="Suggest dinner recipes based on pantry contents",
        domain="consumer-app",
        inputs=["pantry_items"],
        outputs=["recipe_suggestions"],
        affects_humans=False,
        sample_prompts=["What can I cook with chicken and rice?"],
        tools=["recipe_db"],
    )
    classification = ClassificationResult(
        tier=RiskTier.MINIMAL_RISK,
        confidence=0.92,
        triggered_articles=[],
        rationale="No rights impact, outside Annex III.",
        obligations=[],
    )
    return agent, classification


# ---------------------------------------------------------------------------
# Top-level document shape (real Lobster Trap loader requirements)
# ---------------------------------------------------------------------------
def test_document_has_real_lobstertrap_top_level_fields() -> None:
    agent, classification = _high_risk_pair()
    policy = _run(agent, classification, _mock_with())
    parsed = yaml.safe_load(policy.yaml)
    assert parsed["version"] == "1.0"
    assert parsed["policy_name"] == "complyforge-resumeranker"
    assert parsed["default_action"] in VALID_ACTIONS
    # The Go loader requires at least one of these blocks; both exist for high-risk.
    assert "ingress_rules" in parsed
    assert "egress_rules" in parsed


# ---------------------------------------------------------------------------
# Tier behaviour tests
# ---------------------------------------------------------------------------
def test_prohibited_single_deny_rule_with_article_5_reason() -> None:
    agent, classification = _prohibited_pair()
    mock = _mock_with({
        "prohibited_practice_block":
            "Blocked under EU AI Act Article 5(1)(f) prohibition on workplace emotion recognition.",
    })
    policy = _run(agent, classification, mock)

    parsed = yaml.safe_load(policy.yaml)
    rules = _all_rules(parsed)
    assert policy.rules_count == 1
    assert len(rules) == policy.rules_count

    first_rule = rules[0]
    assert first_rule["action"] == "DENY"
    # Higher priority = evaluated first in the real schema (firewall style).
    assert first_rule["priority"] >= 100
    assert "Article 5" in first_rule["description"]
    # Default action also DENY so unmatched traffic still gets blocked.
    assert parsed["default_action"] == "DENY"


def test_high_risk_five_rules_with_pii_and_at_least_one_human_review() -> None:
    agent, classification = _high_risk_pair()
    mock = _mock_with()  # let deterministic fallback descriptions stand
    policy = _run(agent, classification, mock)

    parsed = yaml.safe_load(policy.yaml)
    rules = _all_rules(parsed)
    assert policy.rules_count == 5
    assert len(rules) == policy.rules_count

    actions = [r["action"] for r in rules]
    assert actions.count("HUMAN_REVIEW") >= 1, (
        "Expected at least one HUMAN_REVIEW rule (Article 14 oversight)"
    )

    # At least one rule mentions PII either in conditions or description text.
    pii_mentioned = any(
        "pii" in str(r.get("conditions", [])).lower()
        or "pii" in r.get("description", "").lower()
        for r in rules
    )
    assert pii_mentioned, "Expected at least one rule to mention PII"

    for action in actions:
        assert action in VALID_ACTIONS


def test_limited_risk_two_rules_with_modify_referencing_article_50() -> None:
    agent, classification = _limited_risk_pair()
    mock = _mock_with()
    policy = _run(agent, classification, mock)

    parsed = yaml.safe_load(policy.yaml)
    rules = _all_rules(parsed)
    assert policy.rules_count == 2
    assert len(rules) == policy.rules_count

    modify_rules = [r for r in rules if r["action"] == "MODIFY"]
    assert modify_rules, "Limited-risk policy must contain a MODIFY rule"
    assert any("Article 50" in r["description"] for r in modify_rules), (
        "MODIFY rule must reference Article 50 transparency"
    )


def test_minimal_risk_single_log_rule() -> None:
    agent, classification = _minimal_risk_pair()
    mock = _mock_with()
    policy = _run(agent, classification, mock)

    parsed = yaml.safe_load(policy.yaml)
    rules = _all_rules(parsed)
    assert policy.rules_count == 1
    assert len(rules) == policy.rules_count
    assert rules[0]["action"] == "LOG"


# ---------------------------------------------------------------------------
# Cross-tier guarantees
# ---------------------------------------------------------------------------
def test_generate_makes_exactly_one_gemini_call_per_tier() -> None:
    pairs = (
        _prohibited_pair(),
        _high_risk_pair(),
        _limited_risk_pair(),
        _minimal_risk_pair(),
    )
    for agent, classification in pairs:
        mock = _mock_with()
        _run(agent, classification, mock)
        assert mock.generate_structured.await_count == 1, (
            f"Expected exactly 1 Gemini call for tier {classification.tier.value}, "
            f"got {mock.generate_structured.await_count}"
        )
        # No other Gemini surface area should be touched.
        mock.generate_text.assert_not_called()


def test_rule_actions_remain_in_documented_vocabulary() -> None:
    pairs = (
        _prohibited_pair(),
        _high_risk_pair(),
        _limited_risk_pair(),
        _minimal_risk_pair(),
    )
    for agent, classification in pairs:
        mock = _mock_with()
        policy = _run(agent, classification, mock)
        parsed = yaml.safe_load(policy.yaml)
        for rule in _all_rules(parsed):
            assert rule["action"] in VALID_ACTIONS, (
                f"Rule {rule['name']} has invalid action {rule['action']!r}"
            )


def test_yaml_is_indented_block_style_and_round_trips() -> None:
    agent, classification = _high_risk_pair()
    mock = _mock_with()
    policy = _run(agent, classification, mock)

    text = policy.yaml
    parsed = yaml.safe_load(text)
    assert parsed["policy_name"] == "complyforge-resumeranker"
    assert parsed["version"] == "1.0"

    # Block style indicators
    assert "policy_name: complyforge-resumeranker" in text
    assert "version:" in text and "1.0" in text
    assert "ingress_rules:" in text or "egress_rules:" in text
    assert "- name:" in text
    assert "action:" in text
    assert "conditions:" in text
    # default_flow_style=False produces newline-separated mappings.
    assert "{policy_name:" not in text
    assert "[ingress_rules" not in text


def test_policy_name_uses_slugified_lowercased_agent_name() -> None:
    agent = AgentDescriptor(
        name="My Sample Agent",
        purpose="Test slug",
        domain="test",
    )
    classification = ClassificationResult(
        tier=RiskTier.MINIMAL_RISK,
        confidence=0.9,
        triggered_articles=[],
        rationale="ok",
        obligations=[],
    )
    mock = _mock_with()
    policy = _run(agent, classification, mock)
    assert policy.name == "complyforge-my-sample-agent"


def test_purpose_field_is_populated_per_tier() -> None:
    pairs = (
        _prohibited_pair(),
        _high_risk_pair(),
        _limited_risk_pair(),
        _minimal_risk_pair(),
    )
    for agent, classification in pairs:
        mock = _mock_with()
        policy = _run(agent, classification, mock)
        assert policy.purpose, (
            f"Empty purpose for tier {classification.tier.value}"
        )


def test_every_rule_has_at_least_one_condition() -> None:
    """Real Lobster Trap loader rejects rules with zero conditions."""
    pairs = (
        _prohibited_pair(),
        _high_risk_pair(),
        _limited_risk_pair(),
        _minimal_risk_pair(),
    )
    for agent, classification in pairs:
        mock = _mock_with()
        policy = _run(agent, classification, mock)
        parsed = yaml.safe_load(policy.yaml)
        for rule in _all_rules(parsed):
            conditions = rule.get("conditions") or []
            assert conditions, (
                f"Rule {rule['name']} has no conditions — Lobster Trap "
                "loader will reject the policy"
            )
            for cond in conditions:
                assert "field" in cond
                assert "match_type" in cond
                assert "value" in cond


# ---------------------------------------------------------------------------
# Robustness: hallucinated / missing triggered_articles
# ---------------------------------------------------------------------------
def test_empty_triggered_articles_still_produces_valid_policy() -> None:
    agent, classification = _prohibited_pair()
    classification = classification.model_copy(update={"triggered_articles": []})
    mock = _mock_with()
    policy = _run(agent, classification, mock)

    parsed = yaml.safe_load(policy.yaml)
    rules = _all_rules(parsed)
    assert policy.rules_count == 1
    first = rules[0]
    assert first["action"] == "DENY"
    # Falls back to generic "Article 5" when no specific paragraph supplied.
    assert "Article 5" in first["description"]


def test_junk_triggered_articles_still_produce_valid_policy() -> None:
    agent, classification = _high_risk_pair()
    classification = classification.model_copy(
        update={"triggered_articles": ["GDPR Article 22", "", "lol", 42]},
    )
    mock = _mock_with()
    policy = _run(agent, classification, mock)

    parsed = yaml.safe_load(policy.yaml)
    rules = _all_rules(parsed)
    assert policy.rules_count == 5
    actions = [r["action"] for r in rules]
    assert all(a in VALID_ACTIONS for a in actions)


def test_gemini_failure_falls_back_to_deterministic_descriptions() -> None:
    """If Gemini blows up, PolicyAgent must still emit a valid policy."""
    agent, classification = _high_risk_pair()
    mock = AsyncMock()
    mock.generate_structured = AsyncMock(side_effect=RuntimeError("503 unavailable"))
    policy = asyncio.run(PolicyAgent(gemini=mock).generate(agent, classification))

    parsed = yaml.safe_load(policy.yaml)
    rules = _all_rules(parsed)
    assert policy.rules_count == 5
    for rule in rules:
        assert rule["description"], f"Rule {rule['name']} has empty description"
        assert "Article" in rule["description"]
    assert mock.generate_structured.await_count == 1


# ---------------------------------------------------------------------------
# Prompt template sanity
# ---------------------------------------------------------------------------
def test_reason_prompt_template_constrains_output_shape() -> None:
    template = REASON_PROMPT_TEMPLATE
    assert "AGENT" in template
    assert "CLASSIFICATION" in template
    assert "triggered_articles" in template
    assert "EU AI Act Article" in template
    assert "Output JSON only" in template


def test_constructor_accepts_optional_gemini_for_dependency_injection() -> None:
    fake = AsyncMock()
    agent = PolicyAgent(gemini=fake)
    assert agent.gemini is fake
