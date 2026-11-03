# Phonon Voices -- Product Requirements

Version 0.2, 2026-11-03. **Status: phases 1 and 2 shipped** in QUILL and QUILL
Studio (PR #1747, 2026-11-02): Phonon 31m and its 37 English voices ship in the
shared runtime, in Read Aloud, audio export, voice previews, batch export and
Studio narration. Where the build differs from this plan, the code and its
docstrings (`quill/core/speech/phonon_tts.py`) are the record: the CPU check asks
Windows for AVX2 instead of spawning a probe process, the model ships bundled
rather than downloaded, and the speed range is 0.85 to 1.3, measured. Phases 3
and 4 are still to do.

The research behind it, with a link for every outside claim and the prototype
measurements from this computer, is
`docs/design/2026-11-02-phonon-research.md` (formerly `phonon.md`). Where this
document states a fact about Phonon it is taken from there.

**Licensing in one paragraph:** the Phonon runtime is MIT or Apache 2.0. Phonon
31m (English) and the 102 voice files are Apache 2.0, so QUILL may bundle and
mirror them. The five per-language 40m models and the 40m multilingual model are
CC BY-NC 4.0 and gated on Hugging Face; the licence allows a free,
non-commercial project like QUILL to redistribute them with attribution, but we
ask Gradium in writing before mirroring any of them, and until they answer QUILL
only points people to the upstream download.

## 1. Product statement

Phonon is an offline voice for Read Aloud and Studio narration that sounds
natural and starts speaking almost at once, on the kind of computer most of our
readers actually own. Today the choice on a cheap laptop is between Piper, which
is quick and a bit flat, and Kokoro, which sounds better and is slow to start.
Phonon is small (64.5 MB for the English model), needs no phonemizer, and its
maker reports it running faster than Kokoro by a wide margin. If our own
measurements agree on a weak machine, it becomes the natural-sounding voice for
people who cannot wait for Kokoro.

It is one more voice, not a new product. It lives inside QUILL's existing Read
Aloud, Studio, Voice Previews and download machinery, and it adds no new window
and no new key.

## 2. Users

- U-1. Blind and low-vision people who listen to long documents, on a Windows
  laptop bought cheaply or handed down, often with NVDA or JAWS running beside
  QUILL. They notice a two-second wait before every paragraph; they also notice
  when a voice stumbles over a phone number.
- U-2. People making audiobooks and narrated files in Studio, who care about
  total render time on the same kind of machine.
- U-3. People without a reliable connection, for whom "offline" must mean that
  nothing leaves the computer after the one download.

## 3. The low computer standard (a hard requirement)

- R-1. **The standard.** Windows 10 or 11, 64-bit; two CPU cores; 4 GB of RAM; no
  graphics card. This is the baseline QUILL's dictation work already uses ("a
  4 GB dual-core Windows 10 computer") and matches every installer's
  `MinVersion=10.0` and `ArchitecturesAllowed=x64compatible`.
- R-2. **Phonon's extra condition: AVX2, FMA and F16C.** Gradium's Windows x64
  builds are compiled for x86-64-v3. Roughly: Intel Core 4th generation (2013)
  or later, AMD 2015 or later, and Celeron or Pentium only from 2020. On
  Windows on ARM, Windows 11 24H2 or later, where Prism shows AVX2 to x64
  programs. A computer without these is inside QUILL's standard but outside
  Phonon's, and R-30 says what happens there.
- R-3. **Phonon is not offered as a voice unless it meets the budgets in
  section 14 on the reference low machine.** If it only meets them on two
  cores, it is offered with the "needs a newer computer" note and is never the
  default.
- R-4. **Memory.** Phonon, loaded and speaking, stays inside the speech budget
  QUILL already enforces: 600 MB on a 4 GB computer. Low-resource mode may
  unload it like any other engine.

## 4. Goals and non-goals

Goals:

- G-1. A natural English voice that starts speaking in well under half a second
  on the low machine.
- G-2. Thirty-seven English voices (twenty-five plus twelve character voices)
  chosen exactly the way Kokoro and Piper voices are chosen today.
- G-3. Studio narration with the same voice, at least twice real time on the
  low machine.
- G-4. Fully offline after one download, verified by a test.
- G-5. Notices and attribution correct for every file we ship or mirror.

Non-goals:

- N-1. Voice cloning or Voice Design. Those need Gradium's online studio and an
  account; QUILL does not send anyone's voice anywhere.
- N-2. GPU, CUDA, Vulkan or WebGPU builds.
- N-3. Building our own non-AVX2 Phonon binary in the first release (see D-4).
- N-4. Any voice in QUILL Lite. Lite has no self-voicing by design
  (`quill/apps/lite_voice.py`); see R-12.
- N-5. Replacing Piper or Kokoro. Both stay; Piper stays the voice that works on
  every computer QUILL supports.
- N-6. macOS. QUILL supports it, but this program measures and ships Windows
  first; the macOS wheel exists and can follow.

## 5. Architecture

- R-5. **One engine id, `phonon`,** added beside `sapi5`, `dectalk`, `piper`,
  `kokoro`, `espeak`, `macos` and `elevenlabs` everywhere those are listed:
  `quill/core/read_aloud.py`, `settings.py`, `settings_specs.py`,
  `speech/document_speech.py`, `speech/batch_export.py`,
  `speech/project_profile.py`, `speech/pronunciation.py`, `voice_catalog.py`,
  `optional_components.py`, `release_assets.py`, `apps/studio.py`,
  `ui/batch_speech_runner.py`, `ui/main_frame_speech_hub.py`,
  `ui/main_frame_speech_downloads.py` and `ui/main_frame_voice_preview.py`.
- R-6. **The engine code lives in a new wx-free module,
  `quill/core/speech/phonon_tts.py`,** strict-typed and in `mypy` scope.
  `read_aloud.py` (1,702 lines and on a size budget) gains only the dispatch
  branch and a thin `_run_phonon_live`, as Kokoro and ElevenLabs did.
- R-7. **In process, through the `ptts` Python wheel** (`cp39-abi3`,
  `win_amd64`, about 7 MB). One model is loaded and cached, exactly like
  `_get_cached_kokoro_onnx`, registered with `lifecycle_service` as
  `tts:phonon` so low-resource mode can evict it.
- R-8. **The CPU check runs before the import, in a child process.** A library
  built for AVX2 that lands on a CPU without it dies with an illegal-instruction
  exception that Python cannot catch, which would take QUILL down with it. A
  short child process imports `ptts` and speaks one word from the local model;
  QUILL records the result per machine (CPU name and Windows build) and only
  then imports `ptts` in its own process. The check reruns when either changes.
- R-9. **Always a local path.** QUILL never constructs the model without a local
  folder and never asks for a voice the folder lacks. The library has a Hugging
  Face fetch path for both; QUILL must never reach it (R-40).
- R-10. **Speech is per sentence span, written to WAV and played through
  QUILL's existing player**, the same shape as Kokoro and Piper, so pause,
  resume, the cursor and the synthesis cache all work unchanged. Streaming
  frames for faster first audio is phase 3, not phase 1.
- R-11. **Threads.** Follow `quill/core/onnx_threads.py`: cores, at most four,
  and one on the low machine if measurement shows the second core is better
  left to the screen reader.
- R-12. **QUILL Lite.** No change. Family rule 10 says Lite may never be ahead
  of QUILL; adding a voice to QUILL only is the permitted direction. The new
  settings are recorded as `one_side` in the settings vocabulary audit with the
  reason "QUILL Lite has no self-voicing".

## 6. Models, delivery and licence

| Model | Size | Licence | Delivery in phase 1 |
|---|---|---|---|
| Phonon 31m English, q8 | 64.5 MB | Apache 2.0 | mirrored on assets-v1, downloaded on request |
| 37 English voices + default | 256 KB each, about 9.7 MB | Apache 2.0 | in the same zip |
| Phonon 40m English, q8 | 74.6 MB | CC BY-NC 4.0, gated | not offered (phase 4) |
| Phonon 40m fr, de, es, pt | 74.6 MB each (assumed same as English) | CC BY-NC 4.0, gated | not offered (phase 4) |
| Phonon 40m multilingual | 74.6 MB | CC BY-NC 4.0, gated | not offered (phase 4) |
| 65 non-English voices | 256 KB each, about 16.6 MB | Apache 2.0 | with the 40m models |

- R-13. **Phonon 31m ships as one zip on QUILL's `assets-v1` release,**
  `phonon-31m-en.zip`, pinned by SHA-256 in `release_assets.py` with
  `expect_member="model.q8.gguf"`, holding `model.q8.gguf`, `config.json`,
  `tokenizer.json`, `default-voice.safetensors`, the 37 English voice files,
  `voices.jsonl` and the model card saved from the pinned Hugging Face commit.
  About 75 MB. The model card goes in because neither Hugging Face repo has a
  LICENSE file; the card is the licence statement and it must travel with the
  bytes.
- R-14. **The Offline Edition may bundle the same zip** as an optional
  component, as Kokoro is today. Apache 2.0 allows it. Whether it does is D-3.
- R-15. **40m models: point only, until Gradium answers.** Phase 4 offers them
  in one of two ways, decided by D-2: mirrored like 31m (with Gradium's written
  permission on file), or a help page that tells people how to accept the terms
  on Hugging Face and where to put the folder, after which QUILL finds it. QUILL
  itself never signs in to Hugging Face for this.
- R-16. **Labelled honestly.** Any 40m model shown in QUILL says "free for
  non-commercial use only" in its description, because QUILL's own MIT licence
  does not cover it and a fork could otherwise be sold with it inside.
- R-17. **Responsible use.** The model cards ask that Phonon not be used to
  impersonate a real person. QUILL ships no cloned voices and offers no
  cloning (N-1), so there is nothing to enforce; the user guide says so in one
  sentence.

## 7. Read Aloud

- R-18. Phonon appears in the Read Aloud engine list as "Phonon (neural,
  offline)", after Kokoro.
- R-19. Every existing Read Aloud command works with it unchanged: start,
  pause, resume, stop, next and previous sentence, read selection, read from
  cursor. No new command and no new key.
- R-20. **Rate.** Phonon sets speed with its `duration_delta` condition. QUILL
  maps its usual rate control onto that over a range the prototype finds safe;
  if the mapping cannot cover at least 0.75 to 1.5 times normal without the
  voice falling apart, the rate control says its range rather than pretending.
- R-21. **Pronunciation dictionaries** apply, because they rewrite text before
  the engine sees it. `pronunciation.ENGINES` gains `phonon`.
- R-22. **Text.** Phonon reads raw text, numbers and email addresses itself, and
  its maker reports fewer mistakes on them than Kokoro. QUILL's existing text
  normalising still runs first; the prototype checks it does not make Phonon
  worse, and if it does, Phonon skips the steps that hurt.

## 8. Studio narration

- R-23. Phonon is offered in Studio's engine list and in batch export, with the
  same voice and rate settings as Read Aloud.
- R-24. It is added to `_SINGLE_THREAD_ENGINES` in `batch_export.py` until
  measurement shows two parallel jobs are faster on the low machine.
- R-25. Narration projects (`project_profile.py`) remember `phonon` and its
  voice like any other engine, and a project saved with Phonon opened on a
  computer that fails the CPU check falls back as R-31 describes.

## 9. Voice previews

- R-26. Each English voice has a short sample in
  `quill/data/voice-previews/phonon`, about 4 to 5 MB for 37 voices at Kokoro's
  sample size.
- R-27. The samples are Gradium's own (Apache 2.0, from `phonon-voices`),
  converted to the format the other previews use, or made on the build machine
  with QUILL's standard preview sentence. D-5 chooses. Either way they work on a
  computer that cannot run Phonon, so a person can hear what they would get
  before learning their computer is too old for it.

## 10. Settings and keys

- R-28. New settings, each documented (GATE-SETDOC) and added to the settings
  vocabulary audit as `one_side`:
  - `read_aloud_phonon_voice`, default the model's default voice;
  - `read_aloud_phonon_rate`, default 1.0;
  - `warm_phonon_model`, default false (Kokoro's warm-up is true; Phonon loads
    fast enough that warming it should not be needed -- measured, not assumed).
- R-29. No new chords. Phonon is a choice inside existing windows, reached by
  existing commands, so rule 8 is already satisfied and the keyboard reference
  does not change.

## 11. Accessibility contract

- A-1. Every new control (engine choice entry, voice list, rate) has an
  accessible name and an access key unique in its window (GATE-14). OK, Cancel
  and Close carry none.
- A-2. Each new control has inline `SetHelpText` at its construction site, and
  the window's F1 purpose mentions Phonon where it lists engines. The F1 help
  reference is regenerated.
- A-3. Speak only what the screen reader does not already say (GATE-13).
  Selecting Phonon in a list is not announced; the list already says it. What
  is announced: a finished download, a failed CPU check, a fallback to another
  voice, and a model removed by low-resource mode while reading.
- A-4. Everything announced is also brailled, through the announcement service
  (GATE-BRAILLE). No direct speech call.
- A-5. Focus does not move when a download finishes or the CPU check completes.
  If the check fails while the person is in the engine list, focus stays where
  it is and the explanation is spoken once and written to the status bar.
- A-6. Download progress uses the existing accessible progress path: a
  percentage, no more than one update per percent.
- A-7. Phonon's own voice must never speak over the screen reader's. Read Aloud
  already stops when the person starts typing; that behaviour is tested with
  Phonon too.
- A-8. Nothing depends on colour. "Needs a newer computer" is words.

## 12. Failure and fallback

- R-30. **CPU check fails (no AVX2).** Phonon is still listed, with the words
  "needs a newer computer (AVX2)". Choosing it says, once: "Phonon needs a
  processor from about 2015 or later, and this computer's processor is older.
  Piper works here and sounds similar for most reading." and offers Piper. It
  never crashes and never silently switches.
- R-31. **Too slow on this machine.** QUILL measures the first few sentences.
  If Phonon cannot keep up -- audio running out before the next sentence is
  ready, twice in one minute -- QUILL says once: "Phonon is too slow on this
  computer to read without pauses. Piper is quicker here. Switch to Piper?"
  Yes switches for this session and offers to make it the default; No keeps
  Phonon and does not ask again until the next start.
- R-32. **Model missing or damaged.** The SHA-256 check fails or a file is
  absent: say which, offer the download again, and fall back the way a missing
  Kokoro model does today.
- R-33. **Synthesis error on one passage.** Split the passage and retry, as
  Kokoro does at 400 characters; if a piece still fails, skip it, say "one
  sentence could not be read", and carry on.
- R-34. **Safe Mode** does not disable Phonon (it is offline and local), but it
  skips the warm-up.
- R-35. **Error codes.** One new exception, `PhononUnavailableError`, under
  `ReadAloudUnavailableError` with its own code,
  `QUILL-READALOUD-PHONON-UNAVAILABLE` (GATE-EC), and messages in plain words.

## 13. Notices and attribution

- R-36. Three new entries in `quill/data/third_party/components.json`, with the
  notices regenerated:
  - `ptts` runtime: MIT OR Apache-2.0, shared runtime, Copyright Gradium.
  - `phonon-31m`: Apache-2.0, on request (and bundled if D-3 says so).
    Obligations: keep the Apache text and the model card; credit "Phonon 31m by
    Gradium. Phonon builds on Pocket TTS and the Mimi codec, developed by
    Kyutai."
  - `phonon-voices`: Apache-2.0, with the samples.
- R-37. If any 40m model is ever mirrored or bundled, its entry carries the full
  CC BY-NC 4.0 attribution: creator, copyright notice, link to the licence,
  warranty disclaimer, link to the model, "not modified", and "free for
  non-commercial use only", plus a reference to Gradium's written permission.
- R-38. About QUILL and the user guide name Phonon and Gradium with the same
  credit line.

## 14. Performance budgets

Measured on the reference low machine (4 GB, two cores, Windows 10, AVX2), NVDA
running, with a fixed 12-word sentence, a 150-word paragraph full of numbers and
an email address, and a 2,000-word chapter; five runs, median reported.

| Measure | Budget | How |
|---|---|---|
| Real-time factor, one core | 1.5x or better | audio seconds over wall seconds, affinity to one core |
| Real-time factor, two cores | 2x or better | affinity to two cores |
| Time to first audio | under 300 ms after load | start call to first sentence WAV ready |
| Load time | under 2 s | model construct to ready, warm disk |
| Peak memory | under 300 MB | peak working set of the process doing synthesis |
| Studio, 2,000 words | under half the audio length | wall time for a batch export |
| Screen reader | no audible stutter while typing | a person listening |

- R-39. A small benchmark tool, `python -m quill.tools.tts_benchmark`, prints
  these numbers for any installed engine, so the same table can be made for
  Piper and Kokoro on the same machine. It is a developer tool, not a gate:
  timings on shared CI runners mean nothing.

## 15. Privacy and network

- R-40. No network at run time. The only download is the assets-v1 zip through
  `release_assets`, which the network egress audit already lists. The audit's
  notes record that `ptts` contains a Hugging Face fetch path that QUILL never
  reaches, and why (R-9).
- R-41. A test runs synthesis from a local folder with sockets blocked and fails
  on any connection attempt.
- R-42. Text read aloud is never logged beyond what Read Aloud logs today.

## 16. Packaging and sizes

| Item | Size | Where |
|---|---|---|
| `ptts` wheel | about 7 MB compressed; installed size to measure | shared runtime (335.2 MB today) |
| 31m model zip | about 75 MB | assets-v1, on request |
| English previews | about 4 to 5 MB | repo, every installer that ships previews |
| 40m model (each) | 74.6 MB plus voices | phase 4 only |

- R-43. The `ptts` wheel is pinned by version and hash in the runtime build and
  appears in the build inventory, so the notices gate sees it.
- R-44. Portable editions of Studio decide separately whether to carry the 31m
  zip, as they do for Kokoro.

## 17. Tests and gates

- T-1. Unit tests for `phonon_tts.py`: model folder discovery, voice listing,
  the CPU check's cache and its invalidation, rate mapping, and the fallback
  messages -- without importing `ptts`, by faking the child-process answer.
- T-2. Every Read Aloud and Studio handler that gained a `phonon` branch has a
  behavioural test that calls it.
- T-3. The network-blocked synthesis test (R-41), marked so it runs only where
  the model is present.
- T-4. Gates that must stay green: third-party notices (`--check`), settings
  documentation (GATE-SETDOC), settings vocabulary, F1 help reference
  (GATE-HELPREF), access keys (GATE-14), over-announce (GATE-13), braille
  parity, error codes (GATE-EC), module size budget (GATE-11), network egress
  audit, surface reachability (no new surface expected), dialog inventory.
- T-5. A person with NVDA and a person with JAWS on the low machine, added to
  `docs/qa/screen-reader-checks-2026-10.md`: choose the voice, read a chapter,
  type during reading, fail the CPU check on a second machine.

## 18. Phases

| Phase | What | Size |
|---|---|---|
| 0 | Measure on real machines (the research note, section 5); Jeff decides go or stop | one evening; no repo change |
| 1 | 31m in Read Aloud: engine, CPU check, download, settings, notices, tests | about 600 to 900 lines plus tests; 7 MB runtime, 75 MB mirror |
| 2 | Studio narration and Voice Previews | about 200 to 300 lines; 4 to 5 MB samples |
| 3 | Streaming first audio and the slow-machine detector tuned from field reports | about 200 lines |
| 4 | 40m models, after Gradium answers | about 150 lines; 75 MB per model on the mirror if permitted |

## 19. Risks

- K-1. **AVX2.** The cheapest laptops of 2015 to 2019 cannot run Phonon at all.
  Mitigated by R-8 and R-30; the real fix is D-4.
- K-2. **No x86 figures exist.** Every speed number so far is Gradium's, on Arm
  or Apple hardware with acceleration our Windows build does not have. Phase 0
  exists for this.
- K-3. **Young project.** First stable release 2026-10-20, five releases in ten
  days. Pin the version; update deliberately.
- K-4. **Rate control** may not reach the range people use. R-20 says what we do.
- K-5. **The 40m gate.** Mirroring without asking could sour the relationship
  with a vendor that has shown it is willing to help. Mitigated by D-2.
- K-6. **In-process native code.** A crash in `ptts` is a crash in QUILL.
  Mitigated by the child-process check; if crashes appear in the field, move
  synthesis into a worker process like the one Piper already uses.

## 20. Open decisions for Jeff

- D-1. **Go or stop after phase 0?** Recommended: go only if 31m makes 1.5x real
  time on one pinned core of the low machine with under 300 MB peak.
- D-2. **Ask Gradium to mirror the 40m models?** Recommended: yes, now, by
  email, naming QUILL as free and non-commercial for blind readers and citing
  the iOS Phonon app as precedent. Until they answer, point only.
- D-3. **Bundle 31m in the Offline Edition?** Recommended: yes, as an optional
  component beside Kokoro, after phase 1 has been used for one release.
- D-4. **Build a non-AVX2 `ptts` wheel ourselves?** Recommended: not in phase 1.
  The licence allows it, but it means building and signing third-party Rust code
  in QUILL's CI, and it will be slower without the AVX kernels. Revisit if the
  field shows many readers on older Celerons; ask Gradium first whether they
  would publish an x86-64-v2 wheel themselves.
- D-5. **Preview samples: Gradium's or our own?** Recommended: our own, made on
  the build machine with QUILL's standard sentence, so every engine's previews
  say the same thing and can be compared fairly.
- D-6. **Default voice for new users?** Recommended: unchanged. Phonon is never
  the default in phase 1; revisit after one release of field reports.
- D-7. **Write a public "System requirements" page?** Recommended: yes. QUILL has
  no single place that says 4 GB, two cores, Windows 10, and which features need
  AVX2 (Phonon and the local AI models). This program is a good reason to write
  it.
