"""Secret storage on macOS via the login Keychain.

Replaces the Windows DPAPI module (``quill.platform.windows.dpapi``). Rather
than returning portable ciphertext, secrets live in the Keychain and are
referenced by an account label. A DPAPI-shaped ``protect_secret`` /
``unprotect_secret`` facade is provided for the cross-platform secret layer:
``protect_secret`` stores the value and returns an opaque locator token;
``unprotect_secret`` resolves that token back to the secret.

Two backends, tried in order:

1. **PyObjC ``Security`` framework (``SecItemAdd`` / ``SecItemCopyMatching`` /
   ``SecItemDelete``)** -- the primary path. The secret travels as the
   ``kSecValueData`` entry of an in-process CFDictionary, so it never appears
   in any child process's argv. This is the leak-free path a real macOS build
   uses (pyobjc is declared in the ``[macos]`` extra).
2. **The ``security`` CLI** -- a fallback for environments without pyobjc.
   ``security add-generic-password -w <secret>`` is the only way to write a
   generic-password item via the CLI, and ``-w`` takes the secret as an
   *argument*, so the plaintext is visible to any local process via
   ``ps -ww`` for the call's duration. The fallback therefore emits a one-time
   ``RuntimeWarning`` so a pyobjc-less install knows it is on the leaking path
   (see issue #1 / #16 / #43). The read/delete CLI calls do not leak -- ``-w``
   there only selects "print the password to stdout", and the password is not
   an argument -- so no warning is needed for those.
"""

from __future__ import annotations

import subprocess
import uuid
import warnings

from quill.platform.credential_validation import validate_credential_identifier

DEFAULT_SERVICE = "Quill"
_TOKEN_PREFIX = "macos-keychain:"

# macOS Security framework OSStatus values (``Security/SecBase.h``). Defined as
# module-level ints so the pyobjc path does not depend on importing the
# ``errSec*`` enums, which not every pyobjc build re-exports.
_ERR_SEC_SUCCESS = 0
_ERR_SEC_ITEM_NOT_FOUND = -25300
_ERR_SEC_DUPLICATE_ITEM = -25206
_ERR_SEC_PARAM = -50


class KeychainError(RuntimeError):
    pass


class _PyobjcUnavailable(RuntimeError):
    """Internal sentinel: pyobjc's Security framework could not be imported."""


# Resolved lazily by :func:`_security_binding`. ``None`` means "not probed yet";
# the string ``"unavailable"`` means "probed and missing"; a ``(Security,
# kCFBooleanTrue)`` tuple means "probed and present".
_SECURITY_BINDING: object = None
_CLI_LEAK_WARNED = False


def _security_binding() -> tuple[object, object]:
    """Return ``(Security module, kCFBooleanTrue)`` or ``(None, None)``.

    Probes once and caches the result so repeated secret reads/writes don't
    retry the import. pyobjc (the ``[macos]`` extra) bundles the
    ``Security`` and ``CoreFoundation`` framework bindings; if either is
    absent we fall back to the ``security`` CLI.
    """
    global _SECURITY_BINDING
    if _SECURITY_BINDING is None:
        try:
            import Security  # type: ignore[import-not-found]
            from CoreFoundation import kCFBooleanTrue  # type: ignore[import-not-found]
        except ImportError:
            _SECURITY_BINDING = "unavailable"
        else:
            _SECURITY_BINDING = (Security, kCFBooleanTrue)
    if _SECURITY_BINDING == "unavailable":
        return None, None
    return _SECURITY_BINDING  # type: ignore[return-value]


def _sec_call(call_result: object) -> tuple[object, int]:
    """Normalize a pyobjc ``SecItem*`` call result to ``(out_param, osstatus)``.

    pyobjc wraps ``OSStatus``-returning C functions that take pointer
    out-parameters (``SecItemAdd`` / ``SecItemCopyMatching``) by returning a
    ``(out_param, osstatus)`` tuple, while functions with no out-parameter
    (``SecItemDelete``) return the ``osstatus`` int directly. Rather than
    depend on which convention a given pyobjc version uses, identify the
    ``OSStatus`` as the integer element and the out-parameter as the other.
    The ``SecItem*`` out-parameters here are always a ``CFDataRef`` / ``None``
    (never an int), so this disambiguation is safe.
    """
    if isinstance(call_result, bool):  # pragma: no cover - defensive
        return None, _ERR_SEC_PARAM
    if isinstance(call_result, int):
        return None, call_result
    if isinstance(call_result, tuple):
        if len(call_result) == 1:
            return None, int(call_result[0])
        if len(call_result) == 2:
            a, b = call_result
            if isinstance(a, int) and not isinstance(a, bool):
                return b, a
            return a, int(b)
    return None, _ERR_SEC_PARAM


def _cfdata_to_bytes(ref: object) -> bytes:
    """Coerce a pyobjc ``CFDataRef`` / ``NSData`` / ``bytes`` to ``bytes``."""
    if ref is None:
        return b""
    if isinstance(ref, (bytes, bytearray, memoryview)):
        return bytes(ref)
    try:
        return bytes(ref)  # CFDataRef/NSData support the buffer protocol
    except Exception:  # noqa: BLE001 - proxy without the buffer protocol
        return bytes(ref.bytes())  # type: ignore[union-attr]


def _pyobjc_set(account: str, secret: str, service: str) -> None:
    Security, kcf_true = _security_binding()
    if Security is None:
        raise _PyobjcUnavailable()
    data = secret.encode("utf-8")
    query = {
        Security.kSecClass: Security.kSecClassGenericPassword,
        Security.kSecAttrService: service,
        Security.kSecAttrAccount: account,
        Security.kSecValueData: data,
    }
    _out, status = _sec_call(Security.SecItemAdd(query, None))
    if status == _ERR_SEC_SUCCESS:
        return
    if status == _ERR_SEC_DUPLICATE_ITEM:
        # ``-U`` (update-if-exists) equivalent: update the existing item's data.
        match = {
            Security.kSecClass: Security.kSecClassGenericPassword,
            Security.kSecAttrService: service,
            Security.kSecAttrAccount: account,
        }
        update = {Security.kSecValueData: data}
        _out, status = _sec_call(Security.SecItemUpdate(match, update))
        if status == _ERR_SEC_SUCCESS:
            return
        raise KeychainError(f"SecItemUpdate failed (OSStatus {status})")
    raise KeychainError(f"SecItemAdd failed (OSStatus {status})")


def _pyobjc_get(account: str, service: str) -> str | None:
    Security, kcf_true = _security_binding()
    if Security is None:
        raise _PyobjcUnavailable()
    query = {
        Security.kSecClass: Security.kSecClassGenericPassword,
        Security.kSecAttrService: service,
        Security.kSecAttrAccount: account,
        Security.kSecReturnData: kcf_true,
        Security.kSecMatchLimit: Security.kSecMatchLimitOne,
    }
    out, status = _sec_call(Security.SecItemCopyMatching(query, None))
    if status == _ERR_SEC_ITEM_NOT_FOUND:
        return None
    if status != _ERR_SEC_SUCCESS:
        raise KeychainError(f"SecItemCopyMatching failed (OSStatus {status})")
    if out is None:
        return None
    return _cfdata_to_bytes(out).decode("utf-8", "replace")


def _pyobjc_delete(account: str, service: str) -> None:
    Security, _kcf_true = _security_binding()
    if Security is None:
        raise _PyobjcUnavailable()
    query = {
        Security.kSecClass: Security.kSecClassGenericPassword,
        Security.kSecAttrService: service,
        Security.kSecAttrAccount: account,
    }
    _out, status = _sec_call(Security.SecItemDelete(query))
    # Deleting a missing item is not an error (mirrors the CLI fallback, which
    # also ignores a missing-item exit code).
    if status not in (_ERR_SEC_SUCCESS, _ERR_SEC_ITEM_NOT_FOUND):
        raise KeychainError(f"SecItemDelete failed (OSStatus {status})")


def _warn_cli_secret_leak() -> None:
    global _CLI_LEAK_WARNED
    if _CLI_LEAK_WARNED:
        return
    _CLI_LEAK_WARNED = True
    warnings.warn(
        "pyobjc Security framework unavailable; falling back to the `security` "
        "CLI for Keychain writes, which puts the secret in the child process's "
        "argv (visible via `ps -ww`) for the call's duration. Install the "
        "[macos] extra (pyobjc) to use the leak-free SecItemAdd path.",
        RuntimeWarning,
        stacklevel=3,
    )


# CLI fallback --------------------------------------------------------------


def _cli_set(account: str, secret: str, service: str) -> None:
    # -U updates the item if it already exists. The secret is an argument
    # (``-w <secret>``) and so is visible in the child's argv -- see the module
    # docstring; this path is only reached when pyobjc is unavailable.
    result = subprocess.run(
        ["security", "add-generic-password", "-U", "-s", service, "-a", account, "-w", secret],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise KeychainError(result.stderr.strip() or "security add-generic-password failed")


def _cli_get(account: str, service: str) -> str | None:
    result = subprocess.run(
        ["security", "find-generic-password", "-s", service, "-a", account, "-w"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.rstrip("\n")


def _cli_delete(account: str, service: str) -> None:
    subprocess.run(
        ["security", "delete-generic-password", "-s", service, "-a", account],
        check=False,
        capture_output=True,
        text=True,
    )


# Public API ----------------------------------------------------------------


def set_secret(account: str, secret: str, service: str = DEFAULT_SERVICE) -> None:
    validate_credential_identifier(account, field="account")
    validate_credential_identifier(service, field="service")
    try:
        _pyobjc_set(account, secret, service)
        return
    except _PyobjcUnavailable:
        pass
    _warn_cli_secret_leak()
    _cli_set(account, secret, service)


def get_secret(account: str, service: str = DEFAULT_SERVICE) -> str | None:
    validate_credential_identifier(account, field="account")
    validate_credential_identifier(service, field="service")
    try:
        return _pyobjc_get(account, service)
    except _PyobjcUnavailable:
        pass
    return _cli_get(account, service)


def delete_secret(account: str, service: str = DEFAULT_SERVICE) -> None:
    validate_credential_identifier(account, field="account")
    validate_credential_identifier(service, field="service")
    try:
        _pyobjc_delete(account, service)
        return
    except _PyobjcUnavailable:
        pass
    _cli_delete(account, service)


# DPAPI-shaped facade -------------------------------------------------------


def protect_secret(secret: str, entropy: bytes = b"quill-credential") -> str:
    """Store ``secret`` in the Keychain and return an opaque locator token."""
    account = f"{entropy.decode('utf-8', 'replace')}.{uuid.uuid4().hex}"
    set_secret(account, secret)
    return f"{_TOKEN_PREFIX}{account}"


def unprotect_secret(encoded: str, entropy: bytes = b"quill-credential") -> str:
    """Resolve a locator token produced by :func:`protect_secret`."""
    if not encoded.startswith(_TOKEN_PREFIX):
        raise KeychainError("Not a macOS Keychain locator token")
    account = encoded[len(_TOKEN_PREFIX) :]
    secret = get_secret(account)
    if secret is None:
        raise KeychainError(f"No Keychain item for account {account!r}")
    return secret
