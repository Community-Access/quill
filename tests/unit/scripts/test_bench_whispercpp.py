"""whisper.cpp in dictbench (scripts/bench_whispercpp.py): run the way QUILL
runs it -- the provider's own command, no initial prompt -- with the thread
count the measure needs, and the program's own memory, not this script's."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest

_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"


def _bench():
    if str(_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS))
    return importlib.import_module("bench_whispercpp")


def test_engine_names() -> None:
    bench = _bench()
    assert bench.is_whispercpp("whispercpp:base")
    assert not bench.is_whispercpp("whisper")
    assert bench.model_id("whispercpp:small") == "small"


def test_one_run_uses_the_apps_command_and_reads_the_programs_memory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    psutil = pytest.importorskip("psutil")
    bench = _bench()
    seen: list[list[str]] = []

    class FakeProcess:
        returncode = 0

        def __init__(self, argv: list[str], **_kw: Any) -> None:
            seen.append(argv)
            output = Path(argv[argv.index("-of") + 1]).with_suffix(".json")
            output.write_text(
                json.dumps({
                    "transcription": [{"offsets": {"from": 0, "to": 900}, "text": " Hi."}]
                }),
                encoding="utf-8",
            )
            self._polls = 2

        def poll(self) -> int | None:
            self._polls -= 1
            return None if self._polls > 0 else 0

        def memory_info(self) -> Any:
            class Info:
                rss = 50 * 1_048_576
                peak_wset = 300 * 1_048_576

            return Info()

    monkeypatch.setattr(psutil, "Popen", FakeProcess)
    monkeypatch.setattr(bench, "_POLL_SECONDS", 0)
    text, seconds, peak = bench.transcribe(
        "whisper-cli.exe", tmp_path / "ggml-base.bin", tmp_path / "a.wav", "en", 1
    )
    argv = seen[0]
    assert text == "Hi." and seconds >= 0 and peak == 300
    assert argv[argv.index("-t") + 1] == "1" and "-np" in argv
    assert argv[argv.index("-l") + 1] == "en"
    assert "--prompt" not in argv  # Locked Dictation's prompt is a profile, not the measure


def test_a_missing_program_or_model_says_what_to_do(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bench = _bench()
    import quill.core.speech.providers.whispercpp as provider

    monkeypatch.setattr(provider, "resolve_whisper_executable", lambda _c=None: None)
    with pytest.raises(SystemExit, match="whisper-cli was not found"):
        bench.executable(None)
    monkeypatch.setattr(provider, "_model_path", lambda _m: tmp_path / "none.bin")
    with pytest.raises(SystemExit, match="'base' model is not downloaded"):
        bench.model_path("base")
