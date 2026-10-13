"""Say once that Vosk left dictation and the voice features (2026-10-13).

Loading settings migrates a saved Vosk choice (``Settings.from_dict``): a voice
recognition engine of ``"vosk"`` becomes ``"moonshine_tiny"`` and a dictation
engine of ``"vosk"`` becomes ``""``, the default ladder. A setting that changes
under somebody without a word is a setting that lies, so the migration also
leaves ``vosk_retirement_notice`` at ``"voice"`` or ``"dictation"``, and this
module says the matching sentence once, after the main window is up, then
records ``"done"`` so it is never said again.

The sentence goes to the status bar and through the usual announce path: it is
news only QUILL knows, so the screen reader would never say it (GATE-13).
Nothing here may raise; it runs on the startup path.
"""

from __future__ import annotations

from typing import Any

VOICE_NOTICE = (
    "Vosk is no longer used for voice commands or dictation. Voice commands and "
    "Hey QUILL now use Moonshine tiny, which is already installed. Podcast "
    "chapters still use Vosk."
)
DICTATION_NOTICE = "Vosk is no longer a dictation engine. Dictation now uses your default engine."

_NOTICES = {"voice": VOICE_NOTICE, "dictation": DICTATION_NOTICE}


def pending_notice(settings: Any) -> str:
    """The sentence still to be said for *settings*, or ``""``."""
    return _NOTICES.get(str(getattr(settings, "vosk_retirement_notice", "") or ""), "")


def surface_vosk_retirement_notice(host: Any) -> bool:
    """Say the pending notice once and remember it was said. True if it spoke."""
    try:
        settings = getattr(host, "settings", None)
        message = pending_notice(settings)
        if not message:
            return False
        settings.vosk_retirement_notice = "done"
        try:
            from quill.core.settings import save_settings

            save_settings(settings)
        except Exception:  # noqa: BLE001 - persistence is best-effort
            pass
        host._set_status_quiet(message)
        host._announce(message)
        return True
    except Exception:  # noqa: BLE001 - a notice is never worth a failed start
        return False
