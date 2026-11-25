# QUILL remaining work

Updated: 2026-11-25

This file lists only open implementation and release-engineering work.
Completed rows are removed after they land on `main`. Human acceptance, live
tests, credentials, external permissions, and provider confirmations are
tracked in [report2.md](report2.md) and are not counted as code-complete.
Delete this file when its implementation and release-engineering list reaches
zero; [report2.md](report2.md) remains the human and operational record.

## Current implementation summary

- Ten implementation and release-engineering items remain: two release
  operations, two SwiftLetter items, and six startup-speed items.
- GitHub Workbench implementation is complete on `main`.
- The existing WordPress Workbench and Practice Site implementation is complete
  on `main`; SwiftLetter Phase 1 remains open separately in PR #2003.
- Scribe implementation is complete, including durable conversion and
  transcription queues. Pneuma confirmed the ETA contract, and QUILL now
  follows it. No Scribe code or provider-contract blocker remains.
- Converter queue persistence is complete in PR #2077 and merged to `main`.
- All human, credential, live-service, and external work is kept in
  [report2.md](report2.md) and is not part of the code-work count.

## Release and packaging

- [ ] Run the first catalogue-driven Dev build and inspect every artifact.
- [ ] Build and inventory a real staged shared Windows runtime, then run the
      skipped runtime-inventory gate.

## Startup speed

- [ ] Add a profile read before optional modules import.
- [ ] In Notepad/minimal mode defer Rich Edit/TOM, AI, LSP, Scribe, dictation,
      extensions, printing, and optional menu implementations.
- [ ] Keep crash capture, recovery, atomic save, keymap, focus, announcements,
      TLS, and essential editor behavior in the mandatory core.
- [ ] Preserve the open document/session when moving between light and heavy
      profiles; use an explicit restart when an in-process switch cannot be
      safe.
- [ ] Measure installed-build ready-editor and cold-import startup for QUILL,
      Lite, Radio, Cast, Transcribe, Converter, Studio, Inkwell, Weather,
      Beacon, and Social.
- [ ] Target at least the already achieved 25.5 percent Lite gain as a floor,
      then optimize the minimal profiles separately without weakening
      accessibility or persistence.

## SwiftLetter integration, last

- [ ] Resolve PR #2003's review and failing documentation-contract shard, sync
      the shared SwiftLetter fixtures, and merge the approved stack to `main`.
- [ ] Complete SwiftLetter Phase 1 editor wiring: open an article, Save to
      SwiftLetter, Compare/Retry, and lossless Markdown/HTML round trips.

## Future plan after the remaining tasks: reuse system Whisper resources

Run this work only after the ten remaining items above are complete. The goal
is to save model and engine space without making another project a hidden
dependency.

### 1. Preserve the supported baseline

- Keep QUILL's CPU/int8 Faster Whisper path fully supported.
- Keep the existing automatic CUDA/float16 choice when CTranslate2 detects a
  usable GPU.
- Do not require a GPU, CUDA, another Python installation, or another app.
- Do not scan the whole disk or execute a program found unexpectedly on
  `PATH`.

### 2. Add safe model discovery and adoption

- Inspect only documented model-cache locations and user-selected folders.
- Recognize only catalogued Faster Whisper CTranslate2 model layouts, not an
  arbitrary folder that merely contains `model.bin`.
- Verify model family, revision/format, required files, size, and recorded
  SHA-256 before offering adoption.
- Present one explicit choice: reference the existing model, hard-link it when
  the filesystem permits, or copy it into QUILL-managed storage.
- Explain the failure mode beside reference mode: removing or changing the
  other project can make that reference unusable.
- Keep a QUILL-owned metadata record for adopted models and revalidate it
  before transcription.
- If an adopted model disappears or fails validation, disable it for that
  session and offer QUILL's managed download or CPU fallback.

### 3. Add optional external-engine detection

- Detect a known Faster Whisper installation only in a user-approved
  environment or virtual environment.
- Probe a compatible `faster-whisper`/CTranslate2/Python combination in an
  isolated process; never import an external environment into QUILL's main
  interpreter.
- Verify version, ABI, device availability, model compatibility, and exit
  behavior before enabling it.
- Clearly label the engine as external and keep QUILL's on-demand managed
  engine as the repair path.
- Never reuse an arbitrary `whisper` or `whisper.exe` command; whisper.cpp,
  open-source Whisper, and Faster Whisper do not share the same command
  contract.

### 4. Keep updates and consent predictable

- A detected external engine or model remains optional; QUILL never adopts or
  activates it without an explicit user action.
- Revalidate external resources after QUILL, the other app, Python, CUDA, or
  CTranslate2 changes.
- Do not silently network when probing external installations.
- Keep model removal separate from the other project's storage; QUILL may
  remove only its own copies, links, and metadata.

### 5. Verify behavior and space savings

- Add unit tests for model-layout validation, checksums, missing files,
  broken references, hard-link fallback, incompatible versions, CPU fallback,
  and external-process failure.
- Run live Windows tests for installed QUILL, portable QUILL, CUDA, no-CUDA,
  model removal during a session, and use alongside another Whisper project.
- Measure download/engine footprint, model duplication, startup cost, first
  transcription, warm transcription, and uninstall behavior.
- Document the external-resource risk and update the speech privacy/network
  audit before shipping.

