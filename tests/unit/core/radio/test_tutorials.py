"""The tutorial catalogue is content, and content rots. These are its gates.

Three kinds of check here, in order of how badly a failure would hurt:

* **A lesson may not promise something that does not exist.** Every command a
  step names has to be a real Quill Radio command id, and every window a step
  watches for has to be a real peer window. A tutorial that tells somebody to
  press a key for a command nobody registered is worse than no tutorial.
* **Every check has to be answerable.** A ``check`` the live half cannot
  evaluate would silently never fire, which reads as a lesson that ignores
  you.
* **The prose rules the model's docstring states have to hold.** They are what
  keeps the set readable rather than a keyboard reference with commentary.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from quill.core.app_keymaps import APP_KEYMAPS
from quill.core.keymap import DEFAULT_KEYMAP
from quill.core.radio import tutorials as catalogue
from quill.core.radio.tutorials.model import Tutorial, validate
from quill.ui.radio.tutorial_checks import PEER_WINDOW_TITLES, WINDOW_PREFIX, known_checks

_ROOT = Path(__file__).resolve().parents[4]


def _known_command_ids() -> set[str]:
    """Every command id Quill Radio can resolve, gathered where they are stated.

    Three sources, because the app has three: the palette table, the app's own
    keymap, and the shared transport table (which registers under this app's
    prefix). Read as source text rather than by building a host, so this stays
    a pure test.
    """
    ids: set[str] = set(APP_KEYMAPS.get("radio", {}))
    ids.update(DEFAULT_KEYMAP)
    palette = (_ROOT / "quill" / "ui" / "radio" / "palette_commands.py").read_text(encoding="utf-8")
    ids.update(re.findall(r'"((?:radio|spotify|app|view)\.[a-z_0-9]+)"', palette))
    transport = (_ROOT / "quill" / "core" / "radio" / "transport_commands.py").read_text(
        encoding="utf-8"
    )
    for verb in re.findall(r'"(transport\.[a-z_]+)"', transport):
        ids.add(f"radio.{verb}")
        ids.add(f"radio.{verb.rpartition('.')[2]}")
    return ids


def _steps() -> list[tuple[Tutorial, int, object]]:
    return [
        (tutorial, number, step)
        for tutorial in catalogue.CATALOGUE
        for number, step in enumerate(tutorial.steps, start=1)
    ]


def test_catalogue_is_sound() -> None:
    assert validate(catalogue.CATALOGUE) == []


def test_every_track_has_lessons() -> None:
    for track in catalogue.TRACKS:
        assert catalogue.in_track(track.id), f"{track.id} has no tutorials"


def test_every_command_a_step_names_exists() -> None:
    known = _known_command_ids()
    missing = sorted(
        f"{tutorial.slug} step {number}: {step.command}"
        for tutorial, number, step in _steps()
        if step.command and step.command not in known
    )
    assert not missing, "steps name commands this app does not have:\n  " + "\n  ".join(missing)


def test_every_check_can_be_answered() -> None:
    answerable = known_checks()
    problems: list[str] = []
    for tutorial, number, step in _steps():
        if not step.check:
            continue
        if step.check.startswith(WINDOW_PREFIX):
            title = step.check[len(WINDOW_PREFIX) :]
            if title not in PEER_WINDOW_TITLES:
                problems.append(f"{tutorial.slug} step {number}: '{title}' is not a peer window")
            continue
        if step.check not in answerable:
            problems.append(f"{tutorial.slug} step {number}: unknown check '{step.check}'")
    assert not problems, "\n  ".join(problems)


def test_peer_window_titles_are_the_titles_the_ui_registers() -> None:
    """The watched titles are the ones ``WindowManager.register`` is given.

    A source-level assertion on purpose: it is the seam that would break
    silently. Rename the window and the lesson would simply never notice you
    opened it, which is indistinguishable from a lesson that is not watching.
    """
    registered: set[str] = {"Quill Radio", "Now Playing", "Song History"}
    for path in (_ROOT / "quill" / "ui" / "radio").glob("*.py"):
        source = path.read_text(encoding="utf-8")
        registered.update(re.findall(r'_windows\.register\([^,]+,\s*"([^"]+)"', source))
        if re.search(r"_windows\.register\([^,]+,\s*TITLE\b", source):
            match = re.search(r'^TITLE = "([^"]+)"', source, re.M)
            if match:
                registered.add(match.group(1))
    unknown = sorted(PEER_WINDOW_TITLES - registered)
    assert not unknown, f"watched windows nothing registers: {unknown}"


@pytest.mark.parametrize(
    "pattern",
    [
        # "click" as an instruction. "right-click menu" is allowed: that is the
        # name of a menu, and a screen-reader user reaches it with Shift+F10,
        # which every lesson that mentions it also says.
        r"(?<!right-)clicks?",
        r"obviously",
        r"simply just",
        r"just click",
    ],
)
def test_no_mouse_first_or_dismissive_words(pattern: str) -> None:
    """A tutorial for a screen-reader user is written in keys, not clicks.

    "Obviously" and its family are banned for the same reason: a sentence that
    tells somebody a thing is obvious is a sentence that costs them something
    when it is not.
    """
    matcher = re.compile(pattern, re.I)
    offenders = [
        f"{tutorial.slug} step {number}"
        for tutorial, number, step in _steps()
        if matcher.search(step.body) or matcher.search(step.note)
    ]
    assert not offenders, f"'{pattern}' appears in: {offenders}"


def test_steps_say_enough_to_follow() -> None:
    thin = [
        f"{tutorial.slug} step {number}"
        for tutorial, number, step in _steps()
        if len(step.body) < 80 or len(step.title) > 60
    ]
    assert not thin, f"steps too thin to follow, or with an overlong title: {thin}"


def test_most_steps_say_what_you_should_hear() -> None:
    """Not every step can -- a step that is a fact has nothing to listen for --
    but a set where most of them did not would be a set nobody could check
    themselves against."""
    total = len(_steps())
    with_hear = sum(1 for _tutorial, _number, step in _steps() if step.hear)
    assert with_hear / total > 0.9, f"only {with_hear} of {total} steps say what you should hear"


def test_the_first_hour_is_first() -> None:
    """Ordering is a promise the contents tree makes; pin it."""
    assert catalogue.CATALOGUE[0].track == "first-hour"
    assert catalogue.CATALOGUE[0].slug == "first-station"


def test_search_finds_by_word_from_anywhere_in_a_lesson() -> None:
    assert any(t.slug == "book-a-show" for t in catalogue.search("schedule"))
    # A key somebody found and cannot place, matched out of a step's own keys.
    assert catalogue.search("Shift+F10")
    # Every word has to appear, so two words no single lesson holds match none.
    assert catalogue.search("spotify librivox xmltv") == []


def test_surface_filter_answers_for_a_window() -> None:
    here = catalogue.for_surface("Browse Stations")
    assert here, "no tutorials claim Browse Stations"
    assert all("Browse Stations" in tutorial.surfaces for tutorial in here)


def test_generated_document_matches_the_catalogue() -> None:
    """GATE-TUTDOC: the book and the window teach the same lessons."""
    from quill.tools.build_tutorials_reference import DOC_PATH, render

    assert DOC_PATH.read_text(encoding="utf-8") == render(), (
        "standalone/radio/docs/tutorials.md is out of date. Run: "
        "python -m quill.tools.build_tutorials_reference --write"
    )
