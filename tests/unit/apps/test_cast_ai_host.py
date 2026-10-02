"""QUILL Cast's hosted AI is the family's, through an adapter (ear.md A1).

The service's behaviour is tested once against the shared module both editors
run (``tests/unit/apps/test_lite_ai.py``). What is Cast-specific and tested
here: that Cast grows no command of its own, that the switch and the agreement
live in the history record and round-trip, that the notes pane is what the
commands read, that an answer never writes into Cast, and that every row in
the AI Features submenu has a chord Cast actually binds.
"""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

from quill.core.app_keymaps import APP_KEYMAPS
from quill.core.podcasts.history import PodcastHistory, load_history, save_history
from quill.ui.hosted_ai_commands import HostedAiMixin
from quill.ui.podcasts.cast_ai_host import AI_ROWS, CastAiHost, CastAiMixin

_FIVE = (
    "cmd_ai_assistant",
    "cmd_ai_ask_document",
    "cmd_ai_usage",
    "cmd_ai_sign_in",
    "cmd_ai_privacy",
)


def test_cast_runs_the_shared_commands_rather_than_its_own() -> None:
    assert issubclass(CastAiMixin, HostedAiMixin)
    own = {n for n in vars(CastAiMixin) if n.startswith("cmd_") or n.startswith("_open_ai")}
    assert own == set(), f"QUILL Cast has grown its own hosted-AI commands: {sorted(own)}"
    for name in _FIVE:
        assert callable(getattr(CastAiMixin, name))


def test_the_switch_and_the_agreement_live_in_the_history_and_round_trip(
    tmp_path: Path,
) -> None:
    history = PodcastHistory()
    assert history.ai_help_enabled is False, "AI help is off until switched on"
    assert history.ai_privacy_accepted_version == 0
    history.ai_help_enabled = True
    history.ai_privacy_accepted_version = 3
    history.ai_own_key_provider = "gemini"
    history.ai_own_key_model = "gemini-2.5-flash"
    save_history(tmp_path, history)

    back = load_history(tmp_path)
    assert back.ai_help_enabled is True
    assert back.ai_privacy_accepted_version == 3
    assert (back.ai_own_key_provider, back.ai_own_key_model) == ("gemini", "gemini-2.5-flash")


def test_the_host_answers_the_shared_contract_from_the_history() -> None:
    saved: list[str] = []
    rebuilt: list[str] = []
    frame = SimpleNamespace(
        _podcast_history=PodcastHistory(),
        _save_podcast_history=lambda: saved.append("saved"),
        _build_menu_bar=lambda: rebuilt.append("menus"),
    )
    host = CastAiHost(frame)
    assert host.ai_agent_name == "QUILL Cast", "OpenAI's consent page names the app"
    assert host.settings is frame._podcast_history
    assert host.feature_enabled("hosted_ai") is False
    assert host.feature_enabled("anything_else") is True
    host.features.set_enabled("hosted_ai", True)
    host.save_features()
    host.rebuild_all_menus()
    assert frame._podcast_history.ai_help_enabled is True
    assert saved == ["saved"] and rebuilt == ["menus"]


def test_the_commands_read_the_notes_pane_and_never_write_into_cast() -> None:
    class Frame(CastAiMixin):
        def __init__(self) -> None:
            self.said: list[str] = []
            self._notes_pane = SimpleNamespace(field="the-notes-control")

        def _announce(self, text: str) -> None:
            self.said.append(text)

    frame = Frame()
    assert frame._ai_control() == "the-notes-control"
    frame._replace_range(0, 3, "an answer")
    frame._insert_below("an answer")
    assert len(frame.said) == 2 and all("cannot be changed" in s for s in frame.said)
    assert all("Copy" in s for s in frame.said), "the way out is named"
    assert "Preferences" in frame._ai_switch_route()
    frame._notes_pane = None
    assert frame._ai_control() is None


def test_every_ai_row_has_a_cast_chord_and_a_unique_mnemonic() -> None:
    cast = APP_KEYMAPS["cast"]
    seen: set[str] = set()
    for command_id, label, handler in AI_ROWS:
        if not command_id:
            continue
        assert cast.get(command_id), f"{command_id} has no Cast chord"
        assert callable(getattr(CastAiMixin, handler))
        match = re.search(r"&(.)", label)
        assert match is not None, label
        letter = match.group(1).lower()
        assert letter not in seen, f"mnemonic {letter!r} claimed twice in AI Features"
        seen.add(letter)


def test_the_help_menu_carries_the_submenu() -> None:
    source = Path("quill/apps/podcasts_menu.py").read_text(encoding="utf-8")
    assert "_append_cast_ai_submenu(help_menu)" in source
