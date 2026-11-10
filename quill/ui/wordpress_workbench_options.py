"""Workbench Options and the editor's way in (W6).

A mixin on :class:`quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`
for Tools > Workbench Options: which Watches run (15.7). The choices are kept
by :mod:`quill.core.wordpress.workbench_options`
beside the site list; the doors read them through
:func:`quill.core.wordpress.workbench_flag.workbench_window_enabled`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.wordpress.workbench_options import WorkbenchOptions, load_options, save_options
from quill.core.wordpress.workbench_watches import KINDS
from quill.ui import wordpress_workbench_dialogs as wdlg

__all__ = ["WorkbenchOptionsCommands"]


class WorkbenchOptionsCommands:
    """Tools > Workbench Options."""

    parent: Any
    say: Callable[[str], None]
    show_modal: Callable[[Any, str], int]
    _data_dir: Any

    def options(self) -> WorkbenchOptions:
        return load_options(self._data_dir)

    def do_options(self, _ref: Any, _row: Any) -> None:
        options = self.options()
        kinds = list(KINDS)
        rows = [f"Watch: {KINDS[k]}" for k in kinds]
        checked = [i for i, k in enumerate(kinds) if k in options.watches]
        picked = wdlg.ask_checks(
            self.parent,
            self.show_modal,
            title="Workbench Options",
            prompt="&Options:",
            rows=rows,
            checked=checked,
            help_text="Each Watch is said when it happens, "
            "checked at most every fifteen minutes while the editor is open.",
        )
        if picked is None:
            return
        options.watches = tuple(k for i, k in enumerate(kinds) if i in picked)
        save_options(options, self._data_dir)
        self.say("Workbench options saved.")
