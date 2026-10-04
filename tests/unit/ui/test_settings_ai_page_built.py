"""The Settings dialog's AI and Assistant page draws every setting it declares.

Its builder returned straight after the AI master switch, so eleven settings --
the voice question reply, the assistant's prompt style, Ask AI's default
provider and model, the image description style -- were never drawn, and
Find a setting could not reach them either, because it only saw the controls
on pages somebody had already opened.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core import settings_registry as registry  # noqa: E402
from quill.core.settings import Settings  # noqa: E402
from quill.ui.main_frame import MainFrame  # noqa: E402


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def _frame() -> Any:
    frame = MainFrame.__new__(MainFrame)
    frame._wx = wx
    frame.frame = wx.Frame(None)
    frame.settings = Settings()
    frame._feature_enabled = lambda _gate: True
    frame._set_status = lambda _msg: None
    frame._set_status_quiet = lambda _msg: None
    frame._add_text_editor_prefs = lambda *_a, **_k: None
    frame._wire_experimental_gates = lambda *_a, **_k: None
    return frame


def _drawable_ai_specs() -> list[Any]:
    return [
        spec
        for spec in registry.specs_for_group("ai")
        if not isinstance(registry.get_value(Settings(), spec.key), (list, dict))
    ]


def _labels_on(window: Any) -> list[str]:
    found: list[str] = []
    for child in window.GetChildren():
        if isinstance(child, wx.StaticText):
            found.append(child.GetLabel())
        if isinstance(child, wx.CheckBox):
            found.append(child.GetLabel())
        found.extend(_labels_on(child))
    return found


def test_every_ai_setting_is_drawn_with_help_and_is_findable(wx_app, monkeypatch) -> None:
    import quill.core.ai.model_manager as model_manager

    monkeypatch.setattr(model_manager, "load_ai_enabled", lambda: True)
    frame = _frame()
    seen: dict[str, Any] = {}

    def fake_show(dialog: Any, _label: str) -> int:
        index = dialog._quill_settings_index()
        seen["index"] = [target.label for target in index]
        notebook = next(c for c in dialog.GetChildren() if isinstance(c, wx.Notebook))
        page = next(
            i
            for i in range(notebook.GetPageCount())
            if notebook.GetPageText(i) == "AI and Assistant"
        )
        ai_target = next(t for t in index if t.label.startswith("AI and Assistant: "))
        control = ai_target.reveal()
        seen["revealed"] = control is not None
        panel = notebook.GetPage(page)
        seen["labels"] = _labels_on(panel)
        seen["help"] = [
            c.GetHelpText() for c in panel.GetChildren() if not isinstance(c, wx.StaticText)
        ]
        return wx.ID_CANCEL

    frame._show_modal_dialog = fake_show  # type: ignore[method-assign]
    MainFrame.open_general_preferences(frame)

    specs = _drawable_ai_specs()
    assert len(specs) >= 10
    missing = [spec.label for spec in specs if spec.label not in seen["labels"]]
    assert missing == [], f"declared but never drawn: {missing}"
    unfindable = [
        spec.label for spec in specs if f"AI and Assistant: {spec.label}" not in seen["index"]
    ]
    assert unfindable == [], f"Find a setting cannot reach: {unfindable}"
    assert seen["revealed"]
    described = {spec.description for spec in specs if spec.description}
    assert described <= set(seen["help"]), "a drawn setting has no F1 help"
    frame.frame.Destroy()
