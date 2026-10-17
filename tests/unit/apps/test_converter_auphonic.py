"""Quill Converter's Process with Auphonic, driven without the network or a real window.

The commands run on a stand-in host (the mixin over a fake shell), so no tray
icon or system-wide hotkey is registered and the module is not
``machine_global``; the dialogs are built in memory and never shown modally.
Auphonic itself is a fake client: nothing here can reach the network.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import wx

from quill.apps import converter_auphonic
from quill.apps.converter_auphonic import ConverterAuphonicMixin
from quill.core.converter_settings import ConverterSettings
from quill.core.publish import auphonic_history, auphonic_plan, auphonic_run
from quill.core.publish.auphonic import ProductionStatus
from quill.core.publish.auphonic_plan import (
    MULTITRACK,
    QUICK_CLEANUP,
    AuphonicChoices,
    PendingProduction,
    Skipped,
    add_pending,
    load_pending,
)
from quill.ui import converter_auphonic_dialog as dialogs
from tests.wx_session import patch_call_after, shared_wx_app


@pytest.fixture()
def wx_app():
    app = shared_wx_app()
    from quill.ui.app_context_help import ensure_help_provider

    ensure_help_provider(wx)  # SetHelpText stores nothing without one
    yield app
    app.Destroy()


class _Client:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def create_production(self, token: str, body: dict[str, object]) -> str:
        self.calls.append(f"create {token}")
        return "U1"

    def upload_input(self, token: str, uuid: str, path: Path, **kwargs: Any) -> None:
        self.calls.append(f"upload {path.name}")
        kwargs["on_bytes"](1, 1)

    def start_created(self, token: str, uuid: str) -> None:
        self.calls.append("start")

    def production_status(self, token: str, uuid: str) -> ProductionStatus:
        self.calls.append("status")
        url = "https://auphonic.com/api/download/r.mp3"
        return ProductionStatus(uuid, 3, "Done", [{"format": "mp3", "download_url": url}])

    def audio_results(self, status: ProductionStatus) -> tuple[ProductionStatus, int]:
        from quill.core.publish.auphonic import audio_results

        return audio_results(status)

    def download_results(self, token: str, status: Any, out_dir: Path, **_k: Any) -> list[Path]:
        self.calls.append("download")
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / "r.mp3"
        target.write_bytes(b"done")
        return [target]


class _Host(ConverterAuphonicMixin):
    """Just enough of the Converter window for the Auphonic commands."""

    def __init__(self, tmp_path: Path, entries: list[Path]) -> None:
        self._safe_mode = False
        self._busy = False
        self._cancel: Any = None
        self._entries = [(path, None) for path in entries]
        self._settings = ConverterSettings()
        self.frame = None
        self.dest = tmp_path / "out"
        self._last_report = ""
        self._last_output: Path | None = None
        self.said: list[str] = []
        self.boxes: list[str] = []
        self.status: list[str] = []
        self.progress: list[str] = []
        self.began: list[str] = []
        self.remembered = 0
        self.opened = False

    def _announce(self, text: str, **_k: Any) -> None:
        self.said.append(text)

    def _show_message_box(self, text: str, *_a: Any, **_k: Any) -> int:
        self.boxes.append(text)
        return wx.ID_OK

    def _set_status(self, text: str) -> None:
        self.status.append(text)

    def _run_background_task(self, label: str, work: Any, on_success: Any) -> None:
        on_success(work(lambda *_a: None))

    def _destination(self) -> Path:
        return self.dest

    def _remember(self) -> None:
        self.remembered += 1

    def _begin_work(self, label: str, cancel: Any) -> None:
        self.began.append(label)
        self._busy, self._cancel = True, cancel

    def _end_work(self) -> None:
        self._busy, self._cancel = False, None

    def _note_progress(self, text: str, current: int, total: int) -> None:
        self.progress.append(text)

    def open_output_folder(self) -> None:
        self.opened = True


class _NowThread:
    def __init__(self, target: Any, **_k: Any) -> None:
        self._target = target

    def start(self) -> None:
        self._target()


@pytest.fixture()
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """A host with two queued files, a fake Auphonic, and nothing threaded."""
    files = []
    for name in ("host.wav", "guest.wav"):
        path = tmp_path / name
        path.write_bytes(b"RIFF....")
        files.append(path)
    client = _Client()
    store = tmp_path / "data" / "converter" / "auphonic_pending.json"
    saved_tokens: list[str] = []
    monkeypatch.setattr(auphonic_run, "_default_client", lambda: client)
    monkeypatch.setattr(auphonic_plan, "pending_path", lambda _d=None: store)
    history = tmp_path / "data" / "converter" / "auphonic_history.json"
    monkeypatch.setattr(auphonic_history, "history_path", lambda _d=None: history)
    monkeypatch.setattr(converter_auphonic, "inspect_files", lambda paths: (paths, [], {}))
    monkeypatch.setattr(converter_auphonic, "load_token", lambda: "stored-token")
    monkeypatch.setattr(converter_auphonic, "save_token", saved_tokens.append)
    monkeypatch.setattr(converter_auphonic.threading, "Thread", _NowThread)
    patch_call_after(monkeypatch, lambda fn, *a, **k: fn(*a, **k))
    host = _Host(tmp_path, files)
    return {
        "host": host,
        "client": client,
        "store": store,
        "history": history,
        "files": files,
        "tokens": saved_tokens,
    }


def _answer(monkeypatch: pytest.MonkeyPatch, choices: Any, *, confirmed: bool = True) -> list[str]:
    """Script the two windows; returns the confirmation texts shown."""
    shown: list[str] = []
    monkeypatch.setattr(dialogs, "ask_choices", lambda *_a, **_k: choices)
    monkeypatch.setattr(dialogs, "confirm", lambda _host, text: shown.append(text) or confirmed)
    return shown


def test_safe_mode_declines_both_commands(env) -> None:
    host = env["host"]
    host._safe_mode = True
    host.process_with_auphonic()
    host.show_auphonic_work()
    assert host.boxes == ["Processing with Auphonic is unavailable in Safe Mode."] * 2
    assert env["client"].calls == []


def test_an_empty_queue_or_a_running_job_is_refused(env) -> None:
    host = env["host"]
    host._busy = True
    host.process_with_auphonic()
    assert host.said == ["A job is already running."]
    host._busy = False
    host._entries = []
    host.process_with_auphonic()
    assert "Add the sound files" in host.boxes[-1]


def test_cancelling_the_choices_sends_nothing(env, monkeypatch) -> None:
    _answer(monkeypatch, None)
    env["host"].process_with_auphonic()
    assert env["client"].calls == [] and env["host"].status[-1] == "Nothing was sent to Auphonic."


def test_cancelling_the_confirmation_sends_nothing(env, monkeypatch) -> None:
    shown = _answer(monkeypatch, (AuphonicChoices(), "new-token", True, ""), confirmed=False)
    env["host"].process_with_auphonic()
    assert shown and "host.wav" in shown[0] and "guest.wav" in shown[0]
    assert env["client"].calls == [] and env["tokens"] == []
    assert env["host"].said[-1] == "Nothing was sent to Auphonic."


def test_confirming_sends_one_after_another_and_reports(env, monkeypatch) -> None:
    host = env["host"]
    choices = AuphonicChoices(processing=QUICK_CLEANUP, preset_uuid="P", preset_label="Speech")
    _answer(monkeypatch, (choices, "new-token", True, "account jeff"))
    host.process_with_auphonic()
    assert env["client"].calls == [
        "create new-token", "upload host.wav", "start", "status", "download",
        "create new-token", "upload guest.wav", "start", "status", "download",
    ]  # fmt: skip
    assert env["tokens"] == ["new-token"]  # remembered in the credential store only
    assert host.began == ["Sending 2 files to Auphonic"]
    assert host.said[:2] == ["1 of 2: host.wav, saved.", "2 of 2: guest.wav, saved."]
    assert host.said[-1].startswith("Auphonic: 2 of 2 saved.")
    assert "Ctrl+R" in host.said[-1] and "Ctrl+Shift+F" in host.said[-1]
    assert "What was confirmed:" in host._last_report and "Speech" in host._last_report
    assert host._last_output == host.dest
    assert not host._busy and load_pending(env["store"]) == []
    # The choices are remembered; the token never is.
    assert host._settings.auphonic_processing == QUICK_CLEANUP
    assert host._settings.auphonic_preset_name == "Speech"
    assert "new-token" not in repr(host._settings.to_json())


def test_an_unremembered_token_is_used_and_not_stored(env, monkeypatch) -> None:
    _answer(monkeypatch, (AuphonicChoices(), "once", False, ""))
    env["host"].process_with_auphonic()
    assert env["tokens"] == [] and "create once" in env["client"].calls


def test_one_multitrack_production_saves_into_its_title(env, monkeypatch) -> None:
    host = env["host"]
    host._settings.open_folder_when_done = True
    _answer(monkeypatch, (AuphonicChoices(mode=MULTITRACK, title="Panel"), "t", True, ""))
    host.process_with_auphonic()
    assert env["client"].calls.count("create t") == 1
    assert host.began == ["Sending Panel to Auphonic as one multitrack production"]
    assert host.said[-1] == f"Panel: 1 file saved in {host.dest / 'Panel'}."
    assert host._last_output == host.dest / "Panel" and host.opened


def test_no_eligible_file_explains_every_reason(env, monkeypatch) -> None:
    host = env["host"]
    skipped = [
        Skipped(path, "it is a video file, and this sends sound only") for path in env["files"]
    ]
    monkeypatch.setattr(converter_auphonic, "inspect_files", lambda _p: ([], skipped, {}))
    host.process_with_auphonic()
    assert (
        "None of the queued files" in host.boxes[-1] and "host.wav: it is a video" in host.boxes[-1]
    )


def test_skipped_items_are_counted_in_the_summary(env, monkeypatch) -> None:
    host = env["host"]
    keep, drop = env["files"]
    monkeypatch.setattr(
        converter_auphonic, "inspect_files", lambda _p: ([keep], [Skipped(drop, "gone")], {})
    )
    _answer(monkeypatch, (AuphonicChoices(), "t", True, ""))
    host.process_with_auphonic()
    assert "1 queued item was not sent." in host.said[-1]
    assert "guest.wav: gone." in host._last_report


def test_waiting_work_is_read_locally_and_resumed_on_request(env, monkeypatch) -> None:
    host = env["host"]
    host.show_auphonic_work()
    assert host.said == ["No Auphonic work is waiting."]
    record = PendingProduction(
        "U9", "separate", "Talk", ["talk.wav"], "Speech", str(host.dest / "Talk")
    )
    add_pending(env["store"], record)
    monkeypatch.setattr(dialogs, "ask_resume", lambda _h, _records, dismiss: None)
    host.show_auphonic_work()
    assert env["client"].calls == []  # closing the list contacts nobody
    monkeypatch.setattr(dialogs, "ask_resume", lambda _h, records, dismiss: records)
    host.show_auphonic_work()
    assert env["client"].calls == ["status", "download"]
    assert load_pending(env["store"]) == []
    assert host.began == ["Fetching 1 production from Auphonic"]


def test_resume_without_a_stored_token_says_how(env, monkeypatch) -> None:
    host = env["host"]
    add_pending(env["store"], PendingProduction("U9", "separate", "Talk", [], "", "x"))
    monkeypatch.setattr(converter_auphonic, "load_token", lambda: "")
    monkeypatch.setattr(dialogs, "ask_resume", lambda _h, records, dismiss: records)
    host.show_auphonic_work()
    assert "needs your Auphonic API token" in host.boxes[-1] and env["client"].calls == []


def test_launch_mentions_waiting_work_without_the_network(env, monkeypatch) -> None:
    host = env["host"]
    later: list[Any] = []
    monkeypatch.setattr(converter_auphonic.wx, "CallLater", lambda ms, fn, text: later.append(text))
    host._note_pending_auphonic()
    assert host.status == [] and later == []
    add_pending(env["store"], PendingProduction("U9", "separate", "Talk", [], "", "x"))
    host._note_pending_auphonic()
    assert later == [
        "1 Auphonic production is waiting to be fetched. Press Ctrl+Alt+A to see them."
    ]
    assert env["client"].calls == []


def test_inspect_files_reads_tags_and_refuses_moving_pictures(tmp_path, monkeypatch) -> None:
    from quill.core.audio import media_probe
    from quill.core.audio.media_probe import Chapter, MediaInfo, StreamInfo

    talk, clip = tmp_path / "talk.m4a", tmp_path / "clip.m4a"
    for path in (talk, clip):
        path.write_bytes(b"data")

    def probe(path: Path, **_k: Any) -> MediaInfo:
        if path == clip:
            return MediaInfo(path=path, streams=(StreamInfo(kind="video", codec="h264"),))
        return MediaInfo(
            path=path,
            tags={"title": "Talk", "artist": "Jeff"},
            streams=(StreamInfo(kind="audio", codec="aac"), StreamInfo(kind="cover", codec="png")),
            chapters=(Chapter(title="One", start_s=0.0, end_s=5.0),),
        )

    monkeypatch.setattr(media_probe, "probe", probe)
    eligible, skipped, details = converter_auphonic.inspect_files([talk, clip])
    assert eligible == [talk] and [s.path for s in skipped] == [clip]
    assert details[talk].title == "Talk" and details[talk].artist == "Jeff"
    assert details[talk].chapters == ((0.0, "One"),)


def test_the_token_lives_under_the_family_credential(monkeypatch) -> None:
    from quill.core.publish.auphonic import CREDENTIAL_TARGET
    from quill.platform.windows import credential_manager

    saved: list[tuple[str, str]] = []
    monkeypatch.setattr(
        credential_manager,
        "save_generic_credential",
        lambda target, secret, **_k: saved.append((target, secret)),
    )
    monkeypatch.setattr(
        credential_manager,
        "load_generic_credential",
        lambda target: (
            credential_manager.StoredCredential(target, "auphonic", " tok ")
            if target == CREDENTIAL_TARGET
            else None
        ),
    )
    converter_auphonic.save_token("tok")
    assert saved == [(CREDENTIAL_TARGET, "tok")]
    assert converter_auphonic.load_token() == "tok"
    assert CREDENTIAL_TARGET == "quill:publish:auphonic"  # the Audio Studio's entry


# -- the windows, built in memory -------------------------------------------------------


def _dialog(wx_app, files: list[Path], **kwargs: Any) -> dialogs.AuphonicDialog:
    said: list[str] = []
    args: dict[str, Any] = {
        "skipped": 1,
        "initial": AuphonicChoices(),
        "token": "",
        "check": lambda _t, _deliver: None,
        "announce": said.append,
    }
    args.update(kwargs)
    dialog = dialogs.AuphonicDialog(None, files, **args)
    dialog.said = said  # type: ignore[attr-defined]
    return dialog


def test_the_choices_window_reads_back_what_it_says(wx_app, tmp_path: Path) -> None:
    files = [tmp_path / "host.wav", tmp_path / "guest.wav"]
    initial = AuphonicChoices(
        mode=MULTITRACK,
        preset_uuid="P7",
        preset_label="Speech",
        processing=QUICK_CLEANUP,
        denoise=True,
        output_format="flac",
    )
    dialog = _dialog(wx_app, files, initial=initial, token="tok")
    try:
        assert dialog._title.GetValue() == "host" and dialog._title.IsEnabled()
        assert dialog._denoise.IsEnabled()
        got = dialog.choices()
        assert got == AuphonicChoices(
            mode=MULTITRACK,
            preset_uuid="P7",
            preset_label="Speech",
            processing=QUICK_CLEANUP,
            denoise=True,
            output_format="flac",
            title="host",
        )
        dialog._processing.SetSelection(0)
        dialog._sync()
        assert not dialog._denoise.IsEnabled() and dialog.choices().denoise is False
        assert dialog.token() == "tok" and dialog.remember_token()
    finally:
        dialog.Destroy()


def test_every_control_explains_itself_on_f1(wx_app, tmp_path: Path) -> None:
    dialog = _dialog(wx_app, [tmp_path / "a.wav"])
    try:
        for control in (
            dialog._list,
            dialog._mode,
            dialog._title,
            dialog._token,
            dialog._remember,
            dialog._check_btn,
            dialog._status,
            dialog._preset,
            dialog._processing,
            dialog._denoise,
            dialog._format,
        ):
            assert control.GetHelpText().strip(), control.GetName()
        assert "1 queued item(s) cannot be sent" in dialog._list.GetHelpText()
    finally:
        dialog.Destroy()


def test_the_account_check_fills_presets_and_a_failure_changes_nothing(wx_app, tmp_path) -> None:
    from quill.core.publish.auphonic import AccountInfo, Preset

    dialog = _dialog(wx_app, [tmp_path / "a.wav"], token="tok")
    try:
        dialog.account_checked(None, None, "Auphonic said 401: Unauthorized")
        assert "failed: Auphonic said 401" in dialog._status.GetValue()
        assert dialog.said[-1] == dialog._status.GetValue()
        assert dialog._preset.GetCount() == 1  # no silent fallback to a guessed preset
        presets = [Preset("P1", "Speech"), Preset("P2", "Music")]
        dialog.account_checked(presets, AccountInfo("jeff", 4.5), "")
        assert dialog._preset.GetStrings() == ["Your account's default preset", "Speech", "Music"]
        assert "jeff: 4.5 credit hours left, 2 saved presets loaded." in dialog._status.GetValue()
        dialog._preset.SetSelection(2)
        assert (dialog.choices().preset_uuid, dialog.choices().preset_label) == ("P2", "Music")
        assert dialog.account() == "account jeff, 4.5 credit hours left"
    finally:
        dialog.Destroy()


def test_an_account_check_without_a_token_asks_for_one(wx_app, tmp_path) -> None:
    calls: list[str] = []
    dialog = _dialog(wx_app, [tmp_path / "a.wav"], check=lambda t, _d: calls.append(t))
    try:
        dialog.check_account()
        assert calls == [] and "token first" in dialog._status.GetValue()
    finally:
        dialog.Destroy()


def test_the_account_check_runs_off_the_ui_thread_and_answers_on_it(wx_app, tmp_path, monkeypatch):
    from quill.core.publish.auphonic import AccountInfo, AuphonicError, Preset

    monkeypatch.setattr(converter_auphonic.threading, "Thread", _NowThread)
    patch_call_after(monkeypatch, lambda fn, *a, **k: fn(*a, **k))
    monkeypatch.setattr(
        converter_auphonic,
        "check_account",
        lambda token: ([Preset("P1", "Speech")], AccountInfo("jeff", 1.0)),
    )
    dialog = _dialog(
        wx_app, [tmp_path / "a.wav"], token="tok", check=converter_auphonic.start_account_check
    )
    try:
        dialog.check_account()
        assert "Auphonic account jeff" in dialog._status.GetValue()
        assert dialog._check_btn.IsEnabled()

        def refuse(token: str) -> Any:
            raise AuphonicError("Auphonic said 401: Unauthorized")

        monkeypatch.setattr(converter_auphonic, "check_account", refuse)
        dialog.check_account()
        assert "failed: Auphonic said 401" in dialog._status.GetValue()
    finally:
        dialog.Destroy()


def test_review_is_refused_in_words_when_the_choices_cannot_be_sent(wx_app, tmp_path) -> None:
    refused: list[str] = []
    dialog = _dialog(
        wx_app,
        [tmp_path / "a.wav"],
        problem=lambda _c, _t: "Give the multitrack production a title.",
        refuse=refused.append,
    )
    try:
        skipped: list[bool] = []

        class _Event:
            def Skip(self) -> None:  # noqa: N802 - wx API
                skipped.append(True)

        dialog._on_review(_Event())
        assert refused == ["Give the multitrack production a title."] and skipped == []
    finally:
        dialog.Destroy()


def test_the_confirmation_shows_the_whole_text(wx_app) -> None:
    dialog = dialogs.AuphonicConfirmDialog(None, "Line one\nLine two")
    try:
        assert dialog._body.GetValue() == "Line one\nLine two"
        assert dialog.FindWindow(wx.ID_OK).GetLabel() == "Upload and Process"
    finally:
        dialog.Destroy()


def test_the_waiting_list_dismisses_locally(wx_app) -> None:
    forgotten: list[str] = []
    records = [
        PendingProduction("U1", "separate", "Talk", ["talk.wav"], "Speech", "C:/out/Talk"),
        PendingProduction("U2", MULTITRACK, "Panel", ["a", "b"], "", "C:/out/Panel"),
    ]
    dialog = dialogs.AuphonicWaitingDialog(
        None, records, dismiss=lambda r: forgotten.append(r.uuid)
    )
    try:
        assert (
            dialog._list.GetCount() == 2
            and "multitrack production of 2 files" in dialog._list.GetString(1)
        )
        dialog.dismiss_selected()
        assert forgotten == ["U1"] and [r.uuid for r in dialog.records()] == ["U2"]
        dialog.dismiss_selected()
        assert not dialog.FindWindow(wx.ID_OK).IsEnabled()
    finally:
        dialog.Destroy()
