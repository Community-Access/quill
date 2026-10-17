"""Quill Converter's Auphonic backlog windows and commands, without the network.

Production History, the account view, and Process with Auphonic's two option
windows (post-MVP, PRD section 14). The commands run on a stand-in host, the
windows are built in memory and never shown modally, and Auphonic is a fake:
nothing here can reach the network or the real credential store.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import wx

from quill.apps import converter_auphonic, converter_auphonic_history
from quill.apps.converter_auphonic import ConverterAuphonicMixin
from quill.core.converter_settings import ConverterSettings
from quill.core.publish import auphonic_history, auphonic_plan, auphonic_run
from quill.core.publish.auphonic import ProductionStatus
from quill.core.publish.auphonic_account import AccountDetails, RemoteProduction
from quill.core.publish.auphonic_history import (
    SAVED,
    HistoryEntry,
    load_history,
    record_sent,
    save_history,
)
from quill.core.publish.auphonic_options import CustomProcessing
from quill.core.publish.auphonic_plan import CUSTOM, AuphonicChoices, PendingProduction
from quill.ui import converter_auphonic_dialog as dialogs
from quill.ui import converter_auphonic_history_dialog as history_ui
from quill.ui import converter_auphonic_options_dialog as options_ui
from tests.wx_session import patch_call_after, shared_wx_app


@pytest.fixture()
def wx_app():
    app = shared_wx_app()
    from quill.ui.app_context_help import ensure_help_provider

    ensure_help_provider(wx)  # SetHelpText stores nothing without one
    yield app
    app.Destroy()


class _Client:
    """A fake Auphonic: a finished production with one sound file."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def production_status(self, token: str, uuid: str) -> ProductionStatus:
        self.calls.append(f"status {uuid}")
        url = "https://auphonic.com/api/download/r.mp3"
        return ProductionStatus(uuid, 3, "Done", [{"format": "mp3", "download_url": url}])

    def audio_results(self, status: ProductionStatus) -> tuple[ProductionStatus, int]:
        from quill.core.publish.auphonic import audio_results

        return audio_results(status)

    def download_results(self, token: str, status: Any, out_dir: Path, **_k: Any) -> list[Path]:
        from quill.core.publish.auphonic import _unused_path

        self.calls.append("download")
        out_dir.mkdir(parents=True, exist_ok=True)
        target = _unused_path(out_dir / "r.mp3")
        target.write_bytes(b"done")
        return [target]


class _Host(ConverterAuphonicMixin):
    """Just enough of the Converter window for the backlog commands."""

    def __init__(self, tmp_path: Path) -> None:
        self._safe_mode = False
        self._busy = False
        self._cancel: Any = None
        self._entries: list[Any] = []
        self._settings = ConverterSettings()
        self.frame = None
        self.dest = tmp_path / "out"
        self._last_report = ""
        self._last_output: Path | None = None
        self.said: list[str] = []
        self.boxes: list[str] = []
        self.began: list[str] = []

    def _announce(self, text: str, **_k: Any) -> None:
        self.said.append(text)

    def _show_message_box(self, text: str, *_a: Any, **_k: Any) -> int:
        self.boxes.append(text)
        return wx.ID_OK

    def _set_status(self, text: str) -> None:
        pass

    def _destination(self) -> Path:
        return self.dest

    def _begin_work(self, label: str, cancel: Any) -> None:
        self.began.append(label)
        self._busy = True

    def _end_work(self) -> None:
        self._busy = False

    def _note_progress(self, text: str, current: int, total: int) -> None:
        pass

    def open_output_folder(self) -> None:
        pass


class _NowThread:
    def __init__(self, target: Any, **_k: Any) -> None:
        self._target = target

    def start(self) -> None:
        self._target()


@pytest.fixture()
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    client = _Client()
    history = tmp_path / "data" / "converter" / "auphonic_history.json"
    monkeypatch.setattr(auphonic_run, "_default_client", lambda: client)
    monkeypatch.setattr(auphonic_plan, "pending_path", lambda _d=None: tmp_path / "pending.json")
    monkeypatch.setattr(auphonic_history, "history_path", lambda _d=None: history)
    monkeypatch.setattr(converter_auphonic, "load_token", lambda: "stored-token")
    monkeypatch.setattr(converter_auphonic.threading, "Thread", _NowThread)
    monkeypatch.setattr(converter_auphonic_history.threading, "Thread", _NowThread)
    patch_call_after(monkeypatch, lambda fn, *a, **k: fn(*a, **k))
    return {"host": _Host(tmp_path), "client": client, "history": history}


def _entry(tmp_path: Path, uuid: str = "U1", title: str = "Talk") -> HistoryEntry:
    return HistoryEntry(uuid, title, inputs=["talk.wav"], out_dir=str(tmp_path / "out" / title))


# -- the commands -------------------------------------------------------------------------


def test_safe_mode_declines_history_and_account(env) -> None:
    host = env["host"]
    host._safe_mode = True
    host.show_auphonic_history()
    host.show_auphonic_account()
    assert host.boxes == ["Processing with Auphonic is unavailable in Safe Mode."] * 2
    assert env["client"].calls == []


def test_opening_the_history_reads_locally_and_closing_contacts_nobody(env, monkeypatch) -> None:
    host = env["host"]
    record_sent(env["history"], PendingProduction("U1", "separate", "Talk", ["t.wav"], "", "x"))
    shown: list[list[str]] = []

    def ask(_host: Any, entries: list[HistoryEntry], **_k: Any) -> None:
        shown.append([e.uuid for e in entries])

    monkeypatch.setattr(history_ui, "ask_history", ask)
    host.show_auphonic_history()
    assert shown == [["U1"]] and env["client"].calls == [] and host.began == []


def test_download_again_is_a_converter_job_that_never_overwrites(
    env, monkeypatch, tmp_path
) -> None:
    host = env["host"]
    entry = _entry(tmp_path)
    save_history(env["history"], [entry])
    folder = Path(entry.out_dir)
    folder.mkdir(parents=True)
    (folder / "r.mp3").write_bytes(b"first")
    monkeypatch.setattr(history_ui, "ask_history", lambda _h, entries, **_k: entries[0])
    host.show_auphonic_history()
    assert host.began == ["Downloading Talk again from Auphonic"]
    assert env["client"].calls == ["status U1", "download"]
    assert (folder / "r.mp3").read_bytes() == b"first" and (folder / "r (2).mp3").exists()
    saved = load_history(env["history"])[0]
    assert saved.state == SAVED and saved.files == [str(folder / "r (2).mp3")]
    assert host.said[-1].startswith("Talk: 1 file saved")


def test_download_again_without_a_token_or_while_busy_says_how(env, monkeypatch, tmp_path) -> None:
    host = env["host"]
    save_history(env["history"], [_entry(tmp_path)])
    monkeypatch.setattr(history_ui, "ask_history", lambda _h, entries, **_k: entries[0])
    host._busy = True
    host.show_auphonic_history()
    assert host.said == ["A job is already running."]
    host._busy = False
    monkeypatch.setattr(converter_auphonic, "load_token", lambda: "")
    host.show_auphonic_history()
    assert "Auphonic Account (Ctrl+Alt+Shift+A)" in host.boxes[-1]
    assert env["client"].calls == []


def test_refresh_merges_the_account_list_off_the_ui_thread(env, monkeypatch, tmp_path) -> None:
    save_history(env["history"], [_entry(tmp_path, "U1")])
    from quill.core.publish import auphonic_account

    monkeypatch.setattr(
        auphonic_account,
        "list_productions",
        lambda token: [
            RemoteProduction("U1", "Talk", 3, "Done"),
            RemoteProduction("W2", "Web", 4, "Audio Processing"),
        ],
    )
    got: list[tuple[Any, str]] = []
    converter_auphonic_history.start_history_refresh(
        env["history"], tmp_path / "dest", lambda entries, words: got.append((entries, words))
    )
    entries, words = got[0]
    assert words == "Auphonic listed 2 recent productions: 1 brought up to date, 1 added."
    assert [e.uuid for e in entries] == ["U1", "W2"]
    assert [e.uuid for e in load_history(env["history"])] == ["U1", "W2"]


def test_refresh_without_a_token_asks_nobody(env, monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(converter_auphonic, "load_token", lambda: "")
    got: list[tuple[Any, str]] = []
    converter_auphonic_history.start_history_refresh(
        env["history"], tmp_path, lambda entries, words: got.append((entries, words))
    )
    assert got[0][0] is None and "Sign in with Convert > Auphonic Account" in got[0][1]


def test_open_folder_says_when_there_is_nothing_to_open(tmp_path) -> None:
    entry = _entry(tmp_path)
    assert "does not exist yet" in converter_auphonic_history.open_results_folder(entry)


def test_sign_out_removes_only_the_family_token(monkeypatch) -> None:
    from quill.core.publish.auphonic import CREDENTIAL_TARGET
    from quill.platform.windows import credential_manager

    removed: list[str] = []
    monkeypatch.setattr(credential_manager, "delete_generic_credential", removed.append)
    converter_auphonic_history.forget_token()
    assert removed == [CREDENTIAL_TARGET]


def test_the_account_details_run_off_the_ui_thread(env, monkeypatch) -> None:
    from quill.core.publish.auphonic import AuphonicError

    monkeypatch.setattr(
        converter_auphonic_history, "account_details", lambda token: AccountDetails(token)
    )
    got: list[tuple[Any, str]] = []
    converter_auphonic_history.start_account_details("tok", lambda i, e: got.append((i, e)))
    assert got == [(AccountDetails("tok"), "")]

    def refuse(token: str) -> Any:
        raise AuphonicError("Auphonic said 401: Unauthorized")

    monkeypatch.setattr(converter_auphonic_history, "account_details", refuse)
    converter_auphonic_history.start_account_details("tok", lambda i, e: got.append((i, e)))
    assert got[-1] == (None, "Auphonic said 401: Unauthorized.")


# -- the history window, built in memory -----------------------------------------------------


def _history_dialog(entries: list[HistoryEntry], **kwargs: Any) -> Any:
    said: list[str] = []
    args: dict[str, Any] = {
        "refresh": lambda _deliver: None,
        "open_folder": lambda _e: "",
        "remove": lambda _e: None,
        "announce": said.append,
    }
    args.update(kwargs)
    dialog = history_ui.AuphonicHistoryDialog(None, entries, **args)
    dialog.said = said
    return dialog


def test_the_history_window_shows_details_and_removes_locally(wx_app, tmp_path) -> None:
    removed: list[str] = []
    entries = [_entry(tmp_path, "U1", "First"), _entry(tmp_path, "U2", "Second")]
    dialog = _history_dialog(entries, remove=lambda e: removed.append(e.uuid))
    try:
        assert dialog._list.GetCount() == 2 and "First: processing" in dialog._list.GetString(0)
        assert "Production: First" in dialog._details.GetValue()
        dialog._list.SetSelection(1)
        dialog._show_details()
        assert "Production: Second" in dialog._details.GetValue()
        dialog.remove_selected()
        assert removed == ["U2"] and [e.uuid for e in dialog.entries()] == ["U1"]
        assert (
            dialog.said[-1] == "Removed Second from the list. It is still in your Auphonic account."
        )
        dialog.remove_selected()
        assert not dialog.FindWindow(wx.ID_OK).IsEnabled()
        assert "No productions yet" in dialog._details.GetValue()
    finally:
        dialog.Destroy()


def test_the_history_window_refreshes_in_place(wx_app, tmp_path) -> None:
    asked: list[Any] = []
    dialog = _history_dialog([_entry(tmp_path, "U1")], refresh=asked.append)
    try:
        dialog.refresh()
        dialog.refresh()
        assert len(asked) == 1 and dialog.said[-1] == "Still asking Auphonic."
        fresh = [_entry(tmp_path, "W9", "Web"), _entry(tmp_path, "U1")]
        dialog.refreshed(
            fresh, "Auphonic listed 2 recent productions: 1 brought up to date, 1 added."
        )
        assert dialog._list.GetCount() == 2 and dialog.selected().uuid == "U1"  # kept
        dialog.refreshed(None, "Could not refresh from Auphonic: offline.")
        assert dialog._list.GetCount() == 2 and dialog.said[-1].startswith("Could not")
    finally:
        dialog.Destroy()


def test_the_history_window_says_why_a_folder_will_not_open(wx_app, tmp_path) -> None:
    dialog = _history_dialog([_entry(tmp_path)], open_folder=lambda _e: "That folder is gone.")
    try:
        dialog.open_folder()
        assert dialog.said == ["That folder is gone."]
    finally:
        dialog.Destroy()


# -- the account window, built in memory -----------------------------------------------------


def _account_dialog(stored: list[str], **kwargs: Any) -> Any:
    said: list[str] = []
    args: dict[str, Any] = {
        "stored_token": lambda: stored[0] if stored else "",
        "check": lambda _t, _deliver: None,
        "save": lambda token: stored.insert(0, token),
        "forget": stored.clear,
        "confirm_sign_out": lambda: True,
        "announce": said.append,
    }
    args.update(kwargs)
    dialog = history_ui.AuphonicAccountDialog(None, **args)
    dialog.said = said
    return dialog


def test_the_account_window_says_whether_you_are_signed_in(wx_app) -> None:
    dialog = _account_dialog([])
    try:
        assert dialog._details.GetValue().startswith("Not signed in")
        dialog.check_account()
        assert dialog.said[-1] == "Not signed in. Type your API token and choose Sign In first."
    finally:
        dialog.Destroy()


def test_sign_in_stores_a_token_only_when_auphonic_accepts_it(wx_app) -> None:
    stored: list[str] = []
    asked: list[str] = []
    dialog = _account_dialog(stored, check=lambda token, _deliver: asked.append(token))
    try:
        dialog.sign_in()
        assert asked == [] and dialog.said[-1] == "Type or paste your Auphonic API token first."
        dialog._token.SetValue("bad")
        dialog.sign_in()
        dialog.answered(None, "Auphonic said 401: Unauthorized.", "bad", True)
        assert stored == [] and "Sign-in failed; nothing was stored" in dialog._details.GetValue()
        dialog._token.SetValue("good")
        dialog.sign_in()
        details = AccountDetails("jeff", credits=3.0, recharge_hours=0.0)
        dialog.answered(details, "", "good", True)
        assert stored == ["good"] and dialog._token.GetValue() == ""
        text = dialog._details.GetValue()
        assert text.startswith("Signed in. The token is stored") and "Account: jeff" in text
        assert asked == ["bad", "good"]
    finally:
        dialog.Destroy()


def test_check_account_uses_the_stored_token_and_shows_the_plan(wx_app) -> None:
    asked: list[str] = []
    dialog = _account_dialog(["tok"], check=lambda token, _deliver: asked.append(token))
    try:
        dialog.check_account()
        assert asked == ["tok"]
        dialog.answered(AccountDetails("jeff", credits=1.5, recharge_hours=2.0), "")
        text = dialog._details.GetValue()
        assert "Credits left: 1.5 hours" in text and "2 hours each month" in text
        dialog.answered(None, "Could not reach Auphonic.")
        assert "The account check failed: Could not reach Auphonic." in dialog._details.GetValue()
    finally:
        dialog.Destroy()


def test_sign_out_asks_first_and_then_removes_the_token(wx_app) -> None:
    stored = ["tok"]
    answer = [False]
    dialog = _account_dialog(stored, confirm_sign_out=lambda: answer[0])
    try:
        dialog.sign_out()
        assert stored == ["tok"]  # declined: nothing removed
        answer[0] = True
        dialog.sign_out()
        assert stored == [] and dialog._details.GetValue().startswith("Signed out.")
        dialog.sign_out()
        assert dialog.said[-1] == "Not signed in; there is no token to remove."
    finally:
        dialog.Destroy()


# -- Process with Auphonic's option windows ----------------------------------------------------


def _tags_dialog(**kwargs: Any) -> Any:
    refused: list[str] = []
    args: dict[str, Any] = {
        "artist": "",
        "album": "",
        "cover": "",
        "chapters": None,
        "source_chapters": ((0.0, "Intro"), (65.0, "Talk")),
        "single": True,
        "pick_cover": lambda _parent: "",
        "refuse": refused.append,
    }
    args.update(kwargs)
    dialog = options_ui.AuphonicTagsDialog(None, **args)
    dialog.refused = refused
    return dialog


def test_the_tags_window_reads_back_tags_cover_and_chapters(wx_app, tmp_path) -> None:
    cover = tmp_path / "art.png"
    cover.write_bytes(b"png")
    dialog = _tags_dialog(pick_cover=lambda _p: str(cover))
    try:
        assert dialog._chapters.GetValue() == "0:00:00 Intro\n0:01:05 Talk"
        assert not dialog._chapters.IsEnabled()  # the file's own until you choose to edit
        dialog._artist.SetValue(" Jeff ")
        dialog.choose_cover()
        assert dialog._cover.GetValue() == str(cover) and dialog._remove.IsEnabled()
        dialog._use_chapters.SetValue(True)
        dialog._sync()
        dialog._chapters.SetValue("0:00 Start\n2:00 End")
        assert dialog.values() == ("Jeff", "", str(cover), ((0.0, "Start"), (120.0, "End")))
        dialog.set_cover("")
        assert dialog._cover.GetValue() == "No cover image" and not dialog._remove.IsEnabled()
    finally:
        dialog.Destroy()


def test_the_tags_window_refuses_a_bad_cover_and_bad_chapters(wx_app, tmp_path) -> None:
    dialog = _tags_dialog()
    try:
        dialog.set_cover(str(tmp_path / "art.gif"))
        assert dialog.refused == ["The cover image must be a JPEG or PNG file."]
        dialog._use_chapters.SetValue(True)
        dialog._sync()
        dialog._chapters.SetValue("no time here")
        skipped: list[bool] = []

        class _Event:
            def Skip(self) -> None:  # noqa: N802 - wx API
                skipped.append(True)

        dialog._on_ok(_Event())
        assert skipped == [] and dialog.refused[-1].startswith("Chapter line 1 needs")
    finally:
        dialog.Destroy()


def test_several_productions_cannot_have_edited_chapters(wx_app) -> None:
    dialog = _tags_dialog(single=False, chapters=((0.0, "A"),))
    try:
        assert not dialog._use_chapters.IsEnabled() and dialog.values()[3] is None
    finally:
        dialog.Destroy()


def test_the_more_options_window_reads_back_what_it_says(wx_app) -> None:
    custom = CustomProcessing(leveler=False, loudness=-23, max_peak=-2.0, noise=12)
    dialog = options_ui.AuphonicMoreDialog(
        None, custom=custom, second_format="mp3", transcript=True, language="fr"
    )
    try:
        assert dialog.values() == (custom, "mp3", True, "fr")
        assert dialog._method.IsEnabled() and dialog._language.IsEnabled()
        dialog._noise.SetSelection(0)
        dialog._transcript.SetValue(False)
        dialog._sync()
        assert not dialog._method.IsEnabled() and not dialog._language.IsEnabled()
    finally:
        dialog.Destroy()


def test_process_with_auphonic_keeps_what_the_option_windows_return(wx_app, tmp_path) -> None:
    answers: list[Any] = []

    def show(dialog: Any, title: str) -> int:
        answers.append(title)
        if isinstance(dialog, options_ui.AuphonicTagsDialog):
            dialog._album.SetValue("Season 2")
        else:
            dialog._transcript.SetValue(True)
        return wx.ID_OK

    files = [tmp_path / "a.wav"]
    dialog = dialogs.AuphonicDialog(
        None,
        files,
        skipped=0,
        initial=AuphonicChoices(processing=CUSTOM),
        token="tok",
        check=lambda _t, _d: None,
        announce=lambda _text: None,
        show_modal=show,
    )
    try:
        assert dialog._processing.GetSelection() == 2
        dialog.edit_tags()
        dialog.edit_more()
        got = dialog.choices()
        assert answers == ["Tags, Cover and Chapter Marks", "More Auphonic Options"]
        assert got.album == "Season 2" and got.transcript and got.processing == CUSTOM
        cancelled = dialogs.AuphonicDialog(
            None,
            files,
            skipped=0,
            initial=AuphonicChoices(),
            token="tok",
            check=lambda _t, _d: None,
            announce=lambda _text: None,
            show_modal=lambda _d, _t: wx.ID_CANCEL,
        )
        try:
            cancelled.edit_tags()
            assert cancelled.choices().album == ""  # Cancel changes nothing
        finally:
            cancelled.Destroy()
    finally:
        dialog.Destroy()


def test_every_new_control_explains_itself_on_f1(wx_app, tmp_path) -> None:
    tags = _tags_dialog()
    more = options_ui.AuphonicMoreDialog(
        None, custom=CustomProcessing(), second_format="", transcript=False, language="en"
    )
    history = _history_dialog([_entry(tmp_path)])
    account = _account_dialog([])
    try:
        for window in (tags, more, history, account):
            for child in window.GetChildren():
                if isinstance(child, wx.StaticText):
                    continue
                assert child.GetHelpText().strip(), (window.GetTitle(), child.GetLabel())
    finally:
        for window in (tags, more, history, account):
            window.Destroy()
