"""The Scribe for Documents part of the Add/Edit Watch Profile dialog (PRD 8.1.6).

Kept out of :mod:`quill.ui.main_frame_watch_profile` (GATE-11). In tab order,
after the dialog's AI consent:

1. **"Scribe for Documents makes"**, a labelled group with a check box per
   format (separate check boxes rather than a check list, whose checked state
   NVDA reads unreliably -- accessibility review, 2026-11-21). The profile
   names the formats.
2. **The consent details**, a label and then a read-only multi-line field, so
   Tab reaches the words *before* the check box that agrees to them.
3. **"I agree to send this folder's files to Scribe for Documents (Pneuma
   Solutions)"**: the profile's standing consent, the only one there is
   (PRD 10.1.1), shown in the profile and revocable by unticking it.

The wording says that a watch folder spends Scribe pages with nobody at the
computer, and that each file uses the Scribe for Documents Options as they
are when it is sent -- never a copy of them, which would go stale.
"""

from __future__ import annotations

from typing import Any

from quill.core.scribe import PRODUCT_NAME
from quill.core.scribe.consent import COPYRIGHT_LINE
from quill.core.scribe.model import FORMATS, valid_formats

ACTION_ID = "scribe_convert"

#: The consent the profile's check box agrees to (PRD 10.1, 10.3).
WATCH_CONSENT_TEXT = (
    f"With this action on, every document that arrives in this folder is sent to "
    f"{PRODUCT_NAME} (Pneuma Solutions), one after another, with nobody at the computer. "
    "Each file uses Scribe pages from your account, about one for each page. It is "
    "processed in the United States and kept in your Scribe account under your retention "
    "setting (30 days unless you changed it). Pictures may be described by AI. Pneuma "
    "does not use documents to train AI. Each file uses your Scribe account's default "
    "settings as they are when it is sent, with any you set in Scribe for Documents "
    "Options on top. Only PDF, pictures, Office, OpenDocument, "
    "text, EPUB and MOBI files are sent; anything else is left alone. " + COPYRIGHT_LINE
)


class ScribeProfileControls:
    """Builds the controls into *dialog*'s *root* sizer, in tab order."""

    def __init__(self, wx: Any, dialog: Any, root: Any, options: dict[str, object]) -> None:
        chosen = valid_formats(options.get("formats")) or ["docx"]
        box = wx.StaticBoxSizer(wx.VERTICAL, dialog, f"{PRODUCT_NAME} makes")
        self.formats: dict[str, Any] = {}
        for item in FORMATS:
            check = wx.CheckBox(box.GetStaticBox(), label=item.label)
            check.SetValue(item.id in chosen)
            check.SetName(f"{PRODUCT_NAME} makes {item.label}")
            check.SetHelpText(
                f"With the {PRODUCT_NAME} action, each arriving file is converted to "
                f"{item.label}. You can choose several."
            )
            box.Add(check, 0, wx.ALL, 2)
            self.formats[item.id] = check
        root.Add(box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        label = wx.StaticText(dialog, label=f"{PRODUCT_NAME} consent details:")
        root.Add(label, 0, wx.LEFT | wx.RIGHT, 8)
        self.details = wx.TextCtrl(
            dialog, value=WATCH_CONSENT_TEXT, style=wx.TE_MULTILINE | wx.TE_READONLY
        )
        self.details.SetName(f"{PRODUCT_NAME} consent details")
        self.details.SetHelpText("What agreeing below means. Read it before you tick the box.")
        root.Add(self.details, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.consent = wx.CheckBox(
            dialog,
            label=f"I agree to send this folder's files to {PRODUCT_NAME} (Pneuma Solutions)",
        )
        self.consent.SetValue(bool(options.get("consent", False)))
        self.consent.SetName(f"{PRODUCT_NAME} consent for this profile")
        self.consent.SetHelpText(
            "This profile's standing consent. Untick it at any time and nothing more is sent."
        )
        root.Add(self.consent, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        #: The profile's own settings, if its file names any: kept as they were.
        self._settings = options.get("settings")

    def collect(self) -> dict[str, object]:
        """The action's options: formats, consent and any settings the profile named."""
        options: dict[str, object] = {
            "formats": [fid for fid, check in self.formats.items() if check.GetValue()],
            "consent": bool(self.consent.GetValue()),
        }
        if isinstance(self._settings, dict):
            options["settings"] = dict(self._settings)
        return options

    def problem(self) -> tuple[str, Any] | None:
        """Why OK cannot close yet, and the control to put focus on, or None."""
        if not any(check.GetValue() for check in self.formats.values()):
            return (f"Choose at least one format for {PRODUCT_NAME} to make.", self.formats["docx"])
        if not self.consent.GetValue():
            return (
                f"To use {PRODUCT_NAME} in this profile, read the consent details and tick "
                "the box that agrees to them.",
                self.consent,
            )
        return None


__all__ = ["ACTION_ID", "WATCH_CONSENT_TEXT", "ScribeProfileControls"]
