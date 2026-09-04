# Full Audio Tag Editor and Complete Chapter Editing — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the QUILL Audio Studio's Chapter Workbench into a full MP3 tag editor with complete chapter editing — add, delete, retime, nudge by a configurable step, preview — while keeping every accessibility and architecture gate green.

**Architecture:** A new wx-free core module (`quill/core/speech/audio_tags.py`) owns a table of 26 tag fields and reads/writes them through mutagen — ID3 frames for MP3, MP4 atoms for M4A/M4B. `quill/core/speech/chapters.py` gains four pure functions for add, delete, set-bounds and nudge. Two new UI modules present them: a notebook `TagEditorDialog` built by iterating the field table, and a `ChapterEditsMixin` holding the new Workbench handlers so `chapter_workbench.py` stays near its size budget.

**Tech Stack:** Python 3.13, wxPython, mutagen (the `quill[mp3]` extra, imported lazily), pytest.

## Amendment, 2026-09-02: this work is now shared with podHarvest

**Read `docs/superpowers/specs/ALIGNMENT-audio-tags-and-chapters.md` before
starting.** It is the contract between this repository and `S:\code\pod`
(podHarvest), and it overrides anything here that contradicts it. Three
changes to the plan below follow from it:

**1. The logic goes in a vendored module.** Tasks 1–7 build their code in a
new `quill/core/speech/audio_tags_core.py` — byte-identical to
`podharvest/audio_tags_core.py`, importing nothing from `quill`, with mutagen
imported lazily inside functions. `quill/core/speech/audio_tags.py` becomes a
thin adapter holding only what cannot be shared: the `CodedError` subclasses
(GATE-EC forbids the `class X(Exception, CodedError)` MRO, so the shared
module's plain exceptions are **retranslated** at the boundary) and the
`AudioMetadata` bridge. `chapters.py` keeps its quill-only pieces
(`compute_chapters`, `ChapterSection`, `ChapterSettings`) and re-exports the
shared operations through the same adapter, so all eleven existing importers
of `quill.core.speech.chapters` keep working unchanged.

Add `quill/core/speech/audio_tags_core.sha256` and a drift test mirroring
podHarvest's, so editing one copy without the other fails the build in both
repos.

**2. Chapter element ids change from `chp0000` to `ch0`.** podHarvest's
existing writer (ffmpeg) produces `ch0`-style ids, verified against real
ffmpeg on 2026-09-02, and it has installed libraries of episodes carrying
them. Element ids are opaque handles that no player interprets, so changing
quill's side is free; changing podHarvest's is not. In
`write_mp3_chapters`, `element_id = f"chp{chapter.index:04d}"` becomes
`element_id = f"ch{chapter.index}"`. The TOC id stays `toc`.

**3. Accessibility gains podHarvest's helper.** podHarvest's
`set_accessible_name` has the *same signature* as quill's but a stronger
implementation: it sets `SetName` **and** attaches a `wx.Accessible` subclass
holding a strong reference, because `SetName` alone reaches neither MSAA/UIA,
AT-SPI nor NSAccessibility. Adopt that implementation inside
`quill/ui/audio_studio/pages_base.py:set_accessible_name`, keeping quill's
existing `SpinCtrl` inner-edit walk. Every call site in this plan is
unchanged, and the accessible-name audit still classifies each as `named`.

## Global Constraints

- `quill/core` and `quill/io` are **wx-free** and strict-typed. `mypy quill\core quill\io` must pass. Never run mypy unscoped.
- mutagen is an optional extra. **Import it lazily inside functions**, never at module top level, and raise a one-sentence speakable error when it is missing.
- Every new top-level exception class in `quill/core` must subclass `CodedError` and declare a unique `code = "QUILL-<DOMAIN>-<SUBSYSTEM>-<REASON>"` (GATE-EC). Shape is `class X(CodedError):`, never `class X(Exception, CodedError):`.
- All modal dialogs go through `_show_modal_dialog` / `show_modal_dialog`, never `ShowModal()` directly. `apply_modal_ids` sets the keyboard contract; a Close button is bound via `dialog_contract.bind_close_button`.
- **Z-order (A11Y-Z-ORDER):** create the `wx.StaticText` label *before* the control it labels, in the same scope. Never pass an already-constructed control into a row helper — that is the exact anti-pattern `check_dialog_zorder.py` detects.
- **Accessible names (GATE-A11Y-NAME):** every labelable control calls `set_accessible_name(ctrl, name)` inline at its construction site.
- **F1 help (GATE-STUDIO-HELP):** every control calls `SetHelpText(...)` inline at its construction site. Help set anywhere else does not count.
- **Access keys (GATE-14):** no two controls in one window may claim the same `&` mnemonic. A `wx.Dialog`/`wx.Frame` subclass is one window; any other class is scoped per method. OK, Cancel and Close carry **no** mnemonic. A control that cannot get a free letter ships with none rather than a duplicate.
- **Announcements (GATE-13):** announce only what the screen reader does not already say. Never announce a window title, never announce inside an `EVT_SET_FOCUS` handler.
- **Threading:** the UI thread owns all wx widgets. File writes run on the caller-provided background runner; cross-thread UI updates go through `wx.CallAfter`.
- `chapter_workbench.py` is at its GATE-11 ceiling of **945 lines**. New logic goes in new modules. Any growth needs a `_rebaseline_2026_09_02_` entry in `quill/tools/module_size_budgets.json` explaining why.
- **Commits:** this repository's owner does not want commits created unless explicitly asked. Each task's final step says "commit"; if commits have not been authorised for this run, stage the files and report instead.

---

## File Structure

| File | State | Responsibility |
| --- | --- | --- |
| `quill/core/speech/audio_tags_core.py` | create (vendored) | `TagField` table, `AudioTags`, `CoverArt`, read/write for MP3 and MP4, `Chapter`, every chapter operation. Byte-identical to podHarvest's copy |
| `quill/core/speech/audio_tags_core.sha256` | create | the digest the drift test checks |
| `quill/core/speech/audio_tags.py` | create | the quill adapter: coded errors retranslated, `AudioMetadata` bridge |
| `quill/core/speech/chapters.py` | modify | re-export the shared operations through the adapter; keep `compute_chapters`, `ChapterSection`, `ChapterSettings`; element ids become `ch<N>` |
| `quill/core/speech/book_file.py` | modify | `save_mp3_book` uses the shared ID3 version |
| `quill/core/settings.py` | modify | `audio_studio_chapter_nudge_ms` |
| `quill/core/audio_studio/surface_help.py` | modify | purpose entries for the two new windows |
| `quill/ui/audio_studio/tag_editor.py` | create | `TagEditorDialog` + one `wx.Panel` subclass per notebook page |
| `quill/ui/audio_studio/chapter_workbench_edits.py` | create | `ChapterEditsMixin` — add/delete/edit/preview/nudge handlers, `ChapterDetailsDialog` |
| `quill/ui/audio_studio/chapter_workbench.py` | modify | two table-driven button rows, tag-editor launch, split save path |
| `quill/ui/audio_studio/pages_audio.py` | modify | standalone "Edit tags only..." route |
| `tests/unit/core/speech/test_audio_tags.py` | create | field table, MP3 round-trip, MP4 round-trip, cover art |
| `tests/unit/core/speech/test_chapters.py` | modify | add/delete/bounds/nudge cases |
| `tests/unit/ui/test_tag_editor_dialog.py` | create | dialog build, a11y invariants, value round-trip |
| `tests/unit/ui/test_chapter_workbench_edits.py` | create | mixin handlers against a fake player and list |

---

### Task 1: The tag field table and the `AudioTags` container

**Files:**
- Create: `quill/core/speech/audio_tags.py`
- Test: `tests/unit/core/speech/test_audio_tags.py`

**Interfaces:**
- Consumes: `quill.core.error_codes.CodedError`
- Produces: `TagField`, `TAG_FIELDS: tuple[TagField, ...]`, `GROUPS: tuple[tuple[str, str], ...]`, `fields_in(group: str) -> tuple[TagField, ...]`, `AudioTags` (with `values: dict[str, str]`, `cover: CoverArt | None`, `get(key) -> str`, `set(key, value) -> None`, `copy() -> AudioTags`), `CoverArt`, `TagReadError`, `TagWriteError`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/core/speech/test_audio_tags.py`:

```python
"""Tests for the full audio tag model (field table, container, read/write)."""

from __future__ import annotations

import pytest

from quill.core.speech.audio_tags import (
    GROUPS,
    TAG_FIELDS,
    AudioTags,
    fields_in,
)


def test_field_keys_are_unique() -> None:
    keys = [f.key for f in TAG_FIELDS]
    assert len(keys) == len(set(keys))


def test_every_field_belongs_to_a_declared_group() -> None:
    declared = {key for key, _label in GROUPS}
    assert {f.group for f in TAG_FIELDS} <= declared


def test_every_field_has_an_id3_frame_and_a_help_sentence() -> None:
    for field in TAG_FIELDS:
        assert field.id3, f"{field.key} has no ID3 frame"
        assert field.help.endswith("."), f"{field.key} help is not a sentence"
        assert field.kind in {"text", "number", "pair", "multiline", "bool"}


def test_id3_frames_are_unique() -> None:
    frames = [f.id3 for f in TAG_FIELDS]
    assert len(frames) == len(set(frames))


def test_mnemonics_are_unique_within_each_group() -> None:
    for group, _label in GROUPS:
        letters = [
            f.label[f.label.index("&") + 1].lower()
            for f in fields_in(group)
            if "&" in f.label
        ]
        assert len(letters) == len(set(letters)), f"duplicate mnemonic in {group}"


def test_fields_in_returns_only_that_group() -> None:
    assert all(f.group == "sort" for f in fields_in("sort"))
    assert fields_in("nonexistent") == ()


def test_audio_tags_get_set_copy() -> None:
    tags = AudioTags()
    assert tags.get("album") == ""
    tags.set("album", "  My Book  ")
    assert tags.get("album") == "My Book"
    clone = tags.copy()
    clone.set("album", "Other")
    assert tags.get("album") == "My Book"


def test_audio_tags_rejects_an_unknown_key() -> None:
    with pytest.raises(KeyError):
        AudioTags().set("not_a_tag", "x")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/unit/core/speech/test_audio_tags.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'quill.core.speech.audio_tags'`

- [ ] **Step 3: Write the implementation**

Create `quill/core/speech/audio_tags.py`:

```python
"""The full tag model for an audio file — every field the Tag Editor edits.

One table, :data:`TAG_FIELDS`, is the single source of truth: the dialog
builds itself from it, the MP3 and MP4 readers and writers map through it,
and the tests iterate it. Adding a tag is a table edit, not a UI edit.

MP3 tags are ID3 frames; M4A/M4B/MP4 tags are MP4 atoms, including Apple's
``----:com.apple.iTunes:NAME`` freeform atoms for the fields MP4 has no
standard home for. A field whose ``mp4`` is empty is simply skipped on an MP4
file rather than guessed at.

wx-free, strict-typed. mutagen (the ``quill[mp3]`` extra) is imported lazily
inside the read/write functions so this module loads without it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from quill.core.error_codes import CodedError


class TagReadError(CodedError):
    """The file's tags could not be read; message is speakable."""

    code = "QUILL-SPEECH-TAG-READ"


class TagWriteError(CodedError):
    """The file's tags could not be written; message is speakable."""

    code = "QUILL-SPEECH-TAG-WRITE"


@dataclass(frozen=True, slots=True)
class TagField:
    """One editable tag: how it is shown, and where it lives in each format.

    ``label`` carries its own ``&`` mnemonic; mnemonics are unique within a
    group because each group is its own notebook page, and only the visible
    page's controls are reachable (GATE-14 scopes a non-dialog class per
    method, which matches that reality).

    ``kind`` drives the control the dialog builds: ``text`` a one-line field,
    ``multiline`` a multi-line field, ``number`` a digits-only field,
    ``pair`` two number fields joined as ``"n/m"`` in one value, and ``bool``
    a checkbox stored as ``"1"`` or ``""``.
    """

    key: str
    label: str
    group: str
    kind: str
    id3: str
    mp4: str
    help: str


#: Notebook page order and page titles.
GROUPS: tuple[tuple[str, str], ...] = (
    ("main", "Main"),
    ("details", "Details"),
    ("publishing", "Publishing"),
    ("sort", "Sort order"),
)

TAG_FIELDS: tuple[TagField, ...] = (
    # -- main -----------------------------------------------------------------
    TagField(
        "title", "&Title:", "main", "text", "TIT2", "\xa9nam",
        "The track or book title. Most players show this as the name of what "
        "is playing.",
    ),
    TagField(
        "subtitle", "S&ubtitle:", "main", "text", "TIT3",
        "----:com.apple.iTunes:SUBTITLE",
        "A secondary title, such as a book's subtitle or an episode's strap "
        "line. Few players show it; it is stored for the ones that do.",
    ),
    TagField(
        "artist", "&Artist:", "main", "text", "TPE1", "\xa9ART",
        "The performing artist. For an audiobook this is conventionally the "
        "author.",
    ),
    TagField(
        "album", "Al&bum:", "main", "text", "TALB", "\xa9alb",
        "The album. For an audiobook this is the book's title, and it is what "
        "groups every file of a multi-file book together.",
    ),
    TagField(
        "album_artist", "Album a&rtist:", "main", "text", "TPE2", "aART",
        "The artist the album is filed under. For an audiobook this is "
        "conventionally the narrator.",
    ),
    TagField(
        "track", "Trac&k (number of total):", "main", "pair", "TRCK", "trkn",
        "This file's position in the album and how many there are, written as "
        "number of total. Leave the total blank if you do not know it.",
    ),
    TagField(
        "disc", "&Disc (number of total):", "main", "pair", "TPOS", "disk",
        "This file's disc number and how many discs there are. Leave both "
        "blank for a single-disc release.",
    ),
    TagField(
        "genre", "&Genre:", "main", "text", "TCON", "\xa9gen",
        "The genre. Audiobooks usually say Audiobook, which is what makes "
        "some players file them separately from music.",
    ),
    TagField(
        "year", "&Year:", "main", "text", "TDRC", "\xa9day",
        "The release date, as a four-digit year, or a fuller ISO date such as "
        "2026-09-02. Leave blank to omit it.",
    ),
    # -- details --------------------------------------------------------------
    TagField(
        "original_date", "&Original release date:", "details", "text", "TDOR",
        "----:com.apple.iTunes:ORIGINALDATE",
        "When the work was first released, if this file is a reissue. A "
        "four-digit year or a fuller ISO date.",
    ),
    TagField(
        "comment", "Co&mment:", "details", "multiline", "COMM", "\xa9cmt",
        "A free-text comment. Players that show notes show this one.",
    ),
    TagField(
        "lyrics", "&Lyrics or transcript:", "details", "multiline", "USLT",
        "\xa9lyr",
        "Unsynchronised lyrics, or any long text you want carried with the "
        "file, such as a transcript.",
    ),
    TagField(
        "grouping", "&Grouping:", "details", "text", "TIT1", "\xa9grp",
        "The work or series this belongs to. Apple players group by this "
        "field above the album.",
    ),
    TagField(
        "language", "L&anguage:", "details", "text", "TLAN",
        "----:com.apple.iTunes:LANGUAGE",
        "The spoken or sung language, conventionally a three-letter code such "
        "as eng or fra.",
    ),
    TagField(
        "bpm", "&Beats per minute:", "details", "number", "TBPM", "tmpo",
        "The tempo, as a whole number. Rarely meaningful for speech; leave "
        "blank.",
    ),
    TagField(
        "compilation", "&Part of a compilation", "details", "bool", "TCMP",
        "cpil",
        "Marks the album as a collection by several artists, which stops "
        "Apple players from filing every track under a different artist.",
    ),
    # -- publishing -----------------------------------------------------------
    TagField(
        "composer", "&Composer:", "publishing", "text", "TCOM", "\xa9wrt",
        "The composer or writer.",
    ),
    TagField(
        "conductor", "Con&ductor:", "publishing", "text", "TPE3",
        "----:com.apple.iTunes:CONDUCTOR",
        "The conductor. For spoken audio this field is often used for the "
        "director or producer.",
    ),
    TagField(
        "publisher", "&Publisher:", "publishing", "text", "TPUB",
        "----:com.apple.iTunes:PUBLISHER",
        "The publisher or label that released this.",
    ),
    TagField(
        "copyright", "Cop&yright:", "publishing", "text", "TCOP", "cprt",
        "The copyright line, such as 2026 Example Press.",
    ),
    TagField(
        "encoded_by", "&Encoded by:", "publishing", "text", "TENC",
        "----:com.apple.iTunes:ENCODEDBY",
        "Who or what produced this file. QUILL leaves whatever is already "
        "here alone unless you change it.",
    ),
    TagField(
        "isrc", "&ISRC:", "publishing", "text", "TSRC",
        "----:com.apple.iTunes:ISRC",
        "The International Standard Recording Code, a twelve-character "
        "identifier issued to commercial recordings.",
    ),
    # -- sort -----------------------------------------------------------------
    TagField(
        "title_sort", "Sort &title:", "sort", "text", "TSOT", "sonm",
        "How the title files in a sorted list, without changing what is "
        "displayed. Storing this needs ID3 version 2.4, which QUILL switches "
        "to automatically.",
    ),
    TagField(
        "artist_sort", "Sort &artist:", "sort", "text", "TSOP", "soar",
        "How the artist files in a sorted list -- Austen, Jane for Jane "
        "Austen. Displayed text is unchanged.",
    ),
    TagField(
        "album_sort", "Sort al&bum:", "sort", "text", "TSOA", "soal",
        "How the album files in a sorted list. Displayed text is unchanged.",
    ),
    TagField(
        "album_artist_sort", "Sort album a&rtist:", "sort", "text", "TSO2",
        "soaa",
        "How the album artist files in a sorted list. Displayed text is "
        "unchanged.",
    ),
)

#: Fields ID3 version 2.3 has no home for. Writing any of these forces v2.4.
V24_ONLY_FRAMES: frozenset[str] = frozenset({
    "TDRC", "TDOR", "TSOT", "TSOP", "TSOA", "TSO2",
})

_BY_KEY: dict[str, TagField] = {f.key: f for f in TAG_FIELDS}


def fields_in(group: str) -> tuple[TagField, ...]:
    """Every field in *group*, in table order. Unknown group -> empty."""
    return tuple(f for f in TAG_FIELDS if f.group == group)


def field_for(key: str) -> TagField:
    """The field named *key*. Raises ``KeyError`` for an unknown key."""
    return _BY_KEY[key]


@dataclass(slots=True)
class CoverArt:
    """An embedded cover image: the bytes, plus how to describe and file it."""

    data: bytes
    mime: str = "image/jpeg"
    description: str = ""
    #: ID3 APIC picture type; 3 is "cover (front)".
    picture_type: int = 3


@dataclass(slots=True)
class AudioTags:
    """Every editable tag of one file. Empty string means "not present"."""

    values: dict[str, str] = field(default_factory=dict)
    cover: CoverArt | None = None

    def get(self, key: str) -> str:
        """This tag's value, or "" when it is absent. Unknown key -> KeyError."""
        if key not in _BY_KEY:
            raise KeyError(key)
        return self.values.get(key, "")

    def set(self, key: str, value: str) -> None:
        """Set (or, with an empty value, clear) this tag. Values are stripped."""
        if key not in _BY_KEY:
            raise KeyError(key)
        text = str(value).strip()
        if text:
            self.values[key] = text
        else:
            self.values.pop(key, None)

    def copy(self) -> AudioTags:
        """An independent copy — editing the copy never touches the original."""
        cover = None
        if self.cover is not None:
            cover = CoverArt(
                data=self.cover.data,
                mime=self.cover.mime,
                description=self.cover.description,
                picture_type=self.cover.picture_type,
            )
        return AudioTags(values=dict(self.values), cover=cover)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/unit/core/speech/test_audio_tags.py -q`
Expected: PASS, 8 tests.

- [ ] **Step 5: Type-check and lint**

Run: `mypy quill\core quill\io` — Expected: no new errors.
Run: `ruff check quill/core/speech/audio_tags.py tests/unit/core/speech/test_audio_tags.py && ruff format --check quill/core/speech/audio_tags.py` — Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add quill/core/speech/audio_tags.py tests/unit/core/speech/test_audio_tags.py
git commit -m "feat(speech): add the full audio tag field table and container"
```

---

### Task 2: MP3 read and write, and the adaptive ID3 version

**Files:**
- Modify: `quill/core/speech/audio_tags.py`
- Modify: `quill/core/speech/chapters.py` (`write_mp3_chapters` gains `v2_version`)
- Test: `tests/unit/core/speech/test_audio_tags.py`

**Interfaces:**
- Consumes: `TAG_FIELDS`, `AudioTags`, `V24_ONLY_FRAMES`, `field_for` from Task 1
- Produces: `read_tags(path: Path) -> AudioTags`, `write_tags(path: Path, tags: AudioTags) -> None`, `preferred_id3_version(tags: AudioTags) -> int`; `write_mp3_chapters(path, chapters, *, toc_title="Chapters", v2_version: int = 3)`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/core/speech/test_audio_tags.py`:

```python
from pathlib import Path  # noqa: E402

mutagen = pytest.importorskip("mutagen")

from quill.core.speech.audio_tags import (  # noqa: E402
    CoverArt,
    preferred_id3_version,
    read_tags,
    write_tags,
)
from quill.core.speech.chapters import (  # noqa: E402
    Chapter,
    read_mp3_chapters,
    write_mp3_chapters,
)


@pytest.fixture
def silent_mp3(tmp_path: Path) -> Path:
    """A minimal valid MP3 (silent frames) to tag in place."""
    path = tmp_path / "tagged.mp3"
    frame = b"\xff\xfb\x90\x00" + b"\x00" * 413
    path.write_bytes(frame * 4)
    return path


def _every_text_value() -> AudioTags:
    tags = AudioTags()
    for f in TAG_FIELDS:
        if f.kind in {"text", "multiline"}:
            tags.set(f.key, f"value for {f.key}")
    tags.set("year", "2026")
    tags.set("original_date", "1998")
    tags.set("bpm", "120")
    tags.set("track", "3/12")
    tags.set("disc", "1/2")
    tags.set("compilation", "1")
    return tags


def test_mp3_every_field_round_trips(silent_mp3: Path) -> None:
    tags = _every_text_value()
    write_tags(silent_mp3, tags)
    again = read_tags(silent_mp3)
    for f in TAG_FIELDS:
        assert again.get(f.key) == tags.get(f.key), f"{f.key} did not round-trip"


def test_mp3_empty_value_deletes_the_frame(silent_mp3: Path) -> None:
    tags = AudioTags()
    tags.set("album", "First")
    write_tags(silent_mp3, tags)
    assert read_tags(silent_mp3).get("album") == "First"
    tags.set("album", "")
    write_tags(silent_mp3, tags)
    assert read_tags(silent_mp3).get("album") == ""


def test_reading_a_file_with_no_tag_block_gives_empty_tags(silent_mp3: Path) -> None:
    assert read_tags(silent_mp3).values == {}


def test_preferred_id3_version_is_3_until_a_v24_field_is_set() -> None:
    tags = AudioTags()
    tags.set("album", "Plain")
    assert preferred_id3_version(tags) == 3
    tags.set("title_sort", "Plain, The")
    assert preferred_id3_version(tags) == 4


def test_writing_tags_leaves_chapter_frames_intact(silent_mp3: Path) -> None:
    chapters = [
        Chapter(index=0, title="Intro", start_ms=0, end_ms=60_000),
        Chapter(index=1, title="Body", start_ms=60_000, end_ms=180_000),
    ]
    write_mp3_chapters(silent_mp3, chapters)
    tags = AudioTags()
    tags.set("album", "Kept")
    write_tags(silent_mp3, tags)
    assert [c.title for c in read_mp3_chapters(silent_mp3)] == ["Intro", "Body"]
    assert read_tags(silent_mp3).get("album") == "Kept"


def test_write_mp3_chapters_accepts_an_id3_version(silent_mp3: Path) -> None:
    chapters = [Chapter(index=0, title="Only", start_ms=0, end_ms=1000)]
    write_mp3_chapters(silent_mp3, chapters, v2_version=4)
    assert [c.title for c in read_mp3_chapters(silent_mp3)] == ["Only"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/unit/core/speech/test_audio_tags.py -q`
Expected: FAIL — `ImportError: cannot import name 'read_tags'`

- [ ] **Step 3: Add the ID3 version keyword to `write_mp3_chapters`**

In `quill/core/speech/chapters.py`, change the signature and the final save. The default of 3 keeps every existing caller's on-disk result identical:

```python
def write_mp3_chapters(
    path: Path,
    chapters: list[Chapter],
    *,
    toc_title: str = "Chapters",
    v2_version: int = 3,
) -> None:
    """Write ID3v2 CHAP + CTOC frames onto ``path`` (existing tags preserved).

    Idempotent: any existing CHAP/CTOC frames are removed first so re-running
    does not duplicate chapters. ``v2_version`` selects the ID3 minor version
    the whole tag block is saved as — 3 by default for maximum player
    compatibility, 4 when the file carries a tag ID3v2.3 has no frame for
    (see :func:`quill.core.speech.audio_tags.preferred_id3_version`). Both
    versions define CHAP/CTOC identically. Raises ``RuntimeError`` when
    mutagen is unavailable.
    """
```

and at the end of the function replace `tags.save(str(path), v2_version=3)` with:

```python
    tags.save(str(path), v2_version=v2_version)
```

- [ ] **Step 4: Write the MP3 reader and writer**

Append to `quill/core/speech/audio_tags.py`:

```python
def preferred_id3_version(tags: AudioTags) -> int:
    """3 unless *tags* set a field ID3v2.3 has no frame for, then 4.

    ID3v2.3 is what the widest set of players reads, so it stays the default;
    but ``update_to_v23`` silently drops TSOT/TSOP/TSOA/TSO2 and rewrites the
    date frames, and a tag editor that quietly discards the sort fields is not
    a tag editor. Files are therefore upgraded to 2.4 only when the user has
    actually asked for something only 2.4 can hold.
    """
    for key in tags.values:
        if _BY_KEY[key].id3 in V24_ONLY_FRAMES:
            return 4
    return 3


def _is_mp4(path: Path) -> bool:
    return path.suffix.lower() in {".m4a", ".m4b", ".mp4"}


def read_tags(path: Path) -> AudioTags:
    """Read every modelled tag from *path* (MP3 or M4A/M4B/MP4).

    A file with no tag block at all reads as empty tags rather than an error —
    an untagged file is exactly the one a person opens the editor to fix.
    """
    if not path.is_file():
        raise TagReadError(f"File not found: {path}")
    return _read_mp4_tags(path) if _is_mp4(path) else _read_mp3_tags(path)


def write_tags(path: Path, tags: AudioTags) -> None:
    """Write every modelled tag onto *path*, leaving everything else alone.

    Load-modify-save: frames this module does not model — chapter CHAP/CTOC
    frames above all — survive untouched.
    """
    if not path.is_file():
        raise TagWriteError(f"File not found: {path}")
    if _is_mp4(path):
        _write_mp4_tags(path, tags)
    else:
        _write_mp3_tags(path, tags)


def _load_id3(path: Path) -> object:
    try:
        from mutagen.id3 import ID3, ID3NoHeaderError
    except ImportError as exc:  # pragma: no cover - only without the extra
        raise TagReadError("Editing tags requires the 'mutagen' package.") from exc
    try:
        return ID3(str(path))
    except ID3NoHeaderError:
        return ID3()
    except Exception as exc:  # noqa: BLE001 - mutagen raises many shapes
        raise TagReadError(f"Could not read tags: {exc}") from exc


def _read_mp3_tags(path: Path) -> AudioTags:
    id3 = _load_id3(path)
    tags = AudioTags()
    for f in TAG_FIELDS:
        frames = id3.getall(f.id3)
        if not frames:
            continue
        text = getattr(frames[0], "text", None)
        if not text:
            continue
        value = str(text[0])
        if f.kind == "bool":
            value = "1" if value.strip() not in {"", "0"} else ""
        tags.set(f.key, value)
    pictures = id3.getall("APIC")
    if pictures:
        pic = pictures[0]
        tags.cover = CoverArt(
            data=bytes(pic.data),
            mime=str(pic.mime or "image/jpeg"),
            description=str(pic.desc or ""),
            picture_type=int(pic.type),
        )
    return tags


def _id3_frame(frame_id: str, value: str) -> object:
    """Build the mutagen frame for *frame_id*; COMM and USLT need extra fields."""
    import mutagen.id3 as id3mod

    if frame_id == "COMM":
        return id3mod.COMM(encoding=3, lang="eng", desc="", text=[value])
    if frame_id == "USLT":
        return id3mod.USLT(encoding=3, lang="eng", desc="", text=value)
    frame_cls = getattr(id3mod, frame_id)
    return frame_cls(encoding=3, text=[value])


def _write_mp3_tags(path: Path, tags: AudioTags) -> None:
    id3 = _load_id3(path)
    for f in TAG_FIELDS:
        value = tags.get(f.key)
        if f.kind == "bool":
            value = "1" if value else ""
        if value:
            id3.setall(f.id3, [_id3_frame(f.id3, value)])
        else:
            id3.delall(f.id3)
    id3.delall("APIC")
    if tags.cover is not None:
        import mutagen.id3 as id3mod

        id3.add(
            id3mod.APIC(
                encoding=3,
                mime=tags.cover.mime,
                type=tags.cover.picture_type,
                desc=tags.cover.description,
                data=tags.cover.data,
            )
        )
    try:
        id3.save(str(path), v2_version=preferred_id3_version(tags))
    except Exception as exc:  # noqa: BLE001 - mutagen raises many shapes
        raise TagWriteError(f"Could not write tags: {exc}") from exc
```

Add `from pathlib import Path` to the module's imports.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest tests/unit/core/speech/test_audio_tags.py -q`
Expected: PASS. `test_mp3_every_field_round_trips` is the one to watch — if a frame does not round-trip, the failure names the key.

Run: `pytest tests/unit/core/speech/test_chapters.py tests/unit/core/speech/test_book_file.py -q`
Expected: PASS — the `v2_version` default keeps existing behaviour.

- [ ] **Step 6: Type-check, lint, commit**

Run: `mypy quill\core quill\io` then `ruff check quill/core/speech/`

```bash
git add quill/core/speech/audio_tags.py quill/core/speech/chapters.py tests/unit/core/speech/test_audio_tags.py
git commit -m "feat(speech): read and write the full ID3 tag set, with an adaptive version"
```

---

### Task 3: Cover art loading and validation

**Files:**
- Modify: `quill/core/speech/audio_tags.py`
- Test: `tests/unit/core/speech/test_audio_tags.py`

**Interfaces:**
- Consumes: `CoverArt`, `TagReadError` from Task 1
- Produces: `MAX_COVER_BYTES: int`, `load_cover(path: Path) -> CoverArt`, `cover_extension(cover: CoverArt) -> str`, `describe_cover(cover: CoverArt | None) -> str`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/core/speech/test_audio_tags.py`:

```python
from quill.core.speech.audio_tags import (  # noqa: E402
    MAX_COVER_BYTES,
    cover_extension,
    describe_cover,
    load_cover,
)

_PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000a49444154789c6360000002000100fdff03fd0000000049454e44ae"
    "426082"
)
_JPEG_HEAD = b"\xff\xd8\xff\xe0" + b"\x00" * 64


def test_load_cover_accepts_png(tmp_path: Path) -> None:
    path = tmp_path / "art.png"
    path.write_bytes(_PNG_1X1)
    cover = load_cover(path)
    assert cover.mime == "image/png"
    assert cover.data == _PNG_1X1
    assert cover_extension(cover) == ".png"


def test_load_cover_sniffs_bytes_not_the_extension(tmp_path: Path) -> None:
    path = tmp_path / "actually_a_png.jpg"
    path.write_bytes(_PNG_1X1)
    assert load_cover(path).mime == "image/png"


def test_load_cover_accepts_jpeg(tmp_path: Path) -> None:
    path = tmp_path / "art.jpg"
    path.write_bytes(_JPEG_HEAD)
    assert load_cover(path).mime == "image/jpeg"


def test_load_cover_rejects_a_non_image(tmp_path: Path) -> None:
    path = tmp_path / "notes.txt"
    path.write_bytes(b"this is not a picture")
    with pytest.raises(TagReadError, match="JPEG or PNG"):
        load_cover(path)


def test_load_cover_rejects_an_oversized_image(tmp_path: Path) -> None:
    path = tmp_path / "huge.png"
    path.write_bytes(_PNG_1X1 + b"\x00" * (MAX_COVER_BYTES + 1))
    with pytest.raises(TagReadError, match="8 MB"):
        load_cover(path)


def test_describe_cover_names_format_and_size() -> None:
    assert describe_cover(None) == "No cover art."
    text = describe_cover(CoverArt(data=_PNG_1X1, mime="image/png"))
    assert "PNG" in text
    assert "bytes" in text


def test_cover_art_round_trips_through_an_mp3(silent_mp3: Path) -> None:
    tags = AudioTags()
    tags.cover = CoverArt(data=_PNG_1X1, mime="image/png", description="Front")
    write_tags(silent_mp3, tags)
    back = read_tags(silent_mp3).cover
    assert back is not None
    assert back.data == _PNG_1X1
    assert back.mime == "image/png"
    assert back.description == "Front"


def test_removing_cover_art_clears_it(silent_mp3: Path) -> None:
    tags = AudioTags()
    tags.cover = CoverArt(data=_PNG_1X1, mime="image/png")
    write_tags(silent_mp3, tags)
    tags.cover = None
    write_tags(silent_mp3, tags)
    assert read_tags(silent_mp3).cover is None
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/unit/core/speech/test_audio_tags.py -q -k cover`
Expected: FAIL — `ImportError: cannot import name 'MAX_COVER_BYTES'`

- [ ] **Step 3: Write the implementation**

Append to `quill/core/speech/audio_tags.py`:

```python
#: The largest cover image accepted, in bytes. Beyond this the tag block
#: dwarfs the audio and some players stop reading tags altogether.
MAX_COVER_BYTES: int = 8 * 1024 * 1024

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_JPEG_MAGIC = b"\xff\xd8\xff"


def load_cover(path: Path) -> CoverArt:
    """Read *path* as cover art, sniffing the real bytes, not the extension.

    Only JPEG and PNG are accepted: they are the two formats every player
    decodes, and a file renamed to ``.jpg`` is still whatever it actually is.
    """
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise TagReadError(f"Could not read the image: {exc}") from exc
    if len(data) > MAX_COVER_BYTES:
        raise TagReadError("That image is larger than the 8 MB cover art limit.")
    if data.startswith(_PNG_MAGIC):
        mime = "image/png"
    elif data.startswith(_JPEG_MAGIC):
        mime = "image/jpeg"
    else:
        raise TagReadError("Cover art must be a JPEG or PNG image.")
    return CoverArt(data=data, mime=mime, description="", picture_type=3)


def cover_extension(cover: CoverArt) -> str:
    """The file extension to suggest when saving *cover* out."""
    return ".png" if cover.mime == "image/png" else ".jpg"


def describe_cover(cover: CoverArt | None) -> str:
    """A speakable description of the current art — what a reader can use.

    A thumbnail tells a sighted user everything and a screen-reader user
    nothing, so the text is the primary readout and the picture is the
    supplement, not the other way round.
    """
    if cover is None:
        return "No cover art."
    fmt = "PNG" if cover.mime == "image/png" else "JPEG"
    parts = [f"{fmt} image, {len(cover.data):,} bytes"]
    if cover.description:
        parts.append(f"described as {cover.description}")
    return ". ".join(parts) + "."
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/unit/core/speech/test_audio_tags.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add quill/core/speech/audio_tags.py tests/unit/core/speech/test_audio_tags.py
git commit -m "feat(speech): load, validate, describe and embed cover art"
```

---

### Task 4: MP4 (M4A/M4B) read and write, in place

**Files:**
- Modify: `quill/core/speech/audio_tags.py`
- Test: `tests/unit/core/speech/test_audio_tags.py`

**Interfaces:**
- Consumes: everything from Tasks 1–3
- Produces: `_read_mp4_tags` / `_write_mp4_tags` (private; reached through `read_tags`/`write_tags`)

Writing MP4 tags in place with mutagen is what lets a tags-only edit of an M4B finish instantly instead of re-muxing the whole file. The ffmpeg re-mux stays for chapter changes, which genuinely need it.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/core/speech/test_audio_tags.py`:

```python
@pytest.fixture
def empty_m4a(tmp_path: Path) -> Path:
    """A real, minimal M4A produced by ffmpeg; skipped when ffmpeg is absent."""
    from quill.core.speech.ffmpeg import find_ffmpeg
    from quill.stability.safe_subprocess import run_subprocess_safely

    ffmpeg = find_ffmpeg()
    if ffmpeg is None:
        pytest.skip("ffmpeg is not installed")
    path = tmp_path / "book.m4a"
    args = [
        ffmpeg, "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
        "-t", "1", "-c:a", "aac", "-y", str(path),
    ]
    if run_subprocess_safely(args, timeout_seconds=120.0).returncode != 0:
        pytest.skip("ffmpeg could not build the fixture")
    return path


def test_mp4_mapped_fields_round_trip(empty_m4a: Path) -> None:
    tags = AudioTags()
    tags.set("album", "The Book")
    tags.set("artist", "Jane Doe")
    tags.set("album_artist", "Sam Reader")
    tags.set("genre", "Audiobook")
    tags.set("year", "2026")
    tags.set("track", "3/12")
    tags.set("disc", "1/2")
    tags.set("bpm", "120")
    tags.set("compilation", "1")
    tags.set("publisher", "Example Press")
    tags.set("title_sort", "Book, The")
    write_tags(empty_m4a, tags)
    again = read_tags(empty_m4a)
    for key in (
        "album", "artist", "album_artist", "genre", "year", "track", "disc",
        "bpm", "compilation", "publisher", "title_sort",
    ):
        assert again.get(key) == tags.get(key), f"{key} did not round-trip"


def test_mp4_cover_art_round_trips(empty_m4a: Path) -> None:
    tags = AudioTags()
    tags.cover = CoverArt(data=_PNG_1X1, mime="image/png")
    write_tags(empty_m4a, tags)
    back = read_tags(empty_m4a).cover
    assert back is not None
    assert back.mime == "image/png"
    assert back.data == _PNG_1X1


def test_mp4_skips_fields_with_no_atom(empty_m4a: Path) -> None:
    """A field whose mp4 mapping is empty is skipped, never guessed at."""
    unmapped = [f.key for f in TAG_FIELDS if not f.mp4]
    tags = AudioTags()
    for key in unmapped:
        tags.set(key, "ignored")
    tags.set("album", "Still Written")
    write_tags(empty_m4a, tags)
    again = read_tags(empty_m4a)
    assert again.get("album") == "Still Written"
    for key in unmapped:
        assert again.get(key) == ""
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/unit/core/speech/test_audio_tags.py -q -k mp4`
Expected: FAIL — `NameError: name '_read_mp4_tags' is not defined` (or a skip if ffmpeg is absent; install ffmpeg or run these on a machine that has it before claiming the task done).

- [ ] **Step 3: Write the implementation**

Append to `quill/core/speech/audio_tags.py`:

```python
#: MP4 atoms whose value is an integer pair ``(number, total)``.
_MP4_PAIR_ATOMS: frozenset[str] = frozenset({"trkn", "disk"})
#: MP4 atoms whose value is a plain integer list.
_MP4_INT_ATOMS: frozenset[str] = frozenset({"tmpo"})
#: MP4 atoms whose value is a boolean.
_MP4_BOOL_ATOMS: frozenset[str] = frozenset({"cpil"})


def _load_mp4(path: Path) -> object:
    try:
        from mutagen.mp4 import MP4
    except ImportError as exc:  # pragma: no cover - only without the extra
        raise TagReadError("Editing tags requires the 'mutagen' package.") from exc
    try:
        audio = MP4(str(path))
    except Exception as exc:  # noqa: BLE001 - mutagen raises many shapes
        raise TagReadError(f"Could not read tags: {exc}") from exc
    if audio.tags is None:
        audio.add_tags()
    return audio


def _mp4_value_to_text(atom: str, raw: object) -> str:
    """One MP4 atom value as the flat string the table's model stores."""
    if not isinstance(raw, list) or not raw:
        return ""
    first = raw[0]
    if atom in _MP4_PAIR_ATOMS and isinstance(first, tuple):
        number, total = (list(first) + [0, 0])[:2]
        return f"{number}/{total}" if total else str(number)
    if atom in _MP4_BOOL_ATOMS:
        return "1" if first else ""
    if atom in _MP4_INT_ATOMS:
        return str(int(first))
    if isinstance(first, bytes):  # freeform ---- atoms carry raw bytes
        return first.decode("utf-8", "replace")
    return str(first)


def _mp4_text_to_value(atom: str, text: str) -> object:
    """The typed MP4 atom value for *text*, inverse of :func:`_mp4_value_to_text`."""
    if atom in _MP4_PAIR_ATOMS:
        number, _, total = text.partition("/")
        return [(int(number or 0), int(total or 0))]
    if atom in _MP4_BOOL_ATOMS:
        return bool(text)
    if atom in _MP4_INT_ATOMS:
        return [int(text)]
    if atom.startswith("----"):
        from mutagen.mp4 import MP4FreeForm

        return [MP4FreeForm(text.encode("utf-8"))]
    return [text]


def _read_mp4_tags(path: Path) -> AudioTags:
    audio = _load_mp4(path)
    tags = AudioTags()
    for f in TAG_FIELDS:
        if not f.mp4 or f.mp4 not in audio.tags:
            continue
        value = _mp4_value_to_text(f.mp4, audio.tags[f.mp4])
        if value:
            tags.set(f.key, value)
    covers = audio.tags.get("covr") or []
    if covers:
        from mutagen.mp4 import MP4Cover

        art = covers[0]
        fmt = getattr(art, "imageformat", MP4Cover.FORMAT_JPEG)
        tags.cover = CoverArt(
            data=bytes(art),
            mime="image/png" if fmt == MP4Cover.FORMAT_PNG else "image/jpeg",
        )
    return tags


def _write_mp4_tags(path: Path, tags: AudioTags) -> None:
    audio = _load_mp4(path)
    for f in TAG_FIELDS:
        if not f.mp4:
            continue  # MP4 has no home for this field; skip, never guess
        value = tags.get(f.key)
        if f.kind == "bool":
            value = "1" if value else ""
        if value:
            try:
                audio.tags[f.mp4] = _mp4_text_to_value(f.mp4, value)
            except ValueError:
                # A non-numeric value typed into a numeric atom: drop it
                # rather than refusing the whole save.
                audio.tags.pop(f.mp4, None)
        else:
            audio.tags.pop(f.mp4, None)
    audio.tags.pop("covr", None)
    if tags.cover is not None:
        from mutagen.mp4 import MP4Cover

        fmt = (
            MP4Cover.FORMAT_PNG
            if tags.cover.mime == "image/png"
            else MP4Cover.FORMAT_JPEG
        )
        audio.tags["covr"] = [MP4Cover(tags.cover.data, imageformat=fmt)]
    try:
        audio.save()
    except Exception as exc:  # noqa: BLE001 - mutagen raises many shapes
        raise TagWriteError(f"Could not write tags: {exc}") from exc
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/unit/core/speech/test_audio_tags.py -q`
Expected: PASS. Confirm the MP4 tests did **not** skip: `pytest tests/unit/core/speech/test_audio_tags.py -q -k mp4 -rs` and check the summary reports no skips.

- [ ] **Step 5: Type-check, lint, commit**

```bash
mypy quill\core quill\io
ruff check quill/core/speech/audio_tags.py
git add quill/core/speech/audio_tags.py tests/unit/core/speech/test_audio_tags.py
git commit -m "feat(speech): write M4A/M4B tags in place through MP4 atoms"
```

---

### Task 5: The `AudioMetadata` bridge, and one ID3 version per save

**Files:**
- Modify: `quill/core/speech/audio_tags.py`
- Modify: `quill/core/speech/book_file.py:159-200` (`save_mp3_book`)
- Test: `tests/unit/core/speech/test_audio_tags.py`, `tests/unit/core/speech/test_book_file.py`

**Interfaces:**
- Consumes: `AudioTags` from Task 1, `AudioMetadata` from `quill.core.speech.ffmpeg`
- Produces: `to_audio_metadata(tags: AudioTags) -> AudioMetadata`, `merge_audio_metadata(tags: AudioTags, meta: AudioMetadata) -> AudioTags`

`save_mp3_book` and `write_tags` both run on a save. Both are load-modify-save so neither clobbers the other's frames, but they must agree on the ID3 version or the second save rewrites the first's frames at a different version. The bridge is also what keeps `BookFile`, the M4B re-mux and the batch pipeline working unchanged.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/core/speech/test_audio_tags.py`:

```python
from quill.core.speech.audio_tags import (  # noqa: E402
    merge_audio_metadata,
    to_audio_metadata,
)
from quill.core.speech.ffmpeg import AudioMetadata  # noqa: E402


def test_to_audio_metadata_maps_the_seven_core_fields() -> None:
    tags = AudioTags()
    tags.set("title", "A Title")
    tags.set("artist", "Jane Doe")
    tags.set("album", "The Book")
    tags.set("album_artist", "Sam Reader")
    tags.set("genre", "Audiobook")
    tags.set("year", "2026")
    tags.set("track", "3/12")
    tags.set("comment", "Hello")
    meta = to_audio_metadata(tags)
    assert meta.title == "A Title"
    assert meta.artist == "Jane Doe"
    assert meta.album == "The Book"
    assert meta.album_artist == "Sam Reader"
    assert meta.genre == "Audiobook"
    assert meta.year == "2026"
    assert meta.track == "3/12"
    assert meta.comment == "Hello"


def test_merge_audio_metadata_overlays_without_losing_other_fields() -> None:
    tags = AudioTags()
    tags.set("publisher", "Example Press")
    tags.set("album", "Old Title")
    merged = merge_audio_metadata(tags, AudioMetadata(album="New Title"))
    assert merged.get("album") == "New Title"
    assert merged.get("publisher") == "Example Press"


def test_merge_audio_metadata_does_not_mutate_its_input() -> None:
    tags = AudioTags()
    tags.set("album", "Old Title")
    merge_audio_metadata(tags, AudioMetadata(album="New Title"))
    assert tags.get("album") == "Old Title"
```

Append to `tests/unit/core/speech/test_book_file.py`:

```python
def test_save_mp3_book_keeps_sort_fields_written_by_the_tag_editor(
    silent_mp3: Path,
) -> None:
    """A v2.4-only field survives a Workbench save (GATE: the version agrees)."""
    from quill.core.speech.audio_tags import AudioTags, read_tags, write_tags

    tags = AudioTags()
    tags.set("album", "The Book")
    tags.set("title_sort", "Book, The")
    write_tags(silent_mp3, tags)

    book = read_book(silent_mp3)
    book.tags = AudioMetadata(album="The Book", artist="Jane Doe")
    save_mp3_book(book)

    assert read_tags(silent_mp3).get("title_sort") == "Book, The"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/unit/core/speech/test_audio_tags.py tests/unit/core/speech/test_book_file.py -q`
Expected: FAIL — `ImportError: cannot import name 'to_audio_metadata'`, and the book_file test fails because `save_mp3_book` writes v2.3 and drops `TSOT`.

- [ ] **Step 3: Write the bridge**

Append to `quill/core/speech/audio_tags.py`:

```python
#: The AudioMetadata field each of the seven core tags corresponds to.
_METADATA_KEYS: tuple[tuple[str, str], ...] = (
    ("title", "title"),
    ("artist", "artist"),
    ("album", "album"),
    ("album_artist", "album_artist"),
    ("genre", "genre"),
    ("year", "year"),
    ("track", "track"),
    ("comment", "comment"),
)


def to_audio_metadata(tags: AudioTags) -> AudioMetadata:
    """The seven-field ``AudioMetadata`` view of *tags*, for ffmpeg and BookFile."""
    from quill.core.speech.ffmpeg import AudioMetadata

    return AudioMetadata(**{attr: tags.get(key) for key, attr in _METADATA_KEYS})


def merge_audio_metadata(tags: AudioTags, meta: AudioMetadata) -> AudioTags:
    """A copy of *tags* with the seven core fields overlaid from *meta*.

    The Workbench's five quick fields edit an ``AudioMetadata``; this is how
    those edits reach the full tag set without discarding the twenty-one
    fields the quick view does not show.
    """
    merged = tags.copy()
    for key, attr in _METADATA_KEYS:
        merged.set(key, str(getattr(meta, attr, "") or ""))
    return merged
```

Add the type-checking import at the top of the module so the annotation resolves without importing ffmpeg at load time:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from quill.core.speech.ffmpeg import AudioMetadata
```

- [ ] **Step 4: Make `save_mp3_book` agree on the ID3 version**

In `quill/core/speech/book_file.py`, replace the last two statements of `save_mp3_book` (`id3.save(...)` and the `write_mp3_chapters` call) with:

```python
    # One version for the whole save: write_tags may have already put a
    # v2.4-only frame (a sort field, a full date) on this file, and saving
    # the chapter block back at v2.3 would silently drop it.
    from quill.core.speech.audio_tags import preferred_id3_version, read_tags

    version = preferred_id3_version(read_tags(book.path))
    id3.save(str(book.path), v2_version=version)
    # Chapters go through the shared CHAP/CTOC writer (idempotent, preserves tags).
    write_mp3_chapters(book.path, book.chapters, v2_version=version)
```

Update the function's docstring to mention that the version follows whatever the file already carries.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest tests/unit/core/speech/ -q`
Expected: PASS, no regressions in `test_book_file.py` or `test_chapters.py`.

- [ ] **Step 6: Type-check, lint, commit**

```bash
mypy quill\core quill\io
git add quill/core/speech/audio_tags.py quill/core/speech/book_file.py tests/unit/core/speech/
git commit -m "feat(speech): bridge full tags to AudioMetadata and unify the ID3 version"
```

---

### Task 6: Add, delete and set-bounds chapter operations

**Files:**
- Modify: `quill/core/speech/chapters.py`
- Test: `tests/unit/core/speech/test_chapters.py`

**Interfaces:**
- Consumes: `Chapter`, `ChapterEditError`, `_renumber` from `chapters.py`
- Produces: `add_chapter(chapters, at_ms, *, title="New chapter", min_part_ms=1000) -> list[Chapter]`, `delete_chapter(chapters, index) -> list[Chapter]`, `set_chapter_bounds(chapters, index, start_ms, end_ms, *, min_part_ms=500) -> list[Chapter]`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/core/speech/test_chapters.py`:

```python
from quill.core.speech.chapters import (  # noqa: E402
    add_chapter,
    delete_chapter,
    set_chapter_bounds,
)


def _three() -> list[Chapter]:
    return [
        Chapter(index=0, title="One", start_ms=0, end_ms=10_000),
        Chapter(index=1, title="Two", start_ms=10_000, end_ms=20_000),
        Chapter(index=2, title="Three", start_ms=20_000, end_ms=30_000),
    ]


def test_add_chapter_splits_the_chapter_containing_the_point() -> None:
    result = add_chapter(_three(), 15_000, title="Middle")
    assert [c.title for c in result] == ["One", "Two", "Middle", "Three"]
    assert result[2].start_ms == 15_000
    assert result[1].end_ms == 15_000
    assert [c.index for c in result] == [0, 1, 2, 3]


def test_add_chapter_at_the_end_appends_when_there_is_room() -> None:
    """Past the last end there is nothing to split, so the marker appends."""
    chapters = _three()
    result = add_chapter(chapters, 30_000, title="Outro")
    assert [c.title for c in result] == ["One", "Two", "Three", "Outro"]
    assert result[-1].start_ms == 30_000
    assert result[-1].end_ms == 30_000


def test_add_chapter_too_close_to_a_boundary_is_refused() -> None:
    with pytest.raises(ChapterEditError, match="too close"):
        add_chapter(_three(), 10_500, min_part_ms=1000)


def test_delete_first_chapter_pulls_the_next_start_to_zero() -> None:
    result = delete_chapter(_three(), 0)
    assert [c.title for c in result] == ["Two", "Three"]
    assert result[0].start_ms == 0
    assert result[0].end_ms == 20_000


def test_delete_middle_chapter_extends_the_previous_one() -> None:
    result = delete_chapter(_three(), 1)
    assert [c.title for c in result] == ["One", "Three"]
    assert result[0].end_ms == 20_000


def test_delete_last_chapter_extends_the_previous_one() -> None:
    result = delete_chapter(_three(), 2)
    assert [c.title for c in result] == ["One", "Two"]
    assert result[-1].end_ms == 30_000


def test_delete_the_only_chapter_is_refused() -> None:
    one = [Chapter(index=0, title="All", start_ms=0, end_ms=10_000)]
    with pytest.raises(ChapterEditError, match="only chapter"):
        delete_chapter(one, 0)


def test_delete_out_of_range_is_refused() -> None:
    with pytest.raises(ChapterEditError, match="No chapter"):
        delete_chapter(_three(), 9)


def test_set_chapter_bounds_moves_both_edges_and_the_neighbours() -> None:
    result = set_chapter_bounds(_three(), 1, 8_000, 22_000)
    assert result[0].end_ms == 8_000
    assert result[1].start_ms == 8_000
    assert result[1].end_ms == 22_000
    assert result[2].start_ms == 22_000


def test_set_chapter_bounds_rejects_an_inverted_range() -> None:
    with pytest.raises(ChapterEditError, match="before"):
        set_chapter_bounds(_three(), 1, 20_000, 10_000)


def test_set_chapter_bounds_rejects_swallowing_a_neighbour() -> None:
    with pytest.raises(ChapterEditError, match="between"):
        set_chapter_bounds(_three(), 1, 100, 29_900)


def test_set_chapter_bounds_leaves_the_first_start_and_last_end_pinned() -> None:
    result = set_chapter_bounds(_three(), 0, 0, 12_000)
    assert result[0].start_ms == 0
    assert result[-1].end_ms == 30_000
```

Make sure `pytest` and `ChapterEditError` are already imported at the top of that test module; add them if not.

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/unit/core/speech/test_chapters.py -q`
Expected: FAIL — `ImportError: cannot import name 'add_chapter'`

- [ ] **Step 3: Write the implementation**

Append to `quill/core/speech/chapters.py`, after `set_chapter_start`:

```python
def add_chapter(
    chapters: list[Chapter],
    at_ms: int,
    *,
    title: str = "New chapter",
    min_part_ms: int = 1000,
) -> list[Chapter]:
    """Insert a chapter boundary at *at_ms* — the explicit "add" operation.

    Inside an existing chapter this is :func:`split_chapter`: the chapter is
    cut in two, the left half keeps its title and the right half gets *title*.
    At or past the last chapter's end there is nothing to split, so the marker
    is **appended** as a zero-length chapter that a later retime or a longer
    file fills out — the case :func:`split_chapter` refuses outright, and the
    reason "add" is its own verb rather than an alias.
    """
    if not chapters:
        raise ChapterEditError("There are no chapters to add to.")
    if at_ms < 0:
        raise ChapterEditError("A chapter cannot start before the beginning.")
    last_end = chapters[-1].end_ms
    if at_ms >= last_end:
        appended = Chapter(
            index=len(chapters),
            title=title or "New chapter",
            start_ms=last_end,
            end_ms=last_end,
        )
        return _renumber([*chapters, appended])
    return split_chapter(chapters, at_ms, title=title, min_part_ms=min_part_ms)


def delete_chapter(chapters: list[Chapter], index: int) -> list[Chapter]:
    """Remove chapter *index*'s marker. The audio is never touched.

    Deleting the first chapter pulls the second one's start back to the
    beginning; deleting any other extends the previous chapter over it. Unlike
    :func:`merge_chapter` this is defined for the last chapter too, and it
    keeps the *surviving* chapter's title rather than the deleted one's —
    which is what "delete" means and "merge" does not.
    """
    n = len(chapters)
    if not 0 <= index < n:
        raise ChapterEditError("No chapter is selected.")
    if n < 2:
        raise ChapterEditError("The only chapter cannot be deleted.")
    if index == 0:
        head = replace(chapters[1], start_ms=chapters[0].start_ms)
        return _renumber([head, *chapters[2:]])
    prev = replace(chapters[index - 1], end_ms=chapters[index].end_ms)
    return _renumber([*chapters[: index - 1], prev, *chapters[index + 1 :]])


def set_chapter_bounds(
    chapters: list[Chapter],
    index: int,
    start_ms: int,
    end_ms: int,
    *,
    min_part_ms: int = 500,
) -> list[Chapter]:
    """Retime both edges of chapter *index*, keeping the list contiguous.

    The neighbours stretch or shrink to meet the new edges. The first
    chapter's start and the last chapter's end are pinned to the file, so
    passing a different value for either is ignored rather than refused.
    """
    n = len(chapters)
    if not 0 <= index < n:
        raise ChapterEditError("No chapter is selected.")
    if index == 0:
        start_ms = chapters[0].start_ms
    if index == n - 1:
        end_ms = chapters[-1].end_ms
    if end_ms - start_ms < min_part_ms:
        raise ChapterEditError("A chapter's start must come before its end.")
    lo = chapters[index - 1].start_ms + min_part_ms if index > 0 else chapters[0].start_ms
    hi = chapters[index + 1].end_ms - min_part_ms if index < n - 1 else chapters[-1].end_ms
    if not lo <= start_ms <= hi or not lo <= end_ms <= hi:
        from quill.core.speech.chapter_io import format_timestamp

        raise ChapterEditError(
            f"Start and end must be between {format_timestamp(lo)} "
            f"and {format_timestamp(hi)}."
        )
    result = list(chapters)
    result[index] = replace(chapters[index], start_ms=start_ms, end_ms=end_ms)
    if index > 0:
        result[index - 1] = replace(chapters[index - 1], end_ms=start_ms)
    if index < n - 1:
        result[index + 1] = replace(chapters[index + 1], start_ms=end_ms)
    return _renumber(result)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/unit/core/speech/test_chapters.py -q`
Expected: PASS, including the pre-existing tests.

- [ ] **Step 5: Type-check, lint, commit**

```bash
mypy quill\core quill\io
git add quill/core/speech/chapters.py tests/unit/core/speech/test_chapters.py
git commit -m "feat(speech): add, delete and retime chapters as first-class operations"
```

---

### Task 7: Nudging a marker, and the configurable step setting

**Files:**
- Modify: `quill/core/speech/chapters.py`
- Modify: `quill/core/settings.py:654-660` (field), `:1334-1356` (parse), `:1673-1679` (constructor)
- Test: `tests/unit/core/speech/test_chapters.py`, `tests/unit/core/test_settings.py`

**Interfaces:**
- Consumes: `Chapter`, `ChapterEditError`, `_renumber` from Task 6
- Produces: `NUDGE_STEPS_MS: tuple[int, ...]`, `nudge_chapter_start(chapters, index, delta_ms, *, min_part_ms=500) -> tuple[list[Chapter], int]`; `Settings.audio_studio_chapter_nudge_ms: int`

The nudge is the one chapter operation that **clamps instead of raising**: it is driven by a held key, and stopping at the wall is what a person expects when they run a marker into its neighbour. It returns the delta actually applied so the UI can say "cannot move further" once per run rather than once per press.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/core/speech/test_chapters.py`:

```python
from quill.core.speech.chapters import NUDGE_STEPS_MS, nudge_chapter_start  # noqa: E402


def test_nudge_steps_are_ascending_and_sane() -> None:
    assert list(NUDGE_STEPS_MS) == sorted(NUDGE_STEPS_MS)
    assert NUDGE_STEPS_MS[0] >= 10
    assert 500 in NUDGE_STEPS_MS


def test_nudge_moves_the_start_and_the_previous_end_together() -> None:
    result, applied = nudge_chapter_start(_three(), 1, -500)
    assert applied == -500
    assert result[1].start_ms == 9_500
    assert result[0].end_ms == 9_500


def test_nudge_forward_moves_the_boundary_later() -> None:
    result, applied = nudge_chapter_start(_three(), 1, 2_000)
    assert applied == 2_000
    assert result[1].start_ms == 12_000


def test_nudge_clamps_at_the_previous_chapter_instead_of_raising() -> None:
    result, applied = nudge_chapter_start(_three(), 1, -60_000, min_part_ms=500)
    assert applied == -9_500
    assert result[1].start_ms == 500
    assert result[0].end_ms == 500


def test_nudge_clamps_at_this_chapters_own_end() -> None:
    result, applied = nudge_chapter_start(_three(), 1, 60_000, min_part_ms=500)
    assert applied == 9_500
    assert result[1].start_ms == 19_500


def test_nudge_that_can_move_nothing_reports_zero() -> None:
    chapters = [
        Chapter(index=0, title="One", start_ms=0, end_ms=500),
        Chapter(index=1, title="Two", start_ms=500, end_ms=1_000),
    ]
    result, applied = nudge_chapter_start(chapters, 1, -1_000, min_part_ms=500)
    assert applied == 0
    assert result[1].start_ms == 500


def test_nudge_refuses_the_first_chapter() -> None:
    with pytest.raises(ChapterEditError, match="beginning"):
        nudge_chapter_start(_three(), 0, 500)


def test_nudge_refuses_an_unselected_index() -> None:
    with pytest.raises(ChapterEditError, match="No chapter"):
        nudge_chapter_start(_three(), 9, 500)
```

Append to `tests/unit/core/test_settings.py`:

```python
def test_chapter_nudge_step_defaults_to_500ms() -> None:
    assert Settings().audio_studio_chapter_nudge_ms == 500


def test_chapter_nudge_step_round_trips() -> None:
    loaded = Settings.from_dict({"audio_studio_chapter_nudge_ms": 250})
    assert loaded.audio_studio_chapter_nudge_ms == 250


def test_chapter_nudge_step_clamps_out_of_range_values() -> None:
    assert Settings.from_dict(
        {"audio_studio_chapter_nudge_ms": 0}
    ).audio_studio_chapter_nudge_ms == 10
    assert Settings.from_dict(
        {"audio_studio_chapter_nudge_ms": 999_999}
    ).audio_studio_chapter_nudge_ms == 60_000


def test_chapter_nudge_step_falls_back_on_garbage() -> None:
    assert Settings.from_dict(
        {"audio_studio_chapter_nudge_ms": "banana"}
    ).audio_studio_chapter_nudge_ms == 500
```

Check the top of `tests/unit/core/test_settings.py` for how `Settings` is imported and match it.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/unit/core/speech/test_chapters.py tests/unit/core/test_settings.py -q`
Expected: FAIL — `ImportError: cannot import name 'nudge_chapter_start'` and `AttributeError: 'Settings' object has no attribute 'audio_studio_chapter_nudge_ms'`

- [ ] **Step 3: Write the nudge**

Append to `quill/core/speech/chapters.py`:

```python
#: The nudge step sizes the Workbench offers, in milliseconds.
NUDGE_STEPS_MS: tuple[int, ...] = (100, 250, 500, 1000, 2000, 5000, 10_000)


def nudge_chapter_start(
    chapters: list[Chapter],
    index: int,
    delta_ms: int,
    *,
    min_part_ms: int = 500,
) -> tuple[list[Chapter], int]:
    """Move chapter *index*'s start by *delta_ms*, clamped at its neighbours.

    Returns the new list and the delta **actually** applied. This is the one
    chapter edit that clamps rather than raising: a nudge is a held key, and
    running a marker up against its neighbour should stop there, not throw.
    An applied delta of 0 means the marker is already at the wall, which lets
    the caller say so once per run instead of once per keypress.

    Because chapters are contiguous a chapter's start *is* the previous
    chapter's end, so moving the start moves both sides of one boundary.
    """
    n = len(chapters)
    if not 0 <= index < n:
        raise ChapterEditError("No chapter is selected.")
    if index == 0:
        raise ChapterEditError("The first chapter must start at the beginning.")
    lo = chapters[index - 1].start_ms + min_part_ms
    hi = chapters[index].end_ms - min_part_ms
    current = chapters[index].start_ms
    if lo > hi:
        return list(chapters), 0
    target = max(lo, min(current + delta_ms, hi))
    applied = target - current
    if applied == 0:
        return list(chapters), 0
    prev = replace(chapters[index - 1], end_ms=target)
    cur = replace(chapters[index], start_ms=target)
    result = _renumber([*chapters[: index - 1], prev, cur, *chapters[index + 1 :]])
    return result, applied
```

- [ ] **Step 4: Add the setting**

In `quill/core/settings.py`, beside `audio_studio_last_journey` (around line 660), add the field with its comment:

```python
    # How far one press of the Workbench's Nudge back/forward buttons moves a
    # chapter marker. Remembered so the step a person picked by ear is the one
    # they get next session.
    audio_studio_chapter_nudge_ms: int = 500  # 10-60000
```

In `from_dict` (beside the `audio_studio_last_journey` parse, around line 1352):

```python
        audio_studio_chapter_nudge_ms = _clamp_int(
            data.get("audio_studio_chapter_nudge_ms", 500), 500, 10, 60000
        )
```

In the constructor call (beside `audio_studio_last_journey=`, around line 1679):

```python
            audio_studio_chapter_nudge_ms=audio_studio_chapter_nudge_ms,
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest tests/unit/core/speech/test_chapters.py tests/unit/core/test_settings.py -q`
Expected: PASS.

- [ ] **Step 6: Document the setting (GATE-SETDOC)**

A new `Settings` field is `missing` until it is documented. Add a row for `audio_studio_chapter_nudge_ms` to the settings documentation corpus under `docs/`, then run the inventory to confirm it resolves:

Run: `python -m quill.tools.platform_report`
Expected: the settings-documentation gate reports no `missing` entries. If it still reports one, the doc row's key spelling does not match the field name.

- [ ] **Step 7: Type-check, lint, commit**

```bash
mypy quill\core quill\io
git add quill/core/speech/chapters.py quill/core/settings.py docs/ tests/unit/core/
git commit -m "feat(speech): nudge a chapter marker by a remembered step"
```

---

### Task 8: The Tag Editor dialog — pages, fields, accessibility

**Files:**
- Create: `quill/ui/audio_studio/tag_editor.py`
- Test: `tests/unit/ui/test_tag_editor_dialog.py`

**Interfaces:**
- Consumes: `TAG_FIELDS`, `GROUPS`, `fields_in`, `AudioTags`, `describe_cover`, `load_cover`, `cover_extension` from Tasks 1–3
- Produces: `TagEditorDialog(parent, tags, *, filename, announce=None)` with `result() -> AudioTags`; `TagPagePanel(parent, group)` with `collect(tags) -> None`

Read the Global Constraints again before writing this file. The four that bite hardest here: label **before** control, `set_accessible_name` inline, `SetHelpText` inline, and mnemonics unique per page (which is why each page is its own class).

- [ ] **Step 1: Write the failing test**

Create `tests/unit/ui/test_tag_editor_dialog.py`:

```python
"""The Tag Editor dialog: it builds, it is accessible, and values round-trip."""

from __future__ import annotations

import pytest

wx = pytest.importorskip("wx")

from quill.core.speech.audio_tags import (  # noqa: E402
    GROUPS,
    TAG_FIELDS,
    AudioTags,
    CoverArt,
)
from quill.ui.audio_studio.tag_editor import TagEditorDialog  # noqa: E402

pytestmark = pytest.mark.xdist_group("wx")


@pytest.fixture
def dialog(wx_app: object) -> object:
    tags = AudioTags()
    tags.set("album", "The Book")
    tags.set("publisher", "Example Press")
    frame = wx.Frame(None)
    dlg = TagEditorDialog(frame, tags, filename="book.mp3")
    yield dlg
    dlg.Destroy()
    frame.Destroy()


def test_every_field_has_a_control(dialog: object) -> None:
    for f in TAG_FIELDS:
        assert f.key in dialog.controls, f"{f.key} has no control"


def test_every_control_has_help_text_and_an_accessible_name(dialog: object) -> None:
    for key, ctrl in dialog.controls.items():
        assert ctrl.GetHelpText(), f"{key} has no help text"
        assert ctrl.GetName() not in {"", "control", "panel"}, f"{key} is unnamed"


def test_mnemonics_are_unique_within_each_page(dialog: object) -> None:
    for group, _label in GROUPS:
        page = dialog.pages[group]
        letters: list[str] = []
        for child in page.GetChildren():
            label = child.GetLabel()
            if "&" in label:
                letters.append(label[label.index("&") + 1].lower())
        assert len(letters) == len(set(letters)), f"duplicate mnemonic on {group}"


def test_each_label_is_created_before_its_control(dialog: object) -> None:
    """A11Y-Z-ORDER: screen readers pair a label with the control after it."""
    for group, _label in GROUPS:
        children = list(dialog.pages[group].GetChildren())
        for i, child in enumerate(children):
            if isinstance(child, wx.StaticText) and child.GetLabel().endswith(":"):
                assert i + 1 < len(children), f"{child.GetLabel()} labels nothing"
                assert not isinstance(children[i + 1], wx.StaticText)


def test_values_seed_the_controls_and_come_back_out(dialog: object) -> None:
    assert dialog.controls["album"].GetValue() == "The Book"
    dialog.controls["album"].SetValue("Renamed")
    dialog.controls["copyright"].SetValue("2026 Example Press")
    result = dialog.result()
    assert result.get("album") == "Renamed"
    assert result.get("copyright") == "2026 Example Press"
    assert result.get("publisher") == "Example Press"


def test_result_does_not_mutate_the_tags_it_was_given(wx_app: object) -> None:
    tags = AudioTags()
    tags.set("album", "Original")
    frame = wx.Frame(None)
    dlg = TagEditorDialog(frame, tags, filename="book.mp3")
    dlg.controls["album"].SetValue("Changed")
    dlg.result()
    assert tags.get("album") == "Original"
    dlg.Destroy()
    frame.Destroy()


def test_a_boolean_field_is_a_checkbox(dialog: object) -> None:
    assert isinstance(dialog.controls["compilation"], wx.CheckBox)


def test_a_pair_field_round_trips_as_number_of_total(wx_app: object) -> None:
    tags = AudioTags()
    tags.set("track", "3/12")
    frame = wx.Frame(None)
    dlg = TagEditorDialog(frame, tags, filename="book.mp3")
    assert dlg.controls["track"].GetValue() == "3"
    assert dlg.totals["track"].GetValue() == "12"
    assert dlg.result().get("track") == "3/12"
    dlg.Destroy()
    frame.Destroy()
```

Check `tests/conftest.py` for the existing wx app fixture name and the wx test group marker, and match them; the names above (`wx_app`, `xdist_group("wx")`) assume the repo's existing convention.

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/unit/ui/test_tag_editor_dialog.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'quill.ui.audio_studio.tag_editor'`

- [ ] **Step 3: Write the implementation**

Create `quill/ui/audio_studio/tag_editor.py`:

```python
"""The Tag Editor — every tag of an audio file, on five keyboard-reachable pages.

The Chapter Workbench's five quick fields cover the audiobook case; this is
the rest. The dialog builds itself from
:data:`quill.core.speech.audio_tags.TAG_FIELDS`, so a new tag is a table edit
in the core module and needs no change here.

It is a pure editor: in an :class:`AudioTags`, out an edited copy through
:meth:`TagEditorDialog.result`. It never writes a file — the caller does that
on the background runner, so the UI thread never blocks on a save.

Three accessibility rules shape the layout. Each page is its own class so its
mnemonics get their own namespace (only the visible notebook page's controls
are reachable, so this is true as well as convenient). Each label is created
*before* the control it labels, because screen readers pair them by creation
order. And every control names itself and carries its own help sentence
inline, because that is what the audits can verify.
"""

from __future__ import annotations

from collections.abc import Callable

import wx

from quill.core.i18n import _
from quill.core.speech.audio_tags import (
    GROUPS,
    AudioTags,
    CoverArt,
    TagField,
    TagReadError,
    cover_extension,
    describe_cover,
    fields_in,
    load_cover,
)
from quill.ui.audio_studio.pages_base import set_accessible_name
from quill.ui.dialog_contract import apply_modal_ids, show_message_box


def _plain(label: str) -> str:
    """A field label as a screen reader should hear it: no ampersand, no colon."""
    return label.replace("&", "").rstrip(": ").strip()


class TagPagePanel(wx.Panel):
    """One notebook page: every field of one group, as a two-column grid.

    Its own class, and not a method on the dialog, for two reasons. GATE-14
    scopes a non-dialog class per method, so each page's mnemonics live in
    their own namespace -- which matches Windows, where only the visible
    page's access keys can fire. And a page that owns its own controls can be
    read, changed and tested without the dialog around it.
    """

    def __init__(self, parent: wx.Window, group: str) -> None:
        super().__init__(parent, name=f"audio_studio.tag_editor.{group}")
        self.controls: dict[str, wx.Window] = {}
        self.totals: dict[str, wx.TextCtrl] = {}
        self._fields = fields_in(group)

        grid = wx.FlexGridSizer(cols=2, vgap=6, hgap=8)
        grid.AddGrowableCol(1, 1)
        for field in self._fields:
            self._add_field(grid, field)
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(grid, 1, wx.EXPAND | wx.ALL, 10)
        self.SetSizer(root)

    def _add_field(self, grid: wx.FlexGridSizer, field: TagField) -> None:
        """Label first, then the control -- the order screen readers depend on."""
        if field.kind == "bool":
            # A checkbox carries its own label, so it spans both columns and
            # there is no StaticText to order against.
            grid.Add(wx.StaticText(self, label=""), 0)
            check = wx.CheckBox(self, label=field.label)
            check.SetHelpText(field.help)
            set_accessible_name(check, _plain(field.label))
            grid.Add(check, 0, wx.EXPAND)
            self.controls[field.key] = check
            return

        grid.Add(wx.StaticText(self, label=field.label), 0, wx.ALIGN_CENTER_VERTICAL)
        if field.kind == "pair":
            row = wx.BoxSizer(wx.HORIZONTAL)
            number = wx.TextCtrl(self, size=wx.Size(70, -1))
            number.SetHelpText(field.help)
            set_accessible_name(number, f"{_plain(field.label)} number")
            row.Add(number, 0, wx.RIGHT, 6)
            row.Add(
                wx.StaticText(self, label=_("of")), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6
            )
            total = wx.TextCtrl(self, size=wx.Size(70, -1))
            total.SetHelpText(field.help)
            set_accessible_name(total, f"{_plain(field.label)} total")
            row.Add(total, 0)
            grid.Add(row, 0, wx.EXPAND)
            self.controls[field.key] = number
            self.totals[field.key] = total
            return

        style = wx.TE_MULTILINE if field.kind == "multiline" else 0
        size = wx.Size(-1, 90) if field.kind == "multiline" else wx.DefaultSize
        ctrl = wx.TextCtrl(self, style=style, size=size)
        ctrl.SetHelpText(field.help)
        set_accessible_name(ctrl, _plain(field.label))
        grid.Add(ctrl, 0, wx.EXPAND)
        self.controls[field.key] = ctrl

    def seed(self, tags: AudioTags) -> None:
        """Fill every control on this page from *tags*."""
        for field in self._fields:
            value = tags.get(field.key)
            ctrl = self.controls[field.key]
            if field.kind == "bool":
                ctrl.SetValue(bool(value))
            elif field.kind == "pair":
                number, _sep, total = value.partition("/")
                ctrl.SetValue(number)
                self.totals[field.key].SetValue(total)
            else:
                ctrl.SetValue(value)

    def collect(self, tags: AudioTags) -> None:
        """Write every control on this page back into *tags*."""
        for field in self._fields:
            ctrl = self.controls[field.key]
            if field.kind == "bool":
                tags.set(field.key, "1" if ctrl.GetValue() else "")
            elif field.kind == "pair":
                number = ctrl.GetValue().strip()
                total = self.totals[field.key].GetValue().strip()
                tags.set(field.key, f"{number}/{total}" if total else number)
            else:
                tags.set(field.key, ctrl.GetValue())


class TagEditorDialog(wx.Dialog):
    """Edit every tag of one audio file. Returns the edit; never writes it."""

    def __init__(
        self,
        parent: wx.Window,
        tags: AudioTags,
        *,
        filename: str,
        announce: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(
            parent,
            title=str(_("Tag Editor")),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            name="audio_studio.tag_editor",
        )
        self._tags = tags.copy()
        self._announce_fn = announce
        self.pages: dict[str, TagPagePanel] = {}
        self.controls: dict[str, wx.Window] = {}
        self.totals: dict[str, wx.TextCtrl] = {}

        root = wx.BoxSizer(wx.VERTICAL)
        heading = wx.StaticText(
            self,
            label=_("Tags for {name}").format(name=filename),
            name="audio_studio.tag_editor_heading",
        )
        heading.SetFont(heading.GetFont().Scaled(1.2).Bold())
        root.Add(heading, 0, wx.ALL, 10)

        notebook = wx.Notebook(self, name="audio_studio.tag_editor_pages")
        notebook.SetHelpText(
            "The tags are grouped over five pages. Ctrl+Tab moves to the next "
            "page and Ctrl+Shift+Tab to the previous one; Tab moves between "
            "the fields of the page you are on."
        )
        for group, label in GROUPS:
            page = TagPagePanel(notebook, group)
            page.seed(self._tags)
            notebook.AddPage(page, str(_(label)))
            self.pages[group] = page
            self.controls.update(page.controls)
            self.totals.update(page.totals)
        self._cover_page = CoverPagePanel(notebook, self._tags.cover, announce=announce)
        notebook.AddPage(self._cover_page, str(_("Cover art")))
        self.pages["cover"] = self._cover_page
        root.Add(notebook, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        ok_btn = wx.Button(self, wx.ID_OK, label=_("OK"))
        ok_btn.SetHelpText(
            "Keeps these tag edits and closes the window. Nothing is written "
            "to the file until you save in the Workbench."
        )
        cancel_btn = wx.Button(self, wx.ID_CANCEL, label=_("Cancel"))
        cancel_btn.SetHelpText("Discards every tag edit made in this window.")
        buttons.AddStretchSpacer()
        buttons.Add(ok_btn, 0, wx.RIGHT, 6)
        buttons.Add(cancel_btn, 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

        apply_modal_ids(self, ok_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        self.SetSizer(root)
        self.SetMinSize(wx.Size(620, 560))
        self.Fit()
        self.CentreOnParent()

    def _announce(self, text: str) -> None:
        if self._announce_fn is not None:
            self._announce_fn(text)

    def result(self) -> AudioTags:
        """The edited tags. The `AudioTags` passed in is never mutated."""
        edited = self._tags.copy()
        for group, _label in GROUPS:
            self.pages[group].collect(edited)
        edited.cover = self._cover_page.cover
        return edited
```

Check `apply_modal_ids`'s real signature in `quill/ui/dialog_contract.py:45` before writing this call; pass whatever keyword names it actually declares.

- [ ] **Step 4: Run the tests (they will still fail on `CoverPagePanel`)**

Run: `pytest tests/unit/ui/test_tag_editor_dialog.py -q`
Expected: FAIL — `NameError: name 'CoverPagePanel' is not defined`. Task 9 adds it. Do not stub it here; write it properly in the next task.

- [ ] **Step 5: Commit the work in progress only after Task 9**

This task and Task 9 land together — `TagEditorDialog` does not construct without the cover page. Move straight to Task 9 and commit both.

---

### Task 9: The cover art page

**Files:**
- Modify: `quill/ui/audio_studio/tag_editor.py`
- Test: `tests/unit/ui/test_tag_editor_dialog.py`

**Interfaces:**
- Consumes: `CoverArt`, `describe_cover`, `load_cover`, `cover_extension`, `TagReadError` from Task 3
- Produces: `CoverPagePanel(parent, cover, *, announce=None)` with a `cover: CoverArt | None` attribute

The text description is the primary readout, not the thumbnail — a picture tells a sighted user everything and a screen-reader user nothing.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/ui/test_tag_editor_dialog.py`:

```python
from quill.ui.audio_studio.tag_editor import CoverPagePanel  # noqa: E402


def test_cover_page_describes_absent_art(wx_app: object) -> None:
    frame = wx.Frame(None)
    page = CoverPagePanel(frame, None)
    assert "No cover art" in page.summary.GetLabel()
    assert page.cover is None
    frame.Destroy()


def test_cover_page_describes_present_art(wx_app: object) -> None:
    frame = wx.Frame(None)
    art = CoverArt(data=b"\x89PNG\r\n\x1a\n" + b"\x00" * 40, mime="image/png")
    page = CoverPagePanel(frame, art)
    assert "PNG" in page.summary.GetLabel()
    frame.Destroy()


def test_cover_page_remove_clears_the_art_and_the_summary(wx_app: object) -> None:
    frame = wx.Frame(None)
    art = CoverArt(data=b"\x89PNG\r\n\x1a\n" + b"\x00" * 40, mime="image/png")
    spoken: list[str] = []
    page = CoverPagePanel(frame, art, announce=spoken.append)
    page.remove_cover()
    assert page.cover is None
    assert "No cover art" in page.summary.GetLabel()
    assert spoken == ["Cover art removed."]
    frame.Destroy()


def test_cover_page_set_cover_updates_summary_and_announces(wx_app: object) -> None:
    frame = wx.Frame(None)
    spoken: list[str] = []
    page = CoverPagePanel(frame, None, announce=spoken.append)
    page.set_cover(CoverArt(data=b"\xff\xd8\xff" + b"\x00" * 40, mime="image/jpeg"))
    assert page.cover is not None
    assert "JPEG" in page.summary.GetLabel()
    assert spoken and spoken[0].startswith("Cover art loaded")
    frame.Destroy()


def test_cover_page_controls_are_helped_and_named(wx_app: object) -> None:
    frame = wx.Frame(None)
    page = CoverPagePanel(frame, None)
    for child in page.GetChildren():
        if isinstance(child, wx.Button):
            assert child.GetHelpText(), f"{child.GetLabel()} has no help"
    frame.Destroy()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/unit/ui/test_tag_editor_dialog.py -q -k cover`
Expected: FAIL — `ImportError: cannot import name 'CoverPagePanel'`

- [ ] **Step 3: Write the implementation**

Insert `CoverPagePanel` into `quill/ui/audio_studio/tag_editor.py`, above `TagEditorDialog`:

```python
class CoverPagePanel(wx.Panel):
    """The embedded cover image: what it is, and how to change it.

    The description is a text readout first and a thumbnail second, in that
    order, because a picture tells a sighted user everything about the art and
    a screen-reader user nothing at all. Its own class, like the tag pages,
    so its three buttons hold their own mnemonic namespace.
    """

    def __init__(
        self,
        parent: wx.Window,
        cover: CoverArt | None,
        *,
        announce: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(parent, name="audio_studio.tag_editor.cover")
        self.cover = cover
        self._announce_fn = announce

        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(self, label=_("Current cover art:")),
            0,
            wx.LEFT | wx.TOP,
            10,
        )
        self.summary = wx.StaticText(
            self, label=describe_cover(cover), name="audio_studio.tag_editor.cover_summary"
        )
        root.Add(self.summary, 0, wx.EXPAND | wx.ALL, 10)

        self._thumbnail = wx.StaticBitmap(self, name="audio_studio.tag_editor.cover_image")
        root.Add(self._thumbnail, 0, wx.LEFT | wx.BOTTOM, 10)

        row = wx.BoxSizer(wx.HORIZONTAL)
        load_btn = wx.Button(self, label=_("&Load image..."))
        load_btn.SetHelpText(
            "Chooses a JPEG or PNG image to embed as this file's cover art, "
            "replacing whatever is there now. Images over 8 MB are refused."
        )
        load_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_load())
        save_btn = wx.Button(self, label=_("&Save image as..."))
        save_btn.SetHelpText(
            "Writes the embedded cover art out to a file of its own, leaving "
            "the audio file untouched."
        )
        save_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_save())
        remove_btn = wx.Button(self, label=_("&Remove image"))
        remove_btn.SetHelpText(
            "Takes the cover art off this file. The change is kept when you "
            "save in the Workbench, not before."
        )
        remove_btn.Bind(wx.EVT_BUTTON, lambda _e: self.remove_cover())
        for btn in (load_btn, save_btn, remove_btn):
            row.Add(btn, 0, wx.RIGHT, 6)
        root.Add(row, 0, wx.LEFT | wx.BOTTOM, 10)

        self.SetSizer(root)
        self._refresh()

    def _announce(self, text: str) -> None:
        if self._announce_fn is not None:
            self._announce_fn(text)

    def _refresh(self) -> None:
        """Re-read the summary label and the thumbnail from ``self.cover``."""
        self.summary.SetLabel(describe_cover(self.cover))
        bitmap = wx.NullBitmap
        if self.cover is not None:
            import io

            try:
                image = wx.Image(io.BytesIO(self.cover.data))
                if image.IsOk():
                    scale = 160 / max(image.GetWidth(), image.GetHeight(), 1)
                    bitmap = image.Scale(
                        max(1, int(image.GetWidth() * scale)),
                        max(1, int(image.GetHeight() * scale)),
                        wx.IMAGE_QUALITY_HIGH,
                    ).ConvertToBitmap()
            except Exception:  # noqa: BLE001 - an undecodable image is not fatal
                bitmap = wx.NullBitmap
        self._thumbnail.SetBitmap(bitmap)
        self.Layout()

    def set_cover(self, cover: CoverArt) -> None:
        """Replace the art and say so — a change on a control that has no focus."""
        self.cover = cover
        self._refresh()
        self._announce(str(_("Cover art loaded. {summary}")).format(
            summary=describe_cover(cover)
        ))

    def remove_cover(self) -> None:
        """Drop the art and say so."""
        if self.cover is None:
            self._announce(str(_("There is no cover art to remove.")))
            return
        self.cover = None
        self._refresh()
        self._announce(str(_("Cover art removed.")))

    def _on_load(self) -> None:
        with wx.FileDialog(
            self,
            str(_("Choose a cover image")),
            wildcard=_("Images (*.jpg;*.jpeg;*.png)|*.jpg;*.jpeg;*.png"),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:  # GATE-42-OK: native file picker
                return
            path = dlg.GetPath()
        from pathlib import Path

        try:
            self.set_cover(load_cover(Path(path)))
        except TagReadError as exc:
            show_message_box(str(exc), str(_("Tag Editor")), wx.OK | wx.ICON_ERROR, self)

    def _on_save(self) -> None:
        if self.cover is None:
            self._announce(str(_("There is no cover art to save.")))
            return
        suffix = cover_extension(self.cover)
        with wx.FileDialog(
            self,
            str(_("Save the cover image as")),
            defaultFile=f"cover{suffix}",
            wildcard=f"*{suffix}|*{suffix}",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:  # GATE-42-OK: native file picker
                return
            out = dlg.GetPath()
        from pathlib import Path

        try:
            Path(out).write_bytes(self.cover.data)
        except OSError as exc:
            show_message_box(
                str(_("Could not save the image: {error}")).format(error=exc),
                str(_("Tag Editor")),
                wx.OK | wx.ICON_ERROR,
                self,
            )
            return
        self._announce(str(_("Saved {name}")).format(name=Path(out).name))
```

- [ ] **Step 4: Run the whole dialog test file**

Run: `pytest tests/unit/ui/test_tag_editor_dialog.py -q`
Expected: PASS, all tests from Tasks 8 and 9.

- [ ] **Step 5: Run the accessibility gates**

```bash
python -m quill.tools.check_dialog_zorder
python -m quill.tools.check_access_keys
python -m quill.tools.studio_help_audit
python -m quill.tools.accessible_name_audit
```

Expected: no violations attributed to `tag_editor.py`. The help and accessible-name audits will report **new** sites not yet in their snapshots — that is expected and gets regenerated in Task 14, but any site reported as a *violation* (rather than as new) must be fixed here.

- [ ] **Step 6: Lint and commit**

```bash
ruff check quill/ui/audio_studio/tag_editor.py tests/unit/ui/test_tag_editor_dialog.py
ruff format --check quill/ui/audio_studio/tag_editor.py
git add quill/ui/audio_studio/tag_editor.py tests/unit/ui/test_tag_editor_dialog.py
git commit -m "feat(studio): add the Tag Editor dialog with cover art"
```

---

### Task 10: The chapter edits mixin — add, delete, edit, preview

**Files:**
- Create: `quill/ui/audio_studio/chapter_workbench_edits.py`
- Test: `tests/unit/ui/test_chapter_workbench_edits.py`

**Interfaces:**
- Consumes: `add_chapter`, `delete_chapter`, `set_chapter_bounds`, `Chapter`, `ChapterEditError` from Task 6; `format_timestamp`, `parse_chapter_text` from `chapter_io`
- Produces: `ChapterEditsMixin` with `_on_add_chapter`, `_on_delete_chapter`, `_on_edit_chapter`, `_on_preview_chapter`, `_stop_at_ms: int | None`, `_check_preview_stop()`; `ChapterDetailsDialog(parent, chapter, *, lower_ms, upper_ms)` with `values() -> tuple[str, int | None, int | None, str, str]` (an unparseable time reads back as `None`)

The mixin expects its host to provide `self._book`, `self._selected_index()`, `self._apply(chapters, select=..., spoken=...)`, `self._error(message)`, `self._announce(text)`, `self.player`, and `self.settings_nudge_ms`. Those all exist on `ChapterWorkbenchDialog` (the last is added in Task 12).

- [ ] **Step 1: Write the failing test**

Create `tests/unit/ui/test_chapter_workbench_edits.py`:

```python
"""The Chapter Workbench's add/delete/edit/preview handlers, host-free."""

from __future__ import annotations

import pytest

wx = pytest.importorskip("wx")

from quill.core.speech.chapters import Chapter  # noqa: E402
from quill.ui.audio_studio.chapter_workbench_edits import (  # noqa: E402
    ChapterEditsMixin,
)

pytestmark = pytest.mark.xdist_group("wx")


class _FakePlayer:
    def __init__(self) -> None:
        self.sought: list[int] = []
        self.played = 0
        self._head = 5_000

    def playhead_ms(self) -> int:
        return self._head

    def seek_to(self, ms: int) -> None:
        self.sought.append(ms)
        self._head = ms

    def play(self) -> None:
        self.played += 1

    def pause(self) -> None:
        pass


class _Host(ChapterEditsMixin):
    """The smallest thing the mixin needs: a book, a selection, and a player."""

    def __init__(self, chapters: list[Chapter]) -> None:
        from quill.core.speech.book_file import BookFile
        from quill.core.speech.ffmpeg import AudioMetadata
        from pathlib import Path

        self._book = BookFile(
            path=Path("book.mp3"),
            tags=AudioMetadata(),
            chapters=chapters,
            total_ms=chapters[-1].end_ms,
        )
        self.player = _FakePlayer()
        self.selection = 1
        self.errors: list[str] = []
        self.spoken: list[str] = []
        self.settings_nudge_ms = 500
        self._stop_at_ms: int | None = None

    def _selected_index(self) -> int:
        return self.selection

    def _apply(self, chapters: list[Chapter], *, select: int, spoken: str) -> None:
        self._book.chapters = chapters
        self.selection = select
        self.spoken.append(spoken)

    def _error(self, message: str) -> None:
        self.errors.append(message)

    def _announce(self, text: str) -> None:
        self.spoken.append(text)


def _three() -> list[Chapter]:
    return [
        Chapter(index=0, title="One", start_ms=0, end_ms=10_000),
        Chapter(index=1, title="Two", start_ms=10_000, end_ms=20_000),
        Chapter(index=2, title="Three", start_ms=20_000, end_ms=30_000),
    ]


def test_delete_removes_the_selected_chapter() -> None:
    host = _Host(_three())
    host._on_delete_chapter()
    assert [c.title for c in host._book.chapters] == ["One", "Three"]
    assert not host.errors


def test_delete_the_only_chapter_reports_the_refusal() -> None:
    host = _Host([Chapter(index=0, title="All", start_ms=0, end_ms=10_000)])
    host.selection = 0
    host._on_delete_chapter()
    assert host.errors
    assert len(host._book.chapters) == 1


def test_delete_with_nothing_selected_reports_it() -> None:
    host = _Host(_three())
    host.selection = -1
    host._on_delete_chapter()
    assert host.errors


def test_preview_seeks_to_the_start_and_arms_the_stop() -> None:
    host = _Host(_three())
    host._on_preview_chapter()
    assert host.player.sought == [10_000]
    assert host.player.played == 1
    assert host._stop_at_ms == 20_000


def test_preview_stop_fires_once_at_the_chapter_end() -> None:
    host = _Host(_three())
    host._on_preview_chapter()
    host.player._head = 19_000
    assert host._check_preview_stop() is False
    host.player._head = 20_001
    assert host._check_preview_stop() is True
    assert host._stop_at_ms is None
    assert host._check_preview_stop() is False
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/unit/ui/test_chapter_workbench_edits.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'quill.ui.audio_studio.chapter_workbench_edits'`

- [ ] **Step 3: Write the implementation**

Create `quill/ui/audio_studio/chapter_workbench_edits.py`:

```python
"""The Chapter Workbench's chapter-editing handlers, as a mixin.

Extracted from :mod:`quill.ui.audio_studio.chapter_workbench` so that module
stays inside its GATE-11 size budget while the Workbench gains add, delete,
edit, preview and nudge. The mixin holds handlers only -- the Workbench still
builds the buttons and owns the widgets -- and every chapter computation lives
in the wx-free :mod:`quill.core.speech.chapters`.

The host must provide ``_book``, ``_selected_index()``, ``_apply()``,
``_error()``, ``_announce()``, ``player`` and ``settings_nudge_ms``.
"""

from __future__ import annotations

import wx

from quill.core.i18n import _
from quill.core.speech.chapter_io import format_timestamp
from quill.core.speech.chapters import (
    Chapter,
    ChapterEditError,
    add_chapter,
    delete_chapter,
    set_chapter_bounds,
)
from quill.ui.dialog_contract import apply_modal_ids


def _parse_timestamp(text: str) -> int | None:
    """``h:mm:ss.mmm`` / ``mm:ss`` / plain seconds -> milliseconds, or None."""
    raw = text.strip()
    if not raw:
        return None
    parts = raw.split(":")
    try:
        seconds = 0.0
        for part in parts:
            seconds = seconds * 60 + float(part)
    except ValueError:
        return None
    return int(round(seconds * 1000))


class ChapterDetailsDialog(wx.Dialog):
    """Type a chapter's title, exact start and end, and its Podcasting 2.0 extras.

    Its own class so its mnemonics are scoped to it, and so the Workbench does
    not grow a sixth inline form.
    """

    def __init__(
        self,
        parent: wx.Window,
        chapter: Chapter,
        *,
        lower_ms: int,
        upper_ms: int,
    ) -> None:
        super().__init__(
            parent,
            title=str(_("Edit chapter")),
            style=wx.DEFAULT_DIALOG_STYLE,
            name="audio_studio.chapter_details",
        )
        from quill.ui.audio_studio.pages_base import set_accessible_name

        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                self,
                label=_(
                    "Times are h:mm:ss.mmm. This chapter may run between "
                    "{lower} and {upper}."
                ).format(
                    lower=format_timestamp(lower_ms), upper=format_timestamp(upper_ms)
                ),
            ),
            0,
            wx.ALL,
            10,
        )
        grid = wx.FlexGridSizer(cols=2, vgap=6, hgap=8)
        grid.AddGrowableCol(1, 1)

        def row(label: str, value: str, help_text: str) -> wx.TextCtrl:
            # Label first, then the control: A11Y-Z-ORDER. The control is
            # created here rather than passed in, which is what keeps
            # check_dialog_zorder.py satisfied.
            grid.Add(wx.StaticText(self, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
            ctrl = wx.TextCtrl(self, value=value)
            ctrl.SetHelpText(help_text)
            set_accessible_name(ctrl, label.replace("&", "").rstrip(": "))
            grid.Add(ctrl, 0, wx.EXPAND)
            return ctrl

        self._title = row(
            _("&Title:"),
            chapter.title,
            "The chapter's name, as every player will announce it.",
        )
        self._start = row(
            _("&Start:"),
            format_timestamp(chapter.start_ms),
            "Where this chapter begins, as h:mm:ss.mmm. Moving it moves the "
            "end of the chapter before it, so the book stays gapless.",
        )
        self._end = row(
            _("&End:"),
            format_timestamp(chapter.end_ms),
            "Where this chapter ends, as h:mm:ss.mmm. Moving it moves the "
            "start of the chapter after it.",
        )
        self._url = row(
            _("&Link:"),
            chapter.url,
            "An optional web link for this chapter, carried in the "
            "Podcasting 2.0 chapters file. Most players show it as a button.",
        )
        self._image = row(
            _("&Image:"),
            chapter.image,
            "An optional image URL for this chapter, carried in the "
            "Podcasting 2.0 chapters file.",
        )
        root.Add(grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        ok_btn = wx.Button(self, wx.ID_OK, label=_("OK"))
        ok_btn.SetHelpText("Applies these chapter details to the list.")
        cancel_btn = wx.Button(self, wx.ID_CANCEL, label=_("Cancel"))
        cancel_btn.SetHelpText("Leaves the chapter as it was.")
        buttons.AddStretchSpacer()
        buttons.Add(ok_btn, 0, wx.RIGHT, 6)
        buttons.Add(cancel_btn, 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

        apply_modal_ids(self, ok_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        self.SetSizer(root)
        self.Fit()
        self.CentreOnParent()

    def values(self) -> tuple[str, int | None, int | None, str, str]:
        """Title, start ms, end ms, link, image. A bad time reads back as None."""
        return (
            self._title.GetValue().strip(),
            _parse_timestamp(self._start.GetValue()),
            _parse_timestamp(self._end.GetValue()),
            self._url.GetValue().strip(),
            self._image.GetValue().strip(),
        )


class ChapterEditsMixin:
    """Add, delete, edit and preview handlers for the Chapter Workbench."""

    #: When set, playback stops as soon as the playhead passes this point.
    _stop_at_ms: int | None = None

    def _on_add_chapter(self) -> None:
        """Insert a marker at the playhead (or a typed time) and name it."""
        default = format_timestamp(self.player.playhead_ms())
        with wx.TextEntryDialog(
            self,
            str(
                _(
                    "Where should the new chapter start? Times are h:mm:ss.mmm; "
                    "the playhead's position is filled in."
                )
            ),
            str(_("Add chapter")),
            default,
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:  # GATE-42-OK: simple text prompt
                return
            at_ms = _parse_timestamp(dlg.GetValue())
        if at_ms is None:
            self._error(str(_("That is not a time. Use h:mm:ss.mmm.")))
            return
        with wx.TextEntryDialog(
            self,
            str(_("What is the new chapter called?")),
            str(_("Add chapter")),
            str(_("New chapter")),
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:  # GATE-42-OK: simple text prompt
                return
            title = dlg.GetValue().strip() or str(_("New chapter"))
        try:
            chapters = add_chapter(self._book.chapters, at_ms, title=title)
        except ChapterEditError as exc:
            self._error(str(exc))
            return
        new_index = next(
            (i for i, c in enumerate(chapters) if c.start_ms == at_ms), len(chapters) - 1
        )
        self._apply(
            chapters,
            select=new_index,
            spoken=str(_("Added {title} at {at}")).format(
                title=title, at=format_timestamp(at_ms)
            ),
        )

    def _on_delete_chapter(self) -> None:
        """Remove the selected chapter's marker. The audio is untouched."""
        index = self._selected_index()
        if index < 0:
            self._error(str(_("No chapter is selected.")))
            return
        title = self._book.chapters[index].title
        try:
            chapters = delete_chapter(self._book.chapters, index)
        except ChapterEditError as exc:
            self._error(str(exc))
            return
        self._apply(
            chapters,
            select=max(0, index - 1),
            spoken=str(_("Deleted {title}. The audio is unchanged.")).format(title=title),
        )

    def _on_edit_chapter(self) -> None:
        """Type this chapter's title, exact start and end, and its extras."""
        index = self._selected_index()
        if index < 0:
            self._error(str(_("No chapter is selected.")))
            return
        chapters = self._book.chapters
        chapter = chapters[index]
        lower = chapters[index - 1].start_ms if index > 0 else chapter.start_ms
        upper = chapters[index + 1].end_ms if index + 1 < len(chapters) else chapter.end_ms
        dlg = ChapterDetailsDialog(self, chapter, lower_ms=lower, upper_ms=upper)
        try:
            if dlg.ShowModal() != wx.ID_OK:  # GATE-42-OK: shown by the mixin's host
                return
            title, start_ms, end_ms, url, image = dlg.values()
        finally:
            dlg.Destroy()
        if start_ms is None or end_ms is None:
            self._error(str(_("Start and end must be times, as h:mm:ss.mmm.")))
            return
        try:
            updated = set_chapter_bounds(chapters, index, start_ms, end_ms)
        except ChapterEditError as exc:
            self._error(str(exc))
            return
        updated[index].title = title or chapter.title
        updated[index].url = url
        updated[index].image = image
        self._apply(
            updated,
            select=index,
            spoken=str(_("{title} now runs {start} to {end}")).format(
                title=updated[index].title,
                start=format_timestamp(updated[index].start_ms),
                end=format_timestamp(updated[index].end_ms),
            ),
        )

    def _on_preview_chapter(self) -> None:
        """Play the selected chapter from its start and stop at its end."""
        index = self._selected_index()
        if index < 0:
            self._error(str(_("No chapter is selected.")))
            return
        chapter = self._book.chapters[index]
        self.player.seek_to(chapter.start_ms)
        self._stop_at_ms = chapter.end_ms
        self.player.play()

    def _check_preview_stop(self) -> bool:
        """Stop playback if an armed preview has run past its end. True if stopped.

        Called from the Workbench's existing player tick rather than a second
        timer, so a preview costs no extra wx.Timer.
        """
        if self._stop_at_ms is None:
            return False
        if self.player.playhead_ms() < self._stop_at_ms:
            return False
        self._stop_at_ms = None
        self.player.pause()
        return True
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/unit/ui/test_chapter_workbench_edits.py -q`
Expected: PASS, 5 tests.

- [ ] **Step 5: Lint and commit**

```bash
ruff check quill/ui/audio_studio/chapter_workbench_edits.py tests/unit/ui/test_chapter_workbench_edits.py
git add quill/ui/audio_studio/chapter_workbench_edits.py tests/unit/ui/test_chapter_workbench_edits.py
git commit -m "feat(studio): add, delete, edit and preview chapters in the Workbench"
```

---

### Task 11: Nudging in the UI — buttons, keys, and speech that does not flood

**Files:**
- Modify: `quill/ui/audio_studio/chapter_workbench_edits.py`
- Test: `tests/unit/ui/test_chapter_workbench_edits.py`

**Interfaces:**
- Consumes: `nudge_chapter_start`, `NUDGE_STEPS_MS` from Task 7
- Produces: on `ChapterEditsMixin`: `_on_nudge(direction: int, *, multiplier: int = 1)`, `_on_hear_boundary()`, `_nudge_key_handler(event)`; attributes `_nudge_run_active: bool`, `_wall_announced: bool`

A nudge is a repeated keypress, so a full sentence per press is unusable. Each press speaks the new time alone; the full sentence follows once the run goes quiet. Hitting the wall is announced once per run.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/ui/test_chapter_workbench_edits.py`:

```python
def test_nudge_back_moves_the_marker_by_the_step() -> None:
    host = _Host(_three())
    host._on_nudge(-1)
    assert host._book.chapters[1].start_ms == 9_500
    assert host._book.chapters[0].end_ms == 9_500


def test_nudge_forward_uses_the_configured_step() -> None:
    host = _Host(_three())
    host.settings_nudge_ms = 2_000
    host._on_nudge(1)
    assert host._book.chapters[1].start_ms == 12_000


def test_nudge_multiplier_moves_ten_steps() -> None:
    host = _Host(_three())
    host._on_nudge(1, multiplier=10)
    assert host._book.chapters[1].start_ms == 15_000


def test_nudge_speaks_the_bare_time_not_a_sentence() -> None:
    host = _Host(_three())
    host.spoken.clear()
    host._on_nudge(-1)
    assert host.spoken == ["0:00:09.500"]


def test_nudge_at_the_wall_announces_once_per_run() -> None:
    host = _Host([
        Chapter(index=0, title="One", start_ms=0, end_ms=500),
        Chapter(index=1, title="Two", start_ms=500, end_ms=1_000),
    ])
    host.spoken.clear()
    host._on_nudge(-1)
    host._on_nudge(-1)
    assert host.spoken == ["Cannot move further."]


def test_nudge_on_the_first_chapter_reports_the_refusal() -> None:
    host = _Host(_three())
    host.selection = 0
    host._on_nudge(1)
    assert host.errors


def test_hear_boundary_plays_a_window_around_the_marker() -> None:
    host = _Host(_three())
    host._on_hear_boundary()
    assert host.player.sought == [7_000]
    assert host._stop_at_ms == 12_000
    assert host.player.played == 1


def test_hear_boundary_clamps_the_lead_at_the_start_of_the_file() -> None:
    host = _Host(_three())
    host.selection = 1
    host._book.chapters[1].start_ms = 1_000
    host._book.chapters[0].end_ms = 1_000
    host._on_hear_boundary()
    assert host.player.sought == [0]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/unit/ui/test_chapter_workbench_edits.py -q -k nudge`
Expected: FAIL — `AttributeError: '_Host' object has no attribute '_on_nudge'`

- [ ] **Step 3: Write the implementation**

Add to the imports of `quill/ui/audio_studio/chapter_workbench_edits.py`:

```python
from quill.core.speech.chapters import nudge_chapter_start
```

Add these constants above `ChapterEditsMixin`:

```python
#: How long a run of nudges must go quiet before the full sentence is spoken.
_NUDGE_SETTLE_MS = 600
#: The window "Hear boundary" plays: this much before the marker, and after.
_BOUNDARY_LEAD_MS = 3_000
_BOUNDARY_TAIL_MS = 2_000
```

Add to `ChapterEditsMixin`:

```python
    #: True while a run of nudges is in flight, so the wall is announced once.
    _wall_announced: bool = False

    def _on_nudge(self, direction: int, *, multiplier: int = 1) -> None:
        """Move the selected chapter's start by one step (or ten) either way.

        Announces the bare new time, not a sentence: this runs at key-repeat
        speed, and a sentence repeated ten times a second is noise. The full
        sentence follows from :meth:`_settle_nudge` once the run goes quiet.
        """
        index = self._selected_index()
        if index < 0:
            self._error(str(_("No chapter is selected.")))
            return
        step = max(10, int(self.settings_nudge_ms)) * max(1, multiplier)
        try:
            chapters, applied = nudge_chapter_start(
                self._book.chapters, index, step * (1 if direction >= 0 else -1)
            )
        except ChapterEditError as exc:
            self._error(str(exc))
            return
        if applied == 0:
            if not self._wall_announced:
                self._wall_announced = True
                self._announce(str(_("Cannot move further.")))
            return
        self._wall_announced = False
        self._apply(
            chapters,
            select=index,
            spoken=format_timestamp(chapters[index].start_ms),
        )
        self._schedule_nudge_settle(index)
        if self._hear_after_nudge():
            self._on_hear_boundary()

    def _hear_after_nudge(self) -> bool:
        """Whether the "hear the boundary after each nudge" box is ticked.

        Overridden by the Workbench, which owns the checkbox; the default of
        False keeps the mixin usable without one.
        """
        return False

    def _schedule_nudge_settle(self, index: int) -> None:
        """After the run goes quiet, speak the chapter in full, once."""
        if not hasattr(self, "CallLater"):
            return  # a host without wx timing (the tests) settles immediately

        def settle() -> None:
            chapters = self._book.chapters
            if not 0 <= index < len(chapters):
                return
            chapter = chapters[index]
            self._announce(
                str(_("{title} starts {start}, runs {dur}")).format(
                    title=chapter.title,
                    start=format_timestamp(chapter.start_ms),
                    dur=format_timestamp(chapter.duration_ms),
                )
            )

        if self._settle_timer is not None:
            self._settle_timer.Stop()
        self._settle_timer = wx.CallLater(_NUDGE_SETTLE_MS, settle)

    _settle_timer: object | None = None

    def _on_hear_boundary(self) -> None:
        """Play a few seconds either side of the selected chapter's start."""
        index = self._selected_index()
        if index < 0:
            self._error(str(_("No chapter is selected.")))
            return
        start = self._book.chapters[index].start_ms
        self.player.seek_to(max(0, start - _BOUNDARY_LEAD_MS))
        self._stop_at_ms = min(self._book.total_ms, start + _BOUNDARY_TAIL_MS)
        self.player.play()

    def _nudge_key_handler(self, event: wx.KeyEvent) -> None:
        """Alt+Left/Right nudge one step; add Shift for ten. Anything else passes.

        The Workbench has no menu bar to advertise these, so they are named in
        the buttons' help text and in the chapter list's own help.
        """
        code = event.GetKeyCode()
        if event.AltDown() and code in (wx.WXK_LEFT, wx.WXK_RIGHT):
            self._on_nudge(
                -1 if code == wx.WXK_LEFT else 1,
                multiplier=10 if event.ShiftDown() else 1,
            )
            return
        event.Skip()
```

Note on `_schedule_nudge_settle`: `wx.CallLater` needs a live wx app, which the mixin tests do not build, hence the `hasattr` guard. In the Workbench the mixin is on a `wx.Dialog`, so `CallLater` resolves and the settle fires.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/unit/ui/test_chapter_workbench_edits.py -q`
Expected: PASS. `test_nudge_speaks_the_bare_time_not_a_sentence` asserts the exact string `"0:00:09.500"` — if `format_timestamp` renders differently, fix the expectation to match the real format rather than changing the formatter.

- [ ] **Step 5: Lint and commit**

```bash
ruff check quill/ui/audio_studio/chapter_workbench_edits.py
git add quill/ui/audio_studio/chapter_workbench_edits.py tests/unit/ui/test_chapter_workbench_edits.py
git commit -m "feat(studio): nudge chapter markers by ear, with speech that does not flood"
```

---

### Task 12: Wire it all into the Chapter Workbench

**Files:**
- Modify: `quill/ui/audio_studio/chapter_workbench.py` (class declaration ~line 64, button rows ~line 152-261, tag collection ~line 568, save path ~line 594-643, close handler ~line 863)
- Modify: `quill/tools/module_size_budgets.json`
- Test: `tests/unit/ui/test_chapter_workbench_edits.py`

**Interfaces:**
- Consumes: `ChapterEditsMixin` (Task 10–11), `TagEditorDialog` (Task 8–9), `read_tags`, `write_tags`, `merge_audio_metadata`, `to_audio_metadata` (Tasks 2, 5)
- Produces: `ChapterWorkbenchDialog` with `settings_nudge_ms`, `_full_tags: AudioTags | None`, `_tags_dirty: bool`, `_chapters_dirty: bool`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/ui/test_chapter_workbench_edits.py`:

```python
def test_workbench_inherits_the_edits_mixin() -> None:
    from quill.ui.audio_studio.chapter_workbench import ChapterWorkbenchDialog

    assert issubclass(ChapterWorkbenchDialog, ChapterEditsMixin)


def test_workbench_declares_the_new_buttons(wx_app: object) -> None:
    """Every new operation is reachable by a button, not only by a key."""
    import inspect

    from quill.ui.audio_studio import chapter_workbench

    source = inspect.getsource(chapter_workbench)
    for label in (
        "Add chapter",
        "Delete chapter",
        "Edit chapter",
        "Preview chapter",
        "All",
        "Nudge back",
        "Nudge forward",
        "Hear boundary",
    ):
        assert label.replace(" ", "") in source.replace("&", "").replace(" ", ""), (
            f"no button for {label}"
        )
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/unit/ui/test_chapter_workbench_edits.py -q -k workbench`
Expected: FAIL — `ChapterWorkbenchDialog` is not a subclass of the mixin.

- [ ] **Step 3: Inherit the mixin and hold the new state**

In `quill/ui/audio_studio/chapter_workbench.py`, change the class declaration:

```python
class ChapterWorkbenchDialog(ChapterEditsMixin, wx.Dialog):
    """Edit an opened book's chapters and tags, with the player as the anchor."""
```

and add the import:

```python
from quill.ui.audio_studio.chapter_workbench_edits import ChapterEditsMixin
from quill.ui.audio_studio.tag_editor import TagEditorDialog
```

In `__init__`, beside `self._dirty = False`, replace that one flag with two and seed the nudge step:

```python
        self._chapters_dirty = False
        self._tags_dirty = False
        self._full_tags: object | None = None
        self.settings_nudge_ms = 500
        try:
            from quill.core.settings import load_settings

            self.settings_nudge_ms = int(
                load_settings().audio_studio_chapter_nudge_ms
            )
        except Exception:  # noqa: BLE001 - a settings failure must not block editing
            pass
```

Replace every remaining `self._dirty = True` with `self._chapters_dirty = True` and every `self._dirty = False` with a line clearing both flags. Check the real name of the settings loader in `quill/core/settings.py` and use it.

- [ ] **Step 4: Add the two new button rows**

After the existing `surgery_row`, add:

```python
        edit_row = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler, help_text in (
            (
                _("A&dd chapter..."),
                self._on_add_chapter,
                "Puts a new chapter marker at the playhead, or at a time you "
                "type, and asks what to call it. The audio is not cut.",
            ),
            (
                _("De&lete chapter"),
                self._on_delete_chapter,
                "Removes the highlighted chapter's marker. The audio is "
                "untouched -- it joins the neighbouring chapter.",
            ),
            (
                _("Ed&it chapter..."),
                self._on_edit_chapter,
                "Opens a window to type this chapter's title and its exact "
                "start and end, plus the optional link and image a "
                "Podcasting 2.0 player can show.",
            ),
            (
                _("Pre&view chapter"),
                self._on_preview_chapter,
                "Plays the highlighted chapter from its start and stops at "
                "its end, instead of running on into the next one.",
            ),
        ):
            btn = wx.Button(self, label=label)
            btn.SetHelpText(help_text)
            btn.Bind(wx.EVT_BUTTON, lambda _e, h=handler: h())
            edit_row.Add(btn, 0, wx.RIGHT, 6)
        root.Add(edit_row, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)

        nudge_row = wx.BoxSizer(wx.HORIZONTAL)
        back_btn = wx.Button(self, label=_("N&udge back"))
        back_btn.SetHelpText(
            "Moves the highlighted chapter's start earlier by one step. "
            "Alt+Left does the same from the chapter list, and Alt+Shift+Left "
            "moves ten steps at once."
        )
        back_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_nudge(-1))
        nudge_row.Add(back_btn, 0, wx.RIGHT, 6)
        fwd_btn = wx.Button(self, label=_("Nudge f&orward"))
        fwd_btn.SetHelpText(
            "Moves the highlighted chapter's start later by one step. "
            "Alt+Right does the same from the chapter list, and "
            "Alt+Shift+Right moves ten steps at once."
        )
        fwd_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_nudge(1))
        nudge_row.Add(fwd_btn, 0, wx.RIGHT, 6)
        # Label before control: A11Y-Z-ORDER.
        nudge_row.Add(
            wx.StaticText(self, label=_("Ste&p:")), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4
        )
        self._step_choice = wx.Choice(
            self, choices=[format_timestamp(ms) for ms in NUDGE_STEPS_MS]
        )
        self._step_choice.SetHelpText(
            "How far one nudge moves a marker. The step you pick is "
            "remembered for next time; the default is half a second."
        )
        set_accessible_name(self._step_choice, str(_("Nudge step")))
        self._step_choice.SetSelection(
            NUDGE_STEPS_MS.index(self.settings_nudge_ms)
            if self.settings_nudge_ms in NUDGE_STEPS_MS
            else NUDGE_STEPS_MS.index(500)
        )
        self._step_choice.Bind(wx.EVT_CHOICE, lambda _e: self._on_step_changed())
        nudge_row.Add(self._step_choice, 0, wx.RIGHT, 12)
        hear_btn = wx.Button(self, label=_("Hear boundar&y"))
        hear_btn.SetHelpText(
            "Plays three seconds before the highlighted chapter's start and "
            "two seconds after it, then stops -- the quickest way to judge a "
            "marker by ear."
        )
        hear_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_hear_boundary())
        nudge_row.Add(hear_btn, 0, wx.RIGHT, 6)
        self._hear_after = wx.CheckBox(self, label=_("Hear after each nud&ge"))
        self._hear_after.SetHelpText(
            "Plays the boundary automatically after every nudge. Off by "
            "default, because audio on every keypress should be asked for."
        )
        set_accessible_name(self._hear_after, str(_("Hear after each nudge")))
        nudge_row.Add(self._hear_after, 0, wx.ALIGN_CENTER_VERTICAL)
        root.Add(nudge_row, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
```

Add to the imports:

```python
from quill.core.speech.chapters import NUDGE_STEPS_MS
from quill.ui.audio_studio.pages_base import set_accessible_name
```

Bind the nudge keys on the chapter list, right after the existing `EVT_LISTBOX` binding:

```python
        self._chapter_list.Bind(wx.EVT_KEY_DOWN, self._nudge_key_handler)
        self._chapter_list.SetHelpText(
            "Every chapter, with its start and length. Alt+Left and Alt+Right "
            "nudge the highlighted chapter's start earlier or later by one "
            "step; hold Shift as well to move ten steps at once."
        )
```

Add the step handler and the checkbox hook as methods:

```python
    def _on_step_changed(self) -> None:
        """Remember the nudge step the user picked, for this session and the next."""
        selection = self._step_choice.GetSelection()
        if not 0 <= selection < len(NUDGE_STEPS_MS):
            return
        self.settings_nudge_ms = NUDGE_STEPS_MS[selection]
        try:
            from quill.core.settings import load_settings, save_settings

            settings = load_settings()
            settings.audio_studio_chapter_nudge_ms = self.settings_nudge_ms
            save_settings(settings)
        except Exception:  # noqa: BLE001 - failing to persist must not block editing
            pass

    def _hear_after_nudge(self) -> bool:
        return bool(self._hear_after.GetValue())
```

Use the repository's real settings load/save function names.

- [ ] **Step 5: Add the "All tags..." button and its handler**

Add to `io_row` (beside Import/Export/Split):

```python
        tags_btn = wx.Button(self, label=_("All ta&gs..."))
        tags_btn.SetHelpText(
            "Opens the Tag Editor: every tag this file can carry, over five "
            "pages, including cover art. The five fields below are the ones "
            "an audiobook needs; this is the rest."
        )
        tags_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_all_tags())
        io_row.Add(tags_btn, 0, wx.LEFT, 6)
```

and the handler:

```python
    def _on_all_tags(self) -> None:
        """Open the full Tag Editor, seeded from the file and the quick fields."""
        from quill.core.speech.audio_tags import merge_audio_metadata, read_tags

        self._collect_tags()
        try:
            base = self._full_tags if self._full_tags is not None else read_tags(
                self._book.path
            )
        except Exception as exc:  # noqa: BLE001 - an untagged file is still editable
            self._announce(str(_("Could not read the existing tags: {error}")).format(
                error=exc
            ))
            from quill.core.speech.audio_tags import AudioTags

            base = AudioTags()
        seeded = merge_audio_metadata(base, self._book.tags)
        dlg = TagEditorDialog(
            self,
            seeded,
            filename=self._book.path.name,
            announce=self._announce_fn,
        )
        try:
            if dlg.ShowModal() != wx.ID_OK:  # GATE-42-OK: shown by the Workbench
                return
            self._full_tags = dlg.result()
        finally:
            dlg.Destroy()
        # Push the seven core fields back into the quick view so the two
        # never disagree about the same file.
        from quill.core.speech.audio_tags import to_audio_metadata

        self._book.tags = to_audio_metadata(self._full_tags)
        self._tag_album.SetValue(self._book.tags.album)
        self._tag_artist.SetValue(self._book.tags.artist)
        self._tag_narrator.SetValue(self._book.tags.album_artist)
        self._tag_genre.SetValue(self._book.tags.genre)
        self._tag_year.SetValue(self._book.tags.year)
        self._tags_dirty = True
        self._announce(str(_("Tag edits ready. Save to write them to the file.")))
```

- [ ] **Step 6: Split the save path**

Replace `_on_save` with:

```python
    def _on_save(self) -> None:
        self._collect_tags()
        book = self._book
        if book.kind != "mp3":
            if self._chapters_dirty:
                # M4B chapter atoms cannot be rewritten in place; Save As re-muxes.
                self._on_save_as()
                return
            # Tags only: mutagen rewrites the atoms in place, no re-mux, instant.
            tags = self._full_tags
            self._run_save(
                str(_("Saving audiobook tags")),
                lambda: self._write_all_tags(book.path, tags, book),
                str(_("Saved {name}").format(name=book.path.name)),
            )
            return
        # The player holds the file open; release it for the in-place rewrite.
        self.player.shutdown()
        tags = self._full_tags
        self._run_save(
            str(_("Saving audiobook tags")),
            lambda: self._save_mp3_with_tags(book, tags),
            str(_("Saved {name}").format(name=book.path.name)),
        )

    @staticmethod
    def _write_all_tags(path: Path, tags: object, book: BookFile) -> object:
        """Write the full tag set to *path*; falls back to the core seven."""
        from quill.core.speech.audio_tags import (
            merge_audio_metadata,
            read_tags,
            write_tags,
        )

        full = tags if tags is not None else read_tags(path)
        write_tags(path, merge_audio_metadata(full, book.tags))
        return path

    @classmethod
    def _save_mp3_with_tags(cls, book: BookFile, tags: object) -> object:
        """Chapters and the core seven first, then the full tag set over the top.

        Both passes are load-modify-save, so neither drops the other's frames,
        and ``preferred_id3_version`` gives them one agreed ID3 version.
        """
        save_mp3_book(book)
        if tags is not None:
            cls._write_all_tags(book.path, tags, book)
        return book.path
```

In `_on_save_as`, after the existing `work()` returns the output path, apply the full tags to the new file. For the MP3 branch, add after `save_mp3_book(copy)`:

```python
                self._write_all_tags(out, tags, book)
```

and for the M4B branch, replace the body with:

```python
            def work(_progress: object = None) -> object:
                result = save_m4b_book_as(book, out)
                self._write_all_tags(out, tags, book)
                return result
```

capturing `tags = self._full_tags` before the closures, next to `book = self._book`.

Finally, enable Save for an M4B when only tags are dirty. Replace the constructor's `if book.kind != "mp3":` block with a call to a new method, and call that method from `_apply` and `_on_all_tags` as well:

```python
    def _sync_save_button(self) -> None:
        """Save is in-place for an MP3, and for an M4B when only tags changed."""
        if self._book.kind == "mp3":
            self._save_btn.Enable(True)
            return
        can_save = not self._chapters_dirty
        self._save_btn.Enable(can_save)
        self._save_btn.SetToolTip(
            _("Tags save in place; a chapter change needs Save As.")
            if can_save
            else _("An M4B with edited chapters is saved as a new file; use Save As.")
        )
```

- [ ] **Step 7: Wire the preview stop into the player tick**

Find where the Workbench receives player ticks (`PlayerPanel` drives `_on_tick`). Add a call to `self._check_preview_stop()` there, or, if the Workbench does not observe ticks today, pass `on_tick=self._check_preview_stop` into the `PlayerPanel` constructor and have `PlayerPanel._on_tick` call it when set. Prefer the second: it costs the Workbench no timer of its own, which is the point of `_check_preview_stop` returning a bool rather than owning a `wx.Timer`.

- [ ] **Step 8: Run the tests**

Run: `pytest tests/unit/ui/test_chapter_workbench_edits.py tests/unit/ui/ -q -k "workbench or chapter or tag"`
Expected: PASS.

Run: `pytest tests/unit/core/speech/ -q`
Expected: PASS.

- [ ] **Step 9: Rebaseline the module size budget**

Run: `python -m quill.tools.module_size_budget`
Expected: it reports `quill/ui/audio_studio/chapter_workbench.py` over its 945-line budget.

Update the entry in `quill/tools/module_size_budgets.json` to the new line count and add a sibling `_rebaseline_2026_09_02_full_tag_editor` key explaining what grew and why:

> chapter_workbench.py 945 -> NNN (+NN): the two new button rows (add/delete/edit/preview, and the nudge row with its step choice, Hear boundary and hear-after checkbox), the All tags... launcher, and the save path split into chapters-dirty and tags-dirty so an M4B can save tags in place. Every handler lives in the new under-cap `chapter_workbench_edits.py` and every computation in the wx-free `quill/core/speech/chapters.py` and `audio_tags.py`; this module gained surfaces and wiring only. It remains a decomposition target: the next slice should move the tag row and the player wiring out.

Replace NNN and +NN with the real numbers the gate reports.

- [ ] **Step 10: Lint and commit**

```bash
ruff check quill/ui/audio_studio/chapter_workbench.py
git add quill/ui/audio_studio/chapter_workbench.py quill/tools/module_size_budgets.json tests/unit/ui/
git commit -m "feat(studio): wire the tag editor and the full chapter edits into the Workbench"
```

---

### Task 13: The standalone route and the help catalogue

**Files:**
- Modify: `quill/ui/audio_studio/pages_audio.py:144-227` (`OpenBookPage`)
- Modify: `quill/ui/audio_studio/wizard.py` (surface the new intent)
- Modify: `quill/ui/audio_studio/__init__.py:76-82` (act on it)
- Modify: `quill/core/audio_studio/surface_help.py`
- Test: `tests/unit/ui/test_tag_editor_dialog.py`

**Interfaces:**
- Consumes: `TagEditorDialog`, `read_tags`, `write_tags`
- Produces: `OpenBookPage.tags_only_requested: bool`; `open_tags_in_editor(frame, path) -> None` in `tag_editor.py`

GATE-REACH requires every window-building module to be reachable by imports from an app entry point. `tag_editor.py` is reached from `chapter_workbench.py` already, but a surface reachable only from inside another dialog is one nobody finds — Cast shipped a first-run dialog that way for two releases.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/ui/test_tag_editor_dialog.py`:

```python
def test_open_tags_in_editor_is_importable_from_the_studio_entry_point() -> None:
    """GATE-REACH: the standalone route exists and is wired, not just the dialog."""
    import inspect

    from quill.ui import audio_studio
    from quill.ui.audio_studio.tag_editor import open_tags_in_editor

    assert callable(open_tags_in_editor)
    assert "open_tags_in_editor" in inspect.getsource(audio_studio)


def test_the_tag_editor_title_resolves_in_the_studio_help_catalogue() -> None:
    """GATE-STUDIO-HELP: a window with no authored purpose fails the build."""
    from quill.core.audio_studio import surface_help

    assert surface_help.is_known_title("Tag Editor")
    assert surface_help.is_known_title("Edit chapter")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/unit/ui/test_tag_editor_dialog.py -q -k "reach or catalogue"`
Expected: FAIL — `ImportError: cannot import name 'open_tags_in_editor'`

- [ ] **Step 3: Add the standalone opener**

Append to `quill/ui/audio_studio/tag_editor.py`:

```python
def open_tags_in_editor(frame: object, path: object) -> None:
    """Open *path* in the Tag Editor alone, with no Workbench around it.

    The standalone route from the Audio Studio's open-a-book page, for when
    the job is "fix the tags on this file" and not "reshape this book". Writes
    on OK, on the frame's background runner when it has one.
    """
    from pathlib import Path

    from quill.core.speech.audio_tags import AudioTags, read_tags, write_tags

    target = Path(str(path))
    announce = getattr(frame, "_announce", None)
    try:
        tags = read_tags(target)
    except Exception as exc:  # noqa: BLE001 - an untagged file is still editable
        if announce is not None:
            announce(str(_("Could not read the existing tags: {error}")).format(error=exc))
        tags = AudioTags()
    dlg = TagEditorDialog(
        getattr(frame, "frame", frame), tags, filename=target.name, announce=announce
    )
    try:
        code = frame._show_modal_dialog(dlg, str(_("Tag Editor")))
        edited = dlg.result() if code == wx.ID_OK else None
    finally:
        dlg.Destroy()
    if edited is None:
        return
    try:
        write_tags(target, edited)
    except Exception as exc:  # noqa: BLE001 - surfaced, not raised through wx
        show_message_box(str(exc), str(_("Tag Editor")), wx.OK | wx.ICON_ERROR, None)
        return
    if announce is not None:
        announce(str(_("Saved tags to {name}")).format(name=target.name))
```

- [ ] **Step 4: Add the button to the open-a-book page**

In `quill/ui/audio_studio/pages_audio.py`, inside `OpenBookPage.__init__`, after the Browse button:

```python
        self.tags_only_requested = False
        tags_btn = wx.Button(self, label=_("Edit ta&gs only..."))
        tags_btn.SetHelpText(
            "Opens the chosen file in the Tag Editor alone -- every tag it "
            "can carry, including cover art -- without the Chapter Workbench. "
            "Use this when the chapters are already right."
        )
        tags_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_tags_only())
```

and the handler:

```python
    def _on_tags_only(self) -> None:
        """Ask the wizard to open the Tag Editor rather than the Workbench."""
        self.tags_only_requested = True
        parent = self.GetTopLevelParent()
        if parent is not None:
            parent.EndModal(wx.ID_OK)
```

Add the button to the page's sizer beside Browse, following the row's existing layout.

- [ ] **Step 5: Act on it in the Studio entry point**

In `quill/ui/audio_studio/wizard.py`, expose the flag the same way `edit_path()` is exposed — a `tags_only()` method returning the open-a-book page's `tags_only_requested`.

In `quill/ui/audio_studio/__init__.py`, replace the edit-journey branch:

```python
    if edit_path is not None:
        if dlg_tags_only:
            from quill.ui.audio_studio.tag_editor import open_tags_in_editor

            open_tags_in_editor(frame, edit_path)
            return None
        from quill.ui.audio_studio.chapter_workbench import open_book_in_workbench

        open_book_in_workbench(frame, edit_path)
        return None
```

capturing `dlg_tags_only = dlg.tags_only() if code == wx.ID_OK else False` inside the same `try` block that already captures `edit_path`, before the dialog is destroyed.

- [ ] **Step 6: Author the help catalogue entries**

In `quill/core/audio_studio/surface_help.py`, add to `PURPOSES`:

```python
    "Tag Editor": (
        "Every tag this audio file can carry, over five pages: the main "
        "fields, the details, publishing credits, sort-order fields, and the "
        "cover art. Ctrl+Tab moves between pages. Nothing is written until "
        "you press OK and then save -- the editor hands the edit back, it "
        "does not touch the file itself."
    ),
    "Edit chapter": (
        "This chapter's title and its exact start and end, typed rather than "
        "set by ear, plus the optional link and image a Podcasting 2.0 player "
        "can show. Moving the start moves the end of the chapter before it, "
        "so the book stays gapless; the window tells you the range this "
        "chapter is allowed to occupy."
    ),
```

- [ ] **Step 7: Run the tests and the reachability gate**

Run: `pytest tests/unit/ui/test_tag_editor_dialog.py -q`
Expected: PASS.

Run: `python -m quill.tools.surface_reachability_audit`
Expected: `tag_editor.py` is reachable. If it reports the module as unreached, the import in `__init__.py` is inside a branch the walker cannot see — move it to a module-level import in `chapter_workbench.py`, which is itself an entry point.

- [ ] **Step 8: Lint and commit**

```bash
ruff check quill/ui/audio_studio/ quill/core/audio_studio/surface_help.py
git add quill/ui/audio_studio/ quill/core/audio_studio/surface_help.py tests/unit/ui/
git commit -m "feat(studio): open the Tag Editor standalone, and author its F1 help"
```

---

### Task 14: Regenerate the gate snapshots and run the full scorecard

**Files:**
- Modify: `tests/unit/ui/fixtures/studio_help_inventory.json`
- Modify: `tests/unit/ui/fixtures/accessible_name_inventory.json`
- Modify: `tests/unit/ui/fixtures/surface_reachability.json`
- Modify: the dialog inventory and button-contract snapshots
- Modify: `docs/f1-help-reference.md`

Every snapshot in this repository is a review artifact: the diff *is* the review. Read each one before committing it — a `missing` you commit is a failing build, and a site that lands as `help-elsewhere` or `named-elsewhere` when it should be `helped`/`named` means the inline call is in the wrong place.

- [ ] **Step 1: Regenerate the help inventory**

Run: `python -m quill.tools.studio_help_audit --write`
Then: `git diff tests/unit/ui/fixtures/studio_help_inventory.json`
Expected: new entries for `tag_editor.py` and `chapter_workbench_edits.py`, every one of them `helped`. Any `missing` means a control has no inline `SetHelpText` — go back and add the sentence rather than classifying it.

- [ ] **Step 2: Regenerate the accessible-name inventory**

Run: `python -m quill.tools.accessible_name_audit --write`
Then: `git diff tests/unit/ui/fixtures/accessible_name_inventory.json`
Expected: new entries, every one `named`. A `modal-hook` classification is acceptable only for a control that genuinely sits next to its `StaticText` in a modal; prefer fixing the site to name itself.

- [ ] **Step 3: Regenerate the reachability snapshot**

Run: `python -m quill.tools.surface_reachability_audit --write`
Then: `git diff tests/unit/ui/fixtures/surface_reachability.json`
Expected: `tag_editor.py` and `chapter_workbench_edits.py` appear as reached, not `dynamic` or `parked`.

- [ ] **Step 4: Regenerate the help reference document**

Run: `python scripts/build_help_reference.py`
Expected: `docs/f1-help-reference.md` gains the Tag Editor and Edit chapter sections with every sentence written in Tasks 8–13.

- [ ] **Step 5: Run the dialog gates**

```bash
python -m quill.tools.dialog_inventory
python -m quill.tools.dialog_button_contract
python -m quill.tools.check_access_keys
python -m quill.tools.check_dialog_zorder
python -m quill.tools.check_over_announce
python -m quill.tools.error_code_audit
```

Expected: no violations. `check_over_announce` is the one most likely to fire — it flags an announce inside an `EVT_SET_FOCUS` handler, an announce of `GetTitle()`, and an announce of a `title=` literal. None of the announcements in this work should do any of those; if one does, delete it rather than working around the gate.

- [ ] **Step 6: Run the whole scorecard**

Run: `python -m quill.tools.platform_report`
Expected: exit code 0. This is the gate that must be green before the work is called done — report its actual output, and if any gate fails, say which and why rather than claiming completion.

- [ ] **Step 7: Run the full test suite**

Run: `pytest -q -n 8 --dist loadgroup`
Expected: PASS. Report the real counts. Then the scoped type check: `mypy quill\core quill\io`.

- [ ] **Step 8: Commit**

```bash
git add tests/unit/ui/fixtures/ docs/f1-help-reference.md
git commit -m "chore(studio): regenerate the gate snapshots for the tag editor"
```

---

### Task 15: The standalone Audio Studio — menu routes and packaging

**Files:**
- Modify: `quill/apps/studio.py:922-963` (the Studio menu), `:842-852` (the library-tree context menu)
- Modify: `quill/core/keymap.py` (`APP_KEYMAPS`, the Studio app's chords)
- Modify: `standalone/studio/pyproject.toml:23` (dependency extras)
- Modify: `standalone/studio/quill-audio-studio.spec` (hidden imports)
- Test: `tests/unit/ui/test_menu_accelerators.py` (existing gate), `tests/unit/ui/test_tag_editor_dialog.py`

**Interfaces:**
- Consumes: `open_tags_in_editor` from Task 13
- Produces: a `studio.edit_tags` command in the Studio app keymap

`quill/apps/studio.py` is the standalone QUILL Audio Studio. It vendors and
drives the **same** `quill/ui/audio_studio` package QUILL itself uses, so
Tasks 1–14 reach it with no porting — but only through the Workbench and the
wizard. A standalone app whose front door is a menu bar should offer the Tag
Editor from that menu bar, and it has two packaging problems the in-app build
does not.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/ui/test_tag_editor_dialog.py`:

```python
def test_the_standalone_studio_offers_the_tag_editor_from_its_menu() -> None:
    """The standalone app's front door is its menu bar, not the wizard."""
    import inspect

    from quill.apps import studio

    source = inspect.getsource(studio)
    assert "open_tags_in_editor" in source
    assert "Edit &Tags" in source or "Edit Ta&gs" in source


def test_the_standalone_studio_bundles_mutagen() -> None:
    """A tag editor in a build with no mutagen is a dialog that cannot save."""
    from pathlib import Path

    spec = Path("standalone/studio/quill-audio-studio.spec").read_text(encoding="utf-8")
    assert "mutagen" in spec
    pyproject = Path("standalone/studio/pyproject.toml").read_text(encoding="utf-8")
    assert "mp3" in pyproject
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/unit/ui/test_tag_editor_dialog.py -q -k standalone`
Expected: FAIL on both — the menu has no entry, and the standalone declares `quill[ui]` with no `mp3` extra.

- [ ] **Step 3: Add the menu item, with an accelerator**

The Studio menu already claims Ctrl+N, Ctrl+E, Ctrl+O, Ctrl+J, Ctrl+, and Ctrl+Q. Every enabled menu item must show a keyboard route and no two items in one menu bar may claim the same key — that is a rule, not a preference, and `tests/unit/ui/test_menu_accelerators.py` enforces it. Pick a free chord (Ctrl+Shift+E is the natural neighbour of Ctrl+E, but check the whole menu bar first, including Book Tools and Voices).

In `_build_menu_bar`, after the `edit_id` line:

```python
        tags_id = wx.NewIdRef()
        studio.Append(
            tags_id,
            self._menu_label("Edit &Tags...", "studio.edit_tags"),
            "Open a file in the Tag Editor without the Chapter Workbench",
        )
        self.Bind(wx.EVT_MENU, lambda _e: self._on_edit_tags(), id=tags_id)
```

`_menu_label` renders whatever is *actually* bound and follows the user when
they rebind, so prefer it over a literal `\tCtrl+Shift+E`. Register the
default chord for `studio.edit_tags` in `APP_KEYMAPS` for the Studio app, and
give it an authored Key Describer title if the Studio's keymap carries them.

Add the handler beside the existing `_on_edit_book`:

```python
    def _on_edit_tags(self) -> None:
        """Pick an audio file and open it in the Tag Editor alone."""
        from quill.ui.audio_studio.tag_editor import open_tags_in_editor

        with wx.FileDialog(
            self,
            "Choose an audio file to tag",
            wildcard="Audio (*.mp3;*.m4a;*.m4b)|*.mp3;*.m4a;*.m4b",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:  # GATE-42-OK: native file picker
                return
            path = Path(dlg.GetPath())
        open_tags_in_editor(self, path)
```

- [ ] **Step 4: Add the library-tree context menu entry**

The context menu at `quill/apps/studio.py:842` already offers "&Open in Chapter Workbench" on a selected book. Add, directly beneath it:

```python
        tags_id = menu.Append(wx.ID_ANY, "Edit &Tags...")
```

and bind it to `open_tags_in_editor(self, entry_path)` in the same shape the
existing `open_id` binding uses. A context menu is scoped to itself for access
keys, but check the letters the surrounding items already claim (`O`, `R`,
`M`, `N`, `L`) before settling on `T`.

- [ ] **Step 5: Fix the packaging**

In `standalone/studio/pyproject.toml`, change the dependency to carry the mp3
extra — mutagen is what every MP3 tag and chapter operation runs on, and the
Studio has been shipping the Chapter Workbench's MP3 path without declaring
it:

```toml
dependencies = ["quill[ui,mp3] @ git+https://github.com/Community-Access/quill.git@ca37c60d18b6003c5139ee905ee4bfe84a601cf8"]
```

In `standalone/studio/quill-audio-studio.spec`, collect mutagen explicitly.
Every mutagen import in this codebase is lazy and inside a function, exactly
the shape PyInstaller's import tracer cannot follow — the same reason the
spec already collects PyNaCl and yt-dlp by hand:

```python
# mutagen: every ID3/MP4 tag and chapter operation runs on it, and every one
# of its imports is lazy and inside a function (so the file loads without the
# extra), which is precisely what the import tracer cannot see. Collect it
# explicitly or the Tag Editor ships as a window that cannot save.
mutagen_datas, mutagen_binaries, mutagen_hiddenimports = collect_all("mutagen")
```

and add the three names to `binaries`, `datas` and `hiddenimports` in the
`Analysis(...)` call alongside the existing ones.

- [ ] **Step 6: Run the tests and the menu gate**

Run: `pytest tests/unit/ui/test_tag_editor_dialog.py tests/unit/ui/test_menu_accelerators.py -q`
Expected: PASS. The accelerator gate fails loudly on a duplicate chord and on
a chord `wx.AcceleratorEntry` cannot parse — if it fires, change the chord
rather than the gate.

Run: `python -m quill.tools.check_runtime_imports` (or `python scripts/check_runtime_imports.py`, whichever the repo exposes)
Expected: mutagen is accounted for.

- [ ] **Step 7: Verify the built app, not just the source**

The packaging fix is the one change in this plan that unit tests cannot
prove. Build the standalone Studio and open the Tag Editor in the built
`.exe`:

```powershell
.\build-studio.cmd
```

Then run the produced executable, open an MP3 through Studio > Edit Tags...,
change a field and save. A build that cannot import mutagen fails here with
"Editing tags requires the 'mutagen' package" and nowhere else — report what
actually happened rather than assuming the collect worked.

- [ ] **Step 8: Commit**

```bash
git add quill/apps/studio.py quill/core/keymap.py standalone/studio/pyproject.toml standalone/studio/quill-audio-studio.spec tests/unit/ui/
git commit -m "feat(studio): reach the Tag Editor from the standalone menu, and bundle mutagen"
```

---

## What this does and does not reach

**Reached automatically.** `quill/apps/studio.py` (the standalone QUILL Audio
Studio) vendors and drives the same `quill/ui/audio_studio` package QUILL
itself uses — its own docstring says so. Every change in Tasks 1–14 therefore
lands in both products from one implementation; Task 15 only adds the menu
routes a standalone app's front door needs, and fixes the packaging.

**Deliberately not reached.** QUILL Cast has its own chapter model in
`quill/core/podcasts/chapter_edits.py` — inferred marks carrying a confidence
and a source, where an edit *means* "this is no longer a guess". That is a
different domain with different invariants, and folding it into this work
would damage both. The Media Player and Quill Radio consume chapters but do
not edit them. If the Tag Editor should reach Cast or the Player, that is a
follow-on with its own design, not a line item here.

## Manual verification

The gates prove the code is well-formed; they cannot prove it is usable. Before calling this done, drive it once by hand with a screen reader running:

1. Open a real chaptered MP3 in the Chapter Workbench.
2. Tab to the chapter list, select chapter 2, press Alt+Left five times. Confirm each press speaks only the new time and that the full sentence arrives once you stop.
3. Press Hear boundary. Confirm playback starts three seconds early and stops two seconds after the marker.
4. Add a chapter at the playhead, name it, delete it again. Confirm the audio length never changes.
5. Open All tags..., set a sort title and a cover image, press OK, press Save.
6. Reopen the file. Confirm the sort title and the cover art survived, and that the chapters are still intact — that combination is what proves the ID3 version negotiation works.
7. Repeat steps 5 and 6 on an M4B and confirm the save is instant (no re-mux) when only tags changed.
