"""People > My Keys: your SSH keys, GPG keys and SSH signing keys (GitHub PRD 14.3).

GitHub keeps three kinds of key for you: SSH keys that let git push and pull
over SSH, GPG keys and SSH signing keys that mark your commits Verified. All
three are listed together, one sentence each, so a screen reader hears what a
sighted user reads off the settings page, and the fingerprint is said so a key
can be checked against the one on your computer:

* "SSH key Laptop, ED25519, SHA256:abc..., added 2025-01-02, last used
  2026-11-17."
* "GPG key 3AA5C34371567BD2, for jeff@example.org, signs commits, expires
  2027-01-01."
* "SSH signing key Laptop, ED25519, SHA256:abc..., added 2025-01-02."

**New Here** adds a key, read from a ``.pub`` or ``.asc`` file or pasted;
**Delete Key...** removes one after asking, saying what stops working.

Takes the Workbench's :class:`~quill.core.github.workbench_api.GitHubApi`.
wx-free and strict-typed.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
from collections.abc import Mapping
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.github.explore_models import ExploreRow
from quill.core.github.rest_transport import GitHubRestError
from quill.core.github.workbench_api import GitHubApi

__all__ = [
    "KINDS",
    "AccountKeyError",
    "add_key",
    "delete_key",
    "fetch_keys",
    "fingerprint",
    "key_kind",
]

#: Each kind: (key in rows, the words for it, its REST path, the scope it needs).
KINDS: dict[str, tuple[str, str, str]] = {
    "ssh": ("SSH key", "/user/keys", "admin:public_key"),
    "gpg": ("GPG key", "/user/gpg_keys", "admin:gpg_key"),
    "signing": ("SSH signing key", "/user/ssh_signing_keys", "admin:ssh_signing_key"),
}

_SSH_TYPES = {
    "ssh-ed25519": "ED25519",
    "ssh-rsa": "RSA",
    "ecdsa-sha2-nistp256": "ECDSA",
    "ecdsa-sha2-nistp384": "ECDSA",
    "ecdsa-sha2-nistp521": "ECDSA",
    "sk-ssh-ed25519@openssh.com": "ED25519 security key",
    "sk-ecdsa-sha2-nistp256@openssh.com": "ECDSA security key",
}


class AccountKeyError(CodedError):
    """A key could not be read, added or deleted; the message is said."""

    code = "QUILL-GITHUB-ACCOUNT-KEYS"


def fingerprint(public_key: str) -> str:
    """OpenSSH's ``SHA256:...`` fingerprint of an SSH public key, or "" if it is not one."""
    parts = public_key.split()
    if len(parts) < 2:
        return ""
    try:
        blob = base64.b64decode(parts[1], validate=True)
    except (binascii.Error, ValueError):
        return ""
    digest = base64.b64encode(hashlib.sha256(blob).digest()).decode("ascii").rstrip("=")
    return f"SHA256:{digest}"


def key_kind(text: str) -> str:
    """ "ssh" for an OpenSSH public key, "gpg" for an armored PGP key, else ""."""
    stripped = text.strip()
    if stripped.startswith("-----BEGIN PGP PUBLIC KEY BLOCK-----"):
        return "gpg"
    first = stripped.split(" ", 1)[0]
    return "ssh" if first in _SSH_TYPES else ""


def _date(value: object) -> str:
    return str(value or "")[:10]


def _ssh_row(kind: str, raw: Mapping[str, Any]) -> ExploreRow:
    words = KINDS[kind][0]
    key = str(raw.get("key") or "")
    algorithm = _SSH_TYPES.get(key.split(" ", 1)[0], "")
    parts = [p for p in (algorithm, fingerprint(key)) if p]
    if raw.get("created_at"):
        parts.append(f"added {_date(raw['created_at'])}")
    if raw.get("last_used"):
        parts.append(f"last used {_date(raw['last_used'])}")
    elif kind == "ssh":
        parts.append("never used")
    if raw.get("read_only") is False:
        parts.append("read and write")
    label = f"{words} {raw.get('title') or 'untitled'}, {', '.join(parts)}."
    url = "https://github.com/settings/keys"
    return ExploreRow(label, f"{label}\n{key}\n{url}", url, "", "key", f"{kind}:{raw.get('id')}")


def _gpg_row(raw: Mapping[str, Any]) -> ExploreRow:
    emails = [
        str(e.get("email"))
        for e in raw.get("emails") or ()
        if isinstance(e, Mapping) and e.get("email")
    ]
    parts = [f"for {', '.join(emails)}" if emails else "with no email"]
    if raw.get("can_sign"):
        parts.append("signs commits")
    if raw.get("expires_at"):
        parts.append(f"expires {_date(raw['expires_at'])}")
    if raw.get("revoked"):
        parts.append("revoked")
    name = str(raw.get("name") or raw.get("key_id") or "")
    label = f"GPG key {name}, {', '.join(parts)}."
    url = "https://github.com/settings/keys"
    detail = f"{label}\nKey ID {raw.get('key_id') or ''}\n{url}"
    return ExploreRow(label, detail, url, "", "key", f"gpg:{raw.get('id')}")


def _refused(exc: GitHubRestError, doing: str, kind: str) -> AccountKeyError:
    if exc.status in (401, 403, 404):
        return AccountKeyError(
            f"GitHub refused to {doing}: it needs the {KINDS[kind][2]} permission. Sign in "
            "with GitHub again, from Manage GitHub Accounts, to grant it."
        )
    if exc.status == 422:
        return AccountKeyError(
            f"GitHub refused the key: it may already be on an account, or it is not a "
            f"public {KINDS[kind][0]}. {exc}"
        )
    return AccountKeyError(f"Could not {doing}: {exc}")


def fetch_keys(api: GitHubApi, warnings: list[str] | None = None) -> list[ExploreRow]:
    """Every key of yours, SSH, GPG and signing; a kind refused is a warning, not a failure."""
    rows: list[ExploreRow] = []
    for kind, (words, path, _scope) in KINDS.items():
        try:
            data = api.rest("GET", path, query={"per_page": "100"}).data
        except GitHubRestError as exc:
            if warnings is None:
                raise _refused(exc, f"list your {words}s", kind) from exc
            warnings.append(str(_refused(exc, f"list your {words}s", kind).args[0]))
            continue
        for raw in data or ():
            if isinstance(raw, Mapping):
                rows.append(_gpg_row(raw) if kind == "gpg" else _ssh_row(kind, raw))
    return rows


def add_key(api: GitHubApi, kind: str, title: str, text: str) -> str:
    """Add a key of *kind*; returns the sentence to say."""
    if kind not in KINDS:
        raise AccountKeyError(f"{kind} is not a kind of key.")
    words, path, _scope = KINDS[kind]
    found = key_kind(text)
    wanted = "gpg" if kind == "gpg" else "ssh"
    if found != wanted:
        what = "an armored GPG public key" if wanted == "gpg" else "an SSH public key"
        raise AccountKeyError(
            f"That is not {what}. Use the .pub or .asc file, never a private key."
        )
    if "PRIVATE KEY" in text:
        raise AccountKeyError("That is a private key. Never share it; add the public one instead.")
    body: dict[str, object] = (
        {"armored_public_key": text.strip(), "name": title.strip()}
        if kind == "gpg"
        else {"title": title.strip() or "QUILL", "key": text.strip()}
    )
    try:
        api.rest("POST", path, body=body)
    except GitHubRestError as exc:
        raise _refused(exc, f"add the {words}", kind) from exc
    print_ = f", {fingerprint(text)}" if kind != "gpg" else ""
    return f"Added {words} {title.strip() or 'QUILL'}{print_}."


def delete_key(api: GitHubApi, row_key: str) -> str:
    kind, _, number = row_key.partition(":")
    if kind not in KINDS or not number.isdigit():
        raise AccountKeyError(f"{row_key} is not one of your keys.")
    words, path, _scope = KINDS[kind]
    try:
        api.rest("DELETE", f"{path}/{number}")
    except GitHubRestError as exc:
        raise _refused(exc, f"delete the {words}", kind) from exc
    return f"Deleted the {words}."
