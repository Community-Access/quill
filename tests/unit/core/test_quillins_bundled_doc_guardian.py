"""Tests for the bundled ``doc-guardian`` Quillin.

Pin the lifecycle announcement toggle: the Quillin must check
``enabled_announcements`` before speaking, and the manifest must declare the
preference so it shows up in Preferences.
"""

from __future__ import annotations

import importlib.util
import json
from typing import Any

from quill.core.quillins.loader import bundled_extensions_root
from quill.core.quillins.validation import parse_manifest, validate_manifest

_DIR = bundled_extensions_root() / "doc-guardian"


def _load_manifest() -> dict[str, Any]:
    raw = json.loads((_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert validate_manifest(raw) == []
    parse_manifest(raw)
    return raw


def _load_extension() -> Any:
    spec = importlib.util.spec_from_file_location("doc_guardian_extension", _DIR / "extension.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_manifest_declares_enabled_announcements_preference() -> None:
    raw = _load_manifest()
    prefs = raw["contributes"]["preferences"]
    target_keys: list[str] = []
    for page in prefs:
        for tab in page.get("tabs", []):
            for section in tab.get("sections", []):
                for setting in section.get("settings", []):
                    target_keys.append(str(setting.get("key", "")))
    assert "enabled_announcements" in target_keys, (
        "doc-guardian must declare the enabled_announcements preference so it "
        "shows up in Preferences and the Quillin can gate its lifecycle cues"
    )


def test_on_enabled_is_silent_by_default() -> None:
    extension = _load_extension()
    announced: list[str] = []

    class _FakeApi:
        def get_setting(self, key: str, default: Any = None) -> Any:
            return default

        def log(self, message: str) -> None:
            pass

        def announce(self, message: str) -> None:
            announced.append(message)

    extension.on_enabled(_FakeApi(), {})
    assert announced == [], (
        "Doc Guardian must not speak 'is now active' when "
        "enabled_announcements is off (the default)."
    )


def test_on_enabled_speaks_when_enabled_announcements_is_on() -> None:
    extension = _load_extension()
    announced: list[str] = []

    class _FakeApi:
        def get_setting(self, key: str, default: Any = None) -> Any:
            if key == "enabled_announcements":
                return True
            return default

        def log(self, message: str) -> None:
            pass

        def announce(self, message: str) -> None:
            announced.append(message)

    extension.on_enabled(_FakeApi(), {})
    assert announced == ["Document Guardian is now active."]


def test_on_disabled_is_silent_by_default() -> None:
    extension = _load_extension()
    announced: list[str] = []

    class _FakeApi:
        def get_setting(self, key: str, default: Any = None) -> Any:
            return default

        def log(self, message: str) -> None:
            pass

        def announce(self, message: str) -> None:
            announced.append(message)

    extension.on_disabled(_FakeApi(), {})
    assert announced == [], (
        "Doc Guardian must not speak 'is now inactive' when "
        "enabled_announcements is off (the default)."
    )


def test_on_disabled_speaks_when_enabled_announcements_is_on() -> None:
    extension = _load_extension()
    announced: list[str] = []

    class _FakeApi:
        def get_setting(self, key: str, default: Any = None) -> Any:
            if key == "enabled_announcements":
                return True
            return default

        def log(self, message: str) -> None:
            pass

        def announce(self, message: str) -> None:
            announced.append(message)

    extension.on_disabled(_FakeApi(), {})
    assert announced == ["Document Guardian is now inactive."]
