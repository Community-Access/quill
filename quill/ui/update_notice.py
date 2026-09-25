"""The one "an update is available" dialog, for every app in the family.

Every QuillVille app can update itself, and until now each told the user about
it in its own words. QUILL showed the release notes in a scrollable read-only
box with *Later / Skip this version / Download update*; the eight companion
apps showed a bare Yes/No message box that said a newer version existed and
nothing whatsoever about what was in it. "Download it now?" is a question
nobody can answer: the only honest reply is "what changed?", and the app that
knew the answer -- it had the release body in hand -- threw it away.

So there is one dialog now, and it always carries three things:

* **a summary of what is new** -- the release notes, flattened out of Markdown
  into something a screen reader reads as prose rather than as punctuation, in
  a read-only multi-line control that arrows and Ctrl+Home like any document;
* **Update** -- the affirmative, and the default, so Enter does the expected
  thing from the moment the dialog opens;
* **Close** -- the escape, so Escape does too.

QUILL keeps one extra button (*Skip this version*), because QUILL is the only
app with somewhere to record the answer. Everything else about the dialog is
identical in all nine, which is the point: a person who learns the update
dialog in QUILL Lite has learned it in Quill Radio as well.

Two accessibility details are load-bearing and easy to lose:

* Focus lands on the **notes**, not on a button. A dialog that opens on its
  default button reads the button and stops; a listener then has to go looking
  for the text that was the whole reason the dialog appeared.
* **OK / Cancel / Close carry no access key** (GATE-14): Enter and Escape
  already reach them, and every letter they give up is one a real control in
  some other window can have.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from typing import Any

import wx as _wx_default

from quill.core.text_utils import strip_md_to_plain
from quill.ui.dialog_contract import apply_modal_ids

__all__ = [
    "CLOSE_LABEL",
    "NO_NOTES",
    "SKIP_LABEL",
    "UPDATE_LABEL",
    "present_release_notes",
    "show_update_available",
    "summarize_release_notes",
    "update_header",
]

#: The buttons, by the names the user reads. Update is the affirmative and the
#: default; Close is the escape. Neither carries an ``&`` mnemonic -- Enter and
#: Escape already serve them, and GATE-14 wants those letters back.
UPDATE_LABEL = "Update"
CLOSE_LABEL = "Close"
#: QUILL only: the one app that has a settings field to remember the answer in.
SKIP_LABEL = "Skip this version"

#: Said plainly rather than left blank. An empty notes box reads as a broken
#: dialog; this reads as a release whose author wrote nothing.
NO_NOTES = "(No release notes were provided for this version.)"

#: How much of a release body the dialog shows before it stops. Generous on
#: purpose -- the cap exists so a changelog that carries every commit since the
#: beginning of time does not turn the dialog into a scroll-hunt, not to keep
#: the summary short. Whatever is cut is still one link away.
MAX_NOTE_LINES = 60
MAX_NOTE_CHARS = 4000
_TRUNCATION_NOTE = "(Notes shortened. The full notes are on the release page.)"

#: A line of nothing but rule characters: a heading underline or a ``---``.
_RULE_LINE = re.compile(r"^\s*[-=_*]{3,}\s*$")


def summarize_release_notes(raw: str) -> str:
    """A GitHub release body as plain prose, capped, never empty.

    Markdown is flattened (``strip_md_to_plain``) because a screen reader reads
    ``## What's new`` as "number sign number sign what's new" and reads a table
    of pipes as pipes. Blank runs collapse to a single blank line so arrowing
    down the box moves through content rather than through nothing.
    """
    text = strip_md_to_plain((raw or "").strip()) if (raw or "").strip() else ""
    lines: list[str] = []
    blank = False
    for line in text.splitlines():
        stripped = line.rstrip()
        # The flattener underlines each heading, and a horizontal rule is the
        # same shape: either way a screen reader says "dash dash dash".
        if _RULE_LINE.match(stripped):
            continue
        if not stripped.strip():
            blank = True
            continue
        if blank and lines:
            lines.append("")
        blank = False
        lines.append(stripped)
    if not lines:
        return NO_NOTES
    truncated = len(lines) > MAX_NOTE_LINES
    lines = lines[:MAX_NOTE_LINES]
    summary = "\n".join(lines)
    if len(summary) > MAX_NOTE_CHARS:
        summary = summary[:MAX_NOTE_CHARS].rstrip()
        truncated = True
    if truncated:
        summary = f"{summary}\n\n{_TRUNCATION_NOTE}"
    return summary


def update_header(
    app_name: str,
    current_version: str,
    new_version: str,
    *,
    prerelease: bool = False,
    published_at: str = "",
) -> str:
    """The three or four lines above the notes: what is offered, and from where.

    The app's own name is in the first line because several of these apps can
    be open at once and a dialog that says only "Update available: 2.1.0" makes
    the user guess which window it belongs to.
    """
    channel = "Beta / prerelease" if prerelease else "Stable"
    published = f"Published: {published_at}\n" if str(published_at or "").strip() else ""
    name = f"{app_name} " if app_name else ""
    return (
        f"Update available: {name}{new_version}\n"
        f"Channel: {channel}\n"
        f"{published}"
        f"Current version: {current_version}"
    )


def present_release_notes(
    parent: Any,
    *,
    title: str,
    header: str,
    notes_plain: str,
    buttons: Sequence[tuple[str, int]],
    affirmative_id: int,
    escape_id: int,
    show_modal_dialog: Callable[[Any, str], int],
    wx_module: Any = None,
) -> int:
    """Show release notes in a read-only multi-line edit (help-text style).

    *header* is a short label above the notes; *notes_plain* is the flattened
    changelog shown in a scrollable, screen-reader-friendly ``TextCtrl``.
    *buttons* is ``[(label, id), ...]`` in reading order. Returns the id of the
    button the user pressed.

    *show_modal_dialog* is the host's own modal runner (``MainFrame._show_modal_dialog``
    or ``AppShellFrame._show_modal_dialog``) -- never ``ShowModal`` directly, so
    the keyboard contract and z-order handling stay in one place. *wx_module*
    exists for the hosts that indirect ``wx`` for testing.
    """
    wx = wx_module or _wx_default
    dialog = wx.Dialog(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    dialog.SetSize((560, 520))
    sizer = wx.BoxSizer(wx.VERTICAL)
    if header:
        heading = wx.StaticText(dialog, label=header)
        sizer.Add(heading, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
    notes_label = wx.StaticText(dialog, label="What's &new:")
    sizer.Add(notes_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
    body = wx.TextCtrl(
        dialog,
        value=notes_plain,
        style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_AUTO_URL | wx.TE_RICH2,
        name="release_notes",
    )
    body.SetName("What's new")
    body.SetHelpText(
        "What changed in this release, read-only. Arrow through it like a "
        "document. Tab moves on to the buttons."
    )
    sizer.Add(body, 1, wx.EXPAND | wx.ALL, 12)
    btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
    btn_sizer.AddStretchSpacer()
    for label, return_id in buttons:
        button = wx.Button(dialog, return_id, label=label)
        button.Bind(wx.EVT_BUTTON, lambda _e, r=return_id: dialog.EndModal(r))
        if return_id == affirmative_id:
            button.SetDefault()
        btn_sizer.Add(button, 0, wx.RIGHT, 6)
    sizer.Add(btn_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
    dialog.SetSizer(sizer)
    apply_modal_ids(dialog, affirmative_id=affirmative_id, escape_id=escape_id)
    # Land focus on the notes so screen-reader users enter on the text, not on
    # a button that reads its own label and says nothing about the release.
    wx.CallAfter(body.SetFocus)
    try:
        return show_modal_dialog(dialog, title)
    finally:
        dialog.Destroy()


def show_update_available(
    parent: Any,
    *,
    app_name: str,
    current_version: str,
    release: Any,
    show_modal_dialog: Callable[[Any, str], int],
    announce: Callable[[str], Any] | None = None,
    allow_skip: bool = False,
    title: str = "Check for Updates",
    header: str = "",
    notes_prefix: str = "",
    wx_module: Any = None,
) -> str:
    """Offer an available update, with its notes. Returns what the user chose.

    One of ``"update"`` (download it), ``"skip"`` (only reachable when
    *allow_skip*; don't offer this version again) or ``"close"`` (not now).

    *release* is duck-typed -- anything with ``version``, ``notes``,
    ``published_at`` and ``prerelease`` attributes, which is every shape
    ``quill.core.updates`` hands back. *notes_prefix* prepends a sentence to the
    notes for the cases that need one (QUILL's token self-heal reinstall).
    """
    wx = wx_module or _wx_default
    version = str(getattr(release, "version", "") or "")
    if announce is not None:
        announce(f"Update available: {version}")
    notes = summarize_release_notes(str(getattr(release, "notes", "") or ""))
    if notes_prefix:
        notes = f"{notes_prefix}\n\n{notes}"
    buttons: list[tuple[str, int]] = [(CLOSE_LABEL, wx.ID_CANCEL)]
    if allow_skip:
        buttons.append((SKIP_LABEL, wx.ID_IGNORE))
    buttons.append((UPDATE_LABEL, wx.ID_OK))
    result = present_release_notes(
        parent,
        title=title,
        header=header
        or update_header(
            app_name,
            current_version,
            version,
            prerelease=bool(getattr(release, "prerelease", False)),
            published_at=str(getattr(release, "published_at", "") or ""),
        ),
        notes_plain=notes,
        buttons=buttons,
        affirmative_id=wx.ID_OK,
        escape_id=wx.ID_CANCEL,
        show_modal_dialog=show_modal_dialog,
        wx_module=wx,
    )
    if result == wx.ID_OK:
        return "update"
    if allow_skip and result == wx.ID_IGNORE:
        return "skip"
    return "close"
