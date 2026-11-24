"""FUX-02, journey A: from QUILL Cast (and Quill Radio) to QUILL, with the reason.

Before this, the standalone apps' Open in QUILL and Send to Editor put the
text on the clipboard and said "Show notes copied to clipboard", even for a
transcript, and then "Sent show notes to a new document" as well; Radio's
button was dimmed for good.
"""

from __future__ import annotations

from pathlib import Path

import pytest

wx = pytest.importorskip("wx")

#: A real QUILL Cast window registers the system-wide hotkeys (see
#: ``pytest_collection_modifyitems`` in ``tests/conftest.py``).
pytestmark = pytest.mark.machine_global


@pytest.fixture
def editor(monkeypatch, tmp_path: Path):
    """QUILL installed, Documents in *tmp_path*; records what was opened."""
    from quill.ui import editor_handoff, scribe_app_host

    opened: list[tuple[Path, int | None]] = []
    monkeypatch.setattr(scribe_app_host, "editor_name", lambda: "QUILL")
    monkeypatch.setattr(
        scribe_app_host,
        "open_in_editor",
        lambda path, line=None: opened.append((Path(path), line)) or "QUILL",
    )
    monkeypatch.setattr(editor_handoff, "documents_folder", lambda app: tmp_path / app)
    return opened


@pytest.fixture
def cast(quill_data_dir: Path, wx_app, quiet_cast_startup, close_cast):
    from quill.core.podcasts.models import PodcastShow
    from quill.core.podcasts.models_episode import PodcastEpisode
    from quill.core.podcasts.subscriptions import PodcastLibrary, save_library

    library = PodcastLibrary()
    show = PodcastShow(id="s1", title="Show 1", feed_url="http://x.invalid/1")
    show.episodes.append(
        PodcastEpisode(
            guid="s1e1",
            title="Episode 1",
            audio_url="http://x.invalid/1/1.mp3",
            published="2026-09-01T06:00:00+00:00",
            description="<p>Guests: Jane.</p>",
        )
    )
    library.add_show(show)
    save_library(quill_data_dir, library)
    from quill.apps.podcasts import PodcastsAppFrame
    from quill.ui.dialog_contract import set_transition_announcement_policy

    frame = PodcastsAppFrame()
    said: list[str] = []
    frame._announce = lambda message, **_kw: said.append(str(message))
    frame.said = said
    try:
        yield frame
    finally:
        set_transition_announcement_policy(None)
        close_cast(frame)


def _cues():
    from quill.core.podcasts.transcripts import TranscriptCue

    return [
        TranscriptCue(start_ms=0, end_ms=1000, text="Welcome."),
        TranscriptCue(start_ms=750_000, end_ms=760_000, text="The part worth keeping."),
    ]


def test_show_notes_are_saved_and_opened_in_quill_said_once(cast, editor, tmp_path) -> None:
    from quill.ui.podcasts import transcript_actions

    episode = cast._podcast_library.find_show("s1").find_episode("s1e1")
    transcript_actions.view_show_notes(cast, episode)
    cast.said.clear()
    cast._show_notes_window._on_send_to_editor_click(None)
    saved = tmp_path / "QUILL Cast" / "Show 1 - Episode 1 show notes.md"
    text = saved.read_text(encoding="utf-8")
    assert text.startswith("# Episode 1\n\n*Show 1*\n\nShow notes, from QUILL Cast.")
    assert "Guests: Jane." in text
    assert editor == [(saved, None)]
    assert cast.said == ["Saved in Documents, in the QUILL Cast folder. Opening it in QUILL."]


def test_the_transcript_opens_at_the_line_with_this_episodes_bookmarks(
    cast, editor, tmp_path
) -> None:
    from quill.core import bookmark_anchors
    from quill.core.media.bookmarks import BookmarkStore
    from quill.ui.podcasts import transcript_actions

    BookmarkStore().add(bookmark_anchors.for_episode("s1", "s1e1"), 750_000, note="keep this")
    show = cast._podcast_library.find_show("s1")
    transcript_actions._open_reader(cast, show, show.find_episode("s1e1"), _cues())
    reader = cast._transcript_window.reader
    reader._text.SetInsertionPoint(reader._text.GetLastPosition())
    cast.said.clear()
    assert reader.send_to_quill() is True
    saved, line = editor[0]
    assert saved == tmp_path / "QUILL Cast" / "Show 1 - Episode 1.md"
    lines = saved.read_text(encoding="utf-8").splitlines()
    assert lines[line - 1].endswith("The part worth keeping.")
    assert "- 12:30: keep this" in lines
    assert any(row.startswith("Sent from QUILL Cast at 12:30 in the audio.") for row in lines)
    assert len(cast.said) == 1 and "copied to clipboard" not in cast.said[0]


def test_the_manager_says_one_sentence_not_a_second_false_one(cast, editor) -> None:
    episode = cast._podcast_library.find_show("s1").find_episode("s1e1")
    cast.said.clear()
    cast._on_send_show_notes_click(episode)
    assert len(cast.said) == 1
    assert "Sent show notes to a new document" not in cast.said


def test_inside_quill_it_is_a_new_document_said_once() -> None:
    from quill.ui.main_frame_podcast_dialogs import PodcastDialogsMixin

    class _Quill:
        def __init__(self) -> None:
            self.opened: list[tuple[str, str]] = []

        def _power_tools_open_text_in_new_buffer(self, text: str, message: str) -> None:
            self.opened.append((text, message))

            self.said: list[str] = []
            self.line: int | None = None

        def go_to_line_number(self, line: int) -> None:
            self.line = line

        def _announce(self, message: str) -> None:
            self.said.append(message)

    host = _Quill()
    PodcastDialogsMixin._podcast_send_show_notes_to_editor(
        host, "Guests", kind="show notes", title="Episode 1", show="Show 1"
    )
    text, message = host.opened[0]
    assert text.startswith("# Episode 1\n\n*Show 1*\n\nShow notes, from QUILL.")
    assert host.said == [message] == ["Opened the show notes in a new document."]


def test_a_radio_transcript_is_offered_and_opens_at_the_caret(wx_app, monkeypatch) -> None:
    from quill.ui import editor_handoff
    from quill.ui.transcript_reader import TranscriptReader

    written: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        editor_handoff, "hand_to_editor", lambda content, **kw: written.append((content, kw))
    )
    parent = wx.Frame(None)
    try:
        reader = TranscriptReader(
            parent,
            title="A video",
            cues=_cues(),
            on_send_to_quill=None,
            source_app="Quill Radio",
            show_title="A channel",
        )
        # Before FUX-02 Radio's button was dimmed for good, with no reason given.
        assert reader._quill_btn.IsEnabled()
        reader._text.SetInsertionPoint(reader._text.GetLastPosition())
        assert reader.send_to_quill() is True
        content, about = written[0]
        assert about["filename"] == "A channel - A video.md"
        assert about["source_app"] == "Quill Radio"
        assert content.splitlines()[about["line"] - 1].endswith("The part worth keeping.")
        reader.dialog.Destroy()
    finally:
        parent.Destroy()


def test_inside_quill_a_transcript_opens_at_the_line_being_read() -> None:
    from quill.ui.main_frame_podcast_dialogs import PodcastDialogsMixin

    class _Quill:
        line: int | None = None

        def _power_tools_open_text_in_new_buffer(self, _text: str, _message: str) -> None:
            pass

        def go_to_line_number(self, line: int) -> None:
            self.line = line

        def _announce(self, _message: str) -> None:
            pass

    host = _Quill()
    PodcastDialogsMixin._podcast_send_show_notes_to_editor(
        host, "# Episode 1\n", kind="transcript", title="Episode 1", line=9, wrapped=True
    )
    assert host.line == 9
