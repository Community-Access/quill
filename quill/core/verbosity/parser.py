"""Strict verbosity template parser and validator (verbosity §12-§13).

Templates use exactly three placeholder forms and nothing else:

- ``{name}`` — a bare token.
- ``${filter:name}`` — a token passed through one engine filter.
- ``${filter:arg:name}`` — a filter that takes an argument, e.g. ``${pad:3:line}``.

The parser is deliberately strict and **never raises to its callers**: malformed
input comes back as structured :class:`TemplateError` entries in a
:class:`ParseResult`, so the editor can show problems inline instead of crashing.
:func:`validate` adds the verbosity §13 contract on top: every token must be in
the verb's allowlist, every filter must exist, be allowed for the token's type,
and be in the token's own filter allowlist, and argument-taking filters must get
a valid argument.

Pure and wx-free.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from quill.core.verbosity.tokens import (
    TokenSpec,
    apply_filter,
    filter_allowed_for_type,
    get_filter,
)

if TYPE_CHECKING:
    from quill.core.verbosity.verbs import VerbSpec

__all__ = [
    "LiteralSegment",
    "TokenSegment",
    "TemplateError",
    "ParseResult",
    "ValidationIssue",
    "ValidationReport",
    "parse",
    "validate",
    "render_template",
]

# Matches ${...} (filtered) first, then {...} (bare). Braces may not nest.
_PLACEHOLDER_RE = re.compile(r"\$\{(?P<filtered>[^{}]*)\}|\{(?P<bare>[^{}]*)\}")
_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True, slots=True)
class LiteralSegment:
    """A run of literal text between placeholders."""

    text: str


@dataclass(frozen=True, slots=True)
class TokenSegment:
    """A parsed placeholder: a token, an optional filter, and an optional arg."""

    name: str
    filter: str | None
    arg: str | None
    raw: str
    position: int


@dataclass(frozen=True, slots=True)
class TemplateError:
    """A structured parse problem with the source offset that caused it."""

    message: str
    position: int


@dataclass(frozen=True, slots=True)
class ParseResult:
    """The outcome of parsing a template: segments plus any parse errors."""

    segments: tuple[LiteralSegment | TokenSegment, ...]
    errors: tuple[TemplateError, ...]

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def tokens(self) -> tuple[TokenSegment, ...]:
        return tuple(seg for seg in self.segments if isinstance(seg, TokenSegment))


def _parse_placeholder(body: str, raw: str, position: int) -> TokenSegment | TemplateError:
    """Parse one placeholder body into a :class:`TokenSegment` or an error."""
    if raw.startswith("${"):
        parts = body.split(":")
        if len(parts) == 2:
            filter_name, name = parts[0], parts[1]
            arg: str | None = None
        elif len(parts) == 3:
            filter_name, arg, name = parts[0], parts[1], parts[2]
        else:
            return TemplateError(
                f"Malformed placeholder '{raw}': expected ${{filter:name}} or ${{filter:arg:name}}",
                position,
            )
        if not filter_name:
            return TemplateError(f"Empty filter in '{raw}'", position)
    else:
        if ":" in body:
            return TemplateError(
                f"Bare token '{raw}' may not contain ':'; use ${{filter:name}} for filters",
                position,
            )
        filter_name = None
        arg = None
        name = body
    if not _NAME_RE.match(name):
        return TemplateError(f"Invalid token name '{name}' in '{raw}'", position)
    return TokenSegment(name=name, filter=filter_name, arg=arg, raw=raw, position=position)


def parse(template: str) -> ParseResult:
    """Parse ``template`` into segments, collecting any structured errors.

    Never raises: malformed placeholders become :class:`TemplateError` entries
    while the rest of the template still parses.
    """
    segments: list[LiteralSegment | TokenSegment] = []
    errors: list[TemplateError] = []
    cursor = 0

    def _emit_literal(text: str, start: int) -> None:
        """Add a literal run, flagging any stray (unmatched) brace it contains."""
        if not text:
            return
        segments.append(LiteralSegment(text))
        for offset, char in enumerate(text):
            if char in "{}":
                errors.append(
                    TemplateError("Unbalanced or stray brace in template", start + offset)
                )
                break

    for match in _PLACEHOLDER_RE.finditer(template):
        if match.start() > cursor:
            _emit_literal(template[cursor : match.start()], cursor)
        body = match.group("filtered")
        if body is None:
            body = match.group("bare")
        outcome = _parse_placeholder(body, match.group(0), match.start())
        if isinstance(outcome, TemplateError):
            errors.append(outcome)
        else:
            segments.append(outcome)
        cursor = match.end()
    if cursor < len(template):
        _emit_literal(template[cursor:], cursor)
    return ParseResult(segments=tuple(segments), errors=tuple(errors))


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One validation finding: an error or a warning at a source offset."""

    severity: str  # "error" | "warning"
    message: str
    position: int


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """The result of validating a template against a verb's token allowlist."""

    issues: tuple[ValidationIssue, ...]
    token_count: int

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "error")

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "warning")

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def spoken_summary(self) -> str:
        """The §13 spoken summary, e.g. ``Validation: 3 tokens, 1 warning, 0 errors.``"""
        n_warn = len(self.warnings)
        n_err = len(self.errors)
        return (
            f"Validation: {self.token_count} "
            f"token{'s' if self.token_count != 1 else ''}, "
            f"{n_warn} warning{'s' if n_warn != 1 else ''}, "
            f"{n_err} error{'s' if n_err != 1 else ''}."
        )


def validate(template: str, verb: VerbSpec) -> ValidationReport:
    """Validate ``template`` against ``verb``'s token allowlist (verbosity §13).

    Errors: unknown token, unknown filter, filter not allowed for the token's
    type, filter not in the token's own allowlist, missing/extra filter argument,
    and any structural parse error.
    """
    parsed = parse(template)
    issues: list[ValidationIssue] = [
        ValidationIssue("error", err.message, err.position) for err in parsed.errors
    ]
    specs: dict[str, TokenSpec] = {tok.name: tok for tok in verb.supported_tokens}
    for segment in parsed.tokens:
        spec = specs.get(segment.name)
        if spec is None:
            issues.append(
                ValidationIssue(
                    "error",
                    f"Unknown token '{segment.name}'; this verb does not track it",
                    segment.position,
                )
            )
            continue
        if segment.filter is None:
            continue
        filter_spec = get_filter(segment.filter)
        if filter_spec is None:
            issues.append(
                ValidationIssue("error", f"Unknown filter '{segment.filter}'", segment.position)
            )
            continue
        if segment.filter not in spec.filters:
            issues.append(
                ValidationIssue(
                    "error",
                    f"Filter '{segment.filter}' is not allowed on token '{segment.name}'",
                    segment.position,
                )
            )
            continue
        if not filter_allowed_for_type(filter_spec, spec.type):
            issues.append(
                ValidationIssue(
                    "error",
                    f"Filter '{segment.filter}' cannot be used on a {spec.type.value} token",
                    segment.position,
                )
            )
        if filter_spec.requires_arg and segment.arg is None:
            issues.append(
                ValidationIssue(
                    "error", f"Filter '{segment.filter}' requires an argument", segment.position
                )
            )
        if filter_spec.requires_arg and segment.arg is not None and not segment.arg.isdigit():
            issues.append(
                ValidationIssue(
                    "error",
                    f"Filter '{segment.filter}' argument must be a number",
                    segment.position,
                )
            )
        if not filter_spec.requires_arg and segment.arg is not None:
            issues.append(
                ValidationIssue(
                    "warning",
                    f"Filter '{segment.filter}' ignores its argument",
                    segment.position,
                )
            )
    return ValidationReport(issues=tuple(issues), token_count=len(parsed.tokens))


def render_template(
    template: str, values: dict[str, Any], token_specs: tuple[TokenSpec, ...]
) -> str:
    """Render ``template`` with ``values`` (best-effort; for preview and tests).

    Missing values leave the placeholder's raw text in place. Filter errors fall
    back to the unfiltered value. Validation via :func:`validate` is the right
    gate before relying on output; this is a convenience renderer.
    """
    known = {spec.name for spec in token_specs}
    parsed = parse(template)
    out: list[str] = []
    for segment in parsed.segments:
        if isinstance(segment, LiteralSegment):
            out.append(segment.text)
            continue
        if segment.name not in known or segment.name not in values:
            out.append(segment.raw)
            continue
        value = values[segment.name]
        if segment.filter is None:
            out.append(str(value))
            continue
        try:
            out.append(apply_filter(segment.filter, value, segment.arg))
        except (KeyError, TypeError, ValueError):
            out.append(str(value))
    return "".join(out)
