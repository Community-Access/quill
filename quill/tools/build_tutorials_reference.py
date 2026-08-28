"""GATE-TUTDOC: render the tutorial book from the catalogue the app teaches from.

``standalone/radio/docs/tutorials.md`` is generated, never written by hand.
The window and the document read the same steps, so a lesson cannot be right
in one and stale in the other -- the same rule that governs the keyboard
reference (GATE-KEYREF) and the F1 help reference (GATE-HELPREF).

The keys in the document are the **shipped defaults**, resolved through
``DEFAULT_KEYMAP`` and Radio's ``APP_KEYMAPS`` overrides. The window resolves
the same step against the listener's own keymap, so somebody who has rebound
something sees their key there while the document states what the app ships
with. That difference is stated in the document's own opening rather than
left to be discovered.

Run::

    python -m quill.tools.build_tutorials_reference           # check for drift
    python -m quill.tools.build_tutorials_reference --write   # regenerate
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from quill.core.app_keymaps import APP_KEYMAPS
from quill.core.keymap import DEFAULT_KEYMAP
from quill.core.radio import tutorials as catalogue
from quill.core.radio.tutorials.model import Tutorial, key_phrase, validate

REPO_ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = REPO_ROOT / "standalone" / "radio" / "docs" / "tutorials.md"


def shipped_key(command_id: str) -> str:
    """The key Quill Radio ships with for *command_id* ("" when it has none)."""
    radio = APP_KEYMAPS.get("radio", {})
    binding = radio.get(command_id) or DEFAULT_KEYMAP.get(command_id) or ""
    return binding.strip()


def _tutorial_markdown(tutorial: Tutorial) -> list[str]:
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
        keys = key_phrase(step, shipped_key)
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


def render() -> str:
    """The whole book as Markdown."""
    problems = validate(catalogue.CATALOGUE)
    if problems:
        raise SystemExit("The tutorial catalogue is not sound:\n  " + "\n  ".join(problems))
    total = len(catalogue.CATALOGUE)
    lines: list[str] = [
        "# Quill Radio Tutorials",
        "",
        f"{total} guided tutorials, {catalogue.total_steps()} steps, about "
        f"{catalogue.total_minutes()} minutes of material in all.",
        "",
        "This document is generated from the tutorials inside Quill Radio, so it "
        "says exactly what the app teaches. To work through one with the app "
        "watching -- running a step for you, and moving you on once it can see "
        "you have done it -- open **Help > Tutorials...** instead.",
        "",
        "The keys below are the ones Quill Radio ships with. If you have rebound "
        "something in the Keyboard Manager, the tutorials *inside the app* say "
        "your key; this document cannot know it.",
        "",
        "## Contents",
        "",
    ]
    for track in catalogue.TRACKS:
        lessons = catalogue.in_track(track.id)
        lines.append(f"- **{track.title}** -- {track.blurb}")
        for tutorial in lessons:
            lines.append(f"  - {tutorial.title} ({tutorial.minutes} minutes)")
    lines.append("")
    for track in catalogue.TRACKS:
        lines.extend((f"## {track.title}", "", track.blurb, ""))
        for tutorial in catalogue.in_track(track.id):
            lines.extend(_tutorial_markdown(tutorial))
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the document")
    args = parser.parse_args(argv)
    rendered = render()
    if args.write:
        DOC_PATH.write_text(rendered, encoding="utf-8", newline="\n")
        print(f"Wrote {DOC_PATH.relative_to(REPO_ROOT)} ({len(rendered.splitlines())} lines).")
        return 0
    try:
        current = DOC_PATH.read_text(encoding="utf-8")
    except OSError:
        print(f"{DOC_PATH} is missing. Run with --write.", file=sys.stderr)
        return 1
    if current != rendered:
        print(
            f"{DOC_PATH.relative_to(REPO_ROOT)} is out of date. "
            "Run: python -m quill.tools.build_tutorials_reference --write",
            file=sys.stderr,
        )
        return 1
    print("The tutorial document matches the catalogue.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
