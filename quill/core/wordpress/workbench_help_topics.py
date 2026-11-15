"""Help and Learning's topics for the WordPress Workbench, Search Help and Explain That (Part D).

The same help features the GitHub Workbench has, in WordPress's words
(WP-R-046): Do Something's tasks with the place each is about, The Guide's
chapters (the WordPress and Forms manual that ships with both editors),
What Changed, and Ask a Person; Search Help (Ctrl+Shift+F1) over places,
commands, words and tasks; and Explain That (Shift+F9), which says what the
last result means and what to do next. Ask a Person only ever opens a blank
message to support in the person's own email: nothing is sent, and no site
address, user name or password is put in it. Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from quill.core.wordpress.workbench_glossary import GLOSSARY

__all__ = [
    "ASK_ADDRESS",
    "GUIDE_CHAPTERS",
    "PURPOSE",
    "TASKS",
    "WHAT_CHANGED",
    "HelpHit",
    "chapter_for",
    "empty_text_for",
    "explain_result",
    "search_help",
]

PURPOSE = (
    "The WordPress Workbench: every connected WordPress site in one window, with what "
    "waits on each, everything each holds, and what you can do with it. Alt+F1 explains the "
    "WordPress word for the selected row, Ctrl+F1 opens the guide at this place's chapter, "
    "Ctrl+Shift+F1 searches the help, and Shift+F9 explains the last thing the Workbench said."
)

ASK_ADDRESS = "mailto:support@community-access.org"

#: (id, title, steps, (template, node key)): Do Something, in plain words (D12).
TASKS: tuple[tuple[str, str, str, tuple[str, str]], ...] = (
    (
        "approve",
        "Approve the comments waiting",
        "Under Needs My Attention, Comments Waiting lists every site's. Select one and press "
        "Ctrl+Shift+A to approve it, or Ctrl+Shift+S if it is spam. Ctrl+Z puts it back.",
        ("", "waiting"),
    ),
    (
        "write",
        "Write a new post",
        "Go to Posts with Ctrl+Shift+1 and press Ctrl+N. The post opens in the editor, where "
        "you write; publishing is Ctrl+Shift+P on its row.",
        ("site", "posts"),
    ),
    (
        "find_draft",
        "Finish a draft",
        "My Drafts, under Needs My Attention, lists your drafts on every site. Enter opens one "
        "in the editor.",
        ("", "my_drafts"),
    ),
    (
        "alt_text",
        "Give pictures their alt text",
        "Media > No Alt Text lists every picture a screen reader would call just 'image'. "
        "Alt+Enter on one opens its Properties, where Alt text is the first field.",
        ("site", "media_no_alt"),
    ),
    (
        "update_plugins",
        "Update plugins safely",
        "On Plugins, Check for Updates on WordPress.org marks each plugin with an update "
        "waiting and reads its changelog for the versions you skip, saying plainly when it "
        "mentions security, breaking changes or a database update. The update itself is run "
        "in Dashboard > Updates.",
        ("site", "plugins"),
    ),
    (
        "deactivate",
        "Turn off a plugin without breaking anything",
        "On Plugins, What Depends on It says which plugins need this one, which pages use its "
        "blocks or shortcodes, and which QUILL features use it. Activate or Deactivate asks the "
        "same before it changes anything, and Ctrl+Z turns it back on.",
        ("site", "plugins"),
    ),
    (
        "health",
        "Fix a Site Health problem",
        "Site Health lists every check. On a problem, Explain says what it means for visitors, "
        "what usually causes it and the steps; Fix... does what can be done from here, and "
        "Take Me There goes to the place, or the wp-admin screen, where it is fixed.",
        ("site", "site_health"),
    ),
    (
        "broken_links",
        "Fix a broken link",
        "Needs My Attention > Broken Links lists links that lead nowhere. On one, Fix... asks "
        "for the right address and changes it in the post that holds it, after a preview; "
        "Open in Editor opens that post instead.",
        ("", "broken_links"),
    ),
    (
        "add_person",
        "Add a person and choose their role",
        "On Users, Ctrl+N adds a person. Site > Roles and What They May Do (Ctrl+Alt+R) says "
        "what each role allows before you choose.",
        ("site", "users"),
    ),
    (
        "permalinks",
        "Choose how addresses look",
        "Settings explains each Permalinks choice with what your newest post's address would "
        "become. WordPress changes them in Settings > Permalinks in wp-admin.",
        ("site", "settings"),
    ),
    (
        "spam",
        "Judge what was held as spam",
        "Needs My Attention > Held as Spam lists comments and form entries the site doubted. "
        "Not Spam, Ctrl+Shift+A, lets one through.",
        ("", "held_as_spam"),
    ),
    (
        "practice",
        "Try something on the practice site",
        "Practice Site starts a WordPress on this computer where nothing is at stake. "
        "Site > Practice Site (Ctrl+Alt+P) starts, stops and resets it.",
        ("", "practice"),
    ),
    (
        "undo",
        "Take back a change",
        "Ctrl+Z puts back the last WordPress change. Edit > Change History (Ctrl+Shift+H) "
        "lists every change made in this window, and puts back any one.",
        ("", "inbox"),
    ),
)

#: (number, title) of the WordPress and Forms manual's chapters.
GUIDE_CHAPTERS: tuple[tuple[str, str], ...] = (
    ("01", "Getting started and adding your sites"),
    ("02", "A tour of the WordPress Workbench"),
    ("03", "Writing and publishing posts and pages"),
    ("04", "Blocks made plain"),
    ("05", "Pictures and the Media Library"),
    ("06", "Comments, categories, tags, people and menus"),
    ("07", "Checking before you publish"),
    ("08", "Running your site"),
    ("09", "Moving and copying content"),
    ("10", "Shop, events, SEO, memberships and redirects"),
    ("11", "Writing a form"),
    ("12", "Forms on your site, on the web and on paper"),
    ("13", "Forms in the Workbench, and Gravity Forms"),
    ("14", "QUILL Lite"),
    ("15", "Troubleshooting"),
    ("16", "Every WordPress and Forms key"),
    ("17", "WordPress Workbench reference"),
)

#: Ctrl+F1's chapter for a node, by the start of its key (the tour by default).
_CHAPTER_PREFIXES: tuple[tuple[str, str], ...] = (
    ("posts", "03"),
    ("pages", "03"),
    ("content_types", "03"),
    ("custom_type", "03"),
    ("my_drafts", "03"),
    ("scheduled", "03"),
    ("pending_review", "03"),
    ("media", "05"),
    ("comments", "06"),
    ("waiting", "06"),
    ("categories", "06"),
    ("tags", "06"),
    ("taxonomies", "06"),
    ("custom_taxonomy", "06"),
    ("menus", "06"),
    ("users", "06"),
    ("people", "06"),
    ("app_passwords", "06"),
    ("accessibility", "07"),
    ("broken_links", "07"),
    ("content_audit", "07"),
    ("by_name", "07"),
    ("site_health", "08"),
    ("health_problems", "08"),
    ("plugins", "08"),
    ("updates", "08"),
    ("settings", "08"),
    ("themes", "08"),
    ("appearance", "08"),
    ("global_styles", "08"),
    ("templates", "08"),
    ("template_parts", "08"),
    ("patterns", "08"),
    ("fonts", "08"),
    ("widgets", "08"),
    ("abilities", "08"),
    ("watches", "08"),
    ("more", "08"),
    ("across", "09"),
    ("fleet", "09"),
    ("shop", "10"),
    ("orders", "10"),
    ("events", "10"),
    ("seo", "10"),
    ("memberships", "10"),
    ("membership", "10"),
    ("redirects", "10"),
    ("not_found_log", "10"),
    ("podcast", "10"),
    ("form", "13"),
    ("held_as_spam", "13"),
    ("keys", "16"),
)

WHAT_CHANGED: tuple[tuple[str, str], ...] = (
    (
        "Help that GitHub's Workbench had",
        "Alt+F1, Ctrl+F1, Ctrl+Shift+F1, Alt+Shift+F1, F9 and Shift+F9 now answer in the "
        "WordPress Workbench too, and Help and Learning gained Do Something, The Guide, What "
        "Changed and Ask a Person.",
    ),
    (
        "A bigger glossary",
        "Words explains every WordPress word you are likely to meet, from slug and permalink "
        "to cron and oEmbed, with an example from your own site when the Workbench has read one.",
    ),
    (
        "Settings explained",
        "Settings now explains the Permalinks choices with your newest post's address, how "
        "many of your recent comments each Discussion rule would have held, what search "
        "engine visibility does and does not do, and where each plugin's own settings are "
        "documented.",
    ),
    (
        "Help where the stakes are",
        "Check for Updates reads each plugin's changelog for the versions you skip. Turning a "
        "plugin off first says what depends on it. Site Health and broken links have Explain, "
        "Fix..., Take Me There and Open in Editor.",
    ),
)


def chapter_for(key: str) -> str:
    """The manual's chapter number for a node (chapter 2, the tour, by default)."""
    for prefix, number in _CHAPTER_PREFIXES:
        if key.startswith(prefix):
            return number
    return "02"


_EMPTY: Mapping[str, str] = {
    "waiting": "No comments are waiting on any site. Nothing needs you here.",
    "my_drafts": "You have no drafts on any connected site.",
    "updates": (
        "Nothing is known to wait. WordPress's API does not say; Check for Updates on "
        "WordPress.org, on a plugin's row, asks."
    ),
    "health_problems": "No site reports a Site Health problem.",
    "broken_links": "No broken links were found. Check Every Link, under By Name > Links, "
    "looks again.",
    "held_as_spam": "Nothing is held as spam on any site.",
}


def empty_text_for(key: str) -> str:
    """The details pane's words when a node's list is empty."""
    return _EMPTY.get(
        key, "Nothing here right now. F5 loads it again; F1 says what this place holds."
    )


# -- Search Help (Ctrl+Shift+F1) ------------------------------------------------------


@dataclass(frozen=True, slots=True)
class HelpHit:
    """One Search Help result: what it is, what it says, and where Enter goes.

    *kind* is ``"node"`` (target ``"template:key"``), ``"command"`` (target a
    command id), ``"word"`` or ``"task"`` (target ``"template:key"``).
    """

    kind: str
    title: str
    body: str
    target: str = ""

    def spoken(self) -> str:
        words = {"node": "Place", "command": "Command", "word": "Word", "task": "Task"}
        return f"{words.get(self.kind, 'Topic')}: {self.title}"


def search_help(
    words: str,
    commands: Mapping[str, tuple[str, str]],
    node_labels: Mapping[str, tuple[str, str]],
    glossary: Sequence[tuple[str, str]] = GLOSSARY,
) -> list[HelpHit]:
    """Every task, place, command and word whose words hold all of *words*.

    *commands* maps a command id to its (label, key) as the window shows them;
    *node_labels* maps ``"template:key"`` to the node's (label, help).
    """
    terms = [term.casefold() for term in words.split() if term]
    if not terms:
        return []

    def matches(*texts: str) -> bool:
        joined = " ".join(texts).casefold()
        return all(term in joined for term in terms)

    hits: list[HelpHit] = []
    for _id, title, steps, (template, key) in TASKS:
        if matches(title, steps):
            hits.append(HelpHit("task", title, steps, f"{template}:{key}"))
    for ref, (label, body) in node_labels.items():
        if matches(label, body):
            hits.append(HelpHit("node", label, body, ref))
    for command_id, (label, key) in commands.items():
        if matches(label, key):
            hits.append(HelpHit("command", f"{label}, {key}" if key else label, "", command_id))
    for term, text in glossary:
        if matches(term, text):
            hits.append(HelpHit("word", term, text))
    return hits


# -- Explain That (Shift+F9) ----------------------------------------------------------

#: (how the result starts or what it holds, what it means and what to do next).
_EXPLANATIONS: tuple[tuple[str, str], ...] = (
    (
        "Nothing has happened yet",
        "The Workbench has not said anything since the window opened. F9 says the last result "
        "once there is one.",
    ),
    (
        "Connect a site first",
        "No WordPress site is connected. In the editor, File > WordPress > Connect a Site adds "
        "one; the password is kept safe by Windows, never by the Workbench.",
    ),
    (
        "Only an administrator",
        "Your role on that site does not allow it. Site > Roles and What They May Do says what "
        "yours allows; an administrator can change your role.",
    ),
    (
        "needs the role",
        "Your role on that site does not allow it. Site > Roles and What They May Do says what "
        "yours allows; an administrator can change your role.",
    ),
    (
        "Read Only",
        "Workbench Access for this site is set to Read Only, so nothing is changed from here. "
        "Site > Workbench Access (Ctrl+Alt+A) changes that, on this computer only.",
    ),
    (
        "update waiting",
        "WordPress.org has a newer version than the site. Read in Full on the row says what "
        "changed in the versions you would skip; Dashboard > Updates runs the update, because "
        "WordPress's API cannot.",
    ),
    (
        "is now inactive",
        "The plugin is off: its features stop, and its settings stay, so turning it back on "
        "restores it. Ctrl+Z turns it back on.",
    ),
    (
        "is now active",
        "The plugin is on. Ctrl+Z turns it off again.",
    ),
    (
        "Moved",
        "It is in the site's Trash, which is like the Recycle Bin: Ctrl+Z or Restore from "
        "Trash brings it back until the Trash is emptied.",
    ),
    (
        "Could not reach",
        "The site, or the address it was asked about, did not answer. Check the site opens in "
        "your browser; if it does, try again, since the host may have been busy.",
    ),
    (
        "could not reach",
        "The site, or the address it was asked about, did not answer. Check the site opens in "
        "your browser; if it does, try again, since the host may have been busy.",
    ),
    (
        "Choose ",
        "That command works on a particular kind of row. Shift+F1 lists what can be done with "
        "the row you have selected.",
    ),
    (
        "put back",
        "The change was undone on the site. Edit > Change History lists every change, and "
        "whether each can still be put back.",
    ),
)


def explain_result(text: str) -> str:
    """What the result *text* means and what you might do next ("" when nothing was said)."""
    said = (text or "").strip()
    if not said:
        return ""
    for words, explanation in _EXPLANATIONS:
        if said.startswith(words) or (not words[0].isupper() and words in said):
            return explanation
    return (
        f"The Workbench last said: {said} Shift+F1 lists what you can do with the selection, "
        "and F1 says what this place is for."
    )
