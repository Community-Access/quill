"""The chapter cascade is *connected*, and answers the same way for every engine.

Three things this pins, each of which was untrue and each of which cost a real
listener something:

* **One bad row does not lose an authored chapter list.** A publisher who writes
  ten chapters and ends with a twenty-second sign-off used to get nothing at
  all, because a single sub-minimum gap discarded the whole list.
* **The segmenter's window is a duration, not a count of cues.** Cue length
  belongs to whoever produced the transcript, so a count-based window answered a
  question about the episode using a fact about the file -- and answered it
  worst for the best input, a publisher's word-level transcript.
* **Nothing in the chapter package is unreachable.** Five of its eight modules
  were fully written, documented and unit-tested while being imported by nothing
  outside their own package, so the suite was green and none of it shipped.
"""

from __future__ import annotations

import ast
from functools import cache
from pathlib import Path

from quill.core.podcasts.chapter_inference import (
    TimedCue,
    segment_transcript,
    segment_with_evidence,
)
from quill.core.podcasts.chapter_sources import parse_show_notes_chapters
from quill.core.podcasts.show_note_chapters import MIN_MARK_RETENTION, usable_marks

_HOUR = 60 * 60 * 1000


# -- one bad row loses the row, not the list ------------------------------------


def test_a_short_outro_no_longer_discards_the_whole_chapter_list() -> None:
    """The Double Tap case: nine authored chapters, then a 21-second sign-off.

    The sign-off is genuinely not a chapter and is dropped. What must not happen
    -- what used to happen -- is the other nine going with it.
    """
    notes = "\n".join(
        [f"{minute}:00 Chapter {index}" for index, minute in enumerate(range(0, 45, 5), start=1)]
        + ["40:21 Contact Us"]
    )
    chapters = parse_show_notes_chapters(notes, total_ms=45 * 60_000)
    titles = [c.title for c in chapters]
    assert len(titles) == 9, "the nine well-spaced chapters survive"
    assert "Contact Us" not in titles, "the 21-second sign-off is dropped, not honoured"


def test_a_trailing_timestamp_is_a_chapter_too() -> None:
    """The Access On case: the timestamp is written after the title, not before."""
    notes = "\n".join([
        "Introduction 0:00:00",
        "AI to assist with writing 0:03:21",
        "AI in the enterprise 0:21:45",
        "Closing and contact info 0:57:47",
    ])
    assert [c.title for c in parse_show_notes_chapters(notes, total_ms=_HOUR)] == [
        "Introduction",
        "AI to assist with writing",
        "AI in the enterprise",
        "Closing and contact info",
    ]


def test_a_page_that_needs_mostly_repairing_is_still_refused() -> None:
    # Three marks in the first ten seconds of an hour is not a chapter list, and
    # dropping rows must not turn it into one.
    assert parse_show_notes_chapters("00:00 One\n00:05 Two\n00:10 Three", total_ms=_HOUR) == []


def test_the_repair_budget_is_finite() -> None:
    crammed = [(index * 1000, f"T{index}") for index in range(10)]
    assert usable_marks(crammed, total_ms=_HOUR) == []
    assert 0.0 < MIN_MARK_RETENTION <= 1.0


# -- the window is a duration, not a cue count ----------------------------------


#: Seconds per cue in the synthetic transcripts. Whisper-shaped, so the 45-second
#: default window holds a realistic number of them.
_CUE_MS = 3_000


def _speech(total_cues: int, switch_at: int) -> list[TimedCue]:
    """A transcript that changes subject exactly once, at *switch_at*."""
    before = "braille display refreshable cells notetaker perkins keyboard input".split()
    after = "podcast recording microphone interface mixer levels compression audio".split()
    cues: list[TimedCue] = []
    for index in range(total_cues):
        words = before if index < switch_at else after
        offset = (index * 3) % len(words)
        cues.append(TimedCue(index * _CUE_MS, " ".join(words[offset:] + words[:offset])))
    return cues


def _rechunk(cues: list[TimedCue], per_cue: int) -> list[TimedCue]:
    """The same words at the same moments, in cues of a different size."""
    out: list[TimedCue] = []
    for index in range(0, len(cues), per_cue):
        group = cues[index : index + per_cue]
        out.append(TimedCue(group[0].start_ms, " ".join(c.text for c in group)))
    return out


def test_rechunking_a_transcript_does_not_move_the_boundary() -> None:
    """The same episode, transcribed by engines that cue at different lengths.

    Nothing about the programme changes between these three -- the same words are
    spoken at the same moments. A segmenter whose answer changes is measuring the
    file rather than the episode.
    """
    native = _speech(400, switch_at=200)
    total_ms = 400 * _CUE_MS
    answers = {
        size: [
            c.start_ms
            for c in segment_transcript(
                native if size == 1 else _rechunk(native, size), total_ms=total_ms
            )
        ]
        for size in (1, 2, 5, 10)
    }
    switch_ms = 200 * _CUE_MS
    for size, found in answers.items():
        assert len(found) == 2, f"cues of {size} found {len(found)} boundaries, expected 2"
        assert abs(found[1] - switch_ms) <= 30_000, (
            f"cues of {size} put the boundary at {found[1]}, not near {switch_ms}"
        )


def test_a_word_level_transcript_is_handled_like_any_other() -> None:
    """The best input a publisher can ship, and the one a cue-count window broke.

    Eight cues of a word-level transcript is about three seconds of speech, so
    the old window compared three seconds either side of every gap and found
    "topic changes" everywhere.
    """
    native = _speech(400, switch_at=200)
    words: list[TimedCue] = []
    for cue in native:
        pieces = cue.text.split()
        step = max(1, _CUE_MS // len(pieces))
        words.extend(TimedCue(cue.start_ms + i * step, w) for i, w in enumerate(pieces))
    assert len(words) > 3000, "a word-level transcript really is an order of magnitude denser"
    found = [c.start_ms for c in segment_transcript(words, total_ms=400 * _CUE_MS)]
    assert len(found) == 2, f"a word-level transcript should find one boundary, found {found}"
    assert abs(found[1] - 200 * _CUE_MS) <= 30_000


def test_the_segmenter_reports_how_sure_it_was() -> None:
    """The evidence ``chapter_scoring`` has always asked for and never received."""
    obvious = segment_with_evidence(_speech(400, switch_at=200), total_ms=400 * _CUE_MS)
    assert obvious.chapters
    assert obvious.cohesion_margin > 0.0

    # An hour on one subject has no sections in it. The threshold alone cannot
    # say so -- with no spread it collapses onto the mean and every small wobble
    # clears it -- so flat cohesion is refused outright.
    uniform = segment_with_evidence(_speech(400, switch_at=400), total_ms=400 * _CUE_MS)
    assert uniform.chapters == []
    assert uniform.cohesion_margin == 0.0


# -- nothing in the package is unreachable --------------------------------------

_PACKAGE = Path(__file__).resolve().parents[4] / "quill" / "core" / "podcasts"
_TREE = Path(__file__).resolve().parents[4] / "quill"

#: Modules whose whole job is to be called from elsewhere in the app. Each was
#: written, tested and imported by nothing -- which is why this gate exists.
_MUST_BE_WIRED = (
    "chapter_cascade",
    "chapter_scoring",
    "chapter_naming",
    "chapter_sources",
    "chapter_inference",
    "chapter_skip",
    "show_note_chapters",
    "inference_budget",
)


@cache
def _import_map() -> dict[str, set[str]]:
    """``quill.core.podcasts.<module>`` -> the files outside the package importing it.

    One pass over the tree, not one per module: ``quill/`` holds a 27,000-line
    module among others, and parsing all of it eight times is slower than the
    thing being tested by several orders of magnitude.
    """
    edges: dict[str, set[str]] = {}
    prefix = "quill.core.podcasts."
    for path in _TREE.rglob("*.py"):
        if path.parent == _PACKAGE:
            continue  # the package importing itself proves nothing
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:  # pragma: no cover - unreadable file
            continue
        if prefix not in source:
            continue  # cheap string test before the expensive parse
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:  # pragma: no cover - not this gate's problem
            continue
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(prefix):
                names.append(node.module or "")
            elif isinstance(node, ast.Import):
                names.extend(a.name for a in node.names if a.name.startswith(prefix))
            for name in names:
                edges.setdefault(name.removeprefix(prefix), set()).add(str(path))
    return edges


def _importers(module: str) -> set[str]:
    """Every file in ``quill/`` that imports ``quill.core.podcasts.<module>``."""
    return _import_map().get(module, set())


@cache
def _internal_edges() -> dict[str, set[str]]:
    """``module -> the sibling modules it imports``, within the package."""
    prefix = "quill.core.podcasts."
    edges: dict[str, set[str]] = {}
    for path in _PACKAGE.glob("*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError):  # pragma: no cover
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(prefix):
                edges.setdefault(path.stem, set()).add((node.module or "").removeprefix(prefix))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(prefix):
                        edges.setdefault(path.stem, set()).add(alias.name.removeprefix(prefix))
    return edges


@cache
def _reachable() -> frozenset[str]:
    """Modules the application can actually get to.

    Reachability, not direct import: ``show_note_chapters`` is reached *through*
    ``chapter_sources``, which is itself reached from the UI, and that is a
    perfectly good way to be wired. What this catches is an island -- a module
    the application cannot arrive at by any path, however well tested.
    """
    edges = _internal_edges()
    frontier = [module for module in _MUST_BE_WIRED if _importers(module)]
    seen: set[str] = set()
    while frontier:
        module = frontier.pop()
        if module in seen:
            continue
        seen.add(module)
        frontier.extend(edges.get(module, set()) - seen)
    return frozenset(seen)


def test_every_chapter_module_is_reached_from_the_application() -> None:
    """A tested, documented, unreachable subsystem is worse than none at all.

    It reads as shipped, so the next person to touch chapters believes the
    confidence scores and the effort setting exist. Five of these eight modules
    were in exactly that state: fully written, green in the suite, and reachable
    from nothing.
    """
    reachable = _reachable()
    unwired = sorted(module for module in _MUST_BE_WIRED if module not in reachable)
    assert not unwired, (
        f"the application cannot reach these chapter modules by any import path: {unwired}. "
        "Wire them in or delete them -- do not leave them looking shipped."
    )
