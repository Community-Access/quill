"""Relaunch command construction (build_relaunch_command).

Under ``python -m quill`` (dev tree and the installed quill.exe launcher,
which is a stamped pythonw.exe running ``-m quill``), ``sys.argv[0]`` is the
full path to ``quill/__main__.py``. Re-running that file as a script puts the
package directory itself at ``sys.path[0]``, where ``quill/platform`` shadows
the stdlib ``platform`` module and the relaunched process crashes in
``_build_menu``. The relaunch command must always use ``-m quill``.
"""

from quill.core.relaunch import build_relaunch_command


def test_module_run_relaunches_via_dash_m() -> None:
    command = build_relaunch_command(
        "C:/py/python.exe",
        ["S:/QUILL/quill/__main__.py", "--new-window", "doc.txt"],
        frozen=False,
    )
    assert command == ["C:/py/python.exe", "-m", "quill", "--new-window", "doc.txt"]


def test_argv0_is_never_reused_as_an_argument() -> None:
    # The old [sys.executable, *sys.argv] form passed argv[0] (a script path)
    # back as the first argument; nothing that looks like a path may leak in.
    command = build_relaunch_command("python", ["quill/__main__.py"], frozen=False)
    assert command == ["python", "-m", "quill"]


def test_frozen_build_reuses_executable_without_argv0() -> None:
    command = build_relaunch_command(
        "C:/app/quill.exe", ["C:/app/quill.exe", "doc.txt"], frozen=True
    )
    assert command == ["C:/app/quill.exe", "doc.txt"]


def test_frozen_defaults_to_sys_flag() -> None:
    # No sys.frozen in a plain interpreter -> module invocation.
    command = build_relaunch_command("python", ["whatever/__main__.py", "-x"])
    assert command == ["python", "-m", "quill", "-x"]
