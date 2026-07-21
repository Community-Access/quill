"""Tests for the headless CLI (wx-free)."""

from quill_social import cli


def test_split_command(capsys):
    rc = cli.main(["split", "one. two. three. four. five. six.", "--limit", "20"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "[1/" in out


def test_accounts_and_refresh_and_search(tmp_path, monkeypatch, capsys):
    # Point the store at a temp dir so we do not touch the real profile.
    monkeypatch.setenv("QUILLSOCIAL_DATA", str(tmp_path))
    # Seed one mock account directly through the store.
    from quill_social import paths
    from quill_social.db import SocialStore
    from quill_social.model import Account
    store = SocialStore(paths.db_path())
    store.put_account(Account(account_id="acct_mock", network="mock",
                              handle="@you", display_name="You"))
    store.close()

    assert cli.main(["accounts"]) == 0
    assert "acct_mock" in capsys.readouterr().out

    assert cli.main(["refresh", "--limit", "20"]) == 0
    assert "Refreshed" in capsys.readouterr().out

    assert cli.main(["search", "orbital"]) == 0
    assert "result" in capsys.readouterr().out


def test_version(capsys):
    try:
        cli.main(["--version"])
    except SystemExit:
        pass
    assert "QUILL Social" in capsys.readouterr().out
