"""Build ``quill-optilab``, the adapter around OptiLab Core, if a toolchain exists.

OptiLab Core is by **Lanes Audio / dgl1984** (https://github.com/dgl1984/optilab),
vendored unmodified at v1.4.0 under ``quill/native/optilab/upstream/`` and licensed
Apache-2.0 WITH the Commons Clause v1.0. QUILL owns only the thin adapter
(``quill_optilab.cpp``), which contains no DSP -- upstream asks consumers to do
exactly that, because its C++ API is not a stable C ABI.

Usage::

    python scripts/build_native_optilab.py
    python scripts/build_native_optilab.py --out dist\\QuillRadio

**Best-effort by design.** With no CMake or C++ compiler this prints what is
missing and exits 0 without producing an executable. Exact OptiLab processing is
an optional feature: when the adapter is absent, ``optilab_adapter.available()``
is False, every surface says so in words, and the built-in ffmpeg chain runs
exactly as it always has. A missing toolchain must never fail a build.

``--require`` turns that around for a release build that has decided the
component is not optional there: a failure then exits non-zero.

The executable lands beside the sources at ``quill/native/optilab/quill-optilab.exe``
so a *source checkout* finds it with no configuration -- deliberately unlike the
other optional native component, whose build wrote to a directory nothing on
``sys.path`` could import, so no developer ever exercised it and only a user
could have found a regression.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "quill" / "native" / "optilab"
_BUILD = _SRC / "build"
_EXE_STEM = "quill-optilab"


def _exe_name() -> str:
    return f"{_EXE_STEM}.exe" if sys.platform.startswith("win") else _EXE_STEM


def _find_built() -> Path | None:
    """The freshly built executable, wherever this generator put it."""
    for candidate in (
        _BUILD / "Release" / _exe_name(),
        _BUILD / "Debug" / _exe_name(),
        _BUILD / _exe_name(),
    ):
        if candidate.is_file():
            return candidate
    return None


def _discard_relocated_cache() -> bool:
    """Drop a CMake cache generated for a different checkout path.

    CMakeCache.txt records the absolute source directory it was configured with,
    and CMake hard-errors rather than reuse a cache whose recorded path differs.
    A checkout moved between drives produces exactly that, and because ``build/``
    is gitignored the stale files never appear in ``git status`` -- the same trap
    ``build_native_launcher.py`` already documents. The cache is a pure build
    artifact, so discarding it costs one reconfigure.
    """
    cache = _BUILD / "CMakeCache.txt"
    if not cache.is_file():
        return False
    expected = f"CMAKE_HOME_DIRECTORY:INTERNAL={_SRC.as_posix()}"
    try:
        text = cache.read_text(encoding="utf-8", errors="replace")
    except OSError:
        text = ""
    if expected.casefold() in text.casefold():
        return False
    print(f"Discarding CMake cache configured for another path: {_BUILD}")
    shutil.rmtree(_BUILD, ignore_errors=True)
    return True


def build(*, out_dir: Path | None = None, require: bool = False) -> int:
    if not _SRC.is_dir():
        print(f"No OptiLab adapter sources at {_SRC}; nothing to build.")
        return 1 if require else 0
    cmake = shutil.which("cmake")
    if cmake is None:
        print("CMake was not found on PATH; skipping the OptiLab adapter.")
        print("Exact OptiLab processing will be unavailable in this build.")
        return 1 if require else 0
    _discard_relocated_cache()
    try:
        subprocess.run(
            [cmake, "-S", str(_SRC), "-B", str(_BUILD)],
            cwd=str(_REPO_ROOT),
            check=True,
        )
        subprocess.run(
            [cmake, "--build", str(_BUILD), "--config", "Release"],
            cwd=str(_REPO_ROOT),
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"The OptiLab adapter did not build ({exc}).")
        print("Exact OptiLab processing will be unavailable in this build.")
        return 1 if require else 0
    built = _find_built()
    if built is None:
        print("CMake reported success but no executable was produced.")
        return 1 if require else 0
    # Beside the sources: this is the path quill.core.optilab_adapter looks in
    # first, so a checkout that has built once is a checkout where the tests run.
    staged = _SRC / _exe_name()
    if built != staged:
        shutil.copy2(built, staged)
    print(f"Built the OptiLab adapter: {staged}")
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(staged, out_dir / _exe_name())
        print(f"Staged it into {out_dir}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=None, help="also copy the exe here")
    parser.add_argument(
        "--require",
        action="store_true",
        help="fail (non-zero) instead of skipping when the adapter cannot be built",
    )
    args = parser.parse_args(argv)
    return build(out_dir=args.out, require=bool(args.require))


if __name__ == "__main__":
    raise SystemExit(main())
