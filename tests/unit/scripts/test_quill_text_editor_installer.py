"""QUILL's installer registers it as a text editor, always, and takes nothing over.

The mirror of ``test_quilllite_text_editor_installer.py``. QUILL's ``.iss`` is
generated (``scripts/build_windows_distribution.py``), and the text-editor block
is generated from :data:`quill.core.windows_editor.QUILL` -- the same profile
Tools > Make QUILL My Text Editor writes -- so the installer and the command
cannot offer different types. These tests read the committed file, which the
generator-sync test keeps equal to the generator's output.
"""

from __future__ import annotations

import re
from pathlib import Path

from quill.core import windows_editor as editor

REPO = Path(__file__).resolve().parents[3]
ISS = REPO / "installer" / "quill.iss"
PROFILE = editor.QUILL


def _text() -> str:
    return ISS.read_text(encoding="utf-8")


def _block() -> list[str]:
    """The always-on text-editor lines: every HKA line in [Registry]."""
    section = _text().split("\n[Registry]\n", 1)[1].split("\n[", 1)[0]
    return [line.strip() for line in section.splitlines() if line.strip().startswith("Root: HKA;")]


def test_the_registration_is_unconditional() -> None:
    lines = _block()
    assert len(lines) > 20
    for line in lines:
        assert "Components:" not in line and "Tasks:" not in line and "Check:" not in line


def test_every_key_or_value_is_removed_on_uninstall() -> None:
    for line in _block():
        assert re.search(r"Flags:[^;]*\buninsdelete(key|value|keyifempty)\b", line), line


def test_a_shared_type_key_only_ever_loses_its_own_value() -> None:
    for line in _block():
        if "OpenWithProgids" in line:
            assert "uninsdeletevalue" in line and "uninsdeletekey" not in line, line


def test_the_types_match_the_app_command() -> None:
    joined = "\n".join(_block())
    named = set(re.findall(r"\\(\.[a-z]+)\\OpenWithProgids", joined))
    assert named == set(PROFILE.extensions)
    for ext in PROFILE.extensions:
        assert f'FileAssociations"; ValueType: string; ValueName: "{ext}"' in joined, ext
        assert f'SupportedTypes"; ValueType: string; ValueName: "{ext}"' in joined, ext


def test_progid_capabilities_and_registered_applications_are_written() -> None:
    joined = "\n".join(_block())
    assert 'Subkey: "Software\\Classes\\Quill.Document\\shell\\open\\command"' in joined
    # The same command the app writes when it is the installed quill.exe.
    assert 'ValueData: """{app}\\{#AppExeName}"" -m quill ""%1"""' in joined
    assert 'Subkey: "Software\\Classes\\Applications\\{#AppExeName}"' in joined
    assert '#define AppExeName "quill.exe"' in _text()
    assert (
        'Subkey: "Software\\RegisteredApplications"; ValueType: string; '
        'ValueName: "QUILL"; ValueData: "Software\\QUILL\\Capabilities"'
    ) in joined
    assert "QuillLite" not in joined  # QUILL Lite's names are QUILL Lite's installer's


def test_nothing_takes_a_default_over() -> None:
    assert "UserChoice" not in "\n".join(_block())
    for ext in PROFILE.extensions:
        assert f'Subkey: "Software\\Classes\\{ext}"; ValueType' not in _text()


def test_explorer_is_told_the_associations_changed() -> None:
    assert re.search(r"^ChangesAssociations=yes\s*$", _text(), re.M)


def test_uninstall_puts_notepad_back_but_only_our_values() -> None:
    """Left behind, the Notepad switch would point Notepad at a deleted exe."""
    code = _text().split("[Code]", 1)[1]
    assert "<event('CurUninstallStepChanged')>" in code
    assert "procedure CurUninstallStepChanged(" in code  # the data prompt still runs
    assert "Image File Execution Options\\notepad.exe" in code
    assert "ExpandConstant('{app}\\')" in code  # only values naming this install
    assert "Pos('--notepad'" in code
    assert "RegDeleteValue(HKLM64" in code
    assert "RegDeleteKey" not in code  # Microsoft's own keys are left alone
