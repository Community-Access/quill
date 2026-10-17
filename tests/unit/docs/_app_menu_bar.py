"""Build a standalone app's real menu bar in memory, as a new install gets it.

Shared by the ``test_documented_menus_<app>.py`` gates (GATE-DOCMENU). The frame
is the real one, built over an empty data folder with the release gate closed
(``QUILL_DEV_BUILD`` unset), because a developer build reveals rows a listener
with the published app never sees. Everything the frame would reach on the
*machine* rather than in the process is replaced before it is built, which is
why these tests need no ``machine_global`` mark:

* ``RegisterHotKey`` / ``UnregisterHotKey`` (show/hide, dictation and media
  keys are system-wide) answer True and register nothing;
* the screen-reader bridge (``AnnouncementEngine``) is a silent stand-in;
* no tray icon is put in the notification area;
* nothing deferred runs (``CallAfter`` / ``CallLater``: update checks, resume,
  spoken notices), and the startup-entry heal is not started.

None of that changes which menu rows exist: every row is appended while the
menu bar is built, and that code runs unchanged.
"""

from __future__ import annotations

import importlib
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest

from tests.unit.docs.menu_claims import MenuItem, items_from_wx_menu_bar


class _SilentAnnouncer:
    """Stands in for the screen-reader bridge: accepts every call, says nothing."""

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    def __getattr__(self, _name: str) -> Any:
        return lambda *_a, **_k: None


@contextmanager
def real_menu_bar(
    monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest, module: str, cls: str
) -> Iterator[list[MenuItem]]:
    """Yield the menu items of ``module.cls()``; the data folder is the caller's."""
    with real_app_shell(monkeypatch, request, module, cls) as shell:
        yield items_from_wx_menu_bar(shell.frame.GetMenuBar())


@contextmanager
def real_app_shell(
    monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest, module: str, cls: str
) -> Iterator[Any]:
    """Yield ``module.cls()`` itself, built as :func:`real_menu_bar` builds it.

    For gates that need the whole window rather than its menus: the menu-bar
    versus control access-key check (``test_menu_bar_versus_controls.py``)
    walks ``shell.frame``'s controls against its menu titles.
    """
    wx = pytest.importorskip("wx")
    import quill.ui.app_shell as app_shell
    from quill.platform.windows import launch_heal

    monkeypatch.delenv("QUILL_DEV_BUILD", raising=False)
    monkeypatch.setattr(app_shell, "AnnouncementEngine", _SilentAnnouncer)
    monkeypatch.setattr(wx.Frame, "RegisterHotKey", lambda *_a: True, raising=False)
    monkeypatch.setattr(wx.Frame, "UnregisterHotKey", lambda *_a: True, raising=False)
    monkeypatch.setattr(app_shell.AppShellFrame, "_ensure_tray_icon", lambda *_a, **_k: None)
    monkeypatch.setattr(wx, "CallAfter", lambda *_a, **_k: None)
    monkeypatch.setattr(wx, "CallLater", lambda *_a, **_k: None)
    monkeypatch.setattr(launch_heal, "heal_in_background", lambda *_a, **_k: None)
    app = wx.App.Get() or wx.App(False)
    shell = getattr(importlib.import_module(module), cls)()
    try:
        yield shell
    finally:
        _stop_timers(request)
        from quill.ui.dialog_contract import set_transition_announcement_policy

        set_transition_announcement_policy(None)
        shell.frame.Destroy()
        del app


def _stop_timers(request: pytest.FixtureRequest) -> None:
    """The frame is built, not run, so its own close path never stops its timers."""
    for plugin in request.config.pluginmanager.get_plugins():
        watched = getattr(plugin, "_WATCHED_WX_TIMERS", None)
        if watched is None:
            continue
        for timer in list(watched):
            try:
                if timer.IsRunning():
                    timer.Stop()
            except Exception:  # noqa: BLE001 - a dead timer is a stopped one
                pass
