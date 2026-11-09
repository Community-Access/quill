"""The GitHub token expiry warning, once, for both editors (2026-11-08).

GitHub sends ``GitHub-Authentication-Token-Expiration`` on every API reply for a
token that expires. A token that runs out mid-week otherwise announces itself
the worst possible way: the Workbench simply stops working, with "bad
credentials" as its only explanation.

So each editor calls :func:`watch_token_expiry` at the Workbench's one gate,
with the token it is about to use. The first reply for that token (any reply:
:data:`~quill.core.github.token_health.TOKEN_EXPIRY` is fed by the REST
transport and by the items provider) settles it:

* expiring within seven days: one sentence, and a Notifications entry that opens
  Manage GitHub Accounts;
* already expired (GitHub sends no header then, so this is read from what an
  earlier reply filed): one sentence, and the same entry;
* otherwise, nothing.

At most once a day per account, remembered in the account registry
(:func:`quill.core.github.accounts.update_account_state`), so a person who
opens the Workbench ten times a day hears it once.

The sentence goes through the host's ``say``, which is each editor's
announcement service (so it is brailled too, GATE-BRAILLE). It is an outcome the
screen reader cannot know, which is what GATE-13 allows.

wx-free: the host hands in ``call_after``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path

from quill.core.github.accounts import (
    account_state,
    active_github_account,
    update_account_state,
)
from quill.core.github.token_health import (
    TOKEN_EXPIRY,
    TokenExpiryTracker,
    expiry_sentence,
    expiry_state,
    parse_expiration,
)

__all__ = [
    "GITHUB_ACCOUNTS_TARGET",
    "NOTICE_BODY",
    "ExpiryHost",
    "warn_about_expiry",
    "watch_token_expiry",
]

#: The Notifications entry's target: Manage GitHub Accounts, in either editor
#: (``open_notification_target`` in ``quill/ui/windows_dictation_transcribe.py``).
GITHUB_ACCOUNTS_TARGET = "github-accounts"

#: What the entry says under its title, which is the spoken sentence.
NOTICE_BODY = "Open this to go to Manage GitHub Accounts and sign in again."


def _now() -> datetime:
    return datetime.now(UTC)


def _today() -> str:
    return date.today().isoformat()


@dataclass(slots=True)
class ExpiryHost:
    """What the warning needs from the window whose Workbench is opening."""

    #: The editor's announcement service: speech and braille.
    say: Callable[[str], None]
    #: Run ``fn(*args)`` on the UI thread (``wx.CallAfter``).
    call_after: Callable[..., None]
    #: Who the Notifications entry says it is from.
    app_name: str = "QUILL"
    #: The editor's notifications file; ``None`` is QUILL's default store.
    notice_path: Path | None = None
    #: Called after the entry is written, so a Notifications cell can appear.
    after_notice: Callable[[], None] | None = None
    now: Callable[[], datetime] = field(default=_now)
    today: Callable[[], str] = field(default=_today)


def watch_token_expiry(
    host: ExpiryHost, token: str | None, *, tracker: TokenExpiryTracker = TOKEN_EXPIRY
) -> None:
    """UI thread, at the Workbench's gate: warn about *token*'s expiry if it is near."""
    if not token:
        return
    try:
        account = active_github_account()
        if account is None:
            return
        state = account_state(account.id)
    except Exception:  # noqa: BLE001 - the warning is never worth a failed Workbench
        return
    if state.expiry_warned_on == host.today():
        return
    filed = parse_expiration(state.expires_at)
    if filed is not None and expiry_state(filed, host.now()) == "expired":
        # A dead token's replies carry no expiry header: what was filed is all
        # there is, and the first request is about to fail anyway.
        warn_about_expiry(host, account.id, account.login, filed)
        return
    account_id, login = account.id, account.login

    def seen(value: str) -> None:  # any thread
        host.call_after(_on_seen, host, account_id, login, value)

    tracker.when_seen(token, seen)


def _on_seen(host: ExpiryHost, account_id: str, login: str, value: str) -> None:
    """UI thread: the first reply's expiry header (``""`` for a token that never expires)."""
    expires = parse_expiration(value)
    if expires is None:
        return
    try:
        update_account_state(account_id, expires_at=value)
    except Exception:  # noqa: BLE001 - filing it is a nicety
        pass
    if expiry_state(expires, host.now()) == "ok":
        return
    warn_about_expiry(host, account_id, login, expires)


def warn_about_expiry(host: ExpiryHost, account_id: str, login: str, expires: datetime) -> bool:
    """Say it and file the entry, unless it was already said today. True if said."""
    today = host.today()
    try:
        if account_state(account_id).expiry_warned_on == today:
            return False
        update_account_state(account_id, expiry_warned_on=today)
    except Exception:  # noqa: BLE001 - if it cannot be remembered, say nothing
        return False
    sentence = expiry_sentence(login, expires, host.now())
    host.say(sentence)
    try:
        from quill.core.notifications import add_notice

        add_notice(
            app=host.app_name,
            title=sentence,
            body=NOTICE_BODY,
            target=GITHUB_ACCOUNTS_TARGET,
            category="warning",
            path=host.notice_path,
        )
    except Exception:  # noqa: BLE001 - the spoken sentence already went out
        return True
    if host.after_notice is not None:
        host.after_notice()
    return True
