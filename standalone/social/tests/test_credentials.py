"""Tests for credential storage by reference and redaction (PRD 31.1)."""

from quill_social.security.credentials import (
    REDACTED,
    CredentialRef,
    InMemoryCredentialStore,
    WindowsCredentialManagerStore,
    redact,
)


def test_reference_never_contains_raw_token():
    store = InMemoryCredentialStore()
    ref = store.store("mastodon", "acct_1", "super-secret-token-value")
    # The reference and its persisted form carry no token material.
    assert "super-secret-token-value" not in str(ref.to_dict())
    assert ref.to_dict() == {
        "service": "mastodon",
        "account": "acct_1",
        "handle": "quill_social:mastodon:acct_1",
    }
    # Looking up a reference returns only the pointer, never the secret.
    looked = store.reference("mastodon", "acct_1")
    assert looked == ref
    assert "super-secret" not in str(looked.to_dict())


def test_resolve_is_the_only_secret_boundary():
    store = InMemoryCredentialStore()
    ref = store.store("bluesky", "acct_2", "app-password-abc")
    assert store.resolve(ref) == "app-password-abc"
    store.delete("bluesky", "acct_2")
    assert store.reference("bluesky", "acct_2") is None
    assert store.resolve(ref) is None


def test_ref_roundtrip():
    ref = CredentialRef(service="s", account="a", handle="h")
    assert CredentialRef.from_dict(ref.to_dict()) == ref


def test_windows_store_is_a_documented_boundary():
    # Imports and instantiates without the dependency; available() is a bool.
    store = WindowsCredentialManagerStore()
    assert isinstance(WindowsCredentialManagerStore.available(), bool)
    if not store.available():
        try:
            store.store("mastodon", "acct_1", "x")
        except RuntimeError as exc:
            assert "not available" in str(exc)
        else:
            raise AssertionError("expected RuntimeError when keyring absent")


def test_redact_masks_key_value_secrets():
    text = "access_token=abcd1234efgh5678 and password: hunter2secret"
    out = redact(text)
    assert "abcd1234efgh5678" not in out
    assert "hunter2secret" not in out
    assert REDACTED in out


def test_redact_masks_bearer_and_long_tokens():
    text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9abcdef"
    out = redact(text)
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9abcdef" not in out
    assert REDACTED in out


def test_redact_leaves_ordinary_text_alone():
    text = "Timeline focus jumps to top on refresh."
    assert redact(text) == text
