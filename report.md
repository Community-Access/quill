# QUILL remaining work

Updated: 2026-11-25

This file lists only work that is still open. Completed implementation is
removed after it lands on `main`. Human acceptance, live tests, credentials,
and external permissions are listed separately and are not counted as
code-complete.

## Release and packaging

- [ ] Restore `DEV_BUILDS_TOKEN`.
- [ ] Add `QUILL_PODCAST_INDEX_KEY` and `QUILL_PODCAST_INDEX_SECRET` for Cast
      Dev search, or explicitly keep that capability absent in the Dev build.
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

## Human-only validation

- [ ] Required NVDA/JAWS/Narrator checks for shipped dialogs and family journeys.
- [ ] Clean installed and portable machine updates.
- [ ] Stable/Beta/Dev coexistence on real Windows installs.
- [ ] Real Scribe, Moonshine, OCR, clipboard, display, and Windows integration.
- [ ] GitHub live-role, protected-branch, organization, secret, and Copilot-plan
      scenarios.
- [ ] WordPress live-site, payment, OAuth, and packaged Practice Site scenarios.
- [ ] Screen-reader verification of Cast list stability and Lite handoffs.

## External blockers

- The original Lite `0xc0000374` component remains unidentified. Diagnostics
  are improved, but the native root cause is not claimed fixed.
- Pneuma ETA milliseconds still need provider confirmation.
