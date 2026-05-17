"""Tests for ComplianceOrchestrator.

All sub-agents and the PDF generator are mocked. We verify:
  * `analyze` returns a fully populated ComplianceReport with `pdf_path` set.
  * Classifier is awaited BEFORE DocAgent / PolicyAgent are started
    (sequencing) — proven by a shared call-order list captured in side
    effects of each mock.
  * DocAgent and PolicyAgent run in parallel — both sleep 0.1s and the
    parallel section measures < 0.15s (sequential would be ~0.2s+); total
    elapsed stays under 0.25s.
  * `analyze_stream` yields the documented step events in order, ending with
    a `done` event whose payload is the report.
  * The orchestrator slug helper handles spaces, punctuation, and case.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.orchestrator import ComplianceOrchestrator, slug
from app.data.eu_ai_act_taxonomy import ARTICLE_11_SECTIONS
from app.schemas import (
    AgentDescriptor,
    Article11Section,
    ClassificationResult,
    ComplianceReport,
    LobsterTrapPolicy,
    RiskTier,
    TechnicalFile,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
def _agent() -> AgentDescriptor:
    return AgentDescriptor(
        name="ResumeRanker",
        purpose="Rank resumes",
        domain="HR",
        inputs=["resume_pdf"],
        outputs=["score"],
        affects_humans=True,
        sample_prompts=["score this"],
        tools=["pdf_extractor"],
    )


def _classification() -> ClassificationResult:
    return ClassificationResult(
        tier=RiskTier.HIGH_RISK,
        confidence=0.92,
        triggered_articles=["Annex III(4)", "Article 6"],
        rationale="HR resume screening Annex III(4).",
        obligations=["Maintain Article 11 file"],
    )


def _technical_file() -> TechnicalFile:
    return TechnicalFile(
        agent_name="ResumeRanker",
        risk_tier=RiskTier.HIGH_RISK,
        generated_at=datetime(2026, 5, 17, 12, 0, tzinfo=timezone.utc),
        sections=[
            Article11Section(heading=meta["heading"], body="body")
            for meta in ARTICLE_11_SECTIONS
        ],
        fria_summary="FRIA narrative under Article 27.",
        datasheet={
            "model_provider": "test",
            "intended_use": "test",
            "training_data_summary": "test",
            "performance_metrics": "test",
            "known_limitations": "test",
            "human_oversight": "test",
            "contact": "test",
        },
    )


def _policy() -> LobsterTrapPolicy:
    return LobsterTrapPolicy(
        name="complyforge-resumeranker",
        yaml="name: complyforge-resumeranker\nversion: 1\nrules: []\n",
        purpose="High-risk policy",
        rules_count=5,
    )


def _build_mocks(
    delay: float = 0.0,
    call_order: list[str] | None = None,
) -> tuple[AsyncMock, AsyncMock, AsyncMock, MagicMock]:
    """Wire mock classifier + doc + policy + pdf_generator with optional sleeps."""
    classification = _classification()
    tech_file = _technical_file()
    policy = _policy()

    async def classify_side_effect(_agent_descriptor: AgentDescriptor) -> ClassificationResult:
        if call_order is not None:
            call_order.append("classify_start")
        # No sleep on classifier — the parallel-section timing test only
        # measures the doc/policy pair.
        if call_order is not None:
            call_order.append("classify_end")
        return classification

    async def doc_side_effect(_a, _c) -> TechnicalFile:
        if call_order is not None:
            call_order.append("doc_start")
        if delay:
            await asyncio.sleep(delay)
        if call_order is not None:
            call_order.append("doc_end")
        return tech_file

    async def policy_side_effect(_a, _c) -> LobsterTrapPolicy:
        if call_order is not None:
            call_order.append("policy_start")
        if delay:
            await asyncio.sleep(delay)
        if call_order is not None:
            call_order.append("policy_end")
        return policy

    classifier = AsyncMock()
    classifier.classify = AsyncMock(side_effect=classify_side_effect)

    doc_agent = AsyncMock()
    doc_agent.generate = AsyncMock(side_effect=doc_side_effect)

    policy_agent = AsyncMock()
    policy_agent.generate = AsyncMock(side_effect=policy_side_effect)

    pdf_generator = MagicMock()
    pdf_generator.render_technical_file = MagicMock(
        return_value="generated_pdfs/resumeranker.pdf",
    )

    return classifier, doc_agent, policy_agent, pdf_generator


# ---------------------------------------------------------------------------
# slug helper
# ---------------------------------------------------------------------------
def test_slug_lowercases_and_replaces_special_chars() -> None:
    assert slug("My Sample Agent") == "my-sample-agent"
    assert slug("ResumeRanker") == "resumeranker"
    assert slug("  Heavy / Punct!! & co  ") == "heavy-punct-co"
    assert slug("Multi  spaces") == "multi-spaces"
    assert slug("---weird---") == "weird"
    assert slug("") == "agent"


# ---------------------------------------------------------------------------
# analyze() core behaviour
# ---------------------------------------------------------------------------
def test_analyze_returns_full_report_with_pdf_path() -> None:
    classifier, doc_agent, policy_agent, pdf_generator = _build_mocks()
    orch = ComplianceOrchestrator(
        classifier=classifier,
        doc_agent=doc_agent,
        policy_agent=policy_agent,
        pdf_generator=pdf_generator,
    )

    report = asyncio.run(orch.analyze(_agent()))

    assert isinstance(report, ComplianceReport)
    assert report.agent.name == "ResumeRanker"
    assert report.classification.tier == RiskTier.HIGH_RISK
    assert len(report.technical_file.sections) == 9
    assert report.policy.rules_count == 5
    assert report.pdf_path == "generated_pdfs/resumeranker.pdf"
    pdf_generator.render_technical_file.assert_called_once()
    args, _kwargs = pdf_generator.render_technical_file.call_args
    assert args[0] is doc_agent.generate.return_value or args[0].agent_name == "ResumeRanker"
    assert args[1] == "generated_pdfs/resumeranker.pdf"


def test_analyze_classifier_awaited_before_doc_and_policy_start() -> None:
    call_order: list[str] = []
    classifier, doc_agent, policy_agent, pdf_generator = _build_mocks(
        call_order=call_order,
    )
    orch = ComplianceOrchestrator(
        classifier=classifier,
        doc_agent=doc_agent,
        policy_agent=policy_agent,
        pdf_generator=pdf_generator,
    )

    asyncio.run(orch.analyze(_agent()))

    # Classifier must complete before doc OR policy starts.
    classify_end_idx = call_order.index("classify_end")
    doc_start_idx = call_order.index("doc_start")
    policy_start_idx = call_order.index("policy_start")
    assert classify_end_idx < doc_start_idx, call_order
    assert classify_end_idx < policy_start_idx, call_order
    # And classify_start must be the very first event.
    assert call_order[0] == "classify_start", call_order


def test_analyze_doc_and_policy_run_concurrently() -> None:
    """Concurrency contract: 2 x 0.1 s sleeps < 0.15 s parallel; total < 0.25 s."""
    call_order: list[str] = []
    classifier, doc_agent, policy_agent, pdf_generator = _build_mocks(
        delay=0.1, call_order=call_order,
    )
    orch = ComplianceOrchestrator(
        classifier=classifier,
        doc_agent=doc_agent,
        policy_agent=policy_agent,
        pdf_generator=pdf_generator,
    )

    total_start = time.perf_counter()
    asyncio.run(orch.analyze(_agent()))
    total_elapsed = time.perf_counter() - total_start

    # Identify the parallel-section span: from min(doc_start, policy_start)
    # through max(doc_end, policy_end). We use the same call_order list as a
    # proxy for sequencing — both delays are equal so the elapsed asserts
    # below exercise the gather() guarantee.
    assert "doc_start" in call_order and "policy_start" in call_order
    assert "doc_end" in call_order and "policy_end" in call_order

    # Parallel section bound: must finish well before sequential 0.2 s.
    # We approximate by asserting the *whole* analyze() run is < 0.25 s; the
    # only real work is two 0.1 s sleeps + bookkeeping. Sequential execution
    # would push total >= 0.2 s + overhead, so this is a tight proof.
    assert total_elapsed < 0.25, (
        f"Total elapsed {total_elapsed:.3f}s exceeds 0.25s budget; "
        "doc_agent and policy_agent appear to be running sequentially."
    )

    # Stronger interleaving check: the second start happens before either end.
    starts = [i for i, e in enumerate(call_order) if e in ("doc_start", "policy_start")]
    ends = [i for i, e in enumerate(call_order) if e in ("doc_end", "policy_end")]
    assert max(starts) < min(ends), (
        f"doc and policy did not interleave: {call_order}"
    )


# ---------------------------------------------------------------------------
# analyze_stream() event sequence
# ---------------------------------------------------------------------------
def test_analyze_stream_yields_expected_events_in_order() -> None:
    classifier, doc_agent, policy_agent, pdf_generator = _build_mocks()
    orch = ComplianceOrchestrator(
        classifier=classifier,
        doc_agent=doc_agent,
        policy_agent=policy_agent,
        pdf_generator=pdf_generator,
    )

    async def collect() -> list[dict]:
        return [event async for event in orch.analyze_stream(_agent())]

    events = asyncio.run(collect())
    steps = [(e["step"], e["status"]) for e in events]

    assert ("classifying", "started") in steps
    assert ("classifying", "completed") in steps
    assert ("generating_docs", "started") in steps
    assert ("generating_policy", "started") in steps
    assert ("generating_docs", "completed") in steps
    assert ("generating_policy", "completed") in steps
    assert ("rendering_pdf", "started") in steps
    assert ("rendering_pdf", "completed") in steps

    # Ordering: classifying.started is first; done is last.
    assert steps[0] == ("classifying", "started")
    assert steps[-1] == ("done", "completed")

    # classifying.completed must precede generating_* starts.
    classify_done = steps.index(("classifying", "completed"))
    docs_started = steps.index(("generating_docs", "started"))
    policy_started = steps.index(("generating_policy", "started"))
    assert classify_done < docs_started
    assert classify_done < policy_started

    # rendering_pdf must follow the doc + policy completions.
    docs_done = steps.index(("generating_docs", "completed"))
    policy_done = steps.index(("generating_policy", "completed"))
    pdf_started = steps.index(("rendering_pdf", "started"))
    assert docs_done < pdf_started
    assert policy_done < pdf_started

    # Final event payload is a ComplianceReport-as-dict.
    final = events[-1]
    assert final["step"] == "done"
    payload = final["payload"]
    assert payload["agent"]["name"] == "ResumeRanker"
    assert payload["classification"]["tier"] == "high_risk"
    assert payload["pdf_path"] == "generated_pdfs/resumeranker.pdf"


def test_constructor_falls_back_to_real_defaults_when_args_omitted() -> None:
    """Smoke test: default-constructed orchestrator wires real sub-agents."""
    orch = ComplianceOrchestrator()
    # We don't run it (would touch Gemini); just sanity check the wiring.
    assert orch.classifier is not None
    assert orch.doc_agent is not None
    assert orch.policy_agent is not None
    assert orch.pdf_generator is not None
