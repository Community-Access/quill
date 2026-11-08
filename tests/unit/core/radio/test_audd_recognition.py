"""AudD: the request, and its answers mapped into AcoustID's Match shape.

Fixtures are hand-written from https://docs.audd.io/ and BlindRadio's own test
(serrebidev, MIT). No network: every call goes through a fake ``post``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core.radio import acoustid, audd, song_recognition

MATCH = json.dumps({
    "status": "success",
    "result": {
        "artist": "k.d. lang",
        "title": "Constant Craving",
        "album": "Ingenue",
        "release_date": "1992-03-17",
        "label": "Sire",
        "timecode": "00:56",
        "song_link": "https://lis.tn/example",
    },
})
NO_MATCH = '{"status": "success", "result": null}'
BAD_TOKEN = json.dumps({
    "status": "error",
    "error": {"error_code": 900, "error_message": "Recognition failed: authorization failed."},
})


def test_the_body_is_multipart_with_the_token_and_the_clip() -> None:
    body, content_type = audd.build_body("TOKEN", b"\x00\x01audio", boundary="B")
    assert content_type == "multipart/form-data; boundary=B"
    assert b'name="api_token"\r\n\r\nTOKEN\r\n' in body
    assert b'name="file"; filename="sample"' in body
    assert b"\x00\x01audio\r\n--B--" in body


def test_a_match_becomes_the_same_shape_acoustid_returns() -> None:
    assert audd.parse_answer(MATCH) == [
        acoustid.Match(title="Constant Craving", artist="k.d. lang", score=1.0, album="Ingenue")
    ]


def test_no_match_is_an_empty_list_not_an_error() -> None:
    assert audd.parse_answer(NO_MATCH) == []
    assert audd.parse_answer('{"status": "success", "result": []}') == []
    too_short = '{"status": "error", "error": {"error_code": 300, "error_message": "x"}}'
    assert audd.parse_answer(too_short) == []


def test_a_rejected_token_and_a_used_up_limit_are_sentences() -> None:
    with pytest.raises(audd.AudDError, match="did not accept the API token"):
        audd.parse_answer(BAD_TOKEN)
    limit = '{"status": "error", "error": {"error_code": 901, "error_message": "limit"}}'
    with pytest.raises(audd.AudDError, match="free limit"):
        audd.parse_answer(limit)
    with pytest.raises(audd.AudDError):
        audd.parse_answer("not json")


def test_identify_posts_once_and_refuses_safe_mode_and_no_token() -> None:
    sent: list[tuple[bytes, str]] = []

    def _post(body: bytes, content_type: str) -> str:
        sent.append((body, content_type))
        return MATCH

    assert audd.identify("T", b"clip", post=_post)[0].title == "Constant Craving"
    assert len(sent) == 1
    with pytest.raises(audd.AudDError, match="Safe Mode"):
        audd.identify("T", b"clip", safe_mode=True, post=_post)
    with pytest.raises(audd.AudDError):
        audd.identify("", b"clip", post=_post)
    with pytest.raises(audd.AudDError, match="too large"):
        audd.identify("T", b"x" * (audd.MAX_SAMPLE_BYTES + 1), post=_post)
    assert len(sent) == 1, "nothing else reached the network"


def test_the_spoken_answer_names_audd_and_the_album_and_never_a_percentage() -> None:
    said = song_recognition.describe_audd(audd.parse_answer(MATCH))
    assert said.sentence == "AudD says: Constant Craving by k.d. lang, from Ingenue."
    assert "percent" not in said.sentence
    assert said.best is not None and said.best.artist == "k.d. lang"
    assert song_recognition.describe_audd([]).sentence == audd.NO_MATCH


def test_recognise_with_audd_reads_the_sample_and_never_raises(tmp_path: Path) -> None:
    sample = tmp_path / "sample"
    sample.write_bytes(b"clip")
    got = song_recognition.recognise_with_audd(sample, token="T", post=lambda _b, _c: MATCH)
    assert got.best is not None and got.best.title == "Constant Craving"
    failed = song_recognition.recognise_with_audd(sample, token="T", post=lambda _b, _c: BAD_TOKEN)
    assert "did not accept" in failed.sentence and "[QUILL" not in failed.sentence
    missing = song_recognition.recognise_with_audd(tmp_path / "gone", token="T")
    assert missing.sentence == song_recognition.NOT_ENOUGH_AUDIO


def test_the_service_choice_and_its_precheck() -> None:
    assert song_recognition.normalise_service("AUDD") == "audd"
    assert song_recognition.normalise_service("shazam") == "acoustid"
    assert song_recognition.service_index("audd") == 1
    assert song_recognition.sample_seconds("audd") == audd.SAMPLE_SECONDS
    assert song_recognition.sample_seconds("acoustid") == song_recognition.SAMPLE_SECONDS
    assert (
        song_recognition.precheck(key="", fpcalc=None, service="audd", audd_token="")
        == audd.NO_TOKEN_SENTENCE
    )
    assert song_recognition.precheck(key="", fpcalc=None, service="audd", audd_token="T") == ""
    # AcoustID's own precheck is unchanged.
    assert song_recognition.precheck(key="", fpcalc="x") == acoustid.NO_KEY_SENTENCE
