"""The Navigator tree as data: one :class:`NodeSpec` per node.

A provider describes its tree once, as a flat tuple of nodes naming their
parents, and the window builds a native tree from it. Nodes that stand for
one of many things (each repository, each person, each site) are not listed
one by one: a node names a *template*, and the template's own nodes are the
children every instance gets ("every repository node has the same children,
in this order", GitHub PRD section 3.3).

The rules every provider's tree keeps, checked on construction:

- keys are unique and every parent is listed before its children;
- no node, counting the template it opens, sits more than four levels deep,
  because a deep tree is a slow one to arrow through (GitHub PRD section 9);
- every template a node names exists.

Loaders are named, never imported: ``"items:issues"`` or ``"explore:labels"``
says which existing fetch fills the list, and the window maps the name to
the call. That keeps this module wx-free and network-free.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum

from quill.core.workbench import WorkbenchSpecError

__all__ = ["MAX_DEPTH", "Need", "NodeSpec", "Scope", "TreeSpec"]

MAX_DEPTH = 4


class Scope(StrEnum):
    """What a node's list is about, which decides what its loader is given."""

    NONE = "none"
    ACCOUNT = "account"
    REPOSITORY = "repository"
    PERSON = "person"
    QUERY = "query"
    ORGANIZATION = "organization"


class Need(StrEnum):
    """What a node needs before it can load. The node is shown regardless."""

    SIGN_IN = "sign_in"
    PUSH = "push"
    ADMIN = "admin"
    OPT_IN = "opt_in"
    FORK = "fork"


@dataclass(frozen=True)
class NodeSpec:
    """One node of the Navigator.

    *loader* names the fetch that fills the list ("" for a folder whose list
    is its children). *preset* narrows that fetch (``(("show", "prs"),)``).
    *home* marks the node an old view or door opens: each loader key has
    exactly one home, which is what the "nothing dropped" test counts.
    *template* names the template whose nodes each child instance gets.
    *dynamic* marks a node that stands for each of a set the provider
    discovers at run time (a site's own post types): the window shows one
    copy per discovered thing, labelled by the provider, and none when the
    provider names none. Such a node has no children of its own.
    """

    key: str
    label: str
    parent: str | None = None
    scope: Scope = Scope.NONE
    needs: frozenset[Need] = field(default_factory=frozenset)
    loader: str = ""
    preset: tuple[tuple[str, str], ...] = ()
    columns: tuple[str, ...] = ()
    row_type: str = ""
    home: bool = True
    template: str = ""
    dynamic: bool = False


class TreeSpec:
    """A provider's whole tree: the fixed nodes and the templates they open."""

    def __init__(
        self,
        nodes: Sequence[NodeSpec],
        templates: Mapping[str, Sequence[NodeSpec]] | None = None,
        *,
        max_depth: int = MAX_DEPTH,
    ) -> None:
        self._nodes = self._index(nodes)
        self._templates = {name: self._index(rows) for name, rows in (templates or {}).items()}
        self.max_depth = max_depth
        self._check()

    @staticmethod
    def _index(nodes: Sequence[NodeSpec]) -> dict[str, NodeSpec]:
        index: dict[str, NodeSpec] = {}
        for node in nodes:
            if not node.key or not node.label:
                raise WorkbenchSpecError(f"A node needs a key and a label: {node!r}.")
            if node.key in index:
                raise WorkbenchSpecError(f"Node key {node.key!r} is used twice.")
            if node.parent is not None and node.parent not in index:
                raise WorkbenchSpecError(
                    f"Node {node.key!r} names parent {node.parent!r}, not listed before it."
                )
            index[node.key] = node
        return index

    def _check(self) -> None:
        for group in (self._nodes, *self._templates.values()):
            for node in group.values():
                if node.dynamic and any(other.parent == node.key for other in group.values()):
                    raise WorkbenchSpecError(f"Dynamic node {node.key!r} cannot have children.")
                if node.template and node.template not in self._templates:
                    raise WorkbenchSpecError(
                        f"Node {node.key!r} opens template {node.template!r}, which does not exist."
                    )
        for key in self._nodes:
            if self.depth(key) > self.max_depth:
                raise WorkbenchSpecError(
                    f"Node {key!r} is {self.depth(key)} levels deep; the most is {self.max_depth}."
                )

    # -- reading ---------------------------------------------------------------

    def node(self, key: str) -> NodeSpec:
        """The fixed node *key* (``KeyError`` when there is none)."""
        return self._nodes[key]

    def template(self, name: str) -> tuple[NodeSpec, ...]:
        """A template's nodes, in order; its roots have no parent."""
        return tuple(self._templates[name].values())

    def template_node(self, name: str, key: str) -> NodeSpec:
        return self._templates[name][key]

    @property
    def template_names(self) -> tuple[str, ...]:
        return tuple(self._templates)

    def roots(self) -> tuple[NodeSpec, ...]:
        return self.children(None)

    def children(self, key: str | None, *, template: str = "") -> tuple[NodeSpec, ...]:
        """The children of *key* in the fixed tree, or inside *template*."""
        group = self._templates[template] if template else self._nodes
        return tuple(node for node in group.values() if node.parent == key)

    def __iter__(self) -> Iterator[NodeSpec]:
        return iter(self._nodes.values())

    def all_nodes(self) -> Iterator[tuple[str, NodeSpec]]:
        """Every node, fixed and templated, as ``(template name or "", node)``."""
        for node in self._nodes.values():
            yield "", node
        for name, group in self._templates.items():
            for node in group.values():
                yield name, node

    def path(self, key: str) -> tuple[str, ...]:
        """The labels from the root down to the fixed node *key*."""
        labels: list[str] = []
        current: str | None = key
        while current is not None:
            node = self._nodes[current]
            labels.append(node.label)
            current = node.parent
        return tuple(reversed(labels))

    def _template_depth(self, name: str, seen: frozenset[str] = frozenset()) -> int:
        if name in seen:
            raise WorkbenchSpecError(f"Template {name!r} opens itself.")
        group = self._templates[name]

        def depth(node: NodeSpec) -> int:
            return 1 if node.parent is None else 1 + depth(group[node.parent])

        deepest = 0
        for node in group.values():
            extra = self._template_depth(node.template, seen | {name}) if node.template else 0
            deepest = max(deepest, depth(node) + extra)
        return deepest

    def depth(self, key: str) -> int:
        """How deep *key* is (a root is 1), counting the template it opens."""
        own = len(self.path(key))
        node = self._nodes[key]
        return own + (self._template_depth(node.template) if node.template else 0)

    def loaders(self) -> dict[str, list[tuple[str, str]]]:
        """Each loader name, with the ``(template, key)`` of every node using it."""
        found: dict[str, list[tuple[str, str]]] = {}
        for name, node in self.all_nodes():
            if node.loader:
                found.setdefault(node.loader, []).append((name, node.key))
        return found

    def homes(self) -> dict[str, list[tuple[str, str]]]:
        """Each loader name, with the nodes that are its home (the doors land there)."""
        found: dict[str, list[tuple[str, str]]] = {}
        for name, node in self.all_nodes():
            if node.loader and node.home:
                found.setdefault(node.loader, []).append((name, node.key))
        return found
