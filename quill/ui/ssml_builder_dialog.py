"""SSML Builder — author a pronunciation in SSML by ear, no raw XML required (§4.7.9).

A keyboard-first ``wx.Dialog`` that lets a user construct an SSML fragment for a
term using quick-insert helpers (IPA phoneme, spell-out, substitute, pause,
slow/fast, pitch) instead of typing XML. The assembled fragment is shown in an
editable box, validated as well-formed XML on every change, and a plain-text
fallback is captured so the same entry still works on engines that do not speak
SSML (Kokoro/Piper/DECtalk). ``show`` returns ``(ssml_fragment, plain_fallback)``
or ``None`` on cancel.

The SSML/validation primitives are the wx-free core
(:mod:`quill.core.speech.pronunciation`); this is presentation only. All controls
are parented directly on the dialog (NVDA focus rule).
"""

from __future__ import annotations

from typing import Any

from quill.core.speech.pronunciation import (
    ssml_break,
    ssml_phoneme,
    ssml_prosody,
    ssml_say_as,
    ssml_sub,
    validate_ssml_fragment,
)
from quill.ui.dialog_contract import apply_modal_ids, show_message_box


class SsmlBuilderDialog:
    """Guided SSML authoring for one term, with live validation and a fallback."""

    def __init__(
        self,
        parent: object,
        *,
        term: str,
        fragment: str = "",
        fallback: str = "",
        on_audition: Any = None,
    ) -> None:
        import wx

        self._wx = wx
        self._on_audition = on_audition
        self._result: tuple[str, str] | None = None

        self.dialog = wx.Dialog(
            parent,
            title="SSML Builder",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(wx.Size(560, 520))
        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(wx.StaticText(self.dialog, label="&Word or phrase:"), 0, wx.ALL, 6)
        self._term = wx.TextCtrl(self.dialog, value=term)
        root.Add(self._term, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        # Quick-insert helpers (each appends a fragment for the current term).
        root.Add(wx.StaticText(self.dialog, label="Insert:"), 0, wx.LEFT | wx.TOP, 6)
        grid = wx.GridSizer(cols=3, vgap=4, hgap=4)
        for label, handler in (
            ("Phoneme (&IPA)...", self._insert_phoneme),
            ("Spell &out", lambda _e: self._append(ssml_say_as(self._term_text(), "characters"))),
            ("Su&bstitute...", self._insert_sub),
            ("&Pause...", self._insert_break),
            ("Sl&ow", lambda _e: self._append(ssml_prosody(self._term_text(), rate="slow"))),
            ("&Fast", lambda _e: self._append(ssml_prosody(self._term_text(), rate="fast"))),
            ("Pitch &up", lambda _e: self._append(ssml_prosody(self._term_text(), pitch="high"))),
            ("Pitch &down", lambda _e: self._append(ssml_prosody(self._term_text(), pitch="low"))),
        ):
            b = wx.Button(self.dialog, label=label)
            b.Bind(wx.EVT_BUTTON, handler)
            grid.Add(b, 0, wx.EXPAND)
        root.Add(grid, 0, wx.EXPAND | wx.ALL, 6)

        root.Add(wx.StaticText(self.dialog, label="SS&ML fragment:"), 0, wx.LEFT | wx.TOP, 6)
        self._fragment = wx.TextCtrl(
            self.dialog, value=fragment, style=wx.TE_MULTILINE | wx.TE_DONTWRAP
        )
        self._fragment.SetMinSize(wx.Size(-1, 90))
        self._fragment.Bind(wx.EVT_TEXT, lambda _e: self._validate())
        root.Add(self._fragment, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        self._status = wx.StaticText(self.dialog, label="")
        root.Add(self._status, 0, wx.ALL, 6)

        root.Add(
            wx.StaticText(self.dialog, label="Plain fallback (&spoken on non-SSML engines):"),
            0,
            wx.LEFT | wx.TOP,
            6,
        )
        self._fallback = wx.TextCtrl(self.dialog, value=fallback or term)
        root.Add(self._fallback, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        if on_audition is not None:
            hear = wx.Button(self.dialog, label="Play &fallback")
            hear.Bind(
                wx.EVT_BUTTON,
                lambda _e: self._on_audition(self._fallback.GetValue().strip() or term),
            )
            root.Add(hear, 0, wx.ALL, 6)

        btns = wx.BoxSizer(wx.HORIZONTAL)
        ok = wx.Button(self.dialog, id=wx.ID_OK, label="&Use this SSML")
        cancel = wx.Button(self.dialog, id=wx.ID_CANCEL)
        ok.Bind(wx.EVT_BUTTON, self._on_ok)
        btns.AddStretchSpacer()
        btns.Add(ok, 0, wx.RIGHT, 6)
        btns.Add(cancel, 0)
        root.Add(btns, 0, wx.EXPAND | wx.ALL, 8)

        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        self.dialog.SetSizer(root)
        self._validate()

    # -- helpers ---------------------------------------------------------- #

    def _term_text(self) -> str:
        return self._term.GetValue().strip()

    def _append(self, fragment: str) -> None:
        existing = self._fragment.GetValue().strip()
        self._fragment.SetValue(f"{existing} {fragment}".strip() if existing else fragment)

    def _validate(self) -> bool:
        frag = self._fragment.GetValue().strip()
        if not frag:
            self._status.SetLabel("Empty - add a fragment or use an Insert button.")
            return False
        if validate_ssml_fragment(frag):
            self._status.SetLabel("Valid SSML.")
            return True
        self._status.SetLabel("Not well-formed XML - check the tags.")
        return False

    # -- quick inserts ---------------------------------------------------- #

    def _prompt(self, message: str, caption: str, default: str = "") -> str | None:
        wx = self._wx
        dlg = wx.TextEntryDialog(self.dialog, message, caption, default)
        try:
            if dlg.ShowModal() != wx.ID_OK:
                return None
            return dlg.GetValue().strip()
        finally:
            dlg.Destroy()

    def _insert_phoneme(self, _evt: object) -> None:
        ipa = self._prompt("IPA pronunciation (e.g. kwɪl):", "Phoneme (IPA)")
        if ipa:
            self._append(ssml_phoneme(self._term_text(), ipa))

    def _insert_sub(self, _evt: object) -> None:
        alias = self._prompt("Say this instead:", "Substitute")
        if alias:
            self._append(ssml_sub(self._term_text(), alias))

    def _insert_break(self, _evt: object) -> None:
        ms = self._prompt("Pause length in milliseconds:", "Pause", "300")
        if ms and ms.isdigit():
            self._append(ssml_break(int(ms)))

    # -- finish ----------------------------------------------------------- #

    def _on_ok(self, evt: object) -> None:
        if not self._validate():
            show_message_box(
                "The SSML is empty or not well-formed. Fix it or press Cancel.",
                "SSML Builder",
                self._wx.OK | self._wx.ICON_ERROR,
                self.dialog,
            )
            return
        self._result = (
            self._fragment.GetValue().strip(),
            self._fallback.GetValue().strip() or self._term_text(),
        )
        evt.Skip()

    def show(self, show_modal_dialog: Any) -> tuple[str, str] | None:
        code = show_modal_dialog(self.dialog, "SSML Builder")
        result = self._result if code == self._wx.ID_OK else None
        self.dialog.Destroy()
        return result
