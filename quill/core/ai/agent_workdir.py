"""Per-app engine folders, emptied after every task (codex.md 8, decision 4).

Each app's agent engine gets its own folder under
``app_data_dir()/ai/<engine>/<slug>``: Copilot's empty ``working_directory``
and its session state (``COPILOT_HOME``), and later Codex's ``CODEX_HOME``.
Nothing in it outlives a task. It is swept when the task ends, on Stop, and
again at the next start, so a crash in the middle of a task still leaves
nothing behind after the next run.

Two subfolders, so the engine's own built-in read tools -- were one ever to
slip through the allowlist -- would find nothing to read:

- ``work`` -- the session's working directory, always empty;
- ``home`` -- the engine's state (threads, session files, logs).
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from quill.core.paths import app_data_dir

__all__ = ["AgentFolders", "agent_slug", "agent_folders", "sweep"]

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def agent_slug(agent_name: str) -> str:
    """A filesystem-safe slug for an app's agent name ("QUILL Lite" -> "quill-lite")."""
    slug = _SLUG_STRIP.sub("-", agent_name.strip().lower()).strip("-")
    return slug or "quill"


@dataclass(frozen=True, slots=True)
class AgentFolders:
    """The folders one app's engine uses for one task."""

    root: Path

    @property
    def work(self) -> Path:
        return self.root / "work"

    @property
    def home(self) -> Path:
        return self.root / "home"

    def prepare(self) -> AgentFolders:
        """Sweep anything a previous run left, then make both folders empty."""
        sweep(self.root)
        self.work.mkdir(parents=True, exist_ok=True)
        self.home.mkdir(parents=True, exist_ok=True)
        return self

    def clear(self) -> None:
        """Delete everything under the root (task end, Stop)."""
        sweep(self.root)


def agent_folders(engine: str, agent_name: str, *, base: Path | None = None) -> AgentFolders:
    """The folders for ``engine`` ("copilot", "codex") in the app ``agent_name``."""
    root_base = base if base is not None else app_data_dir() / "ai"
    return AgentFolders(root=root_base / agent_slug(engine) / agent_slug(agent_name))


def sweep(root: Path) -> None:
    """Remove ``root`` and everything under it; a missing folder is fine.

    Best effort: a file another process still holds is left for the next
    sweep rather than failing the task.
    """
    if not root.exists():
        return
    shutil.rmtree(root, ignore_errors=True)
