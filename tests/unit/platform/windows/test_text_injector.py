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

    expected = len(text_injector._text_inputs("A"))  # Shift and A on most layouts
    assert result.requested_events == expected
    assert result.sent_events == expected - 1
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


def test_typing_waits_for_alt_to_be_let_go() -> None:
    """Stopping QUILL Transcribe with Alt+Shift+\ writes the last phrase while
    Alt is still down, and Outlook took its letters as shortcuts -- an "s" was
    Alt+S, Send (2026-10-12). Typing now waits for the key to come up."""
    from quill.platform.windows.text_injector import _wait_for_modifiers_released

    presses = iter([True, True, False])
    assert _wait_for_modifiers_released(lambda: next(presses), timeout_s=1.0) is True


def test_typing_is_refused_while_alt_stays_down(monkeypatch) -> None:
    from types import SimpleNamespace

    from quill.platform.windows import text_injector

    sent: list[int] = []
    # A fake user32: Alt reads as held for ever, and nothing can reach a real window.
    fake = SimpleNamespace(
        GetAsyncKeyState=lambda vk: 0x8000 if vk == 0x12 else 0,
        SendInput=lambda n, *_a: sent.append(n) or n,
    )
    monkeypatch.setattr(text_injector, "_user32", fake)
    monkeypatch.setattr(text_injector, "_MODIFIER_WAIT_S", 0.05)
    result = text_injector.send_text_checked("send")
    assert result.sent_events == 0 and not result.complete
    assert sent == []
    # Let go of Alt, and the same text goes out.
    fake.GetAsyncKeyState = lambda vk: 0
    assert text_injector.send_text_checked("send").complete
    assert sent == [8]


def _us_layout(monkeypatch, *, caps_lock: bool = False):
    """A fake user32 with a US layout: a, T, '.', and a dead key for '`'."""
    from types import SimpleNamespace

    from quill.platform.windows import text_injector

    table = {"a": 0x0041, "t": 0x0054, "T": 0x0154, ".": 0x00BE, "`": 0x00C0, "@": 0x0632}
    fake = SimpleNamespace(
        GetForegroundWindow=lambda: 1,
        GetWindowThreadProcessId=lambda _hwnd, _pid: 2,
        GetKeyboardLayout=lambda _thread: 0x0409,
        GetKeyState=lambda vk: 1 if caps_lock and vk == 0x14 else 0,
        VkKeyScanExW=lambda code, _layout: table.get(chr(code), -1),
        MapVirtualKeyExW=lambda vk, kind, _layout: (
            (0x80000060 if vk == 0xC0 else 0x61) if kind == 2 else 0x1E
        ),
        GetAsyncKeyState=lambda _vk: 0,
    )
    monkeypatch.setattr(text_injector, "_user32", fake)
    return text_injector


def _keys(inputs) -> list[tuple[int, int, bool]]:
    return [(i.ki.wVk, i.ki.wScan, bool(i.ki.dwFlags & 0x0002)) for i in inputs]


def test_a_letter_is_its_key_not_a_unicode_keystroke(monkeypatch) -> None:
    """JAWS announced every Unicode keystroke as "c" (2026-10-12): a character
    the layout has goes as its own key, the way a keyboard sends it."""
    injector = _us_layout(monkeypatch)
    assert _keys(injector._text_inputs("a")) == [(0x41, 0x1E, False), (0x41, 0x1E, True)]


def test_a_capital_is_shift_and_its_key(monkeypatch) -> None:
    injector = _us_layout(monkeypatch)
    vks = [(vk, up) for vk, _scan, up in _keys(injector._text_inputs("T"))]
    assert vks == [(0x10, False), (0x54, False), (0x54, True), (0x10, True)]


def test_caps_lock_is_allowed_for(monkeypatch) -> None:
    injector = _us_layout(monkeypatch, caps_lock=True)
    vks = [vk for vk, _scan, _up in _keys(injector._text_inputs("a"))]
    assert vks[0] == 0x10  # Shift, so Caps Lock's capital comes out small
    assert [vk for vk, _s, _u in _keys(injector._text_inputs("T"))] == [0x54, 0x54]


def test_what_the_layout_cannot_type_plainly_stays_unicode(monkeypatch) -> None:
    """No key, a dead key, or one that needs Ctrl or Alt: the Unicode route."""
    injector = _us_layout(monkeypatch)
    for char in ("é", "`", "@", "\n"):
        inputs = injector._text_inputs(char)
        assert all(i.ki.dwFlags & 0x0004 for i in inputs), char


def _recording_user32(monkeypatch, accept=None):
    """A fake user32 that records every SendInput batch as (vk, key-up) pairs."""
    from types import SimpleNamespace

    from quill.platform.windows import text_injector

    batches: list[list[tuple[int, bool]]] = []

    def send(n, array, _size):
        batch = [(array[i].ki.wVk, bool(array[i].ki.dwFlags & 0x0002)) for i in range(n)]
        batches.append(batch)
        return n if accept is None else accept(batch)

    fake = SimpleNamespace(GetAsyncKeyState=lambda _vk: 0, SendInput=send)
    monkeypatch.setattr(text_injector, "_user32", fake)
    return text_injector, batches


def test_hushing_the_reader_is_a_ctrl_tap_after_the_text(monkeypatch) -> None:
    """Every screen reader stops talking at Ctrl alone. Sent in the same batch,
    it cuts the echo of the last key -- "period" after every phrase (2026-10-12)."""
    injector, batches = _recording_user32(monkeypatch)
    result = injector.send_text_checked("a.", hush_reader=True)
    assert result.complete
    assert batches[0][-2:] == [(0x11, False), (0x11, True)]
    assert len(batches) == 1


def test_without_hushing_there_is_no_ctrl(monkeypatch) -> None:
    injector, batches = _recording_user32(monkeypatch)
    injector.send_text_checked("a.")
    assert all(vk != 0x11 for vk, _up in batches[0])


def test_ctrl_is_never_left_down(monkeypatch) -> None:
    """Windows took the press and not the release: the release goes again."""
    injector, batches = _recording_user32(monkeypatch, accept=lambda batch: len(batch) - 1)
    result = injector.send_text_checked("a", hush_reader=True)
    assert result.complete  # every character went in; only the release was lost
    assert batches[-1] == [(0x11, True)]


# -- astral characters (todo P3: an emoji lost its first half) ----------------


def test_an_emoji_sends_both_key_downs_before_either_key_up() -> None:
    """A key-up between the two surrogate halves is what separated their
    WM_CHARs; the pair now goes down together and comes up together."""
    from quill.platform.windows.text_injector import unicode_key_sequence

    assert unicode_key_sequence("\U0001f600") == [
        (0xD83D, False),
        (0xDE00, False),
        (0xDE00, True),
        (0xD83D, True),
    ]


def test_a_bmp_character_is_still_one_tap() -> None:
    from quill.platform.windows.text_injector import unicode_key_sequence

    assert unicode_key_sequence("é\n") == [(0xE9, False), (0xE9, True), (0x0A, False), (0x0A, True)]


def test_every_unit_of_mixed_text_is_sent_exactly_once_down_and_up() -> None:
    from quill.platform.windows.text_injector import unicode_key_sequence, utf16_code_units

    text = "a\U0001f44d b\U00020041é"
    sequence = unicode_key_sequence(text)
    downs = [unit for unit, up in sequence if not up]
    ups = [unit for unit, up in sequence if up]
    assert downs == utf16_code_units(text)
    assert sorted(ups) == sorted(downs)
    # And the downs decode back to exactly the text: nothing lost, nothing added.
    assert b"".join(u.to_bytes(2, "little") for u in downs).decode("utf-16-le") == text


def test_the_unicode_inputs_follow_that_sequence(monkeypatch) -> None:
    injector = _us_layout(monkeypatch)
    keys = _keys(injector._text_inputs("\U0001f600"))
    assert [(scan, up) for _vk, scan, up in keys] == [
        (0xD83D, False),
        (0xDE00, False),
        (0xDE00, True),
        (0xD83D, True),
    ]


def test_an_astral_character_is_never_typed_as_a_layout_key(monkeypatch) -> None:
    """VkKeyScanExW takes a 16-bit WCHAR: U+20041 reached it as U+0041 and the
    US layout answered with the A key. The fake truncates the way ctypes does."""
    injector = _us_layout(monkeypatch)
    real = injector._user32.VkKeyScanExW
    injector._user32.VkKeyScanExW = lambda code, layout: real(code & 0xFFFF, layout)
    # "a" is in the fake's table, so U+20061 would have typed "a".
    inputs = injector._text_inputs("\U00020061")
    assert all(i.ki.dwFlags & 0x0004 for i in inputs)
    assert [i.ki.wScan for i in inputs if not i.ki.dwFlags & 0x0002] == [0xD840, 0xDC61]
