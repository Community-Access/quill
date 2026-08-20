"""Attribute a built shared runtime to app layers, and name what nobody owns.

WHY THIS EXISTS
---------------
``check_runtime_inventory.py`` answers "did anything appear or vanish?" against
a flat list of names. It cannot answer the question the layering plan turns on:
*who can actually use this, and what does it weigh?* Until something measures
that, "the shared runtime is the union of every app's dependencies" stays a
sentence in a spec file rather than a number anybody can act on.

This reads ``standalone/runtime/app-profiles.json`` -- the same declaration
``tests/unit/structure/test_app_profiles.py`` enforces -- walks a built
``_internal`` for real byte sizes, and prints three groups:

* **core** -- everything every app can call.
* **each layer** -- packages one app owns, with the megabytes every *other* app
  installs anyway.
* **unattributed** -- the interesting column. These are packages nobody has
  decided about: not proven shared, not claimed by a layer. Stage 3 cannot be
  scoped while this list is large, and shrinking it is the cheapest work in the
  whole plan.

It measures; it does not judge. Nothing here fails a build. Turning the layer
split into a gate is Stage 4, and doing it before the unattributed list is
empty would just gate a guess.

WHY NOT ``scripts/footprint_report.py``
---------------------------------------
That one measures AI model and engine footprint (PRD 5.25f) -- a different
subject with a different output contract. Sharing a name would make one of them
lie about what it covers.

Usage::

    python scripts/runtime_layer_report.py <dist-dir>
    python scripts/runtime_layer_report.py <dist-dir> --json <path>

*dist-dir* is a built ``standalone/runtime/dist/QuillVilleRuntime``. Read-only:
it walks the tree and touches nothing.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PROFILES = _REPO_ROOT / "standalone" / "runtime" / "app-profiles.json"

# The normalizer from the inventory gate, imported rather than re-implemented:
# two tools that disagree about what a top-level name *is* would report two
# different runtimes for the same directory.
sys.path.insert(0, str(_REPO_ROOT / "scripts"))
from check_runtime_inventory import normalize  # noqa: E402


def tree_size(path: Path) -> int:
    """Real bytes under *path*. ``du`` rounds every file to a block and
    overstates a tree of small ``.py`` files by hundreds of megabytes."""
    if path.is_file():
        return path.stat().st_size
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:  # a file that vanished mid-walk is not a measurement
                continue
    return total


def measure(internal: Path) -> dict[str, int]:
    """``normalized top-level name -> bytes`` for a built ``_internal``.

    Sizes are summed per normalized name, so ``numpy`` and ``numpy-2.5.1.dist-info``
    land together rather than as two rows that look like two packages.
    """
    sizes: dict[str, int] = {}
    for entry in internal.iterdir():
        key = normalize(entry.name)
        sizes[key] = sizes.get(key, 0) + tree_size(entry)
    return sizes


#: Names that are the runtime itself rather than a package: the interpreter, the
#: C runtime, the frozen stdlib archive, and the application code every app runs.
#: Declared here rather than in the profile file because they are not anybody's
#: dependency -- they are the floor.
_ALWAYS_CORE = frozenset({
    "quill",
    "base_library.zip",
    "python3.dll",
    "python313.dll",
    "msvcp140.dll",
    "vcruntime140.dll",
    "vcruntime140_1.dll",
})


def _is_stdlib_extension(name: str) -> bool:
    """True for a CPython extension module frozen out of the stdlib.

    ``normalize`` strips the interpreter tag from a third-party extension
    (``_brotli.cp313-win_amd64.pyd`` -> ``_brotli``), so a name that still ends
    in ``.pyd`` after normalizing carried no tag -- which is what the stdlib's
    own ``_asyncio.pyd``, ``select.pyd``, ``winsound.pyd`` and their two dozen
    siblings look like. They are the interpreter, not anybody's dependency, and
    listing all of them by hand in ``_ALWAYS_CORE`` would be a list that goes
    stale with every Python upgrade.
    """
    return name.endswith(".pyd")


def attribute(sizes: dict[str, int], profiles: dict) -> dict:
    """Split *sizes* into core, per-layer, and unattributed."""
    owners: dict[str, str] = {}
    # A trailing "*" matches by prefix. PyInstaller renames bundled DLLs with a
    # content hash -- ``libheif-0840364bf533381e2055ff41f7009c9b.dll`` -- which
    # changes on every rebuild of the library, so an exact name here would
    # quietly stop matching and the package would drift back into
    # "unattributed" with nobody the wiser.
    prefixes: list[tuple[str, str]] = []
    for layer, spec in profiles["layers"].items():
        for package in spec["packages"]:
            if package.endswith("*"):
                prefixes.append((normalize(package[:-1]), layer))
            else:
                owners[normalize(package)] = layer

    def owner_of(name: str) -> str | None:
        if name in owners:
            return owners[name]
        for prefix, layer in prefixes:
            if name.startswith(prefix):
                return layer
        return None

    layers: dict[str, dict[str, int]] = {name: {} for name in profiles["layers"]}
    core: dict[str, int] = {}
    unattributed: dict[str, int] = {}
    for name, size in sizes.items():
        layer = owner_of(name)
        if name in _ALWAYS_CORE or _is_stdlib_extension(name):
            core[name] = size
        elif layer is not None:
            layers[layer][name] = size
        else:
            unattributed[name] = size
    return {"core": core, "layers": layers, "unattributed": unattributed}


def _mb(value: int) -> str:
    return f"{value / 1e6:.1f} MB"


def render(split: dict, profiles: dict, total: int) -> str:
    """The report, in plain ASCII a screen reader reads cleanly."""
    lines: list[str] = []
    core = sum(split["core"].values())
    unowned = sum(split["unattributed"].values())
    layer_totals = {name: sum(items.values()) for name, items in split["layers"].items()}

    lines.append(f"Shared runtime Python payload: {_mb(total)}")
    lines.append("")
    lines.append(f"  runtime floor (interpreter + quill):  {_mb(core)}")
    for name, amount in sorted(layer_totals.items(), key=lambda pair: -pair[1]):
        owner = profiles["layers"][name]["owner"]
        others = sorted(app for app in profiles["apps"] if app != owner)
        lines.append(
            f"  layer {name} (owned by {owner}):  {_mb(amount)}"
            f"  -- installed by {len(others)} app(s) that cannot call it"
        )
    lines.append(f"  unattributed:  {_mb(unowned)}")
    lines.append("")

    attributed = core + sum(layer_totals.values())
    share = (attributed / total * 100) if total else 0.0
    lines.append(f"Attributed: {share:.1f}% of the payload.")
    layered = sum(layer_totals.values())
    if total:
        lines.append(
            f"Layerable today: {_mb(layered)} ({layered / total * 100:.1f}%) -- what every"
            " app but one installs and cannot reach."
        )
    lines.append("")

    for name, items in split["layers"].items():
        if not items:
            continue
        lines.append(f"Layer {name}:")
        for package, size in sorted(items.items(), key=lambda pair: -pair[1]):
            lines.append(f"  {_mb(size):>10}  {package}")
        lines.append("")

    lines.append("Unattributed (nobody has decided about these):")
    for package, size in sorted(split["unattributed"].items(), key=lambda pair: -pair[1]):
        lines.append(f"  {_mb(size):>10}  {package}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("dist", type=Path, help="a built dist/QuillVilleRuntime directory")
    parser.add_argument("--json", type=Path, default=None, help="also write the raw split here")
    parser.add_argument("--profiles", type=Path, default=_PROFILES)
    args = parser.parse_args()

    internal = args.dist.resolve() / "_internal"
    if not internal.is_dir():
        print(f"No _internal directory in {args.dist}", file=sys.stderr)
        return 2

    profiles = json.loads(args.profiles.read_text(encoding="utf-8"))
    sizes = measure(internal)
    split = attribute(sizes, profiles)
    total = sum(sizes.values())
    print(render(split, profiles, total))

    if args.json:
        args.json.write_text(
            json.dumps({"total_bytes": total, **split}, indent=2) + "\n", encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
