from __future__ import annotations

import ctypes
import logging
import sys
from ctypes import wintypes
from dataclasses import dataclass

from quill.platform.credential_validation import validate_credential_identifier

_IS_WINDOWS = sys.platform == "win32"
_CRED_TYPE_GENERIC = 1
_CRED_PERSIST_LOCAL_MACHINE = 2

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class StoredCredential:
    target_name: str
    user_name: str
    secret: str


if _IS_WINDOWS:
    _LPBYTE = ctypes.POINTER(ctypes.c_ubyte)

    class _FILETIME(ctypes.Structure):
        _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]

    class _CREDENTIALW(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD),
            ("Type", wintypes.DWORD),
            ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR),
            ("LastWritten", _FILETIME),
            ("CredentialBlobSize", wintypes.DWORD),
            ("CredentialBlob", _LPBYTE),
            ("Persist", wintypes.DWORD),
            ("AttributeCount", wintypes.DWORD),
            ("Attributes", ctypes.c_void_p),
            ("TargetAlias", wintypes.LPWSTR),
            ("UserName", wintypes.LPWSTR),
        ]

    _PCREDENTIALW = ctypes.POINTER(_CREDENTIALW)
    # use_last_error=True so ctypes.get_last_error() returns the error captured
    # immediately after the call rather than a possibly-stale GetLastError value.
    _advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    _cred_free = _advapi32.CredFree
    _cred_free.argtypes = [ctypes.c_void_p]
    _cred_free.restype = None

    _cred_write = _advapi32.CredWriteW
    _cred_write.argtypes = [_PCREDENTIALW, wintypes.DWORD]
    _cred_write.restype = wintypes.BOOL

    _cred_read = _advapi32.CredReadW
    _cred_read.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(_PCREDENTIALW),
    ]
    _cred_read.restype = wintypes.BOOL

    _cred_delete = _advapi32.CredDeleteW
    _cred_delete.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
    _cred_delete.restype = wintypes.BOOL


def credential_manager_available() -> bool:
    return _IS_WINDOWS


def load_generic_credential(target_name: str) -> StoredCredential | None:
    """Read a generic credential from the Windows Credential Manager.

    Two distinct "no usable secret" outcomes are deliberately kept apart
    (CQ-22):

    - **Absent credential** — no entry exists for ``target_name``. Returns
      ``None`` so the caller can fall back to prompting or another store.
    - **Empty secret** — an entry exists but its credential blob is empty
      (size 0). Returns a ``StoredCredential`` whose ``secret`` is ``""`` so the
      caller can tell "stored, but blank" apart from "never stored". Both cases
      are logged at debug level for diagnostics.
    """

    _require_windows()
    validate_credential_identifier(target_name, field="target_name")
    credential_ptr = _PCREDENTIALW()
    ok = _cred_read(target_name, _CRED_TYPE_GENERIC, 0, ctypes.byref(credential_ptr))
    if not ok:
        logger.debug("No credential found for target_name=%r (absent)", target_name)
        return None
    try:
        credential = credential_ptr.contents
        blob_size = int(credential.CredentialBlobSize)
        if blob_size <= 0:
            logger.debug("Credential for target_name=%r has an empty secret blob", target_name)
            return StoredCredential(
                target_name=target_name,
                user_name=str(credential.UserName or ""),
                secret="",
            )
        blob = ctypes.string_at(credential.CredentialBlob, blob_size)
        return StoredCredential(
            target_name=str(credential.TargetName or target_name),
            user_name=str(credential.UserName or ""),
            secret=_decode_credential_blob(blob),
        )
    finally:
        _cred_free(credential_ptr)


def _decode_credential_blob(blob: bytes) -> str:
    """Decode a credential blob without ever letting the raw secret escape.

    A strict ``blob.decode("utf-8")`` raises ``UnicodeDecodeError`` on a
    UTF-16LE blob (what Windows tools commonly write), and that exception's
    ``.object`` attribute carries the raw secret bytes up the stack into logs
    and crash bundles. Try UTF-8, then UTF-16LE, and finally fall back to a
    lossy UTF-8 decode -- none of which raise, so the secret never rides an
    exception.
    """
    for encoding in ("utf-8", "utf-16-le"):
        try:
            return blob.decode(encoding)
        except UnicodeDecodeError:
            continue
    return blob.decode("utf-8", errors="replace")


def save_generic_credential(
    target_name: str,
    secret: str,
    *,
    user_name: str = "quill-user",
) -> None:
    _require_windows()
    validate_credential_identifier(target_name, field="target_name")
    encoded = secret.encode("utf-8")
    blob = ctypes.create_string_buffer(encoded)
    credential = _CREDENTIALW()
    credential.Flags = 0
    credential.Type = _CRED_TYPE_GENERIC
    credential.TargetName = target_name
    credential.Comment = "QUILL secure secret"
    credential.CredentialBlobSize = len(encoded)
    credential.CredentialBlob = ctypes.cast(blob, _LPBYTE)
    credential.Persist = _CRED_PERSIST_LOCAL_MACHINE
    credential.AttributeCount = 0
    credential.Attributes = None
    credential.TargetAlias = None
    credential.UserName = user_name
    ok = _cred_write(ctypes.byref(credential), 0)
    if not ok:
        raise OSError(ctypes.get_last_error(), "CredWriteW failed")


def delete_generic_credential(target_name: str) -> bool:
    _require_windows()
    validate_credential_identifier(target_name, field="target_name")
    ok = _cred_delete(target_name, _CRED_TYPE_GENERIC, 0)
    return bool(ok)


def _require_windows() -> None:
    if not _IS_WINDOWS:
        raise RuntimeError("Windows Credential Manager is unavailable on this platform.")
