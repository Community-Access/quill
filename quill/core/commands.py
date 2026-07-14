from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from quill.core.features import feature_for_command

CommandHandler = Callable[[], None]


@dataclass(frozen=True, slots=True)
class Command:
    id: str
    title: str
    keybinding: str | None
    handler: CommandHandler
    feature_id: str


class CommandRegistry:
    #: Upper bound on a single armed repeat count, so a typo (or a runaway
    #: macro) can never spin the editor for an unbounded number of iterations.
    MAX_REPEAT = 1000

    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}
        self._on_run: Callable[[str], None] | None = None
        self._pending_repeat = 1
        self._non_repeatable: set[str] = set()
        #: Optional gate consulted before every run. Given the command id, it
        #: returns True to allow execution or False to block it (having already
        #: surfaced why). This is the single dispatch chokepoint that makes the
        #: remote feature kill switch apply uniformly to keybindings and the
        #: command palette, which both route through :meth:`run`.
        self._run_gate: Callable[[str], bool] | None = None

    def register(
        self,
        command_id: str,
        title: str,
        handler: CommandHandler,
        keybinding: str | None = None,
        feature_id: str | None = None,
    ) -> None:
        if command_id in self._commands:
            raise ValueError(f"Duplicate command: {command_id}")
        self._commands[command_id] = Command(
            id=command_id,
            title=title,
            keybinding=keybinding,
            handler=handler,
            feature_id=feature_id or feature_for_command(command_id),
        )

    def try_register(
        self,
        command_id: str,
        title: str,
        handler: CommandHandler,
        keybinding: str | None = None,
        feature_id: str | None = None,
    ) -> bool:
        """Register if absent. Returns True if registered, False if it already existed.

        Tooling that conditionally wants to add a command (e.g. a Quillin
        extension on startup) can use this to detect collisions without
        having to catch ValueError.
        """
        if command_id in self._commands:
            return False
        self.register(
            command_id,
            title,
            handler,
            keybinding=keybinding,
            feature_id=feature_id,
        )
        return True

    def replace(
        self,
        command_id: str,
        title: str,
        handler: CommandHandler,
        keybinding: str | None = None,
        feature_id: str | None = None,
    ) -> None:
        """Overwrite any existing entry with the same command_id.

        Use sparingly: callers replacing built-in commands are responsible
        for the resulting keyboard-binding and feature-catalog visibility.
        """
        self._commands[command_id] = Command(
            id=command_id,
            title=title,
            keybinding=keybinding,
            handler=handler,
            feature_id=feature_id or feature_for_command(command_id),
        )

    def arm_repeat(self, count: int) -> None:
        """Arm the *next* :meth:`run` to execute its command ``count`` times.

        Mirrors the WordPerfect Editor "Repeat" feature: set a count, then the
        next command repeats. The count is clamped to ``[1, MAX_REPEAT]`` and is
        consumed by the next eligible :meth:`run` (commands marked
        non-repeatable, such as the arming command itself, reset it to 1).
        """
        self._pending_repeat = max(1, min(int(count), self.MAX_REPEAT))

    @property
    def pending_repeat(self) -> int:
        return self._pending_repeat

    def register_non_repeatable(self, command_id: str) -> None:
        """Mark *command_id* so an armed repeat count never multiplies it."""
        self._non_repeatable.add(command_id)

    def set_run_gate(self, gate: Callable[[str], bool] | None) -> None:
        """Install (or clear) the dispatch gate consulted by :meth:`run`."""
        self._run_gate = gate

    def run(self, command_id: str) -> None:
        command = self._commands.get(command_id)
        if command is None:
            raise KeyError(f"Unknown command: {command_id}")
        # Dispatch gate (kill switch): blocked commands never reach their
        # handler, no matter the entry point. The gate itself surfaces why.
        if self._run_gate is not None and not self._run_gate(command_id):
            self._pending_repeat = 1
            return
        count = self._pending_repeat
        self._pending_repeat = 1
        if command_id in self._non_repeatable:
            count = 1
        for _ in range(count):
            if self._on_run is not None:
                self._on_run(command_id)
            command.handler()

    def get(self, command_id: str) -> Command | None:
        return self._commands.get(command_id)

    def set_run_listener(self, listener: Callable[[str], None] | None) -> None:
        self._on_run = listener

    def list(
        self, feature_manager: object | None = None, include_quiet: bool = True
    ) -> list[Command]:
        commands = list(self._commands.values())
        if feature_manager is not None:
            is_visible = getattr(feature_manager, "is_visible", None)
            if callable(is_visible):
                commands = [command for command in commands if is_visible(command.feature_id)]
            elif include_quiet:
                pass
        return sorted(commands, key=lambda item: item.title.lower())

    def keybinding_for(self, command_id: str) -> str | None:
        command = self._commands.get(command_id)
        if command is None:
            return None
        return command.keybinding
