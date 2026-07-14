"""Mid-task model speed/cost tiers (AI-22).

A writer can keep a *fast* (typically smaller, on-device) model for quick edits
and a *strong* model for a careful rewrite, and switch between them in the
middle of a task. The switch is explicit and announced; nothing changes model
silently. Tier-to-model assignments and the active tier persist under
``<app data>/ai/model-tiers.json``.

This module is UI-framework-agnostic (no ``wx`` imports) and builds on the
existing :mod:`quill.core.ai.model_manager` registry.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from quill.core.ai import model_manager
from quill.core.ai.model_manager import MODELS, ModelSpec
from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

TIER_FAST = "fast"
TIER_STRONG = "strong"
_TIERS = (TIER_FAST, TIER_STRONG)

_TIERS_FILE = "model-tiers.json"

# Sensible defaults: the small model is the fast tier, the larger the strong
# tier. "auto" means "use the RAM recommendation" (see model_manager).
_DEFAULT_ASSIGNMENTS: dict[str, str] = {
    TIER_FAST: "llama-3.2-1b",
    TIER_STRONG: "phi-4-mini",
}
_DEFAULT_ACTIVE = TIER_STRONG

_TIER_LABELS: dict[str, str] = {
    TIER_FAST: "Fast",
    TIER_STRONG: "Strong",
}
_TIER_PURPOSE: dict[str, str] = {
    TIER_FAST: "quick edits",
    TIER_STRONG: "careful rewrites",
}


@dataclass(frozen=True, slots=True)
class ModelTier:
    """A named speed/cost tier and the model assigned to it."""

    tier_id: str
    label: str
    purpose: str
    model_id: str

    @property
    def is_auto(self) -> bool:
        return self.model_id == "auto"


def _tiers_path() -> Path:
    return app_data_dir() / "ai" / _TIERS_FILE


def _load_raw() -> dict[str, str]:
    assignments = dict(_DEFAULT_ASSIGNMENTS)
    active = _DEFAULT_ACTIVE
    raw = read_json(_tiers_path(), default={})
    if isinstance(raw, dict):
        stored = raw.get("assignments")
        if isinstance(stored, dict):
            for tier_id in _TIERS:
                candidate = stored.get(tier_id)
                if isinstance(candidate, str) and (candidate == "auto" or candidate in MODELS):
                    assignments[tier_id] = candidate
        stored_active = raw.get("active")
        if isinstance(stored_active, str) and stored_active in _TIERS:
            active = stored_active
    return {"active": active, **{f"assign:{k}": v for k, v in assignments.items()}}


def _write_raw(active: str, assignments: dict[str, str]) -> None:
    write_json_atomic(
        _tiers_path(),
        {"schema_version": 1, "active": active, "assignments": assignments},
    )


def _tier(tier_id: str, model_id: str) -> ModelTier:
    return ModelTier(
        tier_id=tier_id,
        label=_TIER_LABELS[tier_id],
        purpose=_TIER_PURPOSE[tier_id],
        model_id=model_id,
    )


def load_tiers() -> tuple[ModelTier, ...]:
    """Return the configured tiers (fast first, then strong)."""

    state = _load_raw()
    return tuple(_tier(tier_id, state[f"assign:{tier_id}"]) for tier_id in _TIERS)


def active_tier_id() -> str:
    """The id of the tier currently in use."""

    return str(_load_raw()["active"])


def active_tier() -> ModelTier:
    """The tier currently in use, resolved to its assigned model."""

    active = active_tier_id()
    return next(tier for tier in load_tiers() if tier.tier_id == active)


def set_active_tier(tier_id: str) -> ModelTier:
    """Switch the active tier (mid-task) and persist the choice."""

    if tier_id not in _TIERS:
        raise ValueError(f"Unknown tier: {tier_id!r}")
    state = _load_raw()
    assignments = {key: state[f"assign:{key}"] for key in _TIERS}
    _write_raw(tier_id, assignments)
    return next(tier for tier in load_tiers() if tier.tier_id == tier_id)


def assign_model_to_tier(tier_id: str, model_id: str) -> ModelTier:
    """Choose which model backs a tier (model id, or ``"auto"``)."""

    if tier_id not in _TIERS:
        raise ValueError(f"Unknown tier: {tier_id!r}")
    if model_id != "auto" and model_id not in MODELS:
        raise ValueError(f"Unknown model id: {model_id!r}")
    state = _load_raw()
    assignments = {key: state[f"assign:{key}"] for key in _TIERS}
    assignments[tier_id] = model_id
    _write_raw(str(state["active"]), assignments)
    return _tier(tier_id, model_id)


def resolve_tier_spec(tier: ModelTier | None = None) -> ModelSpec:
    """Resolve a tier (default: active) to a concrete model spec."""

    target = tier or active_tier()
    return model_manager.resolve_spec(target.model_id)


def describe_tier(tier: ModelTier) -> str:
    """A spoken description of a tier and its model."""

    spec = resolve_tier_spec(tier)
    return f"{tier.label} tier for {tier.purpose}: {spec.name}."


def announce_tier_change(previous: ModelTier, current: ModelTier) -> str:
    """An A11Y-1-style announcement for a mid-task tier switch."""

    if previous.tier_id == current.tier_id:
        spec = resolve_tier_spec(current)
        return f"Staying on the {current.label} tier ({spec.name})."
    spec = resolve_tier_spec(current)
    return f"Switched to the {current.label} tier ({spec.name}) for {current.purpose}."


def switch_active_tier(tier_id: str) -> str:
    """Switch the active tier mid-task and return the spoken announcement.

    Thin orchestration used by the AI model panel: it reads the tier in use,
    persists the new active tier, and produces the A11Y-1 announcement for the
    change so the UI only has to speak the returned string.
    """

    previous = active_tier()
    set_active_tier(tier_id)
    return announce_tier_change(previous, active_tier())
