"""Tests for the launcher's command-line quoting (``cmdline.c``).

``CreateProcessW`` takes one string, and the child splits it back into argv
itself -- by the MSVC C runtime's rules, which ``CommandLineToArgvW`` shares.
Until 2026-10-04 the native launcher joined the child's argv with bare spaces,
so a portable Quill Radio unpacked to ``C:\\portable\\Quill Radio`` told Python
its own path was two words, and Python tried to run the second as a script::

    C:\\portable\\Quill: can't open file
    'C:\\\\portable\\\\Quill Radio\\\\Radio\\\\pythonw.exe': [Errno 2] ...

The same join split any file opened from Explorer out of a folder with a space
in its name, which Quill Radio's Open With depends on.

As with ``test_launch_failure.py``, this module reimplements the C in Python
(``quote_arg`` below) and checks it against the documented parsing rules, and a
lexical check pins the C to the same shape. Then, where MSVC and CMake are
installed, it compiles the real ``cmdline.c`` into a small harness and asks
shell32's own ``CommandLineToArgvW`` to read back every command line it built.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[3]
_LAUNCHER_DIR = _REPO / "quill" / "native" / "launcher"
_CMDLINE_C = _LAUNCHER_DIR / "cmdline.c"
_CMDLINE_H = _LAUNCHER_DIR / "cmdline.h"
_LAUNCHER_C = _LAUNCHER_DIR / "launcher.c"

#: The path from the report that found the bug.
_PORTABLE_PYTHONW = "C:\\portable\\Quill Radio\\Radio\\pythonw.exe"

# ----------------------------------------------------------------------
# Python mirror of cmdline.c. MUST stay in sync.
# ----------------------------------------------------------------------

_NEEDS_QUOTES = frozenset(' \t\n\v"')


def quote_arg(arg: str) -> str:
    """One argument, quoted so the CRT and CommandLineToArgvW read back ``arg``."""
    if arg and not any(ch in _NEEDS_QUOTES for ch in arg):
        return arg
    out = ['"']
    backslashes = 0
    for ch in arg:
        if ch == "\\":
            backslashes += 1
            continue
        if ch == '"':
            out.append("\\" * (backslashes * 2 + 1))
            out.append('"')
        else:
            out.append("\\" * backslashes)
            out.append(ch)
        backslashes = 0
    out.append("\\" * (backslashes * 2))
    out.append('"')
    return "".join(out)


def build_command_line(argv: list[str]) -> str:
    return " ".join(quote_arg(a) for a in argv)


def max_len(argv: list[str]) -> int:
    """cmdline.c's buffer: QL_QUOTED_ARG_MAX(len) per argument, plus the NUL."""
    return sum(2 * len(a) + 3 for a in argv) + 1


# ----------------------------------------------------------------------
# The documented parser ("Parsing C++ command-line arguments"; the
# CommandLineToArgvW remarks). argv[0] is special: it is a program name,
# read up to the next quote (when it starts with one) or the next
# whitespace, with no backslash processing at all.
# ----------------------------------------------------------------------


def parse_command_line(line: str) -> list[str]:
    args: list[str] = []
    i, n = 0, len(line)
    # argv[0]
    if i < n and line[i] == '"':
        end = line.find('"', i + 1)
        end = n if end < 0 else end
        args.append(line[i + 1 : end])
        i = end + 1
    else:
        start = i
        while i < n and line[i] not in " \t":
            i += 1
        args.append(line[start:i])
    # the rest
    while True:
        while i < n and line[i] in " \t":
            i += 1
        if i >= n:
            return args
        current: list[str] = []
        in_quotes = False
        while i < n:
            ch = line[i]
            if ch == "\\":
                run = 0
                while i < n and line[i] == "\\":
                    run += 1
                    i += 1
                if i < n and line[i] == '"':
                    current.append("\\" * (run // 2))
                    if run % 2:
                        current.append('"')
                        i += 1
                    # an even run leaves the quote to be read as a delimiter
                else:
                    current.append("\\" * run)
                continue
            if ch == '"':
                if in_quotes and i + 1 < n and line[i + 1] == '"':
                    current.append('"')  # "" inside quotes is a literal quote
                    i += 2
                    continue
                in_quotes = not in_quotes
                i += 1
                continue
            if ch in " \t" and not in_quotes:
                break
            current.append(ch)
            i += 1
        args.append("".join(current))


#: Arguments the old space join broke, and the cases quoting itself gets wrong
#: most often (a trailing backslash eating the closing quote).
_TRICKY = [
    "plain",
    "with space",
    "",
    'say "hi"',
    '"',
    'a\\"b',
    'a\\\\"b',
    "C:\\dir\\",
    "C:\\dir with space\\",
    "trailing\\\\",
    "\\\\server\\share\\x",
    "tab\there",
    "new\nline",
    "vt\vhere",
    "C:\\My Music\\song.mp3",
    "M\u00fasica \u65e5\u672c \u2713 \U0001f3b5",
    "-m",
    "quill.apps.radio",
    "--flag=a b",
    "C:\\a\\b",
]


@pytest.mark.parametrize("arg", _TRICKY)
def test_each_argument_round_trips_through_the_documented_rules(arg: str) -> None:
    argv = [_PORTABLE_PYTHONW, arg]
    assert parse_command_line(build_command_line(argv)) == argv


def test_the_reported_portable_path_survives_as_argv0() -> None:
    argv = [_PORTABLE_PYTHONW, "-m", "quill.apps.radio", "C:\\My Music\\song.mp3"]
    line = build_command_line(argv)
    assert line.startswith('"C:\\portable\\Quill Radio\\Radio\\pythonw.exe" ')
    assert parse_command_line(line) == argv


def test_the_old_space_join_is_what_broke() -> None:
    """The bug, stated: Python saw "C:\\portable\\Quill" and a script path."""
    argv = [_PORTABLE_PYTHONW, "-m", "quill.apps.radio"]
    parsed = parse_command_line(" ".join(argv))
    assert parsed[:2] == ["C:\\portable\\Quill", "Radio\\Radio\\pythonw.exe"]


def test_all_tricky_arguments_together() -> None:
    argv = [_PORTABLE_PYTHONW, *_TRICKY]
    assert parse_command_line(build_command_line(argv)) == argv


def test_simple_arguments_are_left_alone() -> None:
    assert quote_arg("plain") == "plain"
    assert quote_arg("C:\\a\\b") == "C:\\a\\b"
    assert quote_arg("") == '""'
    assert quote_arg("C:\\dir\\") == "C:\\dir\\"  # no quotes, so no doubling
    assert quote_arg("C:\\dir with space\\") == '"C:\\dir with space\\\\"'
    assert quote_arg('a\\"b') == '"a\\\\\\"b"'


@pytest.mark.parametrize("arg", ['"' * 50, "\\" * 50 + " ", "x" * 50, ""])
def test_quoted_length_never_exceeds_the_buffer(arg: str) -> None:
    argv = [arg, arg]
    assert len(build_command_line(argv)) + 1 <= max_len(argv)


@pytest.mark.skipif(sys.platform != "win32", reason="shell32 is Windows-only")
def test_mirror_agrees_with_shell32() -> None:
    argv = [_PORTABLE_PYTHONW, *_TRICKY]
    assert _shell32_split(build_command_line(argv)) == argv


# ----------------------------------------------------------------------
# The C source has the same shape, and the launcher uses it
# ----------------------------------------------------------------------


def test_c_source_exists_and_is_built() -> None:
    assert _CMDLINE_C.is_file() and _CMDLINE_H.is_file()
    cmake = (_LAUNCHER_DIR / "CMakeLists.txt").read_text(encoding="utf-8")
    assert "cmdline.c" in cmake
    launcher = _LAUNCHER_C.read_text(encoding="utf-8")
    assert '#include "cmdline.h"' in launcher
    assert "ql_build_command_line(" in launcher


def test_launcher_no_longer_joins_with_bare_spaces() -> None:
    launcher = _LAUNCHER_C.read_text(encoding="utf-8")
    assert "? L'\\0' : L' '" not in launcher


@pytest.mark.parametrize(
    "token",
    [
        "L' '",
        "L'\\t'",
        "L'\\n'",
        "L'\\v'",
        "L'\"'",
        "backslashes * 2 + 1",
        "backslashes * 2",
        "2 * (len) + 3",
    ],
)
def test_c_source_carries_the_same_rules(token: str) -> None:
    source = _CMDLINE_H.read_text(encoding="utf-8") + _CMDLINE_C.read_text(encoding="utf-8")
    assert token in source, f"cmdline.c/.h lost {token!r}; the Python mirror still has it"


# ----------------------------------------------------------------------
# The real C, compiled, read back by shell32
# ----------------------------------------------------------------------


def _shell32_split(line: str) -> list[str]:
    import ctypes
    from ctypes import wintypes

    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    shell32.CommandLineToArgvW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_int)]
    shell32.CommandLineToArgvW.restype = ctypes.POINTER(wintypes.LPWSTR)
    kernel32.LocalFree.argtypes = [wintypes.HLOCAL]
    kernel32.LocalFree.restype = wintypes.HLOCAL
    count = ctypes.c_int(0)
    parsed = shell32.CommandLineToArgvW(line, ctypes.byref(count))
    assert parsed, f"CommandLineToArgvW failed: {ctypes.get_last_error()}"
    try:
        return [parsed[i] for i in range(count.value)]
    finally:
        kernel32.LocalFree(ctypes.cast(parsed, wintypes.HLOCAL))


_HARNESS_C = r"""
/* Reads NUL-separated UTF-16LE arguments from argv[1], writes the command
 * line ql_build_command_line makes of them, as UTF-16LE, to argv[2]. */
#include "cmdline.h"
#include <stdio.h>
#include <stdlib.h>
#include <wchar.h>

int wmain(int argc, wchar_t **argv) {
    if (argc != 3) return 2;
    FILE *in = _wfopen(argv[1], L"rb");
    if (!in) return 3;
    fseek(in, 0, SEEK_END);
    long bytes = ftell(in);
    fseek(in, 0, SEEK_SET);
    size_t chars = (size_t)bytes / sizeof(wchar_t);
    wchar_t *buf = (wchar_t *)calloc(chars + 1, sizeof(wchar_t));
    if (!buf || fread(buf, sizeof(wchar_t), chars, in) != chars) return 4;
    fclose(in);
    int count = 0;
    for (size_t i = 0; i < chars; ++i) if (buf[i] == 0) ++count;
    const wchar_t **args = (const wchar_t **)calloc((size_t)count + 1, sizeof(wchar_t *));
    if (!args) return 5;
    const wchar_t *p = buf;
    for (int i = 0; i < count; ++i) { args[i] = p; p += wcslen(p) + 1; }
    wchar_t *line = ql_build_command_line(args, count);
    if (!line) return 6;
    FILE *out = _wfopen(argv[2], L"wb");
    if (!out) return 7;
    fwrite(line, sizeof(wchar_t), wcslen(line), out);
    fclose(out);
    free(line);
    free(args);
    free(buf);
    return 0;
}
"""

_HARNESS_CMAKE = """
cmake_minimum_required(VERSION 3.20)
project(ql_cmdline_harness C)
add_executable(harness harness.c "{src}")
target_include_directories(harness PRIVATE "{inc}")
if(MSVC)
    target_compile_options(harness PRIVATE /W4 /WX)
endif()
"""


@pytest.fixture(scope="module")
def harness(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if sys.platform != "win32":
        pytest.skip("the harness is a Windows wmain program")
    from scripts import build_native_launcher as bnl

    cmake = bnl.find_cmake()
    if cmake is None or bnl.find_msvc() is None:
        pytest.skip("MSVC and CMake are not installed")
    root = tmp_path_factory.mktemp("cmdline harness")
    (root / "harness.c").write_text(_HARNESS_C, encoding="utf-8")
    (root / "CMakeLists.txt").write_text(
        _HARNESS_CMAKE.format(src=_CMDLINE_C.as_posix(), inc=_LAUNCHER_DIR.as_posix()),
        encoding="utf-8",
    )
    build = root / "build"
    env = {k: v for k, v in os.environ.items() if not k.startswith("CMAKE_")}
    generator = ["-G", "Visual Studio 17 2022", "-A", "x64"]
    configure = [cmake, "-S", str(root), "-B", str(build), *generator]
    done = subprocess.run(configure, capture_output=True, text=True, env=env, timeout=600)
    if done.returncode != 0:
        # A machine without the Visual Studio 2022 generator (a CI image that
        # ships a newer Visual Studio) cannot configure; that is the
        # environment, not the quoting code. Building, once configured, must work.
        pytest.skip("CMake cannot configure a Visual Studio 2022 build here")
    build_cmd = [cmake, "--build", str(build), "--config", "Release"]
    done = subprocess.run(build_cmd, capture_output=True, text=True, env=env, timeout=600)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    exe = build / "Release" / "harness.exe"
    assert exe.is_file()
    return exe


def _run_harness(exe: Path, argv: list[str], work: Path) -> str:
    src, dst = work / "args.bin", work / "line.bin"
    src.write_bytes("".join(a + "\0" for a in argv).encode("utf-16-le"))
    done = subprocess.run([str(exe), str(src), str(dst)], capture_output=True, timeout=60)
    assert done.returncode == 0, done
    return dst.read_bytes().decode("utf-16-le")


_COMPILED_CASES = [
    [_PORTABLE_PYTHONW, "-m", "quill.apps.radio"],
    [_PORTABLE_PYTHONW, "-m", "quill.apps.radio", "C:\\My Music\\song.mp3"],
    [_PORTABLE_PYTHONW, *_TRICKY],
    *([_PORTABLE_PYTHONW, arg] for arg in _TRICKY),
    ["C:\\NoSpace\\pythonw.exe", "", "", "x"],
    ["C:\\NoSpace\\pythonw.exe", '"' * 40, "\\" * 40, "\\" * 7 + '"' + "\\" * 3],
]


def test_compiled_cmdline_round_trips_through_shell32(harness: Path, tmp_path: Path) -> None:
    for argv in _COMPILED_CASES:
        line = _run_harness(harness, argv, tmp_path)
        assert _shell32_split(line) == argv, line
        assert line == build_command_line(argv), "the C and its Python mirror disagree"
        assert len(line) + 1 <= max_len(argv)


@pytest.mark.skipif(sys.platform != "win32", reason="a raw command line is Windows-only")
def test_python_itself_reads_the_quoted_line_back(tmp_path: Path) -> None:
    """The real consumer: the C runtime inside python.exe fills sys.argv."""
    probe = tmp_path / "dir with space"
    probe.mkdir()
    script = probe / "echo argv.py"
    script.write_text("import sys, json\nprint(json.dumps(sys.argv[1:]))\n", encoding="utf-8")
    args = ["C:\\My Music\\song.mp3", "", 'a "q"', "C:\\dir with space\\", "\\\\x\\\\"]
    line = build_command_line([sys.executable, str(script), *args])
    done = subprocess.run(line, capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout) == args
