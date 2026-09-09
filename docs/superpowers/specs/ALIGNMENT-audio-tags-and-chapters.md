# Alignment: audio tags and chapters across QUILL Audio Studio and podHarvest

Date: 2026-09-02
Status: implemented and verified in both repos (2026-09-02)
Governs: `S:\quill` (QUILL Audio Studio) and `S:\code\pod` (podHarvest)

This document is the contract between two separate repositories. A copy lives
in each; they must stay identical. It exists because both apps now edit the
same thing — an audio file's tags and chapter markers — and a user who moves
between them should find the same fields, the same operations, the same keys
and the same words, and should be able to edit a file in either app without
the other noticing.

## The three decisions

**Sharing.** One pure-Python module, vendored byte-identical into both repos,
with a drift gate in each. No new package, no cross-repo install, no version
skew. QUILL already vendors ChapterForge logic this way; this follows the
same pattern.

**Accessibility.** Both apps get both approaches. Neither loses anything.

**Parity.** Full: all 26 tag fields, cover art, and every chapter operation,
in both apps.

## The shared modules

**Two of them now**, on the same terms: identical bytes in both repos, a
SHA-256 drift test on each side, no import from either host package.

`reuse_core.py` came second (2026-09-03) and holds the *do we already have
this?* rules: the transcript-format ranking, the WebVTT/SRT/JSON transcript
readers, and the show-notes chapter parser. It went in when podHarvest needed
them and QUILL Cast already had them, worked out against real feeds. Rather
than copy, **Cast now delegates**: `show_note_chapters.py` went from 231 lines
to 109, `transcript_choice.py` from 90 to 76, and the text parsers moved out of
`transcripts.py`. Cast's own 749 tests passing against the shared code is the
proof the move was faithful.

`audio_tags_core.py` — identical bytes at
`quill/core/speech/audio_tags_core.py` and `podharvest/audio_tags_core.py`.

Pure Python, wx-free, standard library only, with mutagen imported **lazily
inside functions** so the module loads without it. It carries no import from
either host package — that is what makes byte-identity possible.

It owns:

- `TagField`, `TAG_FIELDS` (26 entries), `GROUPS`, `fields_in`, `field_for`
- `AudioTags`, `CoverArt`, `MAX_COVER_BYTES`, `load_cover`,
  `cover_extension`, `describe_cover`
- `read_tags`, `write_tags`, `preferred_id3_version`
- `Chapter`, and every chapter operation: `add_chapter`, `delete_chapter`,
  `merge_chapter`, `split_chapter`, `set_chapter_start`, `set_chapter_bounds`,
  `nudge_chapter_start`, `clamp_chapters`, `NUDGE_STEPS_MS`
- `write_mp3_chapters`, `read_mp3_chapters`
- `format_time_precise`, `parse_time`
- Plain exception classes: `AudioTagError`, and `TagReadError`,
  `TagWriteError`, `ChapterEditError` beneath it

### Errors at the boundary

QUILL requires every top-level exception in `quill/core` to subclass
`CodedError` with a unique `QUILL-<DOMAIN>-<SUBSYSTEM>-<REASON>` code
(GATE-EC), and forbids the `class X(Exception, CodedError)` MRO. The shared
module cannot import `CodedError`, so it raises its own plain classes and
**QUILL retranslates at the adapter boundary**:

```python
class ChapterEditError(CodedError):
    code = "QUILL-SPEECH-CHAPTER-EDIT"

def merge_chapter(chapters: list[Chapter], index: int) -> list[Chapter]:
    try:
        return _core.merge_chapter(chapters, index)
    except _core.ChapterEditError as exc:
        raise ChapterEditError(str(exc)) from exc
```

podHarvest uses the shared classes directly — it has no coded-error scheme.
The retranslation is one decorator in QUILL's adapter, not seven try blocks.

### The drift gate

Each repo carries a test that hashes its copy and compares against a constant
recorded in this document's companion, `audio_tags_core.sha256`, kept beside
the module in both repos:

```python
def test_shared_module_has_not_drifted() -> None:
    """audio_tags_core.py is vendored; edit it in both repos or neither."""
    digest = hashlib.sha256(MODULE_PATH.read_bytes()).hexdigest()
    assert digest == EXPECTED, (
        "audio_tags_core.py changed. Copy the new file into the other repo "
        "and update the digest in both, or the two apps have silently "
        "diverged."
    )
```

Changing the shared module is therefore always a two-repo change. That is the
point: the gate makes silent divergence impossible, and makes deliberate
divergence loud.

## What "identical output" means

Both apps must write chapter frames a byte-comparison cannot tell apart.
Before this work they did not, and the differences were small but real.

| | podHarvest before | QUILL before | Aligned |
| --- | --- | --- | --- |
| Writer | ffmpeg re-mux | mutagen, in place | mutagen, in place |
| Element ids | `ch0`, `ch1` | `chp0000`, `chp0001` | `ch0`, `ch1` |
| TOC id | `toc` | `toc` | `toc` |
| ID3 version | 2.4 always | 2.3 always | adaptive: 2.3, or 2.4 once a v2.4-only field is set -- and a chapter write inherits it rather than forcing one |
| Whole file rewritten | yes | no | no |

Verified against real ffmpeg on 2026-09-02: podHarvest's existing writer does
produce proper ID3v2.4 `CHAP` + `CTOC` frames that mutagen reads back
correctly — it works, it is simply not identical to QUILL's.

**Element ids become `ch<N>`.** QUILL changes; podHarvest does not. Element
ids are opaque handles, so no player is affected, but podHarvest already has
libraries of harvested episodes carrying `ch0`-style ids and ffmpeg is the
de-facto convention. Changing the app with no installed base is the cheaper
side of the trade.

**The chapter write follows the file's ID3 version.** Found by running the
two apps against one file rather than by reading the code: saving an ID3 block
is all-or-nothing, so writing chapters at a fixed 2.3 onto a file whose tags
had just been written at 2.4 quietly demoted the whole block and stranded the
sort fields. `write_mp3_chapters` therefore takes `v2_version: int | None` and,
left unset, reads what is on disk and asks `preferred_id3_version`. Callers no
longer have to write tags and chapters in a particular order to keep what they
wrote -- which is exactly the kind of thing neither app should have to
remember.

**podHarvest stops re-muxing MP3s to add chapters.** This is the change that
matters most to podHarvest on its own terms. `embed_chapters` currently
copies the entire episode through ffmpeg to add a hundred bytes of chapter
frames; the shared mutagen writer edits the tag block in place. A 60 MB
episode goes from a full file copy to instant, and the temp-file dance that
protects against a truncated write is no longer needed for MP3 at all. The
ffmpeg re-mux stays for `.ogg`, `.opus` and the MP4 family, which mutagen
cannot chapter in place.

## Accessibility: both approaches, in both apps

The two codebases start from positions that look contradictory. They are not,
once the reasons are read rather than the conclusions.

**podHarvest** avoids `&` mnemonics, because `IsDialogMessage` scopes its
mnemonic search to the enclosing `wx.StaticBox` — so a mnemonic is
unreachable from a field in a different box — and because mnemonics match
case-insensitively, so `&Start` and `&speakers` collide. It names controls
with a `_Named` `wx.Accessible` subclass rather than `SetName`.

**QUILL** mandates a unique mnemonic per window (GATE-14) and names controls
with `set_accessible_name`, which calls `SetName` and reaches a `SpinCtrl`'s
inner edit.

The synthesis, which costs neither app anything:

1. **The new dialogs use `FlexGridSizer` rows, not `wx.StaticBox` groups.**
   podHarvest's mnemonic-scoping objection is a property of StaticBox
   containment; without the boxes it does not arise. Mnemonics work in both.
2. **Mnemonics are unique case-insensitively within a page**, which is
   already what GATE-14 enforces and exactly answers podHarvest's
   `&Start`/`&speakers` collision.
3. **Both apps adopt podHarvest's `_Named` `wx.Accessible` helper** in
   addition to `SetName`. It is the stronger of the two implementations: it
   sets a real accessible name rather than relying on the platform to derive
   one, and it costs one small class. QUILL keeps `set_accessible_name` as
   the call site so its accessible-name audit still classifies each site as
   `named`.
4. **Both apps get an accelerator table** for the chapter operations, so
   nudging and previewing are reachable without hunting for a button.
5. **Both apps create the label before the control it labels.** Both
   codebases already believe this; QUILL has a gate for it
   (`check_dialog_zorder.py`) and podHarvest states it in its GUI docstring.
   The shared dialog honours it by construction.

## The shared keyboard

Identical in both apps. podHarvest binds them in its accelerator table;
QUILL binds them on the chapter list and names them in help text, since the
Workbench has no menu bar to advertise them.

| Key | Action |
| --- | --- |
| Alt+Left / Alt+Right | Nudge the selected chapter's start by one step |
| Alt+Shift+Left / Alt+Shift+Right | Nudge by ten steps |
| Enter (on the chapter list) | Edit the selected chapter |
| Ctrl+Tab / Ctrl+Shift+Tab | Move between tag editor pages |

## The shared wording

The help sentence for each tag field lives in `TAG_FIELDS`, so both apps read
the same words by construction. Announcements follow the same two rules in
both:

- A nudge speaks the bare new time (`0:00:09.500`), never a sentence: it runs
  at key-repeat speed, and a sentence repeated ten times a second is noise.
  The full sentence follows once the run goes quiet for 600 ms.
- Hitting the wall says "Cannot move further." once per run, not per press.

## Per-repo work

### QUILL (`S:\quill`)

Follows `docs/superpowers/plans/2026-09-02-audio-tag-editor.md`, amended:

- Tasks 1–7 build their logic **in `audio_tags_core.py`**, not in
  `audio_tags.py`/`chapters.py` directly. `audio_tags.py` becomes the thin
  adapter (coded errors, the `AudioMetadata` bridge), and `chapters.py`
  re-exports the shared operations through the same adapter so all eleven
  existing importers keep working unchanged.
- `write_mp3_chapters` changes its element-id format from `chp{index:04d}` to
  `ch{index}`. Existing files are unaffected — the reader sorts by start
  time and does not care about ids.
- The Tag Editor and the chapter-details dialog adopt the `_Named`
  `wx.Accessible` helper alongside `set_accessible_name`.
- A drift test for the vendored module.

### podHarvest (`S:\code\pod`)

Follows `docs/plans/2026-09-02-tag-and-chapter-editor.md` in this repo. In
outline:

- Vendor `audio_tags_core.py` and add the drift test.
- Add `mutagen` to the **`gui` extra only**. podHarvest's stated promise is
  that its *CLI* runs on the standard library alone, with the desktop GUI as
  the one exception; tag editing is a GUI feature, so the promise is kept
  verbatim. The CLI never imports mutagen.
- Rewrite `chapters.embed_chapters` to use the shared mutagen writer for MP3
  and keep the ffmpeg re-mux for the other containers, preserving its current
  signature and its never-raises contract so the harvest pipeline is
  unchanged.
- Add a Tag and Chapter Editor dialog, opened from the Episodes list, with
  the same five pages, the same fields, the same chapter operations and the
  same keys as QUILL's.

## What podHarvest took from Cast, and what it did not

Cast is a subscription and listening app; podHarvest is an archiver. The line
between them is the one worth holding, so what came across is what serves an
archive:

* the transcript-format ranking and readers, and the show-notes chapter parser
  (shared, above);
* the **media-health** pattern — one boolean, derived text, silent when
  healthy, never silent when asked — because every FFmpeg feature in either app
  fails by producing a plausible result;
* the **F1 help** contract: window purpose, then the focused control, never
  empty, with an audit that fails the build on a control nobody wrote a
  sentence for.

What deliberately did not: subscriptions, an inbox, a play queue, retention and
expiry, listening statistics. Those make a podcatcher, and podHarvest is not
one.

## Out of scope

QUILL Cast's inferred chapters (`quill/core/podcasts/chapter_edits.py`) carry
a confidence and a source, where an edit means "this is no longer a guess" —
a different domain with different invariants. FLAC, OGG and Opus tag editing.
Batch tagging across a folder. Online tag lookup.

## Verified

Run on 2026-09-02, loading both copies of the module side by side as two
distinct module objects and passing one file between them:

- QUILL writes all 26 fields plus cover art; podHarvest reads every one back
  unchanged.
- podHarvest nudges a chapter marker and rewrites the chapter frames; QUILL
  reads the new start, and every one of the 26 tag fields survives that
  rewrite.
- Element ids read back as `ch0`, `ch1` with a `toc`, from both sides.
- The file sits at ID3v2.4 because a sort field is set, and stays there
  through the other app's chapter write.

The last of those is what caught the version-ordering bug above. It is worth
re-running, by hand, after any change to the shared module.
