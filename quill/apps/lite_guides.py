"""Help > Open User Guide and Help > Open GitHub Guide, for QUILL Lite.

The same two rows QUILL has, opened by the same shared code
(:mod:`quill.ui.guide_opener`), so the two editors find their guides the same
way in every download: Open User Guide on Ctrl+Shift+F1 in both (rule 2), and
Open GitHub Guide keyless in both (rule 9; keymap.py's ``help.github_guide``).

The handlers ask their window for nothing but ``_announce``, so the empty
window's menu bar borrows them too (:mod:`quill.apps.lite_shell_menu`).
"""

from __future__ import annotations

from typing import Any

__all__ = ["DocumentGuidesMixin", "register_lite_github_guide_help"]


class DocumentGuidesMixin:
    """``cmd_user_guide`` and ``cmd_github_guide``, mixed into the document window."""

    _announce: Any

    def cmd_user_guide(self) -> None:
        """Help > Open User Guide (Ctrl+Shift+F1): the guide's contents, in the browser."""
        from quill.core.lite.paths import data_dir
        from quill.ui.guide_opener import open_guide

        found = open_guide(
            "quilllite", "user", render_dir=data_dir() / "user-guide", report=self._announce
        )
        if not found:
            self._announce("The user guide is not in this copy of QUILL Lite.")

    def cmd_github_guide(self) -> None:
        """Help > Open GitHub Guide (no key): the shipped GitHub Guide, in the browser."""
        from quill.ui.guide_opener import open_guide

        open_guide("quilllite", "github", report=self._announce)


def register_lite_github_guide_help(app: Any) -> None:
    """F1 in a GitHub window offers the GitHub Guide (called once at startup).

    The outcome is said by the shell's ``_announce``, the app's one voice that
    also writes braille, because the F1 window may belong to no document.
    """
    from quill.ui.guide_opener import register_github_guide_help

    def _report(message: str) -> None:
        shell = getattr(app, "shell", None)
        if shell is not None:
            shell._announce(message)

    register_github_guide_help("quilllite", _report)
