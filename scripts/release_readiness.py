from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path


def _run_step(title: str, command: list[str], *, cwd: Path) -> None:
    print(f"\n==> {title}")
    print(" ".join(command))
    subprocess.run(command, cwd=cwd, check=True)


def _page_title(source: Path) -> str:
    """The document's first Markdown H1, falling back to the file name.

    Keeps rendered pages from being titled by bare filename ("prd"), which is
    what a screen reader announces when the tab or window is focused.
    """
    for line in source.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^#\s+(.+?)\s*$", line)
        if match:
            return match.group(1)
    return source.stem


# Directories under ``docs/`` whose HTML belongs to a different generator.
# ``gen_acceptance_html.py`` and ``gen_signoff_html.py`` each write an
# ``interactive/`` tree of their own; Pandoc must not render into those.
_FOREIGN_HTML_DIRS = frozenset({"interactive"})


def _pandoc_sources(docs_dir: Path) -> list[Path]:
    """Every Markdown file under ``docs/`` that Pandoc owns the rendering of.

    Recursive on purpose. This used to be a non-recursive ``docs/*.md`` glob
    while ``check_docs_artifacts.py`` validated the tree recursively, so the
    nested docs were gated but never rebuilt -- 163 of them sat in the repo
    with no lang attribute, no <main> landmark, and no skip link.

    ``docs/site/`` contains no Markdown at all (it is a separate pipeline) and
    so is naturally excluded.
    """
    return [
        source for source in docs_dir.rglob("*.md") if _FOREIGN_HTML_DIRS.isdisjoint(source.parts)
    ]


def _build_docs(repo_root: Path) -> None:
    pandoc_path = shutil.which("pandoc")
    if pandoc_path is None:
        raise RuntimeError(
            "Pandoc is required for release readiness. "
            "Install with: winget install --id JohnMacFarlane.Pandoc -e"
        )
    # The accessible template adds <html lang="en">, a skip link, and a <main>
    # landmark. Pandoc's default template has none of those, so a missing
    # template is a hard failure rather than a silent downgrade.
    template = repo_root / "docs" / "pandoc" / "quill-accessible.html5"
    if not template.is_file():
        raise RuntimeError(
            f"Accessible pandoc template not found at {template}. Rendering without it "
            "drops <html lang>, the skip link, and the <main> landmark."
        )
    docs_dir = repo_root / "docs"
    for source in sorted(_pandoc_sources(docs_dir)):
        html_out = source.with_suffix(".html")
        epub_out = source.with_suffix(".epub")
        # +smart turns ASCII "--", "..." and straight quotes into real
        # typography. Without it Pandoc slugifies a literal "--" straight into
        # the heading id, changing every anchor and breaking existing deep links.
        _run_step(
            f"Building {html_out.name}",
            [
                pandoc_path,
                str(source),
                "-f",
                "gfm+smart",
                "-t",
                "html5",
                "-s",
                "--template",
                str(template),
                "--metadata",
                f"pagetitle={_page_title(source)}",
                "-o",
                str(html_out),
            ],
            cwd=repo_root,
        )
        _run_step(
            f"Building {epub_out.name}",
            [pandoc_path, str(source), "-f", "gfm+smart", "-t", "epub3", "-o", str(epub_out)],
            cwd=repo_root,
        )


def _require_tool(tool_name: str, *, install_hint: str) -> None:
    if shutil.which(tool_name) is None:
        raise RuntimeError(
            f"{tool_name} is required for release readiness. Install with: {install_hint}"
        )


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    _require_tool("pip-audit", install_hint="python -m pip install pip-audit")

    _run_step(
        "Checking version consistency (GATE-VC)",
        [sys.executable, "-m", "quill.tools.check_version_consistency"],
        cwd=repo_root,
    )
    _run_step("Running lint", ["ruff", "check", "."], cwd=repo_root)
    _run_step("Running dependency audit", ["pip-audit", "--strict"], cwd=repo_root)
    _run_step(
        "Running tests",
        [
            "pytest",
            "tests/unit/",
            "tests/stability/",
            "-q",
            "--ignore=tests/unit/core/test_net_tls.py",
            "--ignore=tests/unit/core/test_thesaurus.py",
        ],
        cwd=repo_root,
    )
    _build_docs(repo_root)
    _run_step(
        "Checking docs artifact parity",
        [sys.executable, "scripts/check_docs_artifacts.py"],
        cwd=repo_root,
    )
    _run_step(
        "Verifying release corpus",
        [sys.executable, "scripts/verify_release_corpus.py"],
        cwd=repo_root,
    )
    print("\nRelease readiness checks completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
