"""The crash dialog's choice, carried out: email support, copy, or nothing.

Split out of :mod:`quill.__main__` (2026-09-26) when crash reports moved from
GitHub issues to email. The excepthook shows
:class:`quill.ui.crash_report_dialog.CrashReportDialog`; this acts on what the
user chose. "Email support" opens the user's own mail program with the
redacted report addressed to ``support@community-access.org`` through
:func:`quill.ui.support_dialog.send_by_mail` -- the one handoff every support
path in the family shares, so the length cut, the clipboard copy and the "no
mail program" answer are the same code. No GitHub, no token, no network call
by QUILL: nothing is sent until the user sends it from their mail program.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill import __version__
from quill.stability.crash_email import build_crash_support_message
from quill.ui import support_dialog
from quill.ui.crash_report_dialog import merge_user_context_into_body


def act_on_crash_choice(
    payload: Any,
    result: Any,
    host: Any = None,
    *,
    copy: Callable[[str], bool],
    notify: Callable[[str], None],
    find_window: Callable[[], object | None],
) -> str:
    """Carry out what the user chose in the crash dialog. Returns what happened.

    ``"cancel"`` does nothing (the local crash file stays). ``"copy"`` puts
    the report on the clipboard and says so. ``"send"`` opens the user's own
    mail program with the report addressed to support -- the same handoff as
    Help > Get Help from Support (:func:`quill.ui.support_dialog.send_by_mail`),
    so a crash report and a support message arrive looking alike, and so the
    "no mail program" answer, the length cut and the clipboard copy are the
    same code. Since 2026-09-26 there is no GitHub path and no token.

    Returns ``"cancelled"``, ``"copied"``, ``"mailed"`` or ``"clipboard"``
    (no mail program answered; the report is on the clipboard).
    """
    act = getattr(result, "act", "cancel")
    if act == "cancel":
        return "cancelled"
    merged = merge_user_context_into_body(payload.body, result)
    if act == "copy":
        copy(merged)
        notify(
            "The crash report was copied to your clipboard. Paste it into an "
            "email to support@community-access.org to send it."
        )
        return "copied"

    import platform as platform_module

    crash_host = host if host is not None else _CrashReportHost(find_window(), copy)
    facts_of = getattr(crash_host, "ai_support_facts", None)
    try:
        extra = facts_of() if callable(facts_of) else {}
    except Exception:  # noqa: BLE001 - a missing fact must not block the report
        extra = {}
    try:
        platform_name = platform_module.platform()
    except Exception:  # noqa: BLE001
        platform_name = ""
    message = build_crash_support_message(
        summary=payload.summary,
        body=merged,
        app_version=str(payload.metadata.get("quill_version", "") or __version__ or ""),
        platform_name=platform_name,
        screen_reader_name=str(payload.metadata.get("screen_reader", "") or ""),
        extra=extra if isinstance(extra, dict) else {},
    )
    if support_dialog.send_by_mail(
        crash_host,
        message,
        title="Report Crash",
        opened=(
            "Your mail program is opening with the crash report ready. "
            "Nothing is sent until you send it there."
        ),
    ):
        return "mailed"
    return "clipboard"


class _CrashReportHost:
    """What :func:`quill.ui.support_dialog.send_by_mail` needs, at crash time.

    The support surface asks its host for a parent window, a way to speak and
    a clipboard. In the excepthook the editor may be half torn down, so each
    is looked up on the live main window when there is one and falls back to
    the excepthook's own best-effort helpers when there is not.
    """

    def __init__(self, frame: object | None, copy: Callable[[str], bool]) -> None:
        self.frame = frame
        self._copy = copy
        self._owner = _find_main_frame_owner()

    def _announce(self, text: str) -> None:
        speak = getattr(self._owner, "_announce", None)
        if callable(speak):
            speak(text)

    def _copy_to_clipboard(self, text: str) -> bool:
        return bool(self._copy(text))

    def ai_support_facts(self) -> dict[str, str]:
        facts_of = getattr(self._owner, "ai_support_facts", None)
        facts = facts_of() if callable(facts_of) else {}
        return facts if isinstance(facts, dict) else {}


def _find_main_frame_owner() -> object | None:
    """Return the object that owns the editor (the MainFrame mixin), or ``None``."""
    try:
        import wx  # type: ignore[import-not-found]

        app = wx.GetApp()  # type: ignore[attr-defined]
        top = app.GetTopWindow() if app is not None else None
    except Exception:  # noqa: BLE001
        return None
    for owner in (top, getattr(top, "_main", None), getattr(top, "frame", None)):
        if owner is not None and callable(getattr(owner, "_announce", None)):
            return owner
    return top
