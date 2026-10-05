"""One switch for "Hey QUILL": the setting and the Tools > Speech command agree.

Before this, ``voice_wakeword_enabled`` was a tick box nothing read, and the
command kept its own private state -- two switches for one microphone, and the
one in Settings did nothing. Now:

* the command records what it did in ``voice_wakeword_enabled`` and saves it;
* the Settings tick box starts or stops listening when Settings is closed with OK;
* at startup QUILL resumes listening only when the setting survived loading,
  which it does only when "Keep listening for 'Hey QUILL' across restarts" is on
  (``Settings.from_dict`` drops it otherwise), so a live microphone is never a
  surprise on the next launch.

Startup is quiet: if voice commands are off, Safe Mode is on, there is no
microphone support or no speech model, it simply does not start -- a dialog
before the window has settled would be worse than the missing listener. A
change made in Settings is the user acting, so it goes through the command and
says why it could not start.

Every function here swallows its own errors: these run on startup and on the
settings-apply path, and neither may ever raise.
"""

from __future__ import annotations

from typing import Any


def wakeword_running(host: Any) -> bool:
    """True while the wake-word controller is listening (any state but off)."""
    wake = getattr(host, "_wake", None)
    return wake is not None and getattr(wake, "state", "off") != "off"


def remember_wakeword(host: Any, enabled: bool) -> None:
    """Record the switch's state in settings and save it when it changed."""
    host._wakeword_applied = bool(enabled)
    settings = getattr(host, "settings", None)
    if settings is None or bool(getattr(settings, "voice_wakeword_enabled", False)) == enabled:
        return
    settings.voice_wakeword_enabled = bool(enabled)
    try:
        from quill.core.settings import save_settings

        save_settings(settings)
    except Exception:  # noqa: BLE001 - recording the switch must never raise
        pass


def _can_start_quietly(host: Any) -> bool:
    from quill.core.speech.voice_commands import voice_commands_available

    if not voice_commands_available(
        getattr(host, "settings", None),
        safe_mode_active=bool(getattr(host, "_safe_mode", False)),
    ):
        return False
    from quill.core.speech.capture import capture_available

    if not capture_available():
        return False
    provider = host._voice_provider()
    return bool(provider.list_installed_models())


def start_wakeword_if_enabled(host: Any) -> None:
    """Startup: resume listening when the saved setting asks for it."""
    try:
        settings = getattr(host, "settings", None)
        wanted = bool(getattr(settings, "voice_wakeword_enabled", False))
        host._wakeword_applied = wanted
        if not wanted or wakeword_running(host) or not _can_start_quietly(host):
            return
        from quill.core.speech.wakeword import WakeController

        host._wake = WakeController()
        host._wake_run(host._wake.start())
    except Exception:  # noqa: BLE001 - a startup task must never raise
        pass


def apply_wakeword_setting(host: Any) -> None:
    """Settings OK: start or stop listening when the tick box changed."""
    try:
        settings = getattr(host, "settings", None)
        wanted = bool(getattr(settings, "voice_wakeword_enabled", False))
        if wanted == getattr(host, "_wakeword_applied", False):
            return
        if wanted != wakeword_running(host):
            # The command announces the outcome (or why it could not start)
            # and records the real state through remember_wakeword.
            host.voice_wakeword_toggle()
        if wakeword_running(host) != wanted:
            remember_wakeword(host, wakeword_running(host))
        else:
            host._wakeword_applied = wanted
    except Exception:  # noqa: BLE001 - a settings-apply side effect must never raise
        pass
