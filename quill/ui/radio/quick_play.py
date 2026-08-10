"""Quick-play the first ten favorites (Radio).

The play logic lives here so ``main_frame_radio`` keeps only the thin command
wiring under the GATE-11 size budget. wx-free: takes the favorites store,
history, player controller, and an announce callback.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def play_favorite_slot(
    slot: int,
    *,
    favorites: Any,
    history: Any,
    controller: Any,
    announce: Callable[[str], None],
) -> None:
    """Play the *slot*-th favorite (1-based) in display order.

    Announces the station played, or -- when the slot is past the end of the
    list -- how many favorites there are, so an empty quick key is never silent.
    """
    ordered = favorites.favorites_in_display_order(
        history.favorites_sort, history.folder_sort_orders
    )
    index = slot - 1
    if 0 <= index < len(ordered):
        favorite = ordered[index]
        controller.play_station(favorite.station)
        announce(f"Playing favorite {slot}: {favorite.display_label}")
    else:
        announce(f"No favorite in slot {slot}. You have {len(ordered)} favorites.")
