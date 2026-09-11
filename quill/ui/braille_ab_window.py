"""Braille A/B: read the same text on two editors that differ by one flag.

The braille fix for #616/#813 is two cooperating pieces -- ``SES_EMULATESYSEDIT``
and the hidden editor border -- and only the border was ever proved to be
load-bearing. The flag might be doing nothing, and if it is doing nothing it
should go, because it is also what makes the Rich Edit misreport the caret's
line at the end of a document (corrected since 2026-09-09 by
:mod:`quill.ui.richedit_line_fix`, which would go with it).

Answering that needs a braille display and a person, and until now it also
needed a restart: ``SES_EMULATESYSEDIT`` is **set-once** -- ``EM_SETEDITSTYLE``
is ignored on a control that already holds text, in *both* directions -- so
flipping the preference cannot change a live editor, and comparing meant
restarting QUILL between every reading. Nobody A/Bs anything under those
conditions, which is why the question sat open for months.

So this window builds both editors at once. Editor A is exactly what QUILL
ships (flag on, borderless, line-fix installed); editor B differs by that one
flag and nothing else. Tab between them, read the same line on the display, and
the comparison is two keystrokes instead of two launches.

What to look for, on the display rather than in speech:

* **Where the text starts.** #616 was text beginning in cell 2 instead of cell 1.
* **Dots 7-8 under a selection.** #813. **Select the sample word** puts the same
  selection in both editors so the two readings are of the same thing.
* **The empty last line.** Both editors are seeded with a trailing blank line.
  **Report caret line** says which line the *control* thinks the caret is on --
  the machine half of the same question a screen reader asks.

If A and B read alike, the flag is not earning its place: turn off
**Preferences > Braille > system edit fix**, and the corrector can be deleted
with it. If A reads better, the flag stays and this window is the evidence.
"""

from __future__ import annotations

from typing import Any

from quill.ui.app_context_help import ensure_help_provider
from quill.ui.dialog_contract import bind_close_button

TITLE = "Braille A/B: system edit fix"

#: Seeded into both editors. A sentence, a word worth selecting, and a trailing
#: newline so the empty final line -- the one the flag used to misreport -- is
#: already there to read.
SAMPLE_TEXT = "This is a test.\nSelect the word braille in this line.\n"

#: The word "Select the sample word" selects, in :data:`SAMPLE_TEXT`.
SAMPLE_WORD = "braille"

_HELP_WINDOW = (
    "Two editors that differ by one setting: the braille system edit fix. "
    "Editor A has it on, which is what QUILL ships; editor B has it off. "
    "Read the same line on your braille display in each and compare where the "
    "text starts and whether a selection shows dots 7 and 8."
)


def _seed(editor: Any) -> None:
    """Put the sample in *editor* with the caret on the empty final line."""
    try:
        editor.ChangeValue(SAMPLE_TEXT)
        editor.SetInsertionPoint(editor.GetLastPosition())
    except Exception:  # noqa: BLE001 - a test surface must never raise at the user
        pass


def _caret_line(editor: Any) -> tuple[int, str]:
    """What the *control* says the caret's line is, and that line's text.

    ``PositionToXY`` is ``EM_EXLINEFROMCHAR`` underneath, which is the question
    a screen reader asks the window -- so this reads what JAWS would be told.
    """
    _ok, _column, row = editor.PositionToXY(editor.GetInsertionPoint())
    return row, editor.GetLineText(row)


def open_braille_ab(host: Any) -> Any:
    """Open (or raise) the A/B window. Returns the frame, or ``None`` on failure.

    Modeless on purpose: this is a bench, not a question. A modal dialog would
    hold the app hostage for a comparison that takes as long as it takes, and
    the tester needs to be free to reach for Preferences mid-session.
    """
    wx = host._wx
    ensure_help_provider(wx)

    existing = getattr(host, "_braille_ab_frame", None)
    if existing is not None:
        try:
            existing.Raise()
            return existing
        except Exception:  # noqa: BLE001 - a destroyed frame: build a new one
            host._braille_ab_frame = None

    from quill.ui.richedit_rtf_surface import create_richedit_rtf

    frame = wx.Frame(host.frame, title=TITLE, size=(720, 520))
    frame.SetHelpText(_HELP_WINDOW)
    panel = wx.Panel(frame)
    panel.SetHelpText(_HELP_WINDOW)
    root = wx.BoxSizer(wx.VERTICAL)

    intro = wx.StaticText(
        panel,
        label=(
            "Read the same line on your braille display in each editor. "
            "They differ by one setting and nothing else."
        ),
    )
    intro.SetHelpText(
        "What this window is for. Editor A is the shipped configuration; editor B "
        "has the braille system edit fix turned off."
    )
    root.Add(intro, 0, wx.ALL, 10)

    editors: dict[str, Any] = {}
    for key, mnemonic, description, emulate in (
        ("A", "&A", "system edit fix ON, which is what QUILL ships", True),
        ("B", "&B", "system edit fix OFF", False),
    ):
        label = wx.StaticText(panel, label=f"Editor {mnemonic}: {description}")
        label.SetHelpText(f"Names the editor below. Editor {key}: {description}.")
        root.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        editor = create_richedit_rtf(
            wx,
            panel,
            wx.TE_MULTILINE | wx.BORDER_NONE,
            emulate_system_edit=emulate,
        )
        editor.SetName(f"Editor {key}")
        editor.SetHelpText(
            f"A sample document with the braille system edit fix "
            f"{'on' if emulate else 'off'}. Type in it, select in it, and read it "
            "on your display; the last line is deliberately empty."
        )
        _seed(editor)
        root.Add(editor, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        editors[key] = editor

    def _on_select(_event: object) -> None:
        """Select the same word in both, so the two readings compare."""
        for editor in editors.values():
            text = editor.GetValue()
            start = text.find(SAMPLE_WORD)
            if start < 0:
                continue
            editor.SetSelection(start, start + len(SAMPLE_WORD))
        host._announce(
            f"Selected {SAMPLE_WORD} in both editors. Read the selection on your display "
            "and compare dots 7 and 8."
        )

    def _on_report(_event: object) -> None:
        """Both editors, never just the focused one.

        Pressing the button takes focus off whichever editor was being read, so
        "the focused one" would always be a guess -- and the answer worth having
        is the comparison anyway.
        """
        parts: list[str] = []
        for key, editor in editors.items():
            try:
                row, text = _caret_line(editor)
            except Exception:  # noqa: BLE001 - report the failure, never raise
                parts.append(f"Editor {key} did not answer")
                continue
            spoken = "blank" if not text.strip() else text.rstrip(" .")
            parts.append(f"Editor {key}, line {row + 1}, {spoken}")
        host._announce(". ".join(parts) + ".")

    def _on_restore(_event: object) -> None:
        for editor in editors.values():
            _seed(editor)
        host._announce("Both editors restored to the sample text.")

    buttons = wx.BoxSizer(wx.HORIZONTAL)
    select_btn = wx.Button(panel, label="&Select the Sample Word")
    select_btn.SetHelpText(
        f"Selects the word {SAMPLE_WORD} in both editors at once, so the two braille "
        "readings are of the same selection."
    )
    select_btn.Bind(wx.EVT_BUTTON, _on_select)
    report_btn = wx.Button(panel, label="&Report Caret Line")
    report_btn.SetHelpText(
        "Speaks which line each editor's control says its caret is on -- both, so the "
        "two can be compared. That is the question a screen reader asks the control, so "
        "a wrong answer here is what you would have heard."
    )
    report_btn.Bind(wx.EVT_BUTTON, _on_report)
    restore_btn = wx.Button(panel, label="Restore Sample &Text")
    restore_btn.SetHelpText("Puts the sample text back in both editors.")
    restore_btn.Bind(wx.EVT_BUTTON, _on_restore)
    close_btn = wx.Button(panel, wx.ID_CANCEL, "Close")
    close_btn.SetHelpText("Closes this window. Escape does the same.")
    bind_close_button(frame, close_btn, modeless=True)
    for button in (select_btn, report_btn, restore_btn):
        buttons.Add(button, 0, wx.RIGHT, 6)
    buttons.AddStretchSpacer()
    buttons.Add(close_btn)
    root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

    panel.SetSizer(root)

    # A wx.Frame has no SetEscapeId, so Escape is wired by hand -- the same
    # way out a dialog gives for free (dialog_contract.bind_close_button).
    frame.Bind(wx.EVT_MENU, lambda _e: frame.Close(), id=wx.ID_CANCEL)
    frame.SetAcceleratorTable(
        wx.AcceleratorTable([wx.AcceleratorEntry(wx.ACCEL_NORMAL, wx.WXK_ESCAPE, wx.ID_CANCEL)])
    )

    def _on_close(event: object) -> None:
        host._braille_ab_frame = None
        event.Skip()

    frame.Bind(wx.EVT_CLOSE, _on_close)
    host._braille_ab_frame = frame
    frame.Show()
    editors["A"].SetFocus()
    return frame
