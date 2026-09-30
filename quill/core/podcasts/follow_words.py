"""Follow, not Subscribe: Cast's vocabulary for having a podcast in your library.

Jeff, 2026-09-30: "This should be changed to Follow framing as that is what is
standard now."

He is right, and the reason is worth writing down because it decides the edge
cases. **Subscribe now reads as something with a price attached.** It did not in
2005, when podcast clients borrowed the word from RSS readers and RSS readers
borrowed it from mailing lists; it does in 2026, when every subscription a listener
has is a monthly charge. QUILL is free and never sold, and the last thing its
wording should suggest is that adding a free feed costs money -- particularly to
somebody deciding whether to try the app at all. Every podcast app a listener has
touched in the last five years -- Apple, Spotify, Pocket Casts, Overcast, Earshot
-- says Follow. A listener should not have to learn Cast's dialect.

**One module, because a vocabulary that lives in fourteen string literals is one
that will be half-changed.** This is the same reason ``ACTION_FEEDBACK_LABELS``
exists and is never retyped: the menu, the Manager, the Add window, the context
menus, the announcements and the OPML report all have to say the same word, and
the way that stops being true is somebody adding a fifteenth literal.

Two things deliberately keep the old word:

* **OPML.** The format's own vocabulary is "subscription list", it is what every
  other app calls the file, and renaming it in Cast's own dialogs would make the
  file harder to recognise rather than easier. The verb changed; the file did not.
* **The on-disk field names.** ``route_to_inbox``, ``PodcastLibrary.shows`` and
  the rest are unchanged, and any settings key with "subscribe" in it stays put.
  A vocabulary change that rewrites a settings file is a migration, and a
  migration is a risk taken for a wording preference -- see principle 6.

wx-free, strict-typed, pure. Nothing here touches a library.
"""

from __future__ import annotations

__all__ = [
    "FOLLOW",
    "FOLLOWING",
    "FOLLOW_MENU",
    "UNFOLLOW",
    "UNFOLLOW_MENU",
    "followed",
    "following_count",
    "unfollow_question",
    "unfollowed",
]

#: The bare verbs, for a sentence.
FOLLOW = "Follow"
UNFOLLOW = "Unfollow"

#: The state, for a row or a status line.
FOLLOWING = "Following"

#: The menu and button labels, with their access keys. The mnemonics are chosen
#: per window, so these are the *defaults* a surface uses when nothing else in
#: that window claims the letter -- a duplicate advertises a key that may
#: silently not work (GATE-14), so a dense window overrides rather than collides.
FOLLOW_MENU = "&Follow"
UNFOLLOW_MENU = "Un&follow"


def unfollow_question(title: str) -> str:
    """The confirmation, naming the show and everything that survives it.

    Both halves are load-bearing. **The title**, because somebody arrowing
    through a list has no other way to be certain which row the question is
    about, and a bare "are you sure?" answers nothing. **What survives**, because
    "stop following" sounds as though it might delete the episodes -- so a
    listener who would happily have unfollowed cancels instead, and then has to
    go and find out.
    """
    name = (title or "").strip() or "that podcast"
    return (
        f"Stop following {name}?\n\n"
        "It leaves your library, along with your place in its episodes. Episodes "
        "you have downloaded are dealt with according to that podcast's own "
        "setting, and you can follow it again at any time."
    )


def followed(title: str, *, backfilled: int = 0) -> str:
    """What to say after following something.

    *backfilled* is named when it is not zero, because a back catalogue queueing
    itself for download is the one consequence of following a podcast that
    somebody might not want and cannot otherwise see happening.
    """
    name = (title or "").strip() or "that podcast"
    said = f"Now following {name}"
    if backfilled:
        said += (
            f"; {backfilled} back-catalogue episode"
            f"{'' if backfilled == 1 else 's'} queued for download"
        )
    return said


def unfollowed(title: str, *, deleted_files: int = 0) -> str:
    """What to say after unfollowing. Names deleted files, never silently."""
    name = (title or "").strip() or "that podcast"
    if deleted_files:
        return (
            f"No longer following {name}; {deleted_files} downloaded "
            f"episode{'' if deleted_files == 1 else 's'} deleted"
        )
    return f"No longer following {name}"


def following_count(count: int) -> str:
    """ "12 podcasts" -- the noun, for a summary line.

    The plural is spelled out rather than a bare "(s)": a screen reader reads
    "podcast(s)" aloud as "podcast open paren s close paren".
    """
    return f"{count} podcast{'' if count == 1 else 's'}"
