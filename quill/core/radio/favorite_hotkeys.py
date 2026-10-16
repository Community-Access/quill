"""A system-wide key per favourite station (xradio2 4.9, todo P3 Radio extras 6).

Optional and empty by default: a listener who wants station nine one chord away
from anywhere gives that favourite its own key, and nothing else changes. The
key is registered with Windows while Quill Radio runs, so it works with another
program in front.

**Why a map beside the favourites rather than a field on each one.** The
favourites file is the record of a collection that is backed up, exported and
imported; a system-wide key is a fact about *this* computer's keyboard, and an
imported favourite arriving with a key that collides with something here would
be the worst kind of surprise. So the keys live in their own small file, keyed
by the favourite's stable key, and a favourite that is removed simply has no
station to play -- its key is dropped the next time the map is saved.

**Conflicts are the family's own check.** :func:`problem` is
``family_chords.show_hide_key_problem`` -- the one that already refuses a key
with no Ctrl or Alt, a key another family app registers, and a key any family
app uses as a shortcut -- plus the keys the other favourites already hold. A
second implementation of "is this key free?" is how two answers drift.

wx-free, strict-typed.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.storage import read_json, write_json_atomic

__all__ = [
    "FILENAME",
    "load_hotkeys",
    "problem",
    "save_hotkeys",
    "set_hotkey",
    "store_path",
]

FILENAME = "radio_favorite_hotkeys.json"


def store_path(data_dir: Path) -> Path:
    return data_dir / FILENAME


def load_hotkeys(data_dir: Path) -> dict[str, str]:
    """``{favourite key: chord}``. ``{}`` when there is no file or it cannot be read."""
    try:
        raw = read_json(store_path(data_dir), {})
    except Exception:  # noqa: BLE001 - an unreadable map is an empty one
        return {}
    if not isinstance(raw, dict):
        return {}
    return {
        str(key): str(chord).strip()
        for key, chord in raw.items()
        if str(key).strip() and str(chord or "").strip()
    }


def save_hotkeys(data_dir: Path, hotkeys: dict[str, str]) -> None:
    write_json_atomic(
        store_path(data_dir), {key: chord for key, chord in hotkeys.items() if chord.strip()}
    )


def set_hotkey(
    data_dir: Path, favorite_key: str, chord: str, *, keep: set[str] | None = None
) -> dict[str, str]:
    """Give *favorite_key* the key *chord* ("" removes it). Returns the new map.

    *keep* is the set of favourite keys that still exist; entries for anything
    else are dropped on the way through, so the file never accumulates keys for
    stations that have gone.
    """
    hotkeys = load_hotkeys(data_dir)
    if chord.strip():
        hotkeys[favorite_key] = chord.strip()
    else:
        hotkeys.pop(favorite_key, None)
    if keep is not None:
        hotkeys = {key: value for key, value in hotkeys.items() if key in keep}
    save_hotkeys(data_dir, hotkeys)
    return hotkeys


def problem(
    chord: str,
    *,
    favorite_key: str,
    hotkeys: dict[str, str],
    names: dict[str, str] | None = None,
    show_hide_key: str = "",
) -> str:
    """Why *chord* cannot be this favourite's key, in one sentence, or "".

    *names* maps favourite keys to the names said when another favourite
    already holds the key; *show_hide_key* is Quill Radio's own show and hide
    key, which a favourite must not take either.
    """
    from quill.core.family_chords import show_hide_key_problem

    own: dict[str, str] = {}
    if show_hide_key.strip():
        own["show and hide key"] = show_hide_key
    for key, held in hotkeys.items():
        if key != favorite_key and held.strip():
            name = (names or {}).get(key, "another favorite")
            own[f"key for {name}"] = held
    return show_hide_key_problem(chord, app_id="radio", own=own)
