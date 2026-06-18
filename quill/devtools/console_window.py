"""Developer Console wx.Frame — the main QDC UI window.

Layout (F6 cycles between regions):
  1. Transcript  — read-only multiline TextCtrl
  2. Input       — editable multiline TextCtrl
  3. Status bar  — StaticText showing language / doc / worker state
  4. Buttons     — Run, Clear, Copy, Save, Help, Close

Keyboard contract (§7.2):
  Enter          Execute (when input is a complete statement)
  Shift+Enter    Insert newline in input
  Ctrl+Enter     Force execute multi-line block
  Up / Down      History navigation (when cursor at first / last line)
  Ctrl+L         Clear transcript
  Ctrl+Shift+C   Copy transcript
  Ctrl+S         Save transcript
  Esc            Return focus to editor
  F1             Console help
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from quill.ui.dialog_contract import show_message_box

if TYPE_CHECKING:
    pass

_PROMPT_PY = ">>> "
_PROMPT_PY_CONT = "... "
_PROMPT_TS = "ts> "
_PROMPT_TS_BUSY = "ts*> "

_LANG_PYTHON = "Python"
_LANG_TS = "TypeScript"


class ConsoleWindow:
    """Non-modal developer console frame.

    Instantiate once and call ``show()`` / ``close()``.  The console is
    created lazily on first ``show()`` to keep startup cost zero.
    """

    def __init__(
        self,
        wx: Any,
        parent: Any,
        on_execute_python: Any,
        on_execute_ts: Any,
        *,
        announce_cb: Callable[[str], None] | None = None,
        focus_editor_cb: Callable[[], None] | None = None,
    ) -> None:
        self._wx = wx
        self._parent = parent
        self._on_execute_python = on_execute_python
        self._on_execute_ts = on_execute_ts
        self._announce = announce_cb or (lambda _: None)
        self._focus_editor = focus_editor_cb
        self._frame: Any = None
        self._transcript: Any = None
        self._input: Any = None
        self._lang_choice: Any = None
        self._status_lbl: Any = None
        self._history_cache: list[str] = []
        self._history_index: int = -1
        self._input_saved: str = ""

    # ------------------------------------------------------------------
    # Public interface

    def show(self) -> None:
        if self._frame is None:
            self._build()
        self._frame.Show()
        self._frame.Raise()
        self._input.SetFocus()

    def close(self) -> None:
        if self._frame:
            self._frame.Hide()
        self._return_focus()

    def is_shown(self) -> bool:
        return self._frame is not None and self._frame.IsShown()

    def append_transcript(self, text: str) -> None:
        """Add *text* to the transcript (thread-safe via CallAfter on the caller side)."""
        if self._transcript is None:
            return
        self._transcript.AppendText(text)

    def _set_status(self, text: str) -> None:
        if self._status_lbl:
            self._status_lbl.SetLabel(text)
        if text:
            self._announce(text)

    def set_status(self, text: str) -> None:
        self._set_status(text)

    def set_language(self, lang: str) -> None:
        """Switch the active console language.  Called by open_python_console /
        open_typescript_console so the Choice control and status reflect the
        language the user actually wants to execute in (was Bug #3: TS console
        launched in Python mode, so typed TS code ran as Python and threw
        syntax errors)."""
        if self._lang_choice is None:
            return
        target = (lang or "").strip()
        for idx in range(self._lang_choice.GetCount()):
            if self._lang_choice.GetString(idx) == target:
                self._lang_choice.SetSelection(idx)
                self.set_status(f"Ready - {target}")
                return

    def load_history(self, entries: list[str]) -> None:
        self._history_cache = list(entries)
        self._history_index = -1

    # ------------------------------------------------------------------
    # Build

    def _build(self) -> None:
        wx = self._wx
        style = wx.DEFAULT_FRAME_STYLE | wx.FRAME_FLOAT_ON_PARENT
        self._frame = wx.Frame(
            self._parent,
            title="QUILL Developer Console",
            style=style,
            size=(800, 550),
        )
        self._frame.SetName("DeveloperConsoleFrame")

        panel = wx.Panel(self._frame)
        panel.SetName("ConsolePanel")
        vbox = wx.BoxSizer(wx.VERTICAL)

        # -- Language selector ------------------------------------------------
        lang_row = wx.BoxSizer(wx.HORIZONTAL)
        lang_lbl = wx.StaticText(panel, label="Language:")
        lang_lbl.SetName("LanguageLabel")
        self._lang_choice = wx.Choice(panel, choices=[_LANG_PYTHON, _LANG_TS])
        self._lang_choice.SetSelection(0)
        self._lang_choice.SetName("LanguageChoice")
        self._lang_choice.SetToolTip("Select Python or TypeScript console")
        lang_row.Add(lang_lbl, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=6)
        lang_row.Add(self._lang_choice, flag=wx.ALIGN_CENTER_VERTICAL)
        vbox.Add(lang_row, flag=wx.EXPAND | wx.ALL, border=6)

        # -- Transcript -------------------------------------------------------
        transcript_lbl = wx.StaticText(panel, label="Transcript:")
        transcript_lbl.SetName("TranscriptLabel")
        vbox.Add(transcript_lbl, flag=wx.LEFT | wx.TOP, border=6)
        self._transcript = wx.TextCtrl(
            panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 | wx.HSCROLL,
        )
        self._transcript.SetName("ConsoleTranscript")
        self._transcript.SetMinSize((-1, 220))
        font = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self._transcript.SetFont(font)
        vbox.Add(self._transcript, proportion=1, flag=wx.EXPAND | wx.ALL, border=6)

        # -- Input ------------------------------------------------------------
        input_lbl = wx.StaticText(panel, label="Input (Enter to run, Shift+Enter for newline):")
        input_lbl.SetName("InputLabel")
        vbox.Add(input_lbl, flag=wx.LEFT | wx.TOP, border=6)
        self._input = wx.TextCtrl(
            panel,
            style=wx.TE_MULTILINE | wx.TE_PROCESS_ENTER | wx.TE_RICH2,
        )
        self._input.SetName("ConsoleInput")
        self._input.SetMinSize((-1, 80))
        self._input.SetFont(font)
        vbox.Add(self._input, flag=wx.EXPAND | wx.ALL, border=6)

        # -- Status -----------------------------------------------------------
        self._status_lbl = wx.StaticText(panel, label="Ready - Python")
        self._status_lbl.SetName("ConsoleStatusBar")
        vbox.Add(self._status_lbl, flag=wx.LEFT | wx.BOTTOM, border=6)

        # -- Buttons ----------------------------------------------------------
        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        run_btn = wx.Button(panel, label="&Run")
        run_btn.SetName("RunButton")
        clear_btn = wx.Button(panel, label="C&lear")
        clear_btn.SetName("ClearButton")
        copy_btn = wx.Button(panel, label="&Copy Transcript")
        copy_btn.SetName("CopyTranscriptButton")
        save_btn = wx.Button(panel, label="&Save Transcript...")
        save_btn.SetName("SaveTranscriptButton")
        help_btn = wx.Button(panel, label="&Help")
        help_btn.SetName("HelpButton")
        close_btn = wx.Button(panel, label="Clos&e")
        close_btn.SetName("CloseButton")

        for btn in (run_btn, clear_btn, copy_btn, save_btn, help_btn, close_btn):
            btn_row.Add(btn, flag=wx.RIGHT, border=4)
        btn_row.AddStretchSpacer()
        vbox.Add(btn_row, flag=wx.EXPAND | wx.ALL, border=6)

        panel.SetSizer(vbox)
        self._frame.Layout()

        # -- Event bindings --------------------------------------------------
        # Frame-level char hook so Esc/F1/Ctrl+L work regardless of focus widget.
        self._frame.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        self._input.Bind(wx.EVT_KEY_DOWN, self._on_key_down)
        run_btn.Bind(wx.EVT_BUTTON, lambda _e: self._run_input())
        clear_btn.Bind(wx.EVT_BUTTON, lambda _e: self._clear_transcript())
        copy_btn.Bind(wx.EVT_BUTTON, lambda _e: self._copy_transcript())
        save_btn.Bind(wx.EVT_BUTTON, lambda _e: self._save_transcript())
        help_btn.Bind(wx.EVT_BUTTON, lambda _e: self._show_help())
        close_btn.Bind(wx.EVT_BUTTON, lambda _e: self.close())
        self._frame.Bind(wx.EVT_CLOSE, self._on_close)
        self._lang_choice.Bind(wx.EVT_CHOICE, self._on_lang_changed)

    # ------------------------------------------------------------------
    # Frame-level keyboard hook (Esc, F1, Ctrl+L, Ctrl+Shift+C, Ctrl+S)

    def _on_char_hook(self, event: Any) -> None:
        wx = self._wx
        key = event.GetKeyCode()
        ctrl = event.ControlDown()
        shift = event.ShiftDown()

        # Only handle frame-level shortcuts here; pass input-field keys to _on_key_down.
        if key == wx.WXK_ESCAPE:
            self.close()
            return
        if key == wx.WXK_F1:
            self._show_help()
            return
        if ctrl and not shift and key == ord("L"):
            self._clear_transcript()
            return
        if ctrl and shift and key == ord("C"):
            self._copy_transcript()
            return
        if ctrl and not shift and key == ord("S"):
            self._save_transcript()
            return
        event.Skip()

    # ------------------------------------------------------------------
    # Keyboard handling (input field)

    def _on_key_down(self, event: Any) -> None:
        wx = self._wx
        key = event.GetKeyCode()
        ctrl = event.ControlDown()
        shift = event.ShiftDown()

        if key == wx.WXK_RETURN and not shift and not ctrl:
            self._run_input()
            return
        if key == wx.WXK_RETURN and shift:
            # Insert literal newline
            pos = self._input.GetInsertionPoint()
            self._input.SetInsertionPoint(pos)
            event.Skip()
            return
        if key == wx.WXK_RETURN and ctrl:
            self._run_input()
            return
        if key == wx.WXK_UP:
            # Only navigate history when caret is on the first line.
            if self._caret_on_first_line():
                self._history_up()
                return
        if key == wx.WXK_DOWN:
            # Only navigate history when caret is on the last line.
            if self._caret_on_last_line():
                self._history_down()
                return
        if key == wx.WXK_ESCAPE:
            self.close()
            if self._parent:
                try:
                    self._parent.SetFocus()
                except Exception:
                    pass
            return
        if ctrl and key == ord("L"):
            self._clear_transcript()
            return
        if ctrl and shift and key == ord("C"):
            self._copy_transcript()
            return
        if ctrl and key == ord("S"):
            self._save_transcript()
            return
        if key == wx.WXK_F1:
            self._show_help()
            return
        event.Skip()

    # ------------------------------------------------------------------
    # Caret helpers (used by history navigation to avoid replacing text
    # mid-edit of a multi-line block — Bug #4)

    def _caret_on_first_line(self) -> bool:
        """True when the caret is on the first line of the multi-line input."""
        try:
            caret = self._input.GetInsertionPoint()
            return "\n" not in self._input.GetValue()[:caret]
        except Exception:
            return True

    def _caret_on_last_line(self) -> bool:
        """True when the caret is on the last line of the multi-line input."""
        try:
            value = self._input.GetValue()
            caret = self._input.GetInsertionPoint()
            return "\n" not in value[caret:]
        except Exception:
            return True

    # ------------------------------------------------------------------
    # Execution

    def _run_input(self) -> None:
        source = self._input.GetValue().strip()
        if not source:
            return
        lang_idx = self._lang_choice.GetSelection()
        lang = _LANG_TS if lang_idx == 1 else _LANG_PYTHON
        prompt = _PROMPT_TS if lang == _LANG_TS else _PROMPT_PY
        self._input.Clear()
        self._history_index = -1
        self._input_saved = ""
        # add to history cache
        if not self._history_cache or self._history_cache[-1] != source:
            self._history_cache.append(source)
        if lang == _LANG_TS:
            self._on_execute_ts(source, prompt)
        else:
            self._on_execute_python(source, prompt)

    # ------------------------------------------------------------------
    # History navigation

    def _history_up(self) -> None:
        if not self._history_cache:
            return
        if self._history_index == -1:
            self._input_saved = self._input.GetValue()
            self._history_index = len(self._history_cache) - 1
        elif self._history_index > 0:
            self._history_index -= 1
        entry = self._history_cache[self._history_index]
        self._input.SetValue(entry)
        self._input.SetInsertionPointEnd()
        n = len(self._history_cache)
        self._announce(f"History {n - self._history_index} of {n}: {entry[:40]}")

    def _history_down(self) -> None:
        if self._history_index == -1:
            return
        if self._history_index < len(self._history_cache) - 1:
            self._history_index += 1
            entry = self._history_cache[self._history_index]
            self._input.SetValue(entry)
            self._input.SetInsertionPointEnd()
            n = len(self._history_cache)
            self._announce(f"History {n - self._history_index} of {n}: {entry[:40]}")
        else:
            self._history_index = -1
            self._input.SetValue(self._input_saved)
            self._input.SetInsertionPointEnd()
            self._announce("End of history")

    # ------------------------------------------------------------------
    # Transcript operations

    def _clear_transcript(self) -> None:
        if self._transcript:
            self._transcript.Clear()

    def _copy_transcript(self) -> None:
        wx = self._wx
        if not self._transcript:
            return
        text = self._transcript.GetValue()
        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(text))
            finally:
                wx.TheClipboard.Close()
            self._announce("Transcript copied to clipboard.")
        else:
            self._announce("Could not open clipboard.")

    def _save_transcript(self) -> None:
        wx = self._wx
        if not self._transcript:
            return
        text = self._transcript.GetValue()
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        default_name = f"console-transcript-{ts}.txt"
        with wx.FileDialog(
            self._frame,
            "Save Transcript",
            defaultFile=default_name,
            wildcard="Text files (*.txt)|*.txt|All files (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()
                try:
                    Path(path).write_text(text, encoding="utf-8")
                except OSError as exc:
                    show_message_box(
                        f"Could not save transcript:\n{exc}",
                        "Error",
                        self._wx.OK | self._wx.ICON_ERROR,
                        self._frame,
                        announce=self._announce,
                    )

    def _show_help(self) -> None:
        help_text = (
            "QUILL Developer Console\n\n"
            "Keyboard shortcuts:\n"
            "  Enter          Run command\n"
            "  Shift+Enter    Insert newline\n"
            "  Ctrl+Enter     Force run multi-line\n"
            "  Up / Down      Navigate history (at first/last line)\n"
            "  Ctrl+L         Clear transcript\n"
            "  Ctrl+Shift+C   Copy transcript\n"
            "  Ctrl+S         Save transcript\n"
            "  Esc            Return focus to editor\n"
            "  F1             This help\n\n"
            "Python console:\n"
            "  Type q.help() for the scripting API reference.\n"
            "  q.run_command('command.id') runs any registered command.\n\n"
            "TypeScript console:\n"
            "  await quill.gotoLine(42)\n"
            "  const doc = await quill.activeDocument()\n"
            "  Requires Node.js on PATH."
        )
        show_message_box(
            help_text,
            "Developer Console Help",
            self._wx.OK | self._wx.ICON_INFORMATION,
            self._frame,
            announce=self._announce,
        )

    # ------------------------------------------------------------------
    # Language change

    def _on_lang_changed(self, event: Any) -> None:
        lang = self._lang_choice.GetString(self._lang_choice.GetSelection())
        self._set_status(f"Ready - {lang}")

    # ------------------------------------------------------------------
    # Focus helpers

    def _return_focus(self) -> None:
        if self._focus_editor is not None:
            try:
                self._focus_editor()
            except Exception:  # noqa: BLE001
                pass
        elif self._parent:
            try:
                self._parent.SetFocus()
            except Exception:  # noqa: BLE001
                pass

    # ------------------------------------------------------------------
    # Close

    def _on_close(self, event: Any) -> None:
        self._frame.Hide()
        self._return_focus()
