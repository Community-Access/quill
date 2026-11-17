"""The user folder's name is cut from every spelling of a Windows path.

The crash reports in #1838 and #1841 quoted paths as JSON and as Python
reprs, with doubled backslashes, and the single-backslash pattern let the
Windows user name through in both.
"""

from __future__ import annotations

import pytest

from quill.stability.redaction import redact_command_arg, redact_text_for_bundle


@pytest.mark.parametrize(
    "text",
    [
        r"C:\Users\zelda\AppData\Roaming\Quill\autosave\a.snap",
        r"C:\\Users\\zelda\\AppData\\Roaming\\Quill\\autosave\\a.snap",
        "C:/Users/zelda/AppData/Roaming/Quill/autosave/a.snap",
        r"c:\documents and settings\zelda\x.txt",
        r'  "snapshot": "C:\\Users\\zelda\\AppData\\a.snap"',
        r"module 'comtypes.gen' from 'C:\\Users\\zelda\\AppData\\Local\\x.py'",
    ],
)
def test_the_user_folder_name_never_survives(text: str) -> None:
    assert "zelda" not in redact_command_arg(text)
    assert "zelda" not in redact_text_for_bundle(text)
    assert "[PATH]" in redact_command_arg(text)


def test_the_rest_of_the_path_stays_readable() -> None:
    assert redact_command_arg(r"C:\\Users\\zelda\\AppData\\a.snap") == r"[PATH]\\AppData\\a.snap"
    assert redact_command_arg(r"C:\Users\zelda\AppData") == r"[PATH]\AppData"


def test_a_path_outside_the_user_folders_is_left_alone() -> None:
    text = r"C:\\Program Files\\QUILL for All\\Lib\\site-packages"
    assert redact_command_arg(text) == text
