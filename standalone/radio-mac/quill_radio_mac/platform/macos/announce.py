"""Post spoken announcements to VoiceOver on macOS.

Uses NSAccessibility's announcement notification via pyobjc when available.
If pyobjc isn't installed, falls back to a no-op so imports never fail. Backs
the app's announce handler on macOS: every user-facing status change in
Quill Radio for Mac (station changed, play/stop, recording started, error
recovered, dialog opened/closed) routes through :func:`announce` so a
VoiceOver user hears it without needing to poll a status bar.

Threading contract: :func:`announce` is safe to call from any thread. The
actual ``NSAccessibilityPostNotificationWithUserInfo`` call must happen on
the main thread (AppKit's rule, not just a performance concern); when called
off the main thread this module marshals the post onto the main dispatch
queue via ``libdispatch`` rather than touching AppKit directly. Ported
verbatim from ``quill.platform.macos.announce`` (upstream issue #29 / #42 /
#44 / #45 / #19); only this docstring and module-level comments were
expanded for the port.

macOS notes: without pyobjc (e.g. running the pytest suite on Windows, or a
from-source checkout before ``pip install pyobjc`` has run), every function
here returns ``False``/no-ops instead of raising -- callers never need an
``if sys.platform == "darwin"`` guard of their own.
"""

from __future__ import annotations

# VoiceOver renders very long single announcements poorly (the start scrolls off
# before the user can review it). Cap the payload at a generous length and mark
# truncation, so a runaway status string can't produce an unreadable wall of
# text. ~4096 chars is roughly 600 words -- longer than any intentional message.
_MAX_ANNOUNCE_LEN = 4096


def _truncate(message: str) -> str:
    """Clip *message* to :data:`_MAX_ANNOUNCE_LEN`, marking truncation with an ellipsis."""
    if len(message) <= _MAX_ANNOUNCE_LEN:
        return message
    return message[:_MAX_ANNOUNCE_LEN] + "…"


def announce(message: str, *, interrupt: bool = True) -> bool:
    """Speak ``message`` through VoiceOver. Returns True if dispatched.

    *interrupt* controls priority (finding #45): ``True`` (the default) posts at
    high priority so the message interrupts VoiceOver's current utterance -- used
    for internal-state narration the screen reader won't pick up on its own.
    ``False`` posts at low priority so routine status does not talk over what the
    user is already hearing. The message is capped in length (finding #44) so a
    runaway string can't become an unreadable wall of text under VoiceOver.

    The Cocoa calls are guarded with a main-thread check (finding #19): a future
    background callback that skips ``call_ui_safely`` is marshalled onto the main
    queue rather than touching AppKit off-thread.

    Returns ``False`` (no-op) when ``message`` is empty, when pyobjc / AppKit
    is unavailable (including on any non-macOS platform, where ``import
    AppKit`` always fails), or when the Cocoa call itself raises.
    """
    if not message:
        return False
    try:
        import AppKit  # type: ignore[import-not-found]
        import Foundation  # type: ignore[import-not-found]
    except ImportError:
        return False

    payload = _truncate(message)
    priority = (
        AppKit.NSAccessibilityPriorityHigh if interrupt else AppKit.NSAccessibilityPriorityLow
    )

    try:
        if not Foundation.NSThread.isMainThread():
            # Defense in depth: marshal the AppKit touch onto the main queue so a
            # background TaskManager callback can't reach Cocoa off-thread. Fire
            # and forget -- the caller already treats announce as best-effort.
            return _dispatch_to_main(AppKit, Foundation, payload, priority)
        _post(AppKit, Foundation, payload, priority)
        return True
    except Exception:
        return False


def _post(AppKit, Foundation, payload: str, priority: int) -> None:
    """Post the VoiceOver announcement notification. Must run on the main thread."""
    app = AppKit.NSApplication.sharedApplication()
    window = app.keyWindow() or app.mainWindow()
    element = window if window is not None else app
    user_info = {
        AppKit.NSAccessibilityAnnouncementKey: Foundation.NSString.stringWithString_(payload),
        AppKit.NSAccessibilityPriorityKey: priority,
    }
    AppKit.NSAccessibilityPostNotificationWithUserInfo(
        element,
        AppKit.NSAccessibilityAnnouncementRequestedNotification,
        user_info,
    )


def _dispatch_to_main(AppKit, Foundation, payload: str, priority: int) -> bool:
    """Re-post *payload* on the main queue and return True (best-effort).

    Uses libdispatch when available; if it isn't, falls back to posting directly
    (NSAccessibilityPostNotification is documented thread-safe, so the fallback
    is no worse than the pre-guard behavior).
    """
    try:
        from libdispatch import (  # type: ignore[import-not-found]
            dispatch_async,
            dispatch_get_main_queue,
        )
    except ImportError:
        _post(AppKit, Foundation, payload, priority)
        return True

    def _run() -> None:
        try:
            _post(AppKit, Foundation, payload, priority)
        except Exception:  # noqa: BLE001
            pass

    dispatch_async(dispatch_get_main_queue(), _run)
    return True
