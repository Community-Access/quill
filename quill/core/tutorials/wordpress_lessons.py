"""Seven WordPress lessons, the same in QUILL and QUILL Lite.

Both editors reach WordPress through one table (``quill/core/wordpress/menu.py``)
and one set of handlers (``quill/ui/wordpress_commands.py``), so the lessons are
written once. Each editor passes a function that turns a WordPress row's short
name (``"open"``) into its own command id, its Save command, and its name, and
the lessons render whatever key the person has bound.

The examples are the QUILL WordPress Test Site (docs/qa/wordpress-regression-
testing.md): its welcome post, its draft full of things to check, its pictures
and its three comments. Somebody practising on their own site uses their own
pages wherever a lesson names one. No lesson ever holds a password: it says
where an application password comes from, and nothing more.

The WordPress key layer is taught from
:data:`quill.core.wordpress.menu.LAYER_KEYS`, the one table both editors'
keymaps are built from: a step's literal key is that table's letter, written
the way the keymap writes a layer chord, so once the live binding renders it
is the same string and the step shows it once.

The wording follows :mod:`quill.core.tutorials.model`: one action a step, the
reason as well as the instruction, what you should hear, and no key promised in
prose.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.tutorials.model import Step, Tutorial
from quill.core.wordpress.menu import LAYER_KEYS, all_rows

__all__ = ["LAYER", "SITE_ADDRESS", "layer_keys", "layer_table", "wordpress_lessons"]

#: The chord that starts the WordPress key layer.
LAYER = "Ctrl+Alt+Shift+Grave"

#: The test site every lesson uses as its example.
SITE_ADDRESS = "https://lp.csedesigns.com/wordpress/"
SITE_NAME = "QUILL WordPress Test Site"
WELCOME_ADDRESS = "https://lp.csedesigns.com/wordpress/welcome/"


def layer_keys(name: str) -> tuple[str, ...]:
    """The layer chord for the WordPress row *name* (``"open"``), or ``()``.

    Read from :data:`~quill.core.wordpress.menu.LAYER_KEYS`, so a lesson can
    only ever teach the letter the layer actually has.
    """
    command_id = f"wordpress.{name}"
    for letter, owner in LAYER_KEYS.items():
        if owner == command_id:
            return (f"{LAYER}, {letter}",)
    return ()


def layer_table() -> str:
    """Every layer letter and its command, as one sentence for a lesson."""
    titles = {row[0]: row[1].replace("&", "").removesuffix("...") for _path, row in all_rows()}
    parts = [f"{letter} {titles[owner]}" for letter, owner in LAYER_KEYS.items()]
    return "The whole layer: " + ", ".join(parts) + "."


def wordpress_lessons(
    command: Callable[[str], str],
    *,
    save: str,
    track: str,
    surfaces: tuple[str, ...],
    app: str,
) -> tuple[Tutorial, ...]:
    """The seven lessons: three here, four in :mod:`wordpress_lessons_more`.

    *command* maps a row's short name in ``wordpress/menu.py`` (``"publish"``)
    to this editor's command id; *save* is the editor's own Save command; *app*
    is the editor's name as its lessons say it.
    """
    from quill.core.tutorials.wordpress_lessons_more import later_wordpress_lessons

    return (
        Tutorial(
            slug="wordpress-connect",
            title="Connect your WordPress site",
            track=track,
            minutes=5,
            surfaces=surfaces,
            summary=(
                f"Connect {app} to a WordPress site with an application password, "
                "hear which role you have there, and learn the WordPress keys."
            ),
            steps=(
                Step(
                    title="Know what you need first",
                    body=(
                        "You need three things: the site's address, your WordPress "
                        "username, and an application password. An application "
                        "password is a separate password WordPress makes for one app. "
                        "It is not the password you sign in with, and you can take it "
                        "away again at any time."
                    ),
                    note=(
                        "These lessons use the QUILL WordPress Test Site, at "
                        f"{SITE_ADDRESS}, as the example. On your own site, use your "
                        "own pages wherever a lesson names one."
                    ),
                ),
                Step(
                    title="Open Connect a Site",
                    body=(
                        "In the File menu, open WordPress and choose Connect a Site. "
                        "It is a short form, and nothing is saved until the site has "
                        "said yes."
                    ),
                    command=command("connect"),
                    keys=layer_keys("connect"),
                    hear="The Connect a WordPress Site dialog, on Kind of site.",
                ),
                Step(
                    title="Type the site's address",
                    body=(
                        "Leave Kind of site on My own WordPress site. Tab to Site "
                        f"address and type it, for example {SITE_ADDRESS}. {app} only "
                        "connects over HTTPS, so your password never travels in the "
                        "clear."
                    ),
                    hear="Site address, edit, and the letters as you type them.",
                ),
                Step(
                    title="Get the password with your browser",
                    body=(
                        "Press Get Password with My Browser. Your browser opens the "
                        "site's own approval page. Sign in there if it asks, then "
                        f"choose Approve. On a newer site the password comes back to "
                        f"{app} by itself."
                    ),
                    hear=f'"Connected to {SITE_NAME} as" and your role, such as Editor.',
                    note=(
                        "On an older site, WordPress shows you the password instead. "
                        "Copy it, come back, and paste it into the box that is waiting "
                        "for it."
                    ),
                ),
                Step(
                    title="Or paste one from your profile",
                    body=(
                        "If you would rather do it by hand, make an application "
                        "password in your WordPress profile, under Application "
                        "Passwords, and copy it. Type your username, paste the "
                        "password into Application password, and press Connect."
                    ),
                    hear=f'"Connected to {SITE_NAME} as" and your role.',
                    note=(
                        "Your password is kept in Windows' own Credential Manager, "
                        "never in a settings file. Never paste it into an email or a "
                        "chat."
                    ),
                ),
                Step(
                    title="Choose which site comes first",
                    body=(
                        "With more than one site, Switch Site, in File, WordPress, "
                        "chooses your default. New and Open start there, and a "
                        "document always stays with the site it came from."
                    ),
                    command=command("switch_site"),
                    keys=layer_keys("switch_site"),
                    hear='"Default site:" and its name, or that it is your only site.',
                ),
                Step(
                    title="Learn the WordPress keys",
                    body=(
                        "The WordPress key layer gives the commands one letter each. "
                        "Press the layer key, let go, then press a letter. The six you "
                        "will use most are O for "
                        "Open Page or Post, P for Publish or Update, M for Media "
                        "Library, S for Switch Site, W for Open by Web Address, or D "
                        "for Save Draft to Site. Escape leaves the layer without "
                        "doing anything."
                    ),
                    keys=(f"{LAYER}, then a letter",),
                    hear="Whatever the letter runs. After Escape, nothing at all.",
                    note=layer_table()
                    + " Every WordPress command is also in the Command Palette: type "
                    "WordPress, or part of the command's name.",
                ),
            ),
            closing=(
                "You are connected, and the site has told you what your account may "
                "do. Next, write something and send it."
            ),
            then=("wordpress-write-and-publish",),
        ),
        Tutorial(
            slug="wordpress-write-and-publish",
            title="Write a post and publish it",
            track=track,
            minutes=6,
            surfaces=surfaces,
            summary=(
                "Start a new post, write it in the editor you already know, keep it "
                "on your computer, send it as a draft, and then publish it."
            ),
            steps=(
                Step(
                    title="Start a new post",
                    body=(
                        "In the File menu, open WordPress and choose New Post. A post "
                        "is a dated article, the kind that goes in a blog or a news "
                        "list. A page is the lasting kind, like About or Contact."
                    ),
                    command=command("new_post"),
                    keys=layer_keys("new_post"),
                    hear="The New Post dialog, on Site, with your default site chosen.",
                ),
                Step(
                    title="Give it a title and a format",
                    body=(
                        "Tab to Title and type one. The slug, which is the end of the "
                        "web address, fills itself in as you type. Choose Markdown or "
                        "HTML under Write in, check a category or two, and press "
                        "Create."
                    ),
                    hear=(
                        '"New post for" the site, and that nothing is sent until you '
                        "choose Save Draft to Site or Publish."
                    ),
                    note=(
                        "Markdown is the easier one to write by ear. The format cannot "
                        "change later."
                    ),
                ),
                Step(
                    title="Write, and save on this computer",
                    body=(
                        "Write a few sentences the way you write anything else. Find, "
                        "spelling and dictation all work here. Save as you always do: "
                        "it keeps the post on this computer and sends nothing."
                    ),
                    command=save,
                    hear="The usual saved message. The site has not changed.",
                ),
                Step(
                    title="Send it as a draft",
                    body=(
                        "Save Draft to Site, in File, WordPress, puts your post on the "
                        "site where only you and your editors can see it. It is the "
                        "safe way to see how it looks before anybody else does."
                    ),
                    command=command("save_draft"),
                    keys=layer_keys("save_draft"),
                    hear=f'"Draft saved to {SITE_NAME}. It is not public."',
                ),
                Step(
                    title="Publish it",
                    body=(
                        "Choose Publish or Update. Before anything goes, a question "
                        "names the post and the site, and says what Check Before "
                        "Publishing found. Press Publish if you are happy, or Escape "
                        "to stop."
                    ),
                    command=command("publish"),
                    keys=layer_keys("publish"),
                    hear=(
                        '"Publish on" the site, the title, and "Ready to publish: no '
                        'problems found", or how many things there are to look at.'
                    ),
                    note=(
                        "If your role cannot publish, the same command sends the post "
                        "for review instead, and says so."
                    ),
                ),
                Step(
                    title="Hear where it went",
                    body=(
                        "Once it is published, the post's web address is put on the "
                        "clipboard, ready to paste into an email. Open on Site, in "
                        "File, WordPress, opens it in your browser if you want to hear "
                        "it the way a visitor will."
                    ),
                    command=command("open_on_site"),
                    keys=layer_keys("open_on_site"),
                    hear=f'"Published on {SITE_NAME}. The address is on the clipboard."',
                ),
            ),
            closing=(
                "Saving keeps it here, Save Draft to Site sends it quietly, and Publish "
                "asks first. Closing a document never publishes anything."
            ),
            then=("wordpress-open-by-address", "wordpress-check"),
        ),
        Tutorial(
            slug="wordpress-open-by-address",
            title="Open a page by its address and fix a sentence",
            track=track,
            minutes=5,
            surfaces=surfaces,
            summary=(
                "Open a post you found in your browser straight from its web "
                "address, change one sentence, and send the change back."
            ),
            steps=(
                Step(
                    title="Copy the address",
                    body=(
                        "In your browser, copy the address of the post you want to "
                        "change. On the test site, use the welcome post, at "
                        f"{WELCOME_ADDRESS}. Copy it from the address bar."
                    ),
                    hear="Your browser's own word that the address was copied, if it says one.",
                ),
                Step(
                    title="Open it by its address",
                    body=(
                        "Choose Open by Web Address, in File, WordPress. When there is "
                        "an address on the clipboard it is used straight away; when "
                        "there is not, a box asks you for one."
                    ),
                    command=command("open_by_address"),
                    keys=layer_keys("open_by_address"),
                    hear="Open Welcome to the test site, and the Open as list.",
                ),
                Step(
                    title="Open it as Markdown",
                    body=(
                        "Choose Markdown. It reads more easily than HTML, and anything "
                        "Markdown cannot show is kept exactly on a short line of its "
                        "own, so nothing on the page is lost."
                    ),
                    hear=f'"Opened Welcome to the test site from {SITE_NAME}."',
                ),
                Step(
                    title="Fix one sentence",
                    body=(
                        "Find the sentence that says Open me by web address, and "
                        "rewrite it in your own words. Arrow over it first if you like; "
                        "this is an ordinary document now."
                    ),
                    hear="Your new sentence, read back as you arrow over it.",
                ),
                Step(
                    title="Send the change",
                    body=(
                        "Choose Publish or Update. A post that is already public is "
                        "updated rather than published again, and the question says "
                        "Update. Press Update."
                    ),
                    command=command("publish"),
                    keys=layer_keys("publish"),
                    hear=f'"Update on {SITE_NAME}", then "Published on {SITE_NAME}."',
                    note=(
                        "If somebody changed the post on the site after you opened it, "
                        "nothing is sent. You are told what changed, and offered "
                        "Compare the two, Open the site's copy, or Send mine anyway."
                    ),
                ),
            ),
            closing=(
                "Any address on one of your sites opens this way. Next time, try "
                "Open Page or Post for a page you know by name rather than by address."
            ),
            then=("wordpress-versions",),
        ),
    ) + later_wordpress_lessons(command, track=track, surfaces=surfaces, app=app)
