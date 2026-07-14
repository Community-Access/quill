"""The Podcasts data model: folders, shows, episodes, and settings.

Folders, shows, episodes, and settings for the shipped feature (PRD
§5.84g); a few fields exist now purely as forward schema for later phases
(see ``docs/planning/podcasts.md``) so the on-disk shape never needs a
migration later: ``is_favorite`` for the planned Favorites virtual view,
``route_to_inbox`` / ``inbox_default_folder_id`` for the planned Inbox.
``position_ms`` (resume sync) is already wired up and in active use. The
still-forward-only fields are plain default-off values nothing reads or
writes yet, not a half-built UI. wx-free, strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class PodcastFolder:
    """Organizes shows. A show lives in exactly one folder (or none).
    Arbitrarily deep nesting via ``parent_folder_id`` (adjacency list)."""

    id: str
    name: str
    parent_folder_id: str | None = None


@dataclass(slots=True)
class PodcastSettings:
    """One global defaults record; a show's own ``PodcastShow.settings`` only
    stores the fields it overrides (``None`` = inherit the global value)."""

    playback_mode: str = "download"  # "stream" | "download"
    retention: str = "keep_all"  # "keep_all" | "keep_last_n" | "delete_after_play"
    retention_count: int = 5
    speed: float = 1.0
    download_root: str = ""  # "" = default (<data_dir>/podcasts)
    delete_files_on_remove: str = "ask"  # "ask" | "always" | "never" -- on Unsubscribe

    def to_dict(self) -> dict[str, object]:
        return {
            "playback_mode": self.playback_mode,
            "retention": self.retention,
            "retention_count": self.retention_count,
            "speed": self.speed,
            "download_root": self.download_root,
            "delete_files_on_remove": self.delete_files_on_remove,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> PodcastSettings:
        delete_policy = str(data.get("delete_files_on_remove", "ask"))
        return cls(
            playback_mode=str(data.get("playback_mode", "download")),
            retention=str(data.get("retention", "keep_all")),
            retention_count=_coerce_int(data.get("retention_count"), 5),
            speed=_coerce_float(data.get("speed"), 1.0),
            download_root=str(data.get("download_root", "")),
            delete_files_on_remove=delete_policy
            if delete_policy in ("ask", "always", "never")
            else "ask",
        )


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
    position_ms: int = 0  # resume position; syncs via QUILL Sync (guid-keyed)

    def to_dict(self) -> dict[str, object]:
        return {
            "guid": self.guid,
            "title": self.title,
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
            "position_ms": self.position_ms,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> PodcastEpisode | None:
        guid = str(data.get("guid", "")).strip()
        title = str(data.get("title", "")).strip()
        audio_url = str(data.get("audio_url", "")).strip()
        if not guid or not title or not audio_url:
            return None
        return cls(
            guid=guid,
            title=title,
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
            position_ms=_coerce_int(data.get("position_ms"), 0),
        )


@dataclass(slots=True)
class PodcastShow:
    """One subscribed feed, or one local (imported) show."""

    id: str
    title: str
    feed_url: str = ""  # "" for is_local shows
    homepage: str = ""
    artwork_url: str = ""
    is_local: bool = False
    folder_id: str | None = None
    paused: bool = False
    is_favorite: bool = False  # §10, not yet surfaced in the UI this phase
    route_to_inbox: bool = False  # §9, not yet surfaced in the UI this phase
    inbox_default_folder_id: str | None = None  # §9
    settings: PodcastSettings | None = None
    episodes: list[PodcastEpisode] = field(default_factory=list)

    def find_episode(self, guid: str) -> PodcastEpisode | None:
        for episode in self.episodes:
            if episode.guid == guid:
                return episode
        return None

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "title": self.title,
            "feed_url": self.feed_url,
            "homepage": self.homepage,
            "artwork_url": self.artwork_url,
            "is_local": self.is_local,
            "folder_id": self.folder_id,
            "paused": self.paused,
            "is_favorite": self.is_favorite,
            "route_to_inbox": self.route_to_inbox,
            "inbox_default_folder_id": self.inbox_default_folder_id,
            "settings": self.settings.to_dict() if self.settings is not None else None,
            "episodes": [e.to_dict() for e in self.episodes],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> PodcastShow | None:
        show_id = str(data.get("id", "")).strip()
        title = str(data.get("title", "")).strip()
        if not show_id or not title:
            return None
        settings_data = data.get("settings")
        settings = (
            PodcastSettings.from_dict(settings_data) if isinstance(settings_data, dict) else None
        )
        episodes_data = data.get("episodes")
        episodes: list[PodcastEpisode] = []
        for entry in episodes_data if isinstance(episodes_data, list) else []:
            if not isinstance(entry, dict):
                continue
            episode = PodcastEpisode.from_dict(entry)
            if episode is not None:
                episodes.append(episode)
        folder_id = data.get("folder_id")
        inbox_folder_id = data.get("inbox_default_folder_id")
        return cls(
            id=show_id,
            title=title,
            feed_url=str(data.get("feed_url", "")),
            homepage=str(data.get("homepage", "")),
            artwork_url=str(data.get("artwork_url", "")),
            is_local=bool(data.get("is_local", False)),
            folder_id=str(folder_id) if isinstance(folder_id, str) and folder_id else None,
            paused=bool(data.get("paused", False)),
            is_favorite=bool(data.get("is_favorite", False)),
            route_to_inbox=bool(data.get("route_to_inbox", False)),
            inbox_default_folder_id=(
                str(inbox_folder_id)
                if isinstance(inbox_folder_id, str) and inbox_folder_id
                else None
            ),
            settings=settings,
            episodes=episodes,
        )


def _coerce_int(value: object, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value)) if value.strip() else default
        except ValueError:
            return default
    return default


def _coerce_float(value: object, default: float) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value) if value.strip() else default
        except ValueError:
            return default
    return default
