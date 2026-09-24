"""QUILL's free AI: the adapter, the three hooks, and the menu it opens with.

The hosted service's *behaviour* is tested once, in ``tests/unit/apps/test_lite_ai.py``,
against the shared module both editors run. What is QUILL-specific and therefore
tested here is the wiring: that QUILL supplies its own frame, its own editor and
its own settings to that shared code, that it does not reimplement any of the
commands, and that the AI menu opens with the free rows rather than the provider
surface.

The last one is checked against the source rather than a built menu bar because
that is what a wx-free unit test can see, and because the failure it guards
against is textual: a row quietly dropped, or a mnemonic quietly duplicated.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.ai.onboarding import EXPERIENCE_ADVANCED, EXPERIENCE_BASIC
from quill.core.settings import Settings
from quill.ui.hosted_ai_commands import HostedAiMixin
from quill.ui.main_frame_hosted_ai import HostedAiCommandsMixin, QuillAiHost


def _source(rel: str) -> str:
    return Path(rel).read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# One capability, not two
# --------------------------------------------------------------------------- #


def test_quill_runs_the_shared_commands_rather_than_its_own() -> None:
    """QuillLite had hosted AI first; QUILL must not grow a second copy of it.

    The family rule is that the small editor is never ahead of the big one, and
    the way that rule gets broken quietly is a second implementation rather than
    a missing feature. So this asserts the *absence* of commands here: every
    ``cmd_ai_*`` QUILL answers has to come from the shared mixin.
    """
    assert issubclass(HostedAiCommandsMixin, HostedAiMixin)
    own = {
        name
        for name in vars(HostedAiCommandsMixin)
        if name.startswith("cmd_") or name.startswith("_open_ai")
    }
    assert own == set(), f"QUILL has grown its own hosted-AI commands: {sorted(own)}"


def test_main_frame_answers_all_five_hosted_ai_commands() -> None:
    from quill.ui.main_frame import MainFrame

    for name in (
        "cmd_ai_assistant",
        "cmd_ai_ask_document",
        "cmd_ai_usage",
        "cmd_ai_sign_in",
        "cmd_ai_privacy",
    ):
        assert hasattr(MainFrame, name), name


#: QuillLite handler -> QUILL command id, for all five hosted-AI commands.
_PAIRS = {
    "cmd_ai_assistant": "tools.hosted_ai_assistant",
    "cmd_ai_ask_document": "tools.hosted_ai_ask_document",
    "cmd_ai_usage": "tools.hosted_ai_usage",
    "cmd_ai_sign_in": "tools.hosted_ai_sign_in",
    "cmd_ai_privacy": "tools.hosted_ai_privacy",
}

#: The two that could not keep QuillLite's chord, and must therefore carry a
#: reviewed reason. Ctrl+Alt+Shift+F7 to F12 are the six QuillVille sibling
#: launchers in QUILL; QuillLite, being the editor on its own, has none to
#: launch, so F9 and F10 are free over there and spoken for here.
_MUST_DIVERGE = {"cmd_ai_usage", "cmd_ai_sign_in"}


def _lite_chords() -> dict[str, str]:
    from quill.core.lite.commands import COMMANDS

    return {row[3]: row[2] for row in COMMANDS if row[3]}


@pytest.mark.parametrize("handler", sorted(_PAIRS.keys() - _MUST_DIVERGE))
def test_three_hosted_ai_commands_keep_quilllites_chord(handler: str) -> None:
    """Family rule 2: the command both products have keeps the chord.

    These three were free on QUILL's side, so there was nothing to arbitrate --
    a person who learned Ctrl+Alt+G in QuillLite has learned it in QUILL.
    """
    from quill.core.keymap import DEFAULT_KEYMAP

    assert DEFAULT_KEYMAP[_PAIRS[handler]] == _lite_chords()[handler]


@pytest.mark.parametrize("handler", sorted(_MUST_DIVERGE))
def test_the_two_that_diverge_say_why_and_stay_off_the_launcher_row(handler: str) -> None:
    """A divergence is allowed; an unexplained one is not (family rule 11).

    And the thing it must not do is sit on a launcher key: a chord claimed twice
    means one of the pair silently never fires, and nothing announces the loss.
    """
    from quill.core.app_keymaps import SIBLING_APP_ACCELERATORS
    from quill.core.keymap import DEFAULT_KEYMAP
    from quill.core.lite.parity import DIVERGENCES

    quill_chord = DEFAULT_KEYMAP[_PAIRS[handler]]
    assert quill_chord != _lite_chords()[handler], "no divergence to explain"
    assert quill_chord not in SIBLING_APP_ACCELERATORS
    reason = DIVERGENCES.get(handler, "")
    assert reason, f"{handler} diverges with no row in lite/parity.py DIVERGENCES"
    assert "launcher" in reason, "the reason must name the actual obstacle"


def test_quilllite_still_uses_the_launcher_row_for_those_two() -> None:
    """The divergence is QUILL's, not QuillLite's: nothing moved over there.

    Worth pinning, because the tempting "fix" for a divergence is to change both
    sides -- which would take a key away from people already using it, to buy a
    symmetry only this test can see.
    """
    from quill.core.app_keymaps import SIBLING_APP_ACCELERATORS

    lite = _lite_chords()
    assert lite["cmd_ai_usage"] in SIBLING_APP_ACCELERATORS
    assert lite["cmd_ai_sign_in"] in SIBLING_APP_ACCELERATORS


# --------------------------------------------------------------------------- #
# The three hooks
# --------------------------------------------------------------------------- #


class _Frame(HostedAiCommandsMixin):
    """Just enough MainFrame for the hooks to answer."""

    def __init__(self) -> None:
        self.frame = object()
        self.editor = object()
        self.settings = Settings()
        self.rebuilt = 0

    def _build_menu(self) -> None:
        self.rebuilt += 1


def test_the_parent_is_the_frame_not_the_controller() -> None:
    """A frame parented to the controller would be parented to nothing.

    QuillLite's document window *is* a wx.Frame and is its own parent; QUILL's
    MainFrame is a controller that owns one. Getting this wrong is not cosmetic:
    an unparented modeless window is one Windows can bury behind the editor with
    no keyboard route back to it, while somebody waits for an answer in it.
    """
    frame = _Frame()
    assert frame._ai_parent() is frame.frame
    assert frame._ai_parent() is not frame


def test_the_control_is_quills_editor() -> None:
    frame = _Frame()
    assert frame._ai_control() is frame.editor


def test_the_host_is_made_once_and_kept() -> None:
    frame = _Frame()
    assert frame._ai_host() is frame._ai_host()
    assert isinstance(frame._ai_host(), QuillAiHost)


# --------------------------------------------------------------------------- #
# The adapter
# --------------------------------------------------------------------------- #


def test_the_host_reads_and_writes_quills_own_settings() -> None:
    frame = _Frame()
    host = frame._ai_host()
    assert host.settings is frame.settings
    host.settings.ai_privacy_accepted_version = 4
    assert frame.settings.ai_privacy_accepted_version == 4


def test_the_privacy_version_survives_a_settings_round_trip() -> None:
    """It is stored, not merely held: a decision a crash lost is one to make again.

    And it is a **version**, not a boolean: a material change to what is sent
    bumps the agreement's version and everybody is asked again, which a yes/no
    could not express -- an old yes would silently cover a new thing.
    """
    assert Settings.from_dict({"ai_privacy_accepted_version": 7}).ai_privacy_accepted_version == 7
    assert Settings.from_dict({}).ai_privacy_accepted_version == 0
    # Garbage in the file is "not accepted", never "accepted".
    assert (
        Settings.from_dict({"ai_privacy_accepted_version": "yes"}).ai_privacy_accepted_version == 0
    )
    assert Settings.from_dict({"ai_privacy_accepted_version": -3}).ai_privacy_accepted_version == 0


def test_a_settings_write_that_fails_does_not_raise(monkeypatch) -> None:
    """A locked profile must not turn "I agree" into an error dialog."""
    frame = _Frame()
    monkeypatch.setattr(
        "quill.core.settings.save_settings",
        lambda _settings: (_ for _ in ()).throw(OSError("read-only")),
    )
    frame._ai_host().save_settings()  # must not raise


def test_the_feature_switch_is_quills_use_ai_switch(monkeypatch) -> None:
    """One switch, not a second one for people to find and disagree with."""
    state = {"on": False}
    monkeypatch.setattr("quill.core.ai.model_manager.load_ai_enabled", lambda: state["on"])
    monkeypatch.setattr(
        "quill.core.ai.model_manager.save_ai_enabled",
        lambda enabled: state.__setitem__("on", bool(enabled)),
    )
    host = _Frame()._ai_host()
    assert host.feature_enabled("hosted_ai") is False
    host.features.set_enabled("hosted_ai", True)
    host.save_features()
    assert state["on"] is True
    assert host.feature_enabled("hosted_ai") is True


def test_the_host_answers_yes_for_every_other_feature_name() -> None:
    """The shared code only ever asks about hosted_ai; anything else is not ours
    to refuse, and answering False would silently disable a caller we did not
    write."""
    assert _Frame()._ai_host().feature_enabled("something_else") is True


def test_rebuilding_the_menus_rebuilds_quills_menu_bar() -> None:
    frame = _Frame()
    frame._ai_host().rebuild_all_menus()
    assert frame.rebuilt == 1


def test_quills_switch_route_names_quills_switch() -> None:
    """The one sentence that cannot be shared: the switch is in two places.

    Every other route sentence in the shared module names a row that exists in
    both products ("Connect or Sign Out in the AI menu"), which is why this is
    the only hook of its kind.
    """
    assert "Use Artificial Intelligence" in _Frame()._ai_switch_route()
    assert "Customize Features" in HostedAiMixin._ai_switch_route(object())


# --------------------------------------------------------------------------- #
# The menu it opens with
# --------------------------------------------------------------------------- #

_AI_MENU = "quill/ui/main_frame_ai_menu.py"


def test_the_ai_menu_opens_with_the_free_rows() -> None:
    body = _source("quill/ui/main_frame_menu.py")
    hosted = body.index("self._build_hosted_ai_rows(ai_menu)")
    advanced = body.index("self._build_advanced_ai_rows(ai_menu)")
    assert hosted < advanced, "the free rows must come first in the AI menu"


def test_the_advanced_surface_is_behind_the_basic_check() -> None:
    body = _source("quill/ui/main_frame_menu.py")
    assert "if not is_basic_mode():\n            self._build_advanced_ai_rows(ai_menu)" in body


@pytest.mark.parametrize(
    "label",
    [
        'Fr&ee AI Assistant..."',
        'Ask About This &Document..."',
        'Free AI Usa&ge..."',
        '&Connect or Sign Out..."',
        'Privac&y Agreement..."',
    ],
)
def test_every_free_row_is_in_the_menu(label: str) -> None:
    assert label in _source(_AI_MENU)


def test_no_two_free_rows_claim_the_same_mnemonic() -> None:
    """GATE-14's rule, applied where the gate cannot see: Windows cycles focus
    between duplicate mnemonics instead of pressing, so one of a pair silently
    cannot be reached and nothing announces the loss."""
    import re

    body = _source(_AI_MENU)
    start = body.index("def _build_hosted_ai_rows")
    end = body.index("def _build_advanced_ai_rows")
    letters = re.findall(r"&([A-Za-z])", body[start:end])
    assert len(letters) == 5, letters
    assert len(set(letter.lower() for letter in letters)) == 5, letters


def test_the_free_mnemonics_do_not_collide_with_the_advanced_rows() -> None:
    """Basic hides the advanced rows, so a collision would only bite in Advanced
    -- which is exactly the kind of defect that ships."""
    import re

    body = _source(_AI_MENU)
    hosted_start = body.index("def _build_hosted_ai_rows")
    advanced_start = body.index("def _build_advanced_ai_rows")
    toggle_start = body.index("def _append_ai_experience_toggle")

    def top_level_mnemonics(chunk: str) -> set[str]:
        # Only rows appended to ai_menu itself; submenu rows are their own
        # namespace and cannot collide with these.
        letters: set[str] = set()
        for line in chunk.splitlines():
            if "ai_menu.Append" in line or "ai_menu.AppendSubMenu" in line:
                continue
            match = re.search(r'_\("([^"]*&[A-Za-z][^"]*)"\)', line)
            if match and "menu_label" in line or (match and "ai_menu" in chunk):
                found = re.search(r"&([A-Za-z])", match.group(1))
                if found:
                    letters.add(found.group(1).lower())
        return letters

    free = top_level_mnemonics(body[hosted_start:advanced_start])
    assert free == {"e", "d", "g", "c", "y"}, sorted(free)
    # The toggle's own letter must not be one of the five either.
    toggle = top_level_mnemonics(body[toggle_start:])
    assert not (free & toggle), sorted(free & toggle)


# --------------------------------------------------------------------------- #
# Which mode a fresh install starts in
# --------------------------------------------------------------------------- #


def test_a_fresh_install_starts_in_basic(monkeypatch, tmp_path) -> None:
    """The reversal: Basic is the working experience now, not a reduced one.

    QUILL has its own free service, so the short menu needs no account, no key
    and no decision about which company sees your writing. The long menu is the
    specialist one.
    """
    import quill.core.ai.onboarding as onboarding

    monkeypatch.setattr(onboarding, "onboarding_state_path", lambda: tmp_path / "state.json")
    monkeypatch.setattr(onboarding, "configured_cloud_providers", lambda: [])
    assert onboarding.default_experience_mode() == EXPERIENCE_BASIC
    assert onboarding.is_basic_mode() is True


def test_an_install_that_already_ran_the_wizard_stays_in_advanced(monkeypatch, tmp_path) -> None:
    """An update must never take working menus away from somebody using them."""
    import quill.core.ai.onboarding as onboarding

    monkeypatch.setattr(onboarding, "onboarding_state_path", lambda: tmp_path / "state.json")
    monkeypatch.setattr(onboarding, "configured_cloud_providers", lambda: [])
    onboarding.mark_onboarding_complete()
    assert onboarding.default_experience_mode() == EXPERIENCE_ADVANCED


def test_an_install_with_a_provider_key_stays_in_advanced(monkeypatch, tmp_path) -> None:
    import quill.core.ai.onboarding as onboarding

    monkeypatch.setattr(onboarding, "onboarding_state_path", lambda: tmp_path / "state.json")
    monkeypatch.setattr(onboarding, "configured_cloud_providers", lambda: [("openai", "OpenAI")])
    assert onboarding.default_experience_mode() == EXPERIENCE_ADVANCED


def test_the_derived_mode_is_written_down_once(monkeypatch, tmp_path) -> None:
    """Settled rather than re-derived, so a menu cannot grow as a side effect.

    The derivation reads the credential store. If it ran on every menu build,
    pasting a key into an unrelated feature would silently lengthen the AI menu
    -- and the mode would also cost a credential-store read per menu build.
    """
    import quill.core.ai.onboarding as onboarding

    monkeypatch.setattr(onboarding, "onboarding_state_path", lambda: tmp_path / "state.json")
    monkeypatch.setattr(onboarding, "configured_cloud_providers", lambda: [])
    assert onboarding.load_experience_mode() == EXPERIENCE_BASIC

    calls = {"n": 0}

    def _counted() -> list[tuple[str, str]]:
        calls["n"] += 1
        return [("openai", "OpenAI")]

    monkeypatch.setattr(onboarding, "configured_cloud_providers", _counted)
    assert onboarding.load_experience_mode() == EXPERIENCE_BASIC
    assert calls["n"] == 0, "the mode was re-derived instead of read"


def test_an_unreadable_credential_store_is_not_treated_as_configured(monkeypatch, tmp_path) -> None:
    import quill.core.ai.onboarding as onboarding

    monkeypatch.setattr(onboarding, "onboarding_state_path", lambda: tmp_path / "state.json")
    monkeypatch.setattr(
        onboarding,
        "configured_cloud_providers",
        lambda: (_ for _ in ()).throw(OSError("no keyring")),
    )
    assert onboarding.default_experience_mode() == EXPERIENCE_BASIC


def test_the_toggle_flips_the_mode_rather_than_re_reading_it() -> None:
    """The original toggle saved the value it had just read, so nothing changed."""
    body = _source(_AI_MENU)
    assert "EXPERIENCE_ADVANCED if is_basic_mode() else EXPERIENCE_BASIC" in body
