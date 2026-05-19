# ComplyForge

**Autonomous EU AI Act Compliance Agent for Enterprise AI Systems**

> 75 days to August 2, 2026. €35M fines. Zero inventory at most enterprises. ComplyForge is an autonomous agent that **reasons** about your AI, **plans** a compliance pipeline, and **executes** it in 60 seconds — leaving a regulator-ready paper trail and an enforced runtime policy behind.

Built for the **lablab.ai AI Agent Olympics @ Milan AI Week 2026 Hackathon**.

## The Problem

On **August 2, 2026**, the EU AI Act's high-risk system rules become binding. Penalties reach **€35M or 7% of global revenue**. Recent surveys show **50%+ of enterprises have no AI inventory**, no Article 11 technical file, and no Fundamental Rights Impact Assessment (FRIA) on record. Compliance teams have 75 days to a deadline they cannot meet manually.

## The Autonomous Agent

ComplyForge is an autonomous compliance agent. Provide an `AgentDescriptor` for any enterprise AI system and ComplyForge will:

1. **Reason** — Classify the system against the four EU AI Act risk tiers (Prohibited / High-Risk / Limited / Minimal), citing the exact Article 5, Annex III, or Article 50 anchor. Drops hallucinated citations against a real taxonomy whitelist. Applies the precautionary principle when confidence is low.
2. **Plan** — The Orchestrator sequences a 12-step pipeline: gated classification first, then concurrent document and policy generation, then PDF render. Sub-agents internally fan out further (DocAgent runs 10 concurrent Gemini calls per Article 11 file).
3. **Execute** — Generates a regulator-ready Article 11 technical file (9 sections per Annex IV) + Article 27 FRIA + datasheet as a 13-page PDF. Auto-generates a Veea Lobster Trap YAML policy that enforces Article 14 oversight, Article 15 injection blocks, Article 12 logging, and Article 10 PII gates.
4. **Audit** — Every event lands in a JSONL audit log with the triggered rule, action, request snippet, and metadata — regulator-ready.

## Architecture — Agentic Workflow

```
                  ┌──────────────────────────────────┐
                  │       Enterprise AI agent        │
                  └────────────────┬─────────────────┘
                                   │ (proxied)
                                   ▼
                  ┌──────────────────────────────────┐
                  │       Veea Lobster Trap          │ ◄── runtime enforcement
                  └────────────────┬─────────────────┘
                                   │
                                   ▼
              ┌──────────────────────────────────────────┐
              │   ComplyForge Orchestrator (planner)     │
              ├──────────────────────────────────────────┤
              │  1. ClassifierAgent   → risk tier        │
              │  2. DocAgent          → Article 11 + FRIA│  (concurrent)
              │  3. PolicyAgent       → Lobster Trap YAML│  (concurrent)
              │  4. PDFGenerator      → regulator PDF    │
              └────────────────┬─────────────────────────┘
                               │
                               ▼
              ┌──────────────────────────────────────────┐
              │  Compliance Dashboard (React + Tailwind) │
              │  Inventory · Heatmap · Docs · Audit Log  │
              └──────────────────────────────────────────┘
```

**One orchestrator + three specialised sub-agents.** Architecture chosen against the published research showing structured small-team multi-agent designs outperform 5-7 agent meshes by roughly 17× on multi-step error rate.

## Hackathon Theme Fit

- **Agentic Workflows** — Orchestrator plans, sequences, and concurrently executes a 12-step pipeline.
- **Intelligent Reasoning** — Classifier reasons about a system's purpose, validates citations against the real taxonomy, applies precautionary promotion under uncertainty.
- **Enterprise Utility** — Solves the €35M EU AI Act compliance friction with regulator-ready outputs.
- **Multimodal Output** — Emits three artefact modalities (PDF for regulators, YAML for the security proxy, JSONL for observability).

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

- **94 unit tests + 7 endpoint tests passing** — `cd backend; pytest tests/ -v -m "not e2e"`
- **1 opt-in end-to-end integration test** — `pytest tests/ -v -m e2e` (requires live services)
- Concurrency proof — 10 mocked Gemini calls finish in 0.11s vs ~1.0s sequential.

## Demo Materials

- `demo/pitch_deck.md` — 5-slide Sequoia-format deck.
- `demo/script.md` — 2:30 video script with timestamps.
- `demo/attack_scenarios.md` — 8 rogue prompts mapped to the policy enforcement that catches them.
- `demo/judge_qa.md` — anticipated questions with crisp answers.

## Repository Layout

```
complyforge/
├── backend/         FastAPI + Gemini orchestrator + 3 sub-agents
├── frontend/        React + Tailwind autonomous-agent dashboard
├── lobstertrap/     Veea Lobster Trap config + policies
├── demo/            Pitch deck, video script, attack scenarios
├── docs/            Architecture, EU AI Act mapping
└── scripts/         Preflight + seed scripts
```

## License

MIT — see [LICENSE](LICENSE).

---

Built solo by Avinash Kumar for the AI Agent Olympics @ Milan AI Week 2026 hackathon. Powered by Google Gemini and Veea Lobster Trap.
