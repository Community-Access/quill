"""First run, and the one-shot tips that follow it.

QUILL Cast drops a new listener into an empty library tree. That is not a broken
window -- it is an accurate picture of having no podcasts -- but it answers none
of the three questions somebody actually arrives with: *what is this, how do I
add a show, and what happens then?*

So: **three screens, not seven.** Welcome, add your first podcast, you're set.
Cast does not need the privacy screens a phone app needs -- nothing here has an
account, a tracker or a cloud -- and a first-run flow that asks somebody to page
through consent they never gave anything is how people learn to dismiss dialogs
without reading them.

Then **one-shot tips**: a single sentence, the first time somebody reaches a
place where knowing one non-obvious thing changes what they can do. Each fires
once, ever, and is remembered as fired. Together with a master switch, that is
the whole feature.

The rules that make tips bearable rather than an irritation:

* **Once, ever.** A tip that reappears is an interruption; a tip that appears
  once is a fact you now know.
* **Never modal, never focus-stealing.** They ride the ordinary announcement
  path, which means speech and braille, and they never take the keyboard.
* **Only where they change what you can do.** No tip explains a button whose
  label already explains it.
* **Off in one place, permanently.** Somebody who does not want them should not
  have to dismiss each one to find that out.

wx-free, strict-typed. The store is a plain set of ids the caller persists with
the rest of its settings.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: The three first-run screens, in order. Each is a heading and a body; the UI
#: renders them, and this decides what they say -- so the words are testable and
#: cannot drift between an announcement and a label.
WELCOME = "welcome"
ADD_FIRST = "add_first"
DONE = "done"

FIRST_RUN_SCREENS: tuple[str, ...] = (WELCOME, ADD_FIRST, DONE)

SCREEN_TITLES: dict[str, str] = {
    WELCOME: "Welcome to QUILL Cast",
    ADD_FIRST: "Add your first podcast",
    DONE: "You're set",
}

SCREEN_BODIES: dict[str, str] = {
    WELCOME: (
        "QUILL Cast is a podcast player built for listening with a screen reader. "
        "Everything is a list you can arrow through, every row reads as a whole "
        "sentence, and every command has a key you can change.\n\n"
        "Nothing here needs an account, and nothing you listen to leaves this "
        "computer."
    ),
    ADD_FIRST: (
        "There are two ways in, and you can use either at any time.\n\n"
        "**Add Podcast...** searches by name -- type a few words of a show you "
        "know and press Enter.\n\n"
        "**Add by Feed URL...** takes an address you already have, including a "
        "private or supporter feed, which will ask for its username and password "
        "if it needs one.\n\n"
        "Already have a subscription list from another app? **Import OPML...** "
        "brings the whole thing across."
    ),
    DONE: (
        "Two things worth knowing before you start.\n\n"
        "**New episodes can arrive downloaded.** Podcast Settings can keep the "
        "newest few episodes of each show ready to play with nothing to wait "
        "for.\n\n"
        "**The Inbox is for triage.** Route a show to it and its new episodes "
        "wait there to be sorted rather than piling into your queue -- useful "
        "when you follow more shows than you listen to."
    ),
}

#: Every one-shot tip: id, where it fires, and the single sentence it says.
#: Kept as data so the set is reviewable in one place -- a tip added by hand at
#: a call site is a tip nobody can audit.
TIPS: dict[str, str] = {
    "queue_vs_inbox": (
        "The Play Queue is what plays next; the Inbox is where episodes wait to "
        "be sorted. An episode can be in either without being in the other."
    ),
    "per_show_settings": (
        "Most settings can differ per podcast. Settings for This Podcast... "
        "overrides the shared default for this show only."
    ),
    "chapters_worked_out": (
        "This episode published no chapters, so these were worked out. "
        "How Were These Found... says which method and how confident it was."
    ),
    "expired_queue": (
        "A queued episode you never got to expires rather than sitting there "
        "taking a turn. Recently Expired holds it for seven days."
    ),
    "smart_playlists": (
        "A Smart Playlist re-asks its question every time you open it, so it is "
        "never stale. A plain playlist keeps exactly what you put in it."
    ),
    "transcript_reader": (
        "Read Transcript... follows the audio as it plays, and Enter on any line plays from there."
    ),
}


@dataclass(slots=True)
class OnboardingState:
    """What the listener has already been shown.

    Persisted by the caller alongside its other settings. Deliberately a set of
    ids rather than a version number: a tip added next year should fire for
    somebody who has been using Cast for a year, and a version stamp would say
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
    def from_dict(cls, data: object) -> OnboardingState:
        if not isinstance(data, dict):
            return cls()
        raw = data.get("seen_tips")
        # An unknown id is kept rather than dropped: it is a tip from a newer
        # build, and forgetting it would show it again on the way back.
        seen = {str(item) for item in raw} if isinstance(raw, list) else set()
        return cls(
            completed_first_run=bool(data.get("completed_first_run", False)),
            seen_tips=seen,
            tips_enabled=bool(data.get("tips_enabled", True)),
        )


def needs_first_run(state: OnboardingState, *, has_shows: bool) -> bool:
    """Whether to run the three screens.

    Not for somebody who already has podcasts, however they got there -- an
    imported OPML, a restored backup, an upgrade. Explaining how to add a first
    podcast to somebody with two hundred is a way of saying nobody checked.
    """
    return not state.completed_first_run and not has_shows


def tip_for(state: OnboardingState, tip_id: str) -> str:
    """The tip's sentence if it should fire now, else "".

    Marking is the caller's job (:func:`mark_seen`) so a tip that could not
    actually be delivered -- the window closed, speech was off -- is not recorded
    as shown.
    """
    if not state.tips_enabled or tip_id in state.seen_tips:
        return ""
    return TIPS.get(tip_id, "")


def mark_seen(state: OnboardingState, tip_id: str) -> None:
    """Record that *tip_id* has now been shown. Once, ever."""
    if tip_id in TIPS:
        state.seen_tips.add(tip_id)


def reset_tips(state: OnboardingState) -> None:
    """Show every tip again -- for somebody who wants the refresher."""
    state.seen_tips.clear()


def remaining_tips(state: OnboardingState) -> int:
    """How many tips have not fired yet, for the settings label."""
    return len([tip for tip in TIPS if tip not in state.seen_tips])


def describe_tips(state: OnboardingState) -> str:
    """The settings line: what tips are, and where this listener stands."""
    if not state.tips_enabled:
        return "Tips are switched off."
    left = remaining_tips(state)
    if not left:
        return "You have seen every tip. Show Tips Again puts them back."
    return f"{left} tip{'' if left == 1 else 's'} still to appear, each shown once."
