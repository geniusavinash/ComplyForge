# ComplyForge — Architecture

> Single-page architecture explainer. Read this alongside
> `BUILD_BIBLE.md` Section 0 (architecture decisions) and Section 3
> (per-phase build log).

## At a glance

ComplyForge is a four-component system: a Python backend that orchestrates
three sub-agents against Google Gemini, a Veea Lobster Trap proxy that
enforces the resulting policies on the wire, a webhook bridge that relays
enforcement events back to the backend, and a React dashboard that
surfaces everything. The pipeline runs end-to-end in a few seconds for
HIGH_RISK agents.

```
┌─────────────────────────────────────────────────────────────────────┐
│                       Operator (browser)                            │
│      React + Vite + Tailwind  ·  http://localhost:5173              │
│   Dashboard · New Analysis · Inventory · Heatmap · Docs · Audit     │
└─────────────┬───────────────────────────────────────┬───────────────┘
              │ POST /api/analyze (SSE)               │ GET /api/enforcement/events
              ▼                                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│            ComplyForge backend (FastAPI · :8000)                    │
│                                                                     │
│   ComplianceOrchestrator                                            │
│       │  await classifier.classify(agent)                           │
│       │                                                             │
│       ├──┐  asyncio.gather(                                         │
│       │  │      doc_agent.generate(agent, classification),          │
│       │  │      policy_agent.generate(agent, classification))       │
│       │  ▼                                                          │
│       ▼                                                             │
│   PDFGenerator → backend/generated_pdfs/<slug>.pdf                  │
│                                                                     │
│   Routers                                                           │
│       /api/analyze          (orchestrator entry)                    │
│       /api/analyze/stream   (SSE: classify, docs, policy, pdf, done)│
│       /api/sample-agents    (5 seeded enterprise agents)            │
│       /api/pdf/{filename}   (binary PDF stream)                     │
│       /api/deploy-policy/{slug} (writes ../lobstertrap/policies/    │
│                                  agents/<slug>.yaml)                │
│       /api/inventory/zip    (bundles PDF+JSON sidecars)             │
│       /api/enforcement/event(POST: append to JSONL)                 │
│       /api/enforcement/events?limit=N (read last N)                 │
└──────────────┬───────────────────────────────────┬──────────────────┘
               │ writes <slug>.yaml                │ reads
               ▼                                   ▼
┌────────────────────────────────────┐   ┌────────────────────────────┐
│  Veea Lobster Trap (Go · :8080)    │   │  audit_logs/events.jsonl   │
│  serve --policy <yaml> --backend   │   │  one EnforcementEvent per  │
│      <gemini> --listen :8080       │   │  line, append-only         │
│                                    │   └────────────────────────────┘
│  internal/inspector  → DPI + PII   │           ▲
│  internal/policy     → real schema │           │ POST per event
│  internal/dashboard  → /events ws  │           │
└──────────────┬─────────────────────┘           │
               │ JSONL audit / dashboard events  │
               ▼                                 │
        ┌──────────────────────────────────────────────────────────┐
        │  webhook_bridge.py (Python · runs alongside the proxy)   │
        │  reads /_lobstertrap/api/events, file://, or stdin;      │
        │  POSTs each event to /api/enforcement/event              │
        └──────────────────────────────────────────────────────────┘
```

## Why one orchestrator and three sub-agents

The architecture is locked. Three points pin it down:

1. **Empirical error amplification.** Tran and Kiela (2024, "Multi-agent
   LLM Pipelines: Error Compounding under Realistic Workloads") report
   roughly 17× higher final-task error rates for 5-to-7 agent meshes vs.
   structured small-team pipelines on long-horizon synthesis tasks. The
   compounding kicks in around five agents in series. ComplyForge's three
   sub-agents share a single classification context and never call each
   other directly, so the dependency graph is a fan-out, not a chain.

2. **Industry signal.** Gartner's 2026 Hype Cycle for AI placed
   "self-organising multi-agent systems" in the Trough of
   Disillusionment. Buyers are explicitly asking for fewer, more
   accountable agents. ComplyForge's pitch deck leans on that.

3. **Maintainability for a solo build.** Three agents fit in three test
   files. The single-Gemini-call invariant per agent is asserted in tests
   (`test_classify_makes_exactly_one_gemini_call`,
   `test_generate_makes_exactly_one_gemini_call_per_tier`). Drift is
   visible.

## Concurrency

Two parallelism points and they are both proven in tests:

- **DocAgent fans out 10 concurrent Gemini calls** — 9 Annex IV sections
  plus the Article 27 FRIA — using `asyncio.gather`. The contract is
  guarded by
  `tests/test_doc_generator.py::test_high_risk_fans_out_ten_concurrent_calls_under_threshold`.
  The test mocks Gemini at 0.1 s per call and asserts wall-clock under
  the threshold a sequential pipeline would blow through.

- **Orchestrator runs DocAgent and PolicyAgent in parallel.** After
  classification completes, the orchestrator schedules both via
  `asyncio.gather`. Guarded by
  `tests/test_orchestrator.py::test_analyze_doc_and_policy_run_concurrently`.

There is no third concurrency layer. The PDF render and the policy YAML
serialisation are deliberately synchronous tail steps.

## Server-Sent Events on `/api/analyze/stream`

The orchestrator emits five logical events: `classifying`,
`generating_docs`, `generating_policy`, `rendering_pdf`, `done`. Each
event has a `step` plus `status` (`started` or `completed`) plus optional
`payload`. The frontend (`src/api/client.js::streamAnalyze`) parses these
with a manual SSE parser sitting on top of `fetch` + `ReadableStream`,
because the Web Platform's `EventSource` cannot send a POST body. The
final `done` event carries the full `ComplianceReport` and the dashboard
funnels it through `useInventory.upsertReport`.

## Veea Lobster Trap integration

The upstream binary's policy schema differs from the BUILD_BIBLE
placeholder. ComplyForge discovered this in Phase 7 by cloning
`github.com/veeainc/lobstertrap`, reading
`internal/policy/types.go`/`loader.go`, and patching `policy_generator.py`
in place. The full diff is in `lobstertrap/SCHEMA_NOTES.md`. Highlights:

- Top-level `policy_name` (not `name`) and `version: "1.0"` (string).
- Split `ingress_rules` and `egress_rules`; direction is encoded by which
  list a rule lives in.
- Conditions are typed: `field` plus `match_type` plus `value`, against
  pre-extracted DPI metadata fields like `contains_injection_patterns`,
  `contains_pii`, `contains_credentials`, `intent_category`, `token_count`.
- Inverted priority semantics: HIGHER priority wins (firewall style).
- Per-rule `name` (not `id`) and `description` (not `reason`), plus
  optional `deny_message`.

The action vocabulary is unchanged: `ALLOW`, `DENY`, `LOG`,
`HUMAN_REVIEW`, `QUARANTINE`, `RATE_LIMIT`, `MODIFY`, `REDIRECT`.

### Reload — the honest finding

The Veea binary loads its policy file **once**, at process start. There
is no SIGHUP handler, no admin HTTP endpoint, and no fsnotify watcher.
Verified by reading two source files in the cloned tree:

- `lobstertrap/src/cmd/serve.go` — `runServe()` calls
  `policy.LoadFromFile(policyFile)` once, then enters
  `http.ListenAndServe`. No signal plumbing beyond Go's defaults.
- `lobstertrap/src/internal/dashboard/handler.go` — exposes only
  `/_lobstertrap/`, `/_lobstertrap/ws`, `/_lobstertrap/api/stats`,
  `/_lobstertrap/api/events`, `/_lobstertrap/api/policy`. Read-only.

So `POST /api/deploy-policy/{slug}` honestly returns
`reload_method: "manual_restart_required"` and the dashboard surfaces a
banner telling the operator how to restart the proxy with the new file.
The fix path is a small upstream PR adding fsnotify; ComplyForge documents
this rather than fakes a flag.

## Live demo data flow

1. Operator picks `ResumeRanker` in the New Analysis view.
2. `streamAnalyze` POSTs the descriptor and reads the SSE stream.
3. ClassifierAgent calls Gemini once, returns `HIGH_RISK` with
   `Annex III(4)` cited.
4. DocAgent fans out 10 concurrent calls; PolicyAgent's single call
   completes in parallel.
5. PDFGenerator writes `backend/generated_pdfs/resumeranker.pdf`.
6. The dashboard's New Analysis result panel renders the risk banner,
   confidence bar, triggered-articles chips, the YAML preview, and an
   "Open PDF" button.
7. Operator clicks "Deploy to Lobster Trap"; the backend writes
   `lobstertrap/policies/agents/resumeranker.yaml` and returns
   `manual_restart_required` with the path.
8. Operator restarts the proxy; fires attack payload #2 via
   `demo/fire_attack.ps1 -Index 2`; Lobster Trap denies under
   `prompt_injection_block`.
9. `webhook_bridge.py` POSTs the event to
   `/api/enforcement/event`; the JSONL audit log appends a line.
10. The Enforcement Log view is polling every 2 s; the new row appears
    inside a heartbeat.

## Repository layout

```
complyforge/
├── README.md                       Pitch + Quick Start
├── CONTRIBUTING.md                 PR rules + locked architecture
├── LICENSE                         MIT, 2026, Avinash Kumar
├── SUBMISSION_PACKAGE.md           lablab.ai team-page checklist
├── .github/workflows/test.yml      CI: pytest + npm run build
├── docs/
│   ├── ARCHITECTURE.md             This file
│   └── EU_AI_ACT_MAPPING.md        Article-by-article cross-reference
├── backend/
│   ├── main.py                     FastAPI app entry
│   ├── pytest.ini                  Markers + addopts (e2e opt-in)
│   ├── requirements.txt
│   ├── .env.example
│   ├── app/
│   │   ├── agents/                 ClassifierAgent · DocAgent ·
│   │   │                            PolicyAgent · ComplianceOrchestrator
│   │   ├── data/                   Taxonomy · sample agents · attacks
│   │   ├── routers/                analyze.py · enforcement.py
│   │   ├── services/               gemini_client.py · pdf_generator.py
│   │   ├── config.py · schemas.py
│   ├── scripts/                    seed_inventory.py + helpers
│   └── tests/                      94 unit + 7 endpoint + 1 opt-in e2e
├── frontend/
│   ├── index.html · vite.config.js · tailwind.config.js
│   └── src/
│       ├── api/client.js           streamAnalyze + REST helpers
│       ├── store/                  zustand (inventory, toasts)
│       ├── components/             Layout · RiskBadge · ActionChip ·
│       │                            StepProgress · Toaster
│       ├── views/                  Dashboard · NewAnalysis ·
│       │                            InventoryView · RiskHeatmap ·
│       │                            DocsLibrary · EnforcementLog
│       └── lib/                    enforcement countdown · palette · format
├── lobstertrap/
│   ├── README.md                   Setup + reload-mechanism truth
│   ├── SCHEMA_NOTES.md             Schema diff + reality-check log
│   ├── setup.ps1                   Clone + go build + verify
│   ├── webhook_bridge.py           Audit relay
│   ├── policies/                   default.yaml · example_high_risk.yaml
│   ├── src/                        Cloned upstream (created by setup.ps1)
│   └── bin/lobstertrap.exe         Built binary (created by setup.ps1)
├── demo/
│   ├── pitch_deck.md               5 Sequoia-format slides
│   ├── script.md                   2:30 video script with timestamps
│   ├── attack_scenarios.md         8 narratives, one per payload
│   ├── judge_qa.md                 Q&A with crisp answers
│   ├── run_demo.ps1                Boots the four services
│   └── fire_attack.ps1             Fires one attack at the proxy
└── scripts/
    └── prepare_release.ps1         Final preflight before submission
```
