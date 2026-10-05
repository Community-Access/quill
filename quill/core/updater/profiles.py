"""One profile per app: the seam a QuillVille app joins release channels through.

Release-channels plan 6.9. An app that wants channels adds a profile here, a
snapshot adapter (:mod:`.snapshots`), and the Help menu item and Preferences row
that open the shared Release Channel dialog. Phase 1 covers the four apps the
plan names; the rest of the family joins in Phase 6.

wx-free and strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass

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


QUILL = UpdaterProfile(
    app_key="quill",
    tag_key="",
    display_name="QUILL",
    uses_shared_runtime=False,
    runtime_ref="",
    snapshot_covers="your settings, keys and preferences",
    snapshot_leaves="Your documents are not copied, and updates don't change them.",
)
QUILL_LITE = UpdaterProfile(
    app_key="quilllite",
    tag_key="lite",
    display_name="QUILL Lite",
    uses_shared_runtime=True,
    runtime_ref="quilllite",
    snapshot_covers="your settings, keys and recent files list",
    snapshot_leaves="Your documents are not copied, and updates don't change them.",
)
RADIO = UpdaterProfile(
    app_key="radio",
    tag_key="radio",
    display_name="Quill Radio",
    uses_shared_runtime=True,
    runtime_ref="radio",
    snapshot_covers="your favorites, history and settings",
    snapshot_leaves="Your recordings are not copied, and updates don't change them.",
)
CAST = UpdaterProfile(
    app_key="cast",
    tag_key="cast",
    display_name="QUILL Cast",
    uses_shared_runtime=True,
    runtime_ref="cast",
    snapshot_covers="your subscriptions, playlists, listening places and settings",
    snapshot_leaves="Downloaded episodes are not copied, and updates don't change them.",
)

#: Every app with release channels, in the order the chooser lists siblings.
PROFILES: dict[str, UpdaterProfile] = {p.app_key: p for p in (QUILL, QUILL_LITE, RADIO, CAST)}


def profile_for(app_key: str) -> UpdaterProfile:
    """The profile for *app_key*; raises ``KeyError`` for an app without one."""
    return PROFILES[app_key]
