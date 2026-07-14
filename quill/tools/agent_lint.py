"""Agent standards linter (GATE) — enforce authoring quality on agent files.

:func:`quill.core.ai.agent_catalog.validate_agent` is the *load-tolerant* schema
floor: it keeps a bad file from crashing the catalog. This linter is the stricter
**authoring standard** an agent must meet to ship or be accepted — the thing that
fails when someone edits an agent and drifts from the conventions.

It checks every ``*.md`` / ``*.json`` agent (front matter + Markdown body, or
legacy JSON) for:

- schema validity (reuses ``validate_agent``);
- the file name matching the agent ``id`` (so agents stay discoverable);
- no duplicate ids across the linted set;
- a real, one-line ``description`` and a substantive ``system_prompt``;
- ``recommended_file_types`` / ``tools`` in canonical form;
- a known ``default_harness``;
- **human-in-the-loop on mutations**: a mutating permission may never be
  ``allow`` (must be ``ask`` / ``preview_required`` / ``deny``);
- high/critical agents declaring their permissions explicitly;
- scope ↔ permission coherence (warning).

Usage::

    python -m quill.tools.agent_lint quill/core/ai/agents
    python -m quill.tools.agent_lint path/to/my-agent.md --strict

Exit code is non-zero when any **error** is found (or any warning under
``--strict``). wx-free; importable so an in-app agent editor can reuse the rules.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

from quill.core.ai.agent_catalog import (
    bundled_agents_dir,
    parse_agent_markdown,
    validate_agent,
)
from quill.core.ai.permissions import Decision, PermissionCategory

__all__ = [
    "Finding",
    "ERROR",
    "WARNING",
    "lint_agent_data",
    "lint_path",
    "lint_paths",
    "lint_dir",
    "main",
]

ERROR = "error"
WARNING = "warning"

_MIN_DESCRIPTION = 12
_MAX_DESCRIPTION = 200
_MIN_SYSTEM_PROMPT = 80
_MAX_DISPLAY_NAME = 60

_FILE_TYPE_RE = re.compile(r"^[a-z0-9]+$")
_COMMAND_ID_RE = re.compile(r"^[a-z0-9]+([._-][a-z0-9]+)*$")

# Categories whose decision must keep a human in the loop (never silently allow).
_MUTATING = {
    PermissionCategory.MODIFY_SELECTION.value,
    PermissionCategory.MODIFY_DOCUMENT.value,
    PermissionCategory.CREATE_FILE.value,
    PermissionCategory.GITHUB.value,
    PermissionCategory.TERMINAL.value,
    PermissionCategory.RUN_COMMAND.value,
    PermissionCategory.WEB.value,
}
_SAFE_MUTATING_DECISIONS = {
    Decision.ASK.value,
    Decision.PREVIEW_REQUIRED.value,
    Decision.DENY.value,
}

_SELECTION_SCOPES = {"selection", "current_section"}
_DOCUMENT_SCOPES = {"full_document", "open_documents", "explicit_files"}
_HIGH_RISK = {"high", "critical"}


@dataclass(frozen=True, slots=True)
class Finding:
    """One lint result against an agent file."""

    level: str  # ERROR | WARNING
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.level.upper()}: {self.message}"


def _known_harnesses() -> set[str]:
    from quill.core.ai.sdk_install import PACK_INSTALLS

    return {"auto", "native", *PACK_INSTALLS}


def lint_agent_data(data: object, *, path: str = "<data>") -> list[Finding]:
    """Apply the schema floor plus the authoring standards to one parsed agent."""
    findings = [Finding(ERROR, path, p) for p in validate_agent(data)]
    if not isinstance(data, dict):
        return findings

    def err(msg: str) -> None:
        findings.append(Finding(ERROR, path, msg))

    def warn(msg: str) -> None:
        findings.append(Finding(WARNING, path, msg))

    display = data.get("display_name")
    if isinstance(display, str):
        if display != display.strip():
            err("display_name has leading/trailing whitespace.")
        if len(display.strip()) > _MAX_DISPLAY_NAME:
            err(f"display_name is over {_MAX_DISPLAY_NAME} characters.")

    description = data.get("description")
    if not isinstance(description, str) or not description.strip():
        err("description is required (a one-line summary of what the agent does).")
    else:
        if "\n" in description:
            err("description must be a single line.")
        length = len(description.strip())
        if length < _MIN_DESCRIPTION:
            err(f"description is too short (min {_MIN_DESCRIPTION} characters).")
        elif length > _MAX_DESCRIPTION:
            err(f"description is too long (max {_MAX_DESCRIPTION} characters).")

    prompt = data.get("system_prompt")
    if isinstance(prompt, str) and 0 < len(prompt.strip()) < _MIN_SYSTEM_PROMPT:
        err(
            "system_prompt is too short to be a real instruction "
            f"(min {_MIN_SYSTEM_PROMPT} characters)."
        )

    harness = data.get("default_harness")
    if isinstance(harness, str) and harness and harness not in _known_harnesses():
        err(
            f"default_harness {harness!r} is unknown "
            f"(expected one of {sorted(_known_harnesses())})."
        )

    ftypes = data.get("recommended_file_types")
    if isinstance(ftypes, list):
        for ft in ftypes:
            if not (isinstance(ft, str) and _FILE_TYPE_RE.match(ft)):
                err(f"recommended_file_types entry {ft!r} must be lowercase, no leading dot.")

    tools = data.get("tools")
    if isinstance(tools, list):
        for tool in tools:
            if not (isinstance(tool, str) and _COMMAND_ID_RE.match(tool)):
                err(f"tools entry {tool!r} is not a valid command id.")

    perms = data.get("permissions")
    perms = perms if isinstance(perms, dict) else {}
    for category, decision in perms.items():
        if category in _MUTATING and decision == Decision.ALLOW.value:
            err(
                f"permission {category!r} may not be 'allow' — a mutating action must keep "
                "a human in the loop ('ask', 'preview_required', or 'deny')."
            )

    risk = data.get("risk")
    if risk in _HIGH_RISK and not perms:
        err(f"a {risk!r}-risk agent must declare its permissions explicitly.")

    # Scope <-> permission coherence (warning: legitimate edge cases exist).
    scope = data.get("default_scope")
    if PermissionCategory.MODIFY_SELECTION.value in perms and scope not in _SELECTION_SCOPES:
        warn(f"modify_selection with scope {scope!r}: expected a selection-level scope.")
    if PermissionCategory.MODIFY_DOCUMENT.value in perms and scope not in _DOCUMENT_SCOPES:
        warn(f"modify_document with scope {scope!r}: expected a document-level scope.")

    return findings


def lint_path(path: Path) -> list[Finding]:
    """Lint a single agent file (``.md`` or ``.json``)."""
    rel = str(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [Finding(ERROR, rel, f"could not read file: {exc}")]
    try:
        data: object = parse_agent_markdown(text) if path.suffix == ".md" else json.loads(text)
    except ValueError as exc:
        return [Finding(ERROR, rel, f"could not parse: {exc}")]

    findings = lint_agent_data(data, path=rel)
    if isinstance(data, dict):
        agent_id = data.get("id")
        if isinstance(agent_id, str) and agent_id and path.stem != agent_id:
            findings.append(
                Finding(ERROR, rel, f"file name must match the agent id ({agent_id!r}).")
            )
    return findings


def _is_doc(path: Path) -> bool:
    return path.stem.lower() == "readme" or path.name.startswith(("_", "."))


def lint_paths(paths: list[Path]) -> list[Finding]:
    """Lint each file and add a cross-file duplicate-id check."""
    findings: list[Finding] = []
    ids: dict[str, str] = {}
    for path in paths:
        if _is_doc(path):
            continue
        file_findings = lint_path(path)
        findings.extend(file_findings)
        try:
            text = path.read_text(encoding="utf-8")
            data = parse_agent_markdown(text) if path.suffix == ".md" else json.loads(text)
        except (OSError, ValueError):
            continue
        if isinstance(data, dict):
            agent_id = data.get("id")
            if isinstance(agent_id, str) and agent_id:
                if agent_id in ids:
                    findings.append(
                        Finding(
                            ERROR,
                            str(path),
                            f"duplicate agent id {agent_id!r} (also in {ids[agent_id]}).",
                        )
                    )
                else:
                    ids[agent_id] = str(path)
    return findings


def lint_dir(directory: Path) -> list[Finding]:
    """Lint every agent file under ``directory``."""
    files = sorted(directory.glob("*.md")) + sorted(directory.glob("*.json"))
    return lint_paths(files)


def _gather(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted(path.glob("*.md")) + sorted(path.glob("*.json")))
        else:
            files.append(path)
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lint QUILL agent files against the standards.")
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Agent files or directories (default: the bundled agents dir).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as failures.",
    )
    args = parser.parse_args(argv)

    targets = _gather(args.paths) if args.paths else _gather([bundled_agents_dir()])
    findings = lint_paths(targets)

    errors = [f for f in findings if f.level == ERROR]
    warnings = [f for f in findings if f.level == WARNING]
    for finding in findings:
        print(finding)

    if not findings:
        print(f"agent_lint: OK ({len(targets)} file(s))")
    else:
        print(f"agent_lint: {len(errors)} error(s), {len(warnings)} warning(s)")

    if errors or (args.strict and warnings):
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
