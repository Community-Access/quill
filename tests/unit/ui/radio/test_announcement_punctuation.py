"""Every Radio announcement ends as a sentence.

Not pedantry. A screen reader applies sentence-final prosody on a full stop --
the pitch drop that marks "that thought is finished" -- and Quill Radio fires
announcements in quick succession (a station starts, the volume moves, a
download lands). An unterminated phrase runs into whatever comes next, so
"Playing WNYC" followed by "Volume 60 percent." is heard as one run-on.

71 of 240 announcements were missing it when this was written (2026-08-19), and
the pattern was inconsistent *within single files*: recordings_manager_dialog
had "Still recording; stop it before removing it." two lines from "Removed
recording {name}". Mechanical to fix and mechanical to keep, which is what this
is for.

Escape hatch: put ``# announce-punctuation: exempt`` on or just above the call.
``bounded_playback_ui`` uses it where the sentence ends before an f-string
placeholder that supplies its own.
"""

from __future__ import annotations

import ast
import pathlib

_TERMINAL = ".!?:"
_PRAGMA = "announce-punctuation: exempt"
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[4]

#: The functions that speak. ``announce`` is the injected callback the dialogs
#: receive; ``_announce`` is the method the frames and mixins carry.
_SPEAKERS = {"_announce", "announce"}


def _spoken_literals(node: ast.expr):
    """Yield the string nodes this argument can end up speaking.

    An ``IfExp`` speaks one of two literals, and both have to be checked --
    ``_announce("Paused" if playing else "Playing")`` was two violations on one
    line. An f-string is judged on its **last** element: when that is a
    placeholder, the sentence ends wherever the value does, which is nowhere.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        yield node, node.value
    elif isinstance(node, ast.JoinedStr) and node.values:
        last = node.values[-1]
        if isinstance(last, ast.Constant) and isinstance(last.value, str):
            yield node, last.value
        else:
            yield node, ""  # ends on a placeholder
    elif isinstance(node, ast.IfExp):
        yield from _spoken_literals(node.body)
        yield from _spoken_literals(node.orelse)


def _violations(path: pathlib.Path) -> list[str]:
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    found: list[str] = []
    for call in ast.walk(ast.parse(source)):
        if not isinstance(call, ast.Call):
            continue
        func = call.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        if name not in _SPEAKERS:
            continue
        # Measured from the *call*, not from the string: an announcement whose
        # f-string sits on its own continuation line puts the string three or
        # four lines below the comment, and a window measured from the string
        # silently misses the pragma (which is how a stray second full stop got
        # into bounded_playback_ui the first time).
        nearby = "\n".join(lines[max(0, call.lineno - 4) : call.lineno])
        if _PRAGMA in nearby:
            continue
        for argument in call.args:
            for node, text in _spoken_literals(argument):
                if text and text.rstrip()[-1:] in _TERMINAL:
                    continue
                if not text and not isinstance(node, ast.JoinedStr):
                    continue  # an empty literal says nothing at all
                shown = text or "<ends on a placeholder>"
                found.append(f"{path.name}:{node.lineno}: {shown[-60:]}")
    return found


def _radio_sources() -> list[pathlib.Path]:
    return sorted((_REPO_ROOT / "quill" / "ui" / "radio").glob("*.py")) + sorted(
        (_REPO_ROOT / "quill" / "apps").glob("radio*.py")
    )


def test_every_radio_announcement_ends_as_a_sentence() -> None:
    offenders = [line for path in _radio_sources() for line in _violations(path)]

    assert not offenders, "Announcements missing terminal punctuation:\n" + "\n".join(offenders)


def test_the_checker_catches_the_shapes_that_were_actually_wrong(tmp_path) -> None:
    """The four spellings this found in the tree, so the gate cannot rot."""
    sample = tmp_path / "sample.py"
    sample.write_text(
        "def f(host, announce):\n"
        '    host._announce("Radio stopped")\n'
        '    host._announce(f"Playing {name}")\n'
        '    announce("Paused" if x else "Playing")\n'
        '    host._announce("Stopped.")\n'
        "    # announce-punctuation: exempt\n"
        '    host._announce("fine because exempt")\n',
        encoding="utf-8",
    )

    offenders = _violations(sample)

    assert len(offenders) == 4, offenders
    assert all("exempt" not in line for line in offenders)


def test_the_checker_reads_the_real_tree() -> None:
    """A gate that scans nothing passes forever."""
    assert len(_radio_sources()) > 50
