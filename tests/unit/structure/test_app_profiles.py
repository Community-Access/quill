"""Every shipped app declares what it needs, and the declaration cannot drift.

``standalone/runtime/app-profiles.json`` is the first place in the repository
that says, in a form something can check, which app requires what. Before it,
``REQUIRED_COMPONENTS`` in each app module declared external tools and *nothing
at all* declared Python dependencies per app -- so the shared runtime could ship
a PDF renderer, an image library and a spell checker to a weather app, and no
build, gate or test could notice.

These are the checks that keep the file honest:

* a shipped entry point with no row is a new app nobody declared;
* a row naming a module that does not exist is a rename nobody finished;
* a row whose ``components`` disagree with the module's own
  ``REQUIRED_COMPONENTS`` is the two halves drifting, which is exactly the
  "profile duplication" risk that makes declarations worthless.

``layers`` is deliberately *not* checked against a built artifact here. Nothing
loads layers yet; ``scripts/runtime_layer_report.py`` measures the split, and
turning that into a gate is Stage 4 of the runtime layering plan.

Read with ``ast`` rather than by importing: ``quill.apps.radio`` pulls in wx and
a window, and a structural test must not need a display.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PROFILES = _REPO_ROOT / "standalone" / "runtime" / "app-profiles.json"

#: Entry points that ship as an application but are not ``quill/apps/*.py``.
#: The editor is the repository's own ``__main__``; Beacon is a package.
_EXTRA_ENTRIES = ("quill/__main__.py", "quill/apps/beacon/__init__.py")

#: Modules under ``quill/apps`` that are helpers for an app rather than an app.
#: They have no ``main()``, which is how the sweep below tells them apart, so
#: this exists only to document the distinction.
_NOT_APPS_NOTE = "modules under quill/apps without a main() are helpers, not apps"


def _profiles() -> dict:
    return json.loads(_PROFILES.read_text(encoding="utf-8"))


def _has_main(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return any(isinstance(node, ast.FunctionDef) and node.name == "main" for node in tree.body)


def _required_components(path: Path) -> tuple[str, ...] | None:
    """The module's ``REQUIRED_COMPONENTS`` literal, or None when it declares none."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        for target in targets:
            if isinstance(target, ast.Name) and target.id == "REQUIRED_COMPONENTS":
                value = node.value
                if value is None:
                    return None
                return tuple(ast.literal_eval(value))
    return None


def _shipped_entries() -> list[str]:
    """Every module that starts an app, repo-relative and forward-slashed."""
    found = []
    for path in sorted((_REPO_ROOT / "quill" / "apps").glob("*.py")):
        if path.name == "__init__.py":
            continue
        if _has_main(path):
            found.append(path.relative_to(_REPO_ROOT).as_posix())
    for extra in _EXTRA_ENTRIES:
        if (_REPO_ROOT / extra).is_file():
            found.append(extra)
    return sorted(found)


# -- the file itself -----------------------------------------------------------


def test_the_profile_file_parses_and_has_both_sections() -> None:
    data = _profiles()
    assert set(data) >= {"layers", "apps"}
    assert data["apps"], "a profile file with no apps declares nothing"


def test_every_app_row_has_the_fields_a_build_would_read() -> None:
    for app_id, row in _profiles()["apps"].items():
        assert isinstance(row.get("name"), str) and row["name"], app_id
        assert "entry" in row, app_id
        assert isinstance(row.get("components"), list), app_id
        assert isinstance(row.get("layers"), list), app_id


# -- apps <-> entry points -----------------------------------------------------


def test_every_shipped_entry_point_is_declared() -> None:
    declared = {row["entry"] for row in _profiles()["apps"].values() if row["entry"]}
    missing = sorted(set(_shipped_entries()) - declared)
    assert not missing, (
        "These modules start an app and have no row in app-profiles.json. "
        f"A new app that declares nothing is how the runtime grew: {missing}. "
        f"({_NOT_APPS_NOTE}.)"
    )


def test_every_declared_entry_point_exists() -> None:
    for app_id, row in _profiles()["apps"].items():
        entry = row["entry"]
        if entry is None:
            # An app that ships as its own wheel (Social) has no module here.
            assert row.get("external_package"), app_id
            continue
        assert (_REPO_ROOT / entry).is_file(), f"{app_id} names a module that is gone: {entry}"


def test_every_declared_standalone_directory_exists() -> None:
    for app_id, row in _profiles()["apps"].items():
        standalone = row.get("standalone")
        if standalone is None:
            continue
        assert (_REPO_ROOT / standalone).is_dir(), f"{app_id}: {standalone} is gone"


# -- the halves that must not drift --------------------------------------------


def test_declared_components_match_the_modules_own_declaration() -> None:
    """The build-side declaration and the runtime one are the same list.

    This is the control for the risk the whole idea carries: if the profile file
    and ``REQUIRED_COMPONENTS`` both own the truth, they drift, and a
    declaration that can be wrong is worse than none. Studio shipped for months
    declaring ffmpeg while its build staged libmpv too.
    """
    for app_id, row in _profiles()["apps"].items():
        entry = row["entry"]
        if entry is None:
            continue
        declared = tuple(row["components"])
        actual = _required_components(_REPO_ROOT / entry) or ()
        assert declared == actual, (
            f"{app_id}: app-profiles.json says {list(declared)} but {entry} declares {list(actual)}"
        )


# -- layers --------------------------------------------------------------------


def test_every_layer_an_app_names_actually_exists() -> None:
    data = _profiles()
    known = set(data["layers"])
    for app_id, row in data["apps"].items():
        unknown = sorted(set(row["layers"]) - known)
        assert not unknown, f"{app_id} requires layers nobody defined: {unknown}"


def test_no_package_belongs_to_two_layers() -> None:
    # A package in two layers has no owner, which is the state this file exists
    # to end.
    seen: dict[str, str] = {}
    for layer, spec in _profiles()["layers"].items():
        for package in spec["packages"]:
            assert package not in seen, f"{package} claimed by {seen[package]} and {layer}"
            seen[package] = layer


def test_every_layer_names_an_owning_app() -> None:
    data = _profiles()
    for layer, spec in data["layers"].items():
        owner = spec.get("owner")
        assert owner in data["apps"], f"{layer} is owned by {owner!r}, which is not an app"
        assert layer in data["apps"][owner]["layers"], (
            f"{layer} says {owner} owns it, but {owner} does not require it"
        )


@pytest.mark.parametrize("layer", ["documents", "spellcheck"])
def test_the_editor_is_the_only_app_requiring_the_heavy_layers(layer: str) -> None:
    """The measured fact the whole layering plan rests on.

    110.1 MB of the 284.1 MB Python payload is these two layers, and one app of
    ten can call either. If a second app ever legitimately needs one, this test
    failing is the moment to re-price the split rather than discover it later.
    """
    data = _profiles()
    requiring = sorted(app for app, row in data["apps"].items() if layer in row["layers"])
    assert requiring == ["quill"], f"{layer} is now required by {requiring}"
