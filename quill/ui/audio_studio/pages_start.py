"""Audio Studio wizard — the start page (choose a journey)."""

from __future__ import annotations

import wx

from quill.core.i18n import _
from quill.ui.audio_studio.pages_base import StudioPage
from quill.ui.audio_studio.request import JOURNEYS


class StartPage(StudioPage):
    """Page 1: what would you like to make?"""

    def __init__(self, parent: wx.Window, *, initial_journey: str = "documents") -> None:
        super().__init__(
            parent,
            "audio_studio.start",
            _("Welcome to the Audio Studio"),
            _("Choose what to make; the next steps adapt to your choice."),
        )
        self._journey = wx.RadioBox(
            self,
            label=_("What would you like to make?"),
            choices=[
                _("Narrate documents into an audiobook or speech audio"),
                _("Combine audio files into one chaptered audiobook"),
                _("Edit an existing audiobook (chapters, tags, and cover)"),
            ],
            majorDimension=1,
            style=wx.RA_SPECIFY_COLS,
            name="audio_studio.journey",
        )
        # Pre-select the journey the user used last (remembered journey).
        # Falls back to "documents" (the first option) for any unknown
        # value so a stale setting never strands the wizard.
        try:
            initial_idx = JOURNEYS.index(initial_journey)
        except ValueError:
            initial_idx = 0
        self._journey.SetSelection(initial_idx)
        self.sizer.Add(self._journey, flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=12)

        self.sizer.Add(
            wx.StaticText(
                self,
                label=_(
                    "Narrating documents reads Word, Markdown, HTML, or text files\n"
                    "aloud with any QUILL voice, one chapter per document or heading.\n"
                    "Combining audio files merges a folder of recordings into one\n"
                    "book, one chapter per file, with a review step before the merge.\n"
                    "Editing opens a finished MP3 or M4B in the Chapter Workbench:\n"
                    "listen, rename, split at the playhead, retime, fix tags, save."
                ),
                name="audio_studio.start_explainer",
            ),
            flag=wx.ALL,
            border=12,
        )

        self._load_job_btn = wx.Button(self, label=_("&Load a job file..."))
        self.sizer.Add(self._load_job_btn, 0, wx.LEFT | wx.BOTTOM, 12)

    def journey(self) -> str:
        idx = self._journey.GetSelection()
        return JOURNEYS[idx] if 0 <= idx < len(JOURNEYS) else "documents"

    def bind_journey_changed(self, handler) -> None:
        self._journey.Bind(wx.EVT_RADIOBOX, lambda _e: handler())

    def bind_load_job(self, handler) -> None:
        self._load_job_btn.Bind(wx.EVT_BUTTON, lambda _e: handler())
