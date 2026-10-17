"""The tree-navigator row type shared by ``MainFrame`` and its mixins.

``_show_tree_navigator`` lists these: a label, the preview text shown beside
the tree, the payload returned when the row is chosen, the action button's
label, and child rows. It lives in its own module so a mixin can build rows
without importing ``main_frame`` (which would be circular); ``main_frame``
re-exports it under the same name.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class _NavigatorNode:
    label: str
    preview: str
    payload: object
    action_label: str
    children: list[_NavigatorNode]
