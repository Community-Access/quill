"""A CMake cache generated for a different checkout path must be discarded.

CMakeCache.txt records the absolute source and binary directories it was
configured with, and CMake hard-errors rather than reusing a cache whose
recorded paths differ. A checkout moved between drives produces exactly that:
caches written when this repo lived on ``S:\\`` stopped every Quill Radio and
Quill Weather build once it moved to ``D:\\``, and because ``build/`` is
gitignored the stale files never showed up in ``git status``.
"""

from __future__ import annotations

from pathlib import Path

from scripts.build_native_launcher import _LAUNCHER_SRC, _discard_relocated_cmake_cache


def _write_cache(build_dir: Path, home: str) -> Path:
    build_dir.mkdir(parents=True, exist_ok=True)
    cache = build_dir / "CMakeCache.txt"
    cache.write_text(f"CMAKE_HOME_DIRECTORY:INTERNAL={home}\n", encoding="utf-8")
    return cache


def test_cache_from_another_checkout_path_is_discarded(tmp_path: Path) -> None:
    build_dir = tmp_path / "radio"
    _write_cache(build_dir, "S:/QUILL/quill/native/launcher")
    (build_dir / "leftover.obj").write_text("x", encoding="utf-8")

    assert _discard_relocated_cmake_cache(build_dir) is True
    assert not build_dir.exists(), "the whole stale build tree must go, not just the cache file"


def test_cache_for_this_checkout_is_kept(tmp_path: Path) -> None:
    """Reconfiguring is cheap, recompiling is not -- never discard a usable cache."""
    build_dir = tmp_path / "radio"
    _write_cache(build_dir, _LAUNCHER_SRC.as_posix())

    assert _discard_relocated_cmake_cache(build_dir) is False
    assert (build_dir / "CMakeCache.txt").is_file()


def test_path_comparison_ignores_case(tmp_path: Path) -> None:
    """Windows paths differ in case between tools; that is not a relocation."""
    build_dir = tmp_path / "radio"
    _write_cache(build_dir, _LAUNCHER_SRC.as_posix().upper())

    assert _discard_relocated_cmake_cache(build_dir) is False


def test_missing_build_dir_is_not_an_error(tmp_path: Path) -> None:
    """The first build on a clean machine has no cache at all."""
    assert _discard_relocated_cmake_cache(tmp_path / "never-built") is False


def test_unreadable_cache_is_treated_as_stale(tmp_path: Path) -> None:
    """A cache we cannot parse is not one we can trust to match."""
    build_dir = tmp_path / "radio"
    build_dir.mkdir(parents=True)
    (build_dir / "CMakeCache.txt").write_bytes(b"\xff\xfe\x00garbage")

    assert _discard_relocated_cmake_cache(build_dir) is True
