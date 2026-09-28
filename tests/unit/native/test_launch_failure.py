"""Tests for the launcher's "it did not start" report.

The real code is C, in ``quill/native/launcher/launch_report.c``: the launcher
redirects the interpreter's stderr to a launch log and, when the child exits
non-zero, turns the exit code and the log's last line into one sentence a
person can act on. Before 2026-09-28 the launcher threw the exit code away,
so a portable copy whose Python died at import time did nothing at all --
no window, no dialog, no file -- and the first report of it was "no matter
what she does it just doesn't return anything".

As with ``test_runtime_resolver.py``, this module reimplements the decision
logic in Python so the *contract* is exercised without a C toolchain, and a
lexical check at the bottom pins every constant and every key phrase to the C
source, so the two cannot drift silently. If you change one, change the other.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_LAUNCHER_DIR = Path(__file__).resolve().parents[3] / "quill" / "native" / "launcher"
_REPORT_C = _LAUNCHER_DIR / "launch_report.c"
_REPORT_H = _LAUNCHER_DIR / "launch_report.h"
_LAUNCHER_C = _LAUNCHER_DIR / "launcher.c"

# ----------------------------------------------------------------------
# Python mirror of launch_report.c. MUST stay in sync.
# ----------------------------------------------------------------------

#: NTSTATUS values a process exits with when Windows, not Python, killed it.
#: None of these leave a line in the log, which is why they need words.
STATUS_ACCESS_VIOLATION = 0xC0000005
STATUS_ACCESS_DENIED = 0xC0000022
STATUS_INVALID_IMAGE_FORMAT = 0xC000007B
STATUS_DLL_NOT_FOUND = 0xC0000135
STATUS_DLL_INIT_FAILED = 0xC0000142
STATUS_HEAP_CORRUPTION = 0xC0000374
STATUS_STACK_BUFFER_OVERRUN = 0xC0000409

#: A launch that ran at least this long before exiting non-zero "stopped
#: unexpectedly"; a shorter one "did not start". Milliseconds.
STARTED_AFTER_MS = 60_000

#: The longest tail line the dialog repeats.
LAST_LINE_MAX = 300

#: Folder names the archive tools use when a file is opened from *inside* a
#: zip, so only that one file exists on disk: Explorer's zip folder view
#: (``Temp1_<name>.zip``), 7-Zip (``7zO<hex>``) and WinRAR (``Rar$EXa...``).
_ARCHIVE_PREVIEW_RE = re.compile(r"^(Temp\d+_.*\.zip|7zO[0-9A-Za-z]+|Rar\$.*)$", re.IGNORECASE)


def looks_like_archive_preview(self_path: str) -> bool:
    """True when the launcher is running from an archive tool's scratch folder."""
    for part in re.split(r"[\\/]", self_path)[:-1]:
        if _ARCHIVE_PREVIEW_RE.match(part):
            return True
    return False


def launch_log_path(data_dir: str, product_name: str, appdata: str | None, temp: str | None) -> str:
    """Where the child's stderr lands.

    A portable copy (``<data_dir>\\data`` exists) logs beside its own settings,
    in ``data\\logs\\launch.log``; an installed copy logs beside ``quill.log``
    in ``%APPDATA%\\Quill\\logs``; with no APPDATA at all, ``%TEMP%``. The
    caller creates the folder; this only names the file.
    """
    if data_dir and Path(data_dir, "data").is_dir():
        return str(Path(data_dir, "data", "logs", "launch.log"))
    if appdata:
        return str(Path(appdata, "Quill", "logs", f"{product_name}-launch.log"))
    if temp:
        return str(Path(temp, f"{product_name}-launch.log"))
    return ""


def last_message_line(text: str, header: str) -> str:
    """The last non-blank line of the log that is not the launcher's own header."""
    last = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line == header.strip():
            continue
        last = line
    return last[:LAST_LINE_MAX]


def describe_exit(code: int, last_line: str, display_name: str) -> str:
    """One paragraph saying why ``display_name`` exited with ``code``."""
    if code == STATUS_DLL_NOT_FOUND:
        return (
            "A file it needs is missing (Windows reported that a DLL could not be "
            "found). If this is a portable copy, extract the whole zip again, keeping "
            "every file together, and check whether antivirus quarantined a file from "
            "its folder."
        )
    if code == STATUS_DLL_INIT_FAILED:
        return (
            "A file it needs could not be started (a DLL failed to initialise). "
            "Sign out of Windows and back in, or restart the computer, then try again."
        )
    if code == STATUS_INVALID_IMAGE_FORMAT:
        return (
            "A file in its folder is damaged, or is the wrong kind for this computer "
            f"({display_name} needs 64-bit Windows). Download and extract it again."
        )
    if code == STATUS_ACCESS_DENIED:
        return (
            "Windows refused to run its files. Antivirus, application control or a "
            "folder permission is blocking it. Try extracting it to a folder of your "
            "own, such as Documents, and check the antivirus quarantine."
        )
    if code in (STATUS_ACCESS_VIOLATION, STATUS_HEAP_CORRUPTION, STATUS_STACK_BUFFER_OVERRUN):
        return "It crashed inside a component (a memory fault), not in its own code."
    if last_line:
        hint = ""
        if "No module named" in last_line:
            hint = (
                " Part of the program is missing: this copy is incomplete, or its files "
                "are mixed with another version's. Extract the whole zip again into an "
                "empty folder."
            )
        elif "DLL load failed" in last_line:
            hint = (
                " A component could not be loaded. Check the antivirus quarantine, and "
                "extract the whole zip again, keeping every file together."
            )
        elif "PermissionError" in last_line or "Permission denied" in last_line:
            hint = (
                " It is not allowed to write where it is. Move the folder somewhere "
                "you own, such as Documents, or run it from a different drive."
            )
        return f"Python reported: {last_line}{hint}"
    return f"It exited with code {code} and left no message."


def headline(display_name: str, ran_for_ms: int) -> str:
    if ran_for_ms >= STARTED_AFTER_MS:
        return f"{display_name} stopped unexpectedly."
    return f"{display_name} did not start."


# ----------------------------------------------------------------------
# Archive preview detection
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        r"C:\Users\ann\AppData\Local\Temp\Temp1_Quill-Radio-Portable-3.0.4.zip\QuillRadio.exe",
        r"C:\Users\ann\AppData\Local\Temp\Temp1_Quill-Radio-Portable-3.0.4.zip\QuillRadio\QuillRadio.exe",
        r"C:\Users\ann\AppData\Local\Temp\7zO4C1A2B3\QuillRadio.exe",
        r"C:\Users\ann\AppData\Local\Temp\Rar$EXa12345.6789\QuillRadio\QuillRadio.exe",
        r"c:\users\ann\appdata\local\temp\temp12_download.ZIP\QuillRadio.exe",
    ],
)
def test_archive_preview_paths_are_recognised(path: str) -> None:
    assert looks_like_archive_preview(path)


@pytest.mark.parametrize(
    "path",
    [
        r"D:\QuillRadio\QuillRadio.exe",
        r"C:\Temp\QuillRadio\QuillRadio.exe",
        r"C:\Users\ann\Downloads\Quill-Radio-Portable-3.0.4\QuillRadio\QuillRadio.exe",
        r"C:\Users\ann\Downloads\Temp1_notes.txt\QuillRadio.exe",
        # The exe's own name never counts, only the folders above it.
        r"D:\apps\Temp1_thing.zip.exe",
    ],
)
def test_ordinary_paths_are_not_previews(path: str) -> None:
    assert not looks_like_archive_preview(path)


# ----------------------------------------------------------------------
# Where the log goes
# ----------------------------------------------------------------------


def test_portable_copy_logs_beside_its_data(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    got = launch_log_path(str(tmp_path), "quill-radio", r"C:\Users\ann\AppData\Roaming", r"C:\T")
    assert got == str(tmp_path / "data" / "logs" / "launch.log")


def test_installed_copy_logs_beside_quill_log(tmp_path: Path) -> None:
    got = launch_log_path(str(tmp_path), "quill-radio", r"C:\Users\ann\AppData\Roaming", r"C:\T")
    assert got == r"C:\Users\ann\AppData\Roaming\Quill\logs\quill-radio-launch.log"


def test_no_appdata_falls_back_to_temp(tmp_path: Path) -> None:
    got = launch_log_path(str(tmp_path), "quill-radio", None, r"C:\T")
    assert got == r"C:\T\quill-radio-launch.log"
    assert launch_log_path(str(tmp_path), "quill-radio", None, None) == ""


# ----------------------------------------------------------------------
# Reading the tail
# ----------------------------------------------------------------------

_HEADER = "Quill Radio 3.0.4 launcher: C:\\R\\pythonw.exe -m quill.apps.radio"


def test_last_line_is_the_tracebacks_final_line() -> None:
    text = (
        _HEADER + "\n"
        "Traceback (most recent call last):\n"
        '  File "<frozen runpy>", line 198, in _run_module_as_main\n'
        "ModuleNotFoundError: No module named 'quill.apps.radio'\n"
        "\n"
    )
    expected = "ModuleNotFoundError: No module named 'quill.apps.radio'"
    assert last_message_line(text, _HEADER) == expected


def test_header_alone_is_no_message() -> None:
    assert last_message_line(_HEADER + "\n\n   \n", _HEADER) == ""
    assert last_message_line("", _HEADER) == ""


def test_last_line_is_bounded() -> None:
    assert len(last_message_line("x" * 5000, _HEADER)) == LAST_LINE_MAX


# ----------------------------------------------------------------------
# The sentence
# ----------------------------------------------------------------------


def test_windows_status_codes_get_words_not_numbers() -> None:
    for code in (
        STATUS_DLL_NOT_FOUND,
        STATUS_DLL_INIT_FAILED,
        STATUS_INVALID_IMAGE_FORMAT,
        STATUS_ACCESS_DENIED,
        STATUS_ACCESS_VIOLATION,
        STATUS_HEAP_CORRUPTION,
        STATUS_STACK_BUFFER_OVERRUN,
    ):
        text = describe_exit(code, "", "Quill Radio")
        assert str(code) not in text, code
        assert "exited with code" not in text, code


def test_missing_dll_names_the_two_likely_causes() -> None:
    text = describe_exit(STATUS_DLL_NOT_FOUND, "", "Quill Radio")
    assert "extract the whole zip" in text
    assert "antivirus" in text


def test_wrong_image_names_the_product_and_64_bit() -> None:
    text = describe_exit(STATUS_INVALID_IMAGE_FORMAT, "", "Quill Converter")
    assert "Quill Converter needs 64-bit Windows" in text


def test_python_traceback_is_quoted_with_a_hint() -> None:
    line = "ModuleNotFoundError: No module named 'quill.apps.radio'"
    text = describe_exit(1, line, "Quill Radio")
    assert text.startswith("Python reported: " + line)
    assert "incomplete" in text

    text = describe_exit(1, "ImportError: DLL load failed while importing _core: x", "Quill Radio")
    assert "quarantine" in text

    text = describe_exit(1, "PermissionError: [Errno 13] Permission denied: 'x'", "Quill Radio")
    assert "Documents" in text


def test_unknown_traceback_is_quoted_verbatim() -> None:
    line = "RuntimeError: something else"
    assert describe_exit(1, line, "Quill Radio") == "Python reported: " + line


def test_silent_exit_says_the_code() -> None:
    assert describe_exit(7, "", "Quill Radio") == "It exited with code 7 and left no message."


def test_headline_distinguishes_never_started_from_died_later() -> None:
    assert headline("Quill Radio", 0) == "Quill Radio did not start."
    assert headline("Quill Radio", STARTED_AFTER_MS - 1) == "Quill Radio did not start."
    assert headline("Quill Radio", STARTED_AFTER_MS) == "Quill Radio stopped unexpectedly."


# ----------------------------------------------------------------------
# The C source carries the same constants and the same words
# ----------------------------------------------------------------------


def test_c_source_exists_and_is_built() -> None:
    assert _REPORT_C.is_file()
    cmake = (_LAUNCHER_DIR / "CMakeLists.txt").read_text(encoding="utf-8")
    assert "launch_report.c" in cmake
    launcher = _LAUNCHER_C.read_text(encoding="utf-8")
    assert '#include "launch_report.h"' in launcher


@pytest.mark.parametrize(
    "token",
    [
        "0xC0000005",
        "0xC0000022",
        "0xC000007B",
        "0xC0000135",
        "0xC0000142",
        "0xC0000374",
        "0xC0000409",
        str(STARTED_AFTER_MS),
        str(LAST_LINE_MAX),
        "Temp",
        "7zO",
        "Rar$",
        "launch.log",
        "-launch.log",
        "did not start.",
        "stopped unexpectedly.",
        "Python reported: ",
        "No module named",
        "DLL load failed",
        "PermissionError",
        "Permission denied",
        "and left no message.",
        "needs 64-bit Windows",
        "extract the whole zip",
        "support@community-access.org",
        "Extract All",
    ],
)
def test_c_source_carries_every_constant_and_phrase(token: str) -> None:
    source = _REPORT_H.read_text(encoding="utf-8") + _REPORT_C.read_text(encoding="utf-8")
    assert token in source, f"launch_report.c/.h lost {token!r}; the Python mirror still has it"
