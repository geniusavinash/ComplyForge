"""Tests for PlannerAgent.

Gemini is fully mocked. We verify:
  * Plan has exactly 4 steps with the expected ids in the canonical order.
  * depends_on topology is correct (critique->classify, generate->critique,
    render->generate, classify has no deps).
  * Plan calls gemini exactly ONCE per plan().
  * Plan survives Gemini returning a malformed plan — post-processing fixes
    it deterministically while salvaging the model's rationale.
  * `rationale` is non-empty after post-processing (including the fallback
    path when Gemini hands back an empty rationale).
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from app.agents.planner import (
    EXPECTED_STEP_IDS,
    PIPELINE_NAME,
    PlannerAgent,
)
from app.schemas import AgentDescriptor, ExecutionPlan, ExecutionPlanStep
from app.services.gemini_client import GeminiClientError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
def _agent() -> AgentDescriptor:
    return AgentDescriptor(
        name="ResumeRanker",
        purpose="Rank candidate resumes for HR screening",
        domain="HR",
        inputs=["resume_pdf"],
        outputs=["score"],
        affects_humans=True,
        sample_prompts=["score this resume"],
        tools=["pdf_extractor"],
    )


def _good_plan() -> ExecutionPlan:
    """A well-formed Gemini response: should be returned verbatim."""
    return ExecutionPlan(
        pipeline=PIPELINE_NAME,
        rationale=(
            "HR domain agent — classify under EU AI Act Article 6 / Annex III(4); "
            "critique gates fan-out; generate runs 10 concurrent Gemini calls."
        ),
        steps=[
            ExecutionPlanStep(
                id="classify",
                description="ClassifierAgent vs taxonomy",
                expected_duration_seconds=2.5,
                depends_on=[],
            ),
            ExecutionPlanStep(
                id="critique",
                description="CriticAgent second opinion",
                expected_duration_seconds=2.0,
                depends_on=["classify"],
            ),
            ExecutionPlanStep(
                id="generate",
                description="DocAgent + PolicyAgent in parallel",
                expected_duration_seconds=8.0,
                depends_on=["critique"],
            ),
            ExecutionPlanStep(
                id="render",
                description="PDFGenerator emits PDF",
                expected_duration_seconds=1.0,
                depends_on=["generate"],
            ),
        ],
    )


def _malformed_plan() -> ExecutionPlan:
    """Wrong step count + wrong ids + broken topology — must be repaired."""
    return ExecutionPlan(
        pipeline="something_else",
        rationale="HR resume ranking implicates Annex III(4) under the EU AI Act.",
        steps=[
            ExecutionPlanStep(
                id="run_everything",
                description="do it all",
                expected_duration_seconds=5.0,
                depends_on=[],
            ),
            ExecutionPlanStep(
                id="classify",
                description="classify",
                expected_duration_seconds=1.0,
                depends_on=["render"],  # cycle!
            ),
        ],
    )


def _make_gemini(return_value: ExecutionPlan) -> AsyncMock:
    mock = AsyncMock()
    mock.generate_structured = AsyncMock(return_value=return_value)
    return mock


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_plan_has_exactly_four_steps_with_expected_ids() -> None:
    gemini = _make_gemini(_good_plan())
    planner = PlannerAgent(gemini=gemini)
    plan = asyncio.run(planner.plan(_agent()))

    assert plan.pipeline == PIPELINE_NAME
    assert len(plan.steps) == 4
    assert [s.id for s in plan.steps] == list(EXPECTED_STEP_IDS)


def test_plan_depends_on_topology_is_correct() -> None:
    gemini = _make_gemini(_good_plan())
    planner = PlannerAgent(gemini=gemini)
    plan = asyncio.run(planner.plan(_agent()))

    by_id = {s.id: s for s in plan.steps}
    assert by_id["classify"].depends_on == []
    assert by_id["critique"].depends_on == ["classify"]
    assert by_id["generate"].depends_on == ["critique"]
    assert by_id["render"].depends_on == ["generate"]


def test_plan_calls_gemini_exactly_once() -> None:
    gemini = _make_gemini(_good_plan())
    planner = PlannerAgent(gemini=gemini)
    asyncio.run(planner.plan(_agent()))

    assert gemini.generate_structured.await_count == 1


def test_plan_survives_malformed_gemini_response() -> None:
    gemini = _make_gemini(_malformed_plan())
    planner = PlannerAgent(gemini=gemini)
    plan = asyncio.run(planner.plan(_agent()))

    assert plan.pipeline == PIPELINE_NAME
    assert [s.id for s in plan.steps] == list(EXPECTED_STEP_IDS)
    # Topology fully repaired:
    by_id = {s.id: s for s in plan.steps}
    assert by_id["classify"].depends_on == []
    assert by_id["critique"].depends_on == ["classify"]
    assert by_id["generate"].depends_on == ["critique"]
    assert by_id["render"].depends_on == ["generate"]
    # Rationale salvaged from the malformed response.
    assert "Annex III" in plan.rationale or "EU AI Act" in plan.rationale


def test_plan_rationale_non_empty_after_post_processing() -> None:
    # Gemini returns a valid-shape plan but with an EMPTY rationale.
    empty_rationale = _good_plan().model_copy(update={"rationale": "   "})
    # The topology is still valid, so the plan is returned verbatim — but the
    # contract is that rationale survives post-processing as non-empty when
    # the plan needs fixing. Force the fix path by also breaking the pipeline.
    bad = empty_rationale.model_copy(update={"pipeline": "wrong"})
    gemini = _make_gemini(bad)
    planner = PlannerAgent(gemini=gemini)
    plan = asyncio.run(planner.plan(_agent()))

    assert plan.pipeline == PIPELINE_NAME
    assert plan.rationale.strip(), "rationale must be non-empty after fix"
    # Fallback rationale references the agent domain + EU AI Act.
    assert "HR" in plan.rationale
    assert "EU AI Act" in plan.rationale


def test_plan_falls_back_when_gemini_raises() -> None:
    gemini = AsyncMock()
    gemini.generate_structured = AsyncMock(
        side_effect=GeminiClientError("boom"),
    )
    planner = PlannerAgent(gemini=gemini)
    plan = asyncio.run(planner.plan(_agent()))

    # Still produces a canonical 4-step plan and a non-empty rationale.
    assert [s.id for s in plan.steps] == list(EXPECTED_STEP_IDS)
    assert plan.rationale.strip()
    assert gemini.generate_structured.await_count == 1
