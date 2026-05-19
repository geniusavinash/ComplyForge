"""ComplianceOrchestrator — pure conductor for the sub-agents.

Per BUILD_BIBLE Section 0 / Phase 5, with v0.3.0 upgrade for the AI Agent
Olympics tracks (Agentic Workflows + Intelligent Reasoning):

  * Step 0 (optional, v0.3.0): PlannerAgent.plan(agent) — commits to a DAG
                               up front. Emits {step: "planning", ...}.
  * Step 1: ClassifierAgent.classify(agent)              (sequential)
  * Step 1.5 (optional, v0.3.0): CriticAgent.review(agent, classification)
                                 — second-opinion gate. Emits
                                 {step: "critiquing", ...}.
  * Steps 2 + 3: DocAgent.generate + PolicyAgent.generate run IN PARALLEL
                 via asyncio.gather (the only orchestrator-level concurrency).
  * Step 4: PDFGenerator.render_technical_file -> generated_pdfs/<slug>.pdf
  * Step 5: assemble + return a ComplianceReport.

Backwards-compatibility contract:
  When planner is None and critic is None the orchestrator emits the EXACT
  same SSE event sequence as v0.2.x. The new "planning" and "critiquing"
  events ONLY fire when their respective agents are injected.

The orchestrator does NOT import or instantiate GeminiClient. Every Gemini
call lives inside the sub-agents.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, AsyncIterator

from app.agents.classifier import ClassifierAgent
from app.agents.critic import CriticAgent
from app.agents.doc_generator import DocAgent
from app.agents.planner import PlannerAgent
from app.agents.policy_generator import PolicyAgent
from app.schemas import (
    AgentDescriptor,
    ClassificationResult,
    ComplianceReport,
    CriticReview,
    ExecutionPlan,
    LobsterTrapPolicy,
    TechnicalFile,
)
from app.services.pdf_generator import PDFGenerator

logger = logging.getLogger(__name__)

_PDF_OUTPUT_DIR = "generated_pdfs"
_CRITIQUE_DOWNGRADE_THRESHOLD = -0.3
_CRITIQUE_NOTE_TEMPLATE = (
    " [CriticAgent flagged disagreement (delta={delta:+.2f}); "
    "concerns: {concerns}. Suggestion: {suggestion}]"
)


def slug(name: str) -> str:
    """Lowercase, replace non-alphanumeric runs with single hyphens, strip ends."""
    lowered = (name or "").lower()
    hyphenated = re.sub(r"[^a-z0-9]+", "-", lowered)
    collapsed = re.sub(r"-+", "-", hyphenated)
    cleaned = collapsed.strip("-")
    return cleaned or "agent"


def _apply_critique(
    classification: ClassificationResult,
    critique: CriticReview,
) -> ClassificationResult:
    """Append a critique note to rationale when critic disagrees strongly.

    Does NOT change tier — that is out of scope for v0.3.0.
    """
    if critique.agreed or critique.confidence_delta > _CRITIQUE_DOWNGRADE_THRESHOLD:
        return classification
    concerns_text = "; ".join(critique.concerns) if critique.concerns else "none stated"
    suggestion_text = critique.suggestion or "none"
    note = _CRITIQUE_NOTE_TEMPLATE.format(
        delta=critique.confidence_delta,
        concerns=concerns_text,
        suggestion=suggestion_text,
    )
    if note.strip() in classification.rationale:
        return classification
    return classification.model_copy(
        update={"rationale": classification.rationale.rstrip() + note},
    )


class ComplianceOrchestrator:
    """Conducts Planner -> Classifier -> Critic -> (Doc || Policy) -> PDF."""

    def __init__(
        self,
        classifier: ClassifierAgent | None = None,
        doc_agent: DocAgent | None = None,
        policy_agent: PolicyAgent | None = None,
        pdf_generator: PDFGenerator | None = None,
        planner: PlannerAgent | None = None,
        critic: CriticAgent | None = None,
    ) -> None:
        self.classifier = classifier or ClassifierAgent()
        self.doc_agent = doc_agent or DocAgent()
        self.policy_agent = policy_agent or PolicyAgent()
        self.pdf_generator = pdf_generator or PDFGenerator()
        # planner / critic are OPT-IN. Default None keeps the v0.2.x SSE
        # event sequence byte-for-byte identical for existing callers.
        self.planner = planner
        self.critic = critic

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def analyze(self, agent: AgentDescriptor) -> ComplianceReport:
        """Run the full pipeline and return a populated ComplianceReport."""
        return await self._run(agent, queue=None)

    async def analyze_stream(
        self, agent: AgentDescriptor,
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield orchestrator events; final event is `{"step": "done", ...}`."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        task = asyncio.create_task(self._run(agent, queue=queue))
        try:
            while True:
                event = await queue.get()
                yield event
                if event.get("step") == "done":
                    break
        finally:
            # Surface any exception raised inside _run.
            await task

    # ------------------------------------------------------------------
    # Internal pipeline
    # ------------------------------------------------------------------
    async def _run(
        self,
        agent: AgentDescriptor,
        queue: asyncio.Queue[dict[str, Any]] | None,
    ) -> ComplianceReport:
        async def emit(event: dict[str, Any]) -> None:
            if queue is not None:
                await queue.put(event)

        # Step 0 (optional) — planning
        plan: ExecutionPlan | None = None
        if self.planner is not None:
            plan = await self.planner.plan(agent)
            await emit({
                "step": "planning",
                "status": "completed",
                "payload": plan.model_dump(mode="json"),
            })

        # Step 1 — classify (sequential)
        await emit({"step": "classifying", "status": "started"})
        classification: ClassificationResult = await self.classifier.classify(agent)
        await emit({
            "step": "classifying",
            "status": "completed",
            "payload": {
                "tier": classification.tier.value,
                "confidence": classification.confidence,
            },
        })

        # Step 1.5 (optional) — critique
        critique: CriticReview | None = None
        if self.critic is not None:
            critique = await self.critic.review(agent, classification)
            await emit({
                "step": "critiquing",
                "status": "completed",
                "payload": critique.model_dump(mode="json"),
            })
            classification = _apply_critique(classification, critique)

        # Steps 2 + 3 — DocAgent and PolicyAgent run IN PARALLEL
        await emit({"step": "generating_docs", "status": "started"})
        await emit({"step": "generating_policy", "status": "started"})
        tech_file, policy = await asyncio.gather(
            self.doc_agent.generate(agent, classification),
            self.policy_agent.generate(agent, classification),
        )
        assert isinstance(tech_file, TechnicalFile)
        assert isinstance(policy, LobsterTrapPolicy)
        await emit({"step": "generating_docs", "status": "completed"})
        await emit({"step": "generating_policy", "status": "completed"})

        # Step 4 — PDF render (sync)
        await emit({"step": "rendering_pdf", "status": "started"})
        pdf_path = self.pdf_generator.render_technical_file(
            tech_file, f"{_PDF_OUTPUT_DIR}/{slug(agent.name)}.pdf",
        )
        await emit({
            "step": "rendering_pdf",
            "status": "completed",
            "payload": {"pdf_path": pdf_path},
        })

        # Step 5 — assemble report
        report = ComplianceReport(
            agent=agent,
            classification=classification,
            technical_file=tech_file,
            policy=policy,
            pdf_path=pdf_path,
            plan=plan,
            critique=critique,
        )
        await emit({
            "step": "done",
            "status": "completed",
            "payload": report.model_dump(mode="json"),
        })
        return report


__all__ = ["ComplianceOrchestrator", "slug"]
