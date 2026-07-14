from __future__ import annotations

from pathlib import Path

import pytest

import quill.core.updates as updates_module
import quill.ui.main_frame as main_frame_module
from quill.core.document import Document
from quill.core.notifications import Notification
from quill.core.updates import GitHubRelease, UpdateManifest
from quill.ui.main_frame import MainFrame


@pytest.fixture(autouse=True)
def _force_non_portable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin check_for_updates onto the installer (non-portable) path.

    ``check_for_updates`` branches on ``running_portable()``, which sniffs the
    filesystem/env for a portable bundle. In a full-suite run that ambient state
    can be left set by an earlier test, flipping these tests onto the GitHub
    releases path they do not stub (manifest -> None -> live fetch_releases).
    These unit tests exercise the installer flow, so they must control that
    branch explicitly rather than depend on detection.

    Patched on ``quill.core.updates`` (the source module) rather than
    ``quill.ui.main_frame``: ``check_for_updates``/``_on_update_fetch_done``
    import these names locally (perf: lazy-import quill.core.updates), so
    patching the consumer's namespace no longer has any effect.
    """
    monkeypatch.setattr(updates_module, "running_portable", lambda: False)


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


def test_report_bug_failure_copies_support_url_and_reports_plainly(monkeypatch) -> None:
    # The legacy built-in form is gone (feedback_hub ships with QUILL), so a
    # hub failure must still leave the user a path: the online support-form
    # URL lands on the clipboard and a message box says so out loud.
    frame = _build_frame()
    copied: list[str] = []
    boxes: list[tuple[str, str]] = []

    def _boom() -> None:
        raise RuntimeError("hub exploded")

    monkeypatch.setattr(frame, "_report_bug_via_hub", _boom)
    monkeypatch.setattr(frame, "_copy_to_clipboard", lambda text: copied.append(text) or True)
    frame._show_message_box = lambda message, caption, _style: boxes.append((message, caption))
    frame._wx = type(
        "Wx",
        (),
        {"version": staticmethod(lambda: "4.2-test"), "OK": 4, "ICON_ERROR": 512},
    )()

    frame.report_bug()

    assert len(copied) == 1
    assert copied[0].startswith("https://github.com/Community-Access/support/issues/new?")
    assert boxes and boxes[0][1] == "Report a Bug"
    assert "copied to your clipboard" in boxes[0][0]


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
        updates_module,
        "fetch_update_manifest",
        lambda *_a, **_k: UpdateManifest(
            version="0.1.1",
            download_url="https://example.com/Quill-Setup-0.1.1.exe",
            published_at="2026-05-30T00:00:00Z",
            notes="Patch update",
            signature="sig",
        ),
    )
    monkeypatch.setattr(updates_module, "is_newer_version", lambda _current, _available: True)
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
        updates_module,
        "fetch_update_manifest",
        lambda *_a, **_k: UpdateManifest(
            version="0.1.1",
            download_url="https://example.com/Quill-Setup-0.1.1.exe",
            published_at="2026-05-30T00:00:00Z",
            notes="Patch update",
            signature="sig",
        ),
    )
    monkeypatch.setattr(updates_module, "is_newer_version", lambda _current, _available: True)
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
        updates_module,
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
    monkeypatch.setattr(updates_module, "fetch_releases", lambda: [release])
    frame._download_update_release = lambda _release: (_ for _ in ()).throw(
        AssertionError("a skipped version must not download")
    )

    frame.check_for_updates(silent_no_update=True)

    assert frame._notification == ("Update 9.9.9 available (skipped by you)", "update")
