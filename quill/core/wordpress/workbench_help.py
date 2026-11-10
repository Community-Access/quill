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

from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.help import HelpCatalogue, HelpRecord

__all__ = ["HOW_IT_THINKS", "KEYS", "START_HERE", "WORDPRESS_HELP", "WORDS", "help_rows"]

START_HERE = (
    "The WordPress Workbench is one window for your WordPress sites. The tree, where you "
    "are now, says where you are: Needs My Attention gathers what waits on every site, and "
    "Sites has each site with its posts, pages, media, comments, people, plugins and "
    "settings. The list says what is there, and the details say what the selected one is. "
    "F6 moves from pane to pane and then to the status bar. Enter does the obvious thing: "
    "on a post or page it opens it in the editor, where writing happens. The Applications "
    "key lists everything else; Alt+Enter opens Properties; Delete moves to the Trash, and "
    "Ctrl+Z puts the last change back. F1 says what any control does.\n\nThis is an early "
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

WORDS = (
    ("Post", "A dated piece of writing, filed under categories and tags."),
    ("Page", "A piece that stands on its own, like About or Contact; pages can nest."),
    ("Slug", "The last part of an address, such as about-us."),
    ("Draft", "Saved on the site but not public."),
    ("Pending review", "Written by someone who cannot publish, waiting for an editor."),
    ("Scheduled", "Will be published by itself at a set time."),
    ("Private", "Published, but only people signed in with the right role see it."),
    ("Trash", "Like the Recycle Bin: Restore brings an item back until it is emptied."),
    ("Category", "Like a folder for posts; categories can sit inside one another."),
    ("Tag", "Like a label in Outlook: a word many posts can share."),
    ("Taxonomy", "A way of grouping things: categories and tags are two."),
    ("Custom post type", "A kind of content a plugin adds, such as Events or Products."),
    ("Custom field", "An extra fact stored with an item, such as an event's date."),
    ("Role", "What someone may do on the site: Subscriber up to Administrator."),
    ("Capability", "One thing a role allows, such as publish pages."),
    ("Application password", "A password made for one app, such as QUILL, and revocable."),
    ("Held as spam", "A comment or form entry the site doubted, kept for you to judge."),
    ("Site Health", "WordPress's own checks of how well the site is set up."),
)

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
)


WORDPRESS_HELP = HelpCatalogue([
    HelpRecord("start_here", "Start Here", START_HERE),
    HelpRecord("how_it_thinks", "How WordPress Thinks", HOW_IT_THINKS),
    *(HelpRecord(f"word.{w.casefold()}", w, m) for w, m in WORDS),
    *(HelpRecord(f"key.{k.casefold()}", k, d, keys=(k,)) for k, d in KEYS),
])
"""Every help record the Workbench shows, checked so no related link leads nowhere."""


def help_rows(what: str) -> list[WbRow]:
    """The Words or Keys node's rows."""
    pairs = WORDS if what == "words" else KEYS
    first, second = ("word", "meaning") if what == "words" else ("key", "does")
    return [
        WbRow("help", "", str(i), {first: a, second: b}, f"{a}: {b}")
        for i, (a, b) in enumerate(pairs)
    ]
