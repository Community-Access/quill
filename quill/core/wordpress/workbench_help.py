"""The WordPress Workbench's own words: Start Here, How WordPress Thinks, Words and Keys (Part D).

Help is built once, in the shared engine's help model
(:class:`~quill.core.workbench.help.HelpCatalogue`); this is WordPress's
catalogue of it. :data:`WORDPRESS_HELP` holds a record per glossary word and
per key of Part C, which the Help and Learning nodes list and which a test
checks against the window's menu, so a key the help teaches is one the
window answers to. The words follow D1: WordPress's own names, explained
with analogies from what people already know. Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from quill.core.wordpress.workbench_glossary import GLOSSARY, example_for
from quill.core.wordpress.workbench_help_topics import (
    ASK_ADDRESS,
    GUIDE_CHAPTERS,
    TASKS,
    WHAT_CHANGED,
)
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.help import HelpCatalogue, HelpRecord

__all__ = [
    "HOW_IT_THINKS",
    "KEYS",
    "START_HERE",
    "TOPIC_VIEWS",
    "WORDPRESS_HELP",
    "WORDS",
    "help_rows",
]

START_HERE = (
    "The WordPress Workbench is one window for your WordPress sites. The tree, where you "
    "are now, says where you are: Needs My Attention gathers what waits on every site, and "
    "Sites has each site with its posts, pages, media, comments, people, plugins and "
    "settings. The list says what is there, and the details say what the selected one is. "
    "F6 moves from pane to pane and then to the status bar. Enter does the obvious thing: "
    "on a post or page it opens it in the editor, where writing happens. The Applications "
    "key lists everything else; Alt+Enter opens Properties; Delete moves to the Trash, and "
    "Ctrl+Z puts the last change back. F1 says what any control does.\n\nNew to looking "
    "after a site? Your First Week, in the editor's Help > Tutorials, is one short lesson a "
    "day for seven days, each ending with something real on your own site and nothing done "
    "that you did not choose. The Practice Site lessons and Break It on Purpose are there "
    "too, for trying things with nothing at stake.\n\nThis is an early "
    "preview, behind a developer setting. Your Tools > WordPress windows still work."
)

HOW_IT_THINKS = (
    "How WordPress thinks. A site is posts and pages, made of blocks, dressed by a theme, "
    "extended by plugins, and run by people with roles. Posts are dated and filed under "
    "categories and tags; pages stand on their own and can sit under one another. A "
    "category is like a folder and a tag like a label in Outlook. Trash is like the "
    "Recycle Bin: things wait there until emptied. A role decides what someone may do: a "
    "Contributor writes but cannot publish, an Author publishes their own, an Editor "
    "publishes anyone's and moderates comments, and an Administrator runs the whole site."
)

WORDS = GLOSSARY
"""Every glossary word (D1), from :mod:`~quill.core.wordpress.workbench_glossary`."""

KEYS = (
    ("Enter", "The obvious thing: on a post or page, open it in the editor."),
    ("Alt+Enter", "Properties of the selection; of several, one sheet for all."),
    ("Delete", "Move to the Trash. On a user, Remove, with their posts given to someone."),
    ("Shift+Delete", "Delete permanently, after you confirm by name."),
    ("Ctrl+Z", "Undo the last WordPress change."),
    ("Ctrl+Shift+A", "Approve the selected comments; on held spam, Not Spam."),
    ("Ctrl+Shift+U", "Unapprove."),
    ("Ctrl+Shift+S", "Mark as spam."),
    ("Ctrl+Shift+M", "Reply to the selected comment."),
    ("Ctrl+Shift+P", "Publish or update the selected items."),
    ("Ctrl+Enter", "Preview on the site, in your browser."),
    ("Shift+Enter", "Open on the site, in your browser."),
    ("Ctrl+E", "The filter box. Ctrl+Shift+F, the Filter Builder."),
    ("Ctrl+1", "Needs My Attention. Ctrl+2, the current site."),
    (
        "Ctrl+Shift+1 to 9",
        "Posts, Pages, Media, Comments, Users, Plugins, Appearance, "
        "Settings and Site Health of the current site.",
    ),
    ("F6", "The next pane, then the status bar."),
    ("Alt+1", "Where you are. Alt+2, how many are selected."),
    ("Shift+F1", "What your role lets you do here."),
    ("Alt+F1", "What Is This? The WordPress word for the selected row, with your site's example."),
    ("Ctrl+F1", "The WordPress and Forms guide, at the chapter for where you are."),
    ("Ctrl+Shift+F1", "Search Help: places, commands, words and tasks."),
    ("Alt+Shift+F1", "Every key in this window."),
    ("F9", "Say the last result again. Shift+F9 explains it."),
)


WORDPRESS_HELP = HelpCatalogue([
    HelpRecord("start_here", "Start Here", START_HERE),
    HelpRecord("how_it_thinks", "How WordPress Thinks", HOW_IT_THINKS),
    *(HelpRecord(f"word.{w.casefold()}", w, m) for w, m in WORDS),
    *(HelpRecord(f"key.{k.casefold()}", k, d, keys=(k,)) for k, d in KEYS),
])
"""Every help record the Workbench shows, checked so no related link leads nowhere."""


#: The Help and Learning nodes whose rows are topics (kind ``help_topic``).
TOPIC_VIEWS = frozenset({"tasks", "guide", "changes", "ask"})

_ASK = (
    "Write to support",
    "Write to support@community-access.org from your own email. Say what you were doing and "
    "what you expected. The Workbench sends nothing, and puts no site address, user name or "
    "password in the message; leave them out of what you write too.",
)


def _topic(index: int, title: str, body: str, target: str) -> WbRow:
    return WbRow(
        "help_topic",
        "",
        str(index),
        {"title": title, "says": body},
        f"{title}: {body}",
        link=target if target.startswith("mailto:") else "",
        raw={"target": target},
    )


def _topics(what: str) -> list[WbRow]:
    if what == "tasks":
        return [
            _topic(i, title, steps, f"{template}:{key}")
            for i, (_id, title, steps, (template, key)) in enumerate(TASKS)
        ]
    if what == "guide":
        return [
            _topic(
                i,
                f"Chapter {int(number)}: {title}",
                f"Chapter {int(number)} of the WordPress and Forms guide. Enter opens it.",
                f"chapter:{number}",
            )
            for i, (number, title) in enumerate(GUIDE_CHAPTERS)
        ]
    if what == "changes":
        return [_topic(i, title, text, "") for i, (title, text) in enumerate(WHAT_CHANGED)]
    if what == "ask":
        return [_topic(0, _ASK[0], _ASK[1], ASK_ADDRESS)]
    return []


def help_rows(
    what: str,
    seen: Mapping[str, Sequence[WbRow]] | None = None,
) -> list[WbRow]:
    """A Help and Learning node's rows: words (with this site's examples), keys or topics."""
    if what in TOPIC_VIEWS:
        return _topics(what)
    if what != "words":
        return [
            WbRow("help", "", str(i), {"key": a, "does": b}, f"{a}: {b}")
            for i, (a, b) in enumerate(KEYS)
        ]
    rows = []
    for i, (word, meaning) in enumerate(WORDS):
        example = example_for(word, None, seen or {})
        said = f"{meaning} {example}".strip()
        rows.append(WbRow("help", "", str(i), {"word": word, "meaning": said}, f"{word}: {said}"))
    return rows
