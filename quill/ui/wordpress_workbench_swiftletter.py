"""SwiftLetter navigation through the standard Workbench tree and list."""

from __future__ import annotations

from typing import Any

from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_swiftletter import NEWSLETTER, ROOT


class WorkbenchSwiftLetter:
    def swiftletter_children(self, instance: str) -> tuple[tuple[str, str], ...]:
        return getattr(self, "_swiftletter_nodes", {}).get(instance, ())

    def remember_newsletters(self, site: str, sep: str, rows: list[WbRow]) -> None:
        """Keep each site's newsletters as tree nodes; rebuild only when they changed.

        Runs on the loading thread, so the shared dict is replaced whole, never
        changed in place while the tree may be reading it.
        """
        import wx

        old = getattr(self, "_swiftletter_nodes", {})
        children = tuple((f"{site}{sep}{row.key}", row.title) for row in rows)
        if children != old.get(site, ()):
            self._swiftletter_nodes = {**old, site: children}
            wx.CallAfter(self._swiftletter_tree_changed)

    def _swiftletter_tree_changed(self) -> None:
        frame = self.frame
        if frame is None:
            return
        current = frame.current
        frame.rebuild_tree()
        # A refresh can drop the newsletter being shown; land on SwiftLetter, not nowhere.
        if current is not None and current.key == NEWSLETTER:
            from quill.ui.wordpress_workbench_window import SEP
            from quill.ui.workbench_frame import NodeRef

            site = current.instance.split(SEP, 1)[0]
            kept = {instance for instance, _name in self.swiftletter_children(site)}
            if current.instance not in kept:
                frame.select(NodeRef(current.template, ROOT, site), remember=False)

    def do_show_articles(self, ref: Any, row: WbRow | None) -> None:
        from quill.ui.wordpress_workbench_window import SEP
        from quill.ui.workbench_frame import NodeRef

        if row is None or row.kind != NEWSLETTER or self.frame is None:
            return
        if self.frame.select(NodeRef(ref.template, NEWSLETTER, f"{row.site}{SEP}{row.key}")):
            self.frame.tree.SetFocus()
        else:
            self.say(f"{row.title} is not in the tree yet. Refresh lists the newsletters again.")
