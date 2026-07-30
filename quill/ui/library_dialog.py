"""Accessible Book Library browser (plan xxx.md Part 4).

Search free/accessible ebook sources (Project Gutenberg via Gutendex, Standard
Ebooks via OPDS), then Download or Download & Open -- the download lands in a file
whose extension matches the format, so it opens in QUILL's reader through the
normal open flow (plain text and EPUB natively).

Accessible by construction: results are a single-select ``wx.ListBox`` (no
checkboxes) with explicit action buttons; the status line is a reviewable,
spoken read-only field; every control has a label; focus moves to the results
after a search. The heavy search/download is injectable so the dialog is
unit-testable without the network.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import wx

from quill.core import library
from quill.core.library.model import Book, LibraryError

# Display label -> source ids passed to library.search.
_SOURCES: list[tuple[str, tuple[str, ...]]] = [
    ("All free sources", ("gutenberg", "googlebooks")),
    ("Project Gutenberg", ("gutenberg",)),
    ("Google Books (free ebooks)", ("googlebooks",)),
    ("Standard Ebooks", ("standard-ebooks",)),
    ("Feedbooks (public domain)", ("feedbooks",)),
]


class LibraryDialog(wx.Dialog):
    """Search a book library and open a chosen title in QUILL."""

    def __init__(
        self,
        parent,
        *,
        dest_dir: Path | str,
        search_fn: Callable[..., list[Book]] | None = None,
        download_fn: Callable[..., Path] | None = None,
        announce: Callable[[str], None] | None = None,
        on_open: Callable[[Path], None] | None = None,
        safe_mode: bool = False,
    ) -> None:
        super().__init__(
            parent, title="Book Library", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self._dest_dir = Path(dest_dir)
        self._search_fn = search_fn or library.search
        self._download_fn = download_fn or library.download_to_path
        self._announce = announce or getattr(parent, "_announce", lambda _t: None)
        self._on_open = on_open
        self._safe_mode = safe_mode
        self._results: list[Book] = []

        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(wx.StaticText(self, label="&Source:"), 0, wx.LEFT | wx.TOP, 6)
        self.source = wx.Choice(self, choices=[label for label, _ in _SOURCES])
        self.source.SetName("Source")
        self.source.SetSelection(0)
        sizer.Add(self.source, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        sizer.Add(wx.StaticText(self, label="Search &for:"), 0, wx.LEFT | wx.TOP, 6)
        row = wx.BoxSizer(wx.HORIZONTAL)
        self.query = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        self.query.SetName("Search for")
        row.Add(self.query, 1, wx.RIGHT, 6)
        self.search_btn = wx.Button(self, label="&Search")
        row.Add(self.search_btn, 0)
        sizer.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        sizer.Add(wx.StaticText(self, label="&Results:"), 0, wx.LEFT | wx.TOP, 6)
        self.results = wx.ListBox(self, style=wx.LB_SINGLE)
        self.results.SetName("Results")
        sizer.Add(self.results, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        # Format chooser: populated from the selected book's available formats so
        # the reader picks (e.g.) EPUB vs plain text rather than accepting a
        # silent default. Empty until a result is selected.
        fmt_row = wx.BoxSizer(wx.HORIZONTAL)
        fmt_row.Add(
            wx.StaticText(self, label="Fo&rmat:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4
        )
        self.format_choice = wx.Choice(self, choices=[])
        self.format_choice.SetName("Download format")
        fmt_row.Add(self.format_choice, 0)
        sizer.Add(fmt_row, 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)

        # Find within results (Ctrl+F / F3 / Shift+F3), parity with the reader
        # shells so a long result list is keyboard-navigable without the mouse.
        find_row = wx.BoxSizer(wx.HORIZONTAL)
        find_row.Add(
            wx.StaticText(self, label="Find in re&sults:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            4,
        )
        self.find = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        self.find.SetName("Find in results")
        find_row.Add(self.find, 1, wx.RIGHT, 6)
        self.find_btn = wx.Button(self, label="Find &next")
        find_row.Add(self.find_btn, 0)
        sizer.Add(find_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        self.status = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(-1, 48))
        self.status.SetName("Status")
        sizer.Add(self.status, 0, wx.EXPAND | wx.ALL, 6)

        btns = wx.BoxSizer(wx.HORIZONTAL)
        self.open_btn = wx.Button(self, label="Download && &Open")
        self.dl_btn = wx.Button(self, label="&Download")
        close_btn = wx.Button(self, wx.ID_CANCEL, "&Close")
        self.open_btn.SetDefault()
        # Right-align the buttons with a leading stretch spacer + EXPAND instead of
        # wx.ALIGN_RIGHT (banned by the A11Y-4 dialog contract).
        btns.AddStretchSpacer(1)
        btns.Add(self.open_btn, 0, wx.RIGHT, 6)
        btns.Add(self.dl_btn, 0, wx.RIGHT, 6)
        btns.Add(close_btn, 0)
        sizer.Add(btns, 0, wx.EXPAND | wx.ALL, 8)

        # Keyboard contract: Escape maps to the Close button (shared modal-id
        # wiring every hardened dialog uses).
        from quill.ui.dialog_contract import apply_modal_ids

        apply_modal_ids(self, cancel_id=wx.ID_CANCEL, cancel_label="Close")

        self.SetSizer(sizer)
        self.SetSize((560, 520))
        self.query.SetFocus()

        self.search_btn.Bind(wx.EVT_BUTTON, self._on_search)
        self.query.Bind(wx.EVT_TEXT_ENTER, self._on_search)
        self.open_btn.Bind(wx.EVT_BUTTON, lambda _e: self._download(open_after=True))
        self.dl_btn.Bind(wx.EVT_BUTTON, lambda _e: self._download(open_after=False))
        self.find.Bind(wx.EVT_TEXT_ENTER, lambda _e: self._find_in_results(1))
        self.find_btn.Bind(wx.EVT_BUTTON, lambda _e: self._find_in_results(1))
        self.results.Bind(wx.EVT_LISTBOX, lambda _e: self._sync_format_choice())

        # Keyboard shortcuts: Ctrl+F focuses Find, F3 / Shift+F3 step matches.
        id_find, id_next, id_prev = wx.NewIdRef(), wx.NewIdRef(), wx.NewIdRef()
        self.Bind(wx.EVT_MENU, lambda _e: self.find.SetFocus(), id=id_find)
        self.Bind(wx.EVT_MENU, lambda _e: self._find_in_results(1), id=id_next)
        self.Bind(wx.EVT_MENU, lambda _e: self._find_in_results(-1), id=id_prev)
        self.SetAcceleratorTable(
            wx.AcceleratorTable([
                (wx.ACCEL_CTRL, ord("F"), id_find),
                (wx.ACCEL_NORMAL, wx.WXK_F3, id_next),
                (wx.ACCEL_SHIFT, wx.WXK_F3, id_prev),
            ])
        )

    def _set_status(self, text: str) -> None:
        self.status.SetValue(text)
        self._announce(text)

    def _selected_sources(self) -> tuple[str, ...]:
        idx = self.source.GetSelection()
        return _SOURCES[idx][1] if idx >= 0 else _SOURCES[0][1]

    def _on_search(self, _e) -> None:
        query = self.query.GetValue().strip()
        if not query:
            self._set_status("Type what to search for first.")
            return
        self.results.Clear()
        self._results = []
        self._set_status("Searching the library...")
        wx.BeginBusyCursor()
        wx.SafeYield(self)
        try:
            books = self._search_fn(
                query, sources=self._selected_sources(), safe_mode=self._safe_mode
            )
        except LibraryError as exc:
            wx.EndBusyCursor()
            self._set_status(f"Search failed: {exc}")
            return
        except Exception as exc:  # noqa: BLE001 - surface any error to the user
            wx.EndBusyCursor()
            self._set_status(f"Error: {exc}")
            return
        wx.EndBusyCursor()
        self._results = books
        for book in books:
            fmts = ", ".join(sorted(book.formats)) or "no downloads"
            self.results.Append(f"{book.title} — {book.authors_label}  [{fmts}]")
        if books:
            self.results.SetSelection(0)
            self._sync_format_choice()
            self.results.SetFocus()
            self._set_status(f"Found {len(books)} book(s). Choose one, then Download.")
        else:
            self.format_choice.Set([])
            self._set_status("No books found. Try different words.")

    def _sync_format_choice(self) -> None:
        """Fill the Format chooser from the selected book, best format first."""
        idx = self.results.GetSelection()
        if not (0 <= idx < len(self._results)):
            self.format_choice.Set([])
            return
        book = self._results[idx]
        formats = sorted(book.formats)
        self.format_choice.Set(formats)
        if formats:
            best = book.resolve()
            chosen = best[0] if best and best[0] in formats else formats[0]
            self.format_choice.SetStringSelection(chosen)

    def _chosen_format(self) -> str:
        """The format key the user picked, or '' to let download choose the best."""
        return self.format_choice.GetStringSelection() if self.format_choice.GetCount() else ""

    def _find_in_results(self, direction: int) -> int:
        """Select the next result whose text contains the Find phrase (wraps).

        ``direction`` is +1 (next) or -1 (previous). Returns the matched index or
        -1; the outcome is always spoken so a screen-reader user hears the jump.
        """
        phrase = self.find.GetValue().strip().lower()
        if not phrase:
            self._set_status("Type a word to find in the results.")
            self.find.SetFocus()
            return -1
        n = self.results.GetCount()
        if n == 0:
            self._set_status("No results to search yet.")
            return -1
        start = self.results.GetSelection()
        if start == wx.NOT_FOUND:
            start = 0 if direction > 0 else n - 1
            offsets = range(n)
        else:
            offsets = range(1, n + 1)
        for step in offsets:
            idx = (start + direction * step) % n
            if phrase in self.results.GetString(idx).lower():
                self.results.SetSelection(idx)
                self.results.SetFocus()
                self._set_status(f"Match {idx + 1} of {n}: {self.results.GetString(idx)}")
                return idx
        self._set_status(f"'{self.find.GetValue().strip()}' not found in results.")
        return -1

    def _download(self, *, open_after: bool) -> None:
        idx = self.results.GetSelection()
        if idx == wx.NOT_FOUND or not (0 <= idx < len(self._results)):
            self._set_status("Choose a book in the results first.")
            return
        book = self._results[idx]
        fmt = self._chosen_format()
        self._set_status(f"Downloading {book.title}...")
        wx.BeginBusyCursor()
        wx.SafeYield(self)
        try:
            path = self._download_fn(book, self._dest_dir, fmt=fmt, safe_mode=self._safe_mode)
        except LibraryError as exc:
            wx.EndBusyCursor()
            self._set_status(f"Download failed: {exc}")
            return
        except Exception as exc:  # noqa: BLE001
            wx.EndBusyCursor()
            self._set_status(f"Error: {exc}")
            return
        wx.EndBusyCursor()
        self._set_status(f"Saved {book.title} to {path}.")
        if open_after and self._on_open is not None:
            self._on_open(path)
            if self.IsModal():
                self.EndModal(wx.ID_OK)
