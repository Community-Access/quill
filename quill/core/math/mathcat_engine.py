"""ctypes binding to MathCAT (daisy/MathCATForC) — real math speech.

MathCAT converts MathML into natural-language speech (and Nemeth/UEB
braille, not yet wired here). This binds the prebuilt ``libmathcat_c.dll``
via plain ``ctypes`` against its C-string API — no PyO3, no Rust build
needed at all, since MathCATForC already publishes prebuilt Windows
binaries. Optional: :mod:`quill.core.math.speech` falls back to
:mod:`quill.core.math.navigator`'s template-based reading when this engine
is not installed.

The underlying C API is process-global mutable state (``SetMathML`` sets
"the" current equation for the whole process, not a per-call object), so
every call here is serialized behind a lock rather than being safely
reentrant.

Memory: every MathCAT function that returns a string hands back a pointer
*it* allocated, which must be freed with ``FreeMathCATString`` — but only
using that *exact* pointer. Declaring a function's ``restype`` as
``ctypes.c_char_p`` makes ctypes copy the C string into a new Python
``bytes`` object and discard the original pointer, so freeing "it"
afterwards frees memory Rust's allocator never allocated (a real heap
corruption, confirmed by hand: STATUS_HEAP_CORRUPTION when this module
first got this wrong). Every string-returning function is therefore
declared ``c_void_p`` here; :func:`_read_and_free` casts that same address
to read it, then frees that same address.
"""

from __future__ import annotations

import ctypes
import os
import threading
from pathlib import Path

from quill.core.error_codes import CodedError


class MathCatUnavailable(CodedError):
    """Raised when the MathCAT engine pack is not installed."""

    code = "QUILL-MATH-MATHCAT-UNAVAILABLE"


class MathCatError(CodedError):
    """Raised when MathCAT itself reports an error via ``GetError()``."""

    code = "QUILL-MATH-MATHCAT-FAILED"


_lock = threading.Lock()
_dll: ctypes.CDLL | None = None


def pack_dir() -> Path:
    """The folder the MathCAT engine pack (DLL + Rules data) lives in.

    Prefers the Offline Edition's bundled copy under ``{app}/tools/mathcat``
    (present when QUILL_APP_ROOT is set and the pack is staged there), falling
    back to the on-demand download location in the app-data engine-packs root.
    """
    app_root = os.environ.get("QUILL_APP_ROOT", "").strip()
    if app_root:
        bundled = Path(app_root) / "tools" / "mathcat"
        if (bundled / "libmathcat_c.dll").is_file() or (bundled / "Rules").is_dir():
            return bundled
    from quill.core.speech.engine_install import engine_packs_dir

    return engine_packs_dir() / "mathcat"


def is_available() -> bool:
    """Return True when the engine pack (DLL + Rules data) is present on disk."""
    pack = pack_dir()
    return (pack / "libmathcat_c.dll").is_file() and (pack / "Rules").is_dir()


def _read_and_free(dll: ctypes.CDLL, raw_ptr: int | None) -> str:
    """Decode the string at *raw_ptr* and free that exact address.

    ``raw_ptr`` must come from a function declared ``restype = ctypes.c_void_p``
    — never from one declared ``c_char_p``, which would have already copied the
    string and discarded the address that needs freeing.
    """
    if not raw_ptr:
        return ""
    text = ctypes.cast(raw_ptr, ctypes.c_char_p).value or b""
    dll.FreeMathCATString(ctypes.c_void_p(raw_ptr))
    return text.decode("utf-8", "replace")


def _load() -> ctypes.CDLL:
    global _dll
    if _dll is not None:
        return _dll
    pack = pack_dir()
    dll_path = pack / "libmathcat_c.dll"
    rules_path = pack / "Rules"
    if not dll_path.is_file() or not rules_path.is_dir():
        raise MathCatUnavailable("MathCAT engine pack is not installed.")

    dll = ctypes.CDLL(str(dll_path))
    dll.GetError.restype = ctypes.c_void_p
    dll.FreeMathCATString.argtypes = [ctypes.c_void_p]
    dll.SetRulesDir.argtypes = [ctypes.c_char_p]
    dll.SetRulesDir.restype = ctypes.c_void_p
    dll.SetMathML.argtypes = [ctypes.c_char_p]
    dll.SetMathML.restype = ctypes.c_void_p
    dll.GetSpokenText.restype = ctypes.c_void_p
    dll.GetMathCATVersion.restype = ctypes.c_void_p
    dll.SetPreference.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    dll.SetPreference.restype = ctypes.c_void_p

    result = _read_and_free(dll, dll.SetRulesDir(str(rules_path).encode("utf-8")))
    if result != "Ok":
        error = _read_and_free(dll, dll.GetError())
        raise MathCatError(f"SetRulesDir failed: {error}")
    _dll = dll
    return dll


def _check_error(dll: ctypes.CDLL) -> None:
    error = _read_and_free(dll, dll.GetError())
    if error:
        raise MathCatError(error)


def get_version() -> str:
    """Return the loaded MathCAT engine's version string, e.g. ``"0.7.6-beta.5"``."""
    with _lock:
        dll = _load()
        version = _read_and_free(dll, dll.GetMathCATVersion())
        _check_error(dll)
        return version


def mathml_to_speech(mathml: str) -> str:
    """Return MathCAT's natural-language spoken-text rendering of *mathml*.

    Raises :class:`MathCatUnavailable` if the engine pack is not installed,
    or :class:`MathCatError` if MathCAT reports a conversion error.
    """
    with _lock:
        dll = _load()
        set_result = _read_and_free(dll, dll.SetMathML(mathml.encode("utf-8")))
        _check_error(dll)
        if not set_result:
            raise MathCatError("MathCAT rejected the MathML (no result, no error reported).")
        speech = _read_and_free(dll, dll.GetSpokenText())
        _check_error(dll)
        return speech
