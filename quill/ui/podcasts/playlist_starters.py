"""Add the starter playlists, and say which ones arrived.

The rules themselves are ``core/podcasts/playlists.STARTERS``; this is the two
sentences that go with pressing the menu item, and it lives here because
``manager_dialog`` is at its GATE-11 ceiling.

**They arrive as ordinary playlists, not as built-ins.** Renaming, retuning or
deleting one works exactly the way it does for a playlist somebody wrote
themselves -- a built-in that cannot be changed is a decision imposed on
somebody's library. The cost is that pressing the item twice does nothing the
second time, which is why it says so.
"""

from __future__ import annotations

from typing import Any

__all__ = ["add_starters"]


def add_starters(dialog: Any) -> list[str]:
    """Create whichever starter playlists this library does not have."""
    from quill.core.podcasts.playlists import add_starter_playlists

    added = add_starter_playlists(dialog._library)
    if not added:
        dialog._announce("You already have all of the starter playlists.")
        return []
    dialog._on_library_changed()
    dialog.refresh_tree()
    dialog._announce(
        f"Added {len(added)} playlist{'' if len(added) == 1 else 's'}: {', '.join(added)}. "
        "You can rename or change any of them."
    )
    return added
