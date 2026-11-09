"""Quill Converter's window, driven: queue, choices, effects, report, keys.

The window registers a tray icon and the global show/hide hotkey, which is why
the module is ``machine_global`` (tests/conftest.py groups those on one worker).
"""

from __future__ import annotations

from pathlib import Path

import pytest

#: Serialized onto one worker under ``-n --dist loadgroup``: this file builds a
#: real Quill Converter window, which registers the system-wide show/hide hotkey
#: (RegisterHotKey is per-desktop, not per-process) and a tray icon.
#: See ``pytest_collection_modifyitems`` in ``tests/conftest.py``.
pytestmark = pytest.mark.machine_global


@pytest.fixture()
def converter(wx_app, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from quill.apps import converter as app
    from quill.core import converter_settings

    monkeypatch.setattr(
        converter_settings, "settings_path", lambda _d=None: tmp_path / "converter.json"
    )
    monkeypatch.setattr(app, "_find_ffmpeg", lambda: None)  # formats list: WAV only
    frame = app.QuillConverterFrame()
    frame._formats  # noqa: B018 - constructed
    said: list[str] = []
    boxes: list[str] = []
    monkeypatch.setattr(frame, "_announce", lambda text, **_k: said.append(text))
    monkeypatch.setattr(frame, "_show_message_box", lambda text, *_a, **_k: boxes.append(text))
    frame.said, frame.boxes = said, boxes
    yield frame
    frame._ipc_timer.Stop()
    frame._remove_tray_icon()
    frame.frame.Destroy()
    wx_app.Yield()


def _files(tmp_path: Path, *names: str) -> list[Path]:
    paths = []
    for name in names:
        path = tmp_path / name
        path.write_bytes(b"x")
        paths.append(path)
    return paths


def test_add_paths_queues_media_and_says_what_was_left_out(converter, tmp_path: Path) -> None:
    song, clip, note = _files(tmp_path, "song.mp3", "clip.mkv", "notes.txt")
    converter.add_paths([song, clip, note])
    assert [entry for entry, _root in converter._entries] == [song, clip]
    assert converter._list.GetCount() == 2
    assert "Added 2" in converter.said[-1] and "1 not a media file" in converter.said[-1]
    converter.add_paths([song])  # a duplicate is queued once
    assert len(converter._entries) == 2


def test_move_remove_and_clear(converter, tmp_path: Path) -> None:
    a, b, c = _files(tmp_path, "a.mp3", "b.mp3", "c.mp3")
    converter.add_paths([a, b, c], announce=False)
    converter._list.SetSelection(2)
    converter.move_entry(-1)
    assert [e.name for e, _r in converter._entries] == ["a.mp3", "c.mp3", "b.mp3"]
    assert converter.said[-1] == "Moved to position 2 of 3."
    converter._on_remove(None)
    assert [e.name for e, _r in converter._entries] == ["a.mp3", "b.mp3"]
    converter.clear_queue()
    assert converter._entries == [] and converter.said[-1] == "Queue cleared."


def test_convert_with_an_empty_queue_explains(converter) -> None:
    converter.convert_or_stop()
    assert converter.boxes == ["Add some files or a folder first."]


def test_convert_without_ffmpeg_points_at_the_repair(
    converter, tmp_path: Path, monkeypatch
) -> None:
    import quill.core.speech.ffmpeg as ff

    monkeypatch.setattr(ff, "find_ffmpeg", lambda: None)
    converter.add_paths(_files(tmp_path, "a.mp3"), announce=False)
    converter.convert_or_stop()
    assert "Get FFmpeg" in converter.boxes[-1]


def test_effects_and_keep_part_reach_the_spec(converter) -> None:
    from quill.core.audio.dsp import DspOptions

    converter._effect.SetSelection(converter._effect_ids.index("podcast"))
    spec = converter.current_spec()
    assert any(f.startswith("loudnorm=I=-16") for f in spec.filters)
    converter._settings.custom_effects = DspOptions(bass_boost=True)
    converter._settings.start_s, converter._settings.end_s = 3.0, 9.0
    converter._effect.SetSelection(converter._effect_ids.index("custom"))
    spec = converter.current_spec()
    assert "bass=g=6:f=100" in spec.filters and (spec.start_s, spec.end_s) == (3.0, 9.0)
    assert "custom effects (bass boost)" in converter.describe_choices()
    assert "keeping 3 seconds to 9" in converter.describe_choices()


def test_choices_are_remembered(converter, tmp_path: Path) -> None:
    from quill.core import converter_settings

    converter._effect.SetSelection(converter._effect_ids.index("night"))
    converter._dest.SetValue(str(tmp_path / "out"))
    converter._remember()
    saved = converter_settings.ConverterSettings.from_json(
        __import__("json").loads((tmp_path / "converter.json").read_text(encoding="utf-8"))
    )
    assert saved.effect == "night" and saved.dest_dir == str(tmp_path / "out")


def test_report_lists_failures_with_reasons(converter, tmp_path: Path) -> None:
    from quill.core.audio.convert import BatchResult, ConversionJob, ConversionSpec, JobResult

    job = ConversionJob(tmp_path / "a.mp3", tmp_path / "out" / "a.wav", ConversionSpec(fmt="wav"))
    result = BatchResult(results=[JobResult(job=job, ok=False, error="The output drive is full.")])
    converter.add_paths(_files(tmp_path, "a.mp3"), announce=False)
    converter._busy = True
    converter._finish_batch(result, 1, tmp_path / "out", "", 2.0)
    assert not converter._busy
    assert "Press Ctrl+R for the report." in converter.said[-1]
    assert (
        "FAILED" in converter._last_report and "The output drive is full." in converter._last_report
    )


def test_report_keeps_the_note_on_a_converted_file(converter, tmp_path: Path) -> None:
    from quill.core.audio.convert import BatchResult, ConversionJob, ConversionSpec, JobResult

    job = ConversionJob(tmp_path / "a.wav", tmp_path / "out" / "a.ogg", ConversionSpec(fmt="ogg"))
    note = "3 chapters are in a.cue beside it."
    result = BatchResult(results=[JobResult(job=job, ok=True, error=note)])
    converter.add_paths(_files(tmp_path, "a.wav"), announce=False)
    converter._finish_batch(result, 1, tmp_path / "out", "", 1.0)
    assert f"Converted: a.wav -> a.ogg\n  Note: {note}" in converter._last_report


def test_a_download_converts_into_downloads_not_the_temp_folder(
    converter, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import tempfile

    temp = tmp_path / "temp"
    (temp / "dl").mkdir(parents=True)
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(temp))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))
    converter._dest.SetValue("")
    converter._entries = [(temp / "dl" / "talk.m4a", None)]
    assert converter._destination() == tmp_path / "home" / "Downloads" / "Converted"
    converter._entries = [(tmp_path / "music" / "song.wav", None)]
    assert converter._destination() == tmp_path / "music" / "Converted"


def test_the_progress_bar_follows_the_work_and_empties_after(converter) -> None:
    converter._note_progress("Converting a.wav: 42 percent", 420, 1000)
    assert converter._progress.GetValue() == 420
    converter._end_work()
    assert converter._progress.GetValue() == 0


def test_every_menu_item_names_a_key_and_no_key_is_claimed_twice(converter) -> None:
    from quill.apps.converter_menu import shortcut_list

    text = shortcut_list(converter.frame.GetMenuBar())
    keys = [
        line.rsplit(": ", 1)[1]
        for line in text.splitlines()
        if line.startswith("  ") and ": " in line
    ]
    assert len(keys) == len(set(keys)), keys
    for wanted in (
        "Ctrl+Enter",
        "Ctrl+P",
        "Ctrl+Shift+P",
        "Ctrl+J",
        "Alt+Enter",
        "Ctrl+Alt+F2",
        "Ctrl+F1",
    ):
        assert wanted in keys, wanted


def test_main_window_access_keys_are_unique_and_leave_the_menu_bar_alone(converter) -> None:
    """Alt+F must open the File menu, not jump to a control (reported 2026-09-27:
    "the converter doesn't let me see the menu bar")."""
    letters = []
    for child in converter._main_panel.GetChildren():
        label = child.GetLabel() if hasattr(child, "GetLabel") else ""
        if "&" in label:
            letters.append(label[label.index("&") + 1].lower())
    assert len(letters) == len(set(letters)), letters
    bar = converter.frame.GetMenuBar()
    menu_letters = set()
    for index in range(bar.GetMenuCount()):
        title = bar.GetMenuLabel(index)
        assert "&" in title, title
        menu_letters.add(title[title.index("&") + 1].lower())
    assert len(menu_letters) == bar.GetMenuCount()
    assert not menu_letters & set(letters), sorted(menu_letters & set(letters))


def test_custom_effects_dialog_round_trips(converter) -> None:
    from quill.core.audio.dsp import DspOptions
    from quill.ui.converter_dialogs import ConverterEffectsDialog

    dialog = ConverterEffectsDialog(
        converter.frame, DspOptions(deesser=True, loudness="audiobook"), start_s=2.0, end_s=1.0
    )
    try:
        dsp, start, end = dialog.result()
        assert dsp.deesser and dsp.loudness == "audiobook" and not dsp.bass_boost
        assert (start, end) == (2.0, 0.0)  # an end before the start means "to the end"
        dialog._boxes["bass_boost"].SetValue(True)
        assert dialog.result()[0].bass_boost
    finally:
        dialog.Destroy()


def test_view_advanced_options_shows_the_settings_in_the_main_window(converter) -> None:
    from quill.core.audio.convert import Channels

    assert not converter._main_sizer.IsShown(converter._advanced_box)
    converter.set_advanced_visible(True)
    assert converter._main_sizer.IsShown(converter._advanced_box)
    assert converter._settings.show_advanced is True
    ctrl, table = converter._advanced_choices["adv_channels"]
    ctrl.SetSelection([value for value, _t in table].index(Channels.MONO))
    rate_ctrl, rate_table = converter._advanced_choices["adv_rate"]
    rate_ctrl.SetSelection([value for value, _t in rate_table].index("16000"))
    spec = converter.current_spec()
    assert spec.channels is Channels.MONO and spec.sample_rate == 16000
    converter.set_advanced_visible(False)
    assert not converter._main_sizer.IsShown(converter._advanced_box)


def test_the_view_menu_holds_advanced_options(converter) -> None:
    bar = converter.frame.GetMenuBar()
    titles = [bar.GetMenuLabelText(i) for i in range(bar.GetMenuCount())]
    assert titles[:4] == ["File", "Queue", "View", "Convert"]
    view = bar.GetMenu(2)
    item = view.GetMenuItems()[0]
    assert item.IsCheckable() and item.GetItemLabel().endswith("\tCtrl+Alt+V")


def test_ai_lives_only_in_the_ai_menu(converter) -> None:
    """Quill Converter had no AI (owner decision, 2026-10-05) until codex.md
    Phase 3 (2026-11-01) gave it one AI menu. Find a Setting or Command lists
    exactly the menu bar's rows, so one walk covers both; a shared menu that
    grows an AI row anywhere else would show up here first."""
    import re

    from quill.ui.menu_palette import menu_rows

    rows = menu_rows(converter.frame.GetMenuBar())
    assert rows
    ai = re.compile(r"\bAI\b|ChatGPT|OpenAI|Copilot|Claude|Gemini|Assistant|API key", re.I)
    found = [row.spoken() for row in rows if ai.search(f"{row.path} {row.label}")]
    assert found
    # The AI menu, or its Accounts and Usage submenu (quill/core/ai/ai_menu_layout.py).
    assert all(re.search(r" -- AI\b", row) for row in found), found
    # Not a release-channel app either: Converter offers Stable only.
    assert not [row.label for row in rows if "Release Channel" in row.label]


def test_the_chapters_choice_reaches_the_spec_and_the_summary(converter) -> None:
    converter._chapters.SetSelection(converter._chapter_ids.index("every-30"))
    assert converter.current_spec().chapter_source == "every-30"
    assert "a chapter every 30 minutes" in converter.describe_choices()


def test_the_workbench_explains_other_formats(converter, tmp_path: Path) -> None:
    converter.add_paths(_files(tmp_path, "talk.wav"), announce=False)
    converter.open_chapter_workbench()
    assert "talk.chapters.txt" in converter.boxes[-1]


def test_edit_tags_opens_the_shared_tag_editor_for_mp3_and_m4b(
    converter, tmp_path, monkeypatch
) -> None:
    import quill.ui.audio_studio.tag_editor as tag_editor

    opened: list[Path] = []
    monkeypatch.setattr(tag_editor, "open_tags_in_editor", lambda _host, path: opened.append(path))
    book, talk = _files(tmp_path, "book.m4b", "talk.flac")
    converter.add_paths([book, talk], announce=False)
    converter._list.SetSelection(0)
    converter.edit_tags()
    assert opened == [book]
    converter._list.SetSelection(1)
    converter.edit_tags()
    assert opened == [book]  # a FLAC is refused, never given an ID3 block
    assert "MP3, M4A, M4B and MP4" in converter.boxes[-1]


def test_edit_tags_is_on_the_queue_menu(converter) -> None:
    bar = converter.frame.GetMenuBar()
    queue = bar.GetMenu(1)
    labels = [item.GetItemLabel() for item in queue.GetMenuItems()]
    assert "Edit &Tags...	Ctrl+T" in labels


# -- Convert from URL: playlists and channels ---------------------------------


def _channel_info():
    from quill.core.audio.url_collections import LinkInfo

    return LinkInfo(
        url="https://www.youtube.com/@x",
        kind="channel",
        title="X",
        sections=(
            ("Videos", "https://www.youtube.com/channel/UCx/videos"),
            ("Shorts", "https://www.youtube.com/channel/UCx/shorts"),
        ),
    )


def test_a_single_video_link_takes_the_one_video_path(
    converter, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.core.audio.url_collections import LinkInfo
    from quill.ui.audio_studio import convert_audio_dialog

    fetched: list[str] = []
    monkeypatch.setattr(
        convert_audio_dialog, "_download_then_convert", lambda _host, url: fetched.append(url)
    )
    converter._link_read("https://youtu.be/a", LinkInfo("https://youtu.be/a", "video", "A"))
    assert fetched == ["https://youtu.be/a"]


def test_the_channel_dialog_reads_back_a_choice(converter) -> None:
    from quill.ui.converter_dialogs import ConverterLinkDialog

    dialog = ConverterLinkDialog(converter.frame, _channel_info())
    try:
        dialog._section.SetSelection(1)
        dialog._since.SetSelection(2)  # the past month
        choice = dialog.result()
    finally:
        dialog.Destroy()
    assert choice.url == "https://www.youtube.com/channel/UCx/shorts"
    assert (choice.title, choice.is_channel, choice.newest, choice.within_days) == (
        "X - Shorts",
        True,
        25,
        31,
    )
    assert choice.only_new is True


def test_a_video_inside_a_playlist_can_be_taken_alone(converter) -> None:
    from quill.core.audio.url_collections import LinkInfo
    from quill.ui.converter_dialogs import ConverterLinkDialog

    info = LinkInfo("https://y/watch?v=a&list=P", "playlist", "Talks", 9, "Talk 3")
    dialog = ConverterLinkDialog(converter.frame, info)
    try:
        assert dialog.result().newest is None  # the whole playlist by default
        dialog._scope.SetSelection(0)
        assert dialog.result() == "video"
    finally:
        dialog.Destroy()


def test_a_cancelled_question_downloads_nothing(converter, monkeypatch) -> None:
    from quill.ui import converter_dialogs

    monkeypatch.setattr(converter_dialogs, "ask_what_to_download", lambda _h, _i: None)
    started: list[object] = []
    monkeypatch.setattr(converter, "_download_collection", started.append)
    converter._link_read("https://www.youtube.com/@x", _channel_info())
    assert started == []


def test_a_finished_download_fills_the_queue_and_the_report(converter, tmp_path: Path) -> None:
    from quill.core.audio.url_collections import CollectionChoice, CollectionResult

    folder = tmp_path / "quill-url-list-abc" / "Talks"
    folder.mkdir(parents=True)
    files = _files(folder, "001 - One.webm", "002 - Two.webm")
    result = CollectionResult(folder=folder, files=files, failed=["zzz: Video unavailable"])
    converter._busy = True
    converter._collection_done(CollectionChoice(url="u", title="Talks"), result)
    assert not converter._busy
    assert [path for path, _root in converter._entries] == files
    assert converter.said[-1] == (
        "Downloaded 2 files from Talks into the queue. 1 could not be downloaded; "
        "Ctrl+R lists them."
    )
    assert "FAILED: zzz: Video unavailable" in converter._last_report


def test_a_downloaded_playlist_converts_into_its_own_folder(
    converter, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import tempfile

    temp = tmp_path / "temp"
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(temp))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))
    converter._dest.SetValue("")
    converter._entries = [(temp / "quill-url-list-abc" / "Talks" / "001 - One.webm", None)]
    assert converter._destination() == tmp_path / "home" / "Downloads" / "Converted" / "Talks"


# -- one job at a time, previews, and the close (converter_lifecycle) -----------------


class _CloseEvent:
    def __init__(self) -> None:
        self.vetoed = self.skipped = False

    def CanVeto(self) -> bool:  # noqa: N802 - wx's name
        return True

    def Veto(self) -> None:  # noqa: N802
        self.vetoed = True

    def Skip(self) -> None:  # noqa: N802
        self.skipped = True


def test_a_link_being_read_is_a_job_convert_waits_for(converter, monkeypatch) -> None:
    from quill.apps import converter_lifecycle

    started: list[object] = []
    monkeypatch.setattr(
        converter_lifecycle.threading,
        "Thread",
        lambda target, **_k: type("T", (), {"start": lambda self: started.append(target)})(),
    )
    done: list[object] = []
    converter._run_background_task(
        "Reading the link", lambda _p: "info", done.append, exclusive=True
    )
    assert converter._busy and len(started) == 1
    converter.convert_or_stop()  # while busy, Ctrl+Enter is Stop
    assert converter.said[-1] == "Reading the link cannot be stopped; it ends on its own."
    converter._run_background_task(
        "Checking the files for Auphonic", lambda _p: 0, done.append, exclusive=True
    )
    assert converter.said[-1] == "A job is already running." and len(started) == 1
    converter._finish_task("Reading the link", None, "info", done.append, True)
    assert not converter._busy and done == ["info"]
    converter._run_background_task("Proposing titles", lambda _p: 0, done.append)
    assert not converter._busy  # the Chapter Workbench's helpers are not jobs


def test_a_stopped_preview_never_plays_and_its_file_is_removed(
    converter, tmp_path: Path, monkeypatch
) -> None:
    import os
    import tempfile
    import winsound

    from quill.apps import converter_lifecycle

    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    jobs: list = []
    monkeypatch.setattr(converter_lifecycle, "_off_ui_thread", lambda w, d: jobs.append(d))
    played: list[object] = []
    monkeypatch.setattr(winsound, "PlaySound", lambda name, _flags: played.append(name))
    monkeypatch.setattr(converter_lifecycle.wx, "CallLater", lambda *_a: None)
    monkeypatch.setattr(converter, "_ffmpeg", lambda: "ffmpeg")
    (song,) = _files(tmp_path, "song.mp3")
    converter.add_paths([song], announce=False)
    converter.preview(original=True)  # preview 1
    converter.preview(original=True)  # again: stop (and number 2 orphans it)
    converter.preview(original=True)  # preview 3
    wavs = [tmp_path / f"quill-converter-preview-{os.getpid()}-{n}.wav" for n in (1, 3)]
    for wav in wavs:
        wav.write_bytes(b"RIFF")  # what render_preview would have written
    jobs[0](None, None)  # the stopped preview finishes rendering late
    assert played == [None] and not wavs[0].exists()  # not played, and removed
    jobs[1](None, None)
    assert played == [None, str(wavs[1])]
    converter._preview_ended(1)  # the first one's timer cannot end the second
    assert converter._previewing
    converter._preview_ended(converter._preview_number)
    assert not converter._previewing and not wavs[1].exists()


def test_closing_exits_and_removes_the_tray_icon_and_downloads(
    converter, tmp_path: Path, monkeypatch
) -> None:
    import threading

    from quill.core.audio.convert import CancelToken

    folder = tmp_path / "quill-url-list-x"
    (folder / "Talks").mkdir(parents=True)
    converter._download_folders = [folder]
    cancel = CancelToken()
    worker = threading.Thread(target=lambda: cancel_seen.append(cancel_wait()), daemon=True)
    cancel_seen: list[bool] = []

    def cancel_wait() -> bool:
        while not cancel.is_cancelled():
            threading.Event().wait(0.01)
        return True

    converter._cancel, converter._work_thread = cancel, worker
    worker.start()
    event = _CloseEvent()
    converter._on_converter_close(event)  # nothing is a job: closing exits, no question
    assert event.skipped and not event.vetoed
    assert cancel_seen == [True] and not worker.is_alive()  # stopped and waited for
    assert converter._tray_icon is None and not folder.exists()


def test_closing_during_a_conversion_asks_first(converter, monkeypatch) -> None:
    calls: list[object] = []
    monkeypatch.setattr(converter._wx, "CallAfter", lambda fn, *a: calls.append((fn, a)))
    converter._busy = True
    event = _CloseEvent()
    converter._on_converter_close(event)
    assert event.vetoed and not event.skipped and calls  # the question is deferred
    converter._closing_in_progress = False
    converter.boxes.clear()
    monkeypatch.setattr(converter, "_show_message_box", lambda *_a, **_k: 0)  # No
    assert converter._converter_close_confirm() is None
    converter._busy = False
