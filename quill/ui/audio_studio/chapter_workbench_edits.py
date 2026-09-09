"""The Chapter Workbench's chapter-editing handlers, as a mixin.

Extracted from :mod:`quill.ui.audio_studio.chapter_workbench` so that module
stays inside its GATE-11 size budget while the Workbench gains add, delete,
edit, preview and nudge. The mixin holds handlers only -- the Workbench still
builds the buttons and owns the widgets -- and every chapter computation lives
in the wx-free :mod:`quill.core.speech.chapters`, which delegates in turn to
the model shared byte-for-byte with podHarvest.

The nudge is the reason most of this exists. Setting a boundary by ear used to
mean play, stop, press *Set start to playhead*, listen again; now it is a held
key. Two consequences shape the code:

* **Speech has to keep up without drowning you.** A nudge speaks the bare new
  time and nothing else, because a sentence repeated at key-repeat speed is
  noise. The full sentence follows once the run goes quiet. Running a marker
  into its neighbour says so once per run, not once per press.
* **Clamping beats raising.** :func:`nudge_chapter_start` stops at the wall
  and reports how far it actually moved, so holding the key down does the
  obvious thing instead of throwing on the twentieth press.

The host must provide ``_book``, ``_selected_index()``, ``_apply()``,
``_error()``, ``_announce()``, ``player`` and ``settings_nudge_ms``.
"""

from __future__ import annotations

from pathlib import Path

import wx

from quill.core.i18n import _
from quill.core.speech.audio_tags import format_time_precise, parse_time
from quill.core.speech.book_file import BookFile, save_mp3_book
from quill.core.speech.chapters import (
    NUDGE_STEPS_MS,
    ChapterEditError,
    add_chapter,
    delete_chapter,
    nudge_chapter_start,
    set_chapter_bounds,
)
from quill.ui.audio_studio.chapter_workbench_dialogs import ChapterDetailsDialog
from quill.ui.audio_studio.pages_base import set_accessible_name
from quill.ui.audio_studio.tag_editor import TagEditorDialog

#: How long a run of nudges must go quiet before the full sentence is spoken.
_NUDGE_SETTLE_MS = 600
#: The window "Hear boundary" plays: this much before the marker, and after.
_BOUNDARY_LEAD_MS = 3_000
_BOUNDARY_TAIL_MS = 2_000


class ChapterEditsMixin:
    """Add, delete, edit, preview and nudge handlers for the Chapter Workbench."""

    #: When set, playback stops as soon as the playhead passes this point.
    _stop_at_ms: int | None = None
    #: True while a run of nudges is at the wall, so it is announced once.
    _wall_announced: bool = False
    #: The pending "say the whole chapter" call, cancelled by the next nudge.
    _settle_timer: object | None = None

    # -- add / delete / edit ---------------------------------------------------

    def _on_add_chapter(self) -> None:
        """Insert a marker at the playhead (or a typed time) and name it."""
        default = format_time_precise(self.player.playhead_ms())
        with wx.TextEntryDialog(
            self,
            str(
                _(
                    "Where should the new chapter start? Times are "
                    "hours:minutes:seconds.milliseconds; the playhead's "
                    "position is filled in."
                )
            ),
            str(_("Add chapter")),
            default,
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:  # GATE-42-OK: simple text prompt
                return
            at_ms = parse_time(dlg.GetValue())
        if at_ms is None:
            self._error(str(_("That is not a time. Use hours:minutes:seconds.milliseconds.")))
            return
        with wx.TextEntryDialog(
            self,
            str(_("What is the new chapter called?")),
            str(_("Add chapter")),
            str(_("New chapter")),
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:  # GATE-42-OK: simple text prompt
                return
            title = dlg.GetValue().strip() or str(_("New chapter"))
        try:
            chapters = add_chapter(self._book.chapters, at_ms, title=title)
        except ChapterEditError as exc:
            self._error(str(exc))
            return
        new_index = next(
            (i for i, c in enumerate(chapters) if c.title == title and c.start_ms <= at_ms),
            len(chapters) - 1,
        )
        self._apply(
            chapters,
            select=new_index,
            spoken=str(_("Added {title} at {at}")).format(
                title=title, at=format_time_precise(at_ms)
            ),
        )

    def _on_delete_chapter(self) -> None:
        """Remove the selected chapter's marker. The audio is untouched."""
        index = self._selected_index()
        if index < 0:
            self._error(str(_("No chapter is selected.")))
            return
        title = self._book.chapters[index].title
        try:
            chapters = delete_chapter(self._book.chapters, index)
        except ChapterEditError as exc:
            self._error(str(exc))
            return
        self._apply(
            chapters,
            select=max(0, index - 1),
            spoken=str(_("Deleted {title}. The audio is unchanged.")).format(title=title),
        )

    def _on_edit_chapter(self) -> None:
        """Type this chapter's title, exact start and end, and its extras."""
        index = self._selected_index()
        if index < 0:
            self._error(str(_("No chapter is selected.")))
            return
        chapters = self._book.chapters
        chapter = chapters[index]
        lower = chapters[index - 1].start_ms if index > 0 else chapter.start_ms
        upper = chapters[index + 1].end_ms if index + 1 < len(chapters) else chapter.end_ms
        dlg = ChapterDetailsDialog(self, chapter, lower_ms=lower, upper_ms=upper)
        try:
            if dlg.ShowModal() != wx.ID_OK:  # GATE-42-OK: shown by the Workbench
                return
            title, start_ms, end_ms, url, image = dlg.values()
        finally:
            dlg.Destroy()
        if start_ms is None or end_ms is None:
            self._error(
                str(_("Start and end must be times, as hours:minutes:seconds.milliseconds."))
            )
            return
        try:
            updated = set_chapter_bounds(chapters, index, start_ms, end_ms)
        except ChapterEditError as exc:
            self._error(str(exc))
            return
        updated[index].title = title or chapter.title
        updated[index].url = url
        updated[index].image = image
        self._apply(
            updated,
            select=index,
            spoken=str(_("{title} now runs {start} to {end}")).format(
                title=updated[index].title,
                start=format_time_precise(updated[index].start_ms),
                end=format_time_precise(updated[index].end_ms),
            ),
        )

    # -- listening -------------------------------------------------------------

    def _on_preview_chapter(self) -> None:
        """Play the selected chapter from its start and stop at its end."""
        index = self._selected_index()
        if index < 0:
            self._error(str(_("No chapter is selected.")))
            return
        chapter = self._book.chapters[index]
        self.player.seek_to(chapter.start_ms)
        self._stop_at_ms = chapter.end_ms
        self.player.play()

    def _on_hear_boundary(self) -> None:
        """Play a few seconds either side of the selected chapter's start.

        The quickest way to judge a marker: you hear the tail of what came
        before, the boundary, and the head of what follows, then it stops.
        """
        index = self._selected_index()
        if index < 0:
            self._error(str(_("No chapter is selected.")))
            return
        start = self._book.chapters[index].start_ms
        self.player.seek_to(max(0, start - _BOUNDARY_LEAD_MS))
        self._stop_at_ms = min(self._book.total_ms, start + _BOUNDARY_TAIL_MS)
        self.player.play()

    def _check_preview_stop(self) -> bool:
        """Stop playback if an armed preview has run past its end. True if stopped.

        Driven by the player's existing tick rather than a timer of its own,
        which is why previewing costs nothing when nothing is armed.
        """
        if self._stop_at_ms is None:
            return False
        if self.player.playhead_ms() < self._stop_at_ms:
            return False
        self._stop_at_ms = None
        self.player.pause()
        return True

    # -- nudging ---------------------------------------------------------------

    def _hear_after_nudge(self) -> bool:
        """Whether the "hear the boundary after each nudge" box is ticked.

        Overridden by the Workbench, which owns the checkbox. The default of
        False keeps the mixin usable without one.
        """
        return False

    def _on_nudge(self, direction: int, *, multiplier: int = 1) -> None:
        """Move the selected chapter's start by one step (or ten) either way.

        Announces the bare new time, not a sentence: this runs at key-repeat
        speed, and a sentence ten times a second is unusable. The full
        sentence follows from :meth:`_schedule_nudge_settle` once the run
        stops.
        """
        index = self._selected_index()
        if index < 0:
            self._error(str(_("No chapter is selected.")))
            return
        step = max(10, int(self.settings_nudge_ms)) * max(1, multiplier)
        try:
            chapters, applied = nudge_chapter_start(
                self._book.chapters, index, step * (1 if direction >= 0 else -1)
            )
        except ChapterEditError as exc:
            self._error(str(exc))
            return
        if applied == 0:
            if not self._wall_announced:
                self._wall_announced = True
                self._announce(str(_("Cannot move further.")))
            return
        self._wall_announced = False
        self._apply(
            chapters,
            select=index,
            spoken=format_time_precise(chapters[index].start_ms),
        )
        self._schedule_nudge_settle(index)
        if self._hear_after_nudge():
            self._on_hear_boundary()

    def _schedule_nudge_settle(self, index: int) -> None:
        """After the run goes quiet, speak the chapter in full, once."""

        def settle() -> None:
            chapters = self._book.chapters
            if not 0 <= index < len(chapters):
                return
            chapter = chapters[index]
            self._announce(
                str(_("{title} starts {start}, runs {dur}")).format(
                    title=chapter.title,
                    start=format_time_precise(chapter.start_ms),
                    dur=format_time_precise(chapter.duration_ms),
                )
            )

        timer = self._settle_timer
        if timer is not None and hasattr(timer, "Stop"):
            timer.Stop()
        try:
            self._settle_timer = wx.CallLater(_NUDGE_SETTLE_MS, settle)
        except Exception:  # noqa: BLE001 - no wx app (tests): settle immediately
            self._settle_timer = None
            settle()

    def _nudge_key_handler(self, event: wx.KeyEvent) -> None:
        """Alt+Left/Right nudge one step; add Shift for ten. Anything else passes.

        The Workbench has no menu bar to advertise these, so they are named in
        the buttons' help text, in the chapter list's own help, and in the
        window's F1 purpose.
        """
        code = event.GetKeyCode()
        if event.AltDown() and code in (wx.WXK_LEFT, wx.WXK_RIGHT):
            self._on_nudge(
                -1 if code == wx.WXK_LEFT else 1,
                multiplier=10 if event.ShiftDown() else 1,
            )
            return
        event.Skip()

    def _sync_save_button(self) -> None:
        """Save is in place for an MP3, and for an M4B when only tags changed.

        M4B chapter atoms cannot be rewritten without a re-mux, so a chapter
        edit still needs Save As -- but a tag-only edit is a mutagen write of
        the atoms and finishes instantly, which is worth offering rather than
        making somebody produce a second copy of a book to fix a typo.
        """
        if self._book.kind == "mp3":
            self._save_btn.Enable(True)
            self._save_btn.SetToolTip(_("Writes the edits into this MP3; the audio is untouched."))
            return
        can_save = not self._chapters_dirty
        self._save_btn.Enable(can_save)
        self._save_btn.SetToolTip(
            _("Tags save into this M4B in place; a chapter change needs Save As.")
            if can_save
            else _("An M4B with edited chapters is saved as a new file; use Save As.")
        )

    def _on_step_changed(self) -> None:
        """Remember the nudge step, for this session and the next."""
        selection = self._step_choice.GetSelection()
        if not 0 <= selection < len(NUDGE_STEPS_MS):
            return
        self.settings_nudge_ms = NUDGE_STEPS_MS[selection]
        try:
            from quill.core.settings import load_settings, save_settings

            settings = load_settings()
            settings.audio_studio_chapter_nudge_ms = self.settings_nudge_ms
            save_settings(settings)
        except Exception:  # noqa: BLE001 - failing to persist must not block editing
            pass

    def _hear_after_nudge(self) -> bool:
        return bool(self._hear_after.GetValue())

    def _on_all_tags(self) -> None:
        """Open the full Tag Editor, seeded from the file and the quick fields.

        The five fields below the player and the twenty-six in the editor are
        two views of one file, so opening the editor overlays whatever is
        currently typed here, and pressing OK writes the shared seven back --
        neither view is ever showing something the other has forgotten.
        """
        from quill.core.speech.audio_tags import (
            AudioTags,
            merge_audio_metadata,
            read_tags,
            to_audio_metadata,
        )

        self._collect_tags()
        base = self._full_tags
        if base is None:
            try:
                base = read_tags(self._book.path)
            except Exception as exc:  # noqa: BLE001 - an untagged file still opens
                self._announce(
                    str(_("Could not read the existing tags: {error}")).format(error=exc)
                )
                base = AudioTags()
        seeded = merge_audio_metadata(base, self._book.tags)
        dlg = TagEditorDialog(
            self,
            seeded,
            filename=self._book.path.name,
            announce=self._announce_fn,
        )
        try:
            if dlg.ShowModal() != wx.ID_OK:  # GATE-42-OK: shown by the Workbench
                return
            self._full_tags = dlg.result()
        finally:
            dlg.Destroy()
        self._book.tags = to_audio_metadata(self._full_tags)
        self._tag_album.SetValue(self._book.tags.album)
        self._tag_artist.SetValue(self._book.tags.artist)
        self._tag_narrator.SetValue(self._book.tags.album_artist)
        self._tag_genre.SetValue(self._book.tags.genre)
        self._tag_year.SetValue(self._book.tags.year)
        self._tags_dirty = True
        self._sync_save_button()
        self._announce(str(_("Tag edits ready. Save to write them to the file.")))

    @staticmethod
    def _write_all_tags(path: Path, tags: object, book: BookFile) -> Path:
        """Write the full tag set to *path*, overlaid with the quick fields.

        Runs after the chapter write, and both are load-modify-save, so
        neither drops the other's frames.
        """
        from quill.core.speech.audio_tags import (
            merge_audio_metadata,
            read_tags,
            write_tags,
        )

        full = tags if tags is not None else read_tags(path)
        write_tags(path, merge_audio_metadata(full, book.tags))
        return path

    @classmethod
    def _save_mp3_with_tags(cls, book: BookFile, tags: object) -> Path:
        """Chapters and the core seven first, then the full tag set over them."""
        save_mp3_book(book)
        if tags is not None:
            cls._write_all_tags(book.path, tags, book)
        return book.path


def build_chapter_edit_rows(dialog: wx.Window, root: wx.Sizer) -> None:
    """Build the Workbench's add/delete/edit/preview row and its nudge row.

    A module function rather than a method so the Workbench keeps only the
    one call that puts them on screen: ninety lines of button construction
    belongs with the handlers those buttons fire, which is here.
    """

    edit_row = wx.BoxSizer(wx.HORIZONTAL)
    for label, handler, help_text in (
        (
            _("A&dd chapter..."),
            dialog._on_add_chapter,
            "Puts a new chapter marker at the playhead, or at a time you "
            "type, and asks what to call it. The audio is not cut.",
        ),
        (
            _("De&lete chapter"),
            dialog._on_delete_chapter,
            "Removes the highlighted chapter's marker. The audio is "
            "untouched -- it simply joins the neighbouring chapter.",
        ),
        (
            _("Ed&it chapter..."),
            dialog._on_edit_chapter,
            "Opens a window to type this chapter's title and its exact "
            "start and end, plus the optional link and image a "
            "Podcasting 2.0 player can show.",
        ),
        (
            _("Pre&view chapter"),
            dialog._on_preview_chapter,
            "Plays the highlighted chapter from its start and stops at "
            "its end, instead of running on into the next one.",
        ),
    ):
        btn = wx.Button(dialog, label=label)
        btn.SetHelpText(help_text)
        btn.Bind(wx.EVT_BUTTON, lambda _e, h=handler: h())
        edit_row.Add(btn, 0, wx.RIGHT, 6)
    root.Add(edit_row, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)

    # Nudging is how a boundary actually gets set: you listen, you move it
    # a little, you listen again. The step, the audition and the
    # audition-automatically switch all live together for that reason.
    nudge_row = wx.BoxSizer(wx.HORIZONTAL)
    back_btn = wx.Button(dialog, label=_("N&udge back"))
    back_btn.SetHelpText(
        "Moves the highlighted chapter's start earlier by one step. Alt "
        "with Left arrow does the same from the chapter list, and adding "
        "Shift moves ten steps at once."
    )
    back_btn.Bind(wx.EVT_BUTTON, lambda _e: dialog._on_nudge(-1))
    nudge_row.Add(back_btn, 0, wx.RIGHT, 6)

    fwd_btn = wx.Button(dialog, label=_("Nudge f&orward"))
    fwd_btn.SetHelpText(
        "Moves the highlighted chapter's start later by one step. Alt "
        "with Right arrow does the same from the chapter list, and adding "
        "Shift moves ten steps at once."
    )
    fwd_btn.Bind(wx.EVT_BUTTON, lambda _e: dialog._on_nudge(1))
    nudge_row.Add(fwd_btn, 0, wx.RIGHT, 6)

    # Label before control: screen readers pair them by creation order.
    nudge_row.Add(
        wx.StaticText(dialog, label=_("Ste&p:")),
        0,
        wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
        4,
    )
    dialog._step_choice = wx.Choice(
        dialog, choices=[format_time_precise(ms) for ms in NUDGE_STEPS_MS]
    )
    dialog._step_choice.SetHelpText(
        "How far one nudge moves a marker. Half a second to start with; "
        "the step you pick is remembered for next time."
    )
    set_accessible_name(dialog._step_choice, str(_("Nudge step")))
    dialog._step_choice.SetSelection(
        NUDGE_STEPS_MS.index(dialog.settings_nudge_ms)
        if dialog.settings_nudge_ms in NUDGE_STEPS_MS
        else NUDGE_STEPS_MS.index(500)
    )
    dialog._step_choice.Bind(wx.EVT_CHOICE, lambda _e: dialog._on_step_changed())
    nudge_row.Add(dialog._step_choice, 0, wx.RIGHT, 12)

    hear_btn = wx.Button(dialog, label=_("Hear boundar&y"))
    hear_btn.SetHelpText(
        "Plays three seconds before the highlighted chapter's start and "
        "two seconds after it, then stops -- the quickest way to judge a "
        "marker by ear."
    )
    hear_btn.Bind(wx.EVT_BUTTON, lambda _e: dialog._on_hear_boundary())
    nudge_row.Add(hear_btn, 0, wx.RIGHT, 6)

    dialog._hear_after = wx.CheckBox(dialog, label=_("Hear after each nud&ge"))
    dialog._hear_after.SetHelpText(
        "Plays the boundary automatically after every nudge. Off by "
        "default, because audio on every keypress is something to ask "
        "for rather than discover."
    )
    set_accessible_name(dialog._hear_after, str(_("Hear after each nudge")))
    nudge_row.Add(dialog._hear_after, 0, wx.ALIGN_CENTER_VERTICAL)
    root.Add(nudge_row, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
