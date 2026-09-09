"""``--check``: what this build can actually do, in twelve lines.

Split from :mod:`quill.apps.lite` because it answers a different question and is
the only part of the app that never opens a window somebody uses. That module is
the application -- windows, numbering, the inbox, the main loop; this is the
diagnostic, and it is the first thing worth asking for in a support
conversation.

It exists because a frozen build fails in ways a source build cannot. The native
Rich Edit surface may not come up; a bundled data file may have been dropped by
the packager; a screen reader may not be reachable. Every one of those produces
an app that *starts* and is then quietly wrong, which is the worst shape a
failure can take for somebody who cannot see the window. So the answers are
written to stdout and to ``check.log`` beside the settings, where they can be
read back later or pasted into an email.
"""

from __future__ import annotations

import sys

import wx

from quill.core.lite import APP_NAME, APP_VERSION
from quill.core.lite.paths import data_dir
from quill.ui.richedit_editing import RICH

__all__ = ["run_check"]


def run_check() -> int:
    """Report what this build can actually do, to stdout and to check.log.

    The only way to smoke-test a frozen build without disturbing a running copy,
    and the first thing worth asking for in a support conversation: it answers
    whether the native surface came up, which text mode the control is in,
    whether a screen reader is reachable, and where the data lives.
    """
    # Imported here, not at module scope: quill.apps.lite imports this module's
    # run_check on the --check path, so a top-level import back into it would be
    # circular.
    from quill.apps.lite import _TITLE, ScreenReaderVoice
    from quill.ui.richedit_editing import create_richedit_document

    app = wx.App(redirect=False)
    frame = wx.Frame(None, title=_TITLE)
    surface = create_richedit_document(wx, frame, wx.TE_MULTILINE, RICH)
    editor = surface.quill_richedit
    lines = [
        f"{APP_NAME} {APP_VERSION}",
        f"frozen: {getattr(sys, 'frozen', False)}",
        f"python: {sys.version.split()[0]}",
        f"wxPython: {wx.version()}",
        f"native rich edit: {editor.rtf_available()}",
        f"text mode: {editor.current_text_mode()}",
        f"screen reader: {ScreenReaderVoice().backend_name()}",
        f"data dir: {data_dir()}",
    ]
    # Whether the dictionary actually loaded in *this* build. The wordlist is a
    # data file, and a data file is exactly what a frozen build drops silently:
    # the spell checker would then still run, still answer, and quietly call
    # every word a misspelling. Worth one line here rather than a support
    # conversation that starts "it says everything is wrong".
    try:
        from quill.core.spellcheck import backend_info, is_known_word

        info = backend_info()
        lines.append(f"spell backend: {getattr(info, 'name', info)}")
        lines.append(f"spell dictionary usable: {is_known_word('letter')}")
    except Exception as exc:  # noqa: BLE001 - a diagnostic reports, it does not raise
        lines.append(f"spell backend: unavailable ({exc})")
    try:
        surface.ChangeValue("check")
        surface.SetSelection(0, 5)
        editor.set_heading(1)
        lines.append(f"heading applied: {editor.heading_level_at_caret() == 1}")
        lines.append(f"describe: {editor.caret_format_description()}")
    except Exception as exc:  # noqa: BLE001 - a diagnostic reports, it does not raise
        lines.append(f"heading check failed: {exc}")
    frame.Destroy()
    del app
    report = "\n".join(lines)
    try:
        (data_dir() / "check.log").write_text(report + "\n", encoding="utf-8")
    except OSError:
        pass
    print(report)
    return 0
