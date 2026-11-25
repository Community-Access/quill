"""The one release catalogue for every Windows QuillVille product.

Versions, build scripts, feed entries, sibling checks and the family build
command must all agree with this list. A new standalone wrapper is not a
release product until it is named here; a held product may have no installer
yet, but it cannot disappear silently from the maintenance inventory.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

ReleaseWave = Literal["platform", "companion", "later", "held"]


@dataclass(frozen=True, slots=True)
class ReleaseProduct:
    """One product's source and release identity."""

    key: str
    name: str
    tag_prefix: str
    asset_prefix: str
    version_file: str
    version_constant: str
    build_file: str
    build_constant: str
    changelog: str
    build_entry: str = ""
    wave: ReleaseWave = "held"
    shared_runtime: bool = True
    wrapper: str = ""

    @property
    def buildable(self) -> bool:
        return bool(self.build_entry)


PRODUCTS: tuple[ReleaseProduct, ...] = (
    ReleaseProduct(
        "quill",
        "QUILL",
        "v",
        "Quill",
        "quill/__init__.py",
        "__version__",
        "quill/__init__.py",
        "__build__",
        "CHANGELOG.md",
        "scripts/build_windows_distribution.py",
        "platform",
        False,
    ),
    ReleaseProduct(
        "quilllite",
        "QUILL Lite",
        "quill-lite-v",
        "QuillLite",
        "quill/core/lite/__init__.py",
        "APP_VERSION",
        "quill/core/lite/__init__.py",
        "APP_BUILD",
        "standalone/quilllite/docs/CHANGELOG.md",
        "standalone/quilllite/scripts/build_release.ps1",
        "platform",
        True,
        "standalone/quilllite",
    ),
    ReleaseProduct(
        "radio",
        "Quill Radio",
        "quill-radio-v",
        "Quill-Radio",
        "quill/apps/radio.py",
        "_VERSION",
        "quill/apps/radio.py",
        "_BUILD",
        "standalone/radio/docs/CHANGELOG.md",
        "standalone/radio/scripts/build_release.ps1",
        "platform",
        True,
        "standalone/radio",
    ),
    ReleaseProduct(
        "cast",
        "QUILL Cast",
        "quill-cast-v",
        "Quill-Cast",
        "quill/apps/podcasts_menu.py",
        "APP_VERSION",
        "quill/apps/podcasts_menu.py",
        "APP_BUILD",
        "standalone/cast/docs/CHANGELOG.md",
        "standalone/cast/scripts/build_release.ps1",
        "platform",
        True,
        "standalone/cast",
    ),
    ReleaseProduct(
        "transcribe",
        "QUILL Transcribe",
        "quill-transcribe-v",
        "QUILL-Transcribe",
        "quill/apps/transcribe.py",
        "_VERSION",
        "quill/apps/transcribe.py",
        "_BUILD",
        "standalone/transcribe/docs/CHANGELOG.md",
        "standalone/transcribe/scripts/build_release.ps1",
        "platform",
        True,
        "standalone/transcribe",
    ),
    ReleaseProduct(
        "converter",
        "Quill Converter",
        "quill-converter-v",
        "Quill-Converter",
        "quill/apps/converter.py",
        "_VERSION",
        "quill/apps/converter.py",
        "_BUILD",
        "standalone/converter/docs/CHANGELOG.md",
        "standalone/converter/scripts/build_release.ps1",
        "platform",
        True,
        "standalone/converter",
    ),
    ReleaseProduct(
        "studio",
        "QUILL Studio",
        "quill-studio-v",
        "QUILL-Audio-Studio",
        "quill/apps/studio.py",
        "_VERSION",
        "quill/apps/studio.py",
        "_BUILD",
        "standalone/studio/docs/CHANGELOG.md",
        "standalone/studio/scripts/build_release.ps1",
        "companion",
        True,
        "standalone/studio",
    ),
    ReleaseProduct(
        "player",
        "Quill Media Player",
        "quill-player-v",
        "Quill-Player",
        "quill/apps/player.py",
        "_VERSION",
        "quill/apps/player.py",
        "_BUILD",
        "standalone/player/docs/CHANGELOG.md",
        wave="held",
        wrapper="standalone/player",
    ),
    ReleaseProduct(
        "inkwell",
        "Quill Inkwell",
        "quill-inkwell-v",
        "Quill-Inkwell",
        "quill/apps/inkwell.py",
        "_VERSION",
        "quill/apps/inkwell.py",
        "_BUILD",
        "standalone/inkwell/docs/CHANGELOG.md",
        "standalone/inkwell/scripts/build_release.ps1",
        "companion",
        True,
        "standalone/inkwell",
    ),
    ReleaseProduct(
        "weather",
        "Quill Weather",
        "quill-weather-v",
        "Quill-Weather",
        "quill/apps/weather.py",
        "_VERSION",
        "quill/apps/weather.py",
        "_BUILD",
        "standalone/weather/docs/CHANGELOG.md",
        "standalone/weather/scripts/build_release.ps1",
        "companion",
        True,
        "standalone/weather",
    ),
    ReleaseProduct(
        "social",
        "QUILL Social",
        "quill-social-v",
        "QUILL-Social",
        "standalone/social/quill_social/__init__.py",
        "__version__",
        "standalone/social/quill_social/__init__.py",
        "__build__",
        "standalone/social/CHANGELOG.md",
        "standalone/social/scripts/build_release.ps1",
        "later",
        True,
        "standalone/social",
    ),
    ReleaseProduct(
        "beacon",
        "Quill Beacon",
        "quill-beacon-v",
        "Quill-Beacon",
        "quill/apps/beacon/app.py",
        "_VERSION",
        "quill/apps/beacon/app.py",
        "_BUILD",
        "standalone/beacon/CHANGELOG.md",
        "standalone/beacon/scripts/build_release.ps1",
        "later",
        True,
        "standalone/beacon",
    ),
)

BY_KEY: MappingProxyType[str, ReleaseProduct] = MappingProxyType({
    product.key: product for product in PRODUCTS
})

PLATFORM_VARIANTS = frozenset({"radio-mac", "weather-ios"})


def product(key: str) -> ReleaseProduct:
    return BY_KEY[key]


__all__ = [
    "BY_KEY",
    "PLATFORM_VARIANTS",
    "PRODUCTS",
    "ReleaseProduct",
    "ReleaseWave",
    "product",
]
