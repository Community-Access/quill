"""One document, one window.

Every DocumentFrame owns exactly one editor and one document. There are no
tabs. The menu bar is generated from COMMANDS so the F1 shortcut list and the
uniqueness test cannot drift from what is actually bound.
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path

import wx

from quilllite import APP_NAME, __version__, recovery, speech
from quilllite.commands import COMMANDS, shortcut_text
from quilllite.dialogs import (
    FindDialog,
    ReplaceDialog,
    ask_line_number,
    choose_heading,
    show_text_window,
)
from quilllite.editor import BODY_POINT_SIZE, PLAIN, RICH, Editor, RichEditError, create_editor
from quilllite.rtf_safety import scan_rtf_safety

RICH_SUFFIXES = {".rtf"}
_TEXT_LIKE = "*.txt;*.rtf;*.md;*.log;*.csv;*.json;*.py;*.html"
OPEN_WILDCARD = (
    f"All supported files ({_TEXT_LIKE})|{_TEXT_LIKE}|"
    "Text files (*.txt)|*.txt|Rich Text (*.rtf)|*.rtf|Markdown (*.md)|*.md|All files (*.*)|*.*"
)
SAVE_WILDCARD_PLAIN = (
    "Text files (*.txt)|*.txt|Markdown (*.md)|*.md|Rich Text (*.rtf)|*.rtf|All files (*.*)|*.*"
)
SAVE_WILDCARD_RICH = "Rich Text (*.rtf)|*.rtf|Text files (*.txt)|*.txt|All files (*.*)|*.*"


class DocumentFrame(wx.Frame):
    def __init__(
        self,
        app,
        path: Path | None = None,
        mode: str | None = None,
        recovery_slot: recovery.RecoverySlot | None = None,
    ) -> None:
        settings = app.settings
        super().__init__(None, title=APP_NAME, size=(settings.window_width, settings.window_height))
        self.app = app
        self.path: Path | None = None
        self.modified = False
        self.newline = "\r\n"
        self.encoding = "utf-8"
        self._loading = False
        self._find_options: dict = {}
        self._find_dialog: wx.Dialog | None = None
        self._slot: recovery.RecoverySlot | None = None
        self._window_menu_items: list[int] = []
        self._check_items: dict[str, wx.MenuItem] = {}

        self.editor: Editor = create_editor(wx, self, mode or settings.default_mode)
        self.CreateStatusBar(3)
        self._build_menus()
        self._apply_editor_font()
        self.apply_theme()
        self.editor.set_word_wrap(settings.word_wrap)

        self.editor.control.Bind(wx.EVT_TEXT, self._on_text)
        self.editor.control.Bind(wx.EVT_KEY_UP, self._on_caret_moved)
        self.editor.control.Bind(wx.EVT_LEFT_UP, self._on_caret_moved)
        self.Bind(wx.EVT_CLOSE, self._on_close)
        self.Bind(wx.EVT_ACTIVATE, self._on_activate)
        self.Bind(wx.EVT_MENU_OPEN, self._on_menu_open)

        self._autosave = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_autosave_tick, self._autosave)
        self._autosave.Start(max(15, settings.autosave_seconds) * 1000)

        if settings.window_maximized:
            self.Maximize(True)
        if recovery_slot is not None:
            self._load_recovery(recovery_slot)
        elif path is not None:
            self.load(path)
        self._update_title()
        self._update_status()
        self.editor.control.SetFocus()

    # ------------------------------------------------------------------ #
    # Menus
    # ------------------------------------------------------------------ #

    def _build_menus(self) -> None:
        bar = wx.MenuBar()
        menus: dict[str, wx.Menu] = {}
        for menu_label, label, key, handler, kind in COMMANDS:
            menu = menus.get(menu_label)
            if menu is None:
                menu = wx.Menu()
                menus[menu_label] = menu
                bar.Append(menu, menu_label)
                if menu_label == "&File":
                    self._recent_menu = wx.Menu()
            if kind == "sep":
                menu.AppendSeparator()
                continue
            item_kind = wx.ITEM_CHECK if kind == "check" else wx.ITEM_NORMAL
            item = menu.Append(wx.ID_ANY, f"{label}\t{key}", kind=item_kind)
            self.Bind(wx.EVT_MENU, self._dispatch(handler), item)
            if kind == "check":
                self._check_items[handler] = item
            if handler == "cmd_open":
                menu.AppendSubMenu(self._recent_menu, "Open &Recent")
        self._window_menu = menus["&Window"]
        self._window_menu.AppendSeparator()
        self.SetMenuBar(bar)
        self.refresh_recent_menu()
        self.refresh_window_menu()
        self._sync_check_items()

    def _dispatch(self, handler: str):
        def run(_event: wx.CommandEvent) -> None:
            getattr(self, handler)()

        return run

    def _sync_check_items(self) -> None:
        self._check_items["cmd_toggle_dark"].Check(self.app.settings.theme == "dark")
        self._check_items["cmd_toggle_wrap"].Check(self.app.settings.word_wrap)

    def refresh_recent_menu(self) -> None:
        for item in list(self._recent_menu.GetMenuItems()):
            self._recent_menu.Delete(item)
        # Entries whose file has gone are skipped rather than offered: choosing
        # one would only ever produce a "does not exist" prompt.
        recent = [p for p in self.app.settings.recent_files if Path(p).exists()]
        if not recent:
            item = self._recent_menu.Append(wx.ID_ANY, "No recent files")
            item.Enable(False)
            return
        for index, path in enumerate(recent[:9], start=1):
            item = self._recent_menu.Append(
                wx.ID_ANY, f"&{index} {Path(path).name}  ({Path(path).parent})"
            )
            self.Bind(wx.EVT_MENU, lambda e, p=path: self.app.open_path(Path(p)), item)

    def refresh_window_menu(self) -> None:
        for item_id in self._window_menu_items:
            self._window_menu.Delete(item_id)
        self._window_menu_items = []
        for index, frame in enumerate(self.app.frames, start=1):
            label = frame.document_name()
            if index <= 9:
                label = f"&{index} {label}\tAlt+{index}"
            item = self._window_menu.Append(wx.ID_ANY, label, kind=wx.ITEM_CHECK)
            item.Check(frame is self)
            self._window_menu_items.append(item.GetId())
            self.Bind(wx.EVT_MENU, lambda e, f=frame: self.app.focus_frame(f), item)

    def _on_menu_open(self, event: wx.MenuEvent) -> None:
        self._sync_check_items()
        event.Skip()

    # ------------------------------------------------------------------ #
    # Document state
    # ------------------------------------------------------------------ #

    def document_name(self) -> str:
        return self.path.name if self.path else "Untitled"

    def _update_title(self) -> None:
        mode = "rich text" if self.editor.mode == RICH else "plain text"
        star = "*" if self.modified else ""
        self.SetTitle(f"{star}{self.document_name()} - {APP_NAME} ({mode})")

    def _update_status(self) -> None:
        try:
            pos = self.editor.control.GetInsertionPoint()
            _ok, col, line = self.editor.control.PositionToXY(pos)
            self.SetStatusText(f"Line {line + 1}, column {col + 1}", 0)
        except Exception:
            pass
        self.SetStatusText("Rich text" if self.editor.mode == RICH else "Plain text", 1)
        self.SetStatusText("Modified" if self.modified else "Saved", 2)

    def _set_modified(self, modified: bool) -> None:
        if modified == self.modified:
            return
        self.modified = modified
        self._update_title()
        self._update_status()
        if modified and self._slot is None:
            self._slot = recovery.new_slot(self.editor.mode, str(self.path) if self.path else "")

    def _on_text(self, event: wx.CommandEvent) -> None:
        if not self._loading:
            self._set_modified(True)
        event.Skip()

    def _on_caret_moved(self, event: wx.Event) -> None:
        self._update_status()
        event.Skip()

    def _on_activate(self, event: wx.ActivateEvent) -> None:
        if event.GetActive():
            self.app.active_frame = self
        event.Skip()

    def speak(self, text: str) -> None:
        speech.speak(text)
        self.SetStatusText(text, 2)

    # ------------------------------------------------------------------ #
    # Load and save
    # ------------------------------------------------------------------ #

    def load(self, path: Path) -> bool:
        path = Path(path)
        mode = RICH if path.suffix.lower() in RICH_SUFFIXES else PLAIN
        self._loading = True
        try:
            if mode == RICH:
                if not self.editor.native():
                    raise RichEditError("Rich text needs the Windows Rich Edit control.")
                raw = path.read_text(encoding="utf-8", errors="replace")
                report = scan_rtf_safety(raw)
                self._set_mode_internal(RICH)
                self.editor.set_rtf(report.sanitized_rtf.encode("utf-8", errors="replace"))
                self._apply_rich_theme_colour()
                if report.blocked:
                    self.speak("Removed for safety: " + ", ".join(report.blocked))
            else:
                data = path.read_bytes()
                text, self.encoding = _decode_text(data)
                self.newline = "\r\n" if "\r\n" in text else "\n"
                text = text.replace("\r\n", "\n").replace("\r", "\n")
                self._set_mode_internal(PLAIN)
                self.editor.set_text(text)
        except (OSError, RichEditError) as exc:
            self._loading = False
            wx.MessageBox(
                f"Could not open {path.name}.\n\n{exc}", "Open failed", wx.OK | wx.ICON_ERROR, self
            )
            return False
        finally:
            self._loading = False
        self.path = path
        self._discard_slot()
        self.modified = False
        self.app.settings.remember_recent(str(path))
        self.app.save_settings()
        self.app.refresh_all_menus()
        self.editor.control.SetInsertionPoint(0)
        self._update_title()
        self._update_status()
        return True

    def _load_recovery(self, slot: recovery.RecoverySlot) -> None:
        self._loading = True
        try:
            if slot.mode == RICH and self.editor.native():
                self._set_mode_internal(RICH)
                self.editor.load_rtf(str(slot.content_path))
                self._apply_rich_theme_colour()
            else:
                self._set_mode_internal(PLAIN)
                text, self.encoding = _decode_text(slot.content_path.read_bytes())
                self.editor.set_text(text.replace("\r\n", "\n"))
        except (OSError, RichEditError) as exc:
            wx.MessageBox(
                f"Could not restore {slot.title}.\n\n{exc}",
                "Recovery failed",
                wx.OK | wx.ICON_ERROR,
                self,
            )
        finally:
            self._loading = False
        if slot.original_path and Path(slot.original_path).exists():
            self.path = Path(slot.original_path)
        self._slot = slot
        self.modified = True
        self._update_title()
        self._update_status()

    def save(self, target: Path | None = None) -> bool:
        target = target or self.path
        if target is None:
            return self.cmd_save_as()
        target = Path(target)
        try:
            if self.editor.mode == RICH:
                self._write_rtf(target)
            else:
                text = self.editor.get_text().replace("\n", self.newline)
                _write_bytes_atomic(target, text.encode(self.encoding, errors="replace"))
        except (OSError, RichEditError) as exc:
            wx.MessageBox(
                f"Could not save {target.name}.\n\n{exc}",
                "Save failed",
                wx.OK | wx.ICON_ERROR,
                self,
            )
            return False
        self.path = target
        self._discard_slot()
        self._set_modified(False)
        self._update_title()
        self.app.settings.remember_recent(str(target))
        self.app.save_settings()
        self.app.refresh_all_menus()
        self.speak(f"Saved {target.name}")
        return True

    def _write_rtf(self, target: Path) -> None:
        """Save via the TOM to a temp file beside the target, then replace.

        The theme colour is reset to automatic for the duration of the save so
        dark mode never leaks light grey text into the file.
        """
        tmp = target.with_name(target.name + ".quilllite-tmp")
        self._set_whole_document_colour(None)
        try:
            self.editor.save_rtf(str(tmp))
            os.replace(tmp, target)
        finally:
            self._apply_rich_theme_colour()
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass

    def _write_recovery_copy(self) -> None:
        slot = self._slot
        if slot is None or not self.modified:
            return
        try:
            if self.editor.mode == RICH and slot.mode == RICH:
                tmp = slot.content_path.with_suffix(".rtf.tmp")
                self._set_whole_document_colour(None)
                try:
                    self.editor.save_rtf(str(tmp))
                finally:
                    self._apply_rich_theme_colour()
                os.replace(tmp, slot.content_path)
            else:
                if slot.mode != self.editor.mode:
                    recovery.discard(slot)
                    slot = self._slot = recovery.new_slot(
                        self.editor.mode, str(self.path) if self.path else ""
                    )
                _write_bytes_atomic(slot.content_path, self.editor.get_text().encode("utf-8"))
            slot.original_path = str(self.path) if self.path else ""
            recovery.write_meta(slot)
        except (OSError, RichEditError):
            pass

    def _discard_slot(self) -> None:
        if self._slot is not None:
            recovery.discard(self._slot)
            self._slot = None

    def _on_autosave_tick(self, _event: wx.TimerEvent) -> None:
        self._write_recovery_copy()

    def confirm_discard(self) -> bool:
        """True when it is fine to lose this window's content."""
        if not self.modified:
            return True
        self.Raise()
        answer = wx.MessageBox(
            f"Save changes to {self.document_name()}?",
            APP_NAME,
            wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION,
            self,
        )
        if answer == wx.YES:
            return self.save()
        return answer == wx.NO

    def _on_close(self, event: wx.CloseEvent) -> None:
        if event.CanVeto() and not self.confirm_discard():
            event.Veto()
            return
        self._autosave.Stop()
        self._discard_slot()
        self.app.settings.window_maximized = self.IsMaximized()
        if not self.IsMaximized():
            width, height = self.GetSize()
            self.app.settings.window_width, self.app.settings.window_height = width, height
        self.app.forget_frame(self)
        self.Destroy()

    # ------------------------------------------------------------------ #
    # Mode, theme, font
    # ------------------------------------------------------------------ #

    def _set_mode_internal(self, mode: str) -> None:
        """Switch the control's text mode with the buffer emptied first."""
        control = self.editor.control
        control.ChangeValue("")
        self.editor.set_mode(mode)
        self._apply_editor_font()
        self._update_title()
        self._update_status()

    def switch_mode(self, mode: str) -> None:
        if mode == self.editor.mode:
            return
        if mode == RICH and not self.editor.native():
            self.speak("Rich text needs the Windows Rich Edit control")
            return
        text = self.editor.get_text()
        caret = self.editor.control.GetInsertionPoint()
        if mode == PLAIN and self.editor.mode == RICH:
            answer = wx.MessageBox(
                "Switching to plain text removes all formatting. Continue?",
                APP_NAME,
                wx.YES_NO | wx.ICON_QUESTION,
                self,
            )
            if answer != wx.YES:
                return
        self._loading = True
        try:
            self._set_mode_internal(mode)
            self.editor.set_text(text)
            self._apply_rich_theme_colour()
        finally:
            self._loading = False
        self.editor.control.SetInsertionPoint(min(caret, len(text)))
        if self.path is not None and (self.path.suffix.lower() in RICH_SUFFIXES) != (mode == RICH):
            self.path = None  # a rich document cannot be saved back over a .txt without Save As
        self._set_modified(True)
        self.speak("Rich text mode" if mode == RICH else "Plain text mode")

    def _apply_editor_font(self) -> None:
        settings = self.app.settings
        if self.editor.mode == RICH:
            font = wx.Font(
                int(BODY_POINT_SIZE),
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                faceName=settings.font_name,
            )
            self.editor.control.SetFont(font)
            self.editor.set_zoom(settings.font_size, BODY_POINT_SIZE)
        else:
            font = wx.Font(
                settings.font_size,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                faceName=settings.font_name,
            )
            self.editor.control.SetFont(font)
            self.editor.set_zoom(0, 0)

    def theme_colours(self) -> tuple[wx.Colour, wx.Colour, wx.Colour]:
        if self.app.settings.theme == "dark":
            return wx.Colour(230, 230, 230), wx.Colour(30, 30, 30), wx.Colour(45, 45, 45)
        return (
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT),
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW),
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DFACE),
        )

    def apply_theme(self) -> None:
        fg, bg, chrome = self.theme_colours()
        control = self.editor.control
        control.SetBackgroundColour(bg)
        self.editor.set_background(bg.Red(), bg.Green(), bg.Blue())
        if self.editor.mode == PLAIN:
            control.SetForegroundColour(fg)
        else:
            self._apply_rich_theme_colour()
        self.SetBackgroundColour(chrome)
        status = self.GetStatusBar()
        if status is not None:
            status.SetBackgroundColour(chrome)
            status.SetForegroundColour(fg)
        control.Refresh()
        self.Refresh()

    def _apply_rich_theme_colour(self) -> None:
        if self.editor.mode != RICH or not self.editor.native():
            return
        fg, _bg, _chrome = self.theme_colours()
        if self.app.settings.theme == "dark":
            self._set_whole_document_colour((fg.Red(), fg.Green(), fg.Blue()))
        else:
            self._set_whole_document_colour(None)

    def _set_whole_document_colour(self, rgb: tuple[int, int, int] | None) -> None:
        if self.editor.mode != RICH or not self.editor.native():
            return
        was_loading = self._loading
        self._loading = True  # a theme recolour is not an edit
        try:
            self.editor.set_whole_document_colour(rgb)
        except RichEditError:
            pass
        finally:
            self._loading = was_loading

    # ------------------------------------------------------------------ #
    # File commands
    # ------------------------------------------------------------------ #

    def cmd_new(self) -> None:
        self.app.new_window(self.app.settings.default_mode)

    def cmd_new_rich(self) -> None:
        self.app.new_window(RICH)

    def cmd_new_plain(self) -> None:
        self.app.new_window(PLAIN)

    def cmd_open(self) -> None:
        default_dir = str(self.path.parent) if self.path else ""
        with wx.FileDialog(
            self,
            "Open",
            defaultDir=default_dir,
            wildcard=OPEN_WILDCARD,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE,
        ) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            paths = [Path(p) for p in dialog.GetPaths()]
        for path in paths:
            self.app.open_path(path, reuse=self if self._is_blank() else None)

    def _is_blank(self) -> bool:
        return self.path is None and not self.modified and not self.editor.get_text()

    def cmd_save(self) -> None:
        self.save()

    def cmd_save_as(self) -> bool:
        wildcard = SAVE_WILDCARD_RICH if self.editor.mode == RICH else SAVE_WILDCARD_PLAIN
        default_name = (
            self.path.name
            if self.path
            else ("Untitled.rtf" if self.editor.mode == RICH else "Untitled.txt")
        )
        default_dir = str(self.path.parent) if self.path else ""
        with wx.FileDialog(
            self,
            "Save As",
            defaultDir=default_dir,
            defaultFile=default_name,
            wildcard=wildcard,
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return False
            target = Path(dialog.GetPath())
        wants_rich = target.suffix.lower() in RICH_SUFFIXES
        if wants_rich and self.editor.mode == PLAIN:
            self.switch_mode(RICH)
        elif not wants_rich and self.editor.mode == RICH:
            answer = wx.MessageBox(
                "Saving as plain text removes all formatting. Continue?",
                APP_NAME,
                wx.YES_NO | wx.ICON_QUESTION,
                self,
            )
            if answer != wx.YES:
                return False
            text = self.editor.get_text()
            self._loading = True
            try:
                self._set_mode_internal(PLAIN)
                self.editor.set_text(text)
                self.apply_theme()
            finally:
                self._loading = False
        return self.save(target)

    def cmd_close(self) -> None:
        self.Close()

    def cmd_exit(self) -> None:
        self.app.exit_all()

    # ------------------------------------------------------------------ #
    # Edit commands
    # ------------------------------------------------------------------ #

    def cmd_undo(self) -> None:
        if self.editor.control.CanUndo():
            self.editor.control.Undo()
        else:
            self.speak("Nothing to undo")

    def cmd_redo(self) -> None:
        if self.editor.control.CanRedo():
            self.editor.control.Redo()
        else:
            self.speak("Nothing to redo")

    def cmd_cut(self) -> None:
        self.editor.control.Cut()

    def cmd_copy(self) -> None:
        self.editor.control.Copy()

    def cmd_paste(self) -> None:
        self.editor.control.Paste()

    def cmd_select_all(self) -> None:
        self.editor.control.SelectAll()

    def cmd_insert_datetime(self) -> None:
        self.editor.control.WriteText(time.strftime("%H:%M %d/%m/%Y"))

    def cmd_goto_line(self) -> None:
        control = self.editor.control
        total = max(1, control.GetNumberOfLines())
        _ok, _col, line = control.PositionToXY(control.GetInsertionPoint())
        chosen = ask_line_number(self, line + 1, total)
        if chosen is None:
            return
        position = control.XYToPosition(0, chosen - 1)
        if position < 0:
            position = control.GetLastPosition()
        control.SetInsertionPoint(position)
        control.SetFocus()
        self._update_status()

    # -- find and replace ------------------------------------------------ #

    def _selected_or_word(self) -> str:
        start, end = self.editor.control.GetSelection()
        if end > start:
            return self.editor.get_text()[start:end]
        return self._find_options.get("needle", "")

    def cmd_find(self) -> None:
        if self._find_dialog is not None and self._find_dialog:
            try:
                self._find_dialog.Raise()
                return
            except RuntimeError:
                self._find_dialog = None
        self._find_dialog = FindDialog(self, self._selected_or_word(), self._do_find)
        self._find_dialog.Bind(wx.EVT_WINDOW_DESTROY, self._forget_find_dialog)
        self._find_dialog.Show()

    def _forget_find_dialog(self, event: wx.WindowDestroyEvent) -> None:
        if event.GetEventObject() is self._find_dialog:
            self._find_dialog = None
        event.Skip()

    def cmd_find_next(self) -> None:
        if not self._find_options.get("needle"):
            self.cmd_find()
            return
        self._do_find(self._find_options, False)

    def cmd_find_previous(self) -> None:
        if not self._find_options.get("needle"):
            self.cmd_find()
            return
        self._do_find(self._find_options, True)

    def _pattern(self, options: dict) -> re.Pattern | None:
        needle = options.get("needle", "")
        if not needle:
            return None
        flags = 0 if options.get("match_case") else re.IGNORECASE
        body = re.escape(needle)
        if options.get("whole_word"):
            body = rf"\b{body}\b"
        return re.compile(body, flags)

    def _do_find(self, options: dict, reverse: bool) -> bool:
        pattern = self._pattern(options)
        if pattern is None:
            self.speak("Type something to find")
            return False
        self._find_options = dict(options)
        text = self.editor.get_text()
        sel_start, sel_end = self.editor.control.GetSelection()
        wrapped = False
        if reverse:
            matches = list(pattern.finditer(text[:sel_start]))
            if not matches:
                matches = list(pattern.finditer(text))
                wrapped = True
            match = matches[-1] if matches else None
        else:
            match = pattern.search(text, sel_end if sel_end > sel_start else sel_start)
            if match is None:
                match = pattern.search(text)
                wrapped = True
        if match is None:
            self.speak(f"Not found: {options.get('needle')}")
            return False
        self.editor.control.SetSelection(match.start(), match.end())
        self.editor.control.ShowPosition(match.start())
        self.editor.control.SetFocus()
        self._update_status()
        if wrapped:
            self.speak("Wrapped to the start" if not reverse else "Wrapped to the end")
        return True

    def cmd_replace(self) -> None:
        dialog = ReplaceDialog(
            self, self._selected_or_word(), self._do_find, self._do_replace, self._do_replace_all
        )
        dialog.Show()

    def _do_replace(self, options: dict) -> None:
        pattern = self._pattern(options)
        if pattern is None:
            self.speak("Type something to find")
            return
        start, end = self.editor.control.GetSelection()
        selected = self.editor.get_text()[start:end]
        if end > start and pattern.fullmatch(selected):
            self.editor.control.Replace(start, end, options.get("replacement", ""))
            self._set_modified(True)
        self._do_find(options, False)

    def _do_replace_all(self, options: dict) -> None:
        pattern = self._pattern(options)
        if pattern is None:
            self.speak("Type something to find")
            return
        if self.editor.mode == RICH:
            answer = wx.MessageBox(
                "Replace all in a rich text document removes formatting on the "
                "replaced text. Continue?",
                APP_NAME,
                wx.YES_NO | wx.ICON_QUESTION,
                self,
            )
            if answer != wx.YES:
                return
        text = self.editor.get_text()
        replacement = options.get("replacement", "")
        count = 0
        # Walk from the end so earlier offsets stay valid, and use Replace so undo works.
        for match in reversed(list(pattern.finditer(text))):
            self.editor.control.Replace(match.start(), match.end(), replacement)
            count += 1
        if count:
            self._set_modified(True)
        self.speak(f"Replaced {count} occurrence{'s' if count != 1 else ''}")

    # ------------------------------------------------------------------ #
    # Format commands
    # ------------------------------------------------------------------ #

    def _require_rich(self) -> bool:
        if self.editor.mode != RICH:
            self.speak("Not available in plain text. Press Control Shift M to switch to rich text.")
            return False
        if not self.editor.native():
            self.speak("Rich text formatting is unavailable on this system")
            return False
        return True

    def _toggle_attr(self, attr: str, label: str) -> None:
        if not self._require_rich():
            return
        try:
            state = self.editor.toggle(attr)
        except RichEditError as exc:
            self.speak(str(exc))
            return
        self._set_modified(True)
        self.speak(f"{label} on" if state else f"{label} off")

    def cmd_bold(self) -> None:
        self._toggle_attr("Bold", "Bold")

    def cmd_italic(self) -> None:
        self._toggle_attr("Italic", "Italic")

    def cmd_underline(self) -> None:
        self._toggle_attr("Underline", "Underline")

    def _heading(self, level: int) -> None:
        if not self._require_rich():
            return
        try:
            self.editor.set_heading(level)
        except RichEditError as exc:
            self.speak(str(exc))
            return
        self._set_modified(True)
        self.speak(f"Heading {level}" if level else "Body text")

    def cmd_heading_0(self) -> None:
        self._heading(0)

    def cmd_heading_1(self) -> None:
        self._heading(1)

    def cmd_heading_2(self) -> None:
        self._heading(2)

    def cmd_heading_3(self) -> None:
        self._heading(3)

    def cmd_heading_4(self) -> None:
        self._heading(4)

    def _align(self, how: str, label: str) -> None:
        if not self._require_rich():
            return
        try:
            self.editor.set_alignment(how)
        except RichEditError as exc:
            self.speak(str(exc))
            return
        self._set_modified(True)
        self.speak(label)

    def cmd_align_left(self) -> None:
        self._align("left", "Aligned left")

    def cmd_align_center(self) -> None:
        self._align("center", "Centred")

    def cmd_align_right(self) -> None:
        self._align("right", "Aligned right")

    def cmd_selection_font(self) -> None:
        if not self._require_rich():
            return
        with wx.FontDialog(self, wx.FontData()) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            font = dialog.GetFontData().GetChosenFont()
        try:
            self.editor.set_font_name(font.GetFaceName())
            self.editor.set_font_size(font.GetPointSize())
        except RichEditError as exc:
            self.speak(str(exc))
            return
        self._set_modified(True)
        self.speak(f"{font.GetFaceName()}, {font.GetPointSize()} point")

    def cmd_describe(self) -> None:
        if self.editor.mode != RICH:
            self.speak("Plain text")
            return
        try:
            self.speak(self.editor.describe_caret())
        except RichEditError as exc:
            self.speak(str(exc))

    def cmd_switch_mode(self) -> None:
        self.switch_mode(PLAIN if self.editor.mode == RICH else RICH)

    # ------------------------------------------------------------------ #
    # Navigate
    # ------------------------------------------------------------------ #

    def _navigate_heading(self, reverse: bool) -> None:
        if self.editor.mode != RICH:
            self.speak("Headings are only available in rich text")
            return
        caret = self.editor.control.GetInsertionPoint()
        found = self.editor.next_heading(caret, reverse=reverse)
        if found is None:
            self.speak("No previous heading" if reverse else "No next heading")
            return
        start, level = found
        self.editor.control.SetInsertionPoint(start)
        self.editor.control.ShowPosition(start)
        self.editor.control.SetFocus()
        self._update_status()
        self.speak(f"Heading {level}: {self.editor.paragraph_text_at(start)}")

    def cmd_next_heading(self) -> None:
        self._navigate_heading(False)

    def cmd_previous_heading(self) -> None:
        self._navigate_heading(True)

    def cmd_list_headings(self) -> None:
        if self.editor.mode != RICH:
            self.speak("Headings are only available in rich text")
            return
        headings = self.editor.all_headings()
        if not headings:
            self.speak("No headings in this document")
            return
        target = choose_heading(self, headings)
        if target is None:
            self.editor.control.SetFocus()
            return
        self.editor.control.SetInsertionPoint(target)
        self.editor.control.ShowPosition(target)
        self.editor.control.SetFocus()
        self._update_status()

    # ------------------------------------------------------------------ #
    # View
    # ------------------------------------------------------------------ #

    def cmd_toggle_dark(self) -> None:
        settings = self.app.settings
        settings.theme = "system" if settings.theme == "dark" else "dark"
        self.app.save_settings()
        for frame in self.app.frames:
            frame.apply_theme()
            frame._sync_check_items()
        self.speak("Dark mode on" if settings.theme == "dark" else "Dark mode off")

    def cmd_toggle_wrap(self) -> None:
        settings = self.app.settings
        settings.word_wrap = not settings.word_wrap
        self.app.save_settings()
        for frame in self.app.frames:
            frame.editor.set_word_wrap(settings.word_wrap)
            frame._sync_check_items()
        self.speak("Word wrap on" if settings.word_wrap else "Word wrap off")

    def _set_text_size(self, size: int) -> None:
        settings = self.app.settings
        settings.font_size = max(6, min(72, size))
        self.app.save_settings()
        for frame in self.app.frames:
            frame._apply_editor_font()
        self.speak(f"{settings.font_size} point")

    def cmd_zoom_in(self) -> None:
        self._set_text_size(self.app.settings.font_size + 1)

    def cmd_zoom_out(self) -> None:
        self._set_text_size(self.app.settings.font_size - 1)

    def cmd_zoom_reset(self) -> None:
        self._set_text_size(12)

    def cmd_editor_font(self) -> None:
        settings = self.app.settings
        data = wx.FontData()
        data.SetInitialFont(
            wx.Font(
                settings.font_size,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                faceName=settings.font_name,
            )
        )
        with wx.FontDialog(self, data) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            font = dialog.GetFontData().GetChosenFont()
        settings.font_name = font.GetFaceName()
        settings.font_size = font.GetPointSize()
        self.app.save_settings()
        for frame in self.app.frames:
            frame._apply_editor_font()
        self.speak(f"Editor font {settings.font_name}, {settings.font_size} point")

    def cmd_statistics(self) -> None:
        text = self.editor.get_text()
        words = len(re.findall(r"\S+", text))
        chars = len(text)
        lines = text.count("\n") + (1 if text else 0)
        self.speak(f"{words} words, {chars} characters, {lines} lines")

    # ------------------------------------------------------------------ #
    # Window and help
    # ------------------------------------------------------------------ #

    def cmd_next_window(self) -> None:
        self.app.cycle(self, 1)

    def cmd_previous_window(self) -> None:
        self.app.cycle(self, -1)

    def cmd_shortcuts(self) -> None:
        show_text_window(self, "Keyboard shortcuts", shortcut_text())

    def cmd_about(self) -> None:
        body = (
            f"{APP_NAME} {__version__}\n\n"
            "A small notepad and wordpad replacement for screen reader users.\n"
            "One document per window. Plain text or rich text, nothing else.\n\n"
            "Derived from QUILL for All by Community Access and BITS (MIT licence).\n"
            "https://github.com/Community-Access/quill\n\n"
            f"Settings and recovery files: {self.app.data_dir}"
        )
        show_text_window(self, f"About {APP_NAME}", body)


# ---------------------------------------------------------------------- #
# helpers
# ---------------------------------------------------------------------- #


def _decode_text(data: bytes) -> tuple[str, str]:
    if data.startswith(b"\xef\xbb\xbf"):
        return data[3:].decode("utf-8", errors="replace"), "utf-8-sig"
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16", errors="replace"), "utf-16"
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace"), "cp1252"


def _write_bytes_atomic(target: Path, payload: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".quilllite-tmp")
    tmp.write_bytes(payload)
    os.replace(tmp, target)
