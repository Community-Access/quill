# JAWS empty-line repro: the verdict, and how to run the harness

Companion runbook for `scripts/jaws_blank_line_repro.py`.

## The answer (2026-09-09)

**Settled, and fixed, without needing JAWS to settle it.** Two different causes
produced one symptom in the two products, and neither is a trade any more.

| Product | Cause | State |
| --- | --- | --- |
| QUILL Lite | `EM_SETTEXTMODE` with `TM_PLAINTEXT` | Fixed: the control stays in rich-text mode, the plain/rich distinction lives in the document. `quill/ui/richedit_editing.py`, guarded by `tests/unit/ui/test_richedit_empty_last_line.py`. |
| QUILL | `SES_EMULATESYSEDIT`, the #616/#813 braille fix | Fixed: the wrong answers are corrected in a window subclass, and the braille fix stays on. `quill/ui/richedit_line_fix.py`, guarded by `tests/unit/ui/test_richedit_final_line_fix.py`. |

### What was measured

RICHEDIT50W (Riched20 10.0.26100), text `"This is a test.\r"`, caret at 16:

| question | flag off | flag on |
| --- | --- | --- |
| `EM_GETLINECOUNT` | 2 | 2 |
| `EM_LINEINDEX` (line 1) | 16 | 16 |
| `EM_EXLINEFROMCHAR` (16) | 1 | **0** |
| `EM_LINEFROMCHAR` (-1) | 1 | **0** |
| `EM_LINEINDEX` (-1) | 16 | **0** |
| `EM_LINELENGTH` (16) | 0 | **15** |

So the flag is the cause, and the damage is narrower than it looked. Everything
the control knows about itself stays right: the line count, the index of an
explicit line, `EM_GETLINE` for the empty line, and every interior empty line
(`"alpha\n\nbeta"` reports line 1 for the caret on the blank). Only the
character-to-line mapping past the start of the final line is wrong, and it
contradicts the control's own answers -- line 1 starts at 16, and character 16 is
said to be on line 0.

That contradiction is what makes the fix possible: every character index at or
after the last line's start is on the last line, in any document, so the right
answer can be supplied without guessing and without ever disagreeing with a
control that is answering correctly. `quill/ui/richedit_line_fix.py` supplies it
from a `comctl32` window subclass, which is where a screen reader's
cross-process `SendMessage` is dispatched -- verified from a second process.

### Two things that rule out the simpler fixes

- **`SES_EMULATESYSEDIT` is set-once.** `EM_SETEDITSTYLE` is ignored once the
  control holds text: it cannot be turned on later and, less obviously, it
  cannot be turned off again either. Nothing can lift the flag around a screen
  reader's question, and the preference genuinely needs the editor rebuilt --
  which Preferences already says.
- **No caret position reports correctly**, so nothing is fixable by moving the
  caret; and wx-level arithmetic cannot help, because a screen reader asks the
  window, not wx.

### What is still worth an A/B, and the bench for it

Nothing is blocked on it, but it would be good to know whether
`SES_EMULATESYSEDIT` is even required. The braille fix was always two pieces --
the flag and the hidden border -- and the border was the half that completed it.
If the borderless editor alone gives braille from cell 1 with dots 7-8 on the
selection, the flag and its corrector can both be deleted.

**Use the in-app bench, not the preference.** Run **Braille A/B: System Edit
Fix...** from the command palette (Ctrl+Shift+P). It builds both editors at
once -- A is exactly what QUILL ships, B differs by that one flag -- so the
comparison is a Tab apart. Toggling the preference cannot do this: the flag is
set-once, so a running editor keeps whatever it was built with and every
reading would need its own restart. That is why this comparison never got made.

In the bench: read the same line on the display in each; press **Select the
Sample Word** and read the selection in each (that is #813, dots 7-8); look at
where the text begins (#616, cell 1 vs cell 2). **Report Caret Line** speaks
what each control says its caret's line is, for the blank-line half.

## What the harness is for

`scripts/jaws_blank_line_repro.py` rebuilds QUILL's exact editor from raw
wxPython plus one ctypes message, importing no QUILL code, so whatever it does is
the control's behaviour rather than QUILL logic layered on top. Its constants
mirror `quill/ui/richedit_rtf_surface.py`. It stays in the tree for the A/B above
and for the next time somebody needs to A/B a Rich Edit flag against a screen
reader. **It does not carry the `richedit_line_fix` correction**, which is the
point: it shows the control raw.

## Prerequisites

- Windows with JAWS installed.
- The same Python environment QUILL uses (wxPython available):
  `pip install -e ".[ui,dev]"`.

## Run it

Run it from a normal terminal (it opens a window and enters an event loop, so do
not launch it with the in-session `!` prefix):

```
python scripts/jaws_blank_line_repro.py
```

The checkboxes default to the exact combination QUILL ships:
`TE_RICH2`, `TE_NOHIDESEL`, `SES_EMULATESYSEDIT`, `BORDER_NONE`, and word wrap, all on.

## Step-by-step procedure

Run this whole procedure with JAWS on.

### Baseline (defaults = QUILL's editor, minus the correction)

1. Leave every checkbox at its default.
2. Click **Load: short line + Enter**. The caret lands on the empty second line.
3. Do a JAWS "say current line" (Insert+Up on the desktop layout). Write down the
   exact words JAWS speaks.
4. Read the **Diagnostics** panel and copy its `current caret line text` line and
   its `VERDICT` line.

### A/B the braille fix

5. Uncheck **SES_EMULATESYSEDIT (braille fix)**.
6. Click **Apply (rebuild control)**, then **Load: short line + Enter** again.
7. Repeat the JAWS "say current line" read and record it, plus the Diagnostics
   lines. Then read a **selection** on the braille display in both states -- that
   is the comparison that has not been made yet.

### Isolate the control type

8. Uncheck **TE_RICH2** (this makes it a plain edit control, not a RichEdit),
   click **Apply**, **Load: short line + Enter**, read with JAWS, and record it.

You can also try toggling **Word wrap** and **BORDER_NONE** if earlier steps are
inconclusive.

## How to read the result

The Diagnostics panel prints a `VERDICT` line for each state.

| What you observe | Where the bug is | What to do |
| --- | --- | --- |
| JAWS misreads with `SES_EMULATESYSEDIT` on, but says "blank" with it off | The braille fix. **This is the known result**, and `richedit_line_fix.py` is the cure | Nothing; confirm QUILL itself no longer misreads |
| JAWS misreads either way, and Diagnostics shows the caret line as `''` (blank) | The control is correct; JAWS is misreading | File with the JAWS team, attach this harness |
| Diagnostics itself reports line 1 for the empty-line caret | Native RichEdit / wxPython, below QUILL and JAWS | File with wxPython / Microsoft |
| Plain edit (TE_RICH2 off) reads "blank" but the RichEdit misreads | RichEdit-specific behaviour | Note this when filing |

## Results to send back

```
Machine / JAWS version:
wxPython version:

Step 3  (defaults, short line):
  JAWS said:
  Diagnostics current caret line text:
  Diagnostics VERDICT:

Step 7  (SES_EMULATESYSEDIT OFF, short line):
  JAWS said:
  Diagnostics current caret line text:
  Diagnostics VERDICT:
  Braille, reading a line:
  Braille, reading a selection:

Step 8 (TE_RICH2 OFF, short line):
  JAWS said:

Any other combinations tried and what happened:
```

## Related code

- Editor construction and the braille flags: `quill/ui/main_frame.py` (search for
  `create_richedit_rtf`).
- The RichEdit wrapper and `SES_EMULATESYSEDIT` application:
  `quill/ui/richedit_rtf_surface.py`.
- The correction and the full measurement: `quill/ui/richedit_line_fix.py`.
- QUILL Lite's separate cause: `quill/ui/richedit_editing.py`, `set_text_mode`.
