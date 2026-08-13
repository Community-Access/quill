# QUILL Media Player — Product Requirements Document (PRD)

**Product:** QUILL Media Player (in-QUILL feature **and** the standalone
`Quill Media Player` app — see Section 9.11)
**Status:** Approved for phased build — Phase 1 (core) shipped; UI phases in progress
**Owners:** Community Access / BITS
**Date:** 2026-08-04
**Related:** `bard.md` (BARD 2.0 integration + Secrets/Token Manager); the user
guide alongside this PRD (`userguide.md`)
**Scope:** One rich, accessible media and audiobook player inside the QUILL
ecosystem — for local files, the QUILL library sources, podcasts, and BARD Digital
Talking Books (see `bard.md` Part A, Service 3).

> **Design stance:** This is not a new player built from scratch. QUILL already has
> a mature, shared audio stack (engine layer, transport panel, chapter engine,
> resume store, audiobook library). This spec **unifies and elevates** that stack
> into one first-class Media Player, reuses every existing module by name, and adds
> only what is genuinely missing: a multi-band equalizer and DSP chain, silence
> trimming, DAISY audio navigation, unified cross-source library, and richer
> bookmarks. Inspiration for the feature bar is drawn from BookPlayer (iOS), adapted
> to a keyboard-and-screen-reader-first desktop experience.

---

## 1. Principles

1. **Accessibility is the product, not a layer.** Every control is keyboard-operable
   and screen-reader- and braille-announced. Nothing is mouse-only. This audience
   lives in NVDA/JAWS and a braille display; a beautiful player they cannot drive is
   worthless. Accessibility is specified first (Section 8), not bolted on.
2. **Reuse the existing stack.** Playback goes through the shared engine in
   `quill/ui/audio/`; transport and chapters reuse the Audio Studio `PlayerPanel`;
   chapters/M4B/ID3 reuse `quill/core/speech/`; resume and per-book state reuse
   `quill/core/speech/listening_positions.py` and `quill/core/audio_studio/`.
3. **One player, many sources.** Local files, QUILL library downloads, podcasts, and
   BARD titles all play in the same player with the same controls and the same
   library shelves.
4. **QUILL UX flavor.** Lives as a `main_frame_*` mixin, opens through
   `_show_modal_dialog` (GATE-16), obeys the keymap/command registry, announces
   through `quill.core.announce`, and persists via atomic JSON in `app_data_dir()`.
5. **Cross-platform, honest about it.** Windows and macOS. Rich DSP depends on the
   libmpv backend; the built-in `wx.media` backend degrades gracefully with an
   announced reason (Section 12).
6. **Robust and gapless.** Large audiobooks, flaky files, and long listening sessions
   are the normal case — resume, integrity, and stability are first-order concerns.

---

## 2. What already exists (the reuse map)

The player is assembled from these existing modules. New work is called out in
Section 3.

| Concern | Reuse |
| --- | --- |
| Playback engine | `quill/ui/audio/audio_engine.py` — `AudioEngine` protocol, `WxMediaEngine` (default, `wx.media`), `create_engine()` / `preferred_backend()` |
| Rich backend | `quill/ui/audio/mpv_engine.py` — `MpvAudioEngine` (libmpv, gapless, exact seek, `scaletempo`) |
| Transport UI | `quill/ui/audio_studio/player_panel.py` — `PlayerPanel` (play/pause/stop, prev/next chapter, rewind/forward, position slider, volume/mute, speed, "Where am I?") |
| Player host | `quill/ui/audio_studio/chapter_workbench.py` — ties panel + library + resume; `open_book_in_workbench(frame, path)` |
| Chapters (ID3/M4B) | `quill/core/speech/chapters.py` (CHAP/CTOC via `mutagen`), `quill/core/speech/audiobook.py` (`read_m4b_chapters`, ffprobe), `quill/core/speech/chapter_io.py` (Audacity/CUE/CSV/Podcasting-2.0 import/export) |
| Resume position | `quill/core/speech/listening_positions.py` (keyed by `path\|size`, capped) |
| Per-book prefs | `quill/core/audio_studio/book_prefs.py` (volume/mute, extend for speed/EQ) |
| Audiobook library | `quill/core/audio_studio/library.py` — `BookEntry`, Favorites / In Progress / Recently Played / Inbox views |
| Play queue | `quill/core/audio_studio/play_queue.py` |
| Sleep timer | `quill/core/audio_studio/sleep_timer.py` (`SleepTimerWatcher`) |
| Playlists (M3U/PLS) | `quill/core/radio/playlist_import.py` / `playlist_export.py` / `m3u_catalog.py`, `quill/core/podcasts/playlists.py` |
| Bookmarks / time-points | `quill/core/bookmarks.py`; Beacon `Location.media_start_ms`, `MediaChapter` (`quill/apps/beacon/model.py`) |
| Background work | `quill/stability/task_manager.py` (`TaskManager`) + `quill/stability/wx_dispatch.py` (`call_ui_safely`) |
| Announcements | `quill/core/announce/` (`AnnouncementService`, sinks) + `quill/platform/windows/prism_bridge.py` (`AnnouncementEngine`) |
| Earcons | `quill/ui/companion_cues.py` (`post_cue`), `quill/core/sound_events.py`, `quill/core/speech/earcon.py` |
| Library sources | `quill/core/library/` (Book model, providers) for downloadable audio; BARD via `bard.md` |

---

## 3. What is genuinely new

Only these are net-new; everything else is composition of Section 2.

1. **DSP chain** — multi-band **equalizer**, **volume boost / normalization**, and
   **skip-silence** (libmpv audio filters; Section 7.4–7.6).
2. **DAISY audio navigation** — navigate DAISY Digital Talking Books by level,
   heading, and page (no DAISY *audio* player exists today). Required for BARD audio.
3. **Unified Media Library** — one library surface spanning local files, QUILL
   library downloads, podcasts, and BARD, layered over `audio_studio/library.py`.
4. **Rich bookmarks** — named, note-bearing time-point bookmarks with a navigable
   list and export, generalizing `bookmarks.py` + Beacon time-points.
5. **The Media Player shell** — a `MediaPlayerMixin` + a full player window and a
   persistent **mini-player**, plus global media-key handling.
6. **OS Now Playing integration** — Windows SMTC and macOS Now Playing / remote
   command center (Section 7.13).

---

## 4. Architecture

```
                 +-------------------------------------------+
   UI layer      |  MediaPlayerMixin (main_frame_media.py)   |
                 |  MediaPlayerWindow / MiniPlayer (wx)      |
                 |  PlayerPanel (reused) + DSP panel (new)   |
                 +---------------------+---------------------+
                                       | UI thread only
                 +---------------------v---------------------+
   Controller    |  MediaController (quill/core/media/)      |
                 |  transport, queue, chapters, position,    |
                 |  bookmarks, sleep, DSP settings           |
                 +----+-------------------+------------------+
                      |                   |
        +-------------v-----+   +---------v-------------------+
   Engine| AudioEngine proto|   | Domain services (core)      |
         | WxMediaEngine    |   | chapters / audiobook / DAISY|
         | MpvAudioEngine   |   | listening_positions /       |
         | (DSP-capable)    |   | library / play_queue /      |
         +------------------+   | bookmarks / sleep_timer     |
                                +-----------------------------+
        Background: TaskManager + wx_dispatch (probe, scan, download)
        Announce:   quill.core.announce -> prism_bridge (speech+braille)
```

- **`quill/core/media/` (new, wx-free, strict-typed):** the `MediaController` and
  the DSP/DAISY/bookmark domain logic — pure, unit-testable, in `mypy` scope.
- **`quill/ui/media/` (new):** the wx shell — player window, mini-player, DSP panel —
  built on the reused `PlayerPanel`.
- The engine stays behind the existing `AudioEngine` protocol; the controller never
  imports wx and never touches the OS directly.

---

## 5. Sources and formats

**Sources:** local files/folders; QUILL library downloads (`quill/core/library/`);
podcasts (Cast); BARD Digital Talking Books (`bard.md`); imported playlists.

**Container/codec support** (via the engine; probe with ffprobe/`mutagen`):

- **Audiobook:** M4B, M4A (chaptered), MP3 (ID3 CHAP/CTOC).
- **Audio:** AAC, Ogg/Opus, FLAC, WAV, and other libmpv-supported codecs.
- **Packaged books:** DAISY 2.02/3 talking books (`.zip`), including BARD titles.
- **Playlists:** M3U / M3U8 / PLS import and export.
- **Archives:** `.zip` of audio auto-expanded into an ordered playlist (BookPlayer
  parity).

Every result/track carries an explicit **format** and **source** so the player can
announce "M4B audiobook, 11 hours, 14 chapters" before playback.

---

## 6. The `MediaController` (core API)

```python
class MediaController:
    # lifecycle
    def load(self, item: MediaItem, *, resume: bool = True) -> None: ...
    def play(self) -> None: ...
    def pause(self) -> None: ...
    def toggle(self) -> None: ...
    def stop(self) -> None: ...

    # transport
    def seek_to(self, ms: int) -> None: ...
    def skip(self, delta_ms: int) -> None: ...              # +/- interval
    def smart_rewind(self) -> None: ...                     # elapsed-aware rewind
    def next_chapter(self) -> None: ...
    def prev_chapter(self) -> None: ...
    def go_to_chapter(self, index: int) -> None: ...

    # rate / audio
    def set_speed(self, rate: float) -> None: ...           # 0.5–4.0, pitch-preserving
    def set_volume(self, pct: int) -> None: ...
    def set_boost(self, db: float) -> None: ...             # gain / normalization
    def set_equalizer(self, eq: Equalizer) -> None: ...
    def set_skip_silence(self, on: bool) -> None: ...

    # bookmarks / position
    def add_bookmark(self, note: str = "") -> Bookmark: ...
    def bookmarks(self) -> list[Bookmark]: ...
    def resume_ms(self) -> int: ...

    # queue
    def queue(self) -> PlayQueue: ...
    def play_next(self) -> None: ...

    # state / events
    def state(self) -> PlayerState: ...
    def subscribe(self, listener) -> Unsubscribe: ...       # UI updates via events
```

`MediaItem` is source-agnostic (`local` / `library` / `podcast` / `bard` / `daisy`)
and carries title, source, path-or-url, format, chapters, duration, and a resume key.
All state changes emit events the UI marshals to the main thread with `call_ui_safely`.

---

## 7. Feature specification

### 7.1 Transport
Play/pause (single toggle), stop, and configurable **skip intervals** (default −15 s /
+30 s; per-book override). Prev/next **chapter**, jump to chapter start, jump to book
start. Position slider that **speaks human time** ("2 hours 14 minutes of 11 hours").
Media-key and headset-button support (Section 7.13).

### 7.2 Smart rewind
On resume after a pause, automatically rewind a small amount that grows with how long
you were away (BookPlayer parity) — so you re-enter with context. Amount is
configurable and can be disabled.

### 7.3 Speed control
Global and **per-book** playback speed, 0.5×–4.0× in fine steps (0.05), **pitch
preserving** via libmpv `scaletempo2`. On the `wx.media` fallback, WMP rate change is
offered at coarser granularity without pitch preservation, and the player announces
the limitation. Speed is remembered per book in `book_prefs`.

### 7.4 Volume, boost, and normalization
Master volume, mute, and **per-book volume** (reuse `book_prefs`). **Volume boost**
and loudness **normalization** for quiet recordings via libmpv `dynaudnorm` /
`loudnorm`. Boost is expressed in dB with a safe ceiling and clipping guard.

### 7.5 Equalizer (new)
A multi-band **graphic EQ** (10 bands, ±12 dB) implemented via the libmpv
`anequalizer`/`equalizer` audio filter. Ships **presets** (Flat, Speech/Voice,
Bass Boost, Treble Boost, Night, Podcast) plus user presets. EQ is applied live,
stored globally and optionally **per-book**. Fully keyboard-operable: each band is a
labeled slider with value announced in dB; presets are a combobox. When the active
backend cannot do EQ (`wx.media`), the EQ controls are disabled with an announced,
explained reason and a one-key offer to enable the mpv backend.

### 7.6 Skip silence (new)
Optional **silence trimming** (BookPlayer "Smart Speed" analog) via libmpv
`silenceremove`, shortening long gaps. Announced when toggled; off by default.

### 7.7 Chapters and markers
Read chapters from ID3 **CHAP/CTOC**, **M4B** atoms, **Podcasting 2.0** JSON, and
**DAISY** navigation (Section 7.8) — all via `quill/core/speech/chapters.py`,
`audiobook.py`, and `chapter_io.py`. A navigable **chapter list** (arrow to move,
Enter to jump) announces title + time; entering a new chapter during playback is
announced (and optionally earconed). Import/export chapters (Audacity labels, CUE,
CSV, chapters.json).

### 7.8 DAISY audio navigation (new)
For DAISY talking books (including BARD audio), navigate by **level/heading**,
**page**, and **phrase**, driven by the DAISY navigation control file. Exposes the
DAISY structure as the player's chapter/heading tree so the same list-and-jump UI
works. This is the one net-new engine-adjacent component and is required for `bard.md`
Service 3.

### 7.9 Bookmarks and notes (new/generalized)
Named, note-bearing **time-point bookmarks**: add at the current position (one key),
optional spoken/typed note, a navigable **bookmark list** (jump on Enter), rename,
delete, and **export**. Built over `quill/core/bookmarks.py` and the Beacon
time-point model. Auto-bookmark on sleep-timer stop so you never lose your place.

### 7.10 Resume / listening position
Every book remembers its exact position via `listening_positions.py` (keyed by
`path|size`), restored on load. "Mark as finished" and progress percentage per book
(reuse library `record_play`). Optional server-side position sync for BARD titles
when the API supports it (`bard.md` A.6).

### 7.11 Sleep timer
Duration-based or **end-of-chapter** sleep, with a **fade-out** and an auto-bookmark
at stop. Reuse `SleepTimerWatcher`; host marshals the fire callback via `wx.CallAfter`.
Announced countdown at intervals; extendable with one key ("still awake?").

### 7.12 Managed library (unified, new surface over existing store)
One **Media Library** over `audio_studio/library.py` with pinned views —
**Favorites**, **In Progress**, **Recently Played**, **Inbox** (recent files not yet
added) — plus **user folders** with automatic sequential playback (BookPlayer parity),
favorites, mark-finished, and search. Sources beyond local files (library downloads,
podcasts, BARD) appear as first-class entries with their source badge. All list
navigation is arrow-key + type-ahead; no drag-only operations (reorder is
combobox-add + Up/Down/Remove per the QUILL list-UI convention).

### 7.13 OS integration and Now Playing
Windows **System Media Transport Controls** (lock screen, hardware/media keys,
headset buttons) and macOS **Now Playing** / remote command center: title, chapter,
artwork, elapsed/remaining, and play/pause/skip/next-chapter commands. Global media
hotkeys work even when the player window isn't focused.

### 7.14 Playlists and queue
Import/export **M3U/M3U8/PLS**; a persistent **play queue** (`play_queue.py`) with
reorder/remove; folder = auto-sequential playlist; `.zip` auto-expanded to a queue.

### 7.14a Winamp classic-skin transport keys (shipped)
The classic main-window letters — `Z X C V B` for previous/play/pause/stop/next,
arrows to seek, `T` elapsed-or-remaining, `J` jump-to-track, `Ctrl+J` go-to-position,
`L` open — resolved through the **one shared map**
(`quill/ui/radio/winamp_keys.py`, wx-free) that Quill Radio's Recordings player and
QUILL Cast already use. The Media Player was the last holdout, and the surface a
Winamp user is most likely to reach for: an audiobook with a track list is a playlist
editor with a transport, which is exactly what the classic skin's main window was.
Adopting the shared map rather than writing a second one is the requirement — the
value of muscle memory is that it is not relearned per app, so the letters, the seek
steps, and the words spoken back must be identical across every surface.
`B`/`Z` step the track list, or by chapter for a single-file book; `Ctrl+J` reuses the
existing accessible Go to Position dialog rather than a second prompt. Letters are
never claimed while a text field has focus (`quill/ui/media/winamp_mixin.py`).

### 7.15 Gapless and crossfade
Gapless playback across a book's files (libmpv), with an optional short crossfade for
music/mixed content. Falls back to sequential load on `wx.media`.

### 7.16 BARD protected playback
BARD Digital Talking Books play in this same player. Content protection is handled per
the **sanctioned** mechanism agreed with NLS (`bard.md` A.4/E): any per-title key is
obtained through the Token Manager / broker, held only in memory for playback, and
**no decrypted or unprotected copy is ever written to disk**. If the sanctioned path
is unavailable on a platform, the player says so rather than working around it.

---

## 8. Accessibility specification (first-class)

This section is normative, not aspirational.

- **Keyboard model.** Every function has a key. Space = play/pause; Left/Right =
  skip interval; `[` / `]` = prev/next chapter; `,` / `.` = speed down/up; `B` = add
  bookmark; `L` = chapter list; `K` = bookmark list; `S` = sleep timer; `Where am I?`
  on one key. A discoverable, remappable shortcut sheet via the keymap registry
  (`quill/core/feature_command_map.py`); no chord is required for core transport.
- **Screen-reader + braille announcements.** All state changes route through
  `quill.core.announce` → `prism_bridge.AnnouncementEngine` (NVDA/JAWS/Narrator/SAPI
  speech **and** braille). Announced events: load ("M4B, 11 h, 14 chapters"),
  play/pause/stop, chapter entry, speed/volume/EQ changes (with value), bookmark
  add/jump, sleep countdown, end of book.
- **Verbosity levels.** Minimal / Normal / Verbose (mirroring Beacon's `Announcer`),
  so power users can silence routine chatter while keeping essential cues.
- **Earcons.** Distinct non-speech cues (`post_cue` / `sound_events`) for
  play/pause/bookmark/chapter/end, independently toggleable from speech.
- **"Where am I?"** One key speaks title, chapter, position, remaining, and speed.
- **Focus management.** Player window/mini-player open through `_show_modal_dialog`
  (GATE-16): focus lands on the primary control, is tracked, and returns to the editor
  on close. Lists expose correct accessible name/role/value (`set_accessible_name`).
- **No mouse-only affordances.** Sliders are keyboard-adjustable and announce values;
  the position bar is arrow-seekable; reordering never requires drag.
- **Self-voicing option.** Optional built-in speech for announcements so the player is
  usable even without a running screen reader (uses the QUILL speech engine).
- **Visual accessibility.** Honors QUILL/OS high-contrast and dark mode; respects
  reduced-motion; large hit targets and scalable text for low-vision mouse users.

---

## 9. UX and where it lives

- **Entry points.** `Tools > Media Player`, the command palette, and a global hotkey.
  A `MediaPlayerMixin` in `quill/ui/main_frame_media.py` adds the commands.
- **Two surfaces.** A full **Player Window** (Section 9.1) with a real menu bar, and a
  compact configurable **Mini-Player** (Section 9.4). Modal child dialogs launched from
  either (Open URL, EQ editor, bookmark note, preferences) go through `_show_modal_dialog`
  (GATE-16).
- **Status bar.** Reuses the audio-studio status-bar pattern for at-a-glance state.
- **Continuity.** Closing the window keeps audio playing via the controller; reopening
  reattaches. One playback session app-wide (no double audio), consistent with the
  radio single-controller lesson.

### 9.1 The full Player Window

The Player Window is a top-level **`wx.Frame`** (not a modal dialog) following the
standalone `AppShellFrame` conventions the audio apps already use — so it can carry a
menu bar, keep playing when unfocused, and host child panels. It implements the
MainFrame host protocol (`_show_modal_dialog`, `_run_background_task`, `_announce`,
`settings`) so every sub-dialog it opens still obeys the modal/keyboard contract.

**Layout (top to bottom), each a labeled region a screen reader lands on in order:**

1. **Menu bar** (Section 9.2) — the complete command surface.
2. **Now Playing header** — title, author/narrator, source badge (Local / Library /
   Podcast / BARD), and format ("M4B · 11 h 14 m · 14 chapters"). A single read-only
   line a screen reader can review; updated live and announced on change.
3. **Transport row** — the reused `PlayerPanel`: Play/Pause, Stop, Skip back/forward,
   Prev/Next chapter, position slider (arrow-seekable, speaks human time), volume,
   mute, speed. Every control keyboard-operable and value-announced.
4. **Content notebook** (Tab-navigable pages, each a proper accessible tab):
   - **Chapters** — the chapter/heading list (Enter jumps; announces title + time).
   - **Bookmarks** — named, note-bearing time-points (Enter jumps; add/rename/delete).
   - **Library** — the unified shelves (Favorites / In Progress / Recently Played /
     Inbox / folders) with type-ahead search.
   - **Queue** — the play queue with keyboard reorder (Up/Down/Remove).
   - **Audio** — the DSP panel: equalizer, boost/normalize, skip-silence, output device.
5. **Status bar** — state, remaining time, backend in use, sleep-timer countdown.

Tab order is header → transport → notebook → status. Focus opens on **Play/Pause**.
The window honors QUILL/OS high-contrast, dark mode, reduced-motion, and text scaling.

### 9.2 Menu bar (complete)

Native `wx.MenuBar` — inherently screen-reader-navigable, with mnemonics (`Alt`) and
accelerators. **Every accelerator is remappable** through the keymap editor
(`quill/core/feature_command_map.py`); the defaults below avoid `Ctrl+Alt` chords
(which fight screen readers). Items disable with a spoken reason when unavailable
(e.g. DAISY navigation on a non-DAISY book; EQ on the `wx.media` fallback).

- **File** — Open File… (Ctrl+O) · Open Folder as Book… (Ctrl+Shift+O) · Open URL or
  Stream… · Open from QUILL Library… · Open BARD Catalog… · Import Playlist (M3U/PLS)… ·
  Export Playlist… · Recent Books ▸ · Add Current to Library · Close Window (Ctrl+W,
  keeps playing) · Exit Player.
- **Playback** — Play/Pause (Space) · Stop · Skip Back (Left) · Skip Forward (Right) ·
  Previous Chapter (`[`) · Next Chapter (`]`) · Go to Position… (Ctrl+G) · Go to
  Percentage… · Restart Book · Speed ▸ (Slower `,` / Faster `.` / Reset / 0.75×–3.0×) ·
  Smart Rewind (toggle) · A–B Repeat ▸ (Set A / Set B / Clear) · Voice Control (toggle) ·
  Sleep Timer ▸ (Off / 5 / 15 / 30 / 60 min / End of Chapter / Custom…).
- **Audio** — Volume Up (Up) · Volume Down (Down) · Mute (M) · Volume Boost ▸ (Off /
  +3 dB / +6 dB / Normalize) · Equalizer… (E) · EQ Preset ▸ (Flat / Voice / Bass /
  Treble / Night / Podcast / your presets) · Skip Silence (toggle) · Gapless (toggle) ·
  Crossfade… · Output Device ▸.
- **Navigation** — Chapters (L) · Bookmarks (K) · Add Bookmark (B) · Add Bookmark with
  Note… (Shift+B) · Send Bookmark to Document (Ctrl+Shift+B) · Search in Audio… ·
  Where Am I? (W) · Read Status Bar · Previous Book · Next Book · DAISY Navigation ▸
  (By Heading / By Page / By Phrase — enabled only for DAISY titles).
- **Library** — Show Library (Ctrl+L) · Favorites · In Progress · Recently Played ·
  Inbox · New Folder… · Rename… · Move to Folder… · Mark as Finished · Search Library…
  (Ctrl+F) · Play Queue….
- **View** — Now Playing (focus view) · Mini-Player · Full Player · Theme ▸ (System /
  Light / Dark / High Contrast / From Cover) · Show Album Art · Show Waveform ·
  Verbosity ▸ (Minimal / Normal / Verbose) · Always on Top.
- **Magical** — Magical Mode (master toggle) and its sub-options (Section 9.5).
- **Tools** — Chapter Editor… · Edit Metadata / Look up Book Details… · Convert or
  Export Audio… · Download for Offline.
- **Settings** — Preferences… · Keyboard Shortcuts… · Audio Backend ▸ (Auto / libmpv /
  wx.media, with current status) · Sound Events & Earcons….
- **Help** — Player Help & Keyboard Reference · What's New · About.

### 9.3 Default keyboard map (all remappable)

| Key | Action | Key | Action |
| --- | --- | --- | --- |
| Space | Play/Pause | `[` / `]` | Prev / Next chapter |
| Left / Right | Skip back / forward | `,` / `.` | Slower / Faster |
| Up / Down | Volume up / down | M | Mute |
| B / Shift+B | Bookmark / with note | K | Bookmarks list |
| L | Chapters list | W | Where am I? |
| E | Equalizer | S | Sleep timer |
| Ctrl+L | Library | Ctrl+F | Search library |
| Ctrl+O | Open file | Ctrl+W | Close window (keeps playing) |
| Ctrl+G | Go to Position (H:M:S) | Ctrl+Shift+B | Send bookmark to document |

Core transport needs **no chord**. The full sheet is discoverable under **Help >
Keyboard Reference** and editable in the keymap editor.

### 9.4 Mini-Player (configurable home — resolves Open Question 4)

A compact always-available transport so playback continues while you read or write.
**Where it lives is a user setting** (`media_mini_player_home`): a **docked panel**, a
**status-bar strip**, or a **floating always-on-top frame** — default docked. It shows
title, chapter, position/remaining, and Play/Pause/Skip/Chapter controls, announces the
same events as the full window, and has a one-key **Expand to Full Player**.

### 9.5 Magical Mode (opt-in delight, never at accessibility's expense)

Off by default; one master toggle plus granular sub-toggles under the **Magical** menu.
The rule for everything here: **dual-channel** (anything shown is also spoken/earconed),
**opt-in**, **Safe-Mode-aware** (AI features vanish in Safe Mode), and it never blocks or
slows a core control. Magic for the ears first, then the eyes.

- **Cinematic Now Playing.** A calm, full-window focus view. For sighted users: ambient
  album-art background, a live waveform, and a color theme derived from the cover
  (reduced-motion honored). For everyone: a beautifully spoken context line and a quiet
  "listening" ambience that never competes with narration.
- **Spoken chapter intros.** Entering a chapter, a warm one-line flourish —
  "Chapter 12, *The Return*. Two hours ten remaining." — with a soft **chapter chime**
  from a selectable earcon personality (Classic / Warm / Minimal).
- **Welcome-back recap.** On resume: Position-only ("Back at 6 h 42 m, Chapter 12"), or —
  AI, opt-in, Safe-Mode-off — a one-sentence recap of the last few minutes so you slide
  back in. Uses the QUILL AI stack; you always approve enabling it.
- **Chapter summary on demand.** "Summarize this chapter" (AI, opt-in) speaks a short
  synopsis — useful for study or for re-finding a passage.
- **Ambient soundscape.** Optional low, tasteful background beds (Off by default) with
  selectable packs; auto-ducks under speech and narration.
- **Gentle sleep.** Sleep timer ends with a soft fade and a "goodnight" chime, and drops
  an auto-bookmark so morning-you never loses the place.
- **Listening stats & streaks.** Optional, announced (not just shown): hours listened,
  books finished, current streak — celebrated with a small earcon, never nagging.
- **Time-of-day greeting.** Optional warm greeting on open ("Good evening — ready for
  *The Return*?"), spoken and shown.

Every magical feature degrades cleanly: with the `wx.media` fallback or in Safe Mode the
AI/soundscape pieces simply aren't offered, and the core player is untouched.

### 9.6 System tray

The Player reuses the existing tray plumbing in `quill/ui/app_shell.py`
(`AppShellFrame._ensure_tray_icon` / `handle_app_close` / `_restore_from_tray` /
`_exit_application`) that Quill Radio, Cast, and Audio Studio already share — no new
tray engine. It is a **Windows notification-area** feature.

- **Icon and tooltip.** A `wx.adv.TaskBarIcon` whose tooltip is the live Now Playing
  line ("*The Return* — Ch 12 — 2 h 10 m left"), updated as state changes so a hover (or
  a screen reader querying the icon) reads current status.
- **Left double-click** restores/raises the Player Window (`_restore_from_tray`).
- **Right-click popup menu**, built fresh each open, mirroring the essentials of the menu
  bar: Play/Pause · Skip Back/Forward · Previous/Next Chapter · Add Bookmark · Sleep
  Timer ▸ · Where Am I? · Show Player · Show Mini-Player · **Exit Player**.
- **Close-to-tray behavior** is a user setting (`media_close_action`: *ask* / *minimize
  to tray* / *exit*), routed through `AppShellFrame.handle_app_close` so the Player shares
  the companion apps' one close path. A deliberate **Exit** sets the exit-requested flag
  (`_exit_application`) so it never bounces back into the tray (#1193).
- **The EVT_CLOSE modal rule.** The confirm dialog is **never** shown from inside the
  `EVT_CLOSE` handler — on wxMSW, with a screen reader's low-level keyboard hook active,
  `ShowModal` from that context can hang (the "Alt+F4 does nothing while playing" class of
  bug). The confirm is scheduled *after* the close flow, exactly as the shared handler
  already does.
- **macOS honesty.** `wx.adv.TaskBarIcon` yields a **Dock tile**, not a menu-bar extra, so
  there is no notification-area tray on macOS; the Player skips it quietly there rather
  than misrepresent it (same choice `AppShellFrame` documents). Close-to-tray degrades to
  ordinary minimize/close on macOS.

**Accessibility posture (important).** The OS notification-area icon and its mouse-style
popup are a historically weak spot for screen-reader users, so the tray is a
**convenience, never the only route**:

- **Global media hotkeys** (Section 7.13) drive Play/Pause, skip, and chapter moves even
  when the Player is minimized to the tray — you never need to open the tray menu to
  control playback.
- A **global "Restore Player" hotkey** brings the window back without touching the tray.
- **State changes are announced** through `quill.core.announce` (speech + braille) while
  minimized, at the chosen verbosity — the spoken cue, not a visual toast, is the primary
  feedback. Optional balloon/toast notifications are off by default and never replace the
  spoken announcement.
- Every tray command exists in the menu bar and the keymap, so nothing is reachable
  *only* by the tray.

### 9.7 Signature features (the QUILL-only greatness)

These are the features that make this more than "a competent player" — each is
accessibility-first and reuses infrastructure QUILL already has. All are additive: every
one also exists as a plain key/menu item, so a feature being off never removes a route.

- **Hands-free voice control.** Drive the player by voice — "play", "next chapter",
  "skip back thirty", "bookmark this", "how much is left", "sleep in twenty", "go to one
  twenty-three". Reuses QUILL's dictation/speech-recognition stack (Vosk / Whisper / the
  Nemotron spike), so it runs **offline** with no cloud. Off by default; opt-in with a
  push-to-talk key (and optional wake word). A confirmation earcon marks a recognized
  command; unrecognized input is announced, never guessed. Menu: **Playback > Voice
  Control** (toggle). Voice is purely additive — every command has a key too.
- **Bookmark → your document or Sticky Note.** Send a time-stamped bookmark straight
  into the open QUILL document or a Sticky Note as `[1:23:45] your note — Title`. This is
  the player-meets-writing bridge no standalone app has; it reuses the Beacon capture
  model. For protected BARD content, only the timestamp and your own note travel — never
  audio. Menu: **Navigation > Send Bookmark to Document** (Ctrl+Shift+B).
- **Braille status line.** A dedicated Now-Playing / chapter / position rendering on the
  refreshable braille display (position in cells, not just speech), via QUILL's braille
  infrastructure — so deaf-blind users are first-class, not an afterthought.
- **Quillin source & command extensibility.** A sandboxed contract lets a Quillin
  register new player **Sources** (a library/source provider) and **Commands** (menu /
  palette entries), gated by its manifest capabilities. The community can add a source or
  an action without any core change.
- **A–B repeat.** Set point A, set point B, and loop the segment — ideal for language
  learning, memorizing a passage, or transcription. Announces "Looping 3 minutes 20."
  Menu: **Playback > A–B Repeat ▸** (Set A / Set B / Clear).
- **Command-palette integration.** Every player command is fuzzy-searchable in QUILL's
  existing palette (`quill/ui/palette.py`).
- **Resume last on launch** (opt-in). Reopen straight into the last book at its exact
  position — a one-setting "pick up where I left off".
- **Search within audio.** Search chapter/heading titles today; search **spoken phrases**
  once an optional per-book Whisper transcript is generated (an opt-in action, consistent
  with the DAISY-audio-only v1 decision). Jumps to the match and announces its chapter.

### 9.8 Go to Position — precise H:M:S seek

Menu: **Playback > Go to Position…** (Ctrl+G). An accessible seek dialog:

- **Three labeled spin fields — Hours / Minutes / Seconds** — each announced and
  arrow-adjustable, seconds/minutes wrapping into the next unit; **or** a single
  **Timecode** field that accepts `1:23:45`, `83:45` (mm:ss), `5025` (seconds), or
  `1h23m45s`. Both routes are keyboard-complete.
- **Bounds-clamped** to the media duration; an out-of-range value is announced and
  clamped ("beyond the end — clamped to 11:14:00").
- On Enter it seeks and announces the landing point in context: "Jumped to 1 hour 23
  minutes 45 seconds — Chapter 12, *The Return*."
- A **Go to Percentage…** variant (0–100%) shares the dialog.
- Core: drives `MediaController.seek_to(ms)`; the parse/format helpers (`"1:23:45"` ↔ ms,
  and the spoken form) are **pure, unit-tested** functions, reusing the timestamp
  conventions in `quill/core/speech/chapter_io.py` (`format_timestamp`).

### 9.9 Rich status bar (QUILL-style, multi-field)

The Player's status bar mirrors QUILL's own multi-field status bar
(`quill/ui/main_frame_statusbar.py` — `SetFieldsCount` / `SetStatusText` with a per-field
announce, plus `quill/ui/audio_studio/status_bar.py`), so the review muscle memory is
**identical** to the editor. Fields, left to right:

1. **State** — Playing / Paused / Stopped / Buffering.
2. **Position** — "1:23:45 / 11:14:00 (12%)".
3. **Chapter** — "Ch 12 of 14 — The Return".
4. **Speed** — "1.25×".
5. **Sleep** — "Sleep 18:04" or "—".
6. **Source & format** — "BARD · DAISY audio" / "Local · M4B".
7. **Backend** — "libmpv" / "wx.media".

- **Keyboard review, exactly like QUILL's status bar:** a command to **move across the
  fields** (each announced with its label as you land on it — "Chapter: 12 of 14, The
  Return") and a one-key **read the whole bar**. Nothing here needs the mouse.
- Fields update live; changes announce at the chosen **verbosity** (Minimal suppresses
  routine position ticks; the fields are still there to review on demand).
- A **braille** rendering of the same fields is available on the display (Section 9.7).

### 9.10 Future / optional (captured, not v1)

Recorded so the spec is complete without bloating v1: reading **goals & pace**
("finish by Friday"), **series auto-advance**, **per-narrator preferences** (auto-apply
your usual speed/EQ for a narrator), **AudiobookShelf / Jellyfin / OPDS server** sources
(reusing the OPDS client), **rate & annotate** finished books, a **Do-Not-Disturb focus
session** (mute other QUILL notifications while listening), and **QuilleBeacon /
QuilleSync** cross-device position & bookmark sync (ties to `bard.md` A.6).

### 9.11 Standalone app (QUILL Media Player)

The player also ships as its **own standalone app**, exactly like Quill Radio, QUILL
Cast, and Audio Studio: `standalone/player/` wrapping `quill/apps/player.py`, built on
`quill/ui/app_shell.py::AppShellFrame` — so it gets the menu bar (Section 9.2), the system
tray (Section 9.6), and the shared close-to-tray / single-instance / update-check
behavior for free. Crucially it runs **the very same** `MediaController` and player UI
that QUILL hosts, so every feature and fix is shared, never forked.

- **One library, one place in every book.** The standalone reads and writes the same
  stores under `app_data_dir()` (library, bookmarks, `listening_positions.py`, `media_*`
  settings), so a book you start in QUILL continues in the standalone app and vice versa —
  same position, same bookmarks, same preferences.
- **Install & launch.** Start-Menu entry and an optional desktop icon via the installer;
  part of the QuillVille cross-app launcher (launch, or offer to download-install if
  absent, via `core/companion_install.py`), with **independent per-app updates** off the
  shared `Community-Access/quill` releases (`updates.fetch_app_releases`).
- **Handoff.** "Open in Media Player" from QUILL hands a file/book to the standalone (or
  plays in-app) — one playback session, never double audio.
- **Build.** A PyInstaller slice like the other apps, with **libmpv bundled** so DSP/EQ
  work out of the box; macOS gets the app without the notification-area tray (Dock only),
  per Section 9.6.

So: yes — one codebase, two front doors (inside QUILL and as **QUILL Media Player**),
identical behavior and shared data.

---

## 10. Settings, configuration, and persistence

Everything the player does is configurable, and every option is discoverable the QUILL
way: each setting is a spec in `quill/core/settings_specs.py` with a label, help text, and
search keywords, so the whole catalog is **type-to-find**. Nothing here is mouse-only.

### 10.1 The Preferences dialog

**Settings > Preferences…** opens a categorized dialog that mirrors QUILL's own settings
UX:

- A **category list** (left) and a **settings panel** (right); both fully keyboard- and
  screen-reader-navigable, each control with a real label and help text.
- A **search field** at the top filters across *all* categories (QUILL's searchable
  settings pattern) — type "sleep" or "skip" and only matching settings show, with the
  category announced.
- **Apply / OK / Cancel / Restore Defaults** buttons; Restore Defaults acts on the current
  category or all, with confirmation.
- A **scope switch** on each setting that supports it: **All books** (the default) vs
  **This book** (a per-book override — Section 10.3).
- Changing a setting announces the new value; anything that needs the libmpv backend or an
  AI connection shows a spoken reason when unavailable, never a silent no-op.

### 10.2 Settings catalog (by category)

Defaults in **bold**. Setting keys are `media_*` in `settings_specs.py`.

**Playback**
- Skip-back interval — 5 / 10 / **15** / 30 s / custom.
- Skip-forward interval — 15 / **30** / 60 s / custom.
- Default playback speed — 0.5×–4.0× (**1.0×**); **Remember speed per book** (on).
- Smart rewind — **On**; curve/amount (how much to rewind vs time away).
- On resume — **Restore exact position**; Resume last book on launch (**off**).
- Stop at end of chapter — **off**; Bookmark on pause — **off**.
- Gapless playback — **On** (libmpv); Crossfade — **Off** / 1–12 s.

**Audio & DSP**
- Audio backend — **Auto** / libmpv / wx.media (shows current + capability).
- Default EQ preset — **Flat** / Voice / Bass / Treble / Night / Podcast / user preset.
- EQ scope — **Global** vs per-book; 10 bands ±12 dB with named user presets.
- Volume boost — **Off** / +3 / +6 dB; Loudness normalization — **Off**.
- Skip silence — **Off**; Output device — **System default** / pick.
- Startup volume — **Last used** vs fixed.

**Chapters & navigation**
- Announce chapter on entry — **On**; Chapter chime — **On** (pack chosen under
  Announcements & sound).
- DAISY default navigation level — **Heading** / Page / Phrase.
- "Where am I?" detail — Brief / **Full** (title, chapter, position, remaining, speed).

**Bookmarks**
- Auto-bookmark on sleep-timer stop — **On**; on pause — **off**.
- Default target for *Send to Document* — **Open document** / Sticky Note.
- Timestamp format — **H:MM:SS**; Bookmark export format — Markdown / CSV / text.

**Library**
- Default view — **In Progress** / Favorites / Recently Played / Inbox / All.
- Auto-add opened files to Inbox — **On**; Mark-finished threshold — **95%** / custom.
- Default sort — **Recently played** / Title / Author / Added; Series auto-advance — **off**.

**Announcements & sound**
- Verbosity — Minimal / **Normal** / Verbose.
- Self-voicing (built-in speech even without a screen reader) — **off**.
- Announce speed / volume / EQ changes — **On**; Position ticks — **off**.
- Earcon pack — **Classic** / Warm / Minimal; per-event earcon toggles
  (play, pause, bookmark, chapter, end).
- Braille status line — **On** where a display is present; choose which fields appear.

**Voice control**
- Enable — **off**; Push-to-talk key; Wake word — **off** / phrase.
- Recognition engine — **Auto** (offline: Vosk / Whisper); Confirmation earcon — **On**;
  Command language.

**Sleep timer**
- Default duration — 5 / 15 / **30** / 60 min / End of chapter.
- Fade-out length — **5 s**; "Still awake?" prompt before stop — **On**.

**Now Playing & OS integration**
- System Media Transport Controls / media keys — **On**; Global media hotkeys — **On**.
- Global "Restore Player" hotkey — configurable.
- Mini-player home — **Docked** / Status-bar strip / Floating (configurable, per 9.4).
- Always on top — **off**; Show album art — **On**; Show waveform — **On**.

**Magical Mode** (all opt-in; AI items vanish in Safe Mode — Section 9.5)
- Magical Mode master — **off**; Cinematic Now Playing; Spoken chapter intros;
  Welcome-back recap — **Off** / Position only / AI recap; Ambient soundscape — **Off** /
  pack; Chapter chime personality; AI chapter summary; Listening stats & streaks;
  Time-of-day greeting.

**Downloads & storage**
- Download location; Keep offline (Library / BARD titles) — **On**;
  Resumable downloads + integrity check — **On**; Cache size cap; Clear cache.

**Appearance**
- Theme — **System** / Light / Dark / High Contrast / From Cover.
- Text scaling; Reduced motion — **Follow OS**; Waveform animation — **On**.

**Privacy & network**
- Safe Mode disables all network sources (local playback still works).
- Telemetry — **Off** (fixed, not a toggle); Clear listening history;
  Cross-device position sync (QuilleSync) — **off**; BARD sign-in / sign-out.

**Keyboard**
- Open **Keyboard Shortcuts…** (the keymap editor) to remap every command; Import /
  Export keymap; defaults avoid `Ctrl+Alt` chords.

**Advanced**
- Backend override + libmpv path; Log verbosity; Per-book overrides manager (10.3);
  Reset all player settings to defaults.

### 10.3 Per-book overrides and scope

Speed, volume/mute, EQ, and skip-silence can be **remembered per book** (extending
`quill/core/audio_studio/book_prefs.py`) so a fast talker always opens at your preferred
speed while everything else keeps the global default. Every override-capable setting shows
an **All books / This book** scope switch; an **Advanced > Per-book overrides** manager
lists what each book has customized, with a one-key **reset to default**.

### 10.4 Persistence

- **Per-book:** position (`quill/core/speech/listening_positions.py`, keyed by
  `path|size`); volume/mute/speed/EQ (`book_prefs.py`, extended); bookmarks
  (`media_bookmarks.json`).
- **Global:** every `media_*` setting above, declared in `settings_specs.py` (searchable)
  and saved via `quill/core/settings.py`.
- **Library / queue:** existing `audio_studio_library.json`, `audio_studio_play_queue.json`.
- All writes are **atomic** via `quill/core/storage.py::write_json_atomic`, schema-validated
  where applicable. **No secret is ever written here** — BARD credentials live only in the
  Secrets Manager (`quill/core/secrets.py`).

### 10.5 Import / export and reset

- **Export / Import settings** — round-trip the player configuration (and, optionally, the
  keymap and EQ presets) as a portable JSON file, so a setup moves between machines.
- **Restore Defaults** — per category or all; a per-book **reset** clears just that book's
  overrides. Nothing destructive happens without a confirmation.

---

## 11. Threading

Playback, timers, and UI live on the **UI thread**. Probing (ffprobe/`mutagen`),
library scans, DAISY parsing, downloads, and chapter assembly run on `TaskManager`;
results marshal back with `call_ui_safely` / `wx.CallAfter`. The controller is
UI-thread-affine; the core domain services it calls are pure and thread-safe.

---

## 12. Backend capability and graceful degradation

| Capability | libmpv (`MpvAudioEngine`) | `wx.media` (`WxMediaEngine`, default) |
| --- | --- | --- |
| Core transport, seek, chapters | Yes | Yes |
| Pitch-preserving speed | Yes (`scaletempo2`) | Coarse, no pitch preserve |
| Equalizer / boost / normalize | Yes | No (controls disabled + announced) |
| Skip silence | Yes | No |
| Gapless / crossfade | Yes | Sequential only |

**libmpv is bundled with the default install** (resolves Open Question 1), so the rich
DSP path — EQ, boost/normalize, skip-silence, gapless, pitch-preserving speed — is
available out of the box and EQ can be on by default. The `wx.media` column is the
**fallback** only when libmpv genuinely cannot load (e.g. a stripped or blocked
environment). The player **detects backend capability at load** and, on the fallback,
hides or disables unsupported controls with a spoken, explained reason. No feature
silently no-ops.

---

## 13. Security and privacy

- BARD protected content per Section 7.16 and `bard.md` — sanctioned decryption only,
  keys in memory only, never an unprotected copy on disk.
- No telemetry; no network egress except the sources the user chose. Any new host
  (e.g. BARD/broker) is a reviewed egress entry (GATE-9).
- Safe Mode disables network sources; local playback still works.

---

## 14. Testing

- **Core (unit, `smoke`-tagged where central):** `MediaController` transport/state
  machine with a fake engine and fake clock; chapter parsing (ID3/M4B/DAISY/JSON);
  DAISY navigation tree; bookmark add/jump/export; resume round-trip; queue ordering;
  playlist import/export; per-book prefs; EQ/DSP settings serialization; skip-silence
  and boost parameter mapping.
- **Backend contract:** the same `AudioEngine`-protocol suite run against a fake
  engine; capability matrix asserted so degradation paths are covered.
- **UI (existing patterns):** `PlayerPanel`/workbench tests under
  `tests/unit/ui/audio_studio/` extended for the new panels; accessible-name/role
  assertions.

---

## 15. Gates and budgets

- New core modules under `quill/core/media/` are strict-typed and in `mypy` scope.
- Any new exception inherits `CodedError` with a unique `QUILL-MEDIA-*` code (GATE-EC).
- Dialogs go through `_show_modal_dialog` (dialog inventory / button-contract gates).
- New hosts pass the egress audit (GATE-9); module size budgets updated as UI grows.

---

## 16. Phased build plan

1. **Controller + engine capability** — `MediaController`, `MediaItem`, capability
   detection, events; fake-engine tests. Reuse `create_engine()`.
2. **Player shell** — `MediaPlayerMixin`, player window (reusing `PlayerPanel`),
   mini-player, media keys / Now Playing. Wire resume + library.
3. **DSP** — EQ, boost/normalize, skip-silence on the libmpv backend; capability
   degradation on `wx.media`.
4. **Chapters + bookmarks** — unified chapter list from all sources; rich bookmarks
   with notes and export.
5. **DAISY navigation** — DAISY audio parser + navigation tree (unblocks BARD audio).
6. **Unified library** — cross-source shelves, folders, sequential playback, search.
7. **BARD integration** — protected playback via the sanctioned mechanism once the
   BARD 2.0 contract and Token Manager land (`bard.md`).

Each phase ends green on `ruff`, scoped `mypy`, and its targeted tests before the next.

---

## 17. Open questions

1. **libmpv distribution** — bundle `libmpv-2.dll` (and macOS equivalent) with the
   default install so DSP/EQ is available out of the box, or keep it an on-demand
   engine pack? (Affects whether EQ is default-on.)

   Answer: Bundle.

2. **DAISY scope** — full DAISY 3 (audio+text sync, e.g. read-along highlighting) or
   audio-navigation-only for v1?

   Answer: Audio only for now.

3. **BARD content protection** — pending the sanctioned mechanism (`bard.md` E.9);
   determines the exact playback path on Windows vs macOS.
4. **Mini-player home** — dockable panel, status-bar strip, or floating frame as the
   default?

   Answer: Can we make this configurable please?

## 18. Future expansion (deferred beyond the first release)

These are intentionally deferred; the shipped player is fully usable without them.

- **Voice control — BUILT, including hands-free.** Drive the player by voice ("play",
  "next chapter", "skip back thirty", "bookmark this", "how much is left", "go to one
  twenty-three", "sleep in twenty"). Two entry points:
  - **Listen for a Command (Ctrl+Shift+L)** — hands-free push-to-talk. A `wx.ITEM_CHECK`
    toggle: first press starts the microphone, second press stops and transcribes. Capture
    and transcription reuse QUILL's shipping **offline** stack (#617) — `MicRecorder` +
    `VoiceServices` on a **small Whisper model** (Base/Tiny/Small; short commands favour
    latency over accuracy, `service.preferred_command_model`). The recognized text is fed
    to the same `parse_voice_command` → `apply_voice_intent` used by the typed path.
    Accessibility is first-class (Desktop A11y spec): a distinct earcon and announcement at
    every state (Listening / Working / result / not-recognized / no-speech / mic-unavailable /
    error), success queued and failures interrupting; the audiobook is **ducked** (not paused)
    while listening; actual capture starts a beat after the "Listening" cue so the screen
    reader's own speech isn't recorded; a hard time cap closes a forgotten-open mic; and the
    menu item's check state mirrors the live listening state.
  - **Type a Voice Command (Ctrl+Shift+V)** — the say-or-type command bar (keyboard- or
    OS-dictation-friendly), for when speaking aloud isn't wanted.
  - The command grammar and dispatch are pure, engine-free, unit-tested modules
    (`quill/core/media/voice.py`, `quill/ui/media/voice_control.py`); the capture glue and
    event styling are `quill/ui/media/voice_capture.py` + `quill/ui/media/listen_mixin.py`.
    Every voice command also has a key, so voice is purely additive.
  - **Still future:** an always-on hotword ("hey player") so no key press is needed to start
    listening — QUILL has the wake-word groundwork (#663), not yet wired into the player.
- **Full DAISY 3 read-along** (audio + text sync / highlighting) — v1 is audio-navigation
  only (Open Question 2). Multi-file DAISY *navigation and playback* ships.
- **Magical AI recaps** — an AI summary of the last few minutes needs a transcript of the
  audio; the chapter + position welcome-back recap ships, the AI recap is a future item.
- **Embedded in-QUILL player window.** Today QUILL opens the player via **Tools ▸ Media ▸
  Media Player**, which launches the standalone **Quill Media Player** (one codebase, shared
  library / bookmarks / positions / settings). A future option is an *embedded* player panel
  inside the QUILL frame; the launch integration ships first because it is low-risk and gives
  the same reach without touching QUILL's core frame.
- **Global media settings in QUILL's Preferences.** Because the in-QUILL entry launches the
  standalone app, the player carries its own settings (`media_*`, `quill/core/media/config.py`);
  registering them into QUILL's global Preferences dialog is only needed once an embedded
  window lands.

## 19. Implementation notes — deltas from this design

Decisions made during the build that refine the design above (this section is the
source of truth where it differs from earlier prose):

- **Chapters render as a tree, not a flat list.** Where this document says "chapter
  list", the shipped UI is a `wx.TreeCtrl`: a multi-level table of contents (DAISY
  headings, nested sections) keeps its hierarchy, and a flat book shows a single level.
  Enter jumps; for a book split across files, the node loads that file and moves there.
- **LibriVox is the initial audio-library source.** The unified library (Sections 3 / 7.12)
  ships against the free, public-domain **LibriVox** catalog (`quill/core/media/librivox.py`,
  File ▸ Book Library), with per-section multi-track playback. OPDS/AudiobookShelf and
  other sources remain future additions behind the same shape.
- **DAISY is single- and multi-file.** A single-audio DAISY book seeks within one file;
  a multi-file book loads the right audio and parks at the SMIL offset (audio-navigation
  only; text+audio read-along stays a future item, Section 18).
- **In-QUILL entry is launch-based.** QUILL opens the player via **Tools ▸ Media ▸ Media
  Player**, which launches the standalone app (shared library / bookmarks / positions).
  The embedded-window design in this PRD is a documented future option (Section 18).
- **Settings today are menu-driven.** The searchable Preferences dialog (Section 10) is on
  the roadmap; the shipped controls live on the Audio page and the Playback / View menus,
  with the full `media_*` catalogue defaulted in `quill/core/media/config.py`.
   