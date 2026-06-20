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
    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}
        self._on_run: Callable[[str], None] | None = None

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

    def run(self, command_id: str) -> None:
        command = self._commands.get(command_id)
        if command is None:
            raise KeyError(f"Unknown command: {command_id}")
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
