# Section — Settings / Preferences (every pane of the Settings dialog)

Everything about **configuring QUILL**: the one Settings dialog and its tabbed
panes, plus the cross-cutting promises that keep your configuration safe — it
persists across a relaunch, it can be reset, a corrupt file is quarantined not
lost, secrets never land in plain text, and Safe Mode ignores the settings it
must. Finish **Part 0** first.

Unlike a single command, "Settings" is a **surface**: one dialog
(`app.preferences`, **Ctrl+,**) with a **notebook of category tabs**. This
section walks the way in (SET-01), then one scenario per tab, then the
cross-cutting safety behaviours. The tab titles and every field come from the
code (`quill/core/settings.py`, `quill/core/settings_specs.py`,
`quill/ui/main_frame_preferences.py`); if a tab or label on screen differs from
what this book prints, fail **Surface-exact** and write down what it said.

The panes (notebook tabs), in order: **General · Editing · Navigation and QUILL
Key · Accessibility and Announcements · Read Aloud · AI and Assistant ·
Performance and Memory · Transcription · Watch Folders · Integration and Context
Menu · Administration · Braille Mode · Spelling Review · Experimental.** A tab
only appears if its feature is enabled in your profile, so a public build may
show fewer than fourteen — that is not a failure (see §5 of `README.md`).

> **Sibling configuration surfaces** (their own dialogs, not tabs of this one)
> live beside Preferences on **Tools ▸ Customize and Support**: *Profiles and
> Features…*, *Status Bar Layout…*, *Keymap Editor…*. They have their own
> scenarios elsewhere in this book; only the Settings dialog and GLOW are
> covered here.

Read §2–§3 of `README.md` for the scenario layout and the
Pass/Fail/Blocked/N-A + Works/Surface-exact/Accessible boxes.

---

## SET-01 — Open Settings and move between panes (`app.preferences`, Ctrl+,)

*What & why.* Get into Settings and prove the whole dialog is drivable by
keyboard and readable by ear — the front door to everything else in this
section.

**Before you start**
- QUILL open, any state. No document is required.

**Do this**
1. Press **Ctrl+,** (Control plus the comma key), or open **Tools menu (Alt, T)
   ▸ Customize and Support ▸ Preferences…**.
2. Listen to where focus lands, then press **Ctrl+Tab** to move to the next tab,
   and **Ctrl+Shift+Tab** to move back. (You can also focus the tab strip and use
   **Left/Right Arrow**.)
3. Press **Tab** to move from the tab strip into the current pane's controls,
   walking them in order; **Shift+Tab** to go back.
4. Do **not** save yet — press **Escape** to close.

**You should see and hear**
- A dialog titled **Settings** opens; it is announced as a tabbed
  (notebook/property-page) dialog whose selector is named **"Settings
  categories."** The first tab, **General**, is selected.
- Each tab is announced by name as you Ctrl+Tab across (**General**, **Editing**,
  **Navigation and QUILL Key**, … through **Experimental**); the pane content
  swaps to match.
- Along the bottom are three buttons: **OK**, **Cancel**, and **Apply**. **Apply**
  starts **disabled** and only enables once you change something (so an untouched
  visit can't "apply" nothing). **OK** saves and closes; **Cancel** (and
  **Escape**) discards and closes; focus returns to where you were.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## SET-02 — General pane (appearance, window, startup)

*What & why.* The everyday look-and-feel and startup choices: theme, title bar,
recent files, and (at the bottom) where QUILL stores its data.

**Before you start**
- Settings open on the **General** tab. Sample change: set **Theme** to **Dark**.

**Do this**
1. Ctrl+Tab to **General** (it opens here).
2. Tab to the **Theme** control (a combo box; choices **System / Light / Dark**).
3. Choose **Dark** with the arrow keys.
4. Press **Apply**.

**You should see and hear**
- The Theme control is announced as a labelled combo box with its current value;
  arrowing changes the selection audibly. On **Apply** the UI repaints to the dark
  theme and the status bar confirms in substance **"Settings applied."**
- The pane also exposes (each labelled, keyboard-reachable): *Title bar path*,
  *Unsaved-change title style*, *Show tab control*, *Recent files to remember*
  (a number), *Default file-open folder* (with a **Choose Default Folder…**
  button), *Interface language*, and a **Data location** block (covered in
  SET-16).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## SET-03 — Editing pane (how the editor behaves)

*What & why.* Writing-time behaviour: autosave cadence, autoformatting, indent,
and conversion-engine choices.

**Before you start**
- Settings open. Sample change: set **Autosave interval (seconds)** to **15**.

**Do this**
1. Ctrl+Tab to **Editing**.
2. Tab to **Autosave interval (seconds)** (a spin/number control, default **30**).
3. Type or arrow the value to **15**.
4. Press **Apply**.

**You should see and hear**
- The spin control is announced with its label and value; changing it is audible.
  On **Apply**, "Settings applied" is confirmed and the live autosave timer is
  re-armed to the new interval (no restart needed).
- Other labelled controls here include *Autoformat straight quotes to curly*,
  *Autoformat double hyphen to dash*, *Links in plain-text export*, and *Word
  document saving engine* — each reachable and announced by keyboard.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## SET-04 — Navigation and QUILL Key pane

*What & why.* Structural movement, Browse Mode feedback, Quick Nav, and the
QUILL-key prefix timing.

**Before you start**
- Settings open. Sample change: set **QUILL browse feedback** to **Both**.

**Do this**
1. Ctrl+Tab to **Navigation and QUILL Key**.
2. Tab to **QUILL browse feedback** (a combo box: sound / speech / both / none).
3. Choose **Both**.
4. Press **Apply**.

**You should see and hear**
- The combo box is labelled and announced; the choice changes audibly and "Settings
  applied" is confirmed.
- Other labelled controls include *QUILL key prefix timeout (seconds)*, *Browse
  mode follow-on timeout* (a combo whose **Custom…** value enables a sibling
  milliseconds spin — the two behave as one row), *Quick Nav debounce
  (milliseconds)*, and the *Include headings / links / lists in Quick Nav*
  checkboxes. Verify the follow-on **Custom…** choice enables its spin and any
  other choice disables it.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## SET-05 — Accessibility and Announcements pane

*What & why.* How QUILL speaks and shows announcements, mirrors them to braille,
and which severities interrupt speech — the heart of a screen-reader-first editor.

**Before you start**
- Settings open. Sample change: set **Interrupt speech for** to **Warnings**.

**Do this**
1. Ctrl+Tab to **Accessibility and Announcements**.
2. Tab to **Interrupt speech for** (a combo: errors / warnings / never).
3. Choose **Warnings**.
4. Press **Apply**.

**You should see and hear**
- The combo is labelled and announced; "Settings applied" is confirmed.
- Other labelled controls include *Show announcements in braille*, *Braille
  announcement style* (speech / compact), *Hold errors on the braille display*,
  *Keep an announcement history*, *Announce entering and leaving dialogs*,
  *Announce indentation depth on Tab*, *Enable sound notifications*, and *Sound
  notification volume*. Each checkbox/combo/slider is reachable and announced with
  its state.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## SET-06 — Read Aloud pane (spoken playback engine and voice)

*What & why.* Choose the Read-Aloud engine and tune the voice — rate, volume,
pitch — for QUILL's own document narration.

**Before you start**
- Settings open. Sample change: set **Read Aloud rate** to **240** (valid 80–450,
  default 200).

**Do this**
1. Ctrl+Tab to **Read Aloud**.
2. Tab to **Read Aloud rate** (a number/spin control).
3. Set it to **240**.
4. Press **Apply**, then run a Read Aloud (see the Speech section) to hear the new
   pace.

**You should see and hear**
- The rate control is announced with label and value; out-of-range typing is
  clamped to 80–450 on save (schema validation), never rejected with a crash.
  Read Aloud then speaks noticeably faster.
- Other labelled controls include *Read Aloud engine* (combo: e.g. SAPI 5, DECtalk,
  Piper, Kokoro, eSpeak, ElevenLabs), *Read Aloud volume*, *Read Aloud pitch*,
  *AI Voice provider / model / voice*, and *Move cursor to follow Read Aloud*.
  **Note:** some engines (Piper, DECtalk, ElevenLabs) need an executable/model or a
  cloud key configured elsewhere; picking one here without that just means playback
  falls back — it should say so, not fail silently.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## SET-07 — AI and Assistant pane [GATED `future.ai`]

*What & why.* The master AI switch, the writing-assistant tone, and the door to
the AI Hub where providers, models, and API keys are managed.

**Before you start**
- **Precondition:** the AI feature is enabled in this profile; otherwise this tab
  is absent — mark **N/A** and confirm absence in `gated-absence.md`.
- Sample change: tick **Use Artificial Intelligence** on.

**Do this**
1. Ctrl+Tab to **AI and Assistant**.
2. Tab to **Use Artificial Intelligence** (the master switch) and toggle it on.
3. Tab to the **Open AI Hub…** button; note it is reachable (do not configure a
   provider here — that is its own section).
4. Note the **Allow external engines** checkbox plus **External engine name** /
   **External engine command** fields.
5. Press **Apply**.

**You should see and hear**
- The master switch is announced as **"Use Artificial Intelligence. Master switch
  for all AI features."**; toggling it enables/disables the rest of the AI menus
  on Apply. The **Open AI Hub…** button is labelled for its purpose.
- The static text confirms **"All other AI settings (providers, models, API keys)
  are managed in the AI Hub."** — i.e. **no API key field lives here** (see SET-21
  for why). **Allow external engines** is off by default and only accepts an
  allow-listed helper command.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## SET-08 — Performance and Memory pane

*What & why.* Keep QUILL light on a modest machine: cap loaded models and unload
idle ones.

**Before you start**
- Settings open. Sample change: set **Unload idle models after (minutes)** to **5**.

**Do this**
1. Ctrl+Tab to **Performance and Memory**.
2. Tab to **Low-resource mode (one model at a time)** — a checkbox — and read its
   state.
3. Tab to **Unload idle models after (minutes)** (a number, default 10) and set it
   to **5**.
4. Press **Apply**.

**You should see and hear**
- Both controls are labelled and announced. On **Apply** the model-lifecycle policy
  is reconfigured live (no restart): idle models now unload after 5 minutes. "Settings
  applied" is confirmed.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## SET-09 — Transcription pane (offline speech / wake word)

*What & why.* Defaults for offline speech-recognition models and the optional
"Hey QUILL" wake word.

**Before you start**
- Settings open. Sample check: read the **Listen for 'Hey QUILL' (wake word)**
  checkbox (default **off**).

**Do this**
1. Ctrl+Tab to **Transcription**.
2. Tab through the controls, reading each label and state.
3. Leave the wake word **off** unless you intend to test it; press **Cancel** if you
   changed nothing.

**You should see and hear**
- Controls are labelled and announced, including *Listen for 'Hey QUILL' (wake
  word)* and *Keep listening for 'Hey QUILL' across restarts*. **Note:** the wake
  word is off by default and, unless you also enable persistence, must not survive
  a restart on its own — verify that in SET-17 if you turn it on.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## SET-10 — Watch Folders pane

*What & why.* The default behaviour for watched-folder automation (QUILL acts on
files that appear in a folder you watch).

**Before you start**
- Settings open. Sample change: tick **Enable folder watching by default** on, then
  set a **Default watch folder**.

**Do this**
1. Ctrl+Tab to **Watch Folders**.
2. Toggle **Enable folder watching by default** on.
3. Tab to **Default watch folder** and enter a folder path (e.g. your
   `qa-samples` copy).
4. Read the *Poll interval (seconds)*, *Include subfolders*, and *Watch folder:
   play a sound on each check* / *let results interrupt speech* controls.
5. Press **Apply**.

**You should see and hear**
- Every control is labelled and keyboard-reachable; the folder path field accepts
  typed text. "Settings applied" is confirmed. **Note:** the ambient tick and
  interrupt flags default **off** — an unrequested check should be silent and must
  not talk over your screen reader.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## SET-11 — Integration and Context Menu pane

*What & why.* Whether QUILL offers itself on the Windows file-manager right-click
menu, and which verbs (Open, OCR, Read, Convert).

**Before you start**
- Settings open. Sample change: tick **Show QUILL in the file-manager right-click
  menu** on.

**Do this**
1. Ctrl+Tab to **Integration and Context Menu**.
2. Toggle **Show QUILL in the file-manager right-click menu** on.
3. Read the verb checkboxes (**Open in QUILL**, **OCR with QUILL**, **Read aloud in
   QUILL**, **Convert with QUILL**) and **File types offered to QUILL**.
4. Press **Apply**.

**You should see and hear**
- Controls are labelled and announced. **Note:** actually registering the shell
  verbs happens via **Tools ▸ Advanced ▸ Install Shell Integration…** (a separate,
  privileged step); this pane sets the preference. Confirm the toggle persists
  (SET-17) rather than confirming Explorer changes here.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## SET-12 — Administration pane (updates, security, developer tools, management)

*What & why.* Update policy, SSH host-key trust, the Developer Console, and the
buttons that export/import/reset your whole configuration.

**Before you start**
- Settings open. Sample check: read **Check for updates on startup** and **Trust
  SSH hosts on first connection** (the safer default is **off**).

**Do this**
1. Ctrl+Tab to **Administration**.
2. Read **Check for updates on startup** (default on) and **Get beta updates**
   (turning beta on triggers a confirm — cancel it).
3. Read **Trust SSH hosts on first connection** — confirm it is **off** by default.
4. Tab to the management buttons: **Export settings…**, **Import settings…**,
   **Reset to Factory Defaults**, **Export profile…**, **Import profile…**. Note
   they are present and reachable (their behaviour is SET-18 / SET-19).
5. Press **Cancel** if you changed nothing.

**You should see and hear**
- Every control is labelled and announced. **Get beta updates** prompts for
  confirmation before switching channels — never silently. **Trust SSH hosts on
  first connection** must default off (QUILL rejects unknown host keys unless you
  opt in — see FILE-23). The five management buttons carry `&` mnemonics and are
  keyboard-operable.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## SET-13 — Braille Mode pane

*What & why.* Braille page geometry, the cell-alignment fix, and braille
announcements — critical for a braille-display user.

**Before you start**
- Settings open. Sample change: set **Cells per line** to **32** (default 40).

**Do this**
1. Ctrl+Tab to **Braille Mode**.
2. Tab to **Cells per line** and set it to **32**.
3. Read **Fix braille cell alignment and selection dots (recommended)** and **Hide
   editor border (required for braille cell alignment)** — both default on.
4. Attempt to **uncheck** *Hide editor border*.
5. Press **Apply**.

**You should see and hear**
- Number and checkbox controls are labelled and announced. Unchecking *Hide editor
  border* raises a spoken warning ("showing the editor border breaks braille cell
  alignment…") with **Show border / Keep it hidden** choices; declining keeps it
  hidden. Changing either braille-editor fix on **Apply** shows a **"Restart to
  apply"** message and speaks that a restart is needed for every document to use the
  new setting.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## SET-14 — Spelling Review pane

*What & why.* How the F7 guided spelling review speaks each misspelling.

**Before you start**
- Settings open. Sample change: set **Spelling review announcement verbosity** to
  a different value than its current one.

**Do this**
1. Ctrl+Tab to **Spelling Review**.
2. Tab to **Spelling review announcement verbosity** (a combo) and change it.
3. Read **Spell out the misspelled word letter by letter**, **Pause before spelling
   the word (milliseconds)**, and **Wrap spelling review to the beginning**.
4. Press **Apply**.

**You should see and hear**
- Each control is labelled and announced; the change is confirmed with "Settings
  applied." Verify later in an F7 review that the new verbosity is honoured.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## SET-15 — Experimental pane (master-switch gating)

*What & why.* Opt-in, for-testing options — and the safety design that hides them
all behind one switch so nothing experimental is reachable by accident.

**Before you start**
- Settings open. Start with the master switch **off** (its default).

**Do this**
1. Ctrl+Tab to **Experimental**.
2. With **Enable experimental features (the master switch for everything on this
   tab)** off, Tab through the pane.
3. Now tick the master switch on and Tab again.
4. Press **Cancel** (leave experimental off unless a later scenario needs it).

**You should see and hear**
- With the master switch **off**, every other control on the tab is **disabled** —
  to a screen-reader user the tab is a single reachable checkbox; the experimental
  options (GLOW review/repair, WordPress publishing, Table Studio, browser Read
  Aloud) drop out of the Tab order and cannot be focused or changed.
- Ticking the master switch **on** live-enables those controls (they enter the Tab
  order). The pane's own text reminds you to **restart** after changing anything
  here.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## SET-16 — Data location and storage mode (applied on next launch)

*What & why.* Choose where QUILL keeps all its data (settings, keymap, documents)
— user profile, a portable drive, or a custom folder. Because settings.json lives
*inside* the data folder, a move can only take effect on the next launch.

**Before you start**
- Settings open on **General**. This scenario **moves QUILL's data** — do it on a
  test machine, and know your current data folder first.

**Do this**
1. On the **General** tab, Tab down to the **Data location** block (**"Store
   QUILL's data:"** combo).
2. Choose **Custom folder**; the **Choose Folder…** button enables. Activate it and
   pick an empty test folder.
3. Press **OK**.
4. When the **Data Location Changed** dialog offers **Restart Now / Later**, choose
   **Restart Now**.

**You should see and hear**
- The mode combo is labelled **"Data location"**; the **Choose Folder…** button
  only enables for **Custom folder**; the chosen path is displayed. On OK a spoken
  **"Data Location Changed"** dialog explains the move takes effect on the next
  start and offers **Restart Now / Later**. After the restart, QUILL reads and
  writes under the new folder (a status/announcement reports the completed move).
  **Note:** on relaunch you may also see a one-time **Import Previous QUILL Data**
  offer if a populated old folder is detected — that is expected.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## SET-17 — Changes persist across a relaunch

*What & why.* A setting you changed must still be set after you quit and reopen —
proof that saves are written atomically and reloaded from disk.

**Before you start**
- Pick one change you can verify by ear or eye. Suggested: **Theme = Dark** (SET-02).

**Do this**
1. Open Settings, set **Theme** to **Dark**, press **OK**.
2. Fully **quit** QUILL (File ▸ Exit, or **Alt+F4**), then **relaunch** it.
3. Open Settings again and read the **Theme** value.

**You should see and hear**
- After relaunch the app is still in **Dark** theme and the Theme combo still reads
  **Dark**. The change survived the restart. (Behind the scenes only your override
  is stored, as a versioned delta, written atomically — but what you verify is
  simply that the value stuck.)

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## SET-18 — Reset to Factory Defaults

*What & why.* Put every setting back to how it shipped, in one confirmed step.

**Before you start**
- Change two or three settings first (e.g. Theme = Dark, Autosave = 15) so a reset
  is observable.

**Do this**
1. Open Settings ▸ **Administration** tab.
2. Activate **Reset to Factory Defaults**.
3. In the confirmation, choose **No** first (hear it), then repeat and choose **Yes**.

**You should see and hear**
- A spoken confirmation warns **"Reset every setting to its factory default? This
  cannot be undone."** with a Yes/No you can cancel. On Yes, every setting returns
  to its default (Theme back to **System**, Autosave back to **30**), the UI
  re-applies (theme, menus, title), and the status confirms **"Reset settings to
  factory defaults."**

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## SET-19 — Export and Import your settings (`.qsf`)

*What & why.* Carry your configuration to another machine, or back it up — a
portable, validated snapshot.

**Before you start**
- Set a recognisable value first (e.g. **Autosave = 12**). Target file name:
  **`qa-settings`**.

**Do this**
1. Open Settings ▸ **Administration** ▸ **Export settings…**; save
   **`qa-settings.qsf`** to a known folder.
2. Change **Autosave** to something else (e.g. **45**) and press **OK**.
3. Reopen Settings ▸ **Administration** ▸ **Import settings…**; pick
   **`qa-settings.qsf`**.

**You should see and hear**
- Export writes a `.qsf` file and confirms **"Exported settings to
  qa-settings.qsf."** Import reads it back and re-applies; **Autosave** returns to
  **12**. A malformed or partial file is handled gracefully (unknown keys ignored,
  values re-validated) — it never produces an invalid configuration or a crash;
  an unreadable file reports "Could not read settings from …" plainly.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## SET-20 — A corrupt settings file is quarantined, not lost

*What & why.* If `settings.json` is ever damaged, QUILL must start on defaults and
keep your original safe for recovery — never crash and never silently destroy it.
Cross-reference **install-matrix INST-06** (migration/quarantine on install).

**Before you start**
- **Precondition:** a dev/test build where you can reach the data folder. Locate
  `settings.json` in QUILL's data folder (see SET-16 for where that is; on a normal
  install it is under your user profile's app-data area). QUILL should be **closed**.

**Do this**
1. With QUILL closed, open `settings.json` in a plain text editor and replace its
   contents with junk (e.g. the single line `not json {{{`), and save.
2. Launch QUILL.
3. After launch, look in the data folder for a quarantined copy of the bad file
   (a backup/corrupt copy alongside a fresh `settings.json`).

**You should see and hear**
- QUILL **starts normally on default settings** — no crash, no error wall. The
  damaged file is **quarantined** (backed up) rather than deleted, and a fresh valid
  `settings.json` is written, so your original is recoverable. **Note:** the exact
  backup filename/location is an implementation detail — confirm a copy of the bad
  content exists somewhere in the data area; if you cannot find it, record what you
  did see in Notes.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## SET-21 — Sensitive settings live in the secret store, not plain text

*What & why.* API keys and connection secrets must never sit in `settings.json`
in the clear — they belong in the platform secret store (Windows Credential
Manager / DPAPI).

**Before you start**
- **Precondition:** AI enabled (SET-07). You will enter a provider API key in the
  **AI Hub** (its own dialog); use a throwaway/test key. If AI is gated off, mark
  **N/A**.

**Do this**
1. Open Settings ▸ **AI and Assistant** ▸ **Open AI Hub…** and set a provider that
   requires a key; enter the test key and save it. (Detailed AI-Hub steps are in the
   AI section; here you only need a key stored.)
2. Close QUILL. Open `settings.json` and the exported `.qsf` from SET-19 in a text
   editor and **search for your key**.

**You should see and hear**
- The AI Hub confirms the key is accepted and, in substance, that **"Your key is
  stored securely on this device and never shared."** The key does **not** appear
  anywhere in `settings.json` or in an exported `.qsf` — those hold only non-secret
  knobs. (SSH site secrets behave the same way; see FILE-24.) If a raw key is found
  in either file, that is a **Fail**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## SET-22 — Safe Mode ignores the settings it must

*What & why.* Safe Mode is the recovery path: it must ignore the settings that
could keep QUILL from starting cleanly — AI, file watchers, experimental features,
startup restore, custom themes/snippets, network services — **without erasing** the
stored values.

**Before you start**
- First, with QUILL in normal mode, turn **on** several of the affected settings and
  **OK** them: **Use Artificial Intelligence** (SET-07), **Enable folder watching by
  default** (SET-10), and **Enable experimental features** (SET-15). Then quit.

**Do this**
1. Launch QUILL in Safe Mode: start it with **`--safe-mode`**, or set the
   environment variable **`QUILL_SAFE_MODE=1`** and launch.
2. Observe the AI menus/features, watch-folder automation, and the experimental
   items.
3. Quit Safe Mode and relaunch normally; reopen Settings.

**You should see and hear**
- In Safe Mode, AI integrations, file watchers, experimental features, startup
  restore, custom themes/snippets, and network services are **off / unavailable**
  regardless of what you set — Safe Mode overrides them for the session. QUILL
  starts and is usable.
- Back in normal mode, your **stored** settings are unchanged — the toggles you
  enabled are still on. Safe Mode ignored them; it did not rewrite them.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## SET-23 — GLOW Accessibility settings [GATED `core.glow`]

*What & why.* QUILL's built-in accessibility engine (GLOW): on by default and
local; its optional networked features are consent-gated and off until you turn
them on.

**Before you start**
- **Precondition:** the GLOW feature is enabled in this profile; otherwise mark
  **N/A**. **Note:** GLOW settings open from the Preferences categories list / the
  Customize-and-Support area rather than as a tab of the Settings dialog; if you
  cannot find the entry in your build, record that in Notes.

**Do this**
1. Open the **GLOW Accessibility** settings dialog.
2. Read the four controls: **Enable the GLOW accessibility engine** (default on),
   and the three consent checkboxes — **AI alt-text generation**, **PII redaction**,
   **WCAG language processing** — each marked **(uses the network)** and default off.
3. Toggle one consent on, then press **OK**; reopen to confirm it stuck.

**You should see and hear**
- The dialog explains GLOW is on by default and runs on your computer, and that the
  networked options are off until you enable them and that **"Quill never sends your
  document anywhere without asking first."** Each checkbox is labelled and
  keyboard-operable; on OK the status confirms **"GLOW settings saved"** and the
  choice persists.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

### Section sign-off
- Tester:
- Screen reader(s) + version(s):
- Build / commit tested:
- Environment (E1–E6):
- Date:
- Scenarios passed / total: ___ / 23
- Release blockers found (must be zero to ship):
- Result: Pass / Pass-with-notes / Fail
- Notes:
