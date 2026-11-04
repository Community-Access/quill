"""The project tools: what an agent may do in a project, all of it QUILL code (code.md 4.2).

The vendors' own shell and file tools stay off; the model sees only these,
under every engine (decision 4). Names are namespaced like ``doc.read_outline``
and the engines see ``project_read`` and so on.

==================  ==============  ======================================
Tool                Category        Asks?
==================  ==============  ======================================
project.list        READ_WORKSPACE  no: reads inside the project are free
project.read        READ_WORKSPACE  no
project.search      READ_WORKSPACE  no
project.outline     READ_WORKSPACE  no
project.git_status  READ_WORKSPACE  no
project.plan        READ_WORKSPACE  no: records the plan for the window
project.ask_person  READ_WORKSPACE  no: a question in the transcript
project.point_to    READ_WORKSPACE  no: coach mode's "look here"
project.edit        MODIFY_DOCUMENT the review is the question
project.create      CREATE_FILE     the review is the question
project.delete      CREATE_FILE     the review, never a task-wide grant
project.rename      CREATE_FILE     the review, never a task-wide grant
project.run         TERMINAL        its own approval, or the allow list
==================  ==============  ======================================

**No tool here writes a file.** An edit, a new file, a deletion or a rename
joins the turn's :class:`~quill.core.ai.change_set.ChangeSet`; only
``ChangeSet.apply``, after the person's review, writes (GATE-PROJECT-REVIEW
scans this module to keep it so). ``project.edit`` takes search-and-replace
blocks or a unified diff, the shape Codex's models are trained on.

wx-free; the window side is a :class:`ProjectToolHost`.
"""

from __future__ import annotations

import re
from typing import Any, Protocol

from quill.core.ai.change_set import ChangeKind, ChangeSet, ChangeSetError
from quill.core.ai.family_tools import FamilyTool
from quill.core.ai.permissions import PermissionCategory, RiskLevel
from quill.core.ai.project import Project, ProjectError

__all__ = [
    "PROJECT_APP",
    "COACH_TOOL_NAMES",
    "ProjectToolHost",
    "apply_unified_diff",
    "apply_search_replace",
    "project_tools",
]

PROJECT_APP = "project"

#: What coach mode keeps: reading and pointing, never changing or running.
COACH_TOOL_NAMES: frozenset[str] = frozenset({
    "project.list",
    "project.read",
    "project.search",
    "project.outline",
    "project.git_status",
    "project.plan",
    "project.ask_person",
    "project.point_to",
})


class ProjectToolHost(Protocol):
    """What the tools need from the task, called on the engine's worker."""

    @property
    def project(self) -> Project: ...
    @property
    def changes(self) -> ChangeSet: ...
    def record_plan(self, steps: list[str]) -> str: ...
    def ask_person(self, question: str) -> str: ...
    def point_to(self, path: str, line: int, note: str) -> str: ...
    def run_command(self, command: str, reason: str) -> str: ...
    def git_status(self) -> str: ...
    def note(self, text: str) -> None: ...


def _schema(props: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": props,
        "required": required,
        "additionalProperties": False,
    }


_STR = {"type": "string"}
_INT = {"type": "integer"}


def apply_search_replace(text: str, edits: list[dict[str, Any]], path: str) -> str:
    """Each ``{"old": ..., "new": ...}`` replaced once; *old* must occur exactly once."""
    for number, edit in enumerate(edits, start=1):
        old = str(edit.get("old", ""))
        new = str(edit.get("new", ""))
        if not old:
            raise ChangeSetError(f"Edit {number} for {path} has no text to find.")
        count = text.count(old)
        if count == 0:
            raise ChangeSetError(
                f"Edit {number}: that text is not in {path}. Read the file again and copy "
                "the lines exactly."
            )
        if count > 1:
            raise ChangeSetError(
                f"Edit {number}: that text appears {count} times in {path}. Include more "
                "lines around it so it appears once."
            )
        text = text.replace(old, new, 1)
    return text


_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def apply_unified_diff(text: str, diff: str, path: str) -> str:
    """Apply a unified diff's hunks to *text*, matching by content near the stated line."""
    lines = text.split("\n")
    hunks: list[tuple[int, list[str], list[str]]] = []
    current: tuple[int, list[str], list[str]] | None = None
    for raw in diff.replace("\r\n", "\n").split("\n"):
        match = _HUNK.match(raw)
        if match:
            current = (int(match.group(1)), [], [])
            hunks.append(current)
            continue
        if current is None or raw.startswith(("---", "+++", "\\")):
            continue
        if raw.startswith("+"):
            current[2].append(raw[1:])
        elif raw.startswith("-"):
            current[1].append(raw[1:])
        else:
            body = raw[1:] if raw.startswith(" ") else raw
            current[1].append(body)
            current[2].append(body)
    if not hunks:
        raise ChangeSetError(f"That diff for {path} has no @@ hunks.")
    offset = 0
    for start, old, new in hunks:
        while old and new and old[-1] == "" and new[-1] == "":
            old.pop()
            new.pop()
        guess = max(0, start - 1 + offset)
        at = _find_block(lines, old, guess)
        if at < 0:
            raise ChangeSetError(
                f"The diff does not match {path} near line {start}. Read the file again."
            )
        lines[at : at + len(old)] = new
        offset += len(new) - len(old)
    return "\n".join(lines)


def _find_block(lines: list[str], block: list[str], guess: int) -> int:
    if not block:
        return min(guess, len(lines))
    size = len(block)
    candidates = sorted(range(0, len(lines) - size + 1), key=lambda i: abs(i - guess))
    for index in candidates:
        if lines[index : index + size] == block:
            return index
    stripped = [b.rstrip() for b in block]
    for index in candidates:
        if [ln.rstrip() for ln in lines[index : index + size]] == stripped:
            return index
    return -1


def _list(project: Project, args: dict[str, Any]) -> str:
    result = project.list_folder(str(args.get("folder", "") or ""))
    if not result.entries and not result.hidden_secrets:
        return "That folder has no files the agent can see."
    rows = [f"{e.path} ({e.size} bytes)" for e in result.entries]
    notes: list[str] = []
    if result.hidden_secrets:
        n = result.hidden_secrets
        notes.append(
            f"{n} file{'s' if n != 1 else ''} hidden by QUILL because they look like "
            "secrets; ask the person if you need what is in them."
        )
    if result.ignored:
        notes.append(f"{result.ignored} ignored by .gitignore and not listed.")
    if result.truncated:
        notes.append("The list was cut short; list a subfolder for more.")
    return "\n".join([*rows, *notes])


def _read(project: Project, args: dict[str, Any]) -> str:
    result = project.read(
        str(args.get("path", "")), int(args.get("start", 1) or 1), int(args.get("end", 0) or 0)
    )
    if result.binary:
        return f"{result.path}: {result.text}"
    head = f"{result.path}, lines {result.start} to {result.end} of {result.total_lines}."
    tail = " Ask for the next range to read more." if result.truncated else ""
    return f"{head}{tail}\n{result.text}"


def _search(project: Project, args: dict[str, Any]) -> str:
    hits = project.search(
        str(args.get("query", "")),
        regex=bool(args.get("regex", False)),
        glob=str(args.get("glob", "") or ""),
    )
    if not hits:
        return "No matches."
    return "\n".join(f"{h.path}:{h.line}: {h.text}" for h in hits)


def _outline(project: Project, args: dict[str, Any]) -> str:
    items = project.outline(str(args.get("path", "")))
    if not items:
        return "No functions or classes were found."
    return "\n".join(f"{'  ' * i.depth}{i.kind} {i.name}, line {i.line}" for i in items)


def _proposal(host: ProjectToolHost, path: str, verb: str) -> str:
    change = host.changes.get(path)
    count = change.change_count if change is not None else 0
    host.note(f"Proposed: {verb} {path}.")
    return (
        f"Proposed {verb} {path} ({count} change{'s' if count != 1 else ''} so far). Nothing "
        "is written yet: the person reviews this turn's changes before a command runs and "
        "when the turn ends, and you will be told what they accepted."
    )


def _edit(host: ProjectToolHost, args: dict[str, Any]) -> str:
    path = host.project.relative(host.project.resolve(str(args.get("path", ""))))
    pending = host.changes.get(path)
    creating = pending is not None and pending.kind is ChangeKind.CREATE
    if not creating and not (host.project.root / path).is_file():
        raise ProjectError(f"{path} does not exist; use project_create for a new file.")
    current = host.changes.current_text(path, host.project.read_text)
    edits = args.get("edits")
    patch = str(args.get("patch", "") or "")
    if isinstance(edits, list) and edits:
        revised = apply_search_replace(current, [e for e in edits if isinstance(e, dict)], path)
    elif patch.strip():
        revised = apply_unified_diff(current, patch, path)
    else:
        raise ChangeSetError("Give either edits (old and new text) or a unified diff patch.")
    reason = str(args.get("reason", "") or "")
    if creating:
        host.changes.propose_create(path, revised, reason)
    else:
        original = pending.original if pending is not None else host.project.read_text(path)
        host.changes.propose_edit(path, original, revised, reason)
    return _proposal(host, path, "a change to")


def _create(host: ProjectToolHost, args: dict[str, Any]) -> str:
    path = host.project.relative(host.project.resolve(str(args.get("path", ""))))
    if (host.project.root / path).exists():
        raise ProjectError(f"{path} already exists; use project_edit to change it.")
    host.changes.propose_create(path, str(args.get("text", "")), str(args.get("reason", "") or ""))
    return _proposal(host, path, "a new file,")


def _delete(host: ProjectToolHost, args: dict[str, Any]) -> str:
    path = host.project.relative(host.project.resolve(str(args.get("path", ""))))
    host.changes.propose_delete(
        path, host.project.read_text(path), str(args.get("reason", "") or "")
    )
    return _proposal(host, path, "deleting")


def _rename(host: ProjectToolHost, args: dict[str, Any]) -> str:
    project = host.project
    path = project.relative(project.resolve(str(args.get("path", ""))))
    if not (project.root / path).is_file():
        raise ProjectError(f"{path} is not a file in the project.")
    destination = str(args.get("new_path", ""))
    project.resolve(destination)  # refuses one outside the project, or a secret
    host.changes.propose_rename(
        path, destination.replace("\\", "/"), str(args.get("reason", "") or "")
    )
    return _proposal(host, path, "renaming")


def _guarded(fn: Any, *pass_through: Any) -> Any:
    def handler(args: dict[str, Any]) -> str:
        try:
            return str(fn(*pass_through, args))
        except (ProjectError, ChangeSetError) as error:
            return re.sub(r"^\[QUILL-[A-Z0-9-]+\]\s*", "", str(error))

    return handler


def project_tools(host: ProjectToolHost, *, coach: bool = False) -> list[FamilyTool]:
    """The project tools over *host*. Coach mode keeps only reading and pointing."""
    project = host.project
    read = PermissionCategory.READ_WORKSPACE
    reason = {"reason": {"type": "string", "description": "Why, in one plain sentence."}}

    def tool(
        name: str,
        description: str,
        handler: Any,
        props: dict[str, Any],
        required: list[str],
        category: PermissionCategory = read,
        *,
        mutating: bool = False,
        risk: RiskLevel = RiskLevel.LOW,
    ) -> FamilyTool:
        return FamilyTool(
            name=f"{PROJECT_APP}.{name}",
            description=description,
            handler=handler,
            parameters=_schema(props, required),
            category=category,
            risk=risk,
            app=PROJECT_APP,
            mutating=mutating,
            asks_itself=category is not read,
        )

    tools = [
        tool(
            "list",
            "List the files in the project, or in one folder of it, with sizes.",
            _guarded(_list, project),
            {"folder": _STR},
            [],
        ),
        tool(
            "read",
            "Read a project file with line numbers; give start and end for a range.",
            _guarded(_read, project),
            {"path": _STR, "start": _INT, "end": _INT},
            ["path"],
        ),
        tool(
            "search",
            "Search the project's files for text, or a regex when regex is true.",
            _guarded(_search, project),
            {"query": _STR, "regex": {"type": "boolean"}, "glob": _STR},
            ["query"],
        ),
        tool(
            "outline",
            "List the functions and classes in a file, with line numbers.",
            _guarded(_outline, project),
            {"path": _STR},
            ["path"],
        ),
        tool(
            "git_status",
            "The project's git branch and changed files, when it uses git.",
            lambda _a: host.git_status(),
            {},
            [],
        ),
        tool(
            "plan",
            "Record your plan as a list of short steps, before you change anything.",
            lambda a: host.record_plan([str(s) for s in a.get("steps", []) if str(s).strip()]),
            {"steps": {"type": "array", "items": _STR}},
            ["steps"],
        ),
        tool(
            "ask_person",
            "Ask the person a question; they answer in their next message.",
            lambda a: host.ask_person(str(a.get("question", ""))),
            {"question": _STR},
            ["question"],
        ),
        tool(
            "point_to",
            "Point the person to a file and line, with what to look at there.",
            lambda a: host.point_to(
                str(a.get("path", "")), int(a.get("line", 1) or 1), str(a.get("note", ""))
            ),
            {"path": _STR, "line": _INT, "note": _STR},
            ["path", "line", "note"],
        ),
        tool(
            "edit",
            "Propose a change to an existing file, as search-and-replace blocks "
            "(edits: [{old, new}], each old appearing exactly once) or a unified diff (patch).",
            _guarded(_edit, host),
            {
                "path": _STR,
                "edits": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"old": _STR, "new": _STR},
                        "required": ["old", "new"],
                        "additionalProperties": False,
                    },
                },
                "patch": _STR,
                **reason,
            },
            ["path"],
            PermissionCategory.MODIFY_DOCUMENT,
            mutating=True,
            risk=RiskLevel.HIGH,
        ),
        tool(
            "create",
            "Propose a new file with its full text.",
            _guarded(_create, host),
            {"path": _STR, "text": _STR, **reason},
            ["path", "text"],
            PermissionCategory.CREATE_FILE,
            mutating=True,
            risk=RiskLevel.HIGH,
        ),
        tool(
            "delete",
            "Propose deleting a file.",
            _guarded(_delete, host),
            {"path": _STR, **reason},
            ["path"],
            PermissionCategory.CREATE_FILE,
            mutating=True,
            risk=RiskLevel.HIGH,
        ),
        tool(
            "rename",
            "Propose renaming or moving a file inside the project.",
            _guarded(_rename, host),
            {"path": _STR, "new_path": _STR, **reason},
            ["path", "new_path"],
            PermissionCategory.CREATE_FILE,
            mutating=True,
            risk=RiskLevel.HIGH,
        ),
        tool(
            "run",
            "Run one command in the project folder, such as the tests. The person "
            "approves it first. Pending changes are reviewed before it runs.",
            lambda a: host.run_command(str(a.get("command", "")), str(a.get("reason", ""))),
            {"command": _STR, **reason},
            ["command"],
            PermissionCategory.TERMINAL,
            risk=RiskLevel.HIGH,
        ),
    ]
    if coach:
        return [t for t in tools if t.name in COACH_TOOL_NAMES]
    return [t for t in tools if t.name != "project.point_to"]
