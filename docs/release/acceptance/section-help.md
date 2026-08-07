# Section — Help menu (`help.*`, 21 commands)

Everything about **finding your way, proving the build, and getting unstuck**:
the About box, the user guide and keyboard help, diagnostics and bug reporting,
the feature-profile controls, and the "what can I do here / why can't I see
this" explainers. Finish **Part 0** first — several scenarios below cross-check
what you recorded in `00-getting-started.md`.

Surface reference (label + shortcut) is
`../../planning/signoff/SIGNOFF-editor.md` → `help.*`. Read §2–§3 of `README.md`
for the scenario layout and the Pass/Fail/Blocked/N-A +
Works/Surface-exact/Accessible boxes.

**How to reach these commands.** Most live on the **Help menu** (press **Alt**
then **H**). A few sit elsewhere and are called out per scenario:

- **Open Logs Folder** and **Open Diagnostics Folder** live under
  **Tools menu ▸ Customize and Support**.
- **Key Cheatsheet** (Alt+Shift+/) and **Why Is This Unavailable?** (Alt+F1) have
  **no menu entry** — reach them by their shortcut or the Command Palette.

**Surface note you will hit repeatedly.** Several Help-menu *labels* are shorter
than the command *titles* this book prints from the sign-off inventory. Where they
differ, the scenario names the exact on-screen label so you can judge
**Surface-exact** correctly. None of that is a bug by itself — it is only a
Surface-exact fail if the label differs from what this book says it is.

---

## HELP-01 — About Quill (`help.about_quill`)

*What & why.* Proves exactly which build you are testing. Sign-off is only valid
against a known version and build stamp — this is where you read them.

**Before you start**
- QUILL open, any state. Have your notebook ready to copy the build line into.

**Do this**
1. Open **Help menu (Alt, H) ▸ About Quill**.
2. With focus in the dialog, **Tab** to the tab strip and **Left/Right arrow**
   through the tabs: **Overview**, **Dependencies**, **Links** (and **Golden
   Quills**).
3. On the Overview tab, find the **Copy** button and press it to put the build
   block on the clipboard; paste it into your notebook.
4. Press **Escape** to close.

**You should see and hear**
- A real tabbed dialog (not one flat blob): the first thing announced on Overview
  is the headline **"QUILL for All 1.0.0"**. The Copy block reports
  **Product: QUILL for All**, **Version: 1.0.0**, a **Build** stamp, **Channel**
  (a stable release reads **Release**), a **Commit** SHA, and a build date.
- **This must match GS-05** in `00-getting-started.md`. If the version is not
  **1.0.0**, or the build stamp differs from what you recorded there, fail and
  write down both values.
- Tabs, links, and the **Visit / Copy** buttons are reachable by keyboard and
  announced with role and name.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## HELP-02 — Context Help: Current Mode Keys (`help.context_help`, Ctrl+Shift+Grave then Shift+H)

*What & why.* Speaks the handful of keys most useful **right where you are** —
editor, QUILL browse mode, or the status bar — so you never have to memorise the
whole map. This is an **announcement**, not a dialog.

**Before you start**
- `plain.txt` open, focus in the editor. Chord: press **Ctrl+Shift+Grave**,
  release, then **Shift+H**. On the Help menu it is labelled **Announce Mode
  Shortcuts** (not "Context Help").

**Do this**
1. In the editor, fire the chord (or **Help menu ▸ Announce Mode Shortcuts**).
2. Listen, then move focus to the status bar (if reachable) and fire it again to
   hear the status-bar key set.

**You should see and hear**
- In the editor you hear an **"Editor mode shortcuts"** summary listing Save,
  Undo, Find, Go to line, Command palette, Go to anything, QUILL browse mode,
  Document summary, and Context help, each with its **live key binding** (the
  bindings are read from your current keymap, so they reflect any remaps).
- In QUILL browse mode it instead lists the single-letter browse keys (H, A, L,
  I, T, B, P, S, C). Nothing opens; focus does not move.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## HELP-03 — Enable Braille Mode… (`help.enable_braille_mode`)

*What & why.* Turns on the braille feature set (BRF/BRL support, Grade 1/2
translation, the braille status cell, and the Braille menu) for testers who did
not select it during onboarding.

**Before you start**
- A build where **Braille Mode is currently off** — the menu item only appears
  when braille is not already active. If it is already on, the command is a spoken
  no-op; record that and mark Pass.

**Do this**
1. **Help menu ▸ Enable Braille Mode…**.
2. Read the description dialog; its buttons are **Enable Braille Mode** and
   **Not Now**. Choose **Not Now** first (confirm nothing changes), then repeat and
   choose **Enable Braille Mode**.

**You should see and hear**
- The dialog explains what braille mode adds and that the **Braille Pack**
  (translation engine) is a separate optional component. On **Enable**, QUILL
  announces **"Braille Mode is now active. The Braille menu has been added."**, the
  menu bar gains a **Braille** menu, and in a real install you may be offered a
  one-time Braille Pack install. On **Not Now / Escape**, nothing changes.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## HELP-04 — Feature Profile Health Check… (`help.feature_profile_health_check`)

*What & why.* Reports whether your active feature profile is internally
consistent — e.g. commands that are visible but whose feature is off, or
dependencies that are not satisfied.

**Before you start**
- Any state. Menu path: **Help menu ▸ Feature Profiles ▸ Profile Health Check…**.

**Do this**
1. Open **Help menu ▸ Feature Profiles ▸ Profile Health Check…**.
2. Read the report; press **Enter** or **Escape** to close.

**You should see and hear**
- An information dialog titled **Feature Profile Health Check** containing a
  readable report (the active profile and any inconsistencies). The text is
  reachable by the screen reader's review cursor. Closing returns focus to the
  Help menu.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## HELP-05 — Key Cheatsheet (`help.key_cheatsheet`, Alt+Shift+/)

*What & why.* One searchable list of **every command and its current key
binding** — the fastest way to answer "what's the shortcut for…?".

**Before you start**
- Any state. This command has **no menu entry**: use **Alt+Shift+/** or the
  Command Palette → "Key Cheatsheet".

**Do this**
1. Press **Alt+Shift+/**.
2. Focus lands with a **search box** at the top ("Search by command name or key
   binding"); type **`save`** and read the filtered results.
3. Clear the search to see the full list; press **Escape** or the **Close** button.

**You should see and hear**
- A **Key Cheatsheet** dialog with a labelled search field and a read-only,
  multi-line list of `Command: binding` rows (commands with no binding read
  "(no binding)"). Typing filters live; an empty match reads
  **"No matching commands."** Everything is keyboard-reachable and announced.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## HELP-06 — Open Logs Folder (`help.open_logs_folder`)

*What & why.* Jumps straight to QUILL's log files in File Explorer — the first
thing support will ask for.

**Before you start**
- Any state. Path: **Tools menu ▸ Customize and Support ▸ Open Logs Folder**.

**Do this**
1. Open **Tools menu (Alt, T) ▸ Customize and Support ▸ Open Logs Folder**.

**You should see and hear**
- File Explorer opens on QUILL's logs folder (under your per-user app-data
  directory, e.g. `…\Quill\logs`). The folder is created if it does not exist yet,
  so the command never errors on a fresh install.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## HELP-07 — Open Diagnostics Folder (`help.open_diagnostics_folder`)

*What & why.* Opens the folder where saved diagnostics bundles land (see HELP-14).

**Before you start**
- Any state. Path: **Tools menu ▸ Customize and Support ▸ Open Diagnostics Folder**.

**Do this**
1. Open **Tools menu (Alt, T) ▸ Customize and Support ▸ Open Diagnostics Folder**.

**You should see and hear**
- File Explorer opens on QUILL's diagnostics folder (e.g. `…\Quill\diagnostics`),
  created if absent. Any bundle you saved in HELP-14 should appear here.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## HELP-08 — Open Third-Party Notices (`help.open_third_party_notices`)

*What & why.* Shows the open-source licences QUILL depends on — a legal
requirement, and a good read for what is bundled.

**Before you start**
- Any state. Path: **Help menu ▸ Open Third-Party Notices**.

**Do this**
1. Open **Help menu ▸ Open Third-Party Notices**.

**You should see and hear**
- A **new document tab** opens containing the third-party notices (dependency
  names, versions, and licences), focus in the editor so you can read it with the
  screen reader like any document. If dependency metadata is unavailable in this
  build, it opens a short "not available in this build" note rather than erroring.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## HELP-09 — Open User Guide (`help.open_user_guide`, Ctrl+F1)

*What & why.* Opens the full bundled user guide, rendered to HTML, in your
system browser.

**Before you start**
- A browser installed and set as default. Menu label is **Open User Guide** and
  carries the **Ctrl+F1** accelerator.

**Do this**
1. Press **Ctrl+F1**, or **Help menu ▸ Open User Guide**.

**You should see and hear**
- QUILL renders the guide to HTML (written under `…\Quill\user-guide`) and opens it
  in the browser; the status bar reports **"Opened user guide in browser"**. The
  page has a real heading outline you can navigate with your screen reader. If the
  guide file cannot be found, QUILL falls back to the in-app **Welcome Guide** and
  says so rather than failing silently.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## HELP-10 — Redeem Unlock Code… (`help.redeem_unlock_code`) [GATED — dev build only]

*What & why.* Lets a trusted tester unlock a pre-release, locked-off feature with
a signed code. It performs **no network call**. It is a **tester-only** surface.

**Before you start**
- Determine your build. In a **public 1.0 build this command and its menu item
  must be ABSENT** — verify it is not on the Help menu and not in the Command
  Palette, then mark this scenario **N/A** (its absence is proven here and in
  `gated-absence.md`). Only a **dev/admin build** (`QUILL_DEV_BUILD=1`) shows it.

**Do this (dev build only)**
1. **Help menu ▸ Redeem Unlock Code…**.
2. Enter a signed unlock code by keyboard; confirm.

**You should see and hear**
- Public build: **not present** anywhere → **N/A**. Dev build: a labelled,
  keyboard-complete code-entry dialog; a valid code unlocks its feature and is
  announced, an invalid code is rejected with a clear spoken message, and nothing
  touches the network.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## HELP-11 — Report a Bug… (`help.report_bug`)

*What & why.* Files a bug without leaving QUILL. **The behaviour depends on
whether this build carries a feedback token** — verify the path your build takes.

**Before you start**
- Network available (submission needs it). Note which build you are on: a normal
  **public** build ships a bundled, issues-only feedback token; a **private or
  `-SkipToken`** build has none.
- Menu label: **Report a Bug…**.

**Do this**
1. **Help menu ▸ Report a Bug…**.
2. If a form opens, fill the fields by keyboard and submit; if a browser opens
   instead, confirm the online form loads and the URL is on your clipboard.

**You should see and hear**
- **Public build (token present):** an in-app **feedback form** opens (labelled
  fields, keyboard-complete). Submitting files a GitHub issue directly and QUILL
  records **"Submitted feedback"**. If submission fails for any reason, it must not
  strand you — it falls back to the online form.
- **Private / `-SkipToken` build (no token):** QUILL says direct reporting isn't
  set up in this build, **opens the online support form in your browser, copies
  the link to your clipboard**, and speaks that it did so. Both paths end with a
  usable way to file the report — a dead-end at submit is a fail.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## HELP-12 — Reset to Essential Profile (`help.reset_feature_profile`)

*What & why.* Returns the feature set to the safe **Essential** profile — the
"put things back the simple way" button. Destructive to your current profile
choice, so it confirms first.

**Before you start**
- Switch to a richer profile first (do HELP-17) so the reset has a visible effect.
  Path: **Help menu ▸ Feature Profiles ▸ Reset to Essential Profile**.

**Do this**
1. **Help menu ▸ Feature Profiles ▸ Reset to Essential Profile**.
2. In the **"Reset Quill to the Essential profile?"** Yes/No prompt, choose **No**
   first (confirm nothing changes), then repeat and choose **Yes**.

**You should see and hear**
- A hearable Yes/No confirmation (No default). On **Yes**, the status bar reports
  **"Reset to Essential profile"**, the title/menus reflect the simpler profile,
  and menus rebuild. On **No/Escape**, nothing changes.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## HELP-13 — Startup Wizard (`help.run_profile_onboarding`)

*What & why.* Re-runs the first-run **setup / onboarding wizard** on demand.
This is the **same wizard** as HELP-15 (`help.startup_wizard`) — an alias command
id used by the Command Palette and onboarding flow. Run it here from the palette
to prove the alias resolves to the wizard.

**Before you start**
- Any state. Reach it via the **Command Palette → "Startup Wizard"**
  (`help.run_profile_onboarding`).

**Do this**
1. Open the Command Palette and run **Startup Wizard**.
2. Step through the wizard by keyboard; on the last step confirm, or **Escape** to
   abort.

**You should see and hear**
- The multi-step setup wizard opens (the same one described in HELP-15): each page
  is labelled and keyboard-complete, choices are announced, and completing it
  applies your profile/intent while aborting leaves settings unchanged.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## HELP-14 — Save Diagnostics… (`help.save_diagnostics`)

*What & why.* Packages logs, settings, and environment into a single redacted ZIP
you can hand to support — showing you what's inside first.

**Before you start**
- Any state. You will choose a save location. Menu label: **Save Diagnostics…**.

**Do this**
1. **Help menu ▸ Save Diagnostics…**.
2. In the **Review Diagnostics Export** dialog, read the preview; decide the
   **"Include plain file paths in the bundle"** checkbox; optionally press **Copy
   Summary**; press **Continue** (or **Cancel** to abort).
3. In the file dialog, accept the suggested `quill-diagnostics-<timestamp>.zip`
   name and save.

**You should see and hear**
- The review dialog is keyboard-complete and its preview readable; **Cancel** at
  either step reports **"Diagnostics export cancelled"** and writes nothing. On
  Continue + Save, a ZIP is written and QUILL reports **"Saved diagnostics bundle
  to …"**; the file appears in the Diagnostics folder (HELP-07). Secrets are
  redacted and file paths are only included if you ticked the box.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## HELP-15 — Startup Wizard… (`help.startup_wizard`)

*What & why.* The guided first-run setup — pick an intent/profile and opt into AI,
braille, and automation. Re-runnable any time to reconfigure. On the Help menu the
item is labelled **Personalise QUILL…**.

**Before you start**
- Any state. Menu path: **Help menu ▸ Personalise QUILL…**.

**Do this**
1. **Help menu ▸ Personalise QUILL…**.
2. Step through each page by keyboard (make a deliberate choice, e.g. an intent
   and whether you want AI/braille/automation), and **Finish**; or **Escape** to
   abort.

**You should see and hear**
- A multi-step wizard whose every page is labelled, announced, and keyboard-only
  operable. Finishing applies your choices (profile + intent + optional
  Quillin/AI/braille setup) and says so; aborting changes nothing. This is the
  same wizard reached in HELP-13.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## HELP-16 — Status Page (`help.status_page`)

*What & why.* A live, at-a-glance panel of QUILL's runtime state — version, active
profile, background tasks, queued notifications, and (when enabled) speech/BITS
Whisperer readiness. Everything is read locally; **no network is required**.

**Before you start**
- Any state. Menu label: **Status Page**.

**Do this**
1. **Help menu ▸ Status Page**.
2. Read the rows with your screen reader; if a **Refresh** control is present,
   activate it and confirm values update. Close with **Escape**.

**You should see and hear**
- A **Status Page** dialog whose **Version** row reads **1.0.0** and which lists
  the active profile, background-task count, and queued-notification count (plus a
  speech/Whisperer block if that feature is on). Rows are keyboard-navigable and
  announced; the page updates live/on refresh; closing returns focus to Help.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## HELP-17 — Switch Feature Profile… (`help.switch_feature_profile`, Alt+Shift+P)

*What & why.* Opens the accessible profile picker to change how much of QUILL is
exposed (Essential, and richer profiles). On the Help menu it is labelled **Switch
Profile…**.

**Before you start**
- Any state. Shortcut **Alt+Shift+P**; menu path **Help ▸ Feature Profiles ▸
  Switch Profile…**.

**Do this**
1. Press **Alt+Shift+P**, or open **Help menu ▸ Feature Profiles ▸ Switch
   Profile…**.
2. Arrow through the profile list; read each profile's description; select one and
   confirm.

**You should see and hear**
- A keyboard-navigable **profile picker** announcing each profile's name and
  description. Choosing one applies it (menus and available commands change to
  match) and announces the new profile. This is undoable via HELP-18.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## HELP-18 — Undo Last Profile Change (`help.undo_last_profile_change`)

*What & why.* Reverts the most recent profile switch — a safety net after
HELP-17 or HELP-12.

**Before you start**
- Do HELP-17 (switch to a different profile) immediately before this, so there is
  a change to undo. Path: **Help ▸ Feature Profiles ▸ Undo Last Profile Change**.

**Do this**
1. **Help menu ▸ Feature Profiles ▸ Undo Last Profile Change**.

**You should see and hear**
- If there was a recent change, the status bar reports **"Profile changed back to
  <name>"** and menus rebuild to the previous profile. If there is nothing to
  undo, it says **"No profile change to undo"** rather than erroring.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## HELP-19 — What Can I Do Here? (`help.what_can_i_do_here`, Shift+F1)

*What & why.* A plain-language explainer of the actions available for the current
document and selection — orientation for a newcomer who is unsure what to try.

**Before you start**
- `formatting.md` open. Select a few words so the report can mention
  selection-specific actions. Menu label **What Can I Do Here?** carries the
  **Shift+F1** accelerator.

**Do this**
1. Press **Shift+F1**, or **Help menu ▸ What Can I Do Here?**.
2. Read the report; press **Enter** or **Escape** to close.

**You should see and hear**
- An information dialog titled **What Can I Do Here?** describing what you can do
  with the current document (and, because text is selected, selection actions).
  The text is review-cursor readable; closing returns focus to the editor.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## HELP-20 — Why Don't I See a Feature? (`help.why_dont_i_see_feature`)

*What & why.* Look up any feature or command by name and hear **why** it is or
isn't showing — usually the active profile or a feature toggle.

**Before you start**
- Any state. Menu label: **Why Don't I See a Feature?**.

**Do this**
1. **Help menu ▸ Why Don't I See a Feature?**.
2. In the text box (pre-filled with **`regex`**), type a feature/command/topic —
   e.g. **`podcasts`** or a tool you cannot find — and confirm.

**You should see and hear**
- A labelled text-entry dialog, then an information dialog reporting whether the
  feature exists, whether it is enabled, and which profile/toggle governs it (and
  how to turn it on). Cancelling reports **"Feature lookup cancelled"**. All
  keyboard-operable and announced.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## HELP-21 — Why Is This Unavailable? (`help.why_unavailable`, Alt+F1)

*What & why.* Explains why the **currently focused** greyed-out button or menu
item is disabled — answered in place, for the exact control you are on. Has **no
menu entry**: use **Alt+F1** or the Command Palette.

**Before you start**
- Get onto a disabled control first: open a menu (or Tab to a toolbar/dialog
  control) that is greyed out in your current state, and leave focus on it.

**Do this**
1. With focus on the disabled item, press **Alt+F1**.
2. Then, with focus **nowhere useful** (e.g. no target), press **Alt+F1** again to
   confirm the guidance message.

**You should see and hear**
- On a disabled control, QUILL speaks/shows why it is unavailable (reading the
  control's help text / the reason it is gated). With nothing suitable focused, it
  guides you: **"Focus the greyed-out button or menu item you are curious about,
  then press Alt+F1."** — never a silent no-op or an error.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

### Section sign-off
- Tester:
- Screen reader(s) + version(s):
- Build / commit tested:
- Environment (E1–E6):
- Date:
- Scenarios passed / total: ___ / 21
- Release blockers found (must be zero to ship):
- Result: Pass / Pass-with-notes / Fail
- Notes:
