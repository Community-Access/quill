"""Filtering for podcast episode and show lists, and a cross-library
"Search Everywhere" -- pure functions, wx-free.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary

EPISODE_FILTER_MODES = ("all", "unplayed", "played", "downloaded", "not_downloaded")
SHOW_FILTER_MODES = ("all", "favorites_only", "has_unplayed")


def filter_episodes(episodes: list[PodcastEpisode], mode: str) -> list[PodcastEpisode]:
    """Return only the episodes matching *mode* (unrecognized modes behave
    like ``"all"``)."""
    if mode == "unplayed":
        return [e for e in episodes if not e.played]
    if mode == "played":
        return [e for e in episodes if e.played]
    if mode == "downloaded":
        return [e for e in episodes if e.downloaded_path]
    if mode == "not_downloaded":
        return [e for e in episodes if not e.downloaded_path]
    return list(episodes)


def filter_shows(shows: list[PodcastShow], mode: str) -> list[PodcastShow]:
    """Return only the shows matching *mode* (unrecognized modes behave like
    ``"all"``)."""
    if mode == "favorites_only":
        return [s for s in shows if s.is_favorite]
    if mode == "has_unplayed":
        return [s for s in shows if any(not e.played for e in s.episodes)]
    return list(shows)


def filter_episodes_by_text(episodes: list[PodcastEpisode], query: str) -> list[PodcastEpisode]:
    """Episodes whose title OR description contains *query* (case-insensitive
    substring; an empty query matches everything) -- the episode list's
    inline search box, distinct from the cross-library Search Everywhere."""
    needle = query.strip().casefold()
    if not needle:
        return list(episodes)
    return [
        e for e in episodes if needle in e.title.casefold() or needle in e.description.casefold()
    ]


def filter_shows_by_text(shows: list[PodcastShow], query: str) -> list[PodcastShow]:
    """Shows whose title contains *query* (case-insensitive substring; an
    empty query matches everything) -- the subscription tree's inline search
    box, sized for libraries in the hundreds or thousands of shows."""
    needle = query.strip().casefold()
    if not needle:
        return list(shows)
    return [s for s in shows if needle in s.title.casefold()]


@dataclass(frozen=True, slots=True)
class SearchResult:
    """One match from :func:`search_everywhere`."""

    kind: str  # "show" | "episode" | "note" | "transcript"
    show: PodcastShow
    episode: PodcastEpisode | None = None
    note_preview: str = ""

    @property
    def label(self) -> str:
        if self.kind == "show":
            return f"Show: {self.show.title}"
        if self.kind == "episode" and self.episode is not None:
            return f"Episode: {self.episode.title} ({self.show.title})"
        if self.kind == "note" and self.episode is not None:
            return f'Note on "{self.episode.title}": {self.note_preview}'
        if self.kind == "transcript" and self.episode is not None:
            return f'Transcript of "{self.episode.title}": {self.note_preview}'
        return self.show.title


def search_everywhere(
    library: PodcastLibrary,
    query: str,
    *,
    episode_notes: list | None = None,
    transcripts: list[tuple[str, str, str]] | None = None,
) -> list[SearchResult]:
    """Search every subscription, episode, (optionally) episode note, and
    (optionally) cached transcript for *query* (case-insensitive substring
    match). Shows first, then episodes, then notes, then transcripts -- each
    group in library order. ``transcripts`` is
    ``(show_id, episode_guid, text)`` tuples (see
    ``transcripts.iter_cached_transcripts``): only transcripts already
    fetched or transcribed are searchable, never a network fetch."""
    needle = query.strip().casefold()
    if not needle:
        return []
    results: list[SearchResult] = []
    for show in library.shows:
        if needle in show.title.casefold():
            results.append(SearchResult("show", show))
    for show in library.shows:
        for episode in show.episodes:
            if needle in episode.title.casefold():
                results.append(SearchResult("episode", show, episode))
    if episode_notes:
        shows_by_id = {show.id: show for show in library.shows}
        for note in episode_notes:
            if needle not in note.text.casefold():
                continue
            note_show = shows_by_id.get(note.show_id)
            if note_show is None:
                continue
            note_episode = note_show.find_episode(note.episode_guid)
            if note_episode is None:
                continue
            preview = note.text.splitlines()[0]
            results.append(SearchResult("note", note_show, note_episode, preview))
    if transcripts:
        shows_by_id = {show.id: show for show in library.shows}
        for show_id, episode_guid, text in transcripts:
            lowered = text.casefold()
            position = lowered.find(needle)
            if position < 0:
                continue
            t_show = shows_by_id.get(show_id)
            if t_show is None:
                continue
            t_episode = t_show.find_episode(episode_guid)
            if t_episode is None:
                continue
            # A short window around the first hit, so the result reads as
            # "why this matched" rather than the transcript's first line.
            start = max(0, position - 30)
            snippet = " ".join(text[start : position + 50].split())
            results.append(SearchResult("transcript", t_show, t_episode, snippet))
    return results
