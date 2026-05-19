# ComplyForge — Final Submission Guide

**One-page cheat sheet to ship the lablab submission in 30 minutes.**

Hackathon: **AI Agent Olympics @ Milan AI Week 2026**
Repo: https://github.com/geniusavinash/ComplyForge
Author: Avinash Kumar `<avinashkumarstm248@gmail.com>`

---

## ✅ What's Already Done (no action needed)

| Artifact | Path | Status |
|----------|------|--------|
| Public GitHub repo | https://github.com/geniusavinash/ComplyForge | ✅ pushed (v0.1.0 tagged) |
| LICENSE (MIT, Avinash Kumar) | `LICENSE` | ✅ |
| README with Milan hackathon framing | `README.md` | ✅ |
| Architecture doc | `docs/ARCHITECTURE.md` | ✅ |
| EU AI Act mapping reference | `docs/EU_AI_ACT_MAPPING.md` | ✅ |
| 94 backend tests passing | `backend/tests/` | ✅ |
| Lobster Trap real schema verified | `lobstertrap/SCHEMA_NOTES.md` | ✅ |
| Pitch deck (5-slide PDF) | `demo/pitch_deck.pdf` | ✅ generated |
| Cover image (1920×1080) | `demo/cover_image.png` | ✅ generated |
| Sample ResumeRanker PDF (HIGH_RISK proof) | downloaded from browser | ✅ |
| Submission text + tracks + tags | `SUBMISSION_PACKAGE.md` | ✅ |

---

## ⏳ What You Must Do (manual — 30-90 min)

### 1. Record the demo video (15-45 min)

**Easiest path: Loom**

1. Go to https://www.loom.com and sign up free (Google account works)
2. Click **"New Recording"** → **"Screen Only"** (no webcam needed)
3. Open browser to http://localhost:5173 (backend + frontend must be running)
4. Record 2 to 2:30 minutes following the flow below
5. Stop recording → Loom auto-saves → click **"Copy link"** → done

**Backup path: Windows Game Bar**

1. Press `Win + G` → recording widget appears
2. Click the red circle button to start
3. Demo for 2 minutes
4. Press `Win + Alt + R` to stop
5. File saves to `Videos\Captures\` → upload to YouTube unlisted later

### 2. Video flow (read aloud or just narrate roughly)

| Time | Action on screen | Narration (English or Hinglish) |
|------|------------------|--------------------------------|
| 0:00-0:25 | Dashboard, countdown badge in top right | "August 2, 2026 — EU AI Act high-risk system rules become binding. €35 million fines. 75 days. Half of enterprises have no AI inventory. ComplyForge is the autonomous agent that closes the gap." |
| 0:25-1:00 | New Analysis → click **ResumeRanker** → click Run | "Pick any enterprise AI agent. ComplyForge plans a four-step pipeline. Classify against EU AI Act. Generate Article 11 documents. Generate Lobster Trap policy. Render PDF. All running concurrently." |
| 1:00-1:40 | Open the downloaded ResumeRanker PDF, scroll | "Sixty seconds later: a fifteen-page regulator-ready Article 11 file. Orange HIGH RISK banner. Annex III(4) employment cited. FRIA section. Datasheet with all seven model-card fields. Real Article references — no hallucinations." |
| 1:40-2:10 | Show Inventory + Risk Heatmap + Enforcement Log views | "Inventory of every AI agent in the enterprise. Risk heatmap by domain. Audit log streamed from Veea Lobster Trap." |
| 2:10-2:30 | Wide Dashboard shot | "Built solo on Google Gemini and Veea Lobster Trap. Ninety-four backend tests passing. Open source MIT. ComplyForge — autonomous EU AI Act compliance." |

### 3. Lablab submission (15 min)

Open the lablab team-page submission flow you were in.

#### Step 1 — Basic Information

Copy from `SUBMISSION_PACKAGE.md` →

- **Submission Title:** `ComplyForge — Autonomous EU AI Act Compliance Agent`
- **Short Description:** the 252-char block in SUBMISSION_PACKAGE.md
- **Long Description:** the full block in SUBMISSION_PACKAGE.md
- **Participation Mode:** Online
- **Categories:** Security, Enterprise, Compliance, AI, Assistant (pick 3-5)
- **Event Tracks:** Agentic Workflows, Enterprise Utility, Intelligent Reasoning, Multimodal Intelligence (pick all 4 if multi-select)
- **Technologies Used:** Google Gemini, AI Studio, Lobster Trap, FastAPI, Python, React, TailwindCSS, Vite, Pydantic, pytest, ReportLab

Click **Next**.

#### Step 2 — Media

- **Cover Image:** upload `demo/cover_image.png`
- **Video Presentation:** paste Loom link OR upload MP4 from Game Bar
- **Slide Presentation:** upload `demo/pitch_deck.pdf`

Click **Next**.

#### Step 3 — Final URLs

- **GitHub repo URL:** `https://github.com/geniusavinash/ComplyForge`
- **Demo video URL:** the Loom / YouTube link you just generated
- **Live demo URL:** `Run locally — see README Quick Start`

Click **Submit**.

### 4. Verify

After submission, your team page should show:
- Cover image at the top
- Project title and description
- Video embedded
- Tracks and categories listed
- GitHub link clickable
- "Submitted" or similar confirmation badge

If anything is missing or rejected, the lablab UI will say so — fix that one field and resubmit.

---

## 🆘 If Something Breaks

### Video upload fails
- File too big? Reduce to 720p in Loom settings, or trim duration
- Loom won't load? Try Game Bar (offline recording) → upload to YouTube unlisted (https://studio.youtube.com)

### Lablab field validation error
- Check character counts (title 50, short 255, long 100+ words)
- Tracks: must pick at least one
- Technologies: at least one (Google Gemini for sure)

### Cover image rejected
- Should be 16:9 — `demo/cover_image.png` is 1920×1080, fits 16:9 exactly
- If lablab wants a different aspect, resize in Paint (Ctrl+E then Resize)

### Pitch PDF rejected
- 5 pages, landscape, under 11 KB — should be fine
- If lablab wants portrait, edit `scripts/build_pitch_pdf.py` and change `landscape(letter)` to `letter`

---

## 📎 Quick Reference

| What | Where |
|------|-------|
| Cover image | `demo/cover_image.png` |
| Pitch deck PDF | `demo/pitch_deck.pdf` |
| Sample HIGH_RISK PDF (open during video) | downloaded earlier — keep handy |
| Submission text blocks | `SUBMISSION_PACKAGE.md` |
| Public repo | https://github.com/geniusavinash/ComplyForge |
| Video script reference | `demo/script.md` |
| Judge Q&A prep | `demo/judge_qa.md` |

---

## ⏰ Suggested Order (90 min target)

```
00:00 — Open Loom, sign up                       (5 min)
00:05 — Record video (2 takes if needed)         (20 min)
00:25 — Verify Loom link works                   (2 min)
00:27 — Open lablab submission flow              (1 min)
00:28 — Step 1 paste fields from SUBMISSION_PACKAGE
                                                  (15 min)
00:43 — Step 2 upload cover + video + pitch PDF (10 min)
00:53 — Step 3 paste GitHub + video URLs         (5 min)
00:58 — Final submit + verify                    (2 min)
01:00 — DONE — go check team page                ✅
```

If lablab build phase has closed already, submit anyway — the project page may still be created as a community showcase, and the public repo + demo materials remain valid portfolio pieces.

---

**Built in 48 hours. Real engineering. Open source. Submit and ship.**
