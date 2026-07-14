"""Story Studio binder dialog (accessible wx shell over quill.core.story).

A keyboard-operable ``wx.TreeCtrl`` that shows a project's binder — the
Manuscript group with heading-derived chapters/scenes, then element groups
(Characters, Places, Plot threads, Research, Brainstorm). Activating a file,
heading, or element node opens that file (at the heading's offset) and closes
the binder; activating a group expands or collapses it.

All structure comes from :func:`quill.core.story.build_binder`; this module is
a wiring layer. ``__init__`` stores its arguments and constructs no wx objects,
so the wx-free seams (``open_target``/``activate``) are unit-tested without a
display, exactly like :class:`quill.ui.list_studio_dialog.ListStudioDialog`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.story.binder import BinderNode, build_binder
from quill.core.story.compile import compile_manuscript
from quill.core.story.model import StoryProject

# Node types that open a file when activated; the rest (root/group) just toggle.
_OPENABLE = {"manuscript", "heading", "element"}


class StoryStudioDialog:
    """Builds the binder tree and routes node activation to an open callback.

    ``on_open(path, offset)`` is called with the relative file path and an
    optional character offset (set for heading nodes) when the user activates an
    openable node. ``read_text(path) -> str`` supplies file contents for heading
    derivation; both are injected so this class stays testable without disk.
    """

    def __init__(
        self,
        wx: Any,
        *,
        project: StoryProject,
        read_text: Callable[[str], str],
        on_open: Callable[[str, int | None], None] | None = None,
        on_edit_details: Callable[[str, str], None] | None = None,
        on_compile: Callable[[str], None] | None = None,
    ) -> None:
        self._wx = wx
        self._project = project
        self._read_text = read_text
        self._on_open = on_open
        self._on_edit_details = on_edit_details
        self._on_compile = on_compile
        self._root_node = build_binder(project, read_text)
        self._element_by_id = {element.id: element for element in project.elements}
        self._tree: Any = None
        self._dialog: Any = None
        self._node_by_item: dict[Any, BinderNode] = {}

    @property
    def root_node(self) -> BinderNode:
        return self._root_node

    def open_target(self, node: BinderNode) -> tuple[str, int | None] | None:
        """Return ``(path, offset)`` for an openable node, else ``None``."""
        if node.node_type not in _OPENABLE or not node.path:
            return None
        return node.path, node.offset

    def activate(self, node: BinderNode) -> bool:
        """Handle activation. Opens the node's file and returns True (caller
        closes the binder), or returns False for a non-openable node."""
        target = self.open_target(node)
        if target is None:
            return False
        if self._on_open is not None:
            self._on_open(*target)
        return True

    def edit_details(self, node: BinderNode) -> bool:
        """Open the details form for an element node. Returns True if it applied."""
        if node.node_type != "element" or node.element_id is None:
            return False
        element = self._element_by_id.get(node.element_id)
        if element is None:
            return False
        # No handler configured means nothing applied; the caller bells instead
        # of silently reporting success (#784 review).
        if self._on_edit_details is None:
            return False
        self._on_edit_details(element.path, element.kind.value)
        return True

    def compiled_text(self) -> str:
        """Return the whole manuscript compiled in spine order (front matter stripped)."""
        return compile_manuscript(self._project, self._read_text)

    def run_compile(self) -> str:
        """Compile the manuscript and hand it to ``on_compile``; return the text."""
        text = self.compiled_text()
        if self._on_compile is not None:
            self._on_compile(text)
        return text

    # --- wx construction (no display in unit tests) -----------------------

    def populate(self, dialog: Any) -> Any:
        """Build the tree control inside ``dialog`` and return the outer sizer."""
        wx = self._wx
        self._dialog = dialog
        outer = wx.BoxSizer(wx.VERTICAL)
        heading = wx.StaticText(dialog, label="&Binder")
        outer.Add(heading, 0, wx.LEFT | wx.TOP | wx.RIGHT, 8)
        tree = wx.TreeCtrl(
            dialog,
            style=wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT | wx.TR_FULL_ROW_HIGHLIGHT,
        )
        tree.SetName("Story binder")
        self._tree = tree
        root_item = self._add_node(tree, None, self._root_node)
        tree.Expand(root_item)
        tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self._on_item_activated)
        outer.Add(tree, 1, wx.EXPAND | wx.ALL, 8)
        actions = wx.BoxSizer(wx.HORIZONTAL)
        edit_button = wx.Button(dialog, label="&Edit details...")
        edit_button.Bind(wx.EVT_BUTTON, self._on_edit_details_button)
        actions.Add(edit_button, 0, wx.RIGHT, 8)
        compile_button = wx.Button(dialog, label="&Compile manuscript...")
        compile_button.Bind(wx.EVT_BUTTON, self._on_compile_button)
        actions.Add(compile_button, 0)
        outer.Add(actions, 0, wx.LEFT | wx.BOTTOM, 8)
        dialog.SetSizer(outer)
        return outer

    def _selected_node(self) -> BinderNode | None:
        if self._tree is None:
            return None
        item = self._tree.GetSelection()
        return self._node_by_item.get(item) if item else None

    def _on_edit_details_button(self, _event: Any) -> None:
        node = self._selected_node()
        if node is None or not self.edit_details(node):
            self._wx.Bell()

    def _on_compile_button(self, _event: Any) -> None:
        # Close the binder first, then compile+open once the modal has actually
        # unwound — running on_compile under the active modal caused focus
        # churn, and this Close-only dialog must end with ID_CLOSE to honor its
        # apply_modal_ids contract (#785 review).
        if self._dialog is not None:
            self._dialog.EndModal(self._wx.ID_CLOSE)
        self._call_after(self.run_compile)

    def _call_after(self, func: Callable[..., Any], *args: Any) -> None:
        """Run ``func`` after the event loop unwinds (directly off-wx)."""
        call_after = getattr(self._wx, "CallAfter", None)
        if callable(call_after):
            call_after(func, *args)
        else:  # unit tests pass a stub wx without CallAfter
            func(*args)

    def _add_node(self, tree: Any, parent_item: Any, node: BinderNode) -> Any:
        if parent_item is None:
            item = tree.AddRoot(node.label)
        else:
            item = tree.AppendItem(parent_item, node.label)
        self._node_by_item[item] = node
        for child in node.children:
            self._add_node(tree, item, child)
        return item

    def _on_item_activated(self, event: Any) -> None:
        item = event.GetItem()
        node = self._node_by_item.get(item)
        if node is None:
            event.Skip()
            return
        if self.open_target(node) is None:
            event.Skip()  # let the tree expand/collapse a group on activation
            return
        # End the modal before opening the file: open_file may itself prompt
        # (save confirmations), and nesting that under the live binder modal
        # caused focus churn (#783 review). ID_CLOSE matches apply_modal_ids.
        if self._dialog is not None:
            self._dialog.EndModal(self._wx.ID_CLOSE)
        self._call_after(self.activate, node)
