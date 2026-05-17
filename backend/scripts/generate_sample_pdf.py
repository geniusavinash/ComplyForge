"""Generate a realistic HIGH_RISK sample PDF for manual inspection.

Run from c:\\Users\\avina\\Pictures\\hackathon\\backend with the venv active:
    python scripts/generate_sample_pdf.py
Outputs:
    backend/sample_outputs/sample_high_risk.pdf
Reports file size and page count (via /Type /Page marker count) on stdout.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

# Allow `python scripts/generate_sample_pdf.py` from the backend dir.
_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.dirname(_HERE)
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from app.schemas import Article11Section, RiskTier, TechnicalFile  # noqa: E402
from app.services.pdf_generator import PDFGenerator  # noqa: E402


SECTION_BODIES: list[tuple[str, str]] = [
    (
        "1. General description of the AI system",
        "ResumeRanker is an enterprise hiring agent that ranks inbound resumes for "
        "shortlisting by recruiters in the HR domain. The provider is the deploying "
        "company; the system version evaluated here is v0.1. ResumeRanker ingests "
        "resume PDFs and a job description and returns a numerical fit score plus a "
        "shortlist recommendation, in accordance with Article 11 and Annex IV.\n\n"
        "Categories of natural persons affected are job applicants for advertised "
        "roles. The system is intended to be used by trained HR staff and operates "
        "as a decision-support tool, not as a fully automated hiring decision, "
        "consistent with Article 14 human oversight obligations."
    ),
    (
        "2. Detailed description of the elements and the development process",
        "ResumeRanker is built on top of a general-purpose large language model "
        "wrapped by a retrieval pipeline that compares structured resume features "
        "against the job description. Training data for the underlying LLM is "
        "managed by its provider; ResumeRanker itself is not fine-tuned on candidate "
        "data, in line with Article 10 data governance.\n\n"
        "Validation procedures include subgroup performance evaluation across "
        "protected categories, with documented test sets and acceptance thresholds. "
        "Human oversight controls are implemented as recruiter approval gates "
        "before any candidate communication is dispatched."
    ),
    (
        "3. Information on monitoring, functioning, and control",
        "Operational monitoring captures decision distributions per role and per "
        "applicant cohort, reviewed weekly by HR analytics. Recruiters retain the "
        "ability to override scores, and any score below a confidence threshold is "
        "routed for manual review under Article 14.\n\n"
        "Known operational limits: the system is intended for English-language "
        "resumes within knowledge-worker roles. Use outside this scope is not "
        "validated and triggers a substantial-modification review under Article 6."
    ),
    (
        "4. Risk management system (Article 9)",
        "A risk management system has been established in accordance with Article 9. "
        "Identified risks include disparate impact on protected groups, over-reliance "
        "by recruiters, and propagation of historical bias from job descriptions.\n\n"
        "Risks are estimated through pre-deployment testing and continuous "
        "production monitoring. Mitigation measures include feature ablation tests, "
        "calibration of decision thresholds per cohort, and documented escalation "
        "paths for incidents."
    ),
    (
        "5. Changes made to the system through its lifecycle",
        "Changes to the system are tracked in a versioned changelog with sign-off "
        "from the provider's compliance officer. Substantial modifications—new "
        "input modalities, new candidate populations, or material changes to the "
        "scoring logic—trigger re-classification under Article 6 and a refreshed "
        "Article 11 technical file.\n\n"
        "Minor parameter adjustments are tracked but do not require re-classification."
    ),
    (
        "6. Performance metrics including foreseeable misuse",
        "Performance is measured via top-k recall against historical recruiter "
        "shortlists, with subgroup parity metrics computed across protected "
        "characteristics in accordance with Article 15. Cybersecurity testing "
        "covers prompt injection and resume-content exfiltration attempts.\n\n"
        "Foreseeable misuse includes recruiters treating the score as a final "
        "decision; this is mitigated by Article 14 oversight controls and "
        "in-product warnings."
    ),
    (
        "7. Harmonised standards and common specifications applied",
        "ISO/IEC 42001 (AI management system) and ISO/IEC 23894 (AI risk "
        "management) are applied as governing frameworks. ISO/IEC 25059 quality "
        "characteristics inform the performance specification. Where harmonised "
        "standards do not yet exist, alternative technical solutions are documented "
        "with rationale, in accordance with Article 40."
    ),
    (
        "8. EU declaration of conformity",
        "An EU declaration of conformity is drawn up in accordance with Article 47 "
        "and made available to national authorities on request. The declaration "
        "states that ResumeRanker meets the relevant requirements of Chapter III, "
        "Section 2 of the EU AI Act and identifies the provider, the system, and "
        "the conformity assessment route taken."
    ),
    (
        "9. Post-market monitoring plan (Article 72)",
        "A post-market monitoring system is operated under Article 72. Logged data "
        "from production is sampled monthly to recompute subgroup parity, reviewer "
        "override rate, and serious-incident indicators. Serious incidents are "
        "reported to the relevant market-surveillance authority under Article 73, "
        "with corrective actions tracked to closure."
    ),
]


FRIA_NARRATIVE = (
    "1. Description of the deployer's processes — ResumeRanker is used by HR "
    "recruiters during the screening stage of open requisitions. Each requisition "
    "is reviewed by a named recruiter who validates the shortlist before any "
    "candidate is contacted, in accordance with Article 27.\n\n"
    "2. Period and frequency of intended use — The system runs on every inbound "
    "application for participating roles, typically tens to hundreds of applications "
    "per requisition over a four-week posting window.\n\n"
    "3. Categories of natural persons and groups likely to be affected — Job "
    "applicants are the primary affected group. Particular attention is paid to "
    "applicants in protected categories under EU non-discrimination law.\n\n"
    "4. Specific risks of harm to fundamental rights — Risks include unfair "
    "exclusion through proxy features, opacity of decision rationale, and "
    "amplification of historical hiring biases. These are addressed through "
    "Article 10 data governance and Article 9 risk management measures.\n\n"
    "5. Human oversight measures — Article 14 oversight is implemented as a "
    "recruiter approval gate, mandatory review of low-confidence scores, and "
    "logging of all overrides for audit.\n\n"
    "6. Measures to be taken if risks materialise — Internal governance escalates "
    "incidents to the data protection officer and triggers a corrective action plan, "
    "with reporting to the relevant market-surveillance authority where required "
    "under Article 73."
)


def _build_high_risk_fixture() -> TechnicalFile:
    sections = [Article11Section(heading=h, body=b) for h, b in SECTION_BODIES]
    return TechnicalFile(
        agent_name="ResumeRanker (Acme Corp)",
        risk_tier=RiskTier.HIGH_RISK,
        generated_at=datetime.now(timezone.utc),
        sections=sections,
        fria_summary=FRIA_NARRATIVE,
        datasheet={
            "model_provider": "Acme Corp / Gemini 2.0 Flash backbone",
            "intended_use": (
                "Rank inbound resumes for shortlisting by HR recruiters in "
                "knowledge-worker roles."
            ),
            "training_data_summary": (
                "No fine-tuning on candidate data. Underlying LLM training data is "
                "managed by the model provider; resume features are processed in "
                "memory only, in accordance with Article 10 data governance."
            ),
            "performance_metrics": (
                "Top-k recall against historical recruiter shortlists, subgroup "
                "parity across protected characteristics, prompt-injection "
                "robustness rate; tracked under Article 72 post-market monitoring."
            ),
            "known_limitations": (
                "English-language resumes only; not validated outside knowledge-"
                "worker roles. Use outside this scope triggers re-classification "
                "under Article 6."
            ),
            "human_oversight": (
                "Article 14 measures: recruiter approval gate before candidate "
                "contact; mandatory review of low-confidence scores; full audit "
                "log of overrides."
            ),
            "contact": "compliance@acme.example",
        },
    )


def main() -> None:
    out_dir = os.path.join(_BACKEND, "sample_outputs")
    out_path = os.path.join(out_dir, "sample_high_risk.pdf")
    PDFGenerator().render_technical_file(_build_high_risk_fixture(), out_path)
    raw = open(out_path, "rb").read()
    page_markers = raw.count(b"/Type /Page\n") + raw.count(b"/Type /Page ")
    print(f"Wrote: {out_path}")
    print(f"Size:  {os.path.getsize(out_path)} bytes")
    print(f"Magic: {raw[:5]!r}")
    print(f"Pages: ~{page_markers} (counted via /Type /Page markers)")


if __name__ == "__main__":
    main()
