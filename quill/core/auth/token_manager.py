"""The Token Manager: valid access tokens on demand, for every provider.

This is the layer that turns "a stored refresh token" into "a valid access
token, right now" (``bard.md`` Part D). It persists sessions only through the
:class:`~quill.core.secrets.SecretsManager` (never an OS vault directly), reads
the wall clock through an injected ``now`` so every branch is deterministically
testable, and performs the token-endpoint exchange through an injected
``poster`` -- by default the already-reviewed, TLS-verified
:func:`quill.core.ai.oauth_poster.post_form`, so this module adds **no** new
network egress site.

Refresh is single-flight per provider: concurrent callers that all find the
access token expired do not stampede the token endpoint; the first refreshes and
the rest reuse the result.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import replace
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from quill.core.auth.flows import BrowserOpener, RedirectWaiter

from quill.core.auth.errors import (
    AuthError,
    ProviderConfigError,
    RefreshInvalidGrantError,
    TokenUnavailableError,
)
from quill.core.auth.events import (
    REFRESH_FAILED,
    SIGNED_IN,
    SIGNED_OUT,
    AuthEvent,
    AuthListener,
)
from quill.core.auth.provider import OAuthProvider, ProviderRegistry
from quill.core.auth.token_bundle import TokenBundle
from quill.core.secrets import SecretRef, SecretsManager, default_secrets_manager

#: A poster performs one token-endpoint form POST and returns the parsed JSON
#: object (OAuth signals progress/errors with an ``error`` field in the body).
Poster = Callable[[str, "dict[str, str]"], "dict[str, Any]"]

_TOKENS_NAME = "tokens"


def _default_poster() -> Poster:
    """The real network poster: the reviewed, TLS-verified OAuth form poster."""

    def poster(url: str, fields: dict[str, str]) -> dict[str, Any]:
        from quill.core.ai.oauth_poster import post_form

        return post_form(url, fields)

    return poster


class TokenManager:
    """Issues and refreshes OAuth tokens for registered providers."""

    def __init__(
        self,
        secrets: SecretsManager | None = None,
        registry: ProviderRegistry | None = None,
        poster: Poster | None = None,
        *,
        now: Callable[[], float] = time.time,
    ) -> None:
        self._secrets = secrets or default_secrets_manager()
        self._registry = registry if registry is not None else ProviderRegistry()
        self._poster = poster or _default_poster()
        self._now = now
        self._locks_guard = threading.Lock()
        self._locks: dict[str, threading.Lock] = {}
        self._listeners: list[AuthListener] = []

    @property
    def registry(self) -> ProviderRegistry:
        return self._registry

    # -- events --------------------------------------------------------------

    def subscribe(self, listener: AuthListener) -> Callable[[], None]:
        """Register ``listener`` for auth events. Returns an unsubscribe callable."""
        self._listeners.append(listener)

        def unsubscribe() -> None:
            try:
                self._listeners.remove(listener)
            except ValueError:
                pass

        return unsubscribe

    def _emit(self, kind: str, provider: str) -> None:
        event = AuthEvent(kind, provider)
        for listener in list(self._listeners):
            try:
                listener(event)
            except Exception:  # noqa: BLE001 - a bad listener must not break auth
                pass

    # -- storage -------------------------------------------------------------

    def _ref(self, provider: str) -> SecretRef:
        return SecretRef(provider, _TOKENS_NAME)

    def _load(self, provider: str) -> TokenBundle:
        raw = self._secrets.get(self._ref(provider))
        return TokenBundle.from_json(raw) if raw else TokenBundle()

    def _store(self, provider: str, bundle: TokenBundle) -> None:
        self._secrets.set(self._ref(provider), bundle.to_json())

    def is_signed_in(self, provider: str) -> bool:
        return not self._load(provider).is_empty

    def bundle(self, provider: str) -> TokenBundle | None:
        loaded = self._load(provider)
        return None if loaded.is_empty else loaded

    # -- access-token acquisition -------------------------------------------

    def get_access_token(self, provider: str) -> str | None:
        """Return a valid access token, refreshing if needed, or ``None``.

        ``None`` means the caller must sign in again (no session, or the refresh
        token was rejected). Raises :class:`TokenUnavailableError` only when a
        refresh was genuinely required but a transport failure prevented it.
        """
        prov = self._registry.get(provider)  # ProviderUnknownError if unknown
        loaded = self._load(provider)
        if loaded.is_empty:
            return None
        if not loaded.needs_refresh(self._now()):
            return loaded.access_token or None
        with self._lock_for(provider):
            loaded = self._load(provider)  # re-read: another thread may have refreshed
            if loaded.is_empty:
                return None
            if not loaded.needs_refresh(self._now()):
                return loaded.access_token or None
            try:
                return self._refresh_locked(prov, loaded)
            except RefreshInvalidGrantError:
                return None

    def _lock_for(self, provider: str) -> threading.Lock:
        with self._locks_guard:
            lock = self._locks.get(provider)
            if lock is None:
                lock = threading.Lock()
                self._locks[provider] = lock
            return lock

    def _refresh_locked(self, prov: OAuthProvider, current: TokenBundle) -> str | None:
        fields = {
            "grant_type": "refresh_token",
            "refresh_token": current.refresh_token,
            "client_id": prov.client_id,
        }
        if prov.scopes:
            fields["scope"] = prov.scope_str
        try:
            response = self._poster(prov.broker_url or prov.token_url, fields)
        except (OSError, ValueError) as exc:  # URLError is an OSError subclass
            if not current.is_expired(self._now(), skew=0.0):
                return current.access_token or None
            raise TokenUnavailableError(f"could not refresh {prov.name}: {exc}") from exc

        error = str(response.get("error", ""))
        if error:
            if error == "invalid_grant":
                self.wipe(prov.name)
                self._emit(REFRESH_FAILED, prov.name)
                raise RefreshInvalidGrantError(f"{prov.name} refresh rejected: {error}")
            raise AuthError(f"{prov.name} refresh failed: {error}")

        merged = self._merge_refresh(current, TokenBundle.from_mapping(response, now=self._now()))
        if not merged.access_token:
            raise TokenUnavailableError(f"{prov.name} refresh returned no access token")
        self._store(prov.name, merged)
        return merged.access_token

    @staticmethod
    def _merge_refresh(old: TokenBundle, new: TokenBundle) -> TokenBundle:
        # A refresh response often omits an unchanged refresh_token (and scope);
        # keep the previous values so the session is not silently downgraded.
        return replace(
            new,
            refresh_token=new.refresh_token or old.refresh_token,
            scope=new.scope or old.scope,
        )

    # -- session lifecycle ---------------------------------------------------

    def store_new_session(self, provider: str, bundle: TokenBundle) -> None:
        """Persist a freshly-obtained session and emit ``signed_in``.

        Called by the sign-in flows (Phase 3) after a successful exchange.
        """
        self._store(provider, bundle)
        self._emit(SIGNED_IN, provider)

    def wipe(self, provider: str) -> None:
        """Clear every stored secret for ``provider`` (no event emitted)."""
        self._secrets.wipe_namespace(provider)

    def sign_out(self, provider: str) -> None:
        """Best-effort revoke, then clear the session and emit ``signed_out``."""
        loaded = self._load(provider)
        if self._registry.has(provider):
            prov = self._registry.get(provider)
            token = loaded.refresh_token or loaded.access_token
            if prov.revoke_url and token:
                try:
                    self._poster(prov.revoke_url, {"token": token, "client_id": prov.client_id})
                except (OSError, ValueError):
                    pass
        self.wipe(provider)
        self._emit(SIGNED_OUT, provider)

    # -- interactive sign-in (delegates to flows; Phase 3) -------------------

    def sign_in(
        self,
        provider: str,
        *,
        waiter: RedirectWaiter | None = None,
        opener: BrowserOpener | None = None,
        timeout: float = 300.0,
    ) -> TokenBundle:
        """Run the Authorization Code + PKCE loopback flow and store the session."""
        from quill.core.auth.flows import run_authorization_code_flow

        prov = self._registry.get(provider)
        bundle = run_authorization_code_flow(
            prov,
            self._poster,
            waiter=waiter,
            opener=opener,
            now=self._now,
            timeout=timeout,
        )
        self.store_new_session(provider, bundle)
        return bundle

    def sign_in_device(
        self,
        provider: str,
        on_code: Callable[[str, str], None],
        *,
        sleep: Callable[[float], None] | None = None,
        max_seconds: float = 900.0,
    ) -> TokenBundle:
        """Run the device-code flow and store the session."""
        from quill.core.auth.flows import run_device_code_flow

        prov = self._registry.get(provider)
        if not prov.device_code_url:
            raise ProviderConfigError(f"provider {prov.name!r} has no device_code_url")
        bundle = run_device_code_flow(
            prov,
            self._poster,
            on_code,
            now=self._now,
            sleep=sleep,
            max_seconds=max_seconds,
        )
        self.store_new_session(provider, bundle)
        return bundle


__all__ = ["Poster", "TokenManager"]
