from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from quill.core.commands import Command, CommandRegistry
from quill.core.features import FeatureManager


@dataclass(frozen=True, slots=True)
class AssistantTool:
    name: str
    title: str
    description: str
    category: str
    command_id: str | None = None
    requires_confirmation: bool = False
    dangerous: bool = False


@dataclass(frozen=True, slots=True)
class AssistantPromptPreset:
    name: str
    title: str
    description: str
    template: str


_CONTENT_TOOLS: tuple[AssistantTool, ...] = (
    AssistantTool(
        name="get_document_text",
        title="Get Document Text",
        description="Return the current document text for analysis.",
        category="content",
    ),
    AssistantTool(
        name="get_selection",
        title="Get Selection",
        description="Return the current selection or an empty string.",
        category="content",
    ),
    AssistantTool(
        name="get_outline",
        title="Get Outline",
        description="Return the document outline for heading-aware editing.",
        category="content",
    ),
    AssistantTool(
        name="replace_selection",
        title="Replace Selection",
        description="Replace the current selection with new text.",
        category="content",
        requires_confirmation=True,
    ),
    AssistantTool(
        name="insert_at_cursor",
        title="Insert at Cursor",
        description="Insert text at the current caret position.",
        category="content",
    ),
    AssistantTool(
        name="replace_range",
        title="Replace Range",
        description="Replace a specific text range in the current document.",
        category="content",
        requires_confirmation=True,
        dangerous=True,
    ),
    AssistantTool(
        name="find_text",
        title="Find Text",
        description="Search the current document for a query.",
        category="content",
    ),
    AssistantTool(
        name="run_python",
        title="Run Python",
        description=(
            "Run a restricted Python transform against document text (import "
            "allowlist and resource limits, not a security boundary)."
        ),
        category="automation",
        requires_confirmation=True,
        dangerous=True,
    ),
)

_PROMPT_PRESETS: tuple[AssistantPromptPreset, ...] = (
    AssistantPromptPreset(
        name="rewrite",
        title="Rewrite Selection",
        description="Rewrite the selected text to read more clearly.",
        template="Rewrite the selected text to be clearer and more polished:\n\n{selection}",
    ),
    AssistantPromptPreset(
        name="summarize",
        title="Summarize Selection",
        description="Turn the selected text into a short summary.",
        template="Summarize the selected text in plain English:\n\n{selection}",
    ),
    AssistantPromptPreset(
        name="continue",
        title="Continue Writing",
        description="Continue the current draft from the current point.",
        template="Continue this draft in the same voice and structure:\n\n{selection}{document}",
    ),
    AssistantPromptPreset(
        name="grammar",
        title="Fix Grammar",
        description="Correct grammar, spelling, and punctuation.",
        template="Fix grammar, spelling, and punctuation without changing meaning:\n\n{selection}",
    ),
    AssistantPromptPreset(
        name="outline",
        title="Turn Into Outline",
        description="Convert the text into a structured outline.",
        template=(
            "Turn the selected text into a structured outline with headings and bullets:\n\n"
            "{selection}"
        ),
    ),
)


def build_assistant_tools(
    command_registry: CommandRegistry,
    feature_manager: FeatureManager | None = None,
) -> list[AssistantTool]:
    tools = [_tool_for_command(command) for command in command_registry.list(feature_manager)]
    tools.extend(_CONTENT_TOOLS)
    return sorted(tools, key=lambda item: (item.category, item.title.lower()))


def assistant_prompt_presets() -> list[AssistantPromptPreset]:
    return list(_PROMPT_PRESETS)


def assistant_prompt_preset(name: str) -> AssistantPromptPreset | None:
    normalized = name.strip().lower()
    for preset in _PROMPT_PRESETS:
        if preset.name == normalized:
            return preset
    return None


def render_assistant_prompt(
    preset_name: str,
    *,
    selection_text: str = "",
    document_text: str = "",
) -> str:
    preset = assistant_prompt_preset(preset_name)
    if preset is None:
        return ""
    selection = selection_text.strip()
    document = document_text.strip()
    if document:
        document = f"\n\nDocument context:\n{document}"
    return preset.template.format(selection=selection, document=document).strip()


def rank_assistant_tools(
    query: str,
    tools: Iterable[AssistantTool],
    limit: int = 10,
) -> list[AssistantTool]:
    terms = [term for term in _tokenize(query) if term]
    if not terms:
        return list(tools)[:limit]
    scored: list[tuple[int, AssistantTool]] = []
    for tool in tools:
        score = 0
        haystack = " ".join(
            filter(
                None,
                [
                    tool.name,
                    tool.title,
                    tool.description,
                    tool.category,
                    tool.command_id or "",
                ],
            )
        ).lower()
        for term in terms:
            if term in haystack:
                score += 3
            if tool.name.lower().startswith(term):
                score += 2
            if tool.title.lower().startswith(term):
                score += 2
        if score:
            scored.append((score, tool))
    scored.sort(key=lambda item: (-item[0], item[1].command_id is None, item[1].title.lower()))
    return [tool for _score, tool in scored[:limit]]


def _tool_for_command(command: Command) -> AssistantTool:
    category = _category_for_command(command.id)
    dangerous = command.id.startswith((
        "file.",
        "edit.replace",
        "tools.report",
        "tools.shell_remove",
    ))
    requires_confirmation = dangerous or command.id in {
        "file.open",
        "file.save_as",
        "file.restore_backup",
        "tools.run_python",
    }
    return AssistantTool(
        name=command.id,
        title=command.title,
        description=_command_description(command),
        category=category,
        command_id=command.id,
        requires_confirmation=requires_confirmation,
        dangerous=dangerous,
    )


def _command_description(command: Command) -> str:
    if command.keybinding:
        return f"{command.title} ({command.keybinding})"
    return command.title


def _category_for_command(command_id: str) -> str:
    if command_id.startswith("file."):
        return "file"
    if command_id.startswith("edit.") or command_id.startswith("format."):
        return "editing"
    if command_id.startswith("navigate."):
        return "navigation"
    if command_id.startswith("tools.read_aloud"):
        return "audio"
    if command_id.startswith("tools."):
        return "tools"
    if command_id.startswith("view."):
        return "view"
    if command_id.startswith("help."):
        return "help"
    return "app"


def _tokenize(text: str) -> list[str]:
    return [part for part in text.lower().split() if part]
