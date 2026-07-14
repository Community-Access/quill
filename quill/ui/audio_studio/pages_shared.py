"""Audio Studio wizard — pages shared by both journeys (book details, summary)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import wx

from quill.core.i18n import _
from quill.ui.audio_studio.pages_base import StudioPage
from quill.ui.audio_studio.request import (
    BOOK_FORMAT_INDEX,
    BOOK_FORMATS,
    BatchSpeechRequest,
)
from quill.ui.dialog_contract import show_message_box


class BookPage(StudioPage):
    """The book: tags, cover, format, mastering, and the review step.

    For the combine-audio journey the assembly toggle is forced on (that journey
    IS the book build); for the documents journey it is optional, exactly like
    the classic dialog's "Assemble the results into one audiobook".
    """

    def __init__(
        self,
        parent: wx.Window,
        defaults: BatchSpeechRequest,
        *,
        forced: bool = False,
        source_provider: Callable[[], BatchSpeechRequest] | None = None,
    ) -> None:
        super().__init__(
            parent,
            "audio_studio.book",
            _("Tell me about the book"),
            _("Titles and tags travel with the book in every player."),
        )
        self._forced = forced
        self._source_provider = source_provider

        self.make_book = wx.CheckBox(self, label=_("Assemble the results into one audioboo&k"))
        self.make_book.SetValue(True if forced else defaults.make_book)
        self.make_book.Bind(wx.EVT_CHECKBOX, lambda _e: self.sync_enabled())
        if forced:
            self.make_book.Hide()
        else:
            self.sizer.Add(self.make_book, 0, wx.LEFT | wx.TOP, 12)

        grid = wx.FlexGridSizer(cols=2, vgap=4, hgap=8)
        grid.AddGrowableCol(1, 1)
        self.title = self._field(grid, _("Book ti&tle:"), defaults.book_title)
        self.author = self._field(grid, _("A&uthor:"), defaults.book_author)
        self.narrator = self._field(grid, _("Narra&tor:"), defaults.book_narrator)
        self.genre = self._field(grid, _("Gen&re:"), defaults.book_genre)
        self.year = self._field(grid, _("Yea&r:"), defaults.book_year)
        self.sizer.Add(grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)

        lookup_btn = wx.Button(self, label=_("Look up book detai&ls..."))
        lookup_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_lookup())
        self.sizer.Add(lookup_btn, 0, wx.LEFT | wx.TOP, 12)
        self._lookup_consented = False

        self.add_label(_("Cover ima&ge (auto-detected from the folder; optional):"))
        cover_row = wx.BoxSizer(wx.HORIZONTAL)
        self.cover = wx.TextCtrl(self, value=defaults.book_cover_path)
        self.cover.SetName(_("Cover image"))
        cover_browse = wx.Button(self, label=_("Browse co&ver..."))
        cover_browse.Bind(wx.EVT_BUTTON, self._on_browse_cover)
        cover_row.Add(self.cover, 1, wx.EXPAND | wx.RIGHT, 6)
        cover_row.Add(cover_browse, 0)
        self.sizer.Add(cover_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        fmt_row = wx.BoxSizer(wx.HORIZONTAL)
        fmt_row.Add(wx.StaticText(self, label=_("Book for&mat:")), 0, wx.ALIGN_CENTER_VERTICAL)
        self.format = wx.Choice(
            self,
            choices=[_("M4B audiobook (native chapters)"), _("MP3 (with chapter markers)")],
        )
        self.format.SetName(_("Book format"))
        self.format.SetSelection(BOOK_FORMAT_INDEX.get(defaults.book_format, 0))
        self.format.Bind(wx.EVT_CHOICE, lambda _e: self._sync_output_suffix())
        fmt_row.Add(self.format, 0, wx.LEFT, 6)
        self.sizer.Add(fmt_row, 0, wx.LEFT | wx.TOP, 12)

        self.acx = wx.CheckBox(self, label=_("Normalize the book to ACX (Audible) lou&dness"))
        self.acx.SetValue(defaults.book_acx_normalize)
        self.sizer.Add(self.acx, 0, wx.LEFT | wx.TOP, 12)

        polish_grid = wx.FlexGridSizer(cols=2, vgap=4, hgap=8)
        self.fade_in = self._ms_spin(
            polish_grid, _("Fade &in at each chapter start (ms):"), defaults.book_fade_in_ms
        )
        self.fade_out = self._ms_spin(
            polish_grid, _("Fade out at each chapter &end (ms):"), defaults.book_fade_out_ms
        )
        polish_grid.Add(
            wx.StaticText(self, label=_("Book temp&o (1.0 = as recorded):")),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self.tempo = wx.SpinCtrlDouble(
            self, min=0.5, max=2.0, inc=0.05, initial=max(0.5, min(2.0, defaults.book_tempo))
        )
        from quill.ui.audio_studio.pages_base import set_accessible_name

        set_accessible_name(self.tempo, _("Book tempo"))
        polish_grid.Add(self.tempo, 0)
        self.sizer.Add(polish_grid, 0, wx.LEFT | wx.TOP, 12)
        self.credits = wx.CheckBox(
            self, label=_("Add spo&ken opening and closing credits (uses the chosen voice)")
        )
        self.credits.SetValue(defaults.book_credits)
        if forced:
            # The combine-audio journey has no narration voice to speak them with.
            self.credits.Hide()
        else:
            self.sizer.Add(self.credits, 0, wx.LEFT | wx.TOP, 12)
        self.review = wx.CheckBox(
            self, label=_("&Review chapters (rename/reorder/merge) before building")
        )
        self.review.SetValue(True if forced else defaults.book_review_chapters)
        if forced:
            # The combine-audio journey always reviews; state it, don't offer it.
            self.review.Hide()
            self.sizer.Add(
                wx.StaticText(
                    self,
                    label=_("You will review the chapter list before the book is built."),
                    name="audio_studio.book_review_note",
                ),
                0,
                wx.LEFT | wx.TOP,
                12,
            )
        else:
            self.sizer.Add(self.review, 0, wx.LEFT | wx.TOP, 12)

        self.add_label(_("Save the book &as (blank = the source folder):"))
        out_row = wx.BoxSizer(wx.HORIZONTAL)
        self.output = wx.TextCtrl(self, value=defaults.book_output_path)
        self.output.SetName(_("Save the book as"))
        out_browse = wx.Button(self, label=_("Browse boo&k..."))
        out_browse.Bind(wx.EVT_BUTTON, self._on_browse_output)
        out_row.Add(self.output, 1, wx.EXPAND | wx.RIGHT, 6)
        out_row.Add(out_browse, 0)
        self.sizer.Add(out_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        self._book_controls: list[wx.Window] = [
            self.title,
            self.author,
            self.narrator,
            self.genre,
            self.year,
            self.cover,
            cover_browse,
            self.format,
            self.acx,
            self.review,
            self.output,
            out_browse,
        ]
        self.sync_enabled()

    def _field(self, grid: wx.FlexGridSizer, text: str, value: str) -> wx.TextCtrl:
        grid.Add(wx.StaticText(self, label=text), 0, wx.ALIGN_CENTER_VERTICAL)
        ctrl = wx.TextCtrl(self, value=value)
        ctrl.SetName(text.replace("&", "").rstrip(":"))
        grid.Add(ctrl, 0, wx.EXPAND)
        return ctrl

    def _ms_spin(self, grid: wx.FlexGridSizer, text: str, value: int) -> wx.SpinCtrl:
        from quill.ui.audio_studio.pages_base import set_accessible_name

        grid.Add(wx.StaticText(self, label=text), 0, wx.ALIGN_CENTER_VERTICAL)
        spin = wx.SpinCtrl(self, min=0, max=10000, initial=max(0, int(value)))
        set_accessible_name(spin, text.replace("&", "").rstrip(":"))
        grid.Add(spin, 0)
        return spin

    def sync_enabled(self) -> None:
        """Enable the book fields only while assembly is on (always on when forced)."""
        on = self.make_book.GetValue()
        for ctrl in self._book_controls:
            ctrl.Enable(on)

    def _on_lookup(self) -> None:
        """Fill the fields from Open Library / MusicBrainz (consented, explicit)."""
        title = self.title.GetValue().strip()
        if not title:
            show_message_box(
                str(_("Type the book's title first, then look it up.")),
                str(_("Look up book details")),
                wx.OK | wx.ICON_INFORMATION,
                self,
            )
            return
        if not self._lookup_consented:
            answer = show_message_box(
                str(
                    _(
                        "QUILL will contact Open Library and MusicBrainz — free, public"
                        " book catalogs — to search for this title. Only the title and"
                        " author you typed are sent. Continue?"
                    )
                ),
                str(_("Look up book details")),
                wx.YES_NO | wx.ICON_QUESTION,
                self,
            )
            if answer != wx.YES:
                return
            self._lookup_consented = True
        from quill.core.metadata_lookup import search

        busy = wx.BusyCursor()
        try:
            results = search(title, self.author.GetValue().strip())
        finally:
            del busy
        if not results:
            show_message_box(
                str(_("No matches were found for that title.")),
                str(_("Look up book details")),
                wx.OK | wx.ICON_INFORMATION,
                self,
            )
            return
        with wx.SingleChoiceDialog(
            self,
            str(_("Choose the matching book; its details fill the form:")),
            str(_("Look up book details")),
            [r.display for r in results],
        ) as picker:
            if picker.ShowModal() != wx.ID_OK:  # GATE-42-OK: native chooser
                return
            chosen = results[picker.GetSelection()]
        self.title.SetValue(chosen.title or title)
        if chosen.author:
            self.author.SetValue(chosen.author)
        if chosen.genre:
            self.genre.SetValue(chosen.genre)
        if chosen.year:
            self.year.SetValue(chosen.year)
        if chosen.cover_id and not self.cover.GetValue().strip():
            self._offer_cover(chosen.cover_id)

    def _cover_target(self) -> Path | None:
        """Where the fetched jacket should land: cover.jpg beside the sources."""
        if self._source_provider is None:
            return None
        try:
            folder = self._source_provider().source_folder
        except Exception:  # noqa: BLE001 - a half-filled wizard must not crash lookup
            return None
        if not str(folder) or str(folder) == ".":
            return None
        return Path(folder) / "cover.jpg"

    def _offer_cover(self, cover_id: int) -> None:
        """One more consented fetch: the chosen match's jacket as cover.jpg."""
        from quill.core.metadata_lookup import LookupError_, fetch_cover

        target = self._cover_target()
        if target is None:
            return
        answer = show_message_box(
            str(
                _(
                    "The chosen match has a cover image on Open Library."
                    " Download it as {name} next to your audio and use it"
                    " for the book?"
                ).format(name=target.name)
            ),
            str(_("Download cover art")),
            wx.YES_NO | wx.ICON_QUESTION,
            self,
        )
        if answer != wx.YES:
            return
        busy = wx.BusyCursor()
        try:
            written = fetch_cover(cover_id, target)
        except LookupError_ as exc:
            show_message_box(
                str(exc), str(_("Download cover art")), wx.OK | wx.ICON_INFORMATION, self
            )
            return
        finally:
            del busy
        self.cover.SetValue(str(written))

    def current_format(self) -> str:
        idx = self.format.GetSelection()
        return BOOK_FORMATS[idx] if 0 <= idx < len(BOOK_FORMATS) else "m4b"

    def _sync_output_suffix(self) -> None:
        text = self.output.GetValue().strip()
        if not text:
            return
        path = Path(text)
        if not path.name:
            return
        self.output.SetValue(str(path.with_suffix(f".{self.current_format()}")))

    def _on_browse_cover(self, _evt: wx.Event) -> None:
        with wx.FileDialog(
            self,
            _("Choose a cover image"),
            wildcard=_("Images (*.jpg;*.jpeg;*.png)|*.jpg;*.jpeg;*.png"),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dlg:
            if dlg.ShowModal() == wx.ID_OK:  # GATE-42-OK: native file picker
                self.cover.SetValue(dlg.GetPath())

    def _on_browse_output(self, _evt: wx.Event) -> None:
        fmt = self.current_format()
        with wx.FileDialog(
            self,
            _("Save the audiobook as"),
            wildcard=f"{fmt.upper()} (*.{fmt})|*.{fmt}",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dlg:
            if dlg.ShowModal() == wx.ID_OK:  # GATE-42-OK: native file picker
                self.output.SetValue(str(Path(dlg.GetPath()).with_suffix(f".{fmt}")))

    def collect(self, req: BatchSpeechRequest) -> None:
        req.make_book = True if self._forced else self.make_book.GetValue()
        req.book_credits = False if self._forced else self.credits.GetValue()
        req.book_title = self.title.GetValue().strip()
        req.book_author = self.author.GetValue().strip()
        req.book_narrator = self.narrator.GetValue().strip()
        req.book_genre = self.genre.GetValue().strip()
        req.book_year = self.year.GetValue().strip()
        req.book_cover_path = self.cover.GetValue().strip()
        req.book_format = self.current_format()
        req.book_output_path = self.output.GetValue().strip()
        req.book_acx_normalize = self.acx.GetValue()
        req.book_fade_in_ms = int(self.fade_in.GetValue())
        req.book_fade_out_ms = int(self.fade_out.GetValue())
        req.book_tempo = float(self.tempo.GetValue())
        if not self._forced:
            req.book_review_chapters = self.review.GetValue()
        # When forced (combine-audio journey) the source page already decided:
        # review is always on for a single book, off for unattended library mode.


class SummaryPage(StudioPage):
    """Review every choice in plain sentences, then Start."""

    def __init__(self, parent: wx.Window) -> None:
        super().__init__(
            parent,
            "audio_studio.summary",
            _("Review and start"),
            _("Everything below comes from your earlier answers; press Back to change any of it."),
        )
        self._text = wx.TextCtrl(
            self,
            value="",
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP,
            name="audio_studio.summary_text",
        )
        self._text.SetMinSize(wx.Size(-1, 240))
        self.sizer.Add(self._text, proportion=1, flag=wx.EXPAND | wx.ALL, border=12)
        self._latest: BatchSpeechRequest | None = None
        save_job_btn = wx.Button(self, label=_("Save a &job file..."))
        save_job_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_save_job())
        self.sizer.Add(save_job_btn, 0, wx.LEFT | wx.BOTTOM, 12)

    def on_shown(self, req: BatchSpeechRequest) -> None:
        self._latest = req
        self._text.SetValue("\n".join(summary_lines(req)))

    def _on_save_job(self) -> None:
        """Pin this exact run to a portable, hand-editable .quilljob file."""
        if self._latest is None:
            return
        from quill.core.speech.job_file import JOB_EXTENSION, save_job

        with wx.FileDialog(
            self,
            str(_("Save this run as a job file")),
            defaultFile=f"{self._latest.source_folder.name or 'audio-studio'}{JOB_EXTENSION}",
            wildcard=f"QUILL job (*{JOB_EXTENSION})|*{JOB_EXTENSION}",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:  # GATE-42-OK: native file picker
                return
            target = Path(dlg.GetPath())
        try:
            written = save_job(target, self._latest)
        except OSError as exc:
            show_message_box(
                str(_("Could not write the job file: {error}").format(error=exc)),
                str(_("Save a job file")),
                wx.OK | wx.ICON_ERROR,
                self,
            )
            return
        show_message_box(
            str(
                _(
                    "Saved {name}. Load it from the Audio Studio's first page — or"
                    " edit it in any text editor — to repeat this exact run."
                ).format(name=written.name)
            ),
            str(_("Save a job file")),
            wx.OK | wx.ICON_INFORMATION,
            self,
        )


def summary_lines(req: BatchSpeechRequest) -> list[str]:
    """Human-readable summary of *req*, one plain sentence per line."""
    yes, no = _("Yes"), _("No")
    lines = [_("Source folder: {folder}").format(folder=req.source_folder)]
    lines.append(_("Include subfolders: {value}").format(value=yes if req.recursive else no))
    if req.extensions:
        lines.append(_("File types: {value}").format(value=", ".join(sorted(req.extensions))))
        lines.append(_("Engine: {value}").format(value=req.engine))
        lines.append(_("Voice: {value}").format(value=req.voice or _("(engine default)")))
        if req.round_robin_voices:
            lines.append(
                _("Round-robin rotation: {value}").format(value=", ".join(req.round_robin_voices))
            )
        if req.translation_targets:
            lines.append(
                _("Translated editions: {value}").format(
                    value=", ".join(code for code, _e, _v in req.translation_targets)
                )
            )
        lines.append(_("Output format: {value}").format(value=req.output_format))
        lines.append(
            _("Chapter mode: {value}").format(
                value=_("one chaptered file per document")
                if req.chapter_mode == "single"
                else _("separate file per article")
            )
        )
        lines.append(
            _("Transition sounder: {value}").format(
                value=_("on, volume {vol}").format(vol=req.sound_volume)
                if req.sound_enabled
                else _("off")
            )
        )
        if req.dry_run:
            lines.append(_("Dry run: preview text only, nothing is synthesized."))
    else:
        lines.append(_("Sources: the audio files already in the folder (no narration)."))
    if req.make_book:
        lines.append(
            _("Audiobook: {title}, saved as {fmt}.").format(
                title=req.book_title or _("(untitled)"), fmt=req.book_format.upper()
            )
        )
        if req.book_acx_normalize:
            lines.append(_("The book is normalized to ACX (Audible) loudness."))
        if req.book_review_chapters:
            lines.append(_("You will review the chapter list before the book is built."))
    lines.append("")
    lines.append(_("Press Start to begin. Progress is announced and can be minimized."))
    return lines
