"""Tests for letting an updated yt-dlp supersede the bundled one.

yt-dlp ships inside the app (a ~3 MB wheel, so a YouTube link works on a fresh
install with no download) but goes stale whenever YouTube changes its player --
upstream ships fixes far more often than QUILL ships releases. So the on-demand
installer has to be able to *override* the bundled copy, and in a frozen build
prepending to ``sys.path`` is not enough: PyInstaller's FrozenImporter sits in
``sys.meta_path``, which is searched in full before ``sys.path`` ever is.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from quill.core.speech import engine_install
from quill.core.speech.engine_pack_imports import EnginePackPriorityFinder


@pytest.fixture(autouse=True)
def _restore_meta_path():
    original = list(sys.meta_path)
    yield
    sys.meta_path[:] = original


def _make_pack(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, marker: str) -> Path:
    pack = tmp_path / "engine-packs" / "yt-dlp"
    (pack / "yt_dlp").mkdir(parents=True)
    (pack / "yt_dlp" / "__init__.py").write_text(f"MARKER = {marker!r}\n", encoding="utf-8")
    monkeypatch.setattr(engine_install, "yt_dlp_pack_dir", lambda: pack)
    return pack


def test_no_pack_means_no_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The normal case: nobody has pressed update, so nothing is installed."""
    monkeypatch.setattr(engine_install, "yt_dlp_pack_dir", lambda: tmp_path / "absent")
    before = list(sys.meta_path)
    assert engine_install.prefer_engine_pack_yt_dlp() is False
    assert sys.meta_path == before


def test_a_pack_installs_a_finder_ahead_of_everything_else(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ahead of *everything*, because in a frozen build the thing it has to beat
    is FrozenImporter, which lives in meta_path itself."""
    _make_pack(tmp_path, monkeypatch, marker="pack")
    assert engine_install.prefer_engine_pack_yt_dlp() is True
    assert isinstance(sys.meta_path[0], EnginePackPriorityFinder)


def test_installing_twice_does_not_stack_finders(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """activate_engine_packs() may be called more than once per process."""
    _make_pack(tmp_path, monkeypatch, marker="pack")
    engine_install.prefer_engine_pack_yt_dlp()
    engine_install.prefer_engine_pack_yt_dlp()
    finders = [f for f in sys.meta_path if isinstance(f, EnginePackPriorityFinder)]
    assert len(finders) == 1


def test_the_finder_declines_every_other_module(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """It must not perturb any import but yt-dlp's."""
    pack = _make_pack(tmp_path, monkeypatch, marker="pack")
    finder = EnginePackPriorityFinder(pack, "yt_dlp")
    for name in ("json", "quill", "quill.core", "yt_dlpx", "wx"):
        assert finder.find_spec(name) is None


def test_the_finder_resolves_yt_dlp_out_of_the_pack(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pack = _make_pack(tmp_path, monkeypatch, marker="pack")
    finder = EnginePackPriorityFinder(pack, "yt_dlp")
    spec = finder.find_spec("yt_dlp")
    assert spec is not None
    assert spec.origin is not None
    assert Path(spec.origin).is_relative_to(pack)


def test_the_pack_copy_wins_over_an_earlier_one_on_sys_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The point of the whole mechanism: the updated copy is the one imported.

    A plain sys.path entry stands in for the bundled copy here -- a real frozen
    build resolves it through FrozenImporter, which is likewise in meta_path and
    likewise loses to a finder inserted at position 0.
    """
    bundled = tmp_path / "bundled"
    (bundled / "yt_dlp").mkdir(parents=True)
    (bundled / "yt_dlp" / "__init__.py").write_text("MARKER = 'bundled'\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(bundled))
    _make_pack(tmp_path, monkeypatch, marker="pack")
    engine_install.prefer_engine_pack_yt_dlp()

    monkeypatch.delitem(sys.modules, "yt_dlp", raising=False)
    import yt_dlp  # noqa: PLC0415 -- resolved through the finder under test

    try:
        assert yt_dlp.MARKER == "pack"
    finally:
        sys.modules.pop("yt_dlp", None)
