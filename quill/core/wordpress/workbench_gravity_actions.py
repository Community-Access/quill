"""Gravity Forms in the Workbench's tree, context menus and Item menu (complete.md 10B.3).

Split from :mod:`quill.core.wordpress.workbench_actions` (GATE-11), which
splices these rows into its table. Each command is offered only on a Gravity
Forms row (:data:`GRAVITY_ONLY`), and each names the Gravity Forms permission
it needs (:data:`NEEDS`), which the window checks itself because Gravity Forms
grants every one of them to ``gform_full_access`` -- the capability a site
administrator holds instead of the individual ones.

Every command has a key or a written reason (family rule 8): the four used
while working through entries carry Ctrl+Alt chords on the Item menu; the rest
sit in Item > Gravity Forms with an access letter, and :data:`KEYLESS` says why
each has no chord. Wx-free.
"""

from __future__ import annotations

from quill.core.workbench.actions import ActionRow, Tier
from quill.core.workbench.menus import MenuRow, MenuSub
from quill.core.workbench.tree import NodeSpec

__all__ = [
    "GRAVITY_BUILD_ROWS",
    "GRAVITY_ENTRY_ROWS",
    "GRAVITY_FEED_ROWS",
    "GRAVITY_FORM_ROWS",
    "GRAVITY_ITEM_ROWS",
    "GRAVITY_NODES",
    "GRAVITY_ONLY",
    "GRAVITY_QAF_ROWS",
    "GRAVITY_SUB",
    "KEYLESS",
    "NEEDS",
]


def command(verb: str) -> str:
    """The same ids as :func:`quill.core.wordpress.workbench_window_menu.command`.

    Not imported from there: that module builds its Item menu from this one.
    """
    return f"wordpress.workbench.{verb}"


def _a(verb: str, label: str, tier: Tier, help: str) -> ActionRow:  # noqa: A002
    return ActionRow(command(verb), label, tier, "", help, False)


GRAVITY_ENTRY_ROWS: tuple[ActionRow, ...] = (
    _a(
        "entry_notes",
        "Notes...",
        Tier.READ,
        "Read this entry's notes, and add one. Ctrl+Alt+N.",
    ),
    _a("toggle_starred", "Star or Unstar", Tier.ORGANIZE, "Star it to come back to. Ctrl+Alt+F."),
    _a("toggle_read", "Mark Read or Unread", Tier.ORGANIZE, "Mark it read or unread. Ctrl+Alt+U."),
    _a(
        "resend_notifications",
        "Resend Notifications...",
        Tier.WRITE,
        "Send its emails again, after a preview of who gets them. Ctrl+Alt+I.",
    ),
)

GRAVITY_FORM_ROWS: tuple[ActionRow, ...] = (
    _a("show_feeds", "Show Its Feeds", Tier.READ, "Its Mailchimp, Stripe and other feeds."),
    _a("show_results", "Show Its Results", Tier.READ, "Its quiz, poll or survey results."),
    _a(
        "test_form",
        "Test This Form...",
        Tier.WRITE,
        "Check test values, then send a real test entry. A practice site is best.",
    ),
)

GRAVITY_BUILD_ROWS: tuple[ActionRow, ...] = (
    _a(
        "edit_gravity_form",
        "Edit Form...",
        Tier.WRITE,
        "Its fields, logic and settings in QUILL's form editor; checked, previewed, then saved.",
    ),
    _a(
        "new_gravity_form",
        "New Gravity Form...",
        Tier.WRITE,
        "Build a new Gravity Forms form in QUILL's form editor. Ctrl+N on Forms does the same.",
    ),
    _a(
        "copy_as_qaf_form",
        "Copy as a QUILL Accessible Form...",
        Tier.WRITE,
        "A new QUILL Accessible Forms draft from this form, after a preview of what cannot carry.",
    ),
)
"""Building forms in QUILL (complete.md WP-C): on a Gravity Forms form row."""

GRAVITY_QAF_ROWS: tuple[ActionRow, ...] = (
    _a(
        "copy_as_gravity_form",
        "Copy as a Gravity Form...",
        Tier.WRITE,
        "A new Gravity Forms form from this one, after a preview of what cannot carry over.",
    ),
)
"""On a QUILL Accessible Forms form row, where the site has Gravity Forms too."""

GRAVITY_FEED_ROWS: tuple[ActionRow, ...] = (
    _a(
        "toggle_feed",
        "Activate or Deactivate...",
        Tier.WRITE,
        "Turn this feed on or off, after a preview.",
    ),
    _a("rename_feed", "Rename...", Tier.WRITE, "Give this feed another name, after a preview."),
)

GRAVITY_ONLY: frozenset[str] = frozenset(
    row.command_id
    for row in (*GRAVITY_ENTRY_ROWS, *GRAVITY_FORM_ROWS, *GRAVITY_FEED_ROWS, *GRAVITY_BUILD_ROWS)
    if row.command_id != command("new_gravity_form")  # a site's command, from any Forms row
)
"""Commands that mean nothing on a QUILL Accessible Forms row."""

NEEDS: dict[str, str] = {
    command("entry_notes"): "view_notes",
    command("toggle_starred"): "edit_entries",
    command("toggle_read"): "edit_entries",
    command("resend_notifications"): "edit_entries",
    command("toggle_feed"): "edit_forms",
    command("rename_feed"): "edit_forms",
    command("edit_gravity_form"): "design_forms",
}
"""The :data:`~quill.core.wordpress.workbench_gravity.CAPABILITIES` key each command needs."""

GRAVITY_ITEM_ROWS: tuple[MenuRow, ...] = (
    MenuRow(command("entry_notes"), "Entry Notes...", "Ctrl+Alt+N", "Read and add entry notes."),
    MenuRow(command("toggle_starred"), "Star or Unstar Entry", "Ctrl+Alt+F", "Star the entry."),
    MenuRow(command("toggle_read"), "Mark Entry Read or Unread", "Ctrl+Alt+U", "Read or unread."),
    MenuRow(
        command("resend_notifications"),
        "Resend Notifications...",
        "Ctrl+Alt+I",
        "Send the entry's emails again, after a preview.",
    ),
)
"""Item menu rows with chords, for the commands used while working through entries."""

GRAVITY_SUB = MenuSub(
    "Gravity &Forms",
    (
        MenuRow(command("show_feeds"), "Show Its &Feeds", help="The selected form's feeds."),
        MenuRow(command("show_results"), "Show Its &Results", help="The form's results."),
        MenuRow(command("test_form"), "&Test This Form...", help="Validate, then submit."),
        MenuRow(
            command("change_gravity_field_type"),
            "Change a Field T&ype...",
            help="Change one field's control after a preview.",
        ),
        MenuRow(command("edit_gravity_form"), "&Edit Form...", help="Edit it in QUILL."),
        MenuRow(command("new_gravity_form"), "Ne&w Gravity Form...", help="Build one in QUILL."),
        MenuRow(
            command("copy_as_qaf_form"),
            "Copy as a &QUILL Accessible Form...",
            help="A QAF draft from this form.",
        ),
        MenuRow(
            command("copy_as_gravity_form"),
            "Copy QAF Form as a &Gravity Form...",
            help="A Gravity Forms form from the selected QAF form.",
        ),
        None,
        MenuRow(command("toggle_feed"), "&Activate or Deactivate Feed...", help="On or off."),
        MenuRow(command("rename_feed"), "Re&name Feed...", help="Another name for the feed."),
    ),
    help="What QUILL does with a Gravity Forms form or feed.",
)
"""Item > Gravity Forms: the commands without a chord, each with its access letter."""

KEYLESS: dict[str, str] = {
    command("show_feeds"): "Once per question about a form; Enter-and-filter on Forms > Feeds.",
    command("show_results"): "Read after a poll closes, not daily; Forms > Results is one key.",
    command("test_form"): "Run after editing a form, a few times a year (rule 9): a letter.",
    command("change_gravity_field_type"): "A form-design change made rarely (rule 9).",
    command("toggle_feed"): "Switching an add-on on or off is rare and previewed (rule 9).",
    command("rename_feed"): "Renaming a feed is rare (rule 9).",
    command("edit_gravity_form"): "Designing a form is occasional work, not daily (rule 9).",
    command("new_gravity_form"): "New Here (Ctrl+N) on a site's Forms node reaches it.",
    command("copy_as_qaf_form"): "Moving a form between plugins is a once-off (rule 9).",
    command("copy_as_gravity_form"): "Moving a form between plugins is a once-off (rule 9).",
}
"""Why each Gravity Forms command without a chord has none (family rule 8)."""

GRAVITY_NODES: tuple[NodeSpec, ...] = (
    NodeSpec(
        "form_feeds",
        "Feeds",
        "forms",
        loader="forms:feeds",
        columns=("name", "form", "addon", "status"),
        row_type="gravity_feed",
    ),
    NodeSpec(
        "form_results",
        "Results",
        "forms",
        loader="forms:results",
        columns=("form", "question", "answer", "count", "share"),
        row_type="gravity_result",
    ),
)
"""Sites > site > Forms > Feeds and Results, beside Responses (the tree keeps four deep)."""
