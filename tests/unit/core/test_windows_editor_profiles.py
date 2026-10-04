"""The shared text-editor registration as QUILL uses it, and the one Notepad hook.

QUILL Lite's own behaviour is pinned in ``tests/unit/core/lite/test_lite_windows_editor.py``
through its bound profile; what is tested here is what changed when the
capability moved into :mod:`quill.core.windows_editor`: QUILL's profile, and
the two editors never mistaking each other's Notepad value for their own.
"""

from __future__ import annotations

import pytest

from quill.core import windows_editor as editor
from quill.core.lite import windows_editor as lite_editor

QUILL_EXE = r"C:\Program Files\QUILL for All\quill.exe"
QUILL_ARGV = [QUILL_EXE, "-m", "quill"]
LITE_EXE = r"C:\Program Files\QUILL Lite\QuillLite.exe"


class FakeWriter:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str], str] = {}

    def set_value(self, path: str, name: str, data: str, kind: str) -> None:
        self.values[(path, name)] = data


class FakeReader:
    def __init__(self, keys: dict[str, dict[str, object]] | None = None) -> None:
        self.keys = keys or {}

    def value(self, path: str, name: str) -> object | None:
        return self.keys.get(path, {}).get(name)

    def subkeys(self, path: str) -> list[str]:
        prefix = path + "\\"
        return sorted({k[len(prefix) :].split("\\")[0] for k in self.keys if k.startswith(prefix)})


# -- QUILL's profile -----------------------------------------------------------


def test_quills_registration_uses_its_own_progid_name_and_capabilities() -> None:
    writer = FakeWriter()
    editor.write_plan(editor.registration_plan(editor.QUILL, QUILL_ARGV, f"{QUILL_EXE},0"), writer)
    command = f'"{QUILL_EXE}" -m quill "%1"'
    assert writer.values[(r"Software\Classes\Quill.Document\shell\open\command", "")] == command
    app = r"Software\Classes\Applications\quill.exe"
    assert writer.values[(app, "FriendlyAppName")] == "QUILL"
    assert writer.values[(r"Software\RegisteredApplications", "QUILL")] == (
        r"Software\QUILL\Capabilities"
    )
    for ext in (".txt", ".md", ".rtf", ".docx", ".odt", ".epub"):
        assert writer.values[(rf"Software\Classes\{ext}\OpenWithProgids", "Quill.Document")] == ""
    assert not any("UserChoice" in path for path, _name in writer.values)
    assert not any("QuillLite" in path for path, _name in writer.values)


def test_quill_opens_everything_quill_lite_does() -> None:
    """QUILL Lite is never ahead of QUILL, in types as in commands."""
    assert set(editor.QUILL_LITE.extensions) <= set(editor.QUILL.extensions)


def test_quills_types_are_ones_quill_reads() -> None:
    from quill.io.detect import STRUCTURED_EXTENSIONS, TEXT_EXTENSIONS

    readable = TEXT_EXTENSIONS | STRUCTURED_EXTENSIONS | {".text", ".rtf", ".odt"}
    assert set(editor.QUILL.extensions) <= readable


def test_the_two_profiles_never_share_a_registry_name() -> None:
    quill, lite = editor.QUILL, editor.QUILL_LITE
    assert quill.progid != lite.progid
    assert quill.exe_name.lower() != lite.exe_name.lower()
    assert quill.capabilities_key.lower() != lite.capabilities_key.lower()
    assert quill.app_name != lite.app_name


def test_default_apps_opens_quills_own_page() -> None:
    assert (
        editor.default_apps_uri(editor.QUILL, 22631)
        == "ms-settings:defaultapps?registeredAppUser=QUILL"
    )


@pytest.mark.parametrize(
    ("base", "expected"),
    [
        # The installed quill.exe is a stamped pythonw: it needs -m quill.
        ([QUILL_EXE], QUILL_ARGV),
        # A dev run already names the module.
        ([r"C:\Python313\python.exe", "-m", "quill"], [r"C:\Python313\python.exe", "-m", "quill"]),
    ],
)
def test_quills_launcher_always_names_the_module(base: list[str], expected: list[str]) -> None:
    assert editor.editor_argv(editor.QUILL, base) == expected


def test_quill_lites_launcher_is_left_as_it_was() -> None:
    assert editor.editor_argv(editor.QUILL_LITE, [LITE_EXE]) == [LITE_EXE]


# -- one hook, two editors -------------------------------------------------------


QUILL_VALUE = editor.notepad_debugger_value(QUILL_ARGV)
LITE_VALUE = editor.notepad_debugger_value([LITE_EXE])
DEV_LITE_VALUE = r'"C:\Python313\python.exe" -m quill.apps.lite --notepad'
RUNTIME_LITE_VALUE = r'"C:\QuillVille\QuillVilleRuntime.exe" -m quill.apps.lite --notepad'


def test_quills_debugger_value_keeps_the_module_before_the_flag() -> None:
    assert QUILL_VALUE == f'"{QUILL_EXE}" -m quill --notepad'


@pytest.mark.parametrize(
    ("value", "owner"),
    [
        (QUILL_VALUE, "QUILL"),
        (r'"C:\Python313\python.exe" -m quill --notepad', "QUILL"),
        (LITE_VALUE, "QUILL Lite"),
        (DEV_LITE_VALUE, "QUILL Lite"),
        (RUNTIME_LITE_VALUE, "QUILL Lite"),
        (r'"C:\npp\notepad++.exe" -notepadStyleCmdline -z', None),
        (f'"{QUILL_EXE}" -m quill', None),  # no flag: not a Notepad hook
        ("", None),
        (None, None),
    ],
)
def test_each_value_has_exactly_the_right_owner(value: object, owner: str | None) -> None:
    assert editor.owner_of(value) == owner
    assert editor.is_ours(editor.QUILL, value) is (owner == "QUILL")
    assert editor.is_ours(editor.QUILL_LITE, value) is (owner == "QUILL Lite")


def test_quill_lites_bound_helpers_agree_with_the_shared_ones() -> None:
    assert lite_editor.is_ours(LITE_VALUE)
    assert not lite_editor.is_ours(QUILL_VALUE)
    assert lite_editor.PROFILE is editor.QUILL_LITE


def test_the_state_names_the_other_family_editor() -> None:
    reader = FakeReader({editor.IFEO_KEY: {"Debugger": LITE_VALUE}})
    state = editor.read_notepad_state(editor.QUILL, reader)
    assert not state.on
    assert state.other == LITE_VALUE
    assert state.other_owner == "QUILL Lite"
    back = editor.read_notepad_state(
        editor.QUILL_LITE, FakeReader({editor.IFEO_KEY: {"Debugger": QUILL_VALUE}})
    )
    assert back.other_owner == "QUILL"
    stranger = editor.read_notepad_state(
        editor.QUILL, FakeReader({editor.IFEO_KEY: {"Debugger": r'"C:\npp\notepad++.exe" -z'}})
    )
    assert stranger.other_owner is None


def test_turning_quill_off_never_removes_quill_lites_value() -> None:
    reader = FakeReader({
        editor.IFEO_KEY: {"Debugger": QUILL_VALUE},
        rf"{editor.IFEO_KEY}\0": {
            "FilterFullPath": r"C:\Windows\System32\notepad.exe",
            "Debugger": LITE_VALUE,
        },
    })
    assert editor.turn_off_commands(editor.QUILL, reader) == [
        ["delete", f"HKLM\\{editor.IFEO_KEY}", "/v", "Debugger", "/f", "/reg:64"]
    ]
    assert editor.turn_off_commands(editor.QUILL_LITE, reader) == [
        ["delete", f"HKLM\\{editor.IFEO_KEY}\\0", "/v", "Debugger", "/f", "/reg:64"]
    ]
