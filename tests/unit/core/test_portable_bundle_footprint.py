"""A portable copy writes nothing to the computer it is plugged into.

Quill-Radio-Portable-<ver>.zip, unpacked on a USB stick, keeps everything inside
the bundle from the first launch, with no setting to find first -- and deleting
the bundle's ``data`` folder turns it into an ordinary copy. Each test here is
one of the places a 2026-09 audit found that promise broken: recordings in the
host's Music folder, downloads in its Downloads folder, yt-dlp's cache under
``~/.cache``, secrets in its Credential Manager, and a host
``storage-mode.json`` taking over the stick's data entirely.

The shape is the real one: a fake bundle (``QuillRadio.exe`` beside ``data``),
and every profile variable pointed at a temporary "host" whose contents are
checked afterwards.
"""

from __future__ import annotations

import os
import sys
import types
from pathlib import Path

import pytest

from quill.core import paths


def _host_files(host: Path) -> list[Path]:
    return [p for p in host.rglob("*") if p.is_file()]


@pytest.fixture
def stick(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, Path]:
    """``(bundle, host)``: an unpacked portable Quill Radio and a stranger's profile."""
    host = tmp_path / "host"
    for sub in ("AppData/Roaming", "AppData/Local", "Music", "Downloads"):
        (host / sub).mkdir(parents=True)
    monkeypatch.setenv("APPDATA", str(host / "AppData" / "Roaming"))
    monkeypatch.setenv("LOCALAPPDATA", str(host / "AppData" / "Local"))
    monkeypatch.setenv("USERPROFILE", str(host))
    monkeypatch.setenv("HOME", str(host))
    bundle = tmp_path / "E" / "Quill Radio"
    (bundle / "data").mkdir(parents=True)
    (bundle / "QuillRadio.exe").write_bytes(b"MZ\x00\x00")
    monkeypatch.setenv("QUILL_APP_ROOT", str(bundle))
    monkeypatch.delenv("QUILL_DATA_DIR", raising=False)
    # Absent for the test *and* afterwards: setenv records the original state,
    # so undoing it removes what a test (or the code under test) set.
    for name in ("QUILL_PORTABLE", "WEBVIEW2_USER_DATA_FOLDER"):
        monkeypatch.setenv(name, "x")
        monkeypatch.delenv(name)
    return bundle.resolve(), host


def test_the_defaults_resolve_inside_the_bundle(stick: tuple[Path, Path]) -> None:
    from quill.core.radio import download_prefs, recordings_index
    from quill.core.radio.recording import RecordingSettings, _default_dir
    from quill.platform.windows import credential_store

    bundle, host = stick
    assert paths.portable_bundle_root() == bundle
    assert paths.app_data_dir() == bundle / "data"
    assert _default_dir() == bundle / "Recordings"
    assert recordings_index.recordings_dir(RecordingSettings()) == bundle / "Recordings"
    assert download_prefs.default_root() == bundle / "Downloads"
    assert download_prefs.resolved_root(download_prefs.DownloadPrefs()) == bundle / "Downloads"
    assert Path(paths.yt_dlp_cache_dir()).is_relative_to(bundle / "data")
    # No QUILL_PORTABLE (a direct pythonw launch): the secrets still stay here.
    assert credential_store.is_portable_mode() is True
    assert _host_files(host) == []


def test_a_chosen_folder_still_wins(stick: tuple[Path, Path], tmp_path: Path) -> None:
    from quill.core.radio import download_prefs, recordings_index
    from quill.core.radio.recording import RecordingSettings

    chosen = tmp_path / "chosen"
    settings = RecordingSettings(destination_root=str(chosen))
    assert recordings_index.recordings_dir(settings) == chosen
    prefs = download_prefs.DownloadPrefs(root=str(chosen))
    assert download_prefs.resolved_root(prefs) == chosen


def test_deleting_data_makes_an_ordinary_copy(stick: tuple[Path, Path]) -> None:
    from quill.core.radio import download_prefs
    from quill.core.radio.recording import _default_dir
    from quill.platform.windows import credential_store

    bundle, host = stick
    (bundle / "data").rmdir()

    assert paths.portable_bundle_root() is None
    assert _default_dir() == host / "Music" / "Quill Radio Recordings"
    assert download_prefs.default_root() == host / "Downloads" / "Quill Radio"
    assert credential_store.is_portable_mode() is False


def test_an_explicit_appdata_choice_is_not_portable_in_effect(
    stick: tuple[Path, Path],
) -> None:
    from quill.core.storage_mode import save_storage_mode

    save_storage_mode("appdata")

    assert paths.portable_bundle_root() is None


def test_propagating_the_environment_keeps_webview2_in_the_bundle(
    stick: tuple[Path, Path],
) -> None:
    """A direct launch still says it is portable, and the Spotify player's
    WebView2 profile (cookies, cache, the signed-in session) stays on the stick."""
    bundle, host = stick

    paths.propagate_portable_environment()

    assert os.environ["WEBVIEW2_USER_DATA_FOLDER"] == str(bundle / "data" / "webview2")
    assert _host_files(host) == []


def test_an_installed_copy_leaves_webview2_alone(
    monkeypatch: pytest.MonkeyPatch, stick: tuple[Path, Path]
) -> None:
    bundle, _host = stick
    (bundle / "data").rmdir()

    paths.propagate_portable_environment()

    assert "WEBVIEW2_USER_DATA_FOLDER" not in os.environ


class _FakeYoutubeDL:
    seen: list[dict[str, object]] = []

    def __init__(self, options: dict[str, object]) -> None:
        _FakeYoutubeDL.seen.append(options)

    def __enter__(self) -> _FakeYoutubeDL:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def extract_info(self, _url: str, download: bool = False) -> dict[str, object]:
        return {}

    def prepare_filename(self, _info: object) -> str:
        return "clip.m4a"


def test_every_yt_dlp_call_keeps_its_cache_in_the_data_folder(
    monkeypatch: pytest.MonkeyPatch, stick: tuple[Path, Path], tmp_path: Path
) -> None:
    """Unset, yt-dlp caches YouTube's player code in ~/.cache/yt-dlp."""
    from quill.core.audio import url_import
    from quill.core.radio import youtube, youtube_channels

    bundle, _host = stick
    monkeypatch.setitem(sys.modules, "yt_dlp", types.SimpleNamespace(YoutubeDL=_FakeYoutubeDL))
    _FakeYoutubeDL.seen = []

    youtube._default_resolver("https://www.youtube.com/watch?v=abc")
    youtube._default_search_resolver("ytsearch5:news")
    youtube._default_playlist_resolver("https://www.youtube.com/playlist?list=x")
    youtube_channels._flat_entries("https://www.youtube.com/@x", limit=5, offset=0)
    url_import._default_download("https://example.com/v", tmp_path, None)

    assert len(_FakeYoutubeDL.seen) == 5
    for options in _FakeYoutubeDL.seen:
        assert options["cachedir"] == str(bundle / "data" / "yt-dlp-cache")
