from __future__ import annotations

from dataclasses import dataclass

from quill.core.assistant_prompts import render_prompt_template


@dataclass(frozen=True, slots=True)
class AgentProfile:
    agent_id: str
    title: str
    description: str
    template: str
    requires_approval: bool = True


@dataclass(frozen=True, slots=True)
class AgentPlan:
    profile: AgentProfile
    prompt: str
    checks: tuple[str, ...]


_AGENT_PROFILES: tuple[AgentProfile, ...] = (
    AgentProfile(
        agent_id="rewrite",
        title="Rewrite Agent",
        description="Refine and rewrite text while preserving intent.",
        template=(
            "Goal: {goal}\n"
            "Audience: {audience}\n"
            "Tone: {tone}\n\n"
            "Rewrite the selected text while preserving meaning:\n\n{selection}"
        ),
    ),
    AgentProfile(
        agent_id="research",
        title="Research Agent",
        description="Extract key points, assumptions, and follow-up questions.",
        template=(
            "Goal: {goal}\n"
            "Audience: {audience}\n"
            "Tone: {tone}\n\n"
            "Analyze this content and produce:\n"
            "1. Key points\n"
            "2. Open questions\n"
            "3. Suggested next actions\n\n"
            "{selection}{document}"
        ),
    ),
    AgentProfile(
        agent_id="summarize",
        title="Summarize Agent",
        description="Produce concise or structured summaries.",
        template=(
            "Goal: {goal}\n"
            "Audience: {audience}\n"
            "Tone: {tone}\n\n"
            "Summarize this content in plain language:\n\n{selection}{document}"
        ),
    ),
    AgentProfile(
        agent_id="qa",
        title="QA Agent",
        description="Review writing quality and suggest precise improvements.",
        template=(
            "Goal: {goal}\n"
            "Audience: {audience}\n"
            "Tone: {tone}\n\n"
            "Review this content for clarity, logic, and correctness. "
            "Return issues, severity, and suggested edits:\n\n{selection}{document}"
        ),
    ),
    AgentProfile(
        agent_id="accessibility",
        title="Accessibility Agent",
        description="Evaluate readability and accessibility-oriented writing quality.",
        template=(
            "Goal: {goal}\n"
            "Audience: {audience}\n"
            "Tone: {tone}\n\n"
            "Audit this content for readability and accessibility. "
            "Suggest improvements that keep meaning intact:\n\n{selection}{document}"
        ),
    ),
    AgentProfile(
        agent_id="expand",
        title="Expand Agent",
        description="Expand a brief outline or passage into fuller prose.",
        template=(
            "Goal: {goal}\n"
            "Audience: {audience}\n"
            "Tone: {tone}\n\n"
            "Expand the following into well-developed prose. Add detail, examples, "
            "and transitions as appropriate. Return only the expanded text:\n\n"
            "{selection}{document}"
        ),
    ),
    AgentProfile(
        agent_id="toc",
        title="Table of Contents Agent",
        description="Generate a structured table of contents from document headings.",
        template=(
            "Goal: {goal}\n"
            "Audience: {audience}\n"
            "Tone: {tone}\n\n"
            "Analyse the following document and produce a hierarchical table of contents "
            "using Markdown nested list syntax. Include only headings that appear in the "
            "text. Return only the table of contents:\n\n{document}{selection}"
        ),
    ),
)


def agent_profiles() -> list[AgentProfile]:
    return list(_AGENT_PROFILES)


def find_agent_profile(agent_id: str) -> AgentProfile | None:
    normalized = agent_id.strip().lower()
    for profile in _AGENT_PROFILES:
        if profile.agent_id == normalized:
            return profile
    return None


def build_agent_plan(
    agent_id: str,
    *,
    selection_text: str,
    document_text: str,
    goal: str = "",
    audience: str = "",
    tone: str = "",
) -> AgentPlan | None:
    profile = find_agent_profile(agent_id)
    if profile is None:
        return None
    prompt = render_prompt_template(
        profile.template,
        values={
            "selection": selection_text.strip(),
            "document": document_text.strip(),
            "goal": goal.strip() or "Help me complete this writing task.",
            "audience": audience.strip() or "General readers",
            "tone": tone.strip() or "Clear and practical",
        },
    )
    checks = (
        "Preview changes before applying.",
        "Require explicit approval for document edits.",
        "Avoid sending sensitive text without user consent.",
    )
    return AgentPlan(profile=profile, prompt=prompt, checks=checks)
