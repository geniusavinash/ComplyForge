"""PolicyAgent — generates Veea Lobster Trap YAML policies from a tiered
classification.

Single async Gemini call per policy (the locked architecture): the
rule skeleton is hard-coded per tier and Gemini only fills in the
human-readable `description` strings, naming specific EU AI Act Article
numbers drawn from `classification.triggered_articles`. We never fan out
per-rule and never invent actions outside the documented Lobster Trap
vocabulary.

Schema reference: github.com/veeainc/lobstertrap (cloned and inspected during
the build step). The real schema differs from the the initial design shape; this module
emits the real schema:

    version: "1.0"
    policy_name: <slug>
    default_action: ALLOW | DENY | ...
    ingress_rules:
      - name: <slug>
        description: <human-readable>
        priority: <int>           # HIGHER number = evaluated first
        action: ALLOW | DENY | LOG | HUMAN_REVIEW | QUARANTINE
                | RATE_LIMIT | MODIFY | REDIRECT
        deny_message: <optional>
        conditions:
          - field: <metadata field, e.g. contains_injection_patterns>
            match_type: exact | prefix | glob | regex | range
                       | contains | boolean | threshold
            value: <typed>
            negate: <optional bool>
    egress_rules: [...same shape...]

Per-tier rule counts are preserved from the the architecture plan
(1 / 5 / 2 / 1). Field names below match the real Go loader
(`internal/policy/types.go`).
"""

from __future__ import annotations

import logging
import re
from typing import Any

import yaml
from pydantic import BaseModel, Field

from app.schemas import (
    AgentDescriptor, ClassificationResult, LobsterTrapPolicy, RiskTier,
)
from app.services.gemini_client import GeminiClient, get_gemini

logger = logging.getLogger(__name__)

# Documented Lobster Trap action vocabulary. Do not extend.
VALID_ACTIONS: frozenset[str] = frozenset({
    "ALLOW", "DENY", "LOG", "HUMAN_REVIEW",
    "QUARANTINE", "RATE_LIMIT", "MODIFY", "REDIRECT",
})

# Real metadata fields exposed by the Lobster Trap inspector. Kept here so the
# skeletons can be audited at a glance against `internal/inspector`.
_INTENT_CATEGORIES = {
    "code_execution", "file_io", "network", "system",
    "communication", "credential_access", "data_access", "general",
}


# -- Structured response schema for the single Gemini reason-fill call -----
class _ReasonItem(BaseModel):
    id: str = Field(description="Rule name matching the skeleton")
    reason: str = Field(description="<= 200 char description citing an EU AI Act Article")


class _ReasonMap(BaseModel):
    reasons: list[_ReasonItem] = Field(default_factory=list)


# -- Article-5 paragraph extraction (for prohibited-tier description) ------
_ARTICLE_5_PARA_RE = re.compile(r"Article\s+5\(1\)\([a-h]\)")


def _article_5_citation(triggered_articles: list[str]) -> str:
    """Most specific Article 5(1)(x) citation present, else 'Article 5'."""
    for citation in triggered_articles or []:
        if isinstance(citation, str):
            m = _ARTICLE_5_PARA_RE.search(citation)
            if m:
                return m.group(0)
    return "Article 5"


# -- Rule helpers ----------------------------------------------------------
def _rule(
    name: str,
    priority: int,
    action: str,
    conditions: list[dict[str, Any]],
    description: str,
    deny_message: str | None = None,
) -> dict[str, Any]:
    """Build a single Lobster Trap rule dict in the real-schema shape.

    The Go loader requires `name` non-empty, `action` in the valid set, and
    at least one condition. Higher `priority` = evaluated first (firewall
    style, opposite of the the initial design assumption).
    """
    rule: dict[str, Any] = {
        "name": name,
        "description": description,
        "priority": priority,
        "action": action,
        "conditions": conditions,
    }
    if deny_message:
        rule["deny_message"] = deny_message
    return rule


def _cond(field: str, match_type: str, value: Any) -> dict[str, Any]:
    """Build a single match condition. Match types come from the Go loader's
    MatchType enum (boolean, threshold, exact, contains, regex, ...)."""
    return {"field": field, "match_type": match_type, "value": value}


# Always-true catch-all condition: token_count >= 0 matches every prompt
# because the inspector only emits non-negative token counts.
def _catch_all() -> dict[str, Any]:
    return _cond("token_count", "threshold", 0)


# -- Tier skeletons --------------------------------------------------------
def _prohibited_skeleton(
    triggered_articles: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """One DENY rule that catches every request. Default action is also DENY
    so even malformed traffic gets blocked at the proxy."""
    article = _article_5_citation(triggered_articles)
    ingress = [_rule(
        name="prohibited_practice_block",
        priority=1000,
        action="DENY",
        conditions=[_catch_all()],
        description=(
            f"EU AI Act {article} prohibits this practice; all traffic "
            "blocked at the Lobster Trap proxy."
        ),
        deny_message=(
            f"[ComplyForge] Blocked under EU AI Act {article} prohibited "
            "practice. Discontinue deployment."
        ),
    )]
    return ingress, []


def _high_risk_skeleton() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Five rules total: three ingress + two egress.

    Mapping vs. the design intent:
      ingress:
        prompt_injection_block      (Article 15 cybersecurity)
        decision_without_oversight  (Article 14 human oversight)
        rate_limit_unusual_surges   (Article 15 robustness)
      egress:
        pii_egress_human_review     (Article 10 data governance)
        comprehensive_logging       (Article 12 record-keeping)
    """
    ingress = [
        _rule(
            name="prompt_injection_block",
            priority=100,
            action="DENY",
            conditions=[_cond("contains_injection_patterns", "boolean", True)],
            description=(
                "Prompt-injection signature detected; request blocked under "
                "Article 15 cybersecurity controls."
            ),
            deny_message=(
                "[ComplyForge] Blocked: prompt-injection signature "
                "(Article 15)."
            ),
        ),
        _rule(
            name="decision_without_oversight_human_review",
            priority=80,
            action="HUMAN_REVIEW",
            conditions=[_cond("contains_role_impersonation", "boolean", True)],
            description=(
                "Decisions affecting natural persons require Article 14 "
                "human oversight prior to completion."
            ),
        ),
        _rule(
            name="rate_limit_unusual_surges",
            priority=50,
            action="RATE_LIMIT",
            conditions=[_cond("token_count", "threshold", 1)],
            description=(
                "Unusual traffic surges throttled to support Article 15 "
                "robustness obligations."
            ),
        ),
    ]
    egress = [
        _rule(
            name="pii_egress_human_review",
            priority=90,
            action="HUMAN_REVIEW",
            conditions=[_cond("contains_pii", "boolean", True)],
            description=(
                "PII detected in agent egress; Article 10 data governance "
                "requires human review before release."
            ),
        ),
        _rule(
            name="comprehensive_logging",
            priority=10,
            action="LOG",
            conditions=[_cond("token_count", "threshold", 0)],
            description=(
                "All requests and responses recorded to satisfy Article 12 "
                "record-keeping and Article 72 post-market monitoring."
            ),
        ),
    ]
    return ingress, egress


def _limited_risk_skeleton() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Two egress rules: AI-disclosure injection + deepfake logging."""
    egress = [
        _rule(
            name="disclose_ai_interaction",
            priority=70,
            action="MODIFY",
            conditions=[_cond("token_count", "threshold", 1)],
            description=(
                "Inject AI-disclosure preamble into outbound responses per "
                "EU AI Act Article 50 transparency obligations."
            ),
        ),
        _rule(
            name="deepfake_generation_log",
            priority=40,
            action="LOG",
            conditions=[_cond("intent_category", "exact", "communication")],
            description=(
                "Synthetic media output logged for downstream Article 50 "
                "deepfake-labelling review."
            ),
        ),
    ]
    return [], egress


def _minimal_risk_skeleton() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Single LOG-everything rule on ingress."""
    ingress = [_rule(
        name="log_everything",
        priority=10,
        action="LOG",
        conditions=[_catch_all()],
        description=(
            "Minimal-risk visibility: all traffic logged voluntarily under "
            "Article 95 codes of conduct, ready for re-classification if "
            "scope changes."
        ),
    )]
    return ingress, []


_TIER_PURPOSES: dict[RiskTier, str] = {
    RiskTier.PROHIBITED:
        "Block all traffic to a prohibited-practice agent under EU AI Act Article 5.",
    RiskTier.HIGH_RISK:
        "Enforce high-risk obligations: PII egress review, human oversight, "
        "injection blocking, comprehensive logging, and rate limiting.",
    RiskTier.LIMITED_RISK:
        "Apply EU AI Act Article 50 transparency: AI-disclosure injection "
        "and synthetic-media logging.",
    RiskTier.MINIMAL_RISK:
        "Voluntary visibility logging for a minimal-risk agent (Article 95).",
}


_TIER_DEFAULT_ACTION: dict[RiskTier, str] = {
    RiskTier.PROHIBITED: "DENY",
    RiskTier.HIGH_RISK: "ALLOW",
    RiskTier.LIMITED_RISK: "ALLOW",
    RiskTier.MINIMAL_RISK: "ALLOW",
}


REASON_PROMPT_TEMPLATE = """You are filling in human-readable `description` strings for a Veea Lobster Trap policy generated for an enterprise AI agent under Regulation (EU) 2024/1689 (the "EU AI Act").

AGENT
  name: {agent_name}
  purpose: {agent_purpose}
  domain: {agent_domain}

CLASSIFICATION
  tier: {tier}
  triggered_articles: {triggered_articles}
  rationale: {rationale}

RULES TO FILL (do NOT alter rule names, actions, conditions, or priorities — only produce the description text):
{rule_list}

INSTRUCTIONS
  * For every rule name above, return one short description sentence (<= 200 characters).
  * Reference at least one specific EU AI Act Article number per description. Prefer Articles drawn from triggered_articles when relevant; otherwise use the article hinted by the rule's purpose.
  * Output JSON only, matching the schema {{"reasons": [{{"id": "<rule_name>", "reason": "<description>"}}]}}.
  * Do not invent new rule names and do not change the action vocabulary.
"""


_SKELETON_BY_TIER = {
    RiskTier.HIGH_RISK: lambda c: _high_risk_skeleton(),
    RiskTier.LIMITED_RISK: lambda c: _limited_risk_skeleton(),
    RiskTier.MINIMAL_RISK: lambda c: _minimal_risk_skeleton(),
    RiskTier.PROHIBITED: lambda c: _prohibited_skeleton(c.triggered_articles or []),
}


# -- Agent -----------------------------------------------------------------
class PolicyAgent:
    """Single-call policy generator producing Lobster Trap YAML."""

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
    ) -> LobsterTrapPolicy:
        ingress_rules, egress_rules = _SKELETON_BY_TIER[classification.tier](classification)
        all_rules = ingress_rules + egress_rules
        self._validate_actions(all_rules)

        reasons = await self._fill_reasons(agent, classification, all_rules)
        for rule in all_rules:
            override = reasons.get(rule["name"])
            if override and override.strip():
                rule["description"] = override.strip()

        slug = self._slug(agent.name)
        policy_name = f"complyforge-{slug}"
        document: dict[str, Any] = {
            "version": "1.0",
            "policy_name": policy_name,
            "default_action": _TIER_DEFAULT_ACTION[classification.tier],
        }
        if ingress_rules:
            document["ingress_rules"] = ingress_rules
        if egress_rules:
            document["egress_rules"] = egress_rules

        yaml_str = yaml.safe_dump(
            document,
            sort_keys=False, default_flow_style=False, indent=2, allow_unicode=True,
        )
        return LobsterTrapPolicy(
            name=policy_name,
            yaml=yaml_str,
            purpose=_TIER_PURPOSES[classification.tier],
            rules_count=len(all_rules),
        )

    @staticmethod
    def _validate_actions(rules: list[dict[str, Any]]) -> None:
        for rule in rules:
            action = rule.get("action")
            if action not in VALID_ACTIONS:
                raise ValueError(
                    f"PolicyAgent produced invented Lobster Trap action "
                    f"{action!r}; allowed: {sorted(VALID_ACTIONS)}"
                )

    async def _fill_reasons(
        self,
        agent: AgentDescriptor,
        classification: ClassificationResult,
        rules: list[dict[str, Any]],
    ) -> dict[str, str]:
        rule_list = "\n".join(
            f"  - name={r['name']} action={r['action']} "
            f"priority={r['priority']} fallback_description={r['description']!r}"
            for r in rules
        )
        prompt = REASON_PROMPT_TEMPLATE.format(
            agent_name=agent.name,
            agent_purpose=agent.purpose,
            agent_domain=agent.domain,
            tier=classification.tier.value,
            triggered_articles=classification.triggered_articles or [],
            rationale=classification.rationale or "",
            rule_list=rule_list,
        )
        try:
            payload = await self.gemini.generate_structured(prompt, _ReasonMap)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "PolicyAgent: Gemini description-fill failed (%s); using "
                "fallback descriptions.",
                exc,
            )
            return {}
        return {item.id: item.reason for item in (payload.reasons or [])}

    @staticmethod
    def _slug(name: str) -> str:
        slug = (name or "").lower().replace(" ", "-").strip("-")
        return slug or "agent"


__all__ = ["PolicyAgent", "VALID_ACTIONS", "REASON_PROMPT_TEMPLATE"]
