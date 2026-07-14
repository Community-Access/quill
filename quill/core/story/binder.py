"""Binder-tree assembly (wx-free).

The binder is the navigable home of a project: a tree of groups, manuscript
files, heading-derived chapters/scenes, and element references. It is *derived*
from the project plus file contents, never stored, so it can never drift from
the prose. File contents are supplied by an injected ``read_text`` callable
(keyed by relative path), keeping this module pure and trivially testable.

A UI renders :class:`BinderNode` into a ``wx.TreeCtrl`` (or any tree control);
the node types tell it what each row is and how to open it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from quill.core.story.manuscript import Heading, iter_headings
from quill.core.story.model import ElementKind, StoryProject

__all__ = ["BinderNode", "build_binder"]

#: Element kinds in reading order, with the group label each appears under.
_GROUP_ORDER: tuple[tuple[ElementKind, str], ...] = (
    (ElementKind.CHARACTER, "Characters"),
    (ElementKind.LOCATION, "Places"),
    (ElementKind.PLOT, "Plot threads"),
    (ElementKind.RESEARCH, "Research"),
    (ElementKind.BRAINSTORM, "Brainstorm"),
)


@dataclass(frozen=True, slots=True)
class BinderNode:
    """One row in the binder tree.

    ``node_type`` is one of ``root``, ``group``, ``manuscript``, ``heading``,
    or ``element``. ``path`` is the relative file a node opens (manuscript,
    heading, element); ``offset``/``level`` describe a heading; ``element_id``
    links an element node back to its :class:`StoryElement`.
    """

    label: str
    node_type: str
    path: str | None = None
    offset: int | None = None
    level: int | None = None
    element_id: str | None = None
    children: tuple[BinderNode, ...] = ()


def build_binder(project: StoryProject, read_text: Callable[[str], str]) -> BinderNode:
    """Assemble the binder tree for ``project``, reading files via ``read_text``."""
    children: list[BinderNode] = [_manuscript_group(project, read_text)]
    for kind, label in _GROUP_ORDER:
        members = [element for element in project.elements if element.kind is kind]
        if not members:
            continue
        children.append(
            BinderNode(
                label=label,
                node_type="group",
                children=tuple(
                    BinderNode(
                        label=element.title,
                        node_type="element",
                        path=element.path,
                        element_id=element.id,
                    )
                    for element in members
                ),
            )
        )
    return BinderNode(label=project.title, node_type="root", children=tuple(children))


def _manuscript_group(project: StoryProject, read_text: Callable[[str], str]) -> BinderNode:
    files = tuple(
        BinderNode(
            label=path,
            node_type="manuscript",
            path=path,
            children=_nest_headings(path, iter_headings(read_text(path))),
        )
        for path in project.manuscript
    )
    return BinderNode(label="Manuscript", node_type="group", children=files)


def _nest_headings(path: str, headings: list[Heading]) -> tuple[BinderNode, ...]:
    """Nest a flat heading list into a tree by level (Part > Chapter > Scene)."""
    roots: list[_MutableNode] = []
    stack: list[_MutableNode] = []
    for heading in headings:
        node = _MutableNode(heading=heading)
        while stack and stack[-1].heading.level >= heading.level:
            stack.pop()
        if stack:
            stack[-1].children.append(node)
        else:
            roots.append(node)
        stack.append(node)
    return tuple(_freeze(node, path) for node in roots)


class _MutableNode:
    """Scratch node used only while nesting headings."""

    __slots__ = ("heading", "children")

    def __init__(self, heading: Heading) -> None:
        self.heading = heading
        self.children: list[_MutableNode] = []


def _freeze(node: _MutableNode, path: str) -> BinderNode:
    return BinderNode(
        label=node.heading.title,
        node_type="heading",
        path=path,
        offset=node.heading.offset,
        level=node.heading.level,
        children=tuple(_freeze(child, path) for child in node.children),
    )
