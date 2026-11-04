"""The family's one AI menu shape (quill/core/ai/ai_menu_layout.py)."""

from __future__ import annotations

import importlib

import pytest

from quill.core.ai import ai_menu_layout as layout


class _Menu:
    def __init__(self) -> None:
        self.items: list[object] = []

    def AppendSeparator(self) -> None:  # noqa: N802 - wx's name
        self.items.append("---")

    def AppendSubMenu(self, sub: _Menu, title: str) -> None:  # noqa: N802
        self.items.append((title, sub.items))

    def GetMenuItemCount(self) -> int:  # noqa: N802
        return len(self.items)


def _labels(rows: tuple[tuple[str, str, str], ...]) -> list[object]:
    menu = _Menu()
    layout.fill(menu, rows, lambda m, row: m.items.append(row[2]), _Menu)
    return menu.items


_WEATHER_LIKE = (
    ("ask", "&Ask...", "cmd_ai_chat_key"),
    ("which", "&Which AI Am I Using", "cmd_ai_which"),
    ("choose", "&Choose Your AI...", "cmd_ai_choose"),
    ("", "", ""),
    ("go", "Should I &Go Out?", "cmd_go_out"),
    ("", "", ""),
    ("plan", "Use My C&hatGPT Subscription...", "cmd_ai_chatgpt"),
    ("key", "Use My &Own AI Key...", "cmd_ai_own_key"),
    ("usage", "AI U&sage...", "cmd_ai_usage"),
    ("privacy", "&Privacy Agreement...", "cmd_ai_privacy"),
)


def test_features_then_which_ai_then_the_accounts_submenu() -> None:
    assert _labels(_WEATHER_LIKE) == [
        "cmd_ai_chat_key",
        "---",
        "cmd_go_out",
        "---",
        "cmd_ai_which",
        "cmd_ai_choose",
        "---",
        (
            layout.ACCOUNTS_TITLE,
            ["cmd_ai_own_key", "cmd_ai_chatgpt", "cmd_ai_usage", "cmd_ai_privacy"],
        ),
    ]


def test_no_stray_separators_and_no_empty_submenu() -> None:
    rows = (("", "", ""), ("a", "&A", "cmd_a"), ("", "", ""), ("", "", ""))
    assert _labels(rows) == ["cmd_a"]


def test_extra_rows_join_the_features() -> None:
    menu = _Menu()
    layout.fill(
        menu,
        _WEATHER_LIKE[:3],
        lambda m, row: m.items.append(row[2]),
        _Menu,
        extra=lambda m: m.items.append("cmd_extra"),
    )
    assert menu.items == ["cmd_ai_chat_key", "cmd_extra", "---", "cmd_ai_which", "cmd_ai_choose"]


@pytest.mark.parametrize(
    "module",
    [
        "quill.apps.converter_ai",
        "quill.apps.inkwell_ai",
        "quill.apps.player_ai",
        "quill.apps.transcribe_ai",
        "quill.apps.weather_ai",
        "quill.ui.audio_studio.studio_ai_host",
        "quill.ui.podcasts.cast_ai_host",
        "quill.ui.radio.radio_ai_host",
        "quill.apps.beacon.ai",
    ],
)
def test_every_app_menu_keeps_a_unique_access_key_per_level(module: str) -> None:
    """Moving rows between levels must not leave two rows on one letter."""
    rows = importlib.import_module(module).AI_ROWS
    features, choose, accounts = layout.arrange(rows)
    title_letter = layout.ACCOUNTS_TITLE.split("&")[1][0].lower()

    def letters(group: list[tuple[str, str, str]]) -> list[str]:
        return [r[1].split("&")[1][0].lower() for r in group if r[0] and "&" in r[1]]

    top = letters(features + choose) + ([title_letter] if accounts else [])
    assert len(top) == len(set(top)), (module, top)
    inner = letters(accounts)
    assert len(inner) == len(set(inner)), (module, inner)


def test_quill_lite_tools_ai_is_in_the_family_shape() -> None:
    from quill.core.lite.commands_ai import AI_MENU_ROWS

    top = [r[3] or r[1] or "---" for r in AI_MENU_ROWS if r[0] == "&Tools|&AI"]
    assert top[-1] == layout.ACCOUNTS_TITLE
    assert top.index("cmd_ai_choose") > top.index("cmd_ai_task")
    inner = [r[3] for r in AI_MENU_ROWS if r[0].endswith(layout.ACCOUNTS_TITLE)]
    assert inner == list(layout.ACCOUNT_HANDLERS)
