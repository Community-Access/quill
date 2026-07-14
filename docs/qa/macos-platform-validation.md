# macOS platform review — status

Status of the macOS platform review. Every item is **fixed in code**; nothing
remains for the dev side to do. What's left is Mac validation, which needs real
hardware — so this file is now a record of what shipped plus the checklist a Mac
tester runs, and the community help ask lives in the 0.9.0-beta2 release notes
(see *A favor to ask Mac users* there).

The dev box is Windows, so every fix was made without Mac hardware: each is
either inert on Windows and exercised by a unit test, or is a platform-branch
edit whose Mac behaviour a tester confirms below.

## Support inbox (Community-Access/support)

| Issue | Title | Status |
|-------|-------|--------|
| [support#67](https://github.com/Community-Access/support/issues/67) | Keyboard shortcuts replace Polish diacritical marks | Fixed in code; routed to the community for Mac validation in the release notes. Close once a comment confirms it. |
| [support#69](https://github.com/Community-Access/support/issues/69) | Disconnected controls/labels in Settings on macOS | Fixed in code; routed to the community for Mac validation in the release notes. Close once a comment confirms it. |
| [support#66](https://github.com/Community-Access/support/issues/66) | "product-feedback" | Out of scope — filed against the Git Going workshop, not QUILL |

#67 and #69 are `OPEN / needs-triage` in the support repo as of 2026-07-10. The
release notes link both and ask Mac users to comment; close as completed once a
comment confirms the fix. No longer an internal dev action item.

---

## Shipped — needs Mac validation

Each entry names the evidence and what a tester checks. Grouped by when it
shipped; earlier-batch rows are already in the CHANGELOG and are listed for
tester reference.

### Shipped this pass (2026-07-10)

| Item | Fix | Evidence | What a Mac tester verifies |
|------|-----|----------|----------------------------|
| #21 / #75 | "macOS (system voice)" wired as a first-class Read Aloud engine (Speech Hub engine option + voice picker + preview, Read Aloud pause/stop, batch export) via the `say` CLI backend (pyobjc voice catalog with `say -v ?` fallback). Off-darwin inert; 10 new unit tests. | `quill/core/read_aloud.py`, `settings.py`/`settings_specs.py`, `speech/{batch_export,document_speech,project_profile}.py`, `ui/{main_frame,batch_speech_runner,voice_browser_dialog}.py` | Voice picker lists system voices; Preview speaks; Read Aloud reads with pause/stop; export-to-file produces audio. |
| #37 | Windows-only UI strings adapt via gettext-wrapped `quill/core/platform_nouns.py`: "Keychain" on darwin (AI Hub, SFTP publish, GitHub sign-in, forget-key, trust-consent); "System dictation"; "In my user profile"; "Cmd+Alt" in help text. Windows strings unchanged. | `quill/core/platform_nouns.py`, `ui/{ai_hub_dialog,audio_studio/publish_dialog,main_frame_github,main_frame,main_frame_speech,setup_wizard_pages,keymap_editor}.py`, `tools/network_egress_audit.py` | API-key/publish/forget-key messages say "Keychain"; dictation status says "System dictation"; wizard says "In my user profile"; help chord says "Cmd+Alt". |
| #2 / #10 | The five remaining `quill.platform.windows.sr_announce` / `announce_engine` import sites now import the platform-neutral shims. The `tts_init_failed` deferred import stays direct so its monkeypatch test keeps working. | `ui/main_frame.py`, `ui/main_frame_intellisense.py`, `ui/main_frame_format_codes.py`, three tests | No behaviour change; macOS announce routing now lives behind a neutral facade. Covered by existing accessibility tests. |
| #6 | Dark Mode read via wx `SystemSettings.GetAppearance().IsDark()`; Increase Contrast detection kept. Dead `is_dark_mode_enabled` / `is_reduce_motion_enabled` / `macos_appearance()` helpers (no UI consumer) deleted. | `quill/platform/macos/high_contrast.py`, `quill/platform/high_contrast.py`, `tests/unit/platform/macos/test_high_contrast_appearance.py` | QUILL's theme follows Dark Mode when toggled in System Settings. |
| #3 / #13 | The dialog-inventory and network-egress gates now tag each discovered site with a `platform` field (`"darwin"` when it sits inside a `sys.platform == "darwin"` branch, `""` otherwise), via a conservative AST guard detector (`quill/tools/platform_guard.py`). The classification snapshot shape is unchanged, so existing consumers are unaffected. The live scan confirms **0** dialog and **0** egress sites are Mac-only today. | `quill/tools/platform_guard.py`, `quill/tools/dialog_inventory.py`, `quill/tools/network_egress_audit.py`, `tests/unit/tools/test_platform_guard.py` | N/A — gate metadata. A future Mac-only dialog/egress added inside a darwin guard will now be tagged in `python -m quill.tools.dialog_inventory` output. |
| #64 | eSpeak live Read Aloud pipes >8000-char sentences via `--stdin` (mirrors the batch overflow guard). | `quill/core/read_aloud.py` `_run_espeak_live` | Read Aloud with eSpeak over a very long sentence does not fail/truncate. |
| #11 | Tray terminology is platform-neutral: `_TRAY_NOUN` ("menu bar" on darwin), Settings label/description, Help topic body. | `main_frame.py:759`, `settings_specs.py`, `help/topics.json` | Settings and Help say "menu bar", not "system tray", on macOS. |
| #7 / F8 | Extend-selection caret movement matches native Mac semantics: Option = word, Cmd = line/document. | `main_frame.py` `_move_extend_selection_caret` | Option+Left/Right extends by word; Cmd+Left/Right to line start/end; Cmd+Home/End to document start/end. |
| #18 / #54 | The system-wide sticky-note hotkey path emits a clear status on darwin (RegisterHotKey is Windows-only) instead of silently dropping. | `main_frame.py` `_reload_global_hotkeys` | On darwin, a single-keystroke sticky-note hotkey shows the "not available on macOS" status; the Tools command and QUILL-key chord still work. |
| #39 | The close handler no longer `Hide()+Veto()` on darwin when no tray icon was created. | `main_frame.py` `_on_close` tray branch | With tray mode on, closing the window closes normally (refusal announced once); it never vanishes with no restore path. |
| #42 | The diagnostic bundle collects recent macOS crash reports from `~/Library/Logs/DiagnosticReports/` (darwin-only, redacted, capped). | `quill/stability/crash_report.py` `_collect_macos_diagnostic_reports` | Help > Save Diagnostics on macOS includes any recent `Quill*.crash`/`.ips` under `macos/`. Inert on Windows. |
| #53 | OK/Cancel rows use native order (Cancel-left/OK-right on macOS) via `ok_cancel_platform_order`. | `dialog_contract.py`, `vision_prompt_manager_dialog.py`, `remote_sites_dialog.py`, `voice_browser_dialog.py`, `main_frame.py` | The four dialogs show Cancel left, affirmative right on macOS. |
| #52 | Paste-HTML-as-Markdown tries the macOS `public.html` pasteboard flavour on darwin; Windows CF_HTML path unchanged. | `main_frame_power_tools.py` `_power_tools_clipboard_html` | Copy rich text from Safari/Notes; QUILL-key + M pastes converted Markdown on macOS. |

### Shipped in earlier batches (in CHANGELOG; listed for Mac validation)

| Item | Fix | Evidence |
|------|-----|----------|
| #1 / #43 | Keychain uses PyObjC `SecItemAdd` first; `security -w` CLI is a fallback with a one-time leak warning. | `quill/platform/macos/keychain.py:124-151` |
| #2 | Self-voicing fallback: when VoiceOver is off, darwin self-voices via `macos/tts.py`. | `quill/platform/windows/prism_bridge.py:308-330` |
| #35 | Portable mode on macOS routes credentials to Keychain with a warning. | `quill/platform/windows/credential_store.py` |
| #41 | LibreOffice import finds `/Applications/LibreOffice.app/Contents/MacOS` on darwin after PATH. | `quill/core/external_tools.py` |
| #46 | MathCAT gated Windows-only (ships only a Windows .dll). | `quill/core/optional_components.py:788-815` |
| #47 | Braille pack `lou_translate.exe` gated Windows-only; macOS shows a Homebrew message. | `quill/core/braille_pack.py:52-60` |
| #48 | External-engine resolution checks Homebrew/MacPorts/nvm for Finder-launched apps; allowlist has `node` not `node.exe`. | `quill/core/ai/external_engine.py` |
| #58 | PDF extractor classifies encrypted vs damaged vs scanned vs unavailable distinctly. | `quill/io/pdf.py:23-83` |
| #4 | Keymap pack overrides dropped on darwin when macOS-reserved or colliding. | `quill/core/keymap.py` `_apply_darwin_pack_overrides` |
| #8 / #61 / #74 | `duti` missing returns a status; `lsregister -f` refresh; `_app_path` walks to the `.app` bundle. | `quill/platform/macos/shell_integration.py` |
| #29 | STT self-test synthesizes its clip via `say -o` on darwin. | `quill/core/optional_components.py:396-449` |
| #65 / #78 | eSpeak pause keeps the cursor at the sentence start when interrupted. | `quill/core/read_aloud.py` |
| #76 | Window menu has standard stock items and is registered as the system Window menu on darwin. | `quill/ui/main_frame_menu.py` |
| #38 | persona_launcher writes a `.command` script (shebang + chmod 0755) on darwin. | `quill/core/persona_launcher.py` |
| #40 | The dead `Ctrl+Alt+Shift+` / `Alt+Shift+D` chords are routed to AI/compare/dark-mode commands. | `quill/core/keymap.py:165-188` |
| #51 | "Toggle hidden files" is `Cmd+Shift+.` on darwin (not Ctrl+H, which is system Hide). | `quill/ui/simple_open_dialog.py:43-47` |
| #55 | `EnginesPanel._after_install` guards all four post-install widget calls against a destroyed panel. | `quill/ui/ai_hub_engines_panel.py:184-196` |
| #59 | `bundled_subpath` values use forward slashes. | `quill/core/external_tools.py` |
| #60 / #73 | Redaction covers the `security` CLI `-w` short-secret form. | `quill/stability/redaction.py:131-141` |
| #7 (dispatch) | Platform dispatch delegates via module-level `sys.platform` gates. | `quill/platform/dispatch.py:28-49` |
| #50 | macOS `shell_integration` has direct unit tests. | `tests/unit/platform/macos/test_shell_integration.py` |
| #36 | feedback-hub in py2app includes, `.[feedback]` installed, mandatory token generated. | `scripts/setup_macos.py:95`, `macos-release.yml`, `build_macos.sh` — needs Mac bundle validation that the package lands in the `.app` |

### Needs Mac hardware (validation only — no code change expected)

- **NSSound / afplay Read Aloud.** `_NSSoundBackend` and the `_LiveWavPlayer`
  afplay path are unit-tested with fakes. Confirm on a real Mac that earcons and
  Piper/Kokoro/ElevenLabs/`say` Read Aloud produce audible output, and that the
  16-entry live-sound retention is generous enough under real firing rates.
- **MacOpenFile cold-launch race + doc-switch chord.** Confirm Finder/Dock/`open
  -a` file-open end-to-end (including the cold-launch race where the Apple Event
  arrives before `MainFrame` finishes constructing), and that the
  `Cmd+Shift+]`/`[` doc-switch chord and the `Cmd+Alt+F`/`Cmd+Alt+M`/
  `Cmd+Alt+Space` darwin alternates do not collide with the tester's setup.

---

## Mac tester validation checklist

Run these on a real Mac (VoiceOver + a non-VoiceOver pass) against a build from
main after this pass.

1. **F8 selection semantics.** Selection mode on (F8). Option+Left/Right extends
   by word; Cmd+Left/Right to line start/end; Cmd+Home/End to document start/end.
2. **macOS (system voice) Read Aloud engine (#21/#75).** In Speech Hub, pick the
   "macOS (system voice)" engine: voice picker lists system voices; Preview
   speaks; Read Aloud reads with pause/stop; batch export-to-file produces audio.
3. **Tray mode.** Enable tray mode; close the window — it closes normally with a
   one-time "not available on macOS" status (must NOT vanish with no restore
   path). Settings/Help say "menu bar", not "system tray".
4. **Sticky-note hotkey.** Bind a single-keystroke sticky-note hotkey; on darwin
   you get the "not available on macOS" status. Tools > Sticky Note and the
   QUILL-key chord still create a note.
5. **OK/Cancel order.** Voice Browser, Remote Sites (Open/Save), Vision Prompt
   Manager, Magic Paste — Cancel left, affirmative right on macOS.
6. **Paste HTML as Markdown.** Copy rich text from Safari; QUILL-key + M pastes
   converted Markdown (not plain text).
7. **Diagnostic bundle.** Help > Save Diagnostics — the zip includes any recent
   `macos/Quill*.crash`/`.ips`; no secrets (redaction stats in metadata.json).
8. **eSpeak long Read Aloud.** Read Aloud with eSpeak over a >8000-char sentence
   completes without truncation/failure.
9. **Platform-aware strings (#37).** AI Hub Auphonic note, Audio Studio SFTP
   publish note, GitHub sign-in failure, and Forget-API-key confirmation all say
   "Keychain"; dictation status says "System dictation"; the first-run wizard
   says "In my user profile"; the keymap editor's example chord says "Cmd+Alt".
10. **Dark Mode (#6).** Toggle Dark Mode in System Settings; QUILL's theme
    follows it.
11. **New Mac shortcuts (community ask).** Cmd+Alt+F / Cmd+Alt+M /
    Cmd+Alt+Space, and Cmd+G / Cmd+Shift+G for Find Next/Previous — confirm none
    collides with your setup and they feel natural; comment via the release-notes
    ask if not.
12. **Bundle items from earlier batches** (Keychain, LibreOffice, MathCAT/braille
    gating, engine resolution, Window menu, .command persona shortcut, etc.) per
    the "Shipped in earlier batches" table.

support#67 (diacriticals) and support#69 (Settings speech labels) are fixed in
code and are **not** on this internal checklist — they are routed to the
community for validation via the release notes, which link both issues.

---

## Build gates

All gates green this pass: `ruff check`, `dialog_button_contract`,
`check_banned_patterns`, `module_size_budget` (GATE-11 rebaselined with
`_rebaseline_2026_07_10_macos_say_read_aloud_engine` and
`_rebaseline_2026_07_10_macos_windows_strings_sweep`), and the smoke/unit suites
for the touched modules (read_aloud, platform_nouns, settings, speech,
voice_browser, i18n/catalogs, accessibility, network_egress_audit, dialog
inventory, setup wizard, keymap editor, github, ai_hub, assistant_ai,
platform_guard). The new `platform` field on the dialog-inventory and
network-egress gates is pinned by `tests/unit/tools/test_platform_guard.py` plus
sanctioned-platform-tag tests in both gate test files; the classification
snapshot shape is unchanged, so `check_banned_patterns` and the snapshot
consumer tests are unaffected. No Mac-only gate is exercised locally; the macOS
CI test job runs the `darwin`-gated tests. The `.pot` was regenerated and the
Italian `.mo` recompiled (3 invalidated entries cleared to English fallback).
The release notes `.html`/`.epub` were regenerated to match the edited `.md`
(docs-artifact parity).