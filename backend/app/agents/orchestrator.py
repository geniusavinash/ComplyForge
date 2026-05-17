"""ComplianceOrchestrator — pure conductor for the three sub-agents.

Per BUILD_BIBLE Section 0 / Phase 5:
  * Step 1: ClassifierAgent.classify(agent)         (sequential)
  * Step 2 + 3: DocAgent.generate + PolicyAgent.generate run IN PARALLEL
                via asyncio.gather (the only orchestrator-level concurrency).
  * Step 4: PDFGenerator.render_technical_file -> generated_pdfs/<slug>.pdf
  * Step 5: assemble + return a ComplianceReport.

The orchestrator does NOT import or instantiate GeminiClient. Every Gemini
call lives inside the sub-agents. Architecture stays at 1 orchestrator + 3
sub-agents — no expansion.

Streaming: `analyze_stream` yields the same step events emitted by `analyze`
through an `asyncio.Queue`, ending with a `{"step": "done", ...}` event whose
payload is the JSON-mode dump of the final ComplianceReport.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any, AsyncIterator

from app.agents.classifier import ClassifierAgent
from app.agents.doc_generator import DocAgent
from app.agents.policy_generator import PolicyAgent
from app.schemas import (
    AgentDescriptor,
    ClassificationResult,
    ComplianceReport,
    LobsterTrapPolicy,
    TechnicalFile,
)
from app.services.pdf_generator import PDFGenerator


_PDF_OUTPUT_DIR = "generated_pdfs"


def slug(name: str) -> str:
    """Lowercase, replace non-alphanumeric runs with single hyphens, strip ends."""
    lowered = (name or "").lower()
    hyphenated = re.sub(r"[^a-z0-9]+", "-", lowered)
    collapsed = re.sub(r"-+", "-", hyphenated)
    cleaned = collapsed.strip("-")
    return cleaned or "agent"


class ComplianceOrchestrator:
    """Conducts ClassifierAgent -> (DocAgent || PolicyAgent) -> PDFGenerator."""

    def __init__(
        self,
        classifier: ClassifierAgent | None = None,
        doc_agent: DocAgent | None = None,
        policy_agent: PolicyAgent | None = None,
        pdf_generator: PDFGenerator | None = None,
    ) -> None:
        self.classifier = classifier or ClassifierAgent()
        self.doc_agent = doc_agent or DocAgent()
        self.policy_agent = policy_agent or PolicyAgent()
        self.pdf_generator = pdf_generator or PDFGenerator()

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
        )
        await emit({
            "step": "done",
            "status": "completed",
            "payload": report.model_dump(mode="json"),
        })
        return report


__all__ = ["ComplianceOrchestrator", "slug"]
