"""The chosen-shows list: A-Z until you move one, then exactly as you left it.

Asked for on 2026-08-25, for the ACB Media Podcasts picker: *"allow them to
move them up and down so they can organize the folder in the order they wish
with the default being sorted in A-Z order even if they add them out of order,
then if they move any keep those stuck in position"*.

Two rules that sound like one:

* **Adding never disturbs the order.** Pick "Zoom Call", then "ACB Advocacy
  Update", and the list still reads A-Z. Somebody assembling a list of forty
  shows should not have to add them alphabetically to get an alphabetical
  result -- they are choosing *what*, not *where*.
* **Moving one ends that.** The first Move Up or Move Down bakes the order you
  can currently see and keeps it, so a show you deliberately put third stays
  third even when you add five more afterwards. Re-sorting around somebody who
  has just said where they want something is the app overruling them.

The vocabulary is Favorites' own (``"az"`` / ``"manual"`` -- see
``RadioHistory.favorites_sort``), because this is the same promise the
favorites tree already makes and a listener should only have to learn it once.

Generic in what it holds: the caller supplies the sort key, so this is
testable with plain strings and knows nothing about podcasts. wx-free, pure.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from typing import Any

#: Sorted alphabetically, and re-sorted whenever something is added.
AZ = "az"
#: Left exactly as the reader arranged it.
MANUAL = "manual"


class PickList:
    """An ordered selection that sorts itself until the reader intervenes."""

    __slots__ = ("_items", "_key", "order")

    def __init__(
        self,
        key: Callable[[Any], str],
        items: Iterable[Any] = (),
        *,
        order: str = AZ,
    ) -> None:
        self._key = key
        self.order = order if order in (AZ, MANUAL) else AZ
        self._items: list[Any] = list(items)
        if self.order == AZ:
            self._sort()

    # -- reading ---------------------------------------------------------------

    @property
    def items(self) -> Sequence[Any]:
        """The chosen items, in the order they should be written out."""
        return tuple(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __contains__(self, item: Any) -> bool:
        return any(self._key(existing) == self._key(item) for existing in self._items)

    # -- changing --------------------------------------------------------------

    def add(self, item: Any) -> bool:
        """Add *item*. False when it is already chosen (never a duplicate).

        Re-sorts while the order is still A-Z, so adding out of order still
        reads in order.
        """
        if item in self:
            return False
        self._items.append(item)
        if self.order == AZ:
            self._sort()
        return True

    def add_all(self, items: Iterable[Any]) -> int:
        """Add every one not already chosen. Returns how many were new.

        The count is the point: a verb that touches many rows says how many
        (GATE-BULK-COUNT), and "Add All" on a list of forty is exactly that.
        """
        return sum(1 for item in items if self.add(item))

    def remove_at(self, index: int) -> Any:
        """Drop the item at *index* and return it, or None when out of range.

        Removing does not end A-Z: taking something out expresses no opinion
        about where the rest belong.
        """
        if not 0 <= index < len(self._items):
            return None
        return self._items.pop(index)

    def move(self, index: int, delta: int) -> int:
        """Move one item by *delta*. Returns where it ended up.

        **This is what switches the list to manual.** It happens on the first
        move rather than behind a separate "sort: manual" control, because
        somebody dragging a show to the top has already said what they want and
        should not have to say it twice.

        Clamped rather than wrapped: Move Up on the first row is a no-op, not a
        jump to the bottom -- and it still switches to manual, because the
        reader has engaged with the order either way.
        """
        if not 0 <= index < len(self._items):
            return index
        self.order = MANUAL
        target = max(0, min(len(self._items) - 1, index + delta))
        if target != index:
            self._items.insert(target, self._items.pop(index))
        return target

    def resort(self) -> None:
        """Go back to A-Z, discarding a manual arrangement. The way back."""
        self.order = AZ
        self._sort()

    # -- internals -------------------------------------------------------------

    def _sort(self) -> None:
        # casefold, not lower: the list is people-facing and may hold any
        # language ACB publishes in.
        self._items.sort(key=lambda item: self._key(item).casefold())


__all__ = ["AZ", "MANUAL", "PickList"]
