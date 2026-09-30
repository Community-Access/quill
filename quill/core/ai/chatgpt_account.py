"""Sign in with ChatGPT: use the plan you already pay for, from inside a QUILL app.

OpenAI lets a desktop app use a person's ChatGPT subscription directly. The app
registers itself at sign-in time (no client secret, nothing to extract from the
build), the person confirms in their browser, and from then on every request
goes straight from this computer to OpenAI on their plan -- no API key, no
per-request bill, and no QUILL server in between.

**What is kept, and where.** Two things, kept apart on purpose, the same shape
as :mod:`quill.core.ai.gateway_session`:

* **The refresh token** is the secret and goes to the OS credential store
  through :class:`quill.core.secrets.SecretsManager`, one entry per app. Only
  the refresh token: Windows' credential blobs are small, and the prototype that
  stored the whole token response there failed with error 1783 on real
  accounts. The access token lives in memory and is renewed from the refresh
  token whenever it is needed, including once per launch.
* **Everything else** -- which account, the client id OpenAI issued, the stable
  host id, the chosen model, whether web search is allowed -- is ordinary state
  in ``<data>/ai/chatgpt.json``. None of it is sensitive and all of it is useful
  in a bug report.

**Each app is its own agent.** OpenAI shows the agent's name on the consent
page and in the person's ChatGPT settings, so QUILL Lite signs in as "QUILL
Lite" and Quill Radio as "QUILL Radio", each with its own host id, its own
issued client id and its own refresh token. Signing one out leaves the others
connected, which is what somebody who revokes "QUILL Radio" in their ChatGPT
settings expects to happen.

**The ID token is checked, not merely decoded.** The nonce, the issuer, the
audience and the expiry are all verified. Its signature is not: the token
arrives over a certificate-verified TLS connection straight from the issuer's
own token endpoint, in direct exchange for a code only this process holds the
PKCE verifier for, which is the case OpenID Connect Core 3.1.3.7 names as
sufficient -- and it keeps a JWT library and a JWKS fetch out of the build.

The network is injectable throughout (*poster*, *opener*, *browser*), so the
whole flow is unit-tested without a socket. wx-free and strict-typed.
"""

from __future__ import annotations

import base64
import json
import secrets
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from quill.core.ai.chatgpt_errors import ChatGptSignedOutError, ChatGptSignInError
from quill.core.ai.chatgpt_loopback import CALLBACK_PATH, LoopbackListener
from quill.core.secrets import SecretRef, SecretsManager
from quill.core.storage import read_json, write_json_atomic

__all__ = [
    "API_BASE",
    "AUTH_BASE",
    "CALLBACK_PATH",
    "PLAN_SCOPE",
    "SCOPES",
    "USAGE_URL",
    "ChatGptAccount",
    "ChatGptState",
    "LoopbackListener",
    "decode_claims",
    "load_state",
    "save_state",
    "slug_for",
]

AUTH_BASE = "https://auth.openai.com"
AUTHORIZE_URL = f"{AUTH_BASE}/api/accounts/authorize"
TOKEN_URL = f"{AUTH_BASE}/api/accounts/oauth/token"
OPENID_CONFIGURATION_URL = f"{AUTH_BASE}/.well-known/openid-configuration"
API_BASE = "https://api.openai.com/v1"
#: Where a person's own plan usage is. OpenAI's page is the only true answer;
#: QUILL keeps a local count of requests but never sees the plan's limits.
USAGE_URL = "https://chatgpt.com/#settings/Usage"

#: The permission that lets an app spend the plan. Without it in the granted
#: scope the sign-in is refused here, because every request would fail later
#: with a less helpful sentence.
PLAN_SCOPE = "chatgpt.tokens.use.direct"
SCOPES: tuple[str, ...] = (
    "openid",
    "profile",
    "email",
    "offline_access",
    "resource.invoke",
    PLAN_SCOPE,
)

#: The placeholder client id that asks OpenAI to register this app on the spot.
#: The redirect carries the client id actually issued; that is what is kept.
DYNAMIC_CLIENT = "dynamic_agent_client"
_SECRETS_NAMESPACE = "chatgpt"
_STATE_DIR = "ai"
_STATE_FILE = "chatgpt.json"
#: A refresh happens this many seconds before the access token would expire.
_REFRESH_SKEW_SECONDS = 120.0
#: How long the browser is waited for before the sign-in is abandoned.
SIGN_IN_TIMEOUT_SECONDS = 300.0

#: Posts a urlencoded form and returns the parsed JSON body (the OAuth poster's shape).
Poster = Callable[[str, "dict[str, str]"], "dict[str, Any]"]
#: Opens a URL in the person's browser. Returns whether it could.
Browser = Callable[[str], bool]


def slug_for(agent_name: str) -> str:
    """``"QUILL Lite"`` -> ``"quill-lite"``: the secrets-store name for an agent."""
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in agent_name.strip())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "quill"


@dataclass(frozen=True, slots=True)
class ChatGptState:
    """Everything non-secret this app knows about its ChatGPT sign-in."""

    #: Stable per install and per app; OpenAI ties the dynamic registration to it.
    host_id: str = ""
    client_id: str = ""
    subject: str = ""
    email: str = ""
    scope: str = ""
    connected_at: str = ""
    #: The model requests use, chosen from the account's own list. Empty until
    #: the list has been read once; a request with no model says so.
    model: str = ""
    #: Whether OpenAI's hosted web search may be offered to the model. Off by
    #: default: a search is a second thing sent somewhere, and it is the
    #: person's to switch on.
    web_search: bool = False

    @property
    def signed_in(self) -> bool:
        return bool(self.client_id and self.subject)

    @property
    def account_label(self) -> str:
        """The account as a person hears it: the email, or a neutral phrase."""
        return self.email or "your ChatGPT account"

    def to_dict(self) -> dict[str, Any]:
        return {
            "host_id": self.host_id,
            "client_id": self.client_id,
            "subject": self.subject,
            "email": self.email,
            "scope": self.scope,
            "connected_at": self.connected_at,
            "model": self.model,
            "web_search": self.web_search,
        }

    @classmethod
    def from_dict(cls, data: object) -> ChatGptState:
        if not isinstance(data, dict):
            return cls()
        return cls(
            host_id=str(data.get("host_id", "") or ""),
            client_id=str(data.get("client_id", "") or ""),
            subject=str(data.get("subject", "") or ""),
            email=str(data.get("email", "") or ""),
            scope=str(data.get("scope", "") or ""),
            connected_at=str(data.get("connected_at", "") or ""),
            model=str(data.get("model", "") or ""),
            web_search=bool(data.get("web_search", False)),
        )


def _state_path(data_dir: Path) -> Path:
    return data_dir / _STATE_DIR / _STATE_FILE


def load_state(data_dir: Path) -> ChatGptState:
    try:
        return ChatGptState.from_dict(read_json(_state_path(data_dir), default={}))
    except OSError:
        return ChatGptState()


def save_state(data_dir: Path, state: ChatGptState) -> None:
    path = _state_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(path, state.to_dict())


# --------------------------------------------------------------------------- #
# The ID token
# --------------------------------------------------------------------------- #


def decode_claims(id_token: str) -> dict[str, Any]:
    """The claims in a JWT's payload, or ``{}`` for anything that is not one."""
    parts = id_token.split(".")
    if len(parts) != 3:
        return {}
    payload = parts[1]
    payload += "=" * (-len(payload) % 4)
    try:
        decoded = json.loads(base64.urlsafe_b64decode(payload.encode("ascii")))
    except (ValueError, UnicodeDecodeError):
        return {}
    return decoded if isinstance(decoded, dict) else {}


def _check_claims(claims: dict[str, Any], *, client_id: str, nonce: str, now: float) -> None:
    if claims.get("iss") != AUTH_BASE:
        raise ChatGptSignInError("The sign-in answer did not come from OpenAI.")
    audience = claims.get("aud")
    audiences = audience if isinstance(audience, list) else [audience]
    if client_id not in audiences:
        raise ChatGptSignInError("The sign-in answer was meant for a different app.")
    if claims.get("nonce") != nonce:
        raise ChatGptSignInError("The sign-in answer did not match this request.")
    try:
        expires = float(claims.get("exp", 0) or 0)
    except (TypeError, ValueError):
        expires = 0.0
    if expires and expires < now:
        raise ChatGptSignInError("The sign-in answer had already expired. Try again.")
    if not str(claims.get("sub", "") or ""):
        raise ChatGptSignInError("The sign-in answer named no account.")


# --------------------------------------------------------------------------- #
# The account
# --------------------------------------------------------------------------- #


def _default_poster() -> Poster:
    def poster(url: str, fields: dict[str, str]) -> dict[str, Any]:
        from quill.core.ai.oauth_poster import post_form

        return post_form(url, fields)

    return poster


def _default_browser(url: str) -> bool:
    import webbrowser

    return bool(webbrowser.open(url))


def _now_iso() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()


class ChatGptAccount:
    """One app's ChatGPT sign-in: the state, the secret, and a valid token on demand."""

    def __init__(
        self,
        data_dir: Path,
        *,
        agent_name: str,
        secrets_manager: SecretsManager | None = None,
        poster: Poster | None = None,
        browser: Browser | None = None,
        now: Callable[[], float] = time.time,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.agent_name = agent_name
        self.slug = slug_for(agent_name)
        self._secrets = secrets_manager
        self._poster = poster or _default_poster()
        self._browser = browser or _default_browser
        self._now = now
        self._state: ChatGptState | None = None
        self._access_token = ""
        self._access_expires_at = 0.0
        self._lock = threading.Lock()
        self._listener: LoopbackListener | None = None

    # -- storage ----------------------------------------------------------- #

    @property
    def _store(self) -> SecretsManager:
        if self._secrets is None:
            from quill.core.secrets import default_secrets_manager

            self._secrets = default_secrets_manager()
        return self._secrets

    @property
    def _refresh_ref(self) -> SecretRef:
        return SecretRef(_SECRETS_NAMESPACE, f"{self.slug}-refresh")

    @property
    def state(self) -> ChatGptState:
        if self._state is None:
            self._state = load_state(self.data_dir)
        return self._state

    def _save(self, state: ChatGptState) -> None:
        save_state(self.data_dir, state)
        self._state = state

    @property
    def signed_in(self) -> bool:
        """Whether this app holds a usable sign-in: an account, and its refresh token."""
        if not self.state.signed_in:
            return False
        try:
            return bool(self._store.get(self._refresh_ref))
        except Exception:  # noqa: BLE001 - an unreadable store means "signed out"
            return False

    def _host_id(self) -> str:
        host_id = self.state.host_id
        if not host_id:
            host_id = "urn:uuid:" + str(uuid.uuid4())
            self._save(replace(self.state, host_id=host_id))
        return host_id

    # -- preferences --------------------------------------------------------- #

    @property
    def model(self) -> str:
        return self.state.model

    @property
    def web_search(self) -> bool:
        return self.state.web_search

    def set_model(self, model: str) -> None:
        self._save(replace(self.state, model=model.strip()))

    def set_web_search(self, allowed: bool) -> None:
        self._save(replace(self.state, web_search=bool(allowed)))

    # -- signing in ---------------------------------------------------------- #

    def sign_in(self, *, on_waiting: Callable[[str], None] | None = None) -> ChatGptState:
        """Continue with ChatGPT. Blocking; run it on a worker thread.

        Opens the browser, waits for it to come back, exchanges the code, checks
        the ID token, and stores the result. *on_waiting* is told the redirect
        address once the browser has been asked to open, so a window can say
        "waiting for your browser" with the address to open by hand if it did
        not. Raises :class:`ChatGptSignInError` with a sentence for a person.
        """
        from quill.core.auth.pkce import generate_pkce_pair

        pair = generate_pkce_pair()
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        known = self.state
        client = known.client_id or DYNAMIC_CLIENT
        listener = LoopbackListener()
        self._listener = listener
        try:
            query = {
                "client_id": client,
                "ext_agent_host_id": self._host_id(),
                "response_type": "code",
                "redirect_uri": listener.redirect_uri,
                "scope": " ".join(SCOPES),
                "resource": API_BASE,
                "state": state,
                "nonce": nonce,
                "code_challenge_method": pair.method,
                "code_challenge": pair.challenge,
            }
            if known.client_id:
                if known.email:
                    query["login_hint"] = known.email
            else:
                query["agent_name_hint"] = self.agent_name
            url = f"{AUTHORIZE_URL}?{urlencode(query)}"
            opened = self._browser(url)
            if on_waiting is not None:
                on_waiting(url if not opened else "")
            answer = listener.wait(SIGN_IN_TIMEOUT_SECONDS)
        finally:
            listener.close()
            self._listener = None
        if not answer:
            raise ChatGptSignInError(
                "The browser did not come back with a sign-in. Nothing was changed."
            )
        if answer.get("state") != state:
            raise ChatGptSignInError("The sign-in answer did not match this request.")
        if answer.get("error"):
            raise ChatGptSignInError(
                str(answer.get("error_description") or answer["error"]).strip()
            )
        issued = str(answer.get("client_id") or client)
        if issued == DYNAMIC_CLIENT or not answer.get("code"):
            raise ChatGptSignInError("OpenAI did not register this app. Nothing was changed.")
        tokens = self._poster(
            TOKEN_URL,
            {
                "grant_type": "authorization_code",
                "client_id": issued,
                "code": str(answer["code"]),
                "code_verifier": pair.verifier,
                "redirect_uri": listener.redirect_uri,
                "resource": API_BASE,
            },
        )
        if tokens.get("error"):
            raise ChatGptSignInError(
                str(tokens.get("error_description") or tokens["error"]).strip()
            )
        claims = decode_claims(str(tokens.get("id_token", "") or ""))
        _check_claims(claims, client_id=issued, nonce=nonce, now=self._now())
        granted = set(str(tokens.get("scope", "") or "").split())
        if PLAN_SCOPE not in granted:
            raise ChatGptSignInError(
                "ChatGPT did not allow this app to use your plan. Choose Continue "
                "with ChatGPT again and allow it on the consent page."
            )
        refresh = str(tokens.get("refresh_token", "") or "")
        if not refresh:
            raise ChatGptSignInError("OpenAI did not return a refresh token, so nothing was kept.")
        try:
            self._store.set(self._refresh_ref, refresh)
            stored = self._store.get(self._refresh_ref) == refresh
        except Exception:  # noqa: BLE001 - reported below, never raised bare
            stored = False
        if not stored:
            raise ChatGptSignInError(
                "ChatGPT signed you in, but the sign-in could not be stored securely "
                "on this computer, so it would be forgotten on the next launch. "
                "Nothing was kept."
            )
        self._remember_access(tokens)
        self._save(
            replace(
                self.state,
                client_id=issued,
                subject=str(claims.get("sub", "")),
                email=str(claims.get("email", "") or ""),
                scope=" ".join(sorted(granted)),
                connected_at=_now_iso(),
            )
        )
        return self.state

    def cancel_sign_in(self) -> None:
        """Stop waiting for the browser, if a sign-in is waiting."""
        listener = self._listener
        if listener is not None:
            listener.cancel()

    # -- the token ------------------------------------------------------------ #

    def _remember_access(self, tokens: dict[str, Any]) -> None:
        self._access_token = str(tokens.get("access_token", "") or "")
        try:
            lifetime = float(tokens.get("expires_in", 0) or 0)
        except (TypeError, ValueError):
            lifetime = 0.0
        self._access_expires_at = self._now() + lifetime if lifetime > 0 else 0.0

    def access_token(self) -> str:
        """A valid access token, refreshed when needed. Raises when signed out.

        Single-flight: two requests that both find the token expired share one
        refresh rather than racing the token endpoint with the same refresh token.
        """
        with self._lock:
            if self._access_token and self._now() < self._access_expires_at - _REFRESH_SKEW_SECONDS:
                return self._access_token
            state = self.state
            if not state.signed_in:
                raise ChatGptSignedOutError("This app is not signed in with ChatGPT.")
            try:
                refresh = self._store.get(self._refresh_ref) or ""
            except Exception:  # noqa: BLE001 - unreadable store: treated as signed out
                refresh = ""
            if not refresh:
                self._forget_locally()
                raise ChatGptSignedOutError("This computer's ChatGPT sign-in is gone.")
            tokens = self._poster(
                TOKEN_URL,
                {
                    "grant_type": "refresh_token",
                    "client_id": state.client_id,
                    "refresh_token": refresh,
                    "resource": API_BASE,
                },
            )
            if tokens.get("error") or not tokens.get("access_token"):
                self._forget_locally()
                raise ChatGptSignedOutError(
                    "OpenAI no longer accepts this computer's ChatGPT sign-in."
                )
            new_refresh = str(tokens.get("refresh_token", "") or "")
            if new_refresh and new_refresh != refresh:
                try:
                    self._store.set(self._refresh_ref, new_refresh)
                except Exception:  # noqa: BLE001 - the old token keeps working until it rotates
                    pass
            self._remember_access(tokens)
            return self._access_token

    # -- signing out ---------------------------------------------------------- #

    def _forget_locally(self) -> None:
        self._access_token = ""
        self._access_expires_at = 0.0
        try:
            self._store.delete(self._refresh_ref)
        except Exception:  # noqa: BLE001 - already gone is the outcome wanted
            pass
        self._save(
            ChatGptState(
                host_id=self.state.host_id,
                client_id=self.state.client_id,
                model=self.state.model,
                web_search=self.state.web_search,
            )
        )

    def forget(self) -> None:
        """Forget the sign-in on this computer only. Never touches the network.

        The client id and the host id are kept, so signing in again reuses the
        registration OpenAI already knows this app by rather than making a
        second "QUILL Lite" in the person's ChatGPT settings.
        """
        self._forget_locally()

    def sign_out(self, *, opener: Any = None) -> bool:
        """Forget locally, and ask OpenAI to revoke the refresh token too.

        Local always succeeds; remote is best effort and the result says whether
        it was confirmed, so the window can be honest about which happened.
        """
        state = self.state
        try:
            refresh = self._store.get(self._refresh_ref) or ""
        except Exception:  # noqa: BLE001 - nothing to revoke
            refresh = ""
        self._forget_locally()
        if not refresh or not state.client_id:
            return False
        try:
            from quill.core.ai.chatgpt_http import get_json

            configuration = get_json(OPENID_CONFIGURATION_URL, opener=opener)
            endpoint = str(configuration.get("revocation_endpoint", "") or "")
            if not endpoint:
                return False
            answer = self._poster(
                endpoint,
                {
                    "token": refresh,
                    "token_type_hint": "refresh_token",
                    "client_id": state.client_id,
                },
            )
            return not answer.get("error")
        except Exception:  # noqa: BLE001 - remote revocation is best effort
            return False
