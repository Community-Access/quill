# Editor Control Surface Analysis

Date: 2026-07-03. Written after the two startup crashes found while A/B testing
surfaces (the relaunch stdlib-shadowing crash and the RichTextCtrl selection
crash). This maps each of the six `experimental_editor_surface` choices against
QUILL's feature set, the risk each carries, and the changes each would need to
be safe. File is for review; not linked from docs.

## The contract QUILL assumes of the editor

Every feature that touches text goes through `self.editor` and assumes the
wx.TextCtrl API and semantics:

- Value: `GetValue`, `ChangeValue`, `SetValue`, `GetRange`, `IsEmpty` -- LF-only
  text, offsets that match Python string indices into `GetValue()`.
- Caret and selection: `GetInsertionPoint`, `SetInsertionPoint`, `GetSelection`
  returning an `(start, end)` tuple with `(caret, caret)` when empty,
  `SetSelection`, `GetStringSelection`, `ShowPosition`, `GetLastPosition`.
- Editing: `WriteText` at caret, `AppendText`, `Replace`, `Remove`, `Clear`.
- State: `IsModified`, `SetModified`, `MarkDirty`, `DiscardEdits`,
  `SetEditable`, `IsEditable`, `Undo`, `Redo`, `CanUndo`, `CanRedo`.
- Geometry: `PositionToXY`, `XYToPosition`, `GetNumberOfLines` (go-to-line,
  line-oriented commands).
- Events (bound in `_bind_editor_events`): `EVT_TEXT` (dirty tracking, word
  count, Reveal Codes idle sync), `EVT_CHAR_HOOK` (describe-key, Ctrl+K insert
  link, SET-4 typography autoformat, extend-selection Escape), `EVT_KEY_DOWN` /
  `EVT_KEY_UP` (QUILL key chords, typing echo, dictation hotkeys),
  `EVT_LEFT_UP` + `EVT_SET_FOCUS` (caret-activity announcements, status bar,
  braille refresh), `EVT_CONTEXT_MENU`.
- Accessibility: the control must report its value, caret, and selection
  through IAccessible/UIA so JAWS and NVDA read and track it, and so braille
  displays follow the caret. This is the reason rich2 is the default (#616).

Features that consume this contract, grouped by what breaks when part of the
contract is missing:

- Offset-anchored: bookmarks and last-cursor memory, inline notes, hidden
  formatting codes and Illuminations, wikilink resolution (Vault), search and
  replace, spell/grammar fix-ups, AI change previews (one `Replace`, one undo
  step), read-aloud position tracking.
- Type-time: typography autoformat (smart quotes/dashes), Quillin smart
  triggers and abbreviations, describe-key, typing echo, QUILL key chords.
- Continuous: status bar cells (selection, stats), Reveal Codes sync, braille
  status line, caret-move formatting announcements.

The two crashes this week were both contract drift: a surface that returned a
different `GetSelection` shape took the app down before first paint. Anything
below rated Medium or higher should get a parametrized contract test (same
assertions, run against each surface with real wx) before we lean on it.

## 1. default -- follow the Accessibility setting

- Classes: none of its own; delegates to whatever `editor_control_kind`
  resolves to (rich2, rich, or plain below).
- What it is: not a surface. Applies whatever `editor_control_kind` says
  (rich2, rich, or plain -- the braille A/B knob from #616/#813).
- Feature impact: none of its own; inherits the target surface's behavior.
- Risk: none beyond the chosen target. This is the correct resting state for
  everyone not actively testing.
- Changes required: none. Keep it first in the choice list and keep the
  explainer text current.

## 2. rich2 -- RichEdit 3.0 (RICHEDIT50W), the shipping default

- Classes: Python `wx.TextCtrl`; Win32 window class `RICHEDIT50W`
  (msftedit.dll -- the modern RichEdit engine).
- What it is: `wx.TextCtrl` with `TE_RICH2 | TE_NOHIDESEL`.
- Undo/redo: native multi-level undo AND redo (`CanRedo`/`Redo` work).
- Feature impact: the baseline. Every feature above was built and tested on
  this surface. Multi-level native undo. No practical size limit. Correct
  IAccessible value reporting (#616).
- Known issues: braille cell-two offset on some displays (the long-standing
  Word quirk); #813 (JAWS braille not showing dots 7-8 on selection) is
  suspected to live here -- that is the open investigation driving this A/B.
- Risk: Low. It is the control everything is calibrated against.
- Changes required: none. If #813 confirms RICHEDIT50W as the cause, the fix
  is likely a UIA/IAccessible selection-reporting workaround here, not a
  default-surface change.

## 3. rich -- RichEdit 2.0 (RICHEDIT20W)

- Classes: Python `wx.TextCtrl`; Win32 window class `RICHEDIT20W`
  (riched20.dll -- the older RichEdit engine).
- What it is: `wx.TextCtrl` with `TE_RICH | TE_NOHIDESEL`; same wx wrapper,
  older native engine.
- Undo/redo: native multi-level undo and redo, same as rich2.
- Feature impact: near-identical to rich2. All contract methods behave the
  same through wx. Differences are engine-internal: older IME handling, some
  formatting/measurement differences we do not use (buffer is plain text).
- Risk: Low-Medium. The risk is not breakage but subtle screen-reader and
  braille differences -- which is exactly why it exists (a comparison point for
  #813). Undo depth and limits match rich2 for our usage.
- Changes required: none to function. Worth capturing JAWS/NVDA/braille
  behavior notes per screen reader once, so the A/B results are recorded
  rather than re-discovered.

## 4. plain -- Notepad-style EDIT via wx.TextCtrl

- Classes: Python `wx.TextCtrl`; Win32 window class `EDIT` (user32 -- the
  classic multiline edit control, same class Notepad used for decades).
- What it is: `wx.TextCtrl` with `TE_MULTILINE` only; wx hosts the classic
  Win32 EDIT class.
- Feature impact: all contract methods work because wx still mediates.
  Two real semantic differences:
  - Undo is single-level and there is NO redo at all. The native EDIT
    control has one undo slot that toggles (undo of the undo is the "redo"),
    and `CanRedo` reports false on this class. `MainFrame.undo()` routes to
    `editor.Undo()`, so an AI preview apply followed by any keystroke leaves
    only the keystroke undoable, and nothing is redoable. This is the largest
    hidden feature regression on this surface and users will not expect it.
    Fixing it properly means an app-level undo/redo engine (see the undo/redo
    note after the rankings) -- real engineering, not a wrapper.
  - No visual rich rendering (QUILL's hidden-codes design makes this mostly
    moot; formatting still round-trips through Illuminations/export).
  - wx raises the EDIT text limit for us, so large documents are fine, but
    very large buffers repaint slower than RichEdit.
- Accessibility: excellent -- native EDIT is the best-understood control for
  every screen reader and avoids the braille cell-two offset entirely. That is
  why it is the #813 A/B candidate.
- Risk: Medium, dominated by the single-level undo. Everything else is solid.
- Changes required if it were ever more than a test knob:
  - A document-level undo stack in QUILL (or a guard that warns when an AI /
    multi-step change is about to become un-undoable).
  - A note in the explainer text about undo depth (it currently says "all
    core editing works" without the undo caveat).

## 5. rtf -- wx.RichTextCtrl (experimental)

- Classes: Python `quill.ui.rtf_edit_surface.RtfEditorSurface`, a subclass of
  `wx.richtext.RichTextCtrl`. There is no native text-control window class
  underneath -- the Win32 class is a generic wx window, which is exactly why
  screen readers do not recognize it as a text field.
- What it is: wx's own rich text widget. Crucially, it is NOT a native Windows
  control -- wx draws the text itself.
- Undo/redo: multi-level via wx's own command processor, but grouping
  semantics differ from RichEdit (AI one-step-undo unverified).
- Feature impact today (after this week's fix wrapped `GetSelection`):
  - Value/caret basics work (`GetValue`/`ChangeValue`/insertion point), so
    typing, dirty tracking, word count, and Reveal Codes sync function.
  - Still divergent from the contract: `PositionToXY`/`XYToPosition` and
    `HitTest` have different shapes/semantics (go-to-line and line-oriented
    commands are suspect); `Replace` goes through its own command processor
    (undo grouping of AI previews unverified); styling APIs differ entirely.
  - Its selection-empty convention was `(-2, -2)` where TextCtrl says
    `(caret, caret)` -- the class of mismatch that crashed the status bar. We
    fixed the one we hit; the remaining API surface has not been audited.
- Accessibility: this is the disqualifying risk. Because the control is
  wx-drawn, it does not present as a native EDIT/RichEdit to JAWS/NVDA.
  Value, caret, and selection reporting depend on wx's generic accessibility
  layer, which is historically weak on Windows. Braille tracking is unlikely
  to work at all. For a screen-reader-first product, this surface currently
  contradicts the product's core promise.
- Risk: High. Both on the API-contract axis (proven by this week's crash) and
  on the accessibility axis (structural, not fixable by a wrapper).
- Changes required to make it viable (large):
  - Full contract-shim layer (selection done; PositionToXY/XYToPosition,
    HitTest, undo grouping, modified-state semantics).
  - A UIA provider or wxAccessible implementation that reports text pattern,
    caret, and selection -- essentially the same class of work as the Table
    Studio native provider, but for a text control. Until then it should stay
    double-gated exactly as it is, with the explainer stating plainly that
    screen readers may not track it.
  - Parametrized surface contract tests.

## 6. win32 -- raw Win32 EDIT hosted via pywin32 (spike)

- Classes: Python `quill.ui.win32_edit_surface._Win32EditHost` (a `wx.Window`
  host); the child is a raw Win32 `EDIT` window class created directly with
  CreateWindowEx, driven by SendMessage.
- What it is: a `wx.Window` hosting a genuine EDIT child created with
  CreateWindowEx; messages bridged by hand (`win32_edit_surface.py`).
- Undo/redo: single-level native undo (WM_UNDO), no redo -- same EDIT-class
  limitation as plain, plus the bridge exposes no redo API at all.
- Feature impact (documented in the spike, confirmed by reading the bridge):
  - Works: typing, native selection, GetValue/SetValue with CRLF<->LF
    translation, dirty tracking via the EN_CHANGE wndproc bridge, status bar
    (its `GetSelection` returns a proper tuple), clipboard, native single
    undo.
  - Bypassed entirely: `_bind_editor_events` takes the `bind_editor_events`
    fast path, so NO wx key events reach QUILL. Describe-key, typography
    autoformat, Quillin smart triggers, typing echo, QUILL key chords, the
    extend-selection Escape, and the context-menu handler are all inert while
    focus is in the native child. Frame accelerators may also be swallowed --
    untested.
  - Offset math: caret/selection offsets are in the control's CRLF space
    while QUILL's buffer is LF. Every offset-anchored feature (bookmarks,
    inline notes, hidden codes, wikilinks, spell fix-ups, AI previews) is off
    by one per preceding newline. This corrupts positions silently -- worse
    than crashing.
  - `EM_GETSEL` packed return clamps around 64K, so caret reporting in large
    documents is approximate; the spike never raises the EDIT text limit, so
    very large documents may truncate on load.
  - `SetWindowLong(GWL_WNDPROC)` is fragile on 64-bit (needs the Ptr variant);
    the bridge already swallows failure, which silently downgrades dirty
    tracking.
- Accessibility: the child EDIT itself is perfectly readable by screen
  readers (same class as Notepad), but focus handoff between the wx host and
  the native child is hand-rolled -- tab order, focus announcements, and the
  editor's accessible name need real screen-reader validation.
- Risk: High for any real use; acceptable only as the spike it is. The
  offset skew is the dangerous part because it corrupts saved anchors without
  any error.
- Changes required to graduate it (effectively a rewrite):
  - LF<->CRLF offset translation on every position API (both directions).
  - `EM_EXGETSEL`-style selection retrieval or buffer-based math to remove
    the 64K clamp; `EM_SETLIMITTEXT` on creation.
  - A key bridge (WM_KEYDOWN/WM_CHAR forwarding) so type-time features and
    chords work, or explicit in-app messaging that they do not.
  - `SetWindowLongPtr` via ctypes for the wndproc; focus/name accessibility
    audit.
  - Given that surface 4 (plain) IS the same EDIT control with all of this
    already solved by wx, the honest conclusion is that this spike has told
    us what it cost and "plain" is the better vehicle for everything it
    offers. Recommend keeping win32 only as a reference implementation.

## 7. stc -- Scintilla, the "Notepad++ experiment" (added 2026-07-03)

- Classes: Python `quill.ui.stc_edit_surface.StcEditorSurface`, a subclass of
  `wx.stc.StyledTextCtrl`; Win32 window class `Scintilla` (the Notepad++
  engine). Wired into the Experimental combo as "Notepad++ experiment
  (Scintilla, wx.stc.StyledTextCtrl)".
- What it is: a real windowed native-ish control (not wx-drawn like rtf),
  built for editing. The only alternative surface that natively answers the
  multi-level undo/redo concern.
- Undo/redo: full multi-level undo AND redo, native to the engine.
- Probe results (2026-07-03, wxPython on this machine): StyledTextCtrl
  implements the whole TextCtrl-compatible API QUILL needs -- tuple
  `GetSelection` with `(caret, caret)` when empty, `GetRange`, `Replace`,
  `PositionToXY`, modified-state via save point. Four contract gaps were
  found and are shimmed in `stc_edit_surface.py`:
  - `wx.EVT_TEXT` never fires natively (only `EVT_STC_CHANGE`), which would
    kill dirty tracking, word count, and Reveal Codes sync. The wrapper
    forwards every change as a `wxEVT_TEXT` event.
  - `ChangeValue` fires change notifications and leaves the buffer reported
    modified -- a freshly opened document would look dirty. The wrapper
    suppresses forwarding and sets the Scintilla save point on load.
  - `SetInsertionPoint` moves the caret but leaves the selection anchor
    behind, so the next `WriteText` would replace the dragged selection
    (probe-confirmed). The wrapper routes through `GotoPos`.
  - Line endings pass through unconverted (CRLF default). The wrapper pins
    LF, converts on load, and converts pasted text.
- Accessibility: the open question, and the point of the testing round.
  NVDA supports Scintilla well (it drives Notepad++ daily). JAWS support is
  partial and braille routing is less proven than EDIT/RichEdit. Needs the
  same JAWS/NVDA/braille pass as the other candidates before any promotion.
- Caret-tracking experiment (2026-07-03, tried and REVERTED): live JAWS
  testing showed Enter advanced the buffer but JAWS stayed on the old line.
  The first fix mirrored an invisible Windows system caret (the ScintillaWin
  technique) -- and made things worse: with a caret present, JAWS switched
  from its screen-content fallback into live-edit-control mode, queried the
  window for its text, got nothing back, and went silent. Reading the real
  ScintillaWin.cxx (the Scintilla Notepad++ ships) explains why: the caret
  mirror is only one third of its accessibility story. It also (a) answers
  WM_GETTEXT, WM_GETTEXTLENGTH, EM_GETSEL, EM_EXGETSEL, and EM_LINEFROMCHAR
  at its window proc, so screen readers can pull text and selection through
  the classic channels, and (b) registers the recognizable "Scintilla"
  window class that JAWS/NVDA key dedicated support off. wx's port provides
  none of the three: its own window class, no system caret, and a window
  proc that answers no text queries. Caret alone = silence. To graduate,
  this surface needs a ctypes window-proc bridge answering those messages
  PLUS the caret mirror, or a UIA TextPattern provider. Licensing is not
  the obstacle (Scintilla is permissively licensed; Notepad++ is GPL-3.0,
  so we learn from it, we do not copy from it) -- the effort and JAWS's
  window-class heuristics are.
- Braille findings (2026-07-03, Jeff, JAWS + braille display, on the
  reverted no-caret-mirror build): two clear wins --
  - Braille starts in CELL 1. The long-standing RichEdit cell-two offset
    (#616, "the Word quirk") does not occur on this surface.
  - Selection HIGHLIGHTING WORKS on the braille display. This is exactly
    what #813 reports broken on rich2 (no dots 7-8 on selection), so a
    non-RichEdit surface showing correct selection dots is strong evidence
    that #813 lives in RICHEDIT50W's selection reporting, not in JAWS or
    the display.
  Net: braille output on stc is currently the best of any surface; speech
  caret tracking remains the weak leg (see the experiment note above).
- Risk: Medium. The API contract is in good shape (probed, shimmed, gated,
  with the wx.TextCtrl fallback), so the risk concentrates entirely in
  speech caret tracking; braille results are positive.
- Changes still open if it graduates: verify styling hooks if we ever want
  visual spell-check squiggles (Scintilla indicators are good at this), and
  confirm IME/dead-key behavior.

## 8. richedit_rtf -- QuillRichEdit, the native Rich Edit wrapper (added 2026-07-08)

- Classes: Python `wx.TextCtrl`; Win32 window class `RICHEDIT50W` -- the *same*
  native Rich Edit control as `rich2`/the shipping default. What differs is that
  the live control is tagged with `surface_kind = "richedit_rtf"` and carries a
  `QuillRichEdit` wrapper (`quill/ui/richedit_rtf_surface.py`) that reaches the
  control's `HWND` for things wx's high-level API cannot do.
- What it is: `wx.TextCtrl` with `TE_RICH2 | TE_NOHIDESEL`, built by
  `create_richedit_rtf(...)` which falls back to a plain `wx.TextCtrl` on any
  failure (the proven win32/stc/rtf idiom). Because the inner control is the
  proven native control, the full editor contract (value/caret/selection/undo/
  events) is inherited unchanged -- no behavioral risk to existing surfaces.
- Why it exists: the ladder toward a lightweight, accessible RTF document mode
  (WordPad/HJPad class), and -- because it gives us a *controlled* handle on the
  native control we already ship -- the eventual home for the two open braille
  bugs: **#616 (JAWS cell-2 offset)** and **#813 (JAWS braille not showing dots
  7-8 on selection)**, driven directly on the native HWND rather than the
  generic-window bridge that failed for `stc`.
- **Phase 0 (done):** the surface, `surface_kind`, capability reporting, a
  read-only class-name diagnostic (confirms a genuine `RICHEDIT50W`), the two
  Experimental gates, and the settings/combo/explainer wiring + contract tests.
- **Phase 1 (done, via the TOM path):** native **RTF load/save works** --
  `QuillRichEdit.load_rtf`/`save_rtf`/`get_rtf`/`set_rtf` reach the control's
  **Text Object Model**: `EM_GETOLEINTERFACE` -> `IRichEditOle` ->
  `QueryInterface(ITextDocument)` (via `comtypes` + the tom type library) ->
  `ITextDocument::Open`/`::Save` with the `tomRTF` format flag. **Verified
  end-to-end on a real `RICHEDIT50W`** (load an RTF file, formatting applies;
  save back out is valid RTF with the bold run preserved; live wx edits flow
  out) -- **no crash.** The first attempt used an `EM_STREAMIN`/`EM_STREAMOUT`
  ctypes `EDITSTREAM` callback, which hard-crashes msftedit (post-mortem below);
  TOM avoids a Python callback entirely, which is why it works.
  `get_plain_text()` returns the control's plain value so search/spell/AI/read
  aloud keep working.
- **Phase 2 (done, via TOM):** formatting on the selection --
  `apply_bold`/`apply_italic`/`apply_underline` (toggle via `ITextFont` +
  `tomToggle`), `set_font_name`/`set_font_size` (`ITextFont.Name`/`.Size`), and
  `set_alignment` (`ITextPara.Alignment`). Verified on-device: italic, font
  (Consolas), size (18pt -> `fs36`), and center (`\qc`) all appear in the saved
  RTF, no crash. The surface-level methods are wired; **menu/keyboard command
  routing is the remaining integration** (native RichEdit already handles
  Ctrl+B/I/U itself).
- **Phase 3 (instrument + lever landed; needs braille testing):** the braille
  work for #616 (cell-2) and #813 (dots 7-8 on selection).
  - *Instrument (measures, safe):* the accessibility diagnostic now reports the
    control's edit style (`EM_GETEDITSTYLE`) and a **selection localizer** --
    the selection as the control's TOM (`ITextSelection.Start/End`) sees it vs
    wx's `GetSelection`, offsets/length only, no text. On-device it reports
    `wx=(6,15), TOM=(6,15), agree=True`, which **localizes #813**: the control
    *knows* the selection, so braille not showing dots 7-8 is an AT-rendering
    gap, not a control-tracking one.
  - *Lever (the candidate fix, A/B-able):* `QuillRichEdit.set_emulate_system_edit`
    applies `SES_EMULATESYSEDIT` via `EM_SETEDITSTYLE`, asking the Rich Edit to
    behave like the classic `EDIT` control -- which the four-way table shows is
    the one that renders from cell 1 *and* shows selection dots 7-8 -- while
    staying a Rich Edit so its `IAccessible` value (the reason for #616's default)
    is unchanged. Verified to apply cleanly on-device (edit style 0x0 -> 0x3, no
    crash). Exposed as the gated experimental setting
    `experimental_richedit_emulate_sysedit`, applied at surface creation.
  - **Test protocol (needs JAWS + a braille display -- cannot be done in CI):**
    select the QuillRichEdit surface, attach a braille display, and A/B with the
    emulate-system-edit setting off then on (restart between), checking on each:
    (a) does text start in cell 1 or cell 2? (#616) (b) do dots 7-8 appear under
    selected text? (#813) (c) does JAWS still read the editor value correctly
    (the property the Rich Edit default protects)? Record the result here like
    the 2026-07-03 four-way table. If emulate-sysedit fixes (a)/(b) without
    breaking (c), it graduates to the default surface.
- Risk: Low. Identical native control to the default, gated, with fallback; RTF
  streaming is guarded off (raises a clear error, never crashes); no existing
  surface changes.

### 2026-07-08 EM_STREAM ctypes-callback crash: post-mortem

Driving `EM_STREAMOUT`/`EM_STREAMIN` from a Python `ctypes` callback
**hard-crashes msftedit** (`RICHEDIT50W`) with an access violation the instant
the control invokes the callback. Reproduced and narrowed on-device:

| Variable | Tried | Result |
|----------|-------|--------|
| Control | wx `TextCtrl(TE_RICH2)` and raw `CreateWindowExW('RICHEDIT50W')` | both crash |
| Format | `SF_TEXT` and `SF_RTF` | both crash |
| Convention | `WINFUNCTYPE` (stdcall) and `CFUNCTYPE` | both crash |
| lParam | `byref(stream)` and `addressof(stream)` | both crash |
| Realization | window shown + `Yield()` and never shown | both crash |
| OLE | with and without `CoInitialize` | both crash |

Ruled out: **the thunk is valid** (callable directly from Python; the
`EDITSTREAM` struct is 24 bytes, `pfnCallback` at offset 16, holding the correct
address), and **ctypes callbacks work here with other guarded system APIs**
(`EnumWindows` visits 746 windows fine). The crash is specific to msftedit's
`EM_STREAM` dispatch of a libffi closure -- not a general callback problem, not
CFG in the blanket sense, not wx, not control state.

Verdict: pure-ctypes `EM_STREAM` is not viable. Two paths were identified, both
keeping the callback out of Python:

1. A small native helper `.pyd` owning the `EDITSTREAM` callback in compiled C
   (the `_quill_table_uia` / `scripts/build_table_uia.py` precedent).
2. **The TOM path (CHOSEN, and now shipping):** `EM_GETOLEINTERFACE` ->
   `ITextDocument::Open`/`::Save` with `tomRTF` -- no Python callback at all, so
   no crash surface. Verified end-to-end (see Phase 1 above). It is also the
   natural home for the Phase 3 selection (#813) work (`ITextSelection`).

## Preference ranking

Ranked for QUILL's audience (screen-reader-first, data integrity above all):

| Rank | Surface | Class | Risk | Verdict |
|------|---------|-------|------|---------|
| 1 | default | (delegates) | none | correct resting state |
| 2 | rich2 | wx.TextCtrl / RICHEDIT50W | low | shipping default |
| 3 | plain | wx.TextCtrl / EDIT | medium | best braille; loses multi undo/redo |
| 4 | rich | wx.TextCtrl / RICHEDIT20W | low-medium | A/B comparison point only |
| 5 | stc | StcEditorSurface / Scintilla | medium | testing round; only surface with native redo |
| 6 | rtf | RtfEditorSurface (wx-drawn) | high | testing only; SR-invisible |
| 7 | win32 | _Win32EditHost + raw EDIT | high | reference only; silent offset skew |

Placement note for stc: it enters at rank 5 pending screen-reader evidence.
If the JAWS/braille pass comes back clean it arguably belongs at rank 3 --
it would beat plain by keeping multi-level undo/redo -- but it does not get
that rank on promise.

Reasoning for the close calls:

- plain over rich: rich exists only as an engine-comparison point for #813;
  plain has a genuine end-user story (best braille behavior). If #813 lands
  on "RICHEDIT50W is the culprit," plain is the realistic fallback, so it
  outranks rich despite the undo/redo cost.
- rtf over win32: neither is usable, but rtf fails loudly (screen readers
  cannot read it -- users notice immediately), while win32 fails silently
  (offsets skew in CRLF space and corrupt bookmarks/notes/codes without any
  error). Silent data corruption is the worse failure mode; win32 ranks last.

## Undo/redo across surfaces (the multi-redo concern)

- rich2 / rich: native multi-level undo AND redo from the RichEdit engine.
  This is the only place QUILL gets real redo today, and it is free.
- plain / win32: the EDIT class has a single toggling undo slot and no redo.
  `CanRedo` is false; there is nothing to wire up.
- rtf: multi-level undo/redo exists but lives in wx's own command processor
  with different grouping rules.

You are right that fixing this outside the control is heavy engineering: an
app-level undo/redo engine means intercepting every mutation path (typing via
native WM_CHAR, paste, dictation, AI Replace, spell fix-ups, Quillin inserts),
snapshotting or delta-encoding each, and keeping QUILL's stack coherent with
the native one the control still runs internally -- plus braille/SR
announcements for undo/redo state. Estimate: a dedicated milestone, not a
patch. Practical position: staying on the RichEdit surfaces preserves
multi-level undo/redo for free, and that is a strong argument for solving
#813 *inside* rich2 (selection-reporting workaround) rather than migrating
the default to plain. If plain ever must become the default, the undo engine
should be scoped as its own project first.

## Other surfaces worth considering (not currently wired)

Scintilla previously led this list; it is now wired as surface 7 above
("Notepad++ experiment"). Remaining candidates:

- WebView2 + contenteditable (or a JS editor like ProseMirror) hosted in the
  `wx-accessible-webview` dependency QUILL already ships. Chromium exposes a
  full UIA text pattern, so JAWS/NVDA/braille support is first-class, and
  editor libraries bring multi-level undo/redo. Cost: an IPC boundary between
  QUILL's offset-anchored features and the DOM, focus handoff, latency, and a
  rewrite of the editor contract layer. Strategic option, not a knob -- but
  the only path that gives modern rich rendering AND accessibility AND redo.
- WinUI 3 RichEditBox via XAML island. Same msftedit lineage as rich2
  (RichEditD2D), so it likely inherits the same #813 behavior while adding
  heavy hosting machinery. Not recommended; listed for completeness.
- Fully custom surface with a UIA TextPattern provider (the Word / VS Code
  approach). Total control, total cost -- months of provider work like the
  Table Studio native provider but far larger. Only justified if every native
  option fails the braille requirement.

## Recommended next steps

1. Add a parametrized surface contract test: one set of assertions
   (selection tuple shape, empty-selection convention, offset round-trip
   through a multi-line buffer, undo after Replace) instantiated against
   rich2, rich, plain, and rtf with real wx. This week's two crashes would
   both have been caught by it.
2. Document the single-level undo caveat in the plain surface explainer.
3. Keep rtf and win32 double-gated; update the rtf explainer to state the
   screen-reader limitation explicitly.
4. Decide #813 on the rich2 vs plain A/B evidence, then fold the finding back
   into `editor_control_kind` guidance rather than growing the experimental
   list.

## 2026-07-03 follow-up: STC JAWS troubleshooting hook

After the JAWS test where Enter advanced QUILL's status line but JAWS stayed on
the old top line, the next change was deliberately diagnostic rather than another
caret workaround. `StcEditorSurface` now exposes
`accessibility_diagnostic_summary()`, a document-content-free snapshot that
compares what Scintilla knows internally with what classic Win32 text clients can
query from the control.

The snapshot reports the STC handle, internal text length, line count, current
position, line, column, and selection. On Windows it also reports the visible
Win32 class name, whether that handle has focus, `WM_GETTEXTLENGTH`, `EM_GETSEL`,
and `EM_EXGETSEL`. This is meant to confirm the suspected root cause: STC's
internal caret and line state can be correct while the Win32 text-query surface
that JAWS relies on is empty, incomplete, or not recognized as a real Scintilla
text window.

The existing Tools > Advanced > Developer Console > Copy Diagnostic Summary
command now includes the active editor-surface diagnostics. A tester can select
the Notepad++ experiment, type `this is a test`, press Enter, type another line,
then copy the diagnostic summary. If the STC line and caret values advance but
`WM_GETTEXTLENGTH` or the EM selection values do not reflect the same state, that
supports the theory that QUILL needs a real accessibility bridge for STC: either
a window-proc bridge answering classic text messages plus a system caret, or a
proper UIA TextPattern provider. A caret mirror by itself should remain avoided,
because the earlier experiment showed it can make JAWS switch modes and go
silent.

Guard coverage added with this change: `tests/unit/ui/test_stc_edit_surface.py`
now verifies that the STC surface exposes the diagnostic method, includes the
classic Win32 text-query probes, and does not include document content in the
diagnostic summary path.

## 2026-07-03 second braille round: cell-2 is back with JAWS; analysis

A structured four-way comparison (QUILL vs Notepad++, JAWS vs NVDA, braille
display attached):

| App | Screen reader | Text start cell | Selection visible in braille |
|-----------|---------------|-----------------|------------------------------|
| QUILL | JAWS | cell 2 | yes |
| QUILL | NVDA | cell 1 | yes |
| Notepad++ | JAWS | cell 1 | yes |
| Notepad++ | NVDA | cell 1 | yes |

Two things to note against the earlier round:

- This CONTRADICTS the first braille finding above (stc + JAWS = cell 1).
  Confirm which surface the tester actually had selected -- cell 2 with JAWS
  is exactly the shipping rich2 behavior (#616), so a run against the default
  surface would produce this table without telling us anything new about stc.
  The Copy Diagnostic Summary output settles it: the "Win32 class name" line
  reads the wx class for stc and RICHEDIT50W for the default.
- Selection dots were visible in ALL four cells of this round, including
  QUILL + JAWS -- better than the #813 report. Same caveat: confirm surface.

Root-cause analysis (assuming the run was stc): there is no Scintilla
property that fixes this, because the difference is not in Scintilla -- it is
in which support path JAWS chooses. Notepad++ ships real ScintillaWin:
window class "Scintilla", a window proc answering WM_GETTEXT / EM_GETSEL /
EM_EXGETSEL and the line-index family, and a mirrored system caret. JAWS
keys its dedicated handling off that class name and those channels, and that
path renders from cell 1. wx's port is a from-scratch reimplementation on a
generic wx window class with none of the three, so JAWS falls back to the
same degraded generic path it uses elsewhere. NVDA's generic path is simply
more forgiving.

Zero-code experiments for the next tester session, in cost order:

1. Copy Diagnostic Summary on the stc surface; record the Win32 class name.
2. JAWS window class reassignment (Settings Center / ConfigNames): reassign
   that class to "Scintilla", retest; then to "Edit", retest. Fixes cell 2 =
   the class-name heuristic is confirmed. JAWS goes silent = JAWS
   immediately queries the classic messages (same failure mode as the
   reverted caret mirror), which the bridge below now answers.
3. Check whether cell 2 persists in both JAWS braille structured mode and
   line mode, and on every line or only the caret line.

Performance note on the window-proc bridge (asked and answered): the classic
text queries are demand-driven (a handful per caret move), microseconds
each. The real overhead is the ctypes trampoline sitting in front of every
message to that one HWND -- a few microseconds per message, well under 1%
CPU even at mouse-move rates. The one genuine hotspot is repeated
WM_GETTEXT on a novel-sized buffer, which is why the bridge caches an
immutable text snapshot invalidated on change, and answers line-ranged
queries (EM_GETLINE) from it. If profiling ever shows the trampoline, the
escape hatch is a small native DLL subclass using Scintilla's direct
function pointer (SCI_GETDIRECTFUNCTION) -- the table_uia precedent -- with
zero Python in the hot path.

## 2026-07-03 the accessibility bridge, implemented behind a flag

`quill/ui/stc_accessibility_bridge.py`, opt-in via the new Experimental
setting `experimental_stc_accessibility_bridge` (bool, default off, gated
behind the master + editor-surfaces acknowledgements, restart required,
Windows only, stc surface only). What it installs -- always together,
because the caret-only experiment proved the halves are inseparable:

- A comctl32 `SetWindowSubclass` window-proc hook (ctypes, no pywin32) that
  answers WM_GETTEXT, WM_GETTEXTLENGTH, EM_GETSEL, EM_EXGETSEL,
  EM_LINEFROMCHAR, EM_EXLINEFROMCHAR, EM_LINEINDEX, EM_LINELENGTH,
  EM_GETLINE, and EM_GETLINECOUNT from a cached snapshot of the LF-only
  buffer. Offsets are UTF-16 code units (what Win32 text clients expect);
  Scintilla byte positions are converted at the boundary, with a fast path
  for all-ASCII documents. Unhooks itself on WM_NCDESTROY; every handler
  degrades to DefSubclassProc on any failure.
- The invisible all-zero-bitmap system caret mirror from the reverted
  d4f3f51, reinstated: created on focus, moved on EVT_STC_UPDATEUI,
  destroyed on blur.

Verified live on this machine (real STC window, SendMessageW from outside
the control): WM_GETTEXTLENGTH/WM_GETTEXT return the exact buffer,
EM_GETSEL/EM_EXGETSEL return the live selection both packed and through the
out-pointers, the line family maps offsets to lines and back correctly, and
window destruction unhooks cleanly. What SendMessage cannot prove is JAWS's
reaction -- that needs the hardware round: stc surface + bridge ON vs OFF,
checking (a) speech caret tracking on Enter, (b) braille start cell,
(c) selection dots. The `accessibility_diagnostic_summary` now also reports
"Classic text bridge: active/inactive", and with the bridge on its
WM_GETTEXTLENGTH / EM_GETSEL probe lines show real values instead of zeros.

Known limits, deliberate for the experiment: EM_POSFROMCHAR / EM_CHARFROMPOS
were initially left out until testing said they matter. (Both statements in
this paragraph were overtaken by round 1 -- see the next section: the class
name turned out to BE "Scintilla", and the geometry messages turned out to
be the load-bearing gap.)

How the code is wired, file by file:

- `quill/ui/stc_accessibility_bridge.py` (new, ~470 lines): everything
  lives here. Pure, unit-testable helpers at the top (`utf16_units`,
  `line_starts_utf16`, `line_from_offset`, `pack_em_getsel`,
  `build_snapshot` returning an immutable `TextSnapshot`); the
  `_SystemCaretMirror` class reinstated verbatim from d4f3f51; the
  `StcAccessibilityBridge` class owning the SetWindowSubclass hook, the
  message-handler table, and the snapshot cache; and
  `attach_accessibility_bridge(ctrl)`, the single entry point, which
  installs the subclass and binds the wx events (SET_FOCUS/KILL_FOCUS for
  the caret's lifetime, EVT_STC_UPDATEUI for caret moves, EVT_STC_CHANGE
  for snapshot invalidation, EVT_WINDOW_DESTROY for teardown). Returns
  None on any failure -- non-Windows, subclass rejection, anything.
- `quill/ui/stc_edit_surface.py`: `StcEditorSurface.__init__` and
  `create_stc_editor` gained an `enable_accessibility_bridge: bool = False`
  keyword; when true the surface calls `attach_accessibility_bridge(self)`
  inside try/except and stores the result (or None) on
  `self._accessibility_bridge`. The diagnostic summary reports
  "Classic text bridge: active/inactive".
- `quill/core/settings.py`: the `experimental_stc_accessibility_bridge`
  bool field (default False) with its from-dict parse and constructor
  wiring, same pattern as the other experimental gates.
- `quill/core/settings_specs.py`: its Experimental-tab SettingSpec (bool),
  which is what makes the checkbox appear on the tab.
- `quill/ui/main_frame.py`: three touches. The stc branch of
  `_create_document_tab` passes
  `enable_accessibility_bridge=acknowledged and <setting>`; the
  `_wire_experimental_gates` surface-children list adds the new checkbox so
  it enables/disables with the editor-surfaces gate; the settings-apply
  `_restart_keys` tuple adds the key so changing it warns about restart.
  The stc explainer text mentions the option.
- `quill/tools/module_size_budgets.json`: rebaseline entry
  `_rebaseline_2026_07_03_stc_a11y_bridge` (main_frame 27288->27299,
  settings 1492->1501, settings_specs 2185->2203).
- `tests/unit/ui/test_stc_edit_surface.py`: five new tests -- settings
  round-trip + default off, the spec is an experimental bool with
  scope/restart language, the pure helpers map offsets/lines/packing
  correctly (including astral chars and the ASCII fast path), the bridge
  source answers every ScintillaWin message and ships the caret mirror with
  teardown, and the flag is opt-in at both layers and wired from
  main_frame.

### 2026-07-03 bridge round 1 with JAWS: FAILED, and what the failure taught

Jeff's live test of the bridge above: JAWS showed no blank line on Enter,
newly typed text appeared to replace the previous line, and up arrow could
not review the old line. Classic single-line-edit behavior.

First, data integrity was verified immediately (live probe, typing sent
through the bridged window proc as WM_CHAR): the buffer kept both lines,
line count 2, caret moved freely back to line 0. The bridge answers
read-only queries and forwards everything else; the document was never at
risk. What broke was JAWS's VIEW of the buffer, not the buffer.

Second, two probe facts that rewrite earlier assumptions in this file:

- wx's StyledTextCtrl window class IS "Scintilla" (GetClassNameW, live).
  The caret-experiment note above claiming wx lacks the Scintilla class was
  wrong; both screen readers DO key their Scintilla handling off this
  window.
- wx's window proc answers the real Scintilla API messages natively:
  SCI_GETLENGTH, SCI_GETCURRENTPOS, SCI_LINEFROMPOSITION all returned
  correct values by SendMessage, bridge off. It answers NONE of the classic
  edit contract (EM_GETSEL -> 0, EM_GETLINECOUNT -> 0, geometry -> 0), and
  its native WM_GETTEXTLENGTH returns the window label, not the document.

That pair fully explains the NVDA/JAWS split, no further investigation
needed: NVDA's Scintilla support reads through SCI_* messages in-process,
which work on this control -- so NVDA is flawless. JAWS's handling uses the
classic edit-control contract (system caret + WM_GETTEXT/EM_* queries),
which this control does not speak natively and the bridge only partially
supplied.

The specific gap matching the failure signature: the bridge answered text,
selection, and line queries but not GEOMETRY. JAWS maps the system caret's
screen position back to a character and line via EM_CHARFROMPOS /
EM_POSFROMCHAR (with EM_GETRECT / EM_GETFIRSTVISIBLELINE for the viewport);
unanswered, every caret position resolves to char 0 / line 0 -- one
permanent line 0, which is exactly what Jeff experienced: no new line on
Enter, "replaced" text, nothing above to review.

The four geometry messages are now implemented and live-verified
(EM_POSFROMCHAR(13) -> client coords -> EM_CHARFROMPOS -> char 13 line 1
round-trip; formatting rect matches the client area; out-of-range -> -1).

### Decision point after round 1

Score so far on making wxSTC acceptable to JAWS: caret mirror alone =
worse; text bridge without geometry = worse in a new way. Each retry costs
a hardware session. Options:

- One final round with the geometry messages in, then a hard stop. The
  failure signature matched the geometry gap precisely, and the fix is
  in and verified mechanically -- but JAWS's actual query pattern has now
  surprised us twice.
- Park stc as an NVDA-only experimental surface (it is genuinely excellent
  there), leave the bridge off by default as a documented negative result,
  and decide #813 on the rich2 vs plain A/B as originally planned. If a
  Scintilla-class surface is ever wanted for JAWS users, the honest path is
  hosting the real ScintillaWin (scintilla.dll as a native child) rather
  than emulating it message by message, or a UIA TextPattern provider.

Test protocol for the next hardware round (JAWS + braille display):

1. Settings > Experimental: tick "Enable experimental features", tick the
   editor-surfaces acknowledgement, set Editor surface to "Notepad++
   experiment", tick "Notepad++ experiment: screen reader text bridge
   (Windows)". Restart QUILL.
2. Confirm the bridge took: Tools > Advanced > Developer Console > Copy
   Diagnostic Summary -- "Classic text bridge: active", and the
   WM_GETTEXTLENGTH / EM_GETSEL lines show real values.
3. Type two lines, press Enter between them: does JAWS speech follow the
   caret now (the d4f3f51 failure)? Arrow through lines: does braille
   start at cell 1? Select text: dots 7-8?
4. Repeat with the bridge checkbox OFF (restart) for the A/B.
5. If speech still lags, run the JAWS class-reassignment experiment (wx
   class -> "Scintilla") ON TOP of the bridge -- with the classic messages
   now answered, the reassignment that previously would have gone silent
   has real answers to read.

## 2026-07-03 FINAL: bridge round 2 failed; bridge removed; verdict

Round 2 (geometry messages included) still failed live JAWS testing. Per
the decision point above, that was the hard stop. Jeff called it; the
bridge is rolled back in full:

- `quill/ui/stc_accessibility_bridge.py` deleted; the
  `experimental_stc_accessibility_bridge` setting, its SettingSpec, the
  Experimental-tab checkbox, the gate wiring, the restart key, and the
  creation-site kwarg are all removed; module-size budgets restored to
  their pre-bridge values. A regression test
  (`test_jaws_bridge_stays_removed_and_the_surface_is_labeled_nvda_only`)
  pins the removal so the idea is not casually re-attempted.
- The stc surface itself STAYS, relabeled honestly: the Experimental-tab
  explainer now reads "EXPERIMENTAL, NVDA ONLY: ... JAWS cannot follow the
  caret on this surface (verified 2026-07-03; bridging attempts failed).
  Do not use with JAWS." The surface remains double-gated and off by
  default, and it remains the best NVDA braille result of any surface.

Why it stays rather than being ripped out: the surface is committed,
harmless behind two acknowledgements, genuinely excellent under NVDA, and
it already earned its keep as an instrument -- it isolated #813 to
RICHEDIT50W's selection reporting. Removing it buys nothing; the failed
part (the JAWS emulation) is what was removed.

Final scorecard for making wx.stc acceptable to JAWS, so nobody retries
the cheap paths: (1) system caret mirror alone -- JAWS switched into
live-edit mode with nothing to read, went silent (d4f3f51, reverted).
(2) Caret + classic text/selection/line answers -- JAWS rendered a
permanent single line; typing appeared to replace prior text (view-only;
buffer verified intact). (3) All of that + the EM_POSFROMCHAR /
EM_CHARFROMPOS / EM_GETRECT / EM_GETFIRSTVISIBLELINE geometry set,
mechanically verified by SendMessage round-trip -- still failed. JAWS's
Scintilla-class handling evidently depends on more of real ScintillaWin
than its documented message surface (plausibly in-process direct-function
reads or the character-metrics path); emulating it message by message from
Python is a dead end.

### What JAWS 2026 itself ships for Notepad++ (inspected on this machine)

Question raised after the rollback: does JAWS 2026 ship Notepad++ scripts
or settings that might have made the difference? Answer, from reading the
actual files under C:\ProgramData\Freedom Scientific\JAWS\2026: yes it
ships them, and no, they would not have helped. Three pieces:

- GLOBAL, and the one that matters: Default.JCF, [WindowClasses] section:
  `Scintilla=MultilineEdit` (comment: "Notepad++ and new Script Manager").
  JAWS's entire core Scintilla strategy is a global class reassignment --
  treat any window of class "Scintilla" in any application as a classic
  multiline EDIT. Since our surface's class IS "Scintilla", QUILL received
  this treatment in every test round. This also retro-explains the earlier
  "reassign the class in JAWS" experiment idea as moot: the mapping we
  would have created already exists out of the box.
- Per-app Scripts\Notepad++.jss (source ships uncompiled, ~150 lines):
  handles ONLY the autocomplete popup (ListboxX child window speech,
  braille routing, pan left/right), Ctrl+Arrow unit navigation, and one
  telling quirk fix -- it suppresses speak-window-name-on-focus because
  "Scintilla windows return the entire text of the document as their
  name". Nothing about core text reading, caret tracking, or line
  navigation: all of that is the built-in MultilineEdit backend.
- Per-app SETTINGS\enu\NotePad++.JCF: one line, BrailleMoveActiveCursor=1.

So aliasing quill.exe to the NotePad++ config (ConfigNames.ini) would have
bought autocomplete polish and one braille flag -- not caret tracking. The
core handling QUILL already got, and it failed against our emulation while
succeeding against real ScintillaWin. Conclusion sharpened: JAWS's
MultilineEdit backend depends on genuine EDIT/ScintillaWin behavior beyond
the documented message surface (in-process reads, font metrics, or EM_
semantics we did not replicate). Freedom Scientific's own Script Manager
is a real embedded Scintilla riding the same class map -- the mechanism is
proven, but only with the genuine control behind it.

One extra confirmation from the .jss comment: with our bridge on,
WM_GETTEXT returned the whole document, so JAWS ALSO saw the document as
the window NAME -- Notepad++ needs a script just to mute that. A working
bridge would have needed a per-app QUILL script on top, one more hidden
cost of the emulation path.

If a Scintilla surface for JAWS users ever becomes strategic, the two
honest paths, in order: host the real scintilla.dll as a native child
(class, window proc, caret, and JAWS behavior all come from the genuine
article; the LF EOL mode avoids the CRLF offset skew that killed the raw
EDIT spike), or a full UIA TextPattern provider. Both are real projects,
not knobs.

Where this leaves the original goals: #813 (JAWS selection dots) and the
cell-2 offset get decided on the rich2 vs plain A/B as planned, with the
stc data point (a non-RichEdit surface showing correct selection dots
under JAWS) as supporting evidence that the fault is in RICHEDIT50W's
selection reporting. The undo/redo argument for leaving rich2 is gone --
rich2 already has native multi-level undo/redo, and it remains the
shipping default.
