"""Add to Lineup follows the Customize Features switch for QUILL Lineups."""

from __future__ import annotations

from types import SimpleNamespace

from quill.ui.podcasts import manager_menus


def _dialog(on: bool) -> SimpleNamespace:
    return SimpleNamespace(_cast_area_enabled=lambda area: on or area != "lineups")


def test_lineups_switched_off_leaves_add_to_lineup_out() -> None:
    assert manager_menus._lineups_on(_dialog(True)) is True
    assert manager_menus._lineups_on(_dialog(False)) is False


def test_a_host_without_the_switch_keeps_it() -> None:
    assert manager_menus._lineups_on(SimpleNamespace()) is True


def test_a_failing_settings_read_keeps_it() -> None:
    def boom(_area: str) -> bool:
        raise RuntimeError("settings unreadable")

    assert manager_menus._lineups_on(SimpleNamespace(_cast_area_enabled=boom)) is True
