"""Tests for the Phase 6 demo data: sample agents + attack payloads.

These tests are pure data-shape checks — no Gemini calls, no live backend.
They guard the contract that Phase 7 (Lobster Trap) and the demo narrative
rely on:
  * 5 sample AgentDescriptors covering all four EU AI Act risk tiers by intent.
  * 8 attack payloads with valid Article references, kebab-case ids,
    actions in the documented Lobster Trap vocabulary, and rule ids that
    PolicyAgent actually emits.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app.data.eu_ai_act_taxonomy import (
    HIGH_RISK_DOMAINS,
    LIMITED_RISK_TRIGGERS,
    PROHIBITED_PRACTICES,
)
from app.schemas import AgentDescriptor


_DATA_DIR = Path(__file__).resolve().parent.parent / "app" / "data"
SAMPLE_AGENTS_PATH = _DATA_DIR / "sample_agents.json"
ATTACK_PAYLOADS_PATH = _DATA_DIR / "attack_payloads.json"


# Lobster Trap action vocabulary (mirrors policy_generator.VALID_ACTIONS).
LOBSTER_TRAP_ACTIONS: frozenset[str] = frozenset({
    "ALLOW", "DENY", "LOG", "HUMAN_REVIEW",
    "QUARANTINE", "RATE_LIMIT", "MODIFY", "REDIRECT",
})

# Rule ids that PolicyAgent actually emits across the four tiers
# (see backend/app/agents/policy_generator.py).
POLICY_AGENT_RULE_IDS: frozenset[str] = frozenset({
    "prohibited_practice_block",
    "pii_egress_human_review",
    "decision_without_oversight_human_review",
    "prompt_injection_block",
    "comprehensive_logging",
    "rate_limit_unusual_surges",
    "disclose_ai_interaction",
    "deepfake_generation_log",
    "log_everything",
})

# Standalone EU AI Act citations the demo is allowed to reference directly.
_BASE_ARTICLE_CITATIONS: frozenset[str] = frozenset({
    "Article 5",
    "Article 5(1)(a)", "Article 5(1)(b)", "Article 5(1)(c)", "Article 5(1)(d)",
    "Article 5(1)(e)", "Article 5(1)(f)", "Article 5(1)(g)", "Article 5(1)(h)",
    "Article 9", "Article 10", "Article 11", "Article 12", "Article 14",
    "Article 15", "Article 27", "Article 47", "Article 50",
    "Article 50(1)", "Article 50(3)", "Article 50(4)",
    "Article 72", "Article 95", "Article 99",
    "Annex III(1)", "Annex III(2)", "Annex III(3)", "Annex III(4)",
    "Annex III(5)", "Annex III(6)", "Annex III(7)", "Annex III(8)",
})


_KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _valid_article_citations() -> frozenset[str]:
    """All citations the demo may use — the base set plus every taxonomy entry."""
    citations: set[str] = set(_BASE_ARTICLE_CITATIONS)
    citations.update(p["article"] for p in PROHIBITED_PRACTICES)
    citations.update(p["annex_iii_point"] for p in HIGH_RISK_DOMAINS)
    citations.update(p["article"] for p in LIMITED_RISK_TRIGGERS)
    return frozenset(citations)


def _is_valid_article(citation: str) -> bool:
    return citation in _valid_article_citations()


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------
def _load_json(path: Path) -> list[dict]:
    raw = path.read_bytes()
    # UTF-8 with no BOM.
    assert raw[:3] != b"\xef\xbb\xbf", f"{path} has a UTF-8 BOM"
    data = json.loads(raw.decode("utf-8"))
    assert isinstance(data, list), f"{path} must contain a JSON array"
    return data


@pytest.fixture(scope="module")
def sample_agents() -> list[dict]:
    return _load_json(SAMPLE_AGENTS_PATH)


@pytest.fixture(scope="module")
def attack_payloads() -> list[dict]:
    return _load_json(ATTACK_PAYLOADS_PATH)


# ---------------------------------------------------------------------------
# sample_agents.json
# ---------------------------------------------------------------------------
def test_sample_agents_has_exactly_five_entries(sample_agents: list[dict]) -> None:
    assert len(sample_agents) == 5


def test_sample_agents_validate_against_schema(sample_agents: list[dict]) -> None:
    for entry in sample_agents:
        AgentDescriptor.model_validate(entry)


def test_sample_agents_have_unique_names(sample_agents: list[dict]) -> None:
    names = [entry["name"] for entry in sample_agents]
    assert len(names) == len(set(names)), f"duplicate agent names: {names}"


def test_sample_agents_have_min_prompts_and_tools(sample_agents: list[dict]) -> None:
    for entry in sample_agents:
        agent = AgentDescriptor.model_validate(entry)
        assert len(agent.sample_prompts) >= 3, (
            f"{agent.name} needs at least 3 sample_prompts, has {len(agent.sample_prompts)}"
        )
        assert len(agent.tools) >= 1, (
            f"{agent.name} needs at least 1 tool, has {len(agent.tools)}"
        )


def test_sample_agents_cover_all_expected_names(sample_agents: list[dict]) -> None:
    expected = {"ResumeRanker", "EmotionPulse", "CreditDecider", "SupportBot", "RecipeBuddy"}
    actual = {entry["name"] for entry in sample_agents}
    assert expected == actual, f"missing or extra agents: expected={expected}, actual={actual}"


# ---------------------------------------------------------------------------
# attack_payloads.json
# ---------------------------------------------------------------------------
def test_attack_payloads_has_exactly_eight_entries(attack_payloads: list[dict]) -> None:
    assert len(attack_payloads) == 8


def test_attack_payload_ids_are_unique_and_kebab_case(attack_payloads: list[dict]) -> None:
    ids = [entry["id"] for entry in attack_payloads]
    assert len(ids) == len(set(ids)), f"duplicate payload ids: {ids}"
    for pid in ids:
        assert _KEBAB_RE.match(pid), f"id {pid!r} is not kebab-case"


def test_attack_payload_actions_are_in_lobster_trap_vocabulary(
    attack_payloads: list[dict],
) -> None:
    for entry in attack_payloads:
        assert entry["expected_action"] in LOBSTER_TRAP_ACTIONS, (
            f"{entry['id']}: action {entry['expected_action']!r} is not in the "
            f"Lobster Trap vocabulary {sorted(LOBSTER_TRAP_ACTIONS)}"
        )


def test_attack_payload_articles_are_valid_citations(
    attack_payloads: list[dict],
) -> None:
    valid = _valid_article_citations()
    for entry in attack_payloads:
        citation = entry["eu_ai_act_article"]
        assert _is_valid_article(citation), (
            f"{entry['id']}: {citation!r} is not a recognised EU AI Act citation. "
            f"Valid citations: {sorted(valid)}"
        )


def test_attack_payload_rules_are_emitted_by_policy_agent(
    attack_payloads: list[dict],
) -> None:
    for entry in attack_payloads:
        rule = entry["expected_rule"]
        assert rule in POLICY_AGENT_RULE_IDS, (
            f"{entry['id']}: expected_rule {rule!r} is not emitted by PolicyAgent. "
            f"Valid rule ids: {sorted(POLICY_AGENT_RULE_IDS)}"
        )


def test_attack_payloads_have_required_shape(attack_payloads: list[dict]) -> None:
    required = {"id", "name", "payload", "expected_action", "expected_rule",
                "eu_ai_act_article", "narrative"}
    for entry in attack_payloads:
        missing = required - set(entry.keys())
        assert not missing, f"{entry.get('id')}: missing keys {missing}"
        for key in required:
            value = entry[key]
            assert isinstance(value, str) and value.strip(), (
                f"{entry.get('id')}: {key!r} must be a non-empty string"
            )
