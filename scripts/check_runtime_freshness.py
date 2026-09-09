"""Fail a build whose shared runtime carries an older copy of the quill package.

The QuillVille Runtime is a PyInstaller onedir with its **own frozen copy of
the whole quill package**, and every app installer ships it. ``build_runtime``
freezes whatever the source tree said at the moment it ran, and every app build
may reuse that dist with ``-SkipSharedRuntime`` -- so the code an installer
actually ships is the code of the last runtime build, not of the checkout the
installer was compiled from.

``Assert-QuillRuntimeHasModule`` (scripts/BuildEnv.ps1) was written for the
sharp end of this: a runtime built before an app existed does not contain that
app, and the installer compiles, installs, and fails on first launch. But it
asks whether a module is *present*, and present is not current. On 2026-09-08 a
runtime about to be published contained ``quill/apps/lite.py`` and passed that
assertion, while the frozen tree was 28 files behind the checkout and missing
``lite_check.py`` and ``lite_window_selection.py`` altogether. Nothing else in
the build could see it: the inventory gate compares top-level *names*, the
import gate imports modules that were happily importable in their old form, and
ISCC compiles whatever it is handed.

This gate compares the frozen ``_internal/quill`` tree against the checkout's
``quill/`` tree, file by file, and names every difference:

* **stale** -- present in both, contents differ. The module the build thinks it
  is shipping is not the module it is shipping.
* **missing** -- in the checkout, absent from the frozen tree. A module written
  after the runtime was built.
* **orphan** -- in the frozen tree, gone from the checkout. A module deleted
  after the runtime was built, still shipping.

Usage::

    python scripts/check_runtime_freshness.py <runtime-dist-dir>
    python scripts/check_runtime_freshness.py <dist> --source-root <checkout>

Only ``.py`` files are compared. Data files (catalogues, JSON fixtures, icons)
churn on their own schedule and are inventoried elsewhere; the question here is
whether the *code* is the code. Exits non-zero listing every difference; the
fix is always the same and is never a rebaseline -- rebuild the runtime.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]

#: Path segments whose contents are never evidence of staleness.
#:
#: ``__pycache__``/``.mypy_cache`` are machine-local build products of the
#: checkout, not source. ``build`` covers the CMake trees under
#: ``quill/native``, which are compiler output and are never frozen.
_SKIP_SEGMENTS = frozenset({"__pycache__", ".mypy_cache", "build"})

#: Files excluded by name, each for a stated reason.
#:
#: ``_feedback_token.py`` is written into the checkout by the build itself
#: (tools/generate_feedback_token.py) immediately before packaging, so a runtime
#: reused from an earlier build legitimately carries the previous write. It is
#: gitignored, machine-specific, and carries no app behaviour.
_SKIP_NAMES = frozenset({"_feedback_token.py"})


@dataclass(frozen=True, slots=True)
class Finding:
    """One difference between the frozen tree and the checkout."""

    kind: str  # "stale" | "missing" | "orphan"
    relative: str  # posix path under quill/


def _sources(root: Path) -> dict[str, Path]:
    """Every comparable ``.py`` under *root*, keyed by its posix path from it."""
    if not root.is_dir():
        return {}
    found: dict[str, Path] = {}
    for path in root.rglob("*.py"):
        relative = path.relative_to(root)
        if _SKIP_SEGMENTS.intersection(relative.parts):
            continue
        if path.name in _SKIP_NAMES:
            continue
        found[relative.as_posix()] = path
    return found


def compare(dist_dir: Path, source_root: Path) -> list[Finding]:
    """Every way the runtime's frozen quill package differs from the checkout's.

    Ordered stale-first: a module that is present but wrong is the finding a
    reader most needs, because it is the one no other gate can see.
    """
    frozen = _sources(dist_dir / "_internal" / "quill")
    current = _sources(source_root / "quill")

    stale: list[Finding] = []
    missing: list[Finding] = []
    for relative, path in sorted(current.items()):
        other = frozen.get(relative)
        if other is None:
            missing.append(Finding("missing", relative))
        elif other.read_bytes() != path.read_bytes():
            stale.append(Finding("stale", relative))
    orphans = [Finding("orphan", r) for r in sorted(set(frozen) - set(current))]
    return stale + missing + orphans


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("dist_dir", type=Path, help="the built runtime dist directory")
    parser.add_argument(
        "--source-root",
        type=Path,
        default=_REPO_ROOT,
        help="the checkout whose quill/ the frozen tree must match (default: this repo)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="how many differences to list before summarising the rest",
    )
    args = parser.parse_args(argv)

    dist_dir = args.dist_dir.resolve()
    if not (dist_dir / "QuillVilleRuntime.exe").is_file():
        print(f"Not a runtime dist (no QuillVilleRuntime.exe): {dist_dir}", file=sys.stderr)
        return 2

    findings = compare(dist_dir, args.source_root.resolve())
    if not findings:
        print("Runtime freshness: the frozen quill package matches the checkout.")
        return 0

    for finding in findings[: args.limit]:
        print(f"  {finding.kind}: quill/{finding.relative}")
    if len(findings) > args.limit:
        print(f"  ... and {len(findings) - args.limit} more")
    kinds = ("stale", "missing", "orphan")
    counts = {kind: sum(1 for f in findings if f.kind == kind) for kind in kinds}
    print(
        f"\nRuntime is not built from this checkout: "
        f"{counts['stale']} stale, {counts['missing']} missing, {counts['orphan']} orphaned.\n"
        "The runtime carries its own frozen copy of the quill package, so this build\n"
        "would ship that older code no matter what the checkout says. Rebuild it\n"
        "(standalone\\runtime\\build_runtime.ps1) or drop -SkipSharedRuntime.\n"
        "There is no rebaseline for this one -- the answer is always to rebuild."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
