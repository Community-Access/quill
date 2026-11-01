"""Add Abbreviations from a Document: Quill Inkwell's agent task (codex.md 6.12, Phase 4c).

The person says what they want ("look at my report and add abbreviations for
the long phrases I keep typing"), and an agent engine -- My GitHub Copilot or
Codex -- works through it with Inkwell's own tools in the shared agent window
(:mod:`quill.ui.agent_window`). Unlike Suggest Abbreviations from a Document,
which is one request and a review list, this one can read the library, talk it
over and come back with a better set.

* ``inkwell.choose_document`` -- opens the standard Open window for the person
  to pick a document, reads it on this computer, then asks the same Yes or No
  Suggest asks before any of its text goes (codex.md 10C.3). The file's name and
  folder stay here; only the text goes, capped as Suggest caps it.
* ``inkwell.list_abbreviations`` -- the library, each entry as
  ``abbreviation -> expansion``.
* ``inkwell.add_abbreviations`` -- shows every proposed entry as text, leaves out
  any that clashes with one the person already has, and adds the rest on Apply
  through the same library save Suggest uses.

**Never driven by a model.** System-wide expansion, the keyboard hook and the
matcher never see the AI, and nothing typed in other programs is read. Handlers
run on a worker thread; every touch of the window goes through ``ctx.on_ui``.
Nothing here announces: the agent window says each step and the closing
summary, once (GATE-13).
"""

from __future__ import annotations

import re
from typing import Any

from quill.core.ai.app_task import AppTaskHost, AppTaskSpec
from quill.core.ai.family_tools import FamilyTool, _schema
from quill.core.ai.permissions import PermissionCategory, RiskLevel
from quill.core.ai.tool_gateway import ToolError

__all__ = [
    "ADD_FROM_DOCUMENT",
    "APP",
    "INSTRUCTION_HELP",
    "inkwell_task_facts",
    "inkwell_task_tools",
]

APP = "inkwell"

_LIST_LIMIT = 300
_EXPANSION_LIMIT = 500
_NOT_APPLIED = "The person did not apply it."
#: What an abbreviation may be: what Suggest accepts (``app_requests``).
_ABBREVIATION = re.compile(r"^[A-Za-z0-9]{2,12}$")
_PAIR = re.compile(r"^\s*`?([^\s`]+)`?\s*(?:->|=>|:)\s*(.+?)\s*$", re.DOTALL)

ADD_FROM_DOCUMENT = AppTaskSpec(
    app=APP,
    agent_id="inkwell-add-from-document",
    title="Add Abbreviations from a Document",
    instructions=(
        "You help someone who uses a screen reader build their Quill Inkwell "
        "abbreviation library: short letters that expand into longer text as "
        "they type in any program. Ask them to pick a document with "
        "inkwell_choose_document, see what they already have with "
        "inkwell_list_abbreviations, then propose abbreviations for phrases, "
        "names and terms the document repeats. An abbreviation is 2 to 12 "
        "letters or digits, easy to remember, and must not be an ordinary word "
        "they would type for itself, or one they already have. Add them with "
        "inkwell_add_abbreviations; it shows the person every entry and asks, "
        "and they may say no."
    ),
    done_words={f"{APP}.add_abbreviations": "Added abbreviations"},
)

INSTRUCTION_HELP = (
    "Type what you want from a document, then press Enter. For example: add "
    "abbreviations for the long names and phrases in my report. You pick the "
    "document, you are asked before its text is sent, and you see every "
    "abbreviation before any is added. While a task runs, what you type here goes "
    "to it as a follow-up."
)


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}{'' if count == 1 else 's'}"


def _one_line(text: str, limit: int = 0) -> str:
    flat = " (new line) ".join(part.strip() for part in text.strip().splitlines())
    if limit and len(flat) > limit:
        return flat[:limit].rstrip() + " ..."
    return flat


def inkwell_task_facts(host: Any) -> str:
    """The library's size, sent with the first instruction (never typed text)."""
    library = getattr(host, "_library", None)
    count = len(getattr(library, "abbreviations", ()) or ())
    return f"Abbreviations in the library: {count}."


def _entries(raw: Any) -> list[tuple[str, str]]:
    """``(abbreviation, expansion)`` from a list of objects or "a -> b" lines."""
    if isinstance(raw, str):
        raw = raw.splitlines()
    pairs: list[tuple[str, str]] = []
    for item in raw or []:
        if isinstance(item, dict):
            pairs.append((
                str(item.get("abbreviation", "") or "").strip(),
                str(item.get("expansion", "") or "").strip(),
            ))
            continue
        match = _PAIR.match(str(item))
        if match is not None:
            pairs.append((match.group(1).strip(), match.group(2).strip()))
    return pairs


# --------------------------------------------------------------------------- #
# The tools
# --------------------------------------------------------------------------- #


def inkwell_task_tools(host: Any, ctx: AppTaskHost) -> list[FamilyTool]:
    """Quill Inkwell's tools for one task."""

    def library_now() -> list[Any]:
        library = ctx.on_ui(lambda: getattr(host, "_library", None), None)
        return list(getattr(library, "abbreviations", ()) or ())

    # -- reads ---------------------------------------------------------------

    def choose_document(_args: dict[str, Any]) -> str:
        from quill.apps.inkwell_ai import UnreadableDocument, read_document_text
        from quill.core.ai.app_requests import INKWELL_DOCUMENT_CHARS

        path = ctx.on_ui(host._inkwell_pick_document, None)
        if path is None:
            return "The person did not choose a document."
        try:
            text = read_document_text(path)
        except UnreadableDocument as error:
            raise ToolError(str(error)) from error
        if not text.strip():
            return f"{path.name} has no text in it."
        if not ctx.on_ui(lambda: host._inkwell_confirm_send(path.name, text), False):
            return f"The person chose {path.name} but did not agree to send its text."
        stripped = text.strip()
        whole = len(stripped) <= INKWELL_DOCUMENT_CHARS
        sent = stripped[:INKWELL_DOCUMENT_CHARS]
        amount = "all of it" if whole else f"the first {len(sent.split()):,} words"
        return f"The text of {path.name} ({amount}):\n\n{sent}"

    def list_abbreviations(_args: dict[str, Any]) -> str:
        entries = library_now()
        if not entries:
            return "The library has no abbreviations yet."
        lines = [f"{_plural(len(entries), 'abbreviation')}:"]
        for entry in entries[:_LIST_LIMIT]:
            off = "" if getattr(entry, "enabled", True) else " (turned off)"
            lines.append(f"{entry.abbreviation} -> {_one_line(entry.expansion, 80)}{off}")
        if len(entries) > _LIST_LIMIT:
            lines.append(f"... and {len(entries) - _LIST_LIMIT} more.")
        return "\n".join(lines)

    # -- what changes --------------------------------------------------------

    def sort_out(args: dict[str, Any]) -> tuple[list[tuple[str, str]], list[str]]:
        """The entries that may be added, and a line for each that may not."""
        have = {e.abbreviation.lower(): e for e in library_now()}
        taken: set[str] = set()
        accepted: list[tuple[str, str]] = []
        refused: list[str] = []
        for abbreviation, expansion in _entries(args.get("entries")):
            shown = f"{abbreviation} -> {_one_line(expansion, 80)}"
            key = abbreviation.lower()
            if not _ABBREVIATION.match(abbreviation):
                refused.append(f"{shown} (an abbreviation is 2 to 12 letters or digits)")
            elif not expansion or expansion.lower() == key:
                refused.append(f"{shown} (it needs something to expand to)")
            elif len(expansion) > _EXPANSION_LIMIT:
                refused.append(f"{shown} (longer than {_EXPANSION_LIMIT} characters)")
            elif key in have:
                mine = have[key]
                refused.append(
                    f"{shown} (you already have {mine.abbreviation} -> "
                    f"{_one_line(mine.expansion, 60)})"
                )
            elif key in taken:
                refused.append(f"{shown} (proposed twice)")
            else:
                taken.add(key)
                accepted.append((key, expansion))
        if not accepted and not refused:
            raise ToolError(
                "Give the entries as a list of abbreviation and expansion, such as "
                "btw -> by the way."
            )
        return accepted, refused

    def add_abbreviations(args: dict[str, Any]) -> str:
        accepted, refused = sort_out(args)
        if not accepted:
            raise ToolError("None of them can be added: " + "; ".join(refused) + ".")
        lines = [f"Add {_plural(len(accepted), 'abbreviation')}:"]
        lines += [f"{a} -> {_one_line(e)}" for a, e in accepted]
        if refused:
            lines.append("")
            lines.append("Left out:")
            lines += refused
        if not ctx.preview("Add Abbreviations", "\n".join(lines)):
            raise ToolError(_NOT_APPLIED)
        added = int(ctx.on_ui(lambda: host._inkwell_add_suggestions(accepted), 0) or 0)
        if added == 0:
            raise ToolError("Nothing was added: they now clash with entries in the library.")
        said = f"Added {_plural(added, 'abbreviation')}."
        if added < len(accepted):
            said += f" {len(accepted) - added} clashed with entries added meanwhile."
        if refused:
            said += f" Left out {len(refused)}: " + "; ".join(refused) + "."
        return said

    def add_summary(args: dict[str, Any]) -> str:
        try:
            accepted, _refused = sort_out(args)
        except ToolError:
            return "Add abbreviations to Quill Inkwell."
        names = ", ".join(a for a, _e in accepted)
        return f"Add {_plural(len(accepted), 'abbreviation')} to Quill Inkwell: {names}."

    return [
        FamilyTool(
            name=f"{APP}.choose_document",
            description=(
                "Ask the person to pick a document (plain text, Markdown, Word or rich "
                "text) and, once they agree to send it, return its text."
            ),
            handler=choose_document,
            category=PermissionCategory.READ_WORKSPACE,
            app=APP,
        ),
        FamilyTool(
            name=f"{APP}.list_abbreviations",
            description=(
                "List the abbreviations the person already has, as abbreviation -> expansion."
            ),
            handler=list_abbreviations,
            category=PermissionCategory.READ_WORKSPACE,
            app=APP,
        ),
        FamilyTool(
            name=f"{APP}.add_abbreviations",
            description=(
                "Add new abbreviations. Shows the person every entry first, leaves out "
                "any that clashes with one they have, and asks."
            ),
            handler=add_abbreviations,
            parameters=_schema(
                {
                    "entries": {
                        "type": "array",
                        "description": "The new abbreviations.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "abbreviation": {"type": "string"},
                                "expansion": {"type": "string"},
                            },
                            "required": ["abbreviation", "expansion"],
                        },
                    }
                },
                ("entries",),
            ),
            category=PermissionCategory.MODIFY_DOCUMENT,
            risk=RiskLevel.MEDIUM,
            app=APP,
            mutating=True,
            summarize=add_summary,
        ),
    ]
