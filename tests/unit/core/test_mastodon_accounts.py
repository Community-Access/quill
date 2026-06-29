from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.mastodon import accounts


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, str]:
    """Isolate the data dir and back the secret store with an in-memory dict."""
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    secrets: dict[str, str] = {}
    monkeypatch.setattr(
        accounts, "save_secret", lambda name, value: secrets.__setitem__(name, value)
    )
    monkeypatch.setattr(accounts, "load_secret", lambda name: secrets.get(name, ""))
    monkeypatch.setattr(
        accounts, "delete_secret", lambda name: bool(secrets.pop(name, None) is not None)
    )
    return secrets


def _add(
    nickname: str, instance: str = "https://mastodon.social", handle: str = ""
) -> accounts.MastodonAccount:
    return accounts.add_account(
        nickname=nickname,
        instance_url=instance,
        handle=handle or f"@{nickname}@mastodon.social",
        client_id="cid",
        client_secret="csecret",
        access_token=f"token-{nickname}",
    )


def test_add_stores_metadata_in_json_and_secrets_in_store(store: dict[str, str]) -> None:
    account = _add("Main")
    listed = accounts.list_accounts()
    assert [a.nickname for a in listed] == ["Main"]
    # Token retrievable from the secret store, not the JSON.
    assert accounts.access_token_for(account.id) == "token-Main"
    # The metadata file must not contain the secret or the client secret.
    on_disk = Path(str(accounts.accounts_path())).read_text(encoding="utf-8")
    assert "token-Main" not in on_disk
    assert "csecret" not in on_disk


def test_first_account_becomes_default(store: dict[str, str]) -> None:
    first = _add("Main")
    _add("Alt")
    assert accounts.default_account_id() == first.id


def test_set_default_and_display_name(store: dict[str, str]) -> None:
    _add("Main")
    alt = _add("Alt")
    accounts.set_default_account(alt.id)
    assert accounts.default_account_id() == alt.id
    assert accounts.get_account(alt.id).display_name == "Alt (@Alt@mastodon.social)"


def test_remove_deletes_metadata_secrets_and_reassigns_default(store: dict[str, str]) -> None:
    first = _add("Main")
    second = _add("Alt")
    accounts.remove_account(first.id)
    remaining = accounts.list_accounts()
    assert [a.id for a in remaining] == [second.id]
    assert accounts.access_token_for(first.id) == ""  # secret gone
    assert accounts.default_account_id() == second.id  # default reassigned


def test_display_name_without_handle_is_just_the_nickname(store: dict[str, str]) -> None:
    account = accounts.add_account(
        nickname="Plain",
        instance_url="https://mastodon.social",
        handle="",
        client_id="cid",
        client_secret="csecret",
        access_token="tok",
    )
    assert account.display_name == "Plain"


def test_accounts_file_carries_a_schema_version(store: dict[str, str]) -> None:
    import json as _json

    _add("Main")
    raw = _json.loads(Path(str(accounts.accounts_path())).read_text(encoding="utf-8"))
    assert raw["schema_version"] == 1
    # An older unversioned file (no schema_version) still loads.
    Path(str(accounts.accounts_path())).write_text(
        _json.dumps({"accounts": raw["accounts"], "default_id": raw["default_id"]}),
        encoding="utf-8",
    )
    assert [a.nickname for a in accounts.list_accounts()] == ["Main"]


def test_spell_check_before_post_defaults_off(store: dict[str, str]) -> None:
    account = _add("Main")
    assert account.spell_check_before_post is False
    assert accounts.list_accounts()[0].spell_check_before_post is False


def test_set_spell_check_before_post_toggles_and_persists(store: dict[str, str]) -> None:
    account = _add("Main")
    accounts.set_spell_check_before_post(account.id, True)
    assert accounts.get_account(account.id).spell_check_before_post is True
    accounts.set_spell_check_before_post(account.id, False)
    assert accounts.get_account(account.id).spell_check_before_post is False


def test_add_account_can_enable_pre_post_review(store: dict[str, str]) -> None:
    account = accounts.add_account(
        nickname="Pre",
        instance_url="https://mastodon.social",
        handle="@pre@mastodon.social",
        client_id="cid",
        client_secret="csecret",
        access_token="tok",
        spell_check_before_post=True,
    )
    assert accounts.get_account(account.id).spell_check_before_post is True


def test_existing_account_without_field_migrates_to_off(store: dict[str, str]) -> None:
    import json as _json
    from pathlib import Path

    # Simulate an account saved before the field existed (opt-in migration).
    Path(str(accounts.accounts_path())).write_text(
        _json.dumps({
            "schema_version": 1,
            "accounts": [
                {
                    "id": "abc123",
                    "nickname": "Legacy",
                    "instance_url": "https://mastodon.social",
                    "handle": "@legacy@mastodon.social",
                    "client_id": "cid",
                }
            ],
            "default_id": "abc123",
        }),
        encoding="utf-8",
    )
    account = accounts.get_account("abc123")
    assert account is not None
    assert account.spell_check_before_post is False
