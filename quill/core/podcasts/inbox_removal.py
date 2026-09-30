"""Remove from Inbox, and what that does to the download (R3).

Earshot shipped a fix for this exact seam, and the seam is worth stating because
it is not obvious: removing an episode from the Inbox is a **triage** decision
("I have dealt with this, stop showing it to me"), and deleting a downloaded file
is a **storage** decision. They are different, and a listener who has said
"delete downloads when done" has said something about storage that this verb has
to honour -- otherwise the one action that means "I am finished with this" is the
one action that leaves a file behind forever, and a library quietly fills up with
episodes nobody will ever open.

So: remove from the Inbox, and if that show's settings say downloads go when
you are done with them, the download goes too. If they do not, it stays.

**Why this needs its own marker, and may not reuse the cap's.** The Inbox already
has one way of taking an episode out -- ``TRIMMED_MARKER``, written by
``trim_inbox`` when a cap is exceeded -- and reusing it here would be wrong in a
way that only shows up weeks later: ``resurface_republished`` deliberately clears
that marker when a publisher re-issues an episode, because a cap-trimmed episode
that has been re-cut is, to the listener, new again. An episode somebody
*dismissed by hand* is not. It would come back, and it would come back as though
Cast had forgotten the decision.

So there are two markers, and one rule that tells them apart: the cap's is
reversible by the app, the listener's is reversible only by the listener
(:func:`restore`).

Nothing here deletes a file. The paths come back in the result and the caller
removes them, so the "what gets deleted" decision is readable in one place and
testable without a filesystem.

wx-free, strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from quill.core.podcasts.inbox import REMOVED_MARKER, inbox_key
from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary

__all__ = ["Removal", "is_removed", "remove_from_inbox", "restore"]


@dataclass(slots=True)
class Removal:
    """What a removal did, and what the caller still has to do about it."""

    removed: int = 0
    #: Files to delete, because the shows they belong to say downloads go when
    #: you are done. The caller deletes them; this module only decides.
    delete_paths: list[str] = field(default_factory=list)
    #: Episodes that were not in the Inbox to begin with, named so the caller
    #: can be honest rather than reporting a removal that did not happen.
    skipped: int = 0

    def announcement(self) -> str:
        """What to say. Counts only, and only when there is a count worth saying.

        A single removal says nothing: the row disappearing from a list the
        screen reader is already reading *is* the feedback, and announcing it
        would be GATE-13's textbook case. Two or more is a fact the listener
        cannot get from the list, because they cannot see how much shorter it
        got.
        """
        if self.removed < 2:
            return ""
        freed = len(self.delete_paths)
        if freed:
            return (
                f"{self.removed} episodes removed from the Inbox, "
                f"{freed} download{'' if freed == 1 else 's'} deleted"
            )
        return f"{self.removed} episodes removed from the Inbox"


def is_removed(library: PodcastLibrary, show: PodcastShow, episode: PodcastEpisode) -> bool:
    """Whether the *listener* took this episode out of the Inbox."""
    return library.inbox_assignments.get(inbox_key(show.id, episode.guid)) == REMOVED_MARKER


def remove_from_inbox(
    library: PodcastLibrary, pairs: list[tuple[PodcastShow, PodcastEpisode]]
) -> Removal:
    """Take *pairs* out of the Inbox; collect the downloads that should go with them.

    The per-show setting is read through ``effective_settings``, so a show that
    overrides the library default gets its own answer -- somebody who keeps one
    podcast's episodes forever and clears everything else has said exactly that,
    and a library-wide read would ignore half of it.

    Nothing is marked played. "I have dealt with this" and "I listened to this"
    are different claims, and conflating them would corrupt the listening
    statistics with episodes nobody heard.
    """
    from quill.core.podcasts.retention import wants_delete_after_play

    result = Removal()
    for show, episode in pairs:
        key = inbox_key(show.id, episode.guid)
        if library.inbox_assignments.get(key) == REMOVED_MARKER:
            result.skipped += 1
            continue
        library.inbox_assignments[key] = REMOVED_MARKER
        result.removed += 1
        if not episode.downloaded_path:
            continue
        if wants_delete_after_play(library.effective_settings(show)):
            result.delete_paths.append(episode.downloaded_path)
            # Cleared here, with the decision, rather than by the caller after a
            # successful unlink: a record that still claims a file which has
            # been deleted offers Play and fails, and "the file is gone" is a
            # better state than "the file is gone and Cast disagrees".
            episode.downloaded_path = ""
    return result


def restore(library: PodcastLibrary, show: PodcastShow, episode: PodcastEpisode) -> bool:
    """Put a hand-removed episode back in the Inbox; True when it was removed.

    The undo exists because the removal is a judgement and judgements are made
    quickly -- and because a listener who removed thirty rows and then realised
    the filter was wrong has no other route back. A download that was deleted is
    not restored, and cannot be; the episode returns and will download again.
    """
    key = inbox_key(show.id, episode.guid)
    if library.inbox_assignments.get(key) != REMOVED_MARKER:
        return False
    del library.inbox_assignments[key]
    return True
