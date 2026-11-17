"""Context-menu rows for help topics, problems, plugin dependencies and explained settings (Part D).

Split from :mod:`quill.core.wordpress.workbench_actions` (GATE-11), which
splices these in:

- **Help topics** (Do Something, The Guide, What Changed, Ask a Person):
  Open, the default, reads the topic or opens the chapter or message it names;
  Take Me There goes to the place a task is about (D11, D12).
- **Problems** (Site Health and Broken Links rows): Explain, the default, says
  what it means for visitors, what causes it and the steps; Fix... does what
  can be done from here; Take Me There goes to the place or wp-admin screen;
  Open in Editor opens the post that holds a broken link (D3).
- **Plugins:** What Depends on It, before turning one off or deleting it (D3).
- **Explained settings** (Permalinks, Discussion, search visibility, plugin
  settings): Open Its Documentation and Open in Dashboard (D2).

None has a chord: :data:`KEYLESS` says why for each (family rule 8); they are
reached from the row's context menu (Applications key or Shift+F10), and
Enter does the default. Wx-free.
"""

from __future__ import annotations

from quill.core.workbench.actions import ActionRow, Tier

__all__ = [
    "HELP_TOPIC_ROWS",
    "KEYLESS",
    "PROBLEM_ROWS",
    "SETTING_HELP_ROWS",
    "WHAT_DEPENDS",
    "command",
]


def command(verb: str) -> str:
    """The same ids as :func:`quill.core.wordpress.workbench_window_menu.command`."""
    return f"wordpress.workbench.{verb}"


def _a(
    verb: str,
    label: str,
    help: str,  # noqa: A002 - field name
    *,
    tier: Tier = Tier.READ,
    default: bool = False,
) -> ActionRow:
    return ActionRow(command(verb), label, tier, "", help, default)


HELP_TOPIC_ROWS = (
    _a(
        "open_topic",
        "Open",
        "Read the topic, or open the guide chapter or the support message it names. Enter.",
        default=True,
    ),
    _a("take_me_there", "Take Me There", "Go to the place in the tree that the topic is about."),
)

PROBLEM_ROWS = (
    _a(
        "explain_problem",
        "Explain",
        "What this means for visitors, what usually causes it, and the steps to fix it, with "
        "WordPress's own words. Enter.",
        default=True,
    ),
    _a(
        "fix_problem",
        "Fix...",
        "Do the fix from here when it can be done: change a broken link in the post that holds "
        "it, or set a city time zone, after a preview. When only wp-admin can, open that screen.",
        tier=Tier.WRITE,
    ),
    _a(
        "problem_there",
        "Take Me There",
        "Go to the place in the tree where this is fixed, such as Settings or Plugins.",
    ),
    _a(
        "problem_in_editor",
        "Open in Editor",
        "Open the post or page that holds this broken link in the editor.",
    ),
)

WHAT_DEPENDS = _a(
    "what_depends",
    "What Depends on It",
    "Ask the site what would notice if this plugin went: plugins that require it, pages that "
    "use its blocks or shortcodes, and QUILL features that use it. Nothing is changed.",
)

SETTING_HELP_ROWS = (
    _a(
        "open_docs",
        "Open Its Documentation",
        "Open the plugin's own documentation for its settings in your browser.",
    ),
    _a(
        "setting_screen",
        "Open in Dashboard",
        "Open the wp-admin screen that changes this setting, which WordPress's API does not.",
    ),
)

KEYLESS: dict[str, str] = {
    row.command_id: "Reached from the row's context menu; Enter does the default (rule 9)."
    for row in (*HELP_TOPIC_ROWS, *PROBLEM_ROWS, WHAT_DEPENDS, *SETTING_HELP_ROWS)
}
"""Why each command here has no chord (family rule 8)."""
