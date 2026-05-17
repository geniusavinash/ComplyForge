"""Tests for the EU AI Act taxonomy data module."""

from __future__ import annotations

import pytest

from app.data.eu_ai_act_taxonomy import (
    ARTICLE_11_SECTIONS,
    FRIA_SECTIONS,
    HIGH_RISK_DOMAINS,
    LIMITED_RISK_TRIGGERS,
    PENALTY_TIERS,
    PROHIBITED_PRACTICES,
)


REQUIRED_KEYS = {
    "prohibited": {"id", "article", "title", "description", "examples"},
    "high_risk": {"id", "annex_iii_point", "title", "description", "examples"},
    "limited_risk": {"id", "article", "title", "description"},
    "article_11": {"section_id", "heading", "prompt_hint"},
    "fria": {"section_id", "heading", "prompt_hint"},
}


def test_lists_are_non_empty() -> None:
    assert PROHIBITED_PRACTICES, "PROHIBITED_PRACTICES must not be empty"
    assert HIGH_RISK_DOMAINS, "HIGH_RISK_DOMAINS must not be empty"
    assert LIMITED_RISK_TRIGGERS, "LIMITED_RISK_TRIGGERS must not be empty"
    assert ARTICLE_11_SECTIONS, "ARTICLE_11_SECTIONS must not be empty"
    assert FRIA_SECTIONS, "FRIA_SECTIONS must not be empty"
    assert PENALTY_TIERS, "PENALTY_TIERS must not be empty"


def test_prohibited_practices_count_and_keys() -> None:
    assert len(PROHIBITED_PRACTICES) == 8
    for entry in PROHIBITED_PRACTICES:
        assert REQUIRED_KEYS["prohibited"].issubset(entry.keys())
        assert isinstance(entry["examples"], list) and entry["examples"]


def test_high_risk_domains_count_and_keys() -> None:
    assert len(HIGH_RISK_DOMAINS) == 8
    for entry in HIGH_RISK_DOMAINS:
        assert REQUIRED_KEYS["high_risk"].issubset(entry.keys())
        assert isinstance(entry["examples"], list) and entry["examples"]


def test_limited_risk_triggers_keys() -> None:
    assert len(LIMITED_RISK_TRIGGERS) >= 4
    for entry in LIMITED_RISK_TRIGGERS:
        assert REQUIRED_KEYS["limited_risk"].issubset(entry.keys())


def test_article_11_sections_count_and_keys() -> None:
    assert len(ARTICLE_11_SECTIONS) == 9
    for entry in ARTICLE_11_SECTIONS:
        assert REQUIRED_KEYS["article_11"].issubset(entry.keys())
        assert entry["heading"].strip()
        assert entry["prompt_hint"].strip()


def test_fria_sections_count_and_keys() -> None:
    assert len(FRIA_SECTIONS) == 6
    for entry in FRIA_SECTIONS:
        assert REQUIRED_KEYS["fria"].issubset(entry.keys())


def test_penalty_tiers_shape() -> None:
    expected_keys = {"prohibited_practice", "high_risk_violation", "misleading_information_to_authorities"}
    assert expected_keys.issubset(PENALTY_TIERS.keys())
    for tier in PENALTY_TIERS.values():
        assert "max_eur" in tier
        assert "max_pct_turnover" in tier


@pytest.mark.parametrize(
    "collection",
    [PROHIBITED_PRACTICES, HIGH_RISK_DOMAINS, LIMITED_RISK_TRIGGERS, ARTICLE_11_SECTIONS, FRIA_SECTIONS],
)
def test_ids_are_unique(collection: list[dict]) -> None:
    id_key = "section_id" if "section_id" in collection[0] else "id"
    ids = [entry[id_key] for entry in collection]
    assert len(ids) == len(set(ids)), f"Duplicate ids in {collection}"
