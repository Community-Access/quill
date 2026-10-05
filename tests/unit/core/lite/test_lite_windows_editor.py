"""QUILL Lite as a Windows text editor: what it registers, and how Notepad is replaced.

Nothing here touches the real registry. The writer records what it was asked to
write and the reader answers from a dict, which is the whole point of the
protocols in :mod:`quill.core.lite.windows_editor`.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.lite import windows_editor as editor

LAUNCHER = r"C:\Program Files\QuillLite\QuillLite.exe"
ICON = r"C:\Program Files\QuillLite\quill-lite.ico"
WIN11_SUBKEYS = {
    "0": r"C:\Windows\System32\notepad.exe",
    "1": r"C:\Windows\SysWOW64\notepad.exe",
    "2": r"C:\Windows\notepad.exe",
}


class FakeWriter:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str], tuple[str, str]] = {}

    def set_value(self, path: str, name: str, data: str, kind: str) -> None:
        self.values[(path, name)] = (data, kind)


class FakeReader:
    """HKLM as a dict of ``{key: {value name: data}}``."""

    def __init__(self, keys: dict[str, dict[str, object]] | None = None) -> None:
        self.keys = keys or {}

    def value(self, path: str, name: str) -> object | None:
        return self.keys.get(path, {}).get(name)

    def subkeys(self, path: str) -> list[str]:
        prefix = path + "\\"
        return sorted({
            key[len(prefix) :].split("\\")[0] for key in self.keys if key.startswith(prefix)
        })


def _windows_11(**debuggers: str) -> FakeReader:
    """The notepad.exe key as Windows 11 ships it, plus any Debugger values."""
    keys: dict[str, dict[str, object]] = {editor.IFEO_KEY: {"UseFilter": 1}}
    for name, target in WIN11_SUBKEYS.items():
        keys[rf"{editor.IFEO_KEY}\{name}"] = {
            "FilterFullPath": target,
            "AppExecutionAliasRedirect": 1,
        }
    for name, value in debuggers.items():
        key = editor.IFEO_KEY if name == "parent" else rf"{editor.IFEO_KEY}\{name[1:]}"
        keys[key]["Debugger"] = value
    return FakeReader(keys)


# -- registering ------------------------------------------------------------


def test_the_open_command_quotes_the_launcher_and_the_file() -> None:
    assert editor.open_command([LAUNCHER]) == f'"{LAUNCHER}" "%1"'


def test_registration_writes_a_progid_open_with_and_default_apps_entries() -> None:
    writer = FakeWriter()
    count = editor.write_plan(editor.registration_plan([LAUNCHER], ICON), writer)
    values = writer.values
    assert count == len(values)
    command = (f'"{LAUNCHER}" "%1"', "sz")
    progid = r"Software\Classes\QuillLite.Document"
    assert values[(rf"{progid}\shell\open\command", "")] == command
    assert values[(rf"{progid}\DefaultIcon", "")] == (ICON, "sz")
    app = r"Software\Classes\Applications\QuillLite.exe"
    assert values[(app, "FriendlyAppName")] == ("QUILL Lite", "sz")
    assert values[(rf"{app}\shell\open\command", "")] == command
    for ext in editor.EXTENSIONS:
        assert values[(rf"Software\Classes\{ext}\OpenWithProgids", "QuillLite.Document")] == (
            "",
            "sz",
        )
        assert (rf"{app}\SupportedTypes", ext) in values
        assert values[(rf"{editor.CAPABILITIES_KEY}\FileAssociations", ext)] == (
            "QuillLite.Document",
            "sz",
        )
    assert values[(editor.CAPABILITIES_KEY, "ApplicationName")] == ("QUILL Lite", "sz")
    assert (editor.CAPABILITIES_KEY, "ApplicationDescription") in values
    assert values[(r"Software\RegisteredApplications", "QUILL Lite")] == (
        editor.CAPABILITIES_KEY,
        "sz",
    )


def test_registration_never_touches_a_user_choice_or_a_default() -> None:
    """Windows keeps the choice for the user. A key that pretends otherwise is
    ignored at best and flagged as tampering at worst."""
    for key in editor.registration_plan([LAUNCHER], ICON):
        assert "UserChoice" not in key.path
        if key.path.endswith(tuple(editor.EXTENSIONS)):
            raise AssertionError(f"wrote a type's own default value: {key.path}")


def test_the_types_are_the_ones_quill_lite_opens() -> None:
    from quill.core.lite.filetypes import OPEN_WILDCARD

    for ext in editor.EXTENSIONS:
        assert f"*{ext}" in OPEN_WILDCARD or ext in {".text", ".log"}, ext
    assert ".rtf" in editor.EXTENSIONS


def test_default_apps_opens_quill_lites_own_page_on_windows_11() -> None:
    assert (
        editor.default_apps_uri(22631) == "ms-settings:defaultapps?registeredAppUser=QUILL%20Lite"
    )
    assert (
        editor.default_apps_uri(26100, machine=True)
        == "ms-settings:defaultapps?registeredAppMachine=QUILL%20Lite"
    )
    assert editor.default_apps_uri(19045) == "ms-settings:defaultapps"


def test_an_administrator_install_of_this_copy_is_recognised() -> None:
    reader = FakeReader({
        r"Software\Classes\QuillLite.Document\shell\open\command": {"": f'"{LAUNCHER}" "%1"'},
        r"Software\RegisteredApplications": {"QUILL Lite": editor.CAPABILITIES_KEY},
    })
    assert editor.machine_registered(reader, [LAUNCHER])
    assert not editor.machine_registered(reader, [r"D:\Portable\QuillLite.exe"])
    assert not editor.machine_registered(FakeReader(), [LAUNCHER])


# -- the Notepad switch -----------------------------------------------------


def test_the_debugger_value_names_the_launcher_and_the_flag() -> None:
    assert editor.notepad_debugger_value([LAUNCHER]) == f'"{LAUNCHER}" --notepad'


def test_windows_10_has_one_key_and_windows_11_has_one_per_notepad_path() -> None:
    assert editor.notepad_keys(FakeReader()) == [editor.IFEO_KEY]
    assert editor.notepad_keys(_windows_11()) == [
        editor.IFEO_KEY,
        rf"{editor.IFEO_KEY}\0",
        rf"{editor.IFEO_KEY}\1",
        rf"{editor.IFEO_KEY}\2",
    ]


def test_a_subkey_for_some_other_program_is_not_a_notepad_key() -> None:
    reader = _windows_11()
    reader.keys[rf"{editor.IFEO_KEY}\9"] = {"FilterFullPath": r"C:\Tools\other.exe"}
    assert rf"{editor.IFEO_KEY}\9" not in editor.notepad_keys(reader)


def test_turning_on_writes_every_notepad_key_with_exact_reg_arguments() -> None:
    commands = editor.turn_on_commands(_windows_11(), [LAUNCHER])
    value = f'"{LAUNCHER}" --notepad'
    assert commands[0] == [
        "add",
        r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options"
        r"\notepad.exe",
        "/v",
        "Debugger",
        "/t",
        "REG_SZ",
        "/d",
        value,
        "/f",
        "/reg:64",
    ]
    assert [command[1] for command in commands] == [
        f"HKLM\\{key}" for key in editor.notepad_keys(_windows_11())
    ]


def test_turning_off_removes_only_quill_lites_own_values() -> None:
    ours = f'"{LAUNCHER}" --notepad'
    reader = _windows_11(parent=ours, k0=ours, k2=r'"C:\npp\notepad++.exe" -notepadStyleCmdline')
    assert editor.turn_off_commands(reader) == [
        ["delete", f"HKLM\\{editor.IFEO_KEY}", "/v", "Debugger", "/f", "/reg:64"],
        ["delete", f"HKLM\\{editor.IFEO_KEY}\\0", "/v", "Debugger", "/f", "/reg:64"],
    ]


def test_the_state_says_on_off_and_whose_debugger_is_there() -> None:
    assert not editor.read_notepad_state(_windows_11()).on
    on = editor.read_notepad_state(_windows_11(parent=f'"{LAUNCHER}" --notepad'))
    assert on.on and on.other is None
    other = editor.read_notepad_state(_windows_11(parent=r'"C:\npp\notepad++.exe" -z'))
    assert not other.on
    assert other.other == r'"C:\npp\notepad++.exe" -z'


def test_one_elevated_command_runs_every_reg_call() -> None:
    commands = editor.turn_on_commands(FakeReader(), [LAUNCHER])
    reg = r"C:\Windows\System32\reg.exe"
    parameters = editor.elevated_parameters(commands, reg)
    assert parameters == (
        '/d /s /c ""C:\\Windows\\System32\\reg.exe" add '
        '"HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Image File Execution '
        'Options\\notepad.exe" /v Debugger /t REG_SZ /d '
        '"\\"C:\\Program Files\\QuillLite\\QuillLite.exe\\" --notepad" /f /reg:64"'
    )


def test_a_launcher_path_cmd_would_rewrite_is_refused() -> None:
    assert editor.safe_for_cmd(editor.turn_on_commands(FakeReader(), [LAUNCHER]))
    for bad in (r"C:\R&D\QuillLite.exe", r"C:\100%\QuillLite.exe"):
        assert not editor.safe_for_cmd(editor.turn_on_commands(FakeReader(), [bad]))


# -- launched as Notepad -----------------------------------------------------


def _absolute(name: str) -> str:
    return str(Path(name).absolute())


def test_an_ordinary_launch_is_left_alone() -> None:
    assert editor.translate_notepad_argv(["a.txt", "--rich"]) == ["a.txt", "--rich"]
    assert editor.translate_notepad_argv([]) == []


def test_notepads_own_path_is_dropped_and_the_file_opens() -> None:
    argv = ["--notepad", r"C:\Windows\System32\notepad.exe", r"C:\notes\a.txt"]
    assert editor.translate_notepad_argv(argv, exists=lambda _p: True) == [r"C:\notes\a.txt"]


def test_no_file_means_a_blank_plain_document() -> None:
    assert editor.translate_notepad_argv(["--notepad", "notepad"]) == ["--plain"]
    assert editor.translate_notepad_argv(["--notepad"]) == ["--plain"]


def test_notepads_switches_are_dropped_and_print_opens_instead() -> None:
    for switch in ("/A", "/W", "/p", "/P"):
        argv = ["--notepad", "notepad.exe", switch, r"C:\notes\a.txt"]
        assert editor.translate_notepad_argv(argv) == [r"C:\notes\a.txt"]
    argv = ["--notepad", "notepad.exe", "/PT", r"C:\notes\a.txt", "Printer", "Driver", "Port"]
    assert editor.translate_notepad_argv(argv) == [r"C:\notes\a.txt"]


def test_an_unquoted_path_with_spaces_is_put_back_together() -> None:
    """Explorer's own .txt command is ``notepad.exe %1``, unquoted."""
    argv = ["--notepad", "NOTEPAD.EXE", r"C:\My", r"Notes\a", "b.txt"]
    assert editor.translate_notepad_argv(argv, exists=lambda _p: False) == [r"C:\My Notes\a b.txt"]


def test_separate_files_that_each_exist_stay_separate() -> None:
    real = {r"C:\one.txt", r"C:\two.txt"}
    argv = ["--notepad", "notepad.exe", r"C:\one.txt", r"C:\two.txt"]
    assert editor.translate_notepad_argv(argv, exists=real.__contains__) == sorted(real)


def test_a_relative_name_comes_back_absolute_and_never_as_a_switch() -> None:
    argv = ["--notepad", "notepad.exe", "--check"]
    assert editor.translate_notepad_argv(argv) == [_absolute("--check")]
