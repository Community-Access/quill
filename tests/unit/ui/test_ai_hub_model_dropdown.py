"""AI Hub Provider tab: the Model field is an editable dropdown, not a text box.

The Hub used a bare text field for the model while the Setup Wizard offered a
combo with recommended (now free-first) suggestions and a model list. These tests
pin the control type at the source level and exercise the pure populate/list
helpers on a light stub (no full wx dialog needed).
"""

from __future__ import annotations

import re
from pathlib import Path
from types import MethodType

from quill.ui.ai_hub_dialog import AIHubDialog


def _hub_source() -> str:
    ui = Path(__file__).resolve().parents[3] / "quill" / "ui"
    return (ui / "ai_hub_dialog.py").read_text(encoding="utf-8")


def test_model_control_is_a_combobox() -> None:
    src = _hub_source()
    assert re.search(r"self\._model_ctrl\s*=\s*wx\.ComboBox\(", src), (
        "AI Hub Model field must be an editable wx.ComboBox, not a TextCtrl"
    )


class _FakeCombo:
    def __init__(self) -> None:
        self._items: list[str] = []
        self._value = ""

    def Set(self, items: list[str]) -> None:
        self._items = list(items)

    def SetValue(self, value: str) -> None:
        self._value = value

    def GetValue(self) -> str:
        return self._value

    def GetStrings(self) -> list[str]:
        return list(self._items)


class _FakeLabel:
    def __init__(self) -> None:
        self.text = ""

    def SetLabel(self, text: str) -> None:
        self.text = text


class _FakeButton:
    def __init__(self) -> None:
        self.enabled = True

    def Enable(self, value: bool) -> None:
        self.enabled = value


class _Stub:
    def __init__(self) -> None:
        self._model_ctrl = _FakeCombo()
        self._test_label = _FakeLabel()
        self._list_models_btn = _FakeButton()
        # Real instance methods bound onto the stub so higher-level methods
        # (e.g. _on_hub_provider_changed) can call self._populate_hub_models
        # / self._hub_provider through it, same as on the real dialog.
        self._populate_hub_models = MethodType(AIHubDialog._populate_hub_models, self)
        self._hub_provider = MethodType(AIHubDialog._hub_provider, self)


def test_populate_hub_models_prefers_free_for_openrouter() -> None:
    from quill.core.ai.free_models import best_free_writing_model

    stub = _Stub()
    AIHubDialog._populate_hub_models(stub, "openrouter")
    assert stub._model_ctrl.GetValue() == best_free_writing_model("openrouter")
    assert stub._model_ctrl.GetValue().endswith(":free")


def test_populate_hub_models_keeps_explicit_selection() -> None:
    stub = _Stub()
    AIHubDialog._populate_hub_models(stub, "openai", select="gpt-4.1")
    assert stub._model_ctrl.GetValue() == "gpt-4.1"


def test_hub_models_listed_loads_and_selects() -> None:
    stub = _Stub()
    AIHubDialog._on_hub_models_listed(stub, ["a", "b", "c"], "")
    assert stub._model_ctrl.GetStrings() == ["a", "b", "c"]
    assert stub._model_ctrl.GetValue() == "a"
    assert stub._list_models_btn.enabled is True
    assert "3 models" in stub._test_label.text


def test_hub_models_listed_surfaces_error() -> None:
    stub = _Stub()
    AIHubDialog._on_hub_models_listed(stub, [], "connection refused")
    assert "refused" in stub._test_label.text
    assert stub._list_models_btn.enabled is True


class _FakeProviderChoice:
    """Mimics wx.Choice, tracking focus state and SetFocus() calls."""

    def __init__(self, *, focused: bool) -> None:
        self._focused = focused
        self.focus_calls = 0

    def GetSelection(self) -> int:
        return 1

    def HasFocus(self) -> bool:
        return self._focused

    def SetFocus(self) -> None:
        self.focus_calls += 1
        self._focused = True


class _StealingCombo(_FakeCombo):
    def __init__(self, thief_target: _FakeProviderChoice) -> None:
        super().__init__()
        self._thief_target = thief_target

    def Set(self, items: list[str]) -> None:
        super().Set(items)
        self._thief_target._focused = False


def test_provider_changed_restores_focus_stolen_by_model_repopulation() -> None:
    # #883: selecting a provider via arrow keys (no dropdown opened) lost
    # focus to the model combo once its suggestions were repopulated.
    stub = _Stub()
    provider_choice = _FakeProviderChoice(focused=True)
    stub._provider_choice = provider_choice
    stub._model_ctrl = _StealingCombo(provider_choice)
    AIHubDialog._on_hub_provider_changed(stub, None)
    assert provider_choice.HasFocus() is True
    assert provider_choice.focus_calls == 1


def test_provider_changed_does_not_force_focus_when_choice_was_not_focused() -> None:
    # If the provider choice never had focus (e.g. programmatic refresh),
    # don't yank focus onto it.
    stub = _Stub()
    provider_choice = _FakeProviderChoice(focused=False)
    stub._provider_choice = provider_choice
    stub._model_ctrl = _FakeCombo()
    AIHubDialog._on_hub_provider_changed(stub, None)
    assert provider_choice.focus_calls == 0
