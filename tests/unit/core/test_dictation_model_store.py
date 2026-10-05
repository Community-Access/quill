"""Downloading, resuming, checking and removing optional speech models -- no network."""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.core import release_assets
from quill.core.windows_dictation import engines, model_store
from quill.core.windows_dictation.model_catalog import DownloadableModel, DownloadFile

_BODY = {"encoder.onnx": b"encoder-bytes", "tokens.txt": b"a 1\nb 2\n"}


def _model(**overrides) -> DownloadableModel:
    files = tuple(
        DownloadFile(
            name,
            "encoder" if "encoder" in name else "tokens",
            len(body),
            hashlib.sha256(body).hexdigest(),
        )
        for name, body in _BODY.items()
    )
    values = dict(
        id="nemotron",
        name="Test Model",
        good_for="tests",
        description="d",
        group="g",
        kind="whisper",
        languages=("en",),
        works_best_on="w",
        accuracy="a",
        repo="o/r",
        commit="0" * 40,
        files=files,
        licence="MIT",
        licence_url="https://x",
        source="s",
        cost_factor=1.0,
        folder="test-model",
    )
    values.update(overrides)
    return DownloadableModel(**values)


@pytest.fixture
def root(tmp_path, monkeypatch) -> Path:
    monkeypatch.setenv(model_store.DOWNLOADS_VARIABLE, str(tmp_path / "models"))
    return tmp_path / "models"


def _fake_fetch(calls: list[str], *, corrupt: str = "", cancel_on: str = "", fail_on: str = ""):
    def fetch(url, dest, *, sha256, progress, should_cancel, label, partial):
        name = Path(dest).name
        calls.append(name)
        if name == cancel_on:
            Path(partial).write_bytes(_BODY[name][:3])  # part of it arrived
            raise release_assets.DownloadCancelled("Download cancelled.")
        if name == fail_on:
            raise release_assets.ReleaseAssetError("Download failed from all sources: offline")
        body = b"tampered" if name == corrupt else _BODY[name]
        if hashlib.sha256(body).hexdigest() != sha256:
            raise release_assets.ReleaseAssetError("Checksum mismatch for " + name)
        progress(0.5, label)
        Path(dest).write_bytes(body)
        progress(1.0, label)
        return dest

    return fetch


def test_installed_copies_share_local_app_data(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv(model_store.DOWNLOADS_VARIABLE, raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr("quill.core.paths.portable_bundle_root", lambda: None)
    assert model_store.downloads_root() == tmp_path / "QuillVille" / "Dictation" / "models"


def test_a_portable_copy_keeps_models_inside_the_portable_folder(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv(model_store.DOWNLOADS_VARIABLE, raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "host"))
    stick = tmp_path / "stick"
    monkeypatch.setattr("quill.core.paths.portable_bundle_root", lambda: stick)
    assert model_store.downloads_root() == stick / "data" / "dictation" / "models"
    model = _model()
    assert model_store.model_folder(model).is_relative_to(stick)


def test_download_fetches_each_file_and_reports_rising_progress(root) -> None:
    model, calls, seen = _model(), [], []
    folder = model_store.download(
        model, progress=lambda f, _m: seen.append(f), fetch=_fake_fetch(calls)
    )
    assert folder == root / "test-model"
    assert model_store.installed(model)
    assert calls == ["encoder.onnx", "tokens.txt"]
    assert seen == sorted(seen) and seen[-1] == 1.0
    # A second Download fetches nothing: everything is here at its pinned size.
    calls.clear()
    model_store.download(model, fetch=_fake_fetch(calls))
    assert calls == []


def test_a_cancelled_download_keeps_what_arrived_and_resumes(root) -> None:
    model, calls = _model(), []
    with pytest.raises(release_assets.DownloadCancelled):
        model_store.download(model, fetch=_fake_fetch(calls, cancel_on="tokens.txt"))
    part = root / "test-model" / "tokens.txt.part"
    assert part.is_file(), "the partial file is kept for next time"
    assert not model_store.installed(model)
    assert model_store.remaining_bytes(model) == len(_BODY["tokens.txt"]) - 3
    calls.clear()
    model_store.download(model, fetch=_fake_fetch(calls))
    assert calls == ["tokens.txt"], "the finished file is not fetched again"


def test_a_part_that_arrived_whole_is_checked_and_kept_without_a_request(root) -> None:
    model, calls = _model(), []
    folder = root / "test-model"
    folder.mkdir(parents=True)
    (folder / "encoder.onnx.part").write_bytes(_BODY["encoder.onnx"])
    model_store.download(model, fetch=_fake_fetch(calls))
    assert calls == ["tokens.txt"]
    assert (folder / "encoder.onnx").read_bytes() == _BODY["encoder.onnx"]


def test_a_checksum_failure_is_a_plain_sentence(root) -> None:
    with pytest.raises(model_store.ModelDownloadError, match="checksum"):
        model_store.download(_model(), fetch=_fake_fetch([], corrupt="encoder.onnx"))


def test_a_network_failure_says_what_was_kept(root) -> None:
    with pytest.raises(model_store.ModelDownloadError, match="arrived whole are kept"):
        model_store.download(_model(), fetch=_fake_fetch([], fail_on="encoder.onnx"))


def test_free_space_is_checked_on_the_drive_the_model_would_go_to(root) -> None:
    model = _model()
    asked: list[Path] = []

    def usage(path: Path):
        asked.append(path)
        return SimpleNamespace(free=10)

    problem = model_store.free_space_problem(model, usage=usage)
    assert "not enough free space" in problem and "Test Model" in problem
    assert asked and root.is_relative_to(asked[0]) or asked[0] in root.parents
    roomy = model_store.free_space_problem(model, usage=lambda _p: SimpleNamespace(free=10**12))
    assert roomy == ""


def test_remove_deletes_the_model_and_its_partial_files(root, monkeypatch) -> None:
    model = _model()
    monkeypatch.setattr(model_store, "downloadable", lambda _id: model)
    model_store.download(model, fetch=_fake_fetch([]))
    (root / "test-model" / "extra.part").write_bytes(b"x")
    model_store.remove(model.id)
    assert not (root / "test-model").exists()
    model_store.remove(model.id)  # twice is fine


def test_remove_that_windows_refuses_is_a_sentence(root, monkeypatch) -> None:
    model = _model()
    monkeypatch.setattr(model_store, "downloadable", lambda _id: model)
    (root / "test-model").mkdir(parents=True)

    def refuse(_path):
        raise PermissionError("in use")

    monkeypatch.setattr(model_store.shutil, "rmtree", refuse)
    with pytest.raises(model_store.ModelDownloadError, match="dictation is using it"):
        model_store.remove(model.id)


def test_the_engine_list_shows_downloaded_models_and_a_missing_saved_one(monkeypatch) -> None:
    from quill.core.windows_dictation.model_catalog import CATALOGUE

    whisper_small = next(m for m in CATALOGUE if m.id == "whisper_small")
    monkeypatch.setattr(model_store, "installed_models", lambda: [whisper_small])
    rows = dict(engines.engine_choices("nemotron"))
    assert rows["whisper_small"] == "Whisper small (downloaded)"
    assert "not downloaded" in rows["nemotron"]
    assert list(rows)[:4] == ["moonshine", "whisper", "windows", "voice_typing"]


def test_download_verified_keeps_a_partial_on_cancel_and_drops_it_on_a_bad_checksum(
    tmp_path, monkeypatch
) -> None:
    partial = tmp_path / "m.bin.part"

    def cancelled(urls, dest, progress, **_kw):
        Path(dest).write_bytes(b"half")
        raise release_assets.DownloadCancelled("Download cancelled.")

    monkeypatch.setattr(release_assets, "_download_resumable", cancelled)
    with pytest.raises(release_assets.DownloadCancelled):
        release_assets.download_verified(
            "https://example.org/m.bin", tmp_path / "m.bin", sha256="0" * 64, partial=partial
        )
    assert partial.read_bytes() == b"half"

    def finished(urls, dest, progress, **_kw):
        Path(dest).write_bytes(b"whole but wrong")

    monkeypatch.setattr(release_assets, "_download_resumable", finished)
    with pytest.raises(release_assets.ReleaseAssetError, match="Checksum"):
        release_assets.download_verified(
            "https://example.org/m.bin", tmp_path / "m.bin", sha256="0" * 64, partial=partial
        )
    assert not partial.exists()
    assert not (tmp_path / "m.bin").exists()


def test_safe_mode_refuses_with_a_sentence_and_nothing_is_fetched(root, monkeypatch) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    with pytest.raises(model_store.ModelDownloadError, match="Safe Mode"):
        model_store.download(_model())


def test_the_only_way_out_is_the_shared_reviewed_downloader() -> None:
    """GATE-9: model_store opens no connection of its own; every byte comes
    through release_assets.download_verified, whose egress entry names it."""
    import inspect

    from quill.tools.network_egress_entries import _REVIEWED_EGRESS

    source = inspect.getsource(model_store)
    assert "urlopen" not in source and "requests" not in source
    assert "download_verified" in source
    assert "model_store.py" in _REVIEWED_EGRESS["core/release_assets.py::_download_resumable"]
