"""Structural guards for the repository tree (ORG-1).

These tests encode the "best-in-class repository tree" invariant: a new
contributor should be able to navigate the layout at a glance. Source lives
under ``quill/``, build tooling under ``scripts/``, internal helpers under
``tools/``, and tests under ``tests/`` — never as loose modules in the
repository root. The guards fail loudly if a stray module reappears at the root
so the cleanup cannot silently regress.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]

# The only Markdown files sanctioned to live at the repository root: conventional
# community/governance/legal files plus the two master regression/usability plans
# that copilot-instructions pins to the root — dialogs.md (the manual
# dialog-regression checklist) and menus.md (the definitive menu-reorganization
# plan). Every other Markdown document — design notes, research, planning
# (including ROADMAP.md), and engineering — lives under docs/ so the root stays
# scannable at a glance.
_SANCTIONED_ROOT_MARKDOWN = frozenset({
    "CHANGELOG.md",
    "CLAUDE.md",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "GOVERNANCE.md",
    "MAINTAINERS.md",
    "PRIVACY.md",
    "README.md",
    "RELEASE.md",
    "RESPONSIBLE_AI_USE.md",
    "SECURITY.md",
    "THIRD_PARTY_NOTICES.md",
    "ai.md",
    "dialogs.md",
    "issues.md",
    "menus.md",
    "rel.md",
    "report.md",
    "x2.md",
    "x3.md",
})


def test_repository_root_has_no_loose_python_modules() -> None:
    stray = sorted(path.name for path in _REPO_ROOT.glob("*.py"))
    assert stray == [], (
        "The repository root must stay free of loose Python modules: importable "
        "source belongs under quill/, build tooling under scripts/, and tests "
        f"under tests/. Found stray root modules: {stray}"
    )


def test_repository_root_markdown_is_limited_to_sanctioned_files() -> None:
    present = {path.name for path in _REPO_ROOT.glob("*.md")}
    stray = sorted(present - _SANCTIONED_ROOT_MARKDOWN)
    assert stray == [], (
        "Only conventional root Markdown files are allowed at the repository "
        "root; design, research, and planning notes belong under docs/ (for "
        f"example docs/planning/). Found unsanctioned root Markdown: {stray}"
    )


def test_docs_are_in_their_expected_homes() -> None:
    # Core docs are organized into topic subdirectories. Guard that the key
    # files exist in their canonical locations and that old standalone files
    # that were folded into larger documents have not crept back.
    docs = _REPO_ROOT / "docs"
    # Quillin scripting contract lives under docs/quillins/ alongside generated epub/html.
    assert (docs / "quillins" / "quillins.md").is_file(), "missing docs/quillins/quillins.md"
    # Planning roadmap and braille docs live under docs/planning/
    assert (docs / "planning" / "planning.md").is_file(), "missing docs/planning/planning.md"
    assert (docs / "planning" / "braille.md").is_file(), "missing docs/planning/braille.md"
    # User guide lives under docs/user guide/
    assert (docs / "user guide" / "userguide.md").is_file(), "missing docs/user guide/userguide.md"
    # PRD lives under docs/Product Requirement Documents and Specifications/
    prd_dir = docs / "Product Requirement Documents and Specifications"
    assert (prd_dir / "QUILL-PRD.md").is_file(), "missing QUILL-PRD.md in PRD dir"
    # These old standalone docs were folded into userguide.md / QUILL-PRD.md
    # and must not reappear at the docs root.
    for gone in (
        "engineering.md",
        "qa.md",
        "deployment.md",
        "features.md",
        "developer-console.md",
        "skills-tutorial.md",
        "rtf.md",
        "ACCESSIBLEAPPS_INTEGRATION.md",
    ):
        assert not (docs / gone).is_file(), f"docs/{gone} should have been consolidated"


def test_macos_build_files_live_in_sanctioned_homes() -> None:
    # The py2app entry point is genuine platform source and lives in the macOS
    # platform package; the py2app build configuration is build tooling and
    # lives in scripts/ alongside build_macos.sh (deliberately outside the
    # bundled `quill` package so it is never packed into the .app).
    assert (_REPO_ROOT / "quill" / "platform" / "macos" / "macos_app.py").is_file()
    assert (_REPO_ROOT / "scripts" / "setup_macos.py").is_file()
