"""QUILL Cast's own AI questions, and the answers it refuses to trust (ear.md A3-A9).

Each feature here is the wx-free half: the question as one string, and the
answer read back into something that cannot act on its own. The UI half
(:mod:`quill.ui.podcasts.cast_ai_features`) sends the question through the
family's one shared AI service and shows the result for review.

The rules ear.md sets for every one of them:

* **The model proposes; the listener disposes.** A3-A5 only *say* something.
  A6-A8 return proposals, and nothing is written until Apply.
* **Every proposal is resolved back against the real library by id.** An
  episode, show or folder the model invented is dropped, and the count of
  dropped rows is part of what is said.
* **The model sees titles, descriptions and show notes** -- never a feed
  address, a file path, a listening position or a support id.
* **Lengths are Cast's own.** A listening run is chosen by the model and
  measured by Cast: the model says *which*, never *how long*.

A9 (Tidy the Podcasts I Follow) needs no model at all: dormant, duplicate and
failing podcasts are facts Cast already has, so it computes them, sends
nothing anywhere, and offers an action per row that the listener chooses.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

__all__ = [
    "ChapterTitle",
    "RunPick",
    "TidyRow",
    "about_show_prompt",
    "chapter_titles_prompt",
    "for_me_prompt",
    "listening_run_prompt",
    "playlist_rules_prompt",
    "read_chapter_titles",
    "read_listening_run",
    "read_playlist_rules",
    "summary_prompt",
    "tidy_rows",
]

#: The most text of any one kind sent with a question.
NOTES_CHARS = 6000
TRANSCRIPT_CHARS = 12000
DESCRIPTION_CHARS = 1200

_TAGS = re.compile(r"<[^>]+>")
_SPACE = re.compile(r"\s+")


def _plain(text: str, limit: int) -> str:
    """Show notes as plain text, trimmed: tags out, whitespace folded."""
    cleaned = _SPACE.sub(" ", _TAGS.sub(" ", str(text or ""))).strip()
    return cleaned[:limit]


def _json_block(text: str) -> Any:
    """The first JSON object or array in a model's answer, or None."""
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if 0 <= start < end:
            try:
                return json.loads(text[start : end + 1])
            except ValueError:
                continue
    return None


# -- A3: what is this show about? ------------------------------------------------


def about_show_prompt(show: Any) -> str:
    description = _plain(getattr(show, "description", ""), DESCRIPTION_CHARS)
    recent = [str(ep.title) for ep in list(getattr(show, "episodes", []))[:8]]
    lines = [
        "In two or three plain sentences, say what this podcast is about and who "
        "it is for. Work only from what is below; if it is not enough, say so.",
        "",
        f"Podcast: {show.title}",
        f"Its own description: {description or '(none)'}",
        "Recent episode titles:",
        *[f"- {title}" for title in recent],
    ]
    return "\n".join(lines)


# -- A4: is this episode for me? -------------------------------------------------


def for_me_prompt(show: Any, episode: Any, care: str) -> str:
    notes = _plain(getattr(episode, "description", ""), NOTES_CHARS)
    return "\n".join([
        "A listener described what they care about in this podcast. Decide "
        "whether this episode is for them. Answer in one sentence that starts "
        'with "Yes", "Probably", "Probably not" or "No", then one sentence '
        "giving the reason. Work only from the episode's notes.",
        "",
        f"What the listener cares about: {care.strip()}",
        f"Podcast: {show.title}",
        f"Episode: {episode.title}",
        f"Show notes: {notes or '(none)'}",
    ])


# -- A5: summarise this episode ---------------------------------------------------


def summary_prompt(episode: Any, transcript: str) -> tuple[str, str]:
    """``(prompt, source)``: from the transcript when there is one, else the
    show notes -- and *source* says which, because a summary of a marketing
    blurb must not read as a summary of the episode."""
    if transcript.strip():
        body, source = transcript.strip()[:TRANSCRIPT_CHARS], "the transcript"
    else:
        body = _plain(getattr(episode, "description", ""), NOTES_CHARS)
        source = "the show notes"
    prompt = "\n".join([
        "Summarise this podcast episode in four to six plain sentences, for "
        "someone deciding whether to listen. Use only the text below.",
        "",
        f"Episode: {episode.title}",
        f"Text ({source}):",
        body or "(none)",
    ])
    return prompt, source


# -- A6: build me a listening run ---------------------------------------------------


@dataclass(frozen=True, slots=True)
class RunPick:
    """One episode the model chose, resolved, with Cast's own length."""

    show: Any
    episode: Any
    minutes: int
    reason: str = ""

    def spoken(self) -> str:
        why = f" -- {self.reason}" if self.reason else ""
        return f"{self.episode.title}, {self.show.title}, {self.minutes} minutes{why}"


def _minutes_left(episode: Any) -> int:
    total = int(getattr(episode, "duration_seconds", 0) or 0)
    played = int(getattr(episode, "position_ms", 0) or 0) // 1000
    return max(0, round((total - played) / 60)) if total else 0


def listening_run_prompt(candidates: list[tuple[Any, Any]], minutes: int, care: str = "") -> str:
    """The numbered candidates and the time; the answer is a list of numbers."""
    lines = [
        f"A listener has about {minutes} minutes. From the episodes below, choose "
        "a short listening run they would enjoy, in the order to play them. Prefer "
        "variety over three of one podcast. Use only the numbers listed; Cast "
        "measures the time itself.",
    ]
    if care.strip():
        lines.append(f"They said they care about: {care.strip()}")
    lines += ["", "Episodes:"]
    for number, (show, episode) in enumerate(candidates, start=1):
        length = _minutes_left(episode)
        lines.append(f"{number}. {episode.title} | {show.title} | about {length} minutes")
    lines += [
        "",
        'Answer with JSON only: {"run": [{"number": 3, "reason": "at most ten words"}]}',
    ]
    return "\n".join(lines)


def read_listening_run(
    answer: str, candidates: list[tuple[Any, Any]], minutes: int
) -> tuple[list[RunPick], list[str]]:
    """``(picks that fit, discarded reasons)``. Unknown numbers, repeats and
    anything past the time are dropped, each with its reason."""
    data = _json_block(answer)
    entries = data.get("run") if isinstance(data, dict) else data
    picks: list[RunPick] = []
    discarded: list[str] = []
    seen: set[int] = set()
    used = 0
    for entry in entries if isinstance(entries, list) else []:
        number = entry.get("number") if isinstance(entry, dict) else entry
        try:
            index = int(str(number)) - 1
        except ValueError:
            discarded.append(f"{number!r} is not one of the listed numbers.")
            continue
        if not 0 <= index < len(candidates):
            discarded.append(f"{index + 1} is not one of the listed numbers.")
            continue
        if index in seen:
            discarded.append(f"{index + 1} was chosen twice.")
            continue
        seen.add(index)
        show, episode = candidates[index]
        length = _minutes_left(episode)
        if used + length > minutes and picks:
            discarded.append(f"{episode.title} would not fit in {minutes} minutes.")
            continue
        used += length
        reason = str(entry.get("reason", "")).strip()[:80] if isinstance(entry, dict) else ""
        picks.append(RunPick(show, episode, length, reason))
    return picks, discarded


# -- A7: smart playlist rules from a sentence ------------------------------------


def playlist_rules_prompt(sentence: str, show_titles: list[str], folder_names: list[str]) -> str:
    return "\n".join([
        "Turn the listener's request into a smart playlist rule set. Use only "
        "these fields, and leave out any you do not need:",
        '  "name": a short playlist name',
        '  "episode_status": one of any, unplayed, in_progress, played',
        '  "published_within_days": a whole number, 0 for no limit',
        '  "min_duration_minutes", "max_duration_minutes": whole numbers, 0 for none',
        '  "shows": podcast titles exactly as listed below',
        '  "folders": folder names exactly as listed below',
        '  "text_contains": words the title or notes must contain',
        '  "download_state": one of any, downloaded, not_downloaded',
        '  "sort_mode": one of date_newest, date_oldest, duration_shortest, duration_longest',
        "",
        f"Podcasts: {'; '.join(show_titles[:200]) or '(none)'}",
        f"Folders: {'; '.join(folder_names) or '(none)'}",
        "",
        f"Request: {sentence.strip()}",
        "",
        "Answer with one JSON object only.",
    ])


def read_playlist_rules(answer: str, library: Any) -> tuple[str, Any, list[str]]:
    """``(name, PlaylistRules, discarded)``. Shows and folders are resolved by
    exact name; any the library does not have are dropped with a reason."""
    from quill.core.podcasts.models_playlists import PlaylistRules

    data = _json_block(answer)
    if not isinstance(data, dict):
        return "", PlaylistRules(), ["The answer was not a rule set."]
    discarded: list[str] = []
    by_title = {str(show.title).casefold(): show.id for show in library.shows}
    by_folder = {str(folder.name).casefold(): folder.id for folder in library.folders}
    show_ids: list[str] = []
    for title in data.get("shows", []) if isinstance(data.get("shows"), list) else []:
        found = by_title.get(str(title).casefold())
        if found:
            show_ids.append(found)
        else:
            discarded.append(f"No podcast called {title}.")
    folder_ids: list[str] = []
    for name in data.get("folders", []) if isinstance(data.get("folders"), list) else []:
        found = by_folder.get(str(name).casefold())
        if found:
            folder_ids.append(found)
        else:
            discarded.append(f"No folder called {name}.")
    raw = {key: value for key, value in data.items() if key not in ("shows", "folders", "name")}
    raw["show_ids"] = show_ids
    raw["folder_ids"] = folder_ids
    rules = PlaylistRules.from_dict(raw)
    name = str(data.get("name", "") or "").strip()[:60] or "From a sentence"
    return name, rules, discarded


def describe_rules(rules: Any, library: Any) -> list[str]:
    """The rule set as sentences, one per rule that narrows anything."""
    lines: list[str] = []
    if rules.episode_status != "any":
        lines.append(f"Episodes that are {rules.episode_status.replace('_', ' ')}.")
    if rules.published_within_days:
        lines.append(f"Published in the last {rules.published_within_days} days.")
    if rules.min_duration_minutes:
        lines.append(f"At least {rules.min_duration_minutes} minutes long.")
    if rules.max_duration_minutes:
        lines.append(f"At most {rules.max_duration_minutes} minutes long.")
    if rules.show_ids:
        names = [s.title for s in library.shows if s.id in rules.show_ids]
        lines.append("From " + ", ".join(names) + ".")
    if rules.folder_ids:
        names = [f.name for f in library.folders if f.id in rules.folder_ids]
        lines.append("In the folder" + ("s " if len(names) > 1 else " ") + ", ".join(names) + ".")
    if rules.text_contains:
        lines.append(f'Whose title or notes contain "{rules.text_contains}".')
    if rules.download_state != "any":
        lines.append(f"That are {rules.download_state.replace('_', ' ')}.")
    lines.append(f"Sorted {rules.sort_mode.replace('_', ' ')}.")
    return lines


# -- A8: name these chapters ---------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ChapterTitle:
    """One proposed title for one existing chapter."""

    index: int
    start_ms: int
    old: str
    new: str

    def spoken(self) -> str:
        minutes, seconds = divmod(self.start_ms // 1000, 60)
        return f"{minutes}:{seconds:02d}: {self.new} (now {self.old})"


def chapter_titles_prompt(chapters: list[Any], texts: list[str]) -> str:
    lines = [
        "Give each podcast chapter below a short, specific title of at most eight "
        "words, from what is said in it. Do not invent topics that are not there.",
        "",
    ]
    for number, (chapter, text) in enumerate(zip(chapters, texts, strict=True), start=1):
        lines.append(f"Chapter {number} (now titled {chapter.title!r}):")
        lines.append(text[:1500] or "(nothing transcribed)")
        lines.append("")
    lines.append('Answer with JSON only: {"titles": [{"chapter": 1, "title": "..."}]}')
    return "\n".join(lines)


def read_chapter_titles(answer: str, chapters: list[Any]) -> tuple[list[ChapterTitle], list[str]]:
    data = _json_block(answer)
    entries = data.get("titles") if isinstance(data, dict) else data
    found: list[ChapterTitle] = []
    discarded: list[str] = []
    seen: set[int] = set()
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        try:
            index = int(str(entry.get("chapter"))) - 1
        except ValueError:
            discarded.append("A title named no chapter.")
            continue
        title = _SPACE.sub(" ", str(entry.get("title", ""))).strip()[:80]
        if not 0 <= index < len(chapters) or index in seen or not title:
            discarded.append(f"Chapter {index + 1} is not one of these chapters.")
            continue
        seen.add(index)
        chapter = chapters[index]
        if title != chapter.title:
            found.append(ChapterTitle(index, chapter.start_ms, chapter.title, title))
    return found, discarded


# -- A9: tidy my subscriptions (no model) ----------------------------------------------


@dataclass(frozen=True, slots=True)
class TidyRow:
    """One podcast worth a look, why, and the action offered for it."""

    show_id: str
    title: str
    reason: str
    action: str  # "unfollow" | "pause"

    def spoken(self) -> str:
        verb = "Unfollow" if self.action == "unfollow" else "Pause updates"
        return f"{verb}: {self.title} -- {self.reason}"


def _newest(show: Any) -> datetime | None:
    newest: datetime | None = None
    for episode in getattr(show, "episodes", []):
        try:
            stamp = datetime.fromisoformat(str(episode.published).replace("Z", "+00:00"))
        except ValueError:
            continue
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=UTC)
        if newest is None or stamp > newest:
            newest = stamp
    return newest


def tidy_rows(
    library: Any,
    *,
    now: datetime | None = None,
    failing: set[str] | None = None,
    dormant_days: int = 365,
) -> list[TidyRow]:
    """Podcasts that look finished, doubled up, or broken -- with a reason each."""
    moment = now or datetime.now(UTC)
    rows: list[TidyRow] = []
    seen_titles: dict[str, str] = {}
    for show in library.shows:
        if getattr(show, "is_local", False):
            continue
        key = re.sub(r"[^a-z0-9]+", "", str(show.title).casefold())
        if key and key in seen_titles:
            rows.append(
                TidyRow(
                    show.id,
                    show.title,
                    f"looks like a second copy of {seen_titles[key]}",
                    "unfollow",
                )
            )
            continue
        if key:
            seen_titles[key] = show.title
        if failing and show.id in failing:
            rows.append(TidyRow(show.id, show.title, "its feed keeps failing", "pause"))
            continue
        newest = _newest(show)
        if newest is not None and (moment - newest).days >= dormant_days and not show.paused:
            years = (moment - newest).days // 365
            when = f"{years} year{'s' if years != 1 else ''}" if years else "a year"
            rows.append(TidyRow(show.id, show.title, f"nothing new in over {when}", "pause"))
    return rows
