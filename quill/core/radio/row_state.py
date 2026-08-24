"""What a browse row's window already knows about a folder, without fetching.

Split from :mod:`quill.core.radio.row_actions` under GATE-11. It is the right
seam as well as a necessary one: every field here answers from rows already
loaded or from a local library read, which is the property that keeps opening
a context menu from costing a network round trip -- and stating that property
once, where the record is, is better than restating it beside each menu.

Re-exported from ``row_actions``, so no caller had to move with it.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FolderState:
    """What the window already knows about a folder, without fetching it.

    Every field answers from rows already loaded, so building a menu never
    reaches the network.
    """

    #: Playable rows already loaded under this folder.
    loaded_stations: int = 0
    #: Of those, how many can actually be saved to disk.
    savable: int = 0
    #: A podcast show, whose episodes come from a publisher's own feed.
    is_podcast_show: bool = False
    #: Already subscribed in the shared podcast library.
    subscribed: bool = False
    #: A channel the listener chose to follow (so it can be unfollowed).
    is_followed_channel: bool = False
    #: Whether the tree row is currently expanded (Open reads as Close then).
    expanded: bool = False
    #: A top-level source branch (Popular Stations, Podcasts, ...) -- the
    #: rows that can be hidden in place instead of via Choose Browse Sources.
    root_source: bool = False
    #: Unplayed episodes in this subscribed show, from the shared library
    #: (a local read). Drives Mark All as Played's enabled state: the verb
    #: is always on a subscribed show's menu, dimmed when nothing is unheard.
    unheard: int = 0
    #: Episodes the shared library holds for this subscribed show (a local
    #: read). Lets Download All Episodes appear before the branch is ever
    #: expanded -- the library already knows the list.
    library_episodes: int = 0
    #: Files sitting in this show's downloads folder on disk (a local read).
    #: Drives Remove All Downloads: always on a subscribed show's menu,
    #: dimmed when there is nothing to remove -- same rule as Mark All.
    downloaded_files: int = 0
    #: This branch is already saved in Favorites as a place (a show, a book, a
    #: channel), so the menu offers to remove it rather than to add it again.
    saved_place: bool = False
