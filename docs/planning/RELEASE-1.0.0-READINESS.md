# QUILL 1.0.0 — Release Readiness Program

**Owner:** Jeff Bishop · **Status:** in progress · **Goal:** ship a stable, editor-first QUILL 1.0.0 with only Radio + Weather as public companion apps, complete docs, and an exhaustive feature sign-off.

## Locked decisions (2026-08-05)
- **Public companion apps:** **Radio + Weather only.** Player, Converter, Cast, Audio Studio, and Beacon are gated behind a **developer/private/admin flag** (existing `future.<feature>` mechanism) — installed but not publicly surfaced.
- **App "own repo" extraction = DOCS ONLY.** Move other-app documentation out of QUILL's user guide / PRD / release notes into their own docs; app **code stays in this repo** (gated). No code repo split this cycle.
- **Branches:** **merge all `feat/*` to main** this pass, then delete merged branches — after each merges cleanly and gates pass.
- **Sign-off:** must cover **every single feature in QUILL**, derived from the code (commands, menus, dialogs, keymap) so nothing is missed.

## Phases

### Phase 1 — Stabilize the tree & land in-flight work
- [ ] Commit the large uncommitted WIP (media-player / voice / secrets / auth) onto its own branch, fixing its gate violations so pre-commit passes:
  - [ ] Register the new media dialogs (`quill/apps/player.py`, `quill/ui/media/*`) in the A11Y-4 dialog inventory.
  - [ ] Resolve GATE-11 size caps (`quill/apps/player.py` 1034 > 600; split or reviewed budget entry).
- [ ] Fix GATE-11 on `quill/tools/network_egress_audit.py` (BARD egress entry pushed it 11 over budget — slim the entry).
- [ ] Land the **NLS BARD catalogue search** commit (code + tests already green; docs land with the doc-consolidation commit).

### Phase 2 — Gate non-public apps (Radio + Weather stay public)
- [ ] Gate **Player, Converter, Cast, Audio Studio, Beacon** behind a dev/admin flag: launchers, menu/QuillVille entries, command-palette commands, Explorer shell verbs, and build products all respect the flag.
- [ ] Confirm Radio + Weather remain fully public and unaffected.
- [ ] Tests assert the gated apps are absent from public surfaces when the flag is off.

### Phase 3 — Docs consolidation (editor-first)
- [ ] Archive all **beta** release notes under `docs/release notes/archived/` (keep 1.0.0 live).
- [ ] Write a **new 1.0.0 announcement about the QUILL editor features only** (no companion-app content).
- [ ] Move **other-app** sections (Player/Converter/Cast/Studio/Beacon) out of the user guide, PRD, and release notes into their own per-app docs; keep Radio + Weather where publicly relevant.
- [ ] Verify the **user guide** and **PRD** are complete and accurate for the editor + public apps.

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

### Phase 5 — Branch consolidation
- [ ] Merge every `feat/*` branch to `main` (each verified: merges cleanly + gates pass).
- [ ] Delete merged branches.

### Phase 6 — Readiness gate
- [ ] All sign-off items checked → **announce ready to test.**

---
*The per-feature sign-off checklist lives in `QUILL-1.0.0-SIGNOFF.md` (Phase 4) and is populated from the code inventory so it covers every feature.*
