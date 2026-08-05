"""Dispatch a parsed :class:`VoiceIntent` to the media player (PRD Section 18).

The bridge between the pure command parser (:mod:`quill.core.media.voice`) and the
player. It touches only the player's public transport API plus a handful of thin,
optional ``voice_*`` hooks on the host, so the mapping and the skip/seek clamping
are unit-testable with a fake host -- no wx, no audio engine.

``apply_voice_intent`` returns the phrase to announce (empty when the invoked
handler announces for itself, e.g. Where Am I / Summarize).
"""

from __future__ import annotations

from typing import Any

from quill.core.media.timecode import format_timecode
from quill.core.media.voice import VoiceIntent


def _clamp_target(player: Any, target_ms: int) -> int:
    target = max(0, int(target_ms))
    length = int(player.length_ms() or 0)
    if length > 0:
        target = min(target, length)
    return target


def _hook(host: Any, name: str) -> Any:
    """Return a callable host hook, or ``None`` when the host doesn't provide it."""
    fn = getattr(host, name, None)
    return fn if callable(fn) else None


def apply_voice_intent(host: Any, intent: VoiceIntent | None) -> str:
    """Carry out ``intent`` against ``host``; return the phrase to announce."""
    if intent is None:
        return "Sorry, I didn't catch a command."
    player = getattr(host, "_player", None)
    action = intent.action

    if player is not None:
        if action == "play":
            player.play()
            return "Playing"
        if action == "pause":
            player.pause()
            return "Paused"
        if action == "stop":
            player.stop()
            return "Stopped"
        if action == "toggle":
            player.toggle()
            return "Playing" if player.is_playing() else "Paused"
        if action == "skip":
            target = _clamp_target(player, player.playhead_ms() + intent.value)
            player.seek_to(target)
            verb = "Forward to" if intent.value >= 0 else "Back to"
            return f"{verb} {format_timecode(target, always_hours=True)}"
        if action == "seek":
            target = _clamp_target(player, intent.value)
            player.seek_to(target)
            return f"Jumped to {format_timecode(target, always_hours=True)}"
        if action == "mute":
            player.toggle_mute()
            return "Toggled mute"

    hook_map = {
        "next_chapter": ("voice_next_chapter", "Next chapter"),
        "prev_chapter": ("voice_prev_chapter", "Previous chapter"),
        "bookmark": ("voice_add_bookmark", "Bookmark added"),
        "where_am_i": ("voice_where_am_i", ""),
        "summarize": ("voice_summarize", ""),
        "recap": ("voice_recap", ""),
    }
    if action in hook_map:
        name, announcement = hook_map[action]
        hook = _hook(host, name)
        if hook is not None:
            hook()
            return announcement
        return "That command isn't available right now."

    if action == "sleep":
        hook = _hook(host, "voice_set_sleep")
        if hook is not None:
            hook(intent.value)
            return "Sleep timer off" if intent.value == 0 else f"Sleep in {intent.value} minutes"
        return "Sleep timer isn't available right now."
    if action == "sleep_eoc":
        hook = _hook(host, "voice_sleep_eoc")
        if hook is not None:
            hook()
            return "Sleep at end of chapter"
        return "Sleep timer isn't available right now."

    if action in {"faster", "slower", "volume_up", "volume_down"}:
        return "Use the on-screen control for that."

    return "Sorry, I didn't catch a command."


__all__ = ["apply_voice_intent"]
