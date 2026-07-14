"""Declarative Agent Catalog: validate + load agent files into ``AgentSpec`` (PRD §13).

QUILL ships no ``jsonschema`` runtime dependency, so the contract published at
``quill/core/schemas/agent.json`` is enforced here in pure, strictly-typed Python
— the same hand-rolled-validator style used by the Quillin manifest, QVP, and
sound-pack stores. Tests assert this module and the JSON schema agree.

This is wx-free core and additive: it loads bundled agent specs from
``quill/core/ai/agents/`` (and any extra directories, e.g. user-installed or
Quillin-contributed) into :class:`~quill.core.ai.harness.AgentSpec` objects the AI
Hub lists and any harness can run.

**Authoring format.** Agents are authored as **Markdown with YAML front matter**
(``<id>.md``) — the same shape as Claude Code / Claude Agent SDK subagents and as
QUILL's own Skill packs (:mod:`quill.core.skill_pack`): the front matter carries
the metadata and the Markdown **body is the agent's instructions** (its system
prompt). This keeps the prompt reviewable and diffable instead of trapped on one
JSON line. Legacy ``<id>.json`` files (with a ``system_prompt`` string) are still
loaded for back-compat, so user/Quillin-supplied JSON keeps working. The same
hand-rolled validator enforces both against ``quill/core/schemas/agent.json``;
QUILL ships no ``jsonschema``/``PyYAML`` runtime dependency.

Public API:

* :func:`validate_agent` — return a list of human-readable problems (empty when
  valid). Never raises for malformed data.
* :func:`parse_agent` — build an :class:`AgentSpec`, or raise
  :class:`AgentSpecError` carrying every problem found.
* :func:`parse_agent_markdown` — turn a Markdown-with-front-matter agent file
  into the same data dict :func:`validate_agent` / :func:`parse_agent` accept.
* :func:`load_catalog` — load every ``*.md`` and ``*.json`` agent file under the
  given directories, returning a :class:`CatalogLoadResult` (valid specs +
  per-file errors); a bad file never aborts the load.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from quill.core.ai.context_builder import ContextScope
from quill.core.ai.harness import AgentSpec
from quill.core.ai.permissions import Decision, PermissionCategory, RiskLevel

__all__ = [
    "SCHEMA_ID",
    "AgentSpecError",
    "CatalogLoadResult",
    "validate_agent",
    "parse_agent",
    "parse_agent_markdown",
    "bundled_agents_dir",
    "user_agents_dir",
    "load_catalog",
    "load_full_catalog",
    "save_user_agent",
]

SCHEMA_ID = "quill.agent/1"

_ID_PATTERN = re.compile(r"^[a-z0-9]+([._-][a-z0-9]+)*$")
_REQUIRED = ("schema", "id", "display_name", "system_prompt")
_ALLOWED_KEYS = {
    "schema",
    "id",
    "display_name",
    "description",
    "system_prompt",
    "risk",
    "default_scope",
    "recommended_file_types",
    "default_harness",
    "tools",
    "permissions",
    "needs_tool_use",
}


class AgentSpecError(ValueError):
    """Raised by :func:`parse_agent` for an invalid agent file; lists all problems."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("; ".join(problems))


@dataclass(frozen=True, slots=True)
class CatalogLoadResult:
    """Outcome of loading a catalog directory tree."""

    agents: tuple[AgentSpec, ...] = ()
    errors: tuple[tuple[str, str], ...] = ()  # (file path, problem)

    def ids(self) -> list[str]:
        return [a.id for a in self.agents]


def validate_agent(data: object) -> list[str]:
    """Return a list of problems with ``data`` (empty when it is a valid spec)."""
    problems: list[str] = []
    if not isinstance(data, dict):
        return ["Agent spec must be a JSON object."]

    unknown = sorted(set(data) - _ALLOWED_KEYS)
    if unknown:
        problems.append(f"Unknown key(s): {', '.join(unknown)}.")

    for key in _REQUIRED:
        if not data.get(key):
            problems.append(f"Missing required key: {key}.")

    if data.get("schema") not in (None, SCHEMA_ID) and "schema" in data:
        problems.append(f"schema must be {SCHEMA_ID!r}.")

    agent_id = data.get("id")
    if isinstance(agent_id, str) and agent_id and not _ID_PATTERN.match(agent_id):
        problems.append(f"id {agent_id!r} must be lowercase dotted/dashed segments.")

    for str_key in ("display_name", "system_prompt", "description", "default_harness"):
        if str_key in data and not isinstance(data[str_key], str):
            problems.append(f"{str_key} must be a string.")

    if "needs_tool_use" in data and not isinstance(data["needs_tool_use"], bool):
        problems.append("needs_tool_use must be a boolean.")

    risk = data.get("risk")
    if risk is not None and risk not in _enum_values(RiskLevel):
        problems.append(f"risk {risk!r} is not one of {sorted(_enum_values(RiskLevel))}.")

    scope = data.get("default_scope")
    if scope is not None and scope not in _enum_values(ContextScope):
        problems.append(f"default_scope {scope!r} is not a known context scope.")

    for list_key in ("recommended_file_types", "tools"):
        if list_key in data:
            value = data[list_key]
            if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
                problems.append(f"{list_key} must be a list of strings.")

    perms = data.get("permissions")
    if perms is not None:
        if not isinstance(perms, dict):
            problems.append("permissions must be an object.")
        else:
            for cat, decision in perms.items():
                if cat not in _enum_values(PermissionCategory):
                    problems.append(f"permissions: unknown category {cat!r}.")
                if decision not in _enum_values(Decision):
                    problems.append(f"permissions[{cat!r}]: unknown decision {decision!r}.")

    return problems


def parse_agent(data: object) -> AgentSpec:
    """Build an :class:`AgentSpec` from ``data``, or raise :class:`AgentSpecError`."""
    problems = validate_agent(data)
    if problems:
        raise AgentSpecError(problems)
    assert isinstance(data, dict)  # validate_agent guarantees this

    overrides: tuple[tuple[PermissionCategory, Decision], ...] = tuple(
        (PermissionCategory(cat), Decision(dec))
        for cat, dec in dict(data.get("permissions", {})).items()
    )
    return AgentSpec(
        id=str(data["id"]),
        display_name=str(data["display_name"]),
        system_prompt=str(data["system_prompt"]),
        description=str(data.get("description", "")),
        risk=RiskLevel(data["risk"]) if data.get("risk") else RiskLevel.LOW,
        default_scope=(
            ContextScope(data["default_scope"])
            if data.get("default_scope")
            else ContextScope.SELECTION
        ),
        recommended_file_types=tuple(data.get("recommended_file_types", []) or ()),
        default_harness=str(data.get("default_harness", "auto")),
        tools=tuple(data.get("tools", []) or ()),
        permission_overrides=overrides,
        needs_tool_use=bool(data.get("needs_tool_use", False)),
    )


# ---------------------------------------------------------------------------
# Markdown-with-front-matter authoring (the agent standard)
# ---------------------------------------------------------------------------


def _split_front_matter(source: str) -> tuple[str, str]:
    """Split a leading ``--- ... ---`` front-matter block from the body.

    Returns ``(front_matter_text, body)``. With no front matter the whole source
    is the body (so a bare prompt file still parses, just missing metadata).
    """
    if not source.startswith("---"):
        return "", source
    rest = source[3:]
    nl = rest.find("\n")
    if nl == -1:
        return "", source
    after = rest[nl + 1 :]
    end = after.find("\n---")
    if end == -1:
        return "", source
    return after[:end], after[end + 4 :].lstrip("\n")


def _scalar(value: str) -> object:
    """Coerce a front-matter scalar: inline list, bool, int, or trimmed string."""
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1]
        return [item.strip().strip("\"'") for item in inner.split(",") if item.strip()]
    low = value.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if value.lstrip("-").isdigit():
        return int(value)
    return value.strip("\"'")


def _parse_front_matter(text: str) -> dict[str, object]:
    """Parse the front-matter subset agents need: scalars, inline lists, and a
    single level of nested ``key: value`` mapping (used by ``permissions``).

    Deliberately tiny and PyYAML-free, matching the project's no-runtime-YAML
    rule; richer YAML is intentionally unsupported so agent files stay simple.
    """
    result: dict[str, object] = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or (len(line) - len(line.lstrip())) > 0:
            i += 1
            continue
        if ":" not in line:
            i += 1
            continue
        key, _, raw = line.partition(":")
        key = key.strip()
        raw = raw.strip()
        if raw == "":
            # A nested mapping: gather following indented ``k: v`` lines.
            mapping: dict[str, object] = {}
            i += 1
            while i < len(lines):
                nxt = lines[i]
                if not nxt.strip():
                    i += 1
                    continue
                if (len(nxt) - len(nxt.lstrip())) == 0:
                    break  # back to a top-level key
                if ":" in nxt:
                    k2, _, v2 = nxt.partition(":")
                    mapping[k2.strip()] = _scalar(v2)
                i += 1
            result[key] = mapping
        else:
            result[key] = _scalar(raw)
            i += 1
    return result


def parse_agent_markdown(source: str) -> dict[str, object]:
    """Turn a Markdown-with-front-matter agent file into a spec data dict.

    The front matter supplies the metadata; the Markdown **body is the agent's
    ``system_prompt``** (its instructions). ``schema`` defaults to the current
    :data:`SCHEMA_ID` so authors do not repeat it. The returned dict is exactly
    what :func:`validate_agent` / :func:`parse_agent` consume, so validation and
    error reporting are identical to the JSON path.
    """
    front, body = _split_front_matter(source)
    data: dict[str, object] = dict(_parse_front_matter(front))
    data.setdefault("schema", SCHEMA_ID)
    body = body.strip()
    if body:
        data["system_prompt"] = body
    return data


def bundled_agents_dir() -> Path:
    """The directory holding QUILL's built-in agent spec files."""
    return Path(__file__).resolve().parent / "agents"


def user_agents_dir() -> Path:
    """The directory holding the user's saved/promoted agent spec files.

    This is where Promote-to-Agent writes, so a skill graduated into an agent
    becomes first-class: it shows up in the AI Library Agents tab and runs through
    the gateway like a bundled agent. Created on demand by the writer.
    """
    from quill.core.paths import app_data_dir

    return app_data_dir() / "agents"


def load_full_catalog() -> CatalogLoadResult:
    """Load bundled agents plus the user's saved/promoted agents.

    User agents are loaded after the bundled ones, so a user agent with the same
    id shadows the bundled one (the documented :func:`load_catalog` precedence).
    A missing user dir is simply skipped.
    """
    return load_catalog(bundled_agents_dir(), user_agents_dir())


def save_user_agent(markdown: str) -> AgentSpec:
    """Validate an agent ``.md`` and save it into the user agents dir.

    Returns the parsed :class:`AgentSpec`. Raises :class:`AgentSpecError` if the
    markdown is not a valid agent spec, so a malformed promotion never lands a bad
    file in the catalog.
    """
    raw = parse_agent_markdown(markdown)
    problems = validate_agent(raw)
    if problems:
        raise AgentSpecError(problems)
    spec = parse_agent(raw)
    target_dir = user_agents_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / f"{spec.id}.md").write_text(markdown, encoding="utf-8")
    return spec


def load_catalog(*dirs: Path) -> CatalogLoadResult:
    """Load every ``*.md`` and ``*.json`` agent file under ``dirs``.

    Default search is the bundled dir. A malformed or duplicate file is recorded
    in ``errors`` and skipped; it never aborts the load. Later directories
    override earlier ids (user/extension agents can shadow bundled ones); within a
    directory, files are loaded in name order.
    """
    search = list(dirs) or [bundled_agents_dir()]
    specs: dict[str, AgentSpec] = {}
    errors: list[tuple[str, str]] = []

    for directory in search:
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.md")) + sorted(directory.glob("*.json")):
            # Skip documentation/partials so a folder can carry a README or
            # ``_template`` alongside its agents without failing the load.
            if path.stem.lower() == "readme" or path.name.startswith(("_", ".")):
                continue
            try:
                text = path.read_text(encoding="utf-8")
                raw: object = (
                    parse_agent_markdown(text) if path.suffix == ".md" else json.loads(text)
                )
            except (OSError, ValueError) as exc:
                errors.append((str(path), f"Could not read/parse: {exc}"))
                continue
            problems = validate_agent(raw)
            if problems:
                errors.extend((str(path), p) for p in problems)
                continue
            spec = parse_agent(raw)
            specs[spec.id] = spec

    return CatalogLoadResult(agents=tuple(specs.values()), errors=tuple(errors))


def _enum_values(enum_cls: type) -> set[str]:
    return {member.value for member in enum_cls}  # type: ignore[attr-defined]
