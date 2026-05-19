"""PlannerAgent — produces a 4-step ExecutionPlan for the ComplyForge pipeline.

Why a planner agent (Agentic Workflows track):
  ComplyForge's pipeline is deterministic (classify -> critique -> generate ->
  render), but a planner makes the agent legible: it commits, up front, to the
  exact DAG it will execute, the rationale tied to the agent under review, and
  expected durations. This turns an opaque orchestration into an auditable
  plan-then-execute loop. The planner does ONE Gemini call per `plan()`.

Safety:
  The orchestrator must run a fixed pipeline regardless of what Gemini
  hallucinates, so post-processing rewrites the steps deterministically. Only
  the `rationale` string is salvaged verbatim — everything structural is
  pinned to the canonical 4-step DAG.
"""

from __future__ import annotations

import logging
from typing import Final

from app.schemas import AgentDescriptor, ExecutionPlan, ExecutionPlanStep
from app.services.gemini_client import GeminiClient, GeminiClientError, get_gemini

logger = logging.getLogger(__name__)


PIPELINE_NAME: Final[str] = "eu_ai_act_compliance"
EXPECTED_STEP_IDS: Final[tuple[str, ...]] = ("classify", "critique", "generate", "render")
_EXPECTED_DEPENDENCIES: Final[dict[str, list[str]]] = {
    "classify": [],
    "critique": ["classify"],
    "generate": ["critique"],
    "render": ["generate"],
}
_DEFAULT_DURATIONS: Final[dict[str, float]] = {
    "classify": 2.5,
    "critique": 2.0,
    "generate": 8.0,
    "render": 1.0,
}
_DEFAULT_DESCRIPTIONS: Final[dict[str, str]] = {
    "classify": (
        "ClassifierAgent maps the AgentDescriptor onto the EU AI Act risk "
        "taxonomy (Articles 5, 6, 50; Annex III(1)-(8)) and returns a "
        "ClassificationResult with tier, confidence, triggered articles, "
        "rationale, and operator obligations."
    ),
    "critique": (
        "CriticAgent provides an independent second-opinion review of the "
        "classifier's tier assignment, returning agreement, a confidence "
        "delta, up to three concerns, and an optional suggestion. Runs "
        "sequentially after classify to gate the fan-out."
    ),
    "generate": (
        "DocAgent (9 Article 11 sections + Article 27 FRIA, 10 concurrent "
        "Gemini calls via asyncio.gather) and PolicyAgent (Lobster Trap YAML) "
        "run in parallel. This is the only orchestrator-level fan-out."
    ),
    "render": (
        "PDFGenerator emits a regulator-ready PDF via ReportLab and writes "
        "the ComplianceReport JSON sidecar to generated_pdfs/."
    ),
}


PLANNER_PROMPT_TEMPLATE = """You are the ComplyForge orchestration PLANNER.
Your job is to commit, up front, to the exact pipeline ComplyForge will execute
for the AI agent described below, under Regulation (EU) 2024/1689 (the "EU AI Act").

The pipeline is FIXED at exactly 4 steps in this topology:

  Step 1 (id="classify")  — ClassifierAgent runs against the EU AI Act
        taxonomy (Articles 5, 6, 50; Annex III(1)-(8)) and returns a risk tier.
        depends_on: []
  Step 2 (id="critique")  — CriticAgent provides an independent second-opinion
        review of the classifier's output (agreement + confidence_delta +
        concerns + suggestion). depends_on: ["classify"]
  Step 3 (id="generate")  — DocAgent (9 Article 11 sections + FRIA via 10
        concurrent Gemini calls) AND PolicyAgent (Lobster Trap YAML) run in
        parallel. depends_on: ["critique"]
  Step 4 (id="render")    — PDFGenerator emits a regulator-ready PDF.
        depends_on: ["generate"]

OUTPUT (JSON only, matching the supplied ExecutionPlan schema)
  pipeline: MUST be "eu_ai_act_compliance"
  rationale: 3-5 sentences. MUST reference the agent's domain ({domain}) and
             the EU AI Act explicitly, and MUST justify the concurrency
             choice (10 parallel Gemini calls inside `generate`, sequential
             classify -> critique gate before fan-out).
  steps: EXACTLY 4 entries with ids "classify", "critique", "generate",
         "render" in that order, each with:
           description: 1-3 sentence explanation of the step
           expected_duration_seconds: realistic float (classify ~2.5, critique
                                     ~2.0, generate ~8.0, render ~1.0)
           depends_on: list of prior step ids (see topology above)

AGENT UNDER REVIEW
  name: {name}
  purpose: {purpose}
  domain: {domain}
  affects_humans: {affects_humans}
  inputs: {inputs}
  outputs: {outputs}
  tools: {tools}
"""


def _canonical_steps() -> list[ExecutionPlanStep]:
    """Build the canonical 4-step pipeline with default durations + dependencies."""
    return [
        ExecutionPlanStep(
            id=step_id,
            description=_DEFAULT_DESCRIPTIONS[step_id],
            expected_duration_seconds=_DEFAULT_DURATIONS[step_id],
            depends_on=list(_EXPECTED_DEPENDENCIES[step_id]),
        )
        for step_id in EXPECTED_STEP_IDS
    ]


def _topology_is_correct(steps: list[ExecutionPlanStep]) -> bool:
    """Return True iff steps match the expected 4-step DAG exactly."""
    if len(steps) != len(EXPECTED_STEP_IDS):
        return False
    if [s.id for s in steps] != list(EXPECTED_STEP_IDS):
        return False
    for s in steps:
        expected = _EXPECTED_DEPENDENCIES[s.id]
        if list(s.depends_on) != expected:
            return False
    return True


def _fix_plan(
    raw_plan: ExecutionPlan | None,
    fallback_rationale: str,
) -> ExecutionPlan:
    """Deterministically rebuild a canonical plan, salvaging only the rationale."""
    rationale = ""
    if raw_plan is not None and isinstance(raw_plan.rationale, str):
        rationale = raw_plan.rationale.strip()
    if not rationale:
        rationale = fallback_rationale
    return ExecutionPlan(
        pipeline=PIPELINE_NAME,
        rationale=rationale,
        steps=_canonical_steps(),
    )


def _fallback_rationale(agent: AgentDescriptor) -> str:
    return (
        f"Run the canonical ComplyForge EU AI Act pipeline against the "
        f"{agent.domain or 'unspecified-domain'} agent '{agent.name}'. "
        f"Classify against Articles 5, 6, 50 and Annex III, gate with an "
        f"independent CriticAgent review, then fan out to DocAgent (10 "
        f"concurrent Gemini calls for Article 11 + Article 27 FRIA) and "
        f"PolicyAgent in parallel before rendering a regulator-ready PDF."
    )


class PlannerAgent:
    """One async Gemini call -> ExecutionPlan, with deterministic post-fix."""

    def __init__(self, gemini: GeminiClient | None = None) -> None:
        self._gemini = gemini

    @property
    def gemini(self) -> GeminiClient:
        if self._gemini is None:
            self._gemini = get_gemini()
        return self._gemini

    async def plan(self, agent: AgentDescriptor) -> ExecutionPlan:
        prompt = self._build_prompt(agent)
        fallback = _fallback_rationale(agent)
        raw_plan: ExecutionPlan | None = None
        try:
            raw_plan = await self.gemini.generate_structured(prompt, ExecutionPlan)
        except GeminiClientError as exc:
            logger.warning("PlannerAgent Gemini call failed; using canonical plan: %s", exc)
        except Exception as exc:  # noqa: BLE001
            logger.warning("PlannerAgent unexpected error; using canonical plan: %s", exc)

        if raw_plan is None:
            return _fix_plan(None, fallback)

        if raw_plan.pipeline == PIPELINE_NAME and _topology_is_correct(raw_plan.steps):
            return raw_plan
        logger.info(
            "PlannerAgent fixing malformed plan (pipeline=%r, step_ids=%r)",
            raw_plan.pipeline,
            [s.id for s in raw_plan.steps],
        )
        return _fix_plan(raw_plan, fallback)

    @staticmethod
    def _build_prompt(agent: AgentDescriptor) -> str:
        return PLANNER_PROMPT_TEMPLATE.format(
            name=agent.name,
            purpose=agent.purpose,
            domain=agent.domain,
            affects_humans=agent.affects_humans,
            inputs=agent.inputs,
            outputs=agent.outputs,
            tools=agent.tools,
        )


__all__ = [
    "PlannerAgent",
    "PLANNER_PROMPT_TEMPLATE",
    "PIPELINE_NAME",
    "EXPECTED_STEP_IDS",
]
