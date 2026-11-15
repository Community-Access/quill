"""Context-menu rows for what REST cannot do, PMPro's routes and WordPress.org (complete.md 10B.3).

Split from :mod:`quill.core.wordpress.workbench_actions` (GATE-11), which
splices these rows into its table, as it does the Gravity Forms rows. Each
command is on the context menu of the rows it acts on; none has a chord, and
:data:`KEYLESS` says why for each (family rule 8): they are once-in-a-while
jobs (rule 9) that open a dialog or the browser, and the Workbench's chords
are kept for the jobs done every day. Wx-free.
"""

from __future__ import annotations

from quill.core.workbench.actions import ActionRow, Tier

__all__ = [
    "ACROSS_ROWS",
    "DASHBOARD_ROWS",
    "KEYLESS",
    "MODEL_ROWS",
    "PLUGIN_ROWS",
    "PMPRO_ROWS",
    "SETTING_ROWS",
    "THEME_ROWS",
    "USER_ROWS",
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
    needs: str = "",
    default: bool = False,
) -> ActionRow:
    return ActionRow(command(verb), label, tier, needs, help, default)


_DASHBOARD = _a(
    "open_dashboard",
    "Open in Dashboard",
    "The wp-admin screen for what WordPress's REST API cannot do here: updates, automatic "
    "updates, and for a theme, activating and installing.",
)

PLUGIN_ROWS: tuple[ActionRow, ...] = (
    _a(
        "plugin_directory",
        "Check on WordPress.org...",
        "After you agree to ask WordPress.org, each plugin on this site in words: rating, "
        "active installs, last updated, tested up to, what it needs, and whether it is closed "
        "or looks abandoned. The answer is added to each plugin row for this window.",
    ),
    _a(
        "find_plugin",
        "Find a Plugin on WordPress.org...",
        "Search WordPress.org's plugin directory, after you agree to ask it; read each plugin, "
        "then install the one chosen on this site, inactive, after a preview.",
        tier=Tier.WRITE,
        needs="install_plugins",
    ),
    _DASHBOARD,
)

THEME_ROWS: tuple[ActionRow, ...] = (
    _a(
        "find_theme",
        "Find a Theme on WordPress.org...",
        "Search WordPress.org's theme directory, after you agree to ask it; read each theme, "
        "then install it in a site's Appearance > Themes > Add New.",
    ),
    _DASHBOARD,
)

ACROSS_ROWS: tuple[ActionRow, ...] = (
    _a(
        "install_missing",
        "Install on Sites Missing It...",
        "A plugin from WordPress.org is installed on each site without it, after a preview; "
        "a theme opens each of those sites' Add New screen, because REST cannot install themes.",
        tier=Tier.WRITE,
    ),
    _DASHBOARD,
)

SETTING_ROWS: tuple[ActionRow, ...] = (
    _a(
        "language_packs",
        "Language Pack Status...",
        "Each site's language, and whether WordPress.org has its pack for that WordPress "
        "version, after you agree to ask WordPress.org.",
    ),
)

USER_ROWS: tuple[ActionRow, ...] = (
    _a(
        "check_access",
        "Check Membership Access...",
        "Whether this person may see a post or page, as Paid Memberships Pro decides it.",
    ),
    _a(
        "change_membership",
        "Change Membership Level...",
        "Give this person another Paid Memberships Pro level, after a preview of what ends "
        "and which recurring payment stops.",
        tier=Tier.WRITE,
    ),
    _a(
        "cancel_membership",
        "Cancel Membership...",
        "Cancel one of this person's Paid Memberships Pro levels, after a preview naming the "
        "recurring subscription and gateway that are cancelled with it.",
        tier=Tier.DESTRUCTIVE,
    ),
    _a(
        "user_app_passwords",
        "Their Application Passwords...",
        "This person's application passwords, read from the site, with Revoke after you "
        "confirm. Another person's need the edit_users capability.",
        needs="edit_users",
    ),
    _a(
        "sign_out_everywhere",
        "Sign Out Everywhere...",
        "WordPress keeps sign-in sessions out of its REST API, so this opens the person's "
        "wp-admin screen, where Log Out Everywhere is one button.",
    ),
    _a(
        "never_signed_in",
        "Who Has Never Signed In",
        "The people on this site with no sign-in recorded, where the site gives sign-in times "
        "over REST (a plugin that registers last_login); otherwise it says it cannot tell.",
    ),
    _a(
        "invite_spreadsheet",
        "Invite from a Spreadsheet...",
        "Add people from a CSV file of email, role and name, after a preview of every row.",
        tier=Tier.WRITE,
        needs="create_users",
    ),
)

PMPRO_ROWS: tuple[ActionRow, ...] = (
    _a(
        "look_up_discount",
        "Look Up a Discount Code...",
        "Read one Paid Memberships Pro discount code by its code.",
    ),
    _a(
        "new_discount_code",
        "New Discount Code...",
        "Make a Paid Memberships Pro discount code, after a preview of what it will be.",
        tier=Tier.WRITE,
        needs="manage_options",
    ),
)

MODEL_ROWS: tuple[ActionRow, ...] = (
    _a(
        "define_site_type",
        "Define with QUILL Site Types...",
        "A new post type, taxonomy or field group, kept by the QUILL Site Types plugin and "
        "registered in REST, after a preview. Ctrl+N on Content Model does the same.",
        tier=Tier.WRITE,
        needs="manage_options",
    ),
    _a(
        "stop_defining",
        "Stop Defining...",
        "Take away a definition QUILL Site Types keeps, after a preview; its posts, terms and "
        "values stay in the database, and Ctrl+Z defines it again.",
        tier=Tier.WRITE,
        needs="manage_options",
    ),
    _a(
        "edit_site_type_fields",
        "Fields...",
        "A QUILL Site Types field group's fields, one sheet each: kind, label, help, required, "
        "default and choices, or a new field, after a preview.",
        tier=Tier.WRITE,
        needs="manage_options",
    ),
    _a(
        "add_field_kind",
        "Add a Field Kind...",
        "A field kind of the site's own for QUILL Site Types: how it is stored and a pattern "
        "its values must match, after a preview.",
        tier=Tier.WRITE,
        needs="manage_options",
    ),
    _a(
        "move_to_site_types",
        "Copy to QUILL Site Types...",
        "The way to move a post type, taxonomy or field group a plugin or theme defines into "
        "QUILL Site Types: a copy under the same key, after a preview. The original is not "
        "deleted; the preview says what to turn off where, and what does not come across.",
        tier=Tier.WRITE,
        needs="manage_options",
    ),
    _a(
        "export_as_code",
        "Export as Code",
        "Every QUILL Site Types definition as the PHP register calls, opened in the editor, so "
        "a theme or plugin can keep the types if the plugin goes.",
        needs="manage_options",
    ),
)

DASHBOARD_ROWS: tuple[ActionRow, ...] = (
    _a(
        "open_on_site",
        "Open in Dashboard",
        "The wp-admin screen that does this, in your browser. Enter.",
        default=True,
    ),
)

KEYLESS: dict[str, str] = {
    command("open_dashboard"): "Leaves QUILL for the browser, now and then (rule 9).",
    command("find_theme"): "Choosing a new theme happens a few times a year (rule 9).",
    command("plugin_directory"): "Checked now and then, after you agree to ask (rule 9).",
    command("find_plugin"): "A new plugin is added a few times a year, previewed (rule 9).",
    command("install_missing"): "Filling the gaps across sites is occasional and previewed.",
    command("language_packs"): "Checked after a WordPress release, not daily (rule 9).",
    command("check_access"): "Asked when a member reports a locked page, now and then.",
    command("change_membership"): "Members change level at checkout; staff do it rarely (rule 9).",
    command("cancel_membership"): "A cancellation is rare and stops payments: never a bare key.",
    command("user_app_passwords"): "Checked when a device is lost or a person leaves (rule 9).",
    command("sign_out_everywhere"): "Leaves QUILL for wp-admin, after a lost device (rule 9).",
    command("never_signed_in"): "Checked when tidying accounts, a few times a year (rule 9).",
    command("invite_spreadsheet"): "People arrive in a batch a few times a year (rule 9).",
    command("insert_picked"): "Enter does it in picking mode, the only time it applies.",
    command("look_up_discount"): "A code is looked up when a member asks about it (rule 9).",
    command("new_discount_code"): "Codes are made for a sale or event, rarely (rule 9).",
    command("define_site_type"): "Ctrl+N on Content Model; a new type is rare (rule 9).",
    command("stop_defining"): "Retiring a content type is rare and previewed (rule 9).",
    command("export_as_code"): "Exported once, when a site leaves the plugin (rule 9).",
    command("edit_site_type_fields"): "Fields change when a content type does, rarely (rule 9).",
    command("add_field_kind"): "A site adds its own kind once in a long while (rule 9).",
    command("move_to_site_types"): "A definition moves once, when a site changes plugin (rule 9).",
    command("visual_review"): "A page is reviewed after a redesign, now and then (rule 9).",
    command("set_password"): "Set when a person is locked out, rarely; never a bare key (rule 9).",
}
"""Why each command here has no chord (family rule 8)."""
