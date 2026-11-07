"""Accessibility Tune-Up: a consented, announced, reversible accessibility plan.

This module is the deterministic core of the "Accessibility Tune-Up" feature
(AGENT-1). It audits a document's structure, alt text, link text, Mermaid
diagrams, and plain language, then proposes an ordered plan of discrete steps.
Each step is reviewable on its own (a before/after snippet and a plain-language
rationale) and the user accepts or skips each one before anything is applied.

The engine is UI-framework-agnostic: it imports no ``wx``. It reuses the
existing text-level audit primitives in :mod:`quill.core.glow` and
:mod:`quill.core.plain_language` rather than depending on any networked or
GLOW-platform engine, so it stands on its own for QUILL 1.0.

The contract is intentionally small:

* :func:`build_plan` scans text and returns an :class:`AccessibilityPlan` whose
  ``steps`` describe every proposed change.
* :func:`apply_plan` applies only the accepted, automatically-fixable steps,
  re-audits the result, and returns an :class:`AgentRunResult` with a report of
  what changed. Applying is a single text transform so the UI can register it as
  one undo unit.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

from quill.core.glow import audit_text
from quill.core.mermaid_a11y import check_mermaid
from quill.core.plain_language import lint_plain_language

_TransformFn = Callable[[str], str]

# Category identifiers, ordered by how they are presented in a plan.
CATEGORY_STRUCTURE = "structure"
CATEGORY_ALT_TEXT = "alt-text"
CATEGORY_LINK_TEXT = "link-text"
CATEGORY_DIAGRAMS = "diagrams"
CATEGORY_PLAIN_LANGUAGE = "plain-language"
CATEGORY_CLEANUP = "cleanup"

_CATEGORY_ORDER: dict[str, int] = {
    CATEGORY_STRUCTURE: 0,
    CATEGORY_ALT_TEXT: 1,
    CATEGORY_LINK_TEXT: 2,
    CATEGORY_DIAGRAMS: 3,
    CATEGORY_PLAIN_LANGUAGE: 4,
    CATEGORY_CLEANUP: 5,
}

_GENERIC_LINK_TEXT = {
    "click here",
    "here",
    "read more",
    "more",
    "link",
    "this",
}


@dataclass(frozen=True, slots=True)
class AgentStep:
    """A single reviewable, optionally auto-fixable accessibility change.

    ``before`` and ``after`` hold the snippet the user reviews. For advisory
    steps that need human judgement (for example writing real alt text), the
    step is not automatically fixable and ``after`` equals ``before``.
    """

    step_id: str
    category: str
    title: str
    rationale: str
    before: str
    after: str
    line: int | None
    auto_fixable: bool


@dataclass(slots=True)
class AccessibilityPlan:
    """An ordered, reviewable accessibility plan for one document scope."""

    document_name: str
    markup: str
    scope_label: str
    steps: tuple[AgentStep, ...]
    findings_before: int
    _transforms: dict[str, _TransformFn] = field(default_factory=dict, repr=False, compare=False)

    @property
    def auto_fixable_steps(self) -> tuple[AgentStep, ...]:
        return tuple(step for step in self.steps if step.auto_fixable)

    @property
    def advisory_steps(self) -> tuple[AgentStep, ...]:
        return tuple(step for step in self.steps if not step.auto_fixable)


@dataclass(frozen=True, slots=True)
class AgentRunResult:
    """The outcome of applying an accepted subset of a plan."""

    text: str
    applied: tuple[AgentStep, ...]
    skipped: tuple[AgentStep, ...]
    findings_before: int
    findings_after: int
    report: str

    @property
    def changed(self) -> bool:
        return bool(self.applied)


def build_plan(
    document_name: str,
    text: str,
    markup: str,
    scope_label: str = "current document",
) -> AccessibilityPlan:
    """Scan ``text`` and return an ordered, reviewable accessibility plan."""

    steps: list[AgentStep] = []
    transforms: dict[str, _TransformFn] = {}
    counter = {"n": 0}

    def add(
        category: str,
        title: str,
        rationale: str,
        before: str,
        after: str,
        line: int | None,
        transform: _TransformFn | None,
    ) -> None:
        counter["n"] += 1
        step_id = f"{category}-{counter['n']}"
        auto = transform is not None
        steps.append(
            AgentStep(
                step_id=step_id,
                category=category,
                title=title,
                rationale=rationale,
                before=before,
                after=after if auto else before,
                line=line,
                auto_fixable=auto,
            )
        )
        if transform is not None:
            transforms[step_id] = transform

    lines = text.split("\n")

    _collect_structure_steps(lines, markup, add)
    _collect_alt_text_steps(text, lines, markup, add)
    _collect_link_text_steps(lines, markup, add)
    _collect_diagram_steps(text, markup, add)
    _collect_plain_language_steps(text, lines, add)
    _collect_cleanup_steps(text, add)

    steps.sort(
        key=lambda step: (
            _CATEGORY_ORDER.get(step.category, 99),
            step.line if step.line is not None else 0,
            step.step_id,
        )
    )

    return AccessibilityPlan(
        document_name=document_name,
        markup=markup,
        scope_label=scope_label,
        steps=tuple(steps),
        findings_before=len(audit_text(text, markup)),
        _transforms=transforms,
    )


def apply_plan(
    plan: AccessibilityPlan,
    text: str,
    accepted_ids: set[str] | frozenset[str],
) -> AgentRunResult:
    """Apply the accepted, auto-fixable steps and re-audit the result.

    Advisory steps (those needing human judgement) and steps the user skipped
    are reported as skipped. Applying is deterministic and order-stable.
    """

    updated = text
    applied: list[AgentStep] = []
    skipped: list[AgentStep] = []
    for step in plan.steps:
        transform = plan._transforms.get(step.step_id)
        if step.step_id in accepted_ids and transform is not None:
            candidate = transform(updated)
            if candidate != updated:
                updated = candidate
                applied.append(step)
                continue
        skipped.append(step)

    findings_after = len(audit_text(updated, plan.markup))
    report = build_run_report(
        plan,
        applied=tuple(applied),
        skipped=tuple(skipped),
        findings_after=findings_after,
    )
    return AgentRunResult(
        text=updated,
        applied=tuple(applied),
        skipped=tuple(skipped),
        findings_before=plan.findings_before,
        findings_after=findings_after,
        report=report,
    )


def summarize_plan(plan: AccessibilityPlan) -> str:
    """Return a short, speakable summary of a plan for announcement."""

    total = len(plan.steps)
    if total == 0:
        return (
            f"Accessibility plan for {plan.scope_label}: no actionable issues "
            "found. The document is ready for deeper human review."
        )
    auto = len(plan.auto_fixable_steps)
    advisory = total - auto
    parts = [
        f"Accessibility plan for {plan.scope_label}: {total} {'step' if total == 1 else 'steps'}"
    ]
    parts.append(f"{auto} can be applied automatically")
    if advisory:
        parts.append(f"{advisory} need your review")
    return ", ".join(parts) + "."


def build_plan_report(plan: AccessibilityPlan) -> str:
    """Return a readable, screen-reader-pageable description of a plan."""

    lines = [
        f"Accessibility Tune-Up plan for {plan.document_name}",
        "",
        f"Scope: {plan.scope_label}",
        f"Format: {plan.markup}",
        f"Findings before: {plan.findings_before}",
        f"Proposed steps: {len(plan.steps)} "
        f"({len(plan.auto_fixable_steps)} automatic, "
        f"{len(plan.advisory_steps)} need review)",
    ]
    if not plan.steps:
        lines.extend([
            "",
            "No actionable accessibility issues were detected in this scope.",
            "The document is ready for deeper human review and export checks.",
        ])
        return "\n".join(lines).rstrip() + "\n"
    lines.append("")
    lines.append("Proposed steps:")
    for index, step in enumerate(plan.steps, start=1):
        lines.extend(_describe_step(index, step))
    return "\n".join(lines).rstrip() + "\n"


def build_run_report(
    plan: AccessibilityPlan,
    *,
    applied: tuple[AgentStep, ...],
    skipped: tuple[AgentStep, ...],
    findings_after: int,
) -> str:
    """Return a readable report of what the agent changed and what remains."""

    lines = [
        f"Accessibility Tune-Up report for {plan.document_name}",
        "",
        f"Scope: {plan.scope_label}",
        f"Format: {plan.markup}",
        f"Findings before: {plan.findings_before}",
        f"Findings after: {findings_after}",
        f"Steps applied: {len(applied)}",
        f"Steps skipped or needing review: {len(skipped)}",
    ]
    if applied:
        lines.append("")
        lines.append("Applied:")
        for index, step in enumerate(applied, start=1):
            location = f" (line {step.line})" if step.line is not None else ""
            lines.append(f"{index}. {step.title}{location}")
    if skipped:
        lines.append("")
        lines.append("Skipped or needing review:")
        for index, step in enumerate(skipped, start=1):
            location = f" (line {step.line})" if step.line is not None else ""
            suffix = "" if step.auto_fixable else " [needs your review]"
            lines.append(f"{index}. {step.title}{location}{suffix}")
    lines.append("")
    if findings_after < plan.findings_before:
        removed = plan.findings_before - findings_after
        lines.append(
            f"This run resolved {removed} "
            f"{'finding' if removed == 1 else 'findings'}. "
            "Re-run the agent to review what remains."
        )
    elif applied:
        lines.append("Changes were applied. Re-run the agent to confirm the document is clean.")
    else:
        lines.append("No automatic changes were applied in this run.")
    return "\n".join(lines).rstrip() + "\n"


def _describe_step(index: int, step: AgentStep) -> list[str]:
    tag = "automatic" if step.auto_fixable else "needs review"
    location = f" (line {step.line})" if step.line is not None else ""
    out = [
        f"{index}. [{step.category}] {step.title}{location} [{tag}]",
        f"   {step.rationale}",
    ]
    if step.auto_fixable and step.after != step.before:
        out.append(f"   Before: {step.before}")
        out.append(f"   After: {step.after}")
    elif step.before:
        out.append(f"   Context: {step.before}")
    return out


# ---------------------------------------------------------------------------
# Step collectors
# ---------------------------------------------------------------------------


def _collect_structure_steps(
    lines: list[str],
    markup: str,
    add: Callable[..., None],
) -> None:
    if markup == "markdown":
        previous_level = 0
        for index, line in enumerate(lines):
            tight = re.match(r"^(#{1,6})([^\s#].*)$", line)
            if tight is not None:
                marker = tight.group(1)
                rest = tight.group(2)
                add(
                    CATEGORY_STRUCTURE,
                    "Add a space after the heading markers",
                    "Screen readers and Markdown parsers only treat the line as a "
                    "heading when a space follows the number signs.",
                    line,
                    f"{marker} {rest}",
                    index + 1,
                    _markdown_heading_space_transform(index),
                )
            spaced = re.match(r"^(#{1,6})\s+", line)
            if spaced is not None:
                level = len(spaced.group(1))
                if previous_level and level > previous_level + 1:
                    add(
                        CATEGORY_STRUCTURE,
                        "Heading level jumps by more than one",
                        "Skipping heading levels breaks the document outline that "
                        "screen-reader users rely on to navigate. Use the next "
                        "level down instead.",
                        line.strip(),
                        line.strip(),
                        index + 1,
                        None,
                    )
                previous_level = level
    elif markup == "html":
        previous_level = 0
        for index, line in enumerate(lines):
            for match in re.finditer(r"<h([1-6])\b", line, re.IGNORECASE):
                level = int(match.group(1))
                if previous_level and level > previous_level + 1:
                    add(
                        CATEGORY_STRUCTURE,
                        "Heading level jumps by more than one",
                        "Skipping heading levels breaks the document outline that "
                        "screen-reader users rely on to navigate. Use the next "
                        "level down instead.",
                        line.strip(),
                        line.strip(),
                        index + 1,
                        None,
                    )
                previous_level = level
        # Missing language attribute on the document element.
        for index, line in enumerate(lines):
            html_tag = re.search(r"<html\b([^>]*)>", line, re.IGNORECASE)
            if html_tag is not None and (
                re.search(r"\blang\s*=", html_tag.group(1), re.IGNORECASE) is None
            ):
                original = html_tag.group(0)
                fixed = re.sub(
                    r"<html\b",
                    '<html lang="en"',
                    original,
                    count=1,
                    flags=re.IGNORECASE,
                )
                add(
                    CATEGORY_STRUCTURE,
                    "Declare the document language",
                    "A missing language attribute leaves screen readers guessing "
                    "which voice and pronunciation rules to use.",
                    original,
                    fixed,
                    index + 1,
                    _replace_once_transform(original, fixed),
                )
                break


def _collect_alt_text_steps(
    text: str,
    lines: list[str],
    markup: str,
    add: Callable[..., None],
) -> None:
    if markup == "markdown":
        for index, line in enumerate(lines):
            for match in re.finditer(r"!\[([^\]]*)\]\(([^)]+)\)", line):
                label = match.group(1).strip()
                if not label:
                    add(
                        CATEGORY_ALT_TEXT,
                        "Image is missing alternative text",
                        "Every meaningful image needs alt text that conveys its "
                        "purpose. Describe the image, or mark it decorative.",
                        match.group(0),
                        match.group(0),
                        index + 1,
                        None,
                    )
    elif markup == "html":
        for index, line in enumerate(lines):
            for match in re.finditer(r"<img\b([^>]*)>", line, re.IGNORECASE):
                attributes = match.group(1)
                if re.search(r"\balt\s*=", attributes, re.IGNORECASE) is None:
                    add(
                        CATEGORY_ALT_TEXT,
                        "Image is missing an alt attribute",
                        "Without an alt attribute, screen readers may announce the "
                        "file name or nothing at all. Add a description, or use an "
                        "empty alt for decorative images.",
                        match.group(0),
                        match.group(0),
                        index + 1,
                        None,
                    )


def _collect_link_text_steps(
    lines: list[str],
    markup: str,
    add: Callable[..., None],
) -> None:
    if markup == "markdown":
        for index, line in enumerate(lines):
            for match in re.finditer(r"(?<!!)\[([^\]]*)\]\(([^)]+)\)", line):
                label = match.group(1).strip().lower()
                if label in _GENERIC_LINK_TEXT:
                    add(
                        CATEGORY_LINK_TEXT,
                        "Link text does not describe its destination",
                        "Generic link text like this is meaningless when a screen "
                        "reader lists links out of context. Rewrite it to describe "
                        "where the link goes.",
                        match.group(0),
                        match.group(0),
                        index + 1,
                        None,
                    )
    elif markup == "html":
        for index, line in enumerate(lines):
            for match in re.finditer(r"<a\b[^>]*>(.*?)</a>", line, re.IGNORECASE | re.DOTALL):
                link_text = re.sub(r"<[^>]+>", "", match.group(1)).strip().lower()
                if link_text in _GENERIC_LINK_TEXT:
                    add(
                        CATEGORY_LINK_TEXT,
                        "Link text does not describe its destination",
                        "Generic link text like this is meaningless when a screen "
                        "reader lists links out of context. Rewrite it to describe "
                        "where the link goes.",
                        match.group(0),
                        match.group(0),
                        index + 1,
                        None,
                    )


def _collect_diagram_steps(text: str, markup: str, add: Callable[..., None]) -> None:
    """Mermaid diagrams: accessible title and description, theme, colours, headings."""

    if markup != "markdown":
        return
    for finding in check_mermaid(text):
        add(
            CATEGORY_DIAGRAMS,
            finding.title,
            finding.rationale,
            finding.context,
            finding.context,
            finding.line,
            None,
        )


def _collect_plain_language_steps(
    text: str,
    lines: list[str],
    add: Callable[..., None],
) -> None:
    for issue in lint_plain_language(text):
        line_index = issue.line - 1
        replacement = _match_case(issue.phrase, issue.suggestion)
        before = lines[line_index].strip() if 0 <= line_index < len(lines) else issue.phrase
        after_line = (
            re.sub(re.escape(issue.phrase), replacement, lines[line_index], count=1).strip()
            if 0 <= line_index < len(lines)
            else replacement
        )
        add(
            CATEGORY_PLAIN_LANGUAGE,
            f'Replace "{issue.phrase}" with "{replacement}"',
            "Plainer wording is easier to read and to listen to, and it keeps the meaning intact.",
            before,
            after_line,
            issue.line,
            _plain_language_transform(line_index, issue.phrase, replacement),
        )


def _collect_cleanup_steps(text: str, add: Callable[..., None]) -> None:
    if any(line != line.rstrip() for line in text.split("\n")):
        add(
            CATEGORY_CLEANUP,
            "Trim trailing whitespace",
            "Trailing spaces can produce stray output and inconsistent spacing "
            "when the document is read aloud or exported.",
            "lines with trailing spaces",
            "lines without trailing spaces",
            None,
            _trim_trailing_whitespace_transform,
        )


# ---------------------------------------------------------------------------
# Transforms (each operates on the full document text, order-stable)
# ---------------------------------------------------------------------------


def _markdown_heading_space_transform(line_index: int) -> _TransformFn:
    def apply(text: str) -> str:
        lines = text.split("\n")
        if 0 <= line_index < len(lines):
            lines[line_index] = re.sub(r"^(#{1,6})([^\s#])", r"\1 \2", lines[line_index])
        return "\n".join(lines)

    return apply


def _plain_language_transform(line_index: int, phrase: str, replacement: str) -> _TransformFn:
    pattern = re.compile(re.escape(phrase))

    def apply(text: str) -> str:
        lines = text.split("\n")
        if 0 <= line_index < len(lines):
            lines[line_index] = pattern.sub(replacement, lines[line_index], count=1)
        return "\n".join(lines)

    return apply


def _replace_once_transform(original: str, fixed: str) -> _TransformFn:
    def apply(text: str) -> str:
        return text.replace(original, fixed, 1)

    return apply


def _trim_trailing_whitespace_transform(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.split("\n"))


def _match_case(original: str, suggestion: str) -> str:
    if original[:1].isupper():
        return suggestion[:1].upper() + suggestion[1:]
    return suggestion
