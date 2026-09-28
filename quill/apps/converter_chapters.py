"""Quill Converter's chapter commands: Join, Split by Chapters, the Workbench.

Split out of :mod:`quill.apps.converter_actions` (GATE-11) when chapters
became one of the Converter's headline features on 2026-09-27. The engine is
:mod:`quill.core.audio.chapter_plan` (where chapters come from and where they
land) and :mod:`quill.core.audio.assemble` (Join and the split plan); the
editor is the Audio Studio's Chapter Workbench, reused rather than rebuilt.

Mixed into :class:`~quill.apps.converter.QuillConverterFrame` alongside
:class:`~quill.apps.converter_actions.ConverterActionsMixin`, whose helpers
(``current_spec``, ``_run_jobs``, ``_begin_work``, ``_finish_simple``,
``_preview_source``, ``_ffmpeg``) these commands use.
"""

from __future__ import annotations

import threading
from pathlib import Path

import wx

from quill.core.audio.convert import CancelToken, ConversionJob
from quill.core.audio.formats import format_label

_TITLE = "Quill Converter"


class ConverterChaptersMixin:
    """Join into One File, Split by Chapters, and the Chapter Workbench."""

    # -- join and split -------------------------------------------------------

    def join_into_one(self) -> None:
        """Join the queue into one file, a chapter per source where it can."""
        if self._busy or not self._entries:
            self._announce(
                "Add files to join first." if not self._entries else "A job is already running."
            )
            return
        ffmpeg = self._ffmpeg()
        if ffmpeg is None:
            return
        spec = self.current_spec()
        if spec.is_video():
            self._show_message_box(
                "Join makes one sound file. Choose an audio format first.", _TITLE
            )
            return
        from quill.core.audio.assemble import CHAPTER_FORMATS, join_inputs, run_join

        sources = join_inputs(self._entries, recurse=self._recurse.GetValue())
        if len(sources) < 2:
            self._show_message_box("Join needs at least two files in the queue.", _TITLE)
            return
        dest = self._destination()
        name = sources[0].parent.name or "Joined"
        with wx.FileDialog(
            self.frame,
            "Save the joined file as",
            defaultDir=str(dest),
            defaultFile=name + spec.output_extension(),
            wildcard=f"{format_label(spec.fmt)}|*{spec.output_extension()}",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as picker:
            if picker.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return
            out_path = Path(picker.GetPath())
        cancel = CancelToken()
        self._remember()
        chapters = " with a chapter for each" if spec.fmt in CHAPTER_FORMATS else ""
        self._begin_work(f"Joining {len(sources)} files{chapters}", cancel)

        def progress(text: str, current: int, total: int) -> None:
            wx.CallAfter(self._note_progress, text, current, total)

        def worker() -> None:
            try:
                run_join(
                    ffmpeg,
                    sources,
                    spec,
                    out_path,
                    progress=progress,
                    cancelled=cancel.is_cancelled,
                )
                message = f"Joined {len(sources)} files into {out_path.name}{chapters}."
            except Exception as error:  # noqa: BLE001 - said out loud on the UI thread
                message = (
                    "Join stopped. Nothing was saved."
                    if cancel.is_cancelled()
                    else f"Join failed. {error}"
                )
            wx.CallAfter(self._finish_simple, message, out_path.parent)

        threading.Thread(target=worker, daemon=True, name="converter-join").start()

    def split_by_chapters(self) -> None:
        """One file per chapter, for every queued file that has chapters."""
        if self._busy or not self._entries:
            self._announce(
                "Add a file with chapters first."
                if not self._entries
                else "A job is already running."
            )
            return
        ffmpeg = self._ffmpeg()
        if ffmpeg is None:
            return
        from quill.core.audio.assemble import join_inputs, plan_chapter_split
        from quill.core.audio.media_probe import probe

        spec = self.current_spec()
        dest = self._destination()
        jobs: list[ConversionJob] = []
        without: list[str] = []
        from quill.core.audio.chapter_plan import resolve_chapters
        from quill.core.audio.media_probe import Chapter as Span
        from quill.core.speech.audio_tags_core import Chapter as Mark

        how = self._chosen_chapters()
        for source in join_inputs(self._entries, recurse=self._recurse.GetValue()):
            info = probe(source)
            own = [
                Mark(i, c.title, int(c.start_s * 1000), int(c.end_s * 1000))
                for i, c in enumerate(info.chapters)
            ]
            marks, _note = resolve_chapters(
                source,
                "keep" if how == "none" else how,
                total_ms=int(info.duration_s * 1000),
                own=own,
            )
            spans = [Span(m.title, m.start_ms / 1000, m.end_ms / 1000) for m in (marks or own)]
            if len(spans) >= 2:
                jobs += plan_chapter_split(source, spans, dest, spec)
            else:
                without.append(source.name)
        notes = (
            f"{len(without)} file(s) have no chapters: {', '.join(without[:3])}." if without else ""
        )
        if how == "none":
            # "Remove all chapters" is about what a converted copy keeps; a
            # split needs chapters to cut at, so it uses each file's own. Said
            # rather than silently reinterpreted.
            notes = (
                "Split used each file's own chapters; Remove all chapters applies "
                "to converting, not splitting. " + notes
            ).strip()
        if not jobs:
            self._show_message_box(
                "None of the queued files has chapters to split by. Choose where "
                "chapters come from in Chapters -- at the pauses, every few minutes, "
                "or a chapter list beside the file -- and Split again.",
                _TITLE,
            )
            return
        self._remember()
        self._run_jobs(ffmpeg, jobs, f"Splitting into {len(jobs)} chapter files", dest, notes=notes)

    def open_chapter_workbench(self) -> None:
        """Queue > Chapter Workbench (Ctrl+H): edit the highlighted file's chapters."""
        source = self._preview_source()
        if source is None:
            self._announce("Highlight an MP3, M4B or M4A in the queue first.")
            return
        if source.suffix.lower() not in (".mp3", ".m4b", ".m4a", ".mp4"):
            self._show_message_box(
                f"The Chapter Workbench saves chapters into MP3, M4B and M4A files. "
                f"For {source.name}, choose where its chapters come from in Chapters "
                "-- a chapter list beside it (for example "
                f"{source.stem}.chapters.txt with lines like 0:00 Introduction), the "
                "pauses, or every few minutes -- or convert it to M4B or MP3 first "
                "and open that.",
                "Chapter Workbench",
            )
            return
        from quill.core.speech.book_file import BookReadError, read_book
        from quill.ui.audio_studio.chapter_workbench import ChapterWorkbenchDialog

        try:
            book = read_book(source)
        except (BookReadError, Exception) as error:  # noqa: BLE001 - said, not raised
            self._show_message_box(f"Could not open {source.name}: {error}", "Chapter Workbench")
            return
        dialog = ChapterWorkbenchDialog(
            self.frame, book, announce=self._announce, run_background=self._run_background_task
        )
        try:
            self._show_modal_dialog(dialog, "Chapter Workbench")
        finally:
            dialog.Destroy()
