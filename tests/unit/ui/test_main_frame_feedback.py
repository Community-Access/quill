from __future__ import annotations

from pathlib import Path

import quill.ui.main_frame as main_frame_module
from quill.core.document import Document
from quill.core.notifications import Notification
from quill.core.updates import GitHubRelease, UpdateManifest
from quill.ui.main_frame import MainFrame


class _Frame:
    pass


def _build_frame() -> MainFrame:
    frame = MainFrame.__new__(MainFrame)
    frame.frame = _Frame()
    frame.document = Document(path=Path("note.md"), text="hello")
    frame.settings = type("Settings", (), {})()
    frame.keymap = {"file.open": "Ctrl+O"}
    frame._notifications = []
    frame._wx = type("Wx", (), {"version": staticmethod(lambda: "4.2-test")})()
    frame._set_status = lambda message: setattr(frame, "_status_message", message)
    frame._record_notification = lambda message, category="info": setattr(
        frame, "_notification", (message, category)
    )
    frame._announce = lambda *_args, **_kwargs: None
    return frame


def test_report_bug_feedback_hub_path_goes_through_show_modal_dialog(monkeypatch) -> None:
    import sys

    frame = _build_frame()
    frame._wx = type("Wx", (), {"version": staticmethod(lambda: "4.2-test"), "ID_OK": 5100})()

    modal_calls: list[str] = []
    frame._show_modal_dialog = lambda _dlg, label, **_kw: (
        modal_calls.append(label) or frame._wx.ID_OK
    )

    monkeypatch.setattr(frame, "_feedback_hub_available", lambda: True)

    class _FakeSchema:
        pass

    class _FakeDialog:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def ShowModal(self) -> int:
            raise AssertionError("ShowModal must not be called directly on FeedbackDialog")

        def Destroy(self) -> None:
            pass

    import types

    fake_hub = types.ModuleType("feedback_hub")
    fake_hub.load_schema = lambda _path: _FakeSchema()  # type: ignore[attr-defined]
    fake_wx_dialog = types.ModuleType("feedback_hub.wx_dialog")
    fake_wx_dialog.FeedbackDialog = _FakeDialog  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "feedback_hub", fake_hub)
    monkeypatch.setitem(sys.modules, "feedback_hub.wx_dialog", fake_wx_dialog)

    frame.report_bug()

    assert modal_calls == ["Report an Issue"]
    assert frame._notification == ("Submitted feedback via feedback hub", "support")


def test_report_bug_falls_back_to_legacy_when_hub_raises(monkeypatch) -> None:
    # A broken/incompatible feedback_hub must not strand the user without a
    # report dialog (#210 follow-up): report_bug falls back to the built-in form.
    frame = _build_frame()
    monkeypatch.setattr(frame, "_feedback_hub_available", lambda: True)

    def _boom() -> None:
        raise RuntimeError("hub exploded")

    monkeypatch.setattr(frame, "_report_bug_via_hub", _boom)
    legacy_called: list[bool] = []
    monkeypatch.setattr(frame, "_report_bug_legacy", lambda: legacy_called.append(True))

    frame.report_bug()

    assert legacy_called == [True]
    assert frame._status_message == "Report a Bug: using the built-in form"


def test_report_bug_reviews_then_opens_support_form(monkeypatch) -> None:
    # #618: the auto-open-browser step is opt-in via the
    # report_bug_auto_open_browser setting (default False in 0.7.0).
    # This test exercises the opt-in path.
    frame = _build_frame()
    frame.settings.report_bug_auto_open_browser = True
    opened: list[str] = []
    copied: list[str] = []
    monkeypatch.setattr(frame, "_feedback_hub_available", lambda: False)
    monkeypatch.setattr(
        frame,
        "_review_bug_report",
        lambda: ({"summary": "Bug report: note.md", "body": "Body"}, "https://example.invalid"),
    )
    monkeypatch.setattr(frame, "_copy_to_clipboard", lambda text: copied.append(text) or True)
    monkeypatch.setattr("quill.ui.main_frame.webbrowser.open", lambda url: opened.append(url))

    frame.report_bug()

    assert copied == ["Body"]
    assert opened == ["https://example.invalid"]
    assert frame._notification == ("Opened support-hub bug report form", "support")


def test_report_bug_includes_diagnostics_path_when_present(monkeypatch) -> None:
    # #618: opt-in auto-open-browser to test the diagnostics-bundle path.
    frame = _build_frame()
    frame.settings.report_bug_auto_open_browser = True
    opened: list[str] = []
    copied: list[str] = []
    frame._last_bug_report_diagnostics_path = Path(r"C:\Temp\quill-diagnostics.zip")
    monkeypatch.setattr(frame, "_feedback_hub_available", lambda: False)
    monkeypatch.setattr(
        frame,
        "_review_bug_report",
        lambda: ({"summary": "Bug report: note.md", "body": "Body"}, "https://example.invalid"),
    )
    monkeypatch.setattr(frame, "_copy_to_clipboard", lambda text: copied.append(text) or True)
    monkeypatch.setattr("quill.ui.main_frame.webbrowser.open", lambda url: opened.append(url))

    frame.report_bug()

    assert copied[0].startswith("Body")
    assert "Diagnostics bundle path" in copied[0]
    assert "quill-diagnostics.zip" in copied[0]
    assert opened == ["https://example.invalid"]


def test_report_bug_does_not_open_browser_by_default(monkeypatch) -> None:
    # #618: 0.7.0 default is "Quill copies, you decide whether to open the
    # browser". The browser must NOT open when report_bug_auto_open_browser
    # is False (the default). The clipboard still receives the report.
    frame = _build_frame()
    opened: list[str] = []
    copied: list[str] = []
    monkeypatch.setattr(frame, "_feedback_hub_available", lambda: False)
    monkeypatch.setattr(
        frame,
        "_review_bug_report",
        lambda: ({"summary": "Bug report: note.md", "body": "Body"}, "https://example.invalid"),
    )
    monkeypatch.setattr(frame, "_copy_to_clipboard", lambda text: copied.append(text) or True)
    monkeypatch.setattr("quill.ui.main_frame.webbrowser.open", lambda url: opened.append(url))

    frame.report_bug()

    assert copied == ["Body"], "report must always be copied to the clipboard"
    assert opened == [], "browser must NOT open when auto_open_browser is False"
    assert frame._notification == ("Copied support-hub bug report to clipboard", "support")


def test_save_diagnostics_bundle_cancels_when_review_cancelled(monkeypatch) -> None:
    frame = _build_frame()
    monkeypatch.setattr(frame, "_review_diagnostics_export", lambda: None)

    frame.save_diagnostics_bundle()

    assert frame._status_message == "Diagnostics export cancelled"


def test_open_logs_folder_uses_app_data_logs_path(monkeypatch, tmp_path: Path) -> None:
    frame = _build_frame()
    revealed: list[Path] = []
    root = tmp_path / "Quill"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        main_frame_module,
        "app_data_dir",
        lambda: root,
    )
    monkeypatch.setattr(frame, "_reveal_in_explorer", lambda path: revealed.append(path))

    frame.open_logs_folder()

    assert revealed == [root / "logs"]


def test_open_diagnostics_folder_uses_app_data_diagnostics_path(
    monkeypatch, tmp_path: Path
) -> None:
    frame = _build_frame()
    revealed: list[Path] = []
    root = tmp_path / "Quill"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        main_frame_module,
        "app_data_dir",
        lambda: root,
    )
    monkeypatch.setattr(frame, "_reveal_in_explorer", lambda path: revealed.append(path))

    frame.open_diagnostics_folder()

    assert revealed == [root / "diagnostics"]


def test_open_notifications_clears_from_dialog_action(monkeypatch) -> None:
    frame = _build_frame()
    frame._notifications = [Notification.create("Saved diagnostics to quill.zip", "diagnostics")]
    frame._wx = type("Wx", (), {"ID_CLEAR": 1001})()
    monkeypatch.setattr(frame, "_show_notifications_dialog", lambda: 1001)
    called = {"cleared": False}
    monkeypatch.setattr(
        "quill.ui.main_frame.clear_notifications",
        lambda: called.__setitem__("cleared", True),
    )

    frame.open_notifications()

    assert called["cleared"] is True
    assert frame._notifications == []
    assert frame._status_message == "Cleared notifications"


def test_open_notifications_marks_viewed_when_not_cleared(monkeypatch) -> None:
    frame = _build_frame()
    frame._notifications = [Notification.create("Recovered autosave snapshot", "recovery")]
    frame._wx = type("Wx", (), {"ID_CLEAR": 1001})()
    monkeypatch.setattr(frame, "_show_notifications_dialog", lambda: 1000)

    frame.open_notifications()

    assert frame._status_message == "Viewed notifications"


def test_open_notifications_reports_empty_state(monkeypatch) -> None:
    frame = _build_frame()
    frame._notifications = []
    frame._wx = type("Wx", (), {"ID_CLEAR": 1001})()
    monkeypatch.setattr(frame, "_show_notifications_dialog", lambda: 1000)

    frame.open_notifications()

    assert frame._status_message == "No notifications"


def test_dictionary_status_uses_friendly_not_created_wording(monkeypatch) -> None:
    frame = _build_frame()
    frame.document = Document(path=None, text="hello")
    frame._wx = type("Wx", (), {"ICON_INFORMATION": 1, "OK": 1})()
    captured: dict[str, str] = {}
    frame._show_message_box = lambda message, *_args: captured.setdefault("message", message)

    monkeypatch.setattr(
        main_frame_module,
        "load_scope_dictionary",
        lambda *_args, **_kwargs: set(),
    )
    monkeypatch.setattr(
        main_frame_module,
        "app_data_dir",
        lambda: Path(r"C:\Users\tester\AppData\Roaming\Quill"),
    )
    backend = type("Backend", (), {"name": "enchant", "detail": "en_US (hunspell)"})()
    monkeypatch.setattr(main_frame_module, "spellcheck_backend_info", lambda: backend)
    monkeypatch.setattr(main_frame_module.thesaurus_engine, "is_available", lambda: True)
    monkeypatch.setattr(
        main_frame_module.thesaurus_engine,
        "data_path",
        lambda: Path(r"C:\quill\python\Lib\site-packages\quill\data\th_en_US_v2.dat"),
    )

    frame.show_dictionary_status()

    message = captured["message"]
    assert "missing:" not in message
    assert "not created yet" in message
    assert "not available until the current document is saved" in message


def test_check_for_updates_can_close_app_before_installer(monkeypatch) -> None:
    frame = _build_frame()
    frame._wx = type(
        "Wx",
        (),
        {"ICON_INFORMATION": 1, "ICON_ERROR": 2, "OK": 4, "YES_NO": 8, "NO_DEFAULT": 16, "YES": 32},
    )()
    prompts = iter([frame._wx.YES, frame._wx.YES])
    frame._show_message_box = lambda *_args, **_kwargs: next(prompts)
    frame._can_close_all_documents = lambda: True
    exits: list[str] = []
    frame.exit_app = lambda: exits.append("exit")
    opened: list[str] = []
    monkeypatch.setattr(
        main_frame_module,
        "fetch_update_manifest",
        lambda *_a, **_k: UpdateManifest(
            version="0.1.1",
            download_url="https://example.com/Quill-Setup-0.1.1.exe",
            published_at="2026-05-30T00:00:00Z",
            notes="Patch update",
            signature="sig",
        ),
    )
    monkeypatch.setattr(main_frame_module, "is_newer_version", lambda _current, _available: True)
    monkeypatch.setattr(
        "quill.ui.main_frame.webbrowser.open",
        lambda url: opened.append(url) or True,
    )

    frame.check_for_updates()

    assert opened == ["https://example.com/Quill-Setup-0.1.1.exe"]
    assert exits == ["exit"]
    assert frame._status_message == "Closing Quill for update 0.1.1"


def test_check_for_updates_allows_download_without_immediate_exit(monkeypatch) -> None:
    frame = _build_frame()
    frame._wx = type(
        "Wx",
        (),
        {"ICON_INFORMATION": 1, "ICON_ERROR": 2, "OK": 4, "YES_NO": 8, "NO_DEFAULT": 16, "YES": 32},
    )()
    prompts = iter([frame._wx.YES, 0])
    frame._show_message_box = lambda *_args, **_kwargs: next(prompts)
    frame._can_close_all_documents = lambda: True
    frame.exit_app = lambda: (_ for _ in ()).throw(AssertionError("exit_app should not be called"))
    opened: list[str] = []
    monkeypatch.setattr(
        main_frame_module,
        "fetch_update_manifest",
        lambda *_a, **_k: UpdateManifest(
            version="0.1.1",
            download_url="https://example.com/Quill-Setup-0.1.1.exe",
            published_at="2026-05-30T00:00:00Z",
            notes="Patch update",
            signature="sig",
        ),
    )
    monkeypatch.setattr(main_frame_module, "is_newer_version", lambda _current, _available: True)
    monkeypatch.setattr(
        "quill.ui.main_frame.webbrowser.open",
        lambda url: opened.append(url) or True,
    )

    frame.check_for_updates()

    assert opened == ["https://example.com/Quill-Setup-0.1.1.exe"]
    assert frame._status_message == "Opened download page for 0.1.1"


def test_update_check_due_throttles_recent_checks() -> None:
    from datetime import UTC, datetime, timedelta

    frame = _build_frame()
    frame.settings.last_update_check = ""
    assert frame._update_check_due() is True

    frame.settings.last_update_check = datetime.now(UTC).isoformat()
    assert frame._update_check_due() is False

    frame.settings.last_update_check = (datetime.now(UTC) - timedelta(hours=48)).isoformat()
    assert frame._update_check_due() is True


def test_skip_update_version_records_choice(monkeypatch) -> None:
    frame = _build_frame()
    frame.settings.skipped_update_version = ""
    frame._announce = lambda *_args, **_kwargs: None
    monkeypatch.setattr(main_frame_module, "save_settings", lambda _settings: None)

    frame._skip_update_version("0.2.0")

    assert frame.settings.skipped_update_version == "0.2.0"
    assert frame._status_message == "Skipping update 0.2.0"
    assert frame._notification == ("Update 0.2.0 skipped", "update")


def test_check_for_updates_silent_honors_skipped_version(monkeypatch) -> None:
    frame = _build_frame()
    frame.settings.beta_updates = False
    # The skipped version must be NEWER than the running build, otherwise
    # is_newer_version returns False and the "skipped by you" branch is
    # never reached. 9.9.9 is a sentinel that sorts after every shipped
    # version regardless of when this test runs.
    frame.settings.skipped_update_version = "9.9.9"
    frame.settings.last_update_check = ""
    monkeypatch.setattr(main_frame_module, "save_settings", lambda _settings: None)
    monkeypatch.setattr(
        main_frame_module,
        "fetch_update_manifest",
        lambda *_a, **_k: (_ for _ in ()).throw(main_frame_module.URLError("offline")),
    )
    release = GitHubRelease(
        version="9.9.9",
        download_url="https://github.com/releases/download/x/Quill.exe",
        published_at="2026-06-01",
        notes="New",
        prerelease=False,
    )
    monkeypatch.setattr(main_frame_module, "fetch_releases", lambda: [release])
    frame._download_update_release = lambda _release: (_ for _ in ()).throw(
        AssertionError("a skipped version must not download")
    )

    frame.check_for_updates(silent_no_update=True)

    assert frame._notification == ("Update 9.9.9 available (skipped by you)", "update")
