# QUILL 1.0.0 Sign-off — Installation-mode matrix (portable vs system, all scenarios)

Install-mode behavior is governed by **three independent "portable" signals that can disagree**: (1) **data-dir** (`storage_mode.py`/`storage-mode.json`), (2) **secrets** (`QUILL_PORTABLE=1` → DPAPI `keys.enc` vs Credential Manager), (3) **update-asset** (`updates.running_portable()`, subtracts the `unins000` marker). Every scenario below must be run for **QUILL editor, Quill Radio, and Quill Weather**. Legend per box: **[ ]** = verified.

## Environments (run the whole sign-off in each)
- **E1 Windows system install** (Inno, no `data/`) · **E2 Windows portable ZIP** (`data/` beside exe) · **E3 Windows installed-but-ships-`data/`** (split-signal, #1100) · **E4 Windows custom data location** · **E5 macOS bundle** · **E6 Safe Mode** (portable + system).

---

## 1. Data directory & settings location
- [ ] E1 data + `settings.json` resolve to `%APPDATA%\Quill`.
- [ ] E2 data + settings resolve to `<app>\data`; nothing written under `%APPDATA%`.
- [ ] E3 data resolves per `storage-mode.json`; confirm no accidental split (data in appdata while app "feels" portable).
- [ ] E4 custom path honored; `pending-data-location.json` applied on next launch before dirs resolve.
- [ ] E5 data resolves to `~/.quill` (or chosen); `storage-mode.json` under it.
- [ ] `ensure_app_directories` creates logs / diagnostics / backups / autosave / sessions in the resolved dir (all E).

## 2. Credential / API-key & secret storage (the highest-risk axis)
- [ ] E1 (Windows, `QUILL_PORTABLE` unset): secrets in **Windows Credential Manager** (`CRED_PERSIST_LOCAL_MACHINE`); nothing in a `keys.enc`.
- [ ] E2 (Windows, `QUILL_PORTABLE=1`): secrets in **DPAPI `keys.enc`** in the resolved data dir, entropy `quill-portable-keys-v1`, per-key `CryptProtectData`.
- [ ] **E3 split-signal:** with `QUILL_PORTABLE=1` but data in `%APPDATA%`, confirm `keys.enc` lands in `%APPDATA%\Quill\keys.enc` (follows resolved data dir). **Record actual vs product intent** — keystore backend is chosen by bundle layout, not the user's storage choice.
- [ ] Env override `QUILL_<KEY>_KEY` wins in every mode and is never overwritten/persisted.
- [ ] E5 macOS: secrets in **login Keychain** both modes; portable shows the one-time "system-level storage" warning (no silent drop); DPAPI path never taken (raises off-Windows).
- [ ] Linux/other: no secure store — save/load/delete return empty/None/False gracefully (no crash), both modes.
- [ ] Sign-out of a service wipes only that service's namespace; nothing left behind.
- [ ] Redaction: no token/key survives logs, diagnostics, or crash bundle (SEC-13) in any mode.

## 3. Updates
- [ ] E1/E3: offered the **platform installer** (`.exe`/`.msi`; macOS `.dmg`/`.pkg`); applies via elevated silent `setup.exe`, then relaunch.
- [ ] E2: offered the **portable `.zip`** (name contains `portable`); applies via `robocopy /MIR` **excluding `data/`**, then relaunch; zip-slip/bomb guard holds.
- [ ] E3 disambiguation (#1100): `running_portable()` returns **False** for an installed build with `{app}\data` because of the `unins000` marker → gets the installer (not the portable zip).
- [ ] Update discovery is HTTPS-only, trusted-host allowlisted, signed-manifest verified — identical all modes.
- [ ] Dev/non-frozen run: update falls back to "reveal download" (no crash) instead of applying.
- [ ] Companion apps (Radio/Weather) resolve their own portable/installed verdict correctly (they use a bare `unins000`-beside-exe check + `prefer_portable`).

## 4. First-run, migration & import
- [ ] Fresh install triggers the **Startup Wizard** (nine pages); `quill-new-install.txt` marker consumed even if appdata says "done."
- [ ] Change data location: recorded as pending, applied next launch; portable target = `portable_root_dir()`, appdata = `%APPDATA%\Quill`/`~/.quill`, custom = saved path.
- [ ] Import stranded prior-install data: on a fresh data dir, QUILL offers to import a populated prior location (old portable `data/` ↔ appdata); location-control files are **not** carried over.
- [ ] Settings schema migration (delta-based, `schema_version 2`): legacy backed up to `<data>/migration-backups/` before rewrite; corrupt settings quarantined, not lost — backup dir follows the resolved data dir in every mode.

## 5. Safe Mode (install-mode-independent — verify it does NOT differ)
- [ ] `QUILL_SAFE_MODE=1` / `--safe-mode` disables plugins, AI, network, restore, indexing, watchers, themes, snippets — identical in portable and system.
- [ ] Verbosity Safe Mode (`QUILL_VERBOSITY_SAFE_MODE=1`) ignores custom verbosity — mode-independent.
- [ ] Radio and Weather network features all refuse in Safe Mode.

## 6. Portable-specific behaviors
- [ ] Everything (data, settings, secrets, logs) stays inside the app folder **only when all three signals agree** (E2). Document any case where they don't.
- [ ] Moving the portable folder to another machine/drive: DPAPI `keys.enc` is machine/account-bound — confirm the documented re-entry behavior (keys don't transfer), no crash.
- [ ] Portable on a read-only/USB medium: `storage-mode.json` falls back to appdata path gracefully.

## 7. Per-app install-mode pass
- [ ] **Editor:** all of §1–§6.
- [ ] **Quill Radio:** data/settings/secrets/updates verdict correct in E1–E5; stations & recordings land in the right place; `.qrbackup` restore works portable + system.
- [ ] **Quill Weather:** data/settings/updates verdict correct; the **background Scheduled-Task** registers per-user and fires in both install modes; alert dedupe store follows the data dir.

> **Landmine to watch (from code):** `is_portable_mode()` reads only `QUILL_PORTABLE`, which the launcher sets whenever `data/` exists beside the exe — so a build shipping `data/` writes DPAPI `keys.enc` even if the user picked appdata storage. Verify this matches product intent before sign-off.
