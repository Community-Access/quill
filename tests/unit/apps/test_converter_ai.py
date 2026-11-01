"""Quill Converter's AI, in the real window (codex.md Phase 3, 10E.7).

Its own "QUILL Converter" sign-in, the AI menu on the Window-menu fallback keys,
Ask about the queue, Will This Play on My Device?, the AI line and Safe Mode.
The AI is a stand-in on the real service and ffprobe is a stand-in too, so
nothing leaves the machine and no tool runs.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

wx = pytest.importorskip("wx")

#: Builds a real Quill Converter window, which registers the show/hide key and a tray icon.
pytestmark = pytest.mark.machine_global


class _Account:
    def __init__(self, signed_in: bool = True) -> None:
        self.signed_in = signed_in
        self.model = ""
        self.slug = "quill-converter"
        self.web_search = False
        self.ended_by_openai = False


def _info(path: Path):
    from quill.core.audio.media_probe import MediaInfo, StreamInfo

    return MediaInfo(
        path=path,
        container="flac",
        duration_s=125.0,
        size_bytes=4_000_000,
        streams=(StreamInfo("audio", "flac", sample_rate=96000, channels=2),),
    )


@pytest.fixture
def converter(quill_data_dir: Path, wx_session_app, tmp_path: Path, monkeypatch):
    from quill.apps import converter as app
    from quill.core import converter_settings
    from quill.core.audio import media_probe

    monkeypatch.setattr(
        converter_settings, "settings_path", lambda _d=None: tmp_path / "converter.json"
    )
    monkeypatch.setattr(app, "_find_ffmpeg", lambda: None)  # formats list: WAV only
    probed: list[str] = []

    def probe(path, **_kw):
        probed.append(path.name)
        return _info(path)

    monkeypatch.setattr(media_probe, "probe", probe)
    frame = app.QuillConverterFrame()
    frame.probed = probed
    said: list[str] = []
    frame._announce = lambda message, **_kw: said.append(str(message))
    frame.said = said
    # The background read, run at once: what the task manager would deliver later.
    frame.reads = []

    def submit(name, work, *, on_success=None, on_failure=None, **_kw):
        frame.reads.append(name)
        if not getattr(frame, "hold_reads", False):
            on_success(name, work())

    monkeypatch.setattr(frame._task_manager, "submit", submit)
    service = frame._ai_service()
    monkeypatch.setattr(type(service), "refresh_limits", lambda self, on_done=None: None)
    frame.sent = []

    def ask(feature, prompt, chunks, *, on_done, on_error, language="", requires=("text",)):
        frame.sent.append((feature, prompt, requires))
        on_done("Yes on the iPhone; FLAC at 96 kHz will not play in most cars.", None)

    def converse(message, excerpts, history, *, on_done, on_error, requires=("text",)):
        frame.sent.append(("converse", message, list(excerpts)))
        on_done("An answer.", None, 0)

    service.ask = ask
    service.converse = converse
    service._chatgpt = _Account(signed_in=True)
    frame._ai_host().settings.ai_connection = "chatgpt"
    frame.shown = []
    monkeypatch.setattr(frame, "_show_ai_window", lambda window: frame.shown.append(window))
    try:
        yield frame
    finally:
        for window in [*getattr(frame, "_ai_windows", {}).values(), *frame.shown]:
            if window:
                window.Destroy()
        frame._ipc_timer.Stop()
        frame._remove_tray_icon()
        frame.frame.Destroy()


def _queue(frame, tmp_path: Path, *names: str) -> list[Path]:
    folder = tmp_path / "My Private Folder"
    folder.mkdir(exist_ok=True)
    paths = []
    for name in names:
        path = folder / name
        path.write_bytes(b"x")
        paths.append(path)
    frame.add_paths(paths, announce=False)
    return paths


def _answer_device(frame, monkeypatch, value: str | None) -> list[str]:
    asked: list[str] = []

    def show(dialog, label, **_kw):
        asked.append(label)
        if value is None:
            return wx.ID_CANCEL
        dialog.SetValue(value)
        return wx.ID_OK

    monkeypatch.setattr(frame, "_show_modal_dialog", show)
    return asked


def _menu(frame, name: str):
    bar = frame.frame.GetMenuBar()
    return bar.GetMenu(bar.FindMenu(name))


def test_the_ai_menu_sits_before_quillville_on_the_fallback_keys(converter) -> None:
    bar = converter.frame.GetMenuBar()
    titles = [bar.GetMenuLabel(i) for i in range(bar.GetMenuCount())]
    assert titles.index("A&I") == titles.index("&Convert") + 1
    assert titles.index("A&I") + 1 == titles.index("Q&uillVille")
    labels = [
        i.GetItemLabel() for i in _menu(converter, "AI").GetMenuItems() if not i.IsSeparator()
    ]
    assert labels == [
        "&Ask...\tCtrl+Shift+8",
        "&Which AI Am I Using\tCtrl+F8",
        "&Choose Your AI...\tCtrl+Shift+F8",
        "Will This Play on My &Device?...\tCtrl+Shift+D",
        "Use My C&hatGPT Subscription...\tAlt+F5",
        "Use My &Own AI Key...\tAlt+F2",
        "AI U&sage...\tCtrl+Alt+Shift+F2",
        "&Privacy Agreement...\tCtrl+Alt+Shift+K",
    ]
    assert converter.commands.get("converter.ai_will_play") is not None


def test_converter_signs_in_as_itself(converter) -> None:
    service = converter._ai_service()
    assert service._app.ai_agent_name == "QUILL Converter"
    del service._chatgpt
    assert service.chatgpt.agent_name == "QUILL Converter"


def test_the_choice_is_kept_in_converters_own_file(converter) -> None:
    from quill.core.paths import app_data_dir

    converter._ai_host().save_settings()
    saved = json.loads((app_data_dir() / "converter-ai.json").read_text(encoding="utf-8"))
    assert saved["ai_connection"] == "chatgpt"


def test_will_play_asks_which_device_and_sends_probe_text(converter, tmp_path, monkeypatch) -> None:
    _queue(converter, tmp_path, "book.flac")
    converter._last_report = "Converted 1 of 1. book.flac to book.wav."
    asked = _answer_device(converter, monkeypatch, "iPhone")
    converter.cmd_converter_will_play()
    assert asked == ["Will This Play on My Device?"]
    assert converter.probed == ["book.flac"]
    feature, prompt, requires = converter.sent[0]
    assert requires == ("text",)
    assert "on this device: iPhone" in prompt
    assert "File: book.flac" in prompt and "96 kHz" in prompt
    assert "Convert to: WAV" in prompt
    assert "Converted 1 of 1" in prompt
    assert "My Private Folder" not in prompt  # file names, never folders
    window = converter.shown[0]
    assert window.GetTitle() == "Will This Play on My Device?"
    assert "FLAC at 96 kHz" in window._text


def test_will_play_with_an_empty_device_asks_about_the_usual_ones(
    converter, tmp_path, monkeypatch
) -> None:
    _queue(converter, tmp_path, "a.mp3")
    _answer_device(converter, monkeypatch, "")
    converter.cmd_converter_will_play()
    assert "on a phone, on a car stereo" in converter.sent[0][1]


def test_will_play_reuses_what_was_already_read(converter, tmp_path, monkeypatch) -> None:
    _queue(converter, tmp_path, "a.mp3")
    _answer_device(converter, monkeypatch, "Echo")
    converter.cmd_converter_will_play()
    converter.cmd_converter_will_play()
    assert converter.probed == ["a.mp3"]
    assert len(converter.sent) == 2


def test_will_play_cancelled_sends_nothing(converter, tmp_path, monkeypatch) -> None:
    _queue(converter, tmp_path, "a.mp3")
    _answer_device(converter, monkeypatch, None)
    converter.cmd_converter_will_play()
    assert converter.sent == [] and converter.probed == [] and converter.shown == []


def test_will_play_with_an_empty_queue_says_so_and_sends_nothing(converter, monkeypatch) -> None:
    asked = _answer_device(converter, monkeypatch, "iPhone")
    converter.cmd_converter_will_play()
    assert converter.said == ["The queue is empty. Add files first, then ask."]
    assert asked == [] and converter.sent == []


def test_ask_facts_never_wait_and_name_what_is_not_read_yet(converter, tmp_path) -> None:
    _queue(converter, tmp_path, "a.mp3", "b.m4b")
    converter.hold_reads = True  # the background read has not come back
    facts = converter._app_ask_facts("Will these play?", "")
    assert facts.get("Not read yet") == "a.mp3, b.m4b"
    assert facts.get("Convert to").startswith("WAV")
    assert converter.reads == ["converter-ai-probe"] and converter.probed == []
    converter.hold_reads = False
    converter._converter_ai_read()  # what the background read delivers
    facts = converter._app_ask_facts("Will these play?", "")
    assert facts.get("Not read yet") == ""
    assert "File: a.mp3" in facts.get("File details")
    assert "File: b.m4b" in facts.get("File details")


def test_ask_sends_the_queue_by_file_name(converter, tmp_path) -> None:
    from quill.ui.hosted_ai_app_ask import AppAskFrame

    _queue(converter, tmp_path, "book.flac")
    converter._converter_ai_read()
    converter.cmd_ai_chat_key()
    frame = converter._ai_windows["ask"]
    assert isinstance(frame, AppAskFrame)
    assert frame._about.GetValue().startswith("Asking My ChatGPT plan about these files.")
    frame._message.SetValue("Will this play in my car?")
    frame._send()
    facts = converter.sent[0][2][0]
    assert "File: book.flac" in facts and "Convert to: WAV" in facts
    assert "My Private Folder" not in facts


def test_a_queued_folder_is_read_in_the_background(converter, tmp_path) -> None:
    folder = tmp_path / "Album"
    folder.mkdir()
    (folder / "one.mp3").write_bytes(b"x")
    (folder / "notes.txt").write_bytes(b"x")
    converter.add_paths([folder], announce=False)
    converter.hold_reads = True
    assert converter._app_ask_facts("", "").get("Not read yet") == "Album (a folder)"
    converter.hold_reads = False
    converter._converter_ai_read()
    facts = converter._app_ask_facts("", "")
    assert facts.get("Files queued") == "1" and "File: one.mp3" in facts.get("File details")


def test_safe_mode_refuses_every_ai_command(converter, tmp_path, monkeypatch) -> None:
    _queue(converter, tmp_path, "a.mp3")
    asked = _answer_device(converter, monkeypatch, "iPhone")
    converter._safe_mode = True
    for command in (
        lambda c: c.cmd_ai_chat_key(),
        lambda c: c.cmd_ai_which(),
        lambda c: c.cmd_ai_choose(),
        lambda c: c.cmd_ai_usage(),
        lambda c: c.cmd_ai_chatgpt(),
        lambda c: c.cmd_converter_will_play(),
    ):
        converter.said.clear()
        command(converter)
        assert converter.said == ["AI is off in Safe Mode."]
    assert converter.sent == [] and asked == []


def test_the_ai_line_says_which_ai_and_enter_opens_choose(converter, monkeypatch) -> None:
    opened: list[str] = []
    monkeypatch.setattr(type(converter), "cmd_ai_choose", lambda self: opened.append("x"))
    assert converter._ai_text.GetValue().startswith("AI")
    assert "Choose Your AI" in converter._ai_text.GetHelpText()
    event = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    event.SetKeyCode(wx.WXK_RETURN)
    converter._on_ai_line_key(event)
    assert opened == ["x"]


def test_open_output_folder_when_done_still_answers_from_the_menu(converter) -> None:
    from quill.apps.converter_preferences import set_open_when_done

    set_open_when_done(converter, True)
    assert converter._settings.open_folder_when_done is True
    assert converter.said[-1] == "The output folder opens when a conversion finishes."


def test_the_adapter_has_no_command_of_its_own() -> None:
    from quill.apps.converter_ai import ConverterAiMixin
    from quill.ui.hosted_ai_app_adapter import AppAiHost, AppAiMixin

    for cls in (ConverterAiMixin, AppAiMixin, AppAiHost):
        assert [name for name in vars(cls) if name.startswith("cmd_")] == []
