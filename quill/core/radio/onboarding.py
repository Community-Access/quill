"""Quill Radio's first thirty seconds.

A new listener opens Quill Radio and gets an empty favorites tree. That is an
accurate picture of having no favorites, and it answers none of the questions
somebody actually arrives with: *where are the stations, how do I play one, and
how do I keep it?*

The feature set is not the problem -- Radio browses eight directories, records
on a schedule, rewinds live audio and remembers a volume per station. The
problem is that none of it is reachable by somebody who does not already know
it is there. Every product review of this app has said the same thing, in the
same words: the app is excellent and the first minute is a locked door.

So: **three screens, not seven**, exactly the shape
:mod:`quill.core.podcasts.onboarding` uses for QUILL Cast. Welcome, find a
station, keep it. Radio has no account, no tracker and no cloud, so it needs
none of the consent screens a phone app needs -- and a first-run flow that asks
somebody to page through permissions they never granted is how people learn to
dismiss dialogs without reading them.

Then **one-shot tips**: one sentence, the first time somebody reaches a place
where knowing one non-obvious thing changes what they can do. Each fires once,
ever. The rules that make tips bearable rather than an irritation are Cast's,
because they were right there:

* **Once, ever.** A tip that reappears is an interruption; a tip that appears
  once is a fact you now know.
* **Never modal, never focus-stealing.** They ride the ordinary announcement
  path -- speech and braille -- and never take the keyboard.
* **Only where they change what you can do.** No tip explains a button whose
  label already explains it.
* **Off in one place, permanently.**

Every key named in a screen or a tip is Radio's *default*. They are rebindable
in the Keyboard Manager, which is why :func:`screen_body` takes a resolver: a
first-run screen that teaches a key somebody has already changed is worse than
one that teaches nothing.

wx-free, strict-typed. The store is a plain set of ids the caller persists with
the rest of the radio history.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

WELCOME = "welcome"
FIND_STATION = "find_station"
KEEP_IT = "keep_it"

#: The three screens, in order.
FIRST_RUN_SCREENS: tuple[str, ...] = (WELCOME, FIND_STATION, KEEP_IT)

SCREEN_TITLES: dict[str, str] = {
    WELCOME: "Welcome to Quill Radio",
    FIND_STATION: "Find something to listen to",
    KEEP_IT: "Keep the ones you like",
}

#: Screen bodies, with ``{command}`` placeholders resolved by
#: :func:`screen_body` against whatever the listener has actually bound. The
#: raw text is kept here so the words are testable and cannot drift between a
#: label and an announcement.
SCREEN_BODIES: dict[str, str] = {
    WELCOME: (
        "Quill Radio plays internet radio, and it is built for listening with a "
        "screen reader. Everything is a list you can arrow through, every "
        "station reads as a whole sentence, and every command has a key you can "
        "change.\n\n"
        "Nothing here needs an account, and nothing you listen to leaves this "
        "computer.\n\n"
        "One key carries most of the app: {browse} opens the station browser, "
        "and What's Playing (in the Playback menu) says what is on, wherever "
        "you are."
    ),
    FIND_STATION: (
        "There are three ways in, and you can use any of them at any time.\n\n"
        "Browse Stations ({browse}) is a tree: genres, countries, networks, "
        "news, weather and reading services for blind listeners. Arrow into a "
        "branch, arrow through the stations, press Enter to play.\n\n"
        "Search All Sources, at the top of that tree, asks every directory at "
        "once -- by name, call sign or genre.\n\n"
        "Add Station ({add_station}) takes an address you already have, "
        "including a YouTube link or a podcast feed."
    ),
    KEEP_IT: (
        "Two things worth knowing before you start.\n\n"
        "Favorites are yours to arrange. Add to Favorites keeps the station "
        "you are playing; Manage Favorites ({manage_favorites}) groups them "
        "into folders, renames them and moves them where you want. The first "
        "ten answer a key each -- {play_first} plays the first -- so a station "
        "you listen to daily is one keystroke away.\n\n"
        "Radio keeps going while you work. Closing the window can send it to "
        "the tray instead of stopping it, and it remembers the volume you set "
        "for each station separately."
    ),
}

#: Every one-shot tip: id, and the single sentence it says. Kept as data so the
#: whole set is reviewable in one place -- a tip added by hand at a call site is
#: a tip nobody can audit.
TIPS: dict[str, str] = {
    "live_rewind": (
        "Live radio can be paused and rewound. The pause key holds the "
        "broadcast and picks it up where you left it, up to the buffer's length."
    ),
    "per_station_volume": (
        "Radio remembers a volume for each station, so a loud one stays turned "
        "down next time. Use One Volume for All Stations turns that off."
    ),
    "record_schedule": (
        "A recording can be scheduled for a programme that has not started yet, "
        "and it will wake the computer to catch it."
    ),
    "sound_enhancements": (
        "Sound Enhancements has a three-band equalizer, a compressor and a night "
        "mode, and each can be set for one station rather than all of them."
    ),
    "browse_position": (
        "Browse Stations reopens where you left it, with the branch you were in still expanded."
    ),
    "song_history": (
        "Song History keeps every track a station announced while you listened, "
        "so a song you half-caught an hour ago is still there."
    ),
}

#: Which command each ``{placeholder}`` in the screens refers to. Kept beside
#: the text so a renamed command id fails a test here rather than rendering an
#: empty pair of braces to a new listener.
#:
#: Only ids that actually carry a *binding* appear here. Two things the screens
#: mention -- Search All Sources and Add to Favorites -- are a tree row and a
#: button, not keymap commands, so they are named rather than keyed. Teaching a
#: key that does not exist is worse than teaching a menu route that does.
SCREEN_COMMANDS: dict[str, str] = {
    "browse": "radio.browse",
    "add_station": "radio.add_custom_station",
    "manage_favorites": "radio.manage_favorites",
    "play_first": "radio.play_favorite_1",
}


@dataclass(slots=True)
class RadioOnboardingState:
    """What the listener has already been shown.

    Persisted by the caller with the rest of ``RadioHistory``. Deliberately a
    set of ids rather than a version number: a tip added next year should fire
    for somebody who has used Radio for a year, and a version stamp would say
    they had already seen it.
    """

    completed_first_run: bool = False
    seen_tips: set[str] = field(default_factory=set)
    tips_enabled: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "completed_first_run": self.completed_first_run,
            "seen_tips": sorted(self.seen_tips),
            "tips_enabled": self.tips_enabled,
        }

    @classmethod
    def from_dict(cls, data: object) -> RadioOnboardingState:
        if not isinstance(data, dict):
            return cls()
        raw = data.get("seen_tips")
        # An unknown id is kept rather than dropped: it is a tip from a newer
        # build, and forgetting it would show it again on the way back down.
        seen = {str(item) for item in raw} if isinstance(raw, list) else set()
        return cls(
            completed_first_run=bool(data.get("completed_first_run", False)),
            seen_tips=seen,
            tips_enabled=bool(data.get("tips_enabled", True)),
        )


def needs_first_run(state: RadioOnboardingState, *, has_favorites: bool) -> bool:
    """Whether to run the three screens.

    Not for somebody who already has favorites, however they got there -- an
    imported station list, a restored backup, an upgrade from a version that
    predates this flow. Explaining how to find a first station to somebody with
    forty is a way of saying nobody checked.
    """
    return not state.completed_first_run and not has_favorites


def screen_body(key: str, resolve_key: Callable[[str], str] | None = None) -> str:
    """The screen's words, with each command placeholder replaced by its key.

    *resolve_key* takes a command id and returns the keystroke bound to it now.
    Without one, or when a command has no key, the placeholder collapses to the
    command's menu route rather than leaving braces on screen -- a first-run
    screen that reads out "press left brace radio browse right brace" is worse
    than one that says nothing at all.
    """
    body = SCREEN_BODIES[key]
    replacements: dict[str, str] = {}
    for placeholder, command_id in SCREEN_COMMANDS.items():
        binding = ""
        if resolve_key is not None:
            try:
                binding = (resolve_key(command_id) or "").strip()
            except Exception:  # noqa: BLE001 - a keymap lookup must not break a screen
                binding = ""
        replacements[placeholder] = binding or "the menu item of the same name"
    return body.format(**replacements)


def tip_for(state: RadioOnboardingState, tip_id: str) -> str:
    """The tip's sentence if it should fire now, else "".

    Marking is the caller's job (:func:`mark_seen`) so a tip that could not
    actually be delivered -- the window closed, speech was off -- is not
    recorded as shown.
    """
    if not state.tips_enabled or tip_id in state.seen_tips:
        return ""
    return TIPS.get(tip_id, "")


def mark_seen(state: RadioOnboardingState, tip_id: str) -> None:
    """Record that *tip_id* has now been shown. Once, ever."""
    if tip_id in TIPS:
        state.seen_tips.add(tip_id)


def reset_tips(state: RadioOnboardingState) -> None:
    """Show every tip again -- for somebody who wants the refresher."""
    state.seen_tips.clear()


def remaining_tips(state: RadioOnboardingState) -> int:
    """How many tips have not fired yet, for the settings label."""
    return len([tip for tip in TIPS if tip not in state.seen_tips])


def describe_tips(state: RadioOnboardingState) -> str:
    """The settings line: what tips are, and where this listener stands."""
    if not state.tips_enabled:
        return "Tips are switched off."
    left = remaining_tips(state)
    if not left:
        return "You have seen every tip. Show Tips Again puts them back."
    return f"{left} tip{'' if left == 1 else 's'} still to appear, each shown once."
