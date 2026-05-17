# ComplyForge

**EU AI Act Article 11 Compliance Co-Pilot for Enterprise AI Agents**

> 77 days. €35M fines. Zero inventory. ComplyForge turns your AI chaos into regulator-ready compliance in 60 seconds.

Built for the **lablab.ai TechEx — Transforming Enterprise Through AI Hackathon** (May 2026).

## The Problem

On **August 2, 2026**, the EU AI Act's high-risk system rules become binding. Penalties reach **€35M or 7% of global revenue**. According to recent surveys, **50%+ of enterprises have no AI inventory**, no Article 11 technical files, and no Fundamental Rights Impact Assessment (FRIA) on record. Compliance teams are 77 days from a deadline they cannot meet.

## The Solution

ComplyForge is a single drop-in tool that:

1. **Discovers** every AI agent in your enterprise by proxying traffic through **Veea Lobster Trap**.
2. **Classifies** each agent against EU AI Act risk tiers (Prohibited / High-Risk / Limited / Minimal) using Google **Gemini**.
3. **Generates** the Article 11 technical file + FRIA + datasheet — full PDFs, in 60 seconds.
4. **Enforces** compliance by auto-generating **Lobster Trap YAML policies** that block violations in real time.
5. **Audits** every decision with regulator-ready trails.

## Architecture

```
[Enterprise AI agents / LLM calls]
            │
            ▼  (proxied)
  [Veea Lobster Trap]  ← logs every call, enforces policies
            │
            ▼
  [ComplyForge Orchestrator (Gemini)]
       ├── ClassifierAgent  → EU AI Act risk tier
       ├── DocAgent         → Article 11 PDF + FRIA + datasheet
       └── PolicyAgent      → auto-generates Lobster Trap YAML
            │
            ▼
  [Compliance Dashboard (React + Tailwind)]
       Inventory · Risk heatmap · Doc library · Live enforcement log
```

**One orchestrator + three specialised sub-agents.** Built on research showing structured small-team multi-agent (LangGraph-style) outperforms 5-6 agent meshes 17× in error rate.

## Sponsor Tech

- [Google Gemini API](https://aistudio.google.com/) — structured output, risk classification, long-form regulatory writing.
- [Veea Lobster Trap](https://github.com/veeainc/lobstertrap) — open-source LLM security proxy, MIT-licensed.

## Quick Start

```powershell
# Backend
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # then paste your GEMINI_API_KEY
uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev

# Lobster Trap (new terminal)
cd lobstertrap
.\setup.ps1
```

Visit http://localhost:5173 — drag and drop a sample agent from `backend/app/data/sample_agents/`.

## Demo

See `demo/script.md` for the 2:30 video walkthrough and `demo/pitch_deck.md` for the Sequoia-format pitch.

## Repository Layout

```
complyforge/
├── backend/         FastAPI + Gemini orchestrator + 3 sub-agents
├── frontend/        React + Tailwind compliance dashboard
├── lobstertrap/     Veea Lobster Trap config + policies
├── demo/            Pitch deck, video script, attack scenarios
└── docs/            Architecture, EU AI Act mapping
```

## License

MIT — see [LICENSE](LICENSE).

---

Built solo by Avinash Kumar for the TechEx 2026 hackathon. Powered by Gemini + Lobster Trap.
