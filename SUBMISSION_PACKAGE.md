# ComplyForge — Submission Package

Final lablab.ai team-page checklist plus ready-to-paste content. Replace
every `{{...}}` placeholder before submitting; `scripts/prepare_release.ps1`
will list every remaining placeholder with file:line so nothing slips.

---

## Team-page fields (copy-paste ready)

**Project name**

```
ComplyForge
```

**Tagline (≤120 chars)**

```
EU AI Act Article 11 Compliance Co-Pilot. Auto-generates technical files + FRIA + Lobster Trap policies in 60s.
```

**Long description**

Paste the **Problem**, **Solution**, and **Architecture** sections from
`README.md` verbatim. lablab.ai supports Markdown, so the headings, ASCII
diagram, and bullet lists render as-is.

**Team members**

- Avinash Kumar (solo) — `avinashkumarstm248@gmail.com`

**Tech tags**

```
FastAPI, React, Vite, Tailwind, Google Gemini, Veea Lobster Trap,
Pydantic v2, Pytest, EU AI Act, Article 11, FRIA, Annex IV, Annex III
```

**GitHub repo URL**

```
https://github.com/geniusavinash/complyforge
```

(Repository must be **public** before the deadline. The MIT LICENSE in
the repo root will surface in GitHub's sidebar.)

**Demo video URL**

```
https://youtu.be/{{YOUTUBE_VIDEO_ID}}
```

(Unlisted YouTube. Recorded against `demo/script.md` — 2:30 hard cap.)

**Live demo URL**

```
Run locally — see README "Quick Start". No hosted instance.
```

**Pitch deck link**

Either link to `demo/pitch_deck.md` in the repo (renders as-is on
GitHub), or export the five slides to Google Slides / Pitch.com and paste
that URL.

---

## Pre-flight checklist

Tick every box before you submit. `scripts/prepare_release.ps1` runs the
machine-checkable items automatically.

- [ ] All 94 unit tests + 7 endpoint tests pass:
      `cd backend; python -m pytest tests/ -v -m "not e2e"`
- [ ] e2e test passes locally with `GEMINI_API_KEY` set:
      `cd backend; python -m pytest tests/ -v -m e2e`
- [ ] Frontend builds clean: `cd frontend; npm run build`
- [ ] `demo/run_demo.ps1` boots all four services and opens the browser
- [ ] `demo/fire_attack.ps1 -Index 2` produces a visible DENY plus a new
      event in the dashboard's Enforcement Log
- [ ] At least 5 PDFs render under `backend/generated_pdfs/` after
      `scripts/seed_inventory.py`
- [ ] The HIGH_RISK ResumeRanker PDF opens; cover banner is orange; nine
      Article 11 sections present; FRIA section present; footer reads
      "Not legal advice | Article 11 + Annex IV mapping"
- [ ] Demo video recorded against `demo/script.md`, under 3 minutes,
      uploaded to YouTube unlisted, ID captured
- [ ] GitHub repo is **public**, README renders, LICENSE shows in sidebar
- [ ] `lablab.ai` team page populated with every field above
- [ ] (Optional) Posted in lablab Discord `#showcase` channel

---

## Manual steps still required

These are human tasks. ComplyForge will not perform them.

1. Create the GitHub repo at `github.com/geniusavinash/complyforge` —
   set visibility to **Public**.
2. From the workspace root:
   ```powershell
   git init
   git add -A
   git commit -m "ComplyForge — TechEx 2026 hackathon submission"
   ```
3. Add the remote and push:
   ```powershell
   git remote add origin https://github.com/geniusavinash/complyforge.git
   git push -u origin main
   ```
4. Tag a release:
   ```powershell
   git tag v0.1.0
   git push --tags
   ```
5. Record the demo video using `demo/script.md` (one take or stitched).
   Upload to YouTube as **Unlisted**.
6. Replace `{{YOUTUBE_VIDEO_ID}}` in this file with the real ID.
7. Replace `geniusavinash` everywhere it appears. Use:
   ```powershell
   Get-ChildItem -Recurse -File | Select-String -Pattern '\{\{GITHUB_USERNAME\}\}|\{\{LABLAB_TEAM_NAME\}\}|\{\{YOUTUBE_VIDEO_ID\}\}'
   ```
   `scripts/prepare_release.ps1` does the same scan and reports
   `file:line` for each remaining placeholder.
8. Replace `{{LABLAB_TEAM_NAME}}` in any docs that reference it.
9. Paste the team-page fields into:
   ```
   https://lablab.ai/ai-hackathons/techex-intelligent-enterprise-solutions-hackathon/{{LABLAB_TEAM_NAME}}
   ```
10. Submit before **2026-05-19** (lablab deadline).
