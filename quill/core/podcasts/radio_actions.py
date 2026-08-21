"""What Quill Radio was *asked* to do to an episode, for Quill Cast to carry out.

:mod:`quill.core.podcasts.radio_listens` already carries what Radio *heard* --
positions and finished episodes. This is the other half: what the listener asked
for. From Radio's browse tree you can play a subscribed show's episode; until
now you could not mark it played, put it in Cast's queue, or send it to the
Inbox, so the same episode row offered different things depending on which app
you were looking at it in.

WHY THIS IS A SECOND FILE AND NOT A FIELD ON THE FIRST
------------------------------------------------------
It was going to be an ``action`` field on the existing record, and that would
have silently lost people's queue intent. ``radio_listens._read`` keeps any dict
carrying a non-empty ``audio`` key, and ``merge_radio_listens`` consumes every
record it can match to an episode, writing only the unmatched ones back. So a
record written by a new Radio as ``{"action": "queue_top", "position_ms": 0}``
and read by an **already-installed** Cast is matched, does nothing (the position
branch requires a non-zero position), and is then deleted.

That is the common case, not the edge one: Radio ships before Cast's next
release, so every Cast in the field is the old one.

A separate file has none of that problem. An old Cast never opens it, so the
records simply wait; Cast adds the reader in its own release and finds the
backlog intact. Positions and finished records keep flowing through
``radio-listens.json`` unchanged.

Same discipline as its sibling: Radio only ever appends, Cast merges at launch
when it is the sole holder of the file and consumes what it matched, unmatched
records are kept for a while because the episode may simply not be in Cast's
library yet, and nothing here ever raises -- a handoff is a courtesy and must
never cost somebody their playback.

wx-free, strict-typed. Losing this file costs at most one deferred instruction,
so its persistence class is cache.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from quill.core.podcasts.subscriptions import PodcastLibrary

_FILE_NAME = "radio-actions.json"

#: Mark the episode finished in Cast.
ACTION_PLAYED = "played"
#: Undo that. Present because "mark played" without "mark unplayed" is a trap.
ACTION_UNPLAYED = "unplayed"
#: Put it at the top of Cast's Play Queue -- "next, after this one".
ACTION_QUEUE_TOP = "queue_top"
#: Put it at the end of the queue -- "some time".
ACTION_QUEUE_BOTTOM = "queue_bottom"
#: File it into Cast's Inbox, the triage list.
ACTION_INBOX = "inbox"

ACTIONS: tuple[str, ...] = (
    ACTION_PLAYED,
    ACTION_UNPLAYED,
    ACTION_QUEUE_TOP,
    ACTION_QUEUE_BOTTOM,
    ACTION_INBOX,
)

#: What each one is called out loud, in Radio, where it is being asked for.
ACTION_LABELS: dict[str, str] = {
    ACTION_PLAYED: "Mark Played in QUILL Cast",
    ACTION_UNPLAYED: "Mark Unplayed in QUILL Cast",
    ACTION_QUEUE_TOP: "Play Next in QUILL Cast",
    ACTION_QUEUE_BOTTOM: "Add to QUILL Cast Queue",
    ACTION_INBOX: "Send to the QUILL Cast Inbox",
}

#: And what to say once it has been noted. Deliberately in the future tense and
#: honest about the delay: Cast applies these when it next opens, and a message
#: that implied it had already happened would be a small lie the listener would
#: find out about later.
ACTION_DONE: dict[str, str] = {
    ACTION_PLAYED: "Marked played. QUILL Cast will pick that up next time it opens.",
    ACTION_UNPLAYED: "Marked unplayed. QUILL Cast will pick that up next time it opens.",
    ACTION_QUEUE_TOP: "It will be next in the QUILL Cast queue.",
    ACTION_QUEUE_BOTTOM: "Added to the end of the QUILL Cast queue.",
    ACTION_INBOX: "Sent to the QUILL Cast Inbox.",
}

#: Newest records kept when the file is trimmed.
_MAX_RECORDS = 500

#: Unmatched records older than this are dropped at merge: if Cast has not
#: fetched the episode in a month, the instruction is stale.
_MAX_UNMATCHED_AGE_SECONDS = 30 * 24 * 3600


def _path(data_dir: Path) -> Path:
    return data_dir / _FILE_NAME


def _read(data_dir: Path) -> list[dict]:
    try:
        raw = json.loads(_path(data_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(raw, list):
        return []
    return [
        row
        for row in raw
        if isinstance(row, dict)
        and str(row.get("audio", "")).strip()
        and str(row.get("action", "")) in ACTIONS
    ]


def record_action(
    data_dir: Path,
    *,
    feed_url: str,
    audio_url: str,
    action: str,
    title: str = "",
) -> bool:
    """Note that the listener asked for *action* on this episode.

    One record per episode **and** action: asking twice is not two
    instructions, and the last word on "played or unplayed" is the one that
    counts. Queue and Inbox are kept separately from played state because they
    are not alternatives -- "mark it played" and "put it in the queue" can both
    be true, and collapsing them would silently drop one.

    Returns whether it was written. Never raises.
    """
    feed = (feed_url or "").strip()
    audio = (audio_url or "").strip()
    if not feed or not audio or action not in ACTIONS:
        return False
    try:
        from quill.core.storage import write_json_atomic

        # played/unplayed replace each other; the queue and inbox instructions
        # replace only themselves.
        family = _family(action)
        records = [
            row
            for row in _read(data_dir)
            if not (row.get("audio") == audio and _family(str(row.get("action", ""))) == family)
        ]
        records.append({
            "feed": feed,
            "audio": audio,
            "title": (title or "").strip(),
            "action": action,
            "at": time.time(),
        })
        write_json_atomic(_path(data_dir), records[-_MAX_RECORDS:])
    except Exception:  # noqa: BLE001 - a handoff is a courtesy, never a crash
        return False
    return True


def _family(action: str) -> str:
    """Which instructions supersede each other."""
    if action in (ACTION_PLAYED, ACTION_UNPLAYED):
        return "played"
    if action in (ACTION_QUEUE_TOP, ACTION_QUEUE_BOTTOM):
        return "queue"
    return action


def pending(data_dir: Path) -> list[dict]:
    """Every instruction still waiting, for a report or a test."""
    return _read(data_dir)


def merge_radio_actions(data_dir: Path, library: PodcastLibrary) -> tuple[int, list[str]]:
    """Carry out what Radio was asked for. Cast calls this at launch.

    Returns ``(applied, spoken)`` -- the count, and one sentence per distinct
    kind of thing that happened, so a launch can say "2 episodes are in your
    queue" rather than a bare number. Mutates *library* in place; the caller
    decides whether to save. Never raises.
    """
    try:
        records = _read(data_dir)
        if not records:
            return (0, [])
        applied = 0
        counts: dict[str, int] = {}
        kept: list[dict] = []
        now = time.time()
        for row in records:
            found = _find(library, str(row.get("feed", "")), str(row.get("audio", "")))
            if found is None:
                if now - float(row.get("at") or 0.0) <= _MAX_UNMATCHED_AGE_SECONDS:
                    kept.append(row)
                continue
            show, episode = found
            action = str(row.get("action", ""))
            if _apply(library, show, episode, action):
                applied += 1
                counts[action] = counts.get(action, 0) + 1
        from quill.core.storage import write_json_atomic

        write_json_atomic(_path(data_dir), kept)
        return (applied, _spoken(counts))
    except Exception:  # noqa: BLE001 - a failed merge must never block launch
        return (0, [])


def _spoken(counts: dict[str, int]) -> list[str]:
    lines: list[str] = []
    played = counts.get(ACTION_PLAYED, 0)
    if played:
        lines.append(f"{played} episode{'' if played == 1 else 's'} marked played in Quill Radio.")
    unplayed = counts.get(ACTION_UNPLAYED, 0)
    if unplayed:
        lines.append(
            f"{unplayed} episode{'' if unplayed == 1 else 's'} marked unplayed in Quill Radio."
        )
    queued = counts.get(ACTION_QUEUE_TOP, 0) + counts.get(ACTION_QUEUE_BOTTOM, 0)
    if queued:
        lines.append(f"{queued} episode{'' if queued == 1 else 's'} added to your queue.")
    inbox = counts.get(ACTION_INBOX, 0)
    if inbox:
        lines.append(f"{inbox} episode{'' if inbox == 1 else 's'} sent to your Inbox.")
    return lines


def _find(library: PodcastLibrary, feed: str, audio: str) -> tuple[Any, Any] | None:
    """The (show, episode) a record names, or ``None``.

    By feed URL and audio URL, which is what a Radio browse row carries. The
    same lookup ``radio_listens`` does, kept here rather than imported so a
    change to one file's matching cannot quietly alter the other's.
    """
    wanted_feed = (feed or "").strip()
    wanted_audio = (audio or "").strip()
    if not wanted_audio:
        return None
    for show in getattr(library, "shows", []) or []:
        if wanted_feed and str(getattr(show, "feed_url", "") or "").strip() != wanted_feed:
            continue
        for episode in getattr(show, "episodes", []) or []:
            if str(getattr(episode, "audio_url", "") or "").strip() == wanted_audio:
                return (show, episode)
    return None


def _apply(library: PodcastLibrary, show: Any, episode: Any, action: str) -> bool:
    """One instruction, against the library. Returns whether anything changed."""
    from quill.core.podcasts import position_sync

    if action == ACTION_PLAYED:
        if getattr(episode, "played", False):
            return False
        position_sync.mark_played(episode)
        return True
    if action == ACTION_UNPLAYED:
        if not getattr(episode, "played", False):
            return False
        position_sync.mark_played(episode, False)
        return True
    show_id = str(getattr(show, "id", "") or "")
    guid = str(getattr(episode, "guid", "") or "")
    if action == ACTION_QUEUE_TOP:
        from quill.core.podcasts import queue as queue_module

        # play_next rather than add-then-move: it keeps an already-queued
        # episode's original added_at, so reordering the queue does not
        # quietly reset that episode's expiry clock.
        queue_module.play_next(library, show_id, guid)
        return True
    if action == ACTION_QUEUE_BOTTOM:
        from quill.core.podcasts import queue as queue_module

        return bool(queue_module.add_to_queue(library, show_id, guid))
    if action == ACTION_INBOX:
        from quill.core.podcasts import inbox as inbox_module

        # None, not "": None files it at the Inbox top level, which is what
        # "send it to the Inbox" means when no folder was named. An empty
        # string is the *explicit unfile* marker and would mean something else.
        inbox_module.file_episode(library, show, episode, None)
        return True
    return False
