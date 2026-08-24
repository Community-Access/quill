"""What Quill Radio heard, for Quill Cast to catch up on.

Quill Radio can play a subscribed show's episodes (Browse Stations >
Podcasts > Subscriptions), but the rich side of podcasting -- the Inbox,
Continue Listening, played state -- lives in Quill Cast. Without this file,
half an episode heard over lunch in Radio leaves Cast none the wiser: the
episode still presents as brand new. This is the small pipe that fixes that.

The shape is a *handoff*, deliberately, rather than Radio writing into
Cast's stores: both apps load-and-save ``podcasts.json`` wholesale, so a
Radio write while Cast is open would be a last-writer-wins clobber waiting
to happen (the same reason weather monitoring hands off between apps
instead of sharing a store). Radio only ever appends records here;
Cast merges them into its own library at launch, when it is the one
holder of that file, and consumes what it matched.

Records that match nothing are kept for a while -- the episode may simply
not have been fetched into Cast's library yet -- and dropped when stale,
so the file cannot grow forever on a feed Cast never refreshes.

wx-free, strict-typed. Loss of this file is harmless (worst case Cast does
not learn about one listening session), so the persistence class is cache.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from quill.core.podcasts import position_sync
from quill.core.podcasts.cross_app_resume import Place as CrossAppPlace
from quill.core.podcasts.models import PodcastEpisode

if TYPE_CHECKING:
    from quill.core.podcasts.subscriptions import PodcastLibrary

#: ``RadioStation.source`` values that mean "a podcast episode played from a
#: publisher's feed" -- the rows whose positions are worth telling Cast about.
PODCAST_EPISODE_SOURCES = frozenset({"Apple Podcasts", "Subscribed Podcasts"})

_FILE_NAME = "radio-listens.json"

#: Newest records kept when the file is trimmed. A record is one heard
#: episode, so hundreds is weeks of listening.
_MAX_RECORDS = 500

#: Unmatched records older than this are dropped at merge: if Cast has not
#: fetched the episode in a month, the position is stale anyway.
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
    return [row for row in raw if isinstance(row, dict) and str(row.get("audio", "")).strip()]


def record_listen(
    data_dir: Path,
    *,
    feed_url: str,
    audio_url: str,
    title: str = "",
    position_ms: int = 0,
    finished: bool = False,
    app: str = "radio",
) -> None:
    """Note that *app* reached *position_ms* in (or finished) an episode.

    One record per episode: a later save for the same audio URL replaces the
    earlier one, so the file holds the latest word on each episode rather
    than a keystroke log. Best effort; never raises -- losing a handoff
    record must never cost the listener their playback.

    *app* was added with cross-app resume (11.11), which turned this from a
    one-way handoff into a place both apps write: Cast records here too, so
    an episode paused in Cast picks up in Radio. The field is what lets the
    resume say *which* app the place came from, which is the difference
    between an explained jump and a mysterious one.
    """
    feed = (feed_url or "").strip()
    audio = (audio_url or "").strip()
    if not feed or not audio:
        return
    try:
        from quill.core.storage import write_json_atomic

        records = [row for row in _read(data_dir) if row.get("audio") != audio]
        records.append({
            "feed": feed,
            "audio": audio,
            "title": (title or "").strip(),
            "position_ms": max(0, int(position_ms)),
            "finished": bool(finished),
            "at": time.time(),
            "app": (app or "radio").strip() or "radio",
        })
        write_json_atomic(_path(data_dir), records[-_MAX_RECORDS:])
    except Exception:  # noqa: BLE001 - a handoff is a courtesy, never a crash
        return


def merge_radio_listens(data_dir: Path, library: PodcastLibrary) -> tuple[int, int]:
    """Fold Radio's listening records into *library* (Cast calls this).

    Returns ``(episodes_updated, episodes_finished)``. Mutates *library* in
    place; the caller decides whether to save (skip when both counts are
    zero). Matched records are consumed; young unmatched ones are kept for a
    later merge, stale ones dropped. Never raises.
    """
    try:
        records = _read(data_dir)
        if not records:
            return (0, 0)
        updated = finished_count = 0
        kept: list[dict] = []
        now = time.time()
        for row in records:
            episode = _find_episode(library, str(row.get("feed", "")), str(row.get("audio", "")))
            if episode is None:
                if now - float(row.get("at") or 0.0) <= _MAX_UNMATCHED_AGE_SECONDS:
                    kept.append(row)
                continue
            if bool(row.get("finished")):
                # Cast's own convention for a finished episode: played, and
                # the place cleared so replaying starts at the top.
                if not episode.played or episode.position_ms:
                    position_sync.mark_played(episode)
                    updated += 1
                    finished_count += 1
            else:
                position = max(0, int(row.get("position_ms") or 0))
                if position and position != episode.position_ms and not episode.played:
                    position_sync.remember_position(episode, position)
                    updated += 1
        from quill.core.storage import write_json_atomic

        write_json_atomic(_path(data_dir), kept)
        return (updated, finished_count)
    except Exception:  # noqa: BLE001 - a failed merge must never block launch
        return (0, 0)


def finished_audio_urls(data_dir: Path) -> frozenset[str]:
    """Audio URLs Radio has heard to the end, still awaiting Cast's merge.

    Read by Radio's own unheard badges (browse_libraries) so an episode
    finished five minutes ago stops counting as unheard *now*, without Radio
    ever writing the shared library -- the records here are the handoff, and
    Cast consumes them at its next launch, at which point the library itself
    says played and this set says nothing. Never raises.
    """
    try:
        return frozenset(
            str(row.get("audio", "")) for row in _read(data_dir) if bool(row.get("finished"))
        )
    except Exception:  # noqa: BLE001 - an empty overlay is the safe answer
        return frozenset()


def merge_summary(updated: int, finished: int) -> str:
    """What to announce after a merge, or ``""`` when there is nothing to say."""
    if not updated:
        return ""
    if finished == updated:
        plural = "s" if finished != 1 else ""
        return f"Caught up from Quill Radio: {finished} episode{plural} finished."
    plural = "s" if updated != 1 else ""
    return f"Caught up from Quill Radio: {updated} episode{plural} updated."


def _find_episode(library: PodcastLibrary, feed_url: str, audio_url: str) -> PodcastEpisode | None:
    feed = (feed_url or "").strip()
    audio = (audio_url or "").strip()
    if not feed or not audio:
        return None
    show = library.find_show_by_feed_url(feed)
    if show is None:
        return None
    for episode in show.episodes:
        if episode.audio_url == audio:
            return episode
    return None


@dataclass(frozen=True, slots=True)
class EpisodePlaybackProfile:
    """What the shared library knows that should shape playing one episode.

    Read by Quill Radio when a subscription episode starts (the reverse
    direction of the handoff above -- and read-only on purpose: positions
    written FROM Radio still travel through the append-only records so a
    Radio write can never clobber Cast's open library).
    """

    #: Where Quill Cast (or a merged listen) left this episode. 0 = start.
    position_ms: int = 0
    #: The show's effective playback speed (its own setting, or the library
    #: default). 1.0 = normal.
    speed: float = 1.0
    #: The episode's Podcasting 2.0 chapters file, when the feed declared one.
    chapters_url: str = ""
    #: Ready ``Authorization`` header for this show's private resources
    #: (same-host rule applied by feed_auth), or "".
    chapters_auth_header: str = ""


def episode_playback_profile(
    data_dir: Path, *, feed_url: str, audio_url: str
) -> EpisodePlaybackProfile:
    """The library's knowledge about one subscribed episode, or defaults.

    Never raises, and answers defaults for an unfollowed feed -- an Apple
    row played before subscribing is an ordinary recording, not an error.
    """
    try:
        from quill.core.podcasts import feed_auth
        from quill.core.podcasts.subscriptions import load_library

        library = load_library(data_dir)
        show = library.find_show_by_feed_url((feed_url or "").strip())
        if show is None:
            return EpisodePlaybackProfile()
        episode = _find_episode(library, feed_url, audio_url)
        chapters_url = str(getattr(episode, "chapters_url", "") or "")
        return EpisodePlaybackProfile(
            position_ms=max(0, int(getattr(episode, "position_ms", 0) or 0)),
            speed=float(library.effective_settings(show).speed or 1.0),
            chapters_url=chapters_url,
            chapters_auth_header=(
                feed_auth.auth_header_for_url(show, chapters_url) if chapters_url else ""
            ),
        )
    except Exception:  # noqa: BLE001 - a broken profile must never break playback
        return EpisodePlaybackProfile()


def feed_credentials(data_dir: Path, feed_url: str) -> tuple[str, str]:
    """``(username, password)`` for fetching *feed_url* itself, or ``("", "")``.

    The same same-host gate Cast applies (feed_auth.auth_for_url against the
    feed's own address), so a private feed that works in Cast lists its
    episodes in Radio instead of reading as broken.
    """
    try:
        from quill.core.podcasts import feed_auth
        from quill.core.podcasts.subscriptions import load_library

        show = load_library(data_dir).find_show_by_feed_url((feed_url or "").strip())
        if show is None:
            return ("", "")
        return feed_auth.auth_for_url(show, show.feed_url)
    except Exception:  # noqa: BLE001 - no credentials is the safe answer
        return ("", "")


# -- per-show speed, remembered on Radio's side --------------------------------
# A speed the listener sets IN RADIO while a show's episode plays. Kept in
# Radio's own small store rather than written into the shared library, for the
# same clobber reason as the listen records above; Cast's own per-show speed
# stays Cast's, and Radio's remembered speed wins locally when both exist.

_SPEEDS_FILE = "radio-show-speeds.json"

#: Shows kept when the speeds file is trimmed; a speed is one line, so this is
#: effectively "every show anyone actually adjusts".
_MAX_SPEEDS = 200


def _speeds_path(data_dir: Path) -> Path:
    return data_dir / _SPEEDS_FILE


def _read_speeds(data_dir: Path) -> dict[str, float]:
    try:
        raw = json.loads(_speeds_path(data_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(raw, dict):
        return {}
    speeds: dict[str, float] = {}
    for key, value in raw.items():
        try:
            speeds[str(key)] = float(value)
        except (TypeError, ValueError):
            continue
    return speeds


def remember_show_speed(data_dir: Path, feed_url: str, speed: float) -> None:
    """Persist the speed *feed_url*'s episodes should play at in Radio.

    ``speed == 1.0`` forgets the entry -- normal is the default, not a
    preference. Never raises: losing a speed must never cost a playback.
    """
    feed = (feed_url or "").strip()
    if not feed:
        return
    try:
        speeds = _read_speeds(data_dir)
        if float(speed) == 1.0:
            speeds.pop(feed, None)
        else:
            speeds[feed] = float(speed)
        if len(speeds) > _MAX_SPEEDS:
            for stale in list(speeds)[: len(speeds) - _MAX_SPEEDS]:
                speeds.pop(stale, None)
        from quill.core.storage import write_json_atomic

        write_json_atomic(_speeds_path(data_dir), speeds)
    except Exception:  # noqa: BLE001 - best effort, never fatal
        return


def remembered_show_speed(data_dir: Path, feed_url: str) -> float:
    """The speed Radio remembered for *feed_url*, or 0.0 when none is set."""
    try:
        return float(_read_speeds(data_dir).get((feed_url or "").strip(), 0.0))
    except Exception:  # noqa: BLE001 - no memory is the safe answer
        return 0.0


def latest_place(data_dir: Path, audio_url: str) -> CrossAppPlace | None:
    """The shared place for *audio_url*, or ``None`` (cross-app resume, 11.11).

    The read half of the store: either app asks this before it starts an
    episode, and :mod:`quill.core.podcasts.cross_app_resume` decides whether
    what comes back beats what the app already knows. Never raises -- a
    missing or unreadable file simply means "no shared opinion".
    """
    audio = (audio_url or "").strip()
    if not audio:
        return None
    for row in reversed(_read(data_dir)):
        if row.get("audio") != audio:
            continue
        try:
            return CrossAppPlace(
                position_ms=max(0, int(row.get("position_ms", 0) or 0)),
                updated_at=float(row.get("at", 0.0) or 0.0),
                finished=bool(row.get("finished", False)),
                app=str(row.get("app", "radio") or "radio"),
            )
        except (TypeError, ValueError):
            return None
    return None
