"""The Chapter Workbench — open, hear, reshape, and save an existing audiobook.

The Audio Studio's *edit an existing audiobook* journey. One dialog holds the
chapter list (with real times), the chapter-aware player, and the surgery
tools: rename, **split at the playhead** (the fix-a-bad-boundary-by-ear
operation), **set a chapter's start to the playhead**, merge into previous,
restore, and full chapter-list import/export (Audacity, CUE, timestamps,
Podcasting 2.0 JSON, CSV). Book tags are editable in place.

Saving: an MP3 saves **in place** (mutagen rewrites only the tags; the audio
is untouched); an M4B saves as a **new file** (lossless ``-c copy`` re-mux).
Long saves run on the caller-provided background runner so the UI thread
never blocks. Chapter math lives in :mod:`quill.core.speech.chapters`; file
IO in :mod:`quill.core.speech.book_file`.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

import wx

from quill.core.i18n import _
from quill.core.speech.book_file import BookFile, save_m4b_book_as, save_mp3_book
from quill.core.speech.chapter_io import (
    EXPORT_FORMATS,
    ChapterParseError,
    export_chapter_text,
    format_timestamp,
    parse_chapter_text,
    suggested_extension,
)
from quill.core.speech.chapters import (
    Chapter,
    ChapterEditError,
    merge_chapter,
    set_chapter_start,
    split_chapter,
)
from quill.ui.audio_studio.player_panel import PlayerPanel
from quill.ui.dialog_contract import (
    apply_listbox_activation,
    apply_modal_ids,
    show_message_box,
)

_log = logging.getLogger(__name__)

# (menu label, chapter_io format key) for Export chapters...
_EXPORT_LABELS: tuple[tuple[str, str], ...] = (
    ("Audacity labels (.txt)", "audacity"),
    ("Timestamps (.txt)", "timestamps"),
    ("CUE sheet (.cue)", "cue"),
    ("Podcasting 2.0 JSON (.chapters.json)", "pod2"),
    ("CSV spreadsheet (.csv)", "csv"),
)


class ChapterWorkbenchDialog(wx.Dialog):
    """Edit an opened book's chapters and tags, with the player as the anchor."""

    def __init__(
        self,
        parent: wx.Window,
        book: BookFile,
        *,
        announce: Callable[[str], None] | None = None,
        run_background: Callable[..., None] | None = None,
        on_publish: Callable[[BookFile], None] | None = None,
        ask_ai: Callable[[str], str] | None = None,
    ) -> None:
        super().__init__(
            parent,
            title=str(_("Chapter Workbench")),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            name="audio_studio.workbench",
        )
        self._book = book
        self._original_chapters = [
            Chapter(index=c.index, title=c.title, start_ms=c.start_ms, end_ms=c.end_ms)
            for c in book.chapters
        ]
        self._announce_fn = announce
        self._run_background = run_background
        self._on_publish_cb = on_publish
        self._ask_ai = ask_ai
        self._dirty = False

        root = wx.BoxSizer(wx.VERTICAL)
        heading = wx.StaticText(
            self,
            label=_("Editing {name}").format(name=book.path.name),
            name="audio_studio.workbench_heading",
        )
        heading.SetFont(heading.GetFont().Scaled(1.2).Bold())
        root.Add(heading, 0, wx.ALL, 10)

        root.Add(
            wx.StaticText(
                self,
                label=_("C&hapters (select to hear; edits apply on Save):"),
            ),
            0,
            wx.LEFT,
            10,
        )
        self._chapter_list = wx.ListBox(self, style=wx.LB_SINGLE)
        self._chapter_list.SetName(_("Chapters"))
        self._chapter_list.Bind(wx.EVT_LISTBOX, lambda _e: self._on_selected())
        apply_listbox_activation(self._chapter_list, lambda _e: self._play_selected())
        root.Add(self._chapter_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        title_row = wx.BoxSizer(wx.HORIZONTAL)
        title_row.Add(wx.StaticText(self, label=_("Chapter t&itle:")), 0, wx.ALIGN_CENTER_VERTICAL)
        self._title_edit = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        self._title_edit.SetName(_("Chapter title"))
        self._title_edit.Bind(wx.EVT_TEXT_ENTER, lambda _e: self._on_rename())
        rename_btn = wx.Button(self, label=_("Re&name"))
        rename_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_rename())
        title_row.Add(self._title_edit, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)
        title_row.Add(rename_btn, 0)
        root.Add(title_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

        surgery_row = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler in (
            (_("&Split at playhead"), self._on_split),
            (_("Set st&art to playhead"), self._on_retime),
            (_("&Merge into previous"), self._on_merge),
            (_("Rest&ore original"), self._on_restore),
        ):
            btn = wx.Button(self, label=label)
            btn.Bind(wx.EVT_BUTTON, lambda _e, h=handler: h())
            surgery_row.Add(btn, 0, wx.RIGHT, 6)
        root.Add(surgery_row, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)

        analysis_row = wx.BoxSizer(wx.HORIZONTAL)
        propose_btn = wx.Button(self, label=_("Propose chapters from s&ilences..."))
        propose_btn.SetToolTip(
            _(
                "Scan the recording for silences with ffmpeg and propose chapter "
                "boundaries at the silence midpoints. The proposal lands in the list "
                "for review; nothing is applied blind."
            )
        )
        propose_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_propose_from_silences())
        acx_btn = wx.Button(self, label=_("Check against &ACX"))
        acx_btn.SetToolTip(
            _(
                "Measure the book against Audible's ACX submission window and hear "
                "the verdict with plain recommendations for any failing criterion."
            )
        )
        acx_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_check_acx())
        titles_btn = wx.Button(self, label=_("Propose AI tit&les..."))
        titles_btn.SetToolTip(
            _(
                "Transcribe the opening minute of each chapter with the local "
                "speech model, then ask your configured AI for a short title. "
                "Proposals land in the list for review; nothing is applied blind."
            )
        )
        titles_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_propose_ai_titles())
        analysis_row.Add(propose_btn, 0, wx.RIGHT, 6)
        analysis_row.Add(titles_btn, 0, wx.RIGHT, 6)
        analysis_row.Add(acx_btn, 0)
        root.Add(analysis_row, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)

        io_row = wx.BoxSizer(wx.HORIZONTAL)
        import_btn = wx.Button(self, label=_("Import chap&ters..."))
        export_btn = wx.Button(self, label=_("E&xport chapters..."))
        episodes_btn = wx.Button(self, label=_("Split into &files..."))
        import_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_import())
        export_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_export())
        episodes_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_split_into_files())
        io_row.Add(import_btn, 0, wx.RIGHT, 6)
        io_row.Add(export_btn, 0, wx.RIGHT, 6)
        io_row.Add(episodes_btn, 0)
        root.Add(io_row, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)

        self.player = PlayerPanel(self, announce=announce)
        root.Add(self.player, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

        root.Add(wx.StaticText(self, label=_("Book details:")), 0, wx.LEFT | wx.TOP, 10)
        grid = wx.FlexGridSizer(cols=2, vgap=4, hgap=8)
        grid.AddGrowableCol(1, 1)
        self._tag_album = self._tag_field(grid, _("Book ti&tle (album):"), book.tags.album)
        self._tag_artist = self._tag_field(grid, _("A&uthor:"), book.tags.artist)
        self._tag_narrator = self._tag_field(grid, _("Narrato&r:"), book.tags.album_artist)
        self._tag_genre = self._tag_field(grid, _("&Genre:"), book.tags.genre)
        self._tag_year = self._tag_field(grid, _("&Year:"), book.tags.year)
        root.Add(grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._save_btn = wx.Button(self, label=_("&Save"))
        self._save_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_save())
        save_as_btn = wx.Button(self, label=_("Save &As..."))
        save_as_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_save_as())
        self._publish_btn = wx.Button(self, label=_("&Publish..."))
        self._publish_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_publish())
        close_btn = wx.Button(self, wx.ID_CANCEL, label=_("Close"))
        btn_row.AddStretchSpacer()
        btn_row.Add(self._save_btn, 0, wx.RIGHT, 6)
        btn_row.Add(save_as_btn, 0, wx.RIGHT, 6)
        btn_row.Add(self._publish_btn, 0, wx.RIGHT, 6)
        btn_row.Add(close_btn, 0)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)
        if book.kind != "mp3":
            # M4B chapter atoms cannot be rewritten in place; Save As re-muxes.
            self._save_btn.Enable(False)
            self._save_btn.SetToolTip(_("An M4B is saved as a new file; use Save As."))

        apply_modal_ids(self, cancel_id=wx.ID_CANCEL)
        self.Bind(wx.EVT_CLOSE, self._on_close)
        self.SetMinSize(wx.Size(720, 720))
        self.SetSizer(root)
        self.Fit()
        self.CentreOnParent()
        self._refresh_list()
        from quill.core.paths import app_data_dir
        from quill.core.speech.listening_positions import load_position_ms

        self.player.load(
            str(book.path),
            book.chapters,
            resume_ms=load_position_ms(app_data_dir(), book.path),
        )

    # -- helpers ---------------------------------------------------------------

    def _tag_field(self, grid: wx.FlexGridSizer, label: str, value: str) -> wx.TextCtrl:
        grid.Add(wx.StaticText(self, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
        ctrl = wx.TextCtrl(self, value=value)
        ctrl.SetName(label.replace("&", "").rstrip(":"))
        grid.Add(ctrl, 0, wx.EXPAND)
        return ctrl

    def _announce(self, text: str) -> None:
        if self._announce_fn is not None:
            self._announce_fn(text)

    def _error(self, message: str) -> None:
        show_message_box(message, str(_("Chapter Workbench")), wx.OK | wx.ICON_ERROR, self)

    def _selected_index(self) -> int:
        idx = self._chapter_list.GetSelection()
        return idx if 0 <= idx < len(self._book.chapters) else -1

    def _refresh_list(self, *, select: int = -1) -> None:
        self._chapter_list.Set([
            _("{num}. {title} — starts {start}, runs {dur}").format(
                num=c.index + 1,
                title=c.title,
                start=format_timestamp(c.start_ms),
                dur=format_timestamp(c.duration_ms),
            )
            for c in self._book.chapters
        ])
        if self._book.chapters:
            index = select if 0 <= select < len(self._book.chapters) else 0
            self._chapter_list.SetSelection(index)
        self._on_selected()
        self.player.set_chapters(self._book.chapters)

    def _on_selected(self) -> None:
        idx = self._selected_index()
        self._title_edit.SetValue(self._book.chapters[idx].title if idx >= 0 else "")

    def _play_selected(self) -> None:
        idx = self._selected_index()
        if idx >= 0:
            self.player.play_chapter(idx)

    def _apply(self, chapters: list[Chapter], *, select: int, spoken: str) -> None:
        self._book.chapters = chapters
        self._dirty = True
        self._refresh_list(select=select)
        self._announce(spoken)

    # -- edits -------------------------------------------------------------------

    def _on_rename(self) -> None:
        idx = self._selected_index()
        if idx < 0:
            return
        title = self._title_edit.GetValue().strip()
        if not title:
            self._error(str(_("A chapter title cannot be empty.")))
            return
        self._book.chapters[idx].title = title
        self._dirty = True
        self._refresh_list(select=idx)
        self._announce(_("Renamed chapter to {title}").format(title=title))

    def _on_split(self) -> None:
        at_ms = self.player.playhead_ms()
        try:
            chapters = split_chapter(self._book.chapters, at_ms, title=str(_("New chapter")))
        except ChapterEditError as exc:
            self._error(str(exc))
            return
        self._apply(
            chapters,
            select=min(
                len(chapters) - 1, next(i for i, c in enumerate(chapters) if c.start_ms == at_ms)
            ),
            spoken=_("Split at {pos}; now {count} chapters").format(
                pos=format_timestamp(at_ms), count=len(chapters)
            ),
        )

    def _on_retime(self) -> None:
        idx = self._selected_index()
        at_ms = self.player.playhead_ms()
        try:
            chapters = set_chapter_start(self._book.chapters, idx, at_ms)
        except ChapterEditError as exc:
            self._error(str(exc))
            return
        self._apply(
            chapters,
            select=idx,
            spoken=_("Chapter {num} now starts at {pos}").format(
                num=idx + 1, pos=format_timestamp(at_ms)
            ),
        )

    def _on_merge(self) -> None:
        idx = self._selected_index()
        try:
            chapters = merge_chapter(self._book.chapters, idx)
        except ChapterEditError as exc:
            self._error(str(exc))
            return
        self._apply(
            chapters,
            select=max(0, idx - 1),
            spoken=_("Merged; {count} chapters remain").format(count=len(chapters)),
        )

    def _on_restore(self) -> None:
        restored = [
            Chapter(index=c.index, title=c.title, start_ms=c.start_ms, end_ms=c.end_ms)
            for c in self._original_chapters
        ]
        self._apply(
            restored,
            select=0,
            spoken=_("Restored the original {count} chapters").format(count=len(restored)),
        )
        self._dirty = False

    # -- import / export -----------------------------------------------------------

    def _on_import(self) -> None:
        with wx.FileDialog(
            self,
            str(_("Import a chapter list")),
            wildcard=(
                "Chapter lists (*.txt;*.cue;*.json;*.csv)|*.txt;*.cue;*.json;*.csv|"
                "All files (*.*)|*.*"
            ),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:  # GATE-42-OK: native file picker
                return
            path = Path(dlg.GetPath())
        try:
            chapters = parse_chapter_text(path.read_text(encoding="utf-8-sig"), self._book.total_ms)
        except (OSError, ChapterParseError) as exc:
            self._error(str(exc))
            return
        self._apply(
            chapters,
            select=0,
            spoken=_("Imported {count} chapters from {name}").format(
                count=len(chapters), name=path.name
            ),
        )

    def _on_export(self) -> None:
        labels = [label for label, _fmt in _EXPORT_LABELS]
        with wx.SingleChoiceDialog(
            self, str(_("Export the chapter list as:")), str(_("Export chapters")), labels
        ) as picker:
            if picker.ShowModal() != wx.ID_OK:  # GATE-42-OK: native chooser
                return
            fmt = _EXPORT_LABELS[picker.GetSelection()][1]
        assert fmt in EXPORT_FORMATS
        extension = suggested_extension(fmt)
        with wx.FileDialog(
            self,
            str(_("Save the chapter list as")),
            defaultFile=self._book.path.stem + extension,
            wildcard=f"{extension} (*{extension})|*{extension}|All files (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:  # GATE-42-OK: native file picker
                return
            out = Path(dlg.GetPath())
        text = export_chapter_text(
            self._book.chapters,
            fmt,
            audio_filename=self._book.path.name,
            performer=self._tag_artist.GetValue().strip(),
            album=self._tag_album.GetValue().strip(),
        )
        try:
            out.write_text(text, encoding="utf-8")
        except OSError as exc:
            self._error(str(_("Could not write that file: {error}").format(error=exc)))
            return
        self._announce(
            _("Exported {count} chapters to {name}").format(
                count=len(self._book.chapters), name=out.name
            )
        )

    # -- saving ---------------------------------------------------------------------

    def _collect_tags(self) -> None:
        self._book.tags.album = self._tag_album.GetValue().strip()
        self._book.tags.title = self._book.tags.album
        self._book.tags.artist = self._tag_artist.GetValue().strip()
        self._book.tags.album_artist = self._tag_narrator.GetValue().strip()
        self._book.tags.genre = self._tag_genre.GetValue().strip()
        self._book.tags.year = self._tag_year.GetValue().strip()

    def _run_save(self, title: str, work: Callable[[], object], done_message: str) -> None:
        """Run a save on the background pool when available, else inline."""
        if self._run_background is not None:

            def on_success(_result: object) -> None:
                self._dirty = False
                self._announce(done_message)

            self._run_background(title, work, on_success)
            return
        try:
            work()
        except Exception as exc:  # noqa: BLE001 - surfaced, not raised through wx
            self._error(str(exc))
            return
        self._dirty = False
        self._announce(done_message)

    def _on_save(self) -> None:
        self._collect_tags()
        if self._book.kind != "mp3":
            self._on_save_as()
            return
        # The player holds the file open; release it for the in-place rewrite.
        self.player.shutdown()
        book = self._book
        self._run_save(
            str(_("Saving audiobook tags")),
            lambda: save_mp3_book(book),
            str(_("Saved {name}").format(name=book.path.name)),
        )

    def _on_save_as(self) -> None:
        self._collect_tags()
        kind = self._book.kind
        with wx.FileDialog(
            self,
            str(_("Save the book as")),
            defaultFile=self._book.path.stem + f" (edited).{kind}",
            wildcard=f"{kind.upper()} (*.{kind})|*.{kind}",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:  # GATE-42-OK: native file picker
                return
            out = Path(dlg.GetPath())
        book = self._book
        if kind == "mp3":
            import shutil

            def work(_progress: object = None) -> object:
                shutil.copyfile(book.path, out)
                copy = BookFile(
                    path=out, tags=book.tags, chapters=book.chapters, total_ms=book.total_ms
                )
                save_mp3_book(copy)
                return out

        else:

            def work(_progress: object = None) -> object:
                return save_m4b_book_as(book, out)

        self._run_save(
            str(_("Saving audiobook")),
            work,
            str(_("Saved {name}").format(name=out.name)),
        )

    def _on_split_into_files(self) -> None:
        """The reverse trip: one file per chapter (podcast episodes, track players)."""
        with wx.DirDialog(self, str(_("Choose a folder for the per-chapter files"))) as dlg:
            if dlg.ShowModal() != wx.ID_OK:  # GATE-42-OK: native folder picker
                return
            out_dir = Path(dlg.GetPath())
        book = self._book
        extension = ".mp3" if book.kind == "mp3" else ".m4a"

        def work(_progress: object = None) -> object:
            from quill.core.speech.audio_edit import split_into_files

            return split_into_files(book.path, book.chapters, out_dir, extension=extension)

        self._run_save(
            str(_("Splitting into chapter files")),
            work,
            str(
                _("Wrote {count} chapter file(s) to {folder}").format(
                    count=len(book.chapters), folder=out_dir.name
                )
            ),
        )

    def _on_publish(self) -> None:
        if self._on_publish_cb is None:
            self._error(str(_("Publishing is not available here.")))
            return
        if self._dirty:
            self._error(str(_("Save your chapter edits first, then publish.")))
            return
        self._collect_tags()
        self._on_publish_cb(self._book)

    # -- analysis: silence auto-chapter, ACX check ---------------------------

    def _on_propose_from_silences(self) -> None:
        """Run ffmpeg silencedetect on the background pool; the proposal lands in the list."""
        from quill.core.speech.silence import detect_silence_chapters

        with SilenceParamsDialog(self) as dlg:
            if dlg.ShowModal() != wx.ID_OK:  # GATE-42-OK: native modal
                return
            noise_db, min_silence_s = dlg.values()
        if not self._book.path.is_file():
            self._error(str(_("The book file is missing on disk.")))
            return
        path = self._book.path

        def work(_progress: object = None) -> object:
            return detect_silence_chapters(
                path,
                noise_db=noise_db,
                min_silence_s=min_silence_s,
                min_chapter_ms=5000,
                title_prefix=str(_("Chapter")),
            )

        def on_success(result: object) -> None:
            from quill.core.speech.chapters import Chapter

            proposed = result
            if not isinstance(proposed, list) or not proposed:
                self._announce(str(_("No silences were found; no changes made.")))
                return
            chapters = [
                Chapter(index=i, title=c.title, start_ms=c.start_ms, end_ms=c.end_ms)
                for i, c in enumerate(proposed)
            ]
            self._apply(
                chapters,
                select=0,
                spoken=str(
                    _(
                        "Proposed {count} chapters from silences — review the list, "
                        "rename or restore as needed."
                    ).format(count=len(chapters))
                ),
            )

        if self._run_background is not None:
            self._run_background(str(_("Proposing chapters from silences")), work, on_success)
            return
        try:
            on_success(work())
        except Exception as exc:  # noqa: BLE001 - surfaced, not raised through wx
            self._error(str(exc))

    def _on_propose_ai_titles(self) -> None:
        """Transcribe each chapter's opening locally, ask the AI for titles."""
        if self._ask_ai is None:
            self._error(
                str(
                    _(
                        "AI title proposals need a configured AI provider"
                        " (and are unavailable in Safe Mode). Set one up in"
                        " AI > AI Hub first."
                    )
                )
            )
            return
        if not self._book.path.is_file():
            self._error(str(_("The book file is missing on disk.")))
            return
        answer = show_message_box(
            str(
                _(
                    "QUILL will transcribe the first minute of each of the {count}"
                    " chapters with the local speech model (the audio never leaves"
                    " this computer), then send only that transcribed text to your"
                    " configured AI to suggest a short title per chapter. The"
                    " proposals land in the list for review — Restore original"
                    " undoes them. Continue?"
                ).format(count=len(self._book.chapters))
            ),
            str(_("Propose AI titles")),
            wx.YES_NO | wx.ICON_QUESTION,
            self,
        )
        if answer != wx.YES:
            return
        book = self._book
        ask = self._ask_ai

        def work(_progress: object = None) -> object:
            import tempfile

            from quill.core.speech.chapter_titles import propose_chapter_titles

            work_dir = Path(tempfile.mkdtemp(prefix="quill_titles_"))
            try:
                return propose_chapter_titles(book.path, book.chapters, ask, work_dir)
            finally:
                import shutil

                shutil.rmtree(work_dir, ignore_errors=True)

        def on_success(result: object) -> None:
            if not isinstance(result, list) or len(result) != len(self._book.chapters):
                self._announce(str(_("No titles were proposed; no changes made.")))
                return
            changed = 0
            chapters = []
            for chapter, proposal in zip(self._book.chapters, result, strict=True):
                title = str(proposal).strip() or chapter.title
                if title != chapter.title:
                    changed += 1
                chapters.append(
                    Chapter(
                        index=chapter.index,
                        title=title,
                        start_ms=chapter.start_ms,
                        end_ms=chapter.end_ms,
                        url=chapter.url,
                        image=chapter.image,
                    )
                )
            if not changed:
                self._announce(str(_("The AI proposed no different titles; no changes made.")))
                return
            self._apply(
                chapters,
                select=0,
                spoken=str(
                    _(
                        "Proposed {count} new title(s) — review the list;"
                        " Restore original undoes them."
                    ).format(count=changed)
                ),
            )

        self._announce(str(_("Transcribing chapter openings and asking the AI...")))
        if self._run_background is not None:
            self._run_background(str(_("Proposing AI chapter titles")), work, on_success)
            return
        try:
            on_success(work())
        except Exception as exc:  # noqa: BLE001 - surfaced, not raised through wx
            self._error(str(exc))

    def _on_check_acx(self) -> None:
        """Measure the book with loudnorm analysis and announce + show the verdict."""
        from quill.core.speech.loudness import AcxCheck, acx_check_file

        if not self._book.path.is_file():
            self._error(str(_("The book file is missing on disk.")))
            return
        path = self._book.path

        def work(_progress: object = None) -> object:
            return acx_check_file(path)

        def on_success(result: object) -> None:
            if result is None:
                self._announce(
                    str(_("Could not measure the book against ACX; check ffmpeg is installed."))
                )
                AcxResultDialog(self, check=None).ShowModal()
                return
            assert isinstance(result, AcxCheck)
            self._announce(
                str(
                    _("ACX verdict: {verdict}.").format(
                        verdict=_("passes") if result.ok else _("fails")
                    )
                )
            )
            AcxResultDialog(self, check=result).ShowModal()

        if self._run_background is not None:
            self._run_background(str(_("Checking against ACX")), work, on_success)
            return
        try:
            on_success(work())
        except Exception as exc:  # noqa: BLE001 - surfaced, not raised through wx
            self._error(str(exc))

    # -- lifecycle --------------------------------------------------------------------

    def _on_close(self, evt: wx.CloseEvent) -> None:
        from quill.core.paths import app_data_dir
        from quill.core.speech.listening_positions import save_position_ms

        position = self.player.playhead_ms()
        if position > 0:
            save_position_ms(app_data_dir(), self._book.path, position)
        self.player.shutdown()
        evt.Skip()


class SilenceParamsDialog(wx.Dialog):
    """Modal that asks for the two ffmpeg silencedetect knobs.

    Returns ``(noise_db, min_silence_s)`` on OK. The defaults match
    :func:`quill.core.speech.silence.detect_silence_chapters` so a brand-new
    user gets the same result the core ships; lowering noise_db makes the
    scan more sensitive, raising min_silence_s only counts real pauses.
    """

    def __init__(self, parent: wx.Window) -> None:
        super().__init__(
            parent,
            title=str(_("Propose chapters from silences")),
            style=wx.DEFAULT_DIALOG_STYLE,
            name="audio_studio.workbench_silence_params",
        )
        from quill.ui.audio_studio.pages_base import set_accessible_name

        root = wx.BoxSizer(wx.VERTICAL)
        intro = wx.StaticText(
            self,
            label=str(
                _(
                    "ffmpeg will scan the recording for silences and propose chapter "
                    "boundaries at the silence midpoints. The proposal lands in the "
                    "Workbench list for review; nothing is applied blind."
                )
            ),
        )
        intro.Wrap(420)
        root.Add(intro, 0, wx.ALL, 12)
        grid = wx.FlexGridSizer(cols=2, vgap=6, hgap=8)
        grid.Add(
            wx.StaticText(self, label=str(_("Noise threshold (dB):"))),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._noise = wx.SpinCtrlDouble(self, min=-60.0, max=-10.0, inc=1.0, initial=-30.0)
        set_accessible_name(self._noise, str(_("Noise threshold (dB)")))
        grid.Add(self._noise, 0)
        grid.Add(
            wx.StaticText(self, label=str(_("Minimum silence (seconds):"))),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._min_silence = wx.SpinCtrlDouble(self, min=0.1, max=5.0, inc=0.1, initial=0.8)
        set_accessible_name(self._min_silence, str(_("Minimum silence (seconds)")))
        grid.Add(self._min_silence, 0)
        root.Add(grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)
        buttons = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 12)
        self.SetSizer(root)
        self.Fit()
        self.CentreOnParent()
        apply_modal_ids(self, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        self._noise.SetFocus()

    def values(self) -> tuple[float, float]:
        return float(self._noise.GetValue()), float(self._min_silence.GetValue())


class AcxResultDialog(wx.Dialog):
    """Read-only modal that shows the ACX check verdict and any recommendations.

    The verdict is announced when the measurement finishes (the caller fires
    that announce), so the user can dismiss the dialog with Escape and the
    message still reaches them. The dialog exists so the recommendations are
    in front of them, not just spoken once.
    """

    def __init__(self, parent: wx.Window, *, check: object | None) -> None:
        super().__init__(
            parent,
            title=str(_("ACX check")),
            style=wx.DEFAULT_DIALOG_STYLE,
            name="audio_studio.workbench_acx_result",
        )
        from quill.core.speech.loudness import AcxCheck

        root = wx.BoxSizer(wx.VERTICAL)
        if check is None:
            text = wx.StaticText(
                self,
                label=str(
                    _(
                        "The ACX check could not run. Make sure ffmpeg is installed "
                        "and the book file is still on disk."
                    )
                ),
            )
        else:
            assert isinstance(check, AcxCheck)
            verdict = _("passes") if check.ok else _("fails")
            lines: list[str] = [
                _("ACX verdict: {verdict}.").format(verdict=verdict),
                "",
                _(
                    "Integrated loudness: {lufs:.1f} LUFS (target {target} plus or minus {rng})"
                ).format(lufs=check.integrated_lufs, target=-20.0, rng=3.0),
                _("True peak: {peak:.1f} dBFS (max {max})").format(
                    peak=check.true_peak_db, max=-3.0
                ),
                _("Noise floor: {noise:.1f} dBFS (max {max})").format(
                    noise=check.noise_floor_db, max=-60.0
                ),
            ]
            recs = check.recommendations()
            if recs:
                lines.append("")
                lines.append(_("What to fix:"))
                lines.extend(f"- {r}" for r in recs)
            text = wx.StaticText(self, label="\n".join(lines))
        text.Wrap(480)
        root.Add(text, 1, wx.EXPAND | wx.ALL, 12)
        buttons = self.CreateButtonSizer(wx.OK)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 12)
        self.SetSizer(root)
        self.Fit()
        self.CentreOnParent()
        apply_modal_ids(self, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)


def open_book_in_workbench(frame: object, path: Path) -> None:
    """Read *path* and open the Workbench on it (the journey-C entry point)."""
    from quill.core.speech.book_file import BookReadError, read_book

    # Remember this book so the second time the user opens the edit
    # journey, the file is one Tab away. The write is best-effort.
    try:
        from quill.core.recent import add_recent_audiobook_file

        add_recent_audiobook_file(path)
    except Exception:  # noqa: BLE001 - MRU write is best-effort
        pass

    try:
        book = read_book(path)
    except (BookReadError, Exception) as exc:  # noqa: BLE001 - speak, don't crash
        _log.exception("Could not open book")
        frame._show_message_box(  # type: ignore[attr-defined]
            str(_("Could not open that audiobook: {error}").format(error=exc)),
            str(_("Chapter Workbench")),
        )
        return

    def on_publish(current: BookFile) -> None:
        from quill.ui.audio_studio.publish_dialog import open_publish_dialog

        open_publish_dialog(frame, current)

    # AI title proposals ride the frame's assistant; absent in Safe Mode (the
    # same gate that hides every other AI surface).
    ask_ai: Callable[[str], str] | None = None
    if not bool(getattr(frame, "_safe_mode", False)) and hasattr(frame, "_get_assistant"):

        def _ask(prompt: str) -> str:
            return str(frame._get_assistant().ask(prompt))  # type: ignore[attr-defined]

        ask_ai = _ask

    dlg = ChapterWorkbenchDialog(
        frame.frame,  # type: ignore[attr-defined]
        book,
        announce=getattr(frame, "_announce", None),
        run_background=getattr(frame, "_run_background_task", None),
        on_publish=on_publish,
        ask_ai=ask_ai,
    )
    try:
        frame._show_modal_dialog(dlg, str(_("Chapter Workbench")))  # type: ignore[attr-defined]
    finally:
        dlg.Destroy()
