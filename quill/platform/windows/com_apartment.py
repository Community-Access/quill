"""Enter the multithreaded COM apartment before opening a sound stream (MX-188).

A WASAPI stream opened on a worker thread that never initialised COM fails
with an error that names something else entirely: TG Drop Deck measured
"GetNameFromCategory ... [Windows WDM-KS error]" three times out of three
with a wx dialog up, and the same call working once the worker had a
multithreaded apartment. So every thread Studio uses to open a PortAudio or
WASAPI stream enters the MTA first through :func:`mta`.

The other half of the rule is just as important: a thread **never
uninitialises an apartment it did not open**. ``CoInitializeEx`` answers
``S_OK`` or ``S_FALSE`` when this call took a reference, which must be given
back, and ``RPC_E_CHANGED_MODE`` when the thread is already single-threaded
(the UI thread, or a pool thread something else initialised), which took no
reference and must not be balanced -- uninitialising there would pull COM
out from under whoever did open it.

Off Windows, or where ``ole32`` cannot be loaded, :func:`mta` does nothing.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

logger = logging.getLogger(__name__)

__all__ = ["COINIT_MULTITHREADED", "import_comtypes", "mta"]

COINIT_MULTITHREADED = 0x0
_S_OK = 0x0
_S_FALSE = 0x1
_RPC_E_CHANGED_MODE = 0x80010106


def _ole32() -> Any:
    """``ole32``, or ``None`` where there is no COM (patched by tests)."""
    try:
        import ctypes

        return ctypes.windll.ole32  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        return None


@contextmanager
def mta() -> Iterator[bool]:
    """Run the block in the multithreaded apartment; yields whether this call joined it.

    ``False`` means the thread was already single-threaded (or there is no
    COM): the block still runs, and nothing is uninitialised afterwards.
    """
    ole32 = _ole32()
    if ole32 is None:
        yield False
        return
    try:
        result = int(ole32.CoInitializeEx(None, COINIT_MULTITHREADED)) & 0xFFFFFFFF
    except OSError as error:
        logger.debug("CoInitializeEx failed: %s", error)
        yield False
        return
    owned = result in (_S_OK, _S_FALSE)
    if result == _RPC_E_CHANGED_MODE:
        logger.info("This thread is already single-threaded; opening the stream there")
    elif not owned:
        logger.debug("CoInitializeEx returned %#010x", result)
    try:
        yield owned
    finally:
        if owned:
            ole32.CoUninitialize()


def import_comtypes() -> Any:
    """Import comtypes without its import turning this MTA thread single-threaded.

    comtypes initialises COM for whichever thread imports it first, as
    single-threaded unless ``sys.coinit_flags`` says otherwise; on a thread
    already in the MTA that raises "Cannot change thread mode". When this is
    the first import, it is told to join the MTA instead.
    """
    if "comtypes" in sys.modules:
        return sys.modules["comtypes"]
    had = hasattr(sys, "coinit_flags")
    previous = getattr(sys, "coinit_flags", None)
    sys.coinit_flags = COINIT_MULTITHREADED  # type: ignore[attr-defined]
    try:
        import comtypes

        return comtypes
    finally:
        if had:
            sys.coinit_flags = previous  # type: ignore[attr-defined]
        else:
            del sys.coinit_flags  # type: ignore[attr-defined]
