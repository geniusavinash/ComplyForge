"""Tests for the PDFGenerator service.

Builds an in-memory TechnicalFile fixture for each of the 4 EU AI Act risk
tiers, renders to a tempfile, and asserts:
  * a file is produced on disk
  * the magic bytes are %PDF-
  * file size > 5 KB
  * for HIGH_RISK we additionally count `/Type /Page` occurrences as a sanity
    check that the document contains multiple pages.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.data.eu_ai_act_taxonomy import ARTICLE_11_SECTIONS
from app.schemas import Article11Section, RiskTier, TechnicalFile
from app.services.pdf_generator import PDFGenerator


def _build_fake_tech_file(tier: RiskTier) -> TechnicalFile:
    sections = [
        Article11Section(
            heading=meta["heading"],
            body=(
                f"This section addresses {meta['heading'].lower()} for the "
                f"{tier.value} fixture in accordance with Article 11 and Annex IV. "
                "Article 9 risk management procedures apply where relevant.\n\n"
                "Body content is illustrative test data used to exercise PDF "
                "rendering. The deployer is expected to supply real numbers and "
                "evidence under Article 15 performance reporting."
            ),
        )
        for meta in ARTICLE_11_SECTIONS
    ]
    fria = (
        "FRIA narrative for the high-risk fixture, citing Article 27 and "
        "Article 14 oversight measures."
        if tier == RiskTier.HIGH_RISK
        else "FRIA not required at this tier; see Article 27 scope."
    )
    return TechnicalFile(
        agent_name=f"TestAgent-{tier.value}",
        risk_tier=tier,
        generated_at=datetime(2026, 5, 17, 12, 0, tzinfo=timezone.utc),
        sections=sections,
        fria_summary=fria,
        datasheet={
            "model_provider": "TestVendor",
            "intended_use": "Unit testing PDF rendering",
            "training_data_summary": "Synthetic data only",
            "performance_metrics": "n/a (test fixture)",
            "known_limitations": "Test scope only",
            "human_oversight": "Article 14 oversight by reviewer",
            "contact": "test@example.com",
        },
    )


def _read_magic(path) -> bytes:
    with open(path, "rb") as fh:
        return fh.read(5)


def test_render_produces_pdf_above_5kb(tmp_path) -> None:
    tf = _build_fake_tech_file(RiskTier.HIGH_RISK)
    out = tmp_path / "out.pdf"
    result = PDFGenerator().render_technical_file(tf, str(out))
    assert result == str(out)
    assert out.exists()
    assert out.stat().st_size > 5_000, f"PDF too small: {out.stat().st_size} bytes"
    assert _read_magic(out) == b"%PDF-"


@pytest.mark.parametrize("tier", list(RiskTier))
def test_render_supports_all_four_risk_tiers(tier: RiskTier, tmp_path) -> None:
    tf = _build_fake_tech_file(tier)
    out = tmp_path / f"{tier.value}.pdf"
    PDFGenerator().render_technical_file(tf, str(out))
    assert out.exists(), f"PDF for {tier.value} not written"
    assert out.stat().st_size > 5_000, (
        f"PDF for {tier.value} only {out.stat().st_size} bytes"
    )
    assert _read_magic(out) == b"%PDF-", (
        f"PDF for {tier.value} missing magic bytes"
    )


def test_render_writes_into_nested_directory(tmp_path) -> None:
    tf = _build_fake_tech_file(RiskTier.LIMITED_RISK)
    out = tmp_path / "nested" / "deep" / "limited.pdf"
    PDFGenerator().render_technical_file(tf, str(out))
    assert out.exists()
    assert _read_magic(out) == b"%PDF-"


def test_high_risk_pdf_contains_multiple_pages(tmp_path) -> None:
    """Sanity check page count via the /Type /Page marker in PDF content."""
    tf = _build_fake_tech_file(RiskTier.HIGH_RISK)
    out = tmp_path / "high.pdf"
    PDFGenerator().render_technical_file(tf, str(out))
    raw = out.read_bytes()
    page_markers = raw.count(b"/Type /Page\n") + raw.count(b"/Type /Page ")
    # 1 cover + 1 TOC + 9 sections + 1 FRIA + 1 datasheet = 13 logical pages.
    # Allow some slack — paragraphs may overflow onto extra pages.
    assert page_markers >= 10, (
        f"Expected >= 10 page markers in HIGH_RISK PDF, found {page_markers}"
    )
