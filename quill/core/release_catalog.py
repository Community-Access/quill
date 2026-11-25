"""The one release catalogue for every Windows QuillVille product.

Versions, build scripts, feed entries, sibling checks and the family build
command must all agree with this list. A new standalone wrapper is not a
release product until it is named here; a held product may have no installer
yet, but it cannot disappear silently from the maintenance inventory.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
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
    version_module: str
    build_file: str
    build_constant: str
    changelog: str
    build_entry: str = ""
    wave: ReleaseWave = "held"
    shared_runtime: bool = True
    wrapper: str = ""
    released: bool = False
    snapshot_files: tuple[str, ...] = ()
    data_location: Literal["quill_data", "lite_data", "beacon_data", "social_data"] = "quill_data"
    asset_match_prefix: str = ""
    release_menu_file: str = ""

    @property
    def buildable(self) -> bool:
        return bool(self.build_entry)

    @property
    def channels_enabled(self) -> bool:
        return self.buildable and self.wave != "held"

    @property
    def tag_key(self) -> str:
        if self.key == "quill":
            return ""
        if self.key == "quilllite":
            return "lite"
        return self.key

    @property
    def module_name(self) -> str:
        return self.version_module

    @property
    def lookup_asset_prefix(self) -> str:
        return self.asset_match_prefix or self.asset_prefix


PRODUCTS: tuple[ReleaseProduct, ...] = (
    ReleaseProduct(
        "quill",
        "QUILL",
        "v",
        "Quill",
        "quill/__init__.py",
        "__version__",
        "quill",
        "quill/__init__.py",
        "__build__",
        "CHANGELOG.md",
        "scripts/build_windows_distribution.py",
        "platform",
        False,
        released=True,
        snapshot_files=("settings.json", "keymap.json"),
        release_menu_file="quill/ui/main_frame_updates.py",
    ),
    ReleaseProduct(
        "quilllite",
        "QUILL Lite",
        "quill-lite-v",
        "QuillLite",
        "quill/core/lite/__init__.py",
        "APP_VERSION",
        "quill.core.lite",
        "quill/core/lite/__init__.py",
        "APP_BUILD",
        "standalone/quilllite/docs/CHANGELOG.md",
        "standalone/quilllite/scripts/build_release.ps1",
        "platform",
        True,
        "standalone/quilllite",
        True,
        ("settings.json", "lite_keymap.json"),
        "lite_data",
        release_menu_file="quill/apps/lite_updates.py",
    ),
    ReleaseProduct(
        "radio",
        "Quill Radio",
        "quill-radio-v",
        "Quill-Radio",
        "quill/apps/radio.py",
        "_VERSION",
        "quill.apps.radio",
        "quill/apps/radio.py",
        "_BUILD",
        "standalone/radio/docs/CHANGELOG.md",
        "standalone/radio/scripts/build_release.ps1",
        "platform",
        True,
        "standalone/radio",
        True,
        release_menu_file="quill/apps/radio_menu_bar.py",
    ),
    ReleaseProduct(
        "cast",
        "QUILL Cast",
        "quill-cast-v",
        "Quill-Cast",
        "quill/apps/podcasts_menu.py",
        "APP_VERSION",
        "quill.apps.podcasts_menu",
        "quill/apps/podcasts_menu.py",
        "APP_BUILD",
        "standalone/cast/docs/CHANGELOG.md",
        "standalone/cast/scripts/build_release.ps1",
        "platform",
        True,
        "standalone/cast",
        release_menu_file="quill/apps/podcasts_menu.py",
    ),
    ReleaseProduct(
        "transcribe",
        "QUILL Transcribe",
        "quill-transcribe-v",
        "QUILL-Transcribe",
        "quill/apps/transcribe.py",
        "_VERSION",
        "quill.apps.transcribe",
        "quill/apps/transcribe.py",
        "_BUILD",
        "standalone/transcribe/docs/CHANGELOG.md",
        "standalone/transcribe/scripts/build_release.ps1",
        "platform",
        True,
        "standalone/transcribe",
        True,
        ("transcribe.json",),
        release_menu_file="quill/apps/transcribe_menus.py",
    ),
    ReleaseProduct(
        "converter",
        "Quill Converter",
        "quill-converter-v",
        "Quill-Converter",
        "quill/apps/converter.py",
        "_VERSION",
        "quill.apps.converter",
        "quill/apps/converter.py",
        "_BUILD",
        "standalone/converter/docs/CHANGELOG.md",
        "standalone/converter/scripts/build_release.ps1",
        "platform",
        True,
        "standalone/converter",
        True,
        ("converter.json",),
        release_menu_file="quill/apps/converter_menu.py",
    ),
    ReleaseProduct(
        "studio",
        "QUILL Studio",
        "quill-studio-v",
        "QUILL-Audio-Studio",
        "quill/apps/studio.py",
        "_VERSION",
        "quill.apps.studio",
        "quill/apps/studio.py",
        "_BUILD",
        "standalone/studio/docs/CHANGELOG.md",
        "standalone/studio/scripts/build_release.ps1",
        "companion",
        True,
        "standalone/studio",
        False,
        (
            "studio-ai.json",
            "audio_studio_book_prefs.json",
            "audio_studio_history.json",
            "audio_studio_library.json",
            "audio_studio_play_queue.json",
            "audio_studio_sleep_timer.json",
        ),
        "quill_data",
        "Quill-Audio",
        "quill/apps/studio.py",
    ),
    ReleaseProduct(
        "player",
        "Quill Media Player",
        "quill-player-v",
        "Quill-Player",
        "quill/apps/player.py",
        "_VERSION",
        "quill.apps.player",
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
        "quill.apps.inkwell",
        "quill/apps/inkwell.py",
        "_BUILD",
        "standalone/inkwell/docs/CHANGELOG.md",
        "standalone/inkwell/scripts/build_release.ps1",
        "companion",
        True,
        "standalone/inkwell",
        True,
        ("inkwell.json",),
        release_menu_file="quill/apps/inkwell.py",
    ),
    ReleaseProduct(
        "weather",
        "Quill Weather",
        "quill-weather-v",
        "Quill-Weather",
        "quill/apps/weather.py",
        "_VERSION",
        "quill.apps.weather",
        "quill/apps/weather.py",
        "_BUILD",
        "standalone/weather/docs/CHANGELOG.md",
        "standalone/weather/scripts/build_release.ps1",
        "platform",
        True,
        "standalone/weather",
        True,
        ("weather_settings.json",),
        release_menu_file="quill/apps/weather.py",
    ),
    ReleaseProduct(
        "social",
        "QUILL Social",
        "quill-social-v",
        "QUILL-Social",
        "standalone/social/quill_social/__init__.py",
        "__version__",
        "quill_social",
        "standalone/social/quill_social/__init__.py",
        "__build__",
        "standalone/social/CHANGELOG.md",
        "standalone/social/scripts/build_release.ps1",
        "later",
        True,
        "standalone/social",
        False,
        ("a11y.json", "keymap.json", "mastodon_apps.json"),
        "social_data",
        release_menu_file="standalone/social/quill_social/ui/app.py",
    ),
    ReleaseProduct(
        "beacon",
        "Quill Beacon",
        "quill-beacon-v",
        "Quill-Beacon",
        "quill/apps/beacon/app.py",
        "_VERSION",
        "quill.apps.beacon.app",
        "quill/apps/beacon/app.py",
        "_BUILD",
        "standalone/beacon/CHANGELOG.md",
        "standalone/beacon/scripts/build_release.ps1",
        "later",
        True,
        "standalone/beacon",
        False,
        (
            "a11y.json",
            "player_settings.json",
            "routing.json",
            "sync_config.json",
            "sync_conflicts.json",
        ),
        "beacon_data",
        release_menu_file="quill/apps/beacon/app.py",
    ),
)

BY_KEY: MappingProxyType[str, ReleaseProduct] = MappingProxyType({
    product.key: product for product in PRODUCTS
})

PLATFORM_VARIANTS = frozenset({"radio-mac", "weather-ios"})


def product(key: str) -> ReleaseProduct:
    return BY_KEY[key]


def version_parts(key: str) -> tuple[str, int]:
    """The version/build for *key*, source-only when files are present."""
    found = product(key)
    root = Path(__file__).resolve().parents[2]
    version_path = root / found.version_file
    build_path = root / found.build_file
    if version_path.is_file() and build_path.is_file():
        version_text = version_path.read_text(encoding="utf-8")
        build_text = build_path.read_text(encoding="utf-8")
        version_match = re.search(
            rf"^{re.escape(found.version_constant)}\s*(?::[^=\n]+)?=\s*['\"]([^'\"]+)['\"]",
            version_text,
            re.M,
        )
        build_match = re.search(
            rf"^{re.escape(found.build_constant)}\s*(?::[^=\n]+)?=\s*(\d+)",
            build_text,
            re.M,
        )
        if version_match is not None and build_match is not None:
            return version_match.group(1), int(build_match.group(1))
    module = import_module(found.version_module)
    return (
        str(getattr(module, found.version_constant)),
        int(getattr(module, found.build_constant, 0) or 0),
    )


def installed_version(key: str, *, current: bool = True) -> str:
    """The installed marker's version, falling back to the running source."""
    from quill.core.app_version import full_version, marker_roots, read_marker

    if not current:
        from quill.core.runtime_apps import RUNTIME_APPS, installed_launcher

        app = next((entry for entry in RUNTIME_APPS if entry.ref_id == key), None)
        launcher = installed_launcher(app) if app is not None else None
        if launcher is not None:
            sibling_marker = read_marker(launcher.parent)
            if sibling_marker:
                return sibling_marker
        version, build = version_parts(key)
        return full_version(version, build)
    for root in marker_roots():
        marker = read_marker(root)
        if marker:
            return marker
    version, build = version_parts(key)
    return full_version(version, build)


def data_dir(key: str) -> Path:
    """The product's real data root, including independent later-wave apps."""
    found = product(key)
    if found.data_location == "lite_data":
        from quill.core.lite.paths import data_dir as lite_data_dir

        return lite_data_dir()
    if found.data_location == "beacon_data":
        beacon_paths = import_module("quill.apps.beacon.paths")
        beacon_data_dir = beacon_paths.data_dir

        return Path(beacon_data_dir())
    if found.data_location == "social_data":
        social_paths = import_module("quill_social.paths")
        social_data_dir = social_paths.data_dir

        return Path(social_data_dir())
    from quill.core.paths import app_data_dir

    return app_data_dir()


__all__ = [
    "BY_KEY",
    "PLATFORM_VARIANTS",
    "PRODUCTS",
    "ReleaseProduct",
    "ReleaseWave",
    "data_dir",
    "installed_version",
    "product",
    "version_parts",
]
