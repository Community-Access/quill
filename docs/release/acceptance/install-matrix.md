# Section — Install matrix (portable vs system, secrets, updates, migration)

This section proves QUILL behaves correctly depending on **how it was installed**.
It is a little more technical than the rest of the book because you will check
**where files land on disk** — but every step still tells you exactly what to open
and what you should find. If a term is new, that is fine; follow the path given.

**Why this matters most for secrets.** Install mode is decided by **three
independent signals that can disagree**: (1) the **data directory**, (2) the
**secrets backend** (`QUILL_PORTABLE`), and (3) the **update asset**. The riskiest
one is secrets — an API key or token must land in the *right* protected store and
never in plain text. Run this section carefully.

**Environments (run the whole book once per environment).**

| # | Environment | Data dir | Secrets backend | Update path |
|---|---|---|---|---|
| E1 | Windows system install (Inno, no `data/`) | `%APPDATA%\Quill` | Windows Credential Manager | installer `setup.exe` |
| E2 | Windows portable ZIP (`data/` beside exe, `QUILL_PORTABLE=1`) | `<app>\data` | DPAPI `keys.enc` (`quill-portable-keys-v1`) | portable `.zip` |
| E3 | Installed but ships `data/` (split-signal, #1100) | per `storage-mode.json` | **DPAPI `keys.enc`** even if data is `%APPDATA%` | installer (via `unins000` marker) |
| E4 | Custom data location (chosen in Settings) | user path | per `QUILL_PORTABLE` | per detection |
| E5 | macOS bundle | `~/.quill` (or chosen) | login **Keychain** | `.dmg`/`.pkg` |
| E6 | Safe Mode (`QUILL_SAFE_MODE=1`, both modes) | as above | as above | n/a |

Run each scenario for **QUILL editor, Quill Radio, and Quill Weather**. Read §2–§3
of `README.md` for the box layout. Mark **N/A** for environment lines that do not
apply to the machine you are on, and record which E-number this run is.

> **Landmine to watch (from the code).** `is_portable_mode()` reads only
> `QUILL_PORTABLE`, which the launcher sets whenever a `data/` folder exists beside
> the executable. So a build that *ships* a `data/` folder writes DPAPI `keys.enc`
> even if the user picked appdata storage. Verify this matches product intent
> before sign-off — it is the crux of INST-03.

---

## INST-01 — Data and settings land in the right folder

*What & why.* Prove the document data, settings, logs, backups, and autosave all
resolve to the folder the install mode intends.

**Before you start**
- QUILL installed for the environment under test. Know the expected data dir from
  the table above.

**Do this**
1. Launch QUILL, change one setting (e.g. toggle a view option), and create + save a
   throwaway document so backups/autosave have something to write.
2. Open File Explorer (Windows) or Finder (macOS) and go to the **expected data
   dir** for this environment (e.g. `%APPDATA%\Quill` for E1, `<app>\data` for E2).
3. Confirm `settings.json` and the `logs`, `diagnostics`, `backups`, `autosave`,
   and `sessions` subfolders exist there.

**You should see and hear**
- E1: everything under `%APPDATA%\Quill`; **nothing** QUILL-owned appears beside the
  exe. E2: everything under `<app>\data`; **nothing** under `%APPDATA%`. E4: your
  chosen path is used. E5: `~/.quill` (or chosen) with `storage-mode.json` inside.
  `ensure_app_directories` created all the subfolders in the resolved dir.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## INST-02 — Secrets go to the correct protected store (never plain text)

*What & why.* The highest-risk check: an API key/token must be stored in the
platform's protected store for this mode, and never written in the clear.

**Before you start**
- QUILL open. A throwaway secret to enter — e.g. add an AI provider key in the AI
  Hub, or connect a GitHub account (use a disposable token).

**Do this**
1. Enter the secret through its normal UI and confirm it saves.
2. E1 (Windows, not portable): open **Credential Manager ▸ Windows Credentials** and
   find the QUILL entry. E2 (Windows portable): find **`keys.enc`** in the resolved
   data dir. E5 (macOS): open **Keychain Access** and find the login-keychain entry.
3. Search the data dir, `logs`, `diagnostics`, and any crash bundle for the raw
   secret string.

**You should see and hear**
- The secret is in the **expected store** for the mode (Credential Manager / DPAPI
  `keys.enc` / Keychain) and appears **nowhere in plain text** in settings, logs,
  diagnostics, or crash bundles (redaction, SEC-13). Signing out of the service
  removes only that service's entry.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## INST-03 — The split-signal case (E3): keystore follows the resolved data dir

*What & why.* When `QUILL_PORTABLE=1` but the data dir is `%APPDATA%`, the keystore
must follow the **resolved data dir**, not the user's abstract choice. This is the
#1100 landmine.

**Before you start**
- An E3 build (installed, but ships a `data/` folder beside the exe). A throwaway
  secret.

**Do this**
1. Launch, enter a secret (as in INST-02).
2. Confirm where `keys.enc` was written.

**You should see and hear**
- `keys.enc` lands in **`%APPDATA%\Quill\keys.enc`** (it follows the resolved data
  dir). **Record actual vs. intended** — the backend is chosen by bundle layout, not
  the storage choice. Flag any mismatch with product intent as a release blocker.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## INST-04 — Environment-variable key override wins and is never persisted

*What & why.* A `QUILL_<KEY>_KEY` env override must take precedence and must not be
written into any store.

**Before you start**
- Set an env override for a key you also have stored (e.g. `QUILL_OPENAI_KEY`), then
  launch QUILL.

**Do this**
1. Use the feature that consumes that key.
2. Inspect the secret store afterward.

**You should see and hear**
- The env value is used in every mode; the stored value is **not** overwritten and
  the env value is **not** persisted into the store.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## INST-05 — Updates offer the right asset for the mode

*What & why.* An installed build must update via the installer; a portable build via
the portable zip (preserving `data/`).

**Before you start**
- The build under test with update checking available (network + a reachable update
  source). If offline, mark **Blocked**.

**Do this**
1. Run **Help ▸ Check for Updates…**.
2. Read what update asset is offered and, if safe in your test setup, apply it and
   let QUILL relaunch.

**You should see and hear**
- E1/E3: offered the **platform installer** (`.exe`/`.msi`; macOS `.dmg`/`.pkg`),
  applied via elevated silent setup then relaunch. E2: offered the **portable
  `.zip`** (name contains "portable"), applied via mirror-copy that **excludes
  `data/`**, then relaunch — your documents/settings survive. E3 (#1100):
  `running_portable()` returns False (the `unins000` marker), so it gets the
  installer, not the zip. Discovery is HTTPS-only, host-allowlisted, and
  signed-manifest verified in every mode. A dev/non-frozen run falls back to "reveal
  download" instead of applying (no crash).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## INST-06 — First run, migration, and importing prior data

*What & why.* A brand-new user gets the Startup Wizard; an existing user's data is
migrated safely with backups.

**Before you start**
- For the fresh-install path: a machine/profile with no prior QUILL data. For the
  import path: a populated prior data location available.

**Do this**
1. Launch a fresh install and confirm the **Startup Wizard** appears.
2. On a fresh data dir with a populated prior location present, accept the offer to
   **import prior data**.
3. Inspect the data dir for a `migration-backups/` folder after a settings-schema
   migration (e.g. upgrading over an older build).

**You should see and hear**
- Fresh install triggers the nine-page **Startup Wizard** (the `quill-new-install.txt`
  marker is consumed). Import brings over documents/settings but **not** the
  location-control files. Schema migration backs up the old settings to
  `<data>/migration-backups/` before rewriting; corrupt settings are **quarantined,
  not lost**. The backup dir follows the resolved data dir in every mode.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## INST-07 — Safe Mode is identical in portable and system

*What & why.* Safe Mode must disable the same things regardless of install mode.

**Before you start**
- Relaunch with **`QUILL_SAFE_MODE=1`** (or `--safe-mode`), once portable, once
  system.

**Do this**
1. Confirm plugins, AI, network, restore, indexing, watchers, themes, and snippets
   are disabled.
2. Confirm Radio and Weather network features refuse in Safe Mode.
3. Separately, set `QUILL_VERBOSITY_SAFE_MODE=1` and confirm custom verbosity is
   ignored.

**You should see and hear**
- The same features are off in both install modes; Safe Mode is announced/obvious;
  Radio/Weather network calls refuse cleanly; verbosity Safe Mode ignores custom
  verbosity — all mode-independent.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## INST-08 — Portable-only behaviors (self-containment and moving the stick)

*What & why.* A true portable copy keeps everything inside its folder and survives
being moved — with one documented exception for machine-bound secrets.

**Before you start**
- An E2 portable copy on a writable medium; optionally a second machine/drive and a
  read-only/USB medium.

**Do this**
1. Confirm data, settings, secrets, and logs all stay **inside the app folder**
   (all three signals agree).
2. Move the whole folder to another machine/drive and launch.
3. Put the folder on a read-only/USB medium and launch.

**You should see and hear**
- E2 keeps everything inside the folder. After a move, DPAPI `keys.enc` is
  **machine/account-bound**, so stored keys do not transfer — QUILL prompts for
  re-entry (documented), no crash. On read-only media, `storage-mode.json` falls
  back to the appdata path gracefully.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## INST-09 — Per-app pass for Radio and Weather

*What & why.* The companion apps decide their own install mode and must place their
data correctly.

**Before you start**
- Quill Radio and Quill Weather installed for the environment under test.

**Do this**
1. **Radio:** confirm the data/settings/secrets/update verdict is correct for E1–E5;
   stations and recordings land in the right place; a `.qrbackup` restore works in
   both portable and system.
2. **Weather:** confirm data/settings/update verdict; the **background Scheduled
   Task** registers per-user and fires in both install modes; the alert-dedupe store
   follows the data dir.

**You should see and hear**
- Each app resolves its own portable/installed verdict (a bare `unins000`-beside-exe
  check plus `prefer_portable`); files land in the right place; Radio backup/restore
  round-trips; Weather's Scheduled Task fires and dedupe persists — all correct in
  both modes.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

### Section sign-off
- Tester:
- Screen reader(s) + version(s):
- Build / commit tested:
- Environment (E1–E6):
- Date:
- Scenarios passed / total: ___ / 9
- Release blockers found (must be zero to ship):
- Result: Pass / Pass-with-notes / Fail
- Notes:
