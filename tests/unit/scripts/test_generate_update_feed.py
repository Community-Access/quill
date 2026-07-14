"""Tests for the update-feed publisher (autoupdate manifest generator).

The manifest lives at ``docs/site/updates/.quill-update-feed-v1.json`` and
is what ``quill.core.updates.fetch_update_manifest`` reads at runtime.
Its ``version`` and ``download_url`` fields MUST agree with what the
InnoSetup installer actually produces; otherwise the running build never
sees the "update available" notification. These tests guard against that
drift.
"""

from __future__ import annotations

import json
from pathlib import Path

import scripts.generate_update_feed as feed_mod


def _write_version_toml(source_root: Path, *, base: str, channel: str, pre: int) -> None:
    (source_root / "build").mkdir(exist_ok=True)
    (source_root / "build" / "version.toml").write_text(
        f'base_version = "{base}"\n'
        f'channel = "{channel}"\n'
        f"prerelease_number = {pre}\n"
        'product_name = "QUILL for All"\n'
        'publisher = "Community Access"\n',
        encoding="utf-8",
    )


def test_resolve_version_reads_canonical_toml(tmp_path: Path) -> None:
    _write_version_toml(tmp_path, base="0.7.0", channel="beta", pre=2)

    assert feed_mod._resolve_version(tmp_path) == "0.7.0 Beta 2"


def test_resolve_version_falls_back_when_toml_missing(tmp_path: Path) -> None:
    init_py = tmp_path / "quill" / "__init__.py"
    init_py.parent.mkdir()
    init_py.write_text('__version__ = "1.2.3"\n', encoding="utf-8")

    assert feed_mod._resolve_version(tmp_path) == "1.2.3"


def test_resolve_product_name_falls_back_to_branding_constant(tmp_path: Path) -> None:
    # When build/version.toml is absent, the product name must come from
    # the single branding source of truth (quill.branding.APP_DISPLAY_NAME)
    # rather than a hard-coded string in this script. If the product is
    # ever rebranded, only quill/branding.py needs to change.
    from quill.branding import APP_DISPLAY_NAME

    assert feed_mod._resolve_product_name(tmp_path) == APP_DISPLAY_NAME


def test_resolve_product_name_uses_toml_value(tmp_path: Path) -> None:
    _write_version_toml(tmp_path, base="0.7.0", channel="beta", pre=1)
    # _write_version_toml writes product_name = "QUILL for All" so the
    # TOML path returns it directly.
    assert feed_mod._resolve_product_name(tmp_path) == "QUILL for All"


def test_installer_filename_matches_inno_setup() -> None:
    """The feed publisher must agree with the installer's OutputBaseFilename."""
    # The string is hard-coded so a rename on either side fails this test.
    assert feed_mod._installer_filename("0.7.0 Beta 1") == ("Quill-for-All-Setup-0.7.0 Beta 1.exe")


def test_github_release_asset_name_rewrites_space() -> None:
    """GitHub's release-asset CDN rewrites spaces in the asset filename to dots.

    The Inno Setup step keeps the space in the on-disk filename, but the URL
    the running build hits must match what GitHub serves. ``.Beta.1.exe`` is
    what the asset URL actually is for a 0.7.0 Beta 1 release.
    """
    assert (
        feed_mod._github_release_asset_name("Quill-for-All-Setup-0.7.0 Beta 1.exe")
        == "Quill-for-All-Setup-0.7.0.Beta.1.exe"
    )
    # A stable release has no space, so the helper must be a no-op.
    assert (
        feed_mod._github_release_asset_name("Quill-for-All-Setup-0.7.0.exe")
        == "Quill-for-All-Setup-0.7.0.exe"
    )


def test_build_payload_derives_url_from_toml(tmp_path: Path) -> None:
    _write_version_toml(tmp_path, base="0.7.0", channel="beta", pre=1)

    payload = feed_mod.build_payload(source_root=tmp_path, tag="v0.7.0-beta.1")

    assert payload["version"] == "0.7.0 Beta 1"
    # GitHub's release-asset CDN rewrites the space in the installer filename
    # to a dot, so the URL we point users at must match what GitHub serves
    # (not what Inno Setup wrote to disk).
    assert payload["download_url"].endswith("/v0.7.0-beta.1/Quill-for-All-Setup-0.7.0.Beta.1.exe")
    assert payload["signature"]


def test_build_payload_accepts_explicit_overrides(tmp_path: Path) -> None:
    payload = feed_mod.build_payload(
        version="0.7.0",
        download_url="https://example.com/custom.exe",
        notes="Fixes.",
        published_at="2026-06-19T00:00:00Z",
    )

    assert payload["version"] == "0.7.0"
    assert payload["download_url"] == "https://example.com/custom.exe"
    assert payload["notes"] == "Fixes."
    assert payload["published_at"] == "2026-06-19T00:00:00Z"


def test_signature_matches_canonical_form(tmp_path: Path) -> None:
    payload = feed_mod.build_payload(
        version="1.0.0",
        download_url="https://example.com/setup.exe",
        notes="release",
        published_at="2026-06-19T00:00:00Z",
    )

    expected = feed_mod._signature_for({
        "version": "1.0.0",
        "download_url": "https://example.com/setup.exe",
        "published_at": "2026-06-19T00:00:00Z",
        "notes": "release",
    })
    assert payload["signature"] == expected


def test_main_writes_feed_file(tmp_path: Path, monkeypatch) -> None:
    _write_version_toml(tmp_path, base="0.7.0", channel="beta", pre=1)
    output = tmp_path / "feed.json"

    monkeypatch.setattr(
        "sys.argv",
        [
            "generate_update_feed",
            "--output",
            str(output),
            "--source-root",
            str(tmp_path),
            "--tag",
            "v0.7.0-beta.1",
        ],
    )
    rc = feed_mod.main()

    assert rc == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["version"] == "0.7.0 Beta 1"
    assert payload["download_url"].endswith("/v0.7.0-beta.1/Quill-for-All-Setup-0.7.0.Beta.1.exe")
    assert payload["signature"]
