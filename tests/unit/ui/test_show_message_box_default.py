"""Regression: the two host _show_message_box implementations must accept a
call that omits ``style``.

Shared surfaces call ``frame._show_message_box(message, caption)`` on the
error path (e.g. an unreadable audiobook in the Chapter Workbench, a Safe Mode
publish refusal). When ``style`` was a required parameter that 2-argument call
raised TypeError -- crashing the very code trying to report a failure. Both
hosts (AppShellFrame for the standalone apps, MainFrame for the editor) must
give ``style`` a default so those calls surface the message instead.
"""

from __future__ import annotations

import inspect

from quill.ui.app_shell import AppShellFrame
from quill.ui.main_frame import MainFrame


def _style_has_default(func) -> bool:
    param = inspect.signature(func).parameters["style"]
    return param.default is not inspect.Parameter.empty


def test_app_shell_show_message_box_style_optional():
    assert _style_has_default(AppShellFrame._show_message_box)


def test_main_frame_show_message_box_style_optional():
    assert _style_has_default(MainFrame._show_message_box)
