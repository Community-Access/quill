"""The Accessible Libraries Hub: one search across every free book source.

Project Gutenberg, Standard Ebooks, LibriVox recordings, Open Library, Google
Books' free ebooks and the NLS BARD public catalogue -- searched together, and
presented as **one row per book** rather than one row per library.

Three things carry this window, and each is here because of how it sounds rather
than how it looks:

* **One row per book.** *Middlemarch* found in four catalogues used to be four
  near-identical rows differing only in a source name near the end -- which under
  a screen reader means hearing the same title four times to learn one fact. The
  rows are :class:`~quill.core.library.works.Work` records now: every edition
  found, on one line, naming every library it came from.
* **Every row says what you can do with it.** *open now*, *catalog record*,
  *account required*, *partner integration required* -- the four-category rule
  (:mod:`quill.core.library.availability`). Pressing Enter on a mixed result list
  otherwise opens a book, or a web page, or does nothing, and the only way to
  find out is to try.
* **Read or listen is a property of the book, not a separate search.** A LibriVox
  recording and a Gutenberg text of the same work group into one row that says
  *read or listen*. Nothing in QUILL joined those two before.

The filter is local to what has already been fetched, so "only what I can open"
costs nothing rather than a second wait. **Catalogs...** adds an OPDS library
QUILL has never heard of -- the payoff for building this half on an open standard.

Accessible by construction: a single-select ``wx.ListBox`` (no checkboxes) with
explicit action buttons; a reviewable, spoken read-only status field; a label on
every control; focus on the results after a search. The heavy search/download is
injectable, so the whole window is unit-testable with no network.
"""

from __future__ import annotations

import webbrowser
from collections.abc import Callable
from pathlib import Path

import wx

from quill.core import library
from quill.core.library import availability
from quill.core.library import catalogs as catalogs_module
from quill.core.library import works as works_module
from quill.core.library.model import Book, LibraryError
from quill.core.library.works import Work

# Display label -> source ids passed to library.search. "Everywhere" is first
# and is the default: somebody looking for a book wants the book, and choosing
# which library might have it is a question only this app knows to ask.
_SOURCES: list[tuple[str, tuple[str, ...]]] = [
    ("Everywhere free", library.FREE_SOURCES),
    ("Project Gutenberg", ("gutenberg",)),
    ("Standard Ebooks", ("standard-ebooks",)),
    ("LibriVox (recordings)", ("librivox",)),
    ("Open Library", ("openlibrary",)),
    ("Google Books (free ebooks)", ("googlebooks",)),
    ("Internet Archive (public domain)", ("archive",)),
    ("NLS BARD (catalog search)", ("bard",)),
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
        data_dir: Path | str | None = None,
    ) -> None:
        super().__init__(
            parent, title="Book Library", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self._dest_dir = Path(dest_dir)
        # Where the catalogue list lives. Separate from where books are saved:
        # one is a setting and the other is a folder somebody may well move.
        self._data_dir = Path(data_dir) if data_dir is not None else Path(dest_dir).parent
        self._search_fn = search_fn or library.search
        self._download_fn = download_fn or library.download_to_path
        self._announce = announce or getattr(parent, "_announce", lambda _t: None)
        self._on_open = on_open
        self._safe_mode = safe_mode
        #: The raw records the last search returned, before grouping. Kept
        #: because the grouped rows are a view of these, not a replacement.
        self._results: list[Book] = []
        #: Every work the last search found, and the subset the filter shows.
        #: Two lists rather than one filtered in place, so changing the filter
        #: never costs a second search.
        self._works: list[Work] = []
        self._shown: list[Work] = []

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

        # Filter: local to the results already fetched, so "only what I can open"
        # is instant rather than a second wait.
        filter_row = wx.BoxSizer(wx.HORIZONTAL)
        filter_row.Add(
            wx.StaticText(self, label="S&how:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4
        )
        self.filter_choice = wx.Choice(self, choices=[label for _id, label in works_module.FILTERS])
        self.filter_choice.SetName("Show which results")
        self.filter_choice.SetSelection(0)
        filter_row.Add(self.filter_choice, 0)
        sizer.Add(filter_row, 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)

        # Edition chooser: one book can exist in several libraries, and which
        # edition is a real question -- a proofread text is not a raw scan.
        # Grouping the row must not take that choice away.
        ed_row = wx.BoxSizer(wx.HORIZONTAL)
        ed_row.Add(
            wx.StaticText(self, label="&Edition:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4
        )
        self.edition_choice = wx.Choice(self, choices=[])
        self.edition_choice.SetName("Which library's edition")
        ed_row.Add(self.edition_choice, 0)
        sizer.Add(ed_row, 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)

        # Format chooser: populated from the selected edition's formats so the
        # reader picks (e.g.) EPUB vs plain text rather than accepting a silent
        # default. Empty until a result is selected.
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
        # For results QUILL cannot open itself -- a BARD catalog record, an Open
        # Library page, a borrowable scan -- hand off to the library's own page.
        # Named for what it does rather than for one provider, because it is now
        # reached from several.
        self.bard_btn = wx.Button(self, label="Open in &Browser")
        self.catalogs_btn = wx.Button(self, label="Catalo&gs...")
        close_btn = wx.Button(self, wx.ID_CANCEL, "&Close")
        self.open_btn.SetDefault()
        # Right-align the buttons with a leading stretch spacer + EXPAND instead of
        # wx.ALIGN_RIGHT (banned by the A11Y-4 dialog contract).
        btns.AddStretchSpacer(1)
        btns.Add(self.open_btn, 0, wx.RIGHT, 6)
        btns.Add(self.dl_btn, 0, wx.RIGHT, 6)
        btns.Add(self.bard_btn, 0, wx.RIGHT, 6)
        btns.Add(self.catalogs_btn, 0, wx.RIGHT, 6)
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
        self.bard_btn.Bind(wx.EVT_BUTTON, lambda _e: self._open_in_bard())
        self.find.Bind(wx.EVT_TEXT_ENTER, lambda _e: self._find_in_results(1))
        self.find_btn.Bind(wx.EVT_BUTTON, lambda _e: self._find_in_results(1))
        self.catalogs_btn.Bind(wx.EVT_BUTTON, lambda _e: self.open_catalogs())
        self.results.Bind(wx.EVT_LISTBOX, lambda _e: self._on_result_selected())
        self.edition_choice.Bind(wx.EVT_CHOICE, lambda _e: self._sync_format_choice())
        self.filter_choice.Bind(wx.EVT_CHOICE, lambda _e: self._apply_filter())

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
                query,
                sources=self._selected_sources(),
                safe_mode=self._safe_mode,
                # Catalogues somebody added themselves are searched like any
                # other source; the search facade never has to know they exist.
                catalogs=catalogs_module.enabled_urls(catalogs_module.load(self._data_dir)),
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
        # One row per book, not one per library: four catalogues holding the same
        # title used to be four near-identical rows read out in full.
        self._works = works_module.group(books)
        self._apply_filter(announce=False)
        if self._shown:
            self.results.SetFocus()
        self._set_status(works_module.summarise(self._works))

    def _apply_filter(self, *, announce: bool = True) -> None:
        """Redraw the results under the chosen filter. Never re-searches."""
        index = self.filter_choice.GetSelection()
        mode = works_module.FILTERS[index][0] if index >= 0 else "all"
        self._shown = works_module.apply_filter(self._works, mode)
        self.results.Set([work.row_label() for work in self._shown])
        if self._shown:
            self.results.SetSelection(0)
        self._on_result_selected()
        if not announce:
            return
        if not self._works:
            self._set_status("Nothing found. Try different words.")
        elif not self._shown:
            # Said plainly rather than shown as an empty list: an empty list and
            # a failed search sound identical, and they are not the same thing.
            self._set_status(
                f"None of the {len(self._works)} books found match that filter. "
                "Choose Everything found to see them all again."
            )
        else:
            self._set_status(f"Showing {len(self._shown)} of {len(self._works)}.")

    def selected_work(self) -> Work | None:
        index = self.results.GetSelection()
        if index < 0 or index >= len(self._shown):
            return None
        return self._shown[index]

    def selected_book(self) -> Book | None:
        """The edition to act on: the one chosen, else the work's best."""
        work = self.selected_work()
        if work is None:
            return None
        index = self.edition_choice.GetSelection()
        if 0 <= index < len(work.editions):
            return work.editions[index]
        return work.best_edition

    def _on_result_selected(self) -> None:
        """Fill the Edition chooser, then the Format chooser under it."""
        work = self.selected_work()
        if work is None:
            self.edition_choice.Set([])
            self.format_choice.Set([])
            self._sync_buttons()
            return
        editions = [works_module.source_name(e.source) for e in work.editions]
        self.edition_choice.Set(editions)
        if editions:
            best = work.best_edition
            self.edition_choice.SetSelection(
                work.editions.index(best) if best in work.editions else 0
            )
        self._sync_format_choice()

    def _sync_buttons(self) -> None:
        """Enable only what the highlighted result can actually do.

        A Download button that is pressed and then explains it cannot download a
        catalog record is worse than one that was never offered -- and the row
        already said which kind it is, so a disabled button agrees with it.
        """
        book = self.selected_book()
        can_open = book is not None and availability.can_open_here(book)
        self.open_btn.Enable(bool(can_open))
        self.dl_btn.Enable(bool(can_open))
        self.bard_btn.Enable(bool(book is not None and book.site_url))

    def _sync_format_choice(self) -> None:
        """Fill the Format chooser from the selected edition, best format first."""
        book = self.selected_book()
        if book is None:
            self.format_choice.Set([])
            self._sync_buttons()
            return
        formats = sorted(book.formats)
        self.format_choice.Set(formats)
        if formats:
            best = book.resolve()
            chosen = best[0] if best and best[0] in formats else formats[0]
            self.format_choice.SetStringSelection(chosen)
        self._sync_buttons()

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
        book = self.selected_book()
        if book is None:
            self._set_status("Choose a book in the results first.")
            return
        if not availability.can_open_here(book):
            # The row said "catalog record" and the button is disabled; this is
            # the belt to that braces, and it names the way forward rather than
            # only refusing.
            self._set_status(availability.describe(book))
            return
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

    def open_catalogs(self) -> None:
        """Manage the OPDS catalogues this window searches.

        Reopened rather than live-refreshed: a catalogue added here changes the
        *next* search, and quietly re-running the current one would replace a
        result list somebody may still be reading.
        """
        from quill.ui.library_catalogs_dialog import LibraryCatalogsDialog

        LibraryCatalogsDialog(self, data_dir=self._dest_dir, announce=self._announce).show()
        self._set_status("Catalog changes apply to your next search.")

    def _open_in_bard(self) -> None:
        """Open the selected result on the library's own page.

        Reached for anything QUILL cannot open itself: a BARD record (obtaining
        the title needs an eligible patron account and happens on their site), an
        Open Library page, a borrowable scan. The outcome is spoken so a
        screen-reader user hears where they were taken.
        """
        book = self.selected_book()
        if book is None:
            self._set_status("Choose a result first.")
            return
        if not book.site_url:
            self._set_status(f"No web page is available for {book.title}.")
            return
        # Speak the hand-off BEFORE opening the browser: webbrowser.open raises the
        # browser to the foreground and the screen reader switches context, which
        # would clip an announcement made afterward. The status field still records
        # it for when the reader returns to QUILL.
        if book.source == "bard":
            self._set_status(
                f"Opening {book.title} in your browser. Sign in on the BARD site to download."
            )
        else:
            self._set_status(f"Opening {book.title} in your browser.")
        webbrowser.open(book.site_url)
