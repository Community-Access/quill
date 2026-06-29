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

## 10. Detailed, code-grounded phase analysis

This section walks each phase against the actual code, describing what is *safe*
to do (guarded, reversible, no new failure modes), the expected impact across
**size / memory / footprint / speed / capability**, and the **Windows/macOS**
differences. "Safe" assumes: downloads are SHA-256-verified (existing pattern),
work stays off the UI thread, every change is opt-in or behaviour-preserving, and
Safe Mode still disables network/AI. Network-dependent steps assume stable
internet *for the download only* — once a model/asset is local, the feature is
fully offline.

### 10.0 Current baseline (what we are optimizing from)

- **Installer ≈ 245 MB** (measured from a local 0.8.1 build). It is dominated by
  the embedded CPython 3.13 runtime + wheels (notably wxPython) under
  `Lib/site-packages`, plus `python313.dll`/`.zip` and the bundled whisper.cpp
  engine (#747, ~8 MB CPU build).
- **Speech model downloads** (on first use, not in the installer) —
  whisper.cpp / Faster Whisper: tiny 75 MB, base 145 MB, small 465 MB, medium
  1500 MB, large-v3 3100 MB. Faster Whisper's on-disk int8 is smaller than the
  GGML figure for the same tier.
- **On-device LLM (GGUF, Q4_K_M)** via `quill/core/ai/model_manager.py`:
  `llama-3.2-1b` ≈ 0.8 GB (default under 8 GB RAM), `phi-4-mini` ≈ 2.5 GB (8 GB+).
  Auto-downloaded to `<app data>/models`, SHA-256-verified, urllib-only.
- **Already quantized + lazy + machine-aware**, so the wins below are about
  *fit, footprint, and routing*, not new quantization.

### 10.1 Phase 0 — Measurement (no behaviour change; foundation)

**What is possible, safely.** A read-only `scripts/footprint_report.py` that emits:
installed size by component (walk `{app}` and the optional-component dirs), each
on-disk model size (`<app data>/models`, `speech-engine`, `kokoro-models`), and
peak RSS per engine for a fixed sample (drive each provider's `transcribe_file` /
read-aloud / a short LLM completion under a sampler). Reuse the existing machine
probes (`service.detect_total_ram_gb`, `detect_has_gpu`, `models_dir_free_gb`).
Pure measurement — no risk.

**Impact:** none to the product; unlocks every later decision with numbers.
**Cross-platform:** identical logic; sizes differ (macOS bundle is a `.app`, no
embedded `python313.dll`; it has a Python.framework). The report should label the
platform and not assume Windows paths.

### 10.2 Phase 1 — Packaging / disk footprint

**What exists.** `scripts/build_windows_distribution.py` already: bundles the
embedded runtime, **prunes build-only packages**, makes large engines optional
installer components (Kokoro ~120 MB, DECtalk, Piper, eSpeak, Node.js ~30 MB,
braille pack ~15 MB, pandoc), and **downloads engines at build time** (#747
whisper, etc.). macOS uses py2app (`scripts/setup_macos.py` / `build_macos.sh`),
which zips pure-Python into `pythonNNN.zip` and now bundles missing `@rpath`
dylibs (#755).

**Safe, high-value moves:**
- **Trim the embedded stdlib/wheels.** Exclude provably-unused stdlib (e.g.
  `tkinter`, `test`, `idlelib`, `ensurepip`, `distutils` leftovers) and large
  unused wheel data. *Guard:* gate behind the existing import-surface tests + a
  smoke launch (`python -m quill --version`) so a wrongly-pruned module fails the
  build, never the user. **Impact:** tens of MB off the installer; faster
  download/extract; zero runtime change. **Reversible:** it is a build-time
  exclude list.
- **More assets on-demand.** Anything rarely used (extra Kokoro voices, large
  speech tiers) moves from "bundled" to "downloaded on first use" via the existing
  SHA-verified download path. **Impact:** smaller base installer; first-use cost
  shifts to a one-time, resumable download. *Guard:* the feature already degrades
  to "download needed" messaging; Safe Mode blocks it.
- **DLL de-dup / compression.** Detect duplicate native DLLs across engine dirs;
  rely on the installer's compression. **Impact:** moderate size; no behaviour
  change.

**Cross-platform.** Windows: the embedded-runtime trim is the biggest lever.
macOS: the py2app bundle has different internals (framework Python, `.dylib`
signing); the trim list must be computed per-platform, and the macOS `.app` must
stay notarization-valid (every Mach-O signed — already handled in `build_macos.sh`).
Note today's whisper.cpp bundling is **Windows-specific**; a macOS build would need
a mac `whisper-cli` (a tracked gap, see 10.5).

**Impact summary:** size ↓↓ (installer), download time ↓; memory/speed unchanged;
capability unchanged (on-demand keeps every feature, just not pre-bundled).

### 10.3 Phase 2 — Runtime memory & model lifecycle

**What exists.** Heavy ML imports are lazy (`FasterWhisperProvider.is_available`
probes via `importlib.util.find_spec`, never importing CTranslate2 on the UI
thread). Providers expose `warm()` / `unload()`; the dictation provider is cached
(`_dictation_provider`) and prewarmed in the background; Kokoro has
`prewarm_kokoro_model` / `warm_kokoro_onnx`. So the machinery to load/unload
exists — there is no *policy* tying it together.

**Safe, high-value moves:**
- **Idle-unload policy.** A background, timer-based sweep that calls the existing
  `unload()` on a model untouched for N minutes (and on memory-pressure). *Guard:*
  unload is already a no-op-safe operation; a subsequent use simply reloads (warm
  cost). Off-thread via `QuillTaskManager`; UI via `wx.CallAfter`. **Impact:**
  peak RSS ↓↓ when the user moves between features; first-use-after-idle speed ↓
  slightly (one reload) — acceptable and configurable.
- **Single-flight loading.** Ensure only one load of a given model is in flight
  (a lock keyed by model id) so rapid triggers can't double-load. **Impact:**
  memory spike ↓, no duplicate work. Pure safety.
- **Low-resource mode (opt-in or auto on low RAM).** Caps *concurrently loaded*
  engines to one and biases selection to the smallest model. **Crucially it never
  disables AI or speech** — it serializes them. *Guard:* a setting (default off;
  may auto-enable below a RAM threshold with a one-time, accessible notice).
  **Impact:** the full feature set fits on small machines; throughput ↓ when many
  features are used at once (one-at-a-time), which is the right trade for a
  capability floor.

**Cross-platform.** Memory probing already abstracts via `bw_speech`
(`total_ram_gb`). `psutil`-style RSS sampling for the report must tolerate absence;
unload semantics are pure-Python and identical on both OSes. CUDA paths only ever
*add* a faster option when present.

**Impact summary:** memory ↓↓ (the headline runtime win); speed ↓ slightly only
on reload-after-idle; capability unchanged (never disables features); footprint
unchanged.

### 10.4 Phase 3 — Model / quant selection (extend the recommender)

**What exists.** `quill/core/speech/service.py` already does machine-aware
selection: `recommend_model_id` uses conservative RAM tiers (≤3 GB → tiny; <6 →
base; <12 → small; <16 → medium; ≥16 → medium, or large-v3 with a GPU),
`required_ram_gb` maps size→RAM (≤200 MB→2 GB, ≤600→4 GB, ≤1800→6 GB, else 8 GB),
`enough_disk_for` guards disk, and `describe_models` surfaces fit + a GPU note.
The LLM side mirrors this (`model_manager` RAM tiering at an 8 GB threshold).

**Safe, high-value moves:**
- **Smallest-viable default + accessible upgrade prompt.** New installs default to
  the recommended (smallest-that-fits) model; offer "your machine can handle a
  more accurate model" as a one-step, screen-reader-friendly prompt — never an
  automatic large download. **Impact:** download size ↓ and time-to-first-use ↓↓
  for most users; accuracy is a deliberate upgrade. *Guard:* recommendation is
  already conservative and selectable.
- **Expose quant variants where they help.** Offer q5/q8 whisper.cpp or CTranslate2
  `int8_float16` as alternatives within a tier, picked by the recommender.
  **Impact:** lets a machine trade a little size/RAM for accuracy without jumping a
  whole tier. *Guard:* additive catalog entries; defaults unchanged.
- **Unify the speech + LLM recommenders** behind one machine profile so guidance is
  consistent. Pure refactor; behaviour preserved.

**Cross-platform.** RAM/disk/GPU probes already cross-platform; CUDA nudge only
applies where a GPU exists, so macOS/CPU users always get the CPU-appropriate
default. No OS-specific behaviour.

**Impact summary:** size ↓ (smaller defaults), speed ↑ (right-sized models load
and run faster), capability ↑ (clear upgrade path), memory ↓ (defaults fit).

### 10.5 Phase 4 — AI routing (cloud-first / minimal-local)

**What exists.** `quill/core/ai/` already supports cloud providers (OpenAI,
Anthropic, Gemini, OpenRouter) and on-device (Ollama probed in `onboarding`,
llama.cpp via `llama_cpp_backend` + the GGUF `model_manager`), with a fast/quality
tier split (`model_tiers.py`) and consent-gated, provider-neutral routing.

**Safe, high-value moves:**
- **First-class "cloud-first / no local weight" path.** A setup choice that uses a
  cloud provider for AI and downloads **zero** local LLM weight — ideal for very
  low-storage machines. **Impact:** footprint ↓↓ (no multi-GB GGUF), quality ↑
  (frontier models), at the cost of requiring connectivity + consent for AI only.
  *Guard:* the consent gates and "nothing sent without consent" model are
  unchanged; speech stays fully on-device.
- **Low-resource on-device default.** Where on-device is chosen, default to the
  smallest capable GGUF (`llama-3.2-1b`, ~0.8 GB) on <8 GB machines (already the
  threshold) and only suggest `phi-4-mini` upward. **Impact:** on-device AI runs on
  modest hardware; bigger models are an opt-in upgrade.
- **Graceful fallback chain.** When a cloud call fails (offline/timeout) and a
  local model exists, offer to fall back (and vice versa), surfaced accessibly.
  *Guard:* never silently switch providers in a way that changes the privacy
  posture; always announce.

**Cross-platform.** Cloud routing is OS-agnostic. On-device llama.cpp + GGUF work
on both; macOS could additionally use Metal acceleration via the runtime when
present (bonus, never required). **Tracked gap:** the offline *speech* engine
binary (whisper.cpp) is bundled for Windows only today; macOS parity (a mac
`whisper-cli`, or defaulting macOS offline speech to Faster Whisper / a mac build)
should be called out so "speech wherever possible" holds on Mac too.

**Impact summary:** footprint ↓↓ (cloud-first), capability ↑ (frontier or
right-sized local), reliability ↑ (fallback chain), with privacy posture preserved.

### 10.6 Sequencing, reliability, and "make it magic" notes

- **Order matters:** Phase 0 first (numbers), then 1 (cheap, safe size wins), then
  2 (the memory headline), then 3/4 (capability + routing). Each phase is
  independently shippable and reversible.
- **Reliability:** every download stays SHA-256-verified and resumable-by-retry;
  every new mode is a setting with a safe default; Safe Mode continues to disable
  network/AI; all model work stays off the UI thread. No phase introduces a new
  hard dependency or a GPU requirement.
- **The "magic":** the compounding effect is *a screen-reader-first writing studio
  whose full AI + speech feature set installs small, starts fast, and runs on a
  cheap CPU-only laptop* — downloading only what a given machine can use, holding
  only one model in memory at a time when RAM is tight, and transparently using a
  GPU or a cloud provider as a bonus when they exist. Capability scales *up* with
  the hardware and never falls *off* on the low end.

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

## Appendix B — size / RAM reference (current values)

Offline speech models (download size; on-disk int8 for Faster Whisper is smaller),
and the RAM tier `service.required_ram_gb` maps each to:

| Model | Download | Accuracy | Speed | Est. RAM tier |
| --- | --- | --- | --- | --- |
| tiny | 75 MB | low | fast | ~2 GB |
| base | 145 MB | low | fast | ~2 GB |
| small | 465 MB | medium | medium/fast | ~4 GB |
| medium | 1500 MB | high | slow | ~6 GB |
| large-v3 | 3100 MB | highest | slow | ~8 GB |

Speech recommender (`service.recommend_model_id`) by total RAM: <3 GB → tiny;
<6 → base; <12 → small; <16 → medium; ≥16 → medium (or large-v3 with a GPU).

On-device LLM (GGUF Q4_K_M, `ai/model_manager.py`; auto-downloaded + SHA-256):

| Model | Size | Default for |
| --- | --- | --- |
| Llama 3.2 1B Instruct | ~0.8 GB | machines under 8 GB RAM |
| Phi-4-mini Instruct | ~2.5 GB | machines with 8 GB+ RAM |

Installer (Windows, 0.8.1 local build): ≈ 245 MB, dominated by the embedded
CPython 3.13 runtime + wheels. Optional/bundled components include Kokoro voices
(~120 MB), Node.js (~30 MB), the braille pack (~15 MB), and the whisper.cpp CPU
engine (~8 MB, Windows build).

All figures are current observations to be re-baselined by the Phase 0 report.
