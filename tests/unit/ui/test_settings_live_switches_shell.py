"""Changing a right-click setting in Settings re-registers the verbs at once.

Before 2026-10 the Integration page only took effect the next time someone ran
Install Shell Integration. The registry write itself is faked here.
"""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.settings import Settings
from quill.ui import settings_live_switches


@pytest.fixture
def applied(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    calls: list[Any] = []
    monkeypatch.setattr(settings_live_switches, "_apply_shell_verbs", calls.append)
    monkeypatch.setattr(
        settings_live_switches.wakeword_switch, "apply_wakeword_setting", lambda host: None
    )
    return calls


def test_changed_file_types_reregister(applied: list[Any]) -> None:
    host = SimpleNamespace(settings=Settings(shell_file_types="images_pdf"))
    settings_live_switches.remember_shell_verbs(host)
    host.settings = replace(host.settings, shell_file_types="images")
    settings_live_switches.after_settings_applied(host)
    assert [s.shell_file_types for s in applied] == ["images"]


def test_ok_on_an_unrelated_page_leaves_the_registry_alone(applied: list[Any]) -> None:
    host = SimpleNamespace(settings=Settings())
    settings_live_switches.remember_shell_verbs(host)
    host.settings = replace(host.settings, theme="dark")
    settings_live_switches.after_settings_applied(host)
    assert applied == []


def test_nothing_is_written_before_startup_recorded_a_baseline(applied: list[Any]) -> None:
    host = SimpleNamespace(settings=Settings(shell_file_types="images"))
    settings_live_switches.after_settings_applied(host)
    assert applied == []
