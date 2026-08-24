"""QUILL Cast's Go To: one key for every place, in the order you choose (5.2).

The machinery -- fixed numbering, a pool that protects it, ten positions
because that is where the number row ends -- is
:mod:`quill.core.go_to_menu`, shared with Quill Radio. What is here is the
part that is genuinely Cast's: **which places**.

Cast's "Go To" until now was ``podcasts.go_to_position``, which jumps to a
*time inside an episode*. A different feature with the same two words, and a
listener who went looking for the other one found it and was confused rather
than helped.

The order below is the default menu, and it is a claim about how somebody
uses a podcast app: the Podcast Manager is where nearly everything happens,
so it is 1; Continue Listening is the "carry on from where I was" answer, so
it is 2; the Play Queue and Downloads are the two lists that fill up on their
own and want checking. Preferences is on the menu rather than in the pool
because it is the destination people most often cannot find a key for.

Everything after the first ten starts pooled -- see the shared module for why
that is the protection that makes the numbering permanent.
"""

from __future__ import annotations

from pathlib import Path

from quill.core import go_to_menu
from quill.core.go_to_menu import MAX_ENTRIES, Destination, GoToLayout, position_key

__all__ = [
    "DEFAULT_ORDER",
    "DESTINATIONS",
    "MAX_ENTRIES",
    "Destination",
    "GoToLayout",
    "default_layout",
    "destination",
    "load_layout",
    "position_key",
    "refusal_for_adding",
    "refusal_for_removing",
    "repair",
    "save_layout",
]

_FILE_NAME = "cast-go-to.json"

#: Every place Go To can reach in QUILL Cast. The first ten are the default
#: menu; the rest start in the pool. Adding to this tuple is safe by
#: construction -- a new entry appears in the pool for anyone with a saved
#: layout, so nobody's numbering moves.
DESTINATIONS: tuple[Destination, ...] = (
    Destination("manager", "Podcast Manager", "open_podcast_manager", "Ctrl+M"),
    Destination("continue", "Continue Listening", "open_continue_listening"),
    Destination("queue", "Play Queue", "_open_play_queue"),
    Destination("downloads", "Downloads", "open_podcast_downloads"),
    Destination("bookmarks", "Bookmarks", "open_bookmarks", "Ctrl+Alt+Shift+J"),
    Destination("statistics", "Listening Statistics", "open_podcast_statistics"),
    Destination("add", "Add a Podcast", "_podcast_open_add_dialog"),
    Destination("notes", "Episode Notes", "add_podcast_note"),
    Destination("sleep", "Sleep Timer", "open_sleep_timer_dialog"),
    Destination("preferences", "Preferences", "_open_preferences", "Ctrl+,"),
    # -- the pool: available to add, not in the menu by default ---------------
    Destination("enhancements", "Sound Enhancements", "open_podcast_sound_enhancements"),
    Destination("skip", "Skip Settings", "open_podcast_skip_settings"),
    Destination("quick_actions", "Quick Actions", "open_podcast_quick_actions"),
    Destination("extras", "Episode Extras", "open_podcast_episode_extras"),
    Destination("shortcuts", "Keyboard Shortcuts", "open_keymap_editor"),
    Destination("sheet", "Keyboard Shortcuts Sheet", "podcast_keyboard_cheat_sheet"),
    Destination("media_tools", "Media Tools", "podcast_media_tools_status"),
)

#: The first ten, which is what a fresh install gets.
DEFAULT_ORDER: tuple[str, ...] = go_to_menu.default_order(DESTINATIONS)


def destination(destination_id: str) -> Destination | None:
    return go_to_menu.lookup(DESTINATIONS, destination_id)


def default_layout() -> GoToLayout:
    return GoToLayout(order=list(DEFAULT_ORDER), catalogue=DESTINATIONS)


def repair(layout: GoToLayout) -> GoToLayout:
    return go_to_menu.repair(GoToLayout(order=list(layout.order), catalogue=DESTINATIONS))


def refusal_for_adding(layout: GoToLayout) -> str:
    return go_to_menu.refusal_for_adding(layout)


def refusal_for_removing(layout: GoToLayout, destination_id: str) -> str:
    return go_to_menu.refusal_for_removing(layout, destination_id)


def load_layout(data_dir: Path) -> GoToLayout:
    return go_to_menu.load_layout(data_dir, file_name=_FILE_NAME, catalogue=DESTINATIONS)


def save_layout(data_dir: Path, layout: GoToLayout) -> None:
    go_to_menu.save_layout(data_dir, repair(layout), file_name=_FILE_NAME)
