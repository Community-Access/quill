"""The shared runtime's own list of the apps it can start.

It exists so a bare launch -- a taskbar pin of the running app, which Windows
makes of the runtime with no arguments -- starts the app instead of saying
"not an app" (reported 2026-09-27). The list must agree with the launchers and
installers, or a pin starts the wrong thing or nothing.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

from quill.core import runtime_apps, runtime_refs

_REPO = Path(__file__).resolve().parents[3]


def _launcher_products():
    spec = importlib.util.spec_from_file_location(
        "build_native_launcher_for_runtime_apps", _REPO / "scripts" / "build_native_launcher.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve annotations through it
    spec.loader.exec_module(module)
    return module.PRODUCTS


def test_every_runtime_app_matches_its_native_launcher() -> None:
    products = _launcher_products()
    for app in runtime_apps.RUNTIME_APPS:
        product = products[app.ref_id]
        assert product.module == app.module
        assert product.app_id == app.app_user_model_id


def test_every_shared_runtime_installer_registers_a_known_app() -> None:
    known = {app.ref_id for app in runtime_apps.RUNTIME_APPS}
    for iss in (_REPO / "standalone").glob("*/installer/*.iss"):
        found = re.search(r'#define AppRefId "([^"]+)"', iss.read_text(encoding="utf-8"))
        if found:
            assert found.group(1) in known, iss


def test_an_app_claims_its_id_only_where_its_shortcuts_carry_it() -> None:
    """Claiming an id the shortcuts do not carry splits the taskbar button."""
    for app in runtime_apps.RUNTIME_APPS:
        installers = [
            iss.read_text(encoding="utf-8")
            for iss in (_REPO / "standalone").glob("*/installer/*.iss")
            if f'#define AppRefId "{app.ref_id}"' in iss.read_text(encoding="utf-8")
        ]
        carries = any(f'AppUserModelID: "{app.app_user_model_id}"' in text for text in installers)
        assert app.shortcuts_carry_id == carries, app.ref_id


def test_installed_apps_come_from_the_runtime_refs(tmp_path: Path) -> None:
    runtime_refs.register(tmp_path, "radio", "3.13.15")
    runtime_refs.register(tmp_path, "quilllite", "3.13.15")
    runtime_refs.register(tmp_path, "some-future-app", "3.13.15")
    names = [app.display for app in runtime_apps.installed_apps(tmp_path)]
    assert names == ["Quill Radio", "QUILL Lite"]


def test_no_refs_file_is_no_apps(tmp_path: Path) -> None:
    assert runtime_apps.installed_apps(tmp_path) == []


def test_only_a_known_app_claims_an_id() -> None:
    assert runtime_apps.claim_taskbar_identity("not.an.app") is False
    assert runtime_apps.app_for_module("quill.apps.radio").ref_id == "radio"
