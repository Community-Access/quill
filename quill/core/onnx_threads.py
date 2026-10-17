"""How many threads each ONNX runtime in the process may use.

QUILL runs two ONNX runtimes side by side (dict.md, "The two-runtime question,
resolved"): sherpa-onnx carries its own ``onnxruntime.dll`` for every speech
model, and Python ``onnxruntime`` runs Kokoro read-aloud. They coexist as two
copies (``tests/unit/core/test_onnxruntime_coexistence.py`` keeps that true),
and each has its own thread pool. Left alone, Python onnxruntime sizes its pool
to every core, so Kokoro speaking while dictation listens would oversubscribe
a two-core computer and slow the screen reader. So the threads are set
explicitly on both sides:

* **sherpa-onnx**: every recogniser is built with ``num_threads`` (one or two
  in dictation; ``model_loader``, ``local_recognizer``).
* **Python onnxruntime** (Kokoro): :func:`kokoro_threads` cores, at most four,
  and never more than half the computer -- one on a two-core machine.

wx-free.
"""

from __future__ import annotations

import os
from typing import Any

__all__ = ["kokoro_threads", "kokoro_with_threads", "session_options"]


def kokoro_threads(cores: int | None = None) -> int:
    """Half the cores, between one and four."""
    count = cores if cores is not None else (os.cpu_count() or 2)
    return max(1, min(4, count // 2))


def session_options(onnxruntime: Any, threads: int) -> Any:
    """``SessionOptions`` with the intra-op pool set to *threads* and the
    inter-op pool to one (Kokoro's graph has no parallel branches worth a pool)."""
    options = onnxruntime.SessionOptions()
    options.intra_op_num_threads = threads
    options.inter_op_num_threads = 1
    return options


def kokoro_with_threads(kokoro_class: Any, model_path: str, voices_path: str) -> Any:
    """A ``kokoro_onnx.Kokoro`` whose session uses :func:`kokoro_threads`.

    Built through ``Kokoro.from_session`` with the providers kokoro-onnx would
    choose itself; falls back to the plain constructor when this kokoro-onnx
    has no ``from_session``, so read-aloud never breaks over a thread count.
    """
    real = isinstance(kokoro_class, type) and "from_session" in vars(kokoro_class)
    if not real:  # an older kokoro-onnx, or a stand-in
        return kokoro_class(model_path, voices_path)
    from_session = kokoro_class.from_session
    import onnxruntime  # type: ignore[import-not-found,import-untyped]

    try:
        import kokoro_onnx  # type: ignore[import-not-found,import-untyped]

        providers = list(getattr(kokoro_onnx, "resolve_providers")())  # noqa: B009 - patched wheel only
    except Exception:  # noqa: BLE001 - an older wheel: the processor is always there
        providers = ["CPUExecutionProvider"]
    session = onnxruntime.InferenceSession(
        model_path,
        sess_options=session_options(onnxruntime, kokoro_threads()),
        providers=providers,
    )
    return from_session(session, voices_path)
