"""The live WordPress harness's pure parts, with no network and no real passwords.

``docs/qa/wordpress-live-run.py`` signs in to the test site with real
application passwords at run time; everything here uses made-up strings only
("abcd efgh ..."), and nothing reaches a network or the Credential Manager.
"""

from __future__ import annotations

import base64
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

_ROOT = Path(__file__).resolve().parents[3]
_HARNESS = _ROOT / "docs" / "qa" / "wordpress-live-run.py"
_STORE = _ROOT / "docs" / "qa" / "wordpress-test-site" / "store-passwords.py"

MADE_UP = "abcd efgh ijkl mnop qrst uvwx"


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses look their module up while the class is made
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def live() -> ModuleType:
    return _load("wordpress_live_run_under_test", _HARNESS)


@pytest.fixture(scope="module")
def store() -> ModuleType:
    return _load("store_passwords_under_test", _STORE)


# --------------------------------------------------------------------------- #
# the accounts format


def test_parse_accounts_reads_both_kinds(live: ModuleType) -> None:
    text = (
        "quill-editor sign-in password: abcd efgh\n"
        "quill-editor application password: wxyz 1234 abcd efgh\n"
        "quilladmin application password: " + MADE_UP + "\n"
    )
    found = live.parse_accounts(text)
    assert found == {
        ("quill-editor", "sign-in"): "abcd efgh",
        ("quill-editor", "application"): "wxyz 1234 abcd efgh",
        ("quilladmin", "application"): MADE_UP,
    }


def test_parse_accounts_skips_junk_and_keeps_the_last(live: ModuleType) -> None:
    text = (
        "# a comment\r\n"
        "\r\n"
        "not an account line\r\n"
        "quill-author application password:\r\n"
        "quill-author application password: abcd efgh\r\n"
        "quill-author application password: efgh abcd  \r\n"
        "quill-author fax password: abcd\r\n"
    )
    assert live.parse_accounts(text) == {("quill-author", "application"): "efgh abcd"}


def test_env_name_is_upper_with_underscores(live: ModuleType) -> None:
    assert live.env_name("quill-editor") == "QUILL_LIVE_APP_PASSWORD_QUILL_EDITOR"
    assert live.env_name("quilladmin") == "QUILL_LIVE_APP_PASSWORD_QUILLADMIN"


def test_load_passwords_falls_back_to_the_file_then_the_environment(
    live: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(live, "_keyring_getter", lambda: None)
    accounts = tmp_path / "accounts.txt"
    accounts.write_text("quill-editor application password: abcd efgh\n", encoding="utf-8")
    environ = {
        "QUILL_LIVE_ACCOUNTS": str(accounts),
        "QUILL_LIVE_APP_PASSWORD_QUILL_AUTHOR": "efgh abcd",
    }
    found = live.load_passwords(["quill-editor", "quill-author", "quilladmin"], environ)
    assert found.found == {"quill-editor": "abcd efgh", "quill-author": "efgh abcd"}
    assert found.where == {
        "quill-editor": "QUILL_LIVE_ACCOUNTS",
        "quill-author": "QUILL_LIVE_APP_PASSWORD_QUILL_AUTHOR",
    }
    assert found.missing == ["quilladmin"]
    assert "abcd" not in repr(found) and "efgh" not in repr(found)


def test_load_passwords_asks_credential_manager_first(
    live: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    asked: list[tuple[str, str]] = []

    def fake_get(service: str, user: str) -> str | None:
        asked.append((service, user))
        return "abcd efgh" if user == "quill-editor application" else None

    monkeypatch.setattr(live, "_keyring_getter", lambda: fake_get)
    found = live.load_passwords(
        ["quill-editor"], {"QUILL_LIVE_APP_PASSWORD_QUILL_EDITOR": "efgh abcd"}
    )
    assert asked == [(live.SERVICE, "quill-editor application")]
    assert found.found == {"quill-editor": "abcd efgh"}
    assert found.where == {"quill-editor": "Credential Manager"}


# --------------------------------------------------------------------------- #
# masking


def test_mask_hides_a_secret_and_its_spellings(live: ModuleType) -> None:
    forms = live.secret_forms("quill-editor", MADE_UP)
    token = base64.b64encode(f"quill-editor:{MADE_UP}".encode()).decode()
    assert MADE_UP in forms and MADE_UP.replace(" ", "") in forms and token in forms
    text = f"sent {MADE_UP} and {MADE_UP.replace(' ', '')} and {token}"
    masked = live.mask(text, forms)
    assert "abcd" not in masked and token not in masked
    assert masked.count("***") == 3


def test_mask_hides_authorization_headers_with_no_secret_known(live: ModuleType) -> None:
    samples = [
        "{'Authorization': 'Basic YWJjZDplZmdo', 'Accept': 'application/json'}",
        "Authorization: Bearer abcdefgh.ijkl-mnop",
        'headers={"authorization":"Basic YWJjZDplZmdo"}',
        "failed with Basic YWJjZDplZmdoaWpr in the log",
    ]
    for sample in samples:
        masked = live.mask(sample)
        assert "YWJjZDplZmdo" not in masked and "abcdefgh.ijkl" not in masked, masked
        assert "***" in masked
    assert "'Accept': 'application/json'" in live.mask(samples[0])


def test_mask_leaves_ordinary_sentences_alone(live: ModuleType) -> None:
    sentence = "QUILL WordPress Test Site did not accept the sign-in. Basic checks passed."
    assert live.mask(sentence, ["abcd efgh"]) == sentence


# --------------------------------------------------------------------------- #
# the results table


def test_results_count_and_group_in_area_order(live: ModuleType) -> None:
    results = live.Results()
    results.add("Forms (17a)", "63", "Publish", live.FAIL, "no form")
    results.add("Site and routes", "index", "Index", live.PASS, "802 routes")
    results.add("Forms (17a)", "68", "Lite", live.NEEDS_JEFF, "QUILL Lite", "-")
    assert results.counts() == {live.PASS: 1, live.FAIL: 1, live.NEEDS_JEFF: 1, live.NOT_RUN: 0}
    assert [area for area, _rows in results.by_area()] == ["Site and routes", "Forms (17a)"]
    assert [r.ref for r in results.failures()] == ["63"]
    with pytest.raises(ValueError):
        results.add("Forms (17a)", "1", "x", "maybe")


def test_render_section_is_one_small_table_per_area(live: ModuleType) -> None:
    results = live.Results()
    results.add("Site and routes", "index", "Index | routes", live.PASS, "a\nb")
    results.add("Checks (7)", "24", "Check", live.FAIL, "x" * 400, "quill-editor")
    text = live.render_section(results, {"Date": "2026-11-04 10:00 UTC", "Build": "abc1234"})
    assert text.startswith(live.SECTION_HEADING + "\n")
    assert "- **Build:** abc1234" in text
    assert "- **Results:** 1 pass, 1 fail, 0 needs Jeff, 0 not run" in text
    assert text.count("| Test | Check | Result | As | Detail |") == 2
    assert "Index \\| routes" in text and "| a b |" in text
    assert "| no sign-in |" in text and "| quill-editor |" in text
    long_row = next(line for line in text.splitlines() if "| 24 |" in line)
    assert long_row.endswith("... |") and len(long_row) < 330


def test_replace_section_adds_then_replaces(live: ModuleType) -> None:
    doc = "# Plan\n\n## The tests\n\nOne.\n\n## Looking after the site\n\nUpkeep.\n"
    first = live.replace_section(doc, "## Live run\n\nRun one.\n")
    assert first.index("## Live run") < first.index("## Looking after the site")
    assert "Run one." in first and first.endswith("Upkeep.\n")
    second = live.replace_section(first, "## Live run\n\nRun two.\n")
    assert "Run one." not in second and "Run two." in second
    assert second.count("## Live run") == 1 and "## Looking after the site" in second


def test_replace_section_keeps_crlf_and_appends_when_no_anchor(live: ModuleType) -> None:
    doc = "# Plan\r\n\r\nText.\r\n"
    out = live.replace_section(doc, "## Live run\n\nRun.\n")
    assert out.endswith("## Live run\r\n\r\nRun.\r\n")
    assert "\n" not in out.replace("\r\n", "")


def test_the_harness_never_names_a_real_secret_source_in_code(live: ModuleType) -> None:
    source = _HARNESS.read_text(encoding="utf-8")
    assert "test-accounts.txt" in source or "QUILL_LIVE_ACCOUNTS" in source
    assert "print(secret" not in source and "print(pw" not in source


# --------------------------------------------------------------------------- #
# store-passwords.py


def test_store_entries_use_the_harness_parser_and_the_admin_line(store: ModuleType) -> None:
    text = (
        "quill-editor sign-in password: abcd efgh\n"
        "quill-editor application password: efgh abcd ijkl\n"
        "quill-subscriber sign-in password: ijkl mnop\n"
    )
    found = store.entries_from(text, "'mnop qrst'\n")
    assert found == {
        ("quill-editor", "sign-in"): "abcd efgh",
        ("quill-editor", "application"): "efgh abcd ijkl",
        ("quill-subscriber", "sign-in"): "ijkl mnop",
        ("quilladmin", "sign-in"): "mnop qrst",
    }
    assert store.entries_from("", "") == {}


def test_store_user_names_match_what_the_harness_asks_for(store: ModuleType) -> None:
    assert store.keyring_user("quill-editor", "application") == "quill-editor application"
    assert store.keyring_user("quilladmin", "sign-in") == "quilladmin sign-in"


def test_store_prints_names_only(
    store: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    kept: dict[tuple[str, str], str] = {}
    fake = ModuleType("keyring")
    fake.set_password = lambda service, user, secret: kept.__setitem__((service, user), secret)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "keyring", fake)
    accounts = tmp_path / "accounts.txt"
    accounts.write_text("quill-author application password: abcd efgh\n", encoding="utf-8")
    assert store.main(["--file", str(accounts)]) == 0
    printed = capsys.readouterr().out
    assert "Stored quill-author application" in printed
    assert "abcd" not in printed
    assert list(kept.values()) == ["abcd efgh"]
