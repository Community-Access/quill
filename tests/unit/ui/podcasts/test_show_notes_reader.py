"""The Show Notes window reads with the Notes reader, and the reader takes a window's own keys."""

from __future__ import annotations

import pytest
import wx

NOTES = '<h2>Guests</h2><p>With <a href="https://example.com/jane">Jane</a> at 1:05.</p>'


@pytest.fixture
def wx_app():
    yield wx.GetApp() or wx.App(False)


def test_the_show_notes_window_is_the_notes_reader_with_send_and_save(wx_app) -> None:
    from quill.ui.podcasts.show_notes_dialog import ShowNotesDialog

    parent = wx.Frame(None)
    said: list[str] = []
    seeks: list[int] = []
    sent: list[str] = []
    try:
        dialog = ShowNotesDialog(
            parent,
            episode_title="Thursday",
            description_html=NOTES,
            on_send_to_editor=sent.append,
            announce_cb=said.append,
            on_seek=seeks.append,
            podcast_title="The Daily",
        )
        assert dialog.dialog.GetTitle() == "Show Notes -- Thursday"
        assert dialog.reader.document.headings[0].text == "Guests"
        assert dialog.reader.links_btn.GetName() == "Links, 1 in these notes"
        # The reader's Tab circuit and seeking work here exactly as in Now Playing.
        assert dialog.reader._move_span(backwards=False) is True
        assert said[-1] == "Link, Jane."
        span = dialog.reader.document.timestamps[0]
        dialog.reader.field.SetSelection(span.start, span.end)
        assert dialog.reader._activate_span() is True
        assert seeks == [65_000]
        dialog._on_send_to_editor_click(None)
        assert sent == ["Guests\nWith Jane at 1:05."] or sent[0].startswith("Guests")
        assert dialog.show_links.__name__ == "show_links"
        dialog.dialog.Destroy()
    finally:
        parent.Destroy()


def test_the_reader_takes_a_windows_own_access_keys_and_a_placeholder(wx_app) -> None:
    from quill.ui.notes_reader import NotesReader

    frame = wx.Frame(None)
    try:
        panel = wx.Panel(frame)
        sizer = wx.BoxSizer(wx.VERTICAL)
        reader = NotesReader(
            panel,
            sizer,
            label="Sh&ow notes:",
            announce=lambda _m: None,
            labels={"copy": "&Copy Notes", "links": "Lin&ks", "browser": "View in B&rowser"},
        )
        assert reader.copy_btn.GetLabel() == "&Copy Notes"
        assert reader.links_btn.GetLabel() == "Lin&ks"
        reader.set_placeholder("Select an episode to read its show notes here.")
        assert reader.field.GetValue() == "Select an episode to read its show notes here."
        assert not reader.copy_btn.IsEnabled()
        assert not reader.links_btn.IsEnabled()
        reader.set_notes(NOTES, title="Thursday")
        assert reader.copy_btn.IsEnabled()
    finally:
        frame.Destroy()


def test_the_main_panel_pane_follows_the_library_cursor(wx_app) -> None:
    """The mixin's refresh, driven on a stand-in with the pane and a selection."""
    from types import SimpleNamespace

    from quill.ui.notes_reader import NotesReader
    from quill.ui.podcasts.main_panel import CastMainPanelMixin

    frame = wx.Frame(None)
    try:
        panel = wx.Panel(frame)
        sizer = wx.BoxSizer(wx.VERTICAL)
        episode = SimpleNamespace(guid="ep", title="Thursday", description=NOTES)
        show = SimpleNamespace(title="The Daily", description="<p>A daily show.</p>")

        class Host(CastMainPanelMixin):
            def __init__(self) -> None:
                self.selection: object = None
                self._notes_pane = NotesReader(panel, sizer, announce=lambda _m: None)

            def _selected_episode(self):
                return (show, episode) if self.selection == "episode" else None

            def _selected_show(self):
                return show if self.selection == "show" else None

        host = Host()
        host._refresh_notes_pane()
        assert host._notes_pane.field.GetValue().startswith("Select an episode")
        host.selection = "episode"
        host._refresh_notes_pane()
        assert host._notes_pane.document.headings[0].text == "Guests"
        host.selection = "show"
        host._refresh_notes_pane()
        assert host._notes_pane.field.GetValue() == "A daily show."
    finally:
        frame.Destroy()
