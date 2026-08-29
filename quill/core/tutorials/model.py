"""The shape of a tutorial in any Quill app, and the pure text that renders one.

A tutorial here is not a page of prose with the keys written into it. It is a
list of **steps**, and a step names the *command* it is about rather than the
key that runs it. Everything downstream follows from that one decision:

* The lesson shows **the key you actually have**. Rebind Browse Stations to
  something else and the tutorial says your key, because it asks the command
  registry at the moment it draws the step -- the same reason the Keyboard
  Shortcuts Sheet is built by walking the live menu bar rather than kept as a
  second list that is wrong by the next release.
* The lesson can **do the step for you**. A step that names a command can
  offer "Try it", which runs exactly what the key would have run.
* The lesson can **notice that you did it**. A step may carry a ``check`` --
  the name of a question about the app's live state ("something is playing
  now", "your favorites grew by one") -- and the window watches for the
  answer. Nothing is graded and nothing is required: a check that never comes
  true costs you one keypress to move on.

The model is deliberately wx-free and has no idea how any of that is
rendered. It knows what a step *says*; :mod:`quill.ui.tutorials_window` knows
how to show it, and each app's ``tutorial_checks`` knows how to answer a
check. The same text renders to Markdown for each app's printed tutorial book
(``quill/tools/build_tutorials_reference.py``), so the document and the window
can never drift: they are one source.

Written for Quill Radio first (2026-08-27) and shared out the next day, when
QUILL Cast, Quill Weather and QUILL itself got lessons of their own. Nothing
here knows which app it is serving: a :class:`TutorialSet` carries its own
tracks and its own lessons, and the window is handed one.

Wording rules for the content modules, so the set stays worth reading:

* A step is one action. "Open Browse Stations and find a jazz station" is two,
  and the second one is where somebody gets lost.
* Say **why**, not only what. A tutorial that lists keystrokes is a keyboard
  reference with extra words; the guide already has one of those.
* Say what you should **hear**. A screen-reader user's confirmation that a
  step worked is a sentence, not a green tick, and a step that does not say
  what to listen for cannot be checked by the person doing it.
* Never promise a key in prose. Name the command and let the key render.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass

#: How a caller resolves a command id to the key that is bound to it *now*.
#: Returns "" when the command has no key, or is not registered in this build.
KeyLookup = Callable[[str], str]


@dataclass(frozen=True, slots=True)
class Step:
    """One thing to do, and what should happen when you do it."""

    #: Short imperative title. What this step is, in a handful of words.
    title: str
    #: The instruction, and the reason for it. One short paragraph.
    body: str
    #: The Quill Radio command this step is about, if it is about one. The
    #: lesson renders this command's live key and offers to run it.
    command: str = ""
    #: Literal keys, for the steps no command id covers -- arrowing a tree,
    #: Escape, the Winamp letters. Written as they are spoken: "Ctrl+Up".
    keys: tuple[str, ...] = ()
    #: What you should hear when the step worked.
    hear: str = ""
    #: The name of a live-state question the window can watch for. Empty means
    #: "this step cannot be checked" -- most of them, and no worse for it.
    check: str = ""
    #: An aside: the thing that goes wrong, the setting that changes it, the
    #: fact that saves a support email. Optional, and skipped when empty.
    note: str = ""


@dataclass(frozen=True, slots=True)
class Tutorial:
    """A lesson: a handful of steps that leave you able to do one thing."""

    slug: str
    title: str
    #: The track id this belongs to (see :data:`TRACKS`).
    track: str
    #: What you will be able to do at the end. One or two sentences, written
    #: for somebody deciding whether to spend the next five minutes here.
    summary: str
    #: Roughly how long it takes, in minutes. Honest, not flattering.
    minutes: int
    steps: tuple[Step, ...]
    #: Window titles this lesson is about, so "tutorials about where I am
    #: standing" can answer. Matched against the front window's title.
    surfaces: tuple[str, ...] = ()
    #: The closing paragraph: what you now have, and what is worth doing next.
    closing: str = ""
    #: Slugs of lessons that assume this one. Rendered as "what to read next".
    then: tuple[str, ...] = ()

    @property
    def step_count(self) -> int:
        return len(self.steps)


@dataclass(frozen=True, slots=True)
class Track:
    """A group of lessons, in the order somebody would work through them."""

    id: str
    title: str
    blurb: str


@dataclass(frozen=True, slots=True)
class Progress:
    """Where somebody is in one lesson.

    ``step`` is the index of the step they are standing on. ``done`` says the
    lesson was finished at least once -- it is never cleared by starting the
    lesson again, because "I have done this" and "I am part way through it"
    are different facts, and a re-read should not throw the first one away.
    """

    slug: str
    step: int = 0
    done: bool = False


def track_titles(tracks: Sequence[Track]) -> dict[str, str]:
    return {track.id: track.title for track in tracks}


def tutorials_in(track_id: str, tutorials: Sequence[Tutorial]) -> list[Tutorial]:
    return [tutorial for tutorial in tutorials if tutorial.track == track_id]


def by_slug(slug: str, tutorials: Iterable[Tutorial]) -> Tutorial | None:
    for tutorial in tutorials:
        if tutorial.slug == slug:
            return tutorial
    return None


def _haystack(tutorial: Tutorial) -> str:
    parts: list[str] = [tutorial.title, tutorial.summary, tutorial.closing]
    parts.extend(tutorial.surfaces)
    for step in tutorial.steps:
        parts.extend((step.title, step.body, step.hear, step.note, step.command))
        parts.extend(step.keys)
    return " ".join(parts).lower()


def search(query: str, tutorials: Sequence[Tutorial]) -> list[Tutorial]:
    """Lessons matching every word of *query*, in catalogue order.

    Every word has to appear somewhere -- title, summary, any step, a key, a
    command id -- so "record tuesday" finds the scheduling lesson without
    anybody having to know which field holds which word. It is the same rule
    the ACB schedule's search uses, for the same reason.
    """
    words = [word for word in query.lower().split() if word]
    if not words:
        return list(tutorials)
    out: list[Tutorial] = []
    for tutorial in tutorials:
        hay = _haystack(tutorial)
        if all(word in hay for word in words):
            out.append(tutorial)
    return out


def for_surface(title: str, tutorials: Sequence[Tutorial]) -> list[Tutorial]:
    """Lessons about the window called *title*.

    Matched by prefix, because several windows carry what they are showing in
    their own title ("Now Playing: WQXR"), exactly as the F1 catalogue does.
    """
    clean = (title or "").strip()
    if not clean:
        return []
    out: list[Tutorial] = []
    for tutorial in tutorials:
        for surface in tutorial.surfaces:
            if clean == surface or clean.startswith(surface):
                out.append(tutorial)
                break
    return out


def key_phrase(step: Step, key_for: KeyLookup) -> str:
    """The keys for *step*, as a phrase, or "" when it has none.

    The command's live binding comes first; the literal keys are the fallback
    and the supplement. A step that names a command with no key bound falls
    back to its literals rather than claiming a key that is not there.
    """
    parts: list[str] = []
    if step.command:
        bound = (key_for(step.command) or "").strip()
        if bound:
            parts.append(bound)
    parts.extend(key for key in step.keys if key)
    seen: set[str] = set()
    unique: list[str] = []
    for part in parts:
        if part not in seen:
            seen.add(part)
            unique.append(part)
    return ", ".join(unique)


def step_heading(tutorial: Tutorial, index: int) -> str:
    """ "Play your first station -- step 2 of 7: Open Browse Stations"."""
    step = tutorial.steps[index]
    return f"{tutorial.title} -- step {index + 1} of {tutorial.step_count}: {step.title}"


def render_step(tutorial: Tutorial, index: int, key_for: KeyLookup) -> str:
    """The whole of one step as plain text, ready for a read-only field.

    Labelled lines rather than prose with the keys buried inside it: a screen
    reader reads this a line at a time, and "Keys: Ctrl+B" is one line worth
    arrowing to, where the same fact mid-sentence is one you have to hunt for.
    """
    step = tutorial.steps[index]
    lines: list[str] = [step_heading(tutorial, index), "", step.body]
    keys = key_phrase(step, key_for)
    if keys:
        lines.extend(("", f"Keys: {keys}"))
    if step.hear:
        lines.extend(("", f"You should hear: {step.hear}"))
    if step.note:
        lines.extend(("", f"Worth knowing: {step.note}"))
    return "\n".join(lines)


def render_tutorial(tutorial: Tutorial, key_for: KeyLookup) -> str:
    """The whole lesson as one document -- for reading straight through."""
    lines: list[str] = [
        tutorial.title,
        "",
        tutorial.summary,
        "",
        f"{tutorial.step_count} steps, about {tutorial.minutes} minutes.",
        "",
    ]
    for index in range(tutorial.step_count):
        lines.append(render_step(tutorial, index, key_for))
        lines.append("")
    if tutorial.closing:
        lines.extend((tutorial.closing, ""))
    return "\n".join(lines).rstrip() + "\n"


def contents_label(tutorial: Tutorial, progress: Progress | None) -> str:
    """The row a screen reader reads in the contents tree.

    Title, then size, then where you are -- in that order, because the title
    is what somebody is arrowing for, and everything after it is detail they
    can stop listening to once they have heard the name they wanted.
    """
    parts = [tutorial.title, f"{tutorial.step_count} steps", f"about {tutorial.minutes} minutes"]
    if progress is not None and progress.done:
        parts.append("finished")
    elif progress is not None and progress.step > 0:
        parts.append(f"you stopped at step {progress.step + 1}")
    return ", ".join(parts) + "."


def validate(tutorials: Sequence[Tutorial], track_ids: Iterable[str]) -> list[str]:
    """Complaints about the catalogue, as sentences. Empty means it is sound.

    Pure, so the test that guards the content can call it without a window,
    and so the doc builder can refuse to render a broken set.
    """
    known = frozenset(track_ids)
    problems: list[str] = []
    seen: set[str] = set()
    for tutorial in tutorials:
        where = tutorial.slug
        if tutorial.slug in seen:
            problems.append(f"{where}: two lessons share this slug.")
        seen.add(tutorial.slug)
        if tutorial.track not in known:
            problems.append(f"{where}: track '{tutorial.track}' is not one of the tracks.")
        if not tutorial.steps:
            problems.append(f"{where}: a lesson with no steps.")
        if tutorial.minutes <= 0:
            problems.append(f"{where}: minutes must say something honest.")
        if not tutorial.summary.strip():
            problems.append(f"{where}: no summary, so the contents row says nothing.")
        for number, step in enumerate(tutorial.steps, start=1):
            if not step.title.strip():
                problems.append(f"{where} step {number}: no title.")
            if not step.body.strip():
                problems.append(f"{where} step {number}: no body.")
            if step.command and " " in step.command:
                problems.append(f"{where} step {number}: '{step.command}' is not a command id.")
    for tutorial in tutorials:
        for slug in tutorial.then:
            if by_slug(slug, tutorials) is None:
                problems.append(f"{tutorial.slug}: points at '{slug}', which is not a lesson.")
    return problems


@dataclass(frozen=True, slots=True)
class TutorialSet:
    """One app's lessons: its tracks, its tutorials, and the questions asked of them.

    Assembled once per app in that app's content package and passed around
    read-only. Every window, document builder and test takes one of these
    rather than importing an app's modules directly, which is what lets the
    same window teach four different apps.
    """

    app_id: str
    tracks: tuple[Track, ...]
    tutorials: tuple[Tutorial, ...]

    def __len__(self) -> int:
        return len(self.tutorials)

    def slugs(self) -> tuple[str, ...]:
        return tuple(tutorial.slug for tutorial in self.tutorials)

    def find(self, slug: str) -> Tutorial | None:
        return by_slug(slug, self.tutorials)

    def in_track(self, track_id: str) -> list[Tutorial]:
        return tutorials_in(track_id, self.tutorials)

    def search(self, query: str) -> list[Tutorial]:
        return search(query, self.tutorials)

    def for_surface(self, title: str) -> list[Tutorial]:
        return for_surface(title, self.tutorials)

    def total_minutes(self) -> int:
        return sum(tutorial.minutes for tutorial in self.tutorials)

    def total_steps(self) -> int:
        return sum(tutorial.step_count for tutorial in self.tutorials)

    def problems(self) -> list[str]:
        return validate(self.tutorials, (track.id for track in self.tracks))

    def ordered(self) -> tuple[Tutorial, ...]:
        """The lessons in teaching order: by track, then as each track lists them.

        Grouping here rather than by hand means a lesson can live in whichever
        module it reads best in -- several belong to a track its module is not
        named for -- without anybody maintaining a second order.
        """
        return tuple(
            tutorial
            for track in self.tracks
            for tutorial in self.tutorials
            if tutorial.track == track.id
        )


def build(app_id: str, tracks: Sequence[Track], *groups: Sequence[Tutorial]) -> TutorialSet:
    """A :class:`TutorialSet` from an app's tracks and its content modules."""
    authored: list[Tutorial] = []
    for group in groups:
        authored.extend(group)
    unordered = TutorialSet(app_id=app_id, tracks=tuple(tracks), tutorials=tuple(authored))
    return TutorialSet(app_id=app_id, tracks=tuple(tracks), tutorials=unordered.ordered())
