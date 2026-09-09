# Full audio tag editor and complete chapter editing — design

Date: 2026-09-02
Status: approved (design), not yet implemented
Area: QUILL Audio Studio — Chapter Workbench

## Problem

The Chapter Workbench (`quill/ui/audio_studio/chapter_workbench.py`) opens a
finished MP3 or M4B, plays it chapter-aware, and can rename, split, retime,
merge and restore chapters, plus import and export chapter lists in five
formats. What it cannot do:

- **Tags.** It edits seven fields only — the `AudioMetadata` dataclass in
  `quill/core/speech/ffmpeg.py` (title, artist, album, album artist, genre,
  year, comment) — and the dialog exposes five of them. There is no track,
  disc, composer, publisher, copyright, BPM, ISRC, lyrics, language,
  grouping, compilation flag, sort-order field, or cover art.
- **Chapters.** There is no explicit *add*, no *delete*, no way to type an
  exact start **and** end, and no preview that stops at the chapter's end.
  `split_chapter`, `merge_chapter` and `set_chapter_start` approximate three
  of those with different semantics and different wording.

The goal is a full MP3 tag editor and complete chapter editing — add, remove,
preview, alter — reachable both from the Workbench and standalone.

## Scope decisions

| Decision | Choice |
| --- | --- |
| Tag depth | Curated named fields plus cover art. No raw-frame grid, no arbitrary TXXX editor. |
| Placement | A new dialog opened from the Workbench and standalone from the Studio wizard. |
| Chapter operations | Add, delete, edit start/end/title/extras, preview-to-end. |
| Formats | MP3 in full; M4A/M4B best-effort via MP4 atoms. Not FLAC/OGG/WAV. |
| M4B tag writes | In place with mutagen. The ffmpeg re-mux stays reserved for chapter changes. |

## Architecture

Three new modules and three extended ones. Everything with logic is wx-free
and strict-typed; the UI modules gain surfaces and wiring only.

| Module | State | Role |
| --- | --- | --- |
| `quill/core/speech/audio_tags.py` | new | field table, `AudioTags`, read/write, cover art |
| `quill/core/speech/chapters.py` | grow | `add_chapter`, `delete_chapter`, `set_chapter_bounds` |
| `quill/ui/audio_studio/tag_editor.py` | new | `TagEditorDialog` — notebook, one panel class per page |
| `quill/ui/audio_studio/chapter_workbench_edits.py` | new | the new chapter handlers, as a mixin |
| `quill/ui/audio_studio/chapter_workbench.py` | grow | one table-driven button row |
| `quill/ui/audio_studio/pages_audio.py` | grow | the standalone "Edit tags only..." route |
| `quill/core/settings.py` | grow | `audio_studio_chapter_nudge_ms`, the remembered nudge step |

### `quill/core/speech/audio_tags.py`

`TagField` is the single source of truth for one tag, so the dialog, the
readers, the writers and the tests all agree:

```python
@dataclass(frozen=True, slots=True)
class TagField:
    key: str      # "album_artist"
    label: str    # "Album &artist:" — mnemonic included
    group: str    # "main" | "details" | "publishing" | "sort"
    kind: str     # "text" | "number" | "pair" | "multiline" | "bool"
    id3: str      # "TPE2"
    mp4: str      # "aART", or "----:com.apple.iTunes:PUBLISHER", or "" for none
    help: str     # the sentence F1 reads out
```

`TAG_FIELDS` holds 26 entries in four groups:

- **main** — title (`TIT2`/`©nam`), subtitle (`TIT3`/freeform SUBTITLE),
  artist (`TPE1`/`©ART`), album (`TALB`/`©alb`), album artist
  (`TPE2`/`aART`), track number and track total (`TRCK` as `n/m`, `trkn`),
  disc number and disc total (`TPOS` as `n/m`, `disk`), genre
  (`TCON`/`©gen`), year (`TDRC`/`©day`).
- **details** — original release date (`TDOR`/freeform ORIGINALDATE), comment
  (`COMM`/`©cmt`), lyrics (`USLT`/`©lyr`, multiline), grouping
  (`TIT1`/`©grp`), language (`TLAN`/freeform LANGUAGE), BPM (`TBPM`/`tmpo`),
  part of a compilation (`TCMP`/`cpil`, boolean).
- **publishing** — composer (`TCOM`/`©wrt`), conductor (`TPE3`/freeform
  CONDUCTOR), publisher (`TPUB`/freeform PUBLISHER), copyright
  (`TCOP`/`cprt`), encoded by (`TENC`/freeform ENCODEDBY), ISRC
  (`TSRC`/freeform ISRC).
- **sort** — sort title (`TSOT`/`sonm`), sort artist (`TSOP`/`soar`), sort
  album (`TSOA`/`soal`), sort album artist (`TSO2`/`soaa`).

`AudioTags` holds `values: dict[str, str]` keyed by `TagField.key`, plus
`cover: CoverArt | None`. Empty string means "not present"; writing an empty
value deletes the frame. Helpers: `get`, `set`, `copy`.

`CoverArt` holds `data: bytes`, `mime: str`, `description: str`, and
`picture_type: int` (3 = front cover). Only `image/jpeg` and `image/png` are
accepted; `load_cover(path)` sniffs the real bytes rather than trusting the
extension and rejects anything over 8 MB with a speakable message.

`read_tags(path)` and `write_tags(path, tags)` dispatch on suffix: `.mp3`
through `mutagen.id3.ID3`, `.m4a`/`.m4b`/`.mp4` through `mutagen.mp4.MP4`.
Both load the existing tag block and change only the frames the table names,
so CHAP/CTOC chapter frames — and any frame this editor does not model —
survive untouched. Fields whose `mp4` is empty are skipped on MP4 files
rather than guessed at.

**ID3 version.** `save_mp3_book` currently saves `v2_version=3`. ID3v2.3 has
no home for `TDRC`, `TDOR`, `TSOT`, `TSOP`, `TSOA` or `TSO2`; mutagen's
`update_to_v23()` converts two of those and drops the rest, and a tag editor
that silently discards every sort field is not a full tag editor. So
`preferred_id3_version(tags) -> int` returns 3 when no v2.4-only field is
set and 4 once one is. Files stay maximally compatible until the user asks
for something only v2.4 can hold. `write_mp3_chapters` takes the version as a
keyword argument so one save cannot write the tag block at v2.3 and the
chapter block at v2.4.

**Bridge.** `to_audio_metadata(tags)` and `merge_audio_metadata(tags, meta)`
convert to and from the existing `AudioMetadata`, so `BookFile`, the M4B
re-mux and the batch document-to-speech pipeline are unchanged.

**Errors.** `TagReadError` (`QUILL-SPEECH-TAG-READ`) and `TagWriteError`
(`QUILL-SPEECH-TAG-WRITE`), both `CodedError` subclasses per GATE-EC, both
carrying speakable messages.

### Chapter operations in `chapters.py`

Three pure functions beside the existing ones, each returning a renumbered
list and raising `ChapterEditError` with a speakable message:

- `add_chapter(chapters, at_ms, *, title, min_part_ms=1000)` inserts a
  boundary at `at_ms`. Inside a chapter it behaves as `split_chapter` does;
  at or past the last chapter's end it appends, which `split_chapter`
  refuses.
- `delete_chapter(chapters, index)` removes that chapter's marker; the audio
  is never touched. Deleting chapter 0 pulls chapter 1's start back to 0; any
  other deletion extends the previous chapter over it. Unlike `merge_chapter`
  it is defined for the last chapter, and it says "deleted", not "merged".
- `set_chapter_bounds(chapters, index, start_ms, end_ms, *, min_part_ms=500)`
  retimes both edges at once, adjusting the neighbours so the list stays
  contiguous and ordered.

`merge_chapter`, `split_chapter` and `set_chapter_start` keep their current
behaviour and their Workbench buttons.

### Nudging a chapter marker

Setting a boundary by ear is the Workbench's whole reason to exist, and
"play, stop, press Set start to playhead, listen again" is a clumsy way to
move a marker half a second. So a fourth function:

```python
def nudge_chapter_start(
    chapters: list[Chapter], index: int, delta_ms: int, *, min_part_ms: int = 500
) -> tuple[list[Chapter], int]:
```

It returns the new list and the delta **actually** applied. This is the one
place that clamps instead of raising: a nudge is a held key, and stopping at
the wall is the behaviour a person expects when they run a marker up against
its neighbour. A press that can move nothing at all returns a zero delta, and
the UI says so once rather than every press.

Because chapters are contiguous, a chapter's start *is* the previous
chapter's end, so nudging the start is the only degree of freedom a boundary
has — moving the start moves both sides of one boundary. Chapter 0's start is
pinned at 0 and the last chapter's end is pinned at the file length; both are
correctly immovable, and every other boundary is reachable by selecting the
chapter that follows it.

**Step size, configurable.** A new `wx.Choice` beside the nudge buttons
offers 100 ms, 250 ms, 500 ms, 1 s, 2 s, 5 s and 10 s. The choice persists in
a new setting, `audio_studio_chapter_nudge_ms` (default 500, clamped 10 to
60000 through the existing `_clamp_int` path in `core/settings.py`), so the
step a person picked is the step they get next time. `settings.py` grows by
one field with its parse and constructor wiring — the accepted additive
pattern — and the field needs a documentation entry or it fails GATE-SETDOC.

**Keyboard.** Buttons alone make a repeated nudge a chore, so the chapter
list also answers Alt+Left and Alt+Right for one step, and Alt+Shift+Left and
Alt+Shift+Right for ten steps at once. Neither chord is claimed by
`wx.ListBox`. There is no menu bar on this dialog to advertise them, so the
keys are named in the buttons' help text and in the list's own help, and the
Workbench's `surface_help` entry mentions them.

**Hearing the result.** A `Hear &boundary` button plays from three seconds
before the marker to two seconds after it and then stops, so the edit can be
judged without losing the playhead. A checkbox, `Hear the boundary after
each nudge`, automates that; it defaults off, because auto-playing audio on
every keypress is exactly the kind of thing that should be opted into rather
than discovered.

**Announcing without flooding.** Each press announces the new start time
alone, short form (`12:04.500`) — not a sentence, because a sentence repeated
at key-repeat speed is unusable. The full sentence ("Chapter 3 starts
12:04.500, runs 4:12") is announced once when a run of nudges goes quiet for
600 ms. Hitting the wall announces "Cannot move further" once per run, not
per press. This stays inside GATE-13: the marker time is a change on an
unfocused control that the screen reader does not otherwise say.

### `quill/ui/audio_studio/tag_editor.py`

`TagEditorDialog(wx.Dialog)` is a `wx.Notebook` with five pages — Main,
Details, Publishing, Sort order, Cover art. Each page is its own `wx.Panel`
subclass built by iterating the `TAG_FIELDS` entries for its group, so adding
a tag is a table edit rather than a UI edit.

The dialog is pure: it takes an `AudioTags` and returns an edited copy
through `result()`. It never writes a file. The caller does the write on the
background runner, so the threading invariant holds.

The cover art page shows a text description of the current art first —
format, pixel dimensions, byte size, description — because that is what a
screen reader can use, with a thumbnail beside it for sighted users, then
Load..., Save as... and Remove buttons.

### Accessibility and z-order

This is a dense form, which is exactly where this codebase's accessibility
gates earn their keep. The design commits to all of them up front rather than
fixing them after the audit fails.

**Z-order (A11Y-Z-ORDER, `check_dialog_zorder.py`).** NVDA and JAWS associate
a static label with the control that follows it in Windows child-window
z-order, which in wxPython is creation order. The field builder therefore
creates the `wx.StaticText` and only then constructs the control, in that
order, inside the same loop iteration — it never accepts a pre-built control
as a parameter, which is the anti-pattern the gate detects. Written as
`_field_row(panel, grid, field)`, the label is created inside and the control
is created inside; nothing is passed in.

**Accessible names (GATE-A11Y-NAME, `accessible_name_audit.py`).** macOS
VoiceOver never picks up the neighbouring `StaticText`, so every control names
itself inline at its construction site with `set_accessible_name`, using the
field label with the mnemonic ampersand and trailing colon stripped. Every
new site should land in the snapshot as `named`, not `modal-hook`, so the
names are true on both platforms.

**Access keys (GATE-14, `check_access_keys.py`).** Twenty-six fields plus
buttons cannot hold unique mnemonics in one namespace. The gate scopes a
`wx.Dialog`/`wx.Frame` subclass as one window but any other class per method,
so one panel class per page gives each page its own namespace — and that
matches real Windows behaviour, since only the visible notebook page's
controls are reachable. Mnemonics are declared in `TAG_FIELDS`, and a unit
test asserts uniqueness within each page. OK, Cancel and Close carry no
mnemonic, per the house rule.

**F1 help (GATE-STUDIO-HELP).** Every control calls `SetHelpText(field.help)`
inline at its construction site, which is what `studio_help_audit.py` can
verify. The sentences carry units and defaults in the Studio's style: the
year field says what format it accepts, BPM says it is a whole number, the
sort fields say they change filing order and not what is displayed. The
dialog's own title gets an entry in `quill/core/audio_studio/surface_help.py`
so F1 opens with what the window is for.

**Dialog contract.** The dialog is shown through `_show_modal_dialog`, never
`ShowModal()` directly; `apply_modal_ids` sets the keyboard contract, and the
Close button is bound through `dialog_contract.bind_close_button`. It joins
the dialog inventory and the button-contract snapshots.

**Announcements (GATE-13).** The dialog announces only what the screen reader
does not already say: the outcome of loading or removing cover art, the
result of a chapter edit, and the outcome of a save. It never announces its
own title, never announces on focus, and never re-reads a control the reader
just read.

**Keyboard.** Notebook pages are reachable with Ctrl+Tab and Ctrl+Page
Up/Down as wx provides. Tab order follows the visual and z-order sequence
because they are constructed in that sequence. The chapter list keeps its
existing `apply_listbox_activation` behaviour, so Enter on a chapter opens
the edit dialog.

### Workbench wiring

`chapter_workbench.py` is at its GATE-11 ceiling of 945 lines, so the new
handlers live in `chapter_workbench_edits.py` as `ChapterEditsMixin`, which
`ChapterWorkbenchDialog` inherits. The Workbench itself gains one
table-driven button row — roughly 25 lines — and a `_rebaseline_2026_09_02_`
entry in `module_size_budgets.json` recording why.

New buttons: `&Add chapter...` (at the playhead or a typed time, prompting
for a title), `&Delete chapter`, `&Edit chapter...` (title, exact start,
exact end, and the Podcasting 2.0 url and image the `Chapter` dataclass
already carries), `Pre&view chapter` (plays from the chapter start and stops
at its end, using the player panel's existing tick timer rather than a second
timer), and `All &tags...`.

A second row carries the nudge controls: Nudge back, Nudge forward, the step
`wx.Choice`, Hear boundary, and the "Hear the boundary after each nudge"
checkbox. All five are disabled when the selection is chapter 0, whose start
is pinned at the beginning, with a tooltip saying why.

The mnemonics above are deliberately not pinned in this spec. The Workbench
is one window under GATE-14 and already claims roughly fifteen letters across
its existing buttons and tag fields; these nine new controls must be assigned
against the letters actually free at implementation time, and any control
that cannot get a free letter ships with no mnemonic rather than a duplicate,
per the house rule. `check_access_keys.py` is the arbiter.

The five quick tag fields stay as the fast path. Opening the full editor
seeds it from `read_tags(book.path)` overlaid with whatever is currently
typed in those five; on OK the five are written back from the editor's
result, so the two views never disagree.

Saving an MP3: `save_mp3_book` writes the chapters and the core seven, then
`write_tags` writes the full set — both are load-modify-save, so neither
clobbers the other, and `preferred_id3_version` decides the version once for
both. Saving an M4B splits on what actually changed: a tags-only edit calls
`write_tags` in place and finishes instantly, while a chapter change still
goes through `save_m4b_book_as` and then applies `write_tags` to the new
file. The Save button, disabled today for an M4B because chapter atoms
cannot be rewritten in place, becomes enabled when only tags are dirty.

`write_mp3_chapters` gains a keyword-only `v2_version: int = 3`, so today's
callers and today's on-disk result are unchanged; only a save that carries a
v2.4-only field passes 4.

### Standalone route

The Studio wizard's open-a-book page (`pages_audio.OpenBookPage`) gains an
"Edit &tags only..." button that opens `TagEditorDialog` on the chosen file
without the Workbench. This satisfies GATE-REACH: the surface is reached from
an app entry point, not only from inside another dialog.

### Shared with podHarvest

Amended 2026-09-02. This feature is now built once and used by two
repositories: QUILL and podHarvest (`S:\code\pod`). The contract is
`ALIGNMENT-audio-tags-and-chapters.md`, beside this file and identical in
both repos; it governs the vendored module, the chapter frame format, the
shared keyboard and the accessibility synthesis, and it overrides anything
here that disagrees with it.

The consequences for this design: the tag table, the readers and writers and
every chapter operation move into `audio_tags_core.py`, vendored byte-
identical into both repos behind a drift gate; `audio_tags.py` shrinks to the
adapter that cannot be shared (coded errors, the `AudioMetadata` bridge);
chapter element ids change from `chp0000` to `ch0` to match what ffmpeg — and
therefore podHarvest's installed libraries — already write; and
`set_accessible_name` adopts podHarvest's stronger implementation, which
attaches a real `wx.Accessible` rather than relying on `SetName` alone.

### Which products this reaches

`quill/apps/studio.py` — the standalone QUILL Audio Studio — vendors and
drives the **same** `quill/ui/audio_studio` package QUILL itself uses. Every
change above therefore lands in both products from one implementation. The
standalone app needs two things the in-app build does not: menu routes, since
its front door is a menu bar rather than a wizard (a Studio menu item and a
library-tree context-menu entry, both with accelerators that clear the
menu-accelerator gate), and a packaging fix.

The packaging fix is not cosmetic. `standalone/studio/pyproject.toml`
declares `quill[ui]`, and mutagen lives in the `mp3` extra — so the
standalone Studio does not declare the library its whole MP3 tag and chapter
path already runs on. Worse, every mutagen import in this codebase is lazy
and inside a function, which is exactly the shape PyInstaller's import tracer
cannot follow; `quill-audio-studio.spec` already hand-collects PyNaCl and
yt-dlp for that reason and does not collect mutagen. Both are fixed here, and
the fix is verified against a **built executable**, because no unit test can
prove it.

QUILL Cast is deliberately out of scope. Its chapters
(`quill/core/podcasts/chapter_edits.py`) are inferred marks carrying a
confidence and a source, where an edit means "this is no longer a guess" —
a different domain with different invariants. The Media Player and Quill
Radio consume chapters but do not edit them.

## Error handling

- A file whose tags cannot be read opens the editor with empty fields and
  announces why, rather than refusing — the user may be tagging a file that
  has no tag block yet.
- A write failure surfaces through the Workbench's existing `_error` path and
  leaves the file untouched; mutagen writes through a temporary file, so a
  failed save cannot truncate the original.
- A cover image that is not JPEG or PNG, or is over 8 MB, is rejected at load
  time with a message naming the limit.
- Chapter edits that would leave a sliver shorter than the minimum, or that
  fall outside the file, raise `ChapterEditError` and leave the list
  unchanged.
- mutagen is the `quill[mp3]` extra and is imported lazily, so these modules
  load without it and the failure is one clear sentence.

## Testing

- `tests/unit/core/speech/test_audio_tags.py` — every field round-trips
  through write-then-read on a generated silent MP3 (the existing
  `silent_mp3` fixture pattern) and on a generated MP4; an empty value
  deletes the frame; unmapped fields are skipped on MP4 without error; cover
  art add, replace, remove and save-out; a non-image file is rejected;
  `preferred_id3_version` returns 3 for a plain tag set and 4 once a sort
  field is set; writing tags leaves existing CHAP/CTOC frames intact.
- `tests/unit/core/speech/test_chapters.py` — add at the playhead, add past
  the end (append), add too close to a boundary; delete first, middle and
  last; delete the only chapter; set bounds valid, inverted, and overlapping
  a neighbour; nudge forward and back by a step, nudge clamped at each
  neighbour, nudge that can move nothing returning a zero delta, and nudge
  refused on chapter 0.
- `tests/unit/core/test_settings.py` — `audio_studio_chapter_nudge_ms`
  round-trips, clamps out-of-range values, and falls back to 500 on garbage.
- `tests/unit/ui/test_tag_editor_dialog.py` — the dialog builds; every
  `TAG_FIELDS` entry has a control; mnemonics are unique within each page;
  every control has help text and an inline accessible name; the label for
  each field is created before its control (z-order); values round-trip in
  and out.
- Regenerated gate snapshots: `module_size_budgets.json`,
  `surface_reachability.json`, `studio_help_inventory.json`,
  `accessible_name_inventory.json`, the dialog inventory, and
  `docs/f1-help-reference.md`.
- Whole-gate check: `python -m quill.tools.platform_report`.

## Out of scope

Raw arbitrary-frame editing, FLAC/OGG/WAV, batch tagging across a folder,
online tag lookup (MusicBrainz and friends), chapter-level embedded images in
CHAP sub-frames, and any change to the batch document-to-speech pipeline.

Snapping a nudged marker to the nearest detected silence is the obvious next
step — `quill/core/speech/silence.py` already finds them for the propose-from-
silences button — but it is a separate feature with its own tuning, and it is
not in this one.
