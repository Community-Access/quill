"""F1 on QUILL Cast's episode list: what is unavailable for the selected row, and why (FUX-10).

Every dimmed episode and podcast action already carries its reason
(:mod:`quill.core.dimmed_reason`), but the reason reached a person only as the
context menu item's help string, which most screen readers do not speak in a
menu. F1 on the list now says it too, from the same resolved actions the menu
is built from, so the two cannot disagree.

Asked only when F1 is pressed (:func:`quill.ui.app_context_help.set_selection_help`),
never on selection.
"""

from __future__ import annotations

from typing import Any

from quill.core import dimmed_reason

__all__ = ["describe_selected_row", "install"]


def _episode_sentences(host: Any) -> list[str]:
    from quill.ui.podcasts.context_menus import resolved_episode_actions

    # Pause Download is left out: it is dimmed on every episode that is not
    # downloading, so it would end every answer with the least news. Its menu
    # item carries its own reason (context_menus.episode_row_menu).
    return [
        action.unavailable_sentence()
        for action in resolved_episode_actions(host)
        if not action.enabled
    ]


def _show_sentences(host: Any, show_id: str) -> list[str]:
    from quill.ui.podcasts.manager_menus import ordered_actions, show_actions

    show = host._podcast_library.find_show(show_id)
    if show is None:
        return []
    actions = ordered_actions(host, "show", show_actions(host, show))
    return [action.unavailable_sentence() for action in actions if not action.enabled]


def describe_selected_row(host: Any) -> str:
    """What is unavailable for the selected episode or podcast, or "" for anything else."""
    selected = host._list_selected_data()
    if selected is None:
        return ""
    kind, value = selected
    if kind == "episode":
        return dimmed_reason.unavailable_for("episode", _episode_sentences(host))
    if kind == "show":
        return dimmed_reason.unavailable_for("podcast", _show_sentences(host, value))
    return ""


def install(host: Any, episodes: Any) -> None:
    """Give the episode list its F1 paragraph about the selected row."""
    from quill.ui import app_context_help

    app_context_help.set_selection_help(episodes, lambda: describe_selected_row(host))
