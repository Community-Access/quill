"""GATE-TUTDOC: render each app's tutorial book from the lessons it teaches.

Four apps have lessons, and each ships a Markdown book beside its user guide:

* Quill Radio -- ``standalone/radio/docs/tutorials.md``
* QUILL Cast -- ``standalone/cast/docs/tutorials.md``
* Quill Weather -- ``standalone/weather/docs/tutorials.md``
* QUILL -- ``docs/user guide/tutorials.md``

Every one is generated, never written by hand. The window and the document
read the same steps, so a lesson cannot be right in one and stale in the other
-- the same rule that governs the keyboard reference (GATE-KEYREF) and the F1
help reference (GATE-HELPREF).

The keys in a document are the **shipped defaults**, resolved through
``DEFAULT_KEYMAP`` and that app's ``APP_KEYMAPS`` overrides. The window
resolves the same step against the listener's own keymap, so somebody who has
rebound something sees their key there while the document states what the app
ships with. That difference is stated in each document's own opening rather
than left to be discovered.

Run::

    python -m quill.tools.build_tutorials_reference           # check for drift
    python -m quill.tools.build_tutorials_reference --write   # regenerate
    python -m quill.tools.build_tutorials_reference --app radio --write
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from quill.core.app_keymaps import APP_KEYMAPS
from quill.core.keymap import DEFAULT_KEYMAP
from quill.core.tutorials.model import Tutorial, TutorialSet, key_phrase

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class Book:
    """One app's document: where it goes, and what it is called there."""

    app_id: str
    #: The app's display name, as its own documents say it.
    app_name: str
    #: Where the book is written, relative to the repo root.
    path: Path
    #: The keymap section to resolve shipped keys against.
    keymap_id: str
    #: How to reach the lessons from inside the app.
    door: str


BOOKS: tuple[Book, ...] = (
    Book(
        "radio",
        "Quill Radio",
        REPO_ROOT / "standalone" / "radio" / "docs" / "tutorials.md",
        "radio",
        "Help > Tutorials...",
    ),
    Book(
        "cast",
        "QUILL Cast",
        REPO_ROOT / "standalone" / "cast" / "docs" / "tutorials.md",
        "podcasts",
        "Help > Tutorials...",
    ),
    Book(
        "weather",
        "Quill Weather",
        REPO_ROOT / "standalone" / "weather" / "docs" / "tutorials.md",
        "weather",
        "Help > Tutorials...",
    ),
    Book(
        "quill",
        "QUILL",
        REPO_ROOT / "docs" / "user guide" / "tutorials.md",
        "",
        "Help > Tutorials...",
    ),
)


def catalogue_for(app_id: str) -> TutorialSet:
    """The lessons for *app_id*, imported on demand."""
    if app_id == "radio":
        from quill.core.radio.tutorials import CATALOGUE

        return CATALOGUE
    if app_id == "cast":
        from quill.core.podcasts.tutorials import CATALOGUE as CAST

        return CAST
    if app_id == "weather":
        from quill.core.weather.tutorials import CATALOGUE as WEATHER

        return WEATHER
    if app_id == "quill":
        from quill.core.quill_tutorials import CATALOGUE as QUILL

        return QUILL
    raise SystemExit(f"No tutorials for app '{app_id}'.")


def shipped_key(keymap_id: str) -> object:
    """A lookup answering the key *keymap_id*'s app ships with for a command."""
    overrides = APP_KEYMAPS.get(keymap_id, {}) if keymap_id else {}

    def lookup(command_id: str) -> str:
        binding = overrides.get(command_id) or DEFAULT_KEYMAP.get(command_id) or ""
        return binding.strip()

    return lookup


def _tutorial_markdown(tutorial: Tutorial, catalogue: TutorialSet, key_for: object) -> list[str]:
    lines: list[str] = [
        f"### {tutorial.title}",
        "",
        tutorial.summary,
        "",
        f"*{tutorial.step_count} steps, about {tutorial.minutes} minutes.*",
        "",
    ]
    for number, step in enumerate(tutorial.steps, start=1):
        lines.append(f"{number}. **{step.title}.** {step.body}")
        keys = key_phrase(step, key_for)  # type: ignore[arg-type]
        if keys:
            lines.append(f"   - Keys: {keys}")
        if step.hear:
            lines.append(f"   - You should hear: {step.hear}")
        if step.note:
            lines.append(f"   - Worth knowing: {step.note}")
        lines.append("")
    if tutorial.closing:
        lines.extend((tutorial.closing, ""))
    if tutorial.then:
        names = [
            found.title
            for found in (catalogue.find(slug) for slug in tutorial.then)
            if found is not None
        ]
        if names:
            lines.extend(("Next: " + "; ".join(names) + ".", ""))
    return lines


def render(book: Book) -> str:
    """One app's whole book as Markdown."""
    catalogue = catalogue_for(book.app_id)
    problems = catalogue.problems()
    if problems:
        raise SystemExit(
            f"The {book.app_name} tutorial catalogue is not sound:\n  " + "\n  ".join(problems)
        )
    key_for = shipped_key(book.keymap_id)
    lines: list[str] = [
        f"# {book.app_name} Tutorials",
        "",
        f"{len(catalogue)} guided tutorials, {catalogue.total_steps()} steps, about "
        f"{catalogue.total_minutes()} minutes of material in all.",
        "",
        f"This document is generated from the tutorials inside {book.app_name}, so it "
        f"says exactly what the app teaches. To work through one with the app "
        f"watching -- running a step for you, and moving you on once it can see "
        f"you have done it -- open **{book.door}** instead.",
        "",
        f"The keys below are the ones {book.app_name} ships with. If you have rebound "
        "something in the Keyboard Manager, the tutorials *inside the app* say "
        "your key; this document cannot know it.",
        "",
        "## Contents",
        "",
    ]
    for track in catalogue.tracks:
        lessons = catalogue.in_track(track.id)
        lines.append(f"- **{track.title}** -- {track.blurb}")
        for tutorial in lessons:
            lines.append(f"  - {tutorial.title} ({tutorial.minutes} minutes)")
    lines.append("")
    for track in catalogue.tracks:
        lines.extend((f"## {track.title}", "", track.blurb, ""))
        for tutorial in catalogue.in_track(track.id):
            lines.extend(_tutorial_markdown(tutorial, catalogue, key_for))
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the documents")
    parser.add_argument("--app", default="", help="only this app (radio, cast, weather, quill)")
    args = parser.parse_args(argv)

    books = [book for book in BOOKS if not args.app or book.app_id == args.app]
    if not books:
        print(f"No tutorial book for app '{args.app}'.", file=sys.stderr)
        return 1

    stale: list[str] = []
    for book in books:
        rendered = render(book)
        if args.write:
            book.path.parent.mkdir(parents=True, exist_ok=True)
            book.path.write_text(rendered, encoding="utf-8", newline="\n")
            print(f"Wrote {book.path.relative_to(REPO_ROOT)} ({len(rendered.splitlines())} lines).")
            continue
        try:
            current = book.path.read_text(encoding="utf-8")
        except OSError:
            stale.append(f"{book.path.relative_to(REPO_ROOT)} is missing")
            continue
        if current != rendered:
            stale.append(f"{book.path.relative_to(REPO_ROOT)} is out of date")
    if args.write:
        return 0
    if stale:
        print(
            "\n".join(stale) + "\nRun: python -m quill.tools.build_tutorials_reference --write",
            file=sys.stderr,
        )
        return 1
    print(f"{len(books)} tutorial document(s) match their catalogues.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
