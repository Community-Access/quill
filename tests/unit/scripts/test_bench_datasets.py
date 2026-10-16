"""The benchmark's dataset table and its fetch script (dict.md B-1b).

No network: every download here is a fake that writes a tiny archive, and a
socket guard fails the test if anything tries to connect.
"""

from __future__ import annotations

import hashlib
import importlib
import io
import json
import socket
import sys
import tarfile
import urllib.parse
from pathlib import Path
from typing import Any

import pytest

_REPO = Path(__file__).resolve().parents[3]
_SCRIPTS = _REPO / "scripts"


def _fetch() -> Any:
    if str(_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS))
    return importlib.import_module("fetch_bench_audio")


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("a benchmark test tried to use the network")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.delenv("CI", raising=False)


@pytest.fixture()
def cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "cache"
    monkeypatch.setenv("QUILL_BENCH_AUDIO", str(root))
    return root


# -- the table ---------------------------------------------------------------- #

_REQUIRED = {
    "id",
    "name",
    "part",
    "licence",
    "licence_url",
    "licence_verified",
    "attribution",
    "redistribution",
    "access",
    "source_url",
    "version",
    "size",
    "languages",
    "style",
    "speech_disabilities",
    "contamination",
    "contaminated_models",
    "layout",
    "archives",
}


def test_every_dataset_names_its_licence_size_source_and_checksum_slot() -> None:
    table = _fetch().load_table()
    ids = [entry["id"] for entry in table["datasets"]]
    assert len(ids) == len(set(ids))
    for entry in table["datasets"]:
        assert _REQUIRED <= set(entry), entry["id"]
        assert entry["licence"].strip() and entry["size"].strip(), entry["id"]
        assert entry["access"] in {"auto", "by_request", "assets", "not_usable"}, entry["id"]
        assert entry["redistribution"] in {"allowed", "attribution", "never"}, entry["id"]
        for archive in entry["archives"]:
            assert set(archive) == {"url", "sha256", "bytes"}, entry["id"]
            assert archive["sha256"] is None or len(archive["sha256"]) == 64


def test_only_automatic_sets_have_archives_and_licensed_ones_are_never_fetched() -> None:
    for entry in _fetch().load_table()["datasets"]:
        if entry["access"] != "auto":
            assert entry["archives"] == [], entry["id"]
        else:
            assert entry["archives"], entry["id"]
    names = {e["id"]: e["access"] for e in _fetch().load_table()["datasets"]}
    for licensed in ("common-voice", "chime", "torgo", "speech-accessibility-project"):
        assert names[licensed] == "by_request"
    assert names["uaspeech"] == "not_usable"


def test_every_archive_host_is_allowed_and_named_in_the_docstring() -> None:
    fetch = _fetch()
    hosts = set()
    for entry in fetch.load_table()["datasets"]:
        for archive in entry["archives"]:
            parsed = urllib.parse.urlparse(archive["url"])
            assert parsed.scheme == "https"
            hosts.add(parsed.hostname)
    assert hosts <= fetch.ALLOWED_HOSTS
    for host in fetch.ALLOWED_HOSTS:
        assert host in (fetch.__doc__ or ""), host


def test_the_contamination_flag_covers_families_and_everyone() -> None:
    fetch = _fetch()
    sets = fetch.datasets()
    assert fetch.may_be_in_training_data(sets["librispeech-test-clean"], "parakeet")
    assert fetch.may_be_in_training_data(sets["fleurs-en"], "moonshine_base")
    assert not fetch.may_be_in_training_data(sets["fleurs-en"], "whisper_small")
    assert not fetch.may_be_in_training_data(sets["torgo"], "moonshine")


def test_the_model_cutoffs_are_dates_or_honestly_unknown() -> None:
    cutoffs = _fetch().load_table()["model_cutoffs"]
    assert cutoffs["moonshine"]["date"] and cutoffs["whisper"]["date"]
    assert cutoffs["parakeet"]["date"] is None and cutoffs["parakeet"]["basis"]


# -- the cache -------------------------------------------------------------------- #


def test_the_cache_is_outside_the_repository(monkeypatch: pytest.MonkeyPatch) -> None:
    fetch = _fetch()
    monkeypatch.delenv("QUILL_BENCH_AUDIO", raising=False)
    root = fetch.cache_root()
    assert _REPO not in root.parents
    monkeypatch.setenv("QUILL_BENCH_AUDIO", str(_REPO / "build" / "bench-audio"))
    with pytest.raises(SystemExit, match="inside the repository"):
        fetch.cache_root()


# -- fetching ------------------------------------------------------------------------ #


def _tiny_archive() -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        data = b"hello"
        info = tarfile.TarInfo("set/readme.txt")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def _entry(sha: str | None) -> dict[str, Any]:
    return {
        "id": "tiny",
        "name": "Tiny",
        "access": "auto",
        "size": "1 KB",
        "licence": "CC0",
        "attribution": "nobody",
        "source_url": "https://www.openslr.org/0",
        "archives": [{"url": "https://www.openslr.org/resources/0/tiny.tar.gz", "sha256": sha}],
    }


def test_an_unpinned_archive_is_refused_without_pin(cache: Path) -> None:
    with pytest.raises(SystemExit, match="--pin"):
        _fetch().fetch(_entry(None), pin=False, confirm=lambda _q: True)


def test_nothing_is_fetched_in_ci(cache: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CI", "true")
    with pytest.raises(SystemExit, match="CI"):
        _fetch().fetch(_entry("0" * 64), pin=False, confirm=lambda _q: True)


def test_a_licensed_set_says_where_to_ask_and_downloads_nothing(cache: Path) -> None:
    fetch = _fetch()
    with pytest.raises(SystemExit, match="--local"):
        fetch.fetch(fetch.dataset("torgo"), pin=True, confirm=lambda _q: True)


def test_saying_no_downloads_nothing(cache: Path) -> None:
    calls: list[str] = []
    with pytest.raises(SystemExit, match="Nothing was downloaded"):
        _fetch().fetch(
            _entry("0" * 64),
            pin=False,
            confirm=lambda _q: False,
            download=lambda url, _t: calls.append(url),
        )
    assert calls == []


def test_a_pinned_archive_is_verified_unpacked_and_attributed(cache: Path) -> None:
    fetch = _fetch()
    data = _tiny_archive()
    digest = hashlib.sha256(data).hexdigest()
    recorded = fetch.fetch(
        _entry(digest),
        pin=False,
        confirm=lambda _q: True,
        download=lambda _url, target: target.write_bytes(data),
    )
    assert recorded == [(_entry(digest)["archives"][0]["url"], digest)]
    assert (cache / "tiny" / "raw" / "unpacked" / "set" / "readme.txt").read_bytes() == b"hello"
    assert "CC0" in (cache / "tiny" / "ATTRIBUTION.txt").read_text(encoding="utf-8")


def test_a_hash_mismatch_deletes_the_download(cache: Path) -> None:
    with pytest.raises(SystemExit, match="does not match"):
        _fetch().fetch(
            _entry("f" * 64),
            pin=False,
            confirm=lambda _q: True,
            download=lambda _url, target: target.write_bytes(_tiny_archive()),
        )
    assert not (cache / "tiny" / "raw" / "tiny.tar.gz").exists()


def test_an_archive_cannot_write_outside_its_folder(tmp_path: Path) -> None:
    evil = tmp_path / "evil.tar"
    with tarfile.open(evil, "w") as tar:
        info = tarfile.TarInfo("../escaped.txt")
        info.size = 1
        tar.addfile(info, io.BytesIO(b"x"))
    with pytest.raises(tarfile.TarError):
        _fetch().safe_unpack(evil, tmp_path / "inside")
    assert not (tmp_path / "escaped.txt").exists()


def test_pins_are_written_into_a_copy_of_the_table(tmp_path: Path) -> None:
    fetch = _fetch()
    copy = tmp_path / "bench_datasets.json"
    copy.write_text(fetch.DATASETS_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    url = "https://www.openslr.org/resources/12/test-clean.tar.gz"
    fetch.write_pins([(url, "a" * 64)], copy)
    table = json.loads(copy.read_text(encoding="utf-8"))
    entry = next(e for e in table["datasets"] if e["id"] == "librispeech-test-clean")
    assert entry["archives"][0]["sha256"] == "a" * 64


def test_a_local_copy_needs_a_transcripts_file(cache: Path, tmp_path: Path) -> None:
    fetch = _fetch()
    entry = fetch.dataset("torgo")
    with pytest.raises(SystemExit, match="transcripts.txt"):
        fetch.register_local(entry, tmp_path)
    (tmp_path / "transcripts.txt").write_text("a.wav\thello\n", encoding="utf-8")
    fetch.register_local(entry, tmp_path)
    assert fetch.prepared_folder("torgo") == tmp_path.resolve()


# -- preparing and subsets ------------------------------------------------------------ #


def test_librispeech_layout_becomes_rows_with_speaker_and_gender(tmp_path: Path) -> None:
    chapter = tmp_path / "LibriSpeech" / "test-clean" / "1089" / "134686"
    chapter.mkdir(parents=True)
    (chapter / "1089-134686.trans.txt").write_text(
        "1089-134686-0000 HE HOPED THERE WOULD BE STEW\n", encoding="utf-8"
    )
    (tmp_path / "LibriSpeech" / "SPEAKERS.TXT").write_text(
        "; ID | SEX | SUBSET\n1089 | M | test-clean\n", encoding="utf-8"
    )
    rows = _fetch().librispeech_rows(tmp_path)
    assert rows[0][:3] == (
        "1089-134686-0000.wav",
        "he hoped there would be stew",
        {"speaker": "1089", "gender": "male", "language": "en"},
    )


def test_write_prepared_makes_the_folder_dictbench_reads(tmp_path: Path) -> None:
    fetch = _fetch()
    rows = [("a.wav", "Hello.", {"speaker": "s1", "accent": "scottish"})]
    fetch.write_prepared(tmp_path, rows, lambda _n, target: target.write_bytes(b""))
    assert (tmp_path / "transcripts.txt").read_text(encoding="utf-8") == "a.wav\tHello.\n"
    assert fetch.read_speakers(tmp_path)["a.wav"]["accent"] == "scottish"


def test_a_seeded_subset_is_the_same_every_time_and_caps_each_speaker() -> None:
    fetch = _fetch()
    names = [f"{n:03d}.wav" for n in range(100)]
    speakers = {
        name: {"speaker": "prolific" if i < 60 else f"s{i}"} for i, name in enumerate(names)
    }
    first = fetch.seeded_subset(names, seed=7, count=30, speakers=speakers, per_speaker=3)
    again = fetch.seeded_subset(reversed(names), seed=7, count=30, speakers=speakers, per_speaker=3)
    assert first == again and len(first) == 30
    assert sum(1 for n in first if speakers[n]["speaker"] == "prolific") <= 3


def test_an_unpinned_subset_comes_from_its_seed(tmp_path: Path) -> None:
    fetch = _fetch()
    lines = [f"{n:02d}.wav\tword {n}" for n in range(40)]
    (tmp_path / "transcripts.txt").write_text("\n".join(lines), encoding="utf-8")
    chosen = fetch.subset_names("anything", "quick", tmp_path)
    assert len(chosen) == 20
    assert chosen == fetch.subset_names("anything", "quick", tmp_path)


def test_resampling_keeps_the_duration() -> None:
    np = pytest.importorskip("numpy")
    tone = np.sin(np.arange(22_050) * 2 * np.pi * 440 / 22_050).astype("float32")
    out = _fetch().resample(tone, 22_050, 16_000)
    assert out.size == 16_000
    assert 0.6 < float(np.max(np.abs(out))) < 1.2
