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
Build a repeatable, read-only footprint/inventory report: installed size by
component, per-model on-disk sizes, peak RAM per engine and per concurrent
combination, and cold-start / first-token timings. Land it as a script + a short
doc (machine-readable JSON + summary) so every later phase is judged against
numbers. **Acceptance:** a committed baseline report for the current release on a
defined reference machine — ideally including a low-end, CPU-only machine (the
capability-floor target). See 10.1 for the completed analysis.

### Phase 1 — Packaging / disk footprint
Audit the installer (currently ~245 MB, dominated by the embedded runtime +
wheels). Trim the embedded stdlib/wheels, dedupe native binaries, and push
*eligible* assets to on-demand. Unbundling is **gated** by the scope rule (10.2.2:
never unbundle launch-critical/offline-first assets) and the reliable-acquisition
model (10.2.3: pinned source + SHA-256, GATE-9 audit + consent, atomic install,
**retry/resumable download**, a mirror/fallback URL, graceful offline UX, and an
acquisition healthcheck). Hardening acquisition is part of Phase 1, not a
follow-up. **Acceptance:** measurable base-installer reduction with no feature
loss; every on-demand asset has a verified, retry/resumable, audited download with
a fallback source and an accessible offline-failure path. See 10.1–10.2 for the
completed analysis.

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
- Asset hosting (10.2.4): use the `quill` repo's releases, or a dedicated
  `quill-assets` repo / pinned `assets-vN` tag? (Leaning: a dedicated tag so asset
  churn is decoupled from code releases.)
- ~~Redistribution clearance for re-hosting **DECtalk** and **eSpeak NG** on our
  releases.~~ **Resolved:** DECtalk is BSD and eSpeak NG is GPLv3 (source-offer
  already in `compliance`/third-party notices); both are now re-hosted on `assets-v1`
  and fetched on demand. ffmpeg stays excluded (never re-hosted).
- Download discoverability (10.2.5): an **optional Setup-Wizard step** offering the
  offline voices/engine on first run, a **Help-menu** "Download optional
  components…" entry, or both? (Leaning: both — wizard offer + a permanent Help
  entry — with everything still working uninstalled.)
- Newer-version awareness (10.2.3 item 9): update-check **cadence** (on startup, on
  feature use, or a manual "check for updates to components"?), and how to surface
  the offer without nagging.

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

### 10.1 Phase 0 — Measurement (no behaviour change; foundation) — ANALYSIS COMPLETE

Phase 0 is pure, read-only measurement. It ships nothing user-facing and changes
no behaviour; its entire value is producing the numbers every later phase is
judged against. Treat its output as the project's optimization baseline.

**What to measure (deliverables of a `scripts/footprint_report.py`):**

1. **Installed/disk size, by component.** Walk `{app}` (Windows) or `Quill.app`
   (macOS) and the optional-component locations, and attribute bytes to: the
   embedded runtime (`python313.dll`/`.zip`, `Lib/`, `Scripts/`), each wheel under
   `Lib/site-packages` (top offenders: wxPython, Pillow, winrt, kokoro/onnx,
   vosk), and each bundled engine/asset dir (`tools/speech/*`, `kokoro-models`,
   `vendor/braille-pack`, `tools/nodejs`, `tools/pandoc`). Output a sorted
   "biggest first" table.
2. **On-disk model/asset sizes** under the data dir: `<app data>/models` (GGUF +
   speech models), `speech-engine`, `kokoro-models`, `tools/ffmpeg`.
3. **Peak RSS per engine**, sampled off the UI thread, for a fixed micro-task:
   whisper.cpp and Faster Whisper transcribing a short clip; a Kokoro/Piper
   read-aloud; a short llama.cpp completion. Also the **N-engines-loaded-at-once**
   peak (the case Phase 2 attacks).
4. **Cold start** to first usable editor, and **time-to-first-token / first-audio**
   per engine.
5. **Machine context** for the run: reuse `service.detect_total_ram_gb`,
   `detect_has_gpu`, `models_dir_free_gb` so the report is interpretable per tier.

**Method/guards.** Read-only filesystem walks + an off-thread RSS sampler
(`QuillTaskManager`); tolerate a missing `psutil` (degrade to "RSS unavailable",
never crash). No network. Emit machine-readable JSON + a short Markdown summary so
results are diffable release-over-release.

**Acceptance.** A committed baseline report for the current release on a defined
reference machine (and ideally a low-end CPU-only one — the capability-floor
target). The report is the gate input for Phases 1–4.

**Impact.** Product: none (no behaviour change, no size change). Process:
foundational — converts "we think this is big/heavy" into ranked, attributable
numbers, so Phase 1 trims the *actually* large things and later phases prove their
wins. **Cross-platform:** identical logic; sizes differ (macOS `.app` has a
`Python.framework`, not `python313.dll`). The report labels the platform and uses
platform-correct roots — no Windows path assumptions.

### 10.2 Phase 1 — Packaging / disk footprint — ANALYSIS COMPLETE

**What exists.** `scripts/build_windows_distribution.py` bundles the embedded
runtime, **prunes build-only packages**, makes large engines optional installer
components (Kokoro ~120 MB, DECtalk, Piper, eSpeak, Node.js ~30 MB, braille pack
~15 MB, pandoc), and **downloads engines at build time** (#747 whisper, etc.).
macOS uses py2app (`scripts/setup_macos.py` / `build_macos.sh`), zipping
pure-Python into `pythonNNN.zip` and bundling missing `@rpath` dylibs (#755).
Runtime acquisition already follows a strong pattern (see 10.2.3) that any
unbundling must inherit.

#### 10.2.1 Safe, high-value moves (with quantified impact)

- **Trim unused *wheel* data — the stdlib is already minimal (measured).**
  Phase 0 measurement (Appendix C) shows the embeddable runtime already excludes
  the usual stdlib trim targets (`tkinter`, `test`, `idlelib`, `ensurepip`,
  `lib2to3`, `distutils` are all **absent**; `python313.zip` is only 3.6 MB), so
  the real footprint is the **wheels** under `Lib/site-packages` (≈ 534 MB
  uncompressed). The lever is therefore large *data inside wheels* (e.g. spell-check
  dictionaries, CLDR locale data) and over-broad transitive packages — not stdlib
  modules. *Guard:* an explicit, reviewed exclude list, gated by the existing
  import-surface tests + a smoke launch (`python -m quill --version`, and
  `--dump-stacks` which imports the wx UI) so a wrong exclusion fails the **build**,
  never the user. **Impact:** tens of MB off the installer (Appendix C ranks the
  exact targets); faster download + extract + first launch; **zero**
  runtime/behaviour change. Fully reversible (a build-time list).
- **Move rarely-used assets to on-demand — only those that pass 10.2.2/10.2.3.**
  Candidates: extra Kokoro voices, large/rare speech tiers, optional engines not
  needed at first run. **Impact:** smaller base installer; first-use cost becomes a
  one-time verified download. *Guard:* the feature must degrade to an accessible
  "download needed" affordance, Safe Mode blocks it, and acquisition must meet the
  reliability bar below **before** the asset is removed from the installer.
- **Native-binary de-dup + compression.** Detect duplicate DLLs/dylibs across
  engine dirs; rely on installer compression. **Impact:** moderate size; no
  behaviour change.

**Impact summary:** size ↓↓ (installer + first download), launch ↑ (less to
unpack); memory/speed of features unchanged; capability unchanged — on-demand
keeps every feature, just not pre-bundled, *provided acquisition is reliable*.

#### 10.2.2 Scope rule: what may and may not be unbundled

Unbundling trades disk for a network dependency, so it is gated by how the feature
behaves when the asset is absent. Classify every candidate:

- **Never unbundle (must work offline at first run):** the embedded runtime and
  first-party `quill` package; anything required to launch, edit, save, or read
  the UI; the braille pack if braille is a launch-critical accessibility surface.
  These ship in the installer, always.
- **Keep a minimal default bundled, offer better on-demand:** speech/TTS where an
  offline-first experience matters. Ship the smallest viable engine/voice so the
  feature works with no network; let users download larger/higher-quality variants
  on demand. (whisper.cpp CPU engine staying bundled is the model here.)
- **Safe to unbundle (graceful "download needed"):** large optional voices, large
  model tiers, optional tools (e.g. Node.js, pandoc) whose absence shows a clear,
  accessible "install/download this to use the feature" path and never blocks core
  editing.

A candidate may move to on-demand only if (a) it is not launch-critical, (b) its
absence degrades to an accessible, understandable prompt — never a crash or a
silent no-op — and (c) it satisfies the reliable-acquisition model in 10.2.3.

#### 10.2.3 Reliable acquisition model (the touch points must be dependable)

Anything we stop bundling becomes something we must fetch dependably, possibly
years later when an upstream URL may have moved. The existing patterns
(`build_windows_distribution._download_with_verification`,
`ai/model_manager._download`, `scripts/fetch_bootstrappers.py`) already encode most
of this; unbundling must adopt **all** of it, and close the gaps:

1. **Pinned, versioned source + SHA-256.** Every asset has a pinned URL (or pinned
   release tag/commit) and a recorded SHA-256; the bytes are verified before use,
   and a moving ref (`HEAD`/`latest`/`main`) is refused for the *pinned* path
   (mirrors `fetch_bootstrappers`). Optional "try latest, fall back to pinned"
   is allowed only where the pinned fallback is real.
2. **GATE-9 / no-silent-network.** Each new download call site is added to
   `network_egress_audit.py` with a reviewed entry and a visible, consented
   surface (progress dialog / explicit action). No silent fetches; Safe Mode
   disables all of it.
3. **Atomic + verified install.** Download to a temp path, verify the SHA, then
   atomically place it (temp + replace) so a partial/failed download never leaves a
   half-installed asset that looks present.
4. **Retry + resumability (the gap to close).** Today's helpers stream-and-verify
   but **re-download from scratch on failure** (no HTTP Range/`.part` resume).
   Before unbundling anything large (hundreds of MB+), add bounded retry with
   backoff and resumable download so a dropped connection on a 0.5–3 GB asset does
   not force a full restart. This is a prerequisite, not an afterthought.
5. **Source resilience.** Pin to a stable host; record a **mirror/fallback URL**
   where licensing allows (e.g. a Community-Access-controlled mirror) so a single
   upstream outage or a deleted release does not strand a feature. The verified
   SHA makes any mirror safe to trust.
6. **Graceful offline / failure UX.** On no-network, timeout, 404 (upstream moved),
   checksum mismatch, rate-limit (HF token messaging already exists), or low disk
   (`enough_disk_for` already guards), surface a clear, screen-reader-friendly
   message and leave the app fully usable for everything else. Never crash, never
   silently degrade.
7. **Integrity over time.** A periodic/CI "acquisition healthcheck" that resolves
   every pinned URL and re-checks reachability + checksum, so a dead upstream is
   caught by us, not by a user offline at the worst moment.
8. **Already-present is smart, not silent.** If a component is already installed,
   QUILL does not re-download it; it **offers to replace** (re-fetch) so the user
   stays in control, and declining keeps the existing copy. (Shipped for Kokoro,
   whisper.cpp, DECtalk, eSpeak NG, and on-demand spell-check language packs —
   es_ES and fr_FR as the proof-of-concept, discovered at runtime via
   `ENCHANT_CONFIG_DIR`; see `quill/core/spellcheck.py`.)
9. **Newer-version awareness (planned).** Each asset records its upstream
   **version** (a `version` field already exists on the manifest entry). A
   lightweight update check compares the installed version against the pinned
   manifest and, when a newer verified version exists, **notifies the user and
   offers it** — never auto-replacing a working component. This keeps voices and
   engines current without surprise downloads, and reuses the same verified,
   cancelable, Safe-Mode-gated fetch.

**Scope consequence:** Phase 1 explicitly includes hardening acquisition (items 4,
5, 7 are partly new work) as a *precondition* for any unbundling. We do not remove
an asset from the installer until its download path meets this bar; the size win
and the reliability work ship together, never the win alone.

#### 10.2.4 Recommended host: GitHub Releases on a Community-Access repo (controlled primary)

The strongest way to satisfy "source resilience" (item 5) is to host the
redistributable assets **ourselves** as GitHub Release assets on a Community-Access
repo (the `quill` repo, or a dedicated `quill-assets` repo / a pinned `assets-vN`
release tag). The build already pulls several engines from *upstream* GitHub
releases (`dectalk/dectalk`, `ggml-org/whisper.cpp`, `rhasspy/piper`, `electron/rcedit`);
this change re-points the *runtime* on-demand path at a release **we control**.
Recommended for: **whisper.cpp CLI** (~8 MB), **Kokoro** models (~120 MB),
**DECtalk**, **Piper**, **eSpeak NG**, **non-English Hunspell spell-check
dictionaries** (en_US ships inside pyenchant; other languages download on demand),
and small/medium speech tiers.

**Why it fits the model:**
- *Pinned + verifiable (item 1):* stable `…/releases/download/<tag>/<asset>` URLs,
  pinned by tag, each with a recorded SHA-256. Use the **direct download URL**, not
  the releases **API**, so unauthenticated GitHub API rate limits never apply.
- *Source resilience (item 5):* we own the release, so an upstream deleting or
  moving a binary can't strand us; we re-host once (SHA-verified) and pin to our
  copy. We can still record the upstream URL as a *fallback*, or vice-versa.
- *Resumable (item 4):* GitHub release-asset downloads honour HTTP Range, so the
  resumable/retry work applies cleanly.
- *Healthcheck (item 7):* trivial — CI resolves our own pinned asset URLs + checksums.
- *Cost:* public-repo release assets are free and CDN-backed — appropriate for a
  small nonprofit; no bandwidth billing surprise.

**Hard constraints — must be designed in:**
- **License/redistribution gate (per asset).** We may only re-host what we are
  licensed to redistribute. whisper.cpp (MIT) and Piper are fine; **eSpeak NG is
  GPLv3** (redistribution allowed *with* the source-offer obligation — already in
  `compliance`/third-party notices, same obligation as bundling); **DECtalk** is
  BSD-licensed (the `dectalk/dectalk` release we already consume), so re-hosting is
  permitted. **Status:** whisper.cpp, Kokoro, DECtalk, and eSpeak NG are all now
  re-hosted on our pinned `assets-v1` release and fetched on demand at runtime
  (byte-identical re-publishes of the upstream binaries, matching the build pins).
  **ffmpeg is
  explicitly excluded:** QUILL's deliberate stance (see `quill/core/speech/ffmpeg.py`)
  is to *not* bundle or redistribute ffmpeg — it stays user-installed / official
  source, never on our releases. Every re-hosted asset needs a notices entry.
- **2 GB per-asset limit.** GitHub caps a single release asset at 2 GB. So this is
  ideal for engines + small/medium models, but the **multi-GB** assets — speech
  `large-v3` (~3.1 GB) and the GGUF LLMs (`phi-4-mini` ~2.5 GB) — stay on their
  canonical, already-reliable hosts (Hugging Face), which the code already uses.
  (Splitting a >2 GB asset is possible but not worth the complexity now.)
- **Verify regardless of host.** Even though we control the release, the SHA-256
  check stays — it defends against a replaced/corrupted asset and lets any
  mirror/fallback be trusted.

**Net:** adopt our own GitHub Release as the *pinned primary* for redistributable
sub-2 GB components, keep multi-GB models on Hugging Face, and never re-host
ffmpeg. This converts item 5 from "hope upstream stays up" into "we are the
upstream," which is the single biggest reliability gain for unbundling.

#### 10.2.5 The download experience must be magical and fully accessible

Unbundling is only acceptable if fetching a component is delightful and never
strands a screen-reader user. Requirements for every on-demand download:

- **Focus + progress, never "la-la-land."** Each download runs behind an
  accessible, **cancelable** progress dialog (the existing `AIProgressDialog`)
  with spoken milestones; focus is owned and predictable, and on completion focus
  returns to a sensible place (the feature that needed the component, or the
  voice/model list). The UI never blocks (work is off the UI thread) and the user
  is never left waiting silently — progress is both visible and announced.
- **Discoverable in the right places.** The component download is reachable where
  the user already is: the relevant **feature surface** (e.g. choosing a Kokoro
  voice triggers its download; Tools > Speech for the engine), the **Help menu**
  (a "Download optional components…" / "Get offline voices & engines" entry so it
  is findable on purpose), and — for first-run — an **optional Setup-Wizard step**
  that offers to fetch the offline voices/engine a user is likely to want, while
  making clear everything works without it and nothing downloads without consent.
- **Smart and respectful.** Already-installed components are not re-downloaded;
  QUILL offers to **replace** them, and surfaces a **newer version** when one is
  available (10.2.3 items 8–9). Disk and network are checked first
  (`enough_disk_for`), failures degrade to a clear spoken message, and **Safe
  Mode** disables all of it.
- **One consistent surface across services.** OCR engines, Scribe, speech, and
  voices all download through the same verified path and present the same
  accessible progress/consent UX, so "get a component" feels identical everywhere
  (see the AI Hub Services framework in
  `quill-supported-ocr-tool-ai-hub-services-friendly-prd.md`).

The compounding effect: a first run that is small and fast, an obvious accessible
way to add exactly the offline capability you want, progress you can always hear,
and components that stay current — without ever surprising the user or leaving
them wondering whether anything is happening.

**Cross-platform.** Windows: embedded-runtime trim is the biggest lever; on-demand
assets land under the data dir. macOS: the py2app bundle differs (framework Python,
`.dylib` signing), so the trim list is computed per-platform and the `.app` must
stay notarization-valid (every Mach-O signed — handled in `build_macos.sh`); an
asset downloaded post-install must not need re-signing to run (prefer
data/model files over executables for on-demand on macOS, or sign/quarantine-clear
on fetch). Today's whisper.cpp engine is **Windows-only**; macOS offline-speech
parity (a mac `whisper-cli`, or Faster Whisper as the mac default) is the tracked
gap (see 10.5) and is itself an acquisition touch point to design reliably.

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

## Appendix C — Phase 0 wheel/runtime size inventory (measured)

Read-only measurement of a built portable distribution (Windows, 0.8.1 local
build). **No files were modified; this is analysis only.** Phase 0 proposes *no
removals* — it ranks targets and records the verification each would require before
any later phase acts.

**Embedded runtime — already lean.** `python313.dll` 5.8 MB, `python313.zip`
(zipped stdlib) 3.6 MB, `python3.dll` 0.1 MB. The usual stdlib trim targets
(`tkinter`, `test`, `idlelib`, `ensurepip`, `lib2to3`, `distutils`, `turtledemo`,
`tcl`) are **all absent** — the Windows embeddable distribution already excludes
them. Conclusion: "trim the stdlib" is essentially already done; the footprint
lever is the wheels below.

**`Lib/site-packages` total: 534.6 MB.** Top entries (MB), with role and a
*candidate* flag. "Candidate" never means "remove now" — it means "investigate,
with the named verification, in a later phase."

| MB | Package | Role (to confirm) | Candidate? / verification needed |
| --- | --- | --- | --- |
| 90.9 | enchant | pyenchant spell-check backend + bundled dictionaries | Trim bundled dictionary languages to those actually shipped/used. Core feature — keep engine, audit dictionary data. |
| 66.0 | win32more | broad Win32/WinRT API projection | **Highest-value unknown.** Confirm which import pulls it (likely a transitive dep) and whether a slimmer subset/alternative suffices. No action until origin + usage proven. |
| 54.8 | quill | first-party package (incl. bundled data: voice previews, schemas, quillins) | Audit bundled *data* (e.g. voice-preview MP3s) for on-demand; do not touch code. |
| 52.1 | wx | wxPython — core UI | Keep (required). |
| 51.6 | vosk | optional offline STT engine (libvosk) | "Safe to unbundle" per 10.2.2 → on-demand via 10.2.4, if not a default. Verify it isn't a default engine first. |
| 37.7 | onnxruntime | runs Kokoro ONNX (and OCR paths) | Keep while Kokoro is offered; could become on-demand bundled *with* Kokoro. |
| 29.4 | babel | CLDR locale data | Trim to needed locales — verify i18n usage before any trim (i18n risk). |
| 20.0 + 19.4 | numpy.libs + numpy | transitive (onnxruntime / vosk / kokoro) | Keep (transitive dependency). |
| 17.9 | espeakng_loader | eSpeak NG engine/data (pip) | Optional TTS → on-demand candidate per 10.2.2/10.2.4. |
| 13.9 | PIL (Pillow) | image handling / OCR | Keep (used by image + OCR paths). |
| 10.0 | pip | runtime pip | **Deliberately kept** — enables the optional Faster Whisper pip install (per the build script). Not a candidate. |
| 8.5 | lxml | XML (docx / rdflib) | Keep. |

**Reading of the data (analysis, not a plan):**
- The four biggest single wins to *investigate* are `enchant` (dictionary data),
  `win32more` (origin + necessity unknown — verify first), `babel` (locale data),
  and the optional speech/TTS engines `vosk` + `espeakng_loader` (which fit the
  10.2.2 "safe to unbundle" class if they are not defaults).
- Several large entries (`wx`, `numpy`, `onnxruntime`, `PIL`) are core or
  transitive and are **not** reduction targets.
- Every candidate is gated: confirm role/usage (Phase 0 follow-up), then — only if
  it passes 10.2.2 — move to on-demand via the 10.2.3/10.2.4 acquisition model.

**Caveat:** uncompressed on-disk sizes; the installer compresses, so MB-on-disk
overstates MB-in-installer. The Phase 0 report should also record compressed
contribution per component. macOS sizes will differ and need the same measurement.
