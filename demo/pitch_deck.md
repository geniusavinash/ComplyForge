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
An autonomous agent that reasons, plans, and executes — in 60 seconds.

### Body bullets
- Four artefacts per run: tier classification, Article 11 PDF plus FRIA, Lobster Trap YAML, audit log.
- Single async pipeline; classifier first, then DocAgent and PolicyAgent in parallel; PDF rendered at the end.
- Gemini 2.0 Flash for classification and structured documentation.
- Veea Lobster Trap for live policy enforcement on the wire.
- Locked at 1 plus 3 agents — not a 5-to-7 mesh.

### Speaker notes
The architecture is deliberately small. One orchestrator. Three sub-agents.
ClassifierAgent reads the agent descriptor and the full EU AI Act taxonomy
and emits a tier with cited articles. DocAgent fans out ten concurrent
Gemini calls, one per Article 11 section plus the FRIA, and assembles a
multi-page PDF. PolicyAgent emits Veea Lobster Trap YAML in the real
schema. The orchestrator runs DocAgent and PolicyAgent in parallel; the
end-to-end pipeline finishes in a few seconds. We chose this shape on
purpose: large agent meshes are in the trough of disillusionment because
their error rates compound.

### Visual
Block diagram. Top: `AgentDescriptor` input. Middle: a single
`ComplianceOrchestrator` box. Three branches below: `ClassifierAgent`,
`DocAgent` (annotated "9 Article 11 sections + 1 FRIA, async.gather"), and
`PolicyAgent` (annotated "Veea Lobster Trap YAML"). Bottom: four output
tiles — Risk tier, Article 11 PDF, Policy YAML, Audit log. Sponsor
logos for Google Gemini and Veea Lobster Trap on the side.

---

## Slide 4: Why us / Why now

### Headline
Solo build, sponsor-native, real engineering honesty.

### Body bullets
- 94 passing tests (87 unit plus 7 new endpoint tests); 1 opt-in end-to-end test.
- Verified Veea Lobster Trap schema differs from BUILD_BIBLE placeholder; patched in two hours and documented every field.
- Lobster Trap binary has no hot reload; we surface `manual_restart_required` in the API response rather than fake one.
- Two sponsor stacks, used as the manuals describe: Gemini for inference, Veea Lobster Trap MIT for enforcement.
- 1 plus 3 agents, not 5 to 7. Smaller surface, fewer compounding errors.

### Speaker notes
Two things matter here. First, every claim on this slide is on disk. We
have 94 passing tests today: 87 unit tests plus 7 new endpoint tests for
the deploy-policy and inventory-zip endpoints, with one end-to-end test
that is opt-in via the e2e marker. Second, we have not faked anything we
could not verify. The Veea Lobster Trap policy schema in our brief turned
out to differ from the real binary's loader. We read serve.go and the
loader, patched our PolicyAgent in one centralised helper, and shipped a
diff document. The same binary has no reload mechanism. We tell the
operator that, with the policy file path, instead of inventing a flag.

### Visual
Two-column layout. Left column: a small stat card grid — "94 tests
passing", "5 enterprise agents seeded", "8 attack payloads", "Schema diff
patched in 2 hours", each in `bg-panel` with the `accent` color number.
Right column: a soft `border-soft` callout with the line **"We will not
fake what we cannot verify."** in `text-main`, centred.

---

## Slide 5: Demo + Ask

### Headline
Watch high-risk to Article 11 to enforced to audited. Sixty seconds.

### Body bullets
- Pick `ResumeRanker` from the seeded inventory.
- Classifier returns HIGH_RISK with `Annex III(4)` employment cited.
- DocAgent renders the Article 11 PDF and FRIA; PolicyAgent emits the 5-rule YAML.
- Deploy writes the policy to disk; restart Lobster Trap with the new file.
- Fire prompt-injection payload #2; proxy denies; audit log lights up.
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
