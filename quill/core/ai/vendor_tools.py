"""The engines' own tools, by the person's choice only (code.md decision 4) -- wx-free.

QUILL's project tools are the default and, until somebody chooses otherwise,
the only tools an engine sees: every write is reviewed first and every
command approved first, the same under every engine. Decision 4 adds a door:
the person may look at an engine's own tools and turn some of them on, for
one project.

- **Per engine,** because each vendor's tools are different things.
- **Off until checked.** Nothing here is on by default, and a project folder
  cannot turn anything on: the choice is stored in QUILL's app data, keyed by
  the project, never in the repository.
- **Asked every time.** An engine's own tool still goes through QUILL's
  approval question before each use; turning one on only means the engine may
  ask.
- **Shown in the plan and the transcript,** so a turn that used them says so.

What turning one on costs, said plainly in :data:`VENDOR_TOOLS_WARNING`: an
engine's own edit tool writes straight to disk without QUILL's review (the
turn's checkpoint still lets Undo Last Turn put files back), and its shell
runs in the project folder with nothing between it and the person's account
but the approval.

The names are each engine's own: Copilot's are its built-in tool names as
``--available-tools`` takes them, with the permission kind its callback sends.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from quill.core.storage import read_json, write_json_atomic

__all__ = [
    "VENDOR_TOOLS",
    "VENDOR_TOOLS_WARNING",
    "VendorTool",
    "VendorToolChoices",
    "engine_for_harness",
    "permission_kinds",
    "vendor_tools_sentence",
]


@dataclass(frozen=True, slots=True)
class VendorTool:
    """One of an engine's own tools, as the person sees it in the opt-in list."""

    id: str  # the engine's own name for it
    label: str  # a plain name for the check box
    description: str
    #: The permission kind the engine asks with when it wants to use it.
    kind: str
    writes: bool = False


VENDOR_TOOLS: dict[str, tuple[VendorTool, ...]] = {
    "copilot": (
        VendorTool("view", "Read files (view)", "Copilot's own file reader.", "read"),
        VendorTool("grep", "Search file contents (grep)", "Copilot's own search.", "read"),
        VendorTool("glob", "Find files by name (glob)", "Copilot's own file finder.", "read"),
        VendorTool(
            "edit",
            "Edit files (edit)",
            "Copilot's own editor. Its changes go straight to disk, without Review Changes.",
            "write",
            writes=True,
        ),
        VendorTool(
            "bash",
            "Run shell commands (bash)",
            "Copilot's own shell, in the project folder. Each command still asks first.",
            "shell",
            writes=True,
        ),
        VendorTool("web_fetch", "Fetch web pages (web_fetch)", "Reads a web address.", "url"),
        VendorTool("web_search", "Search the web (web_search)", "Searches the web.", "url"),
    ),
    "codex": (
        VendorTool(
            "commandExecution",
            "Run commands (Codex's shell)",
            "Codex's own command runner, in the project folder. Each command asks first.",
            "shell",
            writes=True,
        ),
        VendorTool(
            "fileChange",
            "Change files (Codex's apply_patch)",
            "Codex's own patch tool. Its changes go straight to disk, without Review Changes.",
            "write",
            writes=True,
        ),
    ),
    "claude": (
        VendorTool("Read", "Read files (Read)", "Claude's own file reader.", "read"),
        VendorTool("Grep", "Search file contents (Grep)", "Claude's own search.", "read"),
        VendorTool("Glob", "Find files by name (Glob)", "Claude's own file finder.", "read"),
        VendorTool(
            "Edit",
            "Edit files (Edit and Write)",
            "Claude's own editor. Its changes go straight to disk, without Review Changes.",
            "write",
            writes=True,
        ),
        VendorTool(
            "Bash",
            "Run shell commands (Bash)",
            "Claude's own shell, in the project folder. Each command asks first.",
            "shell",
            writes=True,
        ),
        VendorTool("WebFetch", "Fetch web pages (WebFetch)", "Reads a web address.", "url"),
    ),
}

VENDOR_TOOLS_WARNING = (
    "These are the engine's own tools, not QUILL's. QUILL asks you before each use, "
    "but an engine's own edit tool writes straight to disk without Review Changes, "
    "and its shell can do anything your account can. Undo Last Turn still puts the "
    "project's files back. All of them are off until you check them, and the choice "
    "is kept in QUILL for this project only."
)

_ENGINE_NAMES = {"copilot": "GitHub Copilot", "codex": "Codex", "claude": "Claude"}


def engine_for_harness(harness_id: str) -> str:
    """The :data:`VENDOR_TOOLS` key for a harness id ("" for an engine with none)."""
    low = str(harness_id or "").lower()
    for engine in VENDOR_TOOLS:
        if low.startswith(engine):
            return engine
    return ""


def permission_kinds(engine: str, enabled: frozenset[str]) -> frozenset[str]:
    """The permission kinds an engine may ask with, given the tools turned on."""
    return frozenset(t.kind for t in VENDOR_TOOLS.get(engine, ()) if t.id in enabled)


def vendor_tools_sentence(engine: str, enabled: frozenset[str]) -> str:
    """For the plan and the transcript: which of the engine's own tools are on, or ""."""
    tools = [t.label for t in VENDOR_TOOLS.get(engine, ()) if t.id in enabled]
    if not tools:
        return ""
    name = _ENGINE_NAMES.get(engine, engine)
    return (
        f"Also on for this project: {name}'s own tools: {'; '.join(tools)}. Each asks "
        "before it runs, and what they change is not shown in Review Changes."
    )


class VendorToolChoices:
    """Which engine tools one project allows, in QUILL's app data."""

    def __init__(self, data_dir: Path, project_key: str) -> None:
        self._path = Path(data_dir) / "ai" / "projects" / project_key / "vendor_tools.json"

    @property
    def path(self) -> Path:
        return self._path

    def enabled(self, engine: str) -> frozenset[str]:
        raw = read_json(self._path, default={})
        engines = raw.get("engines", {}) if isinstance(raw, dict) else {}
        items = engines.get(engine, []) if isinstance(engines, dict) else []
        known = {t.id for t in VENDOR_TOOLS.get(engine, ())}
        return frozenset(str(i) for i in items if isinstance(i, str) and i in known)

    def set_enabled(self, engine: str, ids: frozenset[str] | set[str]) -> None:
        raw = read_json(self._path, default={})
        engines = dict(raw.get("engines", {})) if isinstance(raw, dict) else {}
        known = {t.id for t in VENDOR_TOOLS.get(engine, ())}
        engines[engine] = sorted(i for i in ids if i in known)
        write_json_atomic(self._path, {"version": 1, "engines": engines})
