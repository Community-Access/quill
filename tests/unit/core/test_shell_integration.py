from __future__ import annotations

import pytest

from quill.core.shell_verbs import default_shell_verbs
from quill.platform.windows.shell_integration import (
    APPLICATION_KEY,
    PROGID_HTML,
    PROGID_MARKUP,
    PROGID_TEXT,
    _coerce_registry_value,
    build_context_menu_plan,
    build_shell_integration_plan,
    context_menu_registry_paths,
    verb_launcher_command,
)


def test_build_shell_integration_plan_includes_progids() -> None:
    plan = build_shell_integration_plan('"python.exe" -m quill "%1"')
    paths = {entry.path for entry in plan}

    assert APPLICATION_KEY in paths
    assert rf"{APPLICATION_KEY}\shell\open\command" in paths
    assert rf"{APPLICATION_KEY}\SupportedTypes" in paths
    assert rf"Software\Classes\{PROGID_TEXT}" in paths
    assert rf"Software\Classes\{PROGID_MARKUP}" in paths
    assert rf"Software\Classes\{PROGID_HTML}" in paths


def test_build_shell_integration_plan_includes_extension_open_with_entries() -> None:
    plan = build_shell_integration_plan('"python.exe" -m quill "%1"')
    open_with_paths = [entry.path for entry in plan if entry.path.endswith(r"OpenWithProgids")]

    assert open_with_paths


def test_verb_launcher_command_carries_action() -> None:
    command = verb_launcher_command("ocr")
    assert "--action ocr" in command
    assert command.rstrip().endswith('"%1"')


def test_verb_launcher_command_rejects_unknown_action() -> None:
    # SEC-17: the command is written to the registry; only allowlisted shell
    # verb actions may reach it. A free-form/injected action must be refused.
    with pytest.raises(ValueError):
        verb_launcher_command('open" & del /q "%1')
    with pytest.raises(ValueError):
        verb_launcher_command("not-a-real-verb")


def test_verb_launcher_command_normalizes_case_and_whitespace() -> None:
    # Known actions are accepted regardless of surrounding case/whitespace,
    # proving normalization happens before the allowlist check.
    command = verb_launcher_command("  OCR  ")
    assert "--action ocr" in command


def test_context_menu_plan_registers_each_verb_extension() -> None:
    plan = build_context_menu_plan()
    paths = {entry.path for entry in plan}
    # The OCR verb applies to images, so a .png shell key must exist.
    assert any(r"SystemFileAssociations\.png\shell\Quill.ocr" in path for path in paths)
    # Every verb shell key must have a matching \command child.
    shell_keys = {p for p in paths if not p.endswith("command")}
    for key in shell_keys:
        assert rf"{key}\command" in paths


def test_context_menu_plan_default_value_is_label() -> None:
    plan = build_context_menu_plan()
    ocr = default_shell_verbs()[0]
    label_entries = [entry for entry in plan if entry.path.endswith(rf"shell\Quill.{ocr.verb_id}")]
    assert label_entries
    for entry in label_entries:
        default_value = next(v.value for v in entry.values if v.name == "")
        assert default_value == ocr.label


def test_context_menu_registry_paths_cover_command_and_key() -> None:
    paths = context_menu_registry_paths()
    assert any(path.endswith("command") for path in paths)
    assert any(not path.endswith("command") for path in paths)


def test_coerce_registry_value_passes_bytes_for_binary_kinds() -> None:
    # #921: the OpenWithProgids entry writes an empty REG_NONE value with the
    # progid as the value NAME. Python 3.13's winreg rejects a str for a binary
    # kind ("Objects of type 'str' can not be used as binary registry values"),
    # which crashed Tools -> Install Shell Integration on the 3.13 build. The
    # empty str (and None) must coerce to b""; a non-empty str must encode; raw
    # bytes pass through untouched.
    import winreg

    assert _coerce_registry_value(winreg.REG_NONE, "") == b""
    assert _coerce_registry_value(winreg.REG_NONE, None) == b""
    assert _coerce_registry_value(winreg.REG_BINARY, "abc") == b"abc"
    assert _coerce_registry_value(winreg.REG_BINARY, b"raw") == b"raw"


def test_coerce_registry_value_passes_str_for_string_kinds() -> None:
    # String kinds keep a str (winreg rejects bytes for REG_SZ); bytes are
    # decoded back to str so a caller that happens to hold bytes still works.
    import winreg

    assert _coerce_registry_value(winreg.REG_SZ, "label") == "label"
    assert _coerce_registry_value(winreg.REG_EXPAND_SZ, b"label") == "label"


def test_build_shell_integration_plan_openwithprogids_uses_none_kind() -> None:
    # The progid OpenWithProgids entries are the exact #921 crash site: an empty
    # value under REG_NONE. Confirm the plan still produces that shape so the
    # coercion above is the thing standing between it and a crash on 3.13.
    import winreg

    plan = build_shell_integration_plan('"python.exe" -m quill "%1"')
    open_with = [entry for entry in plan if entry.path.endswith(r"OpenWithProgids")]
    assert open_with
    for entry in open_with:
        for value in entry.values:
            assert value.kind == winreg.REG_NONE
            assert value.value == ""
