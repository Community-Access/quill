"""Machine-aware model upgrade advice (Phase 3 — model/quant selection).

New installs default to the smallest model that fits the machine (the recommenders
in :mod:`quill.core.ai.model_manager` and :mod:`quill.core.speech.service` already
do this). This module answers the *other half* of Phase 3: when a user is running a
smaller model than their machine could comfortably handle, produce a single,
screen-reader-friendly **upgrade suggestion** — never an automatic download.

Kept wx-free and headless-testable: it computes the suggestion; the UI decides when
to surface it (as an accessible, dismissible prompt) and owns the actual download.
The advice is symmetric across engines via :class:`UpgradeSuggestion`, so speech and
LLM surfaces read the same way to a screen-reader user.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UpgradeSuggestion:
    """A one-step, opt-in move from a smaller model to a larger one that now fits."""

    from_id: str
    to_id: str
    to_name: str
    #: Approximate download the upgrade costs, in GB (for the accessible prompt).
    extra_download_gb: float
    #: Plain-language, speakable reason ("Your computer has enough memory for …").
    reason: str

    def message(self) -> str:
        """A complete, screen-reader-friendly one-line prompt."""
        size = f"about {self.extra_download_gb:.1f} GB to download"
        return (
            f"{self.reason} Upgrade to {self.to_name} ({size})? Your current model keeps working."
        )


def suggest_llm_upgrade(
    current_id: str,
    total_ram_gb: float,
    *,
    low_resource_mode: bool = False,
) -> UpgradeSuggestion | None:
    """Suggest a larger local LLM when the machine can handle one, else ``None``.

    Honours the same 8 GB threshold the recommender uses: a machine with 8 GB+ that
    is still on the 1B model is offered the 4-mini upgrade. Returns ``None`` when the
    user is already on the best-fit model, on an unknown model, when RAM is unknown,
    or when **low-resource mode** is on (the user has explicitly asked to stay small,
    so we never nag them upward).
    """
    if low_resource_mode or total_ram_gb <= 0:
        return None
    # Imported lazily so this wx-free module has no import cost when advice isn't needed.
    from quill.core.ai.model_manager import _LOW_RAM_THRESHOLD_GB, MODELS

    # Best-fit for the *given* RAM (mirrors recommended_id()'s threshold, but honours
    # the argument instead of re-detecting the host — so it is testable and correct
    # when advising about a machine profile other than the one running the tests).
    best = "phi-4-mini" if total_ram_gb >= _LOW_RAM_THRESHOLD_GB else "llama-3.2-1b"
    if current_id == best or current_id not in MODELS or best not in MODELS:
        return None
    current = MODELS[current_id]
    target = MODELS[best]
    if target.approx_gb <= current.approx_gb:
        return None  # only ever suggest strictly larger/more-capable
    reason = (
        f"Your computer has {total_ram_gb:.0f} GB of memory — enough for a more "
        f"accurate model (machines with {_LOW_RAM_THRESHOLD_GB:.0f} GB or more)."
    )
    return UpgradeSuggestion(
        from_id=current_id,
        to_id=best,
        to_name=target.name,
        extra_download_gb=max(0.0, target.approx_gb - current.approx_gb),
        reason=reason,
    )
