# ComplyForge — Pitch Deck

Solo build for the lablab.ai **AI Agent Olympics @ Milan AI Week 2026**
hackathon. Five slides, Sequoia format. Speaker notes are written for
reading aloud in 30–60 seconds at a natural ~150 words per minute.

---

## Slide 1: Hook

### Headline
On August 2, 2026, the EU AI Act's high-risk rules become binding.

### Body bullets
- Penalty for prohibited practices: 35 million EUR or 7 percent global revenue, whichever is higher.
- Other high-risk violations: 15 million EUR or 3 percent.
- 50 percent of enterprises still have no AI inventory.
- 75 days remain. Article 11 technical files are not optional.
- Being caught flat-footed is a budget event, not a fine line item.

### Speaker notes
Today is May 19, 2026. In 75 days, on August 2, the EU AI Act's high-risk
system rules become legally binding across the European Union. Article 99
sets the ceiling at 35 million euros or 7 percent of global revenue for
prohibited practices, and 15 million or 3 percent for other high-risk
violations. The European Commission's own DG-CNECT survey says more than
half of enterprises do not have a current inventory of the AI systems they
deploy. They cannot classify what they cannot see. And they cannot produce
an Article 11 technical file for a system they have not catalogued. That
is the gap ComplyForge closes.

### Visual
Full-bleed countdown bar in `risk-prohibited` red. Centered text: **75 DAYS**
on the first line, **August 2, 2026** on the second, in `accent` amber.
Sub-line in `text-dim`: "EU AI Act Article 6 + Annex III obligations binding".

---

## Slide 2: Problem

### Headline
Compliance teams have no tooling for Article 11.

### Body bullets
- The buyers: CISO, General Counsel, Head of Compliance, AI Ethics Lead.
- The need: AI inventory, EU AI Act classification, Article 11 technical file, Article 27 FRIA, enforced policy, audit trail.
- Trapdoor Tech ships access control, not regulatory documents.
- Sky/AgentWatch ships detection observability, not an Annex IV draft.
- Harvey, Ironclad, PreMortem, Infinite Context — none cover Article 11 plus FRIA plus enforcement.

### Speaker notes
There are good tools in adjacent lanes. Trapdoor Tech is contractor access
control on top of Lobster Trap. Sky and AgentWatch are detection
observatories. Harvey and Ironclad live in legal contracts. PreMortem AI
does retrospective failure analysis. Infinite Context does multi-agent
research. None of them produces an Annex IV technical file that an EU
auditor would recognise. None of them issues a Lobster Trap policy that
enforces what the file claims. None of them keeps an audit log a regulator
can replay. ComplyForge is the only one that closes that loop end to end.

### Visual
Six-row by four-column matrix table. Rows: AI inventory, EU AI Act
classification, Article 11 PDF, Article 27 FRIA, Lobster Trap enforcement,
Audit trail. Columns: Trapdoor Tech, AgentWatch, Harvey, **ComplyForge**.
Each cell is a tick or empty circle. Only the ComplyForge column is full.

---

## Slide 3: Solution / Architecture

### Headline
An autonomous agent that plans, reasons, critiques, and executes — in 60 seconds.

### Body bullets
- Five specialised sub-agents: Planner, Classifier, Critic, Doc, Policy. All speak only to the Orchestrator — no inter-agent chains.
- Plan first: PlannerAgent emits a four-step execution plan with dependency graph before any work runs. Visible in the dashboard.
- Critic last: CriticAgent does a second-opinion review of the Classifier's tier before docs and policy are written.
- Multimodal input: JSON, PNG, JPEG, or PDF — Gemini Vision extracts the AgentDescriptor when the input is visual.
- Output: 13-page Article 11 PDF, Veea Lobster Trap YAML, JSONL audit trail.

### Speaker notes
ComplyForge is one orchestrator and five specialised sub-agents. Planner
emits an explicit execution plan with dependencies — the operator sees the
agent reason about what it is about to do, before any of it happens.
ClassifierAgent reads the descriptor and the full EU AI Act taxonomy and
emits a tier with cited articles. CriticAgent then runs an independent
second-opinion review, surfaces concerns, and proposes a confidence delta;
it cannot change the tier, only the orchestrator can. DocAgent fans out
ten concurrent Gemini calls — nine Annex IV sections plus the Article 27
FRIA — and assembles a multi-page PDF. PolicyAgent emits Veea Lobster Trap
YAML in the real binary's schema. Doc and Policy run in parallel.
End-to-end in seconds. Inputs can be JSON, an image, or a PDF — Gemini
Vision handles the descriptor extraction. Five agents, but no chains: the
dependency graph is a fan-in and fan-out, every decision routes through
the Orchestrator's shared context.

### Visual
Block diagram. Top: input box showing three icons — JSON, image, PDF — all
flowing into `/api/extract-descriptor` (Gemini Vision) to produce an
`AgentDescriptor`. Middle: a single `ComplianceOrchestrator` card. Five
agent cards beneath in a fan layout: `PlannerAgent` (first), then
`ClassifierAgent` -> `CriticAgent`, then `DocAgent` (annotated "9 Article
11 sections + 1 FRIA, async.gather") and `PolicyAgent` (annotated "Veea
Lobster Trap YAML") side by side. Bottom: four output tiles — Plan
preview, Article 11 PDF, Policy YAML, Audit log. Sponsor logos for Google
Gemini and Veea Lobster Trap on the side.

---

## Slide 4: Why us / Why now

### Headline
Solo build, sponsor-native, real engineering honesty.

### Body bullets
- 116 passing backend tests across eleven test files; one opt-in end-to-end test runs against live services.
- Verified Veea Lobster Trap schema by reading the binary's source; patched our PolicyAgent in one centralised helper and documented every field.
- Lobster Trap binary has no hot reload; we surface `manual_restart_required` in the API response rather than fake one.
- Multimodal input: drop a model card PDF or a system-architecture PNG and Gemini Vision extracts the descriptor for you.
- Five specialised sub-agents (Planner, Classifier, Critic, Doc, Policy), fan-in / fan-out only — every decision routes through the Orchestrator's shared context.

### Speaker notes
Two things matter here. First, every claim on this slide is on disk. We
have 116 passing tests today across eleven test files, plus one
end-to-end test that is opt-in via the e2e marker. Second, we have not
faked anything we could not verify. The Veea Lobster Trap policy schema
in our initial design turned out to differ from the real binary's loader.
We read serve.go and the loader, patched our PolicyAgent in one
centralised helper, and shipped a diff document. The same binary has no
reload mechanism. We tell the operator that, with the policy file path,
instead of inventing a flag.

### Visual
Two-column layout. Left column: a small stat card grid — "116 tests
passing", "5 sub-agents", "5 enterprise agents seeded", "8 attack
payloads", each in `bg-panel` with the `accent` color number. Right
column: a soft `border-soft` callout with the line **"We will not fake
what we cannot verify."** in `text-main`, centred.

---

## Slide 5: Demo + Ask

### Headline
Watch high-risk to Article 11 to enforced to audited. Sixty seconds.

### Body bullets
- Pick `ResumeRanker` or upload an HR-tool architecture diagram — same pipeline.
- PlannerAgent emits a four-step plan, then ClassifierAgent returns HIGH_RISK with `Annex III(4)` cited.
- CriticAgent reviews and agrees (or dissents — both rendered in the Reasoning Trace panel).
- DocAgent renders the Article 11 + FRIA PDF; PolicyAgent emits the 5-rule Lobster Trap YAML.
- Deploy writes the policy; restart Lobster Trap; fire prompt-injection payload — proxy denies; audit log lights up.
- Ask: judges' vote, Veea Discord support, lablab community share.

### Speaker notes
The demo is one click. Pick ResumeRanker, the HR resume screener. Watch
four streaming steps: classify, generate documents, generate policy,
render PDF. The classifier returns HIGH_RISK with Annex III(4). The
DocAgent renders an Article 11 PDF with the nine Annex IV sections and the
six-section FRIA. The PolicyAgent emits a five-rule Veea Lobster Trap
policy that cites Articles 10, 12, 14, 15, and 72. Click Deploy. The API
honestly tells us the binary needs a restart with the new policy file. We
restart. We fire the prompt-injection attack. The proxy denies it under
the injection rule. The dashboard's enforcement log lights up within two
seconds. That is the loop. Vote ComplyForge.

### Visual
Four-frame horizontal storyboard: (1) sample-agent grid with `ResumeRanker`
selected and a `ring-2 ring-accent`; (2) the streaming `StepProgress`
component mid-pipeline; (3) the Lobster Trap YAML viewer expanded with the
five rules visible; (4) the EnforcementLog feed showing a `DENY` chip with
`prompt_injection_block` and a `~2s ago` timestamp. Caption strip: "60-second
end-to-end run, all real artefacts on disk."
