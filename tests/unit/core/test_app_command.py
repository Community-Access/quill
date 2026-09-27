"""The command line that starts this app again (quill.core.app_command).

Found 2026-09-27: every "start with Windows" entry and scheduled task written
by a shared-runtime build named ``QuillVilleRuntime.exe`` alone, which is not an
app. These pin the three answers -- launcher, interpreter plus ``-m``, genuine
app exe -- and the rule for when a stored entry may be replaced.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.app_command import (
    app_argv,
    app_command,
    is_generic_interpreter,
    should_replace,
    split_command,
    to_command_line,
)

RUNTIME = r"C:\Users\x\AppData\Local\QuillVille\Runtime\3.13\QuillVilleRuntime.exe"
LAUNCHER_DIR = r"C:\Program Files\Quill Radio"
LAUNCHER = LAUNCHER_DIR + r"\QuillRadio.exe"


def _exists(*present: str):
    return lambda path: str(path) in present


def test_prefers_the_native_launcher_when_it_started_us() -> None:
    argv = app_argv(
        "quill.apps.radio",
        "QuillRadio.exe",
        args=("--tray",),
        executable=RUNTIME,
        environ={"QUILL_LAUNCHER_DIR": LAUNCHER_DIR},
        exists=_exists(LAUNCHER),
    )
    assert argv == [LAUNCHER, "--tray"]


def test_a_launcher_dir_without_this_app_s_launcher_is_ignored() -> None:
    # A sibling app started us and its QUILL_LAUNCHER_DIR leaked in.
    argv = app_argv(
        "quill.apps.weather",
        "QuillWeather.exe",
        executable=RUNTIME,
        environ={"QUILL_LAUNCHER_DIR": LAUNCHER_DIR},
        exists=_exists(LAUNCHER),
    )
    assert argv == [RUNTIME, "-m", "quill.apps.weather"]


@pytest.mark.parametrize(
    "exe", [RUNTIME, r"C:\py\python.exe", r"D:\stick\pythonw.exe", "/usr/bin/python"]
)
def test_an_interpreter_gets_dash_m(exe: str) -> None:
    argv = app_argv("quill.apps.radio", "QuillRadio.exe", executable=exe, environ={})
    assert argv == [exe, "-m", "quill.apps.radio"]


@pytest.mark.parametrize("exe", [r"C:\Quill\quill.exe", r"C:\Old\QuillRadio.exe"])
def test_a_genuine_app_exe_runs_bare(exe: str) -> None:
    assert app_argv("quill", executable=exe, environ={}, args=("--x",)) == [exe, "--x"]


def test_no_launcher_name_never_looks_for_one() -> None:
    argv = app_argv(
        "quill",
        None,
        executable=r"C:\py\python.exe",
        environ={"QUILL_LAUNCHER_DIR": LAUNCHER_DIR},
        exists=lambda _p: True,
    )
    assert argv == [r"C:\py\python.exe", "-m", "quill"]


def test_command_line_quotes_the_exe_and_only_args_that_need_it() -> None:
    assert to_command_line([LAUNCHER]) == f'"{LAUNCHER}"'
    assert (
        to_command_line([RUNTIME, "-m", "quill.apps.inkwell", "--tray"])
        == f'"{RUNTIME}" -m quill.apps.inkwell --tray'
    )
    assert to_command_line(["a.exe", "two words"]) == '"a.exe" "two words"'
    assert to_command_line([]) == ""


def test_app_command_joins_app_argv() -> None:
    assert (
        app_command(
            "quill.apps.weather",
            "QuillWeather.exe",
            args=("--check-once",),
            executable=RUNTIME,
            environ={},
        )
        == f'"{RUNTIME}" -m quill.apps.weather --check-once'
    )


def test_split_command_round_trips() -> None:
    assert split_command(f'"{RUNTIME}" -m quill.apps.radio') == (RUNTIME, "-m quill.apps.radio")
    assert split_command(f'"{LAUNCHER}"') == (LAUNCHER, "")
    assert split_command(r"C:\x\a.exe --tray") == (r"C:\x\a.exe", "--tray")
    assert split_command("") == ("", "")


def test_interpreter_detection() -> None:
    assert is_generic_interpreter(f'"{RUNTIME}"')
    assert is_generic_interpreter("pythonw.exe")
    assert not is_generic_interpreter("quill.exe")
    assert not is_generic_interpreter("")


def test_the_broken_entry_is_replaced_by_the_launcher() -> None:
    assert should_replace(f'"{RUNTIME}"', f'"{LAUNCHER}"')


def test_the_broken_entry_is_replaced_even_without_a_launcher() -> None:
    # Started from a taskbar pin: the runtime form is all we know, and it is
    # still better than the runtime alone.
    assert should_replace(f'"{RUNTIME}" --tray', f'"{RUNTIME}" -m quill.apps.inkwell --tray')


def test_a_working_launcher_entry_is_never_downgraded() -> None:
    assert not should_replace(f'"{LAUNCHER}"', f'"{RUNTIME}" -m quill.apps.radio')


def test_an_identical_or_empty_entry_is_left_alone() -> None:
    assert not should_replace(f'"{LAUNCHER}"', f'"{LAUNCHER}"')
    assert not should_replace("", f'"{LAUNCHER}"')
    assert not should_replace(f'"{LAUNCHER}"', "")


def test_the_runtime_form_is_upgraded_to_the_launcher() -> None:
    assert should_replace(f'"{RUNTIME}" -m quill.apps.radio', f'"{LAUNCHER}"')


def test_default_exists_is_a_real_file_check(tmp_path: Path) -> None:
    (tmp_path / "QuillRadio.exe").write_bytes(b"MZ")
    argv = app_argv(
        "quill.apps.radio",
        "QuillRadio.exe",
        executable=RUNTIME,
        environ={"QUILL_LAUNCHER_DIR": str(tmp_path)},
    )
    assert argv == [str(tmp_path / "QuillRadio.exe")]
