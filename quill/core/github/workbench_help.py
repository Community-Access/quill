"""The GitHub Workbench's authored help, as one catalogue (GitHub PRD section 7, Part D).

Every help string the Workbench says is written once, here, and read
everywhere it appears (D19): F1, Shift+F1, Explain That, Search Help, the
Words node, the generated reference. wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields

from quill.core.github.workbench_glossary import (
    _CHAPTER_FOR,
    GLOSSARY,
    GUIDE_CHAPTERS,
    KEY_FAMILIES,
    ROW_TYPE_WORDS,
    TASKS,
    WHAT_CHANGED,
)
from quill.core.github.workbench_help_text import (
    _EMPTY,
    CHOICE_WORDS,
    NODE_HELP,
    PREF_HELP,
    PREF_PAGES,
    RESULT_EXPLANATIONS,
    SURFACE_PURPOSES,
)

__all__ = [
    "CHOICE_WORDS",
    "GLOSSARY",
    "GUIDE_CHAPTERS",
    "KEY_FAMILIES",
    "NODE_HELP",
    "PREF_HELP",
    "PREF_PAGES",
    "RESULT_EXPLANATIONS",
    "ROW_TYPE_WORDS",
    "SURFACE_PURPOSES",
    "TASKS",
    "WHAT_CHANGED",
    "HelpHit",
    "HelpTopic",
    "chapter_for",
    "empty_text_for",
    "explain_result",
    "gaps",
    "help_rows",
    "is_known_title",
    "node_help_for",
    "search_help",
    "word_for",
]


#: The window purposes, under the name every app's help catalogue uses, so the
#: family F1 reference (``quill/tools/build_help_reference.py``) renders them.
PURPOSES: dict[str, str] = dict(SURFACE_PURPOSES)


def _reference_sections() -> tuple[tuple[str, tuple[tuple[str, str], ...]], ...]:
    """The Workbench's help beyond windows and controls, for the F1 reference."""
    from quill.core.github.item_actions import GITHUB_ACTIONS
    from quill.core.github.workbench_tree import GITHUB_TREE
    from quill.core.github.workbench_window_menu import WINDOW_MENU
    from quill.core.workbench.menus import all_rows

    nodes = tuple(
        (
            node.label if not template else f"{template}: {node.label}",
            node_help_for(template, node.key),
        )
        for template, node in GITHUB_TREE.all_nodes()
    )
    menu = tuple(
        (f"{spec.title.replace('&', '')} > {row.label.replace('&', '')}", row.help)
        for spec, row in all_rows(WINDOW_MENU)
    )
    seen: set[str] = set()
    actions: list[tuple[str, str]] = []
    for kind in GITHUB_ACTIONS.row_types:
        for action in GITHUB_ACTIONS.rows_for(kind):
            if action.command_id not in seen:
                seen.add(action.command_id)
                actions.append((action.label.rstrip("."), action.help))
    options = tuple(
        (f"{page}: {label.replace('&', '').rstrip(':')}", text)
        for page, label, text in PREF_HELP.values()
    )
    return (
        ("Every place in the tree", nodes),
        ("Every menu row", menu),
        ("Every context-menu row", tuple(actions)),
        ("Every Workbench option", options),
    )


def __getattr__(name: str) -> object:
    if name == "REFERENCE_SECTIONS":
        return _reference_sections()
    raise AttributeError(name)


def explain_result(text: str) -> str:
    """What the result *text* means and what you might do next (Shift+F9)."""
    said = (text or "").strip()
    for start, explanation in RESULT_EXPLANATIONS:
        if said.startswith(start):
            return explanation
    if not said:
        return ""
    return (
        f"The Workbench last said: {said} Shift+F1 lists what you can do with the "
        "selection, and F1 says what this view is for."
    )


# ---------------------------------------------------------------------------
# Windows: what each GitHub window is for (the title half of GATE-GITHUB-HELP)
# ---------------------------------------------------------------------------


def is_known_title(title: str) -> bool:
    """Whether a GitHub Workbench surface has an authored purpose here."""
    text = title.strip()
    return any(text.startswith(known) for known in SURFACE_PURPOSES)


# ---------------------------------------------------------------------------
# Nodes: what each place shows, what you can do there, what it needs
# ---------------------------------------------------------------------------


def node_help_for(template: str, key: str) -> str:
    """F1's words for a node ("" when there are none, which the gate refuses)."""
    return NODE_HELP.get(f"{template}:{key}", "")


# ---------------------------------------------------------------------------
# Words: the GitHub glossary (Alt+F1, the Words node, D6)
# ---------------------------------------------------------------------------


def word_for(row_type: str) -> tuple[str, str]:
    """(term, explanation) for *row_type*, for What Is This? (Alt+F1)."""
    term = ROW_TYPE_WORDS.get(row_type, "Repository")
    return term, GLOSSARY[term]


# ---------------------------------------------------------------------------
# Do Something: tasks in plain words (D12)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Key families (the Keys node and Help > Workbench Keys, Part C)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# The guide: which chapter Ctrl+F1 opens for a place
# ---------------------------------------------------------------------------


def chapter_for(template: str, key: str) -> str:
    """The GitHub Guide chapter number for a node (the Workbench chapter by default)."""
    found = _CHAPTER_FOR.get(f"{template}:{key}")
    if found:
        return found
    if template == "repository":
        return "07"
    return "12"


# ---------------------------------------------------------------------------
# Search Help (Ctrl+Shift+F1, D7)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class HelpHit:
    """One Search Help result: what it is, what it says, and where Enter goes.

    *kind* is ``"node"`` (target ``"template:key"``), ``"command"`` (target a
    command id), ``"word"`` or ``"task"`` (target ``"template:key"``).
    """

    kind: str
    title: str
    body: str
    target: str = ""

    def spoken(self) -> str:
        words = {"node": "Place", "command": "Command", "word": "Word", "task": "Task"}
        return f"{words.get(self.kind, 'Topic')}: {self.title}"


def search_help(
    words: str,
    commands: Mapping[str, tuple[str, str]],
    node_labels: Mapping[str, str],
) -> list[HelpHit]:
    """Every place, command, word and task whose words hold all of *words*.

    *commands* maps a command id to its (label, key) as the window shows them;
    *node_labels* maps ``"template:key"`` to the node's label.
    """
    terms = [term.casefold() for term in words.split() if term]
    if not terms:
        return []

    def matches(*texts: str) -> bool:
        joined = " ".join(texts).casefold()
        return all(term in joined for term in terms)

    hits: list[HelpHit] = []
    for _task_id, title, steps, (template, key) in TASKS:
        if matches(title, steps):
            hits.append(HelpHit("task", title, steps, f"{template}:{key}"))
    for ref, label in node_labels.items():
        body = NODE_HELP.get(ref, "")
        if matches(label, body):
            hits.append(HelpHit("node", label, body, ref))
    for command_id, (label, key) in commands.items():
        if matches(label, key):
            title = f"{label}, {key}" if key else label
            hits.append(HelpHit("command", title, "", command_id))
    for term, text in GLOSSARY.items():
        if matches(term, text):
            hits.append(HelpHit("word", term, text))
    return hits


# ---------------------------------------------------------------------------
# What changed (the Help and Learning branch's What Changed node)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class HelpTopic:
    """A row of a Help and Learning node: its title, its words and where it leads."""

    title: str
    body: str
    target: str = ""


def help_rows(view: str, keys: Mapping[str, tuple[str, str]] | None = None) -> list[HelpTopic]:
    """The topics of one Help and Learning node, in order."""
    if view == "tasks":
        return [
            HelpTopic(title, steps, f"{template}:{key}")
            for _id, title, steps, (template, key) in TASKS
        ]
    if view == "words":
        return [HelpTopic(term, text) for term, text in sorted(GLOSSARY.items())]
    if view == "keys":
        families = [HelpTopic(name, text) for name, text in KEY_FAMILIES]
        bound = [
            HelpTopic(f"{key}, {label}", f"{label}: {key}.")
            for label, key in sorted((keys or {}).values(), key=lambda pair: pair[1])
            if key
        ]
        return families + bound
    if view == "guide":
        return [
            HelpTopic(
                f"Chapter {number}: {title}",
                f"Chapter {number} of the GitHub Workbench Guide. Enter opens it.",
                f"chapter:{number}",
            )
            for number, title in GUIDE_CHAPTERS
        ]
    if view == "changes":
        return [HelpTopic(title, text) for title, text in WHAT_CHANGED]
    if view == "ask":
        return [
            HelpTopic(
                "Write to support",
                "Write to support@community-access.org from your own email. Say what you "
                "were doing and what you expected. Nothing is sent by the Workbench.",
                "mailto:support@community-access.org",
            )
        ]
    return []


# ---------------------------------------------------------------------------
# The gate: what has no help yet (GATE-GITHUB-HELP's catalogue half)
# ---------------------------------------------------------------------------


def gaps() -> list[str]:
    """Every node, row, option or word with no authored help, as sentences."""
    from quill.core.github.item_actions import GITHUB_ACTIONS
    from quill.core.github.workbench_prefs import WorkbenchPrefs
    from quill.core.github.workbench_tree import GITHUB_TREE
    from quill.core.github.workbench_window_menu import WINDOW_MENU
    from quill.core.workbench.menus import all_rows

    found: list[str] = []
    for template, node in GITHUB_TREE.all_nodes():
        if not node_help_for(template, node.key):
            found.append(f"node {template}:{node.key} has no help in NODE_HELP")
    for kind in GITHUB_ACTIONS.row_types:
        for row in GITHUB_ACTIONS.rows_for(kind):
            if not row.help.strip():
                found.append(f"action {row.command_id} on {kind} has no help")
        if kind not in ROW_TYPE_WORDS:
            found.append(f"row type {kind} has no glossary word in ROW_TYPE_WORDS")
    for _menu, menu_row in all_rows(WINDOW_MENU):
        if not menu_row.help.strip():
            found.append(f"menu row {menu_row.command_id} has no help")
    for spec in fields(WorkbenchPrefs):
        if spec.name not in PREF_HELP:
            found.append(f"Workbench Options field {spec.name} has no help in PREF_HELP")
    for term in ROW_TYPE_WORDS.values():
        if term not in GLOSSARY:
            found.append(f"word {term} has no glossary entry")
    for _id, _title, _steps, (template, key) in TASKS:
        if not node_help_for(template, key):
            found.append(f"task {_id} goes to {template}:{key}, which has no help")
    return found


def empty_text_for(template: str, key: str) -> str:
    """The details pane's words when a node's list is empty."""
    return _EMPTY.get(
        f"{template}:{key}",
        "Nothing here right now. F5 loads it again; F1 says what this place holds.",
    )
