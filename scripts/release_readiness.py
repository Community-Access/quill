from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def _run_step(
    title: str, command: list[str], *, cwd: Path, env: dict[str, str] | None = None
) -> None:
    print(f"\n==> {title}")
    print(" ".join(command))
    subprocess.run(command, cwd=cwd, check=True, env=env)


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


# The repo bundles Pandoc 3.10 (see MIRRORED_PANDOC_URL in
# build_windows_distribution.py) and every committed .html/.epub was rendered
# with it. Older releases stamp a different generator string and differ in
# typography, so rendering with one rewrites every artifact and the docs parity
# gate then reports the churn as a real diff.
MINIMUM_PANDOC = (3, 10)


def _pandoc_version(executable: str) -> tuple[int, ...] | None:
    """The version an executable reports, or ``None`` if it is not usable Pandoc."""
    try:
        result = subprocess.run(
            [executable, "--version"], capture_output=True, text=True, timeout=30
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    match = re.search(r"(\d+(?:\.\d+)+)", result.stdout.splitlines()[0] if result.stdout else "")
    if not match:
        return None
    return tuple(int(part) for part in match.group(1).split("."))


def _pandoc_candidates() -> list[str]:
    """Every plausible Pandoc, PATH first then the standard install locations."""
    candidates: list[str] = []
    seen: set[str] = set()

    def add(path: str | None) -> None:
        if not path:
            return
        resolved = str(Path(path).resolve())
        key = resolved.casefold()
        if key not in seen and Path(resolved).is_file():
            seen.add(key)
            candidates.append(resolved)

    for directory in (os.environ.get("PATH") or "").split(os.pathsep):
        if directory:
            add(shutil.which("pandoc", path=directory))
    for root in (
        os.environ.get("LOCALAPPDATA"),
        os.environ.get("ProgramFiles"),
        os.environ.get("ProgramFiles(x86)"),
    ):
        if root:
            add(str(Path(root) / "Pandoc" / "pandoc.exe"))
    return candidates


def _resolve_pandoc() -> str:
    """The newest usable Pandoc, independent of PATH ordering.

    ``shutil.which`` returns the *first* match on PATH, and PATH order is not
    version order: Windows composes it as machine entries then user entries, so
    an old per-machine install shadows a newer per-user one. Removing the old
    copy needs admin rights a developer may not have, so resolve by version
    instead. ``QUILL_PANDOC`` overrides the search entirely.

    Mirrors Resolve-Pandoc in scripts/DocRender.ps1; keep the two in step.
    """
    minimum_text = ".".join(str(part) for part in MINIMUM_PANDOC)

    override = os.environ.get("QUILL_PANDOC")
    if override:
        if not Path(override).is_file():
            raise RuntimeError(f"QUILL_PANDOC points at {override!r}, which is not a file.")
        version = _pandoc_version(override)
        if version is None:
            raise RuntimeError(
                f"QUILL_PANDOC points at {override!r}, which did not report a Pandoc version."
            )
        if version < MINIMUM_PANDOC:
            found = ".".join(str(part) for part in version)
            raise RuntimeError(
                f"QUILL_PANDOC points at Pandoc {found}, but {minimum_text} or newer is required."
            )
        return override

    found_versions: list[tuple[tuple[int, ...], str]] = []
    for candidate in _pandoc_candidates():
        version = _pandoc_version(candidate)
        if version is not None:
            found_versions.append((version, candidate))
    if not found_versions:
        raise RuntimeError(
            "Pandoc is required for release readiness. "
            "Install with: winget install --id JohnMacFarlane.Pandoc -e"
        )

    best_version, best_path = max(found_versions)
    if best_version < MINIMUM_PANDOC:
        detail = "\n".join(
            f"  {'.'.join(str(part) for part in version)}  {path}"
            for version, path in sorted(found_versions, reverse=True)
        )
        raise RuntimeError(
            f"Pandoc {minimum_text} or newer is required to render docs; the newest found is "
            f"{'.'.join(str(part) for part in best_version)}.\n\nFound:\n{detail}\n\n"
            "Upgrade with: winget install --id JohnMacFarlane.Pandoc -e\n"
            "Or point QUILL_PANDOC at a suitable pandoc.exe."
        )
    if len(found_versions) > 1:
        # PATH order is not version order, so say which one won.
        print(
            f"Using Pandoc {'.'.join(str(part) for part in best_version)} ({best_path}); "
            f"{len(found_versions) - 1} older copy/copies ignored"
        )
    return best_path


# Pandoc stamps a fresh random UUID into dc:identifier and the current wall
# clock into dcterms:modified on every EPUB build, so re-rendering an unchanged
# document still produced different bytes -- all 165 committed .epub files
# showed as modified on every run, leaving the docs parity gate unable to tell
# a real content change from a no-op rebuild. Pinning both makes the output a
# pure function of the source. A fixed epoch (2024-01-01T00:00:00Z) is
# deliberate: any per-run or per-checkout value reintroduces the churn.
# Mirrors QuillSourceDateEpoch in scripts/DocRender.ps1.
EPUB_SOURCE_DATE_EPOCH = "1704067200"


def _epub_identifier(repo_relative: Path) -> str:
    """A stable, URN-safe dc:identifier derived from a document's path.

    Must be unique per document and identical across machines and runs, so it
    is derived from the repo-relative path rather than generated. Paths can
    contain spaces and mixed case ("docs/user guide/userguide.md"), so
    everything outside [a-z0-9] collapses to a single hyphen.

    Mirrors Get-QuillEpubIdentifier in scripts/DocRender.ps1.
    """
    stem = repo_relative.with_suffix("").as_posix()
    slug = re.sub(r"[^A-Za-z0-9]+", "-", stem).strip("-").lower()
    return f"urn:quill:{slug}"


def _build_docs(repo_root: Path) -> None:
    pandoc_path = _resolve_pandoc()
    # Scoped to the Pandoc calls rather than set globally: other tools in a
    # release build also honour SOURCE_DATE_EPOCH, and leaking it would
    # silently change their output too.
    epub_env = {**os.environ, "SOURCE_DATE_EPOCH": EPUB_SOURCE_DATE_EPOCH}
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
            [
                pandoc_path,
                str(source),
                "-f",
                "gfm+smart",
                "-t",
                "epub3",
                "--metadata",
                f"identifier={_epub_identifier(source.relative_to(repo_root))}",
                "-o",
                str(epub_out),
            ],
            cwd=repo_root,
            env=epub_env,
        )


def _require_tool(tool_name: str, *, install_hint: str) -> None:
    if shutil.which(tool_name) is None:
        raise RuntimeError(
            f"{tool_name} is required for release readiness. Install with: {install_hint}"
        )


def _require_module(module: str, *, install_hint: str) -> None:
    """Require *module* in **this** interpreter, not merely somewhere on PATH.

    ``shutil.which("pip-audit")`` finds whichever copy PATH happens to reach
    first, and that is not the interpreter the release is built with. On the
    2026-08-25 readiness run it resolved to a second Python install whose
    packages were months stale, so the audit reported six vulnerable packages
    that the build environment did not have -- and, far worse, would equally
    have stayed silent about a real one in the environment that ships. An audit
    of the wrong environment is not a weaker audit; it is a misleading one.
    """
    if importlib.util.find_spec(module) is None:
        raise RuntimeError(
            f"{module} is required for release readiness, in THIS interpreter "
            f"({sys.executable}) -- the one the release is built with. "
            f"Install with: {install_hint}"
        )


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    _require_module("pip_audit", install_hint=f'"{sys.executable}" -m pip install pip-audit')

    _run_step(
        "Checking version consistency (GATE-VC)",
        [sys.executable, "-m", "quill.tools.check_version_consistency"],
        cwd=repo_root,
    )
    _run_step("Running lint", ["ruff", "check", "."], cwd=repo_root)
    # Two corrections, both made 2026-08-25 readying Quill Radio 3.0.0.
    #
    # ``sys.executable -m pip_audit`` rather than the bare command: audit the
    # interpreter that builds the release (see _require_module for what PATH
    # resolution cost us).
    #
    # And ``repo_root`` as the project path rather than auditing the whole
    # environment. QUILL is developed against a shared system Python that also
    # hosts other projects' privately-published packages, and --strict rightly
    # refuses to pass when a dependency cannot be resolved on PyPI -- so the
    # audit failed on a package that is not QUILL's and never ships with it.
    # Auditing the *project* asks the question the release actually needs
    # answered: are the dependencies QUILL declares known-vulnerable?
    _run_step(
        "Running dependency audit",
        [sys.executable, "-m", "pip_audit", "--strict", str(repo_root)],
        cwd=repo_root,
    )
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
