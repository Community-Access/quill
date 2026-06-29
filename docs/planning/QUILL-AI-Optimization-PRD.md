# QUILL AI Footprint & Optimization — PRD (Draft)

- Status: Draft / Proposed (not yet scheduled)
- Owner: TBD
- Created: 2026-06-29
- Related: `docs/planning/roadmap.md`, `docs/Product Requirement Documents and Specifications/QUILL-PRD.md`

> This is an initial draft to frame the work. It is deliberately measurement-first:
> nothing here should be built before Phase 0 produces real numbers, because QUILL
> already does most of the high-value quantization and lazy loading, and the
> remaining wins are in packaging, runtime memory, and routing rather than in
> re-quantizing models.

## 1. Summary

Make QUILL **as capable as possible on whatever hardware the user has**, while
reducing its on-disk and in-memory footprint and improving AI/ML efficiency —
**without** regressing accessibility, output quality, privacy, or the zero-config
"it just works" experience. Optimization here means *fitting more capability onto
modest, CPU-only machines*, not trimming features. The headline levers are
installer/disk size, peak runtime RAM per engine, smallest-viable model selection,
and cloud-vs-on-device routing — not new model quantization, which is already
pervasive.

## 1.1 Design principles (must hold)

These are firm constraints on every phase below:

- **Capable on any hardware.** QUILL should run its full feature set on a modest,
  CPU-only Windows machine with limited RAM. Optimization exists to *extend*
  capability downward to low-end hardware, never to disable features on it.
- **AI and speech available wherever feasible.** Prefer enabling AI and speech —
  on-device when it fits, cloud when the user opts in — over gating them behind
  hardware. A weaker machine should get a smaller/slower model, not "no feature."
- **No GPU requirement, ever.** The default, fully-supported path is **CPU-only**.
  Our user community most likely has no discrete GPU; nothing may require one or
  degrade the experience when one is absent.
- **GPU is a welcome bonus when present.** If a usable GPU is detected, engines may
  auto-accelerate (e.g. Faster Whisper's CUDA float16 path) — automatically and
  optionally, never as a precondition and never something the user must configure.

## 2. Background — what QUILL already does

QUILL is already heavily optimized on the model side. Any plan must build on this,
not duplicate it:

- **Quantized models throughout.** Faster Whisper runs CTranslate2 **int8 on CPU**
  / float16 on CUDA (`quill/core/speech/providers/fasterwhisper.py`); Kokoro TTS
  ships the **int8 ONNX** model (`kokoro-v1.0.int8.onnx`); whisper.cpp uses
  **GGML-quantized** models; local LLMs run through Ollama / `llama_cpp_backend`
  as **GGUF (Q4/Q5)**, where the runtime owns quantization.
- **Lazy, optional loading.** Heavy ML imports are deferred (`faster_whisper` /
  `ctranslate2` are probed via `importlib.util.find_spec`, imported only on use),
  so an uninstalled engine never costs startup time or idle memory.
- **Warm/unload lifecycle.** Dictation and Kokoro models have prewarm + cached
  providers + `unload()` paths.
- **Optional install components + on-demand downloads.** The installer makes large
  engines optional (Kokoro ~120 MB, DECtalk, Piper, eSpeak, Faster Whisper) and
  downloads several on demand; the build prunes build-only packages.
- **Machine-aware recommendations.** The speech model manager already sizes model
  suggestions to the user's RAM / GPU / disk.

So "should we quantize?" is largely answered **yes, already**. The open question is
everything *around* the models.

## 3. Goals

1. **Keep the full feature set usable on CPU-only, modest-RAM machines** — the
   primary target. AI and speech work without a GPU; a weaker machine gets a
   smaller/slower model, not a disabled feature.
2. Make the installed/disk footprint smaller and more predictable, with large or
   rarely-used assets opt-in.
3. Lower peak runtime RAM, especially with multiple engines (speech + TTS + AI)
   in play, via an explicit unload policy and an optional low-resource mode that
   trades speed for fit — without turning features off.
4. Default users onto the smallest viable model/quant for their machine, with a
   clear, accessible upgrade path.
5. Give a first-class "cloud-first / minimal local" path for users who don't want
   on-device model weight at all.
6. Auto-use a GPU when one is present (bonus acceleration), with the CPU path as
   the always-supported default and no required configuration.
7. Do all of the above with **zero** regression to accessibility, output quality,
   privacy posture, or first-run simplicity.

## 4. Non-goals

- Re-quantizing or retraining models QUILL ships (already quantized upstream).
- Changing the privacy model (AI stays opt-in, provider-neutral, consent-gated).
- Custom GPU kernels or vendor-specific accelerator tuning. The engines' built-in
  auto-acceleration (e.g. CUDA) is used as-is **when a GPU is present**; the CPU
  path is the default and is never gated on a GPU. Requiring a GPU for any feature
  is explicitly out of scope.
- Disabling or hiding AI/speech features on low-end hardware. Modest machines get
  smaller/slower models, not fewer features.
- Dropping macOS support or Windows-primary status.

## 5. Success metrics (to be baselined in Phase 0)

- Installer size (MB) and installed-on-disk size, base vs. full component set.
- Peak RSS per engine (whisper.cpp, Faster Whisper, Vosk, Kokoro, local LLM) for a
  representative task, and with N engines concurrently loaded.
- Cold-start time to first usable editor; time-to-first-token / first-audio per
  engine.
- Default-model size shipped/recommended per machine tier.
- **Capability floor:** the full AI + speech feature set runs on a defined low-end,
  **CPU-only** reference machine (no GPU, modest RAM) with acceptable latency — this
  is the primary bar.
- GPU present: features auto-accelerate with no user configuration, and behave
  identically (only faster) to the CPU path.
- No regression: transcription WER, TTS intelligibility, and AI task quality stay
  within agreed tolerances; accessibility checks unchanged.

## 6. Phased plan

### Phase 0 — Measure (prerequisite)
Build a repeatable footprint/inventory report: installed size by component,
per-model on-disk sizes, and peak RAM per engine / per concurrent combination.
Land it as a script + a short doc so every later phase is judged against numbers.
**Acceptance:** a committed report for the current release on a reference machine.

### Phase 1 — Packaging / disk footprint
Audit the installer (currently ~245 MB, dominated by the embedded runtime +
wheels). Trim the embedded stdlib/wheels, dedupe DLLs, and push more assets to
on-demand. **Acceptance:** measurable base-installer reduction with no feature loss
(on-demand paths verified).

### Phase 2 — Runtime memory
Add an explicit **unload-idle-models** policy, single-flight model loading, and a
**Low-resource mode** setting that caps *concurrently loaded* engines and prefers
the smallest models — trading speed/concurrency for fit, never turning AI or speech
off. **Acceptance:** peak RSS with multiple engines drops measurably; every AI and
speech feature still runs (just one-model-at-a-time / smaller) on a CPU-only,
modest-RAM machine; no UI stalls (work stays off the UI thread).

### Phase 3 — Model / quant selection
Default to the smallest viable quant, extend the existing machine-aware recommender
with accessible upgrade prompts, and offer quant variants where useful (e.g.
q4/q8 whisper.cpp, CTranslate2 int8_float16). **Acceptance:** new installs default to
a machine-appropriate model; upgrades are one accessible step.

### Phase 4 — AI routing
A **cloud-first / minimal-local** option (zero local model weight) and low-resource
on-device defaults (small GGUF). **Acceptance:** a user can run the AI suite with no
local model downloaded; on-device defaults fit modest machines.

## 7. Risks & constraints

- **Accessibility first.** Any new setting/mode must be fully keyboard- and
  screen-reader-accessible and announced; no visual-only cues.
- **No quality regression.** Smaller defaults must stay usable; upgrades must be
  obvious.
- **Privacy.** Cloud-first routing must keep the existing consent gates; nothing
  leaves the machine without consent.
- **Thread safety.** Model load/unload and measurement must stay off the UI thread
  (`QuillTaskManager` / `wx.CallAfter`).
- **Platform.** Windows-primary, macOS-supported; Linux is not a target.

## 8. Open questions

- What machine tiers do we target for "smallest viable default"?
- Unload policy: idle-timeout, memory-pressure trigger, or both?
- Does "Low-resource mode" also gate non-AI features (e.g. previews), or AI/speech
  only?
- Cloud-first: a distinct setup-wizard path, or a toggle on the existing one?

## 9. Out of scope (for now)

Upstream model training/quantization; non-Windows/macOS platforms; accelerator
vendor-specific kernels.

## Appendix A — concrete code touchpoints (for scoping)

- Speech engines: `quill/core/speech/providers/` (whispercpp, fasterwhisper, vosk),
  `quill/core/speech/service.py`, model manager UI in `quill/ui/main_frame_speech.py`.
- TTS: `quill/core/read_aloud.py`, Kokoro model resolution / warm.
- Local LLM / AI: `quill/core/ai/model_manager.py`, `quill/core/ai/llama_cpp_backend.py`,
  provider routing in `quill/core/ai/`.
- Packaging: `scripts/build_windows_distribution.py` (optional components, runtime
  bundling, prune step), `installer/quill.iss`, `scripts/setup_macos.py` /
  `scripts/build_macos.sh`.
- Settings surface for new modes: `quill/core/settings.py` + `settings_specs.py`.
