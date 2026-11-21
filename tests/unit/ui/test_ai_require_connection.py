"""The keyed-AI choke point asks Choose Your AI's own question (2026-11-20).

``MainFrame._ai_require_connection`` is the single guard for keyed AI text
features (spell/grammar check, translate, Document Q&A, thesaurus, agent tasks).
It asks what every AI-menu command asks -- AI help on and the free AI's
agreement (``_ai_ready``), an AI in use that can do the job (``_ai_capable``,
which opens Choose Your AI when none is) -- and then hands out the route to the
AI chosen there, never the older AI Hub provider.
"""

from __future__ import annotations

from quill.core.ai import chosen_route
from quill.ui.main_frame import MainFrame


def _frame(*, ready: bool, capable: bool) -> MainFrame:
    frame = MainFrame.__new__(MainFrame)
    asked: list[str] = []
    frame._asked = asked  # type: ignore[attr-defined]
    frame._ai_ready = lambda: ready  # type: ignore[method-assign]
    frame._ai_capable = lambda c: asked.append(c) or capable  # type: ignore[method-assign]
    chosen_route.set_sender(lambda prompt, _system="": prompt)
    return frame


def test_require_connection_returns_none_when_ai_is_not_ready() -> None:
    frame = _frame(ready=False, capable=True)

    assert frame._ai_require_connection() is None
    assert frame._asked == []  # type: ignore[attr-defined]


def test_require_connection_returns_none_when_the_chosen_ai_cannot() -> None:
    frame = _frame(ready=True, capable=False)

    assert frame._ai_require_connection("pictures") is None
    assert frame._asked == ["pictures"]  # type: ignore[attr-defined]


def test_require_connection_hands_out_the_chosen_route() -> None:
    frame = _frame(ready=True, capable=True)

    result = frame._ai_require_connection()

    assert result is not None
    connection, api_key = result
    assert connection.provider == chosen_route.ROUTE_PROVIDER
    assert api_key == ""
