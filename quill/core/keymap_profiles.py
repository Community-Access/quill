"""The bundled keymap profiles: named layouts a person can switch to.

A profile is a **delta**, never a snapshot (bad.md P2.6). Writing down a
binding that already equals the default is what let the three shipped files
drift 29, 28 and 5 bindings behind ``DEFAULT_KEYMAP`` without anyone noticing:
a chord moved in the defaults still reached a profile user at its old value,
forever, because the profile pinned it. ``tests/unit/core/test_keymap_profiles``
is the gate that keeps them deltas.

Extracted from ``keymap.py`` on 2026-09-17 (GATE-11): the loader is a separate
concern from the binding table, and the table is the largest thing in core.
"""

from __future__ import annotations

import logging
from pathlib import Path

from quill.core.storage import read_json

logger = logging.getLogger(__name__)

__all__ = ["list_keymap_profiles", "load_keymap_profile"]

_PROFILES_DIR = Path(__file__).resolve().parent / "keymap"


def _profile_path_for(name: str) -> Path | None:
    """The bundled profile file *name* asks for, by slug or by display name.

    ``profile_<slug>.json`` is tried first, where the slug is the lower-cased
    name with spaces underscored. That alone used to be the whole lookup, and
    it silently missed two of the three shipped profiles: the work-persona
    dialog stores the *display* name, so "QUILL Default" resolved to
    ``profile_quill_default.json``, which does not exist, and the caller got
    ``DEFAULT_KEYMAP`` back as though the profile had applied. So the display
    name recorded in each file's ``_name`` is a lookup key too.
    """
    slug = name.strip().lower().replace(" ", "_")
    if slug:
        direct = _PROFILES_DIR / f"profile_{slug}.json"
        if direct.is_file():
            return direct
    if not _PROFILES_DIR.is_dir():
        return None
    wanted = name.strip().casefold()
    for path in sorted(_PROFILES_DIR.glob("profile_*.json")):
        data = read_json(path, default={})
        if isinstance(data, dict) and str(data.get("_name", "")).casefold() == wanted:
            return path
    return None


def load_keymap_profile(name: str) -> dict[str, str]:
    """Return the merged keymap for a named JSON profile in quill/core/keymap/.

    A profile is a **delta**, never a snapshot (bad.md P2.6). It is one of two
    shapes and its ``_base`` says which:

    ``"default"`` (the default when absent)
        an overlay: ``bindings`` names only the commands this profile moves,
        and every other command tracks ``DEFAULT_KEYMAP``. Writing down a
        binding that already equals the default is what let the shipped files
        drift 29 bindings behind the defaults without anyone noticing, so the
        profile gate rejects it.

    ``"none"``
        a subtractive profile: every command starts unbound, ``keep`` names the
        commands that survive at their *current* default chord, and
        ``bindings`` may then move any of them. This is what makes "Minimal"
        minimal; as an overlay it kept all 415 default bindings and removed
        nothing at all.

    Falls back to ``DEFAULT_KEYMAP`` if the profile is missing or malformed.
    """
    # Local import: keymap imports this module back, at the bottom of its own
    # file, to keep quill.core.keymap's public surface unchanged.
    from quill.core.keymap import DEFAULT_KEYMAP

    profile_path = _profile_path_for(name)
    data = read_json(profile_path, default={}) if profile_path else {}
    if not isinstance(data, dict):
        return DEFAULT_KEYMAP.copy()
    bindings = data.get("bindings", {})
    if not isinstance(bindings, dict):
        return DEFAULT_KEYMAP.copy()
    if data.get("_base") == "none":
        merged = dict.fromkeys(DEFAULT_KEYMAP, "")
        keep = data.get("keep", [])
        if isinstance(keep, list):
            for command_id in keep:
                if isinstance(command_id, str) and command_id in DEFAULT_KEYMAP:
                    merged[command_id] = DEFAULT_KEYMAP[command_id]
    else:
        merged = DEFAULT_KEYMAP.copy()
    merged.update({k: v for k, v in bindings.items() if isinstance(v, str)})
    return merged


def list_keymap_profiles() -> list[str]:
    """Return the display names of available JSON profiles."""
    profiles: list[str] = []
    if not _PROFILES_DIR.is_dir():
        return profiles
    for path in sorted(_PROFILES_DIR.glob("profile_*.json")):
        data = read_json(path, default={})
        if isinstance(data, dict) and "_name" in data:
            profiles.append(str(data["_name"]))
        else:
            logger.debug("Dropping malformed keymap profile: %s", path.name)
    return profiles
