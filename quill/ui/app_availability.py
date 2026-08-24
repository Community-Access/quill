"""Why a command cannot run right now -- the probe every shell app answers with.

The command palette asks this probe why a command is unavailable and says the
answer, instead of the bare "(unavailable)" that leaves a screen-reader user
guessing. ``AppShellFrame`` registers it on the shell's ``CommandRegistry`` at
startup, so every companion app has it from the first launch (11.2).

QUILL's ``MainFrame`` has had one since the remote kill switch shipped: the
command palette asks it, and says the reason instead of the bare
"(unavailable)" that leaves a screen-reader user guessing. The companion apps
never set one, so every dimmed row in Quill Radio's and QUILL Cast's palettes
said nothing at all (list.md 11.2).

Extracted from ``app_shell.py`` under GATE-11. Side-effect-free by contract:
the dispatch gate speaks and blocks; this only answers.
"""

from __future__ import annotations


class CommandAvailabilityMixin:
    """Whether a command can run, and -- when it cannot -- why.

    Both halves in one place: ``_feature_enabled`` is the yes/no the menus
    ask, and ``_command_unavailable_reason`` is the sentence the palette
    says. They read the same two sources, so they cannot drift.
    """

    def _command_unavailable_reason(self, command_id: str) -> str:
        """Side-effect-free probe: why *command_id* cannot run, or "".

        The same source the menus and the dispatch gate consult, with no
        announcement side effects, so a surface can explain unavailability
        *before* the listener tries the command (11.2).
        """
        command = self.commands.get(command_id)
        feature_id = command.feature_id if command is not None else "core.app"
        locks = getattr(self, "_feature_locks", None)
        if locks is not None and locks.is_locked(feature_id):
            reason = locks.reason(feature_id) or "a QUILL safety advisory"
            return f"Turned off by a safety update: {reason}"
        if getattr(self, "_safe_mode", False):
            from quill.core import dimmed_reason

            features = getattr(self, "features", None)
            if features is not None and not features.is_enabled(feature_id):
                return dimmed_reason.safe_mode()
        return ""

    def _feature_enabled(self, feature_id: str) -> bool:
        locks = getattr(self, "_feature_locks", None)
        if locks is not None and locks.is_locked(feature_id):
            return False
        features = getattr(self, "features", None)
        return True if features is None else features.is_enabled(feature_id)
