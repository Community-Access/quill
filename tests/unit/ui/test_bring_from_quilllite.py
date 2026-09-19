"""The frame's half of P2.4: offered once, described before it is done.

Two rules, both about not deciding for somebody:

**Offered, not done.** Activating the QuillLite profile is the moment the
question is worth asking and exactly the wrong moment to answer it: the person's
QuillLite abbreviations and dictionary are months of work, and adopting them
silently is the behaviour ``quill/core/lite/paths.py`` refuses on principle.

**Described first.** "It copied your settings" is not something a listener can
verify afterwards by looking at the screen, so the counts -- and what is being
left behind -- go in the question.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.core.features import PROFILE_ESSENTIAL, PROFILE_QUILLLITE
from quill.core.settings import Settings
from quill.ui.main_frame import MainFrame


class _Host:
    apply_profile_settings = MainFrame.apply_profile_settings
    offer_bring_from_quilllite = MainFrame.offer_bring_from_quilllite
    bring_from_quilllite = MainFrame.bring_from_quilllite

    def __init__(self, *, answer: int = 5100) -> None:
        self.settings = Settings()
        self._answer = answer
        self.announced: list[str] = []
        self.status: list[str] = []
        self.boxes: list[tuple[str, str]] = []
        self.merged: dict[str, str] = {}
        self._wx = SimpleNamespace(YES=5100, NO=5101, OK=4, YES_NO=1, ICON_QUESTION=2)

    def _show_message_box(self, message: str, title: str, _style: int = 0) -> int:
        self.boxes.append((title, message))
        return self._answer

    def _announce(self, message: str) -> None:
        self.announced.append(message)

    def _set_status(self, message: str) -> None:
        self.status.append(message)

    def _merge_keymap_overrides(self, bindings: dict[str, str]) -> None:
        self.merged.update(bindings)


@pytest.fixture(autouse=True)
def _no_writes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import quill.core.settings as settings_module

    monkeypatch.setattr(settings_module, "save_settings", lambda _s: None)
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path / "quill")


def _lite_setup(root: Path) -> Path:
    lite = root / "lite"
    (lite / "dictionaries").mkdir(parents=True)
    (lite / "settings.json").write_text(
        json.dumps({"word_wrap": False, "window_width": 900}), encoding="utf-8"
    )
    (lite / "keymap.json").write_text(json.dumps({"cmd_bold": "Ctrl+Alt+B"}), encoding="utf-8")
    (lite / "abbreviations.json").write_text(
        json.dumps({"abbreviations": [{"abbreviation": "btw"}]}), encoding="utf-8"
    )
    return lite


@pytest.fixture
def _lite(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    lite = _lite_setup(tmp_path)
    monkeypatch.setattr("quill.core.lite_bridge.lite_data_dir", lambda: lite)
    return lite


# -- the settings a profile's name promises ------------------------------------


def test_the_quilllite_profile_sets_the_document_kind_it_promises() -> None:
    host = _Host()
    host.settings.default_new_document_format = "md"

    said = host.apply_profile_settings(PROFILE_QUILLLITE)

    assert host.settings.default_new_document_format == "txt"
    assert "default new document format" in said


def test_a_profile_that_promises_nothing_says_nothing() -> None:
    host = _Host()
    assert host.apply_profile_settings(PROFILE_ESSENTIAL) == ""


def test_a_setting_already_right_is_not_reported_as_changed() -> None:
    host = _Host()
    host.settings.default_new_document_format = "txt"
    assert host.apply_profile_settings(PROFILE_QUILLLITE) == ""


# -- the offer -----------------------------------------------------------------


def test_another_profile_is_never_asked_about_quilllite(_lite: Path) -> None:
    host = _Host()
    assert host.offer_bring_from_quilllite(PROFILE_ESSENTIAL) is False
    assert host.boxes == []


def test_the_offer_is_made_once(_lite: Path) -> None:
    """A profile switched back and forth must not keep asking."""
    host = _Host(answer=5101)  # No

    assert host.offer_bring_from_quilllite(PROFILE_QUILLLITE) is False
    assert len(host.boxes) == 1
    assert host.settings.quilllite_bring_offered is True

    host.offer_bring_from_quilllite(PROFILE_QUILLLITE)
    assert len(host.boxes) == 1


def test_the_question_carries_the_counts_and_what_is_left_behind(_lite: Path) -> None:
    host = _Host(answer=5101)
    host.offer_bring_from_quilllite(PROFILE_QUILLLITE)

    _title, message = host.boxes[0]
    assert "1 setting(s) copied." in message
    assert "1 rebound key(s) copied" in message
    assert "Left behind (1): window_width" in message
    assert "Nothing already in QUILL is replaced." in message


def test_declining_changes_nothing(_lite: Path) -> None:
    host = _Host(answer=5101)
    host.settings.soft_wrap = True

    assert host.bring_from_quilllite() is False
    assert host.settings.soft_wrap is True
    assert host.merged == {}
    assert host.status[-1] == "Left QUILL's own settings as they are."


def test_accepting_copies_the_settings_and_the_keys(_lite: Path) -> None:
    host = _Host(answer=5100)
    host.settings.soft_wrap = True

    assert host.bring_from_quilllite() is True
    assert host.settings.soft_wrap is False
    assert host.merged == {"format.bold": "Ctrl+Alt+B"}
    assert host.announced and "Brought 1 setting(s)" in host.announced[0]


def test_accepting_merges_the_stores_into_quills_folder(_lite: Path, tmp_path: Path) -> None:
    host = _Host(answer=5100)
    host.bring_from_quilllite()

    merged = json.loads((tmp_path / "quill" / "abbreviations.json").read_text(encoding="utf-8"))
    assert [a["abbreviation"] for a in merged["abbreviations"]] == ["btw"]


def test_accepting_points_quilllite_at_quill_from_then_on(_lite: Path) -> None:
    host = _Host(answer=5100)
    host.bring_from_quilllite()

    raw = json.loads((_lite / "settings.json").read_text(encoding="utf-8"))
    assert raw["share_quill_abbreviations"] is True
    assert "either is a change in both" in host.announced[0]


def test_nothing_to_bring_says_so_without_asking(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("quill.core.lite_bridge.lite_data_dir", lambda: None)
    host = _Host()

    assert host.bring_from_quilllite() is False
    assert host.boxes and "has not been run" in host.boxes[0][1]
