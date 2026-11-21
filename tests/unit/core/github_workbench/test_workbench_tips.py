"""Tips at the right moment, with an option for plain help (PRD D16, GH-R-116)."""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

from quill.core.github import workbench_learning as learning
from quill.core.github.workbench_prefs import WorkbenchPrefs
from quill.core.github.workbench_tips import (
    BEE,
    BERT,
    MOMENTS,
    OFFER_AFTER,
    TipMoments,
    voice,
)
from quill.core.github.workbench_window_menu import WORKBENCH_KEYS

_CHORD = re.compile(r"\b(?:(?:Ctrl|Alt|Shift)\+)+(?:F\d+|PageDown|PageUp|Enter|[A-Z0-9])\b")


def test_a_tip_is_offered_the_third_time_and_only_once(tmp_path: Path) -> None:
    path = tmp_path / "tips.json"
    moments = TipMoments.load(path)
    said = [moments.record("load_more_again") for _ in range(OFFER_AFTER + 2)]
    assert said[: OFFER_AFTER - 1] == ["", ""]
    assert said[OFFER_AFTER - 1].startswith(f"{BERT}'s tip: Load All")
    assert said[OFFER_AFTER:] == ["", ""]
    # Nothing is written until the window closes, then it is remembered.
    assert not path.exists()
    moments.save()
    assert TipMoments.load(path).record("load_more_again") == ""


def test_turned_off_counts_nothing_and_plain_help_drops_the_name(tmp_path: Path) -> None:
    moments = TipMoments.load(tmp_path / "tips.json")
    for _ in range(OFFER_AFTER + 1):
        assert moments.record("long_list_no_filter", enabled=False) == ""
    assert moments.counts == {}
    said = [moments.record("long_list_no_filter", plain=True) for _ in range(OFFER_AFTER)]
    assert said[-1].startswith("Tip: Type a word in the filter box")
    assert BERT not in said[-1]


def test_the_characters_speak_in_one_line_or_not_at_all() -> None:
    assert voice(BERT, "x") == "QUILLBert's tip: x"
    assert voice(BEE, "x") == "QUILLBee explains: x"
    assert voice(BEE, "x", plain=True) == "x"
    assert learning.tip_rows(plain=True)[0][1].startswith(f"Tip 1 of {len(learning.TIPS)}:")
    assert learning.tip_rows()[0][1].startswith("QUILLBert's tip 1 of")


def test_every_key_a_moment_teaches_is_bound() -> None:
    bound = set(WORKBENCH_KEYS.values()) | {"Ctrl+Enter", "Alt+Enter"}
    for moment in MOMENTS.values():
        for chord in _CHORD.findall(moment.tip):
            assert chord in bound, f"{chord} in {moment.tip!r}"


def test_options_have_the_two_choices_on_by_default_and_plain_off() -> None:
    prefs = WorkbenchPrefs()
    assert prefs.tips_when_useful is True and prefs.plain_help is False


def test_the_workbench_puts_the_tip_in_details_unspoken(monkeypatch, tmp_path: Path) -> None:
    """The third long list read without the filter: the tip is in Details, not said."""
    from quill.ui.github_workbench_view import GitHubWorkbenchViewMixin

    class Details:
        value = "A row."

        def GetValue(self) -> str:  # noqa: N802 - wx's name
            return self.value

        def ChangeValue(self, text: str) -> None:  # noqa: N802 - wx's name
            self.value = text

    monkeypatch.setattr(
        "quill.core.github.workbench_tips.app_data_dir", lambda: tmp_path, raising=True
    )
    monkeypatch.setattr("quill.core.github.workbench_prefs.load_prefs", lambda: WorkbenchPrefs())
    view = GitHubWorkbenchViewMixin()
    said: list[str] = []
    view._say = said.append  # type: ignore[method-assign]
    view.frame = SimpleNamespace(details=Details())
    for _visit in range(OFFER_AFTER):
        view.offer_tip("long_list_no_filter")
    assert "QUILLBert's tip: Type a word in the filter box" in view.frame.details.value
    assert said == []
