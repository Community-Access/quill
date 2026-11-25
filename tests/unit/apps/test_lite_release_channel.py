"""QUILL Lite: Help > Release Channel... (no key; Alt+H, C) and its Preferences row.

The window and its rules are tested in tests/unit/ui/test_release_channel_dialogs.py
and tests/unit/core/test_release_channels_core.py; this pins QUILL Lite's side:
the handler opens the shared window for QUILL Lite, with the installed version,
and the app records the data-format clock before its first editable window.
"""

from __future__ import annotations

from types import SimpleNamespace

from quill.apps import lite_updates
from quill.apps.lite_startup import LiteStartupMixin


def test_release_channel_opens_the_shared_window_for_quill_lite(lite_window, monkeypatch):
    seen: list[dict] = []
    monkeypatch.setattr(
        "quill.ui.updates.flow.open_release_channel",
        lambda parent, **kwargs: seen.append({"parent": parent, **kwargs}),
    )
    win = lite_window("text")

    win.cmd_release_channel()

    assert len(seen) == 1
    assert seen[0]["app_key"] == "quilllite"
    assert seen[0]["parent"] is win
    assert seen[0]["installed_version"]
    assert callable(seen[0]["check_now"])


def test_preferences_opens_it_without_a_follow_up_check(monkeypatch):
    seen: list[dict] = []
    monkeypatch.setattr(
        "quill.ui.updates.flow.open_release_channel",
        lambda parent, **kwargs: seen.append(kwargs),
    )
    lite_updates.open_release_channel_for(SimpleNamespace(), check=False)
    assert seen[0]["check_now"] is None


def test_lite_records_the_data_formats_before_the_window(monkeypatch):
    recorded: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "quill.core.data_format_ledger.record_running_build",
        lambda app, version: recorded.append((app, version)),
    )
    LiteStartupMixin._record_lite_running_build()
    assert recorded == [("quilllite", lite_updates.APP_VERSION)]
