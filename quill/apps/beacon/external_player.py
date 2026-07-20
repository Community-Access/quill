"""External media-player handoff (PRD 11.5, 44.3).

The built-in player depends on a platform media backend that is not always
present. This module hands playback to an external player the user already has
-- VLC, mpv, or the system default -- with a start time so a saved time-point
resume still works outside the built-in player.

``build_command`` is pure, testable logic. ``launch`` runs it fail-safe: a
missing player falls back to the system default handler, and any error is
returned as a message rather than raised. No project data leaves the machine;
only the media URL the user already saved is passed to the chosen player.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any

# Players that accept a start-time argument. The system default ("default") has
# no start-time support and is the always-available fallback.
PLAYER_VLC = "vlc"
PLAYER_MPV = "mpv"
PLAYER_DEFAULT = "default"
PLAYERS = (PLAYER_DEFAULT, PLAYER_VLC, PLAYER_MPV)

SETTINGS_FILE = "player_settings.json"


@dataclass
class PlayerSettings:
    """User-configurable external-player preferences.

    - ``default_player``: the player used when no per-type override applies.
    - ``custom_path``: maps a player name (``vlc``/``mpv``) to an absolute path
      on this machine, for installs not on ``PATH``.
    - ``per_type``: maps a resource type (e.g. ``radioStream``,
      ``podcastEpisode``) to a player name, so radio opens in one player and
      podcasts in another.
    """

    default_player: str = PLAYER_DEFAULT
    custom_path: dict[str, str] = field(default_factory=dict)
    per_type: dict[str, str] = field(default_factory=dict)

    def player_for(self, resource_type: str | None = None) -> str:
        if resource_type and resource_type in self.per_type:
            return self.per_type[resource_type]
        return self.default_player

    def exe_for(self, player: str) -> str:
        """Resolve the executable for a player, honoring a custom path."""
        return self.custom_path.get(player, player)

    def to_dict(self) -> dict:
        return {
            "default_player": self.default_player,
            "custom_path": dict(self.custom_path),
            "per_type": dict(self.per_type),
        }

    @classmethod
    def from_dict(cls, d: dict) -> PlayerSettings:
        return cls(
            default_player=d.get("default_player", PLAYER_DEFAULT),
            custom_path=dict(d.get("custom_path") or {}),
            per_type=dict(d.get("per_type") or {}),
        )


def load_settings(data_dir) -> PlayerSettings:
    """Load player settings from the data dir; defaults if missing/corrupt."""
    path = os.path.join(str(data_dir), SETTINGS_FILE)
    try:
        with open(path, encoding="utf-8") as fh:
            return PlayerSettings.from_dict(json.load(fh))
    except (FileNotFoundError, ValueError, OSError):
        return PlayerSettings()


def save_settings(data_dir, settings: PlayerSettings) -> bool:
    """Persist player settings. Fail-safe; returns False on write error."""
    path = os.path.join(str(data_dir), SETTINGS_FILE)
    try:
        os.makedirs(str(data_dir), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(settings.to_dict(), fh, indent=2, ensure_ascii=False)
        return True
    except OSError:
        return False


def build_command(
    url: str,
    start_ms: int | None,
    *,
    player: str = PLAYER_DEFAULT,
    custom_path: dict[str, str] | None = None,
) -> list[str] | None:
    """Return an argv list for the chosen player, or None for the system default.

    Returns None when the caller should use the OS default handler (which has
    no start-time support). Start time is converted to seconds. ``custom_path``
    overrides the player executable for installs not on ``PATH``.
    """
    if not url:
        return None
    start_s = (start_ms or 0) / 1000.0
    cp = custom_path or {}
    if player == PLAYER_VLC:
        return [cp.get(PLAYER_VLC, "vlc"), f"--start-time={start_s}", "--", url]
    if player == PLAYER_MPV:
        return [cp.get(PLAYER_MPV, "mpv"), f"--start={start_s}", url]
    return None  # system default


def launch(
    url: str,
    start_ms: int | None = None,
    *,
    player: str = PLAYER_DEFAULT,
    settings: PlayerSettings | None = None,
    resource_type: str | None = None,
) -> dict[str, Any]:
    """Hand off playback to the chosen player. Fail-safe; never raises.

    Returns ``{"ok": bool, "message": str, "player": str}``. If ``settings`` is
    given, the player is resolved from per-type/default and a custom path is
    honored. If the chosen player is not installed, falls back to the system
    default handler.
    """
    if not url or not url.strip():
        return {"ok": False, "message": "no URL", "player": player}
    custom_path = None
    if settings is not None:
        player = settings.player_for(resource_type)
        custom_path = settings.custom_path
    cmd = build_command(url, start_ms, player=player, custom_path=custom_path)
    if cmd is None:
        return _open_default(url)
    exe = cmd[0]
    if not shutil.which(exe):
        # Fall back to the system default handler with no start time.
        res = _open_default(url)
        res["fallback"] = f"{exe} not installed; opened with system default"
        return res
    try:
        if sys.platform.startswith("win"):
            # Detach so closing Beacon does not kill the player.
            subprocess.Popen(
                cmd,
                close_fds=True,
                creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                | getattr(subprocess, "DETACHED_PROCESS", 0),
            )
        else:
            subprocess.Popen(cmd, close_fds=True, start_new_session=True)
    except Exception as ex:
        return {"ok": False, "message": f"launch failed: {ex}", "player": player}
    return {"ok": True, "message": f"launched {exe}", "player": player}


def _open_default(url: str) -> dict[str, Any]:
    try:
        if sys.platform.startswith("win"):
            os_startfile(url)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", url])
        else:
            subprocess.Popen(["xdg-open", url])
    except Exception as ex:
        return {"ok": False, "message": f"open failed: {ex}", "player": PLAYER_DEFAULT}
    return {"ok": True, "message": "opened with system default", "player": PLAYER_DEFAULT}


def os_startfile(url: str) -> None:  # thin wrapper for testability
    import os

    os.startfile(url)  # noqa: S606 (local user media URL)
