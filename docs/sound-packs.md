# QUILL Sound Pack Guide

## What is a QSP file?

A QSP (QUILL Sound Pack) is a directory or `.qsp` ZIP archive that maps QUILL
sound events to WAV files. When a pack is loaded, QUILL plays the corresponding
WAV whenever the event fires.

## Pack structure

```
my_pack/
    manifest.json       -- required
    save.wav            -- referenced by the manifest
    expand.wav
    ...
```

**manifest.json** example:

```json
{
  "format": "qsp",
  "version": "1",
  "name": "My Pack",
  "author": "Your Name",
  "description": "Brief description.",
  "license": "CC0",
  "events": {
    "document_saved": "save.wav",
    "abbreviation_expanded": "expand.wav"
  }
}
```

Required fields: `format` (must be `"qsp"`), `version` (must be `"1"`),
`name`, `events`. All other fields are optional.

## Partial packs

Packs do not have to define every event. A pack that only defines two events
is valid. QUILL loads whatever is present and silently drops missing WAV files.

The Sound Events dialog (**Preferences > Sound > Sound Events...**) shows only
the events that exist in the currently loaded pack(s). If you load a partial
pack, only its events appear as toggles.

## Built-in packs

| Pack directory | Contents |
|---|---|
| `ink/` | Full earcon set for editing, navigation, AI, and system events |
| `indent_pentatonic/` | Indentation tones: C5 pentatonic scale (8 levels x 2 directions) |
| `indent_whole_tone/` | Indentation tones: C5 whole-tone scale |
| `indent_diatonic/` | Indentation tones: C major diatonic (C5-C6) |
| `indent_chromatic/` | Indentation tones: one semitone per level from C5 |

The four indent tone packs are **partial**: they define only the
`indent_level_0_up` through `indent_level_7_down` events. Combine with the
Ink earcon pack for full audio feedback.

## Overlay / indent tone packs

The sound system supports two simultaneous layers:

1. **Primary earcon pack** -- chosen in Preferences > Sound > Sound Pack.
   Provides earcons for editing, navigation, AI, etc.
2. **Indent tone overlay** -- loaded automatically when Indentation Tones are
   enabled in Preferences > Accessibility > Sound > Indentation Feedback.
   The overlay is selected by the Scale preference and merged on top of the
   primary pack at startup (and again whenever the scale changes).

Because the overlay uses the same `register_event()` path as Quillin sound
packs, it is fully compatible with third-party earcon packs.

## Indent tone events

When an indent tone pack is loaded, the following events become available:

| Event ID | Description |
|---|---|
| `indent_level_0_up` | Cursor moved to level 0 from a lower level |
| `indent_level_0_down` | Cursor moved to level 0 from a higher level |
| `indent_level_1_up` | Level 1, going deeper |
| `indent_level_1_down` | Level 1, dedenting |
| ... | (same pattern for levels 2-7) |
| `indent_level_7_up` | Level 7 or deeper, going deeper |
| `indent_level_7_down` | Level 7 or deeper, dedenting |

Levels above 7 are clamped to level 7 for sound; speech mode still announces
the true number ("indent 12").

## Tone design

- Bell synthesis: sine fundamental + inharmonic partial at 2.76× (−12 dB).
- ADSR: attack 3 ms, decay 20 ms, sustain 0.25, release 40 ms → 83 ms total.
- Volume: −18 dBFS.
- **Direction cue** (enabled by default): a 10 ms spectral noise burst at the
  attack. Going deeper (up): high-pass noise (4-8 kHz, upward hiss). Dedenting
  (down): low-pass noise (80-400 Hz, soft thud). Helps distinguish direction
  without relying on pitch memory alone.

## Scale comparison

| Scale | Character | Best for |
|---|---|---|
| Pentatonic | No dissonance possible; any two adjacent levels harmonise | Most users; general coding |
| Whole-tone | Equal brightness steps; very unambiguous direction sense | YAML, Python with consistent 2/4-space indent |
| Diatonic major | Familiar sound; semitone steps make levels very distinct | Users comfortable with Western melody |
| Chromatic | One semitone per level; maximum pitch resolution | Deeply nested code (5+ levels regularly) |

## Regenerating the built-in indent tones

```bash
python scripts/gen_indent_tones.py
```

Writes 64 WAV files (4 scales × 8 levels × 2 directions) to
`quill/assets/sound_packs/indent_*/`. Re-run after changing synthesis
parameters in the script.

## Known events (complete list)

### Earcons (Ink pack)

| Event ID | Fires when |
|---|---|
| `abbreviation_expanded` | Abbreviation auto-expands |
| `abbreviation_deleted` | Expansion undone by backspace |
| `snippet_inserted` | Snippet inserted at cursor |
| `autocomplete_accepted` | Autocomplete suggestion accepted |
| `word_corrected` | Spell-correction applied |
| `document_created` | New document opened/created |
| `document_saved` | File saved |
| `document_closed` | Tab closed |
| `browse_mode_on` | Quick Nav mode activated |
| `browse_mode_off` | Quick Nav mode deactivated |
| `heading_jumped` | Cursor jumped to heading |
| `table_entered` | Cursor entered a table |
| `list_entered` | Cursor entered a list |
| `search_found` | Search result found |
| `search_not_found` | Search found nothing |
| `search_wrapped` | Search wrapped to top/bottom |
| `ai_thinking_started` | AI request sent |
| `ai_response_received` | AI response arrived |
| `ai_error` | AI error occurred |
| `transcription_started` | Dictation started |
| `transcription_stopped` | Dictation stopped |
| `transcription_word_inserted` | Dictated word inserted |
| `ssh_connected` | SSH connection established |
| `ssh_disconnected` | SSH connection closed |
| `error` | Application error |
| `warning` | Application warning |
| `sound_on` | Sound notifications enabled |
| `sound_off` | Sound notifications disabled |

## Creating a custom pack

1. Create a directory with a `manifest.json` and your WAV files.
2. In **Preferences > Sound**, set Sound Pack to your directory path.
3. Open **Sound Events...** to toggle individual events on or off.

To distribute the pack as a single file, zip the directory and rename the
archive to `.qsp`. QUILL loads `.qsp` files the same way as directories.

To lint a Quillin that ships sound contributions:

```bash
python -m quill.tools.quillin_lint <quillin_dir> --strict
```
