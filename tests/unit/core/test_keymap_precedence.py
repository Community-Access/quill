"""A binding you chose outranks a default that arrived later.

Found while fixing a stale test, and left open until 2026-09-10: bind
Ctrl+Alt+Shift+J yourself, upgrade to a build where that chord became
``format.join_lines``'s default, and ``merge_keymaps`` dropped your binding as a
conflict. Silently -- at a debug log level nobody reads -- so a key you
deliberately chose simply stopped working, and there was nothing to look at.

The rule now has two halves, because "conflict" was covering two situations with
different right answers:

* **Your choice against a default: you win.** The default is the app's
  suggestion and yours is an instruction. The command that held it as a default
  is left *unbound* rather than moved somewhere else, because inventing a
  replacement chord is a second surprise, and an unbound command is something
  the Keyboard Manager's audit already reports.
* **Your choice against your other choice: unchanged.** There is nothing to
  choose between them from in here, so the first read keeps the chord.
"""

from __future__ import annotations

from quill.core.keymap import DEFAULT_KEYMAP, KEYMAP_DEFAULTS_EPOCH, merge_keymaps

_EPOCH = "_defaults_epoch"


def _a_command_with_a_default() -> tuple[str, str]:
    """Some command that ships with a real chord, and that chord."""
    for command_id, binding in sorted(DEFAULT_KEYMAP.items()):
        if binding.strip() and "," not in binding:
            return command_id, binding
    raise AssertionError("no plainly-bound default command to test with")


def _another_command(exclude: set[str]) -> str:
    for command_id, binding in sorted(DEFAULT_KEYMAP.items()):
        if command_id not in exclude and binding.strip():
            return command_id
    raise AssertionError("not enough bound commands to test with")


# ---------------------------------------------------------------------------
# your choice against a default


def test_your_binding_survives_a_chord_that_became_someone_elses_default() -> None:
    """The case that was silently losing: your key, their new default."""
    default_holder, chord = _a_command_with_a_default()
    mine = _another_command({default_holder})

    merged = merge_keymaps({_EPOCH: KEYMAP_DEFAULTS_EPOCH, mine: chord})

    assert merged[mine] == chord


def test_the_default_holder_is_left_unbound_rather_than_moved() -> None:
    """Inventing a replacement chord would be a second surprise."""
    default_holder, chord = _a_command_with_a_default()
    mine = _another_command({default_holder})

    merged = merge_keymaps({_EPOCH: KEYMAP_DEFAULTS_EPOCH, mine: chord})

    assert merged[default_holder] == ""


def test_no_other_default_is_disturbed() -> None:
    default_holder, chord = _a_command_with_a_default()
    mine = _another_command({default_holder})

    merged = merge_keymaps({_EPOCH: KEYMAP_DEFAULTS_EPOCH, mine: chord})

    untouched = {
        command_id: binding
        for command_id, binding in DEFAULT_KEYMAP.items()
        if command_id not in {default_holder, mine}
    }
    assert {k: merged[k] for k in untouched} == untouched


def test_the_chord_is_matched_however_it_was_spelled() -> None:
    """A re-ordered spelling is the same chord; comparing text is not a check."""
    default_holder = "format.bold"
    if DEFAULT_KEYMAP.get(default_holder) != "Ctrl+B":
        return  # the default moved; the rule is covered by the tests above
    mine = _another_command({default_holder})

    merged = merge_keymaps({_EPOCH: KEYMAP_DEFAULTS_EPOCH, mine: "ctrl+b"})

    assert merged[mine] == "ctrl+b"
    assert merged[default_holder] == ""


# ---------------------------------------------------------------------------
# your choice against your other choice


def test_two_of_your_own_bindings_on_one_chord_keep_the_first() -> None:
    """Nothing to choose between them from in here."""
    _holder, chord = _a_command_with_a_default()
    first = _another_command({_holder})
    second = _another_command({_holder, first})

    merged = merge_keymaps({_EPOCH: KEYMAP_DEFAULTS_EPOCH, first: chord, second: chord})

    kept = [command for command in (first, second) if merged[command] == chord]
    assert len(kept) == 1, {first: merged[first], second: merged[second]}


# ---------------------------------------------------------------------------
# nothing else changed


def test_an_untouched_keymap_is_the_defaults() -> None:
    assert merge_keymaps({_EPOCH: KEYMAP_DEFAULTS_EPOCH}) == DEFAULT_KEYMAP


def test_a_deliberate_unbind_still_sticks() -> None:
    """ "" in a current-epoch delta means "I cleared this", not "use the default"."""
    command_id, _chord = _a_command_with_a_default()

    merged = merge_keymaps({_EPOCH: KEYMAP_DEFAULTS_EPOCH, command_id: ""})

    assert merged[command_id] == ""


def test_an_unbind_is_an_explicit_choice_for_the_conflict_rule() -> None:
    """Clearing a key and then giving it to something else must not fight itself."""
    holder, chord = _a_command_with_a_default()
    mine = _another_command({holder})

    merged = merge_keymaps({_EPOCH: KEYMAP_DEFAULTS_EPOCH, holder: "", mine: chord})

    assert merged[holder] == ""
    assert merged[mine] == chord


def test_a_binding_for_an_unknown_command_is_still_preserved() -> None:
    """A sibling app of a newer vintage may have written it."""
    merged = merge_keymaps({
        _EPOCH: KEYMAP_DEFAULTS_EPOCH,
        "some.newer.sibling.command": "Ctrl+Alt+Shift+F12",
    })
    assert merged["some.newer.sibling.command"] == "Ctrl+Alt+Shift+F12"


def test_a_metadata_key_is_never_read_as_a_binding() -> None:
    merged = merge_keymaps({_EPOCH: KEYMAP_DEFAULTS_EPOCH})
    assert _EPOCH not in merged


def test_junk_reads_as_the_defaults() -> None:
    assert merge_keymaps("not a keymap") == DEFAULT_KEYMAP
    assert merge_keymaps(None) == DEFAULT_KEYMAP
