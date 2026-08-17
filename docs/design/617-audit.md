# Offline Speech / Dictation Stack Audit (#617, #663, #669)

_Audit date: 2026-08-04. Read-only assessment of the offline speech/dictation
stack, with follow-up work driven from the recommendations. Items marked
**[done 2026-08-04]** were addressed in the same change set that added this file._

## Summary

The offline speech stack for #617 is **substantially built and genuinely wired
end-to-end** — a mature feature, not scaffolding. The default whisper.cpp
provider plus three optional engines (Faster Whisper, Vosk, Nemotron/sherpa-onnx)
all implement `transcribe_file` and are registered lazily; the small Whisper
models (tiny/base/small/medium) have working, SHA-pinned download paths via
QUILL's own `assets-v1` mirror. There are three coexisting dictation systems:
the full state-machine "Locked Dictation" (Ctrl+F9), a simpler "Dictate
(Offline)" push-to-talk toggle, and a legacy Win+H OS-panel shim that is still
live. VAD auto-endpointing and the "Hey QUILL" wake word are both wired, but only
into Conversation Mode / always-listening — not into dictation. The main gaps are
dead scaffold, stale catalog data, and a near-total end-user documentation gap.

## Fully wired & working (usable today)

- **Locked Dictation (Ctrl+F9)** — the real #617 feature. The wx-free state
  machine (`quill/core/speech/dictation/` controller/session/states/insertion/
  recovery) is driven by `DictationHotkeysMixin`
  (`quill/ui/main_frame_dictation_hotkeys.py`), fully mixed into `MainFrame`,
  registered at startup, key-routed through the editor, and menu-bound. Captures
  via `MicRecorder`, secures audio to a recovery repository before transcribing,
  runs Whisper on a worker thread, inserts as one atomic/undoable edit, and
  provides pause/resume, focus-loss stop, a max-duration watchdog, first-use
  onboarding, and crash-recovery review. Default keys in `keymap.py:188-192`.
- **Dictate (Offline) push-to-talk** — `VoiceInteractionMixin.dictate_offline_toggle`;
  simpler (no state machine/recovery) but fully functional.
- **Providers**, all implementing `transcribe_file`, registered in
  `service.default_registry()`: WhisperCpp (always), FasterWhisper, Vosk,
  Nemotron (each if importable), plus Quillin cloud adapters (network, skipped by
  the offline paths).
- **Small Whisper model download + transcribe** — `catalog.WHISPER_CPP_MODELS`
  (tiny/base/small/medium/large-v3/small.en-tdrz) carry pinned sha256; downloads
  go through the `assets-v1` mirror (`model_mirrors.py`). Tiny/Base/Small have
  complete, working paths.
- **Voice commands (#663), Conversation Mode, and "Hey QUILL" wake word** — all
  wired and menu-bound; off by default, Safe-Mode-gated, dispatch limited to
  `SAFE_TOOL_IDS`.
- **VAD auto-endpointing** — live in Conversation Mode (`SilenceDetector` fed
  polled mic energy).
- **Always-listening / hotword** — `WakeController`; a transcription-based wake
  word (rolling windows + Whisper + string-match), off by default.

## Built but unwired (scaffold)

- **`RecordingTranscriptionRequest`** (`provider.py:104`) is defined but never
  imported or consumed anywhere. Every live path uses `TranscriptionRequest` with
  a WAV path. Dead.
- **Removed Hold-to-Dictate leaves dead branches** — `_on_dictation_tick` still
  handles `HOLD_RECORDING` and looks up `tools.dictation_hold`, a binding that
  does not exist. Unreachable.
- **Stale HF catalog data** — `WHISPER_CPP_MODELS` still carry `download_url` /
  `hf_filename` / `revision`, but `_download_to_file` uses only `model_mirrors`;
  the HF fields and the "left to fill in" module docstring are stale.
- **Legacy `dictation_*` settings** (`settings.py:215-218`) are consumed only by
  the legacy Win+H path; the real dictation uses `speech_default_model_id`.

## Bugs / inconsistencies

1. **Three overlapping dictation systems** — legacy Win+H
   (`core/dictation.py`, still instantiated and key-routed), "Dictate (Offline)",
   and "Locked Dictation". A real source of user/maintainer confusion; the legacy
   shim's "QUILL does not yet capture or transcribe audio" premise is now false.
   **[done 2026-08-04]** the false premise in `core/dictation.py` is corrected.
2. **Wake word can clip inline commands** — fixed 2.5s/4s windows, no VAD.
3. **Misleading VAD sample-rate expression** — `_conv_start_capture` passed
   `sample_rate=SAMPLE_RATE * CHANNELS` (correct only because mono).
   **[done 2026-08-04]** corrected to `SAMPLE_RATE`.
4. **large-v3 has no working auto-download** (by design, >2 GiB) yet the
   recommender can return it — worth surfacing as "manual install only".
5. **Wake word runs full Whisper on rolling windows** — a battery/perf concern the
   code does not bound.

## Test coverage

Broad and healthy across `tests/unit/core/speech/` and the dictation package.
Notable untested seams: `dictation/session.py` serialization (only exercised
indirectly through `test_recovery.py`) and `ui/voice_services.py`.

## Documentation gaps

- **No #617 PRD in the repo**; the committed `QUILL-PRD.md` has zero mentions of
  dictation/Whisper though the code cites PRD sections.
- **The flagship feature is undocumented for end users** — `userguide.md` has no
  mention of dictation / Dictate / Whisper.
- `docs/user guide/voice-interaction.md` is good but scoped to "Hey QUILL".

## Concrete recommendations (ranked)

1. **Write the missing user documentation** for offline dictation (highest user
   impact). _In progress alongside this audit._
2. **Delete the dead `RecordingTranscriptionRequest`** or add a tracking note.
3. **Remove the dead Hold-to-Dictate branches** (or restore the binding).
4. **Resolve the three-dictation-systems overlap** — decide what stays; update the
   false premise in `core/dictation.py`. **[done 2026-08-04]** (premise fixed;
   consolidation still open.)
5. **Clean up stale catalog data** — drop unused HF fields or make the fallback
   real; fix the `catalog.py` docstring.
6. **Apply VAD to the wake-word command window**; fix the `SAMPLE_RATE * CHANNELS`
   expression. **[done 2026-08-04]** (sample-rate fixed; wake-word VAD still open.)
7. **Add unit tests** for `dictation/session.py` serialization and
   `ui/voice_services.py`.
8. **Surface the large-v3 limitation** in the model picker/recommender.

## Follow-up landed with this audit (2026-08-04)

Beyond the fixes tagged above, the same change set delivered the two features the
audit's #1 recommendation and the surrounding work called for:

- **Hands-free voice in the Media Player** — the player's command bar now listens
  (offline, small Whisper) and executes media commands. New modules:
  `quill/ui/media/voice_capture.py`, `quill/ui/media/listen_mixin.py`;
  `service.preferred_command_model` prefers the small Whisper tiers.
- **User dictation profile** (`dictation.md`, adapted from VS Code) —
  `quill/core/speech/dictation_profile.py`: vocabulary biases Whisper via
  `initial_prompt` (whisper.cpp gained `--prompt`), plus spoken→written
  replacements and custom command aliases. Wired into Locked Dictation and
  `voice_services`.

Still open from the recommendations: dead-scaffold removal (#2, #3), catalog
cleanup (#5), wake-word VAD (#6 part 2), the two coverage seams (#7), the large-v3
surfacing (#8), and the three-systems consolidation (#4).

## Follow-up landed 2026-08-17: the dictation reliability pass

Studied against the Handy project (`D:\code\handy`, MIT — an offline dictation
app whose production failure catalogue maps almost one-to-one onto ours) and
landed as one change set. Full rationale in the PRD (§5.25 dictation addendum);
architecture notes here:

- **Parakeet 3** (`providers/parakeet_onnx.py`): NVIDIA `parakeet-tdt-0.6b-v3`
  int8 on sherpa-onnx's `OfflineRecognizer` (`model_type="nemo_transducer"`) —
  the *batch* sibling of the Nemotron streaming provider, which is exactly the
  shape the dictation flow wants today (capture a WAV, transcribe the file). It
  reuses `nemotron_onnx.resolve_model_files` (same bundle layout) and the same
  assets-v1 mirror discipline. **Dictation preference ladder** in
  `service.preferred_dictation_provider_id`: explicit choice > installed
  Parakeet > whisper.cpp default. The transducer's silence-safety (no token
  without audio evidence) is the reliability argument; CPU-only sidesteps
  whisper.cpp's GPU crash class.
- **Silence pre-pass** (`speech_vad.py`): RMS tier always (reuses the
  `vad.py` turn-taking calibration), Silero tier when the Parakeet bundle's
  `silero_vad.onnx` is installed; neural may only narrow the RMS span. Wired in
  the dictation transcribe worker; all-silent takes skip the engine and route
  to NO_SPEECH. This retires the whisper silence-hallucination class for batch
  dictation and partially addresses audit recommendation #6.
- **Transcript refinement** (`dictation/refine.py` composing
  `speech/vocabulary.py` + `speech/fillers.py`): vocabulary first (so a filler
  pass can never eat half of a user's term), fillers second, both pure. The
  vocabulary source is the existing `dictation.md` profile — one authoring
  surface feeding both the Whisper `initial_prompt` bias and the fuzzy
  corrector, rather than a second competing word list.
- **Streaming contract** (`speech/streaming.py`): committed/tentative snapshot
  + `StreamAnnouncer` (announce-once). This is the contract the S2–S3 streaming
  work must emit; it exists now so that work is built into it.
- **Capability metadata** (`SpeechModelInfo.capabilities`, spoken by
  `describe_models`): the catalog states what a model can do before download —
  addressing the honesty half of recommendation #8's "surface limitations in
  the picker".
