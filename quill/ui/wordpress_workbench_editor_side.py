"""The editor's two ways into the WordPress Workbench (PRD 14), and the provider half of each.

- **This Post in the Workbench** (File > WordPress, both editors): the
  Workbench opens on the list the document's post belongs to -- Posts, Pages,
  or the site's own content type -- and selects that post, so its
  Properties, revisions and comments are one key away. A post past the rows
  loaded is searched for by its title, once.
- **Picking mode** (Insert > Picture from the Media Library): the Workbench
  opens on the document site's Media; Enter on a file inserts it at the
  caret, through the same picture dialog as before, and the editor comes
  back to the front. Picking ends after one insert, or when the Workbench
  closes.

:func:`open_on_document` and :func:`open_for_picking` are what the shared
:class:`~quill.ui.wordpress_commands.WordPressCommands` calls, so QUILL and
QUILL Lite reach the same code. :class:`WorkbenchEditorSide` is the provider
mixin. Wx is only reached through the frame.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from quill.core.wordpress.site import kind_route
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_tree import DYNAMIC_TYPE
from quill.core.wordpress.workbench_window_menu import command

__all__ = ["WorkbenchEditorSide", "open_for_picking", "open_on_document"]

_INSERT = command("insert_picked")
_MEDIA_DEFAULT = command("open_on_site")


@dataclass
class _Wanted:
    """The post This Post in the Workbench is looking for."""

    site: str
    route: str
    title: str
    searched: bool = False


@dataclass
class _Picking:
    """Insert from the Media Library, waiting for Enter on a file."""

    site: str
    document: str
    insert: Callable[[WbRow], None]


def _node_for(kind: str) -> str:
    return {"post": "posts", "page": "pages"}.get(kind, DYNAMIC_TYPE)


class WorkbenchEditorSide:
    """This Post in the Workbench and the Media Library's picking mode, for the provider."""

    frame: Any
    say: Callable[[str], None]
    _profiles: dict[str, Any]
    split: Callable[[str], tuple[str, str]]
    site_of: Callable[[Any], str]

    def _editor_side(self) -> None:
        if not hasattr(self, "_wanted"):
            self._wanted: _Wanted | None = None
            self._wanted_ref: Any = None
            self._picking: _Picking | None = None

    def site_for_profile(self, profile_id: str) -> str:
        """The Workbench's name for the connected site with *profile_id* ("" when none)."""
        return next((n for n, p in self._profiles.items() if p.id == profile_id), "")

    # -- This Post in the Workbench ----------------------------------------------------

    def go_to_item(self, site: str, kind: str, item_id: int, title: str) -> None:
        """Select the list *kind* lives in on *site*, then the item in it, once it loads."""
        from quill.ui.workbench_frame import NodeRef

        self._editor_side()
        node = _node_for(kind)
        sep = "\x1f"  # the provider's SEP, between a site and a dynamic node's kind
        instance = f"{site}{sep}{kind}" if node == DYNAMIC_TYPE else site
        ref = NodeRef("site", node, instance)
        self._wanted = _Wanted(site, f"{kind_route(kind)}/{item_id}", title)
        self._wanted_ref = ref
        self.after_discovery()

    def after_discovery(self) -> None:
        """Select the node waited on, once its site's content types are known."""
        self._editor_side()
        ref = self._wanted_ref
        if ref is None or self.frame is None:
            return
        if self.frame.select(ref):
            self._wanted_ref = None
            return
        if self.split(ref.instance)[0] not in getattr(self, "_types", {}):
            return  # a content type's node appears once its site's discovery is done
        self._wanted_ref = None
        wanted, self._wanted = self._wanted, None
        if wanted is not None:
            self.say(
                f"{wanted.site} does not show this document's content type in its REST "
                f"index, so {wanted.title} has no list here."
            )

    def after_fill(self, frame: Any) -> None:
        """After a list fills: select the post This Post in the Workbench is looking for."""
        self._editor_side()
        wanted = self._wanted
        if wanted is None or frame.current is None or self.site_of(frame.current) != wanted.site:
            return
        for index, row in enumerate(frame.rows):
            if isinstance(row, WbRow) and row.route == wanted.route:
                self._wanted = None
                frame.focus_row(index)
                frame.details.ChangeValue(row.detail)
                frame.list.SetFocus()
                return
        if frame.loading:
            return
        if not wanted.searched and wanted.title:
            wanted.searched = True
            frame.filter.ChangeValue(wanted.title)
            frame.apply_filter()
            return
        self._wanted = None
        self.say(
            f"{wanted.title} is not in this list on {wanted.site}. It may have been deleted, "
            "or be in a status this list does not show."
        )

    # -- picking mode --------------------------------------------------------------------

    def start_picking(self, site: str, document: str, insert: Callable[[WbRow], None]) -> None:
        self._editor_side()
        self._picking = _Picking(site, document, insert)

    @property
    def picking(self) -> bool:
        self._editor_side()
        return self._picking is not None

    def picked_command(self, command_id: str, row: WbRow | None) -> str:
        """In picking mode Enter on a file (its default, View or Play) inserts it instead."""
        media = row is not None and row.kind == "media"
        if self.picking and media and command_id == _MEDIA_DEFAULT:
            return _INSERT
        return command_id

    def do_insert_picked(self, _ref: Any, row: WbRow | None) -> None:
        self._editor_side()
        picking = self._picking
        if picking is None:
            self.say(
                "Insert into the Document works after Insert > Picture from the Media Library "
                "opens the Workbench; then Enter on a file inserts it."
            )
            return
        if row is None or row.kind != "media":
            self.say("Choose a file in Media to insert.")
            return
        if row.site != picking.site:
            self.say(
                f"That file is on {row.site}, and {picking.document} is on {picking.site}. "
                f"Choose a file in {picking.site}'s Media."
            )
            return
        self._picking = None
        picking.insert(row)

    def end_picking(self) -> None:
        self._editor_side()
        self._picking = None


# -- what the editor calls ------------------------------------------------------------


def _open(commands: Any, site_ref: str = "") -> Any:
    from quill.ui.wordpress_workbench_window import open_workbench

    return open_workbench(
        commands,
        node=site_ref,
        announce=commands.host.announce,
        safe_mode=os.environ.get("QUILL_SAFE_MODE", "") == "1",
        data_dir=getattr(commands, "_data_dir", None),
    )


def open_on_document(commands: Any, copy: Any, profile: Any) -> bool:
    """Open the Workbench on the post *copy* came from; False (and said why) when it has none."""
    if not copy.remote_id:
        commands.host.announce(
            f"{copy.title or 'This document'} is not on {profile.name} yet, so the Workbench has "
            "no post to show. Save Draft to Site sends it first."
        )
        return False
    frame = _open(commands, _node_for(copy.kind) if copy.kind in ("post", "page") else "")
    provider = frame.provider
    site = provider.site_for_profile(profile.id)
    if not site:
        commands.host.announce(f"{profile.name} is not among the Workbench's sites.")
        return False
    provider.go_to_item(site, copy.kind, int(copy.remote_id), copy.title)
    return True


def open_for_picking(
    commands: Any, copy: Any, profile: Any, insert: Callable[[WbRow], None]
) -> bool:
    """Open the Workbench on *profile*'s Media in picking mode; False when it cannot."""
    from quill.ui.workbench_frame import NodeRef

    frame = _open(commands, "media")
    provider = frame.provider
    site = provider.site_for_profile(profile.id)
    if not site:
        commands.host.announce(f"{profile.name} is not among the Workbench's sites.")
        return False
    document = copy.title or "the document"
    provider.start_picking(site, document, insert)
    frame.select(NodeRef("site", "media", site))
    commands.host.announce(f"Picking a file for {document}: Enter on a file inserts it.")
    return True
