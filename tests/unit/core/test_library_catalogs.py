"""Catalogues you add yourself -- the payoff for building on OPDS.

The two rules worth pinning are the ones a quieter implementation would get
wrong: a plain-HTTP catalogue is allowed but *says so*, and removing a built-in
switches it off rather than pretending to delete something that will be back
after the next launch.
"""

from __future__ import annotations

import pytest

from quill.core.library.catalogs import (
    BUILTIN_CATALOGS,
    Catalog,
    add,
    enabled_urls,
    is_supported_url,
    load,
    remove,
    save,
)


def test_the_built_ins_are_there_before_anything_is_added(tmp_path) -> None:
    names = [catalog.id for catalog in load(tmp_path)]
    assert set(BUILTIN_CATALOGS) <= set(names)


def test_a_catalog_on_a_home_network_is_allowed_and_says_it_is_not_encrypted() -> None:
    # Refusing plain HTTP would rule out the personal-library case this feature
    # mostly exists for. A quiet downgrade would be worse than either.
    catalogs: list[Catalog] = []
    added = add(catalogs, name="My Calibre", url="http://192.168.1.5:8080/opds")
    assert added is not None
    assert added.is_encrypted is False
    assert "not an encrypted connection" in added.display


def test_an_https_catalog_says_nothing_extra() -> None:
    catalogs: list[Catalog] = []
    added = add(catalogs, name="A Library", url="https://library.example/opds")
    assert added is not None
    assert added.display == "A Library"


@pytest.mark.parametrize(
    "url", ["", "   ", "file:///etc/passwd", "/home/me/books", "ftp://x/y", "https://"]
)
def test_an_address_that_is_not_a_web_address_is_refused(url: str) -> None:
    # A catalogue address must not become a way to read the disk.
    assert is_supported_url(url) is False
    assert add([], name="Nope", url=url) is None


def test_the_same_catalog_is_not_added_twice() -> None:
    catalogs: list[Catalog] = []
    assert add(catalogs, name="A", url="https://x.example/opds") is not None
    assert add(catalogs, name="A again", url="https://x.example/opds/") is None
    assert len(catalogs) == 1


def test_removing_a_built_in_switches_it_off_and_says_which_it_did(tmp_path) -> None:
    catalogs = load(tmp_path)
    built_in = next(c for c in catalogs if c.id in BUILTIN_CATALOGS)
    assert remove(catalogs, built_in.id) is False  # switched off, not removed
    assert built_in.enabled is False
    assert "switched off" in built_in.display
    assert built_in in catalogs


def test_removing_one_that_was_added_really_removes_it(tmp_path) -> None:
    catalogs = load(tmp_path)
    added = add(catalogs, name="Mine", url="https://mine.example/opds")
    assert added is not None
    assert remove(catalogs, added.id) is True
    assert added not in catalogs


def test_a_switched_off_catalog_is_not_searched() -> None:
    catalogs = [
        Catalog(id="on", name="On", url="https://on.example"),
        Catalog(id="off", name="Off", url="https://off.example", enabled=False),
    ]
    assert enabled_urls(catalogs) == {"on": "https://on.example"}


def test_a_choice_survives_a_restart(tmp_path) -> None:
    catalogs = load(tmp_path)
    add(catalogs, name="Mine", url="https://mine.example/opds")
    remove(catalogs, "standard-ebooks")  # switches it off
    save(tmp_path, catalogs)

    reloaded = load(tmp_path)
    assert any(c.name == "Mine" for c in reloaded)
    assert next(c for c in reloaded if c.id == "standard-ebooks").enabled is False


def test_a_damaged_file_reads_as_the_built_ins_rather_than_nothing(tmp_path) -> None:
    (tmp_path / "library_catalogs.json").write_text("{not json", encoding="utf-8")
    assert {c.id for c in load(tmp_path)} == set(BUILTIN_CATALOGS)
