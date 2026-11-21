"""SwiftLetter navigation through the standard Workbench tree and list."""

from __future__ import annotations

from typing import Any

from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_swiftletter import NEWSLETTER


class WorkbenchSwiftLetter:
    def swiftletter_children(self, instance: str) -> tuple[tuple[str, str], ...]:
        return getattr(self, "_swiftletter_nodes", {}).get(instance, ())

    def remember_newsletters(self, site: str, sep: str, rows: list[WbRow]) -> None:
        import wx

        old = getattr(self, "_swiftletter_nodes", {})
        children = tuple((f"{site}{sep}{row.key}", row.title) for row in rows)
        if children != old.get(site, ()):
            old[site] = children
            self._swiftletter_nodes = old
            wx.CallAfter(self._swiftletter_tree_changed)

    def _swiftletter_tree_changed(self) -> None:
        if self.frame is not None:
            self.frame.rebuild_tree()

    def do_open_newsletter(self, ref: Any, row: WbRow | None) -> None:
        from quill.ui.wordpress_workbench_window import SEP
        from quill.ui.workbench_frame import NodeRef

        if row is not None and row.kind == NEWSLETTER and self.frame is not None:
            if self.frame.select(NodeRef(ref.template, NEWSLETTER, f"{row.site}{SEP}{row.key}")):
                self.frame.tree.SetFocus()
