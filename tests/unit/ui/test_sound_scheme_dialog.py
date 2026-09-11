"""The Sound Scheme window: what a row says, and what the buttons do to it.

This replaces a source-contract test on the retired Sound Events checklist,
which asserted that each section heading carried an accessible name. That
guarantee has not been dropped -- it has moved. The checklist put a heading
above a run of checkboxes, so a listener had to hear "Editing" and then
*remember* it while arrowing through nine rows that never said which section
they were in. The Sound Scheme window puts the group in every row, so the
question "where am I?" is answered by the row you are on rather than by
something you heard four presses ago. :func:`test_a_row_names_its_group` is the
same promise, kept better, and asserted against the real window instead of
against the text of a file.
"""

from __future__ import annotations

from pathlib import Path

import pytest

wx = pytest.importorskip("wx")

from quill.core.sound_scheme import SchemeDraft  # noqa: E402
from quill.ui.sound_event_labels import EVENT_GROUPS  # noqa: E402
from quill.ui.sound_scheme_dialog import SoundSchemeDialog, known_events  # noqa: E402


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


@pytest.fixture()
def parent(wx_app):
    frame = wx.Frame(None)
    yield frame
    frame.Destroy()
    wx_app.Yield()


def _wav(path: Path, seconds: float = 0.05) -> Path:
    import struct
    import wave

    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(44100 * seconds)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(44100)
        handle.writeframes(struct.pack(f"<{frames}h", *([0] * frames)))
    return path


class _Window:
    """A built dialog plus the things it told us about."""

    def __init__(self, parent, tmp_path, disabled=frozenset(), app_id=""):
        base = tmp_path / "pack"
        _wav(base / "save.wav")
        _wav(base / "error.wav")
        self.played: list[str] = []
        self.said: list[str] = []
        self.dialog = SoundSchemeDialog(
            parent,
            draft=SchemeDraft(
                base_events={"document_saved": "save.wav", "error": "error.wav"},
                base_dir=base,
            ),
            disabled=disabled,
            data_dir=tmp_path / "data",
            available=[("Ink", "")],
            current_pack="",
            play=lambda path: self.played.append(Path(path).name),
            announce=self.said.append,
            app_id=app_id,
        )

    def select(self, event: str) -> int:
        index = self.dialog._rows.index(event)
        self.dialog.events.SetSelection(index)
        self.dialog._on_row_changed()
        return index

    def row(self, event: str) -> str:
        return self.dialog.events.GetString(self.dialog._rows.index(event))

    def close(self) -> None:
        self.dialog.dialog.Destroy()


@pytest.fixture()
def window(parent, tmp_path):
    built = _Window(parent, tmp_path)
    yield built
    built.close()


# ---------------------------------------------------------------------------
# The list


def test_every_event_gets_a_row(window) -> None:
    """An event with no row is a sound you can hear and cannot reach: no way to
    preview it, change it, or switch it off."""
    assert window.dialog.events.GetCount() == len(known_events())


def test_a_rostered_app_is_shown_only_what_it_can_play(parent, tmp_path) -> None:
    """Reported by ear: the window listed a hundred and forty rows in an editor
    that posts twenty-two of them, so most of the list was sounds that could be
    chosen and would never be heard."""
    built = _Window(parent, tmp_path, app_id="quilllite")
    try:
        rows = built.dialog.events.GetCount()
        assert rows == len(known_events("quilllite"))
        assert rows < len(known_events("quill"))
        assert "radio_playing" not in built.dialog._rows
        assert "text_pasted" in built.dialog._rows
    finally:
        built.close()


def test_a_row_names_its_group(window) -> None:
    """The replacement for the old section headings, and better: a listener
    arrowing a list hears the row and nothing else, so a group that lives in a
    heading above is one they must remember rather than one they are told."""
    assert window.row("document_saved").startswith("Documents:")
    assert window.row("error").startswith("Messages:")


def test_a_row_carries_its_whole_state(window) -> None:
    """Name, on or off, which file, how long -- all of it in the one utterance
    the reader makes on arrival, rather than spread across controls below."""
    row = window.row("document_saved")
    assert "Save a document" in row
    assert "on" in row
    assert "save.wav" in row
    assert "ms" in row


def test_a_switched_off_event_says_so_in_its_row(parent, tmp_path) -> None:
    built = _Window(parent, tmp_path, disabled=frozenset({"error"}))
    try:
        assert ": off," in built.row("error")
    finally:
        built.close()


def test_an_event_the_pack_has_no_sound_for_reads_as_silent(window) -> None:
    assert "Silent" in window.row("text_pasted")


# ---------------------------------------------------------------------------
# Playing


def test_arrowing_onto_a_row_plays_it(window) -> None:
    """The whole point of the window: a list of a hundred and forty earcon
    names is unusable, and a list you hear is a catalogue."""
    window.select("document_saved")
    assert window.played[-1:] == ["save.wav"]


def test_the_preview_can_be_switched_off(window) -> None:
    """Somebody hunting for one row should be able to pass forty in silence."""
    window.dialog.preview_as_you_go.SetValue(False)
    window.select("error")
    assert window.played == []


def test_play_works_on_an_event_that_is_switched_off(parent, tmp_path) -> None:
    """A preview has to bypass the disabled set: hearing an event you have
    silenced, to decide whether to un-silence it, is a thing people do."""
    built = _Window(parent, tmp_path, disabled=frozenset({"error"}))
    try:
        built.dialog.preview_as_you_go.SetValue(False)
        built.select("error")
        built.dialog._play_current(spoken=True)
        assert built.played[-1:] == ["error.wav"]
    finally:
        built.close()


def test_playing_silence_says_so_rather_than_doing_nothing(window) -> None:
    """Nothing happening is indistinguishable from a broken button."""
    window.dialog.preview_as_you_go.SetValue(False)
    window.select("text_pasted")
    window.dialog._play_current(spoken=True)
    assert window.played == []
    assert "no sound" in window.said[-1]


def test_arrowing_past_a_silent_row_does_not_narrate_it(window) -> None:
    """Said only when the button was pressed. A list that announced every
    silent row would be unusable for the opposite reason to the one this
    window exists to fix."""
    before = list(window.said)
    window.select("text_pasted")
    assert window.said == before


# ---------------------------------------------------------------------------
# Changing one event


def test_switching_an_event_off_updates_its_row_and_says_which(window) -> None:
    """The row's text changes on an unfocused control -- which a reader does
    not say -- and the checkbox announces only its own new state, not which
    event it belongs to."""
    window.select("document_saved")
    window.dialog.enabled_box.SetValue(False)
    window.dialog._on_enabled_toggled()
    assert ": off," in window.row("document_saved")
    assert window.said[-1] == "Save a document off"


def test_no_sound_and_use_default_are_a_round_trip(window) -> None:
    window.select("document_saved")
    window.dialog._silence()
    assert "Silent" in window.row("document_saved")
    window.dialog._restore_one()
    assert "save.wav" in window.row("document_saved")


def test_a_changed_event_says_so_in_its_row(window) -> None:
    """So somebody scanning the list can see what they have touched."""
    window.select("document_saved")
    window.dialog._silence()
    assert "changed" in window.row("document_saved")


def test_use_default_is_only_offered_when_there_is_something_to_undo(window) -> None:
    window.select("document_saved")
    assert not window.dialog.default_button.IsEnabled()
    window.dialog._silence()
    window.dialog._refresh_detail(play=False)
    assert window.dialog.default_button.IsEnabled()


# ---------------------------------------------------------------------------
# Getting back


def test_restore_all_puts_everything_back_and_switches_it_on(parent, tmp_path) -> None:
    """The escape hatch. Whatever somebody has done in here, getting out must
    never be a sequence of steps that could be got wrong halfway."""
    built = _Window(parent, tmp_path, disabled=frozenset({"error"}))
    try:
        built.select("document_saved")
        built.dialog._silence()
        built.dialog._restore_all()
        assert "save.wav" in built.row("document_saved")
        assert ": on," in built.row("error")
        assert "changed" not in built.row("document_saved")
    finally:
        built.close()


def test_restore_all_says_what_it_did(parent, tmp_path) -> None:
    built = _Window(parent, tmp_path)
    try:
        built.dialog._restore_all()
        assert "switched on" in built.said[-1]
    finally:
        built.close()


# ---------------------------------------------------------------------------
# The catalogue behind the list


def test_the_list_order_is_the_catalogue_order() -> None:
    """The window is built from EVENT_GROUPS, so the two cannot drift."""
    expected = [event for _group, events in EVENT_GROUPS for event in events]
    assert known_events() == expected


def test_a_rostered_list_keeps_the_catalogue_order() -> None:
    """Filtering must not reshuffle: a listener who has learned where the
    clipboard group sits should find it in the same place in either app."""
    lite = known_events("quilllite")
    assert lite == [event for event in known_events() if event in set(lite)]
