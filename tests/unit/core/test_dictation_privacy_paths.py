"""Privacy assertions for dictation's newer paths (dict.md section 8, B-7).

* **No network with AI off.** A whole dictation session into another program
  -- phrases, commands, a pause when the focus moves, held words, resume --
  makes no connection at all.
* **Dictated words are not left on disk.** While words are held, no file in
  the data folder holds them as plain text; once they are delivered, the
  live-dictation recovery folder (D-5's ``recovery/live-dictation``, when it
  exists) holds nothing. Rescue may write there, but only encrypted, and it
  must delete each entry on delivery; this test keeps that promise honest
  whatever shape Rescue takes.
* **Dictated words are not logged** (the trace is off by default).
* **The benchmark tools are not a back door**: only the two download scripts
  use the network, and the rest import nothing that could.

Everything is faked: nothing is typed, recorded or sent.
"""

from __future__ import annotations

import ast
import logging
import socket
import urllib.request
from pathlib import Path
from typing import Any

import pytest

from quill.core.windows_dictation import (
    DictationController,
    DictationPreferences,
    RecognizedPhrase,
    words_from_text,
)
from quill.core.windows_dictation.target_lock import LockedTarget
from quill.ui.windows_dictation_external import ExternalDocument

_REPO = Path(__file__).resolve().parents[3]
SECRET = "violet harbour ledger"


class _Feedback:
    def __init__(self) -> None:
        self.said: list[str] = []

    def has_cue(self, _moment: Any) -> bool:
        return False

    def cue(self, _moment: Any) -> None:
        pass

    def say(self, text: str) -> None:
        self.said.append(text)

    def read_back(self, _text: str) -> None:
        pass

    def show(self, _text: str) -> None:
        pass

    def state_changed(self, _state: Any) -> None:
        pass

    def show_commands(self) -> None:
        pass


class _Recognizer:
    def start(self, _microphone: str) -> None:
        pass

    def stop(self) -> None:
        pass


@pytest.fixture()
def no_network(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    attempts: list[str] = []

    def refuse(*args: Any, **_kwargs: Any) -> None:
        attempts.append(repr(args[:2]))
        raise OSError("network refused by the privacy test")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(urllib.request, "urlopen", refuse)
    return attempts


@pytest.fixture()
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    folder = tmp_path / "data"
    folder.mkdir()
    monkeypatch.setenv("QUILL_DATA_DIR", str(folder))
    monkeypatch.delenv("QUILL_DICTATION_TRACE", raising=False)
    return folder


def _session() -> tuple[DictationController, dict[str, Any], _Feedback]:
    world: dict[str, Any] = {"field": ("notepad", 1, "edit-1"), "typed": []}
    inner = ExternalDocument(
        problem=lambda: "",
        where=lambda: world["field"],
        type_text=lambda text, *_a: world["typed"].append(text) or True,
        backspace=lambda count: world["typed"].append(f"<{count}>") or True,
    )
    document = LockedTarget(inner, where=lambda: world["field"], advice="Use Resume.")
    feedback = _Feedback()
    controller = DictationController(
        recognizer=lambda _c, _p: _Recognizer(),
        document=document,
        feedback=feedback,
        preferences=lambda: DictationPreferences(phrase_feedback="silent"),
    )
    controller.start()
    return controller, world, feedback


def _hear(controller: DictationController, text: str) -> None:
    controller.on_phrase(RecognizedPhrase(words_from_text(text)))


def _files_holding(folder: Path, text: str) -> list[Path]:
    found = []
    for path in folder.rglob("*"):
        if path.is_file():
            data = path.read_bytes()
            if text.encode("utf-8") in data or text.encode("utf-16-le") in data:
                found.append(path)
    return found


def test_a_whole_session_with_ai_off_makes_no_connection(
    no_network: list[str], data_dir: Path
) -> None:
    preferences = DictationPreferences()
    assert not preferences.openai_consent  # AI is off by default
    controller, world, _feedback = _session()
    _hear(controller, "hello there")
    _hear(controller, "new paragraph")
    _hear(controller, "scratch that")
    world["field"] = ("mail", 2, "edit-9")  # the focus moves: paused, words held
    _hear(controller, SECRET)
    world["field"] = ("notepad", 1, "edit-1")
    controller.resume_held()
    controller.stop()
    assert no_network == []
    assert any(SECRET in text.lower() for text in world["typed"])  # delivered on resume


def test_held_words_are_never_on_disk_as_plain_text_and_gone_once_delivered(
    data_dir: Path,
) -> None:
    controller, world, _feedback = _session()
    world["field"] = ("mail", 2, "edit-9")
    _hear(controller, SECRET)
    assert controller.held_count == 1
    assert _files_holding(data_dir, SECRET) == []  # Rescue may write, but never plain
    assert _files_holding(data_dir, SECRET.capitalize()) == []
    world["field"] = ("notepad", 1, "edit-1")
    assert controller.resume_held()
    controller.stop()
    rescue = data_dir / "recovery" / "live-dictation"
    left = [p for p in rescue.rglob("*") if p.is_file()] if rescue.exists() else []
    assert left == [], "delivered words must leave no Rescue entry behind"


def test_dictated_words_are_not_logged(data_dir: Path, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG):
        controller, world, _feedback = _session()
        _hear(controller, SECRET)
        world["field"] = ("mail", 2, "edit-9")
        _hear(controller, SECRET + " again")
        controller.stop()
    logged = " ".join(record.getMessage().lower() for record in caplog.records)
    assert SECRET not in logged


_NETWORK_MODULES = {"socket", "urllib", "http", "requests", "httpx", "aiohttp", "ftplib"}
#: The only two benchmark tools that may download, each by a person, never in CI.
_DOWNLOADERS = {"fetch_bench_audio.py", "bench_librivox.py"}


def test_only_the_download_scripts_of_the_benchmark_use_the_network() -> None:
    scripts = sorted((_REPO / "scripts").glob("bench_*.py")) + [_REPO / "scripts" / "dictbench.py"]
    scripts.append(_REPO / "scripts" / "fetch_bench_audio.py")
    offenders = []
    for path in scripts:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        } | {
            (node.module or "").split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        if imported & _NETWORK_MODULES and path.name not in _DOWNLOADERS:
            offenders.append(path.name)
        if path.name in _DOWNLOADERS:
            source = path.read_text(encoding="utf-8")
            assert 'os.environ.get("CI")' in source, f"{path.name} must refuse to run in CI"
    assert offenders == []
