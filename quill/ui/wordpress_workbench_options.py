"""Workbench Options and the editor's way in (W6, decision 7).

A mixin on :class:`quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`
for Tools > Workbench Options: **Use the classic WordPress windows** (the old
Tools > WordPress windows, parked for one release). The choices are kept by
:mod:`quill.core.wordpress.workbench_options` beside the site list; the doors read them through
:func:`quill.core.wordpress.workbench_flag.workbench_window_enabled`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.wordpress.workbench_options import (
    CLASSIC_LABEL,
    WorkbenchOptions,
    load_options,
    save_options,
)
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
        rows = [CLASSIC_LABEL]
        checked = [0] if options.classic_windows else []
        picked = wdlg.ask_checks(
            self.parent,
            self.show_modal,
            title="Workbench Options",
            prompt="&Options:",
            rows=rows,
            checked=checked,
            help_text="Use the classic WordPress windows sends each Tools > WordPress door to "
            "its own window again, for this release only.",
        )
        if picked is None:
            return
        classic = 0 in picked
        options.classic_windows = classic
        save_options(options, self._data_dir)
        if classic:
            self.say(
                "Tools > WordPress opens the classic windows from now on. Open WordPress "
                "Workbench is still on that menu."
            )
        else:
            self.say("Tools > WordPress opens the Workbench.")
