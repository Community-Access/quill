"""The WordPress glossary, generous, with an example from the person's own site (PRD D1).

Every word D1 names, in WordPress's own spelling, explained with something
people already know: a category is like a folder, a pattern like a Word
building block, Trash like the Recycle Bin. :data:`GLOSSARY` feeds the Words
node, Alt+F1 (What Is This?) and Search Help, so the three say the same thing.

:func:`example_for` adds a sentence from the site itself when the Workbench
has already read something that shows the word: the slug of the post you are
on, how many of the loaded posts are drafts, the theme that is active. It
reads only rows already loaded (the selected row, and the rows the window
remembers per kind); it never asks the site anything. Wx-free.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

from quill.core.wordpress.workbench_rows import WbRow

__all__ = ["GLOSSARY", "ROW_TYPE_WORDS", "example_for", "meaning_of", "term_for"]

GLOSSARY: tuple[tuple[str, str], ...] = (
    # -- what a site is made of
    ("Post", "A dated piece of writing, filed under categories and tags."),
    ("Page", "A piece that stands on its own, like About or Contact; pages can nest."),
    ("Slug", "The last part of an address, such as about-us."),
    (
        "Permalink",
        "The lasting address of a post or page. Settings > Permalinks chooses its shape for "
        "the whole site.",
    ),
    ("Excerpt", "A short summary of a post, shown in lists and search results."),
    (
        "Featured image",
        "The one picture that stands for a post: themes show it at the top and in lists.",
    ),
    (
        "Block",
        "One piece of a post or page: a paragraph, a heading, a picture, a list. The block "
        "editor builds everything from blocks.",
    ),
    ("Pattern", "A ready-made group of blocks, like a building block in Word."),
    (
        "Synced pattern",
        "A pattern used in many places that changes everywhere when you change it once, like "
        "a linked picture in Word. It used to be called a reusable block.",
    ),
    ("Template", "The layout a kind of page uses, like a Word template."),
    ("Template part", "A piece every template shares, such as the header or the footer."),
    ("Theme", "The site's look: its layout, fonts and colours. One theme is active at a time."),
    (
        "Block theme",
        "A theme built from blocks, whose templates and styles you change in the Site Editor.",
    ),
    (
        "Classic theme",
        "An older kind of theme, changed with the Customizer, widgets and menus rather than "
        "the Site Editor.",
    ),
    (
        "Child theme",
        "A small theme that borrows everything from a parent theme and changes a little, so "
        "the parent's updates do not wipe out your changes.",
    ),
    (
        "Plugin",
        "An add-on that gives the site something new: a shop, forms, events, SEO. Plugins "
        "can be turned on and off.",
    ),
    ("Widget", "A small box of content in a sidebar or footer of a classic theme."),
    ("Sidebar", "An area of a classic theme that holds widgets, beside or below the content."),
    (
        "Menu location",
        "A place the theme offers for a menu, such as Primary or Footer.",
    ),
    (
        "Navigation block",
        "The block a block theme uses for its menus: the menu lives in the template itself.",
    ),
    (
        "Menu",
        "A list of links visitors use to find their way, shown in a menu location or a "
        "Navigation block.",
    ),
    # -- grouping
    ("Taxonomy", "A way of grouping things: categories and tags are two."),
    ("Category", "Like a folder for posts; categories can sit inside one another."),
    ("Tag", "Like a label in Outlook: a word many posts can share."),
    ("Term", "One entry in a taxonomy: one category, one tag, one genre."),
    ("Custom post type", "A kind of content a plugin adds, such as Events or Products."),
    ("Custom field", "An extra fact stored with an item, such as an event's date."),
    # -- the life of a post
    ("Sticky", "A post pinned to the top of the blog's list, above newer ones."),
    ("Revision", "A saved earlier version of a post or page, like a saved version in Word."),
    (
        "Autosave",
        "A copy WordPress keeps by itself while you write, so a crash loses little.",
    ),
    ("Trash", "Like the Recycle Bin: Restore brings an item back until it is emptied."),
    ("Draft", "Saved on the site but not public."),
    ("Pending review", "Written by someone who cannot publish, waiting for an editor."),
    ("Scheduled", "Will be published by itself at a set time."),
    ("Private", "Published, but only people signed in with the right role see it."),
    (
        "Password protected",
        "Published, but visitors must type the post's own password to read it.",
    ),
    ("Comment", "What a visitor writes under a post. Comments can wait for approval."),
    (
        "Pingback",
        "A note another blog sends when it links to your post, shown among comments.",
    ),
    ("Media Library", "Every picture, sound, video and document uploaded to the site."),
    (
        "Alt text",
        "Words that say what a picture shows, read by screen readers and shown if the "
        "picture cannot load. A picture without it is just 'image' to a screen reader user.",
    ),
    # -- people
    ("Role", "What someone may do on the site: Subscriber up to Administrator."),
    ("Capability", "One thing a role allows, such as publish pages."),
    (
        "Super Admin",
        "On a multisite network, the person who runs every site and the network itself.",
    ),
    ("Administrator", "Runs the whole site: plugins, themes, settings and people."),
    ("Editor", "Publishes and changes anyone's posts and pages, and moderates comments."),
    ("Author", "Writes and publishes their own posts."),
    ("Contributor", "Writes posts but cannot publish them; an editor reviews them first."),
    ("Subscriber", "Can sign in and keep a profile, and nothing more."),
    ("Application password", "A password made for one app, such as QUILL, and revocable."),
    # -- the site as a whole
    (
        "Multisite",
        "One WordPress running many sites that share plugins, themes and people.",
    ),
    ("Network", "The sites of a multisite together, run by a Super Admin."),
    ("Site Health", "WordPress's own checks of how well the site is set up."),
    (
        "REST API",
        "The way programs such as QUILL talk to the site: addresses under wp-json that "
        "read and change it, each a route.",
    ),
    ("Namespace", "A family of REST routes, usually one plugin's, such as wc/v3 for WooCommerce."),
    (
        "Ability",
        "A named job the site offers to AI assistants, such as summarise a post. Each is off "
        "in QUILL until you turn it on.",
    ),
    (
        "Shortcode",
        "A word in square brackets, such as [gallery], that a plugin turns into something "
        "on the page.",
    ),
    (
        "oEmbed",
        "Pasting a YouTube or podcast address on its own line, which WordPress turns into a "
        "player.",
    ),
    (
        "Cron",
        "WordPress's timer: the jobs it runs on a schedule, such as publishing a scheduled "
        "post. It runs when someone visits the site.",
    ),
    (
        "Cache",
        "A stored copy of a page served to the next visitor, so the site is faster. A change "
        "may not show until the cache is cleared.",
    ),
    ("Redirect", "Sends a visitor from an old address to a new one, so links keep working."),
    ("404", "The page a visitor sees when an address leads nowhere: Not Found."),
    ("Sitemap", "A list of every public address, for search engines, at wp-sitemap.xml."),
    ("Update", "A newer version of WordPress, a plugin or a theme, often with security fixes."),
    (
        "Changelog",
        "A plugin's or theme's own list of what changed in each version.",
    ),
    ("Dashboard", "wp-admin, WordPress's own web pages for running the site."),
    (
        "Search engine visibility",
        "Settings > Reading's request that search engines leave the site out. It asks; it "
        "does not hide anything or lock anyone out.",
    ),
    # -- the Workbench's own words
    ("Needs My Attention", "What waits on every connected site, gathered in one place."),
    ("Held as spam", "A comment or form entry the site doubted, kept for you to judge."),
    ("Site Set", "A named group of your sites, such as Clients, to act on together."),
    (
        "Content Model",
        "A site's own kinds of content, their fields and their groupings, as one picture.",
    ),
    (
        "Practice Site",
        "A WordPress on this computer where nothing is at stake, for learning and trying.",
    ),
    ("Change History", "Every change the Workbench made in this window; Ctrl+Z puts one back."),
    (
        "Workbench access",
        "Read Only, Organize or Full: how much this window may change on a site, on top of "
        "your role.",
    ),
)
"""Every word of D1, in WordPress's spelling, with what it means."""

_MEANINGS = {term.casefold(): meaning for term, meaning in GLOSSARY}

#: The glossary word for each row kind (What Is This? on a row, Alt+F1).
ROW_TYPE_WORDS: Mapping[str, str] = {
    "item": "Post",
    "media": "Media Library",
    "comment": "Comment",
    "user": "Role",
    "term": "Term",
    "plugin": "Plugin",
    "theme": "Theme",
    "app_password": "Application password",
    "setting": "Permalink",
    "setting_help": "Permalink",
    "problem": "Site Health",
    "update": "Update",
    "menu": "Menu",
    "pattern": "Synced pattern",
    "writing_type": "Custom post type",
    "taxonomy": "Taxonomy",
    "namespace": "Namespace",
    "route": "REST API",
    "ability": "Ability",
    "model": "Content Model",
    "site": "Site Health",
    "dashboard": "Dashboard",
    "global_style": "Block theme",
    "font": "Theme",
    "form": "Held as spam",
    "gravity_form": "Held as spam",
}

_ITEM_WORDS = {"post": "Post", "page": "Page"}
_TAXONOMY_WORDS = {"category": "Category", "post_tag": "Tag"}


def meaning_of(term: str) -> str:
    return _MEANINGS.get(term.casefold(), "")


def term_for(kind: str, row: WbRow | None = None) -> str:
    """The glossary word for a row of *kind* ("" when there is none)."""
    if row is not None and row.kind == "item":
        return _ITEM_WORDS.get(row.subkind, "Custom post type")
    if row is not None and row.kind == "term":
        return _TAXONOMY_WORDS.get(row.subkind, "Term")
    return ROW_TYPE_WORDS.get(kind, "")


# -- examples from the person's own site ----------------------------------------------

Seen = Mapping[str, Sequence[WbRow]]


def _items(seen: Seen, subkind: str = "") -> list[WbRow]:
    return [r for r in seen.get("item", ()) if not subkind or r.subkind == subkind]


def _first(rows: Sequence[WbRow]) -> WbRow | None:
    return rows[0] if rows else None


def _on(row: WbRow) -> str:
    return f"On {row.site}" if row.site else "On your site"


def _status_example(status: str, word: str) -> Callable[[WbRow | None, Seen], str]:
    def said(_row: WbRow | None, seen: Seen) -> str:
        items = _items(seen)
        found = [r for r in items if r.status == status]
        if not found:
            return ""
        verb = "is" if len(found) == 1 else "are"
        return (
            f"{_on(found[0])}, {len(found)} of the {len(items)} loaded items {verb} {word}, "
            f'such as "{found[0].title}".'
        )

    return said


def _slug(row: WbRow | None, seen: Seen) -> str:
    target = row if row is not None and row.raw.get("slug") else None
    target = target or next((r for r in _items(seen) if r.raw.get("slug")), None)
    if target is None:
        return ""
    slug = str(target.raw.get("slug"))
    return f'"{target.title}" has the slug {slug}, so its address ends with {slug}.'


def _permalink(row: WbRow | None, seen: Seen) -> str:
    target = row if row is not None and row.kind == "item" and row.link else None
    target = target or next((r for r in _items(seen) if r.link), None)
    if target is None:
        return ""
    return f'"{target.title}" lives at {target.link}.'


def _kind_title(kind: str, words: str) -> Callable[[WbRow | None, Seen], str]:
    def said(row: WbRow | None, seen: Seen) -> str:
        found = row if row is not None and row.kind == kind else _first(seen.get(kind, ()))
        if found is None:
            return ""
        return f'{_on(found)}, "{found.title}" is {words}.'

    return said


def _subkind_title(subkind: str, words: str) -> Callable[[WbRow | None, Seen], str]:
    def said(row: WbRow | None, seen: Seen) -> str:
        if row is not None and row.kind == "item" and row.subkind == subkind:
            found: WbRow | None = row
        else:
            found = _first(_items(seen, subkind))
        if found is None:
            return ""
        return f'{_on(found)}, "{found.title}" is {words}.'

    return said


def _term(taxonomy: str, words: str) -> Callable[[WbRow | None, Seen], str]:
    def said(row: WbRow | None, seen: Seen) -> str:
        terms = [r for r in seen.get("term", ()) if r.subkind == taxonomy]
        if row is not None and row.kind == "term" and row.subkind == taxonomy:
            terms = [row]
        if not terms:
            return ""
        count = terms[0].cell("count")
        held = f", holding {count} post{'s' if count != '1' else ''}" if count else ""
        return f'{_on(terms[0])}, "{terms[0].title}" is {words}{held}.'

    return said


def _active_theme(_row: WbRow | None, seen: Seen) -> str:
    active = next((r for r in seen.get("theme", ()) if r.status == "active"), None)
    return f"{_on(active)}, {active.title} is the active theme." if active else ""


def _plugins(_row: WbRow | None, seen: Seen) -> str:
    plugins = list(seen.get("plugin", ()))
    if not plugins:
        return ""
    on = sum(1 for r in plugins if r.status in ("active", "network-active"))
    return f"{_on(plugins[0])}, {on} of {len(plugins)} plugins are on, such as {plugins[0].title}."


def _alt(_row: WbRow | None, seen: Seen) -> str:
    pictures = [r for r in seen.get("media", ()) if r.subkind == "image"]
    missing = [r for r in pictures if r.cell("alt_text") in ("", "none")]
    if not pictures:
        return ""
    if not missing:
        return f"{_on(pictures[0])}, every one of the {len(pictures)} loaded pictures has alt text."
    return (
        f"{_on(missing[0])}, {len(missing)} of {len(pictures)} loaded pictures have none, "
        f'such as "{missing[0].title}".'
    )


def _role_of(role: str) -> Callable[[WbRow | None, Seen], str]:
    def said(_row: WbRow | None, seen: Seen) -> str:
        people = [r for r in seen.get("user", ()) if r.cell("role").casefold() == role.casefold()]
        if not people:
            return ""
        article = "an" if role[0] in "AEIOU" else "a"
        return f"{_on(people[0])}, {people[0].title} is {article} {role}."

    return said


def _comments_held(_row: WbRow | None, seen: Seen) -> str:
    held = [r for r in seen.get("comment", ()) if r.status == "spam"]
    if not held:
        return ""
    return f"{_on(held[0])}, {len(held)} loaded comment{'s are' if len(held) != 1 else ' is'} spam."


def _sticky(_row: WbRow | None, seen: Seen) -> str:
    found = next((r for r in _items(seen, "post") if r.raw.get("sticky")), None)
    return f'{_on(found)}, "{found.title}" is sticky.' if found else ""


def _password(_row: WbRow | None, seen: Seen) -> str:
    found = next((r for r in _items(seen) if r.raw.get("password")), None)
    return f'{_on(found)}, "{found.title}" needs a password.' if found else ""


def _featured(_row: WbRow | None, seen: Seen) -> str:
    found = next((r for r in _items(seen) if int(r.raw.get("featured_media") or 0)), None)
    return f'{_on(found)}, "{found.title}" has a featured image.' if found else ""


def _app_passwords(_row: WbRow | None, seen: Seen) -> str:
    found = list(seen.get("app_password", ()))
    if not found:
        return ""
    return f"{_on(found[0])}, you have {len(found)}, such as {found[0].title}."


_EXAMPLES: Mapping[str, Callable[[WbRow | None, Seen], str]] = {
    "post": _subkind_title("post", "a post"),
    "page": _subkind_title("page", "a page"),
    "slug": _slug,
    "permalink": _permalink,
    "featured image": _featured,
    "theme": _active_theme,
    "plugin": _plugins,
    "category": _term("category", "a category"),
    "tag": _term("post_tag", "a tag"),
    "draft": _status_example("draft", "still in draft"),
    "pending review": _status_example("pending", "waiting for review"),
    "scheduled": _status_example("future", "scheduled"),
    "private": _status_example("private", "private"),
    "trash": _status_example("trash", "in the Trash"),
    "sticky": _sticky,
    "password protected": _password,
    "alt text": _alt,
    "media library": _alt,
    "menu": _kind_title("menu", "a menu"),
    "synced pattern": _kind_title("pattern", "a synced pattern"),
    "pattern": _kind_title("pattern", "a synced pattern"),
    "held as spam": _comments_held,
    "application password": _app_passwords,
    "administrator": _role_of("Administrator"),
    "editor": _role_of("Editor"),
    "author": _role_of("Author"),
    "contributor": _role_of("Contributor"),
    "subscriber": _role_of("Subscriber"),
}


def example_for(term: str, row: WbRow | None, seen: Seen) -> str:
    """A sentence showing *term* on the person's own site ("" when nothing loaded shows it)."""
    said = _EXAMPLES.get(term.casefold())
    if said is None:
        return ""
    try:
        return said(row, seen)
    except (TypeError, ValueError, AttributeError):
        return ""
