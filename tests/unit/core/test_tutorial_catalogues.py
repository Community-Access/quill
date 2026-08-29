"""Every app's tutorial catalogue, checked by the same rules.

Content rots, and four apps' worth of it rots four times as fast. These are
the gates, parameterized over every app that has lessons:

* **A lesson may not promise something that does not exist.** Every command a
  step names has to be a command that app can actually resolve, and every
  window a step watches for has to be one of that app's real peer windows. A
  tutorial that tells somebody to press a key for a command nobody registered
  is worse than no tutorial.
* **Every check has to be answerable** by the shared checks or that app's own
  probe. A check nothing can answer would silently never fire, which reads as
  a lesson that ignores you.
* **The prose rules hold.** They are what keeps the sets readable rather than
  keyboard references with commentary.
* **The generated book matches the lessons** (GATE-TUTDOC).

Radio's own extra invariants -- the ordering promise, the search behaviour --
stay in ``tests/unit/core/radio/test_tutorials.py``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from quill.core.app_keymaps import APP_KEYMAPS
from quill.core.keymap import DEFAULT_KEYMAP
from quill.core.tutorials.model import Tutorial, TutorialSet
from quill.tools.build_tutorials_reference import BOOKS, catalogue_for, render
from quill.ui.tutorial_checks import WINDOW_PREFIX, known_checks, peer_windows

_ROOT = Path(__file__).resolve().parents[3]

#: Every app with lessons: its id, the keymap section its commands live in,
#: where its command ids are stated in source, and its check probe.
_APPS: tuple[tuple[str, str, tuple[str, ...], str], ...] = (
    (
        "radio",
        "radio",
        ("quill/ui/radio/palette_commands.py", "quill/apps/radio.py"),
        "quill.ui.radio.tutorial_checks",
    ),
    (
        "cast",
        "cast",
        ("quill/ui/podcasts/palette_commands.py", "quill/apps/podcasts_menu.py"),
        "quill.ui.podcasts.tutorial_checks",
    ),
    (
        "weather",
        "weather",
        ("quill/apps/weather_commands.py",),
        "quill.ui.weather.tutorial_checks",
    ),
    (
        "quill",
        "",
        ("quill/ui/main_frame_commands.py",),
        "quill.ui.quill_tutorials",
    ),
)

_APP_IDS = [entry[0] for entry in _APPS]


def _probe(app_id: str) -> object:
    module = next(entry[3] for entry in _APPS if entry[0] == app_id)
    imported = __import__(module, fromlist=["PROBE"])
    return imported.PROBE


def _catalogue(app_id: str) -> TutorialSet:
    return catalogue_for(app_id)


def _known_command_ids(app_id: str) -> set[str]:
    """Every command id this app can resolve, gathered where they are stated.

    Read as source text rather than by building a host, so this stays a pure
    test: an app's command table is a table of `host.method` references and
    cannot be imported without a window.
    """
    keymap_id, sources = next((entry[1], entry[2]) for entry in _APPS if entry[0] == app_id)
    ids: set[str] = set(APP_KEYMAPS.get(keymap_id, {}))
    ids.update(DEFAULT_KEYMAP)
    if app_id == "quill":
        # QUILL hosts the other apps' mixins -- the radio, the podcasts and the
        # weather all run inside the editor -- so their command ids are QUILL's
        # too, which is exactly what the family lesson is about.
        for section in APP_KEYMAPS.values():
            ids.update(section)
    for rel in sources:
        text = (_ROOT / rel).read_text(encoding="utf-8")
        ids.update(re.findall(r'"((?:radio|podcasts|weather|spotify|app|view)\.[a-z_0-9]+)"', text))
    # The shared transport table registers under each app's own prefix.
    transport = (_ROOT / "quill" / "core" / "radio" / "transport_commands.py").read_text(
        encoding="utf-8"
    )
    prefix = {"radio": "radio", "cast": "podcasts", "weather": "weather", "quill": ""}[app_id]
    if prefix:
        for verb in re.findall(r'"(transport\.[a-z_]+)"', transport):
            ids.add(f"{prefix}.{verb}")
            ids.add(f"{prefix}.{verb.rpartition('.')[2]}")
    return ids


def _steps(app_id: str) -> list[tuple[Tutorial, int, object]]:
    return [
        (tutorial, number, step)
        for tutorial in _catalogue(app_id).tutorials
        for number, step in enumerate(tutorial.steps, start=1)
    ]


@pytest.mark.parametrize("app_id", _APP_IDS)
def test_catalogue_is_sound(app_id: str) -> None:
    assert _catalogue(app_id).problems() == []


@pytest.mark.parametrize("app_id", _APP_IDS)
def test_every_track_has_lessons(app_id: str) -> None:
    catalogue = _catalogue(app_id)
    for track in catalogue.tracks:
        assert catalogue.in_track(track.id), f"{app_id}: {track.id} has no tutorials"


@pytest.mark.parametrize("app_id", _APP_IDS)
def test_every_command_a_step_names_exists(app_id: str) -> None:
    known = _known_command_ids(app_id)
    missing = sorted(
        f"{tutorial.slug} step {number}: {step.command}"
        for tutorial, number, step in _steps(app_id)
        if step.command and step.command not in known
    )
    assert not missing, f"{app_id} names commands it does not have:\n  " + "\n  ".join(missing)


@pytest.mark.parametrize("app_id", _APP_IDS)
def test_every_check_can_be_answered(app_id: str) -> None:
    answerable = known_checks(_probe(app_id))  # type: ignore[arg-type]
    windows = peer_windows(app_id)
    problems: list[str] = []
    for tutorial, number, step in _steps(app_id):
        if not step.check:
            continue
        if step.check.startswith(WINDOW_PREFIX):
            title = step.check[len(WINDOW_PREFIX) :]
            if title not in windows:
                problems.append(f"{tutorial.slug} step {number}: '{title}' is not a peer window")
            continue
        if step.check not in answerable:
            problems.append(f"{tutorial.slug} step {number}: unknown check '{step.check}'")
    assert not problems, f"{app_id}:\n  " + "\n  ".join(problems)


@pytest.mark.parametrize("app_id", _APP_IDS)
@pytest.mark.parametrize(
    "pattern",
    [
        # "click" as an instruction. "right-click menu" is allowed: that is the
        # name of a menu, and a screen-reader user reaches it with Shift+F10.
        r"(?<!right-)clicks?",
        r"obviously",
        r"simply just",
    ],
)
def test_no_mouse_first_or_dismissive_words(app_id: str, pattern: str) -> None:
    matcher = re.compile(pattern, re.I)
    offenders = [
        f"{tutorial.slug} step {number}"
        for tutorial, number, step in _steps(app_id)
        if matcher.search(step.body) or matcher.search(step.note)
    ]
    assert not offenders, f"{app_id}: '{pattern}' appears in: {offenders}"


@pytest.mark.parametrize("app_id", _APP_IDS)
def test_steps_say_enough_to_follow(app_id: str) -> None:
    thin = [
        f"{tutorial.slug} step {number}"
        for tutorial, number, step in _steps(app_id)
        if len(step.body) < 80 or len(step.title) > 60
    ]
    assert not thin, f"{app_id}: steps too thin, or with an overlong title: {thin}"


@pytest.mark.parametrize("app_id", _APP_IDS)
def test_most_steps_say_what_you_should_hear(app_id: str) -> None:
    """Not every step can -- a step that is a fact has nothing to listen for --
    but a set where most did not would be one nobody could check themselves
    against."""
    steps = _steps(app_id)
    with_hear = sum(1 for _tutorial, _number, step in steps if step.hear)
    assert with_hear / len(steps) > 0.9, (
        f"{app_id}: only {with_hear} of {len(steps)} steps say what you should hear"
    )


@pytest.mark.parametrize("app_id", _APP_IDS)
def test_slugs_are_unique_within_an_app(app_id: str) -> None:
    slugs = _catalogue(app_id).slugs()
    assert len(set(slugs)) == len(slugs)


@pytest.mark.parametrize("app_id", _APP_IDS)
def test_generated_book_matches_the_catalogue(app_id: str) -> None:
    """GATE-TUTDOC: the book and the window teach the same lessons."""
    book = next(entry for entry in BOOKS if entry.app_id == app_id)
    assert book.path.read_text(encoding="utf-8") == render(book), (
        f"{book.path} is out of date. Run: python -m quill.tools.build_tutorials_reference --write"
    )


def test_each_app_keeps_its_own_progress_file() -> None:
    """A lesson slug is only unique within its own set, and forgetting your
    place in one app must never forget it in another."""
    from quill.ui.podcasts.tutorials import APP as CAST
    from quill.ui.quill_tutorials import app as quill_app
    from quill.ui.radio.tutorials import APP as RADIO
    from quill.ui.weather.tutorials import APP as WEATHER

    files = {app.progress_file for app in (RADIO, CAST, WEATHER, quill_app())}
    assert len(files) == 4, files


def test_each_app_has_its_own_window_title() -> None:
    """They can all be open at once, so the titles have to differ -- and each
    has to resolve to an authored F1 purpose in its own app's catalogue."""
    from quill.core.podcasts.surface_help import PURPOSES as CAST_PURPOSES
    from quill.core.radio.surface_help import PURPOSES as RADIO_PURPOSES
    from quill.core.weather.surface_help import PURPOSES as WEATHER_PURPOSES
    from quill.ui.podcasts.tutorials import APP as CAST
    from quill.ui.quill_tutorials import app as quill_app
    from quill.ui.radio.tutorials import APP as RADIO
    from quill.ui.weather.tutorials import APP as WEATHER

    titles = {app.title for app in (RADIO, CAST, WEATHER, quill_app())}
    assert len(titles) == 4, titles
    assert RADIO.title in RADIO_PURPOSES
    assert CAST.title in CAST_PURPOSES
    assert WEATHER.title in WEATHER_PURPOSES
