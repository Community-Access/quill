"""Transcript refinement between the engine and the caret (PRD §17 addendum).

The one place dictation's text-cleanup passes compose, in a fixed order:

1. **Custom vocabulary** (:mod:`quill.core.speech.vocabulary`) — the user's own
   words win first, so a filler pass can never eat a token that was actually
   the first half of "Charge B(ee)".
2. **Filler removal** (:mod:`quill.core.speech.fillers`) — off by default,
   language-honest when on.

Both passes are pure and conservative by design; ``normalize_for_insertion``
(spacing around the caret) still runs *after* them in the controller, so
refinement never sees or disturbs document context. Kept as its own module so
the transcription flows (batch file transcription, voice notes) can reuse the
same policy object rather than growing their own variants.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from quill.core.speech.fillers import remove_filler_words
from quill.core.speech.vocabulary import apply_custom_vocabulary


@dataclass(frozen=True, slots=True)
class RefinePolicy:
    """What refinement the user asked for (all off/empty = pass-through)."""

    #: The user's own terms (names, products, jargon), canonical casing.
    custom_vocabulary: tuple[str, ...] = ()
    #: Master toggle for filler removal (default off: PRD §17 conservatism).
    remove_fillers: bool = False
    #: Language evidence for the gated filler tier ("" = unknown, tier inert).
    #: Fed from the user's dictation language setting, or from an engine that
    #: reports a detected language (Parakeet 3).
    language: str = ""
    #: When not None, replaces both built-in filler tiers (explicit override;
    #: an empty tuple disables built-in lists while the toggle stays on).
    custom_filler_words: tuple[str, ...] | None = field(default=None)


def effective_language(detected: str, configured: str) -> str:
    """The language evidence the filler gate should run on (pure).

    An engine that *heard* the audio outranks a setting that guessed — Parakeet 3
    reports its detected language per utterance — but only real evidence counts:
    ``""``, ``"auto"``, and the ``auto``-prefixed pseudo-codes engines emit mean
    "unknown" and fall back to the configured language (which may itself be
    empty, leaving the gated tier honestly inert).
    """
    cleaned = (detected or "").strip().lower()
    if cleaned and cleaned != "auto" and not cleaned.startswith("auto-"):
        return cleaned
    return (configured or "").strip()


def refine_transcript(text: str, policy: RefinePolicy) -> str:
    """Apply the configured passes to a raw transcript (pure)."""
    refined = apply_custom_vocabulary(text, policy.custom_vocabulary)
    refined = remove_filler_words(
        refined,
        language=policy.language,
        custom_filler_words=(
            list(policy.custom_filler_words) if policy.custom_filler_words is not None else None
        ),
        enabled=policy.remove_fillers,
    )
    return refined.strip()
