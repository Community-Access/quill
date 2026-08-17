"""Clearing a search field clears its results.

A results list that keeps showing matches for text that is no longer in the
field is presenting stale state as current: a screen reader user who empties
the field and arrows into the list has no visual hint that what they are
hearing belongs to a query that no longer exists. Every search surface with a
separate results list binds this, so emptying the field is always equivalent
to whatever that surface's own "start over" path does.

Surfaces that live-filter on every keystroke already behave this way for
free and do not need it.
"""

from __future__ import annotations

from collections.abc import Callable


def bind_empty_query_reset(
    query_ctrl: object, reset: Callable[[], None], *, also: tuple[object, ...] = ()
) -> None:
    """Call *reset* whenever *query_ctrl* (and every control in *also*)
    becomes empty -- the same outcome as the surface's blank-search / clear
    path, without waiting for Enter or a button press.

    *reset* must be idempotent and must not write back into the bound
    controls with ``SetValue`` (use ``ChangeValue``, which fires no event).
    """
    import wx

    controls = (query_ctrl, *also)

    def _on_text(event: object) -> None:
        event.Skip()
        if not any(str(ctrl.GetValue()).strip() for ctrl in controls):
            reset()

    for ctrl in controls:
        ctrl.Bind(wx.EVT_TEXT, _on_text)
