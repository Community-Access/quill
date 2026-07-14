"""Post-transcription "what would you like me to make of this?" (the Listening Companion).

When a transcript is ready, this offers the context-aware Transcript Actions
(:mod:`quill.core.ai.transcript_actions`) as a gentle, single-choice list. Picking one
runs its instruction over the transcript through the configured AI provider and opens
the finished document in a new buffer — minutes, action items, study notes, a clean
draft — reviewed and editable. "Just keep the transcript" falls back to the plain
transcript result.

Built as its own module (not in the size-budgeted ``main_frame``) so the host only needs
a one-line hook. The provider call goes through :class:`ProviderChatBackend`, so it uses
the user's unified AI Hub connection; everything is guarded on AI being enabled and a
provider being reachable, and degrades cleanly to the plain transcript when it is not.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

# generate_action_text lives in core now (shared with the watch worker); re-exported
# here so existing callers/tests keep importing it from this module.
from quill.core.ai.transcript_actions import generate_action_text

if TYPE_CHECKING:
    from quill.core.ai.transcript_actions import TranscriptAction

__all__ = [
    "build_action_labels",
    "generate_action_text",
    "offer_transcript_actions",
    "run_transcript_actions_on_document",
]

_JUST_TRANSCRIPT = "Just keep the transcript"


def build_action_labels(actions: list[TranscriptAction]) -> list[str]:
    """The chooser labels: each action's name + description, then the opt-out."""
    labels = [f"{a.name} — {a.description}" for a in actions]
    labels.append(_JUST_TRANSCRIPT)
    return labels


def _action_backend() -> Any | None:
    """The configured provider backend, or None when AI is off/unavailable."""
    from quill.core.ai.model_manager import load_ai_enabled
    from quill.core.ai.provider_backend import ProviderChatBackend

    if not load_ai_enabled():
        return None
    backend = ProviderChatBackend()
    ok, _reason = backend.is_available()
    return backend if ok else None


def offer_transcript_actions(controller: Any, transcript: str, file_name: str) -> bool:
    """Offer Transcript Actions for a finished transcript.

    Returns True when an action was chosen and started (the caller should not also
    show the plain transcript result); False to fall back to the plain result —
    including when AI is off, no provider is reachable, or the user opts out.
    """
    if not transcript.strip():
        return False
    backend = _action_backend()
    if backend is None:
        # A high-intent moment: offer the gentle AI setup on-ramp instead of a dead
        # end. If the user sets AI up, continue straight into the actions.
        from quill.ui.ai_setup_wizard import maybe_offer_ai_setup

        ready = maybe_offer_ai_setup(
            controller,
            reason="To turn this transcript into minutes, action items, or notes, QUILL needs AI.",
        )
        if not ready:
            return False
        backend = _action_backend()
        if backend is None:
            return False

    import wx

    from quill.core.ai.transcript_actions import recommend_actions
    from quill.ui.dialog_contract import apply_modal_ids

    actions = recommend_actions(transcript)
    labels = build_action_labels(actions)
    dlg = wx.SingleChoiceDialog(
        controller.frame,
        f"Your transcript of {file_name} is ready.\n\nWhat would you like me to make of it?",
        "What would you like me to make of this?",
        labels,
    )
    try:
        apply_modal_ids(dlg)
    except Exception:  # noqa: BLE001 - hardening is best-effort on a native dialog
        pass
    try:
        if dlg.ShowModal() != wx.ID_OK:
            return False
        index = dlg.GetSelection()
    finally:
        dlg.Destroy()

    if index < 0 or index >= len(actions):
        return False  # "Just keep the transcript"
    _run_action(controller, actions[index], transcript, file_name, backend)
    return True


def run_transcript_actions_on_document(controller: Any) -> None:
    """Offer Transcript Actions for the current selection or document (anytime).

    Makes the post-transcription magic reachable from the menu: paste any transcript
    or notes, then turn them into minutes / action items / a clean draft. Gives a
    gentle hint when there is nothing to work on or AI is off.
    """
    editor = getattr(controller, "editor", None)
    text = ""
    if editor is not None:
        text = str(editor.GetStringSelection()) or str(editor.GetValue())
    if not text.strip():
        controller._set_status("Open or select a transcript first, then try again.")
        return
    if offer_transcript_actions(controller, text, "the current document"):
        return
    from quill.core.ai.model_manager import load_ai_enabled

    # offer_transcript_actions returned False: either the user opted out, or AI is
    # off / not reachable. Always say why, so the action never just silently
    # returns to the document (especially for a screen-reader user).
    if not load_ai_enabled():
        controller._set_status("Turn on AI (in the AI menu) to use Transcript Actions.")
    else:
        controller._set_status(
            "Transcript Actions need a working AI connection. Open the AI Hub to "
            "check your provider, or run AI > Set Up AI."
        )


def _run_action(
    controller: Any,
    action: TranscriptAction,
    transcript: str,
    file_name: str,
    backend: Any,
) -> None:
    """Generate the action's document on a worker thread, then open it in a new buffer."""
    import wx

    from quill.ui.ai_transcribe_dialog import AIProgressDialog

    progress = AIProgressDialog(
        controller.frame,
        action.name,
        f"Creating {action.name} from {file_name}...",
    )
    progress.show()
    controller._announce(f"Creating {action.name}...")

    def worker() -> None:
        text, error = generate_action_text(action, transcript, backend)
        wx.CallAfter(_finish, controller, action, file_name, text, error, progress)

    threading.Thread(  # GATE-40-OK: transcript-action generation worker.
        target=worker, daemon=True
    ).start()


def _finish(
    controller: Any,
    action: TranscriptAction,
    file_name: str,
    text: str | None,
    error: str | None,
    progress: Any,
) -> None:
    progress.close()
    if error is not None or not (text and text.strip()):
        controller._set_status(
            f"Could not create {action.name}: {error}"
            if error
            else f"{action.name} produced no output."
        )
        return
    controller._power_tools_open_text_in_new_buffer(text, f"Created {action.name} from {file_name}")
