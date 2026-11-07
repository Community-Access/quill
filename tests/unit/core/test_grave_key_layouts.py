"""The grave key is found by position on every layout (#1753)."""

from __future__ import annotations

import pytest

from quill.core.grave_key import (
    MAC_KVK_ANSI_GRAVE,
    MAC_KVK_ISO_SECTION,
    VK_OEM_3,
    is_grave_key,
)

# Windows: the hardware scan code lives in bits 16-23 of the raw key flags.
_SCAN_0X29_FLAGS = 0x29 << 16


@pytest.mark.parametrize("platform", ["win32", "darwin", "linux"])
def test_back_tick_character_matches_everywhere(platform: str) -> None:
    assert is_grave_key(key_code=ord("`"), platform=platform)
    assert is_grave_key(key_code=0, unicode_key=ord("~"), platform=platform)


def test_mac_us_ansi_keyboard_matches_by_key_code() -> None:
    # Ctrl+Shift with the Control key down: wx may report no printable
    # character at all, only the Mac virtual key code.
    assert is_grave_key(key_code=0, raw_key_code=MAC_KVK_ANSI_GRAVE, platform="darwin")


def test_mac_german_iso_key_above_tab_matches() -> None:
    # German layout: the key above Tab types "^" (Shift gives a degree sign).
    assert is_grave_key(
        key_code=ord("^"),
        unicode_key=ord("°"),
        raw_key_code=MAC_KVK_ISO_SECTION,
        platform="darwin",
    )


def test_mac_german_iso_key_beside_left_shift_matches() -> None:
    # On ISO keyboards macOS reports 0x32 for the extra key beside left Shift
    # ("<" on German); it is the back-tick's code, so it is accepted too.
    assert is_grave_key(
        key_code=ord("<"),
        unicode_key=ord(">"),
        raw_key_code=MAC_KVK_ANSI_GRAVE,
        platform="darwin",
    )


def test_mac_letters_and_digits_do_not_match() -> None:
    # kVK_ANSI_A is 0x00, kVK_ANSI_2 is 0x13, kVK_ANSI_Z is 0x06.
    for raw in (0x00, 0x06, 0x13):
        assert not is_grave_key(key_code=ord("A"), raw_key_code=raw, platform="darwin")


def test_mac_ignores_windows_virtual_key_meaning() -> None:
    # 0xC0 means nothing as a Mac key code; it must not match there.
    assert not is_grave_key(key_code=0, raw_key_code=VK_OEM_3, platform="darwin")


def test_windows_vk_oem_3_matches() -> None:
    assert is_grave_key(key_code=VK_OEM_3, platform="win32")
    assert is_grave_key(key_code=0, raw_key_code=VK_OEM_3, platform="win32")


def test_windows_german_layout_matches_by_scan_code() -> None:
    # German Windows: the key above Tab is VK_OEM_5 (0xDC), scan code 0x29.
    assert is_grave_key(
        key_code=0xDC, raw_key_code=0xDC, raw_key_flags=_SCAN_0X29_FLAGS, platform="win32"
    )


def test_windows_digit_two_is_not_the_grave_key() -> None:
    # 0x32 is the Mac back-tick code but the Windows virtual key for "2".
    assert not is_grave_key(key_code=ord("2"), raw_key_code=MAC_KVK_ANSI_GRAVE, platform="win32")
    assert not is_grave_key(key_code=0, raw_key_code=MAC_KVK_ISO_SECTION, platform="win32")
