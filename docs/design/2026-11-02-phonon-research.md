# Phonon as an offline voice in QUILL

Research note, 2026-11-02, kept here since 2026-11-03 (it was `phonon.md` at the
repository root). The plan it led to is
`docs/Product Requirement Documents and Specifications/phonon-voices-prd.md`,
and phases 1 and 2 of that plan shipped in PR #1747. The sections up to 5 were
written before anything was installed or run; section 6 has the measurements from this
computer. Every external claim has
a link. "Fact" means a source says it; "Inference" means it is my reading and
should be checked.

## Summary (one screen)

- **Verdict: promising with limits.** Phonon 31m is small (64.5 MB), Apache 2.0,
  ships a Windows x64 build and a Windows x64 Python wheel, needs no phonemizer
  and no eSpeak, and its vendor figures beat Kokoro by a wide margin. The limit
  that matters for a low-end standard: the Windows x64 builds are compiled for
  **x86-64-v3 (AVX2, FMA, F16C)**, so a Celeron or Pentium older than 2020, or an
  AMD chip older than 2015, cannot run the shipped binaries at all. Nobody has
  published an x86 speed figure. Until we measure, it is an extra voice for
  machines that pass a CPU check, not a replacement for Piper.
- **Low computer standard (proposed):** Windows 10 or 11, 64-bit; 4 GB RAM; two
  cores; no GPU; for Phonon also AVX2 (Intel Core 4th generation, 2013, or later;
  AMD 2015 or later; Celeron/Pentium 2020 or later). Windows on ARM: Windows 11
  24H2 or later, running QUILL's x64 build under Prism. This matches the baseline
  QUILL's dictation work already uses: "a 4 GB dual-core Windows 10 computer".
- **Licensing, per model:**

| Model | Licence | Bundle | Mirror | Point upstream only |
|---|---|---|---|---|
| Phonon 31m (English) | Apache 2.0 | Yes | Yes | Not needed |
| phonon-voices (102 voice files) | Apache 2.0 (tag only) | Yes | Yes | Not needed |
| Phonon 40m per language (en, fr, de, es, pt) | CC BY-NC 4.0, gated | Licence allows it; ask Gradium first | Licence allows it; ask Gradium first | Yes, today |
| Phonon 40m multilingual | CC BY-NC 4.0, gated | Licence allows it; ask Gradium first | Licence allows it; ask Gradium first | Yes, today |
| Runtime code (ptts) | MIT OR Apache 2.0 | Yes | Yes | Not needed |

- **Windows status:** release v0.6.0 (2026-10-30) has `ptts-0.6.0-x86_64-pc-windows-msvc.zip`
  (7.42 MB, static CRT) and PyPI wheels for `win_amd64` (6.9 MB) and `win_arm64`
  (6.6 MB). Both x64 builds need AVX2. No Windows speed figures exist anywhere.
- **Next steps:**
  1. Jeff approves the measurement run below (one evening, two machines).
  2. If 31m meets the budgets on the low machine: build the 31m provider in QUILL
     (Read Aloud, Studio, previews). Adds about 7 MB to the shared runtime, a
     64.5 MB model plus about 9.5 MB of English voices on the assets-v1 mirror,
     and about 4 to 5 MB of preview samples in the repo.
  3. Write to Gradium asking permission to mirror the 40m models on QUILL's
     release (the iOS precedent below suggests they say yes to free,
     non-commercial accessibility work). Until then, 40m is "sign in to Hugging
     Face and download it yourself", or left out.

## 1. Licensing

### What the sources say (facts)

- Code: "The code is MIT OR Apache-2.0, at your option." The repo has
  `LICENSE-APACHE` and `LICENSE-MIT` and no `NOTICE` file.
  https://github.com/gradium-ai/xn-ptts
- The README: "Phonon 31m is under Apache 2.0, and Phonon 40m and Phonon 40m
  multilingual are under CC BY-NC 4.0", and "Check each model's page on Hugging
  Face before redistribution." https://github.com/gradium-ai/xn-ptts
- Phonon 31m model card: licence tag `apache-2.0`; "The weights, tokenizer and
  voices in this repository are released under Apache 2.0." Attribution line:
  "Phonon builds on Pocket TTS and the Mimi codec, developed by Kyutai." There is
  no LICENSE file in the repo; the licence is the tag and the card.
  https://huggingface.co/gradium/phonon-31m-en and
  https://huggingface.co/gradium/phonon-31m-en/tree/main
- Phonon 40m (English) and 40m multilingual: tag `cc-by-nc-4.0`; "released under
  CC BY-NC 4.0, which does not allow commercial use"; gated: "You need to agree
  to share your Hugging Face information to access this model." No other gate
  conditions are shown. https://huggingface.co/gradium/phonon-40m-en and
  https://huggingface.co/gradium/phonon-40m-multilingual
- The per-language 40m models for fr, de, es and pt are listed in the README with
  the same licence; I read only the English and multilingual cards.
  https://github.com/gradium-ai/xn-ptts
- Voices: `gradium/phonon-voices` is tagged `apache-2.0`, 102 voices (37 English,
  including 12 character voices "made with Gradium Voice Design"), each a
  `.safetensors` embedding made "with no cloning". No LICENSE file in the repo.
  Repo size 69.3 MB including Ogg Opus samples.
  https://huggingface.co/gradium/phonon-voices
- The product page says of the 40m models: "For commercial use, talk to sales."
  https://gradium.ai/phonon
- Responsible-use text on the model cards: "Do not use Phonon to impersonate a
  real person". https://huggingface.co/gradium/phonon-31m-en
- Training data: none of the cards say what the models were trained on. The blog
  says they were distilled from a larger Phonon teacher.
  https://gradium.ai/blog/release-phonon-open-weight
- CC BY-NC 4.0 defines NonCommercial as "not primarily intended for or directed
  towards commercial advantage or monetary compensation", forbids adding terms
  that restrict recipients (2(a)(5)(B)), and asks for creator, copyright notice,
  licence notice, warranty-disclaimer notice and a link (3(a)(1)).
  https://creativecommons.org/licenses/by-nc/4.0/legalcode.en
- The iOS app "Phonon" (id6828988617) is by Andre Louis, free, described as
  "free, non-commercial", and includes the multilingual model "with Gradium's
  permission". https://apps.apple.com/us/app/id6828988617

### What QUILL may do (inference, not legal advice)

QUILL's position, settled in commit 596a67639 (#1740): QUILL is Jeff Bishop's free
personal project with no commercial use; its own code is MIT. The Piper voices
whose datasets are non-commercial are already kept on that basis
(`quill/data/third_party/components.json`, entry `piper-voices`).

- **Phonon 31m and the voices: bundle, mirror, or point - all fine.** Apache 2.0
  asks us to ship the licence text and keep notices. Required wording, in the
  notices: "Phonon 31m by Gradium, Apache License 2.0. Phonon builds on Pocket
  TTS and the Mimi codec, developed by Kyutai." Because there is no LICENSE file
  upstream, save the model card from the pinned commit into the mirror zip so the
  licence statement travels with the bytes.
- **Phonon 40m (all six): the licence itself permits non-commercial bundling and
  mirroring with attribution**, and QUILL fits the non-commercial definition on
  the same basis as the Piper voices. Two reasons to ask Gradium in writing
  anyway:
  - The gate. Gradium chose to collect contact details before download. A
    mirror skips that. The CC licence says no extra terms can bind recipients,
    so this is probably not a licence breach, but it works against the vendor's
    stated choice, and the relationship matters more than the mirror.
  - Downstream reuse. QUILL is MIT, so anyone may sell a fork. A bundled NC model
    must be labelled clearly as not covered by MIT. Also, `.github/FUNDING.yml`
    links to communityaccess.org; that is a link to an organisation, not a sale,
    but it is worth naming in the request so nothing is a surprise.
- **Needs Gradium's written permission (recommended, not strictly required):**
  mirroring or bundling any 40m model. Not needed for 31m or the voices.
- **How they handle requests:** the App Store listing shows they have already
  granted a blind developer permission to ship the 40m multilingual model in a
  free, non-commercial VoiceOver app. That is the closest precedent to QUILL I
  could find.

Attribution text for a 40m model, if permitted: "Phonon 40m multilingual by
Gradium (https://huggingface.co/gradium/phonon-40m-multilingual), licensed CC
BY-NC 4.0 (https://creativecommons.org/licenses/by-nc/4.0/). Not modified.
Provided without warranty. Builds on Pocket TTS and the Mimi codec by Kyutai."

## 2. The low computer standard

### What QUILL already says (facts from the tree)

- Every installer: `ArchitecturesAllowed=x64compatible`, `MinVersion=10.0`
  (`installer/quill.iss` lines 45 to 49, and each `standalone/*/installer/*.iss`).
- The dictation plan names the baseline: "A 4 GB dual-core Windows 10 computer"
  and "4 GB, two cores (the baseline)"
  (`docs/design/2026-10-05-dictation-plan-and-status.md`).
- RAM budgets for speech models: 600 MB on a 4 GB computer, 1.6 GB on 8 GB, 4 GB
  above (`model_types.RAM_TIERS`, CHANGELOG.md).
- Low-resource mode turns on automatically by RAM
  (`quill/core/model_lifecycle.py`, `should_auto_low_resource`).
- No user-facing "System requirements" page exists; nothing in the tree states a
  CPU instruction-set floor. The only AVX2 mention is the llama.cpp backend's
  fallback message (`quill/core/ai/llama_cpp_backend.py`).

### Proposed standard

| Item | Low standard | Note |
|---|---|---|
| OS | Windows 10 or 11, 64-bit | matches `MinVersion=10.0` |
| CPU | two cores, x86-64, about 2015 | the dictation baseline |
| RAM | 4 GB | Phonon must stay inside the 600 MB speech budget |
| GPU | none | Phonon's GPU paths are build-time options we would not ship |
| Phonon extra | AVX2, FMA, F16C | see below |
| Windows on ARM | Windows 11 24H2+, x64 QUILL under Prism | AVX2 is exposed to x64 apps there |

The AVX2 line is the whole problem. Facts: Intel Haswell (2013) and later have
AVX2 "except models branded as Celeron and Pentium"; Celeron and Pentium gain it
from Tiger Lake (2020); AMD from Excavator (2015).
https://en.wikipedia.org/wiki/Advanced_Vector_Extensions. So the proposed
"about 2015, two cores" machine passes if it is a Core i3 or an AMD A-series,
and fails if it is a 2015 to 2019 Celeron or Pentium laptop - which is exactly the
cheap machine many of our readers own. Inference: Phonon can be a voice for most
of the standard, not all of it. Piper stays the voice that works everywhere.

Windows on ARM facts: Prism exposes AVX, AVX2, BMI, FMA and F16C to x64 apps on
Windows 11 24H2 and later, 64-bit apps only.
https://www.neowin.net/forum/topic/1461792-prism-update-unlocks-avx-avx2-support-for-windows-on-arm/
and https://techcommunity.microsoft.com/blog/windowsosplatform/-/4475631.
A native `win_arm64` wheel also exists (no AVX2 flag on that build, per the
workflow below), but QUILL's runtime is x64, so it would not be used today.

## 3. Windows feasibility (documents and source only)

### Facts

- Release v0.6.0, 2026-10-30, assets include
  `ptts-0.6.0-x86_64-pc-windows-msvc.zip` (7.42 MB). No Windows ARM CLI archive
  is visible. https://github.com/gradium-ai/xn-ptts/releases
- `cli-release.yml` builds Windows on `windows-2022` with
  `-C target-cpu=x86-64-v3 -C target-feature=+crt-static`.
  https://raw.githubusercontent.com/gradium-ai/xn-ptts/main/.github/workflows/cli-release.yml
- `maturin-pub.yml` builds wheels for Windows x64 (`target-cpu=x86-64-v3`) and
  Windows aarch64 (no flag); the comments say v3 lets xn use its AVX quantized
  kernels.
  https://raw.githubusercontent.com/gradium-ai/xn-ptts/main/.github/workflows/maturin-pub.yml
- PyPI `ptts` 0.6.0: `cp39-abi3` wheels incl. `win_amd64` (6.9 MB) and
  `win_arm64` (6.6 MB). "Linux and Windows x86_64 wheels target x86-64-v3 (AVX2,
  FMA and F16C); older x86 CPUs need a source build." https://pypi.org/project/ptts/
- The repo's own `.cargo/config.toml` says `target-cpu=native` for local builds.
  https://raw.githubusercontent.com/gradium-ai/xn-ptts/main/.cargo/config.toml
- Runtime: the xn Rust tensor runtime, "needs no PyTorch". Weights are
  `model.q8.gguf` (64.5 MB) or `model.q4k.gguf` (55.1 MB), but GGUF here is only
  the file format; nothing says llama.cpp or ggml is used.
  https://github.com/gradium-ai/xn-ptts and
  https://huggingface.co/gradium/phonon-31m-en/tree/main
- Text goes in raw through a SentencePiece tokenizer: no phonemizer, no eSpeak.
  Output is 24 kHz mono; one 80 ms frame per step.
  https://gradium.ai/blog/release-phonon-open-weight
- Python API: `ptts.TTS(model)`, with `synth`, `save` and `stream`. "Local paths
  download nothing." But without a model argument it downloads the default, and
  the CLI and Python "fetch a voice from [the catalogue] when the checkpoint
  lacks it". https://pypi.org/project/ptts/ and https://github.com/gradium-ai/xn-ptts
- The C library "never downloads". https://raw.githubusercontent.com/gradium-ai/xn-ptts/main/README.md
- Rate control: "Set the speaking rate with the `duration_delta` condition."
  No SSML or pronunciation controls are documented. Same README.

### Speed figures (all vendor-reported; "x" = seconds of audio per second)

| Device | Phonon 31m | Phonon 40m | Source |
|---|---|---|---|
| Raspberry Pi 5, 1 core | 2.3x, 68 ms first audio | 2.2x, 88 ms | README |
| Raspberry Pi 5 (cores not stated) | 3.7x, 38 ms | - | blog |
| Apple M5, 1 core, plain CPU | 11.6x, 13.6 ms | 11.3x, 17.3 ms | blog |
| Apple M5, 1 core, KleidiAI + Accelerate | 26x, 5 ms | 20x, 7 ms | README |
| Kokoro on Apple M5, 1 core (PyTorch) | 7.3x, 776 ms | - | README, blog |
| Kokoro on Raspberry Pi 5 | below real time, about 7 s to start | - | blog |

README: https://github.com/gradium-ai/xn-ptts ; blog:
https://gradium.ai/blog/release-phonon-open-weight

Piper on a Pi 5: the only figure I found is about 0.19 real-time factor (about 5x)
from an unnamed benchmark quoted in a guide - treat as unverified.
https://aivideosensei.com/guides/piper-tts-offline-voice-guide. I found no
sourced Kokoro int8 figure on a Pi 5 or a weak x86 CPU. QUILL has no measured
Kokoro or Piper speed figures in its own docs either.

### Inference

- No x86 number exists. A Pi 5 core (Cortex-A76, 2.4 GHz) is roughly comparable
  to one core of a 2015 to 2017 mobile Core i3/i5, so 2x real time on one core is
  a plausible expectation for the low machine. Plausible is not measured.
- Vendor headline numbers on Apple use KleidiAI and Accelerate, which are Arm/Apple
  paths. The Windows x64 build has neither, so expect the "plain CPU" column, not
  the headline one.
- Raw-text input means numbers, abbreviations and odd punctuation are the model's
  problem; Gradium reports 1.70 percent word error on hard sentences (phone
  numbers, emails) for 31m against 3.50 for Kokoro (https://gradium.ai/phonon).
  QUILL's pronunciation dictionaries still work because they rewrite text.
- An AVX2-built library on a CPU without AVX2 dies with an illegal-instruction
  exception that Python cannot catch. Loading it inside QUILL's process on the
  wrong CPU would crash QUILL. The CPU check must come first, ideally in a child
  process.

## 4. Integration sketch

### Where it would sit (facts from the tree)

There is no TTS provider class. Read Aloud engines are a string set
(`sapi5`, `dectalk`, `piper`, `kokoro`, `espeak`, `macos`, `elevenlabs`)
dispatched in `quill/core/read_aloud.py` (validation and `_run_*_live` methods).
The `SpeechToTextProvider` in `quill/core/speech/provider.py` is speech-to-text
only. Kokoro is the closest model to copy: a cached in-process model
(`_get_cached_kokoro_onnx`), `lifecycle_service.reserve/note_loaded` for
low-resource eviction, thread count from `quill/core/onnx_threads.py`, a
download through `quill/core/release_assets.py` (assets-v1, SHA-256 pinned), and
UI in `quill/ui/main_frame_speech_downloads.py` and `main_frame_speech_hub.py`.

Places a new engine id `phonon` must be added (each lists engines today):

- `quill/core/read_aloud.py` (valid engines, dispatch, live run)
- `quill/core/settings.py`, `quill/core/settings_specs.py` (voice, rate)
- `quill/core/speech/document_speech.py`, `batch_export.py`,
  `project_profile.py`, `pronunciation.py`
- `quill/apps/studio.py` (engine list, readiness, narration)
- `quill/ui/batch_speech_runner.py`, `main_frame_speech_hub.py`,
  `main_frame_speech_downloads.py`, `main_frame_voice_preview.py`
- `quill/core/voice_catalog.py` (voice list and accents)
- `quill/core/optional_components.py`, `quill/core/release_assets.py`
- `quill/data/third_party/components.json` (three entries: runtime, 31m, voices)

`model_mirrors.py` lives at `quill/core/speech/model_mirrors.py` and is for the
speech-to-text models; the TTS precedent is `release_assets.py`'s `kokoro` entry,
so Phonon belongs there.

### Shape

- **In-process wheel**, like Kokoro: `ptts` `win_amd64` wheel in the shared
  runtime, about 7 MB compressed (installed size to measure). One cached model,
  synthesis per sentence span to a WAV, then QUILL's existing player. Streaming
  can come later for faster first audio.
- **CPU gate before import:** a tiny child process imports `ptts` and synthesises
  one word; QUILL caches the answer per machine. On failure the engine is
  hidden with a sentence saying why and suggesting Piper.
- **No runtime network:** always pass a local model folder and local voice
  files; never call `TTS()` without a path. Downloads go only through
  `release_assets` (already in the egress inventory), so
  `network_egress_audit.py` should need no new call site - but the audit must
  be told that `ptts` itself has a Hugging Face fetch path we never reach, and a
  test should run synthesis with the network blocked.
- **Mirror:** one assets-v1 zip `phonon-31m-en.zip`: `model.q8.gguf` (64.5 MB),
  `config.json`, `tokenizer.json`, `default-voice.safetensors` (256 KB), 37
  English voices (256 KB each, about 9.5 MB) and the saved model card. About
  75 MB unpacked; compresses little.
- **Voice previews:** reuse Gradium's own Ogg Opus samples (Apache 2.0) or
  generate them on the build machine; 37 voices at Kokoro's per-sample size is
  about 4 to 5 MB in `quill/data/voice-previews/phonon`.
- **Studio narration:** same engine id through `document_speech` and
  `batch_export`; mark it single-threaded like Kokoro until measured.
- **QUILL Lite:** nothing. Lite has no self-voicing by design
  (`quill/apps/lite_voice.py`), so Lite cannot get ahead (rule 10). No new
  chords: Phonon is a choice inside the existing Read Aloud settings, so rule 8
  is satisfied by the existing commands.
- **Shared runtime:** today 335.2 MB (`docs/build-machine-sync.md`). Phonon adds
  about 7 MB compressed. No eSpeak or phonemizer needed for it.

## 5. Measurement plan (needs Jeff's approval to run)

What: Phonon 31m q8 and q4k, CLI `ptts.exe` and the Python wheel, against Piper
(en_US-ljspeech-medium) and Kokoro int8 as QUILL ships them.

Machines: (a) the low machine - 4 GB, two cores, Windows 10, AVX2 (a 2015 to 2017
Core i3 laptop is ideal); (b) one Celeron or Pentium without AVX2, to confirm the
failure is clean when checked in a child process; (c) optional Windows on ARM on
24H2.

Text: three fixed passages - a 12-word sentence, a 150-word paragraph with
numbers, dates and an email address, and a 2,000-word chapter.

Measure, five runs each, report the median:

| Measure | How | Budget on the low machine |
|---|---|---|
| Real-time factor | audio seconds / wall seconds, whole passage | 1.5x or better on 1 core, 2x on 2 |
| Time to first audio | first WAV chunk (stream) or first sentence written | under 300 ms after load |
| Load time | process start or `TTS()` to ready | under 2 s warm disk |
| Peak memory | peak working set (`psutil` in a wrapper process) | under 300 MB, inside the 600 MB budget |
| Screen reader lag | NVDA running, time keys during synthesis | no audible stutter |

Pinning: run each case with one core and two cores using
`start /affinity 1` and `start /affinity 3` for the CLI, and the same affinity
on the Python wrapper process. Check whether `ptts --help` exposes a thread
count and record what it used.

Also record: CPU model and flags, Windows build, whether the q4k file is slower
or faster than q8 on x86, a listening check of the numbers passage, and the
network-blocked run (no outbound connection while synthesising from a local
folder).

Pass rule: if 31m q8 makes 1.5x real time on one pinned core of the low machine
with under 300 MB peak, build it. If it only passes on two cores, ship it
labelled "needs a newer computer" and keep Piper the default. If it fails, stop.

## 6. Prototype results on this machine (2026-11-02)

Run after the signed QUILL Lite build, with no build running. Machine: AMD
Ryzen 5 Microsoft Surface Edition, 12 threads, AVX2, 7.5 GB RAM, Windows 11.
Phonon 31m English (ptts 0.6.0 wheel, `win_amd64`) and Piper en_US-ljspeech-medium
(piper-tts with onnxruntime), each in its own process pinned to 1, 2 or 4 cores,
with the engine's thread count set to match. Three passages: an 8-word sentence,
a 70-word paragraph full of numbers, dates and an email address, and a
passage of about 570 words. Single runs, not medians.

| Engine and cores | Load | Peak memory | Short: speed / first audio | Numbers: speed | Long: speed / first audio |
|---|---|---|---|---|---|
| Phonon q8, 1 core | 0.4 s | 276 MB | 2.6x / 315 ms | 3.5x | 3.7x / 65 ms |
| Phonon q4k, 1 core | 0.5 s (warm) | 269 MB | 2.9x / 190 ms | 3.7x | 3.8x / 63 ms |
| Phonon q8, 2 cores | 0.4 s | 310 MB | 3.2x / 175 ms | 3.7x | 3.8x / 58 ms |
| Phonon q8, 4 cores | 0.4 s | 376 MB | 4.9x / 108 ms | 5.4x | 5.5x / 49 ms |
| Piper medium, 1 core | about 10 s* | 502 MB | 1.1x / 2,825 ms** | 8.1x | 8.6x / 785 ms |
| Piper medium, 2 cores | about 10 s* | 599 MB | 5.4x / 648 ms | 6.5x | 8.5x / 818 ms |
| Piper medium, 4 cores | about 10 s* | 501 MB | 9.7x / 350 ms | 10.7x | 12.7x / 599 ms |

Speed is audio seconds per wall-clock second (higher is faster; 1x is just
keeping up). * The Piper loader was run twice to apply the thread limit, so its
load time is overstated. ** Piper's very first sentence includes its one-time
warm-up.

What this shows:

- Phonon passes the PRD's bar on this machine: 3.5x real time on one core, well
  above the 1.5x target, with 276 MB peak, under the 300 MB budget.
- Phonon starts speaking far sooner than Piper: about 60 ms into a long passage
  against about 800 ms, and it loads in under half a second. For a screen-reader
  user that is the number that matters most: the gap between pressing the key
  and hearing speech.
- Piper produces audio faster overall once it is going (about 8x on one core),
  and both are comfortably faster than real time.
- Phonon used less memory than Piper here (about 280 to 380 MB against 500 to 600 MB).
- q4k is slightly faster than q8 and slightly smaller; quality to be judged by ear.
- Caveat: one core of a 2021 Ryzen is two to three times faster than one core of
  a 2015 dual-core laptop. Scaled down that far, Phonon would still keep up on one
  core (roughly 1.2x to 1.8x) and more comfortably on two. A machine without AVX2
  cannot run these wheels at all; that needs a separate check on such a machine.

Listening samples (2 cores, q8) are in `S:\QUILL\dist\phonon-samples`: the
short sentence, the numbers paragraph and the long passage for Phonon and for
Piper, named by engine.
