"""Generate a 1920x1080 cover image for the lablab submission.

Dark navy background, ComplyForge wordmark, tagline, and a compact
countdown stripe — all using the brand palette from the frontend.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "demo" / "cover_image.png"

WIDTH, HEIGHT = 1920, 1080

# Brand palette (matches Tailwind tokens used in the frontend)
BG_BASE = (11, 15, 26)             # #0B0F1A
BG_PANEL = (17, 24, 39)            # #111827
BORDER_SOFT = (31, 41, 55)         # #1F2937
TEXT_MAIN = (229, 231, 235)        # #E5E7EB
TEXT_DIM = (156, 163, 175)         # #9CA3AF
ACCENT = (245, 158, 11)            # #F59E0B
RISK_HIGH = (234, 88, 12)          # #EA580C
RISK_PROHIBITED = (220, 38, 38)    # #DC2626


def _load_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Try a series of common Windows / fallback fonts."""
    candidates_bold = [
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/calibrib.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/verdanab.ttf",
    ]
    candidates_regular = [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/verdana.ttf",
    ]
    for path in (candidates_bold if bold else candidates_regular):
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    # Final fallback: PIL default bitmap font (only supports size ~11)
    return ImageFont.load_default()


def _measure(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def build(output: Path) -> None:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_BASE)
    draw = ImageDraw.Draw(img)

    # Top + bottom accent stripes
    stripe_h = 14
    draw.rectangle([0, 0, WIDTH, stripe_h], fill=ACCENT)
    draw.rectangle([0, HEIGHT - stripe_h, WIDTH, HEIGHT], fill=BORDER_SOFT)

    # Subtle radial-ish glow simulation: a softer panel band in the centre
    panel_top = 220
    panel_bottom = HEIGHT - 260
    draw.rectangle([0, panel_top, WIDTH, panel_bottom], fill=BG_PANEL)
    draw.rectangle([0, panel_top, WIDTH, panel_top + 2], fill=BORDER_SOFT)
    draw.rectangle([0, panel_bottom - 2, WIDTH, panel_bottom], fill=BORDER_SOFT)

    # Pre-header pill (top-left)
    pill_text = "AI AGENT OLYMPICS  ·  MILAN AI WEEK 2026"
    pill_font = _load_font(28, bold=True)
    pill_w, pill_h = _measure(draw, pill_text, pill_font)
    pill_pad_x, pill_pad_y = 22, 12
    pill_x, pill_y = 80, 90
    draw.rounded_rectangle(
        [pill_x, pill_y, pill_x + pill_w + 2 * pill_pad_x, pill_y + pill_h + 2 * pill_pad_y],
        radius=12,
        fill=BG_PANEL,
        outline=ACCENT,
        width=2,
    )
    draw.text((pill_x + pill_pad_x, pill_y + pill_pad_y), pill_text, font=pill_font, fill=ACCENT)

    # Wordmark — "ComplyForge"
    wordmark = "ComplyForge"
    wordmark_font = _load_font(180, bold=True)
    w_w, w_h = _measure(draw, wordmark, wordmark_font)
    wordmark_x = (WIDTH - w_w) // 2
    wordmark_y = 320
    draw.text((wordmark_x, wordmark_y), wordmark, font=wordmark_font, fill=TEXT_MAIN)

    # Tagline below wordmark
    tagline = "Autonomous EU AI Act Compliance Agent"
    tagline_font = _load_font(54)
    t_w, t_h = _measure(draw, tagline, tagline_font)
    draw.text(((WIDTH - t_w) // 2, wordmark_y + w_h + 30), tagline, font=tagline_font, fill=TEXT_DIM)

    # Three-stat strip near bottom of the panel.
    # Use font metrics (ascent + descent) for proper baseline spacing —
    # textbbox alone misses descender room and the next line overlaps.
    stats = [
        ("75 days", "to Aug 2, 2026", RISK_PROHIBITED),
        ("€35M", "max EU AI Act fine", RISK_HIGH),
        ("60 sec", "Article 11 pipeline", ACCENT),
    ]
    stat_value_font = _load_font(96, bold=True)
    stat_label_font = _load_font(34)
    value_ascent, value_descent = stat_value_font.getmetrics()
    value_line_height = value_ascent + value_descent
    stat_y_top = wordmark_y + w_h + 30 + t_h + 80
    column_width = WIDTH // 3
    for i, (value, label, color) in enumerate(stats):
        col_centre = column_width * i + column_width // 2
        v_w, _v_h = _measure(draw, value, stat_value_font)
        draw.text((col_centre - v_w // 2, stat_y_top), value, font=stat_value_font, fill=color)
        l_w, _l_h = _measure(draw, label, stat_label_font)
        label_y = stat_y_top + value_line_height + 24
        draw.text((col_centre - l_w // 2, label_y), label, font=stat_label_font, fill=TEXT_DIM)

    # Footer line
    footer = "github.com/geniusavinash/ComplyForge  ·  Google Gemini + Veea Lobster Trap  ·  MIT"
    footer_font = _load_font(26)
    f_w, f_h = _measure(draw, footer, footer_font)
    draw.text(((WIDTH - f_w) // 2, HEIGHT - 100), footer, font=footer_font, fill=TEXT_DIM)

    img.save(output, format="PNG", optimize=True)


if __name__ == "__main__":
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    build(OUTPUT)
    size_kb = OUTPUT.stat().st_size / 1024
    print(f"Wrote {OUTPUT.relative_to(ROOT)} ({size_kb:,.1f} KB, {WIDTH}x{HEIGHT})")
