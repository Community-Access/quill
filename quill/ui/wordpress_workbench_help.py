"""The WordPress Workbench provider's help: the frame's help hooks, Help and Learning, the guide.

WordPress PRD Part D (WP-R-046 to WP-R-048), for
:class:`quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`,
modelled on :mod:`quill.ui.github_workbench_help`. The frame's help keys
(:mod:`quill.ui.workbench_frame_help`) ask the hooks here, so in WordPress:

- **Alt+F1, What Is This?** explains the WordPress word for the selected row,
  with an example from the person's own site when the Workbench has read one
  (:mod:`quill.core.wordpress.workbench_glossary`).
- **Ctrl+F1** opens the WordPress and Forms guide at the chapter for this
  place, or at its contents page.
- **Ctrl+Shift+F1, Search Help** finds places, commands, words and tasks.
- **Alt+Shift+F1** lists the keys; **Shift+F9** explains the last result.
- **Help and Learning** lists Do Something, The Guide, What Changed and Ask a
  Person as topics: Open reads one or opens what it names; Take Me There goes
  to the place it is about. Ask a Person only opens a blank message in the
  person's own email, with nothing of theirs in it.

The problem rows' Explain, Fix..., Take Me There and Open in Editor, What
Depends on It, and the explained settings' links live in
:mod:`quill.ui.wordpress_workbench_problems`. Runs on the UI thread except
:meth:`load_help`, which only reads what is already loaded.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from quill.core.wordpress.workbench_glossary import example_for, meaning_of, term_for
from quill.core.wordpress.workbench_help import KEYS, help_rows
from quill.core.wordpress.workbench_help_topics import (
    PURPOSE,
    HelpHit,
    chapter_for,
    empty_text_for,
    explain_result,
)
from quill.core.wordpress.workbench_help_topics import search_help as search_topics
from quill.core.wordpress.workbench_node_help import node_help as authored_help
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.menus import MenuSub
from quill.core.workbench.tree import NodeSpec

__all__ = ["GUIDE_STEM", "WorkbenchHelpCommands", "guide_contents"]

GUIDE_STEM = "wordpress-forms-guide"

#: Where the WordPress and Forms guide sits: installed, then in the source tree.
_GUIDE_PLACES = (
    Path("docs") / "wordpress-and-forms" / f"{GUIDE_STEM}.html",
    Path("docs") / "user guide" / "wordpress-and-forms" / f"{GUIDE_STEM}.html",
)

_KEEP_ROWS = 200  # rows remembered per kind, for the glossary's examples


def guide_contents(roots: Sequence[Path] | None = None) -> Path | None:
    """The guide's contents page, from the first root that has it."""
    from quill.core.guide_locations import search_roots

    for root in search_roots() if roots is None else roots:
        for place in _GUIDE_PLACES:
            try:
                if (root / place).is_file():
                    return root / place
            except OSError:
                continue
    return None


def _chapter_page(contents: Path, number: str) -> Path | None:
    """The chapter page numbered *number* beside the contents page."""
    found = sorted(contents.parent.glob(f"wordpress-forms-{number}-*{contents.suffix}"))
    return found[0] if found else None


class WorkbenchHelpCommands:
    """Help hooks and Help and Learning for the WordPress provider."""

    frame: Any
    commands: Any
    tree: Any
    menu: Any
    no_instance_text: str
    say: Callable[[str], None]
    current_site: Callable[[], str]

    # -- what has been read, for the glossary's examples ----------------------------

    def remember_rows(self, rows: Sequence[object]) -> None:
        """Keep a few loaded rows of each kind, so a word can be shown on this site."""
        by_kind: dict[str, list[WbRow]] = {}
        for row in rows:
            if isinstance(row, WbRow) and row.kind not in ("help", "help_topic"):
                by_kind.setdefault(row.kind, []).append(row)
        if by_kind:
            seen: dict[str, list[WbRow]] = self.__dict__.setdefault("_seen_rows", {})
            for kind, found in by_kind.items():
                seen[kind] = found[:_KEEP_ROWS]

    def seen_rows(self) -> Mapping[str, Sequence[WbRow]]:
        return dict(self.__dict__.get("_seen_rows", {}))

    def load_help(self, what: str) -> list[WbRow]:
        """A Help and Learning node's rows (words carry this site's examples)."""
        return help_rows(what, self.seen_rows())

    # -- the frame's help hooks -------------------------------------------------------

    def help_purpose(self) -> str:
        return PURPOSE

    def _selected(self) -> WbRow | None:
        frame = self.frame
        row = frame.selected_row() if frame is not None else None
        return row if isinstance(row, WbRow) else None

    def glossary_for(self, row_type: str) -> tuple[str, str]:
        """Alt+F1: the WordPress word for the selected row, with this site's example."""
        row = self._selected()
        if row is not None and row.kind == "help" and row.cell("word"):
            term = row.cell("word")  # on the Words node, the word itself
        else:
            term = term_for(row.kind if row is not None else row_type, row)
        if not term:
            return "", ""
        example = example_for(term, row, self.seen_rows())
        return term, f"{meaning_of(term)} {example}".strip()

    def empty_text(self, _ref: Any, node: NodeSpec) -> str:
        return empty_text_for(node.key)

    def explain(self, text: str) -> str:
        """Shift+F9: what the last result means and what to do next."""
        return explain_result(text)

    def key_text(self) -> str:
        """Alt+Shift+F1: the key families, then every menu row with its key."""
        keys = getattr(self.frame, "_keys", {}) if self.frame is not None else {}
        lines = [f"{key}: {does}" for key, does in KEYS]
        lines.append("")
        for spec in self.menu:
            lines.append(spec.title.replace("&", "") + " menu:")
            for row in spec.rows:
                if isinstance(row, MenuSub):
                    lines.append(f"  {row.title.replace('&', '')}: a submenu")
                elif row is not None:
                    key = keys.get(row.command_id, row.key)
                    lines.append(f"  {row.label.replace('&', '').rstrip('.')}: {key}")
        return "\n".join(lines)

    def search_help(self, words: str, commands: Mapping[str, tuple[str, str]]) -> list[HelpHit]:
        """Ctrl+Shift+F1: tasks, places, commands and words that hold every word typed."""
        labels = {
            f"{template}:{node.key}": (node.label, authored_help(node.key))
            for template, node in self.tree.all_nodes()
            if not node.dynamic
        }
        return search_topics(words, commands, labels)

    def open_guide(self, ref: Any, chapter: str = "") -> None:
        """Ctrl+F1: the WordPress and Forms guide at the chapter for *ref* (or *chapter*)."""
        number = chapter or chapter_for(getattr(ref, "key", ""))
        contents = guide_contents()
        if contents is None:
            self.say(
                "The WordPress and Forms guide is not in this copy. Reinstalling puts it back."
            )
            return
        page = _chapter_page(contents, number) or contents
        self.commands.host.open_in_browser(page.as_uri())

    # -- the topic rows' actions ------------------------------------------------------

    def do_open_topic(self, ref: Any, row: WbRow | None) -> None:
        target = str(row.raw.get("target", "")) if row is not None else ""
        if target.startswith("chapter:"):
            self.open_guide(ref, target.removeprefix("chapter:"))
        elif target.startswith("mailto:"):
            # A blank message in the person's own email: nothing of theirs is put in it.
            self.commands.host.open_in_browser(target)
        elif self.frame is not None:
            self.frame.details.SetFocus()

    def do_take_me_there(self, _ref: Any, row: WbRow | None) -> None:
        from quill.ui.workbench_frame import NodeRef

        target = str(row.raw.get("target", "")) if row is not None else ""
        template, _sep, key = target.partition(":")
        if not key or self.frame is None:
            self.say("This topic is not about one place.")
            return
        instance = self.current_site() if template == "site" else ""
        if template == "site" and not instance:
            self.say(self.no_instance_text)
            return
        if self.frame.select(NodeRef(template, key, instance)):
            self.frame.tree.SetFocus()
