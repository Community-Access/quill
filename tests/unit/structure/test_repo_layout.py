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

# The only Markdown files sanctioned to live at the repository root. Everything
# else — community/governance docs (docs/), legal docs (docs/legal/), the release
# checklist (docs/release/), the manual dialog-regression checklist
# (docs/qa/dialogs.md), design notes, research, and planning — lives under docs/
# so the root stays scannable at a glance. CHANGELOG.md stays at the root because
# release tooling (check_version_consistency, extract_release_body,
# build_windows_distribution) and packaging convention read it there; CLAUDE.md
# is pinned to the root by Claude Code; README.md is the repository front page.
_SANCTIONED_ROOT_MARKDOWN = frozenset({
    "CHANGELOG.md",
    "CLAUDE.md",
    "README.md",
})


def _gitignored_root_files(names: set[str]) -> set[str]:
    """Root file names that ``.gitignore`` excludes from the committed tree.

    The layout gate governs the *committed* repository root, so a file the repo
    intentionally ignores (e.g. a local, untracked working note) is not a layout
    regression. Dependency-free: matches a present root file against the exact,
    non-glob ignore patterns in the top-level ``.gitignore`` (with or without a
    leading slash), which is all the root-file ignores this gate needs.
    """
    gitignore = _REPO_ROOT / ".gitignore"
    if not gitignore.exists():
        return set()
    patterns: set[str] = set()
    for raw in gitignore.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or any(ch in line for ch in "*?[]"):
            continue
        patterns.add(line.lstrip("/"))
    return {name for name in names if name in patterns}


def test_repository_root_has_no_loose_python_modules() -> None:
    present = {path.name for path in _REPO_ROOT.glob("*.py")}
    stray = sorted(present - _gitignored_root_files(present))
    assert stray == [], (
        "The repository root must stay free of loose Python modules: importable "
        "source belongs under quill/, build tooling under scripts/, and tests "
        f"under tests/. Found stray root modules: {stray}"
    )


def test_repository_root_markdown_is_limited_to_sanctioned_files() -> None:
    present = {path.name for path in _REPO_ROOT.glob("*.md")}
    stray = sorted(present - _SANCTIONED_ROOT_MARKDOWN - _gitignored_root_files(present))
    assert stray == [], (
        "Only conventional root Markdown files are allowed at the repository "
        "root; design, research, and planning notes belong under docs/ "
        "(planning material now lives in the QUILL-PRD, the user guide, and "
        f"the release notes since the 0.7.0 release scope). Found unsanctioned "
        f"root Markdown: {stray}"
    )


def test_docs_are_in_their_expected_homes() -> None:
    # Core docs are organized into topic subdirectories. Guard that the key
    # files exist in their canonical locations and that old standalone files
    # that were folded into larger documents have not crept back.
    docs = _REPO_ROOT / "docs"
    # Community/governance docs live at the top of docs/ (a GitHub-recognized
    # home for CONTRIBUTING/CODE_OF_CONDUCT/SECURITY), legal docs under
    # docs/legal/, the release checklist under docs/release/, and the manual
    # dialog-regression checklist under docs/qa/.
    for rel in (
        "CODE_OF_CONDUCT.md",
        "CONTRIBUTING.md",
        "GOVERNANCE.md",
        "MAINTAINERS.md",
        "SECURITY.md",
        "legal/PRIVACY.md",
        "legal/RESPONSIBLE_AI_USE.md",
        "legal/TRADEMARKS.md",
        "legal/THIRD_PARTY_NOTICES.md",
        "release/RELEASE.md",
        "qa/dialogs.md",
    ):
        assert (docs / rel).is_file(), f"missing docs/{rel}"
    # Quillin scripting contract lives under docs/quillins/ alongside generated epub/html.
    assert (docs / "quillins" / "quillins.md").is_file(), "missing docs/quillins/quillins.md"
    # docs/planning/ is retained as the home for active planning, backlog, and
    # naming/branding material (roadmap, feature/braille backlogs, the consolidated
    # 1.0 tracker, the TINDRA naming plan, ...). The earlier 0.7.0 "merge then
    # delete the planning folder" scope was superseded by keeping it as a living
    # home for in-flight planning, so guard that the folder and its anchor file
    # exist rather than forbidding them.
    planning = docs / "planning"
    assert planning.is_dir(), "missing docs/planning/ (the home for planning docs)"
    assert (planning / "roadmap.md").is_file(), "missing docs/planning/roadmap.md"
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
