# ComplyForge — Submission Package

Paste-ready lablab.ai team-page content for the **AI Agent Olympics @ Milan AI Week 2026** hackathon.

---

## Team-page fields (copy-paste ready)

**Team name** (max 45 chars)

```
ComplyForge
```

**Team description** (max 150 chars)

```
EU AI Act Article 11 compliance in 60 seconds — auto-generates technical files, FRIA, and Veea Lobster Trap policies.
```

**Looking for team members?** — `OFF`

**Timezone** — `Asia/Kolkata` (UTC +5:30)

---

## Submission fields

**Submission Title** (max 50 chars)

```
ComplyForge — Autonomous EU AI Act Compliance Agent
```

**Short Description** (max 255 chars)

```
ComplyForge is an autonomous compliance agent that reasons about EU AI Act risk, plans a 12-step pipeline, and executes — classifying enterprise AI, generating Article 11 + FRIA documents, and deploying enforced Veea Lobster Trap policies. All in 60 seconds.
```

**Long Description** (paste verbatim)

```
ComplyForge — Autonomous EU AI Act Compliance Agent

PROBLEM
On August 2, 2026, the EU AI Act's high-risk system rules become binding. Penalties reach €35M or 7% of global revenue. Over half of enterprises have no AI inventory, no Article 11 technical file, and no Fundamental Rights Impact Assessment (FRIA). Compliance teams are 75 days from a deadline they cannot meet manually.

AUTONOMOUS AGENT DESIGN
ComplyForge is an autonomous compliance agent built around one Orchestrator and three specialised sub-agents:

1. ClassifierAgent — reasons about an AI system's purpose against the full EU AI Act taxonomy (Article 5 prohibited categories, Annex III high-risk domains, Article 50 transparency triggers). Drops hallucinated citations against a whitelist, applies the precautionary principle when confidence is low (auto-promotes to HIGH_RISK rather than weakening a compliance posture).

2. DocAgent — plans a 10-step concurrent document generation across the nine Annex IV sections plus the Article 27 FRIA. Auto-corrects if the underlying model returns the wrong section count. Generates a 13-page regulator-ready PDF.

3. PolicyAgent — generates a Veea Lobster Trap YAML policy that enforces classification at runtime. Falls back to deterministic reasons if the LLM is unavailable, and is hard-locked to the eight documented Lobster Trap actions — never invents undocumented actions.

The Orchestrator plans the pipeline, executes classification first (gating step), then runs document and policy generation concurrently, then renders the regulator-ready PDF. End-to-end in 60 seconds.

REASONING + ROADBLOCKS
The Classifier validates every cited article against the taxonomy whitelist — fabricated references like "Article 999" or "GDPR Article 22" are silently dropped with a warning. When confidence drops below 0.5 and the tier isn't already PROHIBITED, the system auto-promotes to HIGH_RISK rather than weakening a compliance posture. The Veea Lobster Trap binary has no hot reload (verified by reading serve.go and handler.go); ComplyForge's deploy endpoint returns manual_restart_required honestly rather than fake a reload, with restart instructions surfaced in the dashboard.

ENTERPRISE UTILITY
Output is a 13-page regulator-ready PDF (Article 11 technical file + FRIA + datasheet) plus a deployable Veea Lobster Trap YAML that actively blocks PII egress, prompt injection, and decisions without Article 14 human oversight. The audit log is structured JSONL — drop into any SIEM.

MULTIMODAL OUTPUT
ComplyForge emits three artefact modalities from a single AgentDescriptor input: a PDF technical file for regulators, a YAML enforcement policy for the security proxy, and JSONL audit events for observability stacks.

TECH STACK
Backend: Python 3.14, FastAPI, Pydantic v2, Google Gemini, ReportLab.
Frontend: React + Vite + TailwindCSS + recharts + zustand.
Sponsor tech: Veea Lobster Trap (MIT, Go binary), Google Gemini.
Testing: 94 unit tests + 7 endpoint tests passing, 1 opt-in end-to-end integration test.
Architecture: one orchestrator plus three sub-agents (research-backed against 5-7 agent meshes).

Built solo in under 48 hours. Open source under MIT. Repository: https://github.com/geniusavinash/ComplyForge
```

---

## Categories (multi-select, pick 3-5)

```
Security
Enterprise
Compliance
AI
Assistant
```

## Event Tracks (pick all that apply)

```
Agentic Workflows
Enterprise Utility
Intelligent Reasoning
Multimodal Intelligence
```

## Technologies Used (paste these tags)

```
Google Gemini
AI Studio
Lobster Trap
FastAPI
Python
React
TailwindCSS
Vite
Pydantic
pytest
ReportLab
```

---

## URLs

**GitHub repo URL**
```
https://github.com/geniusavinash/ComplyForge
```

**Demo video URL** — to be uploaded after recording (YouTube unlisted or Loom share link)

```
{{YOUTUBE_VIDEO_ID_OR_LOOM_LINK}}
```

**Live demo URL**
```
Run locally — see README Quick Start. No hosted instance (deliberate: every demo runs against the deployer's own Gemini key, audit log stays local).
```

---

## Media uploads

| Field | File path | Status |
|-------|-----------|--------|
| Cover image | `demo/cover_image.png` | Generated 1920×1080 |
| Video presentation | record + upload via Loom or YouTube | **TODO by user** |
| Slide presentation | `demo/pitch_deck.pdf` | Generated |

---

## Pre-flight checklist

Tick every box before final submit:

- [x] All 94 unit tests + 7 endpoint tests pass
- [x] Frontend builds clean
- [x] Lobster Trap binary builds and inspects policies correctly
- [x] At least 1 sample agent (RecipeBuddy or ResumeRanker) analyzed end-to-end against live Gemini
- [x] HIGH_RISK PDF (ResumeRanker) opens — orange banner, 9 Article 11 sections, FRIA, footer disclaimer
- [x] GitHub repo public, README renders, LICENSE shows
- [x] Cover image generated
- [x] Pitch deck PDF generated
- [ ] Demo video recorded + uploaded
- [ ] lablab.ai team page populated
- [ ] Final submit clicked before deadline

---

## Manual steps still required

1. Record demo video (2:30) — use `demo/script.md` as the narration guide.
2. Upload video to Loom (https://www.loom.com) or YouTube (unlisted) — paste the link.
3. Open lablab.ai team page for the AI Agent Olympics hackathon.
4. Paste the team-page + submission fields above.
5. Upload `demo/cover_image.png` and `demo/pitch_deck.pdf`.
6. Click submit. Verify confirmation.
