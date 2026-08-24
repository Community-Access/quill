"""Why a verb is dimmed, in words -- shared by Quill Radio and QUILL Cast.

A dimmed menu item is a dead end you cannot see around. A screen reader says
"dimmed" and stops; the item itself says nothing about what would un-dim it,
and this family dims a great deal *on purpose* -- Mark All as Played with
nothing unheard, Remove All Downloads with nothing downloaded, Analyse
Chapters on an episode whose bytes are not here yet. Each of those is a
*state of a verb the row genuinely owns*, which is exactly why it dims rather
than vanishes (see :class:`quill.core.radio.row_actions.RowAction`). The
missing half was saying which state.

So every dimmed action now carries a **reason**: one lower-case clause,
naming the condition and -- where a number makes it concrete -- the number::

    Download All Episodes: nothing to download, all 40 are already here.

The reason travels with the action, in the same wx-free table the label
lives in, and three surfaces spend it:

* the context menu's help string, which the status bar shows and readers that
  voice menu help speak;
* the Quick Action direct keys (Ctrl+1..Ctrl+9), which used to answer a
  dimmed action with "that Quick Action is not available" and now say why;
* the command palette, through ``CommandRegistry.set_availability_probe``.

**Wording rules**, so the reasons read as one voice:

* Lower case, no leading capital: :func:`explain` puts the label in front.
* State the condition, not the fix, unless the fix is one short clause
  ("...-- refresh the feed to fetch them").
* Prefer a count to an adjective. "nothing to download, all 40 are already
  here" answers a question "nothing to download" leaves open.
* No trailing full stop; :func:`explain` adds one.

The rule is enforced: an action that is dimmed with no reason fails
``tests/unit/core/test_dimmed_reason.py``.
"""

from __future__ import annotations

__all__ = [
    "already_downloaded",
    "clean_label",
    "download_in_flight",
    "explain",
    "no_chapters",
    "no_episodes_yet",
    "no_feed_address",
    "no_show_notes",
    "not_downloaded",
    "not_routed_to_inbox",
    "nothing_downloaded",
    "nothing_to_download",
    "nothing_unheard",
    "safe_mode",
]


def clean_label(label: str) -> str:
    """A menu label as a person hears it: no mnemonics, no accelerator tail.

    ``"Download All 40 Episo&des...\\tCtrl+3"`` -> ``"Download All 40 Episodes"``.
    """
    text = label.split("\t")[0].replace("&", "").strip()
    while text.endswith("."):
        text = text[:-1]
    return text.strip()


def explain(label: str, reason: str) -> str:
    """The spoken sentence: ``"<Label>: <reason>."``

    With no reason, the honest floor -- the label and the plain fact that it
    is unavailable -- rather than a sentence that pretends to explain.
    """
    name = clean_label(label) or "This command"
    text = reason.strip().rstrip(".")
    if not text:
        return f"{name} is not available right now."
    return f"{name}: {text}."


# -- the shared vocabulary -----------------------------------------------------
# Builders rather than constants wherever a count makes the answer concrete.


def nothing_unheard(total: int = 0) -> str:
    """Mark All as Played, with nothing left unheard."""
    if total > 0:
        return f"nothing to mark, all {total} episodes are already played"
    return "nothing to mark, every episode is already played"


def nothing_to_download(total: int) -> str:
    """Download All, with every episode already on disk."""
    if total > 0:
        return f"nothing to download, all {total} are already here"
    return "nothing to download"


def no_episodes_yet() -> str:
    """A subscribed show whose feed has not been read yet."""
    return "this show has no episodes yet -- refresh the feed to fetch them"


def nothing_downloaded() -> str:
    """Remove All Downloads, with nothing downloaded."""
    return "nothing is downloaded for this show"


def already_downloaded() -> str:
    return "this episode is already downloaded"


def download_in_flight() -> str:
    return "this episode is downloading now"


def not_downloaded(verb: str = "act on") -> str:
    """A verb that needs the audio on disk. *verb* completes the clause."""
    return f"this episode is not downloaded yet, so there is nothing to {verb}"


def no_show_notes() -> str:
    return "this episode arrived with no show notes"


def no_chapters() -> str:
    return "this episode carries no chapters, and none can be worked out from it"


def no_feed_address() -> str:
    return "this show has no feed address on file"


def not_routed_to_inbox() -> str:
    return "this show does not route new episodes to the Inbox"


def safe_mode() -> str:
    return "Safe Mode is on, so nothing reaches the network"
