from __future__ import annotations

import logging
import queue as _queue
import sys
import threading
import time as _time
from dataclasses import dataclass, replace
from importlib import import_module
from typing import Any

logger = logging.getLogger(__name__)


def _sapi_available() -> bool:
    """True when Windows SAPI 5 speech can be reached (the self-voicing fallback)."""
    try:
        from quill.platform.windows import sapi5

        return sapi5.available()
    except Exception:  # noqa: BLE001
        return False


_VALID_BACKENDS = {"auto", "prism", "status_only"}

_sr_active_cache: bool | None = None
_sr_cache_timestamp: float = 0.0
_SR_CACHE_TTL = 30.0


def _screen_reader_active() -> bool:
    """Cached check for a running screen reader (so 'auto' TTS doesn't double-talk).

    Re-probes after _SR_CACHE_TTL seconds so that starting a screen reader while
    QUILL is running stops self-voicing within the next announcement cycle.
    """
    global _sr_active_cache, _sr_cache_timestamp
    now = _time.monotonic()
    if _sr_active_cache is None or (now - _sr_cache_timestamp) > _SR_CACHE_TTL:
        try:
            from quill.platform.windows.sr_detect import detect_screen_reader

            _sr_active_cache = bool(detect_screen_reader().detected)
        except Exception:  # noqa: BLE001
            _sr_active_cache = False
        _sr_cache_timestamp = now
    return _sr_active_cache


def normalize_backend_name(value: str | None) -> str:
    raw = (value or "").strip().lower()
    if raw in _VALID_BACKENDS:
        return raw
    return "auto"


# SAPI/COM voice construction is expensive on the first call (hundreds of ms
# for voice enumeration), so the self-voicing engine is a process-wide singleton
# built once on the TTS worker thread and reused for every announcement. A SAPI
# SpVoice is an apartment-threaded COM object: it must be created and spoken to
# on the same thread, which is why it lives on the worker thread instead of
# being shared across callers.
_tts_voice: Any | None = None
_tts_engine_failed: bool = False

# TTS-FALLBACK-ANNOUNCE: callers can check this after startup.
# True means SAPI 5 could not be initialised and the screen-reader fallback is active.
_tts_init_failed: bool = False


def tts_init_failed() -> bool:
    """Return True when SAPI 5 failed to initialise for self-voicing.

    The UI uses this to show a one-shot status-bar prompt:
    "Screen reader fallback active. Press F8 to retry TTS."
    """
    return _tts_init_failed


def _build_tts_voice() -> Any | None:
    """Create the SAPI ``SpVoice`` on the calling (worker) thread, or None.

    A failure flips self-voicing off until :func:`retry_tts_init` clears it.
    """
    global _tts_engine_failed, _tts_init_failed
    if _tts_engine_failed:
        return None
    try:
        from quill.platform.windows import sapi5

        if not sapi5.available():
            raise RuntimeError("SAPI 5 is not available")
        return sapi5.create_voice()
    except Exception:  # noqa: BLE001 - any failure flips us off until retried
        _tts_engine_failed = True
        _tts_init_failed = True
        return None


def retry_tts_init() -> bool:
    """Clear the failure flag so the worker rebuilds the SAPI voice on next use.

    Returns True when SAPI 5 looks usable again. Called from the UI when the user
    presses the F8 retry shortcut shown by the TTS-FALLBACK-ANNOUNCE prompt.
    """
    global _tts_voice, _tts_engine_failed, _tts_init_failed
    _tts_voice = None
    _tts_engine_failed = False
    _tts_init_failed = False
    if not _sapi_available():
        _tts_init_failed = True
        return False
    _ensure_tts_worker()
    return True


def reset_tts_engine_for_tests() -> None:
    """Discard the cached voice and SR cache. Test-only helper."""
    global _tts_voice, _tts_engine_failed, _tts_init_failed
    global _sr_active_cache, _sr_cache_timestamp
    _tts_voice = None
    _tts_engine_failed = False
    _tts_init_failed = False
    _sr_active_cache = None
    _sr_cache_timestamp = 0.0


def flush_tts_for_tests(timeout: float = 2.0) -> None:
    """Block until the TTS worker has processed all queued messages. Test-only."""
    _tts_queue.join()


# ------------------------------------------------------------------
# Non-blocking TTS worker (fix #52: speech must not block the UI thread)
# ------------------------------------------------------------------

_tts_queue: _queue.Queue[str | None] = _queue.Queue()
_tts_worker_started = False
_tts_worker_lock = threading.Lock()


def _ensure_tts_worker() -> None:
    global _tts_worker_started
    with _tts_worker_lock:
        if _tts_worker_started:
            return
        _tts_worker_started = True
        t = threading.Thread(target=_tts_worker_loop, daemon=True, name="quill-tts-worker")
        t.start()


def prewarm_tts_engine() -> None:
    """Start the TTS worker thread now so SAPI init cost is paid ahead of time.

    SAPI/COM voice construction is the expensive part of the first announcement
    of the session (hundreds of ms). Doing it at startup keeps that cost out of
    the quill_key_timeout window where it could otherwise expire the key prefix
    before the user's next keystroke arrived. The SpVoice is an apartment COM
    object, so it is built on the worker thread that later speaks with it.
    """
    if not _sapi_available():
        return
    _ensure_tts_worker()


def _tts_worker_loop() -> None:
    global _tts_voice
    _tts_voice = _build_tts_voice()
    while True:
        msg = _tts_queue.get()
        if msg is None:
            _tts_queue.task_done()
            break
        if _tts_voice is None:
            _tts_voice = _build_tts_voice()
        voice = _tts_voice
        if voice is not None:
            try:
                # Synchronous Speak on this dedicated worker thread; the queue
                # already keeps announcements off the UI thread.
                voice.Speak(msg, 0)
            except Exception:  # noqa: BLE001
                pass
        _tts_queue.task_done()


@dataclass(frozen=True, slots=True)
class AnnouncementBackendState:
    requested_backend: str
    active_backend: str
    prism_available: bool
    prism_runtime_ready: bool
    backend_name: str
    last_error: str = ""


class AnnouncementEngine:
    def __init__(self, requested_backend: str = "auto") -> None:
        self._runtime_backend: Any | None = None
        # Hold the Prism Context for as long as we hold its backend: the backend
        # borrows from the context and dangles (segfault on speak) if it is GC'd.
        self._prism_context: Any | None = None
        # accessible_output2 Auto speaker, used as the fallback when Prism cannot
        # acquire a live screen-reader backend (more reliable per-reader detection)
        # before we resort to the SAPI self-voice (#700).
        self._ao2_speaker: Any | None = None
        self._state = AnnouncementBackendState(
            requested_backend="auto",
            active_backend="status_only",
            prism_available=False,
            prism_runtime_ready=False,
            backend_name="Status Bar",
            last_error="",
        )
        self.configure(requested_backend)

    def configure(self, requested_backend: str) -> AnnouncementBackendState:
        requested = normalize_backend_name(requested_backend)
        backend, context, probe = _probe_prism_backend()
        prism_available = probe != "missing"
        prism_runtime_ready = backend is not None
        active_backend = "status_only"
        backend_name = "Status Bar"
        last_error = ""
        ao2_speaker: Any | None = None

        if requested in {"prism", "auto"}:
            if backend is not None:
                active_backend = "prism"
                backend_name = _backend_name(backend)
            else:
                # Prism could not acquire a live screen-reader backend. Try the
                # accessible_output2 bridge (per-reader is_active() detection is
                # more reliable) before giving up to the SAPI self-voice (#700).
                ao2_speaker, ao2_name = _ao2_live_screen_reader()
                if ao2_speaker is not None:
                    active_backend = "accessible_output2"
                    backend_name = ao2_name or "Screen reader"
                elif requested == "prism":
                    last_error = _probe_to_message(probe)
                elif probe not in {"missing", "runtime_unavailable"}:
                    last_error = _probe_to_message(probe)

        self._runtime_backend = backend if active_backend == "prism" else None
        # Keep the context only while we hold its backend; release it otherwise so
        # a discarded Prism runtime can be collected.
        self._prism_context = context if active_backend == "prism" else None
        self._ao2_speaker = ao2_speaker if active_backend == "accessible_output2" else None
        self._state = AnnouncementBackendState(
            requested_backend=requested,
            active_backend=active_backend,
            prism_available=prism_available,
            prism_runtime_ready=prism_runtime_ready,
            backend_name=backend_name,
            last_error=last_error,
        )
        return self._state

    def state(self) -> AnnouncementBackendState:
        return self._state

    def announce(self, message: str, *, force_speech: bool = False) -> str | None:
        if self._runtime_backend is None and self._ao2_speaker is not None:
            # accessible_output2 fallback: route to the live screen reader. Like
            # the Prism path, force_speech interrupts so internal-state narration
            # (Tab-indent, QUILL-key chord) is actually voiced; routine status
            # does not interrupt the reader's current utterance.
            try:
                self._ao2_speaker.speak(message, interrupt=force_speech)
                return None
            except Exception as exc:  # noqa: BLE001
                error = f"accessible_output2 announcement failed: {exc}"
                self._state = replace(self._state, last_error=error)
                return error
        if self._runtime_backend is None:
            # macOS: hand the announcement to VoiceOver via the accessibility
            # API. Never self-voice with SAPI — that talks over VoiceOver
            # (the system voice the user already hears). If VoiceOver is off the
            # post is a harmless no-op.
            if sys.platform == "darwin":
                try:
                    from quill.platform.macos.announce import announce as voiceover_announce

                    voiceover_announce(message)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("macOS VoiceOver announce failed: %s", exc)
                return None
            # Windows/Linux: only speak via system TTS when NO screen reader is
            # running — otherwise it talks over Narrator/NVDA/JAWS (the screen
            # reader already reads the UI through the accessibility API).
            # force_speech bypasses that suppression for callers narrating
            # internal-only state (e.g. the QUILL key chord prefix) that has
            # no focus or control change for the screen reader to pick up on
            # its own, so without this the message is silently dropped.
            if (
                self._state.requested_backend in {"auto", "prism"}
                and not _tts_engine_failed
                and (force_speech or not _screen_reader_active())
            ):
                # Queue speech to the worker thread without resolving the voice
                # here: building the SAPI SpVoice costs hundreds of ms the first
                # time and the worker builds the singleton itself, so resolving
                # it on the caller (the UI thread) would block for that long on
                # the first announcement of the session.
                _ensure_tts_worker()
                _tts_queue.put_nowait(message)
                self._state = replace(
                    self._state,
                    active_backend="speech",
                    backend_name="System Speech",
                    last_error="",
                )
            return None
        speak = getattr(self._runtime_backend, "speak", None)
        if not callable(speak):
            error = "Active Prism backend does not expose speak()."
            self._state = replace(self._state, last_error=error)
            return error
        # force_speech callers (Tab-indent, QUILL-key chord prefix, ...) narrate
        # internal state the screen reader has no focus/control change to read on
        # its own. Queued behind the reader's current utterance (interrupt=False)
        # they are routinely dropped, which reads to the user as "the indentation
        # announcement is gone". Interrupt so a forced announcement is actually
        # voiced; routine status keeps the polite non-interrupting behaviour.
        try:
            speak(message, interrupt=force_speech)
            return None
        except TypeError:
            speak(message)
            return None
        except Exception as exc:  # noqa: BLE001
            error = f"Prism announcement failed: {exc}"
            self._state = replace(self._state, last_error=error)
            return error

    def diagnostics_environment(self) -> dict[str, object]:
        return {
            "announcement_backend_requested": self._state.requested_backend,
            "announcement_backend_active": self._state.active_backend,
            "announcement_backend_name": self._state.backend_name,
            "announcement_prism_available": self._state.prism_available,
            "announcement_prism_runtime_ready": self._state.prism_runtime_ready,
            "announcement_backend_error": self._state.last_error,
        }


# Prism screen-reader backends in preference order. acquire_best() can return a
# backend for a reader that is NOT actually running (observed: NVDA returned while
# JAWS is the live reader). Its runtime check then fails and QUILL silently drops
# to the SAPI self-voice in a foreign voice. We instead pick the first SR backend
# that reports it is live at runtime, preferring the reader QUILL detected. SAPI /
# OneCore are deliberately excluded here — self-voicing is the separate fallback,
# so we never talk over the screen reader with a different voice. (#700)
_PRISM_SR_BACKEND_NAMES: tuple[str, ...] = (
    "JAWS",
    "NVDA",
    "SYSTEM_ACCESS",
    "WINDOW_EYES",
    "ZDSR",
    "ZOOM_TEXT",
    "SENSE_READER",
    "PC_TALKER",
    "BOY_PC_READER",
    "ORCA",
    "SPEECH_DISPATCHER",
)

# QUILL's screen-reader detector names -> Prism BackendId member names.
_SR_NAME_TO_PRISM_BACKEND: dict[str, str] = {
    "jaws": "JAWS",
    "nvda": "NVDA",
}


def _probe_prism_backend() -> tuple[Any | None, Any | None, str]:
    """Return ``(backend, context, probe)``.

    The ``context`` is returned alongside the backend because a Prism ``Backend``
    borrows from its ``Context``: if the context is garbage-collected the backend
    dangles and ``speak()`` segfaults. The caller must keep the context alive for
    as long as it uses the backend (#700). It was never observed before because
    on machines where acquire_best() picked an inactive reader we always fell back
    to status-only and never spoke through Prism.
    """
    prism_module = _import_prism_module()
    if prism_module is None:
        return None, None, "missing"
    try:
        context = prism_module.Context()
    except Exception:  # noqa: BLE001
        return None, None, "context_error"
    # Prefer the SR backend that is live at runtime (matching the running reader)
    # over acquire_best(), which does not runtime-check its pick (#700).
    runtime_backend = _acquire_live_screen_reader(prism_module, context)
    if runtime_backend is not None:
        return runtime_backend, context, "ok"
    try:
        backend = context.acquire_best()
    except Exception:  # noqa: BLE001
        return None, None, "acquire_error"
    features = getattr(backend, "features", None)
    runtime_flag = getattr(features, "is_supported_at_runtime", True)
    if not runtime_flag:
        return None, None, "runtime_unavailable"
    return backend, context, "ok"


def _acquire_live_screen_reader(prism_module: Any, context: Any) -> Any | None:
    """Return the first screen-reader backend that is live at runtime, or None.

    Tries the screen reader QUILL detected first, then a fixed preference list.
    Returns None on any older/stub Prism that lacks ``acquire``/``BackendId`` so
    the caller falls back to ``acquire_best()`` (keeps fakes and tests working).
    """
    acquire = getattr(context, "acquire", None)
    backend_id_enum = getattr(prism_module, "BackendId", None)
    if not callable(acquire) or backend_id_enum is None:
        return None
    ordered: list[str] = []
    try:
        from quill.platform.windows.sr_detect import detect_screen_reader

        detection = detect_screen_reader()
        if detection.detected:
            mapped = _SR_NAME_TO_PRISM_BACKEND.get(detection.name.strip().lower())
            if mapped:
                ordered.append(mapped)
    except Exception:  # noqa: BLE001 - detection must never break announcement setup
        pass
    for name in _PRISM_SR_BACKEND_NAMES:
        if name not in ordered:
            ordered.append(name)
    for name in ordered:
        member = getattr(backend_id_enum, name, None)
        if member is None:
            continue
        try:
            backend = acquire(member)
        except Exception:  # noqa: BLE001 - try the next candidate
            continue
        features = getattr(backend, "features", None)
        if getattr(features, "is_supported_at_runtime", False):
            return backend
    return None


# accessible_output2 fallback. Its Auto speaker exposes a per-output is_active()
# that reliably reports the *running* screen reader, which is why it is a better
# fallback than Prism's "best" guess when Prism cannot acquire a live backend.
_ao2_auto: Any | None = None
_ao2_load_failed: bool = False


def _ao2_speaker_singleton() -> Any | None:
    """Return a cached accessible_output2 Auto instance, or None if unavailable."""
    global _ao2_auto, _ao2_load_failed
    if _ao2_load_failed:
        return None
    if _ao2_auto is None:
        try:
            from accessible_output2.outputs.auto import Auto

            _ao2_auto = Auto()
        except Exception:  # noqa: BLE001 - optional dependency / load failure
            _ao2_load_failed = True
            return None
    return _ao2_auto


def _ao2_live_screen_reader() -> tuple[Any | None, str | None]:
    """Return ``(speaker, reader_name)`` when a screen reader is live, else (None, None).

    SAPI5 is skipped: accessible_output2 always reports it active and it is our
    own self-voice fallback, not a screen reader — using it here would talk over
    the reader with a foreign voice.
    """
    speaker = _ao2_speaker_singleton()
    if speaker is None:
        return None, None
    try:
        outputs = list(getattr(speaker, "outputs", []))
    except Exception:  # noqa: BLE001
        return None, None
    for output in outputs:
        if type(output).__name__.lower() == "sapi5":
            continue
        try:
            if output.is_active():
                name = getattr(output, "name", "") or type(output).__name__
                return speaker, str(name)
        except Exception:  # noqa: BLE001 - probe the next output
            continue
    return None, None


def _reset_ao2_for_tests() -> None:
    """Discard the cached accessible_output2 speaker. Test-only helper."""
    global _ao2_auto, _ao2_load_failed
    _ao2_auto = None
    _ao2_load_failed = False


def _import_prism_module() -> Any | None:
    for module_name in ("prism", "prismatoid"):
        try:
            return import_module(module_name)
        except Exception:  # noqa: BLE001
            continue
    return None


def _backend_name(backend: Any) -> str:
    raw = getattr(backend, "name", None)
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return "Prism"


def _probe_to_message(probe: str) -> str:
    messages = {
        "missing": "Prism is not installed.",
        "context_error": "Prism failed to initialize context.",
        "acquire_error": "Prism could not acquire a backend.",
        "runtime_unavailable": "Prism backend is not active at runtime.",
    }
    return messages.get(probe, "Unknown Prism backend error.")
