"""A source checkout finds the libmpv the checkout already has.

Reported 2026-09-29: "why is mpv not working when running the run-quill-radio
script from the d:\\quill folder? I only see automatic and windows media."

Because ``find_libmpv`` looked everywhere except the repository. Its candidate
list covers the shipped shapes -- the ``QUILL_LIBMPV`` override, an Offline
Edition's ``{app}/tools/mpv``, the runtime folder, the on-demand engine pack --
and none of those exist in a tree you are developing in. Meanwhile the repo's
own build staging, ``build/deps/mpv/libmpv-2.dll``, is exactly where the
installer scripts put it, and it was sitting there the whole time.

What the listener saw was the 3.0.5 engine list doing its job: Preferences
offers no row for an engine this copy does not have, so "no libmpv" reads as
"only Automatic and Windows Media". The list was right; the search was wrong.

The guard matters as much as the search: a frozen build must never read a
developer's build directory. A shipped app that found a DLL there would be
loading something nobody chose to ship.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

from quill.ui.audio import mpv_engine


@pytest.fixture
def staged(tmp_path, monkeypatch):
    """A fake checkout with libmpv staged where the build scripts put it."""
    repo = tmp_path / "checkout"
    build = repo / "build" / "deps" / "mpv"
    build.mkdir(parents=True)
    dll = build / "libmpv-2.dll"
    dll.write_bytes(b"not a real dll")
    # find_libmpv derives the repo root from this module's own location.
    fake_module = repo / "quill" / "ui" / "audio" / "mpv_engine.py"
    fake_module.parent.mkdir(parents=True)
    fake_module.write_text("", encoding="utf-8")
    monkeypatch.setattr(mpv_engine, "__file__", str(fake_module))
    # None of the shipped locations exist for a source run.
    monkeypatch.delenv("QUILL_LIBMPV", raising=False)
    monkeypatch.delenv("QUILL_APP_ROOT", raising=False)
    monkeypatch.setattr(mpv_engine, "mpv_pack_dir", lambda: tmp_path / "no-pack")
    monkeypatch.setattr(sys, "executable", str(tmp_path / "python" / "python.exe"))
    return dll


def test_a_source_run_finds_the_staged_libmpv(staged, monkeypatch) -> None:
    """The whole fix: the DLL in the checkout is the one a source run uses."""
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert mpv_engine.find_libmpv() == staged


def test_a_frozen_build_never_reads_a_build_directory(staged, monkeypatch) -> None:
    """A shipped app must load only what was shipped with it."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert mpv_engine.find_libmpv() is None


def test_the_explicit_override_still_wins(staged, tmp_path, monkeypatch) -> None:
    """QUILL_LIBMPV is how somebody points at a build of their own."""
    monkeypatch.delattr(sys, "frozen", raising=False)
    chosen = tmp_path / "elsewhere" / "libmpv-2.dll"
    chosen.parent.mkdir(parents=True)
    chosen.write_bytes(b"not a real dll either")
    monkeypatch.setenv("QUILL_LIBMPV", str(chosen))
    assert mpv_engine.find_libmpv() == chosen


def test_no_dll_anywhere_is_still_none(tmp_path, monkeypatch) -> None:
    """No libmpv means the Windows Media engine, not an error."""
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.delenv("QUILL_LIBMPV", raising=False)
    monkeypatch.delenv("QUILL_APP_ROOT", raising=False)
    empty = tmp_path / "empty" / "quill" / "ui" / "audio" / "mpv_engine.py"
    empty.parent.mkdir(parents=True)
    monkeypatch.setattr(mpv_engine, "__file__", str(empty))
    monkeypatch.setattr(mpv_engine, "mpv_pack_dir", lambda: tmp_path / "no-pack")
    monkeypatch.setattr(sys, "executable", str(tmp_path / "python" / "python.exe"))
    assert mpv_engine.find_libmpv() is None


def test_the_real_module_still_imports() -> None:
    """The reload the other tests do must leave the module usable."""
    importlib.reload(mpv_engine)
    assert callable(mpv_engine.find_libmpv)
    assert isinstance(Path(__file__), Path)
