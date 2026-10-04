"""Channel runtime slots for the shared QuillVille Runtime (release-channels plan 6.5).

**The rule: each channel has its own runtime slot. Within a slot the newest
build wins, as it always has. Across slots nothing is shared.**

=========== ====================================== ===========================
Channel     Folder under ``%LOCALAPPDATA%\\QuillVille\\Runtime``  Repairs itself from
=========== ====================================== ===========================
Stable      ``3.13`` (the folder that already exists) ``runtime-stable``, and the
                                                   ``runtime-latest`` alias that
                                                   installed launchers know
Beta        ``3.13-beta``                          ``runtime-beta``
Dev         ``3.13-dev``                           nothing: "Reinstall the Dev build"
=========== ====================================== ===========================

So a Beta Quill Radio puts its runtime in ``3.13-beta``, and a Stable QUILL Lite
on the same computer keeps running from ``3.13``, untouched. Going back to
Stable installs into ``3.13`` again, and when the last app leaves a slot its
uninstaller removes it -- about 335 MB comes back.

The installer (``installer/shared-runtime.iss``) chooses the slot from
``/CHANNEL=`` -- which the updater always passes -- or, for a hand install with
no ``/CHANNEL``, Stable for a final version and Beta for any pre-release. It
writes ``[runtime] slot=`` and ``[app] channel=`` into the app's
``quill-app-version.ini``, and the native launcher reads ``slot=`` from there
(``quill/native/launcher/runtime_resolve.c``); with no ``slot=`` it uses
``3.13``, exactly as before.

This module is the Python mirror of those two, unit-tested, plus what the
updater and the risk window need to know. wx-free and strict-typed.
"""

from __future__ import annotations

import re
from pathlib import Path

from quill.core.updater.channels import BETA, DEV, STABLE, Channel, normalize_channel
from quill.core.versioning import ReleaseVersion

__all__ = [
    "PYTHON_MAJOR",
    "RUNTIME_TAGS",
    "SLOT_EXTRA_MB",
    "channel_of_slot",
    "default_channel",
    "installer_args",
    "is_valid_slot",
    "launcher_slot_dir",
    "self_heal_tag",
    "slot_for",
    "slots_in_use",
]

PYTHON_MAJOR = "3.13"

#: About how much disk a Beta or Dev slot adds until the last app leaves it.
#: The risk window says this number plainly (owner decision, 2026-10-03).
SLOT_EXTRA_MB = 335

#: The GitHub release tags each slot's runtime installer is published under.
#: ``runtime-latest`` stays an alias of Stable for ever: installed launchers
#: have it compiled in.
RUNTIME_TAGS: dict[str, tuple[str, ...]] = {
    STABLE: ("runtime-stable", "runtime-latest"),
    BETA: ("runtime-beta",),
    DEV: (),
}

_SLOT_RE = re.compile(r"^\d+\.\d+(?:-(?:beta|dev))?$")


def slot_for(channel: str, python_major: str = PYTHON_MAJOR) -> str:
    """``3.13`` for Stable, ``3.13-beta``, ``3.13-dev``."""
    ch = normalize_channel(channel)
    return python_major if ch == STABLE else f"{python_major}-{ch}"


def channel_of_slot(slot: str) -> Channel:
    if slot.endswith("-dev"):
        return DEV
    if slot.endswith("-beta"):
        return BETA
    return STABLE


def is_valid_slot(slot: str) -> bool:
    """What the launcher accepts from the ini: a version and an optional channel."""
    return bool(_SLOT_RE.match(slot or ""))


def default_channel(version: str, requested: str = "") -> Channel:
    """The installer's rule: ``/CHANNEL=`` when given; else Stable for a final
    version and Beta for any pre-release (a hand install from the website)."""
    if requested.strip():
        return normalize_channel(requested)
    parsed = ReleaseVersion.try_parse(version)
    if parsed is None or not parsed.is_prerelease:
        return STABLE
    return DEV if parsed.stage == "dev" else BETA


def installer_args(channel: str) -> list[str]:
    """What the update helper adds to the installer's command line."""
    return [f"/CHANNEL={normalize_channel(channel)}"]


def self_heal_tag(slot: str) -> str | None:
    """The release tag a missing runtime in *slot* is downloaded from; ``None`` for Dev."""
    tags = RUNTIME_TAGS[channel_of_slot(slot)]
    if not tags:
        return None
    return "runtime-latest" if channel_of_slot(slot) == STABLE else tags[0]


def launcher_slot_dir(local_app_data: Path, slot: str) -> Path:
    """The folder the launcher resolves for *slot* -- the C code's rule, in Python.

    A missing or malformed ``slot=`` means the Stable folder, so a launcher
    reading an older ini behaves exactly as it always has.
    """
    name = slot if is_valid_slot(slot) else PYTHON_MAJOR
    return local_app_data / "QuillVille" / "Runtime" / name


def slots_in_use(refs: dict[str, list[str]]) -> dict[str, list[str]]:
    """Group ``runtime_refs`` entries by slot (old ``3.13.1`` keys are the Stable slot)."""
    from quill.core.runtime_refs import slot_of

    grouped: dict[str, list[str]] = {}
    for key, apps in refs.items():
        grouped.setdefault(slot_of(key), [])
        grouped[slot_of(key)] = sorted({*grouped[slot_of(key)], *apps})
    return grouped
