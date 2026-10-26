# Spike: making screen readers see QUILL's tables (October 2026)

Status: spike finished 2026-10-25. Nothing under `quill/` was changed. The
prototype and its recorded output are in `docs/design/spikes/table_uia/`.

**Decision, 2026-10-26: no add-ons and no reader scripts.** Tables became real
RichEdit tables in rich text (`quill/ui/richedit_tables.py`), which gives
Narrator RichEdit's own grid, and the editors now own the arrow keys inside a
table (`quill/core/table_nav.py`, `arrow_move`): Up and Down move cell to cell
and the app says the cell, so every reader hears the same thing with nothing
installed. The NVDA add-on recommended below was started and withdrawn; it is
kept here as the record of what each reader can and cannot see.

## The question

QUILL and QUILL Lite show a table as Markdown pipe rows (`| a | b |`) inside a
stock Windows Rich Edit control (`RICHEDIT50W`, msftedit.dll, reached through
`wx.TextCtrl` with `TE_RICH2`). QUILL's own commands (`quill/core/table_nav.py`,
Navigate > Table, Ctrl+Alt+arrows) move cell by cell and announce "Row 2 of 4,
column 3 of 5: text". The screen reader itself does not know it is in a table:
no "table with 3 rows" on entry, no braille table indicators, and its own table
commands do nothing.

Can QUILL make NVDA, JAWS and Narrator themselves recognise those regions as
tables, while keeping the stock Rich Edit control?

## How to read this note

Every claim is marked:

- **Verified (ran)**: measured on this machine (Windows 11 build 26200,
  msftedit.dll 10.0.26100.8117, wxPython 4.3.1, NVDA 2026.2 installed).
- **Verified (read)**: read in source or in shipped bytecode.
- **Believed**: my understanding of documented or observed behaviour, not
  checked in this spike.

## Short answer

1. NVDA does not use UI Automation for a `RICHEDIT50W` window at all, so any
   UIA work on the stock control (wrapping provider, child table elements,
   custom text attributes) is invisible to NVDA. **Verified (read)**: NVDA
   2026.2's `UIAHandler` lists `RichEdit`, `RichEdit20` and `RICHEDIT50W` in
   `badUIAWindowClassNames`, and logs "Window found in badUIAWindowClassNames.
   Treating as non-UIA" unless an app module overrides it. NVDA reads Rich Edit
   through the Text Object Model (TOM) instead, in `NVDAObjects/window/edit.py`,
   and that module contains no table handling at all (no "table" string in its
   bytecode).
2. Rich Edit's own UIA provider already exposes native Rich Edit tables, but
   only partly, and only Narrator (and any other pure-UIA client) would see it.
   **Verified (ran)**: a three-by-three RTF `\trowd` table appears as a
   `DataGrid` child named "Rich Edit Table" with the Grid pattern (3 rows,
   3 columns), and nine `DataItem` children with GridItem and Value. There is
   no Table or TableItem pattern, so no header relationships, and
   `GetEnclosingElement()` for text inside a cell returns the grid, not the
   cell. The same table written as pipe rows produces no child elements at all.
3. Switching QUILL's editor representation to native Rich Edit tables is not
   the cheaper path. It buys nothing for NVDA, partial semantics for Narrator,
   an unknown amount for JAWS, and it breaks every offset-based feature, because
   the control's text changes shape (tabs in `GetValue()`, hidden U+FFF9,
   U+FFFB and BEL marker characters in TOM and UIA text).
4. **Recommendation**: reach NVDA through a small, optional NVDA add-on that
   adds table fields for pipe rows to NVDA's existing Rich Edit support, with a
   presence handshake so QUILL stops making its own table announcements when the
   add-on is there (GATE-13). Prototype first: about 3 days for a go/no-go,
   about 2 to 3 weeks to ship. Narrator and JAWS are follow-ups, ranked below.

## What the prototype measured

`docs/design/spikes/table_uia/probe_richedit_table_uia.py` opens a wx frame
with two `TE_RICH2` controls. One gets a real Rich Edit table through
`EM_SETTEXTEX` with RTF (the same storage TOM `ITextRange2::InsertTable`
produces); the other gets the same table as pipe rows. A second process (a UIA
client should not run on the provider's own UI thread) then dumps what UIA
reports. No screen reader is needed. Full output:
`docs/design/spikes/table_uia/probe_output_2026-10-25.txt`.

**Verified (ran)**, both controls:

- `UiaHasServerSideProvider` is true. The element is ControlType `Document`,
  class `RICHEDIT50W`, with the Text, Text2 and Value patterns. The provider
  description names `msftedit.DLL` as the main provider, so this is
  msftedit's own UIA implementation, not the MSAA proxy.
- `UIA_StyleNameAttributeId` and `UIA_StyleIdAttributeId` return
  `ReservedNotSupportedValue`. Rich Edit's provider does not report named
  styles.

**Verified (ran)**, native table control:

- Raw-view children: a vertical scroll bar and `DataGrid "Rich Edit Table"`,
  Grid pattern, `RowCount=3`, `ColumnCount=3`. Its children are `DataItem`
  elements named by cell text ("Name", "Age", ... "C3"), each with GridItem
  (correct row and column) and Value. No TableItem, so no column-header
  relationship, even though RTF has a header-row flag.
- `DocumentRange.GetChildren()` returns the one `DataGrid`.
- `GetEnclosingElement()` of a range on "B2" returns the `DataGrid`, whose
  parent is the edit. The cell is never the enclosing element.
- Searching the subtree for the Table pattern finds nothing.
- Text units: the line unit around "B2" is the whole row with markers,
  `'\ufff9\rA2\x07B2\x07C2\x07\ufffb\r'`; the paragraph unit is the single
  cell, `'B2\x07'`. The document text carries U+FFF9 (row start), U+FFFB
  (row end) and `\x07` (cell end).
- `wx.TextCtrl.GetValue()` returns the table as tab-separated lines:
  `'Name\tAge\tCity\nA2\tB2\tC2\n...'`. The offsets QUILL computes from
  `GetValue()` therefore differ from TOM and UIA offsets inside a table.

**Verified (ran)**, pipe control: no children, `GetChildren()` is empty, the
enclosing element of "B2" is the edit itself, and the line and paragraph units
are the plain pipe row. That is the baseline: today no screen reader can learn
anything about the table from the control.

## How each reader consumes a Rich Edit control

### NVDA

- **Verified (read)**, NVDA 2026.2 bytecode: `RICHEDIT50W` is normalised to
  `RichEdit50` and served by `NVDAObjects/window/edit.py` (TOM through
  `ITextDocument`). UIA is not consulted for this window class. An app module
  can override that with `isGoodUIAWindow`.
- **Verified (read)**: NVDA's UIA text support does understand tables. Its
  `UIATextInfo._getControlFieldForUIAObject` builds `table-id`,
  `table-rowcount`, `table-columncount`, `table-rownumber`,
  `table-columnnumber`, the span fields and `table-columnheadertext` from the
  TableItem pattern and the header-items properties of the elements that
  enclose a text range.
- **Believed**: NVDA walks from `GetEnclosingElement()` up to the root to build
  those control fields, and reports a table on entry when one of them has the
  table role with row and column counts. Because Rich Edit's own provider makes
  the grid, not the cell, the enclosing element, NVDA forced onto UIA would at
  best say "table" without cell coordinates. ScanMaster's changelog (2.21.3)
  confirms the other half: NVDA discovers embedded objects by calling
  `ITextRangeProvider.GetChildren()` on the range it reads.
- **Believed** (ScanMaster 2.22.0-beta.32, and its notes in `C:\sm\sm.md`):
  NVDA only provides its Ctrl+Alt+arrow table commands for Word and web
  documents, not for a plain edit. QUILL keeps its own cell commands whatever
  is chosen here.

### JAWS

- **Believed**: JAWS treats `RICHEDIT50W` as a standard edit, using window
  messages, MSAA and its own Rich Edit support, not UIA. ScanMaster found that
  JAWS "reads nothing via UIA without the MSAA role" and only reads through
  UIA when the MSAA role is a text box (2.22.1). Whether JAWS announces native
  Rich Edit tables (for example in WordPad) is untested. That is a 30-minute
  check with JAWS and the probe's frame, worth doing before any decision
  that leans on native tables.

### Narrator

- **Verified (ran)** in principle: Narrator is a pure UIA client, and msftedit
  answers with a server-side provider, so Narrator would see the native
  `DataGrid` and `DataItem` elements. **Believed**: Narrator's table reading in
  text depends on the enclosing element exposing TableItem or GridItem, so with
  the grid as the enclosing element it may say "table" without cell positions.
  Untested by ear.

## The options

### (a) Subclass the Rich Edit window and answer WM_GETOBJECT with a wrapping provider

The idea: hook `WM_GETOBJECT` on the Rich Edit window, return our own
`IRawElementProviderSimple`, delegate text to msftedit's provider and add
table semantics for pipe ranges.

- **Delegation is the hard part.** For a windowed Rich Edit there is no
  supported way to get msftedit's provider object to wrap. Calling the
  original window procedure with `WM_GETOBJECT` returns an LRESULT meant for
  UIA core, not a pointer. `UiaHostProviderFromHwnd` (which
  `quill/native/table_uia` uses) yields only the HWND proxy, not msftedit's
  Text pattern. **Believed**: msftedit's `IRicheditWindowlessAccessibility` and
  `IRicheditUiaOverrides` (textserv.h) exist for windowless hosts, which QUILL
  is not.
- **Override providers** are the closest supported route: the parent window's
  provider implements `IRawElementProviderHwndOverride` and supplies an override
  provider for the edit's HWND, which UIA merges above msftedit's. **Believed**:
  patterns merge whole, so supplying a Text pattern replaces msftedit's
  entirely. Table semantics need the text ranges themselves to answer
  `GetEnclosingElement()` and `GetChildren()`, so the override ends up as a
  hand-written `ITextProvider` plus `ITextRangeProvider` over TOM.
- That is exactly ScanMaster 2.19 to 2.21. Its lessons, from its changelog:
  NVDA calls the provider from its own thread while TOM is apartment-bound, so
  every TOM call had to be marshalled to the UI thread (2.19.1);
  `GetChildren()` had to be really implemented before NVDA found embedded
  objects (2.21.3); hit-testing and caret problems surfaced elsewhere
  (2.21.4). In 2.22 it abandoned Rich Edit for Qt and still needed twelve
  numbered patches to Qt's UIA text provider: paragraph units, wrapped line
  units, Narrator's stale `Select`, `ScrollIntoView` moving the caret, JAWS's
  blank lines. Writing our own text provider means owning all of those.
- **Reach**: Narrator only, unless an NVDA app module also forces UIA (then
  NVDA too, through our provider rather than its mature TOM support). JAWS:
  probably none without also changing the MSAA role.
- **Risk**: high. UIA calls arrive on other threads; a provider bug crashes or
  hangs QUILL's UI thread, and that affects every user, not only screen-reader
  users.
- **Effort**: 6 to 10 weeks for a text provider good enough to replace
  msftedit's for typing, reading and selection, plus a long tail.

### (b) Pipe tables as UIA child elements of the edit

Add `Table` and `DataItem` fragments under the edit for each pipe region, as
`quill/native/table_uia` does for the virtual list.

- Child elements on their own are not enough: NVDA and Narrator learn they are
  in a table from the text range (`GetEnclosingElement`), and the range comes
  from the Text pattern. Without owning the Text pattern, the children are
  visible to object navigation and inspection tools but are not announced as
  the caret moves. So (b) is a part of (a), not an alternative to it.
- **Reach**: object navigation in Narrator and Inspect; no announcements.
  **Effort**: 1 to 2 weeks on top of the existing provider code, little value
  alone.

### (c) Custom text attributes or UIA_StyleNameAttributeId per range

- **Verified (ran)**: msftedit returns NotSupported for StyleName and StyleId.
  Attributes are answered by `ITextRangeProvider::GetAttributeValue`, so adding
  any attribute again means owning the text provider, as in (a).
- Even if supplied, an attribute such as a style named "Table row 2" is not
  table semantics: no reader turns it into "table with 3 rows" or braille
  table indicators. NVDA can say a style name only with "Report style" on.
- **Verdict**: not useful for tables.

### (d) Screen-reader-specific routes

**NVDA add-on (app module for QUILL's process).** NVDA already reads QUILL's
editor through its TOM-based `RichEdit50` object. An app module can apply an
overlay class whose TextInfo inserts table control fields (`role=TABLE`,
`table-id`, `table-rowcount`, `table-columncount`, then per cell
`table-rownumber`, `table-columnnumber`, and `table-columnheadertext` from the
header row) around the text of pipe rows. NVDA's speech and braille code
already turn those fields into "table with 3 rows and 3 columns", "row 2,
column 3", "out of table", the user's own "Report tables" and cell-coordinate
settings, and braille table output.

- **Where table structure comes from**: the add-on can parse pipe rows itself
  from the lines around the caret, which is the same pure parsing
  `quill/core/table_nav.py` does. A port of `TableGrid` parsing is a
  few hundred lines and keeps the add-on free of any QUILL connection.
- **What else it can add**: NVDA's own Ctrl+Alt+arrow table scripts, by mixing
  in NVDA's document table-navigation support, so the reader's commands match
  Word. QUILL's Ctrl+Alt+arrows already do this; the add-on should either
  leave the chords to QUILL or claim them and keep the behaviour identical.
- **Threading**: none of QUILL's concern. The add-on runs inside NVDA and
  uses NVDA's TOM access exactly as NVDA does today.
- **Precedent**: ScanMaster ships an NVDA add-on (it wires a Hyperlinks List
  to NVDA+F7). **Believed**: the NV Access add-on store accepts app-module
  add-ons like this.
- **Limits**: NVDA only; the user must install it. It reports what the pipe
  text says, so a pipe row typed in prose that `table_nav` would also call a
  table becomes one. That is consistent with QUILL's own commands.
- **Effort**: about 3 days for a prototype that speaks entry, exit and cell
  positions; about 2 to 3 weeks to ship, including braille checks, packaging,
  an installer offer from QUILL, and tests against NVDA's last two releases.

**JAWS scripts.** JAWS scripts for QUILL's executable could detect pipe rows
on caret movement and speak and braille table information, using JAWS's own
table functions where they accept script-supplied data. **Believed**: JAWS
scripting has no supported way to give its built-in table layer a synthetic
table in an edit, so the result would be script-spoken announcements; that
is close to what QUILL already does itself, with different chords. Low value
until users ask. Effort 1 to 2 weeks, plus a JAWS licence for testing.

### (e) MSAA or IAccessible2

- MSAA has no table model. IAccessible2 has `IAccessibleTable2` and
  `IAccessibleTableCell`, and `IAccessibleText` for text, but readers use
  IAccessible2 for browsers and a few toolkits. **Believed**: NVDA does not
  apply IAccessible2 to a `RICHEDIT50W` window, and JAWS's Rich Edit handling
  does not look for it. Implementing IAccessible2 would mean providing our
  own `IAccessibleText` too, so it is (a) again, with fewer readers.
- **Verdict**: no.

## Native Rich Edit tables instead of pipe rows

The question was whether switching the editor representation to native Rich
Edit tables would be cheaper, since Rich Edit's own provider might already do
the work.

**What it would buy** (from the probe and the reader notes):

- NVDA: nothing. Its TOM-based Rich Edit support has no tables, and it ignores
  msftedit's UIA.
- Narrator: a `DataGrid` with Grid and GridItem, no headers, and the grid
  rather than the cell as the enclosing element. Partial at best.
- JAWS: unknown, untested.

**What it would cost** QUILL's pipe-row features (**Verified (read)** in the
tree, plus the probe's text shapes):

- `quill/core/table_nav.py`, `quill/ui/main_frame_table_nav.py`,
  `quill/apps/lite_window_tables.py`, `quill/apps/lite_window_insert_table.py`
  and `quill/core/structure_announce.py` all parse pipe text. They would need
  a second model that reads table structure through TOM (`ITextRange2` table
  and cell properties) rather than through text.
- Offsets: QUILL's search, spelling, AI, read-aloud and braille are anchored to
  `get_plain_text()` offsets. Inside a native table, `GetValue()` gives tabs
  between cells while TOM and UIA count U+FFF9, U+FFFB and `\x07` markers, so
  every offset map needs a table-aware translation.
- `quill/io/docx_reader.py` turns Word tables into pipe rows ("Rich edit has no
  native table vocabulary"); `quill/io/docx_writer.py` turns pipe rows back into
  Word tables; Markdown round trips rely on pipe rows being the text. All
  three would need native-table paths in both directions, and Markdown files
  would need converting at open and save.
- `quill/io/rtf_model.py` lists `\trowd` and `\cell` as unsupported features
  that flatten; QUILL's markup subset has no table vocabulary to carry them.
- QUILL Lite parity (the family rule that Lite may never be ahead of QUILL)
  means both editors change together.
- ScanMaster's history warns that Rich Edit's table insertion over COM threw
  on some Word tables and crashed the app until it was caught (2.19.4).

Estimate: 6 to 8 weeks across both editors and the readers and writers, for a
gain that reaches Narrator partially and NVDA not at all. Not the cheaper path.

## Coexistence with QUILL's own announcements (GATE-13)

Whatever reaches the reader, QUILL must then stop saying the same thing. Today
QUILL announces entering and leaving a table and "Row 2 of 4, column 3 of 5"
on its cell commands. Once the reader reports tables itself:

- On plain caret movement into or out of a table, QUILL must say nothing about
  the table; the reader will.
- On QUILL's Ctrl+Alt+arrow cell moves, the reader will report the new
  row and column from the field change, so QUILL should announce only the
  "edge of table" and "no more rows" outcomes the reader cannot know.
- QUILL can only do that if it knows the add-on is active. Proposed handshake:
  the add-on sets a window property (for example `QuillNvdaTables`) on QUILL's
  top-level window with `SetProp` when NVDA's app module loads, and removes it
  when it unloads; QUILL checks the property before a table announcement. This
  is a cross-process `SetProp` on a window NVDA can already reach. No setting
  for the user, which GATE-13 prefers to a verbosity option.
- The announcement change must also keep GATE-BRAILLE parity: the
  announcements QUILL drops are dropped from braille as well, which is right,
  because NVDA brailles the table fields itself.

## Recommendation

1. **Do not** build a UIA provider over the stock Rich Edit for tables (options
   a, b, c), and do not switch to native Rich Edit tables. NVDA ignores the
   first and gains nothing from the second; both are weeks of work with
   crash risk (a) or broad regressions (native tables).
2. **Do** prototype the NVDA add-on route (option d):
   - Day 1: an app module for QUILL's process that overlays the
     `RichEdit50` object and injects table control fields for pipe rows on the
     caret's line and its neighbours, parsed with a port of `table_nav`'s
     grid code.
   - Day 2: check by ear and in NVDA's log: entry "table with N rows and M
     columns", cell coordinates on Up and Down within a column, exit, the
     column header text, braille output, and say-all over a table.
   - Day 3: the `SetProp` handshake and a matching change in QUILL's table
     announcements behind it (a QUILL change, so outside this spike), then
     go/no-go.
   - If it works: 2 to 3 weeks to ship as an optional add-on, offered from
     QUILL's Help or first-run screen, with its source under `quill/` tooling
     or a sibling repo so the repo-wide gates can see it.
3. **Before committing to anything that leans on native tables**, spend
   30 minutes with JAWS and Narrator against the probe's frame (it stays open
   only while the dump runs; lengthen the `CallLater` delay or drop the dump to
   keep it up) to learn whether either announces the native table. That
   result decides whether native tables are ever worth revisiting for those two
   readers.
4. **Later, only if Narrator users ask**: the override-provider route in (a)
   is the only way to reach Narrator with pipe tables, and it means owning a
   full text provider; revisit it then with ScanMaster's patch list as the
   test plan.

## Files from this spike

- `docs/design/table-uia-spike-2026-10.md`: this note.
- `docs/design/spikes/table_uia/probe_richedit_table_uia.py`: the probe. Run
  with `py -3.14 docs/design/spikes/table_uia/probe_richedit_table_uia.py`.
- `docs/design/spikes/table_uia/probe_output_2026-10-25.txt`: its output on
  this machine.
