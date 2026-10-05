"""Quill Radio's installer registers it as a media player, always, and takes nothing over.

The sibling of ``test_quill_text_editor_installer.py``. ``quill-radio.iss`` is
written by hand except for the block between its generated-block marks, which
comes from :data:`quill.core.windows_media.RADIO` -- the profile Preferences >
Make Quill Radio My Media Player writes for one account -- through the same
generator as QUILL's. These tests read the committed file.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from quill.core.windows_installer_lines import BEGIN_MARK, END_MARK
from quill.core.windows_media import RADIO

REPO = Path(__file__).resolve().parents[3]
ISS = REPO / "standalone" / "radio" / "installer" / "quill-radio.iss"
sys.path.insert(0, str(REPO / "scripts"))

import build_windows_distribution as bwd  # noqa: E402
import sync_radio_installer_registry as sync  # noqa: E402


def _text() -> str:
    return ISS.read_text(encoding="utf-8")


def _block() -> list[str]:
    body = _text().split(BEGIN_MARK, 1)[1].split(END_MARK, 1)[0]
    return [line.strip() for line in body.splitlines() if line.strip()]


def _keys() -> list[str]:
    return [line for line in _block() if line.startswith("Root:")]


def test_the_block_is_what_the_generator_writes() -> None:
    assert _block() == bwd.build_media_player_registry_lines(), (
        "run python scripts/sync_radio_installer_registry.py"
    )
    assert sync.main(["--check"]) == 0


def test_the_block_is_inside_the_registry_section() -> None:
    text = _text()
    section = text.split("\n[Registry]\n", 1)[1].split("\n[", 1)[0]
    assert BEGIN_MARK in section and END_MARK in section


def test_the_registration_is_unconditional_and_uses_hka() -> None:
    lines = _keys()
    assert len(lines) > 40
    for line in lines:
        assert line.startswith("Root: HKA;"), line
        assert "Components:" not in line and "Tasks:" not in line and "Check:" not in line


def test_every_key_or_value_is_removed_on_uninstall() -> None:
    for line in _keys():
        assert re.search(r"Flags:[^;]*\buninsdelete(key|value|keyifempty)\b", line), line


def test_the_verbs_and_the_open_with_entries_go_on_uninstall() -> None:
    """Each kind of line carries the flag that removes exactly what it wrote.

    The two right-click verbs and SupportedTypes live under keys that are
    Quill Radio's own, so the key goes; OpenWithProgids is a key every player
    shares, so only Quill Radio's value goes.
    """
    keys = _keys()

    def flags(line: str) -> str:
        return line.split("Flags:", 1)[1].strip()

    verbs = [line for line in keys if "\\shell\\QuillRadio." in line]
    assert {"Play", "Enqueue"} <= {re.search(r"QuillRadio\.(\w+)", v).group(1) for v in verbs}
    assert any('ValueData: "Play with Quill Radio"' in v for v in verbs)
    assert any('ValueData: "Add to Quill Radio Playlist"' in v for v in verbs)
    supported = [line for line in keys if "\\SupportedTypes" in line]
    progids = [line for line in keys if "\\OpenWithProgids" in line]
    assert len(supported) == len(progids) == len(RADIO.extensions)
    for line in verbs + supported:
        assert flags(line) == "uninsdeletekey", line
    for line in progids:
        assert flags(line) == "uninsdeletevalue", line


def test_a_shared_type_key_only_ever_loses_its_own_value() -> None:
    for line in _keys():
        if "OpenWithProgids" in line or "RegisteredApplications" in line:
            assert "uninsdeletevalue" in line and "uninsdeletekey" not in line, line


def test_the_types_match_the_app_command() -> None:
    joined = "\n".join(_keys())
    named = set(re.findall(r"\\(\.[a-z0-9]+)\\OpenWithProgids", joined))
    assert named == set(RADIO.extensions)
    for ext in RADIO.extensions:
        assert f'FileAssociations"; ValueType: string; ValueName: "{ext}"' in joined, ext
        assert f'SupportedTypes"; ValueType: string; ValueName: "{ext}"' in joined, ext


def test_the_launcher_opens_the_file_and_the_verbs_are_there() -> None:
    joined = "\n".join(_keys())
    assert 'Subkey: "Software\\Classes\\QuillRadio.Media\\shell\\open\\command"' in joined
    assert 'ValueData: """{app}\\QuillRadio.exe"" ""%1"""' in joined
    assert 'ValueData: """{app}\\QuillRadio.exe"" --enqueue ""%1"""' in joined
    assert 'ValueData: "Play with Quill Radio"' in joined
    assert (
        'Subkey: "Software\\RegisteredApplications"; ValueType: string; '
        'ValueName: "Quill Radio"; ValueData: "Software\\QuillRadio\\Capabilities"'
    ) in joined


def test_nothing_takes_a_default_over() -> None:
    text = _text()
    assert "UserChoice" not in text
    for ext in RADIO.extensions:
        assert f'Subkey: "Software\\Classes\\{ext}"; ValueType' not in text


def test_explorer_is_told_the_associations_changed() -> None:
    assert re.search(r"^ChangesAssociations=yes\s*$", _text(), re.M)


def test_there_is_still_no_tasks_section() -> None:
    """Screen readers announce [Tasks] boxes as unchecked whatever they are."""
    assert "\n[Tasks]" not in _text()
