"""Quillin-contributed browse sources -- radio2.md part VIII, shipped.

A Quillin that declares the browse trio (categories / stations / resolve) is a
full source in the tree, under a Quillin Sources root that only exists while
one is registered. Every contributed row passes one validator, a row may carry
a ``key`` instead of a URL and be resolved at play time (the tokenized-locator
rule), and the manifest gate that makes any of it legal -- ``stations_handler``
or nothing -- is a validation-time error, where an author reads it.
"""

from __future__ import annotations

import pytest

from quill.core.radio import browse_sources as bs
from quill.core.radio import directory_registry as registry


@pytest.fixture(autouse=True)
def _clean_registry():
    for entry in registry.browse_providers():
        registry.clear_browse_provider(entry.provider_id)
    yield
    for entry in registry.browse_providers():
        registry.clear_browse_provider(entry.provider_id)


def _register(
    provider_id: str = "ext.demo",
    *,
    categories=lambda: ["Community", "Late Night"],
    stations=None,
    resolve=None,
) -> None:
    if stations is None:

        def stations(category, query):  # noqa: ARG001
            return [
                {"name": "Community Voices FM", "url": "https://a.example/cv.mp3"},
                {"name": "Night Owl", "key": "night-owl"},
            ]

    registry.register_browse_provider(
        provider_id,
        "Community Directory",
        categories=categories,
        stations=stations,
        resolve=resolve,
    )


# --- the root exists only while somebody contributes --------------------------


def test_the_root_is_absent_until_a_provider_registers() -> None:
    roots = dict(bs.visible_roots(None))
    assert "quillins" not in roots
    _register()
    assert dict(bs.visible_roots(None))["quillins"] == "Quillin Sources"


def test_a_hidden_quillins_root_stays_hidden_even_with_providers() -> None:
    _register()
    without = tuple(s for s in dict(bs.visible_roots(None)) if s != "quillins")
    assert "quillins" not in dict(bs.visible_roots(without))


# --- browsing -----------------------------------------------------------------


def test_the_root_lists_one_folder_per_provider() -> None:
    _register("ext.one")
    _register("ext.two")
    labels = [(node.node_id, node.label) for node in bs.browse("quillins")]
    assert labels == [
        ("extdir:ext.one", "Community Directory"),
        ("extdir:ext.two", "Community Directory"),
    ]
    assert all(node.is_folder for node in bs.browse("quillins"))


def test_a_provider_with_categories_opens_into_them() -> None:
    _register()
    nodes = bs.browse("extdir:ext.demo")
    assert [node.label for node in nodes] == ["Community", "Late Night"]
    assert all(node.is_folder for node in nodes)


def test_a_provider_with_no_categories_is_flat() -> None:
    _register(categories=lambda: [])
    nodes = bs.browse("extdir:ext.demo")
    assert nodes and not any(node.is_folder for node in nodes)


def test_a_category_lists_its_stations() -> None:
    _register(resolve=lambda key: "")
    nodes = bs.browse("extdir:ext.demo\tCommunity")
    assert [node.label for node in nodes] == ["Community Voices FM", "Night Owl"]


def test_an_unknown_provider_is_an_empty_branch_not_an_error() -> None:
    assert bs.browse("extdir:ext.vanished") == []


def test_a_provider_that_raises_is_an_empty_branch_not_an_exception() -> None:
    def _boom():
        raise RuntimeError("provider bug")

    _register(categories=_boom)
    assert bs.browse("extdir:ext.demo") == []


# --- the row validator --------------------------------------------------------


def test_rows_pass_one_validator_and_junk_is_refused() -> None:
    assert registry.station_from_row("not a dict", "X") is None
    assert registry.station_from_row({"name": "No Address"}, "X") is None
    assert registry.station_from_row({"url": "https://a.example/s"}, "X") is None
    station, key = registry.station_from_row(
        {
            "name": "OK FM",
            "url": "https://a.example/ok",
            "bitrate_kbps": "128",
            "tags": ["community", ""],
            "unknown_field": "dropped",
        },
        "Community Directory",
    )
    assert station.name == "OK FM" and key == ""
    assert station.bitrate_kbps == 128
    assert station.tags == ("community",)
    assert station.source == "Community Directory"
    # Never Radio Browser's namespace -- the register_click hazard.
    assert station.station_uuid == ""


# --- the resolve step ---------------------------------------------------------


def test_a_keyed_row_is_lazy_and_resolves_at_play_time() -> None:
    _register(resolve=lambda key: f"https://a.example/{key}.mp3")
    nodes = bs.browse("extdir:ext.demo\tLate Night")
    keyed = [node for node in nodes if node.resolve_lazily]
    assert [node.node_id for node in keyed] == ["extdirstation:ext.demo\tnight-owl"]

    station = bs.resolve("extdirstation:ext.demo\tnight-owl")
    assert station is not None
    assert station.stream_url == "https://a.example/night-owl.mp3"
    assert station.source == "Community Directory"


def test_a_keyed_row_without_a_resolver_is_not_offered() -> None:
    """A row that could never play must not be a row."""
    _register(resolve=None)
    nodes = bs.browse("extdir:ext.demo\tCommunity")
    assert [node.label for node in nodes] == ["Community Voices FM"]


def test_a_resolver_that_fails_answers_none_not_an_exception() -> None:
    def _boom(_key):
        raise RuntimeError("resolve bug")

    _register(resolve=_boom)
    assert bs.resolve("extdirstation:ext.demo\tnight-owl") is None
    _register(resolve=lambda _key: "")
    assert bs.resolve("extdirstation:ext.demo\tnight-owl") is None


# --- the manifest gate --------------------------------------------------------


def test_the_browse_trio_requires_a_stations_handler() -> None:
    from quill.core.quillins.validation import validate_manifest

    manifest = {
        "schema": "quill.extension/1",
        "id": "com.example.tvdir",
        "name": "Demo",
        "version": "1.0.0",
        "author": "T",
        "description": "d",
        "targets": ["radio"],
        "capabilities": ["radio.directory"],
        "main": "extension.py",
        "contributes": {
            "directory_providers": [
                {
                    "id": "ext.demo.provider",
                    "display_name": "Demo",
                    "handler": "search",
                    "categories_handler": "cats",
                }
            ]
        },
    }
    errors = validate_manifest(manifest)
    assert any("require stations_handler" in error for error in errors)

    manifest["contributes"]["directory_providers"][0]["stations_handler"] = "stations"
    assert not [error for error in validate_manifest(manifest) if "stations_handler" in error]


def test_the_bundled_example_declares_the_trio_and_lints() -> None:
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[4]
    manifest = json.loads(
        (root / "quill/quillins_bundled/radio-community-directory/manifest.json").read_text(
            encoding="utf-8"
        )
    )
    provider = manifest["contributes"]["directory_providers"][0]
    assert provider["stations_handler"] == "directory_stations"
    assert provider["categories_handler"] == "directory_categories"
    assert provider["resolve_handler"] == "directory_resolve"
    from quill.core.quillins.validation import validate_manifest

    assert validate_manifest(manifest) == []
