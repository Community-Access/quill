"""Running one approved command for an agent (code.md 4.6) -- wx-free.

``project.run`` is where the real risk is, and where Windows gives the least
help. So the rules are plain and live here:

- **The person approves every command,** unless they put that exact command
  (or a prefix they typed, such as ``pytest``) on this project's allow list
  themselves. The list is stored in QUILL's app data keyed by the project's
  path, never in the repository: a cloned project must not be able to
  pre-approve its own ``rm -rf``.
- **QUILL, not the model, works out the warning lines.** "This may reach the
  internet." for installers and network tools; "This deletes files." for
  ``del``, ``rm`` and friends; "This runs outside the project." for a path that
  leaves the root. "Always allow" is never offered with a warning.
- **Some things the person keeps for themselves** in version one: pushing,
  publishing, ``--force`` against a remote, and changing system settings. The
  agent is told so, and can tell the person how.
- **How it runs:** in the project folder, through ``cmd /d /c`` (Windows) or
  ``/bin/sh -c``, in a process tree Stop can kill whole
  (:mod:`quill.stability.process_tree`), with a scrubbed environment -- no
  API key, no GitHub token, no ``QUILL_*`` variable -- and output to a file.

**What QUILL cannot do, said honestly:** an approved command can reach the
network, read files outside the project, and do anything the person's account
can. The approval is the safety boundary, which is why it has to be clear.
"""

from __future__ import annotations

import os
import re
import shlex
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.storage import read_json, write_json_atomic

__all__ = [
    "AllowList",
    "CommandAssessment",
    "CommandResult",
    "CommandRunner",
    "assess_command",
    "child_environment",
    "WARN_DELETES",
    "WARN_NETWORK",
    "WARN_OUTSIDE",
]

WARN_NETWORK = "This may reach the internet."
WARN_DELETES = "This deletes files."
WARN_OUTSIDE = "This runs outside the project."

#: Said to the agent when a command is one the person keeps for themselves.
KEPT_FOR_PERSON = (
    "The person keeps this step for themselves. Do not try another way to do it; "
    "tell them the exact command, and they will run it if they want to."
)

_NEVER: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bgit\b.*\bpush\b"), "pushing to a remote"),
    (re.compile(r"\b(npm|yarn|pnpm)\s+publish\b"), "publishing a package"),
    (re.compile(r"\btwine\s+upload\b"), "publishing a package"),
    (re.compile(r"\bcargo\s+publish\b"), "publishing a package"),
    (re.compile(r"\bgem\s+push\b"), "publishing a package"),
    (re.compile(r"\b(dotnet\s+)?nuget\s+push\b"), "publishing a package"),
    (re.compile(r"\bgh\s+(release|repo)\s+(create|delete|edit)\b"), "changing a remote repository"),
    (re.compile(r"\bgit\b.*--force\b|\bgit\b.*\s-f\b.*\b(origin|upstream)\b"), "forcing a remote"),
    (re.compile(r"\b(reg|regedit)(\.exe)?\s+(add|delete|import)\b"), "changing system settings"),
    (
        re.compile(r"\b(bcdedit|diskpart|netsh|setx|schtasks|sc)(\.exe)?\b\s+\S"),
        "changing system settings",
    ),
    (re.compile(r"\bset-executionpolicy\b"), "changing system settings"),
    (re.compile(r"\b(shutdown|restart-computer|stop-computer)\b"), "changing system settings"),
    (re.compile(r"\bformat(\.com)?\s+[a-z]:"), "changing system settings"),
)

_NETWORK = re.compile(
    r"\b(pip3?|uv|poetry|pipx|conda|mamba)\b.*\b(install|add|sync|update|upgrade)\b"
    r"|\bpython[0-9.]*\s+-m\s+pip\b"
    r"|\b(npm|pnpm|yarn|bun)\b\s+(i|install|ci|add|update|upgrade|dlx|create)\b|\bnpx\b"
    r"|\b(curl|wget|invoke-webrequest|iwr|invoke-restmethod|irm|ssh|scp|ftp|sftp)\b"
    r"|\bgit\b\s+(clone|fetch|pull|submodule|ls-remote)\b"
    r"|\b(winget|choco|scoop|brew|apt|apt-get|dnf|yum)\b"
    r"|\bcargo\s+(install|add|update|fetch)\b|\bgo\s+(get|install|mod\s+download)\b"
    r"|\bdotnet\s+(add\s+package|restore|tool\s+install)\b|\bgem\s+install\b"
    r"|\bhttps?://"
)
_DELETES = re.compile(
    r"(^|[\s;&|(])(del|erase|rm|rmdir|rd|remove-item|ri|clear-content|unlink)(\.exe)?\b"
    r"|\bgit\s+(clean|rm)\b|\bshutil\.rmtree\b"
)


@dataclass(frozen=True, slots=True)
class CommandAssessment:
    """What QUILL makes of a command before anyone is asked."""

    command: str
    kept_for_person: str = ""  # a reason, when the command is never run for an agent
    warnings: tuple[str, ...] = ()

    @property
    def runnable(self) -> bool:
        return not self.kept_for_person

    @property
    def may_always_allow(self) -> bool:
        return self.runnable and not self.warnings


def _tokens(command: str) -> list[str]:
    try:
        return shlex.split(command, posix=os.name != "nt")
    except ValueError:
        return command.split()


def _leaves_root(command: str, root: Path) -> bool:
    """True when an argument names a path outside *root*.

    The first token is the program itself: running the person's own Python
    from where it is installed is not acting outside the project, while
    deleting a file on another drive is.
    """
    for token in _tokens(command)[1:]:
        token = token.strip("\"'")
        if not token or token.startswith("-") and "=" not in token:
            continue
        candidate = token.split("=", 1)[-1]
        looks_absolute = bool(re.match(r"^[A-Za-z]:[\\/]", candidate)) or candidate.startswith((
            "\\\\",
            "/",
            "~",
        ))
        if looks_absolute or ".." in re.split(r"[\\/]", candidate):
            target = Path(candidate).expanduser()
            target = target if target.is_absolute() else root / target
            try:
                resolved = target.resolve()
            except OSError:
                return True
            if resolved != root and root not in resolved.parents:
                return True
    return False


def assess_command(command: str, root: Path) -> CommandAssessment:
    """The warning lines and the never-list, worked out by QUILL."""
    text = " ".join(command.split())
    low = text.lower()
    for pattern, what in _NEVER:
        if pattern.search(low):
            return CommandAssessment(text, kept_for_person=what)
    warnings: list[str] = []
    if _NETWORK.search(low):
        warnings.append(WARN_NETWORK)
    if _DELETES.search(low):
        warnings.append(WARN_DELETES)
    if _leaves_root(text, Path(root).resolve()):
        warnings.append(WARN_OUTSIDE)
    return CommandAssessment(text, warnings=tuple(warnings))


def child_environment(base: dict[str, str] | None = None) -> dict[str, str]:
    """The scrubbed environment a command runs with: no keys, tokens or QUILL_*."""
    from quill.core.ai.harness_credentials import scrubbed_child_env

    env = dict(base) if base is not None else scrubbed_child_env()
    secretish = re.compile(r"(TOKEN|SECRET|PASSWORD|PASSWD|API_?KEY|ACCESS_?KEY|CREDENTIAL)", re.I)
    for name in list(env):
        if name.upper().startswith("QUILL_") or secretish.search(name):
            del env[name]
    env["PYTHONIOENCODING"] = "utf-8"
    env["NO_COLOR"] = "1"
    env["FORCE_COLOR"] = "0"
    return env


class AllowList:
    """The commands this person lets run without asking, in one project.

    Matching is by exact text, or by a prefix the person typed followed by a
    space ("pytest" allows "pytest -q tests"). Never by a pattern the model
    proposed, and never for a command with a warning line.
    """

    def __init__(self, data_dir: Path, project_key: str) -> None:
        self._path = Path(data_dir) / "ai" / "projects" / project_key / "allowed_commands.json"
        self._lock = threading.Lock()

    @property
    def path(self) -> Path:
        return self._path

    def entries(self) -> list[str]:
        raw = read_json(self._path, default={})
        items = raw.get("commands", []) if isinstance(raw, dict) else []
        return [str(item) for item in items if isinstance(item, str) and item.strip()]

    def _save(self, entries: list[str]) -> None:
        unique = list(dict.fromkeys(" ".join(e.split()) for e in entries if e.strip()))
        write_json_atomic(self._path, {"version": 1, "commands": unique})

    def add(self, command: str) -> None:
        with self._lock:
            self._save([*self.entries(), command])

    def remove(self, command: str) -> None:
        with self._lock:
            self._save([e for e in self.entries() if e != command])

    def replace(self, commands: list[str]) -> None:
        with self._lock:
            self._save(commands)

    def allows(self, assessment: CommandAssessment) -> bool:
        if not assessment.may_always_allow:
            return False
        text = assessment.command
        for entry in self.entries():
            if text == entry or text.startswith(entry + " "):
                return True
        return False


@dataclass(frozen=True, slots=True)
class CommandResult:
    command: str
    exit_code: int | None
    output_path: Path
    seconds: float
    stopped: bool = False
    could_not_start: str = ""

    def output(self, limit: int = 2_000_000) -> str:
        try:
            data = self.output_path.read_bytes()[-limit:]
        except OSError:
            return ""
        return data.decode("utf-8", errors="replace")


@dataclass
class CommandRunner:
    """Runs approved commands for one project, one at a time, stoppably."""

    root: Path
    output_dir: Path
    #: Seconds before the person is asked whether to keep waiting.
    notice_after: float = 300.0
    #: ``(seconds_so_far) -> keep_waiting``; asked on the runner's thread.
    keep_waiting: Callable[[float], bool] | None = None
    env: dict[str, str] | None = None
    _current: object | None = field(default=None, init=False, repr=False)
    _stop: threading.Event = field(default_factory=threading.Event, init=False, repr=False)
    _count: int = field(default=0, init=False, repr=False)

    def shell_args(self, command: str) -> str | list[str]:
        """How *command* is handed to the shell, exactly as the person approved it.

        On Windows this is one command line: ``cmd /s /c "..."`` strips the
        outer quotes and runs the rest verbatim, so the quotes inside the
        command survive. An argv list would be re-quoted with backslashes.
        """
        if os.name == "nt":
            comspec = os.environ.get("COMSPEC") or r"C:\Windows\System32\cmd.exe"
            return f'"{comspec}" /d /s /c "{command}"'
        return ["/bin/sh", "-c", command]

    def stop(self) -> None:
        """Stop the running command, tree and all. Safe from any thread."""
        self._stop.set()
        current = self._current
        kill = getattr(current, "kill_tree", None)
        if callable(kill):
            kill()

    def run(self, command: str) -> CommandResult:
        """Run *command* to the end (or Stop). Blocks: call on a worker."""
        from quill.stability.process_tree import start_tree_process

        self._stop.clear()
        self._count += 1
        stamp = time.strftime("%Y%m%d-%H%M%S")
        output_path = Path(self.output_dir) / f"command-{stamp}-{self._count}.txt"
        started = time.monotonic()
        try:
            process = start_tree_process(
                self.shell_args(command),
                cwd=str(self.root),
                env=child_environment(self.env),
                output_path=output_path,
            )
        except (OSError, ValueError) as error:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(str(error), encoding="utf-8")
            return CommandResult(command, None, output_path, 0.0, could_not_start=str(error))
        self._current = process
        next_notice = self.notice_after
        stopped = False
        try:
            while process.poll() is None:
                if self._stop.wait(0.2):
                    process.kill_tree()
                    stopped = True
                    break
                elapsed = time.monotonic() - started
                if self.keep_waiting is not None and elapsed >= next_notice:
                    if not self.keep_waiting(elapsed):
                        process.kill_tree()
                        stopped = True
                        break
                    next_notice += self.notice_after
            code = process.poll()
        finally:
            process.close()
            self._current = None
        return CommandResult(
            command, code, output_path, time.monotonic() - started, stopped=stopped
        )
