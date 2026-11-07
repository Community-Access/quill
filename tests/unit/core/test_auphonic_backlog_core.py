"""Quill Converter's Auphonic backlog, wx-free: options, history, account, and the run.

Post-MVP (docs/planning/QUILL-Converter-Auphonic-Integration-PRD.md, section 14).
No network anywhere: the client's requests go to a fake ``urlopen`` that records
them and answers with recorded Auphonic-shaped JSON, and the lifecycle runs
against a fake client.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from quill.core.publish import auphonic, auphonic_account, auphonic_history
from quill.core.publish.auphonic import AuphonicError, ProductionStatus
from quill.core.publish.auphonic_account import (
    AccountDetails,
    RemoteProduction,
    parse_account,
    parse_productions,
)
from quill.core.publish.auphonic_history import (
    FAILED,
    PROCESSING,
    SAVED,
    WAITING,
    HistoryEntry,
    load_history,
    merge_remote,
    record_outcome,
    record_sent,
    remove_entry,
    save_history,
)
from quill.core.publish.auphonic_options import (
    NOISE_OFF,
    CustomProcessing,
    cover_problem,
    extras_problem,
    format_chapters,
    outputs,
    parse_chapters,
)
from quill.core.publish.auphonic_plan import (
    CUSTOM,
    MULTITRACK,
    AuphonicChoices,
    PendingProduction,
    SourceDetails,
    confirmation_text,
    problem,
    production_body,
    track_ids,
    uploads_for,
)
from quill.core.publish.auphonic_run import Runner

# Recorded shapes of Auphonic's answers (from its published API pages; a live
# account check is listed in the PRD, section 14).
USER_JSON = {
    "status_code": 200,
    "data": {
        "username": "jeff",
        "email": "jeff@example.com",
        "credits": 11.5,
        "onetime_credits": 2.5,
        "recurring_credits": 9.0,
        "recharge_recurring_credits": 9.0,
        "recharge_date": "2026-11-01T00:00:00.000Z",
    },
}
PRODUCTIONS_JSON = {
    "status_code": 200,
    "data": [
        {
            "uuid": "Known1",
            "metadata": {"title": "Episode 1"},
            "status": 3,
            "status_string": "Done",
            "creation_time": "2026-10-16T09:30:00.000Z",
        },
        {
            "uuid": "Other2",
            "metadata": {"title": "Made on the website"},
            "status": 4,
            "status_string": "Audio Processing",
            "creation_time": "2026-10-17T08:00:00.000Z",
        },
        {"uuid": "../etc", "status": 3},
        "junk",
    ],
}


# --------------------------------------------------------------------------- #
# Options: custom processing, chapters, cover, outputs
# --------------------------------------------------------------------------- #


def test_custom_processing_sends_its_numbers_and_says_them_in_words() -> None:
    custom = CustomProcessing(loudness=-19, max_peak=-2.0, noise=12, noise_method="dynamic")
    single, per_track = custom.algorithms(multitrack=False)
    assert per_track == {}
    assert single == {
        "filtering": True,
        "denoise": True,
        "denoiseamount": 12,
        "denoisemethod": "dynamic",
        "leveler": True,
        "normloudness": True,
        "loudnesstarget": -19,
        "maxpeak": -2.0,
    }
    master, track = custom.algorithms(multitrack=True)
    assert "loudnesstarget" in master and "denoise" not in master
    assert track == {
        "filtering": True,
        "denoise": True,
        "denoiseamount": 12,
        "denoisemethod": "dynamic",
    }
    words = custom.describe()
    assert "-19 LUFS" in words and "-2 dB" in words and "medium" in words
    assert "LUFS" not in custom.describe().split(":")[0]  # the lead is plain words
    assert CustomProcessing().algorithms(multitrack=False)[0]["denoise"] is False
    assert "no noise reduction" in CustomProcessing(noise=NOISE_OFF).describe()


def test_custom_values_outside_the_lists_are_refused() -> None:
    assert CustomProcessing().problem() == ""
    assert "loudness" in CustomProcessing(loudness=-5).problem()
    assert "peak" in CustomProcessing(max_peak=0.5).problem()
    assert "strength" in CustomProcessing(noise=7).problem()
    assert "method" in CustomProcessing(noise_method="magic").problem()


def test_chapter_marks_round_trip_and_bad_lines_are_named() -> None:
    chapters, reason = parse_chapters("0:00:00 Welcome\n\n5:30 Interview\n1:02:03.5 Close")
    assert reason == "" and chapters == ((0.0, "Welcome"), (330.0, "Interview"), (3723.5, "Close"))
    assert format_chapters(chapters) == "0:00:00 Welcome\n0:05:30 Interview\n1:02:03 Close"
    assert parse_chapters("Welcome")[1].startswith("Chapter line 1 needs")
    assert "starts before" in parse_chapters("0:05:00 B\n0:01:00 A")[1]
    assert "cannot be right" in parse_chapters("0:00:75 Odd")[1]
    assert parse_chapters("") == ((), "")


def test_a_cover_must_be_a_real_small_jpeg_or_png(tmp_path: Path) -> None:
    good = tmp_path / "cover.png"
    good.write_bytes(b"\x89PNG....")
    empty = tmp_path / "empty.jpg"
    empty.write_bytes(b"")
    assert cover_problem("") == "" and cover_problem(str(good)) == ""
    assert "JPEG or PNG" in cover_problem(str(tmp_path / "cover.gif"))
    assert "no longer there" in cover_problem(str(tmp_path / "gone.jpg"))
    assert "empty" in cover_problem(str(empty))


def test_more_results_need_a_format_and_edited_chapters_one_production() -> None:
    base: dict[str, Any] = {
        "output_format": "mp3",
        "second_format": "",
        "transcript": False,
        "language": "en",
        "cover": "",
        "chapters_edited": False,
        "productions": 1,
    }
    assert extras_problem(**base) == ""
    assert "replaces the preset" in extras_problem(**{
        **base,
        "output_format": "",
        "transcript": True,
    })
    assert "same as the first" in extras_problem(**{**base, "second_format": "mp3"})
    assert "language" in extras_problem(**{**base, "transcript": True, "language": "xx"})
    assert "one production" in extras_problem(**{**base, "chapters_edited": True, "productions": 2})
    assert outputs("flac", "mp3", True) == [
        {"format": "flac"},
        {"format": "mp3"},
        {"format": "subtitle", "ending": "srt"},
        {"format": "transcript", "ending": "txt"},
    ]


# --------------------------------------------------------------------------- #
# The plan: what a production now carries
# --------------------------------------------------------------------------- #


def test_typed_tags_replace_the_sources_and_edited_chapters_replace_its_own() -> None:
    choices = AuphonicChoices(
        artist="Jeff Bishop", album="", chapters=((0.0, "Start"), (90.0, "Middle"))
    )
    details = SourceDetails(
        title="Talk", artist="Old", album="Show", chapters=((0.0, "Their own"),)
    )
    body = production_body(choices, title="Talk", details=details)
    assert body["metadata"] == {"title": "Talk", "artist": "Jeff Bishop", "album": "Show"}
    assert body["chapters"] == [
        {"start": "00:00:00.000", "title": "Start"},
        {"start": "00:01:30.000", "title": "Middle"},
    ]
    cleared = production_body(AuphonicChoices(chapters=()), title="Talk", details=details)
    assert "chapters" not in cleared  # edited to none leaves the file's own out


def test_a_multitrack_production_takes_typed_tags_but_never_merges_the_tracks() -> None:
    choices = AuphonicChoices(mode=MULTITRACK, title="Panel", album="Season 2")
    body = production_body(choices, title="Panel", tracks=["host", "guest"])
    assert body["metadata"] == {"title": "Panel", "album": "Season 2"}


def test_custom_processing_a_second_format_and_a_transcript_go_into_the_body() -> None:
    choices = AuphonicChoices(
        processing=CUSTOM,
        custom=CustomProcessing(loudness=-23, noise=0),
        output_format="flac",
        second_format="mp3",
        transcript=True,
        language="de",
    )
    body = production_body(choices, title="Talk")
    assert body["algorithms"]["loudnesstarget"] == -23  # type: ignore[index]
    assert body["algorithms"]["denoiseamount"] == 0  # type: ignore[index]
    assert body["output_files"][:2] == [{"format": "flac"}, {"format": "mp3"}]  # type: ignore[index]
    assert body["speech_recognition"] == {"type": "auphonic", "language": "de"}
    multi = production_body(
        AuphonicChoices(mode=MULTITRACK, title="P", processing=CUSTOM),
        title="P",
        tracks=["a", "b"],
    )
    assert multi["algorithms"]["normloudness"] is True  # type: ignore[index]
    assert all(t["algorithms"]["filtering"] for t in multi["multi_input_files"])  # type: ignore[index, union-attr]


def test_problems_now_cover_the_extras(tmp_path: Path) -> None:
    files = [tmp_path / "a.wav", tmp_path / "b.wav"]
    assert "loudness" in problem(
        AuphonicChoices(processing=CUSTOM, custom=CustomProcessing(loudness=1)), files
    )
    assert "one production" in problem(AuphonicChoices(chapters=((0.0, "A"),)), files)
    assert problem(AuphonicChoices(chapters=((0.0, "A"),)), files[:1]) == ""
    assert "JPEG or PNG" in problem(AuphonicChoices(cover=str(tmp_path / "x.bmp")), files)


def test_the_confirmation_names_the_extras(tmp_path: Path) -> None:
    choices = AuphonicChoices(
        processing=CUSTOM,
        output_format="flac",
        second_format="mp3",
        transcript=True,
        artist="Jeff",
        cover=str(tmp_path / "art.png"),
        chapters=((0.0, "A"), (5.0, "B")),
    )
    text = confirmation_text(choices, [tmp_path / "a.wav"], [], tmp_path / "out")
    assert "Custom processing, which replaces the preset's own" in text
    assert "saved as FLAC and MP3" in text and "captions and a transcript in English" in text
    assert "Tags you typed, replacing the files' own: artist Jeff." in text
    assert "Cover image uploaded with each production: art.png." in text
    assert "Chapter marks: the 2 you edited." in text


def test_a_track_never_takes_the_covers_field_name(tmp_path: Path) -> None:
    assert track_ids([tmp_path / "image.wav", tmp_path / "input_file.wav"]) == [
        "image track",
        "input_file track",
    ]
    cover = str(tmp_path / "c.jpg")
    sound = [("input_file", tmp_path / "a.wav")]
    assert uploads_for(AuphonicChoices(cover=cover), sound) == [*sound, ("image", Path(cover))]
    assert uploads_for(AuphonicChoices(), sound) == sound


# --------------------------------------------------------------------------- #
# The client: two read-only calls and the result filter
# --------------------------------------------------------------------------- #


class _Response:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload
        self.headers = {"Content-Length": str(len(payload))}

    def read(self, size: int = -1) -> bytes:
        size = len(self._payload) if size is None or size < 0 else size
        chunk, self._payload = self._payload[:size], self._payload[size:]
        return chunk

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


@pytest.fixture()
def wire(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    sent: list[dict[str, Any]] = []

    def urlopen(request: Any, **_kwargs: Any) -> _Response:
        sent.append({
            "url": request.full_url,
            "method": request.get_method(),
            "auth": request.headers.get("Authorization", ""),
            "body": request.data,
        })
        url = request.full_url
        answer = USER_JSON if url.endswith("/user.json") else PRODUCTIONS_JSON
        return _Response(json.dumps(answer).encode())

    monkeypatch.setattr(auphonic.urllib.request, "urlopen", urlopen)
    return sent


def test_the_account_view_reads_user_json_and_uploads_nothing(wire) -> None:
    details = auphonic_account.account_details("tok")
    assert wire == [{
        "url": "https://auphonic.com/api/user.json",
        "method": "GET",
        "auth": "Bearer tok",
        "body": None,
    }]  # fmt: skip
    assert details == AccountDetails(
        username="jeff",
        email="jeff@example.com",
        credits=11.5,
        onetime_credits=2.5,
        recurring_credits=9.0,
        recharge_hours=9.0,
        recharge_date="2026-11-01",
    )
    lines = details.lines()
    assert lines[0] == "Account: jeff" and "Credits left: 11.5 hours of processing." in lines
    assert lines[-1] == "Plan: A recurring plan: 9 hours each month, next added on 2026-11-01."


def test_plan_words_follow_what_auphonic_says() -> None:
    assert "one-time credits only" in AccountDetails("a", recharge_hours=0.0).plan()
    assert "did not say" in AccountDetails("a").plan()
    sparse = parse_account({"data": {"username": "b", "credits": "junk"}})
    assert sparse.credits == 0.0 and sparse.onetime_credits is None
    assert all("One-time" not in line for line in sparse.lines())
    with pytest.raises(AuphonicError):
        parse_account({"data": []})


def test_the_production_list_is_one_read_and_odd_rows_are_dropped(wire) -> None:
    rows = auphonic_account.list_productions("tok")
    assert [r["url"] for r in wire] == ["https://auphonic.com/api/productions.json?limit=50"]
    assert wire[0]["method"] == "GET" and wire[0]["body"] is None
    assert rows == [
        RemoteProduction("Known1", "Episode 1", 3, "Done", "2026-10-16 09:30"),
        RemoteProduction(
            "Other2", "Made on the website", 4, "Audio Processing", "2026-10-17 08:00"
        ),
    ]
    assert parse_productions({"data": "nope"}) == []


def test_captions_and_a_transcript_are_kept_with_the_sound() -> None:
    base = "https://auphonic.com/api/download/"
    status = ProductionStatus(
        "u",
        3,
        "Done",
        [
            {"format": "mp3", "download_url": base + "a.mp3"},
            {"format": "subtitle", "ending": "srt", "download_url": base + "a.srt"},
            {"format": "transcript", "ending": "txt", "download_url": base + "a.txt"},
            {"format": "speech", "ending": "json", "download_url": base + "a.json"},
            {"format": "subtitle", "ending": "srt", "download_url": "https://evil.example/a.srt"},
        ],
    )
    kept, left_out = auphonic.audio_results(status)
    assert [o["download_url"].rsplit("/", 1)[-1] for o in kept.output_files] == [
        "a.mp3",
        "a.srt",
        "a.txt",
    ]
    assert left_out == 2


# --------------------------------------------------------------------------- #
# Production History
# --------------------------------------------------------------------------- #


def _pending(uuid: str = "U1", title: str = "Talk") -> PendingProduction:
    return PendingProduction(uuid, "separate", title, ["talk.wav"], "Speech", "C:/out/Talk")


def test_history_records_a_production_and_its_outcome(tmp_path: Path) -> None:
    store = tmp_path / "converter" / "auphonic_history.json"
    assert load_history(store) == []
    record_sent(store, _pending("U1", "First"))
    record_sent(store, _pending("U2", "Second"))
    entries = load_history(store)
    assert [e.uuid for e in entries] == ["U2", "U1"]  # newest first
    assert entries[0].state == PROCESSING and entries[0].inputs == ["talk.wav"]
    record_outcome(store, "U1", SAVED, "First: 1 file saved.", [tmp_path / "r.mp3"])
    record_outcome(store, "U1", SAVED, "Again.", [tmp_path / "r (2).mp3", tmp_path / "r.mp3"])
    first = load_history(store)[1]
    assert first.state == SAVED and first.message == "Again."
    assert first.files == [str(tmp_path / "r.mp3"), str(tmp_path / "r (2).mp3")]
    assert "results saved, 2 files" in first.describe()
    assert "Auphonic production id: U1" in first.details()
    raw = json.loads(store.read_text(encoding="utf-8"))
    assert raw["schema"] == 1 and "token" not in store.read_text(encoding="utf-8")
    remove_entry(store, "U2")
    assert [e.uuid for e in load_history(store)] == ["U1"]


def test_a_damaged_history_reads_as_empty_and_the_list_is_capped(tmp_path: Path) -> None:
    store = tmp_path / "h.json"
    store.write_text("{not json", encoding="utf-8")
    assert load_history(store) == []
    save_history(store, [HistoryEntry(f"U{n}", f"T{n}") for n in range(250)])
    assert len(load_history(store)) == auphonic_history.MAX_ENTRIES


def test_refresh_merges_the_accounts_list_without_losing_what_was_saved(tmp_path: Path) -> None:
    saved = HistoryEntry("Known1", "Episode 1", state=SAVED, files=["C:/x.mp3"])
    entries = [saved]
    remote = parse_productions(PRODUCTIONS_JSON)
    updated, added = merge_remote(entries, list(remote), tmp_path / "dest")
    assert (updated, added) == (1, 1)
    assert saved.state == SAVED and saved.status_string == "Done" and saved.files == ["C:/x.mp3"]
    other = entries[1]
    assert other.source == "account" and other.state == PROCESSING
    assert other.out_dir == str(tmp_path / "dest" / "Made on the website")
    assert "found in your account" in other.details()
    merge_remote(entries, [RemoteProduction("Other2", "x", 2, "Error")], tmp_path)
    assert other.state == FAILED
    fresh = [HistoryEntry("N1", "New")]
    merge_remote(fresh, [RemoteProduction("N1", "New", 3, "Done")], tmp_path)
    assert fresh[0].state == WAITING  # done at Auphonic, not fetched here


def test_a_history_entry_becomes_the_record_download_again_waits_for() -> None:
    entry = HistoryEntry(
        "U7", "Talk", inputs=["a.wav"], out_dir="C:/o/Talk", sent="2026-10-17 10:00"
    )
    pending = entry.as_pending()
    assert (pending.uuid, pending.title, pending.out_dir) == ("U7", "Talk", "C:/o/Talk")


# --------------------------------------------------------------------------- #
# The run: the cover goes up, and the history follows every production
# --------------------------------------------------------------------------- #


class _Client:
    def __init__(self, *, start_error: Exception | None = None) -> None:
        self.calls: list[tuple[str, Any]] = []
        self.start_error = start_error

    def create_production(self, token: str, body: dict[str, object]) -> str:
        self.calls.append(("create", body))
        return "U1"

    def upload_input(self, token: str, uuid: str, path: Path, **kwargs: Any) -> None:
        self.calls.append(("upload", (kwargs.get("field_name"), path.name)))
        kwargs["on_bytes"](1, 1)

    def start_created(self, token: str, uuid: str) -> None:
        self.calls.append(("start", uuid))
        if self.start_error is not None:
            raise self.start_error

    def production_status(self, token: str, uuid: str) -> ProductionStatus:
        url = "https://auphonic.com/r.mp3"
        return ProductionStatus(uuid, 3, "Done", [{"format": "mp3", "download_url": url}])

    audio_results = staticmethod(auphonic.audio_results)

    def download_results(self, token: str, status: Any, out_dir: Path, **_k: Any) -> list[Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        target = auphonic._unused_path(out_dir / "r.mp3")
        target.write_bytes(b"result")
        return [target]


def _run(client: _Client, tmp_path: Path) -> Runner:
    return Runner(
        "tok",
        tmp_path / "pending.json",
        client=client,
        sleep=lambda _s: None,
        history=tmp_path / "history.json",
    )


def test_the_cover_is_uploaded_after_the_sound_and_is_not_a_track(tmp_path: Path) -> None:
    sound = tmp_path / "talk.wav"
    sound.write_bytes(b"x")
    cover = tmp_path / "art.jpg"
    cover.write_bytes(b"jpeg")
    client = _Client()
    result = _run(client, tmp_path).send(
        AuphonicChoices(cover=str(cover)), [sound], tmp_path / "out"
    )
    uploads = [arg for name, arg in client.calls if name == "upload"]
    assert uploads == [("input_file", "talk.wav"), ("image", "art.jpg")]
    entry = load_history(tmp_path / "history.json")[0]
    assert entry.inputs == ["talk.wav"] and entry.mode == "separate"
    assert entry.state == SAVED and entry.files == [str(tmp_path / "out" / "talk" / "r.mp3")]
    assert result.outcomes[0].uuid == "U1"


def test_download_again_saves_beside_never_over_and_updates_the_history(tmp_path: Path) -> None:
    sound = tmp_path / "talk.wav"
    sound.write_bytes(b"x")
    client = _Client()
    runner = _run(client, tmp_path)
    runner.send(AuphonicChoices(), [sound], tmp_path / "out")
    entry = load_history(tmp_path / "history.json")[0]
    runner.waiting_door = "Convert > Auphonic Production History can try again"
    again = runner.resume([entry.as_pending()])
    assert again.outcomes[0].files == [tmp_path / "out" / "talk" / "r (2).mp3"]
    assert (tmp_path / "out" / "talk" / "r.mp3").read_bytes() == b"result"
    assert len(load_history(tmp_path / "history.json")[0].files) == 2


def test_an_unconfirmed_start_is_in_the_history_to_be_checked(tmp_path: Path) -> None:
    sound = tmp_path / "talk.wav"
    sound.write_bytes(b"x")
    client = _Client(start_error=AuphonicError("timed out"))
    result = _run(client, tmp_path).send(AuphonicChoices(), [sound], tmp_path / "out")
    entry = load_history(tmp_path / "history.json")[0]
    assert entry.state == FAILED and "may have started" in entry.message
    assert result.outcomes[0].uuid == "U1"
    assert not (tmp_path / "pending.json").exists()  # still never resumed blindly


def test_the_backlog_modules_reach_the_network_only_through_the_client() -> None:
    from quill.core.publish import auphonic_options

    for module in (auphonic_account, auphonic_history, auphonic_options):
        source = Path(str(module.__file__)).read_text(encoding="utf-8")
        assert "urllib" not in source and "urlopen" not in source and "http_client" not in source
