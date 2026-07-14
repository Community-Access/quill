# Voice preview feedback: generating cue, stop-the-prior-preview, Play/Stop button — design

## Problem

Previewing a voice (Voice Browser's **&Preview Selected Voice** button, and the
Download Optional Components hub's **&Test** button for voice rows) has three
related gaps, all traced to the same code path
(`MainFrame._preview_voice` / `_play_preview_asset` in `quill/ui/main_frame.py`):

1. **No feedback while synthesis is slow.** Neural/subprocess voices (Kokoro,
   Piper, eSpeak, DECtalk, ElevenLabs) can take a real, human-noticeable amount
   of time to synthesize before anything plays. There is no sound or
   announcement telling the user something is happening.
2. **Overlapping previews.** `_preview_voice` is dispatched as a fire-and-forget
   background thread via `_run_background_task` with no shared "currently
   previewing" state anywhere. Triggering a second preview while the first is
   still generating or playing does not stop the first — both its audio and
   its "Preview started"/"Preview finished" status announcements can overlap
   with the new one.
3. **The button never reflects state.** Both the Voice Browser's Preview
   button and the hub's Test button are static labels — they never become a
   Stop affordance while a preview is generating or playing, so there is no
   way to cancel one short of waiting it out.

## Non-goals

- **No true pause/resume.** WAV/MP3 preview playback here goes through
  `winsound.PlaySound` / Windows MCI, both blocking calls with no
  suspend-and-resume capability. The button is **Preview ↔ Stop**: clicking
  while active cancels playback outright; the next click starts fresh from
  the beginning. Building real pause/resume would mean replacing the
  blocking playback backend entirely — out of scope here.
- **No forced cancellation of in-flight external synthesis.** If a Piper/
  eSpeak/DECtalk subprocess or Kokoro's Python call is still actively
  computing when the user starts a new preview (or hits Stop), QUILL does not
  kill it. It keeps running in the background to completion and its result
  is discarded silently (never played, no callback fires). Only **playback**
  and **QUILL's own announcements** are guaranteed to stop immediately. This
  is a deliberate scope boundary, not an oversight — tracking and terminating
  arbitrary external processes/Python calls is a materially bigger change.
- **Not a new "mode" setting.** No combined enum setting like
  `voice_preview_cue = sound|announcement|both|none`. The sound half already
  has a general, reusable per-event toggle system (Sound Events dialog); the
  announcement half gets one new boolean. Configuring "both" means both are
  independently on by default.
- **Not touching the SAPI5 Read Aloud preview's underlying controller.**
  `ReadAloudController.start`/`.stop()` already exists and already works for
  the `sapi5` preview branch; this design only adds the generation-token
  staleness check and Stop-button wiring around it, not new controller
  behavior.

## Design

### 1. Single active-preview tracking (fixes overlap)

`MainFrame` gains a small piece of state — a monotonically increasing
generation counter (e.g. `self._preview_generation: int`) plus a reference to
whatever is needed to stop the current preview. `_preview_voice` becomes the
single choke point:

- On entry, increment the counter and capture `my_generation = self._preview_generation`.
- Immediately stop whatever was previously active:
  - `sapi5` branch: `self._read_aloud.stop()` (existing method).
  - WAV/MP3 branches (bundled sample or a synthesized clip): stop/purge the
    current `winsound`/MCI playback (`winsound.PlaySound(None, winsound.SND_PURGE)`
    and an MCI `stop`+`close` on the `quill_preview` alias, best-effort, never
    raising).
  - Cancel any pending "generating" cue timer (§2).
- Every callback that eventually fires for this generation (the "generating"
  cue timer, the background-task completion handler, the `on_state_change`
  callback in §3) first checks `my_generation == self._preview_generation`
  and is a no-op if stale. This is what prevents a late-finishing old preview
  from announcing "Preview finished" or playing over a newer one, and is also
  the mechanism the non-goal above relies on (a stale generation's result is
  simply dropped when it does arrive).

### 2. The "generating, please wait" cue

- When `_preview_voice` starts synthesis (i.e. every branch except sample
  playback, where there is nothing to wait for), it starts a one-shot
  `~400ms` `wx.CallLater` timer tagged with `my_generation`.
- If synthesis finishes first, the timer is cancelled and nothing fires — this
  is what keeps fast paths (SAPI5, sample playback, a fast Kokoro run) silent.
- If the timer fires first (still the current generation), it fires the cue
  **once**:
  - **Sound half:** `post_sound(SoundEvent.VOICE_PREVIEW_GENERATING)` (new
    enum member in `quill/core/sound_events.py`). The bundled Ink pack
    (`quill/assets/sound_packs/ink/manifest.json`) maps this new event key to
    the **existing** `ai_start.wav` file (no new audio asset needed — same
    tone already used for "AI thinking started", semantically the same "the
    system is working on it" cue). Because it is a real `SoundEvent` loaded
    from the pack, it automatically appears in the existing Sound Events
    dialog as its own togglable entry, and already respects the master
    `sound_enabled` on/off switch and `sound_volume` — no new sound
    infrastructure required.
  - **Announcement half:** a new setting, `voice_preview_announce_generating`
    (`bool`, default `True`, category `accessibility` in
    `quill/core/settings_specs.py` next to the other sound settings). When
    on, speaks "Generating preview, please wait" once via the existing
    `_announce` path.
  - Both halves are independently toggleable through existing mechanisms
    (Sound Events dialog for the sound; the new setting for the
    announcement) — satisfying "configuration available" without a new
    combined setting.
- No repetition: this is genuinely one-shot per generation, matching the
  approved answer. If a generation somehow takes much longer, nothing further
  fires until the real preview plays, an error surfaces, or the user hits
  Stop.

### 3. Play ↔ Stop button (Voice Browser + hub Test button for voices)

- `_preview_voice` gains an optional keyword-only parameter,
  `on_state_change: Callable[[str], None] | None = None`, invoked via
  `wx.CallAfter` with one of `"generating"`, `"playing"`, `"idle"` at the
  matching lifecycle points (staleness-checked against the generation token
  like everything else in this design). `"idle"` covers both normal
  completion and being stopped/superseded.
- **Voice Browser dialog** (`quill/ui/voice_browser_dialog.py`): `_do_preview`
  passes a closure that relabels `self._preview_btn` between
  `"&Preview Selected Voice"` (idle) and `"&Stop Preview"` (generating/
  playing). The existing click handler, when the button is currently in the
  Stop state, calls the new stop path from §1 instead of starting a new
  preview.
- **Download Optional Components hub** (`quill/ui/optional_components_dialog.py`):
  `_on_test`, when the selected row is a voice component (i.e.
  `oc.read_aloud_engine_for_component(component_id) is not None`), wires the
  same `on_state_change` closure onto the shared `test_btn`, relabeling it
  between `"&Test"` and `"&Stop"`. Non-voice rows (tool/engine self-tests)
  are unaffected — they already run to completion quickly and announce their
  own result.
- Clicking Stop in either surface routes through the same generation-token
  stop path as starting a new preview (§1), so the two entry points share one
  implementation.

## File-by-file touch points

- `quill/ui/main_frame.py` — `_preview_voice` (generation tracking, cue timer,
  `on_state_change` plumbing, stop path), `_play_preview_asset` (purge/stop
  support).
- `quill/core/sound_events.py` — new `VOICE_PREVIEW_GENERATING` member.
- `quill/assets/sound_packs/ink/manifest.json` — new event → `ai_start.wav`
  mapping (reused file, no new binary).
- `quill/core/settings.py` / `quill/core/settings_specs.py` — new
  `voice_preview_announce_generating` bool (default `True`), parse/
  constructor wiring, spec entry (category `accessibility`).
- `quill/ui/voice_browser_dialog.py` — `_do_preview`/`_preview_btn` state
  wiring.
- `quill/ui/optional_components_dialog.py` — `_on_test`/`test_btn` state
  wiring for voice rows.

## Testing

- Core: settings round-trip + default for `voice_preview_announce_generating`;
  a wx-free unit test for the generation-token staleness logic (start
  generation N, "finish" generation N-1, assert no callback fires); the new
  `SoundEvent` member resolves through `sound_manager`/the Ink manifest.
- UI: Voice Browser button relabels generating → playing → idle across a
  faked slow preview; the hub's Test button does the same only for voice
  rows and is unaffected for tool/engine rows; starting a second preview
  while the first is active stops the first's (faked) playback and does not
  fire its completion callback.
