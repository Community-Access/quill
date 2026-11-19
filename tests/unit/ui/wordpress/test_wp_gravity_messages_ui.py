"""The editor's Other Notifications and Confirmations window (complete.md 2.3)."""

from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip("wx")

from quill.core.wordpress.gravity_build import new_form  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui import wordpress_gravity_messages as gmw  # noqa: E402


class _Window:
    def Destroy(self) -> None:  # noqa: N802 - wx's name
        pass


def test_add_turn_off_and_remove_change_the_editors_copy(monkeypatch) -> None:
    form = new_form("Tickets")
    said: list[str] = []
    shown: dict[str, Any] = {}

    def window(_parent: Any, _show: Any, **k: Any) -> _Window:
        shown.update(k)
        return _Window()

    answers = iter([{"name": "Ticket email", "to": "{Email:3}", "subject": "Hi", "message": ""}])
    monkeypatch.setattr(dlg, "show_list_window", window)
    monkeypatch.setattr(gmw, "ask_fields", lambda *_a, **_k: next(answers))
    monkeypatch.setattr(dlg, "confirm", lambda *_a, **_k: True)
    gmw.edit_messages(None, lambda *_a: 0, form, said.append)
    assert shown["rows"] == []
    actions = {a.label: a for a in shown["actions"]}
    rows = actions["Add Notifica&tion..."].run(None)
    assert rows == ["Ticket email, notification, to {Email:3}, on"]
    toggle = actions["Turn On or &Off"]
    assert toggle.label_for is not None and toggle.label_for(0) == "Turn &Off"
    assert toggle.run(0) == ["Ticket email, notification, to {Email:3}, off"]
    assert actions["&Remove..."].run(0) == []
    assert said[-1] == "Removed Ticket email."
