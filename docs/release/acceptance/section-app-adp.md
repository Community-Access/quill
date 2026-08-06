# Section — App launcher & ADP (`app.*` 10, `adp.*` 2)

Two small families that sit at the edges of the editor. **`app.*`** is the
application-level surface: the QuillVille cross-app launcher (open a sibling
app in its own window), the Command Palette, Preferences, Exit, the display
language, and three announcement/diagnostic helpers. **`adp.*`** is the
**Audio Description Project** assistant — a pre-release, ON-by-default search
for described films and TV.

Surface reference (label + shortcut) is
`../../planning/signoff/SIGNOFF-editor.md` → the `## `app.*` (10)` and
`## `adp.*` (2)` sections. Read §2–§3 of `README.md` for the scenario layout,
the Pass/Fail/Blocked/N-A + Works/Surface-exact/Accessible boxes, and §5 for
what **[GATED]** means.

**Two gate notes before you begin.**

- **QuillVille launcher gate.** QUILL 1.0.0 surfaces only the released siblings
  **Quill Radio** and **Quill Weather** in the QuillVille menu; **Cast**,
  **Audio Studio**, **Converter**, and the **Media Player** are built but gated
  and must be **absent** from a public build (single source of truth:
  `RELEASED_APPS` in `quill/core/app_launcher.py`, honored via
  `is_app_released`). A developer build (`QUILL_DEV_BUILD=1`) reveals them all.
  So APP-05 (Media Player) is **N/A** on a public build; the real check is the
  absence proof in `gated-absence.md`.
- **ADP gate.** ADP is guarded by the feature flag **`future.adp_assistant`**,
  which is **ON by default for now** (pre-release, deliberately undocumented for
  users). So the top-level **Audio Description Project** menu is normally
  present and ADP-01/ADP-02 are testable — *unless* a profile has turned the
  flag off, in which case the whole menu is absent and both are **N/A**. The
  separate hands-free **`future.adp_voice_mode`** stays locked off and is out of
  scope here.

---

## APP-01 — Announcement Self-Test (`app.announcement_self_test`)

*What & why.* Answers "is anything actually reaching me?" It announces one test
phrase on every channel, then shows exactly which channels delivered it and
through which backend — the difference between "braille is broken" and "no
display is connected."

**Before you start**
- QUILL open, any document. A screen reader running; optionally a braille
  display connected so you can see a second channel light up.

**Do this**
1. Open the **Command Palette** (**Ctrl+Shift+P**) and run **Announcement
   Self-Test…** (there is no default shortcut).

**You should see and hear**
- You hear the phrase **"QUILL announcement self-test."** spoken (and a sound
  plays). A report then opens (a copyable text surface) listing each channel —
  Speech, Braille, Visual, Transcript — as either **"delivered, through
  <backend>."** or **"not delivered"** with a plain-English reason (e.g. "no
  display bridge"). It ends with a one-line summary, e.g. **"The self-test
  reached 3 channels: speech, transcript, visual."** No status codes; prose you
  can read aloud.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## APP-02 — Command Palette… (`app.command_palette`, Ctrl+Shift+P)

*What & why.* The keyboard-first way to reach any command by name without
hunting through menus. A **double-press** re-runs your last palette command.

**Before you start**
- QUILL open, any document.

**Do this**
1. Press **Ctrl+Shift+P** once. A search dialog opens.
2. Type a few letters of a command name (e.g. `word count`); arrow to a result;
   press **Enter** to run it.
3. Now press **Ctrl+Shift+P** **twice quickly** (within the multi-press window).

**You should see and hear**
- A single press opens the palette: a labelled search field with a results list
  below; typing filters it live; focus starts in the field; **Escape** closes it
  and returns focus to the editor. The chosen command runs. A quick
  **double-press** does **not** reopen the palette — it re-runs the last command
  you ran from it, announced as it fires.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## APP-03 — Change Display Language… (`app.display_language`)

*What & why.* Choose the language for QUILL's menus, dialogs, and messages. In
1.0.0 QUILL ships English only, so on a normal build this command's job is to
say so honestly rather than pretend to offer choices that are not installed.

**Before you start**
- QUILL open, any document. No community translations installed (the shipping
  state).

**Do this**
1. Open the **Command Palette** (**Ctrl+Shift+P**) and run **Change Display
   Language…** (no default shortcut).

**You should see and hear**
- With no translations installed, an information dialog is announced saying QUILL
  is **available in English only** for now and that installed translations will
  appear here later; **OK**/**Escape** dismisses it, nothing changes. If any
  translations *are* installed (dev/translated build), you instead get a
  keyboard-navigable chooser listing **System default** plus each installed
  language; the current one is pre-selected; choosing one saves it and announces
  the change (menus and already-built dialogs update after a restart, runtime
  announcements immediately).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## APP-04 — Exit (`app.exit`, Ctrl+Q)

*What & why.* Quit QUILL, guarding unsaved work on the way out.

**Before you start**
- QUILL open with **one document that has an unsaved change** (type a word in
  `plain.txt` and do not save).

**Do this**
1. Press **Ctrl+Q**, or **File menu ▸ Exit** (label **Exit**).
2. At the unsaved-work guard, choose **Cancel** first (hear it), then repeat and
   choose **Don't Save** / **Save** as appropriate.

**You should see and hear**
- Because there is unsaved work, a **spoken confirmation** appears offering Save
  / Don't Save / Cancel (the universal keyboard contract, README §3 — no
  destructive close without a cancellable prompt). **Cancel** keeps QUILL open
  exactly as it was. Confirming closes the window and the app exits cleanly. With
  **no** unsaved work, Exit closes without a prompt.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## APP-05 — Open the Media Player (`app.open_media_player`) — [GATED]

*What & why.* Launch the standalone **Quill Media Player** from inside QUILL,
reusing the shared library/bookmarks rather than embedding a second player. The
Media Player is a **gated** companion for 1.0.0.

**Before you start**
- Note whether you are on a public build or a developer build
  (`QUILL_DEV_BUILD=1`).

**Do this**
1. Look for **Tools ▸ Media ▸ Media Player…**, or search the Command Palette
   (**Ctrl+Shift+P**) for "Media Player".

**You should see and hear**
- **Public build (expected): ABSENT.** The command is **not registered** and the
  menu item does **not** appear, so it will not show in the palette either. Mark
  this **N/A** and record the real check in **`gated-absence.md`** — do not fail
  it for being missing.
- **Developer build only:** the item appears (command label **"Open the Media
  Player"**; menu label **"Media Player…"** — note the wording differs). Running
  it opens Quill Media Player in its own window (**"Opening Quill Media
  Player."**); if it is not installed, QUILL offers to download it (Yes/No) or
  says it could not be opened — never a silent failure.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## APP-06 — Open Quill Radio (`app.open_radio`)

*What & why.* Launch the standalone **Quill Radio** app in its own window and
process. Radio is a **released** public sibling, so it is present in a normal
build.

**Before you start**
- QUILL open. Quill Radio may or may not be installed alongside QUILL — both
  paths are worth seeing.

**Do this**
1. Open the **QuillVille** menu (in the menu bar, just before Help) and choose
   **Open Quill Radio**. (No default shortcut.)

**You should see and hear**
- Quill Radio opens in its own window with its own system-tray icon; QUILL
  announces **"Opening Quill Radio."** If Radio is already running it simply
  comes to the front (single-instance) rather than opening a second copy. If it
  is **not** installed, QUILL warmly offers to download and install it
  (Yes/No) — and on a source run says it could not be opened; it never fails
  silently and never disturbs the document you are in.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## APP-07 — Open Quill Weather (`app.open_weather`)

*What & why.* Launch the standalone **Quill Weather** app in its own window and
process. Weather is a **released** public sibling.

**Before you start**
- QUILL open.

**Do this**
1. Open the **QuillVille** menu and choose **Open Quill Weather**. (No default
   shortcut.)

**You should see and hear**
- Quill Weather opens in its own window; QUILL announces **"Opening Quill
  Weather."** Already running → it comes forward instead of duplicating. Not
  installed → the same friendly Yes/No download offer as APP-06; never a silent
  failure. Confirm the QuillVille menu lists **only** released siblings (Radio,
  Weather) on a public build — Cast / Audio Studio / Converter must **not**
  appear (their absence is proven in `gated-absence.md`).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## APP-08 — Preferences… (`app.preferences`, Ctrl+,)

*What & why.* Open QUILL's Settings — the one place to change how the app
behaves, organized into categories with a search box and per-setting reset.

**Before you start**
- QUILL open, any document.

**Do this**
1. Press **Ctrl+,** (Control plus comma), or **File/Edit menu ▸ Preferences…**.
2. Tab through a category page; change one setting; use the search box to jump to
   a named setting; try a per-setting **Reset**. Confirm with the default button,
   or **Escape** to cancel.

**You should see and hear**
- A dialog titled **Settings** opens with a **tabbed notebook** of categories
  (announced as "Settings categories"); every field is labelled and reachable by
  keyboard; the search box jumps focus to a matching control; a per-setting Reset
  restores that one default. Saving applies and announces the change; **Escape**
  cancels with no change and returns focus to the editor.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## APP-09 — Repeat Last Announcement (`app.repeat_last_announcement`)

*What & why.* "What did it just say?" Speech is gone the moment it finishes;
this re-announces the most recent message so you can catch it again.

**Before you start**
- QUILL open. First trigger any announcement (e.g. **Ctrl+S** to save, or move
  the cursor so a status is spoken) so there is something to repeat.

**Do this**
1. Open the **Command Palette** (**Ctrl+Shift+P**) and run **Repeat Last
   Announcement** (no default shortcut).
2. As a negative check, restart QUILL and run it again **before** anything else
   has been announced.

**You should see and hear**
- The most recent announcement is spoken again, **forcefully** — it cuts across
  whatever the reader is currently saying (this one you asked for) — and reaches
  every available channel, including braille. On the negative check, instead of
  silence you hear **"No announcement to repeat yet."**

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## APP-10 — Report Editor Surface (`app.report_editor_surface`)

*What & why.* A spoken bug-report helper for someone who cannot screenshot: in
one keystroke it says which editor surface, native window class, emulation
state, and braille bridge are live. **Content-free** — nothing from your
document is spoken.

**Before you start**
- QUILL open with any document.

**Do this**
1. Open the **Command Palette** (**Ctrl+Shift+P**) and run **Report Editor
   Surface** (no default shortcut).

**You should see and hear**
- A single spoken (and status-bar) line naming the diagnostic state, e.g.
  **"Editor surface … Native class … System edit emulation on/off. Braille
  system edit fix on/off. Editor border shown/hidden. Braille output
  active/inactive/no display bridge. Announcement backend …."** Confirm it names
  a real backend and a sensible braille state, and that **no words from your
  document** are read.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## ADP-01 — ADP: Ask about Described Movies and TV… (`adp.ask`) — [GATED `future.adp_assistant`, default ON]

*What & why.* Ask a natural-language question about **audio-described** films,
series, and TV and get a short, speakable answer plus a navigable table of
results. The ADP brain runs on a server; the answer text is fetched from it.

**Before you start**
- The flag **`future.adp_assistant`** is **on** (the default): the top-level
  **Audio Description Project** menu is present. If a profile has turned it off,
  the whole menu is gone — mark **N/A**. Network available (the query reaches the
  ADP server). Not in Safe Mode.
- A question to type: **`what described comedies are on Netflix`**.

**Do this**
1. Open the **Audio Description Project** menu ▸ **Ask ADP…**, or the Command
   Palette (**Ctrl+Shift+P**) → "ADP: Ask about Described Movies and TV".
2. Type the question into the labelled field; press the **Ask** button (Alt+A) or
   Enter.
3. Try **New Conversation** to clear context, then Escape to close.

**You should see and hear**
- A dialog titled **"Ask ADP — Audio Description Search"** opens with a labelled
  question field, an **Ask** button, and a **New Conversation** button. On Ask
  you hear **"Asking ADP…"**; when the answer returns, **focus moves to a
  read-only answer region** (a focus-managed region, deliberately **not** a live
  region) so the reader speaks the answer, and the structured results fill a
  navigable table with a row-count status. In **Safe Mode**, running it instead
  says **"The ADP Assistant is disabled in Safe Mode."** and does nothing else.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## ADP-02 — ADP: Settings… (`adp.settings`) — [GATED `future.adp_assistant`, default ON]

*What & why.* Configure the ADP assistant: its server address, an optional
client access key (kept in the OS credential vault, never in plain settings),
your first name for personalized answers, and whether answers speak
automatically.

**Before you start**
- Same flag as ADP-01 (menu present when `future.adp_assistant` is on, else
  **N/A**).

**Do this**
1. Open the **Audio Description Project** menu ▸ **ADP Settings…**, or the
   Command Palette → "ADP: Settings".
2. Tab through the fields. Confirm the **Server address**, **Client access key**
   (masked), and **first name** fields and the **Speak answers automatically**
   checkbox. Change nothing invalid; press **Save**.
3. As a negative check, set the server address to a value **not** starting with
   `https://` and press Save.

**You should see and hear**
- A dialog titled **"ADP Settings"** with every field labelled and
  keyboard-complete: server address (https-only), a **masked** access-key field
  whose help says leaving it blank uses the built-in key, a first-name field, and
  a **Speak answers automatically** checkbox. **Save** persists and announces
  **"ADP settings saved."** (the key going to the credential vault, not plain
  text). On the negative check the non-https address is **rejected before any
  save** with a spoken **"The server address must start with https; not saved."**
  The hands-free "Route spoken questions to ADP" checkbox is **hidden** unless
  the separate `future.adp_voice_mode` unlock is active — its absence here is
  correct.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

### Section sign-off
- Tester:
- Screen reader(s) + version(s):
- Build / commit tested:
- Environment (E1–E6):
- Date:
- Scenarios passed / total: ___ / 12
- Release blockers found (must be zero to ship):
- Result: Pass / Pass-with-notes / Fail
- Notes:
