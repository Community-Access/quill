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


def test_input_is_the_size_windows_requires() -> None:
    """SendInput rejects the whole call when cbSize is not sizeof(INPUT): 40 on
    64-bit Windows, 28 on 32-bit, set by the union's largest member (MOUSEINPUT).
    With only KEYBDINPUT in the union it was 32, every call failed with
    ERROR_INVALID_PARAMETER, and nothing dictated reached Outlook (2026-10-12)."""
    import ctypes

    from quill.platform.windows import text_injector

    expected = 40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28
    assert ctypes.sizeof(text_injector._INPUT) == expected
