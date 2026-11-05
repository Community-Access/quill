# Appendix D: Notes from earlier versions

This appendix keeps a record of how some parts of QUILL used to work. You
do not need any of it to use QUILL today. The chapters describe QUILL as
it is now, and where a note here disagrees with a chapter, the chapter is
right.

## Fixed in 0.7.0 Beta 2

The Beta 2 release brought a sweep of accessibility, macOS and crash fixes.
Where a fix changes nothing you can see, the note says so; where it does, the
note gives the detail. The full list is in the
[release notes](../release%20notes/release0.8.0-beta1.md).

- **Closing the last document no longer crashes.** Nothing to change. The
  crash showed up as "QUILL encountered an unexpected error and needs to
  close" when you pressed `Ctrl+W` on a document with unsaved changes, chose
  "Don't Save", and the editor was asked about the caret after it had already
  closed. QUILL now checks first, and you will not see that error any more.
- **Help > Check for Updates opens cleanly.** It used to fail with "QUILL
  encountered an unexpected error." Open **Help > Check for Updates** and the
  update channel selector appears as before.
- **The Setup Wizard opens on a clean window, not on top of an "Untitled"
  tab.** If you have already run the wizard, you see the normal "Untitled" tab
  when QUILL starts. On a first run you see the wizard on its own, and an
  untitled document is created for you when the wizard finishes.
- **`Cmd+Q` now quits QUILL on macOS.** The new default is `Ctrl+Q` (which is
  `Cmd+Q` on macOS). Quote Lines moved from `Ctrl+Q` to `Ctrl+Shift+Q` to make
  room, and Unquote Lines moved off `Ctrl+Shift+Q` (today it is on
  `Alt+Shift+.`). A saved `keymap.json` that still has
  the old keys is corrected the first time QUILL starts, and the correction is
  saved so the next start is clean.
- **`Option+Left` and `Option+Right` are no longer taken by Back and Forward
  Location on macOS.** On macOS, Back and Forward Location are now `Cmd+[` and
  `Cmd+]`, the usual Mac back and forward keys used by Safari, Finder and most
  other Mac apps. On Windows they stay on `Alt+Left` and `Alt+Right`. If your
  saved `keymap.json` on a Mac still has the Windows keys, it is changed to
  the new Mac keys the first time QUILL starts, and the change is saved so the
  next start is clean.
- **The Setup Wizard's page heading is the first thing that takes focus, and
  VoiceOver no longer calls the preview "edit text".** On every wizard page a
  screen reader now lands on the heading, not on the read-only preview. The
  preview is shown as a read-only document, so VoiceOver reads it as a
  document or plain text, not as an editable field. Sighted users see the same
  styled preview as before.
- **The wizard's Back and Next buttons are simply "Back" and "Next".**
  VoiceOver on macOS used to read the old labels ("< Back" and "Next >") as
  "less than Back" and "Next greater than". The buttons now read "Back" and
  "Next", which is what every screen reader says and what is printed on the
  button.
- **Read Aloud and Insert Snippet no longer fire when you type a plain `R` or
  `S`.** The key shown beside those items in the Tools and Insert menus was
  being treated as a real shortcut, so the plain letters R and S were caught
  everywhere. The key is now shown as ordinary text after the item name, and
  the letters belong to your writing again.
- **The Help menu is now the macOS system Help menu.** The usual `Cmd+?` Help
  shortcut now works on the Mac. Windows and Linux are unchanged.
- **AI Hub opens cleanly from the wizard, and the editor no longer trips over
  the caret before a document is loaded.** The AI Hub's tab labels and the
  wizard's AI Hub button had the same fault, and the editor failed silently on
  every keystroke before you had even opened a document.
- **JAWS, NVDA, Narrator and VoiceOver now say the QUILL version.** The window
  title now includes the full version (for example, "QUILL for All 0.7.0 Beta
  2"), so any screen reader that reads the window title (JAWS `Insert+T`, NVDA
  `+T`, Narrator `Caps+H`, VoiceOver) says the version along with the document
  name. JAWS's `Ctrl+JAWSKey+V` still says only "Version" until a launcher
  that carries the version ships; the window title is the change you can hear
  today.
- **VoiceOver now reads the editor as a normal text area on macOS.** The
  editor now tells macOS it is a standard text view (`NSTextView`), so
  VoiceOver treats it as an ordinary editable text area with all its usual
  reading commands. Windows is unchanged.
- **The Report a Bug dialog now speaks field names on macOS, opens in its own
  window so you can Alt+Tab to the editor, and no longer opens a browser by
  itself after you submit.** Every field is tied to its label, so VoiceOver
  reads "Summary, edit text", "What happened, edit text" and so on as you tab
  in. The dialog opens in its own window that does not block the editor. The
  report is always on your clipboard after you submit. Opening the browser
  afterwards is now something you turn on in Settings: "After you submit a bug
  report, automatically open the support form in your default browser".
- **`Ctrl+F4` on a document with unsaved changes no longer crashes when you
  choose "Don't Save".** The close prompt was trying to put focus back in the
  editor after the editor had already closed. Save and Cancel work as before,
  and Save still returns focus to the editor.
- **The print-page detector now treats a right-margin continuation as
  certain, and keeps the trailing letter.** In a braille document with
  print-page numbers in the right margin of line 1, the next braille page can
  carry the same number with a continuation letter (for example `7` on braille
  page 1 and `7a` on braille page 2). The print page has not changed; the
  letter is the braille continuation marker. The detector used to rate this
  as `medium` confidence and drop the letter, so the detailed status read
  `Print 7` instead of `Print 7a`. It now matches the previous page's
  right-margin number, rates the boundary `high` confidence, and keeps the
  letter. In practice: open a braille document with right-margin print-page
  numbers, move the caret across a continuation, and the status bar (and
  "Read Detailed Braille Status") reads the full `7a`, not just `7`.

## The original Copy Tray guide

This is the first guide to the Copy Tray, from when it had nine slots. The
Copy Tray now has twelve slots and opens with `Ctrl+Alt+V`. Chapter 4,
Writing and editing, describes it as it is today.

### Overview

Copy Tray gives you nine independently addressable clipboard slots. Each slot
holds a piece of text that you copy there explicitly. Slots survive application
restarts -- their contents are written to disk automatically so nothing is lost
when you close and reopen QUILL.

Unlike the system clipboard, which is shared with every other application and
holds only the most recently copied item, Copy Tray slots are exclusive to
QUILL and hold their contents until you explicitly replace or clear them. This
makes Copy Tray well suited for accumulating related fragments across a long
editing session: quotes from multiple sources, code snippets, address blocks,
standard disclaimers, or any text you paste repeatedly.

### Keyboard Access

#### Paste from a slot

Hold `Ctrl+Shift` and press a number key. That is all.

| Key | Action |
| --- | --- |
| `Ctrl+Alt+Shift+1` | Paste from slot 1 at cursor |
| `Ctrl+Alt+Shift+2` | Paste from slot 2 at cursor |
| `Ctrl+Alt+Shift+3` | Paste from slot 3 at cursor |
| `Ctrl+Alt+Shift+4` | Paste from slot 4 at cursor |
| `Ctrl+Alt+Shift+5` | Paste from slot 5 at cursor |
| `Ctrl+Alt+Shift+6` | Paste from slot 6 at cursor |
| `Ctrl+Alt+Shift+7` | Paste from slot 7 at cursor |
| `Ctrl+Alt+Shift+8` | Paste from slot 8 at cursor |
| `Ctrl+Alt+Shift+9` | Paste from slot 9 at cursor |

If a selection is active when you paste, the pasted text replaces it.
If the slot is empty, QUILL announces "Slot N is empty".

#### Copy to a slot

Hold the QUILL key (`Ctrl+Shift+Grave`), release, then press `Shift+digit`.
The QUILL-key bare digits 1-6 are heading shortcuts; adding Shift is a distinct
binding with no conflict.

| Key | Action |
| --- | --- |
| `Ctrl+Shift+Grave, Shift+1` | Copy selection to slot 1 |
| `Ctrl+Shift+Grave, Shift+2` | Copy selection to slot 2 |
| `Ctrl+Shift+Grave, Shift+3` | Copy selection to slot 3 |
| `Ctrl+Shift+Grave, Shift+4` | Copy selection to slot 4 |
| `Ctrl+Shift+Grave, Shift+5` | Copy selection to slot 5 |
| `Ctrl+Shift+Grave, Shift+6` | Copy selection to slot 6 |
| `Ctrl+Shift+Grave, Shift+7` | Copy selection to slot 7 |
| `Ctrl+Shift+Grave, Shift+8` | Copy selection to slot 8 |
| `Ctrl+Shift+Grave, Shift+9` | Copy selection to slot 9 |

You must have text selected. QUILL announces the slot number and a text
preview: "Copied to slot 2".

#### Management

| Key | Action |
| --- | --- |
| `Ctrl+Alt+V` | Open Copy Tray dialog |

All bindings are reassignable in `Tools > Customize & Support > Keymap Editor` or the Command
Palette.

### Using the Edit Menu

All commands are available in `Edit > Copy Tray`. The submenu contains:

- `Copy to Slot 1` through `Copy to Slot 9` -- copy the current selection
- `Paste from Slot 1` through `Paste from Slot 9` -- paste at the cursor
- `Open Copy Tray...` -- open the management dialog
- `Clear All Tray Slots` -- clear all slots after confirmation

### Using the System Tray Icon

Right-click the QUILL icon in the system notification area (bottom-right
taskbar area). The context menu includes a **Copy Tray** submenu that lists
every occupied slot with its label (if any) and a text preview. Clicking a slot
pastes its content into the currently active QUILL document. This lets you
paste from the tray without bringing the main window to the front.

### Using the Dialog

Open the dialog with `Ctrl+Alt+V`, `Edit > Copy Tray > Open Copy
Tray`, or the Command Palette (`edit.open_copy_tray`). The dialog shows all
nine slots in a list. Each row displays:

- The slot number
- An optional label
- A preview of the stored text (empty slots show `(empty)`)

Navigate the list with the arrow keys. The following buttons appear below the
list:

- **Paste** (Enter or double-click) -- paste the selected slot's text at the
  cursor position and close the dialog. Disabled when the selected slot is
  empty.
- **Copy Selection Here** -- copy the current editor selection into the selected
  slot and refresh the list. Disabled when no text is selected in the editor.
- **Set Label...** -- open a text-entry prompt to name the selected slot. Labels
  appear in all slot listings and in screen-reader announcements.
- **Clear Slot** -- empty the selected slot. Disabled when already empty.
- **Close** (Escape) -- close the dialog without pasting.

### Labelling Slots

Slot labels are optional but recommended for any slot you use regularly. A
label makes the slot identifiable in the dialog and in every spoken
announcement. Labelling slot 1 "signature" means you will hear "Pasted from
slot 1 (signature)" instead of "Pasted from slot 1".

To set a label:

1. Open the Copy Tray dialog.
2. Select the slot you want to label.
3. Press `Set Label...`.
4. Type the label and press Enter.

Labels are persisted alongside slot text and survive restarts.

### Accessibility Notes

- Every Copy Tray operation announces its result through QUILL's screen-reader
  interface. Copy, paste, clear, and label operations all produce spoken
  feedback.
- The slot list in the dialog receives initial focus when the dialog opens.
- Slot labels, when set, are included in every announcement.
- Empty slots are clearly identified as `(empty)` in all contexts.
- The `Clear All Tray Slots` confirmation dialog defaults to No to prevent
  accidental data loss.
- The `Ctrl+Shift+N` paste scheme is designed for screen reader users: one
  familiar chord activates slot N instantly, no menu navigation required.

### Tips

- **Research accumulator.** Assign each tray slot to a document section. Copy
  a relevant excerpt to each slot as you read through a source, then paste
  them in order when drafting.
- **Code boilerplate.** Keep import blocks, standard headers, and closing
  patterns in labelled slots for one-chord insertion.
- **Cross-document paste.** Copy a phrase to a tray slot, switch documents,
  paste from the tray -- the system clipboard is untouched.
- **Persistent library.** Slots survive restarts. Build a set of standard
  fragments you reach for daily.
- **System tray access.** Paste into any QUILL document directly from the
  notification-area icon without bringing the window to the front.


---

---

- Previous: [Appendix C: Every emoji QUILL can insert](quill-guide-appendix-c-every-emoji-quill-can-insert.html)
- Next: [Appendix E: Design notes for developers](quill-guide-appendix-e-design-notes-for-developers.html)
- [Contents](../userguide.html)
