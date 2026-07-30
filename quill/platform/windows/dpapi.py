from __future__ import annotations

import base64
import ctypes
import sys

_IS_WINDOWS = sys.platform == "win32"

# CryptProtectData/CryptUnprotectData flag: never surface an interactive DPAPI
# UI prompt from a background/headless code path -- fail with an error instead.
_CRYPTPROTECT_UI_FORBIDDEN = 0x1

if _IS_WINDOWS:
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

    # use_last_error=True so ctypes snapshots GetLastError right after the call
    # and ctypes.get_last_error() returns that value rather than a stale one.
    _crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


def _require_windows() -> None:
    if not _IS_WINDOWS:
        raise RuntimeError(
            "Windows DPAPI is unavailable on this platform; store secrets via the "
            "platform keychain instead."
        )


# NOTE: ``entropy`` is a fixed, non-secret value. DPAPI already scopes the blob
# to the current user; a hardcoded entropy adds nothing beyond that user scope.
# It must NOT be changed -- doing so would make every already-stored blob
# undecryptable.
def protect_secret(secret: str, entropy: bytes = b"quill-credential") -> str:
    _require_windows()
    raw = secret.encode("utf-8")
    encrypted = _protect_bytes(raw, entropy)
    return base64.b64encode(encrypted).decode("ascii")


def unprotect_secret(encoded: str, entropy: bytes = b"quill-credential") -> str:
    _require_windows()
    encrypted = base64.b64decode(encoded.encode("ascii"))
    decrypted = _unprotect_bytes(encrypted, entropy)
    return decrypted.decode("utf-8")


def _protect_bytes(data: bytes, entropy: bytes) -> bytes:
    in_blob, in_buffer = _blob_for_bytes(data)
    entropy_blob, entropy_buffer = _blob_for_bytes(entropy)
    out_blob = DATA_BLOB()
    try:
        _ = in_buffer, entropy_buffer
        ok = _crypt32.CryptProtectData(
            ctypes.byref(in_blob),
            None,
            ctypes.byref(entropy_blob),
            None,
            None,
            _CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(out_blob),
        )
        if not ok:
            raise OSError(ctypes.get_last_error(), "CryptProtectData failed")
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        if out_blob.pbData:
            _kernel32.LocalFree(out_blob.pbData)


def _unprotect_bytes(data: bytes, entropy: bytes) -> bytes:
    in_blob, in_buffer = _blob_for_bytes(data)
    entropy_blob, entropy_buffer = _blob_for_bytes(entropy)
    out_blob = DATA_BLOB()
    try:
        _ = in_buffer, entropy_buffer
        ok = _crypt32.CryptUnprotectData(
            ctypes.byref(in_blob),
            None,
            ctypes.byref(entropy_blob),
            None,
            None,
            _CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(out_blob),
        )
        if not ok:
            raise OSError(ctypes.get_last_error(), "CryptUnprotectData failed")
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        if out_blob.pbData:
            _kernel32.LocalFree(out_blob.pbData)


def _blob_for_bytes(payload: bytes) -> tuple[DATA_BLOB, ctypes.Array[ctypes.c_char]]:
    buffer = ctypes.create_string_buffer(payload)
    blob = DATA_BLOB(cbData=len(payload), pbData=ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
    return blob, buffer
