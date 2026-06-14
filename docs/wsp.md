# Sound Notifications in QUILL

## Overview

QUILL plays short audio cues (earcons) at meaningful editing moments. The system is
built around QSP (QUILL Sound Packs), swappable theme bundles that map event IDs to
audio files. Playback is non-blocking, fire-and-forget, and pre-buffered so there is
no perceptible lag between event and sound.

---

## QSP - QUILL Sound Pack format

A `.qsp` file is a ZIP archive (rename to `.zip` to inspect). Its root contains:

```
manifest.json
expand.wav
snippet.wav
save.wav
...
```

During development a directory with the same layout is accepted; the loader treats a
directory and a ZIP identically.

### manifest.json schema

```json
{
  "format": "qsp",
  "version": "1",
  "name": "Ink",
  "author": "Jeff Bishop",
  "description": "Crisp mechanical earcons for focused writing.",
  "license": "CC0",
  "events": {
    "abbreviation_expanded":  "expand.wav",
    "abbreviation_deleted":   "delete.wav",
    "snippet_inserted":       "snippet.wav",
    "autocomplete_accepted":  "expand.wav",
    "document_saved":         "save.wav",
    "document_created":       "create.wav",
    "search_found":           "found.wav",
    "search_not_found":       "notfound.wav",
    "search_wrapped":         "wrap.wav",
    "heading_jumped":         "nav_heading.wav",
    "table_entered":          "nav_table.wav",
    "browse_mode_on":         "browse_on.wav",
    "browse_mode_off":        "browse_off.wav",
    "ai_thinking_started":    "ai_start.wav",
    "ai_response_received":   "ai_done.wav",
    "ai_error":               "error.wav",
    "transcription_started":  "rec_start.wav",
    "transcription_stopped":  "rec_stop.wav",
    "ssh_connected":          "connect.wav",
    "ssh_disconnected":       "disconnect.wav",
    "error":                  "error.wav",
    "warning":                "warning.wav"
  }
}
```

Any event key absent from the manifest is silently skipped (no sound, no error).
This allows minimal packs that only cover a subset of events.

The schema is validated at load time against `quill/core/schemas/sound_pack.json`.
A Quillin can ship its own QSP and register additional event IDs.

---

## Canonical event taxonomy

### Editing

| Event ID | Trigger |
|---|---|
| `abbreviation_expanded` | Abbreviation replaced with expansion |
| `abbreviation_deleted` | Expanded text removed by backspace (undo of expansion) |
| `snippet_inserted` | Snippet body placed at cursor |
| `autocomplete_accepted` | Autocomplete word committed |
| `word_corrected` | Inline spellcheck auto-correction |

### Document lifecycle

| Event ID | Trigger |
|---|---|
| `document_created` | New blank document opened |
| `document_saved` | Successful write to disk |
| `document_closed` | Tab or window closed |

### Navigation

| Event ID | Trigger |
|---|---|
| `heading_jumped` | Cursor moved to a heading landmark |
| `table_entered` | Cursor moved inside a table |
| `list_entered` | Cursor moved into a list |
| `browse_mode_on` | Browse/read mode activated |
| `browse_mode_off` | Edit mode resumed |

### Search

| Event ID | Trigger |
|---|---|
| `search_found` | A match was located |
| `search_not_found` | End of document with no match |
| `search_wrapped` | Search wrapped around document end |

### AI and transcription

| Event ID | Trigger |
|---|---|
| `ai_thinking_started` | Assistant generation began |
| `ai_response_received` | Assistant text fully arrived |
| `ai_error` | Generation failed |
| `transcription_started` | Mic open, recording begun |
| `transcription_stopped` | Recording closed |
| `transcription_word_inserted` | A transcribed word committed (optional; off by default) |

### Connectivity

| Event ID | Trigger |
|---|---|
| `ssh_connected` | SSH session established |
| `ssh_disconnected` | SSH session dropped |

### System

| Event ID | Trigger |
|---|---|
| `error` | Any hard error surfaced to user |
| `warning` | Non-fatal warning condition |

---

## Audio file requirements

- Format: **WAV** (PCM, 16-bit, 44100 Hz, mono). WAV plays from memory with no
  decode step, which is the key to zero-lag earcon playback.
- Duration: earcons should be **50-150 ms**. State change sounds (browse mode, SSH)
  may run to 300 ms. Nothing longer.
- Headroom: normalize to -6 dBFS so the system volume knob stays meaningful.

OGG or MP3 are not accepted in the core event table because codec initialization
adds 20-80 ms of jitter on first play. Quillins may play longer ambient files through
a separate path (not via the earcon queue).

---

## Cross-platform audio backend

Research into the [accessibleapps/sound_lib](https://github.com/accessibleapps/sound_lib)
library — widely used in screen-reader-accessible Python apps and NVDA add-ons — points
to BASS (Un4seen Developments) as the right foundation.

`sound_lib` ships pre-compiled BASS binaries for Windows (`bass.dll`), macOS
(`libbass.dylib`), and Linux (`libbass.so`) inside a single PyPI package. Its Python
wrapper is MIT licensed. BASS's key advantage for earcons: it mixes streams natively,
so two sounds triggered close together both play without either being dropped or
delayed.

### Backend priority

`quill/platform/sound_player.py` auto-detects the best available backend at startup:

| Priority | Backend | Platforms | Mixing | Extra dep |
|---|---|---|---|---|
| 1 | `_SoundLibBackend` | Windows, macOS, Linux | Yes | `pip install sound_lib` |
| 2 | `_WinsoundBackend` | Windows only | No (serialising queue) | None (stdlib) |
| 3 | `_NullBackend` | Any | N/A | None |

### Why BASS/sound_lib changes the design

With `winsound`, one sound blocks the next — a queue and daemon thread are required.
With BASS, `FileStream(mem=True, autofree=True).play()` fires a self-managed stream;
BASS mixes it with anything else already playing. The daemon thread is only needed
for the `winsound` fallback. The `_SoundLibBackend` path is stateless per-play call.

### Module layout

```
quill/core/sound_events.py          - SoundEvent enum; all canonical event IDs
quill/core/sound_pack.py            - QSP loader (ZIP + directory); manifest validator
quill/core/schemas/sound_pack.json  - JSON schema for manifest.json
quill/platform/sound_player.py      - Cross-platform player: backend protocol +
                                      _SoundLibBackend / _WinsoundBackend / _NullBackend
quill/platform/windows/sound_player.py  - Re-export shim (backward compat)
quill/ui/sound_manager.py           - Wires wx events -> SoundEvent -> SoundPlayer
```

### `_WavBackend` protocol

```python
class _WavBackend(Protocol):
    def play_wav(self, wav: bytes) -> None: ...
    def shutdown(self, timeout: float = 2.0) -> None: ...
```

Any object satisfying this protocol can be injected into `SoundPlayer(backend=...)`,
which is how tests work: a `_RecordingBackend` records calls synchronously without
touching audio hardware.

### `quill/core/sound_events.py`

A plain `StrEnum` of all canonical event IDs. No wx, no platform code.

### `quill/core/sound_pack.py`

Loads a `.qsp` ZIP or a directory. `load_sound_pack(path)` validates the manifest
and reads every referenced WAV into `bytes` immediately. Zero disk I/O at play time.

### `quill/platform/sound_player.py` — `SoundPlayer`

Owns: cooldown (80 ms per event), mute toggle, per-event disable list.
Delegates actual playback to the injected/detected backend.

```python
player = SoundPlayer()                    # auto-detects backend
player.load_pack(pack, disabled=frozenset({"transcription_word_inserted"}))
player.play("abbreviation_expanded")      # returns in < 1 ms
player.toggle_mute()                      # bound to keymap action sound.toggle_mute
```

### `quill/ui/sound_manager.py`

A singleton held by `MainFrame`. At startup it:

1. Reads `settings.sound_pack_path`.
2. Calls `load_sound_pack(path)` -> `SoundPack`.
3. Passes the pack to `SoundPlayer`.
4. Binds to `EVT_SOUND_EVENT` (a custom wx event) posted by any code that wants to
   trigger a sound.

Any module can post a sound without importing wx directly:

```python
from quill.core.sound_events import SoundEvent
from quill.ui.sound_manager import post_sound

post_sound(SoundEvent.ABBREVIATION_EXPANDED)
```

`post_sound` is a thin wrapper that calls `wx.CallAfter` so it is safe from any
thread.

### Settings additions

New keys in `SETTING_SPECS` (group `accessibility`):

| Key | Kind | Default | Label |
|---|---|---|---|
| `sound_enabled` | bool | `True` | Enable sound notifications |
| `sound_pack_path` | text | `""` (built-in Ink pack) | Sound pack path (.qsp file or folder) |
| `sound_volume` | int | `80` | Notification volume (0-100); passed to `Output.set_volume()` on the sound_lib backend |
| `sound_events_disabled` | text | `""` | Comma-separated event IDs to silence |

A global mute toggle is bound to a keymap action (`sound.toggle_mute`) so the user
can silence earcons mid-session without opening Settings.

### Optional dependency

Add `sound_lib` as an optional extra in `pyproject.toml`:

```toml
[project.optional-dependencies]
audio = ["sound_lib"]
```

Install with `pip install quill[audio]`. If absent, QUILL falls back to `winsound`
on Windows or goes silent on other platforms. The bundled Ink pack is always present;
only the playback quality degrades without sound_lib.

---

## Bundled pack: "Ink"

The default pack ships inside the QUILL wheel at
`quill/assets/sound_packs/ink/`. It uses short typewriter-derived clicks and
tones designed to be unambiguous at low volume and to not clash with screen-reader
speech. Suggested mappings:

| Event | Character |
|---|---|
| `abbreviation_expanded` | Soft click + brief rising pitch - "something replaced" |
| `abbreviation_deleted` | Short descending tick - mirror image of expand, "taken back" |
| `snippet_inserted` | Two-click sequence - slightly longer than abbreviation |
| `document_saved` | Single soft low tick - "settled" |
| `search_not_found` | Very short descending two-tone - "no" |
| `browse_mode_on` | Thin high tone - spatial sense of "stepping back" |
| `browse_mode_off` | Thin low tone - "stepping in" |
| `ai_thinking_started` | Faint ascending shimmer loop (single-play, not looped) |
| `ai_response_received` | Clean bell-like tone |
| `error` | Double low buzz |
| `ssh_connected` | Two ascending beeps |
| `ssh_disconnected` | Two descending beeps |

The Ink pack source files (Audacity project + rendered WAVs) live in
`assets/sound_packs/ink/` and are not packaged into the wheel - only the rendered
WAVs at `quill/assets/sound_packs/ink/` are.

---

## Quillin sound pack integration

A Quillin manifest (`manifest.json`) may declare:

```json
{
  "sound_pack": "sounds/",
  "sound_events": {
    "my_quillin.action_fired": "fire.wav"
  }
}
```

The Quillin runner registers the custom event IDs with `SoundManager` at load time.
The user can then reference `my_quillin.action_fired` in `sound_events_disabled` to
suppress it individually. Quillin-defined events do not need to be in the core
`SoundEvent` enum.

---

## Safe mode

When `QUILL_SAFE_MODE=1`, `SoundPlayer.play()` is a no-op. This keeps safe mode
strictly minimal-resource.

---

## Implementation order

1. `sound_events.py` - enum only, no deps. **Done.**
2. `sound_pack.json` schema + `sound_pack.py` loader. **Done.**
3. `sound_player.py` with `_WavBackend` protocol, `_SoundLibBackend` (BASS/sound_lib),
   `_WinsoundBackend` (stdlib fallback), `_NullBackend`. **Done.**
4. Add `sound_lib` optional extra to `pyproject.toml`.
5. `sound_manager.py` in ui layer, `post_sound` helper, settings wiring.
6. Hook `abbreviation_expanded` and `abbreviation_deleted` in `abbreviations.py`.
   Ship and validate before wiring remaining events.
7. Add remaining event hooks incrementally per the taxonomy table.
8. Record and ship the Ink pack (WAV files using sound_lib for quality monitoring).
9. Quillin sound API.

---

## Open questions

- Volume control: `sound_lib` backend supports `Output.set_volume(float)` cleanly.
  The `winsound` fallback has no per-app volume; users rely on the system mixer.
  Consider exposing the setting only when sound_lib is active.
- BASS license: the Un4seen BASS binary is free for non-commercial use; a commercial
  license is required for paid distribution. Confirm license terms before shipping.
