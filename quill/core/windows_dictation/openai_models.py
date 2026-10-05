"""OpenAI dictation, with the person's own key: may it run, and which models.

**Optional, and off until chosen.** Dictation's default is, and stays, an
engine on this computer. This one is offered only where:

* an **OpenAI key is saved** in Use My Own AI Key (the same key, in the same
  store, that QUILL's AI help uses -- :func:`quill.core.ai.own_key.has_own_key`).
  QUILL's free hosted AI never carries audio, so without a key there is no
  OpenAI dictation at all;
* **Safe Mode is off**; and
* the person has **agreed** that their speech goes to OpenAI
  (:data:`CONSENT_TEXT`, asked once when they choose the engine, saved as
  ``windows_dictation_openai_consent``).

**The model list is read from OpenAI, never written here.** ``/v1/models`` is
asked with the person's key when they open More Dictation Settings, and the
list they choose from is every model it returns that transcribes speech
(:func:`is_transcription_model`), newest first, the newest pre-selected when
nothing was chosen before. Two things are decided here and only here:

* **What counts as a transcription model**: an id with ``transcribe`` in it, or
  a Whisper id. Speaker-labelling ("diarize") models are left out: they are for
  meetings, and dictation is one voice.
* **What OpenAI is retiring.** OpenAI's API does not mark a model as
  deprecated, so :data:`RETIRING` copies OpenAI's deprecations page
  (developers.openai.com/api/docs/deprecations, read 2026-10-05): whisper-1,
  gpt-4o-transcribe, gpt-4o-mini-transcribe and gpt-4o-transcribe-diarize shut
  down on 2027-02-26, replaced by gpt-live-transcribe and gpt-transcribe. A
  model retiring is left out of the list even while it still answers, so
  nobody picks something that is about to stop. It is a list of what to leave
  out, never of what to offer: a model OpenAI adds appears with no change here.

**If the chosen model disappears** from the account's list, the settings window
says so once and asks for another; dictation never moves to a different model
on its own (:func:`model_problem`).

**Which path a model takes** (:func:`is_live_model`): OpenAI's speech-to-text
guide (read 2026-10-05) recommends its Realtime transcription for live
microphone audio, with ``gpt-live-transcribe``; the file-transcription endpoint
with ``stream=true`` serves the others. :mod:`openai_transcribe` speaks both.

wx-free. The one network call is :func:`list_transcription_models`.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable, Mapping
from typing import Any

__all__ = [
    "API_ROOT",
    "CONSENT_TEXT",
    "RETIRING",
    "cloud_problem",
    "is_live_model",
    "is_transcription_model",
    "list_transcription_models",
    "load_key",
    "model_problem",
    "newest",
    "transcription_models",
]

API_ROOT = "https://api.openai.com/v1"

#: Read from OpenAI's deprecations page on 2026-10-05. Matched as a prefix, so
#: a dated snapshot of a retiring model ("gpt-4o-mini-transcribe-2025-12-15")
#: goes with it. Check that page when OpenAI announces a shutdown.
RETIRING: tuple[str, ...] = (
    "whisper-1",
    "gpt-4o-transcribe",
    "gpt-4o-mini-transcribe",
    "gpt-4o-transcribe-diarize",
)

#: What the person agrees to before any of their speech leaves the computer.
CONSENT_TEXT = (
    "OpenAI dictation sends what you say to OpenAI.\n\n"
    "While dictation is on with this engine, each phrase you speak is sent over "
    "an encrypted connection to OpenAI with the OpenAI key saved in Use My Own AI "
    "Key, and the words come back. OpenAI bills your account for it. Nothing goes "
    "through QUILL's servers, and QUILL keeps no copy of the audio.\n\n"
    "OpenAI's own policies apply to what it receives: by default OpenAI does not "
    "train on data sent through its API, and may keep it for up to 30 days to "
    "watch for abuse. Read OpenAI's terms at openai.com/policies before you agree.\n\n"
    "The built-in engines never send anything anywhere. You can switch back to one "
    "at any time in Dictation Settings.\n\n"
    "Send your speech to OpenAI when you dictate with this engine?"
)


def load_key() -> str:
    """The person's saved OpenAI key, or ``""``. Never logged, never shown."""
    try:
        from quill.core.assistant_ai import load_provider_api_key

        return str(load_provider_api_key("openai") or "")
    except Exception:  # noqa: BLE001 - an unreadable store is "no key"
        return ""


def cloud_problem(*, consent: bool | None = None) -> str:
    """Why OpenAI dictation cannot run here, as a sentence; ``""`` when it can.

    *consent* is checked only when given (the settings window lists the engine
    before the person has agreed; starting dictation checks it).
    """
    if os.environ.get("QUILL_SAFE_MODE") == "1":
        return "Safe Mode is on, and Safe Mode never sends anything to the internet."
    if not load_key():
        return (
            "OpenAI dictation needs your own OpenAI key. Save one in Use My Own AI "
            "Key, in the AI menu, first."
        )
    if consent is False:
        return (
            "OpenAI dictation is not switched on. Choose it in Dictation Settings, "
            "where it says what is sent, and agree."
        )
    return ""


def is_transcription_model(model_id: str) -> bool:
    """Whether *model_id* turns speech into text for one voice."""
    name = str(model_id).strip().lower()
    if not name or "diarize" in name or "tts" in name:
        return False
    return "transcribe" in name or name.startswith("whisper")


def _retiring(model_id: str) -> bool:
    name = model_id.strip().lower()
    return any(name == old or name.startswith(old + "-") for old in RETIRING)


def transcription_models(entries: Iterable[Mapping[str, Any] | str]) -> list[str]:
    """The ids in a ``/v1/models`` answer that dictation may offer, newest first.

    *entries* are the answer's ``data`` items (``{"id": ..., "created": ...}``)
    or bare ids. Newest is OpenAI's own ``created`` time; ids without one go
    last, by name.
    """
    seen: dict[str, int] = {}
    for entry in entries:
        if isinstance(entry, str):
            model_id, created = entry, -1
        else:
            model_id = str(entry.get("id", "") or "")
            try:
                created = int(entry.get("created", -1) or -1)
            except (TypeError, ValueError):
                created = -1
        model_id = model_id.strip()
        if is_transcription_model(model_id) and not _retiring(model_id):
            seen[model_id] = max(created, seen.get(model_id, -1))
    return sorted(seen, key=lambda name: (-seen[name], name.lower()))


def newest(models: list[str]) -> str:
    """What is pre-selected when nothing was chosen before."""
    return models[0] if models else ""


def model_problem(chosen: str, available: list[str]) -> str:
    """A sentence when *chosen* is no longer offered, else ``""``."""
    if not chosen or chosen in available:
        return ""
    if available:
        return (
            f"The OpenAI model you chose, {chosen}, is no longer offered for your key, "
            "or OpenAI is retiring it. Choose another from the list."
        )
    return f"The OpenAI model you chose, {chosen}, is no longer offered for your key."


def is_live_model(model_id: str) -> bool:
    """Whether *model_id* is a Realtime (live) transcription model."""
    name = model_id.lower()
    return "live" in name or "realtime" in name


def list_transcription_models(key: str, *, timeout: float = 15.0) -> tuple[list[str], str]:
    """``(models, error)`` for *key*: what it may use for dictation. Blocking;
    never raises. The key goes only to OpenAI, in a header, and is never logged."""
    from urllib.error import HTTPError, URLError
    from urllib.request import Request, urlopen

    from quill.core.net import verified_ssl_context

    if not key:
        return [], "No OpenAI key is saved."
    request = Request(
        f"{API_ROOT}/models", headers={"Authorization": f"Bearer {key}"}, method="GET"
    )
    try:
        with urlopen(request, timeout=timeout, context=verified_ssl_context()) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
    except HTTPError as error:
        if error.code == 401:
            return [], "OpenAI did not accept the saved key. Check it in Use My Own AI Key."
        return [], f"OpenAI could not list its models (error {error.code})."
    except (URLError, OSError, TimeoutError):
        return [], "OpenAI could not be reached. Check the internet connection."
    except ValueError:
        return [], "OpenAI's answer could not be read."
    data = payload.get("data", []) if isinstance(payload, dict) else []
    models = transcription_models(item for item in data if isinstance(item, dict))
    if not models:
        return [], "OpenAI listed no speech-to-text models this key can use."
    return models, ""
