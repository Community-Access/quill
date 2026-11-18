"""The guides' reading grade, and whether each tutorial fits its promised time.

From EdSharp's history (complete.md Part 4): its documentation is checked at
about ninth grade, and each tutorial against the length it promises. QUILL's
guides are long and were never measured; this measures them.

* **Reading grade**: the Flesch-Kincaid grade of each Markdown chapter under
  ``docs/user guide``, prose only (code, tables, headings and lists of keys are
  left out, because a chord is not a hard word).
* **Tutorial length**: an estimate of how long each tutorial takes -- reading
  its steps aloud at 150 words a minute, plus half a minute to do each step --
  against the minutes it promises, with a quarter's margin for a rough estimate.

Both are a ratchet against ``quill/tools/reading_check.json``, the way the
module size budget is: what is too hard or too long today is written down, a
chapter may not get harder than it was by more than half a grade, a new chapter
must come in at or under :data:`GRADE_TARGET`, and a tutorial may not run
longer than it promises unless it is already listed. ``--write`` takes a new
snapshot after an improvement.

    python -m quill.tools.reading_check            # check
    python -m quill.tools.reading_check --report   # every chapter, hardest first
    python -m quill.tools.reading_check --write    # new snapshot
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GUIDES = REPO_ROOT / "docs" / "user guide"
SNAPSHOT = Path(__file__).with_name("reading_check.json")

#: About ninth grade, EdSharp's target.
GRADE_TARGET = 9.0
#: How much harder a listed chapter may get before the check fails.
GRADE_SLACK = 0.5
WORDS_PER_MINUTE = 150
MINUTES_PER_STEP = 0.5
#: The estimate is rough, so a tutorial is "over" only past this share of
#: its promise (a five-minute lesson at six minutes is honest enough).
TIME_MARGIN = 1.25

_FENCE = re.compile(r"^```.*?^```", re.M | re.S)
_WORD = re.compile(r"[A-Za-z][A-Za-z']*")
_SENTENCE_END = re.compile(r"[.!?]+(?:\s|$)")


def _prose(markdown: str) -> str:
    text = _FENCE.sub(" ", markdown)
    kept = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "|", ">", "<", "!")):
            continue
        stripped = re.sub(r"`[^`]*`", " ", stripped)
        stripped = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", stripped)
        stripped = re.sub(r"^([-*+]|\d+\.)\s+", "", stripped)
        kept.append(stripped.replace("**", "").replace("*", ""))
    return " ".join(kept)


def _syllables(word: str) -> int:
    word = word.lower().strip("'")
    if len(word) <= 3:
        return 1
    word = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", word)
    word = re.sub(r"^y", "", word)
    return max(1, len(re.findall(r"[aeiouy]{1,2}", word)))


def grade(text: str) -> float:
    """Flesch-Kincaid grade of *text*; 0.0 for text with no sentences."""
    words = _WORD.findall(text)
    sentences = max(1, len(_SENTENCE_END.findall(text)))
    if len(words) < 30:
        return 0.0
    syllables = sum(_syllables(word) for word in words)
    return round(0.39 * len(words) / sentences + 11.8 * syllables / len(words) - 15.59, 1)


def chapter_grades(root: Path = GUIDES) -> dict[str, float]:
    found: dict[str, float] = {}
    for path in sorted(root.rglob("*.md")):
        relative = path.relative_to(REPO_ROOT).as_posix()
        found[relative] = grade(_prose(path.read_text(encoding="utf-8")))
    return found


def tutorial_minutes() -> dict[str, tuple[int, float]]:
    """``slug -> (promised minutes, estimated minutes)`` for every catalogue."""
    from quill.tools.build_tutorials_reference import BOOKS, catalogue_for

    found: dict[str, tuple[int, float]] = {}
    for book in BOOKS:
        catalogue = catalogue_for(book.app_id)
        for tutorial in catalogue.tutorials:
            words = 0
            for step in tutorial.steps:
                for part in (step.title, step.body, step.hear, step.check, step.note):
                    words += len(_WORD.findall(part))
            estimate = words / WORDS_PER_MINUTE + MINUTES_PER_STEP * len(tutorial.steps)
            found[f"{book.app_id}:{tutorial.slug}"] = (tutorial.minutes, round(estimate, 1))
    return found


def snapshot() -> dict[str, object]:
    grades = chapter_grades()
    tutorials = tutorial_minutes()
    return {
        "grade_target": GRADE_TARGET,
        "chapters_over_target": {
            path: value for path, value in grades.items() if value > GRADE_TARGET
        },
        "tutorials_over_time": {
            slug: estimate
            for slug, (promised, estimate) in tutorials.items()
            if estimate > promised
        },
    }


def problems(saved: dict[str, object] | None = None) -> list[str]:
    if saved is None:
        saved = json.loads(SNAPSHOT.read_text(encoding="utf-8")) if SNAPSHOT.exists() else {}
    listed_chapters = dict(saved.get("chapters_over_target", {}))  # type: ignore[arg-type]
    listed_tutorials = dict(saved.get("tutorials_over_time", {}))  # type: ignore[arg-type]
    found: list[str] = []
    for path, value in chapter_grades().items():
        if value <= GRADE_TARGET:
            continue
        before = listed_chapters.get(path)
        if before is None:
            found.append(f"{path}: reading grade {value}, over the target of {GRADE_TARGET}.")
        elif value > float(before) + GRADE_SLACK:
            found.append(f"{path}: reading grade {value}, harder than its {before}.")
    for slug, (promised, estimate) in tutorial_minutes().items():
        if estimate > promised * TIME_MARGIN and slug not in listed_tutorials:
            found.append(f"{slug}: about {estimate} minutes to do, but it promises {promised}.")
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="take a new snapshot")
    parser.add_argument("--report", action="store_true", help="every chapter, hardest first")
    args = parser.parse_args(argv)
    if args.write:
        SNAPSHOT.write_text(json.dumps(snapshot(), indent=2, sort_keys=True) + "\n", "utf-8")
        print(f"wrote {SNAPSHOT.relative_to(REPO_ROOT).as_posix()}")
        return 0
    if args.report:
        for path, value in sorted(chapter_grades().items(), key=lambda item: -item[1]):
            print(f"{value:5.1f}  {path}")
        for slug, (promised, estimate) in sorted(tutorial_minutes().items()):
            mark = "  over" if estimate > promised * TIME_MARGIN else ""
            print(f"{estimate:5.1f} of {promised:3d} min  {slug}{mark}")
        return 0
    found = problems()
    for line in found:
        print(line)
    print(f"Reading check: {'OK' if not found else str(len(found)) + ' problem(s)'}.")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
