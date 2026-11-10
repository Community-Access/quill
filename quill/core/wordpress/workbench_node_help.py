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

__all__ = ["NODE_HELP", "ROW_HELP", "node_help", "row_help"]

NODE_HELP: Mapping[str, str] = {
    "start": "What the Workbench is and how to move around it.",
    "attention": "What waits on you, gathered from every connected site.",
    "inbox": "Everything below Needs My Attention, newest first, from every site.",
    "waiting": "Comments held for moderation on every site. Ctrl+Shift+A approves.",
    "pending_review": "Posts and pages by people who cannot publish, waiting for an editor.",
    "scheduled": "Posts and pages that will publish themselves, with their dates.",
    "my_drafts": "Your own drafts, on every site.",
    "updates": "WordPress, plugin, theme and translation updates waiting.",
    "health_problems": "Site Health problems on every site, worst first.",
    "accessibility": "Pictures without alt text and other accessibility findings, from every site.",
    "broken_links": "Links that lead nowhere.",
    "held_as_spam": "Comments and form entries a site doubted. Ctrl+Shift+A releases one.",
    "form_responses": "New form responses, from every site with a form plugin QUILL reads.",
    "orders": "New shop orders on sites with a shop.",
    "watches": "What you asked the Workbench to keep an eye on.",
    "sites": "Every connected site, with your role on each. Right Arrow opens one.",
    "calendar": "Every site's scheduled and published content, a day to a node.",
    "search": "One search across every site's posts, pages, media, comments and people.",
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
    "themes": "The installed themes. Activate one with its context menu.",
    "global_styles": "The site's global styles: colours, type and spacing.",
    "templates": "The block theme's templates.",
    "template_parts": "The block theme's template parts, such as the header and footer.",
    "patterns": "Synced patterns: blocks you reuse, changed in one place.",
    "fonts": "The fonts the site has installed.",
    "widgets": "The classic theme's sidebars and their widgets.",
    "forms": "The site's forms, from every form plugin QUILL reads.",
    "form_entries": "Responses to the site's forms.",
    "form_spam": "Form responses held as spam.",
    "shop": "Products, orders and customers, on a site with a shop.",
    "podcast": "Podcast episodes and the feed.",
    "people": "The people on the site and the passwords made for apps.",
    "users": "The people on the site, with their roles. Site > Roles explains each role.",
    "app_passwords": "Your application passwords on this site. Ctrl+N makes one.",
    "plugins": "The installed plugins, active and not.",
    "settings": "The site's settings the REST API can read and change.",
    "site_health": "WordPress's own checks of how well the site is set up.",
    "abilities": "What the site's Abilities API offers, each a command you can run.",
    "more": "Every family of routes on this site, by namespace, and how many are reached.",
    "more_namespace": "One namespace's routes, with their methods and where each is reached.",
    "content_model": "The site's post types and taxonomies, and who registered each, read only.",
    "group": "The rows of the list above that share one value, from View > Group By.",
}
"""One sentence per node key; status children and group nodes share their parent's."""

ROW_HELP: Mapping[str, str] = {
    "item": "A post, page or item. Enter opens it in the editor, Alt+Enter its Properties.",
    "media": "A file in the media library. Enter opens it; Alt+Enter edits its alt text.",
    "comment": "A comment. Ctrl+Shift+A approves, Ctrl+Shift+S marks it as spam.",
    "form_entry": "A form response. Enter reads it in full.",
    "term": "A category, tag or term. Enter lists its posts; Merge Into folds it into another.",
    "user": "A person on the site. Change Role and Remove are on the context menu.",
    "plugin": "A plugin. Activate or Deactivate is on the context menu.",
    "theme": "A theme. Activate is on the context menu.",
    "app_password": "An application password. Delete revokes it.",
    "site": "A connected site. Enter selects it in the tree.",
    "writing_type": "A kind of content. Enter opens its list.",
    "taxonomy": "A way of grouping. Enter opens its terms.",
    "form": "A form. Enter lists its responses.",
    "fact": "A fact about the site. Enter reads it in the details pane.",
    "setting": "A setting. Alt+Enter changes it.",
    "problem": "A problem a check found. Enter reads what it means.",
    "help": "A word or key. Enter reads it in full.",
    "namespace": "A family of routes. Enter lists what it offers.",
    "route": "A route on the site. Enter reads it; Alt+Enter shows what it accepts.",
    "model": "A post type or taxonomy. Alt+Enter shows its fields; who registered it says why.",
    "ability": "An ability the site offers. Enter runs it, after a preview.",
    "menu": "A menu. Enter reads where it is shown.",
    "template": "A template or template part.",
    "pattern": "A synced pattern.",
    "font": "An installed font.",
    "sidebar": "A sidebar and its widgets.",
    "mixed": "Something that needs you. Enter reads it in full.",
    "day": "A day with scheduled or published content. Enter lists it.",
}
"""One sentence per row type."""


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
