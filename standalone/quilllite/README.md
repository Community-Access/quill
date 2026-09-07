# QuillLite

A notepad and wordpad replacement for screen reader users. It is QUILL with
everything removed except the editor.

One document per window, no tabs. Each window is either plain text or rich
text. That is the whole feature list.

QuillLite exists for the person who wants Notepad or WordPad with QUILL's
accessibility, and who finds the full writing environment more than they need.
It is not a replacement for QUILL and it is not where new features should go.
Anyone who wants AI, dictation, conversion, comparison, publishing or Quillins
wants QUILL, and QuillLite deliberately cannot grow into it.

## What it keeps from QUILL

- The native Windows Rich Edit control (`RICHEDIT50W`) as the editor in both
  modes, for the reason QUILL chose it: its `IAccessible` value is reported
  correctly to NVDA and JAWS where a classic EDIT control's is not.
- RTF load and save through the Text Object Model, never through an
  `EM_STREAMIN` callback, because QUILL already established that a Python
  callback hard-crashes msftedit.
- The RTF safety scan: embedded OLE objects and binary payloads are stripped
  before a byte reaches the control, and remote-fetching fields are flagged.
- The heading ladder, so a saved RTF reads as headings in Word.
- The keyboard rules: every menu item shows its key, no key is bound twice,
  no two controls in a window claim the same access key, and the app announces
  only what the screen reader cannot already say.

## What it drops

Tabs, AI, dictation, self-voicing, Markdown and HTML preview, Quillins, remote
files, GitHub, braille tooling, the setup wizard, the command palette, and
every companion app. Speech goes only to a running NVDA or JAWS; there is no
SAPI fallback, because a self-voicing editor talks over the screen reader that
is already talking.

The result is about 2,000 lines across eleven modules, with no dependency
beyond wxPython and comtypes.

## Modes

**Plain text** puts the control into `TM_PLAINTEXT`, so it behaves like
Notepad. Files keep the encoding and line endings they arrived with, verified
byte for byte for CRLF, LF, BOM and empty files.

**Rich text** gives bold, italic, underline, headings 1 to 4, alignment and
font for the selection, saved as `.rtf`. Text colour is not part of the
document: dark mode colours the view, and the colour is reset to automatic
before every save so a theme never leaks into someone's file.

`Ctrl+Shift+M` moves a window between the two, warning before it drops
formatting.

## Running

    python -m quilllite [--rich | --plain] [file ...]
    python -m quilllite --check     # diagnostics, no window

A second launch hands its files to the first through a small inbox directory
and exits, so opening a file from Explorer is instant once QuillLite is up.
Settings and the recovery copies of unsaved windows live in
`%LOCALAPPDATA%\QuillLite`.

## Tests

`pytest -q` runs the wx-free unit tests: the command table (every item has a
key, no key or access key is claimed twice), the RTF scanner, settings, and the
heading ladder.

Four scripts need a real Windows desktop session and are run by hand, because
what they check cannot be faked:

| Script | What it proves |
|---|---|
| `tests/probe_windows.py` | the Rich Edit surface: RTF round trip, headings through the TOM, MSAA value, plain-text saves |
| `tests/probe_app.py` | one window per document, the single-instance handover, unsaved-work recovery |
| `tests/probe_roundtrip.py` | files come back byte for byte |
| `tests/repro_tom_true.py` | the `tomTrue` bug described below |

`probe_app.py` runs its assertions inside a real `MainLoop`. `wx.Yield()` does
not dispatch `WM_TIMER`, so anything timer-driven tests as broken outside one.

## A bug this found in QUILL

`quill/ui/richedit_rtf_surface.py` declares:

    _TOM_TOGGLE = -9999998
    _TOM_TRUE = -9999999
    _TOM_FALSE = 0

In `tom.h`, `tomTrue` is `-1`. `-9999999` is `tomUndefined`. Assigning
`tomUndefined` to `ITextFont.Bold` asks the control to leave bold undefined, so
`set_heading` applies the point size and silently never applies the bold, and
raises nothing.

Because `heading_level_for_font` requires bold to call a paragraph a heading,
QUILL's own heading navigation and Describe Formatting then cannot see the
headings QUILL just created.

`tests/repro_tom_true.py` reproduces it in isolation. Output on
`RICHEDIT50W` / Riched20 10.0.26100, Windows 11 build 26200, wxPython 4.3.1:

    Bold = -9999999 (QUILL's _TOM_TRUE)   -> Bold=0 Weight=400
    Bold = -1 (tom.h tomTrue)             -> Bold=-1 Weight=700

The fix is one line: `_TOM_TRUE = -1`. It is not applied to `quill/` in this
branch, since that is a separate change from adding an app.

## A second finding

`caret_format_description` reads the collapsed selection, and a collapsed range
reports the formatting of the character *before* it. Standing at the start of a
heading therefore describes the previous paragraph. QuillLite's
`Editor._format_range` probes `Range(start, start + 1)` when there is no
selection, matching what a screen reader describes.

## Provenance

QuillLite is a derivative of QUILL for All, MIT licensed, and inherits this
repository's licence. The editor surface, the RTF safety scanner and the
heading ladder are adapted from `quill/ui/richedit_rtf_surface.py` and
`quill/io/rtf_safety.py`, with thanks.
