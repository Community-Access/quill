"""Simple File Open dialog — keyboard-first, screen-reader-friendly file picker.

Implements issue #620. Opt-in via ``Settings.use_simple_file_dialog``. When the
setting is on, ``MainFrame.open_file`` shows this dialog instead of the standard
``wx.FileDialog``. Layout:

- Path field (Ctrl+L focuses it, Enter moves to the list).
- File-type filter (``Supported files`` first, then per-type, then All files).
- File/folder list with ``.. (parent directory)`` and ``[dir]`` prefixes.
- Toolbar: Up (parent), Hidden toggle, Recent, Use Windows Dialog fallback.
- Status line for errors; the dialog stays open until the user opens a file
  or cancels.

Keyboard:
- Enter in the path field -> focus the list, select the first match.
- Enter in the list (or double-click) -> activate: navigate into a directory
  or open the selected file.
- Backspace in the list -> go up one directory.
- Ctrl+H in the path or list -> toggle hidden files (Cmd+Shift+. on macOS).
- Escape -> cancel.

The dialog returns a :class:`SimpleOpenResult` from :meth:`SimpleOpenDialog.show`
so the caller can distinguish "user opened a file" from "user asked for the
native dialog" from "user cancelled".
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

import wx

from quill.core.i18n import _
from quill.ui.dialog_contract import (
    apply_modal_ids,
    show_modal_dialog,
)


def _toggle_hidden_key_pressed(event: wx.KeyEvent) -> bool:
    """Hidden-files toggle: Ctrl+H on Windows, Cmd+Shift+. on macOS (Cmd+H = Hide) (#51)."""
    if sys.platform == "darwin":
        return event.CmdDown() and event.ShiftDown() and event.GetKeyCode() == ord(".")
    return event.ControlDown() and event.GetKeyCode() in (ord("H"), ord("h"))


# ---------------------------------------------------------------------------
# Filter definitions
# ---------------------------------------------------------------------------

# Each entry: (label, extensions). Extensions are lowercase, no leading dot.
_FILTERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        _("Supported files (*.txt;*.md;*.html;*.htm;*.rtf)"),
        ("txt", "md", "html", "htm", "rtf"),
    ),
    (_("Plain text (*.txt)"), ("txt",)),
    (
        _("Markdown (*.md;*.markdown;*.mdown;*.mkd;*.mkdn)"),
        ("md", "markdown", "mdown", "mkd", "mkdn"),
    ),
    (
        _("HTML (*.html;*.htm;*.xhtml)"),
        ("html", "htm", "xhtml"),
    ),
    (_("Rich Text (*.rtf)"), ("rtf",)),
    (_("All files (*.*)"), ()),
)


def _file_matches_filter(path: Path, allowed: tuple[str, ...]) -> bool:
    if not allowed:
        return True
    return path.suffix.lstrip(".").lower() in allowed


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SimpleOpenResult:
    """Result of :meth:`SimpleOpenDialog.show`.

    Exactly one of ``path`` (user opened a file) or ``fallback`` (user asked
    for the native Windows dialog) or ``cancelled`` (user pressed Escape or
    the Cancel button) is set.
    """

    path: Path | None = None
    fallback: bool = False
    cancelled: bool = True

    @classmethod
    def opened(cls, path: Path) -> SimpleOpenResult:
        return cls(path=path, fallback=False, cancelled=False)

    @classmethod
    def use_native(cls) -> SimpleOpenResult:
        return cls(path=None, fallback=True, cancelled=False)

    @classmethod
    def cancel(cls) -> SimpleOpenResult:
        return cls(path=None, fallback=False, cancelled=True)


# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------


class SimpleOpenDialog:
    """Keyboard-friendly file open dialog.

    The caller supplies a parent ``wx.Frame`` (``MainFrame.frame``), an
    initial directory, and a list of recent files. The dialog keeps no
    knowledge of the open pipeline; it returns a :class:`SimpleOpenResult`
    from ``show()``.
    """

    def __init__(
        self,
        parent: wx.Window,
        *,
        initial_dir: Path | None = None,
        initial_filter: int = 0,
        recent_files: Iterable[Path] | None = None,
        announce: Callable[[str], None] | None = None,
    ) -> None:
        self._wx = wx
        self._parent = parent
        self._announce = announce or (lambda _msg: None)
        self._recent_files: list[Path] = list(recent_files or [])
        self._show_hidden: bool = False
        self._result: SimpleOpenResult = SimpleOpenResult.cancel()
        # The list of (path, is_dir) entries currently shown in the ListBox.
        # An empty path means "parent directory".
        self._rows: list[tuple[Path | None, bool]] = []

        # Start in ``initial_dir`` if it exists and is a directory; otherwise
        # fall back to the user's home directory.
        start = initial_dir if initial_dir is not None and initial_dir.is_dir() else None
        self._cwd: Path = start or Path.home()

        self._filter_index: int = 0
        if 0 <= initial_filter < len(_FILTERS):
            self._filter_index = initial_filter

        # --- Dialog window -------------------------------------------------
        self.dialog: wx.Dialog = wx.Dialog(
            parent,
            title=_("Open File"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetName("simple_open")
        self.dialog.SetSize((720, 540))
        self.dialog.SetMinSize((560, 400))

        root = wx.BoxSizer(wx.VERTICAL)

        # --- Path field ---------------------------------------------------
        path_row = wx.BoxSizer(wx.HORIZONTAL)
        path_label = wx.StaticText(self.dialog, label=_("&Path:"))
        path_label.SetName("Path label")
        path_row.Add(path_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self._path_ctrl = wx.TextCtrl(self.dialog, value=str(self._cwd), style=wx.TE_PROCESS_ENTER)
        self._path_ctrl.SetName("Path")
        path_row.Add(self._path_ctrl, 1, wx.EXPAND)
        root.Add(path_row, 0, wx.EXPAND | wx.ALL, 8)

        # --- Filter choice ------------------------------------------------
        filter_row = wx.BoxSizer(wx.HORIZONTAL)
        filter_label = wx.StaticText(self.dialog, label=_("&Filter:"))
        filter_label.SetName("Filter label")
        filter_row.Add(filter_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self._filter_choice = wx.Choice(self.dialog, choices=[label for label, _exts in _FILTERS])
        self._filter_choice.SetName("File type filter")
        self._filter_choice.SetSelection(self._filter_index)
        filter_row.Add(self._filter_choice, 0)
        root.Add(filter_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # --- Toolbar ------------------------------------------------------
        toolbar = wx.BoxSizer(wx.HORIZONTAL)
        self._btn_up = wx.Button(self.dialog, label=_("&Up"))
        self._btn_up.SetName("Up to parent folder")
        self._btn_hidden = wx.ToggleButton(self.dialog, label=_("&Hidden"))
        self._btn_hidden.SetName("Show hidden files")
        self._btn_recent = wx.Button(self.dialog, label=_("&Recent"))
        self._btn_recent.SetName("Recent locations")
        toolbar.Add(self._btn_up, 0, wx.RIGHT, 4)
        toolbar.Add(self._btn_hidden, 0, wx.RIGHT, 4)
        toolbar.Add(self._btn_recent, 0)
        toolbar.AddStretchSpacer(1)
        self._btn_fallback = wx.Button(self.dialog, label=_("Use &Windows Dialog"))
        self._btn_fallback.SetName("Use Windows dialog instead")
        toolbar.Add(self._btn_fallback, 0)
        root.Add(toolbar, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # --- File list ----------------------------------------------------
        self._list = wx.ListBox(self.dialog, style=wx.LB_SINGLE)
        self._list.SetName("Files")
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        # --- Status line --------------------------------------------------
        self._status = wx.StaticText(self.dialog, label="")
        self._status.SetName("Status")
        root.Add(self._status, 0, wx.EXPAND | wx.ALL, 8)

        # --- OK / Cancel --------------------------------------------------
        btn_sizer = wx.StdDialogButtonSizer()
        self._btn_ok = wx.Button(self.dialog, wx.ID_OK, label=_("&Open"))
        self._btn_ok.SetDefault()
        self._btn_ok.SetName("Open selected file")
        btn_cancel = wx.Button(self.dialog, wx.ID_CANCEL, label=_("Cancel"))
        self._btn_cancel = btn_cancel
        self._btn_cancel.SetName("Cancel")
        btn_sizer.AddButton(self._btn_ok)
        btn_sizer.AddButton(self._btn_cancel)
        btn_sizer.Realize()
        root.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 8)

        self.dialog.SetSizer(root)

        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)

        # --- Events -------------------------------------------------------
        self._path_ctrl.Bind(wx.EVT_TEXT, self._on_path_changed)
        self._path_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_path_enter)
        self._filter_choice.Bind(wx.EVT_CHOICE, self._on_filter_changed)
        self._list.Bind(wx.EVT_LISTBOX_DCLICK, self._on_activate)
        self._list.Bind(wx.EVT_KEY_DOWN, self._on_list_key)
        self._path_ctrl.Bind(wx.EVT_KEY_DOWN, self._on_path_key)
        self._btn_up.Bind(wx.EVT_BUTTON, self._on_up)
        self._btn_hidden.Bind(wx.EVT_TOGGLEBUTTON, self._on_hidden_toggle)
        self._btn_recent.Bind(wx.EVT_BUTTON, self._on_recent)
        self._btn_fallback.Bind(wx.EVT_BUTTON, self._on_fallback)

        # Populate initial state. We populate the list before showing so the
        # initial focus target is computed against real content.
        self._populate()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show(self) -> SimpleOpenResult:
        """Show the dialog modally and return the user's choice.

        Always destroys the dialog, even on exception. Initial focus lands on
        the path field (a content control, not the OK button), and the
        standard modal ids wire Enter and Escape for free.
        """
        try:
            self.dialog.CentreOnParent()
            self._path_ctrl.SetFocus()
            self._path_ctrl.SetSelection(-1, -1)  # select all for easy overwrite
            result = show_modal_dialog(
                self.dialog,
                _("Open File"),
                announce=self._announce,
            )
            # Honour the explicit focus we set in show() even if the modal
            # helper moved it.
            if result == wx.ID_OK:
                # If the user pressed OK without double-clicking, use the
                # current list selection.
                self._accept_from_selection()
            return self._result
        finally:
            self.dialog.Destroy()

    # ------------------------------------------------------------------
    # Path field handlers
    # ------------------------------------------------------------------

    def _on_path_changed(self, _event: wx.Event) -> None:
        # We don't auto-navigate on every keystroke (it would steal focus
        # from the path field). Instead, only update the list display when
        # the user presses Enter or Tab-out. For now, just clear errors.
        self._set_status("")

    def _on_path_enter(self, _event: wx.Event) -> None:
        text = self._path_ctrl.GetValue().strip()
        if not text:
            return
        candidate = Path(text).expanduser()
        if not candidate.exists():
            self._set_status(_("Error: path does not exist: ") + text, error=True)
            return
        if candidate.is_file():
            self._result = SimpleOpenResult.opened(candidate.resolve())
            self.dialog.EndModal(wx.ID_OK)
            return
        if candidate.is_dir():
            self._cwd = candidate.resolve()
            self._path_ctrl.SetValue(str(self._cwd))
            self._populate()
            self._list.SetFocus()
            self._list.SetSelection(0)
            return
        self._set_status(_("Error: not a file or directory: ") + text, error=True)

    def _on_path_key(self, event: wx.KeyEvent) -> None:
        # Ctrl+L is a no-op here because focus is already in the path field,
        # but we keep the binding for consistency with the documented
        # keyboard map.
        if event.ControlDown() and event.GetKeyCode() in (ord("L"), ord("l")):
            return
        if _toggle_hidden_key_pressed(event):
            self._show_hidden = not self._show_hidden
            self._btn_hidden.SetValue(self._show_hidden)
            self._populate()
            return
        event.Skip()

    # ------------------------------------------------------------------
    # Filter handlers
    # ------------------------------------------------------------------

    def _on_filter_changed(self, _event: wx.Event) -> None:
        self._filter_index = self._filter_choice.GetSelection()
        self._populate()

    # ------------------------------------------------------------------
    # List handlers
    # ------------------------------------------------------------------

    def _on_activate(self, _event: wx.Event) -> None:
        self._activate_selected()

    def _on_list_key(self, event: wx.KeyEvent) -> None:
        key = event.GetKeyCode()
        if key == wx.WXK_BACK:
            self._go_up()
            return
        if _toggle_hidden_key_pressed(event):
            self._show_hidden = not self._show_hidden
            self._btn_hidden.SetValue(self._show_hidden)
            self._populate()
            return
        if event.ControlDown() and key in (ord("L"), ord("l")):
            self._path_ctrl.SetFocus()
            self._path_ctrl.SetSelection(-1, -1)
            return
        if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self._activate_selected()
            return
        event.Skip()

    def _activate_selected(self) -> None:
        index = self._list.GetSelection()
        if index == wx.NOT_FOUND or index < 0 or index >= len(self._rows):
            return
        path, is_dir = self._rows[index]
        if is_dir:
            if path is None:
                self._go_up()
            else:
                self._cwd = path
                self._path_ctrl.SetValue(str(self._cwd))
                self._populate()
            return
        if path is not None and path.is_file():
            self._result = SimpleOpenResult.opened(path)
            self.dialog.EndModal(wx.ID_OK)

    def _accept_from_selection(self) -> None:
        if self._result.cancelled and not self._result.fallback:
            # The user pressed OK without double-clicking. If a file is
            # selected, accept it; otherwise leave the result as cancelled.
            self._activate_selected()

    # ------------------------------------------------------------------
    # Toolbar handlers
    # ------------------------------------------------------------------

    def _on_up(self, _event: wx.Event) -> None:
        self._go_up()

    def _on_hidden_toggle(self, _event: wx.Event) -> None:
        self._show_hidden = self._btn_hidden.GetValue()
        self._populate()

    def _on_recent(self, _event: wx.Event) -> None:
        if not self._recent_files:
            self._set_status(_("No recent files yet."), error=False)
            return
        menu = wx.Menu()
        for idx, path in enumerate(self._recent_files):
            label = str(path)
            item = menu.Append(wx.ID_ANY, label)
            self.dialog.Bind(
                wx.EVT_MENU,
                lambda _e, p=path: self._open_recent(p),
                id=item.GetId(),
            )
            del idx  # silence linter
        self.dialog.PopupMenu(menu)
        menu.Destroy()

    def _open_recent(self, path: Path) -> None:
        if not path.exists():
            self._set_status(_("Error: path no longer exists: ") + str(path), error=True)
            return
        if path.is_file():
            self._result = SimpleOpenResult.opened(path.resolve())
            self.dialog.EndModal(wx.ID_OK)
            return
        if path.is_dir():
            self._cwd = path.resolve()
            self._path_ctrl.SetValue(str(self._cwd))
            self._populate()
            return

    def _on_fallback(self, _event: wx.Event) -> None:
        self._result = SimpleOpenResult.use_native()
        self.dialog.EndModal(wx.ID_CANCEL)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _go_up(self) -> None:
        parent = self._cwd.parent
        if parent == self._cwd:
            # Already at a filesystem root.
            return
        self._cwd = parent
        self._path_ctrl.SetValue(str(self._cwd))
        self._populate()

    # ------------------------------------------------------------------
    # List population
    # ------------------------------------------------------------------

    def _populate(self) -> None:
        labels: list[str] = []
        self._rows = []
        if self._cwd.parent != self._cwd:
            labels.append(".. (parent directory)")
            self._rows.append((None, True))
        try:
            entries = sorted(self._cwd.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError:
            self._set_status(_("Error: permission denied: ") + str(self._cwd), error=True)
            entries = []
        except OSError as exc:
            self._set_status(_("Error: cannot read directory: ") + str(exc), error=True)
            entries = []
        allowed = _FILTERS[self._filter_index][1]
        for entry in entries:
            name = entry.name
            if not self._show_hidden and self._is_hidden(name, entry):
                continue
            if entry.is_dir():
                labels.append(f"[dir] {name}")
                self._rows.append((entry, True))
            elif entry.is_file() and _file_matches_filter(entry, allowed):
                labels.append(f"      {name}")
                self._rows.append((entry, False))
        self._list.Set(labels)
        if labels:
            self._list.SetSelection(0)
        self._set_status(self._cwd_str_with_count(len(self._rows)))

    @staticmethod
    def _is_hidden(name: str, entry: Path) -> bool:
        if name.startswith("."):
            return True
        # Windows: treat the hidden attribute as hidden.
        try:
            if entry.is_file() or entry.is_dir():
                attrs = entry.stat().st_file_attributes  # type: ignore[attr-defined]
                if attrs & 0x2:  # FILE_ATTRIBUTE_HIDDEN
                    return True
        except (AttributeError, OSError):
            pass
        return False

    def _cwd_str_with_count(self, n: int) -> str:
        # Status line summary of the current directory plus visible count.
        return f"{self._cwd}  ({n} entries)"

    # ------------------------------------------------------------------
    # Status line
    # ------------------------------------------------------------------

    def _set_status(self, message: str, *, error: bool = False) -> None:
        self._status.SetLabel(message)
        if error:
            self._status.SetForegroundColour(wx.RED)
        else:
            self._status.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT))
        self._status.Refresh()
        if message:
            self._announce(message)


__all__ = ["SimpleOpenDialog", "SimpleOpenResult"]
