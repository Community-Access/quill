"""Process with Auphonic's two option windows: tags and cover, and more options.

Both open from buttons in Process with Auphonic and change nothing until OK;
neither contacts anybody. Post-MVP
(``docs/planning/QUILL-Converter-Auphonic-Integration-PRD.md``, section 14).

**Tags, Cover and Chapter Marks** holds what a production carries besides
its sound: an artist and an album that replace the files' own, a JPEG or PNG
cover image uploaded with each production, and -- for a single production
only -- chapter marks typed one a line (``0:05:30 Interview``), starting from
the file's own.

**More Auphonic Options** holds Custom processing's values (used only when
Processing is set to Custom processing), a second output format, and captions
with a transcript made by Auphonic's speech recognition.

Access keys are unique within each window (GATE-14); OK and Cancel carry
none. Every control has its F1 sentence inline (GATE-CONVERTER-HELP).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

import wx

from quill.core.publish.auphonic import OUTPUT_FORMATS
from quill.core.publish.auphonic_options import (
    LOUDNESS_TARGETS,
    NOISE_AMOUNTS,
    NOISE_METHODS,
    PEAK_LIMITS,
    TRANSCRIPT_LANGUAGES,
    CustomProcessing,
    cover_problem,
    format_chapters,
    parse_chapters,
)
from quill.core.publish.auphonic_plan import AuphonicChoices
from quill.ui.accessible_names import set_accessible_name
from quill.ui.dialog_contract import apply_modal_ids

TAGS_TITLE = "Tags, Cover and Chapter Marks"
MORE_TITLE = "More Auphonic Options"
_NO_COVER = "No cover image"
_SECOND: tuple[tuple[str, str], ...] = (("", "No second format"),) + tuple(OUTPUT_FORMATS.items())


def _labelled(parent: wx.Window, root: wx.BoxSizer, label: str, control: wx.Window) -> None:
    root.Add(wx.StaticText(parent, label=label), 0, wx.LEFT | wx.TOP, 8)
    root.Add(control, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)


def _ok_cancel(dialog: wx.Dialog, root: wx.BoxSizer, ok_help: str) -> None:
    root.Add(dialog.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL), 0, wx.ALL | wx.EXPAND, 8)
    apply_modal_ids(
        dialog,
        affirmative_id=wx.ID_OK,
        affirmative_label="OK",
        cancel_id=wx.ID_CANCEL,
        cancel_label="Cancel",
    )
    for button_id, text in (
        (wx.ID_OK, ok_help),
        (wx.ID_CANCEL, "Closes without changing anything."),
    ):
        button = dialog.FindWindow(button_id)
        if button is not None:
            button.SetHelpText(text)


class AuphonicTagsDialog(wx.Dialog):
    """Artist, album, cover image and chapter marks. :meth:`values` reads them back."""

    def __init__(
        self,
        parent: Any,
        *,
        artist: str,
        album: str,
        cover: str,
        chapters: tuple[tuple[float, str], ...] | None,
        source_chapters: tuple[tuple[float, str], ...],
        single: bool,
        pick_cover: Callable[[wx.Window], str],
        refuse: Callable[[str], None],
    ) -> None:
        super().__init__(
            parent,
            title=TAGS_TITLE,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            name="converter.auphonic_tags",
        )
        self._pick_cover = pick_cover
        self._refuse = refuse
        self._cover_path = cover
        root = wx.BoxSizer(wx.VERTICAL)

        self._artist = wx.TextCtrl(self, value=artist)
        set_accessible_name(self._artist, "Artist")
        self._artist.SetHelpText(
            "The artist or author every production is tagged with. Leave it empty to "
            "keep each file's own artist tag."
        )
        _labelled(self, root, "&Artist:", self._artist)
        self._album = wx.TextCtrl(self, value=album)
        set_accessible_name(self._album, "Album")
        self._album.SetHelpText(
            "The album, show or book name every production is tagged with. Leave it "
            "empty to keep each file's own album tag."
        )
        _labelled(self, root, "A&lbum:", self._album)

        self._cover = wx.TextCtrl(self, value=cover or _NO_COVER, style=wx.TE_READONLY)
        set_accessible_name(self._cover, "Cover image")
        self._cover.SetHelpText(
            "The picture uploaded with each production as its cover art, or No cover "
            "image. Read-only; use Choose Cover Image to pick one."
        )
        _labelled(self, root, "Co&ver image:", self._cover)
        row = wx.BoxSizer(wx.HORIZONTAL)
        self._choose = wx.Button(self, label="&Choose Cover Image...")
        self._choose.SetHelpText(
            "Opens a file picker for a JPEG or PNG picture of up to 10 MB. It is "
            "uploaded to Auphonic with each production; the picture itself is not changed."
        )
        self._remove = wx.Button(self, label="&Remove Cover")
        self._remove.SetHelpText("Sends no cover image. The picture file is not touched.")
        row.Add(self._choose, 0, wx.RIGHT, 6)
        row.Add(self._remove, 0)
        root.Add(row, 0, wx.ALL, 8)

        self._use_chapters = wx.CheckBox(
            self, label="Send these chapter &marks instead of the file's own"
        )
        self._use_chapters.SetValue(single and chapters is not None)
        self._use_chapters.SetHelpText(
            "When checked, the production gets exactly the chapter marks below. When "
            "clear, it gets the file's own chapters, if it has any. Only one "
            "production at a time can have edited chapter marks."
            + ("" if single else " This submission makes several productions, so it is off.")
        )
        self._use_chapters.Enable(single)
        root.Add(self._use_chapters, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        start = chapters if chapters is not None else source_chapters
        self._chapters = wx.TextCtrl(
            self, value=format_chapters(start), style=wx.TE_MULTILINE, size=(460, 120)
        )
        set_accessible_name(self._chapters, "Chapter marks")
        self._chapters.SetHelpText(
            "One chapter a line: its start time, a space, and its title, such as "
            "0:00:00 Welcome and then 0:05:30 Interview. Times are hours, minutes "
            "and seconds, or minutes and seconds. It starts with the file's own chapters."
        )
        _labelled(self, root, "C&hapter marks, one a line:", self._chapters)
        _ok_cancel(self, root, "Keeps these tags, cover and chapter marks for this submission.")
        self.SetSizerAndFit(root)

        self._choose.Bind(wx.EVT_BUTTON, lambda _e: self.choose_cover())
        self._remove.Bind(wx.EVT_BUTTON, lambda _e: self.set_cover(""))
        self._use_chapters.Bind(wx.EVT_CHECKBOX, lambda _e: self._sync())
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
        self._sync()
        self._artist.SetFocus()

    def _sync(self) -> None:
        self._chapters.Enable(self._use_chapters.IsEnabled() and self._use_chapters.GetValue())
        self._remove.Enable(bool(self._cover_path))

    def choose_cover(self) -> None:
        chosen = self._pick_cover(self)
        if chosen:
            self.set_cover(chosen)

    def set_cover(self, path: str) -> None:
        reason = cover_problem(path)
        if reason:
            self._refuse(reason)
            return
        self._cover_path = path
        self._cover.SetValue(path or _NO_COVER)
        self._sync()
        if not path:
            self._choose.SetFocus()  # the Remove button just disabled itself

    def values(self) -> tuple[str, str, str, tuple[tuple[float, str], ...] | None]:
        """``(artist, album, cover, chapters)``; chapters ``None`` keeps the file's own."""
        chapters: tuple[tuple[float, str], ...] | None = None
        if self._use_chapters.IsEnabled() and self._use_chapters.GetValue():
            chapters, _problem = parse_chapters(self._chapters.GetValue())
        return (
            self._artist.GetValue().strip(),
            self._album.GetValue().strip(),
            self._cover_path,
            chapters,
        )

    def _on_ok(self, event: Any) -> None:
        if self._use_chapters.IsEnabled() and self._use_chapters.GetValue():
            _chapters, reason = parse_chapters(self._chapters.GetValue())
            if reason:
                self._refuse(reason)
                self._chapters.SetFocus()
                return
        event.Skip()


class AuphonicMoreDialog(wx.Dialog):
    """Custom processing, a second format and a transcript. :meth:`values` reads them."""

    def __init__(
        self,
        parent: Any,
        *,
        custom: CustomProcessing,
        second_format: str,
        transcript: bool,
        language: str,
    ) -> None:
        super().__init__(
            parent,
            title=MORE_TITLE,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            name="converter.auphonic_more",
        )
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(self, label="Custom processing, used when Processing is set to it:"),
            0,
            wx.ALL,
            8,
        )
        self._leveler = wx.CheckBox(self, label="&Even out the levels")
        self._leveler.SetValue(custom.leveler)
        self._leveler.SetHelpText(
            "Auphonic's leveler: quiet and loud speakers, and quiet and loud passages, "
            "come out at a similar level. Usually on for speech."
        )
        root.Add(self._leveler, 0, wx.LEFT | wx.RIGHT, 8)
        self._filtering = wx.CheckBox(self, label="&Filter the sound")
        self._filtering.SetValue(custom.filtering)
        self._filtering.SetHelpText(
            "Auphonic's filtering: takes out rumble and other sound below the voice, "
            "and evens out the tone. Usually on."
        )
        root.Add(self._filtering, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self._loudness = self._choice(
            root,
            "&Loudness target:",
            "Loudness target",
            LOUDNESS_TARGETS,
            custom.loudness,
            "How loud the result is overall. -16 LUFS suits most podcasts; the "
            "broadcast choices suit radio and television. Auphonic does the measuring.",
        )
        self._peak = self._choice(
            root,
            "&Peak limit:",
            "Peak limit",
            PEAK_LIMITS,
            custom.max_peak,
            "How loud the loudest moment may be. -1 dB is usual; a lower limit leaves "
            "room for MP3 and AAC encoding and for audiobook stores' rules.",
        )
        self._noise = self._choice(
            root,
            "&Noise reduction:",
            "Noise reduction",
            NOISE_AMOUNTS,
            custom.noise,
            "How much background noise to take out: off, Auphonic's own choice, or a "
            "fixed strength. Stronger reduction can also change the voice.",
        )
        self._method = self._choice(
            root,
            "Noise reduction &method:",
            "Noise reduction method",
            NOISE_METHODS,
            custom.noise_method,
            "Which kind of noise to take out. Keep only the speech removes music and "
            "every other sound as well, so use it for speech alone.",
        )
        self._second = self._choice(
            root,
            "Also &save as:",
            "Also save as",
            _SECOND,
            second_format,
            "A second format for every result, beside the output format chosen in "
            "Process with Auphonic, such as FLAC to keep and MP3 to share. It needs an "
            "output format chosen there too.",
        )
        self._transcript = wx.CheckBox(self, label="Make captions and a &transcript")
        self._transcript.SetValue(transcript)
        self._transcript.SetHelpText(
            "Auphonic's speech recognition writes what is said: captions (an SRT file) "
            "and a plain-text transcript, saved beside the sound. It uses more of your "
            "Auphonic credits, and it needs an output format chosen."
        )
        root.Add(self._transcript, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self._language = self._choice(
            root,
            "Transcript lan&guage:",
            "Transcript language",
            TRANSCRIPT_LANGUAGES,
            language,
            "The language spoken in the recording, so the transcript is written in it.",
        )
        _ok_cancel(self, root, "Keeps these options for this submission.")
        self.SetSizerAndFit(root)
        self._noise.Bind(wx.EVT_CHOICE, lambda _e: self._sync())
        self._transcript.Bind(wx.EVT_CHECKBOX, lambda _e: self._sync())
        self._sync()
        self._leveler.SetFocus()

    def _choice(
        self,
        root: wx.BoxSizer,
        label: str,
        name: str,
        table: tuple[tuple[Any, str], ...],
        value: Any,
        help_text: str,
    ) -> wx.Choice:
        control = wx.Choice(self, choices=[words for _key, words in table])
        keys = [key for key, _words in table]
        control.SetSelection(keys.index(value) if value in keys else 0)
        control.keys = keys  # type: ignore[attr-defined]
        set_accessible_name(control, name)
        control.SetHelpText(help_text)
        _labelled(self, root, label, control)
        return control

    @staticmethod
    def _value(control: wx.Choice) -> Any:
        keys = control.keys  # type: ignore[attr-defined]
        return keys[max(0, control.GetSelection())]

    def _sync(self) -> None:
        self._method.Enable(self._value(self._noise) != NOISE_AMOUNTS[0][0])
        self._language.Enable(self._transcript.GetValue())

    def values(self) -> tuple[CustomProcessing, str, bool, str]:
        """``(custom, second_format, transcript, language)``."""
        custom = CustomProcessing(
            leveler=self._leveler.GetValue(),
            filtering=self._filtering.GetValue(),
            loudness=self._value(self._loudness),
            max_peak=self._value(self._peak),
            noise=self._value(self._noise),
            noise_method=self._value(self._method),
        )
        return (
            custom,
            self._value(self._second),
            self._transcript.GetValue(),
            self._value(self._language),
        )


def _values_on_ok(dialog: Any, title: str, show_modal: Any) -> Any:
    """*dialog*'s values when it closes with OK, else ``None``; never left alive."""
    try:
        shown = show_modal(dialog, title) if show_modal is not None else wx.ID_CANCEL
        return dialog.values() if shown == wx.ID_OK else None  # dialog_button_contract: exempt
    finally:
        dialog.Destroy()


def edit_tags(
    parent: Any,
    extras: AuphonicChoices,
    single: bool,
    source_chapters: tuple[tuple[float, str], ...],
    show_modal: Any,
    refuse: Callable[[str], None],
) -> AuphonicChoices:
    """Show Tags, Cover and Chapter Marks over *parent*; *extras* updated on OK."""
    dialog = AuphonicTagsDialog(
        parent,
        artist=extras.artist,
        album=extras.album,
        cover=extras.cover,
        chapters=extras.chapters,
        source_chapters=source_chapters,
        single=single,
        pick_cover=pick_cover_file,
        refuse=refuse,
    )
    values = _values_on_ok(dialog, TAGS_TITLE, show_modal)
    if values is None:
        return extras
    artist, album, cover, chapters = values
    return replace(extras, artist=artist, album=album, cover=cover, chapters=chapters)


def edit_more(parent: Any, extras: AuphonicChoices, show_modal: Any) -> AuphonicChoices:
    """Show More Auphonic Options over *parent*; *extras* updated on OK."""
    dialog = AuphonicMoreDialog(
        parent,
        custom=extras.custom,
        second_format=extras.second_format,
        transcript=extras.transcript,
        language=extras.language,
    )
    values = _values_on_ok(dialog, MORE_TITLE, show_modal)
    if values is None:
        return extras
    custom, second, transcript, language = values
    return replace(
        extras, custom=custom, second_format=second, transcript=transcript, language=language
    )


def pick_cover_file(parent: wx.Window) -> str:
    """A JPEG or PNG chosen in the system's file picker, or ``""``."""
    with wx.FileDialog(
        parent,
        "Choose a cover image",
        wildcard="Pictures (*.jpg;*.jpeg;*.png)|*.jpg;*.jpeg;*.png",
        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
    ) as picker:
        if picker.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
            return ""
        return str(Path(picker.GetPath()))
