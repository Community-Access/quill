"""A verb in the transport table means the same thing in both players (12.1).

The table was already enforcing this and nobody had said so. Adding Skip
Silence to it obliged QUILL Cast to implement Skip Silence, because a parity
test went red -- the right outcome, reached by the gate's decision rather than
anybody's. So the rule is now written down in
:mod:`quill.core.radio.transport_commands`, and this is the test that makes it
a rule instead of a habit.

The rule has a sharp edge, which is why it is worth having: **a row costs an
implementation in two apps**. There is no "Radio only" field, and adding one
would be the beginning of the two apps disagreeing about what Ctrl+Shift+Up
does -- the drift the shared table exists to end.

Writing it down found a hole immediately. Ctrl+Shift+P (Command Palette) was
installed on every window of both apps and resolved to *nothing anywhere*: no
host defines ``transport_open_command_palette``, Cast has no
``podcast_open_command_palette``, and it is not a player verb. It was a key on
every window that did nothing, silently, in both apps -- and the "both apps"
part is exactly why no app-specific test could have caught it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.radio import transport_commands as tc
from quill.ui.radio import transport_keys as tk

REPO = Path(__file__).resolve().parents[3]

#: Verbs implemented inside :mod:`transport_keys` itself, for both apps at
#: once. They are here rather than in a player because they are about the
#: *window*: stepping a volume the controller has no stepper for, and summoning
#: a player panel that belongs to no window.
_IN_THE_DISPATCHER = frozenset({"volume_up", "volume_down", "go_to_player"})


def _text(*relative: str) -> str:
    return "\n".join(
        (REPO / part).read_text(encoding="utf-8", errors="replace") for part in relative
    )


def _cast_sources() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in sorted(REPO.glob("quill/ui/podcasts/*.py"))
        + sorted(REPO.glob("quill/ui/main_frame_podcast*.py"))
    )


def _radio_sources() -> str:
    return _text("quill/ui/radio/player_controller.py")


def _shell_sources() -> str:
    """The frame both apps are built on -- a verb defined here serves both."""
    return _text("quill/ui/app_shell.py")


def _shared_sources() -> str:
    """``bounded_playback_ui`` is app-neutral by construction: its
    ``_controller`` resolves Radio's ``_radio_controller``, a modeless
    surface's ``_controller`` *and* Cast's ``_podcast_controller``, so a verb
    implemented there is implemented for both apps at once. That neutrality is
    asserted below rather than trusted -- it is the reason a verb can be
    honoured in Cast with no ``podcast_*`` method of its own."""
    return _text("quill/ui/radio/bounded_playback_ui.py")


@pytest.mark.parametrize("command", tc.COMMANDS, ids=lambda c: c.id)
def test_quill_cast_can_perform_every_verb(command: tc.TransportCommand) -> None:
    """Half the contract: pressing the key in Cast does the thing."""
    if command.verb in _IN_THE_DISPATCHER:
        return
    name = tk._CAST_VERB_ALIASES.get(command.verb, f"podcast_{command.verb}")

    served = (
        f"def {name}(" in _cast_sources()
        or f"def {command.verb}(" in _shared_sources()
        or f"def {command.verb}(" in _shell_sources()
    )

    assert served, (
        f"{command.id} is in the shared table, so Quill Cast owes it an "
        f"implementation: def {name}(...), or a shared one in "
        "bounded_playback_ui. A row only one app honours is the drift the "
        "table exists to end -- either implement it, or take the verb out of "
        "the table and put it in Radio's own menu."
    )


@pytest.mark.parametrize("command", tc.COMMANDS, ids=lambda c: c.id)
def test_quill_radio_can_perform_every_verb(command: tc.TransportCommand) -> None:
    """The other half, and the one that used to be assumed: a verb reaches
    ``bounded_playback_ui``, the radio controller, or the shared shell."""
    if command.verb in _IN_THE_DISPATCHER:
        return

    served = (
        f"def {command.verb}(" in _shared_sources()
        or f"def {command.verb}(" in _radio_sources()
        or f"def {command.verb}(" in _shell_sources()
    )

    assert served, (
        f"{command.id} resolves to nothing in Quill Radio. transport_keys."
        "perform would fall through every candidate and announce 'That is not "
        "available in this window' -- for a key installed on every window."
    )


def test_the_shared_implementations_really_are_app_neutral() -> None:
    """What lets a shared verb count for Cast: one resolver, three host
    shapes. If this narrows, every verb Cast relies on the shared path for
    goes quiet in Cast and nothing else here would notice."""
    source = _shared_sources()

    for shape in ("_radio_controller", "_controller", "_podcast_controller"):
        assert f'getattr(host, "{shape}", None)' in source, (
            f"bounded_playback_ui no longer resolves {shape}"
        )


def test_the_dispatcher_verbs_are_really_in_the_dispatcher() -> None:
    """The exemption above has to be earned, or it becomes a place to hide a
    verb that nothing implements."""
    source = _text("quill/ui/radio/transport_keys.py")

    for verb in _IN_THE_DISPATCHER:
        assert f'verb == "{verb}"' in source, f"{verb} claims an exemption it does not use"


def test_the_command_palette_reaches_a_host_that_offers_one() -> None:
    """The hole this test found, closed and pinned.

    Ctrl+Shift+P was bound on every window of both apps and resolved to
    nothing. The palette is the app shell's, not the player's, so the verb is
    looked up on the host by name -- and only for the verbs that are genuinely
    the window's, since a frame with a method called ``stop`` must not quietly
    take Stop away from the player.
    """
    opened: list[str] = []

    class Shell:
        def open_command_palette(self) -> None:
            opened.append("palette")

    assert tk.perform(Shell(), tc.COMMAND_PALETTE) is True
    assert opened == ["palette"]


def test_the_palette_is_found_from_a_modeless_window_too() -> None:
    """Half the original bug in miniature.

    A modeless surface is its own host -- the browse tree passes ``self`` to
    ``install`` -- and the palette belongs to the app frame, which that
    surface knows as ``_download_host``. Fixing only the frame case would have
    left Ctrl+Shift+P working on the main window and silent in Browse, which
    is precisely the "works for me" bug the shared transport exists to end.
    """
    opened: list[str] = []

    class Frame:
        def open_command_palette(self) -> None:
            opened.append("palette")

    class BrowseWindow:
        def __init__(self) -> None:
            self._download_host = Frame()

    assert tk.perform(BrowseWindow(), tc.COMMAND_PALETTE) is True
    assert opened == ["palette"]


def test_a_host_method_cannot_hijack_a_player_verb() -> None:
    """The guard on the lookup above: only declared host verbs are taken from
    the host, so ``stop`` keeps meaning "stop the player"."""
    hijacked: list[str] = []

    class Frame:
        def stop(self) -> None:  # a window's own unrelated stop()
            hijacked.append("frame")

    assert "stop" not in tk._HOST_VERBS
    tk.perform(Frame(), tc.STOP)

    assert hijacked == []


def test_the_rule_is_written_down_where_the_table_is() -> None:
    """12.1's actual ask: the property had been enforced for a while and
    stated nowhere, so it read as an accident of the tests."""
    doc = tc.__doc__ or ""

    assert "means the same thing in both players" in doc
    assert 'no "Radio only" field' in doc.replace("**", "")
