# Release Channels for the QUILL Family: Stable, Beta and Dev

*Plan of record draft, 2026-10-03. Covers QUILL (the full editor), QUILL Lite, Quill Radio and QUILL Cast. Written so any other QuillVille app can join by adding one profile entry.*

> **Status (2026-10-03): Phases 0 and 1 are implemented** (uncommitted on `main`, not yet released). Phase 0: `quill/core/versioning.py`, `select_latest` in the sibling and Lite checks, `per_page=100` with paging, Cast's installed-version check and `quill-app-version.ini` in both Cast installers, Cast in GATE-APPVER and GATE-SIBVER, `quill/core/data_formats.py` and `data_format_ledger.py` (recording only), `channels.json` (`quill/core/updater/channels.py`), and `windows-release.yml` reading the channel from the tag. Phase 1: Help > Release Channel... and a Preferences row in all four apps (no chord: Alt+Shift+F4 was dropped on 2026-10-03, because Windows reads it as Alt+F4 in a dialog and closes the window -- family rules 4 and 9), the shared chooser and risk windows (`quill/ui/updates/`), joined-Beta copies, "Wait for Stable" plus the same-version flip, a channel-aware update check, read-only Update History (reached from the Release Channel window rather than its own menu item), and the interim runtime rule (6.5).
>
> **Phases 2, 3 and 4 are implemented too** (2026-10-03, uncommitted, not yet run against a real release). Phase 2: the signed per-app feed (`quill/core/updater/feed.py`, `feed_fetch.py`, `feed_publish.py`), resumable downloads checked against the feed's SHA-256 (`download.py`), background downloads on Beta and Dev (`background.py`, `quill/ui/updates/background.py`), `scripts/publish_release.py`, `promote_release.py`, `feed_tool.py` and `dev_build_plan.py` over `quill/tools/release_feed.py`, GATE-FEED (`tests/unit/docs/test_release_feeds.py`, and `quill/tools/release_feed_audit.py` in `platform_report` with the 14-day expiry warning), GATE-RELEASE-PAGE (`tests/unit/scripts/test_release_page_budget.py`), and the `dev-builds.yml` and `promote-release.yml` workflows. Every app's update check reads the v2 feed first and uses the old GitHub path only while no feed is published (HTTP 404). Phase 3: runtime slots (`runtime_slots.py`; `installer/shared-runtime.iss` with `/CHANNEL=`, `[runtime] slot=` and slot-keyed refs; `runtime_resolve.c` and `launcher.c`, source only, not built; `runtime-stable`, `runtime-beta` and the `runtime-latest` alias in `build_runtime_installer.ps1`; channel-aware GATE-SIBVER), which lifts the "alone on the runtime" rule for any install whose marker names a slot. Phase 4: `downgrade_verdict` and the three Go back to Stable windows (`going_back.py`, `quill/ui/updates/return_to_stable_dialog.py`, `going_back_flow.py`), restoring the joined-Beta copy with the shared-file rule and ledger lowering (`snapshots.restore_snapshot`, `data_format_ledger.lower`), `UnsafeDowngradeError`, and the update helper's health check, kept installer and portable `.previous` swap (`apply.py`, `apply_script.py`, `self_update.py`), with every undo in Update History.
>
> **Decisions, 2026-10-03** (the owner's answers to 10.4): per-app channel with "move the others too" (5); Stable takes only final-numbered builds that were first on Beta, promoted as the same files (4); screen-reader sign-off for Stable only (3); at least 7 days on Beta, shorter only with a written reason recorded in the promotion (3); Dev builds by CI from `main`, at most once a day and only when `main` changed, unsigned, published to the separate repository `Community-Access/quillville-dev-builds`, and Dev runtimes do not repair themselves ("Reinstall the Dev build") (1); about 335 MB extra for a Beta or Dev runtime slot is accepted and the risk window says so (2); the v2 feed expires after 90 days and is refreshed at every release, and the signing key stays off CI, so there is no weekly re-sign workflow -- signing happens in the local publish scripts with the owner's existing feed key, and `publish_release.py` and `platform_report` warn when any feed is within 14 days of expiry (6); the previous installer is kept for rollback until 3 successful starts or 7 days, and Update History records each undo (7); macOS later (8); QUILL 1.0.0 is its first Stable, reached through a `v1.0.0-rc.1` tag on Beta and then promotion (9); QUILL Lite keeps the `quill-lite-v` prefix (10); on Beta and Dev every app downloads updates in the background and never installs without asking, skipping metered connections, Quiet Hours and Quill Radio recordings, and Stable is unchanged (11); no gradual rollout (12); `promote-release.yml` requires a GitHub Environment named `stable-promotion` (4.4).
>
> Where the code departs from the text below because of these decisions: no `feed-refresh.yml` (8.2) -- a feed is refreshed at each publish or promotion, or by `scripts/feed_tool.py refresh`; the promote workflow cannot sign, so it runs `promote_release.py --no-sign` and opens a pull request that GATE-FEED keeps red until the owner signs it locally; and, so that a failed update can undo itself at all, the installer of the version you are running stays in `<updates>/rollback/` (the *previous* one is the one aged out after 3 starts or 7 days).
>
> **Also implemented, 2026-10-04:** `scripts/revoke_release.py` (the documented way to withdraw a build; `feed_tool.py revoke` calls the same `release_feed.withdraw`), `scripts/rollup_release_notes.py` over `quill/core/updater/notes_rollup.py` (run by `promote_release.py` at every promotion to Stable, printed by its `--dry-run`, and used for the GitHub release body and the feed's `notes_summary`), GATE-DATAFMT (`quill/tools/data_format_audit.py`, `tests/unit/core/test_data_formats.py`, `tests/unit/core/fixtures/data_format_fingerprints.json`, in `platform_report`), and the rehearsal (`tests/unit/scripts/test_channel_rehearsal_offline.py` in CI, `tests/integration/test_channel_rehearsal.py` opt-in with `QUILL_CHANNEL_REHEARSAL=1`).
>
> **Decisions, 2026-10-04.** (questions.md 32) The installer kept so that a failed update can undo itself is kept **always on Beta and Dev**, and **on Stable only for 7 days or 3 successful starts after each update** (`quill/core/updater/apply.py`, `keeps_installer`), so a Stable computer gets its roughly 200 MB back; this narrows decision 7 for the running version's installer, while the *previous* version's installer still ages out after 3 starts or 7 days on every channel. And the old v1 update list stays signed in CI by `windows-release.yml` with the `QUILL_FEED_SIGNING_KEY` secret for now. Remove that secret from CI and stop v1 signing once every app's channel-aware release (QUILL 1.0.0, QUILL Lite 1.2.0, Quill Radio 3.2.0, QUILL Cast 2.0.0) has been out for one full release cycle; until then, leave it alone (`docs/release/RELEASE.md`).
>
> **Decisions, 2026-10-04 (code signing).** "Beta and developer builds should not be digitally signed." Authenticode signing is refused for any version with a pre-release part (`-dev`, `-alpha`, `-beta`, `-rc`) and for every Dev build: `-Sign`, `QUILL_SIGN` and `QUILL_SIGN_REQUIRED` cannot force it, and the build says "Beta and Dev builds are not code-signed; signing skipped." (`scripts/code_signing.py` `build_decision`, asked by every `build_release.ps1` through `Resolve-QuillSigning` and by `build_windows_distribution.py`). Stable is always signed. The conflict with "Stable takes the same files that were on Beta" is resolved by signing the **final-numbered candidate when it is built**, not at promotion: an Inno `Setup.exe` carries its payload compressed inside it, so signing at promotion would mean either rebuilding the installer (new files, never tested on Beta) or signing only the outer `Setup.exe` (unsigned programs on Stable). A final-numbered build waiting on Beta is a release candidate of Stable, not a Beta build. `publish_release.py` refuses an unsigned final-numbered build and a signed Beta or Dev one; P5 is no longer conditional on `QUILL_SIGN_REQUIRED` and always runs for Stable, reading the embedded signature from the installer and from every `.exe` in the portable zip (so it works on the Linux promote runner), and verifying with `signtool` where it is installed. QUILL's own `v1.0.0` candidate is built and signed on the owner's computer, because `windows-release.yml` has no Azure credential (`docs/code-signing.md`).

---

## 0. The short version

- **Three channels.** Stable, Beta and Dev. Every app is on Stable unless you choose otherwise. You choose per app, and you can also move all your QuillVille apps together in one step.
- **The channel belongs to the listing, not to the binary.** A build is made once and signed once. After that it moves from Dev to Beta to Stable as the same bytes. Only the signed feed changes. Prerelease-numbered builds (`3.3.0-beta.2`) can never become Stable. A plain-numbered *candidate* build (`3.3.0`) goes to Beta first and is then promoted to Stable unchanged.
- **One signed feed per app.** It lives at `updates/v2/<app>.json` on the existing Pages site and is signed with the existing Ed25519 feed key (`quill/core/feed-pub.key`). It lists every build with its channels, SHA-256 hashes, data-format versions, required runtime, rollback targets and a revoked flag. GitHub Releases still hosts the files and keeps the prerelease flags, so copies already installed keep working.
- **"Back to Stable only if safe" becomes a rule the code can check.** Each build declares the data-format versions it *writes* and the versions it can *read*. Each machine keeps a ledger of the highest format version ever written there. Going down is allowed only if the target build can read everything in the ledger. When it can't, you get two safe choices: wait on your current version until Stable catches up (the app then moves you across by itself), or restore the automatic copy saved when you joined Beta.
- **The biggest hidden problem is the shared runtime.** The QuillVille Runtime carries a frozen copy of *every* app's code, and the newest runtime build always wins. So putting Radio on Beta today would silently run Beta code for a Stable QUILL Lite on the same machine. Rolling Radio back would not help either, because the newer runtime is never replaced by an older one. Before runtime apps can offer Beta on a machine with more than one app, the plan adds **channel runtime slots** (`Runtime\3.13`, `Runtime\3.13-beta`, `Runtime\3.13-dev`).
- **Phase order follows user value.** First fix the existing hazards. Then ship the channel choice and risk dialog in all four apps (QUILL first, because it does not use the shared runtime). Then the signed feed and promotion tooling, then runtime slots, then safe downgrade and rollback, then the extras.

---

## 1. Survey: what exists today (with evidence)

### 1.1 Two updaters, one shared UI

| Piece | Where | What it does |
|---|---|---|
| QUILL's updater | `quill/ui/main_frame_updates.py` (`UpdatesMixin`) | Reads the signed v1 manifest, then falls back to the GitHub Releases API. Has a `beta_updates` checkbox, a consent dialog, "Skip this version", automatic download on the silent check, and a GLOW engine updater. |
| Sibling-app updater | `quill/ui/app_shell.py:824-927` (`check_for_app_updates`) for Radio, Cast and others; `quill/apps/lite_updates.py` for Lite | Reads the GitHub Releases API only, filtered to the app's own asset prefix. Takes `stable[0]`. Has no channels. |
| Shared offer dialog | `quill/ui/update_notice.py` (`show_update_available`; `update_header` at 118-132 labels "Beta / prerelease" or "Stable") | One dialog for all nine apps. |
| Shared download and install | `quill/ui/update_download.py` (`download_and_offer_install`, `offer_install` 182-270, `apply_and_restart` 273) | Offers Install and restart now, Install when I close, or Open folder. |
| Self-apply helper | `quill/core/self_update.py` (`build_apply_update_script` 52-167, `begin_self_update` 361-429) | A batch helper waits for the app's PID. Portable copies get `robocopy /MIR /IS` with `data` excluded (line 135). Installed copies get a silent elevated Inno run (`/VERYSILENT /SUPPRESSMSGBOXES /NORESTART`, 141-146). It breaks out of the launcher's job object (300-321). |
| Network core | `quill/core/updates.py` | See the details below. |

Details of `quill/core/updates.py`:

- **v1 manifest feed URL:** `DEFAULT_UPDATE_MANIFEST_URL` at 19-21 (`community-access.github.io/quill/updates/.quill-update-feed-v1.json`).
- **Signature on the v1 manifest:** Ed25519 is *optional*. `parse_update_manifest` (527-552) accepts a feed with no `signature_ed25519` unless `QUILL_REQUIRE_SIGNED_FEED=1` (548-551). The legacy salted SHA-256 uses a public salt (`_SIGNATURE_SALT`, line 25, and the docstring at 660-664 says it "protects against accidental corruption, not a determined attacker").
- **v1 manifest content:** it has no channel field. It holds exactly one `version` and one `download_url` (the `UpdateManifest` dataclass, 97-109).
- **Asset hashes:** these come from GitHub's own API `digest` field (`download_digest`, 136-140), not from anything we signed. The download hashes as it streams (`download_release_asset` 861-908) but **cannot resume**.
- **Resumable download already exists elsewhere:** `quill/core/release_assets.py:283` (`_download_resumable`, using HTTP Range plus mirrors) is used for components, not for updates.
- **Trusted hosts:** `_trusted_update_hosts` (975-984).

### 1.2 How versions are compared today (three different parsers)

1. `quill/core/updates.py:_version_tuple` (778-834) and `_prerelease_rank` (837-858). The order is rc (tier 2) > beta/b (tier 1) > alpha, **dev** and anything unknown (tier 0). It accepts display forms ("0.7.0 Beta 1") and PEP 440 (`0.8.0b1.post1`). The pre-release number is the *first* run of digits. So `3.3.0-dev.20261003.1` and `3.3.0-dev.20261003.2` **tie**, and two dev builds from the same day cannot be ordered. A tag like `quill-radio-v3.0.4` parses as `0.0.0` (partition on the first "-"). QUILL's `fetch_releases` only avoids offering sibling-app releases by that accident.
2. `scripts/check_sibling_versions.py:parse_version` (69-75). Any suffix becomes `-1`, so every pre-release of a version is equal.
3. `tools/generate_build_info.py`: `pep440_version` (61-72) produces `1.0.0b1` and `1.0.0.dev<date><n>`, and `display_version` (75-86) produces "1.0.0 Beta 1" and "1.0.0 Dev".

**Pure semver would sort these wrongly for us.** Semver compares pre-release labels as ASCII, which puts `3.3.0-dev.1` *after* `3.3.0-beta.1`. We need PEP 440 *ordering* (dev < alpha < beta < rc < final) with semver-shaped *spelling* in tags.

### 1.3 Tags actually in the repo

`git tag` shows `quill-lite-v1.1.2`, `quill-lite-v1.1.1`, `quill-lite-v1.1.0`, `quill-radio-v3.0.4` … `v3.0.0`, `quill-lite-v1.0.1`, `quill-lite-v1.0.0`, `runtime-latest`, `v0.9.0-beta.3`, `v0.9.0-beta.2`, `v0.9.0-beta.1`, `v0.8.0-beta.1`, `v0.7.0-beta.1`, `v0.6.0`, and so on. Notes:

- `quill/core/release_tags.py` (19-27) *declares* the convention `quill-<app key>-v<version>` with Lite as `quill-quilllite-v1.0.0`. The real tags use **`quill-lite-v`**, and `check_sibling_versions.SITES` (59-66) uses `quill-lite-v` too. `release_tags.release_tag()` is only called from tests. The plan grandfathers `lite` as the tag key.
- **QUILL:** `build/version.toml` says `base_version = "1.0.0"`, `channel = "stable"`, and `quill/__init__.py:26` says `__version__ = "1.0.0"`. The newest published tag is **v0.9.0-beta.3**. The request said "0.9.0 Beta 2", so 1.0.0 looks like the first QUILL Stable and has not shipped yet. This needs confirming (open question 9).
- **App versions in source:** Radio `quill/apps/radio.py:39` `_VERSION = "3.2.0"` (published 3.0.4). Lite `quill/core/lite/__init__.py:45` `APP_VERSION = "1.2.0"` (published 1.1.2). Cast `quill/apps/podcasts_menu.py:24` `APP_VERSION = "2.0.0"` (never published). The build scripts agree: `standalone/radio/scripts/build_release.ps1:50`, `standalone/quilllite/scripts/build_release.ps1:54`, `standalone/cast/scripts/build_release.ps1:31`.

### 1.4 How a build knows what it is

- **QUILL:** `build/version.toml` (`channel` = dev | alpha | beta | rc | stable) feeds `tools/generate_build_info.py`, which writes `quill/_build_info.py` (`CHANNEL`, `DISPLAY_VERSION`, `PEP440_VERSION`, `GIT_SHA`, `BUILD_STAMP`). That is read by `quill/build_info.py` (`is_release_build` 84-86; `resolve_running_version` 117-135, which returns the display form, for example "1.0.0 Beta 1").
- **Sibling apps:** there is no channel metadata at all. The installed version comes from the installer's marker `{app}\quill-app-version.ini` (`quill/core/app_version.py`: `MARKER_NAME` 53, `installed_version` 87-100), because the runtime's code constant cannot be trusted (see 1.6). It is written by `standalone/radio/installer/quill-radio.iss:142` and `quilllite.iss`, **but not by Cast's installers** (a grep for `quill-app-version.ini` finds only Radio and Lite).
- **Cast passes the wrong version.** It calls `check_for_app_updates(current_version=_VERSION)` with the *code constant* (`quill/apps/podcasts.py:598-600` and `quill/apps/podcasts_menu.py:470-473`). Radio correctly passes `installed_version(_VERSION)` (`radio.py:1048-1054`, `radio_menu_bar.py:456-461`).

### 1.5 Release pipelines

- **QUILL:** `.github/workflows/windows-release.yml` runs on `v*` tags (3-7). It **hard-codes `prerelease: true` and the title `"QUILL for All ${{ github.ref_name }} Beta"`** (158-168). It then runs `generate_update_feed.py` with `QUILL_FEED_SIGNING_KEY` (175-186) and pushes the v1 feed to `main` (188-194). The v1 feed has no channel, so **once 1.0.0 Stable ships, the next Beta tag would be offered to every Stable user through the manifest path** (`main_frame_updates.py:174-194` offers any newer `manifest.version` regardless of `beta_updates`).
- **Sibling apps:** built locally by `standalone/<app>/scripts/build_release.ps1`, which produces a portable zip and a Setup .exe and runs `Assert-QuillSiblingVersions` (`radio/build_release.ps1:73`) and `Assert-QuillRuntimeHasModule`. They are published by hand with `gh` (release bodies are in `build/github-release-lite-1.1.x.md`). `standalone/README.md:76-82` is stale: it says each updater polls its own repo, but all apps now share `Community-Access/quill`.
- **Runtime:** `standalone/runtime/build_runtime_installer.ps1:89-105` republishes `QuillVille-Runtime-Setup.exe` under the **moving tag `runtime-latest`** (`--latest=false`). Native launchers self-heal a missing runtime from it (`scripts/build_native_launcher.py:54-59`).
- **Release notes:** `scripts/extract_release_body.py` reuses `quill/core/release_notes.extract_version_section`, so the GitHub body, the v1 feed `notes` and What's New all match. Sibling apps keep `standalone/<app>/docs/CHANGELOG.md` and `release-notes-*.md`.
- **Test builds:** `windows-test-build.yml` produces unsigned portable artifacts with 14-day retention. These are effectively today's "dev" builds and are not published.
- **Version gates:** `tests/unit/scripts/test_app_versions_agree.py` (GATE-APPVER: module constant, pyproject, build script, Inno and README agree; covers radio, converter, weather, inkwell and Lite, **not Cast**). `scripts/check_sibling_versions.py` (GATE-SIBVER: no sibling may be ahead of its newest published tag unless the build is releasing it; **Cast is not in `SITES`**).

### 1.6 The shared QuillVille Runtime (the hard constraint)

- `standalone/runtime/runtime_launcher.py:1-12`: one PyInstaller onedir holds CPython, wx and the **whole `quill` package**. Every app is `QuillVilleRuntime.exe -m quill.apps.<app>`.
- `installer/shared-runtime.iss`: `RuntimeDir` = `{localappdata}\QuillVille\Runtime\<major>` (139-149). `RuntimeNeedsInstall` (216-233) installs only if the payload's build stamp is newer than the installed one: "installing an older sibling app never downgrades the shared runtime". The Python mirror is `quill/core/runtime_marker.py:needs_install` (74-103).
- **Consequence for channels.** Install Radio 3.3.0-beta.1 and its runtime, which contains main-branch Lite and Cast code, replaces the runtime that Stable Lite and Cast run on. Reinstall Radio 3.2.0 Stable and `RuntimeNeedsInstall` skips the older runtime, so **Radio keeps running Beta code after "rolling back"**. This is the same class of bug GATE-SIBVER was written for (`check_sibling_versions.py:1-20`), made worse.
- Reference counting: `quill/core/runtime_refs.py` (keyed by runtime version) and `quill/core/runtime_apps.installed_apps()` (which apps share this runtime).
- The native launcher resolves `%LOCALAPPDATA%\QuillVille\Runtime\<suite-major>\` (`quill/native/launcher/launcher.c:19-23`, `runtime_resolve.c`) and exports `QUILL_LAUNCHER_DIR` (132-148).
- Cast's `build_release.ps1` does not build the runtime itself (`docs/design/2026-08-17-runtime-layering-delta.md:265-266`).
- **QUILL (the editor) is a self-contained frozen `quill.exe`** (`self_update.py:187-201`). It does not use the shared runtime, so it can get channels first.

### 1.7 Stored data, schemas and "safe to go back"

- **QUILL settings** use the full versioned-delta contract. `quill/core/settings_migration.py:63` has `SETTINGS_SCHEMA_VERSION = 2`. `is_future_settings_document` (226-237) and `quill/core/versioned_store.py:80-83,105-109` mean a file from a *newer* schema is read but **never rewritten**. `reconcile_unknown_overrides` (247+) carries unknown keys forward. Migrations back up the original to `migration-backups/` (`quill/core/migration_backup.py`, keeps 5). This is the best foundation in the repo.
- **QUILL Lite settings:** `quill/core/lite/settings.py:56` has `SCHEMA = 1`. `load` (559-576) skips unknown keys, and `save` (579-588) writes only known deltas, so **an older Lite silently drops settings a newer Lite added**. That is lossy, but it does not break anything. Lite data lives in `%LOCALAPPDATA%\QuillLite` (`quill/core/lite/paths.py`).
- **Radio and Cast stores** (`radio_favorites.json`, `radio_history.json`, `podcasts_library.json`, `podcast_history.json` and others) have **no schema stamp**. `quill/tools/persistence_audit.py` classifies them as `"content"` (177, 229-230, 258). They live in the shared `%APPDATA%\Quill` folder alongside QUILL's data. Cast's backup deliberately includes the Radio-shared `media_bookmarks.json` and `radio-listens.json` (`quill/core/podcasts/backup.py:52-73`).
- **Radio's catalog** is SQLite with a `schema_version` meta row. A mismatch triggers a rebuild, never a migration (`quill/core/radio/catalog/store.py:255-262`), so it is derived data and safe to downgrade.
- **Existing backup features to reuse:**
  - Radio: `quill/core/radio/backup.py` (`create_backup` 87-127, `.qrbackup`, manifest `schema` 1, refuses a newer schema on restore at 138-140).
  - Cast: `quill/core/podcasts/backup.py` (`.qcbackup`, same shape).
  - Lite: Tools > Back Up Settings (`quill/apps/lite_window_settings_backup.py`, `.qsf` via `export_portable`).
  - QUILL: `quill/core/setup_transfer.py` (covers all apps' files, item list at 78-81), `migration_backup.py`, and document `restore_points.py`.

### 1.8 Preferences, Help menus and accessibility conventions

- **QUILL:** `settings_specs.py:2124-2146` defines `auto_check_updates` and `beta_updates` ("Get beta updates", admin page). `main_frame_preferences.py:725-730` pops `_confirm_beta_channel` when the box is checked. The Help menu has "Check for &Updates..." and "Chec&k for GLOW Updates..." (`main_frame_menu.py:3324-3327`). The consent dialog is `main_frame_updates.py:583-608`. QUILL also **auto-enrolls into Beta** when it finds it is running a prerelease (214-222), and the **silent startup check auto-downloads** (237-240).
- **Lite:** `quill/apps/lite_preferences.py:225-238` has "Look for &updates when QUILL Lite starts". The comment there notes every other letter is taken (GATE-14). Help > Check for Updates is Ctrl+Alt+U (`lite_updates.py:192-196`).
- **Radio:** `radio_preferences.py:195-211` uses a `PreferenceCheckbox` list in the shared `quill/ui/app_preferences_dialog.py`, which also offers `PreferenceChoice` (line 78). Help menu: "Check for Up&dates...\tCtrl+Alt+U" (`radio_menu_bar.py:451`).
- **Cast:** `AppRow` rows in `quill/apps/podcasts_preferences.py:30-60` and `quill/ui/podcasts/preferences_window.py:123`. Help menu: "&Check for Updates...\tCtrl+Alt+U" (`podcasts_menu.py:465`).
- **CLAUDE.md rules the new UI must meet:**
  - Every modal goes through `_show_modal_dialog` and `apply_modal_ids`, with Close bound by `dialog_contract.bind_close_button` (line 162).
  - Every enabled menu item shows a keyboard route through `_menu_label` and `APP_KEYMAPS` (164).
  - GATE-13: speak only what the screen reader cannot know (166).
  - GATE-14: no duplicate access keys; OK, Cancel and Close carry none (168).
  - F1 help is inline `SetHelpText` at construction, per-app `surface_help` catalogues, and `docs/f1-help-reference.md` is regenerated (170).
  - GATE-REACH (223), GATE-SETDOC (207), GATE-EC coded errors (215), the network egress audit (GATE-9).
- **Helpers that already exist:** `quill/core/net_metered.py` (`may_download(settings, automatic=True)`, 68; "unknown means unmetered"), `quill/core/quiet_hours.py` (`silences(hours, kind, now, high_priority)`, 164; shared by Radio and Cast), `quill/core/family_preferences.py` (opt-in sharing of a few prefs between apps).

### 1.9 Hazards found during the survey (fix in Phase 0 whatever else happens)

1. **Pagination time bomb.** `fetch_app_releases`, `fetch_releases` and Lite all call `/releases` with no `per_page`, so GitHub returns **30**. One repo now hosts about 20 releases for several apps. Once betas or dev builds are published there, Stable releases fall off page 1 and installed copies **stop seeing updates without saying so**. This applies to copies already installed (Radio 3.0.4, Lite 1.1.2), so new publishing must respect it (see section 9).
2. `stable[0]` in `app_shell.py:883-884` and `lite_updates.py:115-116` trusts GitHub's order (newest *created*), not version order.
3. The v1 manifest has no channel (1.5), and `windows-release.yml` marks every QUILL tag as a prerelease titled "Beta" (1.5).
4. Cast compares the code constant, not the installed marker, and its installers don't write the marker (1.4).
5. Lite drops unknown settings on save (1.7).
6. v1 feed signature is optional; sibling apps have no signed feed at all; hashes come from the same server as the files.

---

## 2. Channels

### 2.1 Names and meanings (user-facing wording)

| Channel | One-line meaning (shown in the chooser) | Who it is for |
|---|---|---|
| **Stable** | "The version we recommend. It has been checked with JAWS and NVDA, and it is what most people use." | Everyone. The default. |
| **Beta** | "New features a few weeks early. Mostly finished, but some things may not work right yet." | People who want to help find problems and can live with a rough edge. |
| **Dev** | "Builds from the work in progress, sometimes several a week. Things will break. Only choose this if a developer asked you to, or you enjoy testing." | Testers and developers. |

Rules:

- **Per app, default Stable.** The chooser also offers "Also move my other QuillVille apps on this computer" with one checkbox per installed app, all unchecked by default.
- **A build never chooses a channel for you without telling you.** This replaces today's silent auto-enroll (`main_frame_updates.py:214-222`). If a pre-release build is started with no channel stored (for example, a tester installed a Beta by hand), the app sets the channel to that build's *birth channel* once and says so: "You installed a Beta version, so QUILL will offer you Beta updates. You can change this in Help > Release Channel."
- **Feed-only states** (never chosen in the UI): `revoked` (pulled) and the internal flag `pending_return` ("on Beta, waiting for Stable to catch up").

### 2.2 How a build knows its identity: baked build metadata

Make QUILL's `build/version.toml` model the family model.

- **New per-app source of truth:** `build/apps/<app>.toml` (radio, quilllite, cast; QUILL keeps `build/version.toml` and gains the same keys):
  ```toml
  app = "radio"
  base_version = "3.3.0"
  prerelease = "beta"          # "", "dev", "alpha", "beta", "rc"
  prerelease_number = 2
  birth_channel = "beta"       # informational: where this build is first listed
  ```
- **Generator:** `tools/generate_build_info.py` becomes `tools/generate_build_info.py --app <key>` and writes:
  - `quill/_build_info.py` for QUILL (unchanged shape plus `DATA_FORMATS`, `READS_FORMATS` and `BIRTH_CHANNEL`).
  - **`build/app-build.json`** for each sibling build, which is then embedded in three places: the Inno `{app}` folder as `quill-app-build.json`, the portable zip root, and the GitHub release as an asset.

  ```json
  {"app":"radio","version":"3.3.0-beta.2","birth_channel":"beta",
   "git_sha":"1a2b3c4","build_stamp":"20261003.1","built_at":"2026-10-03T14:02:11Z",
   "runtime":{"python":"3.13","build":"2026-10-03T13:40:00Z"},
   "carries":{"quilllite":"1.2.0","cast":"2.0.0","radio":"3.3.0-beta.2"},
   "data_formats":{"radio.favorites":2,"radio.history":1,"shared.media_bookmarks":1},
   "reads_formats":{"radio.favorites":2,"radio.history":1,"shared.media_bookmarks":1}}
  ```

- **Extend the installer marker** `quill-app-version.ini` (from `quill-radio.iss:142`) with `[app] channel=` (the channel the install was made *for*, passed in as `/CHANNEL=` by the updater, see 6.6) and `[runtime] slot=` (see 6.5). `app_version.read_marker` grows `read_channel()` and `read_runtime_slot()`. Cast's installers must start writing this marker (Phase 0).
- **Portable zips** gain the same `quill-app-version.ini` at the root (`build_portable.py`). Today a portable copy has no marker and relies on the code constant.
- **Why the channel is not compiled into code:** promotion must not need a rebuild. The *effective channel* is the user's setting. `birth_channel` is only used for the first-run default and in About ("3.3.0, first released on Beta").

### 2.3 Version and tag scheme

| Kind | Version | Tag | Can be listed on |
|---|---|---|---|
| Stable or candidate | `3.3.0` | `quill-radio-v3.3.0` | Beta first, then Stable (promotion) |
| Beta | `3.3.0-beta.2` | `quill-radio-v3.3.0-beta.2` | Beta, Dev |
| Release candidate (optional) | `3.3.0-rc.1` | `quill-radio-v3.3.0-rc.1` | Beta, Dev |
| Dev | `3.3.0-dev.20261003.1` (the last number is the build of the day); the SHA goes in build metadata as `+g1a2b3c4`, display only | `quill-radio-v3.3.0-dev.20261003.1` (only if published to GitHub; see 9.3) | Dev only |
| QUILL | `1.1.0-beta.1` | `v1.1.0-beta.1` (QUILL keeps unprefixed tags, `release_tags.py:19-21`) | as above |

**Ordering rule: PEP 440 semantics with semver spelling.** `dev < alpha < beta < rc < final`, numeric parts compare as numbers, and build metadata after `+` is ignored for order but kept for identity. For example `3.3.0-dev.20261003.2 < 3.3.0-beta.1 < 3.3.0-rc.1 < 3.3.0 < 3.3.1-dev.…`. Plain semver would put `dev` after `beta` (ASCII), which is wrong for us. Say so in the module docstring.

**Build numbers (decided 2026-10-04).** The owner asked for the same release number to ship more than once ("version numbers should also have build numbers so we can ship multiple versions of the same release number"). Every version now has a build: canonical `X.Y.Z[-pre.N]+B` (`3.2.0+2`), shown to people as "3.2.0 (build 2)" in About, Update History, update notices and the Release Channel window; release notes, changelog headings and file names keep `3.2.0`. A *numeric* first identifier after `+` is the build and breaks ties when everything else is equal (`3.2.0-rc.1+40 < 3.2.0 < 3.2.0+1 < 3.2.0+2 < 3.2.1`; a release with no build is build 0); other metadata (`+g1a2b3c4`) is still identity only. **Tags spell the build as a pre-release identifier, not with `+`:** `quill-radio-v3.2.0-build.2`, `v1.1.0-beta.1.build.3`. Copies installed before build numbers read `+` in a sibling tag as no version (`_app_version_from_tag` returns the whole tag, which parses as 0.0.0) and in QUILL's tag as part of the patch (`v1.0.0+2` was 1.0.2); they read `-build.2` as a pre-release of 3.2.0, which a copy on an older release still sees as newer, and which never outranks a later release. A pre-build copy already on 3.2.0 is not offered the 3.2.0 rebuild (accepted); it gets builds from its next update on. The first build of a version is tagged `-build.1` too, so those copies take the newest build rather than the build-less one. Every reader accepts both spellings and the existing build-less tags. The build lives beside each app's version constant (`_BUILD`, `APP_BUILD`, `quill.__build__`), `build_release.ps1 -Build` and `publish_release.py --build` default to the next build after the newest published tag for that version (`release_tags.next_build`), installers write `[app] version_build=` beside `version=` and stamp `VersionInfoVersion` `X.Y.Z.B`, the v2 feed carries `3.2.0+2`, and promotion names one build. Runbook: `docs/release/RELEASE.md`, "Build numbers".

**New module `quill/core/versioning.py`** (wx-free, the one parser):

- `ReleaseVersion.parse(text)` accepts tags (`quill-radio-v3.3.0-beta.2`, via `release_tags.parse_release_tag`), semver-shaped strings, PEP 440 (`1.0.0b1`, `1.0.0.dev20261003`, `0.8.0b1.post1`) and display forms ("1.0.0 Beta 1", "1.0.0 Release Candidate 2", "1.0.0 Dev").
- Fields: `base: tuple[int,int,int]`, `stage: Literal["dev","alpha","beta","rc","final"]`, `numbers: tuple[int,...]`, `post: int`, `local: str`.
- `__lt__` and `key()`, `is_prerelease`, `display()` ("3.3.0 Beta 2"), `tag(app_key)`, `semver()`.
- `updates._version_tuple` and `is_newer_version` become thin wrappers so every existing caller and test keeps working. `check_sibling_versions.parse_version` switches to it.
- `release_tags.py` documents the grandfathered `lite` key: `RELEASE_TAG_KEYS = {"quilllite": "lite"}` with `release_tag("quilllite", …) == "quill-lite-v…"`.

---

## 3. The release feed (v2, signed, per app)

### 3.1 Where

- **Files:** `docs/site/updates/v2/<app>.json` and the detached signature `<app>.json.sig`, served at `https://community-access.github.io/quill/updates/v2/radio.json`. One file per app keeps each request small and means a request reveals only which app is asking, as today.
- **Index:** `docs/site/updates/v2/index.json`, signed, listing the apps and their feed paths. Used by "switch all my apps" and by future apps.
- **Binaries stay on GitHub Releases** (`github.com` and `objects.githubusercontent.com` are already trusted, `updates.py:975-984`), with `prerelease: true` for Beta and Dev listings so the updaters already installed keep ignoring them (section 9).

### 3.2 Signing

- **Reuse the existing feed keypair.** `quill/core/feed-pub.key` is the public half. The secret is `QUILL_FEED_SIGNING_KEY` in the repo and `~/.config/quill/quill-feed-priv.key` locally (`docs/signing.md:44-101`).
- **Sign the exact bytes, not a canonical re-encoding.** Use a minisign-shaped sidecar, generalising `quill/tools/signing.py` with a `key_id` and key-path parameter (`KEY_ID = "quill-feed-2026"`). Signing the bytes removes the class of bug where publisher and client canonicalise differently (`updates.py:648-652` records that history).
- **Key rotation.** Clients carry a *list* of trusted feed keys (`quill/core/feed-pub.keys`, one base64 key per line) so a rotation can be double-signed for one release cycle. This extends `docs/signing.md:94-101`.
- **v2 has no unsigned fallback.** A missing or invalid signature is "couldn't check", never "accept".

### 3.3 Manifest schema (`quillville-release-feed/2`)

```json
{
  "format": "quillville-release-feed/2",
  "app": "radio",
  "app_name": "Quill Radio",
  "sequence": 118,
  "generated_at": "2026-10-20T15:00:00Z",
  "expires_at": "2026-12-19T15:00:00Z",
  "security_floor": "3.0.4",
  "channels": {
    "stable": {"current": "3.3.0"},
    "beta":   {"current": "3.4.0-beta.1"},
    "dev":    {"current": "3.4.0-dev.20261019.2"}
  },
  "releases": [
    {
      "version": "3.3.0",
      "tag": "quill-radio-v3.3.0",
      "channels": ["stable", "beta"],
      "history": [
        {"channel": "beta",   "at": "2026-10-10T12:00:00Z"},
        {"channel": "stable", "at": "2026-10-20T15:00:00Z", "by": "promote_release.py"}
      ],
      "published_at": "2026-10-10T12:00:00Z",
      "notes_url": "https://github.com/Community-Access/quill/releases/tag/quill-radio-v3.3.0",
      "notes_summary": "Plain-text summary, at most 4000 characters (update_notice.MAX_NOTE_CHARS).",
      "assets": [
        {"kind": "installer", "name": "Quill-Radio-Setup-Shared-3.3.0.exe",
         "url": "https://github.com/Community-Access/quill/releases/download/quill-radio-v3.3.0/Quill-Radio-Setup-Shared-3.3.0.exe",
         "size": 189234112, "sha256": "…", "authenticode_subject": "Jeffrey Bishop"},
        {"kind": "portable", "name": "Quill-Radio-Portable-3.3.0.zip", "url": "…", "size": 441000000, "sha256": "…"}
      ],
      "runtime": {"python": "3.13", "build": "2026-10-09T18:22:00Z"},
      "carries": {"quilllite": "1.2.0", "cast": "2.0.0"},
      "data_formats":  {"radio.favorites": 2, "radio.history": 1, "shared.media_bookmarks": 1},
      "reads_formats": {"radio.favorites": 2, "radio.history": 1, "shared.media_bookmarks": 1},
      "can_roll_back_to": ["3.2.0"],
      "min_safe_downgrade": "3.2.0",
      "min_upgrade_from": "3.0.0",
      "revoked": false,
      "revoked_reason": "",
      "replacement": "",
      "advisories": []
    }
  ]
}
```

What the less obvious fields are for:

- **`sequence`** (an integer that always goes up) and **`expires_at`** defend against replay and freeze attacks (8.2). The client stores the highest `sequence` it has seen.
- **`security_floor`**: builds below this are told to update (security), and are never rollback targets.
- **`can_roll_back_to`** and **`min_safe_downgrade`** are *computed by the publisher* from the format tables of every listed release (5.2), so the answer is the same on every machine. The client still re-checks against its own ledger, because the ledger may hold formats written by a *sibling* app.
- **`min_upgrade_from`** lets a release require a stepping stone. The client then offers the stepping stone first.
- **`advisories`** carries the existing feature kill-switch forward (`FeatureAdvisory`, `updates.py:76-94`), per release.
- **QUILL** gets `updates/v2/quill.json` and keeps generating the v1 feed for old clients (section 9).

### 3.4 Client parsing

`quill/core/updater/feed.py`:

- `fetch_feed(app_key) -> ReleaseFeed`. HTTPS only, `_validate_remote_url`, signature checked against `feed-pub.keys` before JSON parsing, schema-validated, rejects a `sequence` lower than the stored one, and marks the feed `stale` past `expires_at`.
- `ReleaseFeed.for_channel(ch)`, `.release(version)`, `.rollback_targets(...)`.
- The last good feed is cached at `<app data>/updates/feed-cache/<app>.json` together with its `.sig`, and re-verified on read. This is what offline mode uses.
- The override env var `QUILL_UPDATE_FEED_BASE` is used for rehearsals, in the same style as the existing `QUILL_UPDATE_API_URL` and `QUILL_UPDATE_MANIFEST_URL` (`updates.py:28-34`). It can only redirect *where to look*. Signatures and trusted hosts still apply.

---

## 4. Promotion: Dev to Beta to Stable without rebuilding

### 4.1 Principles

- **A build is made and signed once.** Promotion edits the GitHub release flags and the signed feed. It never touches the bytes. The SHA-256 in the feed entry stays the same from the first listing onwards, and promotion *re-verifies* it.
- **Stable accepts only final-numbered builds** (`3.3.0`). A `-beta.N` build is never relabelled. To ship a final, build a **candidate** with the final number, list it on Beta, let it soak, then promote it. This is the "release candidate as final bits" model, and the only one that is honestly "no rebuild".
- **Dev to Beta** is allowed for any build (a dev build that turned out good can be put on Beta as-is, keeping its dev version).

### 4.2 Scripts

New, wx-free, unit-tested:

1. **`scripts/publish_release.py`** (first listing). Called from `build_release.ps1 -Publish -Channel dev|beta` and from `windows-release.yml`.
   - Hashes the dist assets locally (never trusts GitHub's digest).
   - Creates the GitHub release: Beta and Dev are `--prerelease`, and every sibling and Dev release uses `--latest=false`. Uploads the assets and `app-build.json`.
   - Writes the feed entry with `channels=[<channel>]`, bumps `sequence`, re-signs, and writes `docs/site/updates/v2/<app>.json`.
   - Commits on a branch and opens a PR (or pushes straight to `main` from the workflow, matching `windows-release.yml:188-194`).
2. **`scripts/promote_release.py --app radio --version 3.3.0 --to stable [--dry-run] [--notes-file …] [--skip-soak "reason"]`**
3. **`scripts/revoke_release.py --app radio --version 3.4.0-beta.1 --reason "…" [--replacement 3.4.0-beta.2]`**. Sets `revoked`, removes the build from `channels.*.current` (falls back to the previous build), and marks the GitHub release title "(withdrawn)". It does **not** delete assets, so people who already have the build can still roll forward or back.
4. **`scripts/rollup_release_notes.py --app radio --from 3.2.0 --to 3.3.0`**. Builds the Stable notes from the Beta sections in between (4.4).
5. **`scripts/feed_tool.py verify|show|resign`**. A maintenance CLI, also used by the CI gate.

### 4.3 Checks `promote_release.py` runs (all must pass; `--dry-run` prints the list)

| # | Check | Source / reuse |
|---|---|---|
| P1 | The release exists, is not a draft and not revoked; the tag matches `release_tags` | `gh release view --json` |
| P2 | Every asset re-downloaded or HEADed: size and **SHA-256 match the feed entry** | `release_assets._download_resumable` + hash |
| P3 | Feed signature valid; `sequence` will increase | `feed_tool verify` |
| P4 | For Stable: version is final (`ReleaseVersion.stage == "final"`) | `versioning.py` |
| P5 | For Stable, always: Authenticode-signed installer and every `.exe` in the portable zip (embedded signature; `signtool verify` where installed). Decided 2026-10-04: Stable is never unsigned | `scripts/code_signing.py` `asset_is_signed` |
| P6 | Version agreement inside the bits: `app-build.json.version` == the tag == `quill-app-version.ini` inside the portable zip == the Inno `VersionInfo` | GATE-APPVER logic, applied to *artifacts* rather than source |
| P7 | **Sibling check, channel-aware (GATE-SIBVER-CH):** for Stable, every entry in `carries` must be ≤ that sibling's newest *Stable* listing; for Beta, ≤ its newest Beta-or-Stable. The promoted runtime lands in that channel's runtime slot, where siblings on the channel will run it (6.5). | `check_sibling_versions.disagreements`, fed by the feed instead of tags |
| P8 | Release notes present: a CHANGELOG section for this version (`release_notes.extract_version_section` returns non-empty) **and**, for Stable, a rolled-up `standalone/<app>/docs/release-notes-<x.y>.md` | `scripts/extract_release_body.py` |
| P9 | **Screen-reader sign-off** for Stable: `docs/qa/signoffs/<app>-<version>.md` exists with `Result: pass`, a tester, screen readers and versions, and a date, plus at least the 20-minute pass IDs checked (for Radio: R-02, R-04, R-08, R-14, R-18, R-37, R-45, R-55, R-69, R-73 from `docs/qa/radio-signoff.md`). New sign-off sheets are generated from the checklists by `scripts/gen_signoff_html.py`, extended to write the results stub. | `docs/qa/*-signoff.md` |
| P10 | Soak time: at least 7 days on Beta before Stable, at least 1 day on Dev before Beta (configurable in `build/release-policy.toml`; `--skip-soak "reason"` is recorded in the feed history) | feed `history` |
| P11 | Data formats: compute `can_roll_back_to` and `min_safe_downgrade` for the new Stable; **warn** if the promotion makes the previous Stable an unsafe target, and print exactly which format moved | 5.2 |
| P12 | Docs build gates pass for the app's docs (`check_docs_artifacts.py`, GATE-SITE-LINKS) | existing |
| P13 | Runtime build referenced in `runtime` exists in the release's assets or as a `runtime-<channel>` tag (6.5) | `gh` |

Actions on success:

1. `gh release edit <tag> --prerelease=false --latest=false` (for QUILL v-tags, `--latest` on Stable only, because "the editor's release train owns Latest", `build_runtime_installer.ps1:89-92`).
2. Append "Promoted to Stable on 20 October 2026" to the release title and body, and replace the body with the rolled-up notes.
3. Add `stable` to the entry's `channels`, set `channels.stable.current`, recompute rollback fields, bump `sequence`, sign, and commit.
4. Republish the runtime installer under `runtime-stable` (the old `runtime-latest`, see 6.5) if this release carries a newer runtime build.
5. Write an entry to `docs/release/promotions.log.md` (an audit trail in the repo).

### 4.4 Workflow with manual approval

**`.github/workflows/promote-release.yml`**: `workflow_dispatch` with inputs `app` (choice), `version`, `to` (dev | beta | stable), `dry_run` (boolean).

- **Job 1 `checks`:** runs `promote_release.py --dry-run` and uploads the report.
- **Job 2 `promote`:** `needs: checks` and `environment: stable-promotion` (or `beta-promotion`). The GitHub Environment has **required reviewers = the owner**, so nothing reaches Stable without a person pressing Approve. Secrets: `QUILL_FEED_SIGNING_KEY`; `GITHUB_TOKEN` with `contents: write`.
- **The same script runs locally.** This matters because sibling apps are built on the owner's machine. Locally it uses `~/.config/quill/quill-feed-priv.key`.

Also, **`windows-release.yml` stops hard-coding Beta.** It reads the channel from `build/version.toml` (`prerelease` / `birth_channel`), sets `prerelease:` and the title from it, and calls `publish_release.py`.

### 4.5 Release notes and changelog conventions

- **CHANGELOG headings** (one convention for all apps, parsed by `release_notes._HEADING`):
  `## 3.3.0-beta.2 (Beta) - 2026-10-03`, `## 3.3.0 (Stable) - 2026-10-20`.
- **Beta notes say what changed since the previous Beta**, plus a short "Known rough edges" list (required, even if it says "none known").
- **At promotion**, `rollup_release_notes.py` writes the Stable section "What's new since 3.2.0" by merging every Beta section from 3.3.0-beta.1 through the candidate, removing "fixed a bug introduced in beta.1" lines (marked `[beta-only]` in the source), and putting **"Before you update"** at the top whenever a data format moved: "This version saves your favorites in a newer way. Once you update, going back to 3.2.0 means restoring a copy." The feed's `notes_summary` is generated from the same text.
- **Notes are written for people:** plain words, second person, no commit hashes. `scripts/plain_language_lint.py` runs on them as part of P8.

---

## 5. "Back to Stable only if safe"

### 5.1 Definitions

- **Data format:** a named on-disk shape with an integer version. The registry lives in **`quill/core/data_formats.py`**:
  ```python
  @dataclass(frozen=True)
  class DataFormat:
      id: str               # "radio.favorites"
      owner: str            # app key, or "shared"
      files: tuple[str, ...]
      location: str         # "quill_data" | "lite_data" | "runtime"
      current: int          # version this build WRITES
      reads_up_to: int      # highest version this build can READ without loss
      lossy_reads: tuple[int, ...] = ()  # versions it reads but would drop fields from
  FORMATS: tuple[DataFormat, ...] = (
      DataFormat("quill.settings", "quill", ("settings.json",), "quill_data", 2, 2),
      DataFormat("quill.keymap", "quill", (...), "quill_data", ...),
      DataFormat("lite.settings", "quilllite", ("settings.json",), "lite_data", 1, 1),
      DataFormat("radio.favorites", "radio", ("radio_favorites.json",), "quill_data", 1, 1),
      DataFormat("radio.history", "radio", ("radio_history.json",), "quill_data", 1, 1),
      DataFormat("cast.library", "cast", ("podcasts_library.json",), "quill_data", 1, 1),
      DataFormat("cast.history", "cast", ("podcast_history.json",), "quill_data", 1, 1),
      DataFormat("shared.media_bookmarks", "shared", ("media_bookmarks.json",), "quill_data", 1, 1),
      # derived data (radio catalog SQLite, caches) is NOT listed: it is rebuilt, never migrated
  )
  ```
  The format version is the **contract**, not the JSON layout. It is bumped only when an older build would *misread or lose* data. Additive fields that older builds ignore safely are recorded as `lossy_reads` for Lite (whose `save` drops unknown keys) and as no change for QUILL (whose `reconcile_unknown` preserves them). The Radio and Cast files do **not** need a stamp inside them on day one. The ledger (below) is enough, and changing their bytes is a risk of its own.
- **Ledger:** `<data dir>/data-format-ledger.json`, kept by **`quill/core/data_format_ledger.py`**. There is one for the shared `%APPDATA%\Quill` folder (QUILL, Radio, Cast, Inkwell) and one in `%LOCALAPPDATA%\QuillLite`, and one inside a portable `data` folder.
  ```json
  {"version": 1, "formats": {"radio.favorites": {"high": 2, "by": "radio 3.4.0-beta.1", "at": "2026-10-21T09:00:00Z"}}}
  ```
  Each app calls `ledger.record_running_build(app_key)` at startup, *before* its first save. It raises `high` to `max(high, current)` for each format the app owns or shares. The ledger only goes up, except through an explicit snapshot restore (5.4), which lowers it to match the restored copy. The ledger is classified `framework` in `persistence_audit.py`.
- **Safety function** (pure, wx-free, table-tested), in `quill/core/updater/policy.py`:
  ```python
  def downgrade_verdict(target: FeedRelease, ledgers: list[Ledger]) -> Verdict
  # Verdict.SAFE                     all formats: target.reads_formats[f] >= ledger.high[f], no lossy reads
  # Verdict.SAFE_WITH_LOSSES(items)  readable, but some newer fields would be forgotten (Lite settings)
  # Verdict.UNSAFE(blockers)         some format f has ledger.high[f] > target.reads_formats.get(f, 0)
  ```
  A format the target has never heard of (missing from `reads_formats`) counts as 0, which is unsafe if the ledger has it. That is the conservative choice.

Precisely: **going back to Stable build T is safe if and only if, for every data format recorded in every ledger the app touches, T's highest readable version is at least the highest version ever written on this machine, T is not revoked, and T is at or above `security_floor`.**

### 5.2 Publisher side

`promote_release.py` and `publish_release.py` compute `can_roll_back_to` for each release as the listed Stable releases T where, for every format in this release's `data_formats`, `T.reads_formats[f] >= data_formats[f]`. `min_safe_downgrade` is the oldest of those. This gives the dialog an answer before anything is downloaded. The client still runs `downgrade_verdict` against the real ledger, because a *sibling* (Cast Beta writing `shared.media_bookmarks` v2) can make Radio's rollback unsafe even when Radio's own entry says it is safe.

### 5.3 What the user is offered when it's not safe

1. **"Wait for Stable"** (the default). Sets `pending_return = true`. The channel *shown* is "Stable (waiting for it to catch up with your version)". The app **stops taking Beta updates** unless the user checks "Keep getting Beta fixes while I wait" (unchecked by default; checking it may move the goalposts, and the dialog says so). When `channels.stable.current >= installed version` and the downgrade verdict for that build is no longer needed (it is an *upgrade* or the same version), the app moves across by itself:
   - If it is the same bits (the candidate was promoted), it simply flips the channel and notes it in Update History.
   - If it is a newer Stable, it is offered as a normal update.
   - Either way it is spoken once: "Stable has caught up. Quill Radio is back on the Stable channel."
2. **"Use the copy from <date>"**: restore the automatic snapshot taken when you joined Beta (5.4), then install Stable.
3. **"Stay on Beta"** (Escape): change nothing.

### 5.4 Automatic snapshots ("the copy saved when you joined Beta")

**`quill/core/updater/snapshots.py`** has per-app adapters that reuse the existing backup code:

| App | Snapshot contents | Reuse |
|---|---|---|
| QUILL | settings, keymap, feature flags, abbreviations, menu customisation, Quillin settings (the QUILL rows of `setup_transfer.SetupItem`) | `setup_transfer` item list (`setup_transfer.py:78+`) packaged as a zip; documents are **not** copied (restore points already cover them, and they are not migrated by updates) |
| QUILL Lite | `%LOCALAPPDATA%\QuillLite\*.json` (settings, keymap, sessions, recent) | raw file copy (not `export_portable`, which is selective) |
| Quill Radio | `RADIO_DATA_FILES`; recordings excluded | `radio.backup.create_backup(include_recordings=False)` → `.qrbackup` |
| QUILL Cast | `CAST_DATA_FILES`; downloaded episodes excluded | `podcasts.backup.create_backup` → `.qcbackup` |

- **Stored at:** `<data dir>/channel-snapshots/<app>-<version>-<reason>-<stamp>.<ext>`, where reason is `joined-beta`, `joined-dev`, `before-update` or `before-restore`.
- **Retention:** the latest `joined-*` copy is kept until you are back on Stable and have run it 3 times. The 3 newest `before-update` copies are kept. Everything else is pruned. Size is tiny (tens of KB). The adapters add a "snapshot" entry to `persistence_audit` (`export`).
- **When snapshots are taken:** on joining Beta or Dev (before the channel flips, so a failure aborts the switch with a message); before every install while on Beta or Dev; before a restore (so "nothing is thrown away").
- **Restore order matters,** because the Stable app may be an *old* build that knows nothing about restores:
  1. The current (Beta) app takes a `before-restore` snapshot.
  2. It closes its own stores and writes the snapshot files back (it knows how).
  3. It lowers the ledger to the snapshot's recorded formats (the snapshot stores its ledger alongside).
  4. It launches the install helper for the Stable build and exits.
  The Stable app then opens restored data it can read.
- **Shared files** (`media_bookmarks.json`, `radio-listens.json`, QUILL's shared folder). A restore writes a shared file back only if **no other installed app on Beta or Dev wrote a higher version of that format**. Otherwise the dialog lists it: "Your bookmarks are shared with QUILL Cast, which is still on Beta, so they stay as they are." This is decided by `downgrade_verdict` over the shared ledger plus `channels.json` (6.2).

### 5.5 How the updater refuses an unsafe downgrade

The install helper is never launched for a lower version unless `downgrade_verdict` is `SAFE` or `SAFE_WITH_LOSSES` (confirmed), or a snapshot restore has just completed. The refusal is one sentence plus what to do:

> "Quill Radio did not go back to 3.2.0, because 3.2.0 cannot read the favorites that 3.4.0 Beta saved. Your favorites are unchanged. You can wait for Stable to catch up, or go back using the copy saved on 3 October."

The refusal is a `CodedError` subclass, `UnsafeDowngradeError(code = "QUILL-UPDATE-CHANNEL-UNSAFE-DOWNGRADE")`, for GATE-EC.

---

## 6. The updater

### 6.1 Package layout (wx-free core, thin UI)

```
quill/core/updater/
  __init__.py
  channels.py        Channel enum, labels, descriptions, ChannelState
  versioning.py      (or quill/core/versioning.py, see 2.3)
  feed.py            fetch/verify/cache ReleaseFeed (3.4)
  policy.py          decide(): the whole decision table, pure (6.3)
  app_profiles.py    one UpdaterProfile per app: the join-later seam (6.9)
  data_formats.py / data_format_ledger.py (5.1)
  snapshots.py       (5.4)
  download.py        resumable, hash-verified, metered-aware (6.4)
  apply.py           wraps self_update.begin_self_update + rollback (6.6)
  runtime_slots.py   channel slot selection + checks (6.5)
  history.py         update-history.jsonl (6.8)
  schedule.py        when a silent check may run / may speak (quiet hours, metered)
quill/ui/updates/
  release_channel_dialog.py   chooser + "move my other apps"
  channel_risk_dialog.py      Beta/Dev warning
  return_to_stable_dialog.py  safe / unsafe variants
  update_history_dialog.py
  (reuse) update_notice.py, update_download.py
```

`main_frame_updates.UpdatesMixin`, `AppShell.check_for_app_updates` and `lite_updates.check_for_updates` all become callers of **one** `quill.ui.updates.run_update_check(host, profile, manual: bool)`. The GLOW updater stays separate.

### 6.2 Channel state storage

The family file is **`%LOCALAPPDATA%\QuillVille\channels.json`** (installed copies), or `<portable>\data\channels.json` (portable copies):

```json
{"version": 1,
 "apps": {"radio": {"channel": "beta", "pending_return": false, "keep_beta_while_waiting": false,
                    "joined_at": "2026-10-03T10:00:00Z", "joined_from": "3.2.0",
                    "snapshot": "C:\\...\\channel-snapshots\\radio-3.2.0-joined-beta-20261003.qrbackup"}}}
```

- One file, so "move all my apps" is one write, every app can see its siblings' channels (shared-file restore rules, slot planning), and Lite (in its own data folder) is not left out.
- Each app's own settings get a mirror key for Preferences and documentation (GATE-SETDOC):
  - QUILL: `update_channel` (new `SettingSpec`, a choice; `beta_updates` is kept as a read-only legacy alias for one cycle, see section 9).
  - Lite: `Settings.update_channel` in `quill/core/lite/settings.py`.
  - Radio: `RadioHistory.update_channel` (`quill/core/radio/history.py:179` area, plus `history_store.py`).
  - Cast: `PodcastHistory.update_channel` (`quill/core/podcasts/history.py:70` area).
  - `channels.json` wins if the two disagree. The mirror is written whenever the channel changes.

### 6.3 The decision table (`policy.decide`)

Inputs: installed `ReleaseVersion`, `ChannelState`, `ReleaseFeed` (or a stale or missing one), ledgers, `skipped_versions`, and the current time. Outputs (a tagged union):

| Situation | Decision |
|---|---|
| Installed build is **revoked** | `RevokedOffer(replacement)`: shown even on a silent check, as the one high-priority case |
| Installed < `security_floor` | `SecurityUpdate(target)`: offered on the silent check; never auto-installed |
| Newer build on my channel (or on any *more stable* channel) | `Offer(target)`. Beta users are also offered Stable builds newer than their Beta, because Stable is always acceptable |
| `pending_return` and Stable ≥ installed | `ReturnComplete(target or None)` |
| `pending_return` and Stable < installed | `Waiting(stable_current)`; offers Beta only if `keep_beta_while_waiting` |
| Channel changed to a *less* stable one | `Offer(newest on new channel)` after the risk dialog |
| Channel changed to Stable, Stable < installed | `downgrade_verdict` → `ReturnSafe(target)` / `ReturnSafeWithLosses(target, items)` / `ReturnUnsafe(blockers, snapshot)` |
| Target needs a newer runtime than the slot holds | handled by the installer bundling its runtime; `runtime_slots.plan()` names the slot (6.5) |
| `min_upgrade_from` > installed | `Offer(stepping_stone)` with the sentence "This needs one step first" |
| Nothing newer | `UpToDate(channel, last_checked)` |
| Feed unreachable, cache fresh | `UpToDate(…, offline=True)`: "Couldn't reach the update server just now. As of <date>, you had the newest Beta." |
| Feed invalid (bad signature, lower sequence) | `CheckFailed(reason)`. Never falls back to unsigned data |

### 6.4 Download

`updater/download.py` is built on `release_assets._download_resumable` (`release_assets.py:283-350`):

- Writes to `<data>/updates/<name>.partial` and resumes with HTTP Range across app restarts.
- Verifies **the SHA-256 from the signed feed** (not GitHub's `digest`) and size, then renames to the final name. A mismatch deletes the file and raises.
- Can be cancelled. Progress is spoken at 25, 50 and 75 percent (keeping `main_frame_updates.py:634-646` and `update_download._progress`).
- **Metered connections:** `net_metered.may_download(settings, automatic=True)`. Automatic downloads (QUILL's silent-check auto-download, `main_frame_updates.py:237-240`, and any Beta "download in background" option) are held on a metered connection and noted in Update History: "Held back because you are on a metered connection." A download the user asked for always goes ahead.
- **Disk check:** before downloading, compare free space with the asset size × 2.5 (download plus extraction plus the old copy) and give a plain message if there isn't enough.

### 6.5 The shared runtime: channel slots

**Rule: each channel has its own runtime slot. Within a slot the newest build wins, as today. Across slots nothing is shared.**

- **Slots:** `%LOCALAPPDATA%\QuillVille\Runtime\3.13` (Stable; the existing folder, so nothing moves for anyone), `Runtime\3.13-beta`, `Runtime\3.13-dev`.
- **Installer:** `installer/shared-runtime.iss` gains `/CHANNEL=` handling. `RuntimeDir()` (139-149) appends `-beta` or `-dev` when the channel is not Stable. `RuntimeNeedsInstall` (216-233) is unchanged inside the slot. The installer writes `[runtime] slot=3.13-beta` into `{app}\quill-app-version.ini`. With **no** `/CHANNEL`, the installer uses Stable for final versions and Beta for any pre-release version. This keeps hand installs from the website sensible.
- **Native launcher:** `runtime_resolve.c` reads `slot=` from the ini beside it and resolves `Runtime\<slot>\`, falling back to `<suite-major>` (so behaviour is unchanged when the key is missing). Any app version that offers channels ships the new launcher, so an old launcher is never asked to find a Beta slot.
- **Reference counting:** `quill/core/runtime_refs.py` keys by *slot* (`"3.13-beta"`) instead of by Python version. The existing unregister path in `shared-runtime.iss` (around line 241) removes an unreferenced slot. When your last Beta app returns to Stable, the Beta slot (about 335 MB) is reclaimed.
- **Self-heal:** `runtime-latest` is renamed in practice to **`runtime-stable`**, with `runtime-latest` kept as an alias forever because installed launchers have it compiled in (`build_native_launcher.py:57-59`). Add `runtime-beta`. Dev slots do not self-heal; they say "Reinstall the Dev build" (open question 1).
- **GATE-SIBVER becomes channel-aware.** Inside the Stable slot, the existing strict rule stands (`check_sibling_versions.py`). Inside Beta and Dev slots, a sibling being *ahead* is allowed, because a Beta Lite running newer Lite code from Radio's Beta runtime is still Beta code you chose, and the About box (`app_version.describe_version`) already shows "(running shared runtime code X)". The promotion check P7 applies the strict rule at the moment a build enters Stable.
- **Portable copies** carry their own interpreter, so they have no slot question. A portable channel switch replaces the bundle.
- **QUILL** has no runtime slot (it is a self-contained exe).
- **Interim before slots ship (Phases 1-2):** a runtime app may join Beta only when `runtime_apps.installed_apps()` shows it is the **only** app on the runtime. Otherwise the chooser explains: "Beta for Quill Radio needs an update that is coming soon, because QUILL Lite on this computer shares Quill Radio's engine. You can move both together instead." It then offers to move all of them, which is safe because they then share one channel.

### 6.6 Install and apply

- **Installed copies:** the existing helper (`self_update.build_apply_update_script`, installer mode) gains `/CHANNEL=<ch>` and `/LOG="<updates>\setup-<ver>.log"` on the Inno command line. The installer UI choice is "Install quietly" (the default: `/VERYSILENT`, as now) or "Show the installer" (`/SILENT` off). This is a Preferences option, `show_installer_when_updating`, default off, for people who want to see the UAC and progress steps.
- **Before Windows elevates the installer:** verify Authenticode (subject matches the feed's `authenticode_subject`) with `Get-AuthenticodeSignature` in the helper. This is required on Stable once signing is mandatory (open question 1).
- **Portable copies** need the helper changed from in-place `/MIR` to a **swap**:
  1. Extract to `<install>.new`.
  2. Rename `<install>` to `<install>.previous`.
  3. Rename `<install>.new` to `<install>`.
  4. Move `data\` back across.
  5. Relaunch.

  `stage_portable_update` (247-272) stays. The extra disk use is one bundle, only during the update.
- **Rollback on failed update.**
  - The helper relaunches the app and waits up to 120 seconds for `<updates>\apply-result.json` with `{"version": X, "started": true}`. The app writes this file after its main window is shown, via `updater.apply.confirm_started()`, called from every app's startup after the first frame.
  - Portable: if the file never appears, or the app exits, the helper swaps `.previous` back and relaunches the old version.
  - Installed: the helper re-runs the cached previous installer (`<updates>\rollback\<previous setup>.exe`, kept until the new version has started 3 times or for 7 days; open question 7). It then writes `apply-result.json` with `rolled_back: true`.
  - On next start, the restored app reads that file and says once: "The update to 3.3.0 didn't start, so Quill Radio went back to 3.2.0. Nothing of yours was changed. Details are in Help > Update History."
- **"No surprise restarts."** Nothing ever closes or restarts the app without the user pressing a button. "Install when I close" stays (`update_download.offer_install`). If a Radio recording or scheduled recording is due within 30 minutes, "Install and restart now" first asks: "A recording is scheduled for 21:00. Install after it finishes?" A silent check never installs. It only offers, or downloads when allowed.

### 6.7 When checks run, and what is spoken

- **Silent startup check:** at most once a day (the existing throttles `_update_check_due` / `_app_update_check_due` / `update_check_due`). It is deferred with `wx.CallAfter`, as now.
- **Quiet hours:** in Radio and Cast, if `quiet_hours.silences(hours, "update", now)` is true, the offer is held and recorded rather than shown. "update" is a new `Kind`. Revocation and security notices are `high_priority=True`.
- **What is spoken** (GATE-13: only what the screen reader cannot know):
  - Spoken: "Checking for updates" on a manual check only; download milestones; "Update 3.3.0 downloaded"; "Switched to Beta"; "Back on Stable"; "Update held back: metered connection"; "Stable has caught up…".
  - Not spoken: dialog titles, button names, focus moves.
- **Offline:** a manual check shows a dialog. A silent check says nothing and records the failure in history. QUILL keeps `_record_notification`.

### 6.8 Update History

Help > **Update History...**, available in all four apps. It reads `<data>/updates/update-history.jsonl`, appended by `updater/history.py`. Entry kinds: `checked` (manual checks only, to keep it short), `downloaded`, `installed`, `failed`, `rolled_back`, `channel_changed`, `snapshot_saved`, `snapshot_restored`, `held_back`, `revoked_notice`.

The dialog is a `wx.ListCtrl` report with columns Date, What happened, From, To, Channel. Below it is a read-only multi-line details box for the selected row (focus starts on the list). Buttons: "Restore this copy..." (enabled on snapshot rows; it goes through the restore flow in 5.4), "Open update folder", and Close (no access key).

### 6.9 One profile per app, so new apps can join

```python
@dataclass(frozen=True)
class UpdaterProfile:
    app_key: str              # "radio" (feed file name; ASSET_PREFIX key)
    tag_key: str              # "radio" / "lite" / "" for QUILL
    display_name: str         # "Quill Radio"
    uses_shared_runtime: bool
    asset_kinds: tuple[str, ...]          # ("installer","portable")
    data_location: Callable[[], Path]     # app_data_dir / lite data_dir
    snapshot: SnapshotAdapter
    formats: tuple[str, ...]              # DataFormat ids this app writes
    channel_mirror: ChannelMirror         # read/write the per-app settings key
PROFILES = {p.app_key: p for p in (QUILL, QUILL_LITE, RADIO, CAST)}
```

For an app to join, it adds a profile, a feed file, `build/apps/<app>.toml`, its formats and snapshot adapter, and the two Help menu items. A gate fails if an app in `companion_install.ASSET_PREFIX` that has an installer lacks a profile.

---

## 7. Switching channels in each app (UI and wording)

### 7.1 Where the controls live

**Changing the channel never happens from a combo box selection.** Arrowing through a combo would otherwise fire a risk dialog per item, which is hostile to a screen-reader user. Every place shows the current channel and a **"Change release channel..."** button that opens one shared dialog.

| App | Help menu | Preferences |
|---|---|---|
| QUILL | Help > "Release &Channel..." and "Update &History..." next to "Check for &Updates..." (`main_frame_menu.py:3324`), labels through `_menu_label` with new command ids `help.release_channel` and `help.update_history` in `DEFAULT_KEYMAP` | Admin page: the `beta_updates` checkbox (`settings_specs.py:2139`) is replaced by a read-only "Release channel: Stable" row plus the "Change release channel..." button; the special case in `main_frame_preferences.py:725-730` is removed |
| QUILL Lite | Help menu (`lite_window_menus.py`) | Under "Look for &updates when QUILL Lite starts" (`lite_preferences.py:228`): a static line plus a button. The access key is chosen by GATE-14 (`check_access_keys.py`); if no letter is free, the button gets none, per CLAUDE.md:168 |
| Quill Radio | Help menu beside "Check for Up&dates..." (`radio_menu_bar.py:451`) | `radio_preferences.py`: add a button row (extend `app_preferences_dialog.PreferencesDialog` with a `PreferenceButton` row type) |
| QUILL Cast | Help menu beside "&Check for Updates..." (`podcasts_menu.py:465`) | `podcasts_preferences.app_rows`: new `AppRow` kind "button" |

**Keyboard routes** (proposed; must be confirmed free by `tests/unit/ui/test_menu_accelerators.py` and GATE-DOCKEY). The family update key stays **Ctrl+Alt+U** for Check for Updates. Release Channel is **Ctrl+Alt+Shift+U** in every app. Update History has a menu access key only, plus a chord where one is free. Each key goes in `keymap.APP_KEYMAPS` per app so the label follows any rebinding. The new keys are added to `docs/keyboard-reference.md` (GATE-KEYREF regenerates it).

The **Check for Updates** result dialog gains a line, "You are on the Beta channel," and a "Change release channel..." button. When up to date on Stable, today's `_offer_beta_switch` nag (`main_frame_updates.py:527-558`) is **removed**: an up-to-date answer should not try to sell Beta.

### 7.2 The Release Channel dialog (`release_channel_dialog.py`)

- **Title:** "Release Channel: Quill Radio"
- **Controls, in tab order:**
  1. Radio buttons for Stable, Beta and Dev, each with the one-line meaning from 2.1 as its help text (`SetHelpText`, F1). The current channel is selected. The label "Choose a release channel" is a static box that the screen reader announces with the group.
  2. A read-only multi-line "What this means" box that updates as the selection changes: the current version, the newest version on the selected channel, and whether going there is an update, the same version, or a return (with the safety answer from 5.1 already computed).
  3. A group "Also move my other QuillVille apps on this computer", with one checkbox per installed app ("QUILL Lite, now on Stable") and every box unchecked by default.
  4. "Read about release channels" (opens the site page).
  5. Buttons: "Switch" (not default when the choice is riskier than the current one), and Close (Escape, no access key).
- Choosing the current channel and pressing Switch does nothing and says "Already on Stable."

### 7.3 Risk dialog for Beta (draft wording)

**Title:** "Move Quill Radio to Beta?"

> Beta gets new features a few weeks before everyone else. In return, some things may not work right yet.
>
> **What could happen**
> - Something might stop working, or Quill Radio might close unexpectedly.
> - Your screen reader might miss something it should announce. We test every Stable version with JAWS and NVDA. Beta versions are tested less.
> - Your favorites and settings may be saved in a newer way that the Stable version can't read yet.
> - Beta and Dev versions aren't signed, so Windows may warn that the installer comes from an unknown publisher; that's expected, and you can choose More info, then Run anyway.
>
> **How you're protected**
> - Before switching, Quill Radio saves a copy of your favorites, history and settings. Your recordings are not copied, and updates don't change them.
> - You can come back to Stable any time from Help > Release Channel. If it's safe, you go straight back. If it isn't, you can stay on your version until Stable catches up, or go back to the copy saved today.
> - Beta versions of the QuillVille apps share their own copy of the engine, which uses about 350 MB more disk space until you come back to Stable.
>
> Nothing about you is sent to us when you switch. The only thing Quill Radio ever sends is a request for the list of versions.

Buttons: **"Stay on Stable"** (the default, and Escape) and **"Move to Beta"**. Focus starts on the text box, as in `update_notice.py` ("focus lands on the notes"). The risk is carried by words and the button text. The icon is decorative only (no colour-only signals).

### 7.4 Risk dialog for Dev (stronger)

**Title:** "Move Quill Radio to Dev?"

> Dev versions are built from work in progress, sometimes several times a week. They are meant for testing.
>
> - Expect things to break. Some days a Dev version may not start at all.
> - Dev versions are not checked with screen readers before they go out.
> - Dev versions may change how your data is saved more than once. Going back to Stable may mean using the copy saved today and losing changes you made since.
> - Beta and Dev versions aren't signed, so Windows may warn that the installer comes from an unknown publisher; that's expected, and you can choose More info, then Run anyway.
>
> If a developer didn't ask you to try Dev, Beta is probably the better choice.

There is a checkbox: "I understand that Dev versions can break and that going back may lose recent changes." Buttons: "Choose Beta instead", "Stay on Stable" (the default, Escape), and "Move to Dev". If "Move to Dev" is pressed with the box unchecked, focus moves to the checkbox and the app says "Check the box first, so we know you've read this." That is an outcome the reader can't know, so it is allowed. Typing a confirmation phrase is avoided because of what it costs a braille or speech user.

### 7.5 What moving to Beta or Dev does, step by step

1. Show the risk dialog. Cancel changes nothing.
2. Take a `joined-beta` snapshot for this app and each checked sibling. Announce "Saved a copy of your settings." If the snapshot fails, stop with: "Quill Radio couldn't save a copy of your favorites, so it stayed on Stable. <reason>."
3. Write `channels.json` and the mirror settings key. Record the change in history.
4. Run an immediate check on the new channel. If there is a newer build, show the normal update dialog (`update_notice`), with the header "Beta version 3.3.0-beta.2". Installing passes `/CHANNEL=beta`, which puts the runtime in the Beta slot.
5. Announce "Quill Radio is on Beta."

### 7.6 Returning to Stable (drafts)

**Safe** (title "Go back to Stable?"):

> Stable is version 3.2.0. You have 3.3.0 Beta 2.
>
> Your favorites and settings will work in 3.2.0, so it's safe to go back now. Features that are only in Beta will go away until they reach Stable.
>
> You can also stay on 3.3.0 Beta 2 and move to Stable when it catches up. You won't get more Beta updates while you wait.

Buttons: "Go back to 3.2.0 now" (the default), "Wait for Stable", Close.

**Safe with losses** (Lite): the same, plus:

> 3.2.0 doesn't know about 4 settings you changed in Beta (for example, "Read headings aloud as I type"). They'll go back to their usual values.

**Not safe** (title "Going straight back isn't safe yet"):

> Quill Radio 3.4.0 Beta saved your favorites in a newer way that Stable 3.2.0 can't read. If 3.2.0 were installed now, it might not see your favorites.
>
> You have two safe choices:
>
> **Wait for Stable.** Keep 3.4.0 Beta, stop taking Beta updates, and move to Stable when it reaches 3.4.0. Quill Radio will do this by itself and tell you.
>
> **Use the copy from 3 October.** Go back to how things were when you joined Beta, then install 3.2.0. Favorites you added after 3 October won't be in it. A copy of how things are right now is saved first, so nothing is thrown away.

Buttons: "Wait for Stable" (the default), "Use the copy from 3 October", Close (no change). If no snapshot exists (for example, the user joined Beta by installing by hand), the second choice reads: "There's no saved copy from before Beta, so the only safe choice is to wait."

---

## 8. Accessibility and security requirements

### 8.1 Accessibility

- **Every dialog:**
  - Is shown through `_show_modal_dialog` (or the app's equivalent) and `apply_modal_ids`, with Close bound by `bind_close_button`. It is listed in the dialog inventory (`dialog_inventory.py`) and reachable from an app entry point (GATE-REACH).
  - Has keyboard-complete tab order, sets focus on the explanatory text first, uses no access keys on OK, Cancel or Close, and has no duplicate mnemonics (GATE-14).
  - Has inline `SetHelpText` on every control and a `surface_help` entry per app (radio, cast, QUILL Lite and QUILL catalogues). `docs/f1-help-reference.md` is regenerated (GATE-HELPREF).
- **No colour-only signals.** Risk is in the words ("Move to Beta?", "isn't safe yet"); icons are decorative.
- **Spoken outcomes only** (GATE-13; `check_over_announce.py` must stay green).
- **No surprise restarts or popups:** see 6.6 and 6.7. A silent check never opens a modal during playback start-up, recording or quiet hours. It records and waits for the next manual check or idle moment.
- Long version strings are read the way they are displayed: "3.3.0 Beta 2", never "3.3.0-beta.2" (`ReleaseVersion.display()`).

### 8.2 Security

- **Signed feed, required** (3.2). The asset hash comes from the signed feed. Authenticode is checked before elevation (6.6).
- **Downgrade attack** (an attacker serving an old, vulnerable build):
  - The client never installs a lower version unless *the user started a return to Stable*, and the target appears in the **current signed feed** with Stable in its `channels`, is not revoked, is at or above `security_floor`, and passes `downgrade_verdict`.
  - Anti-replay: a stored `sequence` high-water mark (an older signed feed is refused) and `expires_at` (a feed frozen in time is treated as "couldn't check" once expired).
  - A scheduled workflow (`feed-refresh.yml`, weekly) re-signs each feed with a new `generated_at`, `expires_at` and `sequence`. This needs the key in CI (open question 6).
- **Revoked builds:** never offered and never a rollback target. If you are running one, you get a high-priority notice that names the replacement. Revocation keeps assets downloadable for people moving forward.
- **Trusted hosts:** the existing allowlist (`updates.py:975-984`) applies to both the feed and the assets.
- **Privacy:**
  - The check is one HTTPS GET for `updates/v2/<app>.json` (and `.sig`), with no query string, no cookies, and a generic User-Agent `QuillVille-Updater/2` with no version or OS.
  - Downloads are plain GETs to GitHub.
  - No telemetry, no install pings, no crash-gated rollouts.
  - New egress sites are registered in `quill/tools/network_egress_entries*.py` (the GATE-9 audit). The Preferences help text already promises "sends nothing about you" (`settings_specs.py:2129-2134`) and stays true.
- **Feed key compromise:** the rotation path in 3.2 applies. The `security_floor` plus revocation give a way to push people off a bad build.

---

## 9. Migrating from today without breaking installed copies

### 9.1 What installed copies do today, and the guarantees we keep

| Installed copy | How it checks | What it will see | Guarantee kept |
|---|---|---|---|
| Quill Radio 3.0.4, QUILL Lite 1.1.2 | GitHub API page 1 (30 releases), own asset prefix, **ignores `prerelease`**, takes `stable[0]` | Only non-prerelease releases | Beta and Dev builds are published as prereleases, so they are never offered. A Stable promotion flips `prerelease=false`, so they see it |
| QUILL 0.9.0 Beta 2/3 | v1 manifest (no channel) plus the GitHub API with `beta_updates` | v1 feed: one version. API: prereleases if beta | Keep generating `.quill-update-feed-v1.json`, **only ever with the newest Stable QUILL** once 1.0.0 ships (until then, newest Beta as today). Beta users on old builds still get Betas through the API path |
| QUILL Cast | not released | — | Cast 2.0.0 ships with the v2 updater from day one |

### 9.2 The pagination hazard (must be handled before any Beta or Dev publishing)

Installed Radio and Lite read only the first 30 releases.

- **Do not publish Dev builds as GitHub Releases in `Community-Access/quill`.** Host them in a separate repo, **`Community-Access/quillville-dev-builds`** (assets only; feed URLs point there; add it to trusted hosts as a `github.com` path, which is already trusted).
- **Cap Betas in the main repo.** When a Beta is superseded, `publish_release.py` *deletes the GitHub release object but keeps the tag* (old Beta bits stay downloadable from the dev-builds repo mirror if needed). A gate (`test_release_page_budget.py`, run by `publish_release.py`) refuses to publish if more than **20** releases are newer than any app's newest Stable on the default listing.
- Phase 0 adds `?per_page=100` to every API call in the new builds. That fixes future copies; the cap protects the copies already out there.

### 9.3 Bridge releases (the first channel-aware versions)

- **Radio 3.2.0, Lite 1.2.0, QUILL 1.0.0 and Cast 2.0.0** are the first builds with the v2 updater. They ship as ordinary Stable releases, so every old copy is offered them through its old path.
- They must:
  - Read the legacy settings (`beta_updates` becomes channel Beta; nothing to read for the others) and write `channels.json`.
  - Start the format ledger at once ("start the clock"), recording today's formats as version 1 (`quill.settings` 2).
  - Write `quill-app-version.ini` with `channel=` and `slot=`. Radio and Lite already write the file; **Cast must start**.
  - Keep working if the v2 feed is unreachable by reporting "couldn't check". There is no unsigned fallback.

### 9.4 Settings migration details

- **QUILL:** add `update_channel: str = "stable"`, with `normalize` restricting it to stable, beta or dev. On load, if `update_channel` is absent and `beta_updates` is true, set `update_channel = "beta"`. Keep writing `beta_updates = (channel != "stable")` for one release cycle so a QUILL downgraded to 0.9.x still behaves (`reconcile_unknown` preserves `update_channel` for it). No `SETTINGS_SCHEMA_VERSION` bump is needed (an additive field). `skipped_update_version` stays and is honoured per channel.
- **QUILL's auto-enroll** (`main_frame_updates.py:214-222`) is replaced by the birth-channel rule (2.1).
- **QUILL's silent auto-download** stays for QUILL, now metered-aware. It does not get added to the other apps.
- **Lite, Radio and Cast:** additive fields. Lite's lossy downgrade behaviour is declared in `data_formats` as `lossy_reads`, so the "Safe with losses" wording appears.

### 9.5 Workflow fixes before QUILL 1.0.0 Stable

- `windows-release.yml:158-168`: `prerelease` and the title come from `build/version.toml`, not hard-coded.
- The v1 feed is generated **only for Stable releases** after 1.0.0 (guarded in `generate_update_feed.py`). Beta tags no longer overwrite it.
- Clients that understand v2 ignore the v1 feed for offers, and keep fetching it only for `advisories` until v2 carries advisories (then drop it).

---

## 10. Gates, tests, documentation, phases and open questions

### 10.1 New and extended gates

| Gate | File | What it enforces |
|---|---|---|
| **GATE-VERSORT** | `tests/unit/core/test_versioning.py` | Ordering across all spellings (tags, semver, PEP 440, display), including dev < alpha < beta < rc < final, two dev builds on one day, `+sha` ignored; Hypothesis-free table plus generated pairs; old `_version_tuple` callers unchanged |
| **GATE-FEED** | `tests/unit/docs/test_release_feeds.py` | Every `docs/site/updates/v2/*.json` matches the schema, its `.sig` verifies against `feed-pub.keys`, `sequence` increases versus `git show HEAD~1`, `channels.*.current` exist and are not revoked, Stable entries are final versions, and `can_roll_back_to` equals the recomputed value |
| **GATE-DATAFMT** | `tests/unit/core/test_data_formats.py` + `quill/tools/data_format_audit.py` | Fingerprints each registered store's serializer (dataclass fields and types, `_deltas` keys, `to_versioned` group layout) against `tests/unit/core/fixtures/data_format_fingerprints.json`; a change fails until someone either bumps `current` or records "additive, compatible" (the classification is the review, like `persistence_audit`) |
| **GATE-SIBVER-CH** | `scripts/check_sibling_versions.py` (extended) | Channel-aware rule (6.5); **Cast added to `SITES`** (`quill/apps/podcasts_menu.py`, `APP_VERSION`, tag `quill-cast-v`) |
| **GATE-APPVER** | `tests/unit/scripts/test_app_versions_agree.py` | Adds `test_cast_says_one_version_everywhere` and Lite parity; checks `build/apps/<app>.toml` agrees with constants |
| **GATE-MARKER** | `tests/unit/structure/test_installer_markers.py` | Every shared-runtime `.iss` writes `quill-app-version.ini` with `version`, `channel` and `slot` |
| **GATE-UPDATER-PROFILE** | `tests/unit/core/test_updater_profiles.py` | Every app with an installer in `ASSET_PREFIX` has an `UpdaterProfile`, a feed file, Help menu items with keyboard routes, and F1 help for the channel surfaces |
| **GATE-RELEASE-PAGE** | `tests/unit/scripts/test_release_page_budget.py` | The 30-release page budget (9.2) |
| Policy tables | `tests/unit/core/updater/test_policy.py` | About 60 rows: installed × channel × feed × ledger × pending, down to the decision |
| Helper script | `tests/unit/core/test_self_update.py` (extended) | Portable swap and rollback script, `/CHANNEL`, `/LOG`, the apply-result wait |
| Snapshots | `tests/unit/core/updater/test_snapshots.py` | Each adapter round-trip, the shared-file rule, ledger lowering on restore |
| Promotion | `tests/unit/scripts/test_promote_release.py` | Each check P1-P13 against a fake `gh` and feed; the dry-run report text |
| UI | dialog inventory, `check_access_keys.py`, `check_over_announce.py`, `test_menu_accelerators.py`, surface reachability snapshot, per-app help audits | Snapshots updated |
| Egress | `quill/tools/network_egress_audit.py` | New v2 feed fetch sites registered |
| Persistence | `quill/tools/persistence_audit.py` | `channels.json` (marker), ledger (framework), snapshots (export), `update-history.jsonl` (cache) |
| Rehearsal | `tests/integration/test_channel_rehearsal.py` (manual or nightly) | Throwaway repo plus `QUILL_UPDATE_FEED_BASE`: publish dev, promote to beta, then stable, revoke, roll back |

### 10.2 Documentation

- **Site page `docs/site/release-channels.html`**, generated from **`docs/release-channels.md`** (a globally unique basename, as GATE-SITE-LINKS requires). It covers: what Stable, Beta and Dev mean; how to switch in each app (with the keys); what "safe to go back" means; snapshots; disk space; privacy; how to report a Beta problem. It is linked from `docs/site/radio.html`, `quilllite.html`, `docs.html` and the FAQ.
- **User guides:** a "Release channels and updates" section in `docs/user guide/userguide.md` (QUILL), `standalone/quilllite/docs/userguide.md`, the Radio user guide and `standalone/cast/docs/userguide.md`. Also a tutorial step in each app's tutorials.
- **Maintainer docs:**
  - `docs/release/RELEASE.md` gains "Channels, publishing and promotion".
  - New `docs/release/channels-runbook.md`: the publish, promote, revoke and rollback commands; a "what to do when a Beta breaks data" playbook; key handling.
  - `standalone/README.md:76-82` corrected.
  - `docs/signing.md` gets the key-list and rotation section.
- **Design record:** `docs/design/2026-10-03-release-channels.md` (this plan), plus an addendum to the shared-runtime program doc for channel slots.
- **Release notes conventions** as in 4.5. **Sign-off results** go in `docs/qa/signoffs/<app>-<version>.md`, with `docs/qa/README.md` explaining them.
- **Settings documentation (GATE-SETDOC):** document `update_channel` in all four apps.

### 10.3 Phased implementation (rough sizes: S is up to 3 days, M is about 1-2 weeks, L is 2-4 weeks)

**Phase 0: fix today's hazards (S to M). This ships in the next point releases.**

- `quill/core/versioning.py` (single parser), with `_version_tuple` and `parse_version` delegating to it. Replace `stable[0]` with `select_latest`. Add `per_page=100`.
- Cast: pass `installed_version(_VERSION)`; write `quill-app-version.ini` in both Cast `.iss` files; add Cast to GATE-APPVER and GATE-SIBVER.
- `windows-release.yml`: take the channel from `version.toml`. v1 feed: Stable-only once 1.0.0 ships; clients ignore a pre-release manifest version unless on Beta.
- Data-format registry plus ledger, recording only ("start the clock"). `channels.json` reader and writer.
- Value: no wrong offers, and the groundwork for every later safety decision.

**Phase 1: choose a channel, with the risk dialog, in all four apps (M). Most user value soonest.**

- Shared `release_channel_dialog`, `channel_risk_dialog`, Help > Release Channel, and Preferences rows. `joined-beta` snapshots.
- **QUILL** gets the full Beta experience at once (it is not on the shared runtime). It uses the existing GitHub path with prerelease flags to find Betas.
- Runtime apps can join Beta when they are alone on the runtime, or by "move all my apps together" (6.5 interim).
- Return to Stable is offered **only as "Wait for Stable"**, which is always safe, plus a same-version flip. No downgrade installs yet.
- Update History, read-only.

**Phase 2: signed v2 feed and release tooling (M to L).**

- `feed.py`, `publish_release.py`, `promote_release.py`, `revoke_release.py`, `rollup_release_notes.py`, `promote-release.yml` with environment approval, GATE-FEED, the `quillville-dev-builds` repo, and the page budget.
- Clients switch to v2. Downloads resume and verify against the feed hash.

**Phase 3: runtime channel slots (L).**

- `shared-runtime.iss` (`/CHANNEL`, `RuntimeDir`), launcher `runtime_resolve.c` (`slot=`), `runtime_refs` by slot, `runtime-stable` and `runtime-beta` tags, channel-aware GATE-SIBVER.
- This removes the "alone on the runtime" restriction.

**Phase 4: safe downgrade and rollback (M to L).**

- `downgrade_verdict` and the three return dialogs. Snapshot restore with shared-file rules. Unsafe-downgrade refusal.
- Portable swap install with `.previous`. The apply-result health check and automatic rollback. A cached previous installer.

**Phase 5: polish (M).**

- Metered holds, quiet hours, recording-aware install timing, Authenticode check before elevation, revocation notices, Update History restore actions, "Show the installer" option, feed refresh workflow and expiry, and the Dev channel risk flow.

**Phase 6: the rest of the family (S per app).**

- Profiles for Weather, Converter, Inkwell, Player, Studio, Beacon and Social.

### 10.4 Open questions for the owner

*All answered on 2026-10-03; the answers are in the Status note at the top. The questions are kept as they were asked.*

1. **Dev builds:** built where (your machine or CI), how often, signed or unsigned (signing costs money per file), and hosted in a separate `quillville-dev-builds` repo (recommended because of the pagination risk)? Should Dev runtime slots self-heal?
2. **Disk:** is about 335 MB extra for a Beta or Dev runtime slot acceptable, and should the risk dialog state the number?
3. **Soak and sign-off:** a 7-day Beta minimum before Stable? Screen-reader sign-off required for Stable only (recommended), or for Beta too?
4. **Promotion model:** do you accept "Stable takes only final-numbered candidate builds that were first on Beta"? The alternative, rebuilding at promotion, gives up "same bits".
5. **Channel scope:** per app with an optional "move all" (proposed), or one family-wide channel with per-app exceptions?
6. **Feed expiry and re-signing:** should CI hold the feed key for a weekly refresh (needed for the anti-freeze expiry), or should expiry be long (for example 90 days) and refreshed only on releases?
7. **Rollback cache:** keep the previous installer (about 180-200 MB) for 7 days or 3 successful starts, so a failed update can undo itself?
8. **macOS** (`standalone/radio-mac`, `macos-release.yml`): in scope now, or later?
9. **QUILL's version:** `build/version.toml` says 1.0.0 Stable while the newest tag is `v0.9.0-beta.3` (you mentioned Beta 2). Is 1.0.0 the first Stable, and should the workflow fix in Phase 0 land before it?
10. **Lite's tag key:** confirm `quill-lite-v` stays (grandfathered) and update `release_tags.py`'s stated convention to match.
11. **Background downloads on Beta:** QUILL already auto-downloads on the silent check. Should Beta users of the other apps get the same (never auto-install)?
12. **Gradual rollout without telemetry:** do you want an optional client-side percentage rollout (a random bucket stored locally, no reporting), or is "promote when the sign-off is green" enough?

---

### Critical Files for Implementation

- S:\QUILL\quill\core\updates.py (version parsing, feed parsing and signing, asset selection, download; to be split into `quill/core/updater/*` and `quill/core/versioning.py`)
- S:\QUILL\quill\ui\main_frame_updates.py and S:\QUILL\quill\ui\app_shell.py (with S:\QUILL\quill\apps\lite_updates.py): the three update flows to fold into one channel-aware `run_update_check`
- S:\QUILL\quill\core\self_update.py: the apply helper (portable swap, `/CHANNEL`, apply-result health check, rollback)
- S:\QUILL\installer\shared-runtime.iss with S:\QUILL\quill\core\runtime_marker.py, S:\QUILL\quill\core\app_version.py and S:\QUILL\quill\native\launcher\runtime_resolve.c: channel runtime slots and the extended app marker
- S:\QUILL\scripts\check_sibling_versions.py with S:\QUILL\.github\workflows\windows-release.yml and S:\QUILL\scripts\generate_update_feed.py: the channel-aware gates and publishing pipeline that the new `publish_release.py` and `promote_release.py` build on

Other files referenced: S:\QUILL\quill\core\settings_migration.py, S:\QUILL\quill\core\versioned_store.py, S:\QUILL\quill\core\lite\settings.py, S:\QUILL\quill\core\radio\backup.py, S:\QUILL\quill\core\podcasts\backup.py, S:\QUILL\quill\core\release_tags.py, S:\QUILL\quill\core\release_assets.py, S:\QUILL\quill\core\net_metered.py, S:\QUILL\quill\core\quiet_hours.py, S:\QUILL\quill\core\settings_specs.py, S:\QUILL\quill\ui\main_frame_preferences.py, S:\QUILL\quill\apps\lite_preferences.py, S:\QUILL\quill\apps\radio_preferences.py, S:\QUILL\quill\apps\podcasts_preferences.py, S:\QUILL\quill\apps\podcasts.py, S:\QUILL\quill\apps\podcasts_menu.py, S:\QUILL\quill\ui\update_notice.py, S:\QUILL\quill\ui\update_download.py, S:\QUILL\tools\generate_build_info.py, S:\QUILL\build\version.toml, S:\QUILL\tests\unit\scripts\test_app_versions_agree.py, S:\QUILL\docs\signing.md, S:\QUILL\docs\design\2026-08-17-runtime-layering-delta.md, S:\QUILL\standalone\runtime\build_runtime_installer.ps1, S:\QUILL\standalone\README.md.
