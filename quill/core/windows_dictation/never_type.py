"""Programs dictation never types into: a list the person keeps (D-24).

Dictation that types into other programs -- QUILL Transcribe, Quill Inkwell's
Dictate Anywhere, Recent Phrases' Insert Again -- already refuses a password
field, a program running as administrator and QUILL's own windows
(:func:`quill.ui.windows_dictation_external.foreground_problem`). This is the
fourth refusal, and the only one the person chooses: a list of program file
names, ``windows_dictation_never_type``, where nothing is ever typed.

* **Matched by the program's file name only** -- ``keepass.exe`` -- never by a
  window title: a title is whatever the program says it is, and a document
  called "KeePass notes" in Notepad is not KeePass. Case does not matter.
* **It starts as the password managers.** The default is
  :data:`quill.core.expansion.targets.DENIED_PROCESSES`, the list Quill
  Inkwell's expansion already refuses, so the two features agree about which
  programs hold secrets. Unlike expansion's, this one can be changed: a person
  who has no password manager loses nothing, and one who uses another can add
  it.
* **Said once, typed never.** The refusal names the program
  (:func:`refusal`); held words stay held (target_hold.py), because the check
  is one more reason a field cannot be written, not a new path.

wx-free and platform-free.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import PureWindowsPath

from quill.core.expansion.targets import DENIED_PROCESSES

__all__ = [
    "DEFAULT_NEVER_TYPE",
    "coerce_never_type",
    "friendly_name",
    "is_listed",
    "normalise_image_name",
    "refusal",
]

#: The list a new install has: the programs expansion already refuses.
DEFAULT_NEVER_TYPE: tuple[str, ...] = tuple(sorted(DENIED_PROCESSES))

#: What each default is called when the refusal names it. The file names were
#: checked against each program's current Windows release (2026-10-13) except
#: where a comment says otherwise; an unlisted name is said as its file name.
_FRIENDLY: dict[str, str] = {
    "1password.exe": "1Password",
    "bitwarden.exe": "Bitwarden",
    "consent.exe": "the Windows administrator prompt",
    "credentialuibroker.exe": "the Windows sign-in prompt",
    # Dashlane's Windows app was retired in 2022 for its browser extension;
    # kept for anybody still running the old one. Not verified on a live copy.
    "dashlane.exe": "Dashlane",
    "enpass.exe": "Enpass",
    "keepass.exe": "KeePass",
    "keepassxc.exe": "KeePassXC",
    # Keeper's desktop app: the file name is not verified on a live copy.
    "keeper.exe": "Keeper",
    # LastPass's Windows app: the file name is not verified on a live copy.
    "lastpass.exe": "LastPass",
    "lockapp.exe": "the Windows lock screen",
    "logonui.exe": "the Windows sign-in screen",
    "nordpass.exe": "NordPass",
    # RoboForm's desktop editor: the file name is not verified on a live copy.
    "roboform.exe": "RoboForm",
}


def normalise_image_name(text: object) -> str:
    """A program file name as the list keeps it: ``keepass.exe``.

    A path is cut to its last part, quotes and spaces at either end go, case
    is folded, and a bare name gains ``.exe`` (somebody typing "KeePass" means
    the program). ``""`` for nothing usable.
    """
    name = str(text or "").strip().strip('"').strip()
    if not name:
        return ""
    name = PureWindowsPath(name).name.strip().lower()
    if not name or name in (".", ".."):
        return ""
    if "." not in name:
        name += ".exe"
    return name


def coerce_never_type(value: object) -> list[str]:
    """The saved list, cleaned: file names, once each, in the saved order.

    Anything that is not a list (a missing field, a hand-edited string) is the
    default. An empty list is kept: the person emptied it.
    """
    if not isinstance(value, (list, tuple)):
        return list(DEFAULT_NEVER_TYPE)
    names: list[str] = []
    for item in value:
        name = normalise_image_name(item)
        if name and name not in names:
            names.append(name)
    return names


def is_listed(image_name: str, names: Iterable[str]) -> bool:
    """Whether *image_name* (the program in front) is on the list."""
    image = normalise_image_name(image_name)
    if not image:
        return False
    return image in {normalise_image_name(name) for name in names}


def friendly_name(image_name: str) -> str:
    """What the program is called in a sentence: KeePass, or its file name."""
    image = normalise_image_name(image_name)
    return _FRIENDLY.get(image, image)


def refusal(image_name: str, names: Iterable[str]) -> str:
    """The sentence when the program in front is on the list, else ``""``."""
    if not is_listed(image_name, names):
        return ""
    return f"Dictation does not type into {friendly_name(image_name)}. Move to another program."
