# ComplyForge

**Autonomous EU AI Act Compliance Agent for Enterprise AI Systems**

> 75 days to August 2, 2026. €35M fines. Zero inventory at most enterprises. ComplyForge is an autonomous agent that **reasons** about your AI, **plans** a compliance pipeline, and **executes** it in 60 seconds — leaving a regulator-ready paper trail and an enforced runtime policy behind.

Built for the **lablab.ai AI Agent Olympics @ Milan AI Week 2026 Hackathon**.

## The Problem

On **August 2, 2026**, the EU AI Act's high-risk system rules become binding. Penalties reach **€35M or 7% of global revenue**. Recent surveys show **50%+ of enterprises have no AI inventory**, no Article 11 technical file, and no Fundamental Rights Impact Assessment (FRIA) on record. Compliance teams have 75 days to a deadline they cannot meet manually.

## The Autonomous Agent

ComplyForge is an autonomous compliance agent. Provide an `AgentDescriptor` — or upload a model card PDF / architecture diagram and Gemini Vision will extract one — and ComplyForge will:

1. **Plan** — A `PlannerAgent` emits an explicit four-step execution plan with rationale, expected durations, and a dependency graph. Visible in the dashboard before any execution starts.
2. **Reason** — `ClassifierAgent` classifies the system against the four EU AI Act risk tiers (Prohibited / High-Risk / Limited / Minimal), citing the exact Article 5, Annex III, or Article 50 anchor. Drops hallucinated citations against a real taxonomy whitelist. Applies the precautionary principle when confidence is low.
3. **Critique** — A `CriticAgent` runs an independent second-opinion review of the classification. Surfaces up to three concerns, proposes a confidence adjustment, and optionally suggests an alternative tier. Falls back gracefully if Gemini is unavailable.
4. **Execute** — `DocAgent` and `PolicyAgent` run in parallel. DocAgent emits a 13-page regulator-ready Article 11 + FRIA + datasheet PDF (10 concurrent Gemini calls). PolicyAgent emits a Veea Lobster Trap YAML enforcing Article 14 oversight, Article 15 injection blocks, Article 12 logging, and Article 10 PII gates.
5. **Audit** — Every runtime enforcement event lands in a JSONL audit log with the triggered rule, action, request snippet, and metadata — regulator-ready.

## Architecture — Agentic Workflow

```
       ┌────────────────────────────────────────────────────┐
       │  Input:  AgentDescriptor JSON   OR                 │
       │          model-card PDF / diagram PNG              │
       │          (Gemini Vision extracts the descriptor)   │
       └─────────────────────────┬──────────────────────────┘
                                 │
                                 ▼
          ┌────────────────────────────────────────────┐
          │   ComplianceOrchestrator (state owner)     │
          │                                            │
          │   1. PlannerAgent     → ExecutionPlan      │
          │   2. ClassifierAgent  → risk tier + cites  │
          │   3. CriticAgent      → second-opinion     │
          │   4a. DocAgent        ┐ in parallel        │
          │   4b. PolicyAgent     ┘                    │
          │   5. PDFGenerator     → regulator PDF      │
          └────────────────┬───────────────────────────┘
                           │
                           ▼
          ┌────────────────────────────────────────────┐
          │   Veea Lobster Trap (real-time proxy)      │
          │   enforces the generated YAML policy       │
          └────────────────┬───────────────────────────┘
                           │ JSONL audit events
                           ▼
          ┌────────────────────────────────────────────┐
          │   Dashboard (React + Tailwind)             │
          │   Plan preview · Reasoning trace · PDF     │
          │   Inventory · Heatmap · Live audit log     │
          └────────────────────────────────────────────┘
```

**One orchestrator owns all state; five specialised sub-agents speak only to the orchestrator, never to each other.** The Planner and Critic add reasoning depth without introducing inter-agent chains — the dependency graph stays a fan-in / fan-out, not a multi-hop chain. Research (Tran & Kiela 2024) shows error compounding kicks in when agents chain decisions sequentially without a coordinator; ComplyForge avoids that by routing every decision through the Orchestrator's shared classification context.

## Hackathon Theme Fit

- **Agentic Workflows** — PlannerAgent emits an explicit four-step plan with dependency graph; Orchestrator executes that plan with parallelism where the graph allows it.
- **Intelligent Reasoning** — ClassifierAgent reasons about a system's purpose against the real EU AI Act taxonomy; CriticAgent runs an independent second-opinion review and surfaces concerns with a confidence delta. Hallucinated citations are silently dropped.
- **Enterprise Utility** — Solves the €35M EU AI Act compliance friction with regulator-ready outputs in 60 seconds.
- **Multimodal Intelligence** — Accepts JSON, image (PNG/JPEG), or PDF input through `POST /api/extract-descriptor` (Gemini Vision); emits three output modalities (PDF for regulators, YAML for the security proxy, JSONL for observability).

## Sponsor Tech

- [Google Gemini API](https://aistudio.google.com/) — structured output, risk classification, long-form regulatory writing.
- [Veea Lobster Trap](https://github.com/veeainc/lobstertrap) — open-source LLM security proxy, MIT-licensed. Real schema verified by reading `serve.go` and `handler.go`; PolicyAgent emits the live schema, not the doc placeholder.

## Honest Engineering

The Veea Lobster Trap binary has no hot-reload mechanism (verified in upstream source). Rather than fake a reload, the deploy endpoint returns `manual_restart_required` and the dashboard surfaces a banner with restart instructions. Real engineering over hackathon theatre.

## Quick Start

```powershell
# Backend
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # paste your GEMINI_API_KEY
uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev

# Lobster Trap (new terminal)
cd lobstertrap
.\setup.ps1
```

Visit http://localhost:5173 — pick a sample agent (ResumeRanker, EmotionPulse, CreditDecider, SupportBot, RecipeBuddy) and watch the autonomous pipeline run live.

## Tests

- **116 passing tests** — `cd backend; pytest tests/ -v -m "not e2e"`
  - Breakdown: classifier 8, doc_generator 10, gemini_client 8, orchestrator 11, pdf_generator 7, planner 6, critic 6, policy_generator 14, sample_data 11, taxonomy 12, api 23.
- **1 opt-in end-to-end integration test** — `pytest tests/ -v -m e2e` (requires live services).
- Concurrency proof — 10 mocked Gemini calls finish in 0.11s vs ~1.0s sequential.
- Backwards-compatible orchestrator: default constructor with no Planner/Critic injection keeps the v0.2.0 SSE event sequence so the original test suite stays green.

## Demo Materials

- `demo/pitch_deck.md` — 5-slide Sequoia-format deck.
- `demo/script.md` — 2:30 video script with timestamps.
- `demo/attack_scenarios.md` — 8 rogue prompts mapped to the policy enforcement that catches them.
- `demo/judge_qa.md` — anticipated questions with crisp answers.

## Repository Layout

```
complyforge/
├── backend/
│   ├── main.py                          FastAPI app (v0.3.0)
│   ├── app/
│   │   ├── agents/
│   │   │   ├── orchestrator.py          state owner; emits SSE pipeline
│   │   │   ├── planner.py               PlannerAgent → ExecutionPlan
│   │   │   ├── classifier.py            ClassifierAgent → risk tier
│   │   │   ├── critic.py                CriticAgent → second-opinion
│   │   │   ├── doc_generator.py         DocAgent → Article 11 + FRIA
│   │   │   └── policy_generator.py      PolicyAgent → Lobster Trap YAML
│   │   ├── services/
│   │   │   ├── gemini_client.py         async wrapper + schema sanitizer
│   │   │   └── pdf_generator.py         ReportLab regulator PDF
│   │   ├── routers/
│   │   │   ├── analyze.py               /api/analyze + /api/analyze/stream
│   │   │   │                            + /api/extract-descriptor (multimodal)
│   │   │   │                            + /api/deploy-policy + /api/pdf
│   │   │   └── enforcement.py           /api/enforcement/event + /events
│   │   ├── data/                        EU AI Act taxonomy + sample agents
│   │   └── schemas.py                   Pydantic v2 models
│   └── tests/                           116 passing tests
├── frontend/
│   ├── src/
│   │   ├── views/                       Dashboard, NewAnalysis, Inventory,
│   │   │                                RiskHeatmap, DocsLibrary, EnforcementLog
│   │   ├── components/                  RiskBadge, ActionChip, StepProgress,
│   │   │                                PlanPreview, ReasoningTrace, Toaster
│   │   ├── api/client.js                axios + manual SSE parser + multimodal
│   │   └── store/inventory.js           zustand (deriveStats with critic + plan)
│   └── tailwind.config.js               locked brand palette
├── lobstertrap/                         Veea Lobster Trap configs + setup
├── demo/                                Pitch deck PDF, cover image, video
│                                        script, attack scenarios, judge Q&A
├── docs/                                Architecture, EU AI Act mapping
├── scripts/                             Preflight, seed, PDF/cover builders
└── SUBMISSION_PACKAGE.md                lablab.ai copy-paste content
```

## License

MIT — see [LICENSE](LICENSE).

---

Built solo by Avinash Kumar for the AI Agent Olympics @ Milan AI Week 2026 hackathon. Powered by Google Gemini and Veea Lobster Trap.
