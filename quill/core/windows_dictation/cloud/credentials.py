"""Where a speech provider's fields are kept (D-31, point 4).

* **Secret fields** go to Windows Credential Manager (or the portable DPAPI
  store, or the macOS Keychain -- :mod:`quill.platform.windows.credential_store`
  decides) under one target per provider and field, built with
  :func:`quill.core.assistant_ai.provider_credential_target`. Never in
  settings JSON, never in a log.
* **A file field** (Google's service-account JSON) is too big for Credential
  Manager, which caps a blob at 2,560 bytes, so its contents are protected
  with DPAPI and written to the app data folder; only that protected file's
  path goes in settings.
* **Everything else** (region, project, endpoint ID) is plain settings:
  ``windows_dictation_speech_providers[<provider id>][<field key>]``.

Every secret this module loads or saves is handed to
:func:`quill.stability.redaction.remember_secret`, so its literal value is
scrubbed from crash bundles and redacted log lines from then on.

The store functions are module attributes (:data:`backend`) so tests use a
dictionary and never the real Credential Manager.

wx-free.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quill.core.windows_dictation.cloud.errors import CloudFieldError
from quill.core.windows_dictation.cloud.types import CloudProvider

__all__ = [
    "SAVED_MARK",
    "Backend",
    "backend",
    "has_required",
    "protected_file",
    "remove",
    "save",
    "secret_target",
    "values_for",
]


@dataclass(slots=True)
class Backend:
    """The secret store and the file protector. Swapped for fakes in tests."""

    load: Callable[[str], str]
    save: Callable[[str, str], None]
    delete: Callable[[str], Any]
    protect: Callable[[str], str]
    unprotect: Callable[[str], str]
    folder: Callable[[], Path]


def _load(target: str) -> str:
    from quill.platform.windows.credential_store import load_secret

    return load_secret(target)


def _save(target: str, secret: str) -> None:
    from quill.platform.windows.credential_store import save_secret

    save_secret(target, secret)


def _delete(target: str) -> bool:
    from quill.platform.windows.credential_store import delete_secret

    return delete_secret(target)


def _protect(text: str) -> str:
    from quill.core.assistant_ai import protect_secret

    return protect_secret(text)


def _unprotect(text: str) -> str:
    from quill.core.assistant_ai import unprotect_secret

    return unprotect_secret(text)


def _folder() -> Path:
    from quill.core.paths import app_data_dir

    return app_data_dir() / "speech-providers"


backend = Backend(_load, _save, _delete, _protect, _unprotect, _folder)

#: Kept in a provider's plain settings by :func:`save`, so a provider whose
#: fields are all secret is still known to be set up -- and so nothing reads
#: the credential store for a provider nobody ever saved.
SAVED_MARK = "saved"


def secret_target(provider_id: str, field_key: str) -> str:
    """The credential target for one secret field of one provider."""
    from quill.core.assistant_ai import provider_credential_target

    return provider_credential_target(f"speech-{provider_id}-{field_key}")


def protected_file(provider_id: str, field_key: str) -> Path:
    """Where a file field's DPAPI-protected copy lives."""
    return backend.folder() / f"{provider_id}-{field_key}.dpapi"


def _remember(value: str) -> None:
    from quill.stability.redaction import remember_secret

    remember_secret(value)
    if value.lstrip().startswith("{"):  # a service-account file: its key lines too
        try:
            data = json.loads(value)
        except ValueError:
            return
        if isinstance(data, dict):
            for name in ("private_key_id", "private_key", "client_id"):
                for line in str(data.get(name, "") or "").splitlines():
                    remember_secret(line)


def values_for(provider: CloudProvider, stored: Mapping[str, Any] | None) -> dict[str, str]:
    """Everything the person entered for *provider*: the settings part from
    *stored*, the secrets from the credential store. In memory only."""
    plain = dict(stored or {})
    values: dict[str, str] = {}
    for spec in provider.fields():
        if spec.kind == "secret":
            value = backend.load(secret_target(provider.id, spec.key))
            if not value:
                fallback = getattr(provider, "fallback_secret", None)
                value = fallback(spec.key) if callable(fallback) else ""
        elif spec.kind == "file":
            value = _read_protected(str(plain.get(spec.key, "") or ""))
        else:
            value = str(plain.get(spec.key, "") or spec.default)
        if value and spec.secret:
            _remember(value)
        values[spec.key] = value
    return values


def _read_protected(path: str) -> str:
    if not path:
        return ""
    try:
        return backend.unprotect(Path(path).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - a lost or foreign file is "not saved"
        return ""


def save(provider: CloudProvider, values: Mapping[str, str]) -> dict[str, str]:
    """Keep *values*: secrets in the credential store, a file field protected
    on disk. Returns the settings part (never a secret) for
    ``windows_dictation_speech_providers[provider.id]``.

    A secret field left empty keeps what is saved: the page never shows a saved
    secret, so an empty field means "unchanged", and Remove forgets it.
    """
    plain: dict[str, str] = {SAVED_MARK: "yes"}
    for spec in provider.fields():
        value = str(values.get(spec.key, "") or "").strip()
        if spec.kind == "secret":
            if value:
                _remember(value)
                backend.save(secret_target(provider.id, spec.key), value)
        elif spec.kind == "file":
            plain[spec.key] = _save_file(provider, spec.key, spec.label, value)
        elif value:
            plain[spec.key] = value
    return plain


def _save_file(provider: CloudProvider, key: str, label: str, value: str) -> str:
    """Protect the file at *value* (a path the person chose), or keep the copy
    already saved when *value* is that copy's path or empty."""
    target = protected_file(provider.id, key)
    if not value or Path(value) == target:
        return str(target) if target.exists() else ""
    try:
        text = Path(value).read_text(encoding="utf-8")
    except OSError:
        raise CloudFieldError(f"That file could not be read. Check {label}.", field=label) from None
    _remember(text)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(backend.protect(text), encoding="utf-8")
    return str(target)


def remove(provider: CloudProvider) -> None:
    """Forget every secret and protected file saved for *provider*."""
    for spec in provider.fields():
        if spec.kind == "secret":
            backend.delete(secret_target(provider.id, spec.key))
        elif spec.kind == "file":
            try:
                protected_file(provider.id, spec.key).unlink(missing_ok=True)
            except OSError:
                pass


def has_required(provider: CloudProvider, values: Mapping[str, str]) -> bool:
    """Whether every required field has something in it, and the provider's own
    check (Region or Endpoint, keys or a profile) is satisfied."""
    filled = all(
        str(values.get(spec.key, "") or "").strip() for spec in provider.fields() if spec.required
    )
    return filled and provider.problem(values) is None
