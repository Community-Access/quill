# QUILL 1.0.0 — Release Sign-off Test Plan (master)

**Purpose:** verify **every feature in QUILL** — the editor plus the two public companion apps (**Quill Radio**, **Quill Weather**) — works, presents an exact surface, and is accessible, under **both portable and system installs**. Nothing ships until every applicable box is checked.

**Scope (derived from the codebase, not memory):** ~290 feature sub-items across 22 areas · 3 menu bars (~480–500 editor leaves + Radio ~10 / Weather ~7 top menus) · 227 distinct custom dialogs + 376 native + 7 web-form. Companion apps Cast / Studio / Converter / Beacon, the Media Player, and the editor-embedded **Podcasts** (`core.podcasts`), **Internet Radio** (`core.radio`), and **Book Library** (`core.library`) features are **gated (dev/admin only)** for 1.0.0 and are verified only for *absence* from public editor surfaces (§G) — do **not** sign them off as public editor features. (The standalone Quill Radio and Quill Weather apps are unaffected and are signed off in full in §C/§D.)

## How to use this pack
Each checklist item is verified on three axes:
- **[ ] Works** — the action does what it says, no error/crash.
- **[ ] Surface-exact** — label, shortcut, and menu path exactly match the reference inventory (`signoff/inventory/`), and the accessible name is correct.
- **[ ] A11y** — keyboard-reachable, focus correct, and the outcome is **announced** (speech + braille), no silent state change.

Run the **entire pass once per environment** in §A. A feature is "signed off" only when it passes on **every applicable environment**.

Files in this pack:
- `QUILL-1.0.0-SIGNOFF.md` — this master (harness + cross-cutting matrices + readiness summary).
- `signoff/SIGNOFF-editor.md` — every editor menu/command/dialog (generated).
- `signoff/SIGNOFF-radio.md` · `signoff/SIGNOFF-weather.md` — the public companion apps.
- `signoff/SIGNOFF-dialogs.md` — every dialog surface (generated from the A11Y-4 registry).
- `signoff/SIGNOFF-install-matrix.md` — the portable/system scenario deep-dive.
- `../release/qa-core-journeys.md` — the hand-held, rigorous **core-journey** test plan (open/heading nav, table cell nav, Save-As fidelity, Insert Equation, Improve Reading Order, Find/Replace + Regex, Read Aloud, open-from-URL). A required companion (see §0).
- `../release/qa-samples/` — the **QA sample-document corpus** the journeys open (known-content inputs for manual QA); manifest in `../release/qa-samples/README.md`.

---

## §0. How to run this sign-off — the hand-held procedure

This pack is more than a checklist: it is an **ordered process**. Run it in the
sequence below, on every §A environment. Do not treat the companion QA plans as
optional reading — they are part of the pass and are listed here as **mandatory**.

### Prerequisites
- A **real Windows build** of the 1.0.0 candidate, installed per the §A environment
  under test (portable and system installs are different runs — see §A).
- **NVDA and JAWS** both installed and speaking (Narrator and, on E5, VoiceOver
  where a case calls for them).
- **Mouse unplugged** for the first pass of every UI step — keyboard-only — then a
  second pass reading with the screen reader's review/virtual cursor.
- The **`qa-samples/` corpus** copied onto the machine (`../release/qa-samples/`);
  read its `README.md` so the "correct" content of each sample is known before you
  start. AI configured with a working provider **only** for the Improve Reading
  Order journey.

### The ordered run
1. **Install / environment** — set up the machine for the §A environment under
   test (E1–E6); record data-dir, secrets backend, and update path. Re-run the
   whole pack once per environment.
2. **Smoke-launch** — launch the build; confirm the window is announced on
   foreground, no crash dialog, and Help > About reads the 1.0.0 candidate version
   and build stamp. A failed smoke-launch stops the run for that environment.
3. **Per-area checklists §B–§D** — work the editor (§B, `signoff/SIGNOFF-editor.md`),
   Quill Radio (§C, `signoff/SIGNOFF-radio.md`), and Quill Weather (§D,
   `signoff/SIGNOFF-weather.md`), triple-checking every applicable item
   (Works · Surface-exact · A11y).
4. **Required companion QA plans (MANDATORY — not optional)** — run each of these
   in full and sign off its footer:
   - `../release/qa-core-journeys.md` — the hand-held core-journey plan, opened
     against the `qa-samples/` corpus (heading nav, table cell nav, Save-As
     fidelity, Insert Equation, Improve Reading Order, Find/Replace + Regex, Read
     Aloud, open-from-URL).
   - `../release/screen-reader-test-plan.md` — every accessibility/focus/keyboard
     case.
   - `../release/user-acceptance-test-plan-0.8.0.md` — the continuous 236-step UAT
     runbook (feature coverage end to end).
   - `../release/fresh-install-regression-0.8.0.md` — brand-new-user install.
   - `../release/upgrade-path-regression-0.8.0.md` — install-on-top upgrade chain,
     no data loss.
5. **§G gated-absence** — with the public build flag OFF, confirm the gated apps
   and editor-embedded Podcasts / Internet Radio / Book Library are **absent** from
   every public surface (the `Tools ▸ Media` submenu omitted entirely, no palette
   commands, no status-bar/tray cells).
6. **Readiness gate** — fill §H; the candidate is ready to test only when every box
   in §A–§G is checked on every environment **and** every companion plan above is
   signed off.

### Definition of done
A feature is signed off only when **every applicable checklist box is
triple-checked (Works · Surface-exact · A11y) on every §A environment (E1–E6)**,
**and** every required companion plan in step 4 is signed off, **with the
`qa-samples/` corpus used for the feature journeys**. Confidence comes from
following the steps + expected results + named sample inputs — not from memory or a
glance. A box is checked only when the outcome happened in front of you, announced
out loud, on the build under test.

---

## §A. Environment matrix — run the whole pack in EACH

Because install-mode behavior is governed by **three independent "portable" signals that can disagree** (data-dir, secrets/`QUILL_PORTABLE`, update-asset), each must be exercised, per OS.

| # | Environment | Data dir | Secrets backend | Update path | Must run |
|---|---|---|---|---|---|
| E1 | **Windows — system install** (Inno, no `data/`) | `%APPDATA%\Quill` | Windows Credential Manager | installer `setup.exe` | ✅ |
| E2 | **Windows — portable ZIP** (`data/` beside exe, `QUILL_PORTABLE=1`) | `<app>\data` | DPAPI `keys.enc` (`quill-portable-keys-v1`) | portable `.zip` robocopy | ✅ |
| E3 | **Windows — installed but ships `data/`** (the split-signal case, #1100) | resolves per `storage-mode.json` | **DPAPI `keys.enc`** even if data is `%APPDATA%` | installer (via `unins000` marker) | ✅ |
| E4 | **Windows — custom data location** (`Settings ▸ data location`) | user-chosen path | per `QUILL_PORTABLE` | per detection | ✅ |
| E5 | **macOS — app bundle** | `~/.quill` (or chosen) | login **Keychain** (no portable single-folder store — expect the one-time warning) | `.dmg`/`.pkg` | ✅ |
| E6 | **Safe Mode** (`QUILL_SAFE_MODE=1`, both portable + system) | as above | as above | n/a | ✅ (network/AI/plugins off) |

- [ ] E1 pass complete  [ ] E2  [ ] E3  [ ] E4  [ ] E5  [ ] E6
- [ ] **Cross-signal check:** in E3, confirm `keys.enc` lands where product intent expects (it follows the *resolved data dir*, so an appdata data-dir + `QUILL_PORTABLE=1` writes `%APPDATA%\Quill\keys.enc`). Record actual vs. intended.

Full per-scenario cases: **`signoff/SIGNOFF-install-matrix.md`**.

---

## §B. Editor — feature/command/surface sign-off
Every editor menu (File · Edit · View · Insert · Format · Navigate · Search · Tools · AI · [ADP] · Window · QuillVille · Help) with each leaf item and dialog. See **`signoff/SIGNOFF-editor.md`** (generated from the command registry + menu tree + dialog registry). Section is complete when every item there is triple-checked across §A environments.

## §C. Quill Radio (public) — sign-off
Station · Playback · [Record] · [Weather] · [ADP] · View · QuillVille · Quillins · Help. Every item + all 15 Radio custom dialogs (+21 native). See **`signoff/SIGNOFF-radio.md`**. Include: playback survives dropped connection, scheduled recording fires, favorites order preserved, backup/restore round-trip, autostart, missed-recording report.

## §D. Quill Weather (public) — sign-off
File · Weather · Options · [ADP] · QuillVille · Help. Every item + WeatherCenter/AddLocation/Settings dialogs. See **`signoff/SIGNOFF-weather.md`**. Include: background Scheduled-Task alert check (no process running), severe-weather poll tightening, alert sounder options, Test Alert, "already-told-you" dedupe across live + background.

## §E. Dialogs — every surface
All 227 custom + 376 native + 7 web-form dialogs, grouped by area, each verified: opens, keyboard-complete, accessible name/role, Escape/Close contract, announces its outcome. See **`signoff/SIGNOFF-dialogs.md`** (generated).

---

## §F. Cross-cutting — accessibility (applies to every item above)
- [ ] Every focusable control has an accessible **name** (audited by `accessible_name_audit`).
- [ ] Every dialog honors the **Escape/Close** contract (`apply_modal_ids`) and is registered in the A11Y-4 dialog inventory.
- [ ] Every user-visible outcome is **announced** (GATE-12 announce-gap); no silent state changes.
- [ ] Menu items expose correct **mnemonics + shortcuts**; no mnemonic collisions introduced.
- [ ] Braille output routes for announcements across Editor + Radio + Cast (the #1283 path).
- [ ] Screen readers verified: **NVDA, JAWS, Narrator** (Windows) and **VoiceOver** (macOS).

## §G. Gating verification — non-public apps MUST be absent from public surfaces
With the release/dev flag OFF (default public build), confirm these are **not reachable**:
- [ ] **QuillVille menu** lists only Open QUILL / Quill Radio / Quill Weather (Cast, Studio, Converter, Beacon hidden — `RELEASED_APPS`).
- [ ] **Tools ▸ Media ▸ Media Player** (`app.open_media_player`) is hidden/gated.
- [ ] The **standalone Audio Studio** launcher (QuillVille) is gated. *(Note: `Tools ▸ Speech ▸ Audiobook & Batch Speech…` / `tools.speech_batch_export` is the editor-embedded batch document-to-speech wizard, NOT the standalone app — it stays. It was relabelled from "Audio Studio…" to remove the name clash.)*
- [ ] **Quill Cast / Converter / Beacon** launchers, command-palette commands, Explorer "Convert with Quill" shell verb, and build products are gated.
- [ ] Command palette does not surface gated-app commands.
- [ ] **Podcasts (`core.podcasts`)** is absent from the editor: no `Tools ▸ Media ▸ Podcasts` items, no `podcasts.*` commands in the command palette, no Podcasts status-bar cell or tray section, no Podcasts entries in `Tools ▸ Global Hotkeys`, no Podcasts chords on the QUILL-key cheat sheet, and no Podcasts row in `Manage Individual Features`. The background new-episode check never runs. (`QUILL_DEV_BUILD=1` restores all of it.)
- [ ] **Internet Radio (`core.radio`)** and **Book Library (`core.library`)** are absent from the editor: no `Tools ▸ Media ▸ Internet Radio` or `Tools ▸ Media ▸ Book Library` items, no `radio.*`/`library.*` commands in the command palette, no Radio status-bar mini-player or tray radio controls, and no Book Library entries anywhere. With Radio, Podcasts, and Book Library all gated, the **`Tools ▸ Media` submenu is omitted entirely** in a public build — confirm it is not shown. (`QUILL_DEV_BUILD=1` restores all of it.) The **standalone Quill Radio and Quill Weather apps are unaffected** and remain launchable via the QuillVille switcher (see the check above).
- [ ] Automated test asserts gated apps are absent from public surfaces when the flag is off (Phase 2 deliverable).

Already-gated (verify still correct): Podcasts (`core.podcasts`, unreleased in public builds — see above), ADP (`future.adp_assistant`, default ON — decide for 1.0), Publishing send half (`future.publishing`), Spotify (`future.spotify`), GLOW (`core.glow`), BITS Whisperer (`core.bw_whisperer`), third-party Quillins (locked; bundled load regardless).

---

## §H. Readiness summary (fill as sections complete)
| Area | Items | Signed off (E1–E6) |
|---|---|---|
| Editor (§B) | ~500 menu + 179 dialogs | ☐ |
| Radio (§C) | ~10 menus + 15 dialogs | ☐ |
| Weather (§D) | ~7 menus + 3 dialogs | ☐ |
| Dialogs (§E) | 227 custom + 376 native + 7 web | ☐ |
| Accessibility (§F) | cross-cutting | ☐ |
| Gating (§G) | non-public absent | ☐ |
| Install matrix | E1–E6 all scenarios | ☐ |

**1.0.0 is ready to test when every box in §A–§G is checked and this table is all ✅.**
