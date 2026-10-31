"""UX-015: every Studio preference changes something you can observe.

A setting that is saved and loaded but read by nothing is worse than no
setting (TG Drop Deck's "Hear yourself through"). Each test here flips one
preference and watches the behaviour it controls, so deleting the code that
reads a preference fails its test. The last test fails when a preference is
added to Studio's defaults without a test here.
"""

from __future__ import annotations

import threading
from types import SimpleNamespace

import pytest
import wx

import quill.apps.studio as studio
from quill.apps.studio import _PREFS_DEFAULTS, StudioAppFrame
from quill.apps.studio_preferences import apply_asio_preference
from tests.wx_session import patch_call_after

#: Every key in Studio's preferences file, and the test below that proves it is read.
COVERED = {
    "check_updates_on_startup": "test_check_updates_on_startup",
    "last_update_check": "test_check_updates_on_startup",
    "alt_f4_to_tray": "test_alt_f4_to_tray",
    "close_action": "test_close_action",
    "announce_run_milestones": "test_announce_run_milestones",
    "use_asio": "test_use_asio",
    "show_status_bar": "test_show_status_bar",
}


def _host(**prefs):
    return SimpleNamespace(_app_prefs={**_PREFS_DEFAULTS, **prefs})


@pytest.mark.parametrize("on", [True, False])
def test_check_updates_on_startup(on, monkeypatch):
    monkeypatch.setattr(studio, "_save_app_prefs", lambda _prefs: None)
    host = _host(check_updates_on_startup=on, last_update_check="2026-10-30T00:00:00+00:00")
    asked, checks = [], []
    host._app_update_check_due = lambda last: asked.append(last) or True
    host.check_for_app_updates = lambda **kwargs: checks.append(kwargs)
    StudioAppFrame._maybe_check_updates_on_startup(host)
    assert len(checks) == (1 if on else 0)
    # last_update_check is what the throttle is given, so it is read too.
    assert asked == (["2026-10-30T00:00:00+00:00"] if on else [])


def _key(code, *, alt=False):
    skipped = []
    event = SimpleNamespace(
        GetKeyCode=lambda: code,
        AltDown=lambda: alt,
        ControlDown=lambda: False,
        Skip=lambda: skipped.append(True),
    )
    return event, skipped


@pytest.mark.parametrize("on", [True, False])
def test_alt_f4_to_tray(on):
    host = _host(alt_f4_to_tray=on)
    sent = []
    host._send_to_tray = lambda: sent.append(True)
    event, skipped = _key(wx.WXK_F4, alt=True)
    StudioAppFrame._on_char_hook(host, event)
    assert sent == ([True] if on else [])
    assert skipped == ([] if on else [True])  # off: Alt+F4 goes on to close the window


@pytest.mark.parametrize("action", ["ask", "exit", "minimize"])
def test_close_action(action):
    host = _host(close_action=action)
    seen = {}
    host.handle_app_close = lambda event, **kwargs: seen.update(kwargs)
    host._protected_background_jobs = {}
    host._studio_close_confirm = host._studio_shutdown = lambda: None
    StudioAppFrame._on_app_close(host, object())
    assert seen["close_action"] == action


@pytest.mark.parametrize("on", [True, False])
def test_announce_run_milestones(on, monkeypatch):
    queued = []
    patch_call_after(monkeypatch, lambda fn, *args, **kwargs: queued.append((fn, args)))
    host = _host(announce_run_milestones=on)
    host._background_task_count = 0
    host._protected_background_jobs = {}
    host._set_status = lambda _text: None
    host._note_progress = object()
    host._announce = object()
    host._finish_background_task = object()
    done = threading.Event()

    def work(progress):
        progress("chapter 2", 50, 100)
        done.set()

    StudioAppFrame._run_background_task(host, "Narrating", work, lambda _result: None)
    assert done.wait(5)
    spoken = [args for fn, args in queued if fn is host._announce]
    assert spoken == ([("Narrating: 50 percent",)] if on else [])


@pytest.mark.parametrize("on", [True, False])
def test_use_asio(on):
    environ: dict[str, str] = {}
    assert apply_asio_preference({**_PREFS_DEFAULTS, "use_asio": on}, environ) is on
    assert environ == ({"SD_ENABLE_ASIO": "1"} if on else {})


def test_show_status_bar(monkeypatch):
    monkeypatch.setattr(studio, "_save_app_prefs", lambda _prefs: None)
    shown = []
    host = _host(show_status_bar=True)
    host.frame = SimpleNamespace(GetMenuBar=lambda: None)
    host._status_bar = SimpleNamespace(set_visible=shown.append, refresh=lambda: None)
    host._announce = lambda _text: None
    StudioAppFrame._toggle_show_status_bar(host)
    StudioAppFrame._toggle_show_status_bar(host)
    assert shown == [False, True]


def test_the_preferences_dialog_writes_the_keys_that_are_read(monkeypatch):
    """Each check box lands on the key its behaviour test reads."""
    import quill.ui.app_preferences_dialog as dialog_module
    from quill.apps import studio_preferences

    class FakeDialog:
        def __init__(self, *_args, **_kwargs):
            pass

        def show(self):
            return [False, True, False, True], [2], []

    monkeypatch.setattr(dialog_module, "PreferencesDialog", FakeDialog)
    monkeypatch.setattr(studio, "_save_app_prefs", lambda _prefs: None)
    monkeypatch.setattr(studio_preferences.app_sounds, "preference_action", lambda _a: None)
    monkeypatch.setattr(studio_preferences.slider_keys, "preference_action", lambda _a: None)
    app = SimpleNamespace(
        _app_prefs=dict(_PREFS_DEFAULTS),
        frame=None,
        _announce=lambda _t: None,
        _set_status_quiet=lambda _t: None,
    )
    studio_preferences.open_preferences(app)
    prefs = app._app_prefs
    assert (prefs["check_updates_on_startup"], prefs["alt_f4_to_tray"]) == (False, True)
    assert (prefs["announce_run_milestones"], prefs["use_asio"]) == (False, True)
    assert prefs["close_action"] == studio._CLOSE_ACTION_VALUES[2]


def test_every_preference_has_an_effect_test():
    assert set(_PREFS_DEFAULTS) == set(COVERED)
    for test_name in set(COVERED.values()):
        assert callable(globals()[test_name])
