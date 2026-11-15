"""Context-menu rows for Earlier Versions, Check for Updates and Check Every Link (wp_missing.md).

Split from :mod:`quill.core.wordpress.workbench_actions` and
:mod:`~quill.core.wordpress.workbench_places` (GATE-11), which splice these
in: Earlier Versions on a post, page or custom item's row, Check for Updates
on WordPress.org on plugin, theme and Needs My Attention > Updates rows, and
Check Every Link on a row of By Name > Links. Each names the capability it
needs and its tier. None has a chord: :data:`KEYLESS` says why for each
(family rule 8); they are reached from the row's context menu (Applications
key or Shift+F10). Wx-free.
"""

from __future__ import annotations

from quill.core.workbench.actions import ActionRow, Tier

__all__ = ["CHECK_LINKS", "ITEM_VERSIONS", "KEYLESS", "UPDATE_CHECK", "command"]


def command(verb: str) -> str:
    """The same ids as :func:`quill.core.wordpress.workbench_window_menu.command`."""
    return f"wordpress.workbench.{verb}"


ITEM_VERSIONS = ActionRow(
    command("item_versions"),
    "Earlier Versions...",
    Tier.WRITE,
    "edit",
    "The site's revisions and autosaves of this item, newest first; each is compared with "
    "the item now, line by line, and restored after that preview. The item is read again "
    "first, and Ctrl+Z puts it back.",
    False,
)

UPDATE_CHECK = ActionRow(
    command("check_updates"),
    "Check for Updates on WordPress.org...",
    Tier.READ,
    "",
    "After you agree to ask WordPress.org, compare this site's WordPress, plugins and themes "
    "with the versions WordPress.org has now, and mark each row update waiting, up to date or "
    "unknown. Only short names are sent. Paid plugins WordPress.org does not list say unknown.",
    False,
)

CHECK_LINKS = ActionRow(
    command("check_every_link"),
    "Check Every Link...",
    Tier.READ,
    "",
    "Every link in every published post, page and item on this site, checked by the site in "
    "the background, with a running count in the status bar. Choose it again, or press Enter "
    "on the status bar's Link check, to stop. The broken links are listed with what holds each.",
    False,
)

KEYLESS: dict[str, str] = {
    ITEM_VERSIONS.command_id: "Looked for after a mistake, rarely (rule 9).",
    UPDATE_CHECK.command_id: "Asked now and then, after you agree to ask (rule 9).",
    CHECK_LINKS.command_id: "A whole-site run after a reorganisation, rarely (rule 9).",
}
"""Why each command here has no chord (family rule 8)."""
