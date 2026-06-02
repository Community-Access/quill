# QUILL dialog regression checklist

This is the master manual regression checklist for every user-facing dialog in
QUILL. Use it to verify that each dialog opens, is fully keyboard and
screen-reader operable, has a working Escape and an explicit default, and
returns focus to the editor on close.

How to use this file:

- Work through a section, open each dialog with the listed keyboard command (or
  menu path when there is no default key), and confirm it behaves.
- Tick the checkbox when a dialog passes a full pass on the current build.
- When a dialog fails, leave it unticked and file or reference an issue next to
  it.
- Keep this file up to date: whenever a dialog is added, removed, or rebound,
  update the matching row in the same change. See the contributor rule in
  `.github/copilot-instructions.md` ("Keep dialogs.md current").

What "passes" means for every dialog (the A11Y-4 contract):

1. It opens from the listed command or menu path.
2. Tab and Shift+Tab reach every control in a sensible order.
3. A screen reader announces the dialog title and each control.
4. Enter activates the default action; Escape (and the close button) cancels.
5. On close, focus returns to the editor.
6. The dialog does not trap, freeze, or go silent.

Legend: "QUILL key" is the prefix chord, default `Ctrl+Shift+Grave` (backtick).
"via menu" means there is no default keybinding; reach it through the named menu
or the command palette (`Ctrl+Shift+P`).

## A. File: open, save, and session

- [ ] Open File: `Ctrl+O`
- [ ] Save File: `Ctrl+S`
- [ ] Save As: `Ctrl+Shift+S`
- [ ] Page Setup: via File menu
- [ ] Print: `Ctrl+P`
- [ ] Restore Backup: via File menu
- [ ] Choose Encoding: via File menu
- [ ] Open from URL: via File menu
- [ ] Save Session: via File menu
- [ ] Open Session: via File menu

## B. Application settings

- [ ] Settings (tabbed, registry-driven): `Ctrl+,` then `General`
- [ ] Settings search jumps to first matching control (within Settings)
- [ ] Export settings to `.qsf` (button within Settings)
- [ ] Import settings from `.qsf` (button within Settings)
- [ ] Reset to Factory Defaults (button within Settings)
- [ ] Export profile to `.qpf` (button within Settings)
- [ ] Import profile from `.qpf` (button within Settings)
- [ ] Customize Menus (Menu Editor): Edit > Customize Menus... (`app.menu_editor`)
- [ ] Rename Menu (text entry, nested in Customize Menus): Rename... button within Customize Menus
- [ ] Command Palette: `Ctrl+Shift+P`

## C. Navigate

- [ ] Go To Line: `Ctrl+G`
- [ ] Go To Page: `Ctrl+Shift+G`
- [ ] Outline Navigator: `Ctrl+Shift+O`
- [ ] Heading Organizer: QUILL key, then `O`
- [ ] Set Bookmark: via Navigate menu
- [ ] Go To Bookmark: via Navigate menu
- [ ] List Bookmarks: `Alt+Shift+B`

## D. Tools: text analysis

- [ ] Word Count: `Ctrl+Shift+W`
- [ ] Dictionary Status: via Tools menu
- [ ] Spell Check: `F7`
- [ ] Misspelling List: `Alt+Shift+L`
- [ ] Thesaurus: `Shift+F7`

## E. Tools: accessibility

- [ ] Validate Contrast: via Tools menu
- [ ] Link Inventory and Alt-Text: via Tools menu

## F. Tools: document intake

- [ ] Document Intake Report: `Ctrl+Shift+I`
- [ ] Review Extraction Quality: via Tools menu
- [ ] Report Bad Extraction: via Tools menu

## G. Tools: read aloud and OCR

- [ ] Read Aloud Voice Settings: via Tools menu
- [ ] Read Aloud Settings: via Tools menu
- [ ] Generate Speech Audio: via Tools menu
- [ ] OCR Image: via Tools menu
- [ ] OCR Review (nested in OCR Image): appears after OCR completes

## H. Tools: sticky notes

- [ ] New Sticky Note: QUILL key, then `N`
- [ ] Manage Sticky Notes: via Tools menu

## I. Tools: formats and external tools

- [ ] External Tools and Formats: via Tools menu
- [ ] Pandoc Conversion Wizard: via Tools menu

## J. Tools: compare documents

- [ ] Compare with File: via Tools menu
- [ ] Compare Open Documents: via Tools menu
- [ ] Compare Difference List: via Tools menu
- [ ] Compare Options: via Tools menu

## K. Tools: keyboard

- [ ] Keymap Editor: via Tools menu
- [ ] Export Keymap: via Tools menu
- [ ] Import Keymap: via Tools menu

## L. Tools: appearance and behavior

- [ ] Status Bar Layout: via Tools menu
- [ ] Export and Back Up (share/backup export): Tools > Customize > Export and Back Up... (via menu)
- [ ] Save export (file picker, nested in Export and Back Up): Save button within Export and Back Up
- [ ] Import or Restore (share/backup import): Tools > Customize > Import or Restore... (via menu)
- [ ] Open profile or backup (file picker, nested in Import or Restore): opens before the Import or Restore preview

## M. Tools: watch folder

- [ ] Watch Folder Profiles: Tools > Dictation and Watch Folder > Watch Folder Profiles... (`tools.watch_folder_settings`)
- [ ] Watch Queue Monitor: Tools > Dictation and Watch Folder > Watch Folder Queue... (`tools.watch_folder_status`)

## N. Tools: notifications

- [ ] Notifications: via Tools menu

## O. Tools: formatting

- [ ] Insert Link: `Ctrl+K` (shared accessible web form: display text + URL)
- [ ] List Manager: QUILL key, then `L`
- [ ] YAML Structure Editor: via Tools menu

## P. Tools: macros

- [ ] Manage Macros: via Tools menu

## Q. Tools: AI and assistant

- [ ] AI Model and Connection: via Tools menu
- [ ] AI Connection Settings: via Tools menu
- [ ] Ask Quill Chat: via Tools menu
- [ ] Train Writing Style: via Tools menu
- [ ] Writing Assistant: via Tools menu
- [ ] Prompt Studio: via Tools menu
- [ ] Agent Center: via Tools menu
- [ ] Make This Document Accessible: via AI menu (Tools > AI > Make This Document Accessible...)
- [ ] AI Hub: via Tools menu

## R. Tools: BITS Whisperer (speech)

- [ ] Announcement Backend: via Tools menu
- [ ] BITS Model Manager: via Tools menu
- [ ] BITS Model Status: via Tools menu
- [ ] BITS Provider Center: via Tools menu
- [ ] BITS Provider Selection: via Tools menu
- [ ] BITS Readiness Check: via Tools menu
- [ ] BITS Capability Matrix: via Tools menu
- [ ] BITS Download Queue: via Tools menu

## S. Help: features and profile

- [ ] Switch Feature Profile: `Alt+Shift+P`
- [ ] Feature Profile Health Check: via Help menu
- [ ] Manage Individual Features: via Help menu (Help > Feature Profiles > Manage Individual Features...)
- [ ] Why Don't I See a Feature?: via Help menu
- [ ] Profiles and Features: via Help menu

## T. Help: startup and support

- [ ] Startup Wizard: via Help menu
- [ ] About Quill: via Help menu
- [ ] What Can I Do Here?: via Help menu
- [ ] Save Diagnostics: via Help menu
- [ ] Report a Bug: via Help menu
- [ ] BITS Whisperer About: via Help menu

## U. Selection and QUILL key

- [ ] Selection Actions: QUILL key, then `A` (with text selected)

## V. Nested and secondary dialogs

These open only from inside another dialog or flow. Test each by reaching its
parent first.

- [ ] Add or Edit Watch Profile (from Watch Folder Profiles)
- [ ] Browse for folder (from Add or Edit Watch Profile)
- [ ] Watch profile dry-run preview (from Add or Edit Watch Profile, Preview (dry run) button)
- [ ] Select font for HTML headings (from Heading Organizer)
- [ ] Rename list item (from List Manager)
- [ ] New list item (from List Manager)
- [ ] Confirm list deletion (from List Manager)
- [ ] New macro name (from Manage Macros)
- [ ] Confirm profile option (from Profiles and Features)
- [ ] Rename profile (from Profiles and Features)
- [ ] Select profile template (from Profiles and Features)
- [ ] Export profile (from Profiles and Features)
- [ ] Import profile (from Profiles and Features)
- [ ] Review AI Changes (from Ask Quill Chat, when approving an AI replacement that differs from the selection)
- [ ] Add custom prompt (from Prompt Studio)
- [ ] Run Python (from Tools, Python sandbox)
- [ ] Confirm download model (from AI Model Settings)
- [ ] Browse sticky note import and export (from Sticky Notes)
- [ ] Add sticky note from document (from Sticky Notes)
- [ ] Spell check ignore and learn (from Spell Check)
- [ ] Confirm item deletion (from YAML Structure Editor)
- [ ] Regex Helper (from Tools)
- [ ] Update downloaded (from Check for Updates, after a successful download)

## W. Startup-only dialogs

These appear only during a specific startup condition. Test by reproducing the
trigger.

- [ ] Crash Recovery (after an unclean exit)
- [ ] Untrusted Location Warning (opening a file from an untrusted folder)

## Maintenance note

This checklist was generated from a full source scrub of `quill/ui/` (chiefly
`quill/ui/main_frame.py`, plus `palette.py`, `assistant_panel.py`,
`assistant_tools.py`, `ai_model_panel.py`, `style_panel.py`, `sticky_notes.py`,
`preview_dialog.py`, and `web_form.py`) and the bindings in
`quill/core/keymap.py`. When you add or change a dialog, update the matching row
here in the same change so this file stays a faithful, complete map.
