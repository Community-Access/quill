# QUILL remaining work

Updated: 2026-11-25

This file lists only open implementation and release-engineering work.
Completed rows are removed after they land on `main`. Human acceptance, live
tests, credentials, external permissions, and provider confirmations are
tracked in [report2.md](report2.md) and are not counted as code-complete.

## Current implementation summary

- Eight implementation and release-engineering items remain: two release
  operations and six startup-speed items.
- GitHub Workbench implementation is complete on `main`; remaining live-role,
  permissions, protected-branch, and Copilot-plan checks are in
  [report2.md](report2.md).
- WordPress Workbench and Practice Site implementation is complete on `main`;
  the remaining staged-runtime inventory is part of release packaging below,
  and live payment/OAuth/site checks are in [report2.md](report2.md).
- Scribe implementation is complete, including durable conversion and
  transcription queues. Real-service acceptance and the Pneuma ETA
  contract remain external checks in [report2.md](report2.md).
- Converter queue persistence is complete in PR #2077 and merged to `main`.
- [report2.md](report2.md) has nine human/credential items and two external
  blockers. They are intentionally excluded from the code-work count.

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

