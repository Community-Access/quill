"""Personal Audio: the listener's own files, as a place rather than a fake podcast.

Cast could already import a file -- Add Local Podcast made a show with
``is_local`` set and copied the audio into its own folder. What it had no concept
of was **the collection**: a listener with four imported lectures had four
one-episode "podcasts" scattered through a library of subscriptions, and no way to
ask "what have I added?"

This module is that collection, modelled the way Earshot's Personal Audio PRD
settles it (``docs/personal-audio-prd.md`` in the Earshot repository), with the
naming it insists on:

* **Personal Audio** is the category. Never "side-loaded", never "file-backed
  episode", and never "subscription" -- an imported file is not a feed, and saying
  so confuses the one thing the listener needs to be certain of, which is that
  their original file is still where they left it.
* Items are listed **newest added first**, because the reason somebody opens this
  place is almost always the thing they just put in it.
* An item stays in Personal Audio whatever folder it is also filed in. Folder
  membership is *organisational, not ownership* -- the PRD's words -- and the
  reason is that a listener who files something and then cannot find it where they
  put it has lost it.

Two things here that the PRD calls for and Cast had nowhere: **an unavailable
state**, for when the managed copy has gone missing, and **orphan reconciliation**,
for a file left behind by an import that failed halfway. Both exist so the answer
to "where is my recording" is never silence.

One deliberate difference, allowed by the parity principle that Cast should not
copy a limit: Earshot's Phase 2 defers queue and folder support for Personal
Audio. Cast has both already, because a local show is an ordinary show to the rest
of the app, and removing that to match would be a downgrade.

wx-free, strict-typed. The only I/O is the existence check, which is the whole
point of :func:`unavailable_items`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = [
    "CATEGORY",
    "NAMESPACE",
    "Item",
    "content_id",
    "count",
    "empty_state",
    "items",
    "node_label",
    "orphan_files",
    "unavailable_items",
]

#: What the category is called wherever a listener meets it. One spelling, used by
#: the tree node, the empty state and every announcement.
CATEGORY = "Personal Audio"

#: The prefix that makes an imported item's identity unmistakable in any shared
#: store -- a queue slot, a restoration record, a listening place. Earshot uses the
#: same one, so the two apps' records read alike to a person debugging them.
NAMESPACE = "personal-audio:"


@dataclass(frozen=True, slots=True)
class Item:
    """One imported file, as the Personal Audio list shows it."""

    show: Any
    episode: Any

    @property
    def title(self) -> str:
        return str(getattr(self.episode, "title", "") or "Untitled")

    @property
    def artist(self) -> str:
        """What the file said about who made it, or ``""``.

        Held in the episode's description by the importer, because that is the
        field a cross-show row already reads as the second half of
        "title -- podcast", and an artist is the nearest thing a loose file has to
        a show.
        """
        return str(getattr(self.episode, "description", "") or "")

    @property
    def path(self) -> str:
        return str(getattr(self.episode, "downloaded_path", "") or "")

    @property
    def available(self) -> bool:
        """Whether the copy Cast made is still on disk."""
        path = self.path
        return bool(path) and Path(path).is_file()

    def row(self) -> str:
        """The row, as it reads.

        Title first, because that is what the list is navigated by. State last,
        with unavailability outranking played state: it is the only part of a row
        that changes what the listener can do next.
        """
        parts = [self.title]
        if self.artist:
            parts.append(self.artist)
        if not self.available:
            parts.append("Unavailable, the file is missing")
        elif getattr(self.episode, "played", False):
            parts.append("Played")
        else:
            parts.append("Unplayed")
        return " -- ".join(parts)


def content_id(show: Any, episode: Any) -> str:
    """A stable, namespaced id for a shared store.

    Never the display filename, which a later rename would break, and never a feed
    URL plus GUID, which an imported file does not have and must not be given --
    pretending it has a feed is how "is this a podcast?" stops having a reliable
    answer.
    """
    return f"{NAMESPACE}{getattr(show, 'id', '')}/{getattr(episode, 'guid', '')}"


def _is_personal(show: Any) -> bool:
    return bool(getattr(show, "is_local", False))


def items(library: Any) -> list[Item]:
    """Every imported file, newest added first.

    Ordered by the episode's published stamp, which the importer sets to the
    moment of import: an imported file has no publication date of its own, and
    taking one from the file's own timestamp would sort a 2009 recording to the
    bottom of a list somebody filled this morning.
    """
    found: list[Item] = []
    for show in getattr(library, "shows", []) or []:
        if not _is_personal(show):
            continue
        for episode in getattr(show, "episodes", []) or []:
            found.append(Item(show=show, episode=episode))
    found.sort(key=lambda item: str(getattr(item.episode, "published", "") or ""), reverse=True)
    return found


def count(library: Any) -> int:
    return len(items(library))


def node_label(library: Any) -> str:
    """``"Personal Audio (4)"``, or the bare name when there is nothing in it.

    The count is in the label rather than announced, for the reason every count on
    a tree node is: the reader says the node when the listener arrives at it, so
    the number is free at exactly the moment it is wanted.
    """
    total = count(library)
    return f"{CATEGORY} ({total})" if total else CATEGORY


def empty_state(library: Any) -> str:
    """What the list says when there is nothing in it yet.

    A sentence with the action in it, because an empty list that only says "empty"
    leaves a keyboard listener nowhere to go.
    """
    if count(library):
        return ""
    return (
        "No personal audio yet. Use Add Local Podcast to bring in a recording, a "
        "lecture or an audiobook; the original file stays where it is."
    )


def unavailable_items(library: Any) -> list[Item]:
    """Items whose managed copy has gone missing.

    Reported rather than repaired, and their progress deliberately **not** reset: a
    file that vanished because a drive was unplugged is a file that will come back,
    and clearing the position would lose the one thing the listener cannot recover.
    The PRD's rule exactly -- mark unavailable, offer removal or re-import, never
    silently reset.
    """
    return [item for item in items(library) if not item.available]


def orphan_files(library: Any, folder: Path) -> list[Path]:
    """Managed files under *folder* that no item refers to.

    An import that failed between copying the bytes and saving the record leaves
    one of these, and nothing would ever look at it again. Returned rather than
    deleted, so the caller decides -- and so a mistake in this function cannot
    delete somebody's audio.
    """
    if not folder.is_dir():
        return []
    known = {Path(item.path).resolve() for item in items(library) if item.path}
    found: list[Path] = []
    for path in sorted(folder.rglob("*")):
        if path.is_file() and path.resolve() not in known:
            found.append(path)
    return found
