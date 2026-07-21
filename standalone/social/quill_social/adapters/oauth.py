"""Mastodon OAuth sign-in helper (PRD 11.1, 31.1).

The accessible desktop sign-in flow: register the app with the server once
(cached per instance), open the server's authorization page in the browser, let
the user approve and copy the out-of-band code, then exchange that code for an
access token. The token is what the credential vault stores; the user never has
to hand-create an application.

This module is wx-free and keeps every network touch behind an injectable
factory, so the caching and URL logic are unit-testable without a live server or
Mastodon.py installed. The live calls lazily import Mastodon.py.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

# Scopes must be identical across create_app, auth_request_url, and log_in or
# the server rejects the exchange, so they live in one place.
SCOPES = ["read", "write", "follow"]
REDIRECT = "urn:ietf:wg:oauth:2.0:oob"  # out-of-band: server shows a copyable code
CLIENT_NAME = "QUILL Social"
APPS_FILE = "mastodon_apps.json"


def normalize_instance(instance: str) -> str:
    """Bare host key for caching (no scheme, no trailing slash, lowercased)."""
    host = (instance or "").strip().rstrip("/")
    host = host.removeprefix("https://").removeprefix("http://")
    return host.lower()


def base_url(instance: str) -> str:
    host = (instance or "").strip().rstrip("/")
    if host.startswith("http://") or host.startswith("https://"):
        return host
    return f"https://{host}"


def _apps_path(data_dir: str | Path) -> Path:
    return Path(data_dir) / APPS_FILE


def _load_all(data_dir: str | Path) -> dict:
    p = _apps_path(data_dir)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (ValueError, OSError):
        return {}


def _save_all(data_dir: str | Path, data: dict) -> None:
    _apps_path(data_dir).write_text(json.dumps(data, indent=2), encoding="utf-8")


def cached_app(data_dir: str | Path, instance: str) -> tuple[str, str] | None:
    entry = _load_all(data_dir).get(normalize_instance(instance))
    if entry and entry.get("client_id") and entry.get("client_secret"):
        return entry["client_id"], entry["client_secret"]
    return None


# A creator returns (client_id, client_secret) for an instance; injectable so
# tests never hit the network.
Creator = Callable[[str], tuple[str, str]]
# A client factory returns an object exposing auth_request_url / log_in.
ClientFactory = Callable[[str, str, str], object]


def register_app(
    instance: str, data_dir: str | Path, *, create: Creator | None = None
) -> tuple[str, str]:
    """Return this instance's (client_id, client_secret), registering if needed.

    Registration is cached in ``mastodon_apps.json`` so re-signing in to the same
    server reuses the same application.
    """
    existing = cached_app(data_dir, instance)
    if existing:
        return existing
    creator = create or _default_create
    client_id, client_secret = creator(instance)
    data = _load_all(data_dir)
    data[normalize_instance(instance)] = {
        "client_id": client_id,
        "client_secret": client_secret,
    }
    _save_all(data_dir, data)
    return client_id, client_secret


def auth_url(
    instance: str,
    client_id: str,
    client_secret: str,
    *,
    factory: ClientFactory | None = None,
) -> str:
    """The server authorization URL the user opens to approve access."""
    make = factory or _default_client
    client = make(instance, client_id, client_secret)
    return client.auth_request_url(scopes=SCOPES, redirect_uris=REDIRECT)


def exchange_code(
    instance: str,
    client_id: str,
    client_secret: str,
    code: str,
    *,
    factory: ClientFactory | None = None,
) -> str:
    """Exchange the pasted authorization code for an access token."""
    make = factory or _default_client
    client = make(instance, client_id, client_secret)
    return client.log_in(code=code.strip(), scopes=SCOPES, redirect_uri=REDIRECT)


def _default_create(instance: str) -> tuple[str, str]:
    from mastodon import Mastodon

    return Mastodon.create_app(
        CLIENT_NAME,
        scopes=SCOPES,
        redirect_uris=REDIRECT,
        api_base_url=base_url(instance),
    )


def _default_client(instance: str, client_id: str, client_secret: str) -> object:
    from mastodon import Mastodon

    return Mastodon(
        client_id=client_id,
        client_secret=client_secret,
        api_base_url=base_url(instance),
    )
