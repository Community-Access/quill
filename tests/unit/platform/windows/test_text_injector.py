from __future__ import annotations

from quill.platform.windows import text_injector
from quill.platform.windows.text_injector import InjectionResult


def test_checked_unicode_injection_reports_partial_send_input(monkeypatch) -> None:
    monkeypatch.setattr(
        text_injector,
        "_send",
        lambda inputs: InjectionResult(len(inputs), max(0, len(inputs) - 1)),
    )

    result = text_injector.send_text_checked("A")

    assert result.requested_events == 2
    assert result.sent_events == 1
    assert not result.complete


def test_checked_expansion_stops_after_partial_backspaces(monkeypatch) -> None:
    typed: list[str] = []
    monkeypatch.setattr(
        text_injector,
        "send_backspaces_checked",
        lambda _count: InjectionResult(4, 2),
    )
    monkeypatch.setattr(
        text_injector,
        "send_text_checked",
        lambda text: typed.append(text) or InjectionResult(2, 2),
    )

    result = text_injector.inject_expansion_checked("replacement", backspace_count=2)

    assert not result.complete
    assert typed == []
