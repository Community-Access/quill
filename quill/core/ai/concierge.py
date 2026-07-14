"""Concierge + Selection Action Ring suggestion logic (PRD §6.1, §6.4).

Two related, wx-free, deterministic features that turn the current editing
context into concrete, keyboard-reachable actions:

- **Concierge** answers "what can I do here?" from the file type, selection state,
  outline size, git presence, and whether AI is on — returning ordered
  :class:`Suggestion`s the AI Hub Home / status bar can present.
- **Selection Action Ring** returns the ordered transform actions for an active
  selection (Rewrite clearly, Shorten, Explain, Check accessibility, ...), each
  bound to a real catalog agent + instruction.

Both are pure functions over the loaded :class:`~quill.core.ai.harness.AgentSpec`
catalog, so they are fully unit-testable and never reference wx. The UI maps the
results onto commands/announcements.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.ai.harness import AgentSpec
from quill.core.ai.permissions import PermissionCategory

__all__ = [
    "write_kind",
    "recommend_agents",
    "ConciergeContext",
    "Suggestion",
    "suggest",
    "RingAction",
    "ring_actions",
]

# File types treated as source code for the action ring.
_CODE_TYPES = frozenset({
    "py",
    "js",
    "ts",
    "tsx",
    "jsx",
    "json",
    "yaml",
    "yml",
    "toml",
    "java",
    "go",
    "rs",
    "c",
    "cpp",
    "h",
})


def write_kind(agent: AgentSpec) -> str:
    """Classify an agent by what it WRITES: ``document`` / ``selection`` / ``produce``.

    Based on the agent's declared modify permissions; a ``produce`` agent makes new
    content rather than editing in place. Shared by the catalog UI and the editor
    wiring so classification lives in one place.
    """
    overrides = agent.overrides_map()
    if PermissionCategory.MODIFY_DOCUMENT in overrides:
        return "document"
    if PermissionCategory.MODIFY_SELECTION in overrides:
        return "selection"
    return "produce"


def _matches_file_type(agent: AgentSpec, file_type: str) -> bool:
    """True if the agent is recommended for this file type (empty = general)."""
    if not agent.recommended_file_types:
        return True
    return file_type.lower() in {t.lower() for t in agent.recommended_file_types}


def recommend_agents(
    agents: list[AgentSpec], *, file_type: str = "", has_selection: bool = False
) -> list[AgentSpec]:
    """Return agents fit for the context, file-type-specific ones first.

    When ``has_selection`` is True, prefer selection-transform and produce agents;
    otherwise prefer document-transform and produce agents. Within each group,
    agents explicitly recommended for ``file_type`` come before general ones; the
    catalog's order is otherwise preserved (stable).
    """
    wanted = {"selection", "produce"} if has_selection else {"document", "produce"}
    eligible = [a for a in agents if write_kind(a) in wanted and _matches_file_type(a, file_type)]
    specific = [a for a in eligible if a.recommended_file_types]
    general = [a for a in eligible if not a.recommended_file_types]
    return specific + general


@dataclass(frozen=True, slots=True)
class ConciergeContext:
    """The lightweight signals the concierge reasons over.

    ``cursor_line`` / ``cursor_column`` (1-based; 0 = unknown) and
    ``current_section_title`` are the Phase 3 "where am I" signals, so the
    concierge and the agent can reason about the editing location, not just the
    document as a whole.
    """

    file_type: str = ""
    has_selection: bool = False
    outline_headings: int = 0
    in_git_repo: bool = False
    ai_enabled: bool = True
    cursor_line: int = 0
    cursor_column: int = 0
    current_section_title: str = ""


@dataclass(frozen=True, slots=True)
class Suggestion:
    """One recommended action. ``target`` is a command id; ``kind`` labels it."""

    label: str
    target: str
    reason: str
    kind: str  # "agent" | "command"


def _agent_command(agent: AgentSpec) -> str:
    """The palette command id registered for an agent (see register_agent_commands)."""
    return "tools.run_agent." + agent.id.replace("-", "_")


def suggest(
    context: ConciergeContext, agents: list[AgentSpec], *, limit: int = 6
) -> list[Suggestion]:
    """Return up to ``limit`` ordered, keyboard-reachable suggestions.

    Cheap context/navigation cues come first so they are never crowded out by a
    long agent list under the cap; agent actions fill the remaining slots.
    """
    out: list[Suggestion] = []

    if not context.ai_enabled:
        out.append(Suggestion("Turn on AI", "tools.ai_hub", "AI is currently off.", "command"))

    if context.outline_headings > 0:
        out.append(
            Suggestion(
                "Jump to a heading",
                "navigate.outline_navigator",
                f"{context.outline_headings} headings in this document",
                "command",
            )
        )

    if context.ai_enabled and context.in_git_repo:
        gh = next((a for a in agents if a.id == "github-maintainer"), None)
        if gh is not None:
            out.append(
                Suggestion(
                    gh.display_name,
                    _agent_command(gh),
                    "You're in a git repository.",
                    "agent",
                )
            )

    if context.ai_enabled:
        scope = "selection" if context.has_selection else "document"
        seen = {s.target for s in out}
        for agent in recommend_agents(
            agents, file_type=context.file_type, has_selection=context.has_selection
        ):
            target = _agent_command(agent)
            if target in seen:
                continue
            seen.add(target)
            out.append(
                Suggestion(
                    f"{agent.display_name}",
                    target,
                    f"{agent.description} (on the {scope})" if agent.description else scope,
                    "agent",
                )
            )

    return out[:limit]


@dataclass(frozen=True, slots=True)
class RingAction:
    """One Selection Action Ring entry: a label bound to an agent + instruction."""

    label: str
    agent_id: str
    instruction: str = ""


_TEXT_RING: tuple[RingAction, ...] = (
    RingAction("Rewrite clearly", "writing-companion", "Rewrite the selected text more clearly."),
    RingAction(
        "Shorten", "writing-companion", "Make the selected text shorter, keeping its meaning."
    ),
    RingAction("Make warmer", "writing-companion", "Rewrite the selected text in a warmer tone."),
    RingAction("Review", "reviewer", "Review the selected text and suggest improvements."),
    RingAction(
        "Check accessibility",
        "accessibility-editor",
        "Check the selection for accessibility issues.",
    ),
)

_CODE_RING: tuple[RingAction, ...] = (
    RingAction("Explain", "code-doctor", "Explain the selected code."),
    RingAction(
        "Document", "code-doctor", "Add or improve docstrings/comments without changing behavior."
    ),
    RingAction("Tidy", "code-doctor", "Tidy the selected code without changing its behavior."),
)


def ring_actions(file_type: str, agents: list[AgentSpec]) -> list[RingAction]:
    """Return the action-ring entries for the current selection + file type.

    Code file types get code actions; everything else gets writing actions. Only
    actions whose agent is actually present in the catalog are returned, so the
    ring never offers something that cannot run.
    """
    available = {a.id for a in agents}
    ring = _CODE_RING if file_type.lower() in _CODE_TYPES else _TEXT_RING
    return [action for action in ring if action.agent_id in available]
