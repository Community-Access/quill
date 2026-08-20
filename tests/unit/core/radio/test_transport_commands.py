"""One transport, one set of keys, every window of Radio and Cast.

The reports these pin down (2026-08-18):

* *"the speed stuff isn't working in the player in the browse window"* -- the
  transport was menu items on the main frame, and a menu accelerator only fires
  for the frame that owns the menu bar.
* *"the ctrl+alt plus arrow keys is going to conflict with table nav"* -- and
  they did: speed and chapters shipped on Ctrl+Alt+Up/Down/Left/Right.
* *"we need one player and it needs to react accordingly with global keystrokes
  throughout the app"* -- in-app, not taken from the rest of Windows.
"""

from __future__ import annotations

from enum import Enum, auto

from quill.core.radio import transport_commands as tc


def test_no_verb_claims_a_key_twice() -> None:
    keys = [command.key for command in tc.COMMANDS]

    assert len(keys) == len(set(keys)), sorted(keys)


def test_nothing_lands_on_ctrl_alt_arrow() -> None:
    """QUILL's table navigation owns that block.

    A transport key there works everywhere except while somebody is reading a
    table, which is the kind of "works for me" bug that never gets reported
    with a reproduction.
    """
    forbidden = {"Ctrl+Alt+Up", "Ctrl+Alt+Down", "Ctrl+Alt+Left", "Ctrl+Alt+Right"}

    assert not [c for c in tc.COMMANDS if c.key in forbidden]


def test_every_verb_names_something_and_says_what_it_needs() -> None:
    for command in tc.COMMANDS:
        assert command.id.startswith("transport."), command.id
        assert command.verb, command.id
        assert "&" in command.label, command.label


def test_speed_and_chapters_refuse_on_live_radio_in_words() -> None:
    # Not silently: a key that does nothing is indistinguishable from one that
    # is not bound, and the browse window is exactly where somebody would
    # conclude the feature is broken.
    for command_id in (tc.SPEED_UP, tc.NEXT_CHAPTER, tc.CHAPTER_LIST, tc.SKIP_FORWARD):
        assert not tc.available(command_id, playing=True, bounded=False)
        assert "live radio" in tc.refusal(command_id, playing=True, bounded=False)


def test_speed_and_chapters_are_available_on_a_recording() -> None:
    for command_id in (tc.SPEED_UP, tc.NEXT_CHAPTER, tc.CHAPTER_LIST, tc.SKIP_FORWARD):
        assert tc.available(command_id, playing=True, bounded=True)
        assert tc.refusal(command_id, playing=True, bounded=True) == ""


def test_volume_and_play_work_with_nothing_playing() -> None:
    # Turning the volume down before starting something, and pressing Play at
    # all, must not require something to already be playing.
    for command_id in (tc.VOLUME_UP, tc.VOLUME_DOWN, tc.MUTE, tc.PLAY_PAUSE, tc.GO_TO_PLAYER):
        assert tc.available(command_id, playing=False, bounded=False)


def test_stop_says_nothing_is_playing_rather_than_stopping_nothing() -> None:
    assert tc.refusal(tc.STOP, playing=False, bounded=False) == "Nothing is playing."


def test_the_controller_verbs_are_named_as_the_controller_names_them() -> None:
    """These three resolve straight onto the player with no adapter.

    If the controller is renamed, this fails here rather than by a key quietly
    doing nothing in a window nobody tested.
    """
    from quill.ui.radio.player_controller import RadioPlayerController

    for command_id in (tc.PLAY_PAUSE, tc.STOP, tc.MUTE):
        verb = tc.command(command_id).verb
        assert callable(getattr(RadioPlayerController, verb, None)), verb


def test_the_bounded_verbs_exist_in_the_shared_playback_module() -> None:
    from quill.ui.radio import bounded_playback_ui

    for command in tc.COMMANDS:
        if not command.needs_bounded:
            continue
        assert callable(getattr(bounded_playback_ui, command.verb, None)), command.verb


def test_keymap_defaults_cover_every_command() -> None:
    defaults = tc.keymap_defaults()

    assert set(defaults) == {command.id for command in tc.COMMANDS}
    assert all(defaults.values())


def test_quill_cast_implements_every_verb_the_table_names() -> None:
    """Cast had the whole transport already -- just no way to reach it.

    Its player has a different shape from Radio's, so the dispatcher routes to
    Cast's own ``podcast_*`` methods before it reaches Radio's shared ones. This
    fails if the table gains a verb Cast cannot do, or if one of Cast's methods
    is renamed out from under the alias table.
    """
    import pytest

    pytest.importorskip("wx")
    from quill.apps.podcasts import PodcastsAppFrame
    from quill.ui.radio import transport_keys

    # Verbs Cast genuinely has no equivalent for; they fall through to the
    # shared implementation or say so out loud, which is the honest answer.
    without = {"go_to_player", "open_chapters", "open_command_palette"}
    missing = []
    for command in tc.COMMANDS:
        if command.verb in without:
            continue
        name = transport_keys._CAST_VERB_ALIASES.get(command.verb, f"podcast_{command.verb}")
        if not callable(getattr(PodcastsAppFrame, name, None)):
            missing.append(f"{command.id} -> {name}")

    assert not missing, "Cast cannot perform: " + ", ".join(missing)


def test_the_palette_can_run_every_transport_verb() -> None:
    """The palette could change a setting and could not pause what was playing.

    Registering the table means a palette entry, a keystroke, a menu item and a
    button are four doors into one implementation -- refusals included.
    """
    from quill.ui.radio import transport_keys

    class _Registry:
        def __init__(self) -> None:
            self.registered: dict[str, str] = {}

        def register(self, command_id, title, handler, keybinding=None, feature_id=None):
            if command_id in self.registered:
                raise ValueError(command_id)
            self.registered[command_id] = keybinding or ""

    class _Host:
        def __init__(self) -> None:
            self.commands = _Registry()

    host = _Host()
    count = transport_keys.register_commands(host, prefix="radio")

    # Everything but the palette itself: an entry that opens the list you are
    # looking at is noise in that list.
    expected = {c.id for c in tc.COMMANDS} - {tc.COMMAND_PALETTE}
    assert count == len(expected)
    assert set(host.commands.registered) == {f"radio.{cid}" for cid in expected}
    # Each entry advertises the same key the menus and accelerators use.
    assert host.commands.registered[f"radio.{tc.NEXT_CHAPTER}"] == tc.command(tc.NEXT_CHAPTER).key


def test_a_verb_the_app_already_lists_is_not_listed_twice() -> None:
    """Quill Cast already had most of the transport in its palette by name.

    A second entry for the same verb leaves two identical-sounding rows in a
    list somebody arrows through, which is worse than the gap it filled. The
    app's own entry wins; the shared table fills only what is missing.
    """
    from quill.ui.radio import transport_keys

    class _Registry:
        def __init__(self) -> None:
            self._commands = {"podcasts.next_chapter": object(), "podcasts.mute_toggle": object()}

        def register(self, command_id, title, handler, keybinding=None, feature_id=None):
            self._commands[command_id] = handler

    class _Host:
        def __init__(self) -> None:
            self.commands = _Registry()

    host = _Host()
    transport_keys.register_commands(host, prefix="podcasts")

    added = set(host.commands._commands)
    assert f"podcasts.{tc.NEXT_CHAPTER}" not in added  # already listed as next_chapter
    assert f"podcasts.{tc.MUTE}" not in added  # already listed as mute_toggle
    assert f"podcasts.{tc.CHAPTER_LIST}" in added  # a genuine gap


def test_registering_twice_is_not_an_error() -> None:
    # A second frame, or an app that already registered one of these ids: the
    # first wins, and a duplicate must never take a window down at startup.
    from quill.ui.radio import transport_keys

    class _Registry:
        def __init__(self) -> None:
            self._commands: dict[str, object] = {}

        def register(self, command_id, title, handler, keybinding=None, feature_id=None):
            if command_id in self._commands:
                raise ValueError(command_id)
            self._commands[command_id] = handler

    class _Host:
        def __init__(self) -> None:
            self.commands = _Registry()

    host = _Host()
    transport_keys.register_commands(host, prefix="radio")

    assert transport_keys.register_commands(host, prefix="radio") == 0


def test_the_palette_is_reachable_from_every_window() -> None:
    """It was on each app's Help menu, so only the main window could open it.

    The same shape the transport had: a palette you can summon from one place
    is a palette you go to rather than one you use.
    """
    palette = tc.command(tc.COMMAND_PALETTE)

    assert palette is not None
    assert palette.key == "Ctrl+Shift+P"
    assert not palette.needs_playing


# --- the two players have two state shapes, and one gate in front of both -----


class _CastPhase:
    """Stands in for ``PodcastPlayerState``: an enum whose ``.name`` is read."""

    def __init__(self, name: str) -> None:
        self.name = name


class _CastState:
    """The shape of ``PodcastPlaybackState``. Note: no ``station`` field."""

    def __init__(self, phase: str = "PLAYING", title: str = "Episode 7") -> None:
        self.state = _CastPhase(phase)
        self.show_id = "show-1"
        self.episode_guid = "guid-1"
        self.title = title


class _CastController:
    """The shape of ``PodcastPlayerController``: volume and rate on itself."""

    def __init__(self, phase: str = "PLAYING", volume: int = 40) -> None:
        self.state = _CastState(phase)
        self.volume_percent = volume
        self.muted = False
        self.rate = 1.5
        self.volume_calls: list[int] = []

    def set_volume(self, percent: int) -> None:
        self.volume_percent = percent
        self.volume_calls.append(percent)

    def position_ms(self) -> int:
        return 65_000

    def length_ms(self) -> int:
        return 600_000


class _CastFrame:
    """The shape of ``PodcastsAppFrame`` as the dispatcher sees it."""

    def __init__(self, controller: _CastController) -> None:
        self._podcast_controller = controller
        self.said: list[str] = []
        self.did: list[str] = []

    def _announce(self, message: str) -> None:
        self.said.append(message)

    def podcast_stop(self) -> None:
        self.did.append("stop")

    def podcast_skip_forward(self) -> None:
        self.did.append("skip_forward")

    def podcast_speed_up(self) -> None:
        self.did.append("speed_up")

    def podcast_next_chapter(self) -> None:
        self.did.append("next_chapter")

    def podcast_player_information(self) -> None:
        self.did.append("where_am_i")


def test_cast_can_reach_its_own_transport_while_an_episode_plays() -> None:
    """The regression: every gated verb refused mid-episode in Quill Cast.

    ``_state`` asked ``controller.state.station`` -- Radio's field, which Cast's
    ``PodcastPlaybackState`` does not have -- so it answered "nothing is
    playing" and ``perform`` refused before it ever reached the ``podcast_*``
    method the alias table points at. Stop, skip, speed, chapters and Where Am I
    were all dead in Cast while an episode played.

    The sibling test above checks those methods *exist*. This one checks they
    can be *reached*, which is the half that shipped broken.
    """
    from quill.ui.radio import transport_keys

    frame = _CastFrame(_CastController())

    assert transport_keys._state(frame) == (True, True)
    for command_id in (tc.STOP, tc.SKIP_FORWARD, tc.SPEED_UP, tc.NEXT_CHAPTER):
        assert transport_keys.perform(frame, command_id), command_id
    assert frame.did == ["stop", "skip_forward", "speed_up", "next_chapter"]
    assert frame.said == []


def test_a_stopped_cast_player_still_refuses_out_loud() -> None:
    """The fix must not make every verb always available -- only reachable."""
    from quill.ui.radio import transport_keys

    frame = _CastFrame(_CastController(phase="STOPPED"))

    assert transport_keys._state(frame) == (False, False)
    assert not transport_keys.perform(frame, tc.STOP)
    assert frame.said == ["Nothing is playing."]
    assert frame.did == []


def test_a_paused_episode_can_still_be_stopped_and_moved_through() -> None:
    """Paused is not stopped: the verbs a listener reaches for still apply."""
    from quill.ui.radio import transport_keys

    frame = _CastFrame(_CastController(phase="PAUSED"))

    assert transport_keys.perform(frame, tc.SKIP_FORWARD)
    assert frame.did == ["skip_forward"]


def test_cast_volume_steps_from_the_level_the_listener_set() -> None:
    """Cast keeps volume on the controller, not on the state.

    Reading only ``state.volume_percent`` fell back to a default of 100, so
    Volume Down from 40 percent jumped *up* to 95.
    """
    from quill.ui.radio import transport_keys

    controller = _CastController(volume=40)
    frame = _CastFrame(controller)

    assert transport_keys.perform(frame, tc.VOLUME_DOWN)
    assert controller.volume_calls == [40 - transport_keys.VOLUME_STEP]


def test_the_readout_speaks_both_players() -> None:
    """The panel is summoned from both apps; its readout knew only Radio.

    Cast fell into the "Playing." catch-all -- no title, no position, no volume
    -- which is the one thing a panel of twelve unlabelled verbs cannot afford.
    """
    from quill.ui.radio import transport_keys

    text = transport_keys.describe_now_playing(_CastFrame(_CastController()))

    assert "Episode 7" in text
    assert "of 10 minutes" in text
    assert "Speed 1.5 times normal." in text
    assert "Volume 40 percent." in text


def test_the_readout_says_nothing_is_playing_rather_than_guessing() -> None:
    from quill.ui.radio import transport_keys

    assert (
        transport_keys.describe_now_playing(_CastFrame(_CastController(phase="STOPPED")))
        == "Nothing is playing."
    )


# --- the panel, the context menu, and the table they all render --------------


def test_the_player_panel_offers_every_verb_the_table_names() -> None:
    """A verb added to the table must not silently miss the panel.

    The table already has tests for duplicate keys, for Ctrl+Alt+arrow, for
    Cast's methods and for palette double-listing. The panel had none, and it
    was already missing Where Am I.
    """
    import pytest

    pytest.importorskip("wx")
    from quill.ui.radio import player_panel

    on_panel = {command_id for command_id, _label in player_panel.BUTTONS}
    expected = {c.id for c in tc.COMMANDS} - player_panel.NOT_BUTTONS

    assert on_panel == expected


def test_no_two_player_panel_buttons_claim_the_same_mnemonic() -> None:
    """A repeated mnemonic in a dialog cycles focus instead of pressing.

    Previous Chapter and Faster both held T, and Slower and Volume Down both
    held W -- four buttons whose Alt key did not press them.
    """
    import pytest

    pytest.importorskip("wx")
    from quill.ui.radio import player_panel

    labels = [label for _cid, label in player_panel.BUTTONS] + ["Cl&ose"]
    mnemonics = [label.split("&", 1)[1][0].lower() for label in labels if "&" in label]

    assert len(mnemonics) == len(labels), labels
    assert len(mnemonics) == len(set(mnemonics)), sorted(mnemonics)


def test_the_context_menu_teaches_the_keystroke_it_has() -> None:
    """The playing row's verbs have keys; the menu never said so.

    A row-level Play or Stop must *not* be labelled with the player's Ctrl+P --
    it plays that station rather than toggling what is already going.
    """
    from quill.core.radio import row_actions

    playing = row_actions.playing_actions(has_chapters=True, has_captions=True)
    labelled = {action.id: row_actions.menu_label(action) for action in playing}

    assert labelled[row_actions.PLAYING_WHERE].endswith("\tCtrl+Shift+W")
    assert labelled[row_actions.PLAYING_NEXT_CHAPTER].endswith("\tCtrl+Shift+.")
    assert "\t" not in labelled[row_actions.TOGGLE_CAPTIONS]
    row_stop = row_actions.transport_actions(playing=True, downloaded=False)[0]
    assert "\t" not in row_actions.menu_label(row_stop)


# --- the player panel is a window too, so the keys must work in it ------------


class _FakeEntry:
    def __init__(self, cmd: int) -> None:
        self.cmd = cmd
        self._code = 0

    def FromString(self, text: str) -> bool:
        self._code = 1
        return True

    def GetKeyCode(self) -> int:
        return self._code


class _FakeIdRef:
    def __init__(self, value: int) -> None:
        self.value = value

    def __int__(self) -> int:
        return self.value


class _FakeWx:
    """Enough wx for ``install``: entries, id refs, Bind and a table."""

    EVT_MENU = object()

    def __init__(self) -> None:
        self._next_id = 100

    def AcceleratorEntry(self, cmd: int) -> _FakeEntry:  # noqa: N802 - wx spelling
        return _FakeEntry(cmd)

    def NewIdRef(self) -> _FakeIdRef:  # noqa: N802 - wx spelling
        self._next_id += 1
        return _FakeIdRef(self._next_id)

    def AcceleratorTable(self, entries: list[_FakeEntry]) -> list[_FakeEntry]:  # noqa: N802
        return entries


class _FakeWindow:
    def __init__(self) -> None:
        self.handlers: dict[int, object] = {}
        self.table: list[_FakeEntry] = []

    def Bind(self, _event: object, handler: object, id: int = 0) -> None:  # noqa: A002, N802
        self.handlers[id] = handler

    def SetAcceleratorTable(self, table: list[_FakeEntry]) -> None:  # noqa: N802
        self.table = table


def test_a_key_pressed_in_a_window_lets_that_window_catch_up() -> None:
    """``install``'s ``after`` hook, which the player panel's readout needs.

    A modal dialog has no accelerator table of its own, so the panel was the one
    window in the app where Ctrl+P did nothing while it did something in every
    window behind it. Installing the keys there means a key must leave the panel
    saying what a button would -- which is what ``after`` is for.
    """
    from quill.ui.radio import transport_keys

    wx = _FakeWx()
    window = _FakeWindow()
    frame = _CastFrame(_CastController())
    refreshed: list[int] = []

    landed = transport_keys.install(window, frame, wx=wx, after=lambda: refreshed.append(1))

    assert landed == len(tc.COMMANDS)
    assert len(window.table) == len(tc.COMMANDS)
    first_bound = window.handlers[next(iter(window.handlers))]
    first_bound(None)  # type: ignore[operator]
    assert refreshed == [1]


def test_a_refused_key_still_lets_the_window_catch_up() -> None:
    """``after`` runs on a refusal too: the state may have changed elsewhere."""
    from quill.ui.radio import transport_keys

    frame = _CastFrame(_CastController(phase="STOPPED"))
    refreshed: list[int] = []

    assert not transport_keys._fire(frame, tc.STOP, lambda: refreshed.append(1))
    assert frame.said == ["Nothing is playing."]
    assert refreshed == [1]


def test_go_to_player_from_inside_the_player_says_so_instead_of_stacking() -> None:
    """The keys work in the panel, so Go to Player is pressable from it.

    A second modal over the first is a trap -- closing one leaves you in the
    other, having pressed nothing to get there -- and doing nothing is how a key
    teaches somebody it is broken.
    """
    import pytest

    pytest.importorskip("wx")
    from quill.ui.radio import player_panel

    said: list[str] = []

    class _Host:
        def _announce(self, message: str) -> None:
            said.append(message)

    player_panel._OPEN = object()  # type: ignore[assignment] - only identity is read
    try:
        player_panel.summon(_Host(), parent=object())
    finally:
        player_panel._OPEN = None

    assert said == ["You are already in the player."]


# --- one volume, one sentence, and no silent success --------------------------


class _RadioPhase(Enum):
    STOPPED = auto()
    CONNECTING = auto()
    PLAYING = auto()
    PAUSED = auto()
    ERROR = auto()


class _RadioStation:
    display_name = "WNYC"
    is_recording = False


class _RadioState:
    def __init__(self) -> None:
        self.state = _RadioPhase.PLAYING
        self.station = _RadioStation()
        self.muted = False
        self.volume_percent = 50


class _RadioController:
    """``RadioPlayerController``'s shape: its own stepper, which clears mute."""

    def __init__(self) -> None:
        self.state = _RadioState()

    def toggle_play_pause(self) -> None:
        self.state.state = (
            _RadioPhase.PAUSED if self.state.state is _RadioPhase.PLAYING else _RadioPhase.PLAYING
        )

    def stop(self) -> None:
        self.state.state = _RadioPhase.STOPPED

    def toggle_mute(self) -> None:
        self.state.muted = not self.state.muted

    def set_volume(self, percent: int) -> None:
        self.state.volume_percent = max(0, min(100, percent))

    def volume_up(self, step: int = 10) -> None:
        self.state.muted = False
        self.set_volume(self.state.volume_percent + step)

    def volume_down(self, step: int = 10) -> None:
        self.state.muted = False
        self.set_volume(self.state.volume_percent - step)


class _RadioFrame:
    def __init__(self) -> None:
        self._radio_controller = _RadioController()
        self.said: list[str] = []

    def _announce(self, message: str) -> None:
        self.said.append(message)


def test_play_pause_stop_and_mute_are_not_silent() -> None:
    """This module's stated law, applied to the verbs that could act.

    The refusal path honoured it; the success path did not. ``toggle_play_pause``,
    ``stop`` and ``toggle_mute`` are not in ``bounded_playback_ui``, so they
    reached the controller and said nothing -- in the browse tree, the player
    panel and Cast's manager, while the same verbs announced from the main
    window. Mute was the worst: silence is the intended effect, so "did it mute
    or did the stream drop?" had no answer.
    """
    from quill.ui.radio import transport_keys

    frame = _RadioFrame()
    for command_id in (tc.PLAY_PAUSE, tc.STOP, tc.MUTE):
        assert transport_keys.perform(frame, command_id), command_id
    assert frame.said == ["Paused.", "Stopped.", "Muted."]


def test_volume_up_while_muted_makes_a_sound() -> None:
    """It announced a level the listener could not hear.

    ``RadioPlayerController.volume_up`` clears mute before stepping; the copy of
    that arithmetic in this module did not, so the engine stayed at zero while
    the key reported "Volume 5 percent."
    """
    from quill.ui.radio import transport_keys

    frame = _RadioFrame()
    transport_keys.perform(frame, tc.MUTE)
    transport_keys.perform(frame, tc.VOLUME_UP)

    assert frame._radio_controller.state.muted is False
    assert frame.said == ["Muted.", "Volume 60 percent."]


def test_the_players_own_stepper_wins_so_one_key_moves_one_distance() -> None:
    """It was 5 here and 10 in the controller, chosen by which window had focus."""
    from quill.ui.radio import transport_keys

    frame = _RadioFrame()
    transport_keys.perform(frame, tc.VOLUME_DOWN)

    assert frame._radio_controller.state.volume_percent == 40  # the controller's step, not ours
    assert transport_keys.VOLUME_STEP == 10  # and the fallback matches it


def test_one_sentence_describes_the_volume() -> None:
    """Three readings of one fact -- "Radio volume 45", "Volume 45", and this."""
    from quill.ui.radio import transport_keys

    controller = _RadioController()

    assert transport_keys.describe_volume(controller) == "Volume 50 percent."
    controller.set_volume(0)
    assert transport_keys.describe_volume(controller) == "Volume off."
    controller.state.muted = True
    assert transport_keys.describe_volume(controller) == "Muted."
