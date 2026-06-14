"""Characterization tests for the first-party contribution facade.

These pin the Wave 0 behaviour of :mod:`quill.core.contributions`: first-party
commands expressed in the shared grammar flow through the *same*
:func:`quill.core.quillins.registry.build_registry` as third-party Quillins, so
uniqueness and hotkey collisions are detected uniformly, and the power-tools pilot
(menus.md Phase 5) is genuinely driven by the declarative manifest.
"""

from __future__ import annotations

import pytest

from quill.core.contributions import (
    FIRST_PARTY_EXTENSION_ID,
    FIRST_PARTY_MENU_PARENTS,
    FirstPartyRegistrar,
    build_first_party_manifest,
    build_first_party_registry,
)
from quill.core.quillins.model import (
    Contributions,
    ExtensionCommand,
    ExtensionManifest,
    HotkeyContribution,
    MenuContribution,
)
from quill.core.quillins.registry import build_registry
from quill.ui.main_frame_power_tools_menu import POWER_TOOLS_COMMANDS


def _registrar_with(*specs: tuple[str, str, str]) -> FirstPartyRegistrar:
    registrar = FirstPartyRegistrar()
    for command_id, top_level, group in specs:
        registrar.add_command(
            id=command_id,
            title=command_id.replace(".", " ").title(),
            top_level=top_level,
            group=group,
            label=command_id,
        )
    return registrar


def test_handler_name_strips_namespace() -> None:
    registrar = _registrar_with(("power.number_lines", "Format", "transform"))
    (command,) = registrar.commands
    assert command.handler_name == "number_lines"


def test_unknown_top_level_menu_is_rejected() -> None:
    registrar = FirstPartyRegistrar()
    with pytest.raises(ValueError, match="unknown top-level menu"):
        registrar.add_command(id="x.do", title="Do", top_level="Bogus", group="g", label="Do")


def test_duplicate_command_id_is_rejected_at_declaration() -> None:
    registrar = _registrar_with(("power.a", "Tools", "g"))
    with pytest.raises(ValueError, match="duplicate first-party command id"):
        registrar.add_command(id="power.a", title="A2", top_level="Tools", group="g", label="A2")


def test_first_party_parents_superset_quillin_parents() -> None:
    # First-party code owns the whole bar (Insert/Search included), unlike the
    # narrow third-party MENU_PARENTS.
    assert "Insert" in FIRST_PARTY_MENU_PARENTS
    assert "Search" in FIRST_PARTY_MENU_PARENTS


def test_manifest_round_trips_through_shared_registry() -> None:
    registrar = _registrar_with(
        ("power.alpha", "Insert", "insert"),
        ("power.beta", "Search", "search"),
    )
    registry = registrar.registry()
    assert set(registry.commands) == {"power.alpha", "power.beta"}
    assert registry.conflicts == ()
    parents = {menu.command_id: menu.parent for menu in registry.menus}
    assert parents == {"power.alpha": "Insert", "power.beta": "Search"}


def test_build_first_party_manifest_records_handlers_and_menus() -> None:
    registrar = _registrar_with(("power.alpha", "Format", "transform"))
    manifest = build_first_party_manifest(registrar.commands)
    assert isinstance(manifest, ExtensionManifest)
    assert manifest.id == FIRST_PARTY_EXTENSION_ID
    (command,) = manifest.contributes.commands
    assert command.handler == "alpha"
    (menu,) = manifest.contributes.menus
    assert menu == MenuContribution(parent="Format", command="power.alpha")


def test_hotkey_collision_with_host_keymap_is_recorded() -> None:
    registrar = FirstPartyRegistrar()
    registrar.add_command(
        id="power.bound",
        title="Bound",
        top_level="Tools",
        group="g",
        label="Bound",
        binding="CTRL+S",
    )
    registry = registrar.registry(host_keymap={"file.save": "CTRL+S"})
    assert registry.hotkeys == ()
    assert len(registry.conflicts) == 1
    conflict = registry.conflicts[0]
    assert conflict.kind == "hotkey"
    assert conflict.conflicting_with == "file.save"


def test_first_party_and_quillin_collide_through_one_registry() -> None:
    # A Quillin binding that clashes with an accepted first-party binding is
    # rejected by the SAME merge engine — proving the shared collision surface.
    first_party = build_first_party_manifest(
        _registrar_with(("power.alpha", "Insert", "insert")).commands
    )
    first_party_bound = ExtensionManifest(
        id=first_party.id,
        name=first_party.name,
        version=first_party.version,
        contributes=Contributions(
            commands=first_party.contributes.commands,
            menus=first_party.contributes.menus,
            hotkeys=(HotkeyContribution(command="power.alpha", binding="CTRL+ALT+J"),),
        ),
    )
    quillin = ExtensionManifest(
        id="ext.sample",
        name="Sample",
        version="1.0",
        contributes=Contributions(
            commands=(ExtensionCommand(id="ext.sample.go", title="Go", handler="go"),),
            hotkeys=(HotkeyContribution(command="ext.sample.go", binding="CTRL+ALT+J"),),
        ),
    )
    registry = build_registry([first_party_bound, quillin])
    assert any(c.kind == "hotkey" and c.extension_id == "ext.sample" for c in registry.conflicts)


def test_power_tools_manifest_is_consumed_and_conflict_free() -> None:
    # 33 original + 10 TextMonkey/EdSharp-parity commands (§4.22/§4.23)
    # + 2 Copy Tray dialog-level commands (open + clear_all)
    # + 3 encoding tools (#197: encode_all_non_ascii, show_non_ascii, reencode_file)
    registry = build_first_party_registry(POWER_TOOLS_COMMANDS)
    assert len(POWER_TOOLS_COMMANDS) == 48
    assert len(registry.commands) == 48
    assert registry.conflicts == ()
    for menu in registry.menus:
        assert menu.parent in FIRST_PARTY_MENU_PARENTS


def test_power_tools_pilot_homes_match_phase_four_recirculation() -> None:
    registry = build_first_party_registry(POWER_TOOLS_COMMANDS)
    parents = {menu.command_id: menu.parent for menu in registry.menus}
    assert parents["power.insert_special_character"] == "Insert"
    assert parents["power.number_lines"] == "Format"
    assert parents["power.go_to_percent"] == "Navigate"
    assert parents["power.count_regex_matches"] == "Search"
    assert parents["power.run_current_file"] == "Tools"
    assert parents["power.toggle_read_only_guard"] == "Tools"
