"""Recognising the grave key by where it sits, not by what it types (#1753).

The QUILL key and the WordPress keys both end on the grave key, the one above
Tab. Only a US layout calls that key a back-tick. On a German layout it types
``^`` (and the back-tick is a dead key somewhere else), on French it types
``²``, on Nordic layouts ``§`` or ``|``. A check that looks only for the
character therefore works on a US layout and nowhere else, which is exactly
what a German VoiceOver user found on macOS.

So the key is matched on four kinds of evidence, any one of which is enough:

1. the character: wx's key code or Unicode key is a back-tick or a tilde;
2. Windows: the virtual key is ``VK_OEM_3`` (0xC0), what wx often reports for
   that key on a US layout;
3. Windows: the hardware scan code in bits 16-23 of the raw key flags is
   0x29, the key above Tab on every PC keyboard whatever the layout;
4. macOS: the raw key code is the Mac virtual key code, which names a
   physical position and never changes with the layout. That key is
   ``kVK_ANSI_Grave`` (0x32) on an ANSI keyboard. On an ISO keyboard (the
   one sold in Germany, the UK and most of Europe) macOS reports the key above
   Tab as ``kVK_ISO_Section`` (0x0A) and the extra key beside the left Shift
   as 0x32, so both are accepted: either way the user presses the key in the
   back-tick's place.

The macOS codes are checked only on macOS. On Windows 0x32 is the virtual key
for the digit 2, so accepting it there would turn Ctrl+Shift+2 into the QUILL
key. No wx here: callers read the event and pass plain numbers.
"""

from __future__ import annotations

import sys

__all__ = [
    "MAC_KVK_ANSI_GRAVE",
    "MAC_KVK_ISO_SECTION",
    "PC_SCAN_CODE_GRAVE",
    "VK_OEM_3",
    "is_grave_key",
]

#: Windows virtual key for the US back-tick key.
VK_OEM_3 = 0xC0
#: PC hardware scan code of the key above Tab, on every layout.
PC_SCAN_CODE_GRAVE = 0x29
#: macOS virtual key code of the back-tick key on an ANSI keyboard.
MAC_KVK_ANSI_GRAVE = 0x32
#: macOS virtual key code of the key above Tab on an ISO keyboard.
MAC_KVK_ISO_SECTION = 0x0A

_GRAVE_CHARACTERS = frozenset({ord("`"), ord("~")})
_MAC_GRAVE_POSITIONS = frozenset({MAC_KVK_ANSI_GRAVE, MAC_KVK_ISO_SECTION})


def _current_platform() -> str:
    """``sys.platform``, behind a function so a test can stand on macOS."""
    return sys.platform


def is_grave_key(
    *,
    key_code: int,
    unicode_key: int = 0,
    raw_key_code: int = 0,
    raw_key_flags: int = 0,
    platform: str | None = None,
) -> bool:
    """True when a key press is the grave key, on any layout.

    *platform* defaults to ``sys.platform`` and is a parameter so tests can
    ask the macOS question on Windows.
    """
    if key_code in _GRAVE_CHARACTERS or unicode_key in _GRAVE_CHARACTERS:
        return True
    plat = _current_platform() if platform is None else platform
    if plat == "darwin":
        return raw_key_code in _MAC_GRAVE_POSITIONS
    if raw_key_code == VK_OEM_3 or key_code == VK_OEM_3:
        return True
    return bool(raw_key_flags) and ((raw_key_flags >> 16) & 0xFF) == PC_SCAN_CODE_GRAVE
