"""Print a sample HIGH_RISK Lobster Trap policy YAML to stdout.

Builds a realistic HIGH_RISK fixture (HR resume screener) and runs PolicyAgent
with a mocked Gemini client so this script never makes a live API call.

Run from c:\\Users\\avina\\Pictures\\hackathon\\backend after activating the venv:

    python scripts\\print_sample_policy.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock

# Make `app` importable when invoked from backend/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents.policy_generator import PolicyAgent, _ReasonItem, _ReasonMap
from app.schemas import AgentDescriptor, ClassificationResult, RiskTier


def _high_risk_fixture() -> tuple[AgentDescriptor, ClassificationResult]:
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
        triggered_articles=["Annex III(4)", "Article 6", "Article 14"],
        rationale=(
            "HR resume screening is Annex III(4) employment use, classified "
            "high-risk under Article 6 and subject to Article 14 human oversight."
        ),
        obligations=[
            "Maintain Article 11 technical file",
            "Implement Article 14 human oversight",
            "Conduct Article 27 FRIA",
        ],
    )
    return agent, classification


def _mock_gemini() -> AsyncMock:
    canned_reasons = {
        "pii_egress_human_review": (
            "PII detected on egress; Article 10 data governance and Article 14 "
            "oversight require recruiter review prior to release."
        ),
        "decision_without_oversight_human_review": (
            "Shortlisting decisions affecting candidates need Article 14 human "
            "oversight before being communicated externally."
        ),
        "prompt_injection_block": (
            "Injection attempt blocked under Article 15 cybersecurity controls; "
            "logged for Article 12 record-keeping."
        ),
        "comprehensive_logging": (
            "Full request/response logging satisfies Article 12 record-keeping "
            "and Article 72 post-market monitoring."
        ),
        "rate_limit_unusual_surges": (
            "Unusual ingress surges throttled to satisfy Article 15 robustness "
            "and Annex III(4) employment-use safeguards."
        ),
    }
    items = [_ReasonItem(id=k, reason=v) for k, v in canned_reasons.items()]
    mock = AsyncMock()
    mock.generate_structured = AsyncMock(return_value=_ReasonMap(reasons=items))
    return mock


async def _main() -> None:
    agent, classification = _high_risk_fixture()
    policy = await PolicyAgent(gemini=_mock_gemini()).generate(agent, classification)
    print(f"# policy.name      = {policy.name}")
    print(f"# policy.purpose   = {policy.purpose}")
    print(f"# policy.rules_count = {policy.rules_count}")
    print("# ---- yaml ----")
    print(policy.yaml)


if __name__ == "__main__":
    asyncio.run(_main())
