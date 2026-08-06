# QUILL 1.0.0 — Release Readiness Program

**Owner:** Jeff Bishop · **Status:** in progress · **Goal:** ship a stable, editor-first QUILL 1.0.0 with only Radio + Weather as public companion apps, complete docs, and an exhaustive feature sign-off.

## Locked decisions (2026-08-05)
- **Public companion apps:** **Radio + Weather only.** Player, Converter, Cast, Audio Studio, and Beacon are gated behind a **developer/private/admin flag** (existing `future.<feature>` mechanism) — installed but not publicly surfaced.
- **App "own repo" extraction = DOCS ONLY.** Move other-app documentation out of QUILL's user guide / PRD / release notes into their own docs; app **code stays in this repo** (gated). No code repo split this cycle.
- **Branches:** **merge all `feat/*` to main** this pass, then delete merged branches — after each merges cleanly and gates pass.
- **Sign-off:** must cover **every single feature in QUILL**, derived from the code (commands, menus, dialogs, keymap) so nothing is missed.

## Phases

### Phase 1 — Stabilize the tree & land in-flight work  ✅ DONE
- [x] Commit the large uncommitted WIP (media-player / voice / secrets / auth) onto its own branch, fixing its gate violations so pre-commit passes (landed as fabc213).
- [x] Fix GATE-11 on `quill/tools/network_egress_audit.py`.
- [x] Land the **NLS BARD catalogue search** commit (4e15cc9).

### Phase 2 — Gate non-public apps (Radio + Weather stay public)  ✅ DONE
- [x] Gate **Player, Converter, Cast, Audio Studio, Beacon** behind `RELEASED_APPS` / `is_app_released()` (25e6611); the editor-embedded **Podcasts** feature joined the gate via `FeatureDefinition.released` (595f553).
- [x] Confirm Radio + Weather remain fully public and unaffected.
- [x] Tests assert the gated apps are absent from public surfaces when the flag is off (`tests/unit/core/test_features.py`, `test_global_hotkeys.py`, `test_main_frame_quill_key.py`).
- [x] Installer creates shortcuts only for public apps — the QUILL Cast Start-menu/desktop entries were removed from `scripts/build_windows_distribution.py` (2026-08-05). Standalone builds are published only for the editor, Quill Radio, and Quill Weather.

### Phase 3 — Docs consolidation (editor-first)  ✅ DONE
- [x] Archive all **beta** release notes under `docs/release notes/archived/` (keep 1.0.0 live).
- [x] Write a **new 1.0.0 announcement about the QUILL editor features only** (`docs/release notes/announcement-1.0.0.md`, 77d395c).
- [x] Move **other-app** sections (Player/Converter/Cast/Studio/Beacon) out of the user guide, PRD, and release notes into per-app docs under `docs/apps/` (Audio Studio's joined `docs/audio-studio/`); Radio + Weather kept public (02a8968).
- [x] Verify the **user guide** and **PRD** are complete and accurate for the editor + public apps.
- [x] **Release-notes fact-check audit (2026-08-05):** ~420 concrete claims (commands, chords, menu paths, dialogs, settings) verified against code surfaces by a two-agent sweep. 9 discrepancies found and fixed in `release1.0.0.md`: Outline Navigator scope (headings only), Go to Anything scope (commands + headings; the element index is Quick Nav), no "Bookmarks Manager" surface, Search in Files / Replace Across Files naming, no clipboard-compare command, the retired editor-control chooser, "AI Spell Check" naming, Radio's cross-app launcher lives on the QuillVille menu, and the View-menu vs Settings vs palette split for dark mode / overwrite / contrast. One in-app status string that pointed at the nonexistent "Bookmarks Manager (Ctrl+Shift+G)" was corrected to "List Bookmarks (Alt+Shift+B)" (`quill/ui/main_frame.py`). Everything else verified, including all Radio/Weather chords, catalog counts, and gated-app absence.

### Phase 4 — Exhaustive 1.0.0 sign-off test plan  ← the check-off list  ✅ BUILT
- [x] Complete **feature / command / surface inventory** generated from the codebase (717 commands, 645 dialog surfaces, ~290 feature sub-items, 3 menu bars).
- [x] **Sign-off pack under `docs/planning/signoff/`** — each item has **Works · Surface-exact · Accessible** boxes, grouped, counted, generated from the real registry (not memory):
  - `QUILL-1.0.0-SIGNOFF.md` — master (env matrix, cross-cutting a11y + gating + readiness).
  - `SIGNOFF-editor.md` (644 editor commands) · `SIGNOFF-radio.md` (29 + dialogs + scenarios) · `SIGNOFF-weather.md` (11 menu + chrome + scenarios).
  - `SIGNOFF-dialogs.md` (all 645 dialog surfaces) · `SIGNOFF-gated-apps.md` (44 gated-app commands to verify ABSENT).
  - `SIGNOFF-install-matrix.md` — portable vs system under all scenarios (E1–E6, all three portable signals), per app.
- [ ] Human execution: check off every box across environments E1–E6 (this is the readiness gate).
- [ ] **Coverage MUST include the public companion apps:** **QUILL Radio** and **QUILL Weather** get the same per-command / per-surface sign-off as the editor.
- [ ] **Installation-path matrix (tested richly, all scenarios):** every item is verified under **portable install** *and* **system install** — data-dir resolution, credential storage (`keys.enc`/DPAPI vs Windows Credential Manager vs macOS Keychain), settings location, first-run, updates, Safe Mode, and every portable-only vs system-only behavior. Cross-cut this matrix across the editor, Radio, and Weather.

### Phase 5 — Branch consolidation  ✅ DONE
- [x] Merge every `feat/*` branch to `main` (each verified: merges cleanly + gates pass). Final two (`feat/gate-podcasts-library`, `docs/consolidate-1.0.0`) landed 2026-08-05.
- [x] Delete merged branches (local + origin; only `main` remains, plus `origin/fix/document-readers-and-office-packaging`, superseded — its content landed via other commits — kept pending a confirming diff before deletion).

### Phase 6 — Readiness gate
- [ ] All sign-off items checked → **announce ready to test.**

## Housekeeping record (2026-08-05)
- **Dependabot:** the high alert was fixed by the ab6d910 dependency bumps. The remaining moderate (alert 14, setuptools < 83 MANIFEST.in bypass on macOS filesystems) is **dismissed as tolerable risk**: the macOS `setuptools<83` pin is forced by py2app 0.28.x (latest 0.28.10 breaks on setuptools >= 83), and the vulnerable path — building sdists on APFS/HFS+ — is one QUILL never exercises (py2app builds .app bundles). Rationale recorded in `pyproject.toml`; re-check when py2app supports setuptools 83.
- **ppp.md retired:** the interim 1.0.0 plan-of-record file at the repo root is deleted; this document is the tracked home for what remains. **Remaining work = Phase 4 human sign-off execution (E1–E6, editor + Radio + Weather, portable and system) and the Phase 6 gate.**

---
*The per-feature sign-off checklist lives in `QUILL-1.0.0-SIGNOFF.md` (Phase 4) and is populated from the code inventory so it covers every feature.*
