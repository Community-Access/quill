"""The 30 and 60 minute dictation soak (dict.md section 8, B-3).

Recorded audio, fed at live pace through the real recogniser (the real
engine and Silero voice detector, its worker thread and watchdogs) and the
real controller, into the shared ``ExternalDocument`` -- whose typing is a
``FakeTarget`` that records what would have been typed and **never sends a
key to any window**. No microphone is opened and nothing is played.

**Off unless asked, and never in CI.** It runs only with
``QUILL_DICTATION_SOAK=1`` and a folder of recordings, and is skipped
whenever ``CI`` is set::

    $env:QUILL_DICTATION_SOAK = "1"
    $env:QUILL_DICTATION_SOAK_AUDIO = "D:\\bench\\librivox-heldout-en"   # WAVs + transcripts.txt
    $env:QUILL_DICTATION_SOAK_MINUTES = "30"                           # or 60
    $env:QUILL_DICTATION_SOAK_ENGINE = "moonshine"                     # any engine id
    pytest tests/stability/test_dictation_soak.py -m slow -p no:xdist -s

The recordings are played in order, round and round, until the minutes are
used up; long B-1a chapters suit it best. A reference written ``!scratch
that`` (B-1c's convention) is a spoken command, so a folder can mix commands
in. It asserts what B-3 asks for:

* **no lost phrase** -- every recording produced at least one phrase;
* **no duplicated phrase** -- no recording produced more phrases than it has
  sentences plus one (a pause inside a sentence may split it once), and no
  phrase was typed twice in a row;
* **no command text typed** -- the words of a spoken command never reached
  the field;
* **flat memory** -- the process's resident memory in the last third of the
  run is within 15 percent (plus 40 MB) of the first third
  (``bench_live.memory_is_flat``);
* **microphone closed after stop** -- the recorded stream closed, the worker
  ended and the controller holds no recogniser.

It also writes a JSON summary (``QUILL_DICTATION_SOAK_RESULTS``, default
``soak-<date>.json`` in the system temporary folder), which includes B-5's
correction efficiency when the folder has a ``corrections.json``.
"""

from __future__ import annotations

import datetime as dt
import importlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest

_REPO = Path(__file__).resolve().parents[2]
_SCRIPTS = _REPO / "scripts"

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(bool(os.environ.get("CI")), reason="the soak never runs in CI"),
    pytest.mark.skipif(
        os.environ.get("QUILL_DICTATION_SOAK") != "1",
        reason="the soak runs only with QUILL_DICTATION_SOAK=1 (it takes 30 minutes or more)",
    ),
]

MINUTES = float(os.environ.get("QUILL_DICTATION_SOAK_MINUTES") or 30)


def _script(name: str) -> Any:
    if str(_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS))
    return importlib.import_module(name)


def _plan(folder: Path, minutes: float) -> list[Any]:
    """The folder's recordings, in order, round and round, for *minutes*."""
    dictbench = _script("dictbench")
    live = _script("bench_live")
    transcripts = dictbench.read_transcripts(folder)
    audio = {name: dictbench.read_wav(folder / name) for name in transcripts}
    clips: list[Any] = []
    seconds = 0.0
    while seconds < minutes * 60:
        for name, reference in transcripts.items():
            clips.append(live.Clip(f"{len(clips):05d}-{name}", audio[name], reference))
            seconds += len(audio[name]) / 16_000 + 2.5
            if seconds >= minutes * 60:
                break
    return clips


def _sentences(reference: str) -> int:
    return max(1, len(re.findall(r"[.?!]+", reference)))


@pytest.mark.timeout(int(MINUTES * 60 * 1.5) + 600)
def test_dictation_soak() -> None:
    folder = Path(os.environ.get("QUILL_DICTATION_SOAK_AUDIO") or "")
    if not (folder / "transcripts.txt").is_file():
        pytest.skip("set QUILL_DICTATION_SOAK_AUDIO to a folder of WAVs and transcripts.txt")
    live = _script("bench_live")
    engine = os.environ.get("QUILL_DICTATION_SOAK_ENGINE") or "moonshine"
    clips = _plan(folder, MINUTES)
    session = live.run_session(clips, engine=engine, pace=1.0, memory_every=30.0)

    per_clip = session.phrases_per_clip()
    lost = [c.name for c, n in zip(clips, per_clip, strict=True) if n == 0]
    doubled = [
        c.name
        for c, n in zip(clips, per_clip, strict=True)
        if n > _sentences(c.reference.removeprefix("!")) + 1
    ]
    repeats = [
        text
        for before, text in zip(session.target.typed, session.target.typed[1:], strict=False)
        if text.strip() and text == before
    ]
    command_words = {
        " ".join(c.reference.removeprefix("!").lower().split())
        for c in clips
        if c.reference.startswith("!")
    }
    typed = " ".join(" ".join(session.target.typed).lower().split())
    commands_typed = sorted(w for w in command_words if w and w in typed)
    summary: dict[str, Any] = {
        "date": dt.date.today().isoformat(),
        "engine": engine,
        "minutes": MINUTES,
        "recordings": len(clips),
        "phrases": len(session.phrases),
        "lost": lost,
        "doubled": doubled,
        "typed_twice_in_a_row": repeats,
        "commands_typed": commands_typed,
        "memory_mb": session.memory_mb,
        "memory_flat": live.memory_is_flat(session.memory_mb),
        "microphone_closed": session.microphone_closed,
        "microphone_reopened": session.reopened,
        "said": session.said[-20:],
    }
    corrections = folder / "corrections.json"
    if corrections.is_file():
        summary["correction_efficiency"] = live.correction_efficiency(
            json.loads(corrections.read_text(encoding="utf-8")), session.target.text
        )
    results = Path(
        os.environ.get("QUILL_DICTATION_SOAK_RESULTS")
        or Path(tempfile.gettempdir()) / f"soak-{summary['date']}.json"
    )
    results.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Soak results: {results}")

    assert session.ui_errors == []
    assert not lost, f"recordings that produced no phrase: {lost[:10]}"
    assert not doubled, f"recordings that produced too many phrases: {doubled[:10]}"
    assert not repeats, f"typed twice in a row: {repeats[:5]}"
    assert not commands_typed, f"spoken commands typed as words: {commands_typed}"
    assert summary["memory_flat"], f"memory grew: {session.memory_mb}"
    assert session.microphone_closed
