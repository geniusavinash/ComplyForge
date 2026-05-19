"""One-shot cleanup of internal BUILD_BIBLE / Phase-N references in the repo.

These were authoring shorthand during development and leak the planning
workflow into the published code/docs. This script rewrites them to
neutral, repo-facing language pointing at docs/ARCHITECTURE.md.

Skips: node_modules, .venv, lobstertrap/src (cloned upstream),
BUILD_BIBLE.md (gitignored), generated_pdfs, audit_logs, .git.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SCAN_GLOBS = ("**/*.py", "**/*.md", "**/*.ps1", "**/*.yaml", "**/*.yml")
EXCLUDE_PARTS = {"node_modules", ".venv", "lobstertrap/src", ".git",
                  "generated_pdfs", "audit_logs"}
EXCLUDE_FILE_NAMES = {"BUILD_BIBLE.md", "scrub_build_bible_refs.py"}


# Order matters — longer patterns first so they win over the bare
# BUILD_BIBLE catch-all.
REPLACEMENTS: list[tuple[str, str]] = [
    (r"BUILD_BIBLE Section 0\s*/\s*Phase\s*\d+", "the locked architecture"),
    (r"BUILD_BIBLE Section 3\s*/\s*Phase\s*\d+", "the architecture spec"),
    (r"BUILD_BIBLE Section\s*\d+\s*/\s*Phase\s*\d+", "the architecture spec"),
    (r"BUILD_BIBLE\.md Section\s*\d+", "docs/ARCHITECTURE.md"),
    (r"BUILD_BIBLE\.md", "docs/ARCHITECTURE.md"),
    (r"BUILD_BIBLE Section 0", "the locked architecture"),
    (r"BUILD_BIBLE Phase\s*\d+", "the architecture spec"),
    (r"BUILD_BIBLE plan", "the architecture plan"),
    (r"BUILD_BIBLE assumption", "the initial design assumption"),
    (r"BUILD_BIBLE intent", "the design intent"),
    (r"BUILD_BIBLE-shape", "placeholder-shape"),
    (r"BUILD_BIBLE shape", "the initial design shape"),
    (r"BUILD_BIBLE", "the architecture spec"),
    # Phase-N markers
    (r"Phase 7\s*/\s*Phase 10", "the integration steps"),
    (r"Phase 8\s*/\s*9", "the frontend dashboard build"),
    (r"per Phase\s*\d+", "per the architecture spec"),
    (r"during Phase\s*\d+", "during the integration step"),
    (r"in Phase\s*\d+", "during the build"),
    (r"Phase\s*\d+\s+(brief|deliverable|contract|inspection)", r"upstream \1"),
    (r"See Phase\s*\d+", "See docs/ARCHITECTURE.md"),
    (r"\bPhase\s*\d+\b", "the build step"),
]


def is_excluded(p: Path) -> bool:
    s = p.as_posix()
    if p.name in EXCLUDE_FILE_NAMES:
        return True
    return any(ex in s for ex in EXCLUDE_PARTS)


def collect_files() -> list[Path]:
    seen: set[Path] = set()
    for glob in SCAN_GLOBS:
        for p in ROOT.glob(glob):
            if is_excluded(p) or not p.is_file():
                continue
            seen.add(p.resolve())
    return sorted(seen)


def main() -> int:
    files = collect_files()
    print(f"Scanning {len(files)} files...")
    modified: dict[str, int] = {}
    for fp in files:
        try:
            text = fp.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        new = text
        for pat, repl in REPLACEMENTS:
            new = re.sub(pat, repl, new)
        if new != text:
            fp.write_text(new, encoding="utf-8")
            hits = sum(1 for _ in re.finditer(r"BUILD_BIBLE|Phase\s*\d", text))
            modified[fp.relative_to(ROOT).as_posix()] = hits

    print(f"Modified files: {len(modified)}")
    for rel, hits in modified.items():
        print(f"  {rel}: {hits} legacy markers cleaned")

    # Residual scan — anything still containing BUILD_BIBLE or Phase N?
    residuals: dict[str, list[str]] = {}
    for fp in collect_files():
        try:
            text = fp.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        hits = []
        if "BUILD_BIBLE" in text:
            hits.append("BUILD_BIBLE")
        if re.search(r"\bPhase\s*\d+\b", text):
            hits.append("Phase N")
        if hits:
            residuals[fp.relative_to(ROOT).as_posix()] = hits

    if residuals:
        print("\nResidual references still present (manual review):")
        for rel, hits in residuals.items():
            print(f"  {rel}: {', '.join(hits)}")
    else:
        print("\nNo residual BUILD_BIBLE or Phase-N references remain.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
