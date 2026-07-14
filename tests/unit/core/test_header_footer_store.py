"""Tests for the per-document Header/Footer spec store (#892)."""

from __future__ import annotations

from pathlib import Path

from quill.core.header_footer import HeaderFooterSpec, PageNumberStyle
from quill.core.header_footer_store import HeaderFooterStore, key_for


def test_key_for_none_path_is_none() -> None:
    assert key_for(None) is None
    assert key_for("") is None


def test_key_for_real_path_is_normalized(tmp_path: Path) -> None:
    target = tmp_path / "report.md"
    key = key_for(target)
    assert key is not None
    assert key == key_for(str(target))


def test_set_and_get_round_trip(tmp_path: Path) -> None:
    store = HeaderFooterStore.load(tmp_path / "header_footer.json")
    key = key_for(tmp_path / "report.md")
    spec = HeaderFooterSpec(header_left="{title}", footer_right="{page}")
    store.set(key, spec)
    assert store.get(key) == spec


def test_set_persists_across_reload(tmp_path: Path) -> None:
    path = tmp_path / "header_footer.json"
    store = HeaderFooterStore.load(path)
    key = key_for(tmp_path / "report.md")
    spec = HeaderFooterSpec(
        header_left="{title}",
        first_page_different=True,
        page_number_style=PageNumberStyle.ROMAN,
        start_page_number=3,
    )
    store.set(key, spec)

    reloaded = HeaderFooterStore.load(path)
    got = reloaded.get(key)
    assert got == spec


def test_get_missing_key_returns_none(tmp_path: Path) -> None:
    store = HeaderFooterStore.load(tmp_path / "header_footer.json")
    assert store.get(key_for(tmp_path / "nope.md")) is None


def test_get_none_key_returns_none(tmp_path: Path) -> None:
    store = HeaderFooterStore.load(tmp_path / "header_footer.json")
    assert store.get(None) is None


def test_set_none_key_is_a_no_op(tmp_path: Path) -> None:
    store = HeaderFooterStore.load(tmp_path / "header_footer.json")
    store.set(None, HeaderFooterSpec())
    assert len(store.documents) == 0


def test_clear_removes_the_entry(tmp_path: Path) -> None:
    store = HeaderFooterStore.load(tmp_path / "header_footer.json")
    key = key_for(tmp_path / "report.md")
    store.set(key, HeaderFooterSpec(header_left="{title}"))
    store.clear(key)
    assert store.get(key) is None


def test_load_corrupt_file_starts_fresh(tmp_path: Path) -> None:
    path = tmp_path / "header_footer.json"
    path.write_text("not json", encoding="utf-8")
    store = HeaderFooterStore.load(path)
    assert len(store.documents) == 0


def test_load_missing_file_starts_fresh(tmp_path: Path) -> None:
    store = HeaderFooterStore.load(tmp_path / "does_not_exist.json")
    assert len(store.documents) == 0
