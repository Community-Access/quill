"""Identify This Song: Chromaprint, AcoustID and the sentences, all with fakes.

Nothing here touches the network, a real fpcalc or the credential store.
"""

from __future__ import annotations

import json
import subprocess
import urllib.parse
from pathlib import Path
from typing import Any

import pytest

from quill.core.radio import acoustid, chromaprint, song_recognition

_ANSWER = {
    "status": "ok",
    "results": [
        {
            "score": 0.62,
            "recordings": [{"id": "r2", "title": "Second Best", "artists": [{"name": "B"}]}],
        },
        {
            "score": 0.91,
            "recordings": [
                {
                    "id": "r1",
                    "title": "Blue Monday",
                    "artists": [{"name": "New Order"}],
                }
            ],
        },
    ],
}


def _run_ok(args: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args, 0, stdout=json.dumps({"duration": 58.4, "fingerprint": "AQAAabc"}), stderr=""
    )


# -- Chromaprint ---------------------------------------------------------------


def test_fpcalc_is_run_with_a_fixed_argument_list(tmp_path: Path) -> None:
    command = chromaprint.build_command("fpcalc.exe", tmp_path / "sample")
    assert command == ["fpcalc.exe", "-json", "-length", "120", str(tmp_path / "sample")]


def test_the_fingerprint_and_length_are_read_from_fpcalc_json() -> None:
    found = chromaprint.parse_output('{"duration": 61.9, "fingerprint": "AQAD"}')
    assert found == chromaprint.Fingerprint(fingerprint="AQAD", duration=61)


@pytest.mark.parametrize("text", ["", "not json", "[]", '{"duration": 0, "fingerprint": "x"}'])
def test_an_unusable_fpcalc_answer_is_a_sentence_not_a_crash(text: str) -> None:
    with pytest.raises(chromaprint.ChromaprintError):
        chromaprint.parse_output(text)


def test_a_failing_fpcalc_is_reported(tmp_path: Path) -> None:
    def _fail(args: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 2, stdout="", stderr="bad")

    with pytest.raises(chromaprint.ChromaprintError):
        chromaprint.fingerprint(tmp_path / "s", fpcalc="fpcalc", run=_fail)


def test_fpcalc_that_cannot_launch_is_reported(tmp_path: Path) -> None:
    def _missing(args: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError(args[0])

    with pytest.raises(chromaprint.ChromaprintError):
        chromaprint.fingerprint(tmp_path / "s", fpcalc="fpcalc", run=_missing)


def test_fpcalc_is_found_in_a_managed_tools_folder(tmp_path: Path) -> None:
    import os

    exe = tmp_path / ("fpcalc.exe" if os.name == "nt" else "fpcalc")
    exe.write_bytes(b"")
    assert chromaprint.find_fpcalc([tmp_path]) == str(exe)


def test_only_a_file_named_fpcalc_is_ever_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "evil.exe").write_bytes(b"")
    monkeypatch.setattr(chromaprint.shutil, "which", lambda _name: str(tmp_path / "evil.exe"))
    assert chromaprint.find_fpcalc([tmp_path]) is None


# -- AcoustID ------------------------------------------------------------------


def test_the_lookup_body_carries_key_fingerprint_and_length_only() -> None:
    body = urllib.parse.parse_qs(acoustid.build_lookup_body("KEY", "AQAD", 58).decode())
    assert body == {
        "client": ["KEY"],
        "format": ["json"],
        "meta": ["recordings"],
        "duration": ["58"],
        "fingerprint": ["AQAD"],
    }


def test_matches_come_back_best_first() -> None:
    matches = acoustid.parse_lookup(json.dumps(_ANSWER))
    assert [m.title for m in matches] == ["Blue Monday", "Second Best"]
    assert matches[0].spoken() == "Blue Monday by New Order"
    assert matches[0].recording_id == "r1"


def test_a_rejected_key_says_so_rather_than_no_match() -> None:
    answer = {"status": "error", "error": {"code": 4, "message": "invalid API key"}}
    with pytest.raises(acoustid.AcoustIdError, match="did not accept the application key"):
        acoustid.parse_lookup(json.dumps(answer))


def test_no_key_never_reaches_the_network() -> None:
    def _never(_body: bytes) -> str:
        raise AssertionError("posted without a key")

    with pytest.raises(acoustid.AcoustIdError):
        acoustid.lookup("", "AQAD", 58, post=_never)


def test_safe_mode_never_reaches_the_network() -> None:
    def _never(_body: bytes) -> str:
        raise AssertionError("posted in Safe Mode")

    with pytest.raises(acoustid.AcoustIdError, match="Safe Mode"):
        acoustid.lookup("KEY", "AQAD", 58, safe_mode=True, post=_never)


def test_the_no_key_sentence_says_where_the_key_goes() -> None:
    sentence = acoustid.NO_KEY_SENTENCE
    assert acoustid.REGISTER_URL in sentence
    assert "Preferences" in sentence


# -- the pipeline and its sentences ---------------------------------------------


def test_a_match_is_reported_as_a_best_guess_with_its_confidence(tmp_path: Path) -> None:
    result = song_recognition.recognise(
        tmp_path / "sample",
        key="KEY",
        fpcalc="fpcalc",
        run=_run_ok,
        post=lambda _body: json.dumps(_ANSWER),
    )
    assert result.sentence == (
        "Best guess: Blue Monday by New Order, 91 percent sure. It could also be Second Best by B."
    )


def test_a_weak_match_is_an_honest_miss(tmp_path: Path) -> None:
    weak = {"status": "ok", "results": [{"score": 0.2, "recordings": [{"title": "Maybe"}]}]}
    result = song_recognition.recognise(
        tmp_path / "s", key="K", fpcalc="f", run=_run_ok, post=lambda _b: json.dumps(weak)
    )
    assert result.sentence == song_recognition.NO_MATCH
    assert result.best is None


def test_no_results_is_an_honest_miss(tmp_path: Path) -> None:
    result = song_recognition.recognise(
        tmp_path / "s",
        key="K",
        fpcalc="f",
        run=_run_ok,
        post=lambda _b: json.dumps({"status": "ok", "results": []}),
    )
    assert result.sentence == song_recognition.NO_MATCH


def test_a_failure_is_spoken_without_the_support_code(tmp_path: Path) -> None:
    def _offline(_body: bytes) -> str:
        raise acoustid.AcoustIdError("Could not reach AcoustID. Check the internet connection.")

    result = song_recognition.recognise(
        tmp_path / "s", key="K", fpcalc="f", run=_run_ok, post=_offline
    )
    assert result.sentence == "Could not reach AcoustID. Check the internet connection."
    assert "QUILL-" not in result.sentence


def test_the_precheck_names_the_key_before_fpcalc() -> None:
    assert song_recognition.precheck(key="", fpcalc=None) == acoustid.NO_KEY_SENTENCE
    assert song_recognition.precheck(key="K", fpcalc=None) == chromaprint.MISSING_SENTENCE
    assert song_recognition.precheck(key="K", fpcalc="fpcalc") == ""
