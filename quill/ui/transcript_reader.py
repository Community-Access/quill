"""One transcript window, shared by Quill Cast and Quill Radio.

Transcripts have been fetchable, parsable, cachable and searchable for a while,
and until now the only thing you could *do* with one was open it as a QUILL
document. That is a good thing to be able to do and it is not reading a
transcript: it cannot follow the audio, it cannot take you to the moment a line
was spoken, and it cannot tell you *when* something you searched for was said.

This is that window, and it is deliberately one window rather than two. Cast
opens it on a podcast episode, Radio opens it on a YouTube video's captions, and
neither owns it -- a second, subtly different transcript reader is exactly the
kind of drift the shared cue parser exists to prevent.

**Why a plain read-only text control and not a list.** A transcript is prose. A
text control gives arrow keys, word and line movement, selection, the screen
reader's own review cursor, and Find, all for nothing and all behaving exactly
the way they behave everywhere else. A custom list would take those away and give
back nothing a listener asked for. The timings live alongside the text rather
than in it: the caret's line is the cue, and the cue knows when it starts.

Four rules this window keeps:

* **Playback never moves your caret.** You are reading; the audio can wait.
  There was once a Follow the Audio checkbox that dragged the cursor along with
  playback, and it was removed (2026-08-18): a caret that moves while you are
  reading is a caret you are fighting, and everything it offered is better
  served by Find, which takes you to a moment you chose rather than to the one
  that happens to be playing.
* **Every position is spoken as words.** "4 minutes 12 seconds", never "4:12",
  which a screen reader reads as an ambiguous pair of numbers.
  ``bounded_playback_ui.spoken_duration`` is the single source for that, here as
  everywhere else.
* **A control that cannot work says why.** Jump to a line needs a player that can
  seek; where there is none, Enter says so rather than doing nothing.
* **Saving keeps the timings.** Plain text, WebVTT and SubRip, because somebody
  who wants to keep a transcript very often wants it in a form another player can
  follow -- writing only flat text would repeat the mistake this whole feature
  exists to correct.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from quill.core.podcasts.transcripts import (
    TranscriptCue,
    cues_to_srt,
    cues_to_text,
    cues_to_vtt,
)
from quill.ui.dialog_contract import apply_modal_ids
from quill.ui.radio.bounded_playback_ui import spoken_duration

#: Save As formats, in the order the dialog offers them. Text first because it
#: is what most people want; the two subtitle formats because somebody keeping
#: a transcript very often wants it in a form another player can follow.
_SAVE_FORMATS: tuple[tuple[str, str, Callable[[Sequence[TranscriptCue]], str]], ...] = (
    # Markdown first, and it is not a nicety: text, WebVTT and SubRip are the
    # formats another *player* wants, and Markdown is the one a **person**
    # wants -- it opens in anything, keeps the speakers as words rather than as
    # a subtitle convention, and is what somebody quoting an episode in an
    # email or a document is going to paste. See core/podcasts/transcript_export.
    ("Markdown", "md", None),  # filled in at call time: it needs the detail setting
    ("Plain text", "txt", cues_to_text),
    ("WebVTT", "vtt", cues_to_vtt),
    ("SubRip", "srt", cues_to_srt),
)


def line_starts(cues: Sequence[TranscriptCue]) -> list[int]:
    """The character offset each cue's line begins at, in the flattened text.

    Pure, and the whole bridge between the two halves of this window: the text
    control knows about characters and the player knows about milliseconds, and
    this is what lets one be turned into the other in both directions without
    either of them learning about the other.

    Built from :func:`cues_to_text`'s own rule -- one line per cue with text --
    so the two can never disagree about which line is which cue.
    """
    offsets: list[int] = []
    position = 0
    for cue in cues:
        if not cue.text.strip():
            # cues_to_text drops these, so they occupy no line. Point them at
            # the line that follows, which is where a listener would land.
            offsets.append(position)
            continue
        offsets.append(position)
        position += len(cue.spoken_label) + 1  # the line, plus its newline
    return offsets


def cue_index_for_offset(offsets: Sequence[int], cues: Sequence[TranscriptCue], offset: int) -> int:
    """Which cue the character at *offset* belongs to, or ``-1``.

    The inverse of :func:`line_starts`, and the reason Enter on any line can seek
    to the right moment however the caret got there -- arrowed, clicked,
    searched, or moved by the screen reader's own review cursor.
    """
    found = -1
    for index, start in enumerate(offsets):
        if start <= offset and cues[index].text.strip():
            found = index
        elif start > offset:
            break
    return found


def describe_position(cue: TranscriptCue) -> str:
    """Where a cue sits, as a listener hears it."""
    return spoken_duration(cue.start_ms)


class TranscriptReader:
    """The transcript window itself.

    The player is injected as two callables rather than as an object, so this
    module knows nothing about either app's player: ``position_ms`` answers where
    playback is, and ``seek_to_ms`` moves it. Either may be ``None`` -- a
    transcript for something that is not playing is still worth reading, and the
    window says plainly which commands that costs.
    """

    def __init__(
        self,
        parent: Any,
        *,
        title: str,
        cues: Sequence[TranscriptCue],
        position_ms: Callable[[], int] | None = None,
        seek_to_ms: Callable[[int], bool] | None = None,
        announce: Callable[[str], None] | None = None,
        show_modal_dialog: Callable[[Any, str], int] | None = None,
        on_send_to_quill: Callable[[str], None] | None = None,
        is_automatic: bool = False,
        show_title: str = "",
        source_url: str = "",
        transcript_detail: str = "",
    ) -> None:
        import wx

        self._wx = wx
        self._cues = list(cues)
        # For the exported file: what it is called, what it came from, and how
        # much scaffolding to keep. The host supplies the last one from its own
        # preference (RadioHistory / PodcastHistory), so a transcript saved
        # from either app comes out the same shape.
        self._title = title
        self._show_title = show_title
        self._source_url = source_url
        self._is_automatic = is_automatic
        self._transcript_detail = transcript_detail
        self._offsets = line_starts(self._cues)
        self._position_ms = position_ms
        self._seek_to_ms = seek_to_ms
        self._announce = announce or (lambda _m: None)
        self._show_modal_dialog = show_modal_dialog
        self._on_send_to_quill = on_send_to_quill

        self._dialog = wx.Dialog(
            parent,
            title=f"Transcript: {title}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        # A real size, not just a floor: the window used to open at whatever
        # its sizer's minimum happened to be, which showed a dozen lines of
        # something that is often an hour of speech ("can we make the
        # transcript window larger to show more text?", 2026-08-18). It is
        # resizable, and this is a starting point worth reading in.
        self._dialog.SetMinSize((640, 520))
        self._dialog.SetSize((1000, 760))
        root = wx.BoxSizer(wx.VERTICAL)

        heading = "&Transcript"
        if is_automatic:
            # Said out loud, not implied. A machine transcript presented as a
            # human one is a confident wrong answer, which is the one kind of
            # output this app refuses to produce.
            heading = "&Transcript (automatic captions -- machine-generated, so expect mistakes)"
        root.Add(wx.StaticText(self._dialog, label=heading), 0, wx.LEFT | wx.TOP, 10)

        self._text = wx.TextCtrl(
            self._dialog,
            value=cues_to_text(self._cues),
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP | wx.TE_PROCESS_ENTER,
        )
        self._text.SetName("Transcript. Enter on a line plays from there; Ctrl+F finds")
        self._text.SetMinSize((-1, 480))
        root.Add(self._text, 1, wx.EXPAND | wx.ALL, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._jump_btn = wx.Button(self._dialog, label="&Play from Here")
        self._find_btn = wx.Button(self._dialog, label="F&ind...")
        self._copy_btn = wx.Button(self._dialog, label="&Copy")
        self._links_btn = wx.Button(self._dialog, label="&Links...")
        self._links_btn.SetName("List every web address in this transcript")
        self._save_btn = wx.Button(self._dialog, label="&Save As...")
        self._quill_btn = wx.Button(self._dialog, label="Open in &QUILL")
        self._close_btn = wx.Button(self._dialog, wx.ID_CANCEL, "Cl&ose")
        for button in (
            self._jump_btn,
            self._find_btn,
            self._copy_btn,
            self._links_btn,
            self._save_btn,
            self._quill_btn,
            self._close_btn,
        ):
            buttons.Add(button, 0, wx.RIGHT, 6)
        self._jump_btn.Enable(seek_to_ms is not None)
        self._quill_btn.Enable(on_send_to_quill is not None)
        root.Add(buttons, 0, wx.ALL, 10)

        self._dialog.SetSizer(root)
        apply_modal_ids(self._dialog, cancel_id=wx.ID_CANCEL)

        self._text.Bind(wx.EVT_TEXT_ENTER, lambda _e: self.jump_to_caret())
        self._text.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        self._jump_btn.Bind(wx.EVT_BUTTON, lambda _e: self.jump_to_caret())
        self._find_btn.Bind(wx.EVT_BUTTON, lambda _e: self.find())
        self._copy_btn.Bind(wx.EVT_BUTTON, lambda _e: self.copy())
        self._links_btn.Bind(wx.EVT_BUTTON, lambda _e: self.show_links())
        self._save_btn.Bind(wx.EVT_BUTTON, lambda _e: self.save_as())
        self._quill_btn.Bind(wx.EVT_BUTTON, lambda _e: self.send_to_quill())
        self._dialog.Bind(wx.EVT_CLOSE, self._on_close)

        self._text.SetFocus()

    # -- the window ------------------------------------------------------------

    @property
    def dialog(self) -> Any:
        return self._dialog

    def show(self) -> int:
        """Show the reader, through the host's modal helper where there is one."""
        title = self._dialog.GetTitle()
        try:
            if self._show_modal_dialog is not None:
                return int(self._show_modal_dialog(self._dialog, title))
            return int(self._dialog.ShowModal())  # dialog_button_contract: exempt
        finally:
            self._dialog.Destroy()

    def _on_close(self, event: Any) -> None:
        event.Skip()

    def _on_char_hook(self, event: Any) -> None:
        wx = self._wx
        key = event.GetKeyCode()
        if event.ControlDown() and key == ord("F") and not event.ShiftDown():
            self.find()
            return
        if event.ControlDown() and event.ShiftDown() and key == ord("L"):
            self.show_links()
            return
        if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self.jump_to_caret()
            return
        event.Skip()

    # -- commands --------------------------------------------------------------

    def caret_cue_index(self) -> int:
        """Which cue the caret is in, however it got there."""
        return cue_index_for_offset(self._offsets, self._cues, self._text.GetInsertionPoint())

    def jump_to_caret(self) -> bool:
        """Play from the line the caret is on. True when playback moved."""
        if self._seek_to_ms is None:
            self._announce("There is nothing playing to move, so this line cannot be played from.")
            return False
        index = self.caret_cue_index()
        if index < 0:
            self._announce("Put the cursor on a line of the transcript first.")
            return False
        cue = self._cues[index]
        if not self._seek_to_ms(cue.start_ms):
            self._announce("That position could not be played.")
            return False
        self._announce(f"Playing from {describe_position(cue)}.")
        return True

    def find(self, query: str = "") -> int:
        """Find *query* forward from the caret. Returns the cue index, or -1.

        Speaks the *position* of the hit as well as moving to it, which is the
        whole reason a transcript reader beats a text file: "found at 12 minutes
        8 seconds" tells you where in the audio to go.
        """
        if not query:
            query = self._ask_for_query()
        if not query:
            return -1
        haystack = self._text.GetValue().lower()
        start = self._text.GetInsertionPoint() + 1
        offset = haystack.find(query.lower(), start)
        if offset < 0:
            offset = haystack.find(query.lower())  # wrap, like every other Find
            if offset < 0:
                self._announce(f"{query} was not found in this transcript.")
                return -1
            self._announce("Searched from the beginning.")
        self._text.SetInsertionPoint(offset)
        self._text.SetSelection(offset, offset + len(query))
        self._text.ShowPosition(offset)
        index = cue_index_for_offset(self._offsets, self._cues, offset)
        if index >= 0:
            # The cursor is already on the hit; this says *when* it was said and
            # what Enter would do about it. Only when there is a real timing to
            # report and something that can act on it -- a transcript with no
            # times, or one opened while nothing is playing, must not be told
            # about a jump it cannot make (2026-08-18).
            cue = self._cues[index]
            said = f"Found at {describe_position(cue)}."
            if self._seek_to_ms is not None:
                said += " Enter plays from here."
            self._announce(said)
        else:
            self._announce(f"Found {query}.")
        return index

    def _ask_for_query(self) -> str:
        wx = self._wx
        entry = wx.TextEntryDialog(self._dialog, "Find in transcript:", "Find")
        try:
            if entry.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return ""
            return entry.GetValue().strip()
        finally:
            entry.Destroy()

    def show_links(self) -> int:
        """List every web address in the transcript, to open or copy.

        A transcript is read-only prose in a text box, so an address in it was
        something to read out and retype. Ctrl+Shift+L, or the Links button.
        """
        from quill.core.text_links import find_links
        from quill.ui.link_list_dialog import LinkListDialog

        links = find_links(self._text.GetValue())
        if not links:
            self._announce("There are no web addresses in this transcript.")
            return 0
        LinkListDialog(
            self._dialog,
            links=links,
            title="Links in This Transcript",
            announce_cb=self._announce,
            show_modal_dialog=self._show_modal_dialog,
        ).show()
        return len(links)

    def copy(self) -> str:
        """Copy the selection, or the whole transcript when nothing is selected."""
        wx = self._wx
        selected = self._text.GetStringSelection()
        text = selected or self._text.GetValue()
        try:
            if wx.TheClipboard.Open():
                try:
                    wx.TheClipboard.SetData(wx.TextDataObject(text))
                finally:
                    wx.TheClipboard.Close()
        except Exception:  # noqa: BLE001 - a clipboard is never worth an exception
            self._announce("The transcript could not be copied.")
            return ""
        self._announce("Copied the selection." if selected else "Copied the whole transcript.")
        return text

    def _markdown_writer(self) -> Callable[[Sequence[TranscriptCue]], str]:
        """The Markdown writer, closed over this transcript's own facts.

        Kept out of :data:`_SAVE_FORMATS` because it is the only format that
        needs more than the cues: the episode and show it belongs to, where it
        came from, whether it is automatic, and how much scaffolding the
        listener asked to keep.
        """
        from quill.core.podcasts import transcript_export

        return lambda cues: transcript_export.cues_to_markdown(
            cues,
            detail=transcript_export.normalize_detail(self._transcript_detail),
            show=self._show_title,
            episode=self._title,
            source_url=self._source_url,
            is_automatic=self._is_automatic,
        )

    def suggested_filename(self, extension: str = "md") -> str:
        """``Show - Episode.md`` -- what the Save dialog should start with.

        A transcript lands in a folder among a hundred others and has to be
        recognisable there a month later, which "transcript.md" never is.
        """
        from quill.core.podcasts import transcript_export

        return transcript_export.safe_filename(self._show_title, self._title, extension=extension)

    def save_as(self) -> str:
        """Write the transcript to a file the listener chooses. Returns the path."""
        wx = self._wx
        wildcard = "|".join(f"{label} (*.{ext})|*.{ext}" for label, ext, _writer in _SAVE_FORMATS)
        dialog = wx.FileDialog(
            self._dialog,
            "Save Transcript As",
            defaultFile=self.suggested_filename(_SAVE_FORMATS[0][1]),
            wildcard=wildcard,
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )
        try:
            if dialog.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return ""
            path = dialog.GetPath()
            _label, extension, writer = _SAVE_FORMATS[max(0, dialog.GetFilterIndex())]
        finally:
            dialog.Destroy()
        if not path.lower().endswith(f".{extension}"):
            path = f"{path}.{extension}"
        if writer is None:  # Markdown: the one format that needs more than cues
            writer = self._markdown_writer()
        try:
            from pathlib import Path

            Path(path).write_text(writer(self._cues), encoding="utf-8")
        except OSError as error:
            self._announce(f"The transcript could not be saved. {error}")
            return ""
        self._announce(f"Saved the transcript to {path}.")
        return path

    def send_to_quill(self) -> bool:
        """Open the transcript as a QUILL document."""
        if self._on_send_to_quill is None:
            self._announce("Opening in QUILL is not available here.")
            return False
        self._on_send_to_quill(self._text.GetValue())
        return True
