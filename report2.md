# QUILL human and live validation

Updated: 2026-11-25

This file lists only checks and external confirmations that require people,
real services, installed Windows builds, assistive technology, or provider
input. Completed rows are removed. `report.md` holds the remaining
implementation and release-engineering work.

## Credentials and operations

- [ ] Restore `DEV_BUILDS_TOKEN`.
- [ ] Add `QUILL_PODCAST_INDEX_KEY` and `QUILL_PODCAST_INDEX_SECRET` for Cast
      Dev search, or explicitly keep that capability absent in the Dev build.

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
