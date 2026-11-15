"""F1 in the WordPress Workbench: what each node and each kind of row is (Part D).

Every node of :data:`~quill.core.wordpress.workbench_tree.WORDPRESS_TREE`
has a sentence here (:data:`NODE_HELP`), and every row type of the action
table one more (:data:`ROW_HELP`); a test checks that none is missing, so a
node added without its help fails the build. The window gives the tree the
selected node's sentence and the list the selected row's, as their F1 help,
so F1 answers with the window's purpose and then what is under focus.

The words follow D1: WordPress's names, explained the way the people who
were never shown would want them. Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping

from quill.core.wordpress.workbench_dashboard_places import (
    DASHBOARD_NODE_HELP,
    DASHBOARD_ROW_HELP,
)
from quill.core.wordpress.workbench_plugin_nodes import PLUGIN_NODE_HELP, PLUGIN_ROW_HELP
from quill.core.wordpress.workbench_sweep_places import SWEEP_NODE_HELP, SWEEP_ROW_HELP

__all__ = ["NODE_HELP", "PLANNED_WORDS", "ROW_HELP", "node_help", "row_help"]

NODE_HELP: Mapping[str, str] = {
    "start": "What the Workbench is and how to move around it.",
    "attention": "What waits on you, gathered from every connected site.",
    "inbox": "Everything below Needs My Attention, newest first, from every site.",
    "waiting": "Comments held for moderation on every site. Ctrl+Shift+A approves.",
    "pending_review": "Posts and pages by people who cannot publish, waiting for an editor.",
    "scheduled": "Posts and pages that will publish themselves, with their dates.",
    "my_drafts": "Your own drafts, on every site.",
    "updates": (
        "WordPress, plugin and theme versions; Check for Updates on WordPress.org, on any "
        "row's context menu, says which have an update waiting. Enter opens Dashboard > Updates."
    ),
    "health_problems": "Site Health problems on every site, worst first.",
    "accessibility": (
        "Pictures without alt text from every connected site. Check This Page finds "
        "page-level issues."
    ),
    "broken_links": (
        "Dead web links found in a bounded sample of published posts and pages on every site."
    ),
    "held_as_spam": "Comments and form entries a site doubted. Ctrl+Shift+A releases one.",
    "form_responses": "New form responses, from every site with a form plugin QUILL reads.",
    "orders": (
        "Paid Memberships Pro orders waiting on a person: pending, in review or failed. "
        "Shop orders are not membership orders and are not listed here."
    ),
    "watches": "What you asked the Workbench to keep an eye on.",
    "sites": "Every connected site, with your role on each. Right Arrow opens one.",
    "calendar": "Every site's scheduled and published content, a day to a node.",
    "search": (
        "WordPress search results from every connected site, with the source site and "
        "content type shown."
    ),
    "practice": "A practice WordPress site on this computer, where nothing is at stake.",
    "calendar_day": "What was published or is scheduled on one day, on every site.",
    "help": "Words, keys, and how WordPress thinks.",
    "how_it_thinks": "How WordPress thinks, in a paragraph.",
    "words": "WordPress's own words, each explained.",
    "keys": "Every key the Workbench answers to.",
    "site": "One site. Its overview is first; Right Arrow opens the rest.",
    "overview": "The site in sentences: its name, address, WordPress version and counts.",
    "posts": "The site's posts, newest change first. Enter opens one in the editor.",
    "pages": "The site's pages, as a tree by parent. Enter opens one in the editor.",
    "content_types": "The kinds of content this site's plugins add, such as Events.",
    "custom_type": "Items of one kind a plugin added. Enter opens one in the editor.",
    "media": "Pictures, audio, video and documents in the media library.",
    "media_no_alt": "Pictures with no alt text, which a screen reader cannot describe.",
    "media_unattached": "Media not attached to any post or page.",
    "comments": "Every comment on the site. Delete moves one to the Trash.",
    "categories": "The site's categories, as a tree. Show Its Posts lists what is filed there.",
    "tags": "The site's tags. Merge Into folds one into another.",
    "taxonomies": "The ways of grouping this site's plugins add.",
    "custom_taxonomy": "The terms of one taxonomy a plugin added.",
    "menus": "The site's menus and where the theme shows them.",
    "appearance": "Themes, templates, patterns, fonts and widgets.",
    "themes": (
        "The installed themes. WordPress's REST API only reads them, so Open in Dashboard "
        "activates, installs and updates in wp-admin; Find a Theme on WordPress.org searches."
    ),
    "global_styles": "The site's global styles: colours, type and spacing.",
    "patterns": "Synced patterns: blocks you reuse, changed in one place.",
    "fonts": "The fonts the site has installed.",
    "forms": "The site's forms, from every form plugin QUILL reads.",
    "form_entries": "Responses to the site's forms.",
    "form_spam": "Form responses held as spam.",
    "form_feeds": (
        "Each Gravity Forms form's add-on feeds, such as Mailchimp, Stripe or Zapier, and "
        "whether each is active. A form's Show Its Feeds lands here filtered to it."
    ),
    "form_results": (
        "Quiz, poll and survey results from Gravity Forms: a row per answer with its count "
        "and share, and the question's results as one sentence in the details pane."
    ),
    "memberships": (
        "Paid Memberships Pro levels, orders, subscriptions and renewals, when its Abilities API "
        "is available."
    ),
    "membership_levels": (
        "Paid Memberships Pro membership levels and their signup and billing terms."
    ),
    "membership_orders": (
        "Paid Memberships Pro order summaries, not WooCommerce shop orders. Card and billing "
        "details are never shown."
    ),
    "membership_subscriptions": "Paid Memberships Pro subscriptions and their next payment dates.",
    "membership_renewals": (
        "Paid Memberships Pro subscriptions due for renewal now or within thirty days."
    ),
    "membership_discount_codes": (
        "Paid Memberships Pro discount codes. Look Up a Discount Code reads one by its code; "
        "New Discount Code makes one after a preview. The full list is in wp-admin unless the "
        "site offers a discount-codes ability."
    ),
    "shop": (
        "WooCommerce's products, from its wc/v3 routes. Ctrl+N makes one; the context menu "
        "edits price, stock, status and categories after a preview. A site without "
        "WooCommerce says so. Shop Orders, below, are the shop's orders."
    ),
    "shop_orders": (
        "WooCommerce's shop orders, each read as a receipt; status, notes and refunds are on "
        "the context menu, each previewed. These are not "
        "membership orders: Paid Memberships Pro's are under Needs My Attention > Membership "
        "Orders and Memberships > Orders."
    ),
    "podcast": (
        "The site's podcast episodes: its podcast content type's items, or else the posts "
        "that carry an episode's player, as Post This Episode makes them. Enter opens one "
        "in the editor."
    ),
    "people": "The people on the site and the passwords made for apps.",
    "users": "The people on the site, with their roles. Site > Roles explains each role.",
    "app_passwords": "Your application passwords on this site. Ctrl+N makes one.",
    "plugins": "The installed plugins, active and not.",
    "settings": "The site's settings the REST API can read and change.",
    "site_health": "WordPress's own checks of how well the site is set up.",
    "site_health_info": (
        "What REST covers of Site Health's Info tab: the tests and the directory sizes. The "
        "server, database and constants are only in wp-admin; their row opens Site Health Info."
    ),
    "site_health_security": (
        "Whether the site still answers on XML-RPC, which QUILL never uses, checked without "
        "a password."
    ),
    "abilities": "What the site's Abilities API offers, each a command you can run.",
    "more": "Every family of routes on this site, by namespace, and how many are reached.",
    "more_namespace": "One namespace's routes, with their methods and where each is reached.",
    "content_model": (
        "The site's post types, taxonomies and field groups, and who registered each. Only "
        "what QUILL Site Types defines can change here: Ctrl+N defines a new one."
    ),
    "across": "The same name on every site, or a Site Set: where copies differ, what is missing.",
    "across_terms": "Each tag and category by name, on every site: differing slugs, sites without.",
    "across_plugins": "Each plugin by name, on every site: versions, active or not, missing.",
    "across_themes": "Each theme by name, on every site.",
    "across_users": "Each person, by email, on every site, with their role on each.",
    "across_settings": "Each setting, on every site, and where the values drift.",
    "across_app_passwords": "Each application password by name and person, on every site.",
    "across_menus": "Each menu by name, on every site: its items, and the sites without it.",
    "across_patterns": "Each synced pattern by title, on every site: its content, where missing.",
    "across_starter_pages": "Each starter page by title, on every site: compared, not copied.",
    "across_forms": "Each QUILL Accessible Forms form by title, on every site: its questions.",
    "across_content_types": "Each post type by name, on every site: compared, not copied.",
    "across_role_pages": "The front page and privacy page of every site, and when each changed.",
    "across_redirects": "Each Redirection redirect by its address, on every site: where it leads.",
    "across_spam_senders": "Each sender blocked by QUILL Accessible Forms, on every site.",
    "fleet": "Every site in one list: health, backups, security and updates, each known, "
    "unknown, unavailable or stale.",
    "by_name": "Everything on this site by name: terms, fields, authors, media, links, blocks.",
    "by_name_terms": "Every term of every taxonomy, with how many posts each has.",
    "by_name_fields": "Every custom field value, and how many items have it.",
    "by_name_authors": "Every author, with what they have written by status.",
    "by_name_media_usage": "Every file in the library, and where it is used.",
    "by_name_patterns": "Synced patterns, and the pages that use them.",
    "by_name_links": (
        "Every link in the content, and the pages it is on. Check Every Link, on a row's "
        "context menu, checks them all in the background."
    ),
    "by_name_blocks": "Blocks and shortcodes, and the pages that use them.",
    "by_name_forms": "Forms placed in pages, and where.",
    "by_name_template_parts": "A block theme's template parts, and the templates that place them.",
    "media_housekeeping": "Files used nowhere, files uploaded twice, very large files, video "
    "without captions, audio without a transcript; usage shows before Move to Trash.",
    "content_audit": "Pages nobody links to, pages not changed in a year, duplicate titles and "
    "text, very long or short pages, hard reading, headings that skip a level.",
    "privacy_requests": "Where wp-admin keeps personal data export and erase requests; Enter "
    "opens it.",
    "group": "The rows of the list above that share one value, from View > Group By.",
    **SWEEP_NODE_HELP,
    **DASHBOARD_NODE_HELP,
    **PLUGIN_NODE_HELP,  # Shop's other nodes, Events Calendar, SEO
}
"""One sentence per node key; status children and group nodes share their parent's."""

ROW_HELP: Mapping[str, str] = {
    "item": (
        "A post, page or item. Enter opens it in the editor, Alt+Enter its Properties; "
        "Earlier Versions on the context menu compares and restores the site's revisions."
    ),
    "media": "A file in the media library. Enter opens it; Alt+Enter edits its alt text.",
    "comment": "A comment. Ctrl+Shift+A approves, Ctrl+Shift+S marks it as spam.",
    "form_entry": (
        "A form response. Enter reads it in full. On Gravity Forms, the context menu also has "
        "Notes, Star, Mark Read and Resend Notifications, and Properties changes its answers."
    ),
    "gravity_feed": (
        "A Gravity Forms add-on feed. Activate or Deactivate, and Rename, preview first; "
        "Shift+Delete deletes it."
    ),
    "gravity_result": "One answer's count in a quiz, poll or survey. Enter reads the question.",
    "pmpro": (
        "A Paid Memberships Pro level, membership order, subscription or discount code. "
        "Alt+Enter reads its details."
    ),
    "term": "A category, tag or term. Enter lists its posts; Merge Into folds it into another.",
    "user": (
        "A person on the site. Change Role, Remove, and any exposed membership details are on "
        "the context menu."
    ),
    "plugin": (
        "A plugin. Activate or Deactivate is on the context menu, and Check for Updates on "
        "WordPress.org says whether one waits; updates run in wp-admin, through Open in Dashboard."
    ),
    "theme": (
        "A theme. REST only reads themes: Activate and Open in Dashboard go to Appearance > "
        "Themes in wp-admin. Check for Updates on WordPress.org says whether one waits."
    ),
    "dashboard": "A job REST cannot do. Enter opens the wp-admin screen that does it.",
    "app_password": "An application password. Delete revokes it.",
    "site": "A connected site. Enter selects it in the tree.",
    "writing_type": "A kind of content. Enter opens its list.",
    "taxonomy": "A way of grouping. Enter opens its terms.",
    "form": "A form. Enter lists its responses.",
    "gravity_form": (
        "A Gravity Forms form. Enter lists responses; the context menu shows its feeds and "
        "results, tests it, and changes a field type."
    ),
    "fact": "A fact about the site. Enter reads it in the details pane.",
    "setting": "A setting. Alt+Enter changes it.",
    "problem": "A problem a check found. Enter reads what it means.",
    "help": "A word or key. Enter reads it in full.",
    "namespace": "A family of routes. Enter lists what it offers.",
    "route": "A route on the site. Enter reads it; Alt+Enter shows what it accepts.",
    "search_result": (
        "A result from WordPress search, with the site it came from. Enter opens it in "
        "your browser."
    ),
    "global_style": (
        "A palette colour or font size in the active block theme. Change... previews the new value."
    ),
    "model": "A post type or taxonomy. Alt+Enter shows its fields; who registered it says why.",
    "ability": "An ability the site offers. Enter runs it, after a preview.",
    "menu": (
        "A menu. Enter reads where it is shown; Ctrl+N or Add Menu Item adds to it, and "
        "Alt+Enter has its Properties, with whether new top-level pages join it by themselves."
    ),
    "pattern": "A synced pattern.",
    "font": "An installed font.",
    "mixed": "Something that needs you. Enter reads it in full.",
    "value": (
        "One value, wherever it is used. Enter lists where. Under Links, Check Every Link "
        "checks the whole site's links in the background."
    ),
    "across": "One name across sites. Alt+Enter shows its variants and the sites missing it.",
    "fleet": "One site in the fleet. Enter selects it in the tree; Alt+Enter reads each state.",
    "day": "A day with scheduled or published content. Enter lists it.",
    "update": (
        "A version on the site and whether an update waits, once Check for Updates on "
        "WordPress.org has asked. Enter opens Dashboard > Updates in your browser."
    ),
    **SWEEP_ROW_HELP,
    **DASHBOARD_ROW_HELP,
    **PLUGIN_ROW_HELP,  # shop, events and SEO rows
}
"""One sentence per row type."""


PLANNED_WORDS: dict[str, str] = {}
"""What each ``planned:`` node will hold, and where that lives today (re-exported by the tree).

Empty since Shop and Podcast read the site (workbench_shop); a new placeholder adds a row.
"""


def node_help(key: str) -> str:
    """The sentence for node *key*; a status or group child borrows its parent's."""
    if key in NODE_HELP:
        return NODE_HELP[key]
    parent = key.rsplit("_", 1)[0]
    if key.endswith("_group"):
        return NODE_HELP["group"]
    return NODE_HELP.get(parent, "")


def row_help(kind: str) -> str:
    return ROW_HELP.get(kind, ROW_HELP["fact"])
