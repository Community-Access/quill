"""Context-menu rows for wp-admin parity on Posts, Pages and Media (wordpress.md 9.18, 1 to 3).

Split from :mod:`quill.core.wordpress.workbench_actions` (GATE-11), which
splices these rows in before Properties, as it does the Gravity Forms and
admin rows. Each row names the capability it needs, so the window refuses it
with the role that would allow it before anything is sent, and its tier,
which decides how it is confirmed. None has a chord: :data:`KEYLESS` says why
for each (family rule 8). The Workbench's chords are already dense, and these
are jobs a person does now and then from the row's context menu
(Applications key or Shift+F10). Wx-free.
"""

from __future__ import annotations

from quill.core.workbench.actions import ActionRow, Tier

__all__ = ["ITEM_ROWS", "KEYLESS", "MEDIA_ROWS", "NODE_ROWS", "command"]


def command(verb: str) -> str:
    """The same ids as :func:`quill.core.wordpress.workbench_window_menu.command`."""
    return f"wordpress.workbench.{verb}"


def _a(
    verb: str,
    label: str,
    help: str,  # noqa: A002 - field name
    *,
    tier: Tier = Tier.READ,
    needs: str = "",
) -> ActionRow:
    return ActionRow(command(verb), label, tier, needs, help, False)


_COUNTS = _a(
    "status_counts",
    "Counts by Status",
    "How many there are in each of wp-admin's views: All, Mine, Published, Drafts, Pending, "
    "Scheduled, Private and Trash; for media, each type and Unattached.",
)
_DASHBOARD = _a(
    "dashboard_screen",
    "Open in wp-admin",
    "The wp-admin screen for what WordPress's REST API cannot do here: who is editing it now, "
    "and for media, scaling the original by numbers. In your browser.",
)
_EMPTY_TRASH = _a(
    "empty_trash",
    "Empty Trash...",
    "Delete everything of this kind in the Trash permanently, after you confirm the count and "
    "the names. This cannot be undone.",
    tier=Tier.DESTRUCTIVE,
    needs="delete",
)

ITEM_ROWS: tuple[ActionRow, ...] = (
    _a(
        "duplicate",
        "Duplicate as Draft",
        "A new draft copy on the same site, with its categories, tags and picture. "
        "Ctrl+Z moves the copy to the Trash.",
        tier=Tier.WRITE,
        needs="edit",
    ),
    _COUNTS,
    _EMPTY_TRASH,
    _DASHBOARD,
)

MEDIA_ROWS: tuple[ActionRow, ...] = (
    _a(
        "edit_picture",
        "Edit Picture...",
        "Turn, flip, crop to a shape, or crop by numbers in percent, after a preview. WordPress "
        "keeps the original and makes the edit a new picture.",
        tier=Tier.WRITE,
        needs="upload_files",
    ),
    _a(
        "regenerate_sizes",
        "Regenerate Sizes",
        "Remake the picture's thumbnail and other sizes from its original.",
        tier=Tier.WRITE,
        needs="upload_files",
    ),
    _a(
        "attach",
        "Attach to a Post or Page...",
        "Find a post or page by words or number and attach the file to it. Ctrl+Z puts it back.",
        tier=Tier.WRITE,
        needs="upload_files",
    ),
    _a(
        "detach",
        "Detach",
        "Leave it in the library, attached to nothing. Ctrl+Z attaches it again.",
        tier=Tier.WRITE,
        needs="upload_files",
    ),
    _a("download", "Download...", "Save the file to this computer, where you choose."),
    _COUNTS,
    _DASHBOARD,
)

NODE_ROWS: tuple[ActionRow, ...] = (_COUNTS, _EMPTY_TRASH)

KEYLESS: dict[str, str] = {
    command("status_counts"): "The tree's status nodes and the status bar count as you go; "
    "every count at once is asked now and then (rule 9).",
    command(
        "dashboard_screen"
    ): "Leaves QUILL for wp-admin, only for what REST cannot do (rule 9).",
    command("empty_trash"): "Permanent and occasional: never a bare key (rules 4 and 9).",
    command("duplicate"): "A copy is made now and then, from the row's context menu (rule 9).",
    command("edit_picture"): "Opens a dialog, a few times a site's life (rule 9).",
    command("regenerate_sizes"): "Needed after an edit or a theme change, rarely (rule 9).",
    command("attach"): "Uploads from the editor attach themselves; this is the exception (rule 9).",
    command("detach"): "The rare undoing of an attachment (rule 9).",
    command("download"): "Opens a Save As box, now and then (rule 9).",
}
"""Why each command here has no chord (family rule 8)."""
