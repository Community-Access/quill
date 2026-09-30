"""What Ask QUILL Radio tells the model before the listener says a word.

The editors' conversation instructions are about a document; a radio has no
document, it has *what is on*. So Quill Radio's assistant gets its own
instructions and, with every message, one line of context the app alone knows:
the station playing and the title the stream is announcing. That is the whole
trick. "What is this song?" and "tell me about this station" need no typing
of names, because the app has already said them.

Pure functions, wx-free, so the sentences are testable and the window is not
the place they are written.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

__all__ = [
    "QUICK_QUESTIONS",
    "RADIO_INSTRUCTIONS",
    "QuickQuestion",
    "context_line",
    "describe_extra",
    "extra_context",
    "instructions_for",
    "suggested_questions",
]

RADIO_INSTRUCTIONS = (
    "You are QUILL Radio's assistant, inside Quill Radio, an internet radio and "
    "podcast player made for blind and low-vision listeners who use a screen "
    "reader. Answer questions about radio stations and broadcasters, programmes "
    "and schedules, music, songs, artists and albums, podcasts and their hosts, "
    "audio description, and about listening in general. Reply in plain language "
    "suitable for a screen reader to read aloud: the answer first, then only the "
    "detail that helps, in short paragraphs, with no tables, no headings and no "
    "bullet symbols. When the context names the station or the title now "
    "playing, use it: 'this station' and 'this song' mean those. Do not quote song "
    "lyrics at length. If you are not sure of something, say so rather than "
    "guessing, and if web search is available and the question is about something "
    "current -- a schedule, a live event, a new release -- use it."
)


def context_line(station: str, now_playing: str) -> str:
    """One sentence saying what is on, or that nothing is."""
    station = (station or "").strip()
    now_playing = (now_playing or "").strip()
    if station and now_playing:
        return f"Right now the listener is playing {station}, and the stream says: {now_playing}."
    if station:
        return f"Right now the listener is playing {station}; the stream has not said what is on."
    return "Nothing is playing right now."


def instructions_for(station: str, now_playing: str, *, web_search: bool, extra: str = "") -> str:
    """The full instructions for one message: the standing ones, plus the context.

    *extra* is context the listener chose to send with a quick question -- the
    names of their favorites, the songs logged on this station -- and goes in
    only when they chose it. Nothing about the listener travels by default
    beyond what is on.
    """
    if web_search:
        search = "Web search is available to you."
    else:
        search = (
            "Web search is not available; answer from what you know and say when it "
            "may be out of date."
        )
    text = f"{RADIO_INSTRUCTIONS}\n\nContext: {context_line(station, now_playing)} {search}"
    if extra.strip():
        text += f"\n\nThe listener chose to send this as well:\n{extra.strip()}"
    return text


# --------------------------------------------------------------------------- #
# Quick questions: one keystroke each, and each says what else it sends
# --------------------------------------------------------------------------- #

#: What a quick question may ask the app to attach. ``playing`` is the station
#: and title that go with every message anyway; the other three are things the
#: app knows about the *listener*, and they travel only when a question that
#: needs them is chosen, never by default.
NEEDS_PLAYING = "playing"
NEEDS_FAVORITES = "favorites"
NEEDS_RECENT_SONGS = "recent_songs"
NEEDS_LISTENING = "listening"

#: How many names and titles at most go with a quick question. Enough for the
#: model to see a taste; not the whole library.
MAX_FAVORITES_SENT = 60
MAX_SONGS_SENT = 25
MAX_STATIONS_SENT = 12


@dataclass(frozen=True, slots=True)
class QuickQuestion:
    """A prepared question, and what it attaches."""

    id: str
    label: str
    question: str
    needs: str = NEEDS_PLAYING


QUICK_QUESTIONS: tuple[QuickQuestion, ...] = (
    QuickQuestion(
        "song",
        "What is this song?",
        "What is this song, who made it, and what should I know about it?",
    ),
    QuickQuestion(
        "artist",
        "Tell me about the artist playing now",
        "Tell me about the artist playing now: who they are, what they are known "
        "for, and two or three of their best-known recordings.",
    ),
    QuickQuestion(
        "station",
        "Tell me about this station",
        "Tell me about this station: who runs it, where it broadcasts from, what it "
        "plays, and what it is known for.",
    ),
    QuickQuestion(
        "schedule",
        "What does this station broadcast, and when?",
        "What kinds of programmes does this station broadcast, and roughly when? "
        "If you know its schedule for today, say what is on next.",
    ),
    QuickQuestion(
        "podcast_like",
        "Is there a podcast like this station?",
        "Is there a podcast like this station or the programme playing now? Name "
        "two or three and say what each is like.",
    ),
    QuickQuestion(
        "translate",
        "What is the title now playing about?",
        "The title now playing may be in another language. Translate it into "
        "English and say, briefly, what the song or programme is about.",
    ),
    QuickQuestion(
        "recommend",
        "Recommend stations like my favorites",
        "Here are my favorite stations. Recommend five internet radio stations I "
        "would probably like and do not already have, and say in a sentence why "
        "each fits.",
        NEEDS_FAVORITES,
    ),
    QuickQuestion(
        "taste",
        "What have I been hearing on this station lately?",
        "Here are the songs this station has played while I listened. Sum up what "
        "it has been playing, name anything that stands out, and suggest two "
        "artists I might look up.",
        NEEDS_RECENT_SONGS,
    ),
    QuickQuestion(
        "discover",
        "Suggest something new from everything I have played",
        "Here is what I have been listening to across my stations. Suggest three "
        "stations or podcasts that would be new to me and say why each one fits.",
        NEEDS_LISTENING,
    ),
)


def extra_context(
    needs: str,
    *,
    favorites: Sequence[tuple[str, str]] = (),
    recent_songs: Sequence[str] = (),
    listening: Sequence[tuple[str, Sequence[str]]] = (),
) -> str:
    """The text a quick question attaches, built from what the app knows.

    *favorites* is ``(station name, folder)`` pairs, *recent_songs* the display
    lines logged on the station playing, *listening* ``(station name, its
    recent song lines)`` for every station with a log. Each is capped, so the
    request stays a request and not the listener's whole history.
    """
    if needs == NEEDS_FAVORITES:
        names = []
        for name, folder in favorites[:MAX_FAVORITES_SENT]:
            names.append(f"{name} (in {folder})" if folder else name)
        return "Favorite stations: " + "; ".join(names) if names else ""
    if needs == NEEDS_RECENT_SONGS:
        songs = list(recent_songs[:MAX_SONGS_SENT])
        return "Songs heard on this station, newest first: " + "; ".join(songs) if songs else ""
    if needs == NEEDS_LISTENING:
        lines = []
        for name, heard_songs in listening[:MAX_STATIONS_SENT]:
            heard = "; ".join(list(heard_songs)[:5])
            lines.append(f"{name}: {heard}" if heard else name)
        return "Stations played recently, with songs heard: " + " | ".join(lines) if lines else ""
    return ""


def describe_extra(needs: str, *, count: int) -> str:
    """What a quick question will send besides the question, said before it goes."""
    if needs == NEEDS_FAVORITES:
        return (
            f"This question also sends the names of your {count} favorite stations."
            if count
            else "This question would send your favorites, but you have none saved yet."
        )
    if needs == NEEDS_RECENT_SONGS:
        return (
            f"This question also sends the {count} songs logged on this station."
            if count
            else "This question needs songs logged on this station, and there are none yet."
        )
    if needs == NEEDS_LISTENING:
        return (
            f"This question also sends the names of {count} stations you have played, "
            "with a few songs from each."
            if count
            else "This question needs a listening history, and there is none yet."
        )
    return "This question sends only the station and title playing now."


def suggested_questions(station: str, now_playing: str) -> list[str]:
    """Questions worth one keystroke, given what is on. Empty when nothing is."""
    questions: list[str] = []
    if now_playing.strip():
        questions.append("What is this song, and who made it?")
        questions.append("Tell me more about the artist playing now.")
    if station.strip():
        questions.append("Tell me about this station: who runs it, where, and what it plays.")
        questions.append("What kind of programmes does this station broadcast, and when?")
    return questions
