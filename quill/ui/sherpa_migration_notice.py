"""Say once that Locked Dictation's Nemotron and Parakeet engines became one (D-26).

On 2026-10-16 QUILL's two Locked Dictation engines of its own, ``nemotron`` and
``parakeet``, were replaced by one engine, QUILL speech models (``sherpa``),
which runs the same models from the one folder QUILL Lite and QUILL
Transcribe use; on 2026-10-17 the duplicate path was formally deprecated
(QUILL 1.1, removed in QUILL 1.2; dictation design record sections 32.6 and
35). Loading settings moves a saved ``nemotron`` or ``parakeet`` to
``sherpa`` (``Settings.from_dict``), and the deprecation policy says such a
move is never silent: ``sherpa_migration_notice`` is ``"pending"`` until this
module has said so once, then ``"done"``.

**What is said.** One plain sentence through the usual announce path (which
also sets the status bar), because it is news only QUILL knows (GATE-13). When
the older Nemotron's files are still on disk -- a different model from the
catalogue's Nemotron 3.5, which nothing uses any more -- the sentence becomes a
Yes/No question instead, with **No the default**: "Delete them to free 650
MB?". The message box is read whole by the screen reader, so nothing is
announced beside it. On Yes the files are deleted and the space actually freed
is said ("Freed 650 MB."); on No they stay, and QUILL never asks again. Nothing
is deleted without that Yes (policy rule 4), and the engine choice itself is
never changed by this module.

It waits :data:`DELAY_MS` after startup, and longer while a modal window is
open, like the Vosk notice it copies (:mod:`quill.ui.vosk_retirement_notice`).
``"done"`` is saved only once it has been said or answered. Nothing here may
raise; it runs on the startup path.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.ui.vosk_retirement_notice import DELAY_MS, RETRY_MS, Later

NOTICE = (
    "Locked Dictation's Nemotron and Parakeet engines are now one engine, QUILL speech "
    "models, which uses the same models as QUILL Lite and QUILL Transcribe. Your choice "
    "moved with it, and a Parakeet you had was moved, not downloaded again. "
    "Choose another engine in Speech and Dictation, on its Dictation tab."
)
TITLE = "QUILL speech models"
_RETRIES = 30


def pending(settings: Any) -> bool:
    return str(getattr(settings, "sherpa_migration_notice", "") or "") == "pending"


def size_words(size: int) -> str:
    """*size* bytes in the words the deprecation policy uses: "650 MB", "1.5 GB"."""
    if size >= 1_000_000_000:
        return f"{size / 1_000_000_000:.1f} GB"
    return f"{max(1, round(size / 1_000_000))} MB"


def question(leftovers: list[tuple[Path, int]]) -> str:
    """The Yes/No wording when old files are still on disk."""
    total = sum(size for _folder, size in leftovers)
    return (
        f"{NOTICE}\n\nThe older Nemotron model QUILL used before is no longer used; to "
        "dictate with Nemotron, download Nemotron 3.5 in Speech Models. "
        f"Delete the older files to free {size_words(total)}? No keeps them."
    )


def _finish(host: Any) -> None:
    settings = host.settings
    settings.sherpa_migration_notice = "done"
    try:
        from quill.core.settings import save_settings

        save_settings(settings)
    except Exception:  # noqa: BLE001 - persistence is best-effort
        pass


def say_now(
    host: Any,
    *,
    leftovers: Callable[[], list[tuple[Path, int]]] | None = None,
    remove: Callable[[list[Path]], int] | None = None,
) -> bool:
    """Say (or ask) the pending notice, then remember it. True if it ran."""
    try:
        if not pending(getattr(host, "settings", None)):
            return False
        from quill.core.speech import sherpa_migration

        found = (leftovers or sherpa_migration.legacy_leftovers)()
        if not found:
            host._announce(NOTICE)
            _finish(host)
            return True
        import wx

        answer = host._show_message_box(
            question(found), TITLE, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION
        )
        _finish(host)
        if answer == wx.YES:
            freed = (remove or sherpa_migration.remove_leftovers)([f for f, _s in found])
            host._announce(f"Freed {size_words(freed)}." if freed else "Nothing was freed.")
        return True
    except Exception:  # noqa: BLE001 - a notice is never worth a failed start
        return False


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


def surface_sherpa_migration_notice(
    host: Any,
    *,
    later: Later | None = None,
    modal_open: Callable[[], bool] | None = None,
) -> bool:
    """Arrange for the pending notice once the startup has settled (after the
    Vosk notice's delay, so the two never talk over each other). True when one
    is pending and has been scheduled."""
    try:
        if not pending(getattr(host, "settings", None)):
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

        schedule(DELAY_MS + RETRY_MS, attempt)
        return True
    except Exception:  # noqa: BLE001 - a notice is never worth a failed start
        return False
