"""Submit to Quillin Hub: local validation plus a guided browser handoff.

Runs the exact same checks the Hub's Submission Forge runs -- via
``quill.tools.artifact_validate``, the single validation authority for every
shareable QUILL artifact type -- and reports the result in an accessible
dialog. Everything is local; the Quillin Hub opens in the user's browser only
on the explicit "Open the Quillin Hub" button press, so QUILL itself makes no
network call anywhere in this flow.

Follows the ``quillin_wizard`` module pattern: a standalone function that
receives the frame, the ``wx`` module, and the MainFrame helpers it needs, so
``main_frame_quillins.py`` stays within its size budget.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.ui.dialog_contract import set_accessible_name

# The community store for every shareable QUILL artifact type.
#
# **Not open yet, and this host does not resolve.** The constants are kept
# rather than deleted because the local validation below is the useful half and
# it works: it runs the exact checks the Hub will run, so an artifact that
# passes here is ready for the day the Hub exists.
#
# What is NOT kept is a button that opened a browser at nothing. A dead link is
# worse for somebody using a screen reader than a missing one: the browser
# opens, focus leaves the app, and what greets them is a DNS error page they
# then have to navigate back out of -- all of which reads as "I did something
# wrong". Until this host answers, the dialog says so in words instead.
#
# The domain is an open question -- see section 6 of
# docs/design/2026-08-26-feedback-redesign-for-freescout.md. To re-enable once
# it resolves, set HUB_IS_LIVE to True: that is the whole change, because the
# button and its handler are still here.
QUILLIN_HUB_URL = "https://hub.quillforall.org"
QUILLIN_HUB_SUBMIT_URL = QUILLIN_HUB_URL + "/forge/submit"
HUB_IS_LIVE = False

_WILDCARD = (
    "All QUILL artifacts|*.zip;*.qsp;*.kqp;*.sqp;*.qvp.json;*.md;*.json|"
    "Quillin manifest (manifest.json)|manifest.json|"
    "All files (*.*)|*.*"
)


def _headline(status: str) -> str:
    if status == "pass":
        return "Passed. This artifact clears every check the Quillin Hub runs on submission."
    if status == "fail":
        return "Needs work. Fix the errors below, then run this check again."
    return "Not recognised. This file does not look like a shareable QUILL artifact."


def open_hub_submission(
    frame: object,
    wx: Any,
    *,
    announce: Any,
    show_modal_dialog: Any,
) -> None:
    """Pick an artifact, validate it locally, and guide the user to the Hub.

    Choosing a Quillin's ``manifest.json`` validates the whole folder -- the
    accessible alternative to a directory picker.
    """

    with wx.FileDialog(
        frame,
        "Choose the artifact to check for Hub submission",
        wildcard=_WILDCARD,
        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
    ) as fdlg:
        if show_modal_dialog(fdlg, "Submit to Quillin Hub") != wx.ID_OK:
            return
        chosen = Path(fdlg.GetPath())

    target = chosen.parent if chosen.name.lower() == "manifest.json" else chosen

    from quill.tools.artifact_validate import render_report, validate_artifact
    from quill.tools.signing import signature_status

    report = validate_artifact(target)
    passed = report["status"] == "pass"
    headline = _headline(report["status"])
    body_text = headline + "\n\n" + render_report(report)

    # Signature status (always shown -- this is the user's only chance to
    # see whether their artifact is signed before they upload it to the
    # Hub, where unsigned submissions are now rejected).
    sig = signature_status(target)
    if sig.verified:
        body_text += f"\n\nSignature: verified, signed by {sig.signer_key_id}."
    elif sig.signed:
        body_text += (
            f"\n\nSignature: invalid ({sig.error or 'does not match publisher key'}). "
            "The Hub will reject this until you re-sign it."
        )
    else:
        body_text += (
            "\n\nSignature: not signed. The Hub rejects unsigned submissions. "
            "Re-sign with 'python -m quill.tools.signing sign <artifact>' and "
            "upload the .minisig sidecar alongside."
        )

    if passed and HUB_IS_LIVE:
        body_text += (
            "\n\nNext step: choose 'Open the Quillin Hub' to start your submission. "
            "The Hub re-runs these same checks and guides you through a GitHub "
            "pull request."
        )
    elif passed:
        body_text += (
            "\n\nThe Quillin Hub is not open yet, so there is nowhere to submit this "
            "today. Nothing is wrong with your artifact -- it has passed every check "
            "the Hub will run, so it is ready for the day it opens. Keep the file and "
            "its .minisig sidecar together."
        )

    dialog = wx.Dialog(
        frame,
        title="Submit to Quillin Hub",
        style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
    )
    sizer = wx.BoxSizer(wx.VERTICAL)
    text = wx.TextCtrl(
        dialog,
        value=body_text,
        style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP,
        size=(560, 300),
    )
    set_accessible_name(text, "Submission check results")
    sizer.Add(text, 1, wx.EXPAND | wx.ALL, 8)

    buttons = wx.BoxSizer(wx.HORIZONTAL)
    if passed and sig.verified and HUB_IS_LIVE:
        open_button = wx.Button(dialog, label="&Open the Quillin Hub")

        def on_open_hub(_event: object) -> None:
            import webbrowser

            webbrowser.open(QUILLIN_HUB_SUBMIT_URL)
            announce("Opened the Quillin Hub in your browser.")

        open_button.Bind(wx.EVT_BUTTON, on_open_hub)
        buttons.Add(open_button, 0, wx.RIGHT, 8)
    close_button = wx.Button(dialog, wx.ID_OK, "&Close")
    close_button.SetDefault()
    buttons.Add(close_button, 0)
    sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
    dialog.SetSizerAndFit(sizer)

    from quill.ui.dialog_contract import apply_modal_ids

    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_OK)
    announce(headline)
    try:
        show_modal_dialog(dialog, "Submit to Quillin Hub")
    finally:
        dialog.Destroy()
