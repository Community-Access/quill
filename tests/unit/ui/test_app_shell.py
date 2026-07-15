"""AppShellFrame host-protocol pieces the ADP mixin relies on.

These cover the pure-logic host methods (no wx.Frame needed): feature
gating, menu labels, and the unlock gate on the ADP menu items.
"""

from __future__ import annotations

from quill.core.keymap import DEFAULT_KEYMAP
from quill.ui.app_shell import AppShellFrame
from quill.ui.main_frame_adp import AdpMixin


class _Locks:
    def __init__(self, locked: set[str]) -> None:
        self._locked = locked

    def is_locked(self, feature_id: str) -> bool:
        return feature_id in self._locked


class _Features:
    def __init__(self, enabled: set[str]) -> None:
        self._enabled = enabled

    def is_enabled(self, feature_id: str) -> bool:
        return feature_id in self._enabled


def _bare_shell() -> AppShellFrame:
    shell = AppShellFrame.__new__(AppShellFrame)
    shell.keymap = dict(DEFAULT_KEYMAP)
    return shell


def test_feature_enabled_consults_manager():
    shell = _bare_shell()
    shell.features = _Features({"future.adp_assistant"})
    shell._feature_locks = _Locks(set())
    assert shell._feature_enabled("future.adp_assistant")
    assert not shell._feature_enabled("future.something_else")


def test_feature_lock_wins_over_unlock():
    shell = _bare_shell()
    shell.features = _Features({"future.adp_assistant"})
    shell._feature_locks = _Locks({"future.adp_assistant"})
    assert not shell._feature_enabled("future.adp_assistant")


def test_menu_label_without_binding_is_bare_title():
    shell = _bare_shell()
    shell.keymap = {}
    assert shell._menu_label("Ask AD&P...", "adp.ask") == "Ask AD&P..."


def test_menu_label_appends_simple_binding_and_skips_chords():
    shell = _bare_shell()
    shell.keymap = {"adp.ask": "Ctrl+Shift+A", "adp.settings": "Ctrl+Shift+Grave, A"}
    assert shell._menu_label("Ask AD&P...", "adp.ask") == "Ask AD&P...\tCtrl+Shift+A"
    # Chord bindings would misparse as bare accelerators after the tab (#612).
    assert shell._menu_label("ADP Se&ttings...", "adp.settings") == "ADP Se&ttings..."


class _ShellWithAdp(AppShellFrame, AdpMixin):
    pass


class _MenuSpy:
    def __init__(self) -> None:
        self.appended: list[str] = []
        self.separators = 0

    def AppendSeparator(self) -> None:  # noqa: N802 - wx spelling
        self.separators += 1

    def Append(self, _id: object, label: str) -> None:  # noqa: N802 - wx spelling
        self.appended.append(label)


def test_adp_menu_items_absent_while_locked():
    shell = _ShellWithAdp.__new__(_ShellWithAdp)
    shell.features = _Features(set())
    shell._feature_locks = _Locks(set())
    menu = _MenuSpy()
    shell._append_adp_media_items(menu)
    assert menu.appended == []
    assert menu.separators == 0


def test_top_level_adp_menu_is_none_while_locked():
    shell = _ShellWithAdp.__new__(_ShellWithAdp)
    shell.features = _Features(set())
    shell._feature_locks = _Locks(set())
    assert shell._build_adp_menu() is None


class _TaskManagerLikeQuills:
    """Calls the submitted func exactly the way QuillTaskManager.wrapped does:
    with cancellation_token / operation_id / progress_callback keyword args.
    The 1.0.0 standalone apps crashed here ("_fetch() got an unexpected
    keyword argument 'cancellation_token'") because the closures took no args."""

    def submit(self, _name, func, **_options):
        return func(
            cancellation_token=object(),
            operation_id="test-op",
            progress_callback=lambda *_a, **_k: None,
        )


class _TaskManagerRoutingCallbacks:
    """Like ``_TaskManagerLikeQuills``, but also routes the result to
    on_success/on_failure the way the real QuillTaskManager does -- needed
    for tests that verify what happens *after* the fetch (silent vs.
    interactive announcements), not just that the fetch itself is callable."""

    def submit(self, name, func, *, on_success=None, on_failure=None, **_options):
        try:
            result = func(
                cancellation_token=object(),
                operation_id="test-op",
                progress_callback=lambda *_a, **_k: None,
            )
        except BaseException as exc:  # noqa: BLE001 - mirrors QuillTaskManager's catch-all
            if on_failure is not None:
                on_failure(name, exc)
            return None
        if on_success is not None:
            on_success(name, result)
        return result


def test_update_check_fetch_accepts_task_manager_kwargs(monkeypatch):
    import quill.core.updates as updates

    calls: list[str] = []
    monkeypatch.setattr(updates, "fetch_releases", lambda url, **_kw: calls.append(url) or [])
    shell = _bare_shell()
    shell._announce = lambda _msg: None
    shell._running_portable_build = lambda: False
    shell._task_manager = _TaskManagerLikeQuills()
    # Must not raise TypeError when the task manager injects its kwargs.
    shell.check_for_app_updates(repo_slug="Community-Access/quill-radio", current_version="1.0.0")
    assert calls == ["https://api.github.com/repos/Community-Access/quill-radio/releases"]


def test_silent_update_check_says_nothing_when_up_to_date(monkeypatch):
    """The automatic startup check (silent_no_update=True) must not announce
    "Checking for updates" or "You are up to date" -- only a genuine
    available update is worth interrupting a launch for."""
    import quill.core.updates as updates
    import quill.ui.app_shell as app_shell_module

    monkeypatch.setattr(app_shell_module.wx, "CallAfter", lambda fn, *a, **k: fn(*a, **k))
    release = type("R", (), {"prerelease": False, "version": "1.0.0"})()
    monkeypatch.setattr(updates, "fetch_releases", lambda url, **_kw: [release])
    announced: list[str] = []
    shell = _bare_shell()
    shell._announce = announced.append
    shell._running_portable_build = lambda: False
    shell._task_manager = _TaskManagerRoutingCallbacks()
    shell.check_for_app_updates(
        repo_slug="Community-Access/quill-radio", current_version="1.0.0", silent_no_update=True
    )
    assert announced == []


def test_manual_update_check_still_announces_up_to_date(monkeypatch):
    import quill.core.updates as updates
    import quill.ui.app_shell as app_shell_module

    monkeypatch.setattr(app_shell_module.wx, "CallAfter", lambda fn, *a, **k: fn(*a, **k))
    release = type("R", (), {"prerelease": False, "version": "1.0.0"})()
    monkeypatch.setattr(updates, "fetch_releases", lambda url, **_kw: [release])
    announced: list[str] = []
    shell = _bare_shell()
    shell._announce = announced.append
    shell._running_portable_build = lambda: False
    shell._task_manager = _TaskManagerRoutingCallbacks()
    shell.check_for_app_updates(repo_slug="Community-Access/quill-radio", current_version="1.0.0")
    assert "Checking for updates" in announced
    assert any("up to date" in msg for msg in announced)


def test_silent_update_check_failure_shows_no_dialog(monkeypatch):
    import quill.core.updates as updates
    import quill.ui.app_shell as app_shell_module

    monkeypatch.setattr(app_shell_module.wx, "CallAfter", lambda fn, *a, **k: fn(*a, **k))

    def _boom(*_a, **_kw):
        raise RuntimeError("no network")

    monkeypatch.setattr(updates, "fetch_releases", _boom)
    shell = _bare_shell()
    shell._announce = lambda _msg: None
    shell._running_portable_build = lambda: False
    shell._task_manager = _TaskManagerRoutingCallbacks()
    boxes: list[str] = []
    shell._show_message_box = lambda *a, **k: boxes.append(a[0])
    shell.check_for_app_updates(
        repo_slug="Community-Access/quill-radio", current_version="1.0.0", silent_no_update=True
    )
    assert boxes == []


def test_manual_update_check_failure_shows_dialog(monkeypatch):
    import quill.core.updates as updates
    import quill.ui.app_shell as app_shell_module

    monkeypatch.setattr(app_shell_module.wx, "CallAfter", lambda fn, *a, **k: fn(*a, **k))

    def _boom(*_a, **_kw):
        raise RuntimeError("no network")

    monkeypatch.setattr(updates, "fetch_releases", _boom)
    shell = _bare_shell()
    shell._announce = lambda _msg: None
    shell._running_portable_build = lambda: False
    shell._task_manager = _TaskManagerRoutingCallbacks()
    boxes: list[str] = []
    shell._show_message_box = lambda *a, **k: boxes.append(a[0])
    shell.check_for_app_updates(repo_slug="Community-Access/quill-radio", current_version="1.0.0")
    assert len(boxes) == 1 and "no network" in boxes[0]


def test_app_update_check_due_when_never_checked():
    shell = _bare_shell()
    assert shell._app_update_check_due("") is True


def test_app_update_check_due_false_within_interval():
    from datetime import UTC, datetime

    shell = _bare_shell()
    recent = datetime.now(UTC).isoformat()
    assert shell._app_update_check_due(recent) is False


def test_app_update_check_due_true_after_interval():
    from datetime import UTC, datetime, timedelta

    shell = _bare_shell()
    old = (datetime.now(UTC) - timedelta(hours=25)).isoformat()
    assert shell._app_update_check_due(old) is True


def test_app_update_check_due_true_on_unparseable_timestamp():
    shell = _bare_shell()
    assert shell._app_update_check_due("not-a-date") is True
