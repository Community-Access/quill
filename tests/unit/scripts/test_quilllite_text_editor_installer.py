"""QUILL Lite's installer registers it as a text editor, always, and takes nothing over.

The installer and Tools > Make QUILL Lite My Text Editor write the same keys, so
the list of types is checked against :data:`quill.core.lite.windows_editor.EXTENSIONS`
-- two lists that drift apart give a type the installer offers and the command
does not, or the other way round.
"""

from __future__ import annotations

import re
from pathlib import Path

from quill.core.lite import windows_editor as editor

REPO = Path(__file__).resolve().parents[3]
ISS = REPO / "standalone" / "quilllite" / "installer" / "quilllite.iss"


def _registry_lines() -> list[str]:
    text = ISS.read_text(encoding="utf-8")
    section = text.split("\n[Registry]\n", 1)[1].split("\n[", 1)[0]
    return [
        line.strip()
        for line in section.splitlines()
        if line.strip() and not line.strip().startswith(";")
    ]


def test_there_is_no_association_component_any_more() -> None:
    text = ISS.read_text(encoding="utf-8")
    assert 'Name: "assoc"' not in text
    assert "Components: assoc" not in text


def test_the_registration_is_unconditional_and_uses_hka() -> None:
    lines = _registry_lines()
    assert lines
    for line in lines:
        assert line.startswith("Root: HKA;"), line
        assert "Components:" not in line and "Tasks:" not in line and "Check:" not in line


def test_every_key_or_value_is_removed_on_uninstall() -> None:
    for line in _registry_lines():
        assert re.search(r"Flags:[^;]*\buninsdelete(key|value|keyifempty)\b", line), line


def test_a_shared_type_key_only_ever_loses_its_own_value() -> None:
    """``.txt`` belongs to every editor on the machine; uninstalling QUILL Lite
    may remove QUILL Lite's entry in it, never the key."""
    for line in _registry_lines():
        if "OpenWithProgids" in line:
            assert "uninsdeletevalue" in line and "uninsdeletekey" not in line, line


def test_the_types_match_the_app_command() -> None:
    lines = _registry_lines()
    for ext in editor.EXTENSIONS:
        assert any(
            f"\\{ext}\\OpenWithProgids" in line and 'ValueName: "QuillLite.Document"' in line
            for line in lines
        ), ext
        assert any(
            "FileAssociations" in line and f'ValueName: "{ext}"' in line for line in lines
        ), ext
        assert any("SupportedTypes" in line and f'ValueName: "{ext}"' in line for line in lines)
    named = set(re.findall(r"\\(\.[a-z]+)\\OpenWithProgids", "\n".join(lines)))
    assert named == set(editor.EXTENSIONS)


def test_progid_capabilities_and_registered_applications_are_written() -> None:
    joined = "\n".join(_registry_lines())
    assert 'Subkey: "Software\\Classes\\QuillLite.Document\\shell\\open\\command"' in joined
    assert '"""{app}\\QuillLite.exe"" ""%1"""' in joined
    assert 'Subkey: "Software\\Classes\\QuillLite.Document\\DefaultIcon"' in joined
    assert 'Subkey: "Software\\Classes\\Applications\\QuillLite.exe"' in joined
    assert 'ValueName: "ApplicationName"' in joined
    assert 'ValueName: "ApplicationDescription"' in joined
    assert (
        'Subkey: "Software\\RegisteredApplications"; ValueType: string; '
        'ValueName: "{#AppName}"; ValueData: "Software\\QuillLite\\Capabilities"'
    ) in joined
    assert editor.CAPABILITIES_KEY == "Software\\QuillLite\\Capabilities"


def test_nothing_takes_a_default_over() -> None:
    text = ISS.read_text(encoding="utf-8")
    assert "UserChoice" not in "\n".join(_registry_lines())
    for ext in editor.EXTENSIONS:
        # A type's own default value is its owner; QUILL Lite never sets one.
        assert f'Subkey: "Software\\Classes\\{ext}"; ValueType' not in text


def test_explorer_is_told_the_associations_changed() -> None:
    assert re.search(r"^ChangesAssociations=yes\s*$", ISS.read_text(encoding="utf-8"), re.M)


def test_uninstall_puts_notepad_back_but_only_our_values() -> None:
    """Left behind, the Notepad switch would point Notepad at a deleted exe."""
    code = ISS.read_text(encoding="utf-8").split("[Code]", 1)[1]
    assert "<event('CurUninstallStepChanged')>" in code
    assert "Image File Execution Options\\notepad.exe" in code
    assert "{app}\\QuillLite.exe" in code  # only values naming this install
    assert "RegDeleteValue(HKLM64" in code
    assert "RegDeleteKey" not in code  # Microsoft's own keys are left alone
