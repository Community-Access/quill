"""Uniform view + Promote continuum over Prompts, Skills, and Agents (AI Library).

The unified AI Library presents three kinds of saved AI intent — Prompts (one
instruction), Skills (a multi-step ``.sqp`` workflow), and Agents (an autonomous,
tool-using catalog entry) — as one library. This wx-free module gives the dialog
a single :class:`LibraryItem` shape over all three so the list/preview code is
uniform, and it implements the **Promote continuum**: a Prompt can graduate to a
Skill, and a Skill to an Agent.

Listing reads the existing stores (:class:`~quill.core.prompt_library.PromptLibrary`,
:class:`~quill.core.skill_store.SkillStore`, the agent catalog). The Promote
generators are pure string transforms that produce valid ``.sqp`` / agent ``.md``
source, so they are fully unit-testable and the UI only has to persist or display
the result.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "LibraryItem",
    "list_prompts",
    "list_skills",
    "list_agents",
    "prompt_to_skill_source",
    "skill_to_agent_markdown",
]


@dataclass(frozen=True, slots=True)
class LibraryItem:
    """One library entry, uniform across all three kinds.

    ``kind`` is ``"prompt"`` / ``"skill"`` / ``"agent"``. ``detail`` is the body
    shown in the preview pane (prompt text, skill source, or agent system prompt).
    ``can_promote`` is True when this kind has a next tier (prompts and skills do;
    agents are the top of the continuum).
    """

    kind: str
    id: str
    name: str
    description: str
    detail: str
    is_builtin: bool = False
    enabled: bool = True

    @property
    def can_promote(self) -> bool:
        return self.kind in ("prompt", "skill")

    @property
    def promote_label(self) -> str:
        return {"prompt": "Promote to Skill", "skill": "Promote to Agent"}.get(self.kind, "")


def list_prompts(library: object) -> list[LibraryItem]:
    """Uniform items for every prompt in a :class:`PromptLibrary`."""
    items: list[LibraryItem] = []
    for p in library.all():  # type: ignore[attr-defined]
        items.append(
            LibraryItem(
                kind="prompt",
                id=p.id,
                name=p.name,
                description=p.category,
                detail=p.text,
                is_builtin=p.is_builtin,
                enabled=p.enabled,
            )
        )
    return items


def list_skills(store: object) -> list[LibraryItem]:
    """Uniform items for every installed skill in a :class:`SkillStore`."""
    items: list[LibraryItem] = []
    for s in store.all():  # type: ignore[attr-defined]
        items.append(
            LibraryItem(
                kind="skill",
                id=s.id,
                name=s.name,
                description=s.description,
                detail=s.source,
                is_builtin=False,
                enabled=s.enabled,
            )
        )
    return items


def list_agents(agents: list) -> list[LibraryItem]:
    """Uniform items for catalog agents (read-only built-ins)."""
    items: list[LibraryItem] = []
    for a in sorted(agents, key=lambda a: a.display_name.lower()):
        items.append(
            LibraryItem(
                kind="agent",
                id=a.id,
                name=a.display_name,
                description=a.description,
                detail=a.system_prompt,
                is_builtin=True,
                enabled=True,
            )
        )
    return items


# ---------------------------------------------------------------------------
# Promote continuum
# ---------------------------------------------------------------------------


def prompt_to_skill_source(name: str, prompt_text: str, *, description: str = "") -> str:
    """Wrap a prompt as a valid one-step ``.sqp`` skill source.

    The prompt text becomes the single step's body, so a saved prompt graduates
    into a runnable, shareable skill the user can then add more steps to.
    """
    from quill.core.skill_pack import SQP_SCHEMA

    safe_name = name.strip() or "Untitled Skill"
    desc = (description.strip() or f"Skill created from the '{safe_name}' prompt.").replace(
        "\n", " "
    )
    body = prompt_text.strip() or "{selection}"
    return (
        "---\n"
        f"schema: {SQP_SCHEMA}\n"
        f"name: {safe_name}\n"
        f"description: {desc}\n"
        "author: You\n"
        "version: 1.0.0\n"
        "---\n"
        "\n"
        f"# Step 1: {safe_name}\n"
        "\n"
        f"{body}\n"
    )


def skill_to_agent_markdown(skill: object) -> str:
    """Generate an agent ``.md`` scaffold from an installed skill.

    The agent's system prompt is derived from the skill's description and its step
    headings, so a multi-step workflow graduates into an autonomous agent the user
    can review, save into their agents folder, and run through the gateway.
    """
    from quill.core.ai.agent_catalog import parse_agent_markdown  # noqa: F401  (kept symmetric)
    from quill.core.skill_pack import parse_skill
    from quill.core.skill_store import slugify_skill_name

    name = getattr(skill, "name", "") or "Untitled Agent"
    description = getattr(skill, "description", "") or f"Agent created from the '{name}' skill."
    agent_id = slugify_skill_name(name)

    headings: list[str] = []
    try:
        pack = parse_skill(getattr(skill, "source", ""))
        headings = [step.heading for step in pack.steps]
    except Exception:  # noqa: BLE001 - a malformed skill still yields a usable scaffold
        headings = []

    steps_text = (
        "\n".join(f"{i}. {h}" for i, h in enumerate(headings, 1))
        if headings
        else "1. Carry out the user's request."
    )
    system_prompt = (
        f"You are {name}, an assistant that helps with the user's open document. "
        f"{description} Work through these steps in order, using the read tools to "
        f"look at the document and the edit tools to propose changes (every edit is "
        f"reviewed before it is applied):\n\n{steps_text}\n\n"
        "Keep your answers concise and clear for screen-reader users."
    )
    return (
        "---\n"
        f"id: {agent_id}\n"
        f"display_name: {name}\n"
        f"description: {description.replace(chr(10), ' ')}\n"
        "risk: low\n"
        "default_scope: full_document\n"
        "default_harness: auto\n"
        "---\n"
        "\n"
        f"{system_prompt}\n"
    )
