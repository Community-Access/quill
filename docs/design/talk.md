# talk.md — Always-On Voice ("Hey Player") Specification

> **The one decisive question:** are we willing to keep a microphone open and run
> speech recognition continuously on the user's machine — and can we make that
> state *unmistakable, at all times, without a screen*? If yes, this ships. If not,
> push-to-talk (Ctrl+Shift+L, already built) is the honest ceiling.

This document specifies **always-on voice control** — hands-free listening with no
key press to begin — for QUILL's speech surfaces, focused on the **Quill Media
Player** where it is the one remaining voice item. It is written to be built
against directly. It reuses the offline stack that already ships (#617) and the
push-to-talk feature already built for the player; it adds only the *continuous*
listening loop and the wake-phrase gate in front of it.

Status of the pieces this builds on (all shipping today):
- **Push-to-talk in the player** — `quill/ui/media/listen_mixin.py`,
  `quill/ui/media/voice_capture.py` (capture → transcribe → parse → dispatch).
- **The command grammar** — `quill/core/media/voice.py` (`parse_voice_command`),
  `quill/ui/media/voice_control.py` (`apply_voice_intent`).
- **The wake-word policy engine** — `quill/core/speech/wakeword.py`
  (`WakeController`), already used by the editor's "Hey QUILL". Pure, wx-free,
  string-driven, fully unit-testable. **This spec's core reuses it unchanged.**
- **Offline recognition** — `MicRecorder`, `VoiceServices`, Whisper/Nemotron/Vosk.
- **The safety allowlist** — voice only ever reaches non-destructive commands.

---

## 1. Goal, and the one hard problem

**Goal.** Let a user say a wake phrase — *"Hey Player"* — and then a command
(*"next chapter"*, *"skip back thirty"*), with **no key press at any point**, fully
offline, and control the player entirely by voice while their hands and attention
are elsewhere.

**The hard problem is not recognition. It is perceivability.** A sighted user knows
an always-on mic is live from an on-screen indicator. A blind user cannot. An
always-open microphone that the user has *forgotten is open* is the single most
serious failure mode of this feature — worse than a missed command, worse than a
misfire. Everything below is organized around making "the mic is listening" a fact
the user can perceive at any instant and review on demand, and around never letting
that state persist silently.

**Non-goals (v1):** dictating document text hands-free (that is Locked Dictation);
multi-turn conversation in the player; wake-word training/personalization; any
cloud recognition; running when the player is not the foreground intent.

---

## 2. The shape: a two-stage gate

Always-on voice is two nested listeners:

```
        ┌─────────────────────────  ALWAYS-LISTENING LOOP  ─────────────────────────┐
        │                                                                            │
   mic ─┼─▶ rolling window ─▶ recognizer ─▶ WakeController.on_window(text)           │
        │        (~2.5 s)         (STT)            │                                  │
        │                                          ├─ no wake  → keep listening       │
        │                                          │            (+ periodic reminder) │
        │                                          ├─ "hey player" alone → ARM        │
        │                                          │            → capture ONE command │
        │                                          │              window → parse →    │
        │                                          │              apply_voice_intent  │
        │                                          └─ "hey player NEXT CHAPTER"        │
        │                                                     → DISPATCH the trailing  │
        │                                                       command immediately    │
        └────────────────────────────────────────────────────────────────────────────┘
```

Stage 1 (the wake gate) is **`WakeController`** — already built, already tested. It
consumes transcribed windows and emits ordered `WakeEffect`s
(`sound | announce | arm | dispatch | listen_again | reminder | stop_listen`). It
never runs a command; it emits `arm`/`dispatch` and the UI validates against the
allowlist and executes. The player supplies the *effects executor* and the capture
loop; the *decision logic* is imported wholesale.

Stage 2 (the command) is the **push-to-talk pipeline already built**: on `arm`,
open a single capture window, `stop_and_transcribe`, `dispatch_transcript` →
`parse_voice_command` → `apply_voice_intent`. On `dispatch` (an inline command
after the wake phrase), skip capture and feed the trailing text straight through.

**Design consequence:** almost nothing new is *logic*. What is new is a
**continuous capture loop** and its **accessibility skin**. That is the whole job.

---

## 3. The wake phrase

- **Default:** `"hey player"`. Configurable to `"hey quill"` (shared with the editor
  loop) or a user phrase, via settings.
- **Matching** reuses `voice_commands.extract_transcript_body`: it strips a leading
  wake phrase and returns the remainder — `""` for a bare wake ("arm and wait"), the
  trailing text when a command follows inline, `None` when the window did not address
  the player at all. `WAKE_PHRASES` gains `"hey player"`.
- **Phrase choice is a real accuracy lever.** Two syllables with distinct consonants
  ("hey player") resist false-accepts far better than a single common word. The
  settings UI should warn against single-word or very common phrases (they will
  trigger on the audiobook's own narration).
- **The audiobook is the adversary.** Because a book is playing, its narration is
  the dominant false-accept source. Mitigations: (a) the phrase must be uncommon in
  prose; (b) duck-while-listening lowers the book under the mic (§6); (c) the
  cooldown after a wake prevents the wake utterance's own tail from re-triggering
  (`WakeController.cooldown_windows`).

---

## 4. Recognition pipeline & endpointing

There are two implementable engines behind the same `WakeController`. Ship the
first; the second is the documented performance upgrade.

### 4a. Transcription-based wake (v1 — buildable today)

Continuously record short rolling windows (~2.5 s, ~0.5 s overlap), transcribe each
with the small Whisper/Nemotron model already resolved by
`build_media_voice_services`, and feed the text to `WakeController.on_window`. This
is exactly what the editor's "Hey QUILL" does today, so it is proven — but see §7:
it runs full STT continuously, which is **CPU/battery-heavy**. Bound it hard.

- **Command endpointing after wake:** apply **VAD** (`core/speech/vad.py`,
  `SilenceDetector`) to the *command* window so the turn ends when the user stops
  speaking, rather than a fixed timeout that clips long commands. (The editor loop
  does not yet do this for its command window — a known gap in the #617 audit; the
  player should do it from the start.)
- **Sample rate is the frame rate.** Feed `SilenceDetector(sample_rate=SAMPLE_RATE)`
  — never `SAMPLE_RATE * CHANNELS` (a bug the audit found and fixed elsewhere).

### 4b. Low-power keyword spotter (v2 — the real destination, "Part Two")

Replace the "transcribe every window" front end with a **three-tier cascade** so the
expensive model almost never runs. Each tier only invokes the next when it must:

```
  mic ─▶ [Tier 0: VAD gate] ──speech?──▶ [Tier 1: keyword spotter] ──"hey player"?──▶ [Tier 2: full STT]
              onnx, ~1 MB          no │        onnx, tiny, text-keyworded      no │      Whisper/Nemotron
              negligible CPU          ▼                                           ▼      (command only)
              (idle = free)      keep gating                                  keep listening
```

- **Tier 0 — VAD gate (Silero VAD, ONNX, MIT, ~1 MB).** Suppress everything
  downstream during silence. A quiet room costs ~nothing; nothing else spins up until
  someone actually speaks. `core/speech/vad.py` already provides the endpointing
  primitive; add a tiny always-on energy/VAD front gate.
- **Tier 1 — keyword spotter.** Runs only on speech frames, decides "was the wake
  phrase said?", and is the piece that replaces continuous Whisper. **Recommended
  model: the sherpa-onnx keyword spotter** — see below.
- **Tier 2 — full STT (already built).** Whisper-small / Nemotron, fired **only**
  after a wake hit, to transcribe the actual command. This is where the real cost
  lives, and now it is on-demand instead of continuous.

This slots in behind `WakeController` with **zero change to the policy or the command
stage** — Tier 1 simply produces the transcribed/greenlit window the controller
already consumes.

#### The model recommendation, and why it scales

**Primary: sherpa-onnx keyword spotting.** QUILL *already bundles the sherpa-onnx
runtime* (it powers Nemotron) — **torch-free, ONNX, CPU-only**, consistent with the
project rule that speech engines never require torch (see `feedback_tts_no_torch`,
`project_nemotron_dictation`). Two properties make it the right pick:

1. **No new heavy dependency.** The runtime is present; a keyword-spotting model is a
   small streaming zipformer-transducer with real-time factor well under 1 on a
   laptop CPU.
2. **Keywords are plain text, not trained models.** The wake phrase(s) live in a
   `keywords.txt` with a per-keyword detection threshold/boost. `"hey player"`,
   `"hey radio"`, `"hey quill"`, `"hey weather"` are *lines in a file*. **This is the
   scaling story:** every app in the QuillVille family gets its own wake word at zero
   marginal model cost, and a user can add or tune a phrase without any retraining.

**Alternative: openWakeWord (Apache-2.0, ONNX).** Higher raw wake accuracy via a
shared audio-embedding feature extractor plus a tiny (~hundreds of KB) per-word
classifier head — so it also scales by *adding small heads*, one per phrase. Trade-
off: a genuinely custom phrase needs a synthetic-data training step, and it adds ONNX
models to the bundle. Keep it as the fallback if sherpa-onnx KWS accuracy proves
marginal for the chosen phrase.

**Avoid for bundling: Picovoice Porcupine** — excellent and very light, but
proprietary licensing makes it a poor fit for a bundled open app. **microWakeWord**
(TFLite-micro, for ESP32-class devices) is not the pick either, but it is proof the
cascade architecture scales all the way down to a microcontroller — useful as a
"how low can this go" reference.

#### Scaling, in two dimensions

- **Across phrases/apps:** a text-keyworded spotter (sherpa-onnx) or a shared-
  embedding spotter (openWakeWord) makes each additional wake word ~free — a text
  line or a tiny head — so the whole app family and per-user custom phrases cost
  nothing extra. Contrast the v1 approach, where "listening" means a full STT pass
  every window regardless of phrase.
- **Across machines:** the cascade's idle cost is a ~1 MB VAD, so weak hardware stays
  responsive; the heavy model is gated behind two cheap tiers and runs only on a real
  hit. Degrade cleanly — if Tier 1 is unavailable, fall back to v1 (transcription-
  based) with the CPU/battery disclosure, or to push-to-talk.

#### Recommended first build (later work): a pure, swappable spotter adapter

Build Part Two the way the rest of this stack was built — **pure core first,
testable with plain strings, no live audio** — so the engine can be validated and
swapped without a microphone. The recommendation for the *first* increment:

- **Add a `KeywordSpotter` protocol and a text-driven adapter**, e.g.
  `quill/core/speech/keyword_spotter.py`, wx-free and unit-tested. It exposes the
  same string-in / effects-out contract the rest of the wake path already uses:
  frames (or an already-transcribed window, in the v1 shim) go in, and it reports
  whether the wake phrase fired and with what trailing text — the exact shape
  `WakeController.on_window` already consumes. So the spotter drops in front of the
  controller with **zero change to policy or the command stage**.
- **Keep the engine behind the protocol.** A `SherpaKeywordSpotter` implementation
  wraps the sherpa-onnx keyword-spotting model and reads its wake phrase(s) from a
  `keywords.txt` (the scaling property, §above). A `TranscriptionKeywordSpotter`
  wraps the v1 "transcribe every window then string-match" path. Both satisfy the
  same protocol, so v1 → v2 is a constructor swap, and tests target the protocol.
- **Unit-test with plain text, today.** Because the adapter's decision surface is
  strings + a threshold, the whole thing is testable now (phrase hit, near-miss
  below threshold, inline trailing command, cooldown interaction) without any audio
  — mirroring how `WakeController` and `parse_voice_command` are tested. The live
  sherpa-onnx model is then the only piece that needs on-device validation.
- **Cost/telemetry hook.** Give the adapter a cheap "was Tier 2 invoked?" signal so
  the duty-cycle (how often the full STT actually fires) can be measured and the
  CPU/battery claims verified on real hardware rather than asserted.

This makes Part Two land in the same low-risk, verifiable way as Part One: the
policy and the command grammar are already proven; the only genuinely new,
device-only piece is the acoustic model behind a tested seam.

**v1 must not pretend to be v2:** if we ship transcription-based always-on first,
settings and docs state plainly that it uses more CPU/battery than push-to-talk, and
that this cascade is the fix.

---

## 5. State machine

Reuse `WakeState` (`OFF | LISTENING | WOKEN`) and extend the player's own listening
states for the command stage. Full lifecycle:

```
OFF ──(enable always-on)──▶ LISTENING ──(wake, bare)──▶ WOKEN/ARMED
 ▲                              │  ▲                         │
 │                              │  │                         ▼
 │                       (periodic reminder)          CAPTURING_COMMAND
 │                              │  │                         │
 │                              │  └────(resume_listening)───┤
 │                              │                            ▼
 └──(disable / Safe Mode / ────┘                       TRANSCRIBING
     app close / instant off)                               │
                                                            ▼
                                                    EXECUTED / NOT_RECOGNIZED
                                                    / NO_SPEECH → resume LISTENING
```

Inline wake (`"hey player next chapter"`) shortcuts WOKEN → TRANSCRIBING by feeding
the trailing text directly (no command capture window).

---

## 6. Accessibility — the specification's core

This is not a section; it is the reason the feature is hard. Requirements are
**MUST** unless noted. They extend the push-to-talk model already built
(`VoiceCommandEvent` + `event_style`) and the Desktop-Accessibility guidance the
player already follows. Route **all** speech through the app's `_announce(message,
*, force, sound)` so braille mirroring and screen-reader-aware interrupt/queue come
for free — never a second TTS path.

### 6.1 The live-mic state must be continuously perceivable

- **Open/close earcons (MUST).** A distinct rising cue when always-listening starts
  and a falling cue when it stops — reusing `SoundEvent.CONVERSATION_ON` /
  `CONVERSATION_OFF`. Played even when speech is suppressed; the pair is the
  primary "mic is armed / mic is closed" signal.
- **Periodic "still listening" reminder (MUST).** `WakeController` already emits a
  `reminder` effect every `reminder_every` idle windows. Execute it as a soft cue
  (`SoundEvent.CONVERSATION_IDLE`) and/or a brief spoken "still listening," **user-
  configurable** (interval, and cue-only vs cue+speech). This is what makes a *long*
  quiet period distinguishable from "it silently died." Default: on.
- **Reviewable status (MUST).** While armed, the status field reads
  *"Listening for 'Hey Player'"* (from `WakeController.status_text()`); WOKEN reads
  *"Awake — say your command"*; OFF clears to *"Ready."* A screen-reader user reviews
  this on demand (NVDA `Insert+End`, JAWS status read); braille mirrors it
  persistently via `_announce`.
- **Menu check state (MUST).** The toggle is a `wx.ITEM_CHECK` item; its checkmark
  mirrors the armed state, giving a role-native second signal the reader announces.

### 6.2 The wake and command moments

Announcement/earcon/interrupt table (extends the push-to-talk `event_style`):

| Moment | Speak (concise) | Earcon | Interrupt? |
|---|---|---|---|
| Always-listening started | "Listening for Hey Player." | `CONVERSATION_ON` | yes |
| Woke (phrase heard) | *(earcon only; speech is noise here)* | `CONVERSATION_WAKE` | — |
| Armed, waiting for command | "Yes?" (short) | `CONVERSATION_LISTEN` | yes |
| Command recognized + run | the **effect** — "Paused." / "Skipped forward thirty." | `CONVERSATION_READY` | **no (queue)** |
| Not recognized | "Didn't catch a command. Heard: '…'." | `CONVERSATION_ERROR` | yes |
| No speech after wake | "No command heard." | `CONVERSATION_IDLE` | yes |
| Still listening (periodic) | *(cue; optional speech)* | `CONVERSATION_IDLE` | no |
| Stopped / disabled | "Stopped listening." | `CONVERSATION_OFF` | yes |
| Mic unavailable / error | "Microphone unavailable." / "Voice failed." | `CONVERSATION_ERROR` | yes |

Principles carried from push-to-talk: announce the **result**, not the mechanism;
routine success queues politely behind the reader; failures interrupt; echo the
transcript **only** on failure.

### 6.3 The screen-reader-captures-itself problem (amplified by always-on)

With a mic open continuously, the screen reader's own speech and the audiobook are
*always* candidates to be transcribed as a false wake.

- **Duck the book while a wake is being evaluated and during command capture**
  (`PlayerPanel.duck()`/`unduck()`, already built) — not paused; restored in a
  `finally` path. Duck **before** the wake earcon.
- **Gate capture around your own announcements.** When the player itself is
  announcing ("Yes?", a result), do not feed those windows to the wake matcher — a
  short post-announcement mute prevents the player's own voice from waking it.
- **Prefer a headset in docs**, but design for a laptop mic.
- **Never steal focus.** No modal "listening" dialog; the entire feature is
  transient announcements + status text + braille. Focus stays where the user put it.

### 6.4 Instant, reliable off

- Re-invoking the toggle, saying the stop phrase, closing the app, or entering Safe
  Mode all stop always-listening immediately and play `CONVERSATION_OFF`.
- Always-listening **does not survive app close** unless the user explicitly opts
  into persistence (and even then, never across Safe Mode).

---

## 7. Performance, battery, and honesty

Transcription-based always-on runs the STT model on every window — real CPU, real
battery, real heat on a laptop. This spec **requires** the cost be bounded and
disclosed:

- **Duty-cycle / gate.** Use VAD/energy to skip STT on clearly-silent windows so an
  idle room does not pin a core. (Even a coarse RMS gate helps.)
- **Model.** Use the *smallest* installed model for the wake loop (Tiny/Base) via
  the existing `preferred_command_model`; accuracy of the *phrase* matters less than
  latency and cost.
- **Bound it.** A hard idle cap that drops out of always-listening after a long
  quiet stretch (configurable; announced when it happens), so a forgotten session
  cannot run the CPU indefinitely.
- **Disclose it.** Settings and docs state plainly that always-on uses more
  CPU/battery than push-to-talk, and that v2 (keyword spotter, §4b) is the fix.
- **Degrade.** If capture or the engine fails mid-loop, fall back to OFF with a clear
  announcement — never a silent dead loop that looks armed but hears nothing.

---

## 8. Privacy, consent, and safety

- **On-device only.** No audio and no transcript leaves the machine. No network call
  is on this path; the network-egress audit stays unchanged.
- **Off by default; explicit opt-in.** Enabling always-on requires a one-time,
  screen-reader-clear consent that names the trade precisely: *"Always-on voice keeps
  your microphone open and listens continuously on this computer for the wake phrase.
  Nothing is uploaded. This uses more battery than press-to-talk."*
- **Safe Mode disables it** entirely, like every voice surface.
- **Allowlist.** The command stage reaches only the player's own command grammar
  (`parse_voice_command`) — itself a curated, non-destructive set. Saying the wrong
  thing cannot delete, send, or overwrite anything.
- **Perceivable = consentful.** The continuous cues (§6.1) are not just UX; they are
  how ongoing consent stays informed. A user must never be able to *forget* it is on.

---

## 9. Settings

All with real static-text labels; all off/conservative by default.

| Setting | Default | Notes |
|---|---|---|
| `player_always_listen_enabled` | off | The master switch (behind the consent gate). |
| `player_wake_phrase` | "hey player" | Warn on single-word / common phrases. |
| `player_wake_reminder_windows` | 12 | Idle windows between "still listening" cues (0 = off). |
| `player_wake_reminder_speak` | off | Cue-only vs cue+speech for the reminder. |
| `player_wake_duck_level` | 20 | Book volume % while evaluating a wake / capturing. |
| `player_wake_idle_cap_seconds` | 600 | Auto-stop after this much continuous quiet. |
| `player_wake_persist` | off | Re-arm on next launch (never across Safe Mode). |
| speech engine/model | inherited | Uses `settings.speech_provider` (Whisper/Nemotron/Vosk). |

---

## 10. Proposed module layout

Keep the wx-free policy pure and testable; keep the wx loop thin.

- **Reused unchanged:** `quill/core/speech/wakeword.py` (`WakeController`),
  `quill/core/speech/voice_commands.py` (`extract_transcript_body`, `WAKE_PHRASES`
  += "hey player"), `quill/core/speech/vad.py`, `quill/core/media/voice.py`,
  `quill/ui/media/voice_control.py`, `quill/ui/media/voice_capture.py`.
- **New, pure/core:** `quill/core/media/wake_session.py` — a thin, testable adapter
  that owns a `WakeController` + duty-cycle policy and maps its effects to the
  player's intent vocabulary (so effect→action is unit-tested with plain strings,
  no audio). Optional; `WakeController` may suffice.
- **New, UI (mixin, under the size budget):**
  `quill/ui/media/always_listen_mixin.py` — the continuous rolling-window capture
  loop (a `wx.Timer` + background STT worker via `wx.CallAfter`), the effects
  executor (earcon/announce/status/duck/dispatch), the consent gate, and the
  `wx.ITEM_CHECK` menu wiring. Mirrors `listen_mixin.py`; the player frame inherits
  both.
- **Menu/keymap:** *Playback ▸ Always Listen for Commands* (`wx.ITEM_CHECK`), an
  optional accelerator, and a keymap entry so it shows in Preferences.

---

## 11. Edge cases

- **Wake fires on the audiobook's narration** → duck + uncommon phrase + cooldown;
  a false wake that captures no real command lands on NO_SPEECH and resumes quietly.
- **Wake with an unrecognized trailing command** ("hey player do a barrel roll") →
  NOT_RECOGNIZED, echoes what was heard, resumes listening.
- **User speaks during the player's own announcement** → capture is gated around
  announcements (§6.3) so the player does not hear itself.
- **Mic seized by another app mid-loop** → MIC_UNAVAILABLE, fall to OFF, announce.
- **Focus is elsewhere entirely** → fine; the feature never depends on focus and
  never steals it. The toggle accelerator still stops it from anywhere in the app.
- **Two voice features at once** (push-to-talk + always-on) → mutually exclusive;
  starting one suspends the other.
- **Long quiet** → idle cap fires, announces "Stopped listening," plays
  `CONVERSATION_OFF`.

---

## 12. Testing

- **Pure policy (no audio):** `WakeController` is already covered; add player-specific
  tests for the effect→intent adapter with plain-string windows — bare wake arms,
  inline command dispatches, cooldown suppresses the wake tail, reminder cadence,
  unrecognized trailing command. Deterministic, fast, no mic.
- **Feedback styling:** every lifecycle event maps to a `(force, earcon)` and a
  concise phrase (extend the `event_style` table test).
- **Construction:** the player frame builds with the always-listen `wx.ITEM_CHECK`
  item and its handlers; resolution returns cleanly when no mic/model is present.
- **Live (device, human):** wake-accuracy against a playing audiobook; the
  screen-reader-captures-itself case on a laptop mic; battery/CPU under a real quiet
  room; NVDA/JAWS/Narrator perceivability of every state and the periodic reminder;
  braille persistence of the armed state. This is the promotion gate and cannot be
  faked headless.

---

## 13. Phased rollout

1. **P1 — Wake gate on the built pipeline.** Continuous rolling-window loop feeding
   `WakeController`; bare-wake → the existing command capture; full a11y skin
   (open/close/reminder cues, status, check state, duck-around-capture); consent
   gate; Safe-Mode off; idle cap. Ships transcription-based, disclosed as such.
2. **P2 — Inline commands + VAD endpointing.** "hey player next chapter" in one
   breath; VAD-bounded command windows; announcement-gated capture hardening.
3. **P3 — Low-power keyword spotter (§4b).** Replace the STT-every-window front end;
   drop CPU/battery to always-on-friendly levels. No change to policy or commands.
4. **P4 — Unify with "Hey QUILL."** Share the wake loop/config across the editor and
   the player; one wake-phrase setting; consistent cues everywhere.

---

## 14. Open questions

1. **Default wake phrase** — "hey player" (app-specific, distinct) vs "hey quill"
   (one phrase family-wide)? Recommendation: app-specific default, shared option.
2. **v1 without the keyword spotter** — acceptable to ship transcription-based
   always-on (heavier CPU) if clearly disclosed, or hold always-on until P3?
   Recommendation: ship P1 disclosed; it is genuinely useful and honest.
3. **Persistence across launches** — off by default is clear; is an opt-in worth the
   "armed at startup" perceivability burden (must announce loudly on launch)?
4. **One mic, many apps** — if several QuillVille apps offer always-on, do they
   coordinate the microphone, or is it last-armed-wins with a clear announcement?

---

## 15. What this reuses vs adds (summary)

**Reused, unchanged:** `WakeController` (policy), `extract_transcript_body` (phrase
match), the command grammar + dispatch, `build_media_voice_services`
(Whisper/Nemotron/Vosk resolution), VAD, the `CONVERSATION_*` earcons, `duck()`/
`unduck()`, `_announce(force, sound)`, the safe-command allowlist.

**Added:** a continuous rolling-window capture loop; its accessibility skin
(open/close/periodic cues, reviewable status, check state, announcement gating);
the consent gate and settings; and — as the real destination — a low-power keyword
spotter to make "always" affordable.

The logic is mostly already written and tested. What remains is the capture loop
and, above all, making a mic that never sleeps something a blind user can always
hear, review, and trust — which is the whole point of doing it right.
