# JAWS empty-line repro: how to run it and report back

Companion runbook for `scripts/jaws_blank_line_repro.py`.

## What we are investigating

When a paragraph that contains inline formatting markers is followed by an empty
line, JAWS "say current line" on that empty line sometimes speaks the previous
line's text instead of "blank". Concretely:

1. Type `This **is** a *test*.` and press Enter.
2. On the now-empty second line, ask JAWS to read the current line.
3. JAWS says the line-1 text rather than "blank".
4. Add more text to line 1 (for example `Thank you for playing this game with me.`)
   and press Enter again, and JAWS correctly says "blank" on the new empty line.

We need to localize the cause to one of three layers before deciding who fixes it:

- QUILL's braille fix (`SES_EMULATESYSEDIT`), which deliberately changes how the
  editor exposes text to screen readers.
- The native RichEdit control / wxPython.
- JAWS itself.

## Why this harness is trustworthy

On Windows, QUILL's editor is not a plain text box. It is a native RichEdit built
as `wx.TextCtrl(TE_RICH2 | TE_NOHIDESEL)` with `SES_EMULATESYSEDIT` applied via the
`EM_SETEDITSTYLE` message (the braille "text starts in cell 1 / selection dots"
fix, on by default) inside a borderless frame. The harness rebuilds that exact
control from raw wxPython plus one ctypes message and imports no QUILL code, so
whatever it does is the control's behavior, not QUILL logic layered on top. Its
constants mirror `quill/ui/richedit_rtf_surface.py`.

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

### Baseline (defaults = QUILL's editor)

1. Leave every checkbox at its default.
2. Click **Load: short line + Enter**. The caret lands on the empty second line.
3. Do a JAWS "say current line" (Insert+Up on the desktop layout). Write down the
   exact words JAWS speaks.
4. Read the **Diagnostics** panel and copy its `current caret line text` line and
   its `VERDICT` line.

### A/B the braille fix (the decisive test)

5. Uncheck **SES_EMULATESYSEDIT (braille fix)**.
6. Click **Apply (rebuild control)**, then **Load: short line + Enter** again.
7. Repeat the JAWS "say current line" read and record it, plus the Diagnostics
   lines.

### Confirm the length correlation

8. Re-check **SES_EMULATESYSEDIT**, click **Apply**.
9. Click **Load: long line + Enter** and read the empty line with JAWS. Record it.

### Isolate the control type

10. Uncheck **TE_RICH2** (this makes it a plain edit control, not a RichEdit),
    click **Apply**, **Load: short line + Enter**, read with JAWS, and record it.

You can also try toggling **Word wrap** and **BORDER_NONE** if earlier steps are
inconclusive.

## How to read the result

The Diagnostics panel prints a `VERDICT` line for each state. Use this table to
turn the readings into a conclusion.

| What you observe | Where the bug is | What to do |
| --- | --- | --- |
| JAWS misreads with `SES_EMULATESYSEDIT` on, but says "blank" with it off | QUILL's braille fix / its interaction with JAWS | Fix or mitigate in QUILL; do not punt blindly |
| JAWS misreads either way, and Diagnostics shows the caret line as `''` (blank) | The control is correct; JAWS is misreading | File with the JAWS team, attach this harness |
| Diagnostics itself reports line 1 for the empty-line caret | Native RichEdit / wxPython, below QUILL and JAWS | File with wxPython / Microsoft |
| Plain edit (TE_RICH2 off) reads "blank" but the RichEdit misreads | RichEdit-specific behavior | Note this when filing |

The single most important comparison is step 3 versus step 7: whether unchecking
`SES_EMULATESYSEDIT` changes JAWS's behavior. That one answer decides whether this
is ours to fix.

## Results to send back

Copy this template, fill it in, and paste it into the issue or the chat.

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

Step 9  (SES_EMULATESYSEDIT ON, long line):
  JAWS said:

Step 10 (TE_RICH2 OFF, short line):
  JAWS said:

Any other combinations tried and what happened:
```

## Related code

- Editor construction and the braille flags: `quill/ui/main_frame.py` (search for
  `create_richedit_rtf`).
- The RichEdit wrapper and `SES_EMULATESYSEDIT` application:
  `quill/ui/richedit_rtf_surface.py`.
