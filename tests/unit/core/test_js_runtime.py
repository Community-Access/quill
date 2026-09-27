"""The bundled deno lookup that lets yt-dlp solve YouTube's JS challenges."""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from quill.core import js_runtime


def _deno(folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    exe = folder / js_runtime.DENO_EXE
    exe.write_bytes(b"")
    return exe


def test_app_root_first_then_the_runtime_folder(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_APP_ROOT", str(tmp_path / "app"))
    monkeypatch.setattr(sys, "executable", str(tmp_path / "rt" / "QuillVilleRuntime.exe"))
    assert js_runtime.deno_search_dirs() == [
        tmp_path / "app" / "tools" / "deno",
        tmp_path / "rt" / "tools" / "deno",
    ]


def test_found_beside_the_runtime_without_a_launcher(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("QUILL_APP_ROOT", raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "rt" / "pythonw.exe"))
    exe = _deno(tmp_path / "rt" / "tools" / "deno")
    assert js_runtime.find_deno() == exe


def test_never_from_path(monkeypatch, tmp_path: Path) -> None:
    """A deno somewhere on the host is not one QUILL shipped."""
    monkeypatch.delenv("QUILL_APP_ROOT", raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "rt" / "pythonw.exe"))
    _deno(tmp_path / "elsewhere")
    monkeypatch.setenv("PATH", str(tmp_path / "elsewhere"))
    assert js_runtime.find_deno() is None
    assert js_runtime.yt_dlp_js_options() == {}


def test_options_name_the_bundled_deno_and_no_remote_components(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_APP_ROOT", str(tmp_path / "app"))
    exe = _deno(tmp_path / "app" / "tools" / "deno")
    options = js_runtime.yt_dlp_js_options()
    assert options == {"js_runtimes": {"deno": {"path": str(exe)}}}
    assert "remote_components" not in options


@pytest.fixture
def fake_yt_dlp(monkeypatch):
    """A stand-in yt_dlp module that records the options it was built with."""
    seen: list[dict] = []

    class _YDL:
        def __init__(self, options):
            seen.append(options)

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

        def extract_info(self, url, download=False):
            return {"url": "https://media.example/a.m4a", "title": "t", "entries": []}

        def prepare_filename(self, info):
            return "x.m4a"

    module = types.ModuleType("yt_dlp")
    module.YoutubeDL = _YDL  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "yt_dlp", module)
    return seen


def test_radio_resolver_hands_yt_dlp_the_bundled_deno(
    monkeypatch, tmp_path: Path, fake_yt_dlp
) -> None:
    from quill.core.radio import youtube

    monkeypatch.setenv("QUILL_APP_ROOT", str(tmp_path / "app"))
    exe = _deno(tmp_path / "app" / "tools" / "deno")
    youtube._default_resolver("https://www.youtube.com/watch?v=abc")
    assert fake_yt_dlp[-1]["js_runtimes"] == {"deno": {"path": str(exe)}}
    assert "remote_components" not in fake_yt_dlp[-1]
