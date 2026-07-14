"""Speech Hub dialog — unified Read Aloud + Dictation settings, split by
Offline/Online, in one tabbed window.

Replaces the two separate dialogs (VoiceBrowserDialog for TTS, SpeechSetupDialog
for STT) with a single ``wx.Notebook``-based dialog so users can switch between
TTS and STT settings without closing and reopening different dialogs. Each of
those two gets its own Offline/Online tab pair, since local engines (installed
once, no ongoing cost) and cloud providers (an API key, per-use network cost)
are different enough resource models that mixing them in one flat list reads
as confusing (#847).

Preview works without closing the hub.  Download and export actions close the
hub so the caller can start the background operation; after completion the hub
is reopened on the same tab via the existing ``on_ok`` callback pattern.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from quill.ui.dialog_contract import apply_modal_ids, focus_primary_control

if TYPE_CHECKING:
    from collections.abc import Callable

    from quill.ui.speech_setup_dialog import SpeechSetupResult
    from quill.ui.voice_browser_dialog import VoiceBrowserResult

# Tab indices, exported so callers of MainFrame.open_speech_hub() name them
# instead of guessing a number.
TAB_SPEECH_OFFLINE = 0
TAB_SPEECH_ONLINE = 1
TAB_DICTATION_OFFLINE = 2
TAB_DICTATION_ONLINE = 3


class SpeechHubDialog:
    """Unified Speech Settings dialog: Speech (Offline/Online) and Dictation
    (Offline/Online) tabs.

    Parameters
    ----------
    parent:
        wx parent window.
    read_aloud_offline_kwargs, read_aloud_online_kwargs:
        Keyword arguments forwarded to ``VoiceBrowserDialog`` (all except
        ``embed_in`` and ``on_action``) for the Speech (Offline)/(Online) tabs.
    dictation_offline_kwargs:
        Keyword arguments forwarded to ``SpeechSetupDialog`` for the Dictation
        (Offline) tab.
    dictation_online_kwargs:
        Keyword arguments forwarded to ``SpeechSetupDialog`` for the Dictation
        (Online) tab, or ``None`` when no cloud dictation provider is
        registered -- the tab then shows a plain explanatory message instead
        of a dialog with nothing to select (a ``wx.RadioBox`` cannot hold zero
        choices).
    initial_tab:
        Which tab to select initially; use the ``TAB_*`` constants above.
    """

    def __init__(
        self,
        parent: object,
        *,
        read_aloud_offline_kwargs: dict,
        read_aloud_online_kwargs: dict,
        dictation_offline_kwargs: dict,
        dictation_online_kwargs: dict | None,
        initial_tab: int = TAB_SPEECH_OFFLINE,
    ) -> None:
        import wx

        self._wx = wx
        self._ra_action: VoiceBrowserResult | None = None
        self._dict_action: SpeechSetupResult | None = None

        self.dialog = wx.Dialog(
            parent,
            title="Speech Settings",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(wx.Size(640, 580))
        self.dialog.SetSize(wx.Size(740, 660))

        root = wx.BoxSizer(wx.VERTICAL)
        self._nb = wx.Notebook(self.dialog)

        from quill.ui.voice_browser_dialog import VoiceBrowserDialog

        offline_page = wx.Panel(self._nb)
        self._voice_browser_offline = VoiceBrowserDialog(
            offline_page,
            embed_in=offline_page,
            on_action=self._on_ra_action,
            **read_aloud_offline_kwargs,
        )
        self._nb.AddPage(offline_page, "Speech (Offline)")

        online_page = wx.Panel(self._nb)
        self._voice_browser_online = VoiceBrowserDialog(
            online_page,
            embed_in=online_page,
            on_action=self._on_ra_action,
            **read_aloud_online_kwargs,
        )
        self._nb.AddPage(online_page, "Speech (Online)")

        from quill.ui.speech_setup_dialog import SpeechSetupDialog

        dict_offline_page = wx.Panel(self._nb)
        self._speech_setup_offline = SpeechSetupDialog(
            dict_offline_page,
            embed_in=dict_offline_page,
            on_action=self._on_dict_action,
            **dictation_offline_kwargs,
        )
        self._nb.AddPage(dict_offline_page, "Dictation (Offline)")

        dict_online_page = wx.Panel(self._nb)
        if dictation_online_kwargs is None:
            self._speech_setup_online: object | None = None
            _build_no_cloud_dictation_panel(wx, dict_online_page)
        else:
            self._speech_setup_online = SpeechSetupDialog(
                dict_online_page,
                embed_in=dict_online_page,
                on_action=self._on_dict_action,
                **dictation_online_kwargs,
            )
        self._nb.AddPage(dict_online_page, "Dictation (Online)")

        if 0 <= initial_tab < self._nb.GetPageCount():
            self._nb.SetSelection(initial_tab)

        root.Add(self._nb, 1, wx.EXPAND | wx.ALL, 6)

        # Dialog-level OK / Cancel
        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        ok_btn = wx.Button(self.dialog, id=wx.ID_OK)
        cancel_btn = wx.Button(self.dialog, id=wx.ID_CANCEL)
        btn_row.AddStretchSpacer()
        btn_row.Add(ok_btn, 0, wx.RIGHT, 6)
        btn_row.Add(cancel_btn, 0)
        root.Add(btn_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        self.dialog.SetSizer(root)

    # ------------------------------------------------------------------
    # Internal callbacks from embedded panels
    # ------------------------------------------------------------------

    def _on_ra_action(self, result: VoiceBrowserResult) -> None:
        """Download / export triggered from a Speech tab — close hub."""
        self._ra_action = result
        self.dialog.EndModal(self._wx.ID_OK)

    def _on_dict_action(self, result: SpeechSetupResult) -> None:
        """Any action triggered from a Dictation tab — close hub."""
        self._dict_action = result
        self.dialog.EndModal(self._wx.ID_OK)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def show(
        self, show_modal_dialog: Callable
    ) -> tuple[VoiceBrowserResult | None, SpeechSetupResult | None]:
        """Open the hub.

        Returns ``(ra_result, dict_result)`` where each is ``None`` when no
        action was taken in that tab.  When the user clicks the dialog-level
        OK button without triggering a specific action and a Speech tab is
        active, the current selection there is collected and returned as a
        ``'select'`` result (matching the single-tab hub's behavior).
        """
        focus_primary_control(self.dialog)
        result_code = show_modal_dialog(self.dialog, "Speech Settings")
        ra_result = self._ra_action
        dict_result = self._dict_action
        if result_code == self._wx.ID_OK and ra_result is None and dict_result is None:
            selection = self._nb.GetSelection()
            if selection == TAB_SPEECH_OFFLINE:
                ra_result = self._voice_browser_offline.collect_result()
            elif selection == TAB_SPEECH_ONLINE:
                ra_result = self._voice_browser_online.collect_result()
        self.dialog.Destroy()
        return ra_result, dict_result


def _build_no_cloud_dictation_panel(wx: object, panel: object) -> None:
    """The Dictation (Online) tab's content when no cloud provider is
    registered: an explanatory message, not an empty, confusing dialog."""
    root = wx.BoxSizer(wx.VERTICAL)  # type: ignore[attr-defined]
    message = wx.StaticText(  # type: ignore[attr-defined]
        panel,
        label=(
            "No cloud dictation provider is installed yet.\n\n"
            "Install a cloud transcription Quillin (OpenAI Whisper, Groq, or "
            "ElevenLabs Scribe) to add one here. Offline dictation (Whisper.cpp, "
            "Faster Whisper, or Vosk) needs no API key or account and works "
            "without an internet connection -- see the Dictation (Offline) tab."
        ),
    )
    message.Wrap(500)
    root.Add(message, 0, wx.ALL | wx.EXPAND, 20)
    panel.SetSizer(root)  # type: ignore[attr-defined]
