# Editor Surface History: how QUILL ended up with one editor

Canonical engineering record, written 2026-07-11 as part of the QuillRichEdit
promotion (0.9.0-beta3, the "One Editor, Every Format" plan). It preserves the
verdicts and post-mortems from the editor-surface experiments so the deleted
code cannot be casually reintroduced without this history. The full analysis
lived in `docs/planning/editor-surface-experiments.md` (retired with the
experiment; recoverable from git history).

## The outcome (what ships)

**QuillRichEdit is QUILL's one editor surface on Windows**: the same native
Rich Edit control (`RICHEDIT50W`, a `wx.TextCtrl` with `TE_RICH2 |
TE_NOHIDESEL`) QUILL always shipped, plus a wrapper
(`quill/ui/richedit_rtf_surface.py`) that adds native RTF load/save and
formatting through the Text Object Model (TOM), and the braille fix applied by
default:

- `SES_EMULATESYSEDIT` via `EM_SETEDITSTYLE` — text renders from braille
  cell 1 (#616) and selections show dots 7-8 (#813).
- A borderless frame (`wx.BORDER_NONE`) — live testing showed the visible
  border itself pushes braille output out of cell 1, so the hidden border is
  part of the fix, not cosmetics.

Both halves are plain checkboxes on the Braille tab
(`braille_editor_system_edit_fix`, `braille_editor_hide_border`), default ON,
forced on for upgraders (the retired surface overrides are dropped from the
settings delta on load). Confirmed working by live JAWS + braille hardware
testing, 2026-07.

macOS keeps the native `wx.TextCtrl` (an `NSTextView` underneath); its rich
path is described in the PRD (converted rich, then the native NSTextView
wrapper).

## The dead ends, and why they stay dead

### Scintilla / wx.stc — the "Notepad++ experiment" (NVDA-only; JAWS impossible)

The most instructive failure. Scintilla was attractive (fast on huge
documents, true multi-level undo/redo), and NVDA read and tracked it well.
JAWS could not follow the caret. Three bridging rounds all failed on live
hardware (2026-07-03):

1. **Caret mirror** — a hidden classic caret positioned to match Scintilla's.
2. **Classic message answers** — responding to `WM_GETTEXT` / `WM_GETTEXTLENGTH`
   / `EM_GETSEL` / `EM_EXGETSEL` from the Scintilla HWND.
3. **Geometry set** — round 2 plus `EM_POSFROMCHAR` / `EM_CHARFROMPOS` so JAWS
   could map offsets to screen positions.

Verdict: JAWS's Notepad++ support is script-side and window-class-keyed; a
foreign app cannot impersonate it by answering messages. The bridge was
removed, the surface labeled NVDA-only, and the negative result pinned in
tests while the surface existed. **Do not retry a JAWS/Scintilla bridge.**

### Raw Win32 EDIT host via pywin32 (silent offset corruption)

Hosting the classic EDIT control directly worked for typing and selection but
kept CRLF line endings in the control while QUILL's model is LF-only. Every
offset-anchored feature (search, spell, bookmarks, AI ranges) skewed silently
past the first line break — the worst failure mode: no crash, wrong behavior.
Translating at every boundary duplicated the whole editor contract for no
accessibility win over `SES_EMULATESYSEDIT` on the Rich Edit.

### wx.RichTextCtrl (invisible to screen readers)

wxWidgets' own rich-text widget renders its document itself; there is no
native text control underneath, so JAWS/NVDA saw nothing they could read as a
document. API-compatible enough for a demo, unusable for QUILL's audience.

### The read-only "rich text lens" (superseded)

`quill/ui/rich_text_surface.py` behind the locked-off `core.rich_text_lens`
flag offered a read-only formatted view next to the markup editor. Rich mode
on the native control delivers editable formatting instead; the lens and the
`view.switch_editing_lens` command retired with it.

### EM_STREAMIN / EM_STREAMOUT ctypes callback (hard crash; use the TOM)

The first native RTF I/O attempt drove `EM_STREAMIN`/`EM_STREAMOUT` with a
ctypes `EDITSTREAM` callback. msftedit access-violates the moment it invokes a
Python callback — a hard, reproducible crash on a real `RICHEDIT50W`
(post-mortem 2026-07-08). The shipped path avoids Python callbacks entirely:
`EM_GETOLEINTERFACE` -> `IRichEditOle` -> QueryInterface to `ITextDocument`
(comtypes + the tom type library) -> `Open`/`Save` with `tomRTF` against a
file. Verified crash-free on-device. **Never wire an EDITSTREAM callback from
Python.**

### The margin lever that didn't help alone

`editor_zero_richedit_margins` (`EM_SETMARGINS`) was tried for the cell-2
offset and removed in beta2 (commit `094b630`) after testing showed it did not
fix alignment by itself. If a residual left-offset ever reappears with the
promoted default, margin zeroing returns *inside*
`braille_editor_system_edit_fix`, not as a separate setting.

## Surface ranking at the end of the experiment

For the record, the final preference order before consolidation: richedit_rtf
(promoted) > rich2 (the previous default, same control unwrapped) > plain
(EDIT semantics without RTF; superseded by `SES_EMULATESYSEDIT`) > rich >
win32 (offset skew) > rtf (SR-invisible) > stc (NVDA-only). The retired
settings: `editor_control_kind`, `experimental_editor_surface`,
`experimental_editor_surfaces_enabled`,
`experimental_richedit_emulate_sysedit`, `editor_hide_border`.

## Safety-valve decision (deliberate)

No hidden fallback combo ships. If a future regression demands a comparison
surface, it returns as a new experimental setting then; QUILL does not carry
seven dead surfaces to hedge. The only in-code fallback is inside
`create_richedit_rtf` itself: any failure yields a stock multiline
`wx.TextCtrl`, so the editor can never fail to build.
