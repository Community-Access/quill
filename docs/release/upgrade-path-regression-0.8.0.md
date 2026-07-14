# QUILL 0.8.0 Beta 1 - Upgrade-Path Regression Test Plan

Goal: validate that a user on an older QUILL release can install newer releases
**on top** without losing data, ending up with a broken/duplicated install, or
hitting a crash on first launch. This is the companion to
`fresh-install-regression-0.8.0.md`, which covers the brand-new-user case.

The upgrade chain under test (oldest to newest):

1. **0.5.0** -> `installers/Quill-Setup-0.5.0.exe`
2. **0.7.0 Beta 1** -> `installers/Quill-for-All-Setup-0.7.0.Beta.1.exe`
3. **0.8.0 Beta 1** -> `installers/Quill-for-All-Setup-0.8.0 Beta 1.exe`

(0.6.0 has no separate Windows installer asset published; the 0.5.0 -> 0.7.0
step exercises the same branding/layout transition that 0.6.0 sat inside.)

All three are per-user installs by default (`PrivilegesRequired=lowest`).

## Test principle: launch and run EACH version - do not chain installers

You must **install -> launch -> use -> close each version in turn**, in order,
before installing the next one. Do not run the three installers back-to-back.

The reason is that QUILL's upgrade logic runs *in the app at launch*, not in the
installer:

- Settings are persisted as a **versioned document**
  (`schema_version`, currently `1`, written by
  `quill/core/settings_migration.py`). The legacy flat settings file is only
  rewritten into the nested/versioned shape when a version that understands it
  actually loads it.
- Field-level migrations fire on read, e.g. the retired `pyttsx3` read-aloud
  engine id -> `sapi5`, and the dictation engine `vosk`/`whisper` -> `offline`
  (#617). These only execute when that version's code runs.
- A pending **data-location move** is applied very early in
  `quill.__main__.main()` on the next launch, not by the installer.

If you skip launching an intermediate version, its state files are never
created and its migration gate never runs - so a later version migrates from
the wrong starting point and the test proves nothing. Each version must write
its files and hand a correctly-migrated state to the next.

At every step, before moving on, confirm the expected files actually exist on
disk under `%APPDATA%\Quill` (not just that the app opened).

## Where the installers live

The three installers are staged locally under
`docs/release/upgrade-test/installers/`. That folder is gitignored (the `.exe`
files are large release binaries and are not committed). To re-fetch them:

```powershell
cd docs\release\upgrade-test\installers
gh release download v0.5.0          --pattern "Quill-Setup-0.5.0.exe" --clobber
gh release download v0.7.0-beta.1   --pattern "Quill-for-All-Setup-0.7.0.Beta.1.exe" --clobber
# 0.8.0 is not yet published; copy the locally built installer:
copy "..\..\..\..\windows-distribution-0.8.0\installer\Output\Quill-for-All-Setup-0.8.0 Beta 1.exe" .
```

## Why this test matters - the branding/AppId transition

This is the specific risk the chain is designed to surface:

- **0.5.0** ships as AppName `Quill`, so it installs to
  `%LOCALAPPDATA%\Programs\Quill` and its Start Menu group is `Quill`.
- **0.7.0 / 0.8.0** ship as AppName `QUILL for All`, default dir
  `%LOCALAPPDATA%\Programs\QUILL for All`, Start Menu group `QUILL for All`.
- **All three share the same Inno Setup `AppId`**
  (`{6E0A1C52-4A90-4C6E-A8A1-3C2A16E2B7F2}`). Inno identifies a product by
  `AppId`, not by name - so the newer installer should recognize the prior
  install and **upgrade in place into the existing `Quill` folder**, rather
  than dropping a second `QUILL for All` folder beside it.

The two failure modes to watch for at the 0.5.0 -> 0.7.0 step:

- **Side-by-side duplication:** both `Programs\Quill` and
  `Programs\QUILL for All` end up present. Result: two Start Menu entries, two
  Add/Remove Programs entries, ambiguous launcher.
- **Orphaned shortcuts:** the old `Quill` Start Menu group / desktop shortcut
  survives but points at a path the upgrade removed or replaced.

User data lives in `%APPDATA%\Quill` for every version, so settings/keymap/
recovery should carry across all three upgrades untouched. Confirming that is
the other half of this test.

## 0. Reset to a clean machine first

An upgrade test is only meaningful starting from nothing - otherwise leftover
state from a prior run hides regressions. Use the cleanup script, which now
removes BOTH branding folders (`Quill` and `QUILL for All`), the elevated
Program Files variants, and the data dirs:

```powershell
# from docs\release
.\clean-quill-install.ps1 -Backup    # backs up %APPDATA%\Quill to Desktop first
```

Verify clean before starting:

```powershell
Test-Path "$env:LOCALAPPDATA\Programs\Quill"            # expect False
Test-Path "$env:LOCALAPPDATA\Programs\QUILL for All"    # expect False
Test-Path "$env:APPDATA\Quill"                          # expect False
Test-Path "$env:LOCALAPPDATA\Quill"                     # expect False
```

For the truest result, run the whole chain on a real machine with your screen
reader. Windows Sandbox is clean but has no screen reader and does not persist
state between launches, which defeats an upgrade test.

## 1. Install the baseline (0.5.0)

1. Run `installers\Quill-Setup-0.5.0.exe`, accept defaults (per-user).
2. Confirm install dir is `%LOCALAPPDATA%\Programs\Quill` and the Start Menu
   group is `Quill`.
3. Launch QUILL. Confirm About reports `0.5.0`.
4. **Seed user data so the upgrade has something to preserve:**
   - [ ] Create and save a document (note its path and contents).
   - [ ] Change at least one visible setting (e.g. a speech voice or a
         verbosity level).
   - [ ] Remap one key in the Keymap Editor.
   - [ ] Note the contents of `%APPDATA%\Quill` (settings.json, keymap, etc.).
5. **Confirm 0.5.0 actually wrote its state before continuing** (this is the
   gate the chain depends on):
   ```powershell
   Test-Path "$env:APPDATA\Quill\settings.json"   # expect True
   Get-ChildItem "$env:APPDATA\Quill"             # settings, keymap, recovery, etc.
   ```
   If these do not exist, the app did not run far enough - stop and fix before
   upgrading, or the migration test below is meaningless.
6. Close QUILL fully (check Task Manager for `quill.exe` / `pythonw.exe`).

Record a snapshot for later comparison:

```powershell
Get-ChildItem "$env:APPDATA\Quill" -Recurse | Select-Object FullName,Length |
  Sort-Object FullName | Format-Table -Auto
```

## 2. Upgrade 0.5.0 -> 0.7.0 Beta 1 (the critical step)

1. Run `installers\Quill-for-All-Setup-0.7.0.Beta.1.exe` **without uninstalling
   0.5.0 first**.
2. Watch the install dir the installer proposes/uses.

Checks:

- [ ] Installer recognizes the prior install (same AppId) and upgrades in
      place - it does NOT prompt as a brand-new install into a fresh dir.
- [ ] **Exactly one** install dir exists afterward. Record which:
      ```powershell
      Test-Path "$env:LOCALAPPDATA\Programs\Quill"          # in-place upgrade -> True
      Test-Path "$env:LOCALAPPDATA\Programs\QUILL for All"  # relocated/new -> True
      ```
      One of these must be True and the **other False**. Both True = the
      side-by-side duplication bug; file it.
- [ ] **Exactly one** Add/Remove Programs entry for QUILL (Settings -> Apps).
- [ ] Start Menu has one usable QUILL entry; no dead `Quill` shortcut left
      pointing at a removed path.
- [ ] Launch QUILL. About reports `0.7.0 Beta 1`.
- [ ] First launch does not show the first-run setup wizard (this is an
      existing user - `setup_wizard_completed` survived).
- [ ] The document saved under 0.5.0 still opens with identical contents.
- [ ] The setting changed under 0.5.0 is still in effect.
- [ ] The remapped key from 0.5.0 still works.
- [ ] `%APPDATA%\Quill` was migrated/preserved (no reset to defaults; diff
      against the step-1 snapshot - additive changes are fine, data loss is not).
- [ ] **Settings migration ran:** after this launch, `settings.json` carries the
      nested/versioned shape (`schema_version: 1`, a `groups` object), not the
      old flat 0.5.0 layout:
      ```powershell
      (Get-Content "$env:APPDATA\Quill\settings.json" -Raw) -match '"schema_version"'
      ```
- [ ] Any retired ids migrated rather than breaking: a `pyttsx3` read-aloud
      engine becomes `sapi5`; a `vosk`/`whisper` dictation engine becomes
      `offline` (#617). Verify the corresponding Preferences controls still show
      a valid selection (no blank/error state).
- [ ] Screen reader announces the window on foreground; no crash dialog.

Close QUILL fully before the next step. Re-run the snapshot command from step 1
so you have a 0.7.0 baseline to diff against after the 0.8.0 upgrade.

## 3. Upgrade 0.7.0 -> 0.8.0 Beta 1

1. Run `installers\Quill-for-All-Setup-0.8.0 Beta 1.exe` over the 0.7.0 install.

Checks:

- [ ] In-place upgrade into the same dir as 0.7.0; still exactly one install
      dir, one Add/Remove entry, one Start Menu group.
- [ ] About reports `0.8.0 Beta 1` and the build stamp.
- [ ] No first-run wizard; existing user state intact.
- [ ] Document, setting, and keymap from earlier steps all still present.
- [ ] `settings.json` still loads cleanly (`schema_version` present and at the
      version 0.8.0 expects; no reset to defaults). Diff against the 0.7.0
      snapshot - additive only, no data loss.
- [ ] No data-location migration error notice surfaces on launch (that path is
      applied early in `quill.__main__.main()`); if one appears, capture it.
- [ ] Help -> Check for Updates does NOT advertise a newer version (the 0.8.0
      feed is intentionally left on the prior release for this beta).
- [ ] Screen reader announces on foreground; no crash dialog.

## 4. Post-upgrade feature smoke (on the upgraded install)

Confirm the upgraded install is fully functional, not just launchable. Bundled
dependencies should all be present from the 0.8.0 layout (same checklist as the
fresh-install plan, section 4):

- [ ] New document, type, save (atomic write), reopen.
- [ ] Import a `.docx` and a `.md`; export to `.docx`, `.md`, and DAISY
      (File -> Export -> DAISY Talking Book).
- [ ] Speech: eSpeak-NG and DECtalk each speak a line.
- [ ] Dictation: F9 hold-to-dictate inserts text as one undoable edit (after
      the Whisper model downloads).
- [ ] Braille Mode toggles and translates.
- [ ] Keymap Editor opens; remap a key; no conflict warnings on save.
- [ ] About QUILL notebook tabs navigate by keyboard.
- [ ] AI gated off under `--safe-mode`, on otherwise.
- [ ] A bundled Quillin loads; Safe Mode disables contributions.

## 5. Clean-uninstall after upgrade

- [ ] Uninstall via Add/Remove Programs.
- [ ] Install dir is removed (whichever one the chain ended on).
- [ ] No second/orphaned QUILL entry remains in Add/Remove Programs.
- [ ] `%APPDATA%\Quill` is intentionally left behind (matches fresh-install
      behavior - data is preserved across uninstall).
- [ ] No dead Start Menu shortcut under either `Quill` or `QUILL for All`.

## 6. Record results

For each failure capture: the upgrade step (e.g. "0.5.0 -> 0.7.0"), expected vs
actual, the install-dir / Add-Remove / Start-Menu state, the screen-reader
announcement (or silence), any data that was lost, and the crash-bundle path if
one was produced. File issues against the 0.8.0 Beta 1 milestone and tag them
`upgrade-path`.
