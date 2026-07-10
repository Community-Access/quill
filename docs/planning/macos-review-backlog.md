# macOS platform review — 2026-07-09

Full-codebase audit of QUILL's macOS support: platform bridges (`quill/platform/macos` vs. `windows`), the keymap/accelerator system, voice/dictation/Whisper, Mac UI conventions and packaging, and macOS test coverage. Cross-referenced against the live macOS bug reports in `Community-Access/support` and used them to validate which issues still need follow-up. This file is a living backlog of the remaining open work. Already-tracked open Mac items (NSSound hardware confirmation, `MacOpenFileApp` Apple Event race + Cmd+Shift+]/[ chord, AI Hub tab group accessible-name verification) are not repeated here.

**Note on numbering:** Earlier drafts of this file double-listed the second-sweep findings (the block numbered 67-78 was a re-statement of #22-#27 and #60-#65), and the header/body counts disagreed ("62" vs "65"). That was a listing artifact, not 13 new findings. This version is deduplicated: every finding appears once. The active backlog count below is the real one.

Active backlog: 40 unresolved items (down from the 65 unique findings in the original audit; the rest were closed this pass — see "Completed this pass").

## Priority ladder

| Rank | Area | Finding | Confirmed by live report |
|------|------|---------|---------------------------|
| P1 | Security | Keychain secrets passed as CLI argv, visible via `ps` | |
| P1 | Accessibility | No self-voicing fallback when VoiceOver is off (needs native macOS TTS) | |
| P1 | Mac conventions | Third-party engine installers (eSpeak, Piper, Tesseract, Pandoc, Node) are Windows-only flows with unclear Mac gating | |
| P2 | 6 findings — keymap pack, screen capture, dark mode sync, platform-dispatch drift, duti silent failure, F8 Mac semantics | see below | |
| P3 | 4 findings — module ownership, tray terminology, dead clipboard module, gate blind spots | see below | |

---

## Completed this pass

- **#3 `total_ram_gb()` macOS branch.** Added a `sysctl -n hw.memsize` branch so macOS reports real RAM instead of a flat 8.0 GB, fixing Whisper model recommendations on every Mac.
- **#4 Mic-permission guidance OS-neutral.** The dictation "microphone unavailable" message no longer says "Windows microphone permissions" verbatim on macOS; it branches to a macOS System Settings path.
- **#5 DECtalk gated to Windows.** DECtalk's only backend is `DECtalk.dll` (Windows-only), so it is no longer offered as an installable component on macOS (matching the Pandoc Mac-note pattern).
- **#6 Bare F-keys / Fn-key accommodation (partial).** Find Next/Previous now have macOS alternates (`Cmd+G` / `Cmd+Shift+G`, the macOS HIG standard) so the highest-traffic find bindings work without holding Fn. The Fn-key requirement is documented in the user guide. The remaining bare F-key bindings (selection F8, spell/thesaurus F7, region F6, dictation F9) are deliberately left as-is pending real Mac validation rather than rebinding blind.
- **#7 Duplicate "About" menu entry.** The Help-menu "About Quill" is now hidden on macOS (the Application menu already shows it via `wx.ID_ABOUT`); Windows keeps the Help entry.
- **#9 macOS CI runs the test suite.** Added a `test` job to `macos-release.yml` that runs `pytest -m "not slow"` on `macos-26`, so the `skipif(sys.platform != "darwin")` tests (Keychain, high-contrast, sr_detect) finally execute somewhere.
- **#10 Earcon volume on macOS.** `_NSSoundBackend` now implements a real `set_volume` (applies `NSSound.setVolume_()` per active sound); the volume slider is no longer a no-op on macOS.
- **#12 Cmd+F4 accelerator guarded.** The redundant `Cmd+F4` close-document accelerator is now non-darwin-only (Cmd+W already closes documents); macOS no longer gets a non-idiomatic chord.
- **#15 SAPI5 guidance platform-conditional.** The "Dictation (offline speech)" description no longer claims "SAPI 5 dictation works without any of this" on macOS (where there is no SAPI 5); it states Whisper is the only dictation path on macOS.
- **#16 Dependency tests guard macOS packaging.** Added `test_macos_packaging_deps_are_platform_marked_for_darwin` (py2app/setuptools/pyobjc/apple-fm-sdk carry `sys_platform == 'darwin'`) and `test_windows_only_deps_are_excluded_from_macos_install` (comtypes/prismatoid/accessible-output2 carry `win32` and never appear in the `[macos]` extra).
- **#17 `test_high_contrast.py` tests behavior.** Replaced the lone `isinstance(result, bool)` assertion with true/false/missing-CLI cases via `subprocess.run` fakes, so a hardcoded-wrong detector would actually fail.
- **#19 AppKit announce main-thread guard.** `macos/announce.py` now checks `NSThread.isMainThread()` and marshals off-main calls onto the main queue via libdispatch (defense in depth for a future background callback).
- **#25 Duplicate `_file_dialog_default_dir`.** Removed the second, shadowing definition in `main_frame.py`.
- **#26 `list_dictation_devices()` dead code.** Removed the always-`[]` placeholder and its placeholder test.
- **#28 Read Aloud silent on macOS.** Live WAV playback (`_run_wav_sentences`) fell through a `winsound`-only guard and silently deleted every synthesized WAV on macOS. Replaced with a cross-platform `_LiveWavPlayer` that uses `afplay` on macOS, so Piper/Kokoro/ElevenLabs/SAPI5/DECtalk Read Aloud actually speaks on macOS.
- **#30/#31/#32 macOS keymap collisions.** `edit.replace` (Ctrl+H → Cmd+H = Hide), `edit.pop_mark` (Ctrl+M → Cmd+M = Minimize), and `edit.select_chunk` (Ctrl+Space → Cmd+Space = Spotlight) now have darwin alternates: `Cmd+Alt+F`, `Cmd+Alt+M`, `Cmd+Alt+Space`. Provisional pending real-Mac validation (same caveat as the doc-switch chord).
- **#33/#34 closed as non-issues.** The audit claimed JSON keymap profiles hardcode `Alt+Left`/`Alt+Right` (back/forward) and doc-switch chords. They do not — no JSON profile contains those entries, so they inherit the already-darwin-aware `DEFAULT_KEYMAP`. No fix needed.
- **#44 VoiceOver announcement length cap.** `macos/announce.py` caps the payload at 4096 chars (with ellipsis) so a runaway status string can't become an unreadable wall of text under VoiceOver.
- **#45 VoiceOver announcement interrupt control.** `announce(message, *, interrupt=True)` now maps to NSAccessibility priority: high (interrupt, for internal narration) vs low (routine status, non-interrupting). `prism_bridge` passes `force_speech` as the interrupt flag, matching Windows semantics.
- **#49 `[macos]` extra platform markers.** `py2app` and `setuptools<83` now carry `sys_platform == 'darwin'` so a non-Mac `pip install .[macos]` no longer pulls macOS-only packaging deps.
- **#56/#57 Atomic document writes.** Added `write_text_atomic` (temp + `fsync` + `os.replace`, mirroring `write_json_atomic`) and applied it to `autosave_document` (the recovery snapshot can no longer be a truncated half-write) and `write_text_document` / `_write_brf_document` (a crash mid-save no longer corrupts the user's document at its real location).

---

## P1 — high (remaining)

1. **Keychain secrets exposed via process listing.** `quill/platform/macos/keychain.py:33` (`set_secret`) calls `security add-generic-password ... -w <secret>` via `subprocess.run`, putting the plaintext API key/token in argv, visible to any local process via `ps -ww` for the call's duration. Fix: use PyObjC's `Security` framework (`SecItemAdd`) directly instead of shelling out with `-w`. (Also covers #43/#60 — the CLI-only path and the redaction gap.)
2. **No self-voicing fallback when VoiceOver is off.** `quill/platform/macos/announce.py` only posts an `NSAccessibilityAnnouncementRequestedNotification`, a no-op unless VoiceOver is listening. Windows falls back to SAPI5 self-voicing when no screen reader is detected (`prism_bridge.py:276-288`); no AVSpeechSynthesizer/NSSpeechSynthesizer equivalent exists on Mac, so every `self._announce(...)` call is silently swallowed for a low-vision Mac user running without VoiceOver. Fix: a native macOS TTS backend is the single biggest lever — it also closes #62/#75 (read-aloud engine choices list) and gives a default engine. Do it early.
3. **Third-party engine installers are Windows-only flows with unclear Mac gating.** `espeak_install.py`, `piper_install.py`, `tesseract_install.py`, `pandoc_install.py`, `node_install.py` are all annotated Windows-only in `network_egress_audit.py`; not confirmed whether the menu items that trigger them are actually hidden on macOS, or whether Mac users hit a dead end with no Homebrew-based guidance. Fix: confirm/enforce `sys.platform` gating in the menu builder, and point to Homebrew equivalents where one exists.

---

## P2 — medium (remaining)

4. **No macOS-oriented keymap pack.** All 8 packs in `keymap_packs.py` are Windows-flavored (Notepad, Notepad++, VS Code, Word) or generic; only one binding in one pack has a `darwin` branch. Overrides apply as-is on Mac with none of the collision review `DEFAULT_KEYMAP` itself received. Fix: ship a VoiceOver-oriented pack, or explicitly document the existing ones as Windows-emulation-only and audit each for Mac system-reserved collisions.
5. **Screen capture/OCR-from-screen has no macOS backend.** `quill/platform/windows/screen_capture.py:46-47,109-110` raises "only available on Windows" on any non-`nt` platform; no `quill/platform/macos/screen_capture.py` exists, and no path handles macOS's separate Screen Recording permission. Fix: implement via `Quartz`/`screencapture` with `CGRequestScreenCaptureAccess()` handling, or make the unsupported message explain why rather than reading as a bare omission.
6. **Dark Mode / Reduce Motion are never synced from the OS.** `quill/platform/macos/high_contrast.py` queries `defaults read com.apple.universalaccess increaseContrast` but nothing queries Dark Mode (`AppleInterfaceStyle`) or Reduce Motion; the in-app dark-mode toggle is manual-only on every platform. Fix: extend the existing `defaults`-shelling module to also report dark-mode/reduce-motion state and offer to sync QUILL's theme to it.
7. **Two independent, drift-prone platform-dispatch mechanisms.** `quill/platform/dispatch.py` does a lazy `current_platform()` check per function while sibling modules (`high_contrast.py`, `sr_detect.py`, `shell_integration.py`) do a module-level `sys.platform` gate. A future macOS-routing change only applied to one surface would silently miss the other. Fix: consolidate on the module-level gate; have `dispatch.py` delegate rather than re-implement.
8. **`duti`-based file-association helper fails silently.** `quill/platform/macos/shell_integration.py:65-81` is a complete no-op whenever `duti` (a third-party Homebrew tool, not preinstalled) is missing — the common case — with no error or UI signal, so a "Set QUILL as default editor" action can appear to succeed while doing nothing. Fix: return a status so calling UI code can tell the user why it didn't work. (Also #61/#74 — `_app_path()` is a stub; no `lsregister` refresh or Dock badge.)
9. **F8 extend-selection caret movement doesn't match native Mac text semantics.** `main_frame.py` (`_move_extend_selection_caret`) uses Cmd (via `ControlDown()`) for word movement and document bounds, where native macOS convention is Option for word and Cmd for line/document bounds. Internally consistent, but diverges from Mac muscle memory. Fix: consider Option-based word movement for parity; low urgency since nothing is broken or colliding.

---

## P3 — low (remaining)

10. **Misleading module ownership.** `quill/platform/sr_announce.py` and `announce_engine.py` are platform-neutral (unconditionally re-export `quill.platform.windows.sr_announce`/`prism_bridge`) but live under `windows/`, inviting a future contributor to assume they're Windows-only and skip Mac testing. Fix: relocate to a platform-neutral path.
11. **"System tray" terminology applied unchanged to the Mac menu-bar item.** `main_frame.py` tray strings ("Quill is running in the system tray") use Windows terminology even though the feature renders as a menu-bar status item on Mac. Low cost, cosmetic.
12. **Dead Windows-only clipboard module with no Mac counterpart.** `quill/platform/windows/clipboard.py` (HTML/RTF email-clipboard payload) has zero callers today; if ever wired up there's no `NSPasteboard` equivalent. Flag as tech debt. (Related: #52 — HTML-clipboard paste-as-Markdown only reads the Windows `CF_HTML` flavour, degrading to plain text on macOS.)
13. **Gate tooling doesn't tag Mac-only surfaces.** `dialog_inventory.py`/`network_egress_audit.py` are platform-agnostic AST scans with no `platform` field, so a Mac-only dialog/egress site never exercised on real hardware can't be distinguished in gate output. Fix: add an optional `platform` field to the scan schema for targeted manual Mac QA.

---

## Additional unresolved items (mac-specific and cross-platform)

These continue the macOS audit. Findings already closed this pass (#28 Read Aloud, #30/#31/#32 collisions, #33/#34 non-issues, #44/#45 VoiceOver, #49 markers, #56/#57 atomic writes) are removed.

- **#29 STT self-test always fails on macOS — hard SAPI5 dependency.** The test harness still depends on a Windows-only SAPI5 clip path.
- **#35 Portable mode silently drops credentials on macOS.** Non-Windows portable mode still provides no usable persistence path and no warning.
- **#36 macOS `.app` ships without `feedback-hub` — Report a Bug is broken despite the token being present.** The release build still omits the feedback extra from the macOS bundle install path.
- **#37 Windows-specific UI strings render verbatim on macOS.** Several setup and connection dialogs still mention Windows-specific storage or dialog terminology.
- **#38 `persona_launcher` writes a useless `.bat` file on macOS.** The macOS fallback still writes a Windows batch file instead of a macOS-launchable script.
- **#39 Tray mode on macOS hides the window with no restore path.** The app can disappear into a non-restorable hide state on macOS.
- **#40 The advertised `Ctrl+Alt+Shift+` / `Alt+Shift+D` shortcuts are dead.** No longer routed to anything.
- **#41 LibreOffice import route never works on a standard macOS install.** The import path still relies on an executable that is not normally on PATH on macOS.
- **#42 Crash-report bundle collects no macOS-native forensic data.** The diagnostic bundle still lacks native macOS capture data for hangs and crashes.
- **#43 Keychain access relies solely on the `security` CLI — no pyobjc fallback, no sandbox path.** Same root as #1; the keychain path has no fallback and no warning for sandboxed or missing-CLI cases.
- **#46 MathCAT is offered on macOS but ships only a Windows `.dll`.** The optional component is still misrepresented on macOS.
- **#47 Braille pack download ships `lou_translate.exe` with no platform gate.** The install path still treats the Windows binary as usable on macOS.
- **#48 External-engine resolution misses Homebrew/nvm on a Finder-launched macOS app; `node.exe` hardcoded.** Finder-launched apps still miss shell-profile paths for engines and Node.
- **#50 macOS `shell_integration` module has zero test coverage.** The Mac-specific shell integration surface lacks direct tests.
- **#51 "Toggle hidden files" (`Ctrl+H`) in the simple open dialog collides with macOS Hide.** The shortcut is still bound to the system Hide shortcut on macOS.
- **#53 Manual OK/Cancel button sizers use Windows order (OK left, Cancel right) — backwards on macOS.** Several dialogs still use the Windows button order on macOS.
- **#54 System-wide "sticky note capture" hotkey is a silent no-op on macOS.** The global hotkey path is still silently dropped on macOS.
- **#55 The #915 crash fix in `EnginesPanel._after_install` only guards the first widget call.** The install-complete callback still risks widget teardown crashes after the first guard.
- **#58 PDF extractor swallows all errors and misreports corrupt/encrypted files as "scanned/image-only."** The error classification still collapses real parse failures into the wrong user message.
- **#59 `external_tools.bundled_subpath` values use Windows backslashes.** The bundled subpath handling still assumes Windows separators.
- **#60/#73 Redaction misses the `security` CLI `-w` short-secret form.** Short secrets passed via the keychain CLI can still leak into logs. (Same root as #1.)
- **#61/#74 `shell_integration._app_path()` is a stub; no `lsregister` refresh or Dock-badge surface.** The macOS shell integration path still lacks app-path and registration handling. (Same root as #8/duti.)
- **#62/#75 `read_aloud_engine` settings choices list no macOS-native TTS option.** The settings UI still exposes only Windows-era voice-engine choices on macOS. (Closed by the native macOS TTS backend lever — see #2.)
- **#63/#76 The Window menu lacks standard macOS items and isn't registered as the system Window menu.** The macOS Window menu still lacks the standard stock items and registration wiring.
- **#64/#77 eSpeak synthesis passes the sentence as CLI argv, risking Windows command-line length overflow.** The Windows eSpeak path still risks overflow on long input spans.
- **#65/#78 eSpeak live pause advances the cursor to `span.end` even though only part was spoken.** Pause handling still reports the sentence as fully spoken even when it was only partially read.

---

## Community support inbox — macOS reports (Community-Access/support)

Two of the three previously-reported QUILL macOS issues in `Community-Access/support` still need follow-up; the preview-path crash in support#68 has now been addressed and is no longer in the active backlog.

| Issue | Title | Root-caused to | Priority |
|-------|-------|-----------------|----------|
| [support#69](https://github.com/Community-Access/support/issues/69) | Disconnected controls/labels in Settings on macOS | Finding 4 (`voice_browser_dialog.py:184-212`) | P0 |
| [support#67](https://github.com/Community-Access/support/issues/67) | Keyboard shortcuts replace Polish diacritical marks | Finding 7 (`keymap.py` bare Option+letter bindings) | P0 |

**[support#66](https://github.com/Community-Access/support/issues/66)** ("product-feedback") is filed against the *Git Going with GitHub* workshop, not QUILL — out of scope; route to that project's own backlog.

No other open issues exist in `Community-Access/support` as of this review (checked 2026-07-09).

---

# Backlog review: remaining open issues

**Already shipped and documented in the CHANGELOG / release notes (removed from this future-facing list):** #909 (the free-first import pipeline is now a base dependency), #890 (Casual Writer tightened to a true "just write" profile), the Report-a-Bug "No token" build regression, #897 (Wikipedia lookup), #895 (Clip Library), #900 (Send/Copy as Email), #894 (Accessible AutoOutline), #896 (Work Personas), #899 (Mandatory alt text + inline image descriptions), #891 (Print Studio), and #892 (Header/Footer Builder). Closed items (#898 Second View, #901 tablet/low-vision, #905/#906/#907 Convert-Non-ASCII bugs) are excluded.

## Follow-up from #892

- **DOCX/RTF native header/footer export**: the Header/Footer Builder authors and saves a spec, and draws it when printing, but does not yet write real header/footer XML into DOCX/RTF exports. Deliberately deferred per the issue's own build order (confirm the round-trip once real usage exists to validate against).

## Priority ladder (my recommendation)

| Rank | Issue | Title (short) | Impact | Confidence | Why here |
|------|-------|---------------|--------|-----------|----------|
| **P3** | #893 | "Rich Document" discoverability | Medium | High (feature exists) | Downgraded per the issue's own re-check: serves a *secondary* audience (low-vision / ex-Word), not QUILL's core keyboard-first user. Low cost, low urgency. |

---

## #893 — "Rich Document" workflow discoverability — **P3**

**State:** The Rich Text lens already exists and works — `core.rich_text_lens` (`feature_catalog.py:~149`), wired to `view.switch_editing_lens`, locked_off under at least one profile (`settings.py:~595`). This is discoverability/framing, not a build.

**Proposal:** Surface "Rich Document" as a plain-language onboarding choice (first-run wizard and/or profile-adjacent setting) for users who want WordPad-like editing without learning Markdown — framed as an experience, not as "enable the Rich Text lens flag." Add an in-context "Switch to Rich Document view" affordance (menu + command palette) for users mid-session. Audit which profiles lock the lens off and confirm that's still right if it's being promoted.

**Non-goals:** Not changing the underlying Markdown-with-invisible-codes architecture; not making Rich Text the default for everyone.

**Priority:** P3 — **explicitly downgraded per the issue's own re-check.** QUILL's plain-text/Markdown default *is* the screen-reader-optimized design, not a way-station to a "real" rich mode. This mainly serves a secondary audience (low-vision, sighted co-authors, ex-Word/WordPad users). Real and worth doing — the feature already exists so the cost is low — but it's a "nice for a secondary audience," not a core-mission gap like #891 or #899.

## Suggested sequencing

1. **#893** — the one remaining item; low-urgency discoverability polish, fold into whatever onboarding-wizard work is already happening rather than scheduling standalone.

---

# Outstanding from the 2026-07-08 session: unresolved reports + follow-ups needing hardware

The earlier-session items already shipped in this pass (the macOS-safe file-open/launch flows, the voice-preview playback fix, and the AI dialog guidance changes) are omitted from the remaining backlog below. The items that still need real hardware or a fresh repro remain:

## 1. NSSound macOS backend — needs real hardware to confirm

The `_NSSoundBackend` (AppKit `NSSound` via `pyobjc`) in `quill/platform/sound_player.py` is unit-tested with fakes only (this dev box is Windows). Two things still need a real Mac: (a) that `NSSound.alloc().initWithData_()` actually produces audible output for QUILL's WAV format, and (b) that the bounded live-sound retention (16 entries) is generous enough under real earcon firing rates without AppKit tearing down a sound mid-playback. (Now also: confirm the new `_LiveWavPlayer` afplay path in `read_aloud.py` produces audible Read Aloud on a real Mac.)

## 2. macOS file-open + document-switch chord — needs real hardware to confirm

`MacOpenFileApp`'s `MacOpenFile`/`MacOpenFiles` override (Finder/Dock/`open -a` file-open handling) is standard wx API usage but the exact Apple Event delivery timing (especially the cold-launch race where a file-open event arrives before `MainFrame` finishes constructing) needs a real Mac to confirm end-to-end. Separately, the default document-switching chord (`Cmd+Shift+]`/`[`, chosen to match Safari/Xcode's tab-cycling convention) is a UX pick, not mechanically forced — worth confirming with an actual Mac user it doesn't collide with anything on their setup before calling it final. (Same provisional-validation caveat now applies to the new #30/#31/#32 darwin alternates: `Cmd+Alt+F`, `Cmd+Alt+M`, `Cmd+Alt+Space`.)

## 3. Latent risk (not yet reproduced): `_show_intellisense_popup` could still crash on a dead popup

The #917/#918 fix made `_IntellisensePopup.is_visible()` tolerate a deleted C/C++ `Frame` (from `main_frame_intellisense.py`'s `_handle_intellisense_key_down`). But `_show_intellisense_popup` (same mixin) still calls `popup.update(...)` / `popup.show(...)` on the same popup object after checking `is_visible()` — if a *future* keystroke reaches that path with the same dead-frame condition instead of the key-down handler, those calls are unguarded and could raise the same class of `RuntimeError` somewhere new. No crash report evidences this path is actually reached (the two filed crashes were both in `is_visible()` specifically, called from the key-down handler), so this is a documented risk, not a confirmed bug — revisit if a similar crash resurfaces with a different traceback location.

---

## Sequencing notes

- **Single biggest lever:** Finding #2 (native macOS TTS backend) collapses three other findings — #62/#75 (read-aloud choices list), the self-voicing fallback, and gives a default engine — into one build. Do it early.
- **Keymap sweep:** The remaining Windows-flavored chords persisted/accelerated unchanged on `darwin` are now mostly darwin-overridden in `DEFAULT_KEYMAP` (Find Next/Prev, replace, pop_mark, select_chunk, doc-switch, back/forward). The open residue is the keymap *packs* (#4) — audit each for Mac system-reserved collisions rather than one pack at a time.
- **Atomic-write sweep:** DONE this pass (#56/#57) via the new `write_text_atomic` helper; no remaining non-atomic document writers known.
- **CI gap:** Finding #9 (no Mac pytest) is now closed; the macOS test job is what will catch #39, #40, #44, #45, #50, #54, #61, #63, and several others going forward.
