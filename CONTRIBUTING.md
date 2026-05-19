# Contributing to ComplyForge

ComplyForge is a solo hackathon submission for the lablab.ai **AI Agent
Olympics @ Milan AI Week 2026**. Issues and pull requests are welcome
**after** the submission window closes.

## Architecture is locked

The project is committed to a **1 orchestrator + 5 sub-agents** topology
(`PlannerAgent`, `ClassifierAgent`, `CriticAgent`, `DocAgent`,
`PolicyAgent`). See `docs/ARCHITECTURE.md` for the rationale: published
research shows fan-in / fan-out designs outperform sequential agent
chains by roughly 17 times on multi-step error rate. All five sub-agents
speak only to the Orchestrator — no inter-agent chains. PRs that introduce new agents
or split existing ones will be declined unless they come with a benchmark
that beats the current pipeline.

## Single touchpoint for Veea Lobster Trap schema drift

If the upstream Lobster Trap policy schema changes (it has changed once
already — see `lobstertrap/SCHEMA_NOTES.md`), the only files that need
edits are:

- `backend/app/agents/policy_generator.py` — specifically the `_rule()`
  and `_cond()` helpers.
- `backend/tests/test_policy_generator.py` — assertions on field names.

Keep changes scoped to those helpers; do not scatter schema knowledge
across views or routes.

## Testing

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pytest tests/ -v               # 116 passing tests
python -m pytest tests/ -v -m e2e        # opt-in: requires live services
```

```powershell
cd frontend
npm run build                            # must exit 0
```

## Code style

- Python: `black` and `ruff` defaults are the target. Not enforced in
  the build step; clean up before merging.
- JSX / JS: Prettier defaults. No TypeScript by design.
- Tailwind: tier colours and palette tokens come from
  `tailwind.config.js`. No hardcoded hex outside `frontend/src/lib/palette.js`
  (which exists only because Recharts cannot consume utility classes).

## Project context

`docs/ARCHITECTURE.md` is the canonical brief: the four-component flow,
concurrency proofs, the Veea Lobster Trap schema-drift finding, and the
repo layout. Read it before opening a PR larger than a single function.
