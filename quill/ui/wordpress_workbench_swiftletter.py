"""SwiftLetter navigation through the standard Workbench tree and list."""

from __future__ import annotations

from typing import Any

from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_swiftletter import NEWSLETTER, ROOT


class WorkbenchSwiftLetter:
    def swiftletter_children(self, instance: str) -> tuple[tuple[str, str], ...]:
        return getattr(self, "_swiftletter_nodes", {}).get(instance, ())

    def swiftletter_offered(self, key: str, context: Any) -> bool:
        """SwiftLetter is for self-hosted sites: a WordPress.com connection never shows it."""
        api = getattr(context, "api", None)
        return key != ROOT or api is None or not api.address.is_wpcom

    def remember_newsletters(self, site: str, sep: str, rows: list[WbRow], ref: Any = None) -> None:
        """Keep each site's newsletters as tree nodes; rebuild only when they changed.

        When the site said how many it has, the list's "more on the site" words say
        how many remain, in place of the usual guess (Michael's answer 12).
        Runs on the loading thread, so the shared dict is replaced whole, never
        changed in place while the tree may be reading it.
        """
        import wx

        if ref is not None and rows and "left" in rows[0].raw:
            self.cut[self.page_key(ref)] = rows[0].raw["left"]  # type: ignore[attr-defined]
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

    def open_swiftletter_row(self, row: WbRow) -> None:
        """Open in Editor on an article row: the editor's own open path, so QUILL and
        QUILL Lite share it. A site whose SwiftLetter does not offer opening says so."""
        from quill.core.wordpress.workbench_swiftletter import discovered

        profile = self.profile(row.site)  # type: ignore[attr-defined]
        if profile is None:
            self.say(f"{row.site} is no longer in your list of sites.")
            return
        offered = discovered(profile.site_url)
        if offered is not None and not offered.can_open:
            self.say(
                f"SwiftLetter on {row.site} does not offer opening articles in QUILL. "
                "Ask the site's administrator to update SwiftLetter."
            )
            return
        raw = row.raw or {}
        can_edit = raw.get("can_edit")
        self.commands.open_swiftletter(  # type: ignore[attr-defined]
            profile,
            int(row.key),
            can_edit=can_edit if isinstance(can_edit, bool) else None,
            can_save=offered is None or offered.can_save,
            newsletter_title=str(raw.get("newsletter_title") or ""),
        )

    def do_show_articles(self, ref: Any, row: WbRow | None) -> None:
        from quill.ui.wordpress_workbench_window import SEP
        from quill.ui.workbench_frame import NodeRef

        if row is None or row.kind != NEWSLETTER or self.frame is None:
            return
        if self.frame.select(NodeRef(ref.template, NEWSLETTER, f"{row.site}{SEP}{row.key}")):
            self.frame.tree.SetFocus()
        else:
            self.say(f"{row.title} is not in the tree yet. Refresh lists the newsletters again.")
