"""Build a control with a label the screen reader will actually read.

On wxMSW the accessible name of a plain control -- a text field, a combo box, a
spin control, a list -- comes from the ``wx.StaticText`` **constructed immediately
before it**, in z-order. Not from ``SetName``, which sets wxWindow's own name and
which the reader never sees. Not from where a sizer happens to put the label. Not
from ``SetHelpText``, which F1 reads and nothing else does.

That single fact is behind a whole class of bug, and it is invisible in code review
because the offending code looks careful: somebody writes a thoughtful sentence,
passes it to ``SetName``, and ships a control that announces as "edit". Two fields
in Add Podcast shipped that way, while the combo box directly above them announced
correctly -- because that one had a label. When the first audit ran there were 165
of them across the tree (``quill/tools/check_control_labels.py``).

So the fix is not 165 careful edits. It is a helper that makes the correct thing the
easy thing, and a gate that notices the next one. This is the helper.

    self._speed = labelled(
        self.dialog, row, "&Speed:", lambda p: wx.SpinCtrlDouble(p, min=0.5, max=5.0),
        help="How fast episodes play, unless a podcast has its own speed.",
    )

Three things it guarantees that hand-written code keeps failing to:

1. **The label is created before the control**, always, because the helper calls the
   factory after building the label. Getting this backwards is the bug.
2. **The label and the control go into the sizer in that order**, so the visual
   order matches the z-order and a sighted user and a screen-reader user meet them
   the same way round.
3. **``SetHelpText`` is set at the construction site**, which is the only place the
   help audit can see it (help set anywhere else is ``help-elsewhere`` and proves
   nothing).

``SetName`` is deliberately *not* set. A control with both a label and a name gets
announced twice on some readers, and the label is the half that always works.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = ["label_for", "labelled"]


def labelled(
    parent: Any,
    sizer: Any,
    label: str,
    make_control: Callable[[Any], Any],
    *,
    help: str = "",  # noqa: A002 - "help" is what every caller means
    proportion: int = 1,
    border: int = 6,
    label_border: int = 6,
    expand: bool = True,
) -> Any:
    """Add ``label`` then the control it names to *sizer*, and return the control.

    *make_control* takes the parent and returns the control. A factory rather than a
    ready-made control, because the whole point is that the label must exist *first*
    -- accepting a finished control would let the caller build it in the wrong order
    and the helper could not tell.

    *label* should carry an ``&`` access key. Alt+that letter then moves focus to the
    control, which is the other thing a real label buys and ``SetName`` does not.
    """
    import wx

    static = wx.StaticText(parent, label=label)
    sizer.Add(static, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, label_border)
    control = make_control(parent)
    if help:
        control.SetHelpText(help)
    flags = wx.ALL | (wx.EXPAND if expand else 0)
    sizer.Add(control, proportion, flags, border)
    return control


def label_for(parent: Any, control_factory: Callable[[Any], Any], label: str) -> tuple[Any, Any]:
    """``(label, control)`` built in the right order, for a caller laying out itself.

    For the cases -- a grid sizer, a two-column form -- where the caller has to place
    the two halves itself. The ordering guarantee is the whole value, so the pair is
    returned already constructed rather than the caller being trusted to do it in
    order.
    """
    import wx

    static = wx.StaticText(parent, label=label)
    return (static, control_factory(parent))
