"""Quill Converter's Auphonic MVP, wx-free: the client's JSON API, the plan, the run.

No network anywhere: the client's requests go to a fake ``urlopen`` that
records them, and the lifecycle runs against a fake client module.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from quill.core.publish import auphonic
from quill.core.publish.auphonic import AuphonicCancelled, AuphonicError, ProductionStatus
from quill.core.publish.auphonic_plan import (
    MULTITRACK,
    QUICK_CLEANUP,
    AuphonicChoices,
    PendingProduction,
    SourceDetails,
    add_pending,
    check_inputs,
    confirmation_text,
    folder_name,
    load_pending,
    problem,
    production_body,
    remove_pending,
    track_ids,
)
from quill.core.publish.auphonic_run import (
    FAILED,
    NOT_SENT,
    SAVED,
    STOPPED,
    WAITING,
    Runner,
)

# --------------------------------------------------------------------------- #
# The shared client's JSON API
# --------------------------------------------------------------------------- #


class _Response:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload
        self.headers = {"Content-Length": str(len(payload))}

    def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            size = len(self._payload)
        chunk, self._payload = self._payload[:size], self._payload[size:]
        return chunk

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


@pytest.fixture()
def wire(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Every request the client makes, with its body read the way http.client would."""
    sent: list[dict[str, Any]] = []

    def urlopen(request: Any, **_kwargs: Any) -> _Response:
        data = request.data
        if data is not None and not isinstance(data, bytes):
            data = b"".join(iter(lambda: data.read(4096), b""))
        sent.append({
            "url": request.full_url,
            "method": request.get_method(),
            "type": request.headers.get("Content-type", ""),
            "auth": request.headers.get("Authorization", ""),
            "body": data,
        })
        return _Response(json.dumps({"data": {"uuid": "Abc123XYZ"}}).encode())

    monkeypatch.setattr(auphonic.urllib.request, "urlopen", urlopen)
    return sent


def test_create_upload_start_are_three_posts_to_the_json_api(wire, tmp_path: Path) -> None:
    audio = tmp_path / "talk.wav"
    audio.write_bytes(b"RIFF" + b"\x01" * 300)
    production = auphonic.create_production("tok", {"metadata": {"title": "Talk"}})
    seen: list[tuple[int, int]] = []
    auphonic.upload_input("tok", production, audio, on_bytes=lambda d, t: seen.append((d, t)))
    auphonic.start_created("tok", production)
    assert production == "Abc123XYZ"
    assert [r["url"] for r in wire] == [
        "https://auphonic.com/api/productions.json",
        "https://auphonic.com/api/production/Abc123XYZ/upload.json",
        "https://auphonic.com/api/production/Abc123XYZ/start.json",
    ]
    assert all(r["method"] == "POST" and r["auth"] == "Bearer tok" for r in wire)
    assert wire[0]["type"] == "application/json"
    assert json.loads(wire[0]["body"]) == {"metadata": {"title": "Talk"}}
    assert b'name="input_file"; filename="talk.wav"' in wire[1]["body"]
    assert audio.read_bytes() in wire[1]["body"]
    assert seen and seen[-1][0] == seen[-1][1]  # streamed, with progress to the end


def test_a_multitrack_upload_names_its_track(wire, tmp_path: Path) -> None:
    audio = tmp_path / "host.wav"
    audio.write_bytes(b"x" * 10)
    auphonic.upload_input("tok", "Abc123XYZ", audio, field_name="host")
    assert b'name="host"; filename="host.wav"' in wire[0]["body"]


def test_an_odd_production_id_is_never_put_in_a_url(wire) -> None:
    with pytest.raises(AuphonicError):
        auphonic.start_created("tok", "../user")
    assert wire == []


def test_a_cancelled_upload_raises_cancelled(wire, tmp_path: Path) -> None:
    audio = tmp_path / "talk.wav"
    audio.write_bytes(b"x" * 10)
    with pytest.raises(AuphonicCancelled):
        auphonic.upload_input("tok", "Abc123XYZ", audio, is_cancelled=lambda: True)


def test_only_sound_files_on_auphonics_host_are_kept() -> None:
    status = ProductionStatus(
        uuid="u",
        status=auphonic.DONE_STATUS,
        status_string="Done",
        output_files=[
            {"format": "mp3", "download_url": "https://auphonic.com/api/download/a.mp3"},
            {"format": "flac", "download_url": "https://cdn.auphonic.com/b.flac"},
            {"format": "waveform", "download_url": "https://auphonic.com/w.png"},
            {"format": "stats", "download_url": "https://auphonic.com/s.txt"},
            {"format": "mp3", "download_url": "https://evil.example/c.mp3"},
            {"format": "mp3", "download_url": "http://auphonic.com/d.mp3"},
            {"ending": "wav", "filename": "e.wav", "download_url": "https://auphonic.com/e.wav"},
        ],
    )
    kept, left_out = auphonic.audio_results(status)
    assert [o["download_url"].rsplit("/", 1)[-1] for o in kept.output_files] == [
        "a.mp3",
        "b.flac",
        "e.wav",
    ]
    assert left_out == 4 and kept.uuid == "u" and kept.done


def test_the_output_formats_offered_are_auphonic_names() -> None:
    assert set(auphonic.OUTPUT_FORMATS) == {"mp3", "aac", "opus", "flac", "wav"}


# --------------------------------------------------------------------------- #
# The plan
# --------------------------------------------------------------------------- #


def _write(folder: Path, *names: str, size: int = 4) -> list[Path]:
    paths = []
    for name in names:
        path = folder / name
        path.write_bytes(b"x" * size)
        paths.append(path)
    return paths


def test_ineligible_files_are_named_with_a_reason(tmp_path: Path) -> None:
    good, clip, odd = _write(tmp_path, "a.wav", "film.mp4", "old.ape")
    (empty,) = _write(tmp_path, "empty.mp3", size=0)
    (pictured,) = _write(tmp_path, "pictured.m4a")
    folder = tmp_path / "folder"
    folder.mkdir()
    eligible, skipped = check_inputs(
        [good, clip, odd, empty, folder, tmp_path / "gone.mp3", pictured, good],
        has_video=lambda path: path.name == "pictured.m4a",
    )
    assert eligible == [good]  # and the repeat is sent once
    reasons = {item.path.name: item.reason for item in skipped}
    assert "video file" in reasons["film.mp4"]
    assert ".ape" in reasons["old.ape"] and "WAV or FLAC" in reasons["old.ape"]
    assert "empty" in reasons["empty.mp3"]
    assert "folder" in reasons["folder"]
    assert "no longer there" in reasons["gone.mp3"]
    assert "video picture" in reasons["pictured.m4a"]


def test_problems_block_the_submission(tmp_path: Path) -> None:
    one = _write(tmp_path, "a.wav")
    two = [*one, *_write(tmp_path, "b.wav")]
    assert "None of the queued files" in problem(AuphonicChoices(), [])
    assert problem(AuphonicChoices(), one) == ""
    assert "at least 2" in problem(AuphonicChoices(mode=MULTITRACK, title="T"), one)
    assert "title" in problem(AuphonicChoices(mode=MULTITRACK, title=" "), two)
    assert problem(AuphonicChoices(mode=MULTITRACK, title="T"), two) == ""
    assert "format" in problem(AuphonicChoices(output_format="mkv"), one)


def test_track_names_are_file_names_made_unique_and_header_safe(tmp_path: Path) -> None:
    a = tmp_path / "x" / "host.wav"
    b = tmp_path / "y" / "host.flac"
    c = tmp_path / 'say "hi".mp3'
    assert track_ids([a, b, c]) == ["host", "host (2)", "say  hi"]


def test_a_separate_production_body_with_the_preset_as_is() -> None:
    body = production_body(
        AuphonicChoices(preset_uuid="P1"),
        title="Talk",
        details=SourceDetails(
            title="Talk",
            artist="Jeff",
            album="Shows",
            chapters=((0.0, "Opening"), (75.5, "Middle")),
        ),
    )
    assert body == {
        "metadata": {"title": "Talk", "artist": "Jeff", "album": "Shows"},
        "preset": "P1",
        "chapters": [
            {"start": "00:00:00.000", "title": "Opening"},
            {"start": "00:01:15.500", "title": "Middle"},
        ],
    }


def test_quick_cleanup_and_a_format_override_the_preset() -> None:
    choices = AuphonicChoices(processing=QUICK_CLEANUP, denoise=False, output_format="flac")
    body = production_body(choices, title="Talk")
    assert body["algorithms"] == {
        "filtering": True,
        "leveler": True,
        "normloudness": True,
        "denoise": False,
    }
    assert body["output_files"] == [{"format": "flac"}]
    assert "preset" not in body  # the account's default


def test_a_multitrack_body_has_tracks_in_order_and_no_merged_tags() -> None:
    choices = AuphonicChoices(mode=MULTITRACK, processing=QUICK_CLEANUP, denoise=True)
    body = production_body(
        choices,
        title="Panel",
        details=SourceDetails(artist="ignored", chapters=((1.0, "x"),)),
        tracks=["host", "guest"],
    )
    assert body["is_multitrack"] is True
    assert body["metadata"] == {"title": "Panel"} and "chapters" not in body
    assert body["multi_input_files"] == [
        {"type": "multitrack", "id": "host", "algorithms": {"filtering": True, "denoise": True}},
        {"type": "multitrack", "id": "guest", "algorithms": {"filtering": True, "denoise": True}},
    ]
    assert body["algorithms"] == {"leveler": True, "normloudness": True}


def test_the_confirmation_names_everything(tmp_path: Path) -> None:
    files = _write(tmp_path, "host.wav", "guest.wav")
    _eligible, skipped = check_inputs([*files, tmp_path / "gone.mp3"])
    text = confirmation_text(
        AuphonicChoices(
            mode=MULTITRACK,
            title="Panel",
            preset_uuid="P",
            preset_label="Speech",
            processing=QUICK_CLEANUP,
            denoise=True,
            output_format="mp3",
        ),
        files,
        skipped,
        tmp_path / "out",
        account="account jeff, 2 credit hours left",
    )
    for needle in (
        "Auphonic, an online service",
        "account jeff",
        "One multitrack production called Panel",
        "Track 1: host",
        "Track 2: guest",
        "Preset: Speech.",
        "Quick cleanup",
        "background noise reduced",
        "saved as MP3",
        str(tmp_path / "out" / "Panel"),
        "gone.mp3",
        "not changed",
    ):
        assert needle in text, needle


def test_folder_names_are_never_paths() -> None:
    assert folder_name("../..\\evil: name?") == "evil name"
    assert folder_name("...") == "Auphonic"


def test_pending_work_round_trips_and_never_holds_the_token(tmp_path: Path) -> None:
    store = tmp_path / "converter" / "auphonic_pending.json"
    record = PendingProduction("U1", "separate", "Talk", ["talk.wav"], "Speech", str(tmp_path))
    add_pending(store, record)
    add_pending(store, PendingProduction("U2", MULTITRACK, "Panel", ["a", "b"], "", "x"))
    raw = store.read_text(encoding="utf-8")
    assert '"schema": 1' in raw and "tok" not in raw.lower().replace("talk", "")
    assert [r.uuid for r in load_pending(store)] == ["U1", "U2"]
    remove_pending(store, "U1")
    remove_pending(store, "U2")
    assert load_pending(store) == [] and not store.exists()


def test_a_damaged_pending_file_reads_as_nothing(tmp_path: Path) -> None:
    store = tmp_path / "p.json"
    store.write_text("{not json", encoding="utf-8")
    assert load_pending(store) == []


# --------------------------------------------------------------------------- #
# The run, against a fake client
# --------------------------------------------------------------------------- #


class _Client:
    """The client's surface, scripted; records every call in order."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []
        self.count = 0
        self.fail_upload: set[str] = set()
        self.statuses: list[Any] = []
        self.outputs: list[dict[str, object]] = [
            {"format": "mp3", "download_url": "https://auphonic.com/r.mp3", "filename": "r.mp3"}
        ]
        self.cancel_after_upload: Any = None
        self.download_error: Exception | None = None

    def create_production(self, token: str, body: dict[str, object]) -> str:
        self.count += 1
        self.calls.append(("create", body))
        return f"U{self.count}"

    def upload_input(self, token: str, uuid: str, path: Path, **kwargs: Any) -> None:
        self.calls.append(("upload", (uuid, kwargs.get("field_name"), path.name)))
        kwargs["on_bytes"](5, 10)
        kwargs["on_bytes"](10, 10)
        if path.name in self.fail_upload:
            raise AuphonicError("Auphonic said 500.")
        if self.cancel_after_upload is not None:
            self.cancel_after_upload()
        if kwargs["is_cancelled"]():
            raise AuphonicCancelled("stopped")

    def start_created(self, token: str, uuid: str) -> None:
        self.calls.append(("start", uuid))

    def production_status(self, token: str, uuid: str) -> Any:
        self.calls.append(("status", uuid))
        item = self.statuses.pop(0) if self.statuses else 3
        if isinstance(item, Exception):
            raise item
        return ProductionStatus(
            uuid,
            item,
            {3: "Done", 2: "Error", 4: "Audio Processing"}.get(item, ""),
            list(self.outputs),
        )

    audio_results = staticmethod(auphonic.audio_results)

    def download_results(self, token: str, status: Any, out_dir: Path, **kwargs: Any) -> list[Path]:
        self.calls.append(("download", (status.uuid, out_dir)))
        if self.download_error is not None:
            raise self.download_error
        kwargs["on_bytes"]("r.mp3", 1, 1)
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / "r.mp3"
        target.write_bytes(b"result")
        return [target]


def _runner(client: _Client, store: Path, **kwargs: Any) -> tuple[Runner, list[tuple[str, float]]]:
    progress: list[tuple[str, float]] = []
    runner = Runner(
        "tok",
        store,
        client=client,
        on_progress=lambda text, fraction: progress.append((text, fraction)),
        sleep=lambda _s: None,
        poll_seconds=1.0,
        **kwargs,
    )
    return runner, progress


def test_separate_productions_run_one_after_another_and_save(tmp_path: Path) -> None:
    files = _write(tmp_path, "a.wav", "b.wav")
    client = _Client()
    client.statuses = [4, 3, 3]
    store = tmp_path / "pending.json"
    runner, progress = _runner(client, store)
    result = runner.send(AuphonicChoices(), files, tmp_path / "out")
    order = [name for name, _arg in client.calls]
    assert order == [
        "create", "upload", "start", "status", "status", "download",
        "create", "upload", "start", "status", "download",
    ]  # fmt: skip
    assert [o.state for o in result.outcomes] == [SAVED, SAVED]
    assert result.outcomes[0].files == [tmp_path / "out" / "a" / "r.mp3"]
    assert result.summary() == "Auphonic: 2 of 2 saved."
    assert not store.exists()  # nothing left pending
    assert any("Uploading a.wav, 1 of 2: 50 percent" == text for text, _f in progress)
    assert any(text.startswith("Auphonic is processing a.wav") for text, _f in progress)
    fractions = [f for _t, f in progress]
    assert fractions == sorted(fractions) and fractions[-1] == 1.0


def test_one_failure_does_not_stop_the_rest(tmp_path: Path) -> None:
    files = _write(tmp_path, "a.wav", "b.wav", "c.wav")
    client = _Client()
    client.fail_upload = {"b.wav"}
    runner, _progress = _runner(client, tmp_path / "p.json")
    result = runner.send(AuphonicChoices(), files, tmp_path / "out")
    assert [o.state for o in result.outcomes] == [SAVED, FAILED, SAVED]
    failed = result.outcomes[1]
    assert "Uploading b.wav failed" in failed.message and "no credits" in failed.message
    assert ("start", "U2") not in client.calls  # never started
    assert result.summary() == "Auphonic: 2 of 3 saved, 1 failed."


def test_stop_during_upload_starts_nothing_more(tmp_path: Path) -> None:
    files = _write(tmp_path, "a.wav", "b.wav")
    client = _Client()
    stopped = {"now": False}
    client.cancel_after_upload = lambda: stopped.update(now=True)
    runner, _progress = _runner(client, tmp_path / "p.json", is_cancelled=lambda: stopped["now"])
    result = runner.send(AuphonicChoices(), files, tmp_path / "out")
    assert [o.state for o in result.outcomes] == [STOPPED, NOT_SENT]
    assert "never started" in result.outcomes[0].message
    assert [name for name, _ in client.calls] == ["create", "upload"]


def test_stop_while_auphonic_works_keeps_the_record_to_resume(tmp_path: Path) -> None:
    files = _write(tmp_path, "a.wav")
    client = _Client()
    client.statuses = [4, 4, 4]
    store = tmp_path / "p.json"
    polls = {"n": 0}

    def cancelled() -> bool:
        return polls["n"] >= 1

    original = client.production_status

    def status(token: str, uuid: str) -> Any:
        polls["n"] += 1
        return original(token, uuid)

    client.production_status = status  # type: ignore[method-assign]
    runner, _progress = _runner(client, store, is_cancelled=cancelled)
    result = runner.send(AuphonicChoices(preset_label="Speech"), files, tmp_path / "out")
    outcome = result.outcomes[0]
    assert outcome.state == WAITING and "keeps processing it" in outcome.message
    (record,) = load_pending(store)
    assert (record.uuid, record.title, record.inputs, record.preset_label) == (
        "U1",
        "a",
        ["a.wav"],
        "Speech",
    )
    assert record.out_dir == str(tmp_path / "out" / "a")

    # Next launch: Resume fetches it and forgets the record.
    later = _Client()
    resumed, _p = _runner(later, store)
    again = resumed.resume(load_pending(store))
    assert [o.state for o in again.outcomes] == [SAVED]
    assert [name for name, _ in later.calls] == ["status", "download"]
    assert (tmp_path / "out" / "a" / "r.mp3").read_bytes() == b"result"
    assert load_pending(store) == []


def test_a_service_failure_is_a_failure_and_is_forgotten(tmp_path: Path) -> None:
    client = _Client()
    client.statuses = [2]
    store = tmp_path / "p.json"
    runner, _p = _runner(client, store)
    result = runner.send(AuphonicChoices(), _write(tmp_path, "a.wav"), tmp_path / "out")
    assert (
        result.outcomes[0].state == FAILED and "could not process a.wav: Error" in result.summary()
    )
    assert load_pending(store) == []


def test_no_sound_file_in_the_result_is_not_a_success(tmp_path: Path) -> None:
    client = _Client()
    client.outputs = [{"format": "stats", "download_url": "https://auphonic.com/s.txt"}]
    runner, _p = _runner(client, tmp_path / "p.json")
    result = runner.send(AuphonicChoices(), _write(tmp_path, "a.wav"), tmp_path / "out")
    assert result.outcomes[0].state == FAILED
    assert (
        "no sound file" in result.outcomes[0].message
        and "1 other file" in result.outcomes[0].message
    )
    assert not any(name == "download" for name, _ in client.calls)


def test_losing_touch_while_waiting_says_it_may_still_finish(tmp_path: Path) -> None:
    client = _Client()
    client.statuses = [AuphonicError("Could not reach Auphonic: offline")] * 3
    store = tmp_path / "p.json"
    runner, _p = _runner(client, store)
    outcome = runner.send(AuphonicChoices(), _write(tmp_path, "a.wav"), tmp_path / "o").outcomes[0]
    assert outcome.state == WAITING and "already started and may still finish" in outcome.message
    assert len(load_pending(store)) == 1


def test_waiting_too_long_keeps_the_record(tmp_path: Path) -> None:
    client = _Client()
    client.statuses = [4] * 10
    ticks = iter(range(0, 100000, 4000))
    store = tmp_path / "p.json"
    runner, _p = _runner(client, store, clock=lambda: float(next(ticks)), timeout_seconds=7200.0)
    outcome = runner.send(AuphonicChoices(), _write(tmp_path, "a.wav"), tmp_path / "o").outcomes[0]
    assert outcome.state == WAITING and "after 2 hours" in outcome.message
    assert len(load_pending(store)) == 1


def test_a_failed_download_can_be_resumed(tmp_path: Path) -> None:
    client = _Client()
    client.download_error = AuphonicError("Could not reach Auphonic: reset")
    store = tmp_path / "p.json"
    runner, _p = _runner(client, store)
    outcome = runner.send(AuphonicChoices(), _write(tmp_path, "a.wav"), tmp_path / "o").outcomes[0]
    assert outcome.state == WAITING and "Downloading a.wav failed" in outcome.message
    assert len(load_pending(store)) == 1


def test_a_start_that_may_have_happened_is_not_retried(tmp_path: Path) -> None:
    client = _Client()

    def start(token: str, uuid: str) -> None:
        raise AuphonicError("Could not reach Auphonic: timed out")

    client.start_created = start  # type: ignore[method-assign]
    runner, _p = _runner(client, tmp_path / "p.json")
    outcome = runner.send(AuphonicChoices(), _write(tmp_path, "a.wav"), tmp_path / "o").outcomes[0]
    assert (
        outcome.state == FAILED
        and "check your Auphonic account before sending it again" in outcome.message
    )


def test_multitrack_uploads_every_track_into_one_production(tmp_path: Path) -> None:
    files = _write(tmp_path, "host.wav", "guest.wav")
    client = _Client()
    runner, _p = _runner(client, tmp_path / "p.json")
    result = runner.send(
        AuphonicChoices(mode=MULTITRACK, title="Panel: 1"), files, tmp_path / "out"
    )
    creates = [arg for name, arg in client.calls if name == "create"]
    uploads = [arg for name, arg in client.calls if name == "upload"]
    assert len(creates) == 1 and creates[0]["is_multitrack"] is True
    assert uploads == [("U1", "host", "host.wav"), ("U1", "guest", "guest.wav")]
    assert result.outcomes[0].state == SAVED
    assert result.outcomes[0].files == [tmp_path / "out" / "Panel 1" / "r.mp3"]


def test_the_runner_uses_the_shared_client_by_default(tmp_path: Path) -> None:
    runner = Runner("tok", tmp_path / "p.json")
    assert runner.client is auphonic


def test_progress_is_not_flooded(tmp_path: Path) -> None:
    client = _Client()

    def upload(token: str, uuid: str, path: Path, **kwargs: Any) -> None:
        for _ in range(500):
            kwargs["on_bytes"](3, 10)  # the same block size, over and over

    client.upload_input = upload  # type: ignore[method-assign]
    runner, progress = _runner(client, tmp_path / "p.json")
    runner.send(AuphonicChoices(), _write(tmp_path, "a.wav"), tmp_path / "o")
    uploads = [t for t, _f in progress if t.startswith("Uploading")]
    assert len(uploads) == 1


def test_the_lifecycle_never_reaches_the_network_by_itself() -> None:
    # The plan and the run hold no HTTP of their own: every call is the client's,
    # whose _request is the one reviewed egress site.
    from quill.core.publish import auphonic_plan, auphonic_run

    for module in (auphonic_plan, auphonic_run):
        source = Path(str(module.__file__)).read_text(encoding="utf-8")
        assert "urllib" not in source and "urlopen" not in source and "http_client" not in source
