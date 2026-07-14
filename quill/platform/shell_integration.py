"""Platform-neutral shell/file-type integration (routes to the OS implementation)."""

from __future__ import annotations

import sys
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ShellIntegrationStatus:
    """Outcome of a best-effort shell-integration install (#8).

    File-type association on macOS is a best-effort runtime step (the primary
    mechanism is the app bundle's ``Info.plist``); when the optional ``duti``
    helper is missing -- the common case -- the install is a silent no-op unless
    the caller can see *why* it did nothing. ``installed`` is False and
    ``message`` explains the remedy so the UI can tell the user instead of
    reporting a false success.
    """

    installed: bool
    message: str


if sys.platform == "darwin":
    from quill.platform.macos.shell_integration import (
        build_shell_integration_plan,
        install_shell_integration,
        launcher_command,
        remove_shell_integration,
    )
elif sys.platform.startswith("win"):
    from quill.platform.windows.shell_integration import (
        build_shell_integration_plan,
        install_shell_integration,
        launcher_command,
        remove_shell_integration,
    )
else:  # pragma: no cover - other platforms
    from dataclasses import dataclass as _dc

    @_dc(frozen=True, slots=True)
    class _PlanEntry:
        path: str

    def launcher_command() -> str:
        return "quill"

    def build_shell_integration_plan(command: str | None = None) -> list[_PlanEntry]:
        return []

    def install_shell_integration(command: str | None = None) -> ShellIntegrationStatus:
        return ShellIntegrationStatus(False, "Shell integration is not supported on this platform.")

    def remove_shell_integration() -> None:
        return None


__all__ = [
    "ShellIntegrationStatus",
    "build_shell_integration_plan",
    "install_shell_integration",
    "launcher_command",
    "remove_shell_integration",
]
