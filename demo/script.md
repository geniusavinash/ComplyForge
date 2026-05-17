# ComplyForge — 2:30 Demo Video Script

Hard timestamps. Narrator pacing target is roughly 150 words per minute, so
each segment's word count is calibrated to land inside its window without
rushing. Read it once aloud against a stopwatch before recording.

Segment-by-segment word counts (verified by `python`/`pwsh` count):
- 0:00–0:25 — 53 words → ~21 s spoken; ~4 s of breathing room.
- 0:25–1:00 — 67 words → ~27 s spoken; ~8 s of breathing room.
- 1:00–1:30 — 61 words → ~24 s spoken; ~6 s of breathing room.
- 1:30–2:05 — 69 words → ~28 s spoken; ~7 s of breathing room.
- 2:05–2:30 — 27 words → ~11 s spoken; ~14 s for the closing card hold.
- Total — 277 spoken words across 2:30 (~111 s), leaving ~39 s of natural pacing room across cuts and reveals. Lands at exactly 2:30 with comfortable headroom; if you read faster, the closing card simply holds longer.

---

## 0:00–0:25 — Hook

- TIME: 0:00–0:25
- SHOT: Full-screen countdown card. Bold red "77 DAYS". Below in amber: "August 2, 2026 — EU AI Act high-risk obligations binding".
- ON-SCREEN: `77 DAYS` · `August 2, 2026` · `Article 99: up to 35M EUR or 7% global revenue` · `50%+ of enterprises have no AI inventory`
- NARRATOR: "August 2, 2026. The EU AI Act's high-risk rules become binding. 77 days from now. The fine for a prohibited practice is 35 million euros, or 7 percent of global revenue, whichever is higher. More than half of enterprises do not even have an AI inventory yet. That is the gap ComplyForge closes."
- MUSIC: Neutral, low, building. No sting.

---

## 0:25–1:00 — Live walkthrough

- TIME: 0:25–1:00
- SHOT: Browser at `http://localhost:5173`, New Analysis view. Cursor picks the `ResumeRanker` sample card; ring-2 ring-accent appears. Click "Run Compliance Analysis". Right pane swaps to StepProgress; four steps tick through.
- ON-SCREEN: `New Analysis → ResumeRanker (Human Resources)` · `Classify` · `Generate Article 11 file (10 parallel Gemini calls)` · `Generate Lobster Trap policy` · `Render PDF`. Banner snaps to `HIGH RISK`.
- NARRATOR: "Pick a sample agent. ResumeRanker, an HR resume screener. Click Run. The orchestrator streams four steps. ClassifierAgent calls Gemini once and returns HIGH_RISK with Annex III(4) — employment — as the trigger. DocAgent fans out ten parallel Gemini calls, nine Article 11 sections plus the FRIA. PolicyAgent emits the Veea Lobster Trap YAML in the real schema. Then the PDF renders. The HIGH RISK banner snaps in."
- MUSIC: Steady. Slight rise as the four steps complete.

---

## 1:00–1:30 — Outputs

- TIME: 1:00–1:30
- SHOT: Quick cut to the rendered PDF (cover page with orange `risk-high` banner, then a section page, then the FRIA summary). Cut back to the dashboard, expand the YAML panel.
- ON-SCREEN: `Article 11 + Annex IV technical file` · `Article 27 FRIA` · `Lobster Trap policy: 5 rules` · `Articles cited: 10, 12, 14, 15, 72`
- NARRATOR: "The PDF has the Annex IV cover, nine numbered sections, the FRIA narrative, and a datasheet appendix. The footer reads 'Not legal advice — Article 11 plus Annex IV mapping'. The YAML panel shows five Lobster Trap rules: PII egress under Article 10, decision oversight under Article 14, injection block under Article 15, comprehensive logging under Article 12, and rate limiting."
- MUSIC: Same bed, slight rise.

---

## 1:30–2:05 — Live attack

- TIME: 1:30–2:05
- SHOT: Click "Deploy to Lobster Trap". Toast: success with rule count. Inline banner appears in the policy card: `manual_restart_required` with the policy path. Cut to terminal: stop and restart `lobstertrap.exe serve --policy policies\agents\resumeranker.yaml`. Cut to a second terminal: `.\demo\fire_attack.ps1 -Index 2`. Proxy returns DENY with `prompt_injection_block`. Cut to Enforcement Log: a new row appears within two seconds.
- ON-SCREEN: `POST /api/deploy-policy/resumeranker` · `reload_method: manual_restart_required` · `attack #2: prompt injection — Ignore previous instructions` · `Lobster Trap → DENY · prompt_injection_block` · `Enforcement Log → +1 event`
- NARRATOR: "Click Deploy. The backend writes the policy file and tells us the truth: the binary has no reload, restart it. We restart. Fire attack number two: the classic 'ignore previous instructions' prompt injection. Lobster Trap denies it under the injection rule. The webhook bridge relays the event. Within two seconds, the dashboard's enforcement log shows the deny with the rule name. That is the loop. Real binary. Real denial."
- MUSIC: Payoff cue at the deny moment. Hold under the dashboard light-up.

---

## 2:05–2:30 — Tech stack credits + closing

- TIME: 2:05–2:30
- SHOT: Wide shot of the dashboard (Inventory plus Enforcement Log on screen). Lower-third reveals the credits.
- ON-SCREEN: `Built on Google Gemini and Veea Lobster Trap (MIT)` · `94 passing tests · 1 opt-in e2e` · `Solo build · TechEx 2026` · `github.com/<user>/complyforge`
- NARRATOR: "Built on Google Gemini and Veea Lobster Trap. 94 passing tests. One opt-in end-to-end. Solo build for TechEx 2026. ComplyForge. Compliance as a service, not a slide."
- MUSIC: Resolve. Out clean at 2:30.
