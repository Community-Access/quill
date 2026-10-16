"""Say once that Vosk left dictation and the voice features (2026-10-13).

Loading settings migrates a saved Vosk choice (``Settings.from_dict``): a voice
recognition engine of ``"vosk"`` becomes ``"moonshine_tiny"`` and a dictation
engine of ``"vosk"`` becomes ``""``, the default ladder. A setting that changes
under somebody without a word is a setting that lies, so the migration also
leaves ``vosk_retirement_notice`` at ``"voice"``, ``"dictation"`` or ``"both"``,
and this module says the matching sentence once, after the main window is up,
then records ``"done"`` so it is never said again.

The sentence goes through the usual announce path, which also puts it in the
status bar: it is news only QUILL knows, so the screen reader would never say
it (GATE-13). It waits :data:`DELAY_MS` after startup, and longer while a modal
window is open, so the reader's own startup speech (the window title, the focus
landing in the document, a first-run prompt) does not talk over it. ``"done"``
is saved only once it has been said: a notice cut off by a crash or a dialog
that never closed is said at the next start instead of lost. Nothing here may
raise; it runs on the startup path.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

_WHERE = "To choose another, press Ctrl+Comma and find voice engine."
VOICE_NOTICE = (
    "Vosk is no longer used for voice commands. Voice commands and Hey QUILL now "
    "use Moonshine tiny, which is already installed and understands English only. "
    + _WHERE
    + " Podcast chapters still use Vosk."
)
DICTATION_NOTICE = (
    "Vosk is no longer a dictation engine. Dictation now uses your default engine. "
    "To choose another, open Speech and Dictation and its Dictation tab."
)
BOTH_NOTICE = (
    "Vosk is no longer used for dictation or voice commands. Dictation now uses your "
    "default engine, and voice commands and Hey QUILL use Moonshine tiny, which "
    "understands English only. Choose others in Speech and Dictation, or press "
    "Ctrl+Comma and find voice engine. "
    "Podcast chapters still use Vosk."
)

_NOTICES = {"voice": VOICE_NOTICE, "dictation": DICTATION_NOTICE, "both": BOTH_NOTICE}

#: How long after startup the notice waits, so it follows the reader's own
#: startup speech instead of being cut off by it.
DELAY_MS = 1500
#: While a modal window is open, look again this often, this many times.
RETRY_MS = 2000
_RETRIES = 30

Later = Callable[[int, Callable[[], None]], Any]


def pending_notice(settings: Any) -> str:
    """The sentence still to be said for *settings*, or ``""``."""
    return _NOTICES.get(str(getattr(settings, "vosk_retirement_notice", "") or ""), "")


def _modal_open() -> bool:
    try:
        import wx

        return any(
            isinstance(window, wx.Dialog) and window.IsModal() for window in wx.GetTopLevelWindows()
        )
    except Exception:  # noqa: BLE001 - no wx answer: nothing in the way
        return False


def _wx_later(delay_ms: int, run: Callable[[], None]) -> Any:
    import wx

    return wx.CallLater(delay_ms, run)


def say_now(host: Any) -> bool:
    """Say the pending notice, then remember it was said. True if it spoke."""
    try:
        settings = getattr(host, "settings", None)
        message = pending_notice(settings)
        if not message:
            return False
        host._announce(message)
        settings.vosk_retirement_notice = "done"
        try:
            from quill.core.settings import save_settings

            save_settings(settings)
        except Exception:  # noqa: BLE001 - persistence is best-effort
            pass
        return True
    except Exception:  # noqa: BLE001 - a notice is never worth a failed start
        return False


def surface_vosk_retirement_notice(
    host: Any,
    *,
    later: Later | None = None,
    modal_open: Callable[[], bool] | None = None,
) -> bool:
    """Arrange for the pending notice to be said once the startup has settled.

    True when a notice is pending and has been scheduled. Still blocked by a
    modal window after every retry, it stays pending for the next start.
    """
    try:
        if not pending_notice(getattr(host, "settings", None)):
            return False
        schedule = later or _wx_later
        blocked = modal_open or _modal_open
        tries = [_RETRIES]

        def attempt() -> None:
            if blocked():
                if tries[0] > 0:
                    tries[0] -= 1
                    schedule(RETRY_MS, attempt)
                return
            say_now(host)

        schedule(DELAY_MS, attempt)
        return True
    except Exception:  # noqa: BLE001 - a notice is never worth a failed start
        return False
