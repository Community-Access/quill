"""Audio Studio wizard — the combine-audio-files journey's source page."""

from __future__ import annotations

from pathlib import Path

import wx

from quill.core.i18n import _
from quill.ui.audio_studio.pages_base import StudioPage
from quill.ui.audio_studio.request import BatchSpeechRequest


class AudioSourcePage(StudioPage):
    """Where are the recordings? Folder of audio files to bind into one book."""

    def __init__(self, parent: wx.Window, defaults: BatchSpeechRequest) -> None:
        super().__init__(
            parent,
            "audio_studio.audio_source",
            _("Where are the recordings?"),
            _(
                "Pick the folder of audio files. Each file becomes one chapter,"
                " in natural filename order, and you review the chapter list"
                " before the book is built."
            ),
        )
        self.add_label(_("&Folder of audio files:"))
        row = wx.BoxSizer(wx.HORIZONTAL)
        # ComboBox seeded from the Audio Studio's source-folder MRU.
        # Same pattern as DocSourcePage — the audio and documents journeys
        # share the source-folder MRU because both pick "the folder of
        # stuff" with no semantic difference at the filesystem level.
        self._seed_source_choices(defaults.source_folder)
        self.source = wx.ComboBox(
            self,
            value=str(defaults.source_folder),
            choices=self._source_choices,
            style=wx.CB_DROPDOWN | wx.TE_PROCESS_ENTER,
        )
        self.source.SetName(_("Folder of audio files"))
        browse = wx.Button(self, label=_("B&rowse..."))
        browse.Bind(wx.EVT_BUTTON, self._on_browse)
        row.Add(self.source, 1, wx.EXPAND | wx.RIGHT, 6)
        row.Add(browse, 0)
        self.sizer.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        self.recursive = wx.CheckBox(self, label=_("Include su&bfolders"))
        self.recursive.SetValue(defaults.recursive)
        self.sizer.Add(self.recursive, 0, wx.LEFT | wx.TOP, 12)

        self.library = wx.CheckBox(
            self,
            label=_("&Library mode: every subfolder becomes its own audiobook"),
        )
        self.library.SetValue(defaults.library_mode)
        self.sizer.Add(self.library, 0, wx.LEFT | wx.TOP, 12)

        self.trim = wx.CheckBox(
            self,
            label=_("&Trim leading and trailing silence from each recording"),
        )
        self.trim.SetValue(defaults.trim_silence_files)
        self.sizer.Add(self.trim, 0, wx.LEFT | wx.TOP, 12)

        self.sizer.Add(
            wx.StaticText(
                self,
                label=_(
                    "MP3, M4A/M4B, WAV, FLAC, Opus and OGG files are accepted.\n"
                    "Files that look like previous builds are set aside automatically.\n"
                    "In library mode each book is titled after its subfolder and\n"
                    "built without the review step."
                ),
                name="audio_studio.audio_source_note",
            ),
            flag=wx.ALL,
            border=12,
        )

    def _seed_source_choices(self, current) -> None:
        """Populate ``self._source_choices`` from the MRU plus the current value.

        Mirrors :meth:`DocSourcePage._seed_source_choices`: the current value
        appears first, the MRU follows, and the dropdown is a one-keystroke
        list of recent folders for the second run.
        """
        try:
            from quill.core.recent import recent_audio_source_folders

            mru = [str(p) for p in recent_audio_source_folders()]
        except Exception:  # noqa: BLE001 - MRU read is best-effort
            mru = []
        seen: set[str] = set()
        ordered: list[str] = []
        if current:
            ordered.append(str(current))
            seen.add(str(current))
        for entry in mru:
            if entry in seen:
                continue
            seen.add(entry)
            ordered.append(entry)
        self._source_choices = ordered

    def _on_browse(self, _evt: wx.Event) -> None:
        with wx.DirDialog(self, _("Choose the folder of audio files")) as dlg:
            if dlg.ShowModal() == wx.ID_OK:  # GATE-42-OK: native folder picker
                self.source.SetValue(dlg.GetPath())
                self._seed_source_choices(dlg.GetPath())
                self.source.SetItems(self._source_choices)
                self.source.SetValue(dlg.GetPath())

    def collect(self, req: BatchSpeechRequest) -> None:
        req.source_folder = Path(self.source.GetValue().strip())
        req.recursive = self.recursive.GetValue()
        # A pure-audio run synthesizes nothing: no document types, book always on,
        # and the chapter review step always offered (the runner also forces the
        # editor open when a folder has no documents).
        req.extensions = ()
        req.make_book = True
        req.trim_silence_files = self.trim.GetValue()
        req.library_mode = self.library.GetValue()
        # Library mode builds unattended (no per-book review dialogs).
        req.book_review_chapters = not req.library_mode
        req.dry_run = False

    def is_valid(self) -> tuple[bool, str]:
        text = self.source.GetValue().strip()
        if not text or not Path(text).is_dir():
            return False, _("Choose a folder of audio files that exists.")
        return True, ""


class EditSourcePage(StudioPage):
    """Open a book: pick the finished MP3 or M4B to edit in the Workbench."""

    def __init__(self, parent: wx.Window) -> None:
        super().__init__(
            parent,
            "audio_studio.edit_source",
            _("Open a book"),
            _(
                "Pick a chaptered MP3 or M4B. It opens in the Chapter Workbench,"
                " where you can listen, rename, split at the playhead, retime"
                " boundaries, fix the tags, and save."
            ),
        )
        self.add_label(_("&Audiobook file:"))
        row = wx.BoxSizer(wx.HORIZONTAL)
        # ComboBox seeded from the audiobooks MRU so the second time the
        # user opens the edit journey, the last book is
        # one Tab away instead of a fresh file dialog.
        self._seed_file_choices()
        self.file = wx.ComboBox(
            self,
            choices=self._file_choices,
            style=wx.CB_DROPDOWN | wx.TE_PROCESS_ENTER,
        )
        self.file.SetName(_("Audiobook file"))
        browse = wx.Button(self, label=_("B&rowse..."))
        browse.Bind(wx.EVT_BUTTON, self._on_browse)
        row.Add(self.file, 1, wx.EXPAND | wx.RIGHT, 6)
        row.Add(browse, 0)
        self.sizer.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        self.sizer.Add(
            wx.StaticText(
                self,
                label=_(
                    "An MP3 saves its edits in place (the audio is untouched).\n"
                    "An M4B saves as a new file, losslessly. A file with no chapter\n"
                    "markers opens as one chapter, ready to split up."
                ),
                name="audio_studio.edit_source_note",
            ),
            flag=wx.ALL,
            border=12,
        )

    def _seed_file_choices(self) -> None:
        """Populate ``self._file_choices`` from the audiobooks MRU.

        Unlike the source-folder pages, there is no current value to
        pre-seed (the edit journey opens from a clean state). The most
        recently opened audiobook lands at the top of the dropdown.
        """
        try:
            from quill.core.recent import recent_audiobook_files

            mru = [str(p) for p in recent_audiobook_files()]
        except Exception:  # noqa: BLE001 - MRU read is best-effort
            mru = []
        self._file_choices = mru

    def _on_browse(self, _evt: wx.Event) -> None:
        with wx.FileDialog(
            self,
            _("Open an audiobook"),
            wildcard=_("Audiobooks (*.mp3;*.m4b;*.m4a)|*.mp3;*.m4b;*.m4a|All files (*.*)|*.*"),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dlg:
            if dlg.ShowModal() == wx.ID_OK:  # GATE-42-OK: native file picker
                self.file.SetValue(dlg.GetPath())
                self._seed_file_choices()
                self.file.SetItems(self._file_choices)
                self.file.SetValue(dlg.GetPath())

    def chosen_path(self) -> Path | None:
        text = self.file.GetValue().strip()
        return Path(text) if text else None

    def is_valid(self) -> tuple[bool, str]:
        path = self.chosen_path()
        if path is None or not path.is_file():
            return False, _("Choose an audiobook file that exists.")
        return True, ""
