"""Skill Quill Pack (.sqp) — multi-step AI workflow engine.

A .sqp file is a Markdown document with a simple YAML front matter block.
Level-1 headings (`# Step N: ...`) define steps; the body between headings is
the prompt text sent to the AI model. Special fenced code blocks inside a step
control data injection, conditional branching, and result handling.

Schema identifier: ``quill.skill/1``

No wx imports; no threading. The caller provides a ``send_fn`` and handles
threading itself.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

from quill.core.error_codes import CodedError

SQP_SCHEMA = "quill.skill/1"

_VALID_PARAM_TYPES = {"text", "multiline", "choice", "bool", "number"}
_VALID_OPERATORS = {
    "contains",
    "equals",
    "starts_with",
    "ends_with",
    "length_gt",
    "length_lt",
    "is_empty",
}
_VALID_ACCEPT_INTO = {"selection", "clipboard", "none"}
_VALID_OUTPUT_FORMATS = {"text", "list", "json"}


class SkillValidationError(CodedError):
    """Raised by :func:`parse_skill` when the .sqp source is invalid."""

    code = "QUILL-SKILL-VALIDATION"

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


@dataclass(frozen=True, slots=True)
class SkillParameter:
    name: str
    label: str
    type: str = "text"
    choices: tuple[str, ...] = ()
    default: str = ""


@dataclass(frozen=True, slots=True)
class ConditionBlock:
    if_expr: str
    operator: str
    value: str
    then_step: int
    else_step: int


@dataclass(frozen=True, slots=True)
class OutputBlock:
    format: str = "text"
    label: str = "Result"
    accept_into: str = "none"


@dataclass(frozen=True, slots=True)
class UsePromptBlock:
    name: str
    input_expr: str = "{selection}"


@dataclass(frozen=True, slots=True)
class UseSkillBlock:
    name: str
    input_expr: str = "{selection}"
    parameters: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class SkillStep:
    index: int
    heading: str
    prompt_template: str
    input_block: str | None = None
    condition: ConditionBlock | None = None
    output: OutputBlock | None = None
    use_prompt: UsePromptBlock | None = None
    use_skill: UseSkillBlock | None = None


@dataclass(slots=True)
class SkillPack:
    schema: str
    name: str
    description: str
    author: str
    version: str
    parameters: list[SkillParameter]
    steps: list[SkillStep]


@dataclass(slots=True)
class StepResult:
    step_index: int
    step_heading: str
    prompt_sent: str
    output_text: str
    skipped: bool = False


# ---------------------------------------------------------------------------
# Frontmatter parser (minimal YAML subset — avoids PyYAML dependency)
# ---------------------------------------------------------------------------


def _parse_frontmatter(source: str) -> tuple[dict[str, object], str]:
    """Split YAML front matter from body. Returns (meta, body)."""
    if not source.startswith("---"):
        return {}, source
    rest = source[3:]
    nl = rest.find("\n")
    if nl == -1:
        return {}, source
    after_first_dash = rest[nl + 1 :]
    end = after_first_dash.find("\n---")
    if end == -1:
        return {}, source
    yaml_text = after_first_dash[:end]
    body = after_first_dash[end + 4 :].lstrip("\n")
    return _parse_simple_yaml(yaml_text), body


def _parse_inline_list(text: str) -> list[str]:
    """Parse `[a, b, c]` inline YAML list."""
    text = text.strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    return [item.strip().strip("\"'") for item in text.split(",") if item.strip()]


def _parse_simple_yaml(text: str) -> dict[str, object]:
    """Parse a tiny YAML subset sufficient for .sqp front matter."""
    result: dict[str, object] = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.strip().startswith("#"):
            i += 1
            continue
        indent = len(line) - len(line.lstrip())
        if indent > 0:
            i += 1
            continue
        if ":" not in line:
            i += 1
            continue
        key, _, raw_value = line.partition(":")
        key = key.strip()
        raw_value = raw_value.strip()
        if raw_value == "" or raw_value is None:
            # Expect a list on subsequent lines
            items: list[dict[str, str]] = []
            i += 1
            while i < len(lines):
                sub = lines[i]
                sub_indent = len(sub) - len(sub.lstrip())
                if sub_indent == 0 and sub.strip() and not sub.strip().startswith("-"):
                    break
                if sub.lstrip().startswith("- "):
                    obj: dict[str, str] = {}
                    kv_text = sub.lstrip()[2:]
                    if ":" in kv_text:
                        k2, _, v2 = kv_text.partition(":")
                        obj[k2.strip()] = v2.strip().strip("\"'")
                    i += 1
                    while i < len(lines):
                        deeper = lines[i]
                        deeper_indent = len(deeper) - len(deeper.lstrip())
                        if deeper_indent <= sub_indent:
                            break
                        if ":" in deeper:
                            k3, _, v3 = deeper.partition(":")
                            k3s = k3.strip()
                            v3s = v3.strip().strip("\"'")
                            if v3s.startswith("["):
                                obj[k3s] = _parse_inline_list(v3s)  # type: ignore[assignment]
                            else:
                                obj[k3s] = v3s
                        i += 1
                    items.append(obj)
                else:
                    i += 1
            result[key] = items
        else:
            value: object
            if raw_value.lower() in ("true", "yes"):
                value = True
            elif raw_value.lower() in ("false", "no"):
                value = False
            elif raw_value.isdigit():
                value = int(raw_value)
            else:
                value = raw_value.strip("\"'")
            result[key] = value
            i += 1
    return result


# ---------------------------------------------------------------------------
# Step body parser
# ---------------------------------------------------------------------------


def _extract_fenced_blocks(body: str) -> tuple[str, dict[str, str]]:
    """Remove fenced blocks from body, return (clean_prompt, blocks).

    ``blocks`` maps block type -> content.  Only the last block of each type
    is kept, which is correct since each step has at most one of each.
    """
    blocks: dict[str, str] = {}
    # Match ```type\ncontent\n``` (no nested fences)
    pattern = re.compile(r"^```(\w[\w-]*)\n(.*?)\n```", re.MULTILINE | re.DOTALL)

    def _replace(m: re.Match[str]) -> str:
        blocks[m.group(1)] = m.group(2).strip()
        return ""

    clean = pattern.sub(_replace, body).strip()
    return clean, blocks


def _parse_condition(text: str, step_count_hint: int) -> ConditionBlock | None:
    """Parse the condition block body."""
    data: dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            # Preserve raw value — the `if:` line contains quotes as syntax
            data[k.strip()] = v.strip()
    if not data.get("if") or not data.get("then"):
        return None
    # Parse `if` expression: `"{var}" operator "value"` or `"{var}" is_empty`
    if_text = data["if"]
    if_match = re.match(
        r'^"([^"]+)"\s+(\w+)(?:\s+"([^"]*)")?$',
        if_text,
    )
    if not if_match:
        return None
    if_expr = if_match.group(1)
    operator = if_match.group(2)
    value = if_match.group(3) or ""

    def _parse_step_ref(s: str) -> int:
        m = re.match(r"step(\d+)", s.strip(), re.IGNORECASE)
        return int(m.group(1)) if m else 0

    then_step = _parse_step_ref(data.get("then", ""))
    else_step = _parse_step_ref(data.get("else", ""))
    return ConditionBlock(
        if_expr=if_expr,
        operator=operator,
        value=value,
        then_step=then_step,
        else_step=else_step,
    )


def _parse_output(text: str) -> OutputBlock:
    data: dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            data[k.strip()] = v.strip().strip("\"'")
    return OutputBlock(
        format=data.get("format", "text"),
        label=data.get("label", "Result"),
        accept_into=data.get("accept_into", "none"),
    )


def _parse_use_prompt(text: str) -> UsePromptBlock:
    data: dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            data[k.strip()] = v.strip().strip("\"'")
    return UsePromptBlock(
        name=data.get("name", ""),
        input_expr=data.get("input", "{selection}"),
    )


def _parse_use_skill(text: str) -> UseSkillBlock:
    data: dict[str, str] = {}
    params: dict[str, str] = {}
    in_params = False
    for line in text.splitlines():
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if ":" not in line:
            continue
        k, _, v = stripped.partition(":")
        k = k.strip()
        v = v.strip().strip("\"'")
        if k == "parameters":
            in_params = True
        elif in_params and indent > 0:
            params[k] = v
        else:
            in_params = False
            data[k] = v
    return UseSkillBlock(
        name=data.get("name", ""),
        input_expr=data.get("input", "{selection}"),
        parameters=params,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_skill(source: str) -> SkillPack:
    """Parse .sqp source text into a :class:`SkillPack`.

    Raises :class:`SkillValidationError` on structural problems.
    """
    meta, body = _parse_frontmatter(source)
    errors: list[str] = []

    schema = str(meta.get("schema", ""))
    if schema != SQP_SCHEMA:
        errors.append(f"schema must be '{SQP_SCHEMA}', got '{schema}'")

    name = str(meta.get("name", "")).strip()
    if not name:
        errors.append("front matter must include 'name'")

    description = str(meta.get("description", "")).strip()
    author = str(meta.get("author", "")).strip()
    version = str(meta.get("version", "1.0.0")).strip()

    # Parameters
    parameters: list[SkillParameter] = []
    raw_params = meta.get("parameters", [])
    if isinstance(raw_params, list):
        for idx, raw in enumerate(raw_params):
            if not isinstance(raw, dict):
                errors.append(f"parameter[{idx}] must be a mapping")
                continue
            pname = str(raw.get("name", "")).strip()
            if not pname:
                errors.append(f"parameter[{idx}] missing 'name'")
                pname = f"param{idx}"
            ptype = str(raw.get("type", "text")).strip()
            if ptype not in _VALID_PARAM_TYPES:
                errors.append(f"parameter '{pname}': unknown type '{ptype}'")
            raw_choices = raw.get("choices", [])
            choices = tuple(str(c) for c in (raw_choices if isinstance(raw_choices, list) else []))
            if ptype == "choice" and not choices:
                errors.append(f"parameter '{pname}': type 'choice' requires 'choices' list")
            parameters.append(
                SkillParameter(
                    name=pname,
                    label=str(raw.get("label", pname)),
                    type=ptype,
                    choices=choices,
                    default=str(raw.get("default", "")),
                )
            )

    # Steps: split on H1 headings
    steps: list[SkillStep] = []
    step_pattern = re.compile(r"^# (.+)$", re.MULTILINE)
    parts = step_pattern.split(body)
    # parts alternates: [preamble, heading1, body1, heading2, body2, ...]
    if len(parts) < 3:
        errors.append("skill must have at least one step (a '# Heading' line)")
        if errors:
            raise SkillValidationError(errors)
        return SkillPack(schema, name, description, author, version, parameters, steps)

    for i in range(1, len(parts), 2):
        heading = parts[i].strip()
        step_body = parts[i + 1] if i + 1 < len(parts) else ""
        idx = (i // 2) + 1
        clean_prompt, blocks = _extract_fenced_blocks(step_body)
        step = SkillStep(
            index=idx,
            heading=heading,
            prompt_template=clean_prompt,
            input_block=blocks.get("input"),
            condition=(
                _parse_condition(blocks["condition"], len(parts) // 2)
                if "condition" in blocks
                else None
            ),
            output=_parse_output(blocks["output"]) if "output" in blocks else None,
            use_prompt=_parse_use_prompt(blocks["use-prompt"]) if "use-prompt" in blocks else None,
            use_skill=_parse_use_skill(blocks["use-skill"]) if "use-skill" in blocks else None,
        )
        steps.append(step)

    if errors:
        raise SkillValidationError(errors)
    return SkillPack(schema, name, description, author, version, parameters, steps)


def validate_skill(pack: SkillPack) -> list[str]:
    """Return a list of semantic validation errors (empty = valid)."""
    errors: list[str] = []
    param_names = {p.name for p in pack.parameters}
    n_steps = len(pack.steps)

    # Check variable references in each step
    var_pattern = re.compile(r"\{([^}]+)\}")
    for step in pack.steps:
        for text in (step.prompt_template, step.input_block or ""):
            for m in var_pattern.finditer(text):
                ref = m.group(1)
                if ref in ("selection", "document", "title", "clipboard"):
                    continue
                sm = re.match(r"step(\d+)\.output$", ref)
                if sm:
                    target = int(sm.group(1))
                    if target >= step.index:
                        errors.append(
                            f"step {step.index}: {{step{target}.output}} references a step "
                            f"that hasn't run yet"
                        )
                    continue
                pm = re.match(r"parameters\.(.+)$", ref)
                if pm:
                    pname = pm.group(1)
                    if pname not in param_names:
                        errors.append(
                            f"step {step.index}: {{parameters.{pname}}} references "
                            f"unknown parameter '{pname}'"
                        )
                    continue
                errors.append(f"step {step.index}: unknown variable '{{{ref}}}'")

        # Condition targets
        if step.condition:
            c = step.condition
            if c.operator not in _VALID_OPERATORS:
                errors.append(f"step {step.index}: condition operator '{c.operator}' is not valid")
            for target, label in ((c.then_step, "then"), (c.else_step, "else")):
                if target < 1 or target > n_steps:
                    errors.append(
                        f"step {step.index}: condition '{label}'"
                        f" target step{target} is out of range"
                    )

        # Output block
        if step.output:
            out = step.output
            if out.format not in _VALID_OUTPUT_FORMATS:
                errors.append(f"step {step.index}: output format '{out.format}' is invalid")
            if out.accept_into not in _VALID_ACCEPT_INTO:
                errors.append(
                    f"step {step.index}: output accept_into '{out.accept_into}' is invalid"
                )

        # use-prompt and use-skill must not both be set
        if step.use_prompt and step.use_skill:
            errors.append(f"step {step.index}: cannot have both use-prompt and use-skill blocks")

    return errors


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

_MAX_SKILL_DEPTH = 2


def _interpolate(template: str, ctx: dict[str, str]) -> str:
    """Replace ``{variable}`` references in ``template`` using ``ctx``."""

    def _replace(m: re.Match[str]) -> str:
        return ctx.get(m.group(1), m.group(0))

    return re.sub(r"\{([^}]+)\}", _replace, template)


def _eval_condition(cond: ConditionBlock, ctx: dict[str, str]) -> bool:
    """Return True if the 'then' branch should be taken."""
    subject = _interpolate("{" + cond.if_expr + "}", ctx)
    value = cond.value
    op = cond.operator
    if op == "contains":
        return value.lower() in subject.lower()
    if op == "equals":
        return subject.strip().lower() == value.strip().lower()
    if op == "starts_with":
        return subject.lower().startswith(value.lower())
    if op == "ends_with":
        return subject.lower().endswith(value.lower())
    if op == "length_gt":
        return len(subject) > int(value) if value.isdigit() else False
    if op == "length_lt":
        return len(subject) < int(value) if value.isdigit() else False
    if op == "is_empty":
        return not subject.strip()
    return False


def run_skill(
    pack: SkillPack,
    context: dict[str, str],
    send_fn: Callable[[str], str],
    *,
    depth: int = 0,
) -> list[StepResult]:
    """Execute a :class:`SkillPack` and return all step results.

    ``context`` should contain: ``selection``, ``document``, ``title``,
    ``clipboard``, and any ``parameters.<name>`` keys.

    ``send_fn`` is called synchronously for each step that sends to AI;
    it receives the final prompt string and must return the response text.

    Raises ``RecursionError`` when nested skill depth exceeds
    :data:`_MAX_SKILL_DEPTH`.
    """
    if depth > _MAX_SKILL_DEPTH:
        raise RecursionError(f"Skill nesting depth {depth} exceeds maximum ({_MAX_SKILL_DEPTH})")

    results: list[StepResult] = []
    step_outputs: dict[str, str] = {}

    # Build a mutable context that gets step outputs added as we run
    ctx = dict(context)

    current_step_index = 1
    while current_step_index <= len(pack.steps):
        step = pack.steps[current_step_index - 1]

        # Determine the prompt to send
        if step.use_prompt:
            use_input = _interpolate(step.use_prompt.input_expr, ctx)
            prompt = _interpolate(step.prompt_template or step.use_prompt.input_expr, ctx)
            if not prompt:
                prompt = use_input
        elif step.use_skill:
            use_input = _interpolate(step.use_skill.input_expr, ctx)
            prompt = use_input
        else:
            prompt = _interpolate(step.prompt_template, ctx)
            if step.input_block:
                injected = _interpolate(step.input_block, ctx)
                if injected:
                    prompt = f"{prompt}\n\n{injected}" if prompt else injected

        # Call the AI (or delegate to a nested skill)
        if step.use_skill and step.use_skill.name:
            output_text = f"[use-skill '{step.use_skill.name}' — not yet resolved by runner]"
        else:
            output_text = send_fn(prompt) if prompt.strip() else ""

        # Store output
        step_outputs[f"step{step.index}.output"] = output_text
        ctx[f"step{step.index}.output"] = output_text

        results.append(
            StepResult(
                step_index=step.index,
                step_heading=step.heading,
                prompt_sent=prompt,
                output_text=output_text,
            )
        )

        # Determine next step
        if step.condition:
            branch_taken = _eval_condition(step.condition, ctx)
            next_index = step.condition.then_step if branch_taken else step.condition.else_step
            if next_index < 1 or next_index > len(pack.steps):
                break
            current_step_index = next_index
        else:
            current_step_index += 1

    return results
