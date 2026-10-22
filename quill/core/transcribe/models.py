"""Which speech model QUILL Transcribe uses: the one you chose, or nothing.

The rule (spec section 7.5) is that the model is **sticky**. The shared engine
code gives way to the built-in model when a downloaded one is missing or will
not load, and says so; that is right in an editor, where you can see what came
out, and wrong in a program whose promise is "the model you chose". So
Transcribe asks first (:func:`start_problem`) and refuses to open the
microphone when the chosen model cannot run, naming it and the way out. Using
the built-in model instead is a separate thing the person does on purpose
(:data:`FALLBACK_ENGINE`), for one session, and it is said out loud.

The list (:func:`model_rows`) is every model QUILL knows, each marked: on this
computer or sent over the internet, which languages, whether it is here yet,
how big it is, and whose it is. A model that is not downloaded is listed so the
person knows it exists, and is not choosable as if it were ready. OpenAI is
listed only where an OpenAI key is saved, and never chosen by itself.

wx-free; reads only names, sizes and whether files exist.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from quill.core.windows_dictation.engines import (
    CLOUD_ENGINE,
    DEFAULT_ENGINE,
    ENGINES,
    OPENAI_ENGINE,
    coerce_engine,
    engine_info,
    language_model_problem,
    model_dir,
)
from quill.core.windows_dictation.model_catalog import CATALOGUE, downloadable
from quill.core.windows_dictation.model_types import megabytes

__all__ = [
    "FALLBACK_ENGINE",
    "ModelRow",
    "model_name",
    "model_rows",
    "start_problem",
]

#: The built-in model the person may choose to use for one session when theirs
#: cannot run. Never switched to without being asked.
FALLBACK_ENGINE = DEFAULT_ENGINE

#: Engines that are not Transcribe's to run: Windows voice typing is Windows'
#: own feature on Windows+H, not a recogniser this app can drive.
_NOT_HERE = frozenset({"voice_typing"})


@dataclass(frozen=True, slots=True)
class ModelRow:
    """One model, as Choose Model lists it."""

    id: str
    name: str
    #: ``True`` when the speech never leaves this computer.
    local: bool
    languages: str
    #: Ready to use now (built in, downloaded, or a saved OpenAI key).
    ready: bool
    size: str
    source: str
    licence: str
    #: One line on what it is good for.
    note: str
    #: Lightweight, Balanced or High accuracy (D-22); ``""`` for an engine that
    #: is not a model (Windows speech recognition, OpenAI).
    tier: str = ""

    @property
    def label(self) -> str:
        """The row as a list says it."""
        where = "on this computer" if self.local else "sends your speech over the internet"
        tier = f"; {self.tier}" if self.tier else ""
        state = "" if self.ready else "; not downloaded"
        return f"{self.name} ({where}{tier}; {self.languages}{state})"


def _openai_ready() -> bool:
    from quill.core.windows_dictation.openai_models import cloud_problem

    try:
        return not cloud_problem()
    except Exception:  # noqa: BLE001 - no key store is no key
        return False


def _note(model: Any) -> str:
    """The model's line, and for one being retired the measured reason too:
    Choose Model's details show this line and not the description."""
    from quill.core.windows_dictation.retiring import RETIRING

    entry = RETIRING.get(model.id)
    if entry is None:
        return str(model.good_for)
    return f"{model.good_for} In our tests with real recordings, {entry.evidence}"


def model_rows() -> list[ModelRow]:
    """Every model Transcribe can use, built in first, then downloads, then OpenAI."""
    from quill.core.windows_dictation.model_advice import engine_tier
    from quill.core.windows_dictation.model_store import installed

    rows: list[ModelRow] = []
    for engine in ENGINES:
        if engine.id in _NOT_HERE:
            continue
        built_in = bool(engine.folder)
        rows.append(
            ModelRow(
                id=engine.id,
                name=engine.label.split(" (")[0],
                local=True,
                languages="English and Spanish" if built_in else "the languages Windows has",
                ready=not built_in or model_dir(engine.id) is not None,
                size="included" if built_in else "part of Windows",
                source="included with QUILL" if built_in else "Microsoft Windows",
                licence="MIT" if built_in else "Windows",
                note=engine.description,
                tier=engine_tier(engine.id),
            )
        )
    for model in CATALOGUE:
        rows.append(
            ModelRow(
                id=model.id,
                name=model.name,
                local=True,
                languages=model.language_names,
                ready=installed(model),
                size=megabytes(model.download_bytes),
                source=model.source,
                licence=model.licence,
                note=_note(model),
                tier=model.tier,
            )
        )
    if _openai_ready():
        rows.append(
            ModelRow(
                id=CLOUD_ENGINE,
                name="OpenAI",
                local=False,
                languages="many languages",
                ready=True,
                size="nothing to download",
                source="OpenAI, with your own key",
                licence="OpenAI's terms",
                note=OPENAI_ENGINE.description,
            )
        )
    return rows


def model_name(engine_id: str) -> str:
    """The plain name of *engine_id*, as the window and the tray say it."""
    engine_id = coerce_engine(engine_id)
    model = downloadable(engine_id)
    if model is not None:
        return model.name
    if engine_id == CLOUD_ENGINE:
        return "OpenAI"
    return engine_info(engine_id).label.split(" (")[0]


def start_problem(
    engine_id: str,
    language: str,
    *,
    openai_consent: bool,
    cloud_fields: Mapping[str, Any] | None = None,
    cloud_consent: Mapping[str, Any] | None = None,
) -> str:
    """Why dictation with *engine_id* cannot start, as a sentence, or ``""``.

    Asked before the microphone opens, so a missing model is a refusal that
    names it rather than a quiet switch to another one. A cloud provider with
    the person's own account (D-31) is checked for its fields and its consent
    with *cloud_fields* and *cloud_consent*.
    """
    if engine_id in _NOT_HERE:
        return (
            "Windows voice typing is Windows' own feature: press Windows+H for it. "
            "Choose another model for QUILL Transcribe."
        )
    engine_id = coerce_engine(engine_id)
    if engine_id.startswith("cloud-"):
        return _cloud_problem(engine_id, cloud_fields or {}, cloud_consent or {})
    name = model_name(engine_id)
    model = downloadable(engine_id)
    if model is not None:
        from quill.core.windows_dictation.model_store import installed

        if not installed(model):
            return (
                f"{name} is not on this computer yet. Download it in the Model "
                "Library, choose another model, or use the built-in model this time."
            )
        if language not in model.languages:
            return f"{name} does not know that language. Choose another model or language."
        return ""
    if engine_id == CLOUD_ENGINE:
        from quill.core.windows_dictation.openai_models import cloud_problem

        return cloud_problem(consent=openai_consent)
    if engine_info(engine_id).folder and model_dir(engine_id, language) is None:
        return (
            f"{name}'s speech model is missing from this copy. Reinstalling QUILL "
            "Transcribe puts it back."
        )
    return language_model_problem(engine_id, language)


def _cloud_problem(engine_id: str, fields: Mapping[str, Any], consent: Mapping[str, Any]) -> str:
    from quill.core.windows_dictation.cloud.consent import start_problem as cloud_start
    from quill.core.windows_dictation.cloud.credentials import values_for
    from quill.core.windows_dictation.cloud.registry import provider_for_engine

    provider = provider_for_engine(engine_id)
    if provider is None:
        return "That speech provider is not part of this copy of QUILL Transcribe."
    plain = fields.get(provider.id, {})
    return cloud_start(
        provider, values_for(provider, plain if isinstance(plain, Mapping) else {}), consent
    )
