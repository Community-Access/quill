"""Speak through the running screen reader, and only the screen reader.

There is deliberately no self-voicing fallback: no SAPI, no accessible_output2
Auto. If neither NVDA nor JAWS is running, messages go to the status bar and
nowhere else.

NVDA: the controller client DLL bundled in quilllite/lib (from NVDA's own
distribution, also shipped with accessible_output2).
JAWS: the FreedomSci.JawsApi COM object, SayString.
"""

from __future__ import annotations

import ctypes
import os
import sys
import threading

_lock = threading.Lock()
_probed = False
_nvda = None
_jaws = None


def _find_controller_dll():
    """The NVDA controller client DLL: ours first, else accessible_output2's.

    A source checkout without the bundled DLL still reaches NVDA if
    accessible_output2 happens to be installed, which it usually is on a
    screen-reader developer's machine.
    """
    from pathlib import Path  # noqa: PLC0415

    from quilllite.paths import lib_dir  # noqa: PLC0415

    name = "nvdaControllerClient64.dll" if sys.maxsize > 2**32 else "nvdaControllerClient32.dll"
    candidates = [lib_dir() / name]
    try:
        import accessible_output2  # noqa: PLC0415

        candidates.append(Path(accessible_output2.__file__).parent / "lib" / name)
    except Exception:
        pass
    for candidate in candidates:
        try:
            if candidate.exists():
                return candidate
        except OSError:
            continue
    return None


def _probe() -> None:
    global _probed, _nvda, _jaws
    with _lock:
        if _probed:
            return
        _probed = True
        if os.name != "nt":
            return
        try:
            dll = _find_controller_dll()
            if dll is not None:
                lib = ctypes.windll.LoadLibrary(str(dll))
                lib.nvdaController_speakText.argtypes = (ctypes.c_wchar_p,)
                lib.nvdaController_brailleMessage.argtypes = (ctypes.c_wchar_p,)
                if lib.nvdaController_testIfRunning() == 0:
                    _nvda = lib
        except Exception:
            _nvda = None
        if _nvda is not None:
            return
        try:
            import comtypes.client  # noqa: PLC0415

            _jaws = comtypes.client.CreateObject("FreedomSci.JawsApi")
        except Exception:
            _jaws = None


def reprobe() -> None:
    """Forget the cached backend so a screen reader started later is picked up."""
    global _probed
    with _lock:
        _probed = False


def prewarm() -> None:
    threading.Thread(target=_probe, name="quilllite-speech", daemon=True).start()


def backend_name() -> str:
    _probe()
    if _nvda is not None:
        return "NVDA"
    if _jaws is not None:
        return "JAWS"
    return "none"


def speak(text: str, interrupt: bool = True) -> None:
    """Say ``text`` through NVDA or JAWS. Never raises."""
    text = (text or "").strip()
    if not text:
        return
    _probe()
    if _nvda is not None:
        try:
            if _nvda.nvdaController_testIfRunning() != 0:
                reprobe()
            else:
                if interrupt:
                    _nvda.nvdaController_cancelSpeech()
                _nvda.nvdaController_speakText(text)
                return
        except Exception:
            pass
    if _jaws is not None:
        try:
            _jaws.SayString(text, interrupt)
            return
        except Exception:
            pass
    if os.name != "nt":
        print(f"[speech] {text}")


def braille(text: str) -> None:
    _probe()
    if _nvda is not None:
        try:
            _nvda.nvdaController_brailleMessage(text)
        except Exception:
            pass
