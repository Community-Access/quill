"""Process-wide model-lifecycle service — wires the policy into the running app.

A wx-free singleton holding one :class:`~quill.core.model_lifecycle.ModelLifecycleManager`
built from the user's settings, so the speech, TTS, and LLM model holders can register
their load/unload with a single idle-unload + low-resource policy **without** importing
wx or each other. ``main_frame`` builds it at startup (:func:`configure`) and runs the
idle sweep on a timer; the model holders call :func:`note_loaded` / :func:`touch` /
:func:`note_unloaded` / :func:`reserve` around their own warm/unload.

Every call degrades to a safe no-op when the service is unconfigured (headless tests,
or before startup), so a registration site can never crash. Model holders wrap their
existing unload as a plain callable — the service adapts it to the manager's
``Unloadable`` protocol — so no holder needs to know about the manager type.
"""

from __future__ import annotations

import threading
from collections.abc import Callable

from quill.core.model_lifecycle import ModelLifecycleManager, build_manager

_lock = threading.Lock()
_manager: ModelLifecycleManager | None = None


class _CallableUnloadable:
    """Adapt a ``Callable[[], None]`` into the manager's ``Unloadable`` protocol."""

    __slots__ = ("_unload",)

    def __init__(self, unload: Callable[[], None]) -> None:
        self._unload = unload

    def unload(self) -> None:
        self._unload()


def configure(
    *,
    low_resource_mode: bool,
    idle_unload_minutes: int,
    total_ram_gb: float,
) -> ModelLifecycleManager:
    """Build (or replace) the process-wide manager from the two settings + machine RAM.

    Returns the new manager. Replacing it drops the previous registrations, which is
    correct: the caller re-registers on next load, and nothing is unloaded here.
    """
    global _manager
    with _lock:
        _manager = build_manager(
            low_resource_mode=low_resource_mode,
            idle_unload_minutes=idle_unload_minutes,
            total_ram_gb=total_ram_gb,
        )
        return _manager


def get() -> ModelLifecycleManager | None:
    """The current manager, or ``None`` when unconfigured."""
    return _manager


def reset() -> None:
    """Drop the manager (used by tests and at shutdown)."""
    global _manager
    with _lock:
        _manager = None


def note_loaded(key: str, unload: Callable[[], None]) -> None:
    """Record that ``key`` is now loaded, with the callable that frees it."""
    manager = _manager
    if manager is not None:
        manager.note_loaded(key, _CallableUnloadable(unload))


def touch(key: str) -> None:
    """Mark ``key`` as just-used (resists idle-unload and LRU eviction)."""
    manager = _manager
    if manager is not None:
        manager.touch(key)


def note_unloaded(key: str) -> None:
    """Drop ``key`` from tracking (its model was freed elsewhere)."""
    manager = _manager
    if manager is not None:
        manager.note_unloaded(key)


def reserve(key: str) -> list[str]:
    """Make room to load ``key`` under low-resource mode; return evicted keys."""
    manager = _manager
    return manager.reserve(key) if manager is not None else []


def sweep(**_kwargs: object) -> list[str]:
    """Unload idle models; return their keys. Safe to call on a timer/worker thread.

    Accepts and ignores ``**_kwargs`` so it satisfies the QuillTaskManager calling
    convention: ``submit`` always invokes the task function with
    ``cancellation_token``, ``operation_id``, and ``progress_callback``. Without
    this the idle sweep raised ``TypeError: sweep() got an unexpected keyword
    argument 'cancellation_token'`` on every timer tick, so idle models were never
    unloaded (the Performance "Unload idle models after" setting was inert).
    """
    manager = _manager
    return manager.sweep_idle() if manager is not None else []
