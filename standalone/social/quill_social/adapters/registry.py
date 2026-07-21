"""Adapter factory: map an Account to its NetworkAdapter (PRD 11, 29.1).

One place decides which adapter serves an account, so the domain and UI ask for
"the adapter for this account" and never construct network clients directly.
The mock network is always available; live adapters are constructed with the
account's durable identity (Mastodon instance, Bluesky DID).

When a :class:`CredentialStore` is supplied and it holds a resolvable secret for
the account, the factory tries to build a *connected* live client and hand it to
the adapter, so read/publish work against the real network. If no credentials
are supplied, none resolve, or the client library is not installed, the factory
returns the descriptor adapter -- which raises a clear "not enabled"
:class:`AdapterError` at each network method. Secrets are resolved only at this
boundary (PRD 31.1); the raw token never lands in the database.

The client builders are module-level so tests can monkeypatch them with a fake
client without importing the (optional) SDKs.
"""

from __future__ import annotations

from typing import Any

from quill_social.adapters.base import NetworkAdapter
from quill_social.adapters.bluesky import BlueskyAdapter
from quill_social.adapters.mastodon import MastodonAdapter
from quill_social.adapters.mock import MockNetwork
from quill_social.model import Account
from quill_social.security.credentials import CredentialStore


def _resolve_secret(credentials: CredentialStore | None, account: Account) -> str | None:
    """Resolve the account's stored secret at the boundary, or ``None``."""
    if credentials is None:
        return None
    ref = credentials.reference(account.network, account.account_id)
    if ref is None:
        return None
    return credentials.resolve(ref)


def _build_mastodon_client(instance: str, token: str) -> Any:
    """Build a connected Mastodon.py client, or ``None`` if the SDK is absent."""
    try:
        from mastodon import Mastodon
    except ImportError:
        return None
    base = instance if instance.startswith("http") else f"https://{instance}"
    return Mastodon(access_token=token, api_base_url=base)


def _build_bluesky_client(identifier: str, service: str, secret: str) -> Any:
    """Build a logged-in atproto client, or ``None`` if the SDK is absent."""
    try:
        from atproto import Client
    except ImportError:
        return None
    client = Client(base_url=service) if service else Client()
    client.login(identifier, secret)
    return client


def adapter_for(
    account: Account, credentials: CredentialStore | None = None
) -> NetworkAdapter:
    """Return a network adapter appropriate for ``account``.

    ``credentials`` is optional and backward compatible: existing callers pass a
    single argument and get the descriptor adapter. When a store is provided and
    a secret resolves, a live adapter connected to the network is returned.
    """
    if account.network == "mastodon":
        secret = _resolve_secret(credentials, account)
        if secret:
            client = _build_mastodon_client(account.instance, secret)
            if client is not None:
                return MastodonAdapter(
                    instance=account.instance,
                    account_id=account.account_id,
                    client=client,
                )
        return MastodonAdapter(instance=account.instance)

    if account.network == "bluesky":
        secret = _resolve_secret(credentials, account)
        if secret:
            identifier = account.handle or account.did
            client = _build_bluesky_client(identifier, "https://bsky.social", secret)
            if client is not None:
                return BlueskyAdapter(
                    did=account.did,
                    account_id=account.account_id,
                    client=client,
                )
        return BlueskyAdapter(did=account.did)

    # mock (and any unknown network) falls back to the deterministic mock so the
    # app never dead-ends on an unconfigured account.
    return MockNetwork(account_id=account.account_id)
