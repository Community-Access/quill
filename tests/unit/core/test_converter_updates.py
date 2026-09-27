"""Quill Converter's Check for Updates finds its own two downloads, and only those.

Before 1.0.0 the Converter had no entry in ``companion_install.ASSET_PREFIX``,
so the shell's update check had no prefix to match on and fell back to the
repository's newest release of any app -- QUILL's own -- and would have
offered QUILL's installer to somebody running the Converter.
"""

from __future__ import annotations

from quill.core.companion_install import ASSET_PREFIX
from quill.core.release_tags import release_tag
from quill.core.updates import _app_asset_url, _app_version_from_tag


def _asset(name: str) -> dict[str, str]:
    return {"name": name, "browser_download_url": f"https://example.invalid/{name}"}


_RELEASE = [
    _asset("QUILL-Setup-1.2.0.exe"),
    _asset("Quill-Radio-Setup-Shared-3.0.0.exe"),
    _asset("Quill-Converter-Setup-Shared-1.0.0.exe"),
    _asset("Quill-Converter-Portable-1.0.0.zip"),
]


def test_converter_and_inkwell_have_asset_prefixes() -> None:
    assert ASSET_PREFIX["converter"] == "Quill-Converter"
    assert ASSET_PREFIX["inkwell"] == "Quill-Inkwell"


def test_installed_converter_is_offered_its_own_installer() -> None:
    url = _app_asset_url(
        _RELEASE, ASSET_PREFIX["converter"], prefer_portable=False, match_edition=False
    )
    assert url.endswith("Quill-Converter-Setup-Shared-1.0.0.exe")


def test_portable_converter_is_offered_its_own_zip() -> None:
    url = _app_asset_url(
        _RELEASE, ASSET_PREFIX["converter"], prefer_portable=True, match_edition=False
    )
    assert url.endswith("Quill-Converter-Portable-1.0.0.zip")


def test_a_release_without_converter_assets_is_not_an_update() -> None:
    other = [_asset("QUILL-Setup-1.2.0.exe"), _asset("Quill-Radio-Portable-3.0.0.zip")]
    assert (
        _app_asset_url(other, ASSET_PREFIX["converter"], prefer_portable=False, match_edition=False)
        == ""
    )


def test_the_release_tag_reads_back_as_the_version() -> None:
    tag = release_tag("converter", "1.0.0")
    assert tag == "quill-converter-v1.0.0"
    assert _app_version_from_tag(tag) == "1.0.0"
