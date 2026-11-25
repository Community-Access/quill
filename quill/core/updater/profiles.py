"""One profile per app: the seam a QuillVille app joins release channels through.

Release-channels plan 6.9. The product catalogue is the one place an app joins
channels: every buildable, non-held product gets a profile automatically, and
the release-catalog gate refuses a menu, feed or snapshot surface that omits it.

wx-free and strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.release_catalog import PRODUCTS

__all__ = ["PROFILES", "UpdaterProfile", "profile_for"]


@dataclass(frozen=True)
class UpdaterProfile:
    #: The family key: ``companion_install.ASSET_PREFIX`` and ``channels.json``.
    app_key: str
    #: The release tag's app key: ``""`` for QUILL (``v1.0.0``), ``"lite"``
    #: for QUILL Lite (``quill-lite-v``, grandfathered), else the app key.
    tag_key: str
    display_name: str
    #: Whether it runs on the shared QuillVille Runtime (plan 6.5).
    uses_shared_runtime: bool
    #: Its id in ``runtime_refs`` (what an installer registers), when it has one.
    runtime_ref: str
    #: What the joined-Beta copy holds, in the words the risk dialog uses.
    snapshot_covers: str
    #: What the copy deliberately leaves alone.
    snapshot_leaves: str


_SNAPSHOT_WORDS = {
    "quill": (
        "your settings, keys and preferences",
        "Your documents are not copied, and updates don't change them.",
    ),
    "quilllite": (
        "your settings, keys and recent files list",
        "Your documents are not copied, and updates don't change them.",
    ),
    "radio": (
        "your favorites, history and settings",
        "Your recordings are not copied, and updates don't change them.",
    ),
    "cast": (
        "your subscriptions, playlists, listening places and settings",
        "Downloaded episodes are not copied, and updates don't change them.",
    ),
    "transcribe": (
        "your settings and dictation choices",
        "Your recordings and transcripts are not copied, and updates don't change them.",
    ),
    "studio": (
        "your Studio library, play queue, history and settings",
        "Your projects and audio files are not copied, and updates don't change them.",
    ),
    "beacon": (
        "your Beacon accessibility, player, routing and sync settings",
        "Your bookmark database is not copied, and updates don't change it.",
    ),
    "social": (
        "your Social accessibility, keymap and connected-app settings",
        "Your posts, accounts and database are not copied, and updates don't change them.",
    ),
}

PROFILES: dict[str, UpdaterProfile] = {}
for release_product in PRODUCTS:
    if not release_product.channels_enabled:
        continue
    covers, leaves = _SNAPSHOT_WORDS.get(
        release_product.key,
        (
            "your settings and preferences",
            "Your documents and large media files are not copied or changed.",
        ),
    )
    PROFILES[release_product.key] = UpdaterProfile(
        app_key=release_product.key,
        tag_key=release_product.tag_key,
        display_name=release_product.name,
        uses_shared_runtime=release_product.shared_runtime,
        runtime_ref=release_product.key if release_product.shared_runtime else "",
        snapshot_covers=covers,
        snapshot_leaves=leaves,
    )

# Historical names remain for direct imports; catalogue rows own the values.
QUILL = PROFILES["quill"]
QUILL_LITE = PROFILES["quilllite"]
RADIO = PROFILES["radio"]
CAST = PROFILES["cast"]
TRANSCRIBE = PROFILES["transcribe"]


def profile_for(app_key: str) -> UpdaterProfile:
    """The profile for *app_key*; raises ``KeyError`` for an app without one."""
    return PROFILES[app_key]
