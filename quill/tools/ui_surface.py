"""Public-surface extraction for the main_frame characterization gate (GATE-6).

``quill/ui/main_frame.py`` is a large module slated for decomposition. To make
that refactor behavior-preserving, the characterization gate snapshots the
public method surface of the ``MainFrame`` class and fails when it changes
unexpectedly. This module extracts that surface from source via AST, so it needs
neither ``wx`` nor a running UI.

When a refactor deliberately changes the surface (a method moves to a new
collaborator, is renamed, or is intentionally removed), regenerate the committed
snapshot with::

    python -m quill.tools.ui_surface --write

and review the diff as part of the change.
"""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MAIN_FRAME = _REPO_ROOT / "quill" / "ui" / "main_frame.py"
SNAPSHOT_PATH = _REPO_ROOT / "tests" / "unit" / "ui" / "fixtures" / "main_frame_public_surface.json"
_UI_ROOT = _REPO_ROOT / "quill" / "ui"


def _ui_class_index() -> dict[str, ast.ClassDef]:
    index: dict[str, ast.ClassDef] = {}
    for path in sorted(_UI_ROOT.glob("main_frame*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                index[node.name] = node
    return index


def _public_methods_for_class(
    class_name: str,
    index: dict[str, ast.ClassDef],
    seen: set[str] | None = None,
) -> set[str]:
    seen = seen or set()
    if class_name in seen or class_name not in index:
        return set()
    seen.add(class_name)
    class_def = index[class_name]
    names = {
        member.name
        for member in class_def.body
        if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not member.name.startswith("_")
    }
    for base in class_def.bases:
        if isinstance(base, ast.Name):
            names.update(_public_methods_for_class(base.id, index, seen))
    return names


def main_frame_public_methods(source_path: Path = _MAIN_FRAME) -> list[str]:
    """Return the sorted public (non-underscore) method names of ``MainFrame``."""
    del source_path  # MainFrame now spans the main module plus extracted mixins.
    index = _ui_class_index()
    return sorted(_public_methods_for_class("MainFrame", index))


def load_snapshot() -> list[str]:
    return list(json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8")))


def write_snapshot() -> list[str]:
    methods = main_frame_public_methods()
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_PATH.write_text(json.dumps(methods, indent=2) + "\n", encoding="utf-8")
    return methods


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate the committed public-surface snapshot.",
    )
    args = parser.parse_args()
    if args.write:
        methods = write_snapshot()
        print(f"Wrote {len(methods)} public methods to {SNAPSHOT_PATH}")
    else:
        methods = main_frame_public_methods()
        print(f"MainFrame exposes {len(methods)} public methods.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
