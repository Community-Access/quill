from quill.core.keymap_query import (
    bindings_equivalent,
    canonical_binding,
    commands_for_keystroke,
    diagnose_keymap,
    duplicate_bindings,
    find_keymap_conflicts,
    parse_binding,
    rewrite_chord_prefixes,
)


class TestParseAndCanonical:
    def test_simple_binding(self) -> None:
        assert canonical_binding("Ctrl+Shift+K") == "Ctrl+Shift+K"

    def test_modifier_order_is_normalised(self) -> None:
        assert canonical_binding("Shift+Ctrl+K") == "Ctrl+Shift+K"
        assert canonical_binding("Shift+Alt+Ctrl+K") == "Ctrl+Alt+Shift+K"

    def test_key_can_come_first(self) -> None:
        assert canonical_binding("k+ctrl+shift") == "Ctrl+Shift+K"

    def test_case_insensitive(self) -> None:
        assert canonical_binding("CONTROL+shift+k") == "Ctrl+Shift+K"

    def test_modifier_aliases(self) -> None:
        for spelling in ("ctrl+m", "control+m", "ctl+m"):
            assert canonical_binding(spelling) == "Ctrl+M", spelling
        assert canonical_binding("option+m") == "Alt+M"
        assert canonical_binding("opt+m") == "Alt+M"

    def test_cmd_stays_distinct_from_ctrl(self) -> None:
        # macOS Cmd is a different physical key from Ctrl; they must not collapse.
        assert canonical_binding("cmd+[") == "Cmd+["
        assert canonical_binding("command+[") == "Cmd+["
        assert not bindings_equivalent("Cmd+[", "Ctrl+[")

    def test_whitespace_tolerated(self) -> None:
        assert canonical_binding("  ctrl + shift + k ") == "Ctrl+Shift+K"

    def test_named_keys(self) -> None:
        assert canonical_binding("ctrl+return") == "Ctrl+Enter"
        assert canonical_binding("ctrl+enter") == "Ctrl+Enter"
        assert canonical_binding("alt+esc") == "Alt+Escape"
        assert canonical_binding("shift+del") == "Shift+Delete"
        assert canonical_binding(" alt+shift+up ") == "Alt+Shift+Up"

    def test_function_keys(self) -> None:
        assert canonical_binding("f2") == "F2"
        assert canonical_binding("ctrl+F12") == "Ctrl+F12"

    def test_punctuation_keys(self) -> None:
        assert canonical_binding("ctrl+]") == "Ctrl+]"
        assert canonical_binding("ctrl+/") == "Ctrl+/"

    def test_chord_grammar(self) -> None:
        assert canonical_binding("Ctrl+Shift+Grave, S") == "Ctrl+Shift+Grave, S"
        # Order and case inside each chord segment normalise independently.
        assert canonical_binding("shift+ctrl+grave, shift+s") == "Ctrl+Shift+Grave, Shift+S"
        assert canonical_binding("ctrl+shift+`, s") == "Ctrl+Shift+Grave, S"

    def test_quill_key_alias_expands_with_prefix(self) -> None:
        assert (
            canonical_binding("quill, s", quill_key_prefix="Ctrl+Shift+Grave")
            == "Ctrl+Shift+Grave, S"
        )
        assert (
            canonical_binding("quill key, shift+s", quill_key_prefix="Ctrl+Shift+Grave")
            == "Ctrl+Shift+Grave, Shift+S"
        )

    def test_quill_key_alias_without_prefix_is_invalid(self) -> None:
        assert canonical_binding("quill, s") is None

    def test_invalid_bindings(self) -> None:
        assert parse_binding("") is None
        assert parse_binding(None) is None
        assert parse_binding("ctrl+") is None  # modifier with no key
        assert parse_binding("ctrl+shift") is None  # all modifiers, no key
        assert parse_binding("ab") is None  # multi-char non-named token
        assert parse_binding("ctrl+a+b") is None  # two keys
        assert parse_binding("a, b, c") is None  # too many chord segments


class TestEquivalenceAndConflicts:
    def test_bindings_equivalent(self) -> None:
        assert bindings_equivalent("Shift+Ctrl+K", "ctrl+shift+k")
        assert not bindings_equivalent("Ctrl+K", "Ctrl+Shift+K")
        assert not bindings_equivalent("garbage", "garbage")

    def test_find_conflicts_is_order_insensitive(self) -> None:
        keymap = {"format.bold": "Ctrl+B", "edit.foo": "Ctrl+Shift+K"}
        # Editing a third command, trying a re-ordered spelling of an existing key.
        assert find_keymap_conflicts(keymap, "edit.new", "shift+ctrl+k") == ["edit.foo"]

    def test_find_conflicts_excludes_self(self) -> None:
        keymap = {"format.bold": "Ctrl+B"}
        assert find_keymap_conflicts(keymap, "format.bold", "ctrl+b") == []

    def test_find_conflicts_returns_all(self) -> None:
        keymap = {"a": "Ctrl+B", "b": "ctrl+b", "c": "Ctrl+K"}
        assert find_keymap_conflicts(keymap, "new", "Ctrl+B") == ["a", "b"]

    def test_commands_for_keystroke(self) -> None:
        keymap = {"format.bold": "Ctrl+B", "edit.foo": "Ctrl+Shift+K"}
        assert commands_for_keystroke(keymap, "control+b") == ["format.bold"]
        assert commands_for_keystroke(keymap, "Ctrl+Q") == []


class TestDiagnostics:
    def test_duplicate_bindings(self) -> None:
        keymap = {"a": "Ctrl+B", "b": "shift+ctrl+k", "c": "Ctrl+Shift+K", "d": ""}
        dupes = duplicate_bindings(keymap)
        assert dupes == {"Ctrl+Shift+K": ["b", "c"]}

    def test_diagnose_clean_keymap(self) -> None:
        keymap = {"a": "Ctrl+B", "b": "Ctrl+K"}
        report = diagnose_keymap(keymap)
        assert report.ok
        assert report.issue_count == 0

    def test_diagnose_flags_invalid_and_unknown_and_missing(self) -> None:
        keymap = {
            "a": "Ctrl+B",
            "b": "totally bogus",
            "ghost.command": "Ctrl+G",
            "inert.command": "Ctrl+H",
        }
        report = diagnose_keymap(
            keymap,
            known_commands={"a", "b", "inert.command"},
            dispatchable_commands={"a", "b"},
        )
        assert report.invalid == {"b": "totally bogus"}
        assert report.unknown_commands == ["ghost.command"]
        assert report.missing_dispatch == ["inert.command"]
        assert not report.ok
        assert report.issue_count == 3

    def test_diagnose_unknown_command_not_double_counted_as_missing(self) -> None:
        keymap = {"ghost": "Ctrl+G"}
        report = diagnose_keymap(keymap, known_commands=set(), dispatchable_commands=set())
        assert report.unknown_commands == ["ghost"]
        assert report.missing_dispatch == []


class TestRewriteChordPrefixes:
    """The QUILL-key prefix rebind: every stored chord must follow the new prefix."""

    def test_rewrites_every_chord_under_the_old_prefix(self) -> None:
        keymap = {
            "file.save": "Ctrl+Shift+Grave, S",
            "edit.find": "Ctrl+Shift+Grave, F",
            "format.bold": "Ctrl+B",  # not a chord -- left alone
            "unused": "",
        }
        out = rewrite_chord_prefixes(keymap, old_prefix="Ctrl+Shift+Grave", new_prefix="Ctrl+Alt+Q")
        assert out["file.save"] == "Ctrl+Alt+Q, S"
        assert out["edit.find"] == "Ctrl+Alt+Q, F"
        assert out["format.bold"] == "Ctrl+B"
        assert out["unused"] == ""

    def test_does_not_mutate_input(self) -> None:
        keymap = {"file.save": "Ctrl+Shift+Grave, S"}
        rewrite_chord_prefixes(keymap, old_prefix="Ctrl+Shift+Grave", new_prefix="Ctrl+Alt+Q")
        assert keymap["file.save"] == "Ctrl+Shift+Grave, S"

    def test_preserves_second_key_modifiers(self) -> None:
        keymap = {"power.command": "Ctrl+Shift+Grave, Shift+O"}
        out = rewrite_chord_prefixes(keymap, old_prefix="Ctrl+Shift+Grave", new_prefix="Ctrl+Alt+Q")
        assert out["power.command"] == "Ctrl+Alt+Q, Shift+O"

    def test_canonicalises_non_canonical_saved_chord(self) -> None:
        # A saved chord spelled "Shift+Ctrl+Grave, S" (modifiers out of order)
        # still moves with the prefix because it is canonicalised first.
        keymap = {"file.save": "Shift+Ctrl+Grave, S"}
        out = rewrite_chord_prefixes(keymap, old_prefix="Ctrl+Shift+Grave", new_prefix="Ctrl+Alt+Q")
        assert out["file.save"] == "Ctrl+Alt+Q, S"

    def test_chord_under_a_different_prefix_is_left_alone(self) -> None:
        keymap = {"other": "Ctrl+Alt+K, X"}
        out = rewrite_chord_prefixes(keymap, old_prefix="Ctrl+Shift+Grave", new_prefix="Ctrl+Alt+Q")
        assert out["other"] == "Ctrl+Alt+K, X"

    def test_quill_alias_query_parses_to_the_bare_prefix(self) -> None:
        # The keymap-editor search bug: typing "quill" must parse as the bare
        # prefix (one segment, not a chord) so the editor can list chord commands
        # instead of matching nothing.
        parsed = parse_binding("quill", quill_key_prefix="Ctrl+Shift+Grave")
        assert parsed is not None
        assert not parsed.is_chord
        assert len(parsed.segments) == 1
        assert parsed.canonical == "Ctrl+Shift+Grave"
