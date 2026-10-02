"""The Notes reader: show notes you can read, not a block you can only hear.

qc.md 5c. One surface used in three places -- the show-notes pane in Now
Playing, the Show Notes window for any other episode, and a podcast's own
description -- built once here over :mod:`quill.core.podcasts.notes_render`.

It is a **native** read-only rich edit (``wx.TextCtrl`` with ``TE_RICH2``),
not ``wx.richtext``: the native control is what every screen reader already
reads as an edit field, line by line and word by word, and a custom-drawn
control would have cost every one of those habits. The structure the notes
had is kept on top of it:

* **Headings** are bold and larger, and **H** / **Shift+H** move between them
  and say "Heading level 2, This week" -- the reader's own heading keys do
  not work inside an edit field, so the field answers them itself.
* **Links are links.** Underlined, **Tab** / **Shift+Tab** move between them
  (and between timestamps) selecting the link text so the reader reads it,
  with "Link, Jane and Co" said; **Enter** opens the link in the browser after
  saying so. The link text is what is read, never the raw address.
* **Timestamps are links to the episode.** Enter on "12:34" seeks there when
  the host gave the reader an ``on_seek``; the caller decides what to do when
  nothing is playing.
* **Ctrl+F** finds inside the notes with the count spoken; **F3** is next.
* **Copy Notes** (Alt+N) copies the whole notes in the format chosen in
  Preferences, and its context menu offers all four formats one key away.
  **Links** (Alt+L) opens Links in These Notes, and is enabled only when there
  is one, with its name saying how many. **View in Browser** (Alt+R) renders
  the notes to a temporary page and opens it.

GATE-13: nothing is announced on focus; the field is what the reader reads.
The announcements here are the ones only the reader knows: a link's title on
Tab, a heading's level, a count, an outcome.
"""

from __future__ import annotations

import tempfile
import webbrowser
from collections.abc import Callable
from pathlib import Path
from typing import Any

import wx

from quill.core.podcasts import notes_export
from quill.core.podcasts.notes_render import NotesDocument, Span, empty_sentence, render_notes
from quill.core.text_links import Link

__all__ = ["NotesReader"]

_PAGES: list[Path] = []


def _spoken_time(ms: int) -> str:
    from quill.core.media.timecode import format_spoken

    return format_spoken(ms)


class NotesReader:
    """A read-only notes field, its navigation keys and its three buttons."""

    def __init__(
        self,
        parent: Any,
        sizer: Any,
        *,
        label: str = "Show n&otes:",
        announce: Callable[[str], None],
        on_seek: Callable[[int], None] | None = None,
        show_modal: Callable[[Any, str], int] | None = None,
        copy_format: Callable[[], str] = lambda: notes_export.DEFAULT_FORMAT,
        set_copy_format: Callable[[str], None] | None = None,
        what: str = "the show notes",
        min_height: int = 160,
        labels: dict[str, str] | None = None,
    ) -> None:
        """*labels* overrides the button captions' access keys per window:
        ``copy``, ``links``, ``browser`` -- the defaults are Copy &Notes, &Links
        and View in B&rowser, and a window whose menu bar or siblings already
        claim N or L passes its own (GATE-14, GATE-15)."""
        names = {"copy": "Copy &Notes", "links": "&Links", "browser": "View in B&rowser"}
        names.update(labels or {})
        self._parent = parent
        self._announce = announce
        self._on_seek = on_seek
        self._show_modal = show_modal
        self._copy_format = copy_format
        self._set_copy_format = set_copy_format
        self._what = what
        self._doc: NotesDocument = render_notes("")
        self._html = ""
        self._title = ""
        self._podcast = ""
        self._spans: list[Span] = []
        self._find_text = ""
        self._find_at = -1

        # The label is created immediately before the field, which is its
        # accessible name on wxMSW.
        self.caption = wx.StaticText(parent, label=label)
        self.field = wx.TextCtrl(
            parent, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 | wx.TE_WORDWRAP
        )
        self.field.SetMinSize((-1, min_height))
        self.field.SetHelpText(
            "The notes the show published, with their headings, lists and links kept. "
            "Read only: arrow through it; H and Shift+H move between headings; Tab and "
            "Shift+Tab move between links and timestamps and Enter opens or seeks; "
            "Ctrl+F finds and F3 finds the next."
        )
        sizer.Add(self.caption, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        sizer.Add(self.field, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        row = wx.BoxSizer(wx.HORIZONTAL)
        self.copy_btn = wx.Button(parent, label=names["copy"])
        self.copy_btn.SetHelpText(
            "Copies the whole notes in the format chosen in Preferences. The "
            "Applications key on this button offers every format: plain text, plain "
            "text with links, Markdown, or formatted."
        )
        self.links_btn = wx.Button(parent, label=names["links"])
        self.links_btn.SetHelpText(
            "Lists every link in these notes, with its title and where it goes: open "
            "one in your browser, or copy its address."
        )
        self.browser_btn = wx.Button(parent, label=names["browser"])
        self.browser_btn.SetHelpText(
            "Opens the notes as the podcast wrote them, with any images, in your "
            "default browser. The page is temporary and carries no scripts."
        )
        for button in (self.copy_btn, self.links_btn, self.browser_btn):
            row.Add(button, 0, wx.RIGHT, 6)
        sizer.Add(row, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 8)

        self.copy_btn.Bind(wx.EVT_BUTTON, lambda _e: self.copy_notes())
        self.copy_btn.Bind(wx.EVT_CONTEXT_MENU, self._on_copy_menu)
        self.links_btn.Bind(wx.EVT_BUTTON, lambda _e: self.show_links())
        self.browser_btn.Bind(wx.EVT_BUTTON, lambda _e: self.view_in_browser())
        self.field.Bind(wx.EVT_CHAR_HOOK, self._on_key)
        self.set_notes("", title="", podcast="")

    # -- content ---------------------------------------------------------------

    @property
    def document(self) -> NotesDocument:
        return self._doc

    def set_notes(self, html: str, *, title: str, podcast: str = "") -> None:
        """Show *html* as structured notes; empty cases say so in words."""
        self._title = title
        self._podcast = podcast
        self._html = html or ""
        self._doc = render_notes(html)
        self._find_at = -1
        if self._doc.is_empty:
            self.field.SetValue(empty_sentence(self._doc))
            self._spans = []
        else:
            self.field.SetValue(self._doc.text)
            self._style()
            self._spans = sorted([*self._doc.links, *self._doc.timestamps], key=lambda s: s.start)
        self.field.SetInsertionPoint(0)
        count = self._doc.link_count
        self.links_btn.Enable(count > 0)
        self.links_btn.SetName(
            f"Links, {count} in these notes" if count else "Links, none in these notes"
        )
        self.copy_btn.Enable(not self._doc.is_empty)
        self.browser_btn.Enable(bool((html or "").strip()))

    def set_placeholder(self, text: str) -> None:
        """No episode to read: say so in the field and dim the buttons."""
        self.set_notes("", title="", podcast="")
        self.field.SetValue(text)

    def _style(self) -> None:
        base = self.field.GetFont()
        for block in self._doc.headings:
            heading = wx.TextAttr()
            font = wx.Font(base)
            font.SetWeight(wx.FONTWEIGHT_BOLD)
            font.SetPointSize(base.GetPointSize() + max(1, 4 - min(block.level, 3)))
            heading.SetFont(font)
            self.field.SetStyle(block.offset, block.offset + len(block.text), heading)
        link_attr = wx.TextAttr()
        link_font = wx.Font(base)
        link_font.SetUnderlined(True)
        link_attr.SetFont(link_font)
        link_attr.SetTextColour(wx.Colour(0, 0, 238))
        for span in (*self._doc.links, *self._doc.timestamps):
            self.field.SetStyle(span.start, span.end, link_attr)

    # -- keys ------------------------------------------------------------------------

    def _on_key(self, event: Any) -> None:
        key = event.GetKeyCode()
        shift = event.ShiftDown()
        if key == wx.WXK_TAB and not event.ControlDown():
            if self._move_span(backwards=shift):
                return
            event.Skip()
            return
        if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            if self._activate_span():
                return
            event.Skip()
            return
        if key == ord("H") and not event.ControlDown() and not event.AltDown():
            self._move_heading(backwards=shift)
            return
        if key == ord("F") and event.ControlDown():
            self.find()
            return
        if key == wx.WXK_F3:
            self.find_next()
            return
        event.Skip()

    def _span_at_caret(self) -> Span | None:
        caret = self.field.GetInsertionPoint()
        start, end = self.field.GetSelection()
        for span in self._spans:
            if span.start <= caret <= span.end or (start, end) == (span.start, span.end):
                return span
        return None

    def _move_span(self, *, backwards: bool) -> bool:
        if not self._spans:
            self._announce("No links or timestamps in these notes.")
            return False
        caret = self.field.GetInsertionPoint()
        current = self._span_at_caret()
        if backwards:
            candidates = [s for s in self._spans if s.start < (current.start if current else caret)]
            target = candidates[-1] if candidates else self._spans[-1]
        else:
            after = current.end if current else caret
            candidates = [s for s in self._spans if s.start >= after and s is not current]
            target = candidates[0] if candidates else self._spans[0]
        self.field.SetSelection(target.start, target.end)
        self.field.ShowPosition(target.start)
        self._announce(self._span_sentence(target))
        return True

    def _span_sentence(self, span: Span) -> str:
        if span.is_timestamp:
            return f"Timestamp, {_spoken_time(span.ms)}. Enter plays from there."
        return f"Link, {self._doc.link_title(span)}."

    def _activate_span(self) -> bool:
        span = self._span_at_caret()
        if span is None:
            return False
        if span.is_timestamp:
            if self._on_seek is None:
                self._announce("Nothing is playing to move within.")
                return True
            self._on_seek(span.ms)
            return True
        self._open(span.url, self._doc.link_title(span))
        return True

    def _open(self, url: str, title: str) -> None:
        try:
            webbrowser.open(url)
        except Exception:  # noqa: BLE001 - a browser that will not start is an answer
            self._announce(f"{title} could not be opened.")
            return
        self._announce(f"Opened {title} in your browser.")

    def _move_heading(self, *, backwards: bool) -> None:
        headings = self._doc.headings
        if not headings:
            self._announce("No headings in these notes.")
            return
        caret = self.field.GetInsertionPoint()
        if backwards:
            candidates = [h for h in headings if h.offset < caret]
            target = candidates[-1] if candidates else None
        else:
            candidates = [h for h in headings if h.offset > caret]
            target = candidates[0] if candidates else None
        if target is None:
            self._announce("No more headings." if not backwards else "No previous heading.")
            return
        self.field.SetInsertionPoint(target.offset)
        self.field.ShowPosition(target.offset)
        self._announce(f"Heading level {target.level or 2}, {target.text}")

    # -- find ------------------------------------------------------------------------

    def find(self) -> None:
        dialog = wx.TextEntryDialog(
            self._parent, "Find in the notes:", "Find", value=self._find_text
        )
        try:
            if self._show(dialog, "Find") != wx.ID_OK:
                return
            needle = dialog.GetValue().strip()
        finally:
            dialog.Destroy()
        if not needle:
            return
        self._find_text = needle
        self._find_at = -1
        count = self._doc.text.lower().count(needle.lower())
        if not count:
            self._announce(f"No match for {needle}.")
            return
        self.find_next(say_count=count)

    def find_next(self, *, say_count: int = 0) -> None:
        if not self._find_text:
            self.find()
            return
        haystack = self._doc.text.lower()
        needle = self._find_text.lower()
        start = haystack.find(needle, self._find_at + 1)
        wrapped = False
        if start < 0:
            start = haystack.find(needle)
            wrapped = True
        if start < 0:
            self._announce(f"No match for {self._find_text}.")
            return
        self._find_at = start
        self.field.SetSelection(start, start + len(needle))
        self.field.ShowPosition(start)
        line = self._doc.text[:start].count("\n") + 1
        said = f"Line {line}"
        if say_count:
            said = f"{say_count} match{'es' if say_count != 1 else ''}. " + said
        elif wrapped:
            said = "Wrapped to the top. " + said
        self._announce(said)

    # -- the buttons -------------------------------------------------------------

    def _show(self, dialog: Any, title: str) -> int:
        if self._show_modal is not None:
            return int(self._show_modal(dialog, title))
        from quill.ui.dialog_contract import show_modal_dialog

        return int(show_modal_dialog(dialog, title, announce=self._announce))

    def copy_notes(self, fmt: str | None = None) -> str:
        """Copy the whole notes in *fmt* (else the preferred format). Returns the text."""
        if self._doc.is_empty:
            self._announce("There are no notes to copy.")
            return ""
        chosen = notes_export.normalize_format(fmt or self._copy_format())
        text = notes_export.export(self._doc, chosen)
        if not wx.TheClipboard.Open():
            self._announce("The clipboard is busy; nothing was copied.")
            return ""
        try:
            if chosen == notes_export.FORMATTED:
                composite = wx.DataObjectComposite()
                composite.Add(wx.HTMLDataObject(text), True)
                composite.Add(wx.TextDataObject(notes_export.to_plain(self._doc)))
                try:
                    rtf = wx.CustomDataObject(wx.DataFormat("Rich Text Format"))
                    rtf.SetData(notes_export.to_rtf(self._doc).encode("utf-8"))
                    composite.Add(rtf)
                except Exception:  # noqa: BLE001 - RTF is a bonus beside HTML and text
                    pass
                wx.TheClipboard.SetData(composite)
            else:
                wx.TheClipboard.SetData(wx.TextDataObject(text))
        finally:
            wx.TheClipboard.Close()
        self._announce(notes_export.spoken_copy(chosen, self._doc, what=self._what))
        return text

    def _on_copy_menu(self, _event: Any) -> None:
        menu = wx.Menu()
        current = notes_export.normalize_format(self._copy_format())
        for fmt in notes_export.FORMATS:
            label = notes_export.FORMAT_LABELS[fmt]
            item = menu.AppendRadioItem(wx.ID_ANY, f"Copy as {label}")
            if fmt == current:
                item.Check(True)
            self.copy_btn.Bind(wx.EVT_MENU, lambda _e, chosen=fmt: self._copy_as(chosen), item)
        self.copy_btn.PopupMenu(menu)
        menu.Destroy()

    def _copy_as(self, fmt: str) -> None:
        if self._set_copy_format is not None:
            self._set_copy_format(fmt)
        self.copy_notes(fmt)

    def links(self) -> list[Link]:
        return [Link(span.url, self._doc.link_title(span)) for span in self._doc.unique_links()]

    def show_links(self) -> None:
        links = self.links()
        if not links:
            self._announce("No links in these notes.")
            return
        from quill.ui.link_list_dialog import LinkListDialog

        remembered = self.field.GetInsertionPoint()
        dialog = LinkListDialog(
            self._parent,
            links=links,
            title="Links in These Notes",
            announce_cb=self._announce,
            show_modal_dialog=self._show_modal,
        )
        dialog.show()
        self.field.SetInsertionPoint(remembered)
        self.field.SetFocus()

    def view_in_browser(self) -> None:
        if self._doc.is_empty and not self._doc.had_media:
            self._announce("There are no notes to show.")
            return
        page_title = f"{self._podcast} - {self._title}" if self._podcast else self._title
        html = notes_export.browser_page(
            self._html, title=self._title or "Show notes", page_title=page_title
        )
        try:
            handle = tempfile.NamedTemporaryFile(
                "w", suffix=".html", prefix="quill-notes-", delete=False, encoding="utf-8"
            )
            with handle:
                handle.write(html)
            path = Path(handle.name)
            _PAGES.append(path)
            webbrowser.open(path.as_uri())
        except Exception:  # noqa: BLE001 - a page that cannot be written or opened is an answer
            self._announce("The notes could not be opened in your browser.")
            return
        self._announce("Opened the notes in your browser.")


def forget_pages() -> None:
    """Delete the temporary pages View in Browser wrote. Called at exit."""
    while _PAGES:
        page = _PAGES.pop()
        try:
            page.unlink(missing_ok=True)
        except Exception:  # noqa: BLE001 - a page the browser still holds is deleted next time
            pass
