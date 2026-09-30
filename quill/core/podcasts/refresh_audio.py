"""Refresh Episode Audio: get this episode's file again, from wherever it is now (R3).

Some hosts move their audio. A podcast network changes CDN, an episode is re-cut
and re-uploaded, an ad-insertion service rotates the address it hands out -- and
the enclosure URL Cast stored when it first read the feed stops working. The
symptoms are miserable and all look like Cast's fault: a download that 404s, or,
worse, a file that downloaded once and is truncated or silent, which plays for
ninety seconds and stops.

The listener's own answer today is to unsubscribe and re-subscribe, which throws
away every position and every played mark in the show to fix one episode.

So: one verb on one episode. Re-read the feed, take **whatever address the feed
says now**, throw the local file away, and download it again.

Three rules, and the middle one is the one worth stating:

1. **The feed is the authority on where the audio is.** If the address changed,
   the stored one was wrong and is replaced.
2. **What you did is never touched.** Position, played, the intro-skip flag, the
   note, the per-file speed: all kept. The audio moved; your history with the
   episode did not, and the whole point of this verb over unsubscribing is that
   it does not cost you that.
3. **A refresh is worth doing even when the address is identical**, because the
   common case is not a moved file, it is a *bad* file. Answering "the address
   has not changed, nothing to do" would refuse the exact repair somebody asked
   for. The wording says which of the two happened, so a listener whose problem
   was the address learns that it moved.

Nothing here deletes or downloads anything: it decides, and returns a
:class:`Plan` for the caller to carry out. That is what makes it testable and
what keeps the "never touch played state" rule checkable by reading one file.

wx-free, strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = ["Plan", "apply_plan", "confirm_message", "plan_for"]


@dataclass(frozen=True, slots=True)
class Plan:
    """What a refresh would do, and what to say about it.

    ``ok`` false means there is nothing to do and ``message`` says why, which is
    always a sentence about this episode rather than a generic refusal -- the
    only two reasons are a local file and a feed that no longer lists the
    episode, and those want very different answers from the listener.
    """

    ok: bool
    message: str
    new_url: str = ""
    delete_path: str = ""
    moved: bool = False


def plan_for(show: Any, episode: Any, fresh_url: str) -> Plan:
    """Decide what refreshing *episode* means, given the address the feed says now.

    *fresh_url* is what a re-read of the feed produced for this episode's guid;
    ``""`` means the feed no longer carries it, which is a different situation
    from a changed address and gets its own sentence.
    """
    title = str(getattr(episode, "title", "") or "this episode")
    if bool(getattr(show, "is_local", False)):
        return Plan(
            False,
            f"{title} is one of your own files, so there is no feed to refresh it "
            "from. Your file is where you put it.",
        )
    if not str(getattr(show, "feed_url", "") or ""):
        return Plan(False, f"{title} belongs to a podcast with no feed address.")
    fresh = fresh_url.strip()
    if not fresh:
        return Plan(
            False,
            f"The feed no longer lists {title}, so there is no new address to "
            "fetch. Anything already downloaded has been left alone.",
        )
    stored = str(getattr(episode, "audio_url", "") or "").strip()
    downloaded = str(getattr(episode, "downloaded_path", "") or "").strip()
    moved = bool(stored) and fresh != stored
    if moved:
        message = (
            f"{title} has moved to a new address. Cast will download it again "
            "from there; your position and played mark are kept."
        )
    else:
        message = (
            f"The feed still gives the same address for {title}. Cast will "
            "download it again anyway, in case the file itself is the problem; "
            "your position and played mark are kept."
        )
    return Plan(True, message, new_url=fresh, delete_path=downloaded, moved=moved)


def confirm_message(plan: Plan) -> str:
    """The question to ask before acting, naming the one cost.

    The cost is the download, and it is named because somebody on a metered
    connection or a slow line should know before, not after. Everything else
    this touches is either already broken or kept.
    """
    if not plan.ok:
        return plan.message
    tail = (
        " The copy on this computer will be deleted first."
        if plan.delete_path
        else " Nothing is downloaded yet, so there is nothing to delete."
    )
    return f"{plan.message}{tail}\n\nRefresh it now?"


def apply_plan(episode: Any, plan: Plan) -> bool:
    """Point *episode* at the fresh address and forget the local file.

    Returns whether anything changed. **Deliberately does not touch**
    ``played``, ``position_ms``, ``intro_skipped``, ``speed_override`` or the
    note: the file is being replaced, not the listening.

    The file on disk is the caller's to remove (it holds the paths and the error
    reporting); this only stops the record pointing at it, and it does that
    *before* the download so a failed download leaves an episode that will
    stream rather than one that claims a file it no longer has.
    """
    if not plan.ok:
        return False
    episode.audio_url = plan.new_url
    episode.downloaded_path = ""
    # The stored hash described the file that is being thrown away. Leaving it
    # would make the replacement look like a duplicate of its own predecessor.
    if getattr(episode, "content_hash", ""):
        episode.content_hash = ""
    return True


def removable(plan: Plan) -> Path | None:
    """The local file to delete, when there is one and it is really there."""
    if not plan.ok or not plan.delete_path:
        return None
    path = Path(plan.delete_path)
    return path if path.is_file() else None
