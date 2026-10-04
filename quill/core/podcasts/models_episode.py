"""One episode: the record, and everything the feed said about it.

Extracted from :mod:`quill.core.podcasts.models` under GATE-11 (extract, never
rebaseline), the same way the settings record, the queue item and the playlists
were. ``models.py`` sat exactly on its budget, and the episode is the record
that grows: a feed carries more about an item than any one release has got
round to reading, and each release reads a little more of it.

The split is not only bookkeeping. An episode is the one record here whose
fields come from **two different places** and must never be confused:

* **What the feed said** -- title, audio, published, duration, description,
  chapter and transcript links, the season and episode numbers, the
  Podcasting 2.0 tags. A refresh overwrites these, because the publisher owns
  them.
* **What you did** -- played, resume position, the downloaded file, a
  stream-or-download override. A refresh never touches these, because you own
  them, and a feed that republishes an old guid with new text must not reset
  what you already did with that episode
  (:func:`quill.core.podcasts.subscriptions.merge_episodes`).

wx-free, strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from quill.core.podcasts.models_queue import coerce_int as _coerce_int
from quill.core.podcasts.namespace_tags import NamespaceTags


def _episode_speed(value: object) -> float:
    """A stored per-file speed, or 0.0 for "inherit the show's".

    Through the shared scale, so a hand-edited 99 becomes the fastest speed the
    app has rather than something the engine will refuse.
    """
    from quill.core.podcasts.speed_scale import clamp_speed

    try:
        speed = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
    return 0.0 if speed <= 0 else clamp_speed(speed)


@dataclass(slots=True)
class PodcastEpisode:
    """One episode of a subscribed (or local) show."""

    guid: str
    title: str
    audio_url: str
    published: str = ""
    duration_seconds: int = 0
    description: str = ""
    chapters_url: str = ""
    transcript_url: str = ""
    transcript_type: str = ""
    downloaded_path: str = ""
    mode_override: str = ""  # "" | "stream" | "download"
    played: bool = False
    #: Whether this episode's intro has already been skipped once (R20). A
    #: separate fact from ``played``: an episode can be unplayed and already
    #: intro-skipped, which is exactly the "started it, went back, started again"
    #: case the flag exists for. Stored, because an intro skipped last night must
    #: not be skipped again this morning.
    intro_skipped: bool = False
    #: SHA-256 of the imported file's contents, for Personal Audio duplicate
    #: detection (R10). Only ever set on an imported item; "" everywhere else. A
    #: filename is never a duplicate, so the bytes are the test.
    content_hash: str = ""
    #: The filename the listener's own file had when it was imported, kept as a
    #: secondary detail for support and for a future rename action. The managed
    #: copy's name is Cast's business; this is what the listener will call it.
    source_filename: str = ""
    #: The feed's own title when the listener renamed the episode (ear.md R8);
    #: "" when not renamed. A refresh updates this, never the listener's name.
    feed_title: str = ""
    #: This file's own playback speed (R12). 0.0 means inherit the show's, which
    #: is what every subscribed episode does; an imported file can want its own --
    #: a lecture at 1.5x and an audiobook at 1.0x, in the same "show".
    speed_override: float = 0.0
    position_ms: int = 0  # resume position; syncs via QUILL Sync (guid-keyed)
    #: When the place above was last decided. RFC 3339 UTC ending ``Z``, so
    #: plain string comparison sorts it and the merge needs no date parsing.
    #: Merging positions is last-write-wins, never furthest-wins -- see
    #: ``core/podcasts/position_sync.py`` -- so without this field there is
    #: nothing to merge on and a place cannot travel between devices at all.
    position_updated_at: str = ""
    #: The device the place above came from, when it came from another one
    #: through Listening Places: "Jeff's iPhone", or "Earshot" when the file
    #: names only its app (ear.md B1). "" when the place was decided here.
    last_played_on: str = ""
    #: ``itunes:season`` and ``itunes:episode``; 0 = the feed did not say.
    #:
    #: Read because serial fiction is meant to be heard **in order** and its
    #: published dates are frequently wrong -- bulk-imported, re-stamped on a
    #: feed rebuild, or simply absent. Where a publisher numbered their
    #: episodes, that numbering is the only reliable order there is, and Cast
    #: was throwing it away. Sorting uses it (``sorting.py``,
    #: ``season_episode``) and the row can say it
    #: (``row_speech.py``); both treat 0 as "unknown" rather than as "zero",
    #: because an unnumbered episode is not episode zero.
    season: int = 0
    episode_number: int = 0
    #: ``itunes:episodeType``: "full", "trailer" or "bonus". Feed-supplied, and
    #: worth keeping because it is the publisher's own answer to the question
    #: Episode Filters exists to ask -- a listener who does not want trailers
    #: can say so once, in the publisher's vocabulary, instead of guessing at a
    #: title pattern.
    episode_type: str = ""
    #: Podcasting 2.0 tags read from this item: who is on it, the moments the
    #: publisher marked, alternate audio, where it is about. Serialised only
    #: when non-empty, so feeds that publish none of it cost nothing.
    tags: NamespaceTags = field(default_factory=NamespaceTags)

    def to_dict(self) -> dict[str, object]:
        return {
            "guid": self.guid,
            "title": self.title,
            **({"feed_title": self.feed_title} if self.feed_title else {}),
            "audio_url": self.audio_url,
            "published": self.published,
            "duration_seconds": self.duration_seconds,
            "description": self.description,
            "chapters_url": self.chapters_url,
            "transcript_url": self.transcript_url,
            "transcript_type": self.transcript_type,
            "downloaded_path": self.downloaded_path,
            "mode_override": self.mode_override,
            "played": self.played,
            "intro_skipped": self.intro_skipped,
            "content_hash": self.content_hash,
            "source_filename": self.source_filename,
            "speed_override": self.speed_override,
            "position_ms": self.position_ms,
            # The three below are written only when the feed said something,
            # so a library of four thousand episodes from feeds that publish
            # none of it is not four thousand lines longer than it was.
            **({"season": self.season} if self.season else {}),
            **({"episode_number": self.episode_number} if self.episode_number else {}),
            **({"episode_type": self.episode_type} if self.episode_type else {}),
            **(
                {"position_updated_at": self.position_updated_at}
                if self.position_updated_at
                else {}
            ),
            **({"last_played_on": self.last_played_on} if self.last_played_on else {}),
            **({"tags": self.tags.to_dict()} if not self.tags.is_empty else {}),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> PodcastEpisode | None:
        guid = str(data.get("guid", "")).strip()
        title = str(data.get("title", "")).strip()
        audio_url = str(data.get("audio_url", "")).strip()
        downloaded_path = str(data.get("downloaded_path", "")).strip()
        # An episode needs *somewhere its audio is*, and for an imported file that
        # is a path, not a URL. Requiring audio_url silently dropped every Personal
        # Audio item on load: Add Local Podcast sets audio_url="" and
        # downloaded_path to the managed copy, so a listener imported a lecture,
        # played it, restarted Cast, and found an empty show and an orphaned file on
        # disk. The show survived because PodcastShow.from_dict has no such rule;
        # only its episodes vanished, which is why it read as "my recording
        # disappeared" rather than as a load failure.
        if not guid or not title or not (audio_url or downloaded_path):
            return None
        return cls(
            guid=guid,
            title=title,
            feed_title=str(data.get("feed_title", "") or ""),
            audio_url=audio_url,
            published=str(data.get("published", "")),
            duration_seconds=_coerce_int(data.get("duration_seconds"), 0),
            description=str(data.get("description", "")),
            chapters_url=str(data.get("chapters_url", "")),
            transcript_url=str(data.get("transcript_url", "")),
            transcript_type=str(data.get("transcript_type", "")),
            downloaded_path=str(data.get("downloaded_path", "")),
            mode_override=str(data.get("mode_override", "")),
            played=bool(data.get("played", False)),
            intro_skipped=bool(data.get("intro_skipped", False)),
            content_hash=str(data.get("content_hash", "") or ""),
            source_filename=str(data.get("source_filename", "") or ""),
            speed_override=_episode_speed(data.get("speed_override")),
            position_ms=_coerce_int(data.get("position_ms"), 0),
            position_updated_at=str(data.get("position_updated_at", "")),
            last_played_on=str(data.get("last_played_on", "") or "")[:80],
            season=max(0, _coerce_int(data.get("season"), 0)),
            episode_number=max(0, _coerce_int(data.get("episode_number"), 0)),
            episode_type=str(data.get("episode_type", "")).strip().lower(),
            tags=NamespaceTags.from_dict(data.get("tags")),
        )

    # -- what the numbering means --------------------------------------------

    @property
    def is_numbered(self) -> bool:
        """Whether the publisher numbered this episode at all."""
        return self.episode_number > 0 or self.season > 0

    def number_label(self) -> str:
        """``"S2 E14"``, ``"Episode 14"``, or ``""`` when it is not numbered.

        Spoken as well as shown, so it is spelled out rather than punctuated:
        a screen reader reads "S2E14" as a word, and the point of the label is
        that somebody can hear which episode it is.
        """
        if self.season and self.episode_number:
            return f"Season {self.season}, episode {self.episode_number}"
        if self.episode_number:
            return f"Episode {self.episode_number}"
        if self.season:
            return f"Season {self.season}"
        return ""


__all__ = ["PodcastEpisode"]
