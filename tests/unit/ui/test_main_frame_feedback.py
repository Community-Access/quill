from __future__ import annotations

from pathlib import Path
from urllib.error import URLError

import pytest

import quill.core.updates as updates_module
import quill.ui.main_frame as main_frame_module
import quill.ui.main_frame_spellcheck as frame_spellcheck_module
import quill.ui.main_frame_updates as frame_updates_module
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


def test_report_bug_opens_the_shared_support_surface(monkeypatch) -> None:
    """QUILL's Help item is the family flow, not a GitHub issue.

    The old path filed the reporter's own words into a public repository and
    gave them no way to be answered; the rule it broke is in
    docs/design/2026-08-26-feedback-redesign-for-freescout.md. What is pinned
    here is that ``report_bug`` reaches the shared surface at all, and that it
    hands over QUILL's own name -- triage should never have to guess which of
    nine products somebody was running.
    """
    import quill.ui.support_dialog as support_dialog

    calls: list[dict] = []
    monkeypatch.setattr(
        support_dialog,
        "open_support_message",
        lambda host, **kwargs: calls.append({"host": host, **kwargs}),
    )

    frame = _build_frame()
    frame.report_bug()

    assert len(calls) == 1
    assert calls[0]["host"] is frame
    assert calls[0]["source_app"] == "QUILL"


def test_report_bug_carries_the_ai_support_id_like_quill_lite(monkeypatch) -> None:
    """The support form asks its host for ``ai_support_facts``, as in QUILL Lite.

    QUILL gets it from the shared hosted-AI mixin, so the ID support asks for
    first is written into the message without the person looking it up.
    """
    import quill.ui.support_dialog as support_dialog

    built: list[dict] = []

    class _FakeDialog:
        def __init__(self, host, wx, **kwargs):
            built.append(kwargs)

        def show(self) -> None:
            return None

    monkeypatch.setattr(support_dialog, "_SupportDialog", _FakeDialog)
    assert callable(getattr(MainFrame, "ai_support_facts", None))
    frame = _build_frame()
    frame.ai_support_facts = lambda: {"QUILL AI support ID": "SUP-7"}

    frame.report_bug()

    assert built and built[0]["extra"] == {"QUILL AI support ID": "SUP-7"}
    assert built[0]["product"].startswith("QUILL ")


def test_help_menu_item_is_get_help_from_support_on_ctrl_alt_f2() -> None:
    """Command id kept (rebinding survives), label and chord shared with QUILL Lite."""
    from quill.core.keymap import DEFAULT_KEYMAP

    assert DEFAULT_KEYMAP["help.report_bug"] == "Ctrl+Alt+F2"
    menu_source = (
        Path(main_frame_module.__file__).with_name("main_frame_menu.py").read_text(encoding="utf-8")
    )
    assert '_("Get He&lp from Support..."), "help.report_bug"' in menu_source


def test_nothing_in_quill_imports_feedback_hub_or_a_bundled_token() -> None:
    """feedback-hub and the bundled GitHub token are gone from the application."""
    root = Path(main_frame_module.__file__).resolve().parents[1]
    offenders = []
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="replace")
        if (
            "import feedback_hub" in text
            or "from feedback_hub" in text
            or "_feedback_token" in text
            or "quill.core.feedback_token" in text
            or "quill.core.issue_submit" in text
        ):
            offenders.append(str(path.relative_to(root)))
    assert offenders == []


def test_get_help_from_support_is_the_same_flow() -> None:
    """Two names, one implementation: the menu's name and the command id's."""
    assert MainFrame.get_help_from_support is MainFrame.report_bug


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
        frame_spellcheck_module,
        "load_scope_dictionary",
        lambda *_args, **_kwargs: set(),
    )
    monkeypatch.setattr(
        frame_spellcheck_module,
        "app_data_dir",
        lambda: Path(r"C:\Users\tester\AppData\Roaming\Quill"),
    )
    backend = type("Backend", (), {"name": "enchant", "detail": "en_US (hunspell)"})()
    monkeypatch.setattr(frame_spellcheck_module, "spellcheck_backend_info", lambda: backend)
    monkeypatch.setattr(frame_spellcheck_module.thesaurus_engine, "is_available", lambda: True)
    monkeypatch.setattr(
        frame_spellcheck_module.thesaurus_engine,
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
    monkeypatch.setattr(frame_updates_module, "save_settings", lambda _settings: None)

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
    monkeypatch.setattr(frame_updates_module, "save_settings", lambda _settings: None)
    monkeypatch.setattr(
        updates_module,
        "fetch_update_manifest",
        lambda *_a, **_k: (_ for _ in ()).throw(URLError("offline")),
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


def test_check_for_updates_never_offers_the_running_version(monkeypatch) -> None:
    """#919's same-version "self-heal" offer is gone (2026-09-26).

    It reinstalled the running version to restore a bundled GitHub token. No
    build carries that token any more -- support messages and crash reports go
    by email -- so a check that finds only the version already installed must
    offer nothing, interactively or in the background.
    """
    frame = _build_frame()
    frame.settings.beta_updates = False
    frame.settings.skipped_update_version = ""
    frame.settings.last_update_check = ""
    monkeypatch.setattr(frame_updates_module, "save_settings", lambda _settings: None)
    monkeypatch.setattr(
        updates_module,
        "fetch_update_manifest",
        lambda *_a, **_k: (_ for _ in ()).throw(URLError("offline")),
    )
    release = GitHubRelease(
        version="0.9.0",
        download_url="https://example.com/Quill-Setup-0.9.0.exe",
        published_at="2026-07-09",
        notes="Same version.",
        prerelease=False,
    )
    monkeypatch.setattr(updates_module, "fetch_releases", lambda: [release])
    monkeypatch.setattr(updates_module, "is_newer_version", lambda _c, _a: False)

    def _no_offer(*_a, **_k):
        raise AssertionError("the running version must not be offered")

    monkeypatch.setattr(frame, "_show_update_available_dialog", _no_offer)
    monkeypatch.setattr(frame, "_download_update_release", _no_offer)
    frame._html_info = lambda *_a, **_k: None

    frame.check_for_updates(silent_no_update=True)

    assert "token" not in str(getattr(frame, "_notification", ("",))[0])
    assert "token" not in str(getattr(frame, "_status_message", ""))


def test_update_flow_no_longer_reads_a_bundled_token() -> None:
    """Nothing in the update flow asks whether a feedback token is present."""
    source = Path(frame_updates_module.__file__).read_text(encoding="utf-8")
    assert "feedback_token" not in source
    assert "self_heal" not in source
