"""Simple Open File dialog integration for MainFrame (#620).

When ``Settings.use_simple_file_dialog`` is true, ``MainFrame.open_file``
shows the keyboard-friendly :class:`SimpleOpenDialog` instead of the standard
``wx.FileDialog``. The simple dialog has a "Use Windows Dialog" button that
returns a fallback result, which the caller translates into a one-shot
invocation of the native dialog. Ctrl+O, the File > Open... menu item, the
Command Palette, the frame context menu, and File > Open Recent all funnel
through :meth:`MainFrame.open_file`, so this mixin is the only place that
needs to know which dialog to show.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from quill.ui.simple_open_dialog import SimpleOpenDialog, SimpleOpenResult

if TYPE_CHECKING:
    from quill.ui.main_frame import MainFrame


class SimpleOpenMixin:
    """Adds the simple open-dialog branch to ``MainFrame.open_file``.

    The mixin reads ``self.settings.use_simple_file_dialog`` and either:
    1. shows the :class:`SimpleOpenDialog`; or
    2. shows the standard ``wx.FileDialog`` (the historical default); or
    3. shows the simple dialog first and, if the user pressed the
       "Use Windows Dialog" button inside it, falls through to the
       standard ``wx.FileDialog`` for one invocation.
    """

    # The default initial directory for the simple dialog. Set by
    # ``MainFrame`` at startup. ``MainFrame.open_file`` reads
    # ``_file_dialog_default_dir`` and feeds it in.

    def _prompt_for_open_path(self) -> Path | None:
        """Run the appropriate file-open dialog and return the chosen path.

        Returns ``None`` if the user cancelled or the dialog did not
        produce a path. This helper isolates the dialog-choice branching
        from the rest of :meth:`MainFrame.open_file` so the open pipeline
        is unchanged regardless of which dialog is shown.
        """
        if TYPE_CHECKING:
            self: MainFrame
        use_simple = bool(getattr(self.settings, "use_simple_file_dialog", False))
        if not use_simple:
            return self._prompt_native_open_dialog()
        # ``_prompt_simple_open_dialog`` returns ``None`` for both "user
        # cancelled" and "user pressed the Use Windows Dialog button". We
        # cannot distinguish them from the return value alone, so the helper
        # signals fallback by setting a side-channel attribute on itself.
        self._simple_dialog_wants_fallback = False
        result = self._prompt_simple_open_dialog()
        if getattr(self, "_simple_dialog_wants_fallback", False):
            return self._prompt_native_open_dialog()
        return result

    def _prompt_simple_open_dialog(self) -> Path | None:
        """Show the simple dialog. ``None`` means cancel, fallback, or
        no selection. The caller decides what to do next based on
        whether a fallback was requested.

        Fallback is signalled by setting ``self._simple_dialog_wants_fallback``
        to ``True`` so the dispatcher in :meth:`_prompt_for_open_path` can
        route the next prompt to the native dialog. We can't use the return
        value alone because ``None`` is already taken for "user cancelled".
        """
        if TYPE_CHECKING:
            self: MainFrame
        from quill.core.recent import load_recent_files  # local import: avoid cycle

        initial_dir = self._simple_open_initial_dir()
        recent = getattr(self, "recent_files", None) or load_recent_files()
        announce = getattr(self, "_announce", None)
        dialog = SimpleOpenDialog(
            self.frame,
            initial_dir=initial_dir,
            recent_files=recent,
            announce=announce,
        )
        result: SimpleOpenResult = dialog.show()
        if result.fallback:
            self._simple_dialog_wants_fallback = True
            return None
        if result.cancelled or result.path is None:
            return None
        self._last_file_dir = str(result.path.parent)
        return result.path

    def _prompt_native_open_dialog(self) -> Path | None:
        """Show the standard ``wx.FileDialog`` and return the chosen path.

        This is the original dialog body that used to live inline in
        ``MainFrame.open_file``. It is kept here so the simple-dialog
        path can call it as a fallback.
        """
        wx = self._wx
        with wx.FileDialog(
            self.frame,
            "Open text file",
            defaultDir=self._file_dialog_default_dir(),
            wildcard=(
                "Supported files"
                " (*.txt;*.md;*.html;*.htm;*.xhtml;*.json;*.yaml;*.yml;"
                "*.toml;*.xml;*.csv;*.tsv;*.ipynb;*.sqlite;*.db;"
                "*.doc;*.docx;*.ppt;*.pptx;*.epub;*.pages;*.pdf;*.odt;*.rtf;"
                "*.py;*.js;*.jsx;*.ts;*.tsx;*.kt;*.kts;*.go;*.rs;*.c;*.cpp;"
                "*.h;*.hpp;*.java;*.swift;*.cs;*.rb;*.php;*.sh;*.ps1;*.lua;"
                "*.css;*.scss;*.less;*.sql;*.log;*.diff;*.patch;*.ini;*.cfg;*.conf;"
                "*.gradle;*.properties;*.gitignore;*.env)|"
                "*.txt;*.md;*.html;*.htm;*.xhtml;*.json;*.yaml;*.yml;"
                "*.toml;*.xml;*.csv;*.tsv;*.ipynb;*.sqlite;*.db;"
                "*.doc;*.docx;*.ppt;*.pptx;*.epub;*.pages;*.pdf;*.odt;*.rtf;"
                "*.py;*.js;*.jsx;*.ts;*.tsx;*.kt;*.kts;*.go;*.rs;*.c;*.cpp;"
                "*.h;*.hpp;*.java;*.swift;*.cs;*.rb;*.php;*.sh;*.ps1;*.lua;"
                "*.css;*.scss;*.less;*.sql;*.log;*.diff;*.patch;*.ini;*.cfg;*.conf;"
                "*.gradle;*.properties;*.gitignore;*.env|"
                "Documents (*.txt;*.md;*.html;*.htm;*.docx;*.odt;*.rtf;*.pdf;*.epub)|"
                "*.txt;*.md;*.html;*.htm;*.docx;*.odt;*.rtf;*.pdf;*.epub|"
                "Source code"
                " (*.py;*.js;*.jsx;*.ts;*.tsx;*.kt;*.kts;*.go;*.rs;*.c;*.cpp;"
                "*.h;*.hpp;*.java;*.swift;*.cs;*.rb;*.php;*.sh;*.ps1;*.lua)|"
                "*.py;*.js;*.jsx;*.ts;*.tsx;*.kt;*.kts;*.go;*.rs;*.c;*.cpp;"
                "*.h;*.hpp;*.java;*.swift;*.cs;*.rb;*.php;*.sh;*.ps1;*.lua|"
                "All files (*.*)|*.*"
            ),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Open text file") != wx.ID_OK:
                return None
            chosen = Path(dialog.GetPath())
            self._last_file_dir = str(chosen.parent)
            return chosen

    def _simple_open_initial_dir(self) -> Path | None:
        """Resolve the initial directory for the simple dialog.

        Mirrors :meth:`MainFrame._file_dialog_default_dir` but returns a
        ``Path`` (or ``None``) instead of a string. The simple dialog
        needs a real ``Path`` so it can use ``iterdir()`` etc.
        """
        if TYPE_CHECKING:
            self: MainFrame
        last = getattr(self, "_last_file_dir", "")
        if last:
            try:
                p = Path(last)
                if p.is_dir():
                    return p
            except OSError:
                pass
        configured = getattr(self.settings, "startup_folder", "")
        if configured:
            try:
                p = Path(configured)
                if p.is_dir():
                    return p
            except OSError:
                pass
        try:
            docs = self._wx.StandardPaths.Get().GetDocumentsDir()
            if docs:
                p = Path(docs)
                if p.is_dir():
                    return p
        except Exception:  # noqa: BLE001 - non-Windows or no StandardPaths
            pass
        return None
