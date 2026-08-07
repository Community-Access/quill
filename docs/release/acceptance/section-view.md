# Section — View, Window & Verbosity (`view.*` + `window.*` + `verbosity.*`, 38 commands)

Everything about **how QUILL looks, how its windows and tabs are arranged, and how
much it talks**. Three namespaces live here because a real user reaches for them
together: change the theme or wrap, jump between the documents you have open, and
turn the speech up or down for the room you are in. Finish **Part 0** first.

Surface reference (label + shortcut) is
`../../planning/signoff/SIGNOFF-editor.md` → the `view.*` (16), `window.*` (14),
and `verbosity.*` (8) sections. Read §2–§3 of `README.md` for the scenario layout
and the Pass/Fail/Blocked/N-A + Works/Surface-exact/Accessible boxes.

Common inputs used below (copy the `../qa-samples/` folder onto the machine first):
`plain.txt`, `formatting.md`, `table.md`.

Two conventions used throughout this section:

- A **chord** written `Ctrl+Shift+Grave, Shift+C` is a two-step shortcut: press and
  release **Ctrl+Shift+Grave** (Grave is the backtick key, top-left), then press
  **Shift+C**. You have a couple of seconds between the two.
- Several items here are **toggles**: pressing them a second time reverses the
  first. Every toggle scenario asks you to press it **twice** and hear both states,
  because a toggle that only announces one direction is half-broken.

---

# View options (`view.*`, 16 commands)

How the editor presents itself: wrap, theme, panels, previews, and the two
accessibility read-outs (contrast and spoken echo). Scenarios VIEW-01 through
VIEW-16.

---

## VIEW-01 — Toggle Soft Wrap (`view.toggle_soft_wrap`, Alt+Z)

*What & why.* Wrap long lines to the window width so you never scroll sideways to
read — or turn it off to see each logical line whole. The everyday reading comfort
switch.

**Before you start**
- Open `plain.txt`. If every line is short, type one very long line (past the
  window edge) so wrapping is visible.

**Do this**
1. Press **Alt+Z**, or open **View menu (Alt, V) ▸ Soft Wrap**.
2. Press **Alt+Z** again to reverse it.

**You should see and hear**
- The first press announces **"Soft wrap on"** and the long line now folds to the
  window width; the second announces **"Soft wrap off"** and the long line runs off
  the edge again. The menu item's checked state matches the spoken state.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VIEW-02 — Toggle Dark Mode (`view.toggle_dark_mode`, Alt+Shift+D)

*What & why.* Flip the editor between the light/system theme and a dark theme —
eye comfort and low-vision contrast.

**Before you start**
- Any document open. Note the current background (light or dark).

**Do this**
1. Press **Alt+Shift+D**, or **View menu ▸ Dark Mode**.
2. Press **Alt+Shift+D** again to return.

**You should see and hear**
- The first press announces **"Dark mode on"** and the editor background turns
  dark; the second announces **"Dark mode off"** and it returns to the light/system
  theme. If a side preview is open (see VIEW-06), it re-renders to match the new
  theme rather than staying light.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VIEW-03 — Announce Contrast Ratio (`view.announce_contrast`, chord then Shift+C)

*What & why.* Read out the measured contrast between the editor's text and
background against the WCAG standard — a low-vision user's proof the theme is
actually readable, not just "dark enough."

**Before you start**
- Any document open, in whatever theme you want to measure. Chord:
  **Ctrl+Shift+Grave** then **Shift+C**.

**Do this**
1. Press the chord **Ctrl+Shift+Grave, Shift+C** (or Command Palette →
   "Announce Contrast Ratio").
2. Toggle dark mode (VIEW-02) and run it again to compare the two numbers.

**You should see and hear**
- QUILL announces the ratio and grade in substance, e.g. **"Contrast ratio:
  7.4:1, WCAG grade: AAA (excellent)"**. The grade band is one of AAA (excellent),
  AA (good), AA large text only (marginal), or below AA (insufficient), and it
  matches the number. It never fails silently — an error reports "Could not
  calculate contrast ratio."

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VIEW-04 — Preview (`view.preview`, Ctrl+Shift+V)

*What & why.* Open a rendered preview of the current document (Markdown/HTML) in an
in-app window, so you hear/see the formatted result, not the raw markup.

**Before you start**
- Open `formatting.md` (it has headings, lists, a link, an image).

**Do this**
1. Press **Ctrl+Shift+V**, or **View menu ▸ Preview**.
2. Read the preview with your screen reader, then close it with **Escape**.

**You should see and hear**
- A preview window opens rendering the document; QUILL announces **"Opened
  preview"**. Because it is a real web document, your screen reader can use
  browse-mode heading navigation inside it. The very first preview on a fresh
  machine may say **"Preparing preview… (one-time WebView2 setup)"** and open a
  moment later — that one-time delay is expected. Escape returns focus to the
  editor.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VIEW-05 — Browser Preview (`view.browser_preview`, chord then V)

*What & why.* Render the same preview in your real web browser — useful for a
full-page read or to hand to someone else. Chord: **Ctrl+Shift+Grave** then **V**.

**Before you start**
- `formatting.md` open. A default browser installed.

**Do this**
1. Press the chord **Ctrl+Shift+Grave, V**, or **View menu ▸ Browser Preview**.

**You should see and hear**
- Your browser opens the rendered document in a new tab; QUILL announces in
  substance **"Opened browser preview in <browser name>"**. Running it again for the
  same document says **"Refreshed browser preview"** rather than piling up new
  browser tabs. With no document open it says "No document open," not an error.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VIEW-06 — Preview Side by Side (`view.split_preview`, Ctrl+Shift+Backslash)

*What & why.* Show a live preview pane to the **right** of the editor and keep it
updating as you type — write and see the result at once.

**Before you start**
- `formatting.md` open.

**Do this**
1. Press **Ctrl+Shift+Backslash**, or **View menu ▸ Preview Side by Side**.
2. Type a new heading line and watch/hear the pane update.
3. Press **Ctrl+Shift+Backslash** again to hide it.

**You should see and hear**
- The first press splits the window and announces **"Preview shown on the right"**;
  the second unsplits and announces **"Preview hidden"**, returning focus to the
  editor. With no document open it says "No document open."

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VIEW-07 — Focus Preview (`view.focus_preview`, Ctrl+F6)

*What & why.* Move keyboard focus **into** the side-preview pane. The editor is an
edit field where NVDA cannot use single-letter browse navigation; the preview is a
real web document where H (headings), K (links) and so on work — this is how you
get there.

**Before you start**
- `formatting.md` open. (You do not need the split open first; this opens it if
  needed.)

**Do this**
1. Press **Ctrl+F6**, or **View menu ▸ Focus Preview**.
2. In the preview, press your screen reader's heading key (NVDA: **H**) to jump
   between headings.
3. Press **Escape** or **F6** to come back to the editor.

**You should see and hear**
- Focus lands inside the preview; QUILL announces **"Moved to preview. Press Escape
  or F6 to return to the editor."** Your screen reader switches to browse mode and
  single-letter navigation works. Escape/F6 announces **"Back in the editor"**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VIEW-08 — Reveal Codes (`view.reveal_codes_toggle`, Alt+F3)

*What & why.* Show/hide the Reveal Codes pane, which exposes the underlying markup
(the "codes" behind the formatting) — a WordPerfect-style read-out for checking
exactly what is in the document.

**Before you start**
- `formatting.md` open.

**Do this**
1. Press **Alt+F3**, or **View menu ▸ Reveal Codes**.
2. Press **F6** to move into the pane and read it, then **Alt+F3** again to hide.

**You should see and hear**
- The first press shows the pane and speaks **"Reveal Codes shown."** (the status
  bar adds the hint "Press F6 to move into it; Alt+F3 to hide"). The second hides it
  and speaks **"Reveal Codes hidden."** If focus was inside the pane when you hide
  it, focus returns to the editor — it is never stranded on a hidden pane. The menu
  item's checked state matches.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VIEW-09 — Show Spoken Echo (`view.spoken_echo`, Alt+Shift+E)

*What & why.* Open a read-only window listing the most recent things QUILL
announced, newest first, so you can re-read a message you missed instead of chasing
it in speech. An accessibility safety net.

**Before you start**
- Any document open. First do a few things that speak (e.g. toggle soft wrap,
  announce contrast) so there is history to show.

**Do this**
1. Press **Alt+Shift+E**, or **View menu ▸ Show Spoken Echo**.
2. Arrow through the read-only text; select a line to copy it. Close with
   **Escape**.

**You should see and hear**
- A dialog titled **"Spoken Echo"** opens with a read-only, arrow-navigable list of
  recent announcements newest-first, labelled so the screen reader reads it as
  "Spoken Echo — read-only history of recent announcements." Text is selectable and
  copyable. Escape returns focus to the editor.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VIEW-10 — Toggle Tab Control (`view.toggle_tab_control`, chord then Shift+T)

*What & why.* Show or hide the visual row of document tabs. Keyboard users who
switch documents with Alt+1..0 (see the Window group) may prefer it hidden; mouse
users want it shown. Chord: **Ctrl+Shift+Grave** then **Shift+T**.

**Before you start**
- Two or three documents open so tabs exist.

**Do this**
1. Press the chord **Ctrl+Shift+Grave, Shift+T**, or **View menu ▸ Tab Control**.
2. Press it again to reverse.

**You should see and hear**
- The first press announces **"Tab control shown"** (or "…hidden") and the tab row
  appears/disappears; the second reverses it. The setting persists and the menu
  item's checked state matches. Hiding the tabs does **not** close any document.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VIEW-11 — Send to Tray (`view.send_to_tray`, chord then T)

*What & why.* Hide QUILL to the Windows system tray/notification area instead of
closing it — tuck it away without losing your documents. Chord:
**Ctrl+Shift+Grave** then **T**.

**Before you start**
- QUILL open with a document. Know how to find the tray/notification area.

**Do this**
1. Press the chord **Ctrl+Shift+Grave, T**, or **View menu ▸ Send to Tray**.
2. Restore QUILL from its tray icon (Enter/context menu on the icon) to confirm your
   document is intact.

**You should see and hear**
- The main window hides and a QUILL tray icon appears; the status line reports it
  was sent to the tray. Restoring from the tray brings the window back with the same
  document open and unchanged. Nothing is closed or lost.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VIEW-12 — Toggle Find Wrap (`view.toggle_find_wrap`)

*What & why.* Decide whether Find, on reaching the end of the document, wraps back
to the top to keep searching, or stops. No default shortcut — reach it from the
menu or the Command Palette.

**Before you start**
- `plain.txt` open with a word that appears more than once.

**Do this**
1. **View menu ▸ Toggle Find Wrap** (or Command Palette → "Toggle Find Wrap").
2. Run it again to reverse.

**You should see and hear**
- The first invocation announces **"Find wrap on"**, the second **"Find wrap off"**;
  the setting persists. With wrap on, a Find that hits the bottom continues from the
  top; with it off, Find stops at the last match. (Verify the search behaviour when
  you run the Edit/Find section.)

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VIEW-13 — Toggle Overwrite Mode (`view.toggle_overwrite_mode`)

*What & why.* Switch between Insert (typing pushes text right) and Overwrite
(typing replaces the character under the caret) — the Insert-key behaviour, as a
command. No default shortcut.

**Before you start**
- `plain.txt` open; place the caret in the middle of a word.

**Do this**
1. **View menu ▸ Toggle Overwrite Mode** (or Command Palette).
2. Type a character and observe replace-vs-insert; run the command again to return.

**You should see and hear**
- The first invocation announces **"Overwrite mode on"** and typing now replaces the
  character under the caret; running it again announces **"Insert mode on"** and
  typing inserts. The status bar's mode cell reflects the current mode.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VIEW-14 — Toggle Persistent Undo (`view.toggle_persistent_undo`)

*What & why.* Keep undo history across save/reopen so you can undo past a save,
rather than losing history when a file is saved. No default shortcut.

**Before you start**
- `plain.txt` open and saved.

**Do this**
1. **View menu ▸ Toggle Persistent Undo** (or Command Palette).
2. Run it again to reverse.

**You should see and hear**
- The first invocation announces **"Persistent undo on"**, the second **"Persistent
  undo off"**. With it on, undo history is preserved for the current file rather than
  reset. No error either way.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VIEW-15 — Toggle Spell Check As You Type (`view.toggle_spellcheck_as_you_type`)

*What & why.* Turn live spell checking on or off while you type. No default
shortcut.

**Before you start**
- `plain.txt` open.

**Do this**
1. **View menu ▸ Toggle Spell Check As You Type** (or Command Palette).
2. Run it again to reverse.

**You should see and hear**
- The first invocation announces **"Spell check as you type on"**, the second
  **"…off"**. With it on, typing a misspelling is flagged; with it off, no live
  flagging occurs.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VIEW-16 — Toggle Word Prediction As You Type (`view.toggle_intellisense_as_you_type`)

*What & why.* Turn the live word-prediction (IntelliSense) pop-up on or off as you
type. The label a user sees is **Word Prediction**. No default shortcut.

**Before you start**
- `plain.txt` open.

**Do this**
1. **View menu ▸ Toggle Word Prediction As You Type** (or Command Palette).
2. Type a few letters and watch for the prediction pop-up; run the command again to
   turn it off.

**You should see and hear**
- The first invocation announces **"Word prediction as you type on"** and a
  prediction pop-up appears as you type; the second announces **"…off"** and hides
  the pop-up. The menu item's checked state matches.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

# Window & tab management (`window.*`, 14 commands)

Opening, moving between, and closing the documents you have open. QUILL keeps
several documents in one window; these commands are how you get around them by
keyboard alone. Scenarios WIN-01 through WIN-05 cover all 14 `window.*` commands
(WIN-02 covers the ten "Go to Document N" commands together).

---

## WIN-01 — New Tab (`window.new_document_tab`, Ctrl+T)

*What & why.* Open a fresh blank document in a new tab alongside what you already
have open.

**Before you start**
- QUILL open with one document (e.g. `plain.txt`).

**Do this**
1. Press **Ctrl+T**, or **Window menu (Alt, W) ▸ New Tab**.

**You should see and hear**
- A new empty document opens and becomes active; the status line reports **"New
  document"** and a create sound plays. The document you had open is **not**
  disturbed — you now have two. Focus lands in the new editor.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WIN-02 — Go to Document 1–10 (`window.go_to_document_1` … `_10`, Alt+1 … Alt+9, Alt+0)

*What & why.* Jump straight to the Nth open document by number — the fastest way to
a specific document without cycling. **Alt+1** is the first tab, **Alt+9** the
ninth, and **Alt+0** the tenth. This one scenario exercises all ten commands
(`window.go_to_document_1` through `window.go_to_document_10`).

**Before you start**
- Open **three** documents so tabs 1, 2 and 3 exist (e.g. `plain.txt`,
  `formatting.md`, `table.md`). Note their order.

**Do this**
1. Press **Alt+2** (or **Window menu ▸ Go to Document 2**). Then **Alt+1**, then
   **Alt+3**.
2. Press **Alt+0** (the "10th document" command) while only three are open, to check
   the out-of-range case.

**You should see and hear**
- Each in-range press switches to that document and announces **"Switched to
  <document name>"** with the right name; the title bar follows. A number with no
  document behind it (here **Alt+0**) does **not** switch and instead announces
  **"No document 10 open"** — never an error, never a silent jump to nowhere.

**Sign off (covers `_1`…`_10`)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WIN-03 — Next Document (`window.next_document`, Ctrl+Tab)

*What & why.* Cycle forward through your open documents.

**Before you start**
- Two or three documents open.

**Do this**
1. Press **Ctrl+Tab**, or **Window menu ▸ Next Document**.
2. Press it enough times to wrap past the last document back to the first.

**You should see and hear**
- Focus moves to the next document and announces **"Switched to <name>"**; after the
  last document it wraps to the first. With only **one** document open it does not
  cycle and announces **"Only one document open"** rather than erroring.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WIN-04 — Previous Document (`window.previous_document`, Ctrl+Shift+Tab)

*What & why.* Cycle backward through your open documents.

**Before you start**
- Two or three documents open.

**Do this**
1. Press **Ctrl+Shift+Tab**, or **Window menu ▸ Previous Document**.
2. Press it enough times to wrap past the first document back to the last.

**You should see and hear**
- Focus moves to the previous document and announces **"Switched to <name>"**;
  before the first document it wraps to the last. With only one document open it
  announces **"Only one document open"**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WIN-05 — Close Other Documents (`window.close_other_documents`, Ctrl+Shift+F4)

*What & why.* Close every open document **except** the current one — clear the desk
in one move while keeping what you are working on.

**Before you start**
- Three documents open; make the one you want to keep active. Give at least one of
  the others an **unsaved change** so the save-guard is exercised.

**Do this**
1. Press **Ctrl+Shift+F4**, or **Window menu ▸ Close Other Documents**.
2. If a document with unsaved changes prompts, choose **Cancel** first (hear it),
   then repeat and choose Save / Don't Save as appropriate.

**You should see and hear**
- The other documents close and the active one remains open and focused. Any
  document with unsaved work triggers a **spoken** Save / Don't Save / Cancel guard
  first — no unsaved work is discarded silently (universal contract, README §3).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

# Speech verbosity (`verbosity.*`, 8 commands)

How much QUILL says out loud, and the tools to review and tune it. The heart of
this group is proving that **changing the level actually changes how much QUILL
announces** — not just that a setting toggles. Scenarios VERB-01 through VERB-08.

The talkativeness ladder has four built-in **profiles**: **Beginner** (full context
for every action, all sounds), **Normal** (informative, the default), **Expert**
(routine confirmations suppressed, errors still speak), and **Quiet** (braille and
the visual status bar only — no speech, no earcons). On top of the profile,
**Quiet Mode** and **Meeting Mode** are instant on/off mutes for the room you are
in. In every case the **status bar keeps the full text** (the "visual floor"), so
nothing is ever lost — it is just not spoken.

---

## VERB-01 — Toggle Quiet Mode (`verbosity.toggle_quiet`)

*What & why.* Instantly silence QUILL's speech and earcons — the "someone just
walked in" button — while the status bar still shows every message. No default
shortcut.

**Before you start**
- `plain.txt` open. Have something handy that normally speaks (e.g. Soft Wrap,
  VIEW-01).

**Do this**
1. Run **verbosity.toggle_quiet** from the **View/Speech menu ▸ Toggle Quiet Mode**
   or the Command Palette → "Toggle Quiet Mode".
2. Now press **Alt+Z** (Soft Wrap) and listen — then read the status bar.
3. Run **Toggle Quiet Mode** again to turn it off and press **Alt+Z** once more.

**You should see and hear**
- Turning it on reports **"Quiet Mode on"** and adds a **[Q]** badge to the status
  bar. With Quiet Mode on, the Soft-Wrap toggle **no longer speaks**, but its text
  ("Soft wrap on/off") still appears on the status bar — proof the floor holds.
  Turning it off reports **"Quiet Mode off"**, drops the [Q] badge, and speech
  returns. This difference in *how much you hear* is the core check.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VERB-02 — Toggle Meeting Mode (`verbosity.toggle_meeting`)

*What & why.* A stronger, presentation-safe mute: hard-silences every earcon and
routes speech through a reduced set, leaving braille and the visual floor. Use it
when you are sharing your screen or presenting. No default shortcut.

**Before you start**
- `plain.txt` open.

**Do this**
1. Run **Toggle Meeting Mode** (menu or Command Palette).
2. Do a few things that normally speak/chime and listen; read the status bar.
3. Run **Toggle Meeting Mode** again to turn it off.

**You should see and hear**
- Turning it on reports **"Meeting Mode on"** and adds an **[M]** badge; earcons go
  silent and speech is reduced, but the status bar keeps full text. Turning it off
  reports **"Meeting Mode off"** and drops the [M] badge. If both modes are on you
  see both badges (**[Q] [M]**).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VERB-03 — Undo Verbosity Change (`verbosity.undo`)

*What & why.* Step back the most recent verbosity change (a mode toggle or profile
change) — an "I didn't mean that" for the speech settings. No default shortcut.

**Before you start**
- `plain.txt` open. First turn **Quiet Mode on** (VERB-01) so there is a change to
  undo.

**Do this**
1. Run **Undo Verbosity Change** (menu or Command Palette).
2. Run it a second time with nothing left to undo.

**You should see and hear**
- The first run reverses the last change and reports it in substance, e.g. **"Undid
  Quiet Mode on"** — and Quiet Mode is actually back off (the [Q] badge clears).
  When there is nothing left to undo it reports **"Nothing to undo"** rather than
  erroring.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VERB-04 — Where Am I (`verbosity.where_am_i`)

*What & why.* Speak the caret's current position on demand — line (of total) and
column — so you can re-orient without moving. No default shortcut.

**Before you start**
- Open `plain.txt` (several lines). Put the caret partway down a line.

**Do this**
1. Run **Where Am I** (menu or Command Palette).

**You should see and hear**
- QUILL speaks the position in substance, e.g. **"Line 4 of 12, column 7"**. The
  numbers match where the caret actually is (move the caret and run it again to
  confirm they change). If a position cannot be read it says **"Position unknown"**
  rather than staying silent.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VERB-05 — What Changed (`verbosity.what_changed`)

*What & why.* Re-speak the most recent announcement — the "wait, what did it just
say?" button. No default shortcut.

**Before you start**
- `plain.txt` open. Do something that speaks (e.g. Soft Wrap, VIEW-01) so there is a
  last announcement.

**Do this**
1. Run **What Changed** (menu or Command Palette).

**You should see and hear**
- QUILL re-speaks the text of the last announcement (e.g. **"Soft wrap on"**). With
  no history yet it says **"Nothing recent"** rather than staying silent.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VERB-06 — Speak Status Bar (`verbosity.speak_status`)

*What & why.* Read the current status-bar message aloud on demand — the visual
floor spoken back to you. No default shortcut.

**Before you start**
- `plain.txt` open. Do something that sets a status message (e.g. a save, or Soft
  Wrap).

**Do this**
1. Run **Speak Status Bar** (menu or Command Palette).

**You should see and hear**
- QUILL speaks the current status-bar text. If the status bar is empty it says
  **"Status bar empty"** rather than staying silent. This works even in Quiet Mode,
  since it is an explicit request to read the floor.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VERB-07 — Verbosity Preferences (`verbosity.preferences`)

*What & why.* The main dial: pick the talkativeness **profile** and the channel mix
(Speech / Braille / Sound / Visual). This is where you prove that **changing the
level changes how much QUILL announces**. No default shortcut.

**Before you start**
- `plain.txt` open.

**Do this**
1. Run **Verbosity Preferences** (menu or Command Palette) to open the
   **"Verbosity Preferences"** dialog.
2. Tab to the **Profile** radio group; note the four choices **Beginner / Normal /
   Expert / Quiet**. Select **Expert**. Close the dialog (**Close** button or
   Escape).
3. Back in the editor, do a couple of routine actions that normally confirm aloud
   (e.g. Soft Wrap on/off) and listen.
4. Reopen Preferences, switch the profile to **Beginner**, close, and repeat the
   same routine actions.

**You should see and hear**
- The dialog's Profile radio group, the four Channels checkboxes (with **Visual**
  checked and disabled — the always-on floor), and the buttons are all labelled and
  reachable by keyboard. The difference is audible: under **Expert**, routine
  confirmations are trimmed/suppressed while errors still speak; under **Beginner**,
  the same actions speak with fuller context. Same action, measurably different
  amount of speech — that is the pass condition. Escape/Close returns focus to the
  editor.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VERB-08 — Announcement History (`verbosity.history`)

*What & why.* Review recent announcements in a browsable list, replay or copy one,
and read its "Why did QUILL say that?" explanation. The deep companion to VIEW-09's
quick Spoken Echo. No default shortcut.

**Before you start**
- `plain.txt` open. First do several things that speak so there is history.

**Do this**
1. Run **Announcement History** (menu or Command Palette). In this build it opens
   the **Verbosity Preferences** surface, where the **History** button opens the
   full **"Announcement history"** dialog — activate it.
2. In the history dialog, use the **Filter** field, arrow the **Announcements**
   list, and try **Replay**, **Copy**, and **Explain** on a selected item.
3. Close with **Escape**.

**You should see and hear**
- The Announcement history dialog shows a labelled **Filter** field, a **Recent
  announcements** list (arrowable), a read-only **"Why did QUILL say that"**
  explanation area, and **Replay / Copy / Explain / Clear History** buttons — all
  keyboard-operable. Replay re-speaks the selected line; Copy puts it on the
  clipboard; Explain fills the explanation area. Escape returns focus.

*Note.* If a future build binds **Announcement History** to open the history dialog
directly (rather than via the Preferences panel's History button), the outcome is
the same dialog — mark Surface-exact against whichever path you actually took and
note it.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

### Section sign-off
- Tester:
- Screen reader(s) + version(s):
- Build / commit tested:
- Environment (E1–E6):
- Date:
- Scenarios passed / total: ___ / 29
- Release blockers found (must be zero to ship):
- Result: Pass / Pass-with-notes / Fail
- Notes:
