"""Fail a runtime build whose swept contents differ from the declared inventory.

``check_build_env.py`` guards the *floor*: every ``[runtime]`` requirement must
be importable before PyInstaller runs. It cannot see the *ceiling*: PyInstaller's
``Analysis`` follows every optional import quill makes, so any extra package
that happens to be importable on the build machine ships silently. That is not
hypothetical -- the 2026-08-15 Quill Radio installers carried 81.8 MB of
undeclared payload (pymupdf, a second OpenBLAS, pydantic, curl_cffi, pyphen,
winrt, even hypothesis) swept from one machine's site-packages, and the next
build on a leaner machine shipped 31 MB smaller with no code change. The only
symptom was the size difference; both builds exited 0. In the other direction,
Windows OCR (the winrt-* packages) shipped in the 2026-08-09 release and then
silently vanished from the next one the same way.

This gate compares the built dist against a checked-in inventory of top-level
names, so either direction of drift -- a package appearing or vanishing --
fails the build naming exactly what changed.

Usage::

    python scripts/check_runtime_inventory.py <dist-dir>
    python scripts/check_runtime_inventory.py <dist-dir> --write   # rebaseline

The inventory records *names*, not versions or hashes: a routine dependency bump
does not churn it, but a new top-level package (or a lost one) is a build
failure until someone either uninstalls the stray or declares the intent by
rebaselining with ``--write`` -- the same ratchet shape as the module size
budget (GATE-11).

Exits non-zero listing every unexpected and missing entry.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_MANIFEST = _REPO_ROOT / "standalone" / "runtime" / "runtime-inventory.json"

#: ``name-1.2.3.dist-info`` -> ``name``; case folded elsewhere.
_DIST_INFO = re.compile(r"^(?P<name>.+?)-[0-9][^-]*\.dist-info$", re.IGNORECASE)

#: ``_brotli.cp313-win_amd64.pyd`` -> ``_brotli``; ``python313.dll`` stays
#: itself. Interpreter tags churn with Python upgrades and must not.
_EXT_TAG = re.compile(r"\.cp3\d+[^.]*\.(pyd|dll)$", re.IGNORECASE)


def normalize(name: str) -> str:
    """One top-level dist entry to its stable, version-free identity."""
    match = _DIST_INFO.match(name)
    if match:
        return match.group("name").casefold().replace("_", "-")
    return _EXT_TAG.sub("", name).casefold()


#: Layouts: which top-level areas each artifact family sweeps content into.
#: "runtime" is the PyInstaller onedir; "portable" is the embeddable-Python
#: bundle (build_portable.py), whose sweep surfaces are the pip site-packages
#: and the copied quill source tree's data dir (P1.2).
_LAYOUTS: dict[str, tuple[tuple[str, str], ...]] = {
    "runtime": (("root", "."), ("_internal", "_internal"), ("tools", "tools")),
    "portable": (
        ("root", "."),
        ("site-packages", "Lib/site-packages"),
        ("quill-data", "Lib/site-packages/quill/data"),
        ("tools", "tools"),
    ),
}


def inventory(dist_dir: Path, layout: str = "runtime") -> dict[str, list[str]]:
    """The dist's top-level names, normalized, per area of *layout*.

    Deeper paths are deliberately out of scope: version bumps churn them
    constantly and the failure mode this gate exists for (a whole package
    appearing or vanishing) is visible at the top.
    """
    areas: dict[str, list[str]] = {}
    for area, rel in _LAYOUTS[layout]:
        base = dist_dir if rel == "." else dist_dir / rel
        if not base.is_dir():
            areas[area] = []
            continue
        nested = {r.split("/", 1)[0] for _a, r in _LAYOUTS[layout] if r != "."}
        names = {normalize(e.name) for e in base.iterdir() if e.name not in nested}
        areas[area] = sorted(names)
    return areas


def duplicate_dist_infos(packages_dir: Path) -> list[str]:
    """Package names present as more than one ``*.dist-info`` version, in the
    given packages directory (``_internal`` or ``Lib/site-packages``).

    Two dist-infos normalize to one inventory entry, so the set comparison
    cannot see them -- but a doubled package doubles its native libraries (the
    2026-08-15 payload carried OpenBLAS twice via numpy 2.5.1 *and* 2.5.2).
    """
    if not packages_dir.is_dir():
        return []
    seen: dict[str, int] = {}
    for entry in packages_dir.iterdir():
        match = _DIST_INFO.match(entry.name)
        if match:
            key = match.group("name").casefold().replace("_", "-")
            seen[key] = seen.get(key, 0) + 1
    return sorted(name for name, count in seen.items() if count > 1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("dist_dir", type=Path, help="the built dist directory")
    parser.add_argument("--manifest", type=Path, default=_DEFAULT_MANIFEST)
    parser.add_argument(
        "--layout",
        choices=sorted(_LAYOUTS),
        default="runtime",
        help="which artifact family's sweep surfaces to inventory",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="rebaseline: record the current dist as the declared inventory",
    )
    args = parser.parse_args()

    dist_dir = args.dist_dir.resolve()
    anchor = "QuillVilleRuntime.exe" if args.layout == "runtime" else "pythonw.exe"
    if not (dist_dir / anchor).is_file():
        print(f"Not a {args.layout} dist (no {anchor}): {dist_dir}", file=sys.stderr)
        return 2

    current = inventory(dist_dir, args.layout)
    packages = dist_dir / ("_internal" if args.layout == "runtime" else "Lib/site-packages")
    doubled = duplicate_dist_infos(packages)
    if doubled:
        print("Packages present at more than one version (each ships its libraries twice):")
        for name in doubled:
            print(f"  duplicated: {name}")
        if not args.write:
            return 1

    if args.write:
        record: dict[str, list[str]] = dict(current)
        if args.manifest.is_file():
            # A rebaseline refreshes what the build produced; the optional list
            # is hand-curated policy and survives it.
            previous = json.loads(args.manifest.read_text(encoding="utf-8"))
            optional = set(previous.get("optional", []))
            if optional:
                record = {
                    area: [name for name in names if name not in optional]
                    for area, names in current.items()
                }
                record["optional"] = sorted(optional)
        args.manifest.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        print(f"Inventory written: {args.manifest}")
        return 0

    if not args.manifest.is_file():
        print(
            f"No inventory at {args.manifest}. Generate one from a verified-good build:\n"
            f"  python scripts/check_runtime_inventory.py {dist_dir} --write",
            file=sys.stderr,
        )
        return 2

    declared = json.loads(args.manifest.read_text(encoding="utf-8"))
    # Allowed-but-not-required, in any area: the OptiLab adapter is staged by
    # the app build script and only when a C++ toolchain exists ("best-effort"
    # by design), so neither its presence nor its absence is drift.
    optional = set(declared.get("optional", []))
    failures = 0
    for area, _rel in _LAYOUTS[args.layout]:
        have = set(current.get(area, []))
        want = set(declared.get(area, [])) - optional
        for name in sorted(have - want - optional):
            print(f"  unexpected in {area}: {name} (swept from this machine; not declared)")
            failures += 1
        for name in sorted(want - have):
            print(f"  missing from {area}: {name} (declared, but this build did not produce it)")
            failures += 1

    if failures:
        print(
            f"\nRuntime inventory drift: {failures} difference(s) against {args.manifest.name}.\n"
            "An unexpected package: uninstall it from the build interpreter, or declare it\n"
            "in pyproject and rebaseline with --write. A missing package: install what\n"
            "[runtime] expects (scripts/check_build_env.py names it), or rebaseline if the\n"
            "removal is intentional."
        )
        return 1
    print(f"Runtime inventory matches {args.manifest.name}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
