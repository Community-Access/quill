"""MainFrame mixin: open the QUILL Media Player from inside QUILL.

The in-QUILL entry point launches the standalone **Quill Media Player** app
(`quill.apps.player`) through QUILL's existing companion-launch path -- the same
mechanism the Tools > Media items use for Quill Radio and Cast. This deliberately
reuses the one codebase (shared library, bookmarks, resume positions, and
settings) rather than embedding a second player, and keeps the edit to MainFrame
tiny and low-risk (``player.md`` Section 9.11; the embedded-window option is a
documented future expansion, Section 18).
"""

from __future__ import annotations


class MediaPlayerMixin:
    """Adds the ``app.open_media_player`` command to MainFrame."""

    def _register_media_player_commands(self) -> None:
        self.commands.register(  # type: ignore[attr-defined]
            "app.open_media_player",
            "Open the Media Player",
            self.open_media_player,
            self._binding_for("app.open_media_player"),  # type: ignore[attr-defined]
        )

    def open_media_player(self) -> None:
        """Open the standalone Quill Media Player (offering to install it if absent)."""
        from quill.ui.companion_offer import try_open_or_offer

        try_open_or_offer(self, "player")
