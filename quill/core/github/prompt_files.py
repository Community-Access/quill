"""GitHub Models prompt files in a repository, read as structure (complete.md 1.3).

A prompt file is YAML named ``*.prompt.yml`` (or ``.prompt.yaml``) that GitHub
Models reads: a ``name`` and ``description``, the ``model`` and its
``modelParameters``, the ``messages`` (each a ``role`` and its ``content``,
with ``{{variables}}``), ``testData`` rows that fill the variables, and
``evaluators`` that judge each answer. This module finds them
(:func:`find_prompt_files`, one recursive tree read) and reads one
(:func:`describe`) as lines a screen reader moves through, with every problem
GitHub Models would trip on said plainly: no model, no messages, a role it does
not know, a variable no test row fills.

QUILL has no GitHub Models client, so it does not run a prompt or an
evaluation; :data:`RUN_ELSEWHERE` says where that is done. Editing is the
editor's: Open in Editor opens the file from GitHub, and saving it commits.

wx-free and strict-typed.
"""

from __future__ import annotations

import base64
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.github.workbench_api import GitHubApi

__all__ = [
    "PROMPT_SUFFIXES",
    "RUN_ELSEWHERE",
    "PromptFile",
    "PromptFileError",
    "PromptFiles",
    "describe",
    "find_prompt_files",
    "read_prompt_file",
]

PROMPT_SUFFIXES = (".prompt.yml", ".prompt.yaml")
RUN_ELSEWHERE = (
    "QUILL reads and edits prompt files but does not run them: it has no GitHub Models "
    "client. Run one on the repository's Models page on GitHub, or with gh models run "
    "and gh models eval."
)
_ROLES = frozenset({"system", "user", "assistant", "developer"})
_VARIABLE = re.compile(r"\{\{\s*([A-Za-z_][\w.-]*)\s*\}\}")


class PromptFileError(CodedError):
    """A prompt file could not be found or read; the message is safe to speak."""

    code = "QUILL-GITHUB-PROMPT-FILE"


@dataclass(frozen=True)
class PromptFiles:
    """The prompt files on a branch, and whether GitHub listed the whole tree."""

    ref: str
    paths: tuple[str, ...]
    complete: bool = True

    @property
    def sentence(self) -> str:
        count = len(self.paths)
        found = (
            f"{count} prompt file{'s' if count != 1 else ''} on {self.ref}"
            if count
            else f"No prompt files (.prompt.yml) on {self.ref}"
        )
        cut = " GitHub listed only part of this large repository." if not self.complete else ""
        return f"{found}.{cut}"


def find_prompt_files(api: GitHubApi, repository: str, ref: str = "") -> PromptFiles:
    """Every ``*.prompt.yml`` on *ref* (the default branch when empty)."""
    if not ref:
        ref = str((api.rest("GET", f"/repos/{repository}").data or {}).get("default_branch"))
    try:
        data = api.rest(
            "GET", f"/repos/{repository}/git/trees/{ref}", query={"recursive": "1"}
        ).data
    except Exception as exc:  # noqa: BLE001 - said as one sentence
        raise PromptFileError(f"Could not list {repository}'s files on {ref}: {exc}") from exc
    rows = data.get("tree") if isinstance(data, Mapping) else None
    paths = sorted(
        str(row.get("path"))
        for row in rows or ()
        if isinstance(row, Mapping)
        and row.get("type") == "blob"
        and str(row.get("path") or "").lower().endswith(PROMPT_SUFFIXES)
    )
    complete = not (isinstance(data, Mapping) and data.get("truncated"))
    return PromptFiles(ref, tuple(paths), complete)


def read_prompt_file(api: GitHubApi, repository: str, path: str, ref: str) -> str:
    """The file's text at *ref*."""
    data = api.rest("GET", f"/repos/{repository}/contents/{path}", query={"ref": ref}).data
    content = data.get("content") if isinstance(data, Mapping) else None
    if not isinstance(content, str):
        raise PromptFileError(f"GitHub did not send the text of {path}.")
    return base64.b64decode(content).decode("utf-8", errors="replace")


@dataclass(frozen=True)
class PromptFile:
    """One prompt file's parts, and what is wrong with it."""

    name: str = ""
    description: str = ""
    model: str = ""
    parameters: tuple[tuple[str, str], ...] = ()
    messages: tuple[tuple[str, str], ...] = ()
    test_rows: int = 0
    evaluators: tuple[str, ...] = ()
    response_format: str = ""
    problems: tuple[str, ...] = field(default=())

    def lines(self, path: str = "") -> list[str]:
        out = [f"File: {path}"] if path else []
        out += [
            f"Name: {self.name or 'not given'}",
            f"Description: {self.description or 'not given'}",
            f"Model: {self.model or 'not given'}",
        ]
        out += [f"Parameter {key}: {value}" for key, value in self.parameters]
        if self.response_format:
            out.append(f"Response format: {self.response_format}")
        out.append(f"{len(self.messages)} messages:")
        for index, (role, content) in enumerate(self.messages, 1):
            first = content.strip().splitlines()[0] if content.strip() else "(empty)"
            more = " ..." if len(content.strip().splitlines()) > 1 else ""
            out.append(f"  {index}. {role}: {first}{more}")
        out.append(f"Test data: {self.test_rows} rows.")
        out.append(
            f"Evaluators: {', '.join(self.evaluators)}." if self.evaluators else "Evaluators: none."
        )
        out += [f"Problem: {problem}" for problem in self.problems] or ["No problems found."]
        out.append(RUN_ELSEWHERE)
        return out


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def describe(text: str) -> PromptFile:
    """The parts of a prompt file's YAML; a file that is not valid YAML is one problem."""
    import yaml  # type: ignore[import-untyped]

    try:
        data = yaml.safe_load(text or "")
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        where = f" at line {mark.line + 1}" if mark is not None else ""
        return PromptFile(problems=(f"It is not valid YAML{where}.",))
    if not isinstance(data, Mapping):
        return PromptFile(problems=("It is not a prompt file: the top is not a set of keys.",))
    problems: list[str] = []
    model = _text(data.get("model"))
    if not model:
        problems.append("It names no model.")
    raw_params = data.get("modelParameters")
    params = (
        tuple((str(k), _text(v)) for k, v in raw_params.items())
        if isinstance(raw_params, Mapping)
        else ()
    )
    messages: list[tuple[str, str]] = []
    for index, message in enumerate(data.get("messages") or (), 1):
        if not isinstance(message, Mapping):
            problems.append(f"Message {index} is not a role and its content.")
            continue
        role = _text(message.get("role"))
        if role not in _ROLES:
            problems.append(f"Message {index} has the role {role or 'none'}, which is not known.")
        messages.append((role or "unknown", _text(message.get("content"))))
    if not messages:
        problems.append("It has no messages.")
    tests = [row for row in data.get("testData") or () if isinstance(row, Mapping)]
    used = {name for _role, content in messages for name in _VARIABLE.findall(content)}
    for name in sorted(used):
        missing = sum(1 for row in tests if name not in row)
        if not tests:
            problems.append(f"The variable {name} is used, but there is no test data to fill it.")
            break
        if missing:
            problems.append(f"The variable {name} is missing from {missing} test rows.")
    evaluators = tuple(
        _text(e.get("name")) or "unnamed"
        for e in data.get("evaluators") or ()
        if isinstance(e, Mapping)
    )
    return PromptFile(
        name=_text(data.get("name")),
        description=_text(data.get("description")),
        model=model,
        parameters=params,
        messages=tuple(messages),
        test_rows=len(tests),
        evaluators=evaluators,
        response_format=_text(data.get("responseFormat")),
        problems=tuple(problems),
    )
