"""Compile small real programs from the launcher's C, for tests that run them.

Release channels had never run for real (2026-10-15): the slot logic in
``runtime_resolve.c`` was pinned only by a Python mirror and by reading the C
as text, and the update helper's undo had only ever been read as batch text.
This module compiles, once per test session and only where MSVC and CMake are
installed:

* ``resolve_probe.exe`` -- ``runtime_resolve.c`` with a tiny ``main`` that
  resolves a runtime for a pretend launcher path and prints what it found, so
  the C itself answers the slot questions;
* ``fakeproc.exe`` -- a windowless stand-in for any process a test needs (a
  shared runtime, an installer, an app that hangs). It is driven by files
  beside it, named after it:

  ``<exe>.calls``   appended: its command line and ``QUILL_APP_ROOT``;
  ``<exe>.copy``    two UTF-8 lines, a source and a destination: copy the file
                    (how a fake installer "installs" a version);
  ``<exe>.sleep``   seconds to stay running (an app that hangs);
  ``<exe>.exit``    the exit code (default 0).

Copies of ``fakeproc.exe`` read their own sidecars, so one build serves every
role. Callers skip when :func:`build` returns ``None``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
LAUNCHER = REPO / "quill" / "native" / "launcher"

_PROBE_C = r"""
#include <stdio.h>
#include "runtime_resolve.h"

int main(int argc, char **argv) {
    QlRuntime rt;
    char url[1024];
    int rc, urc;
    if (argc < 2) return 9;
    rc = ql_resolve_runtime(argv[1], &rt);
    printf("rc=%d\n", rc);
    printf("python=%s\n", rt.python);
    printf("root=%s\n", rt.install_root);
    printf("data=%s\n", rt.data_dir);
    printf("slot=%s\n", rt.slot);
    urc = ql_runtime_url_for_slot(argc > 2 ? argv[2] : "", rt.slot, url, sizeof(url));
    printf("url_rc=%d\n", urc);
    printf("url=%s\n", url);
    return 0;
}
"""

_FAKEPROC_C = r"""
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>

static void sidecar(const wchar_t *self, const wchar_t *ext, wchar_t *out, size_t n) {
    _snwprintf_s(out, n, _TRUNCATE, L"%ls.%ls", self, ext);
}

static void put_utf8(FILE *f, const wchar_t *text) {
    char buf[8192];
    int n = WideCharToMultiByte(CP_UTF8, 0, text, -1, buf, (int)sizeof(buf), NULL, NULL);
    if (n > 1) fwrite(buf, 1, (size_t)(n - 1), f);
}

static int read_int(const wchar_t *path, int fallback) {
    FILE *f = NULL;
    int value = fallback;
    if (_wfopen_s(&f, path, L"rb") != 0 || !f) return fallback;
    if (fscanf_s(f, "%d", &value) != 1) value = fallback;
    fclose(f);
    return value;
}

static void trim(char *s) {
    size_t n = strlen(s);
    while (n && (s[n - 1] == '\n' || s[n - 1] == '\r')) s[--n] = '\0';
}

int WINAPI wWinMain(HINSTANCE inst, HINSTANCE prev, PWSTR cmd, int show) {
    wchar_t self[4096], path[4200], root[4096];
    FILE *f = NULL;
    DWORD n;
    (void)inst; (void)prev; (void)cmd; (void)show;
    if (!GetModuleFileNameW(NULL, self, 4096)) return 90;

    sidecar(self, L"calls", path, 4200);
    if (_wfopen_s(&f, path, L"ab") == 0 && f) {
        n = GetEnvironmentVariableW(L"QUILL_APP_ROOT", root, 4096);
        if (n == 0 || n >= 4096) root[0] = L'\0';
        fputs("cmd=", f); put_utf8(f, GetCommandLineW()); fputs("\n", f);
        fputs("root=", f); put_utf8(f, root); fputs("\n", f);
        fclose(f);
    }

    sidecar(self, L"copy", path, 4200);
    f = NULL;
    if (_wfopen_s(&f, path, L"rb") == 0 && f) {
        char src[4096] = {0}, dst[4096] = {0};
        wchar_t wsrc[4096], wdst[4096];
        if (fgets(src, (int)sizeof(src), f) && fgets(dst, (int)sizeof(dst), f)) {
            trim(src); trim(dst);
            if (MultiByteToWideChar(CP_UTF8, 0, src, -1, wsrc, 4096) &&
                MultiByteToWideChar(CP_UTF8, 0, dst, -1, wdst, 4096)) {
                CopyFileW(wsrc, wdst, FALSE);
            }
        }
        fclose(f);
    }

    sidecar(self, L"sleep", path, 4200);
    {
        int seconds = read_int(path, 0);
        if (seconds > 0) Sleep((DWORD)seconds * 1000u);
    }

    sidecar(self, L"exit", path, 4200);
    return read_int(path, 0);
}
"""

_CMAKE = """
cmake_minimum_required(VERSION 3.20)
project(ql_compiled_harness C)
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded")
add_compile_definitions(_CRT_SECURE_NO_WARNINGS NOMINMAX WIN32_LEAN_AND_MEAN)
add_executable(resolve_probe probe.c "{resolve}")
target_include_directories(resolve_probe PRIVATE "{inc}")
target_link_libraries(resolve_probe PRIVATE shlwapi)
add_executable(fakeproc WIN32 fakeproc.c)
if(MSVC)
    target_compile_options(resolve_probe PRIVATE /W4 /WX)
    target_compile_options(fakeproc PRIVATE /W4 /WX)
endif()
"""


def may_run_real_programs() -> bool:
    """True in CI, or when ``QUILL_RUN_NATIVE_PROGRAMS=1`` asks for it.

    Running the built launcher or a compiled Inno setup on somebody's own
    desktop -- with a screen reader running -- is not something a plain
    ``pytest`` should do unasked: a launcher that fails shows a message box, and
    a setup is still an installer even when it is told to install nothing. So
    those tests run where nobody is at the keyboard (GitHub Actions sets
    ``CI``) and on a developer's machine only on request.
    """
    return bool(os.environ.get("CI")) or os.environ.get("QUILL_RUN_NATIVE_PROGRAMS") == "1"


def toolchain() -> tuple[str, str] | None:
    """``(cmake, generator)`` when this machine can compile the launcher, else None."""
    if sys.platform != "win32":
        return None
    from scripts import build_native_launcher as bnl

    cmake = bnl.find_cmake()
    if cmake is None or bnl.find_msvc() is None:
        return None
    return cmake, bnl.msvc_generator()


def build(root: Path) -> dict[str, Path] | None:
    """Compile the probe and the fake process into *root*; None without a toolchain.

    Raises AssertionError when the toolchain is there and the C does not build:
    that is a real failure, not an environment to skip.
    """
    tools = toolchain()
    if tools is None:
        return None
    cmake, generator = tools
    root.mkdir(parents=True, exist_ok=True)
    (root / "probe.c").write_text(_PROBE_C, encoding="utf-8")
    (root / "fakeproc.c").write_text(_FAKEPROC_C, encoding="utf-8")
    (root / "CMakeLists.txt").write_text(
        _CMAKE.format(resolve=(LAUNCHER / "runtime_resolve.c").as_posix(), inc=LAUNCHER.as_posix()),
        encoding="utf-8",
    )
    out = root / "build"
    env = {k: v for k, v in os.environ.items() if not k.startswith("CMAKE_")}
    configure = [cmake, "-S", str(root), "-B", str(out), "-G", generator, "-A", "x64"]
    done = subprocess.run(configure, capture_output=True, text=True, env=env, timeout=600)
    if done.returncode != 0:
        return None  # no generator for this Visual Studio: the environment, not the C
    done = subprocess.run(
        [cmake, "--build", str(out), "--config", "Release"],
        capture_output=True,
        text=True,
        env=env,
        timeout=600,
    )
    assert done.returncode == 0, done.stdout[-4000:] + done.stderr[-4000:]
    built = {name: out / "Release" / f"{name}.exe" for name in ("resolve_probe", "fakeproc")}
    for exe in built.values():
        assert exe.is_file(), exe
    return built


def fake(source: Path, target: Path, **sidecars: object) -> Path:
    """Copy ``fakeproc.exe`` to *target* and write its sidecars (``copy``, ``sleep``, ``exit``).

    ``copy`` is a ``(source, destination)`` pair.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    for key, value in sidecars.items():
        side = Path(f"{target}.{key}")
        if key == "copy":
            src, dst = value  # type: ignore[misc]
            side.write_text(f"{src}\n{dst}\n", encoding="utf-8")
        else:
            side.write_text(str(value), encoding="utf-8")
    return target


def calls(exe: Path) -> list[str]:
    """The command lines *exe* (a fake) recorded, oldest first."""
    try:
        text = Path(f"{exe}.calls").read_text(encoding="utf-8")
    except OSError:
        return []
    return [line[4:] for line in text.splitlines() if line.startswith("cmd=")]


def roots(exe: Path) -> list[str]:
    """The ``QUILL_APP_ROOT`` each recorded call saw."""
    try:
        text = Path(f"{exe}.calls").read_text(encoding="utf-8")
    except OSError:
        return []
    return [line[5:] for line in text.splitlines() if line.startswith("root=")]
