"""The bundled keymap profiles are deltas, not snapshots (bad.md P2.6).

A profile used to be a full copy of every binding it cared about, which is
exactly the shape that lets it disagree with ``DEFAULT_KEYMAP`` in silence: a
chord moved in the defaults still reached a profile user at its old value,
forever, because the profile pinned it. Three files had drifted 29, 28 and 5
bindings behind before this was noticed.

A profile is now one of two things and says which:

* an **overlay** (``_base`` absent or ``"default"``) whose ``bindings`` are
  *only* the commands it deliberately moves -- everything else tracks
  ``DEFAULT_KEYMAP`` automatically;
* a **subtractive** profile (``_base: "none"``) whose ``keep`` list names the
  commands that stay, each at its current default chord, with everything else
  unbound. That is what makes "Minimal" actually minimal; as an overlay it
  silently kept all 415 default bindings and removed nothing.

The first test is the gate: an entry equal to the default is drift waiting to
happen and must not be written down at all.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core.keymap import DEFAULT_KEYMAP, list_keymap_profiles, load_keymap_profile

_PROFILES_DIR = Path(__file__).resolve().parents[3] / "quill" / "core" / "keymap"


def _profile_files() -> list[Path]:
    return sorted(_PROFILES_DIR.glob("profile_*.json"))


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


class TestProfilesAreDeltas:
    """No bundled profile may restate a binding it does not change."""

    @pytest.mark.parametrize("path", _profile_files(), ids=lambda p: p.name)
    def test_no_binding_equals_the_default(self, path: Path) -> None:
        data = _load(path)
        bindings = data.get("bindings", {})
        assert isinstance(bindings, dict)
        restated = {
            command_id: chord
            for command_id, chord in bindings.items()
            if DEFAULT_KEYMAP.get(command_id) == chord
        }
        assert not restated, (
            f"{path.name} restates {len(restated)} binding(s) that already match "
            "DEFAULT_KEYMAP. Delete them: a profile carries only what it moves."
        )

    @pytest.mark.parametrize("path", _profile_files(), ids=lambda p: p.name)
    def test_every_command_named_is_one_the_defaults_know(self, path: Path) -> None:
        data = _load(path)
        named = set(data.get("bindings", {})) | set(data.get("keep", []))
        unknown = sorted(name for name in named if name not in DEFAULT_KEYMAP)
        assert not unknown, (
            f"{path.name} names commands absent from DEFAULT_KEYMAP: {unknown}. "
            "A command with no default chord gets one in DEFAULT_KEYMAP, not in a profile."
        )

    @pytest.mark.parametrize("path", _profile_files(), ids=lambda p: p.name)
    def test_declares_a_base_it_understands(self, path: Path) -> None:
        base = _load(path).get("_base", "default")
        assert base in {"default", "none"}, f"{path.name} declares unknown _base {base!r}"


class TestDefaultProfileIsTheDefault:
    """ "QUILL Default" must resolve to DEFAULT_KEYMAP, exactly."""

    def test_it_changes_nothing(self) -> None:
        assert load_keymap_profile("QUILL Default") == DEFAULT_KEYMAP

    def test_it_carries_no_bindings_at_all(self) -> None:
        assert _load(_PROFILES_DIR / "profile_default.json").get("bindings") == {}


class TestScreenReaderFriendlyMovesWhatScreenReadersEat:
    """The six table-cell chords are JAWS and NVDA table navigation."""

    _TABLE_COMMANDS = (
        "table.next_cell",
        "table.previous_cell",
        "table.cell_below",
        "table.cell_above",
        "table.first_cell",
        "table.last_cell",
    )

    _SCREEN_READER_OWNS = {
        "CTRL+ALT+RIGHT",
        "CTRL+ALT+LEFT",
        "CTRL+ALT+UP",
        "CTRL+ALT+DOWN",
        "CTRL+ALT+HOME",
        "CTRL+ALT+END",
    }

    def test_no_table_command_stays_on_a_ctrl_alt_arrow(self) -> None:
        resolved = load_keymap_profile("Screen Reader Friendly")
        eaten = {
            command_id
            for command_id in self._TABLE_COMMANDS
            if resolved[command_id].upper() in self._SCREEN_READER_OWNS
        }
        assert not eaten, f"still on a chord the screen reader owns: {sorted(eaten)}"

    def test_it_differs_from_the_default_profile(self) -> None:
        assert load_keymap_profile("Screen Reader Friendly") != load_keymap_profile("QUILL Default")

    def test_everything_it_does_not_name_tracks_the_defaults(self) -> None:
        resolved = load_keymap_profile("Screen Reader Friendly")
        assert resolved["edit.insert_link"] == DEFAULT_KEYMAP["edit.insert_link"]
        assert resolved["tools.word_count"] == DEFAULT_KEYMAP["tools.word_count"]


class TestMinimalSubtracts:
    """Minimal is a keep-list: what it does not name is unbound."""

    def test_a_command_it_does_not_keep_is_unbound(self) -> None:
        resolved = load_keymap_profile("Minimal")
        assert resolved["edit.paste_from_tray_1"] == ""
        assert resolved["format.bold"] == ""

    def test_what_it_keeps_tracks_the_current_default(self) -> None:
        resolved = load_keymap_profile("Minimal")
        assert resolved["tools.word_count"] == DEFAULT_KEYMAP["tools.word_count"]
        assert resolved["edit.insert_link"] == DEFAULT_KEYMAP["edit.insert_link"]

    def test_quitting_survives(self) -> None:
        # Ctrl+Q was reached only because the old overlay kept every default.
        # Subtracting means an essential verb must be kept on purpose.
        assert load_keymap_profile("Minimal")["app.exit"] == DEFAULT_KEYMAP["app.exit"]

    def test_it_holds_no_chord_command(self) -> None:
        bound = {chord for chord in load_keymap_profile("Minimal").values() if chord}
        leaders = sorted(c for c in bound if c.upper().startswith("CTRL+SHIFT+GRAVE"))
        assert not leaders, (
            "Minimal promises no chord commands; a kept command's default has "
            "since moved onto the QUILL Key leader."
        )

    def test_every_command_the_defaults_know_is_present(self) -> None:
        # Subtraction must answer for the whole command set, not a subset:
        # a command missing from the map reads as "unknown", not "unbound".
        assert set(load_keymap_profile("Minimal")) == set(DEFAULT_KEYMAP)


class TestLoaderFallbacks:
    def test_an_unknown_profile_name_is_the_defaults(self) -> None:
        assert load_keymap_profile("no such profile") == DEFAULT_KEYMAP

    def test_the_three_profiles_are_listed(self) -> None:
        assert list_keymap_profiles() == [
            "QUILL Default",
            "Minimal",
            "Screen Reader Friendly",
        ]
