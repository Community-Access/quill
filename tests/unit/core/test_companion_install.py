"""Resolving and obtaining a not-yet-installed sibling app (companion install)."""

from __future__ import annotations

import sys

from quill.core import companion_install as ci


def _releases_fixture() -> list[dict]:
    # Newest-first, like the GitHub Releases API. A mix of apps and asset kinds.
    return [
        {
            "tag_name": "quill-weather-v2.2.0",
            "assets": [
                {
                    "name": "Quill-Weather-Setup-2.2.0.exe",
                    "browser_download_url": "https://github.com/Community-Access/quill/releases/download/quill-weather-v2.2.0/Quill-Weather-Setup-2.2.0.exe",
                },
                {
                    "name": "Quill-Weather-Portable-2.2.0.zip",
                    "browser_download_url": "https://github.com/Community-Access/quill/releases/download/quill-weather-v2.2.0/Quill-Weather-Portable-2.2.0.zip",
                },
            ],
        },
        {
            "tag_name": "quill-radio-v2.2.0",
            "assets": [
                {
                    "name": "Quill-Radio-Setup-2.2.0.exe",
                    "browser_download_url": "https://github.com/Community-Access/quill/releases/download/quill-radio-v2.2.0/Quill-Radio-Setup-2.2.0.exe",
                },
                {
                    "name": "Quill-Radio-Portable-2.2.0.zip",
                    "browser_download_url": "https://github.com/Community-Access/quill/releases/download/quill-radio-v2.2.0/Quill-Radio-Portable-2.2.0.zip",
                },
            ],
        },
    ]


def test_resolve_installer_asset_by_app_and_kind() -> None:
    got = ci.resolve_companion_asset("weather", _releases_fixture(), portable=False)
    assert got is not None
    assert got.app_key == "weather"
    assert got.kind == "installer"
    assert got.filename == "Quill-Weather-Setup-2.2.0.exe"
    assert got.url.endswith("Quill-Weather-Setup-2.2.0.exe")
    assert got.version == "2.2.0" or got.version.endswith("2.2.0")


def test_resolve_portable_asset_when_portable() -> None:
    got = ci.resolve_companion_asset("radio", _releases_fixture(), portable=True)
    assert got is not None
    assert got.kind == "portable"
    assert got.filename == "Quill-Radio-Portable-2.2.0.zip"


def test_resolve_is_cross_app_both_directions() -> None:
    # Radio-in-Weather and Weather-in-Radio resolve to the OTHER app's asset.
    weather = ci.resolve_companion_asset("weather", _releases_fixture(), portable=False)
    radio = ci.resolve_companion_asset("radio", _releases_fixture(), portable=False)
    assert weather is not None and radio is not None
    assert "Weather" in weather.filename and "Radio" in radio.filename


def test_resolve_ignores_drafts_and_non_https() -> None:
    releases = [
        {
            "draft": True,
            "assets": [
                {
                    "name": "Quill-Weather-Setup-9.9.9.exe",
                    "browser_download_url": "https://x/Quill-Weather-Setup-9.9.9.exe",
                }
            ],
        },
        {
            "assets": [
                {
                    "name": "Quill-Weather-Setup-2.2.0.exe",
                    "browser_download_url": "http://insecure/Quill-Weather-Setup-2.2.0.exe",
                }
            ]
        },
    ]
    assert ci.resolve_companion_asset("weather", releases, portable=False) is None


def test_resolve_unknown_app_or_bad_payload_is_none() -> None:
    assert ci.resolve_companion_asset("nope", _releases_fixture(), portable=False) is None
    assert ci.resolve_companion_asset("weather", {"not": "a list"}, portable=False) is None
    assert ci.resolve_companion_asset("weather", [], portable=True) is None


def test_can_offer_download_requires_frozen(monkeypatch) -> None:
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    assert ci.can_offer_download("weather") is False  # from source, -m already runs it
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert ci.can_offer_download("weather") is True
    assert ci.can_offer_download("nope") is False


def test_release_page_url_points_at_the_quill_repo() -> None:
    assert ci.release_page_url() == "https://github.com/Community-Access/quill/releases"
