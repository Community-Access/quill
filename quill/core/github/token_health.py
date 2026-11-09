"""What a GitHub token says about itself: classic or not, how broad, when it expires.

Two things Manage GitHub Accounts and the Workbench say since 2026-11-08 are
decided here, without wx:

* **The sign-in suggestion.** An account added with a *classic* token (one
  that starts ``ghp_``, or one GitHub answers with an ``X-OAuth-Scopes``
  header) that has broad scopes is the kind somebody made by hand long ago and
  has to remake by hand when it runs out. :func:`should_suggest_sign_in` says
  whether to suggest Sign In with GitHub instead -- once per account, never for
  an account that signed in, and never for a fine-grained token, which is the
  one people choose on purpose.
* **The expiry warning.** GitHub sends ``GitHub-Authentication-Token-Expiration``
  on every API reply for a token that expires. :data:`TOKEN_EXPIRY` is the
  process-wide record of what it said, fed by the REST transport and by the
  items provider the way :data:`~quill.core.github.rate_limits.RATE_LIMITS` is,
  and :func:`expiry_sentence` is what is said about it.

The tracker never stores a token: a token is reduced to a short SHA-256
fingerprint, in memory only, so a waiter can be matched to the token it is about.

No ``wx`` imports; strict-typed.
"""

from __future__ import annotations

import hashlib
import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

__all__ = [
    "BROAD_SCOPES",
    "EXPIRY_HEADER",
    "EXPIRY_WARNING_DAYS",
    "SCOPES_HEADER",
    "SUGGEST_SIGN_IN",
    "TOKEN_EXPIRY",
    "TokenExpiryTracker",
    "expiry_sentence",
    "expiry_state",
    "fingerprint",
    "has_broad_scopes",
    "header_value",
    "is_classic_token",
    "parse_expiration",
    "parse_scopes",
    "should_suggest_sign_in",
]

#: The headers GitHub sends about the token itself (lower-cased lookups work too).
SCOPES_HEADER = "X-OAuth-Scopes"
EXPIRY_HEADER = "GitHub-Authentication-Token-Expiration"

#: How far ahead an expiry is worth mentioning.
EXPIRY_WARNING_DAYS = 7

#: The one sentence Manage GitHub Accounts says, once per account.
SUGGEST_SIGN_IN = "This account uses a token. Sign In with GitHub is easier to keep up to date."

#: Scopes that reach well past reading: whole repositories, organizations,
#: workflows, packages, keys, or the account itself. A token holding any of
#: them is a broad one; ``read:org`` or ``gist`` alone is not.
BROAD_SCOPES = frozenset({
    "repo",
    "workflow",
    "delete_repo",
    "write:packages",
    "delete:packages",
    "admin:org",
    "write:org",
    "admin:repo_hook",
    "admin:org_hook",
    "admin:public_key",
    "admin:gpg_key",
    "admin:ssh_signing_key",
    "admin:enterprise",
    "user",
    "project",
    "codespace",
})

_CLASSIC_PREFIX = "ghp_"
#: Prefixes that are never a hand-made classic token: OAuth (Sign In with
#: GitHub, or the GitHub CLI) and fine-grained personal access tokens.
_NOT_CLASSIC_PREFIXES = ("gho_", "github_pat_", "ghu_", "ghs_")


def header_value(headers: object, name: str) -> str | None:
    """*name*'s value in any header container, or ``None`` when it is absent.

    ``""`` and ``None`` are different answers: GitHub sends an *empty*
    ``X-OAuth-Scopes`` for a classic token with no scopes, and no header at all
    for a fine-grained one.
    """
    if headers is None:
        return None
    getter = getattr(headers, "get", None)
    if not callable(getter):
        return None
    for key in (name, name.casefold()):
        try:
            value = getter(key)
        except Exception:  # noqa: BLE001 - header containers vary by client
            value = None
        if isinstance(value, str):
            return value
        if isinstance(value, bytes):
            return value.decode("latin-1")
    return None


def parse_scopes(value: str | None) -> tuple[str, ...] | None:
    """``"repo, workflow"`` as ``("repo", "workflow")``; ``None`` stays ``None``."""
    if value is None:
        return None
    return tuple(part.strip() for part in value.split(",") if part.strip())


def has_broad_scopes(scopes: tuple[str, ...] | None) -> bool:
    """Whether any scope reaches past reading (see :data:`BROAD_SCOPES`)."""
    return bool(scopes) and any(
        scope in BROAD_SCOPES or scope.startswith("admin:") for scope in scopes or ()
    )


def is_classic_token(token: str, scopes_header: str | None, added_by: str) -> bool:
    """A classic personal access token: ``ghp_``, or scopes reported for a pasted one.

    The header alone is not enough for an account of unknown origin, because
    GitHub reports scopes for OAuth tokens too, and every account saved before
    2026-11-08 is of unknown origin.
    """
    value = (token or "").strip()
    if value.startswith(_CLASSIC_PREFIX):
        return True
    if value.startswith(_NOT_CLASSIC_PREFIXES):
        return False
    return added_by == "token" and scopes_header is not None


def should_suggest_sign_in(
    *, token: str, scopes_header: str | None, added_by: str, already_shown: bool
) -> bool:
    """Suggest Sign In with GitHub for this account now? Once, and never forced."""
    if already_shown or added_by == "sign_in":
        return False
    if not is_classic_token(token, scopes_header, added_by):
        return False
    return has_broad_scopes(parse_scopes(scopes_header))


def parse_expiration(value: str | None) -> datetime | None:
    """GitHub's expiry header as an aware UTC datetime, or ``None``.

    GitHub writes ``2026-11-12 18:30:00 UTC``; the ``-0700`` offset form
    appears in some replies and in GitHub's own documentation, so both are read.
    """
    text = (value or "").strip()
    if not text:
        return None
    for pattern in ("%Y-%m-%d %H:%M:%S %Z", "%Y-%m-%d %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            moment = datetime.strptime(text, pattern)
        except ValueError:
            continue
        return moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment.astimezone(UTC)
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment.astimezone(UTC)


def expiry_state(expires_at: datetime | None, now: datetime) -> str:
    """``"expired"``, ``"soon"`` (within :data:`EXPIRY_WARNING_DAYS`), or ``"ok"``."""
    if expires_at is None:
        return "ok"
    if expires_at <= now:
        return "expired"
    if expires_at - now <= timedelta(days=EXPIRY_WARNING_DAYS):
        return "soon"
    return "ok"


def expiry_sentence(login: str, expires_at: datetime, now: datetime) -> str:
    """The one sentence said about an expiring or expired token."""
    who = f"Your GitHub token for {login}" if login else "Your GitHub token"
    if expires_at <= now:
        return f"{who} has expired."
    left = expires_at - now
    if left < timedelta(days=1):
        return f"{who} expires in less than a day."
    days = left.days
    if days == 1:
        return f"{who} expires tomorrow."
    return f"{who} expires in {days} days."


def fingerprint(token: str) -> str:
    """A short, one-way name for *token*, never written anywhere."""
    return hashlib.sha256(token.strip().encode("utf-8")).hexdigest()[:16]


#: ``waiter(header_value)``: the raw expiry header, ``""`` when the reply had none.
Waiter = Callable[[str], None]


class TokenExpiryTracker:
    """The last expiry header seen per token, and one-shot waiters for the next.

    :meth:`observe` is called by the transports on every reply (any thread).
    :meth:`when_seen` hands a waiter what the *first* reply for a token said:
    at once if a reply has already been seen in this process, otherwise as soon
    as one arrives. Each waiter runs once.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._seen: dict[str, str] = {}
        self._waiters: dict[str, list[Waiter]] = {}

    def reset(self) -> None:
        with self._lock:
            self._seen.clear()
            self._waiters.clear()

    def observe(self, token: str | None, headers: object) -> None:
        """Remember what one reply said about *token*'s expiry."""
        if not token:
            return
        key = fingerprint(token)
        value = header_value(headers, EXPIRY_HEADER) or ""
        with self._lock:
            self._seen[key] = value
            waiters = self._waiters.pop(key, [])
        for waiter in waiters:
            try:
                waiter(value)
            except Exception:  # noqa: BLE001 - a waiter never breaks a request
                pass

    def seen(self, token: str) -> str | None:
        """The last expiry header for *token*: ``""`` for none, ``None`` if no reply yet."""
        with self._lock:
            return self._seen.get(fingerprint(token))

    def when_seen(self, token: str, waiter: Waiter) -> None:
        """Run *waiter* with what the first reply for *token* said."""
        if not token:
            return
        key = fingerprint(token)
        with self._lock:
            value = self._seen.get(key)
            if value is None:
                self._waiters.setdefault(key, []).append(waiter)
                return
        waiter(value)


TOKEN_EXPIRY = TokenExpiryTracker()
"""The process-wide tracker every Workbench request reports into."""
