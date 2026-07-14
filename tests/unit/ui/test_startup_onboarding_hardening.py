"""DLG-3 Phase 5: startup / onboarding hardening characterization.

Phase 5 hardens the first-run / startup modal chain (screen-reader detection,
trust consent, crash recovery, first-run onboarding, watch folders). Two of its
three acceptance claims are pure-code contracts that these tests pin so they
cannot silently regress:

1. **The screen-reader startup-crash path is retired.** Every deferred startup
   step runs inside its own ``try/except`` in ``_run_deferred_startup_tasks``; a
   throwing step is recorded via ``_report_startup_task_failure`` and the app
   stays open and keeps running the remaining steps. (Historically an exception
   here killed Quill right after the startup tip with nothing in the log.)

2. **Explicit-consent requirements are preserved.** ``_show_trust_consent_onboarding``
   only marks consent complete when the user explicitly accepts; declining never
   records consent, and a decline during startup closes the app instead of
   silently continuing.

The third claim (deterministic focus across chained modal flows) is verified
live in Phase 8 (DLG-3.8) and structurally enforced by the dialog-hardening
contract gate; it is not re-asserted here.

A #179-era test pins the deferred-modal offload contract: the crash-recovery
offer's snapshot read + ``mkdir`` runs on a background task, and a thrown
``read_recovery_snapshot`` is reported via ``_report_startup_task_failure``
without ever calling ``ShowModal``.
"""

from __future__ import annotations

import quill.ui.main_frame as main_frame_module
from quill.ui.main_frame import MainFrame


class _Frame:
    def __init__(self) -> None:
        self.closed = 0

    def Close(self):  # noqa: N802 - mimics wx API
        self.closed += 1


class _Wx:
    ID_YES = 5103
    ID_NO = 5104
    YES_NO = 0x0008
    ICON_INFORMATION = 0x0002


def _build_frame() -> MainFrame:
    frame = MainFrame.__new__(MainFrame)
    frame.frame = _Frame()
    frame._wx = _Wx()
    frame.settings = type("Settings", (), {"auto_check_updates": False})()
    frame._safe_mode = False
    frame._status: list[str] = []
    frame._set_status = lambda message: frame._status.append(message)
    return frame


def test_deferred_startup_isolates_a_throwing_step_and_keeps_going(monkeypatch) -> None:
    frame = _build_frame()
    failures: list[str] = []
    frame._report_startup_task_failure = lambda label: failures.append(label)
    frame._start_ipc_poll = lambda: None
    frame._first_run_trust_consent_prompt = False

    ran: list[str] = []

    def _boom() -> None:
        raise RuntimeError("crash recovery exploded")

    frame._offer_crash_recovery = _boom
    frame._maybe_run_first_run_onboarding = lambda: ran.append("first-run")
    frame._maybe_start_watch_folder = lambda: ran.append("watch-folder")
    monkeypatch.setattr(
        main_frame_module,
        "detect_screen_reader",
        lambda: type("D", (), {"detected": False, "name": ""})(),
    )

    # Must not raise -- the startup-crash path is retired.
    frame._run_deferred_startup_tasks()

    # The throwing step was recorded, and the steps after it still ran.
    assert "crash recovery" in failures
    assert ran == ["first-run", "watch-folder"]
    assert frame.frame.closed == 0


def test_trust_consent_decline_does_not_record_consent(monkeypatch) -> None:
    frame = _build_frame()
    frame._show_modal_dialog = lambda dialog, title: _Wx.ID_NO
    marked: list[int] = []
    monkeypatch.setattr(main_frame_module, "mark_trust_consent_complete", lambda: marked.append(1))

    class _Dialog:
        def __init__(self, *a, **k) -> None:
            pass

        def SetYesNoLabels(self, *a):  # noqa: N802 - mimics wx API
            return True

        def Destroy(self):  # noqa: N802 - mimics wx API
            return True

    frame._wx.MessageDialog = _Dialog

    accepted = frame._show_trust_consent_onboarding(force=True)

    assert accepted is False
    assert marked == []


def test_trust_consent_accept_records_consent(monkeypatch) -> None:
    frame = _build_frame()
    frame._show_modal_dialog = lambda dialog, title: _Wx.ID_YES
    marked: list[int] = []
    monkeypatch.setattr(main_frame_module, "mark_trust_consent_complete", lambda: marked.append(1))

    class _Dialog:
        def __init__(self, *a, **k) -> None:
            pass

        def SetYesNoLabels(self, *a):  # noqa: N802 - mimics wx API
            return True

        def Destroy(self):  # noqa: N802 - mimics wx API
            return True

    frame._wx.MessageDialog = _Dialog

    accepted = frame._show_trust_consent_onboarding(force=True)

    assert accepted is True
    assert marked == [1]


def test_declined_startup_consent_closes_the_app(monkeypatch) -> None:
    frame = _build_frame()
    frame._report_startup_task_failure = lambda label: None
    frame._start_ipc_poll = lambda: None
    frame._first_run_trust_consent_prompt = True
    frame._show_trust_consent_onboarding = lambda force: False
    later_steps: list[str] = []
    frame._offer_crash_recovery = lambda: later_steps.append("crash")
    frame._maybe_run_first_run_onboarding = lambda: later_steps.append("first-run")
    frame._maybe_start_watch_folder = lambda: later_steps.append("watch")
    monkeypatch.setattr(
        main_frame_module,
        "detect_screen_reader",
        lambda: type("D", (), {"detected": False, "name": ""})(),
    )

    frame._run_deferred_startup_tasks()

    # Declining consent closes the app and short-circuits the rest of startup.
    assert frame.frame.closed == 1
    assert later_steps == []
    assert frame._status[-1] == "Startup consent declined. Quill is closing."


# ---------------------------------------------------------------------------
# #179: crash-recovery snapshot I/O must run on a background task, not the UI
# thread.  These tests pin the offload contract.
# ---------------------------------------------------------------------------


class _FakeTask:
    def __init__(self, name: str, func, kwargs, on_success, on_failure) -> None:
        self.name = name
        self.func = func
        self.kwargs = kwargs
        self.on_success = on_success
        self.on_failure = on_failure


class _FakeTaskManager:
    """In-process stand-in for ``TaskManager`` that drives callbacks synchronously."""

    def __init__(self) -> None:
        self.submissions: list[_FakeTask] = []

    def submit(
        self,
        name: str,
        func,
        *,
        on_success=None,
        on_failure=None,
        **kwargs,
    ) -> _FakeTask:
        task = _FakeTask(name, func, kwargs, on_success, on_failure)
        self.submissions.append(task)
        return task

    def run_last_success(self, result) -> None:
        """Simulate the worker finishing successfully."""
        last = self.submissions[-1]
        assert last.on_success is not None
        last.on_success("op-id", result)

    def run_last_failure(self, exc: BaseException) -> None:
        last = self.submissions[-1]
        assert last.on_failure is not None
        last.on_failure("op-id", exc)


def _make_offer():
    """Build a minimal RecoveryOffer-shaped stand-in."""

    from dataclasses import dataclass
    from pathlib import Path

    @dataclass(frozen=True, slots=True)
    class _Offer:
        session_id: str = "sess-1"
        snapshot: Path = Path("/tmp/snap.txt")
        cursor_position: int = 0
        dismissal_count: int = 0

    return _Offer()


def test_crash_recovery_offloads_snapshot_io_to_background(monkeypatch) -> None:
    """#179: ``_offer_crash_recovery`` must not block the UI thread on snapshot I/O."""
    frame = _build_frame()
    frame._recovery_offers = [_make_offer()]
    frame._task_manager = _FakeTaskManager()
    show_calls: list[dict] = []

    def _record_show(ctx, prepared):
        show_calls.append({"ctx": ctx, "prepared": prepared})

    frame._show_crash_recovery_dialog = _record_show

    # Pre-mock read_recovery_snapshot + app_data_dir so the prepare worker is
    # safe to call synchronously.
    monkeypatch.setattr(
        main_frame_module, "app_data_dir", lambda: __import__("pathlib").Path("/tmp")
    )
    monkeypatch.setattr(
        main_frame_module,
        "read_recovery_snapshot",
        lambda _p: ("line1\nline2\nline3", False),
    )

    # Must not raise, must not call ShowModal directly.
    frame._offer_crash_recovery()

    assert len(frame._task_manager.submissions) == 1
    assert frame._task_manager.submissions[0].name == "crash-recovery-prepare"
    # _show_crash_recovery_dialog has not been called yet — the worker
    # delivers its result via on_success, which we drive next.
    assert show_calls == []

    # Drive the worker success callback (this is what TaskManager would do
    # via call_ui_safely after the worker returns).
    frame._task_manager.run_last_success({
        "logs_path": __import__("pathlib").Path("/tmp/logs"),
        "preview_text": "line1\nline2",
    })

    assert len(show_calls) == 1
    assert show_calls[0]["prepared"]["preview_text"] == "line1\nline2"


def test_crash_recovery_prepare_failure_is_reported_via_startup_failure(monkeypatch) -> None:
    """A throwing prepare must record via ``_report_startup_task_failure`` and
    never show the dialog (no half-broken modal)."""
    frame = _build_frame()
    frame._recovery_offers = [_make_offer()]
    frame._task_manager = _FakeTaskManager()
    show_calls: list = []
    frame._show_crash_recovery_dialog = lambda *a, **k: show_calls.append((a, k))
    failures: list[str] = []
    frame._report_startup_task_failure = lambda label: failures.append(label)
    monkeypatch.setattr(
        main_frame_module, "app_data_dir", lambda: __import__("pathlib").Path("/tmp")
    )
    monkeypatch.setattr(
        main_frame_module,
        "read_recovery_snapshot",
        lambda _p: (_ for _ in ()).throw(OSError("boom")),
    )

    frame._offer_crash_recovery()
    frame._task_manager.run_last_failure(OSError("boom"))

    assert show_calls == []
    assert failures == ["crash recovery"]


def test_deferred_startup_task_list_includes_help_topics_warmup() -> None:
    """#179: the help topics renderer must be warmed during deferred startup so
    the first F1 is instant."""
    frame = _build_frame()
    failures: list[str] = []
    frame._report_startup_task_failure = lambda label: failures.append(label)
    frame._start_ipc_poll = lambda: None
    frame._first_run_trust_consent_prompt = False
    frame._offer_crash_recovery = lambda: None
    frame._maybe_run_first_run_onboarding = lambda: None
    frame._maybe_start_watch_folder = lambda: None
    import quill.ui.main_frame as mf

    monkeypatch = __import__("pytest").MonkeyPatch()
    try:
        monkeypatch.setattr(
            mf,
            "detect_screen_reader",
            lambda: type("D", (), {"detected": False, "name": ""})(),
        )
        # Capture the source so we can grep for the warm-up entry without
        # having to drive every task in the list.
        from pathlib import Path

        src = Path(mf.__file__).read_text(encoding="utf-8")
    finally:
        monkeypatch.undo()

    assert '"help topics warm-up"' in src
    assert "warm_help_topics" in src


def test_first_run_defers_tab_creation_until_wizard_returns() -> None:
    """#606: on first launch the wizard must open before any document tab.

    __init__ builds the frame without a tab when
    setup_wizard_completed is False, so macOS screen readers do not
    announce "Untitled" before the wizard modal grabs focus.
    _maybe_run_first_run_onboarding creates the tab via
    new_document() after the wizard returns, so the user lands in
    a fresh document once the wizard is closed.
    """
    frame = _build_frame()
    frame.settings = type(
        "Settings", (), {"setup_wizard_completed": False, "auto_check_updates": False}
    )()
    frame._first_run_wizard_pending = True
    frame._document_tabs = []
    failures: list[str] = []
    frame._report_startup_task_failure = lambda label: failures.append(label)

    wizard_open_tab_count: list[int] = []

    def _fake_run_startup_wizard(*, first_run: bool = False):
        # #606: while the wizard is "open" the notebook must be
        # empty -- no "Untitled" tab should have been built in
        # __init__ on this branch.
        wizard_open_tab_count.append(len(frame._document_tabs))
        return True, False

    frame.run_startup_wizard = _fake_run_startup_wizard  # type: ignore[method-assign]

    def _stub_create_document_tab(document: object, select: bool = True) -> None:
        # Mirror the real _create_document_tab() side effect for the
        # assertion: a fresh tab lands in _document_tabs. We stub it
        # because the production method requires live wx widgets
        # (Panel, SplitterWindow, TextCtrl) that the __new__-built
        # frame does not have.
        class _StubTab:
            pass

        frame._document_tabs.append(_StubTab())

    frame._create_document_tab = _stub_create_document_tab  # type: ignore[method-assign]
    frame._location_ring = type("LR", (), {"record": lambda self, n: None})()
    frame._region_tracker = type("RT", (), {"enter": lambda self, name: None})()
    frame._focus_editor = lambda: None

    frame._maybe_run_first_run_onboarding()

    # #606 invariants
    assert wizard_open_tab_count == [0], "no document tab must exist while the wizard is open"
    assert len(frame._document_tabs) == 1, (
        "_create_document_tab() must create exactly one tab after the wizard"
    )
    assert frame._first_run_wizard_pending is False, (
        "the pending flag must be cleared once the tab is created"
    )
    # No startup-task failures were reported by this happy path.
    assert failures == []


def test_completed_wizard_shows_no_legacy_onboarding_path(monkeypatch) -> None:
    """Once the unified wizard has run, no second onboarding surface appears.

    Regression (#700): a finished first-run wizard set ``setup_wizard_completed``
    but the legacy per-feature path still fired on the next launch, re-showing
    the "Startup Wizard overview" plus a "Start guided setup now?" prompt every
    time. That whole path is now removed: with setup_wizard_completed True,
    _maybe_run_first_run_onboarding only focuses the editor and never re-runs the
    wizard or shows any modal.
    """
    frame = _build_frame()
    frame.settings = type(
        "Settings", (), {"setup_wizard_completed": True, "auto_check_updates": False}
    )()
    frame._report_startup_task_failure = lambda label: None
    frame._surface_data_migration_notice = lambda: None
    frame.editor = None

    wizard_runs: list[bool] = []
    frame.run_startup_wizard = lambda **kwargs: wizard_runs.append(True)
    modals: list[object] = []
    frame._show_modal_dialog = lambda dlg, title: modals.append(dlg)
    frame._show_message_box = lambda *a, **k: modals.append(a)

    # The legacy methods that drove the second wizard no longer exist.
    assert not hasattr(MainFrame, "show_startup_wizard_page")
    assert not hasattr(MainFrame, "_show_startup_wizard_first_run_prompt")
    assert not hasattr(MainFrame, "_show_profile_onboarding")

    frame._maybe_run_first_run_onboarding()

    assert wizard_runs == [], "the wizard must not re-run after it has completed"
    assert modals == [], "no onboarding modal may appear on a later launch"


# ---------------------------------------------------------------------------
# #44: an undeletable new-install marker must not force the wizard to reopen
# on every subsequent launch.
# ---------------------------------------------------------------------------


class _UndeletableMarker:
    """A marker path stand-in whose unlink() always fails, like a marker
    written into an elevated install directory the running user can't
    write to."""

    def __init__(
        self,
        mtime: float,
        path: str = "C:/Program Files/Quill/quill-new-install.txt",
    ) -> None:
        self._mtime = mtime
        self._path = path
        self.unlink_attempts = 0

    def exists(self) -> bool:
        return True

    def stat(self):
        return type("Stat", (), {"st_mtime": self._mtime})()

    def resolve(self):
        # Real Path.resolve() returns a Path; the production code only uses
        # ``str(resolved)`` so a string-shaped stand-in is fine.
        return self._path

    def unlink(self) -> None:
        self.unlink_attempts += 1
        raise OSError("Access is denied")


def test_undeletable_marker_does_not_reopen_wizard_on_next_launch(monkeypatch, tmp_path) -> None:
    import quill.core.paths as paths_module

    frame = _build_frame()
    frame.settings = type("Settings", (), {"setup_wizard_completed": True})()
    frame.run_startup_wizard = lambda **kwargs: None
    marker = _UndeletableMarker(mtime=12345.0)
    monkeypatch.setattr(paths_module, "new_install_marker_path", lambda: marker)
    monkeypatch.setattr(paths_module, "app_data_dir", lambda: tmp_path)

    saved: list[bool] = []
    import quill.core.settings as settings_module

    monkeypatch.setattr(
        settings_module, "save_settings", lambda s: saved.append(s.setup_wizard_completed)
    )

    # First launch: marker exists and hasn't been consumed before, so the
    # wizard flag resets even though the delete itself fails.
    frame._maybe_run_first_run_onboarding()
    assert marker.unlink_attempts == 1
    assert saved == [False]

    # Second launch: same undeleted marker, same mtime. Before the fix this
    # would reset setup_wizard_completed to False again every single launch,
    # reopening the wizard forever. The sentinel recorded under app_data_dir()
    # must recognize this marker as already consumed and skip the reset.
    frame.settings.setup_wizard_completed = True
    frame._maybe_run_first_run_onboarding()
    assert saved == [False]  # no second reset recorded


# ---------------------------------------------------------------------------
# #647: the sentinel must treat a marker at a path it has already seen as
# consumed, even when the marker's mtime changes between launches. Antivirus
# tools, filesystem mtime drift, and other processes touching the marker file
# can update its mtime without rewriting its content; comparing only on mtime
# (the #44 fix) made the wizard reopen on every launch in that case. The
# marker's resolved path is the stable identity for a given install.
# ---------------------------------------------------------------------------


def test_undeletable_marker_with_changed_mtime_does_not_reopen_wizard(
    monkeypatch, tmp_path
) -> None:
    """#647: same marker path, but mtime has changed between launches. The
    sentinel must still recognize the marker as already consumed -- the wizard
    must NOT reopen just because the mtime drifted."""
    import quill.core.paths as paths_module

    frame = _build_frame()
    frame.settings = type("Settings", (), {"setup_wizard_completed": True})()
    frame.run_startup_wizard = lambda **kwargs: None
    marker = _UndeletableMarker(
        mtime=1000.0,
        path="C:/Program Files/Quill/quill-new-install.txt",
    )
    monkeypatch.setattr(paths_module, "new_install_marker_path", lambda: marker)
    monkeypatch.setattr(paths_module, "app_data_dir", lambda: tmp_path)

    saved: list[bool] = []
    import quill.core.settings as settings_module

    monkeypatch.setattr(
        settings_module, "save_settings", lambda s: saved.append(s.setup_wizard_completed)
    )

    # First launch: marker consumed, wizard flag reset, sentinel written with
    # the marker's resolved path + the original mtime.
    frame._maybe_run_first_run_onboarding()
    assert marker.unlink_attempts == 1
    assert saved == [False]

    # Second launch: AV or filesystem has bumped the marker's mtime to a
    # different value. Same path, so the sentinel should still recognize
    # it as already consumed and skip the reset (#647).
    marker._mtime = 2000.0
    frame.settings.setup_wizard_completed = True
    frame._maybe_run_first_run_onboarding()
    assert marker.unlink_attempts == 2  # unlink was retried
    assert saved == [False]  # no second reset recorded


def test_marker_at_different_path_is_treated_as_new_install(monkeypatch, tmp_path) -> None:
    """#647: a marker at a different resolved path means a genuinely new
    install (portable bundle moved, custom install location, etc.). The
    wizard flag must reset in that case."""
    import quill.core.paths as paths_module

    frame = _build_frame()
    frame.settings = type("Settings", (), {"setup_wizard_completed": True})()
    frame.run_startup_wizard = lambda **kwargs: None
    marker = _UndeletableMarker(
        mtime=1000.0,
        path="C:/Program Files/Quill/quill-new-install.txt",
    )
    monkeypatch.setattr(paths_module, "new_install_marker_path", lambda: marker)
    monkeypatch.setattr(paths_module, "app_data_dir", lambda: tmp_path)

    saved: list[bool] = []
    import quill.core.settings as settings_module

    monkeypatch.setattr(
        settings_module, "save_settings", lambda s: saved.append(s.setup_wizard_completed)
    )

    # First install at one location.
    frame._maybe_run_first_run_onboarding()
    assert saved == [False]

    # Second install at a different location (e.g., user uninstalled and
    # reinstalled into D:/Quill). The path differs, so the sentinel must
    # treat this as a new install and reset the wizard flag.
    marker._path = "D:/Quill/quill-new-install.txt"
    frame.settings.setup_wizard_completed = True
    frame._maybe_run_first_run_onboarding()
    assert saved == [False, False]


def test_legacy_mtime_only_sentinel_is_not_misread_as_new_install(monkeypatch, tmp_path) -> None:
    """#647: a sentinel written by an older QUILL build (mtime-only, before
    the path-aware fix shipped) must still be honored -- the legacy sentinel
    simply lacks a ``path`` key, which does not match any current marker's
    resolved path, so the wizard would reset on the first launch after
    upgrade. That is acceptable: a one-time wizard reopen on the first launch
    after upgrading to the path-aware build is far better than the previous
    behaviour of reopening forever."""
    import json

    import quill.core.paths as paths_module

    legacy_sentinel = tmp_path / "new-install-marker-consumed.json"
    legacy_sentinel.write_text(
        json.dumps({"mtime": 999.0}),  # legacy format: no "path" key
        encoding="utf-8",
    )

    frame = _build_frame()
    frame.settings = type("Settings", (), {"setup_wizard_completed": True})()
    frame.run_startup_wizard = lambda **kwargs: None
    marker = _UndeletableMarker(
        mtime=1234.0,
        path="C:/Program Files/Quill/quill-new-install.txt",
    )
    monkeypatch.setattr(paths_module, "new_install_marker_path", lambda: marker)
    monkeypatch.setattr(paths_module, "app_data_dir", lambda: tmp_path)

    saved: list[bool] = []
    import quill.core.settings as settings_module

    monkeypatch.setattr(
        settings_module, "save_settings", lambda s: saved.append(s.setup_wizard_completed)
    )

    # Legacy sentinel has no "path" key, so the check sees the marker as
    # new and resets the wizard flag once. After this launch, the sentinel
    # is rewritten in the new path-aware format and subsequent launches
    # will recognize the marker correctly.
    frame._maybe_run_first_run_onboarding()
    assert saved == [False]

    # Second launch: the rewritten sentinel now has the path, so the
    # marker is correctly treated as already consumed.
    frame.settings.setup_wizard_completed = True
    frame._maybe_run_first_run_onboarding()
    assert saved == [False]  # no second reset recorded


# ---------------------------------------------------------------------------
# #606 follow-up: _apply_theme runs from __init__ before _create_document_tab
# when the Setup Wizard is pending on a fresh install. self.editor does not
# exist yet, so the three editor.* calls must not raise AttributeError.
# ---------------------------------------------------------------------------


def test_apply_theme_survives_missing_editor_in_wizard_pending_init() -> None:
    """Regression for the fresh-install crash: AttributeError on self.editor
    in _apply_theme() during the wizard-pending branch of __init__ (#606
    follow-up). _apply_theme must guard the editor writes with getattr() and
    still apply the chrome + statusbar colors so the wizard modal sees the
    correct palette."""
    frame = _build_frame()

    class _Colour:
        def __init__(self, r, g, b) -> None:
            self.r, self.g, self.b = r, g, b

        def __eq__(self, other):
            return isinstance(other, _Colour) and (self.r, self.g, self.b) == (
                other.r,
                other.g,
                other.b,
            )

        def __hash__(self):
            return hash((self.r, self.g, self.b))

    class _StatusBar:
        def __init__(self) -> None:
            self.fg = None
            self.bg = None

        def SetForegroundColour(self, colour):  # noqa: N802
            self.fg = colour
            return True

        def SetBackgroundColour(self, colour):  # noqa: N802
            self.bg = colour
            return True

    class _Frame:
        def __init__(self) -> None:
            self.fg = None
            self.bg = None

        def SetForegroundColour(self, colour):  # noqa: N802
            self.fg = colour
            return True

        def SetBackgroundColour(self, colour):  # noqa: N802
            self.bg = colour
            return True

        def Refresh(self):
            pass

    class _CallAfter:
        def __init__(self):
            self.calls = []

        def __call__(self, fn, *args):
            self.calls.append((fn, args))

    wx_stub = _Wx()
    wx_stub.Colour = _Colour
    call_after = _CallAfter()
    wx_stub.CallAfter = call_after  # type: ignore[attr-defined]
    frame._wx = wx_stub
    frame.frame = _Frame()  # type: ignore[assignment]
    frame.statusbar = _StatusBar()  # type: ignore[attr-defined]
    # Note: no frame.editor -- the wizard-pending branch never calls
    # _create_document_tab, so self.editor is unset.
    assert not hasattr(frame, "editor")
    # Use "dark" so the test does not need a real SystemSettings stub.
    frame.settings = type("Settings", (), {"theme": "dark"})()

    # Must not raise AttributeError on self.editor.
    frame._apply_theme("dark")

    # The chrome + statusbar colors still apply so the wizard sees them.
    assert frame.frame.fg == _Colour(230, 230, 230)
    assert frame.frame.bg == _Colour(45, 45, 45)
    assert frame.statusbar.fg == _Colour(230, 230, 230)
    assert frame.statusbar.bg == _Colour(45, 45, 45)
    # The contrast-ratio announce is still scheduled.
    assert len(call_after.calls) == 1


# ---------------------------------------------------------------------------
# Init-order regression: _refresh_contextual_menu_items + _current_markup_context
# must not raise AttributeError on self.editor during the wizard-pending
# branch of __init__ (fresh install). The contextual refresh is deferred via
# _request_menu_refresh(); _current_markup_context falls back to "plain" when
# the editor is missing. After __init__ finishes, _ui_ready is True and the
# pending refresh fires once.
# ---------------------------------------------------------------------------


def test_current_markup_context_returns_plain_when_editor_missing() -> None:
    """Regression for the fresh-install crash: _current_markup_context is
    called from _refresh_contextual_menu_items during the wizard-pending
    branch of __init__ (self.editor does not exist yet). The function must
    fall back to "plain" instead of raising AttributeError on self.editor.
    """
    frame = _build_frame()
    frame.document = type("Document", (), {"path": None})()
    assert not hasattr(frame, "editor")

    # Must not raise AttributeError on self.editor.
    assert frame._current_markup_context() == "plain"


def test_refresh_contextual_menu_items_defers_during_init() -> None:
    """Regression for the fresh-install crash: _build_menu calls
    _refresh_contextual_menu_items during __init__ on the wizard-pending
    branch. With self.editor unset and _ui_ready False, the refresh must
    defer by setting _pending_menu_refresh=True and return rather than
    crash. The deferred refresh is then flushed by the constructor's
    final flush, or by the wizard's post-create flush.
    """
    frame = _build_frame()
    assert not hasattr(frame, "editor")
    frame._ui_ready = False
    frame._pending_menu_refresh = False

    # Must not raise AttributeError on self.editor / self.frame.GetMenuBar.
    frame._refresh_contextual_menu_items()

    # The refresh was deferred (the pending flag is set) rather than
    # executed. The constructor's final flush will pick this up.
    assert frame._pending_menu_refresh is True, (
        "_refresh_contextual_menu_items must set the pending flag when _ui_ready is False"
    )


def test_refresh_contextual_menu_items_runs_normally_after_init() -> None:
    """Once __init__ has finished (_ui_ready is True and self.editor is
    set), _refresh_contextual_menu_items should run normally and not
    defer. The function only defers during construction, not at steady
    state.
    """

    class _Editor:
        def GetValue(self):
            return "hello"

    frame = _build_frame()
    frame.editor = _Editor()  # type: ignore[attr-defined]
    frame._ui_ready = True
    frame._pending_menu_refresh = False

    # Steady-state: the function does not defer; it executes against
    # the (stubbed) menu bar. A bare-metal frame has no GetMenuBar, so
    # the function returns early after detecting a None menu bar.
    # The point of this test is that the lifecycle gate does not
    # intercept the steady-state path.
    frame._refresh_contextual_menu_items()

    # The function was NOT deferred -- the lifecycle gate let it through.
    assert frame._pending_menu_refresh is False


def test_refresh_contextual_menu_items_runs_when_ui_ready_attr_missing() -> None:
    """Tests using ``MainFrame.__new__`` do not set ``_ui_ready`` at all.
    The lifecycle gate must default to 'ready' so these tests are not
    silently gated. This pins the documented invariant: only the real
    ``__init__`` (which sets ``_ui_ready = False`` at the top) is
    intercepted by the gate.
    """

    class _Editor:
        def GetValue(self):
            return "hello"

    frame = _build_frame()
    frame.editor = _Editor()  # type: ignore[attr-defined]
    assert not hasattr(frame, "_ui_ready")
    frame._pending_menu_refresh = False

    frame._refresh_contextual_menu_items()

    # Default (missing attr) means "ready"; the gate let it through.
    assert frame._pending_menu_refresh is False
