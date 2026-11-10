"""The GitHub Workbench provider's help: the catalogue, Help and Learning, the guide.

GitHub PRD section 7 and Part D, for
:class:`quill.ui.github_workbench_window.GitHubWorkbenchProvider`. Every word
comes from the wx-free catalogue :mod:`quill.core.github.workbench_help`, so
F1, Shift+F1, Search Help, the Words node and the generated reference say the
same thing (D19). The frame's help keys
(:mod:`quill.ui.workbench_frame_help`) ask the hooks here.

- **Help and Learning** (D11): ``help:`` nodes list topics as rows (Do
  Something's tasks, the guide's chapters, Words, Keys, What Changed, Ask a
  Person). Enter on a topic reads it, or opens the chapter or the address it
  names; Take Me There goes to the place a task is about (D12).
- **Ctrl+F1** opens the GitHub Guide that ships with the editor at the
  chapter for this node, or its contents page when that chapter is missing.
"""

from __future__ import annotations

import webbrowser
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from quill.core.github import workbench_help as catalogue
from quill.core.github.explore_models import ExploreRow
from quill.core.workbench.menus import MenuSub, all_rows
from quill.core.workbench.tree import NodeSpec

__all__ = ["HELP_PREFIX", "GitHubWorkbenchHelpMixin"]

HELP_PREFIX = "help:"


class GitHubWorkbenchHelpMixin:
    """Help hooks for the GitHub provider. Runs on the UI thread except :meth:`load_help`."""

    frame: Any
    _guide_product: str

    def help_purpose(self) -> str:
        return catalogue.SURFACE_PURPOSES["GitHub Workbench"]

    def catalogue_node_help(self, template: str, key: str) -> str:
        return catalogue.node_help_for(template, key)

    def glossary_for(self, row_type: str) -> tuple[str, str]:
        return catalogue.word_for(row_type)

    def empty_text(self, ref: Any, _node: NodeSpec) -> str:
        return catalogue.empty_text_for(ref.template, ref.key)

    def key_text(self) -> str:
        keys = getattr(self.frame, "_keys", {}) if self.frame is not None else {}
        lines = [f"{name}: {text}" for name, text in catalogue.KEY_FAMILIES]
        lines.append("")
        for spec in getattr(self, "menu", ()):
            lines.append(spec.title.replace("&", "") + " menu:")
            for row in spec.rows:
                if isinstance(row, MenuSub):
                    lines.append(f"  {row.title.replace('&', '')}: a submenu")
                elif row is not None:
                    key = keys.get(row.command_id, row.key)
                    lines.append(f"  {row.label.replace('&', '').rstrip('.')}: {key}")
        return "\n".join(lines)

    def search_help(
        self, words: str, commands: Mapping[str, tuple[str, str]]
    ) -> list[catalogue.HelpHit]:
        labels: dict[str, str] = {}
        for template, node in self.tree.all_nodes():
            labels[f"{template}:{node.key}"] = node.label
        return catalogue.search_help(words, commands, labels)

    def load_help(self, node: NodeSpec) -> list[ExploreRow]:
        """A Help and Learning node's topics, as rows."""
        view = node.loader.removeprefix(HELP_PREFIX)
        keys: dict[str, tuple[str, str]] = {}
        if view == "keys":
            bound = getattr(self.frame, "_keys", {}) if self.frame is not None else {}
            for _spec, row in all_rows(getattr(self, "menu", ())):
                label = row.label.replace("&", "").rstrip(".")
                keys[row.command_id] = (label, bound.get(row.command_id, row.key))
        return [
            ExploreRow(topic.title, topic.body, "", "", "help_topic", topic.target)
            for topic in catalogue.help_rows(view, keys)
        ]

    # -- the guide ------------------------------------------------------------

    def open_guide(self, ref: Any, chapter: str = "") -> None:
        """Ctrl+F1: the GitHub Guide at the chapter for *ref* (or *chapter*)."""
        from quill.core.guide_locations import find_guide

        number = chapter or catalogue.chapter_for(ref.template, ref.key)
        product = getattr(self, "_guide_product", "quill")
        contents = find_guide(product, "github")  # type: ignore[arg-type]
        if contents is None:
            self._say("The GitHub Guide is not in this copy. Reinstalling puts it back.")
            return
        page = _chapter_page(contents, number) or contents
        if not webbrowser.open(page.as_uri()):
            self._say(f"The GitHub Guide is at {page}")

    # -- the topic rows' actions -------------------------------------------------

    def _do_open_topic(self, ref: Any, row: object) -> None:
        assert isinstance(row, ExploreRow)
        target = row.key
        if target.startswith("chapter:"):
            self.open_guide(ref, target.removeprefix("chapter:"))
        elif target.startswith("mailto:"):
            if not webbrowser.open(target):
                self._say("Write to support@community-access.org from your own email.")
        else:
            self.frame.details.SetFocus()

    def _do_take_me_there(self, _ref: Any, row: object) -> None:
        from quill.ui.workbench_frame import NodeRef

        assert isinstance(row, ExploreRow)
        template, _, key = row.key.partition(":")
        if not key:
            self._say("This topic is not about one place.")
            return
        instance = next(iter(self.instances(template)), "") if template else ""  # type: ignore[attr-defined]
        if template and not instance:
            self._say("Open a repository first. Ctrl+L opens one by name or link.")
            return
        if self.frame.select(NodeRef(template, key, instance)):
            self.frame.tree.SetFocus()

    def _say(self, text: str) -> None:  # replaced by the actions mixin's, which comes first
        if self.frame is not None:
            self.frame._say(text)


def _chapter_page(contents: Path, number: str) -> Path | None:
    """The chapter file numbered *number* beside the guide's contents page."""
    stem = contents.stem  # github-guide or lite-github-guide
    found = sorted(contents.parent.glob(f"{stem}-{number}-*{contents.suffix}"))
    return found[0] if found else None
