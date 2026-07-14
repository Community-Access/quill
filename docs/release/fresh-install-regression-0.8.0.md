# QUILL 0.8.0 Beta 1 - Fresh-Install Regression Test Plan

Goal: validate the 0.8.0 Beta 1 installer exactly as a brand-new user would
experience it, with no state carried over from any prior QUILL install on the
machine. Also confirm that all bundled dependencies and features are present.

The installer under test:
`windows-distribution-0.8.0/installer/Quill-for-All-Setup-0.8.0 Beta 1.exe`

This build is a per-user install (no admin required).

- Install dir: `%LOCALAPPDATA%\Programs\QUILL for All`
- User data dir: `%APPDATA%\Quill`
- Start Menu group: `QUILL for All`

The update feed (`docs/site/updates/.quill-update-feed-v1.json`) was deliberately
left pointing at the prior release, so a freshly installed 0.8.0 build will NOT
advertise an update to itself. That is expected for this beta.

## 1. Get to a truly clean machine

Pick ONE of the two approaches. Approach A is the most trustworthy.

### A. Windows Sandbox (recommended - guarantees "never installed")

Windows Sandbox is a disposable, clean Windows instance. Nothing from your
current machine is present, so it is the truest test of a first-time install.

1. Enable it once: Start -> "Turn Windows features on or off" -> check
   "Windows Sandbox" -> reboot. (Requires Windows Pro/Enterprise and
   virtualization enabled in BIOS.)
2. Launch "Windows Sandbox" from the Start menu.
3. Copy `Quill-for-All-Setup-0.8.0 Beta 1.exe` into the sandbox (drag-drop or
   shared folder).
4. Run the installer inside the sandbox.
5. When you close the sandbox, all state is destroyed - so each launch is a
   fresh machine. Great for repeating the test.

Note: a sandbox has no screen reader installed. To exercise the screen-reader
announcements, use Approach B on a real machine with JAWS/NVDA, or install NVDA
portable inside the sandbox.

### B. Clean your current machine (manual reset)

Use this on your real machine (with your screen reader) but reset all QUILL
state first so it behaves as a first install.

1. Uninstall any existing QUILL:
   - Settings -> Apps -> Installed apps -> "QUILL for All" -> Uninstall, or run
     the uninstaller in `%LOCALAPPDATA%\Programs\QUILL for All`.
2. Close QUILL completely (check Task Manager for `quill.exe` / `pythonw.exe`).
3. Delete leftover folders if present (the uninstaller usually removes the
   first; the data dir is intentionally left behind on uninstall):
   - `%LOCALAPPDATA%\Programs\QUILL for All`  (install dir)
   - `%APPDATA%\Quill`                         (settings, keymap, recovery, AI)
   - `%LOCALAPPDATA%\Quill`                    (caches, if present)
4. Confirm no Start Menu shortcut remains under "QUILL for All".

Or just run the cleanup script in this folder, which stops QUILL, runs the
uninstaller, removes both data dirs, and verifies the machine is clean:

```powershell
# from docs\release
.\clean-quill-install.ps1            # prompts before deleting
.\clean-quill-install.ps1 -Backup    # copy settings to Desktop first
.\clean-quill-install.ps1 -Force     # no prompt
```

PowerShell to verify nothing is left (run before installing):

```powershell
Test-Path "$env:LOCALAPPDATA\Programs\QUILL for All"   # expect False
Test-Path "$env:APPDATA\Quill"                          # expect False
Test-Path "$env:LOCALAPPDATA\Quill"                     # expect False
```

Important: back up `%APPDATA%\Quill` first if you have real projects/settings
you want to keep - deleting it is what makes the test a true fresh install.

## 2. Install

1. Run `Quill-for-All-Setup-0.8.0 Beta 1.exe`.
2. Confirm the installer title/version reads "QUILL for All 0.8.0 Beta 1".
3. Accept defaults (per-user, all components) unless you are specifically
   testing component selection.
4. Finish and launch QUILL from the Start menu shortcut.

## 3. First-run / fresh-state checks

- [ ] First-run setup wizard appears (fresh install has no
      `setup_wizard_completed` flag).
- [ ] App launches with no crash dialog; screen reader announces the window on
      foreground (the post-show idle fix).
- [ ] About QUILL (Help menu) shows "0.8.0 Beta 1" and the build stamp.
- [ ] Help -> Check for Updates does NOT report a newer version (feed left on
      prior release on purpose).
- [ ] Settings, keymap, and recovery files get created under `%APPDATA%\Quill`.

## 4. Bundled dependencies and features present

Verify these are present in the install dir without any extra download:

- [ ] Embedded Python runtime: `%LOCALAPPDATA%\Programs\QUILL for All\python\`
- [ ] wxPython UI loads (the app window is itself proof).
- [ ] Pandoc: `...\portable\tools\pandoc\pandoc.exe` (import/export formats).
- [ ] eSpeak-NG: `...\tools\speech\espeak-ng\espeak-ng.exe`.
- [ ] DECtalk: `...\tools\speech\dectalk\speak.exe`.
- [ ] Piper TTS: `...\tools\speech\piper\`.
- [ ] Braille pack: `...\vendor\braille-pack\lou_translate.exe` + `tables\`.
- [ ] Spellcheck, OCR, Kokoro, Vosk wheels installed into embedded Python
      (Tools menu entries enabled; models may download on demand).
- [ ] whisper.cpp offline engine: `...\tools\speech\whispercpp\whisper-cli.exe`
      plus `whisper.dll` and the `ggml*.dll` runtime libraries (the
      "speechwhisper" installer component). Bundled from whisper.cpp v1.9.1
      (CPU build, `whisper-bin-x64.zip`). The Whisper *model* still downloads
      on first use via Tools -> Speech -> Manage Speech Models.

Download-on-demand (models only, by design):

- Whisper, Vosk, and Kokoro model files download on first use. The engine
  binaries/wheels above are bundled; only the large model weights are fetched
  when you first pick a model.

## 5. Core regression pass

Run a quick smoke across the main surfaces:

- [ ] New document, type, save (atomic write), reopen.
- [ ] Open/import a `.docx` and a `.md`; export to `.docx`, `.md`, and DAISY
      (File -> Export -> DAISY Talking Book).
- [ ] Speech: pick eSpeak-NG and DECtalk; speak a line with each.
- [ ] Dictation: F9 hold-to-dictate (after the Whisper model downloads) inserts
      text as one undoable edit; Ctrl+F9 locked session; Escape behaviors.
- [ ] Braille Mode toggles and translates.
- [ ] Keymap Editor opens; remap a key; no conflict warnings on save.
- [ ] About QUILL notebook tabs (3 native ListCtrl tabs) navigate by keyboard.
- [ ] AI features are gated off in Safe Mode (`--safe-mode`) and on otherwise.
- [ ] Quillins: a bundled extension loads; Safe Mode disables contributions.
- [ ] Trigger a non-fatal error and confirm a crash bundle is written with
      secrets redacted.
- [ ] Uninstall cleanly; confirm install dir is removed.

## 6. Record results

For each failure, capture: the step, expected vs actual, the screen-reader
announcement (or silence), and the crash-bundle path if one was produced. File
issues against the 0.8.0 Beta 1 milestone.
