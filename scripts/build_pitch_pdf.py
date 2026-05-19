"""Generate a clean 5-slide pitch deck PDF from demo/pitch_deck.md.

Reads the markdown, splits on '## Slide N:' headers, renders each slide as
one landscape page via ReportLab Platypus.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
)

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "demo" / "pitch_deck.md"
OUTPUT = ROOT / "demo" / "pitch_deck.pdf"

# Brand palette (matches Tailwind tokens used in the frontend)
BG_PANEL = colors.HexColor("#111827")
BORDER_SOFT = colors.HexColor("#1F2937")
TEXT_MAIN = colors.HexColor("#0B0F1A")
TEXT_DIM = colors.HexColor("#6B7280")
ACCENT = colors.HexColor("#F59E0B")
RISK_PROHIBITED = colors.HexColor("#DC2626")
RISK_HIGH = colors.HexColor("#EA580C")

PAGE_WIDTH, PAGE_HEIGHT = landscape(letter)


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "slide_tag": ParagraphStyle(
            name="slide_tag",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=ACCENT,
            spaceAfter=8,
            leading=12,
        ),
        "headline": ParagraphStyle(
            name="headline",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=24,
            textColor=TEXT_MAIN,
            spaceAfter=14,
            leading=28,
        ),
        "section_label": ParagraphStyle(
            name="section_label",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=ACCENT,
            spaceAfter=4,
            leading=12,
        ),
        "bullet": ParagraphStyle(
            name="bullet",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=12,
            textColor=TEXT_MAIN,
            leftIndent=14,
            bulletIndent=2,
            spaceAfter=4,
            leading=16,
        ),
        "speaker": ParagraphStyle(
            name="speaker",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=10,
            textColor=TEXT_DIM,
            spaceAfter=4,
            leading=13,
            leftIndent=4,
        ),
        "visual": ParagraphStyle(
            name="visual",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            textColor=TEXT_DIM,
            spaceAfter=2,
            leading=12,
            leftIndent=4,
        ),
        "footer": ParagraphStyle(
            name="footer",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            textColor=TEXT_DIM,
            alignment=1,
            leading=10,
        ),
    }


_SLIDE_PATTERN = re.compile(r"^## Slide (\d+): (.+)$", re.MULTILINE)


def _split_slides(md: str) -> list[dict[str, str]]:
    """Split markdown into ordered slide dicts."""
    matches = list(_SLIDE_PATTERN.finditer(md))
    if not matches:
        raise SystemExit("No '## Slide N:' headers found in pitch_deck.md")
    slides: list[dict[str, str]] = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md)
        body = md[match.end():end].strip()
        slides.append({
            "number": match.group(1),
            "title": match.group(2).strip(),
            "body": body,
        })
    return slides


def _section(body: str, heading: str) -> str:
    """Extract a ### sub-section from a slide body."""
    pattern = re.compile(rf"^### {re.escape(heading)}\n(.*?)(?=^### |\Z)", re.MULTILINE | re.DOTALL)
    match = pattern.search(body)
    return match.group(1).strip() if match else ""


def _bullets(text: str) -> list[str]:
    """Pull `- bullet` lines out of a block."""
    return [
        line[2:].strip()
        for line in text.splitlines()
        if line.startswith("- ")
    ]


def _escape(text: str) -> str:
    """ReportLab Paragraph uses XML-ish markup; escape unsafe chars."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("**", "")
        .replace("`", "")
    )


def _on_page(canvas, doc):
    """Draw a thin accent strip + page footer on every page."""
    canvas.saveState()
    canvas.setFillColor(ACCENT)
    canvas.rect(0, PAGE_HEIGHT - 0.18 * inch, PAGE_WIDTH, 0.18 * inch, fill=1, stroke=0)
    canvas.setFillColor(BORDER_SOFT)
    canvas.rect(0, 0, PAGE_WIDTH, 0.05 * inch, fill=1, stroke=0)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(TEXT_DIM)
    canvas.drawCentredString(
        PAGE_WIDTH / 2,
        0.18 * inch,
        f"ComplyForge — AI Agent Olympics @ Milan AI Week 2026   ·   github.com/geniusavinash/ComplyForge   ·   Page {doc.page}",
    )
    canvas.restoreState()


def build(source: Path, output: Path) -> None:
    md = source.read_text(encoding="utf-8")
    slides = _split_slides(md)
    styles = _styles()

    margin_x = 0.7 * inch
    margin_top = 0.55 * inch
    margin_bottom = 0.5 * inch
    frame = Frame(
        margin_x,
        margin_bottom,
        PAGE_WIDTH - 2 * margin_x,
        PAGE_HEIGHT - margin_top - margin_bottom,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
        showBoundary=0,
    )

    doc = BaseDocTemplate(
        str(output),
        pagesize=landscape(letter),
        leftMargin=margin_x,
        rightMargin=margin_x,
        topMargin=margin_top,
        bottomMargin=margin_bottom,
        title="ComplyForge — Pitch Deck",
        author="Avinash Kumar",
    )
    doc.addPageTemplates([PageTemplate(id="slide", frames=[frame], onPage=_on_page)])

    story: list = []
    for idx, slide in enumerate(slides):
        story.append(Paragraph(f"SLIDE {slide['number']} — {_escape(slide['title']).upper()}", styles["slide_tag"]))
        headline_raw = _section(slide["body"], "Headline")
        story.append(Paragraph(_escape(headline_raw), styles["headline"]))

        body_bullets = _bullets(_section(slide["body"], "Body bullets"))
        if body_bullets:
            story.append(Paragraph("KEY POINTS", styles["section_label"]))
            for bullet in body_bullets:
                story.append(Paragraph(f"•  {_escape(bullet)}", styles["bullet"]))
            story.append(Spacer(1, 0.12 * inch))

        speaker = _section(slide["body"], "Speaker notes")
        if speaker:
            story.append(Paragraph("SPEAKER NOTES", styles["section_label"]))
            story.append(Paragraph(_escape(speaker), styles["speaker"]))
            story.append(Spacer(1, 0.1 * inch))

        visual = _section(slide["body"], "Visual")
        if visual:
            story.append(Paragraph("VISUAL DIRECTION", styles["section_label"]))
            story.append(Paragraph(_escape(visual), styles["visual"]))

        if idx < len(slides) - 1:
            story.append(PageBreak())

    doc.build(story)


if __name__ == "__main__":
    if not SOURCE.exists():
        sys.exit(f"Source not found: {SOURCE}")
    build(SOURCE, OUTPUT)
    print(f"Wrote {OUTPUT.relative_to(ROOT)} ({OUTPUT.stat().st_size:,} bytes)")
