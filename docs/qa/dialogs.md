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

This manual checklist is the human companion to the machine-enforced dialog
registry. The authoritative, source-of-truth inventory of every dialog *surface*
is generated from code by `quill/tools/dialog_inventory.py` and committed as
`tests/unit/ui/fixtures/dialog_inventory.json`; the A11Y-4 banned-pattern gate
and `tests/unit/ui/test_dialog_inventory.py` fail the build if any dialog is
unregistered, unclassified, or on a bespoke surface. Regenerate the snapshot with
`python -m quill.tools.dialog_inventory --write` whenever you add, move, or
remove a dialog. See "Dialog Excellence Mandates" in the copilot instructions.

What "passes" means for every dialog (the A11Y-4 contract):

1. It opens from the listed command or menu path.
2. Tab and Shift+Tab reach every control in a sensible order.
3. A screen reader announces the dialog title and each control.
4. Enter activates the default action; Escape (and the close button) cancels.
5. On close, focus returns to the editor.
6. The dialog does not trap, freeze, or go silent.

Automated companion tests and the manual QA plan:

- **Announcement and SR detection tests** — `tests/accessibility/test_accessibility_suite.py`
  and `tests/accessibility/test_announcement_grammar.py` cover screen-reader announcement
  capture, SR detection, and announcement grammar. Run with `pytest tests/accessibility/ -q`.
- **Manual QA procedure** — `docs/QUILL-PRD.md` §6 ("Dialog estate pass")
  describes the full human-executed pass against this checklist, including the SR coverage
  matrix (NVDA full, JAWS spot, Narrator sanity) and the A11Y-4 sign-off criteria.

Legend: "QUILL key" is the prefix chord, default `Ctrl+Shift+Grave` (backtick).
"via menu" means there is no default keybinding; reach it through the named menu
or the command palette (`Ctrl+Shift+P`).

## A. File: open, save, and session

- [ ] Open File: `Ctrl+O`
- [ ] Save File: `Ctrl+S`
- [ ] Save As: `Ctrl+Shift+S`
- [ ] Reload in matching view (after Save As changes the format): native Yes/No prompt, shown after `Ctrl+Shift+S` when `save_as_surface_sync` is "Ask each time"
- [ ] Page Setup: via File menu
- [ ] Print: `Ctrl+P`
- [ ] Restore Backup: via File menu
- [ ] Choose Encoding: via File menu
- [ ] Open from URL: via File menu
- [ ] Open from Remote...: QUILL key, then `Shift+O` (issues #154, #155, #156, #157)
  - [ ] Site list (saved FTP, SFTP, WebDAV, S3 sites) and directory browser
  - [ ] New site / Edit site / Delete site buttons
  - [ ] Open button enabled only when a file is selected
- [ ] Save to Remote...: QUILL key, then `W` (issues #154, #155, #156, #157)
  - [ ] Site list and remote directory browser
  - [ ] Save button enabled only when a target file is selected
- [ ] Save Copy to Remote...: via File menu
- [ ] Manage Remote Sites...: QUILL key, then `Shift+M` (issues #154, #155, #156, #157)
  - [ ] Add / Edit / Delete saved sites
  - [ ] Site editor sub-dialog with protocol-specific fields (FTP, SFTP, WebDAV, S3)
  - [ ] Site editor Save button disabled until the required fields are filled
- [ ] Save Session: via File menu
- [ ] Open Session: via File menu

### A.1. Edit over SSH (issue #139)

- [ ] SSH Quick Connect: File > Open over SSH > Quick Connect... (no default key; command palette `Ctrl+Shift+P`)
  - [ ] Host / port / username / authentication / password / key file path / start directory
  - [ ] Private key file field has a Browse button and a tooltip explaining supported formats (OpenSSH, PEM, PuTTY .ppk)
- [ ] SSH Site Manager: File > Open over SSH > Site Manager... (no default key; command palette)
  - [ ] Saved-sites list with New / Edit / Delete / Connect / Close
  - [ ] Site editor sub-dialog: friendly name, host, port, username, authentication, private key file path, default directory
  - [ ] Site editor Save button disabled until the required fields are filled
  - [ ] Private key file field has a Browse button and a tooltip explaining supported formats

## B. Application settings

- [ ] Preferences hub (multi-page book control): `Ctrl+,`
  - [ ] Category selector navigable by arrow keys with first-letter type-ahead, first category selected on open
  - [ ] Each category page opens its area with its `Open ...` button
- [ ] Settings (tabbed, registry-driven): `Ctrl+,` then `Open General`
- [ ] Export settings to `.qsf` (button within Settings)
- [ ] Import settings from `.qsf` (button within Settings)
- [ ] Reset to Factory Defaults (button within Settings)
- [ ] Export profile to `.qpf` (button within Settings)
- [ ] Import profile from `.qpf` (button within Settings)
- [ ] Customize Menus (Menu Editor, three tabs): Tools > Customize > Customize Menus... (`app.menu_editor`)
  - [ ] Top-Level Menus tab: reorder, rename, show/hide, and reset top-level menus
  - [ ] Menu Items tab: select a menu, then reorder, rename, show/hide its items
  - [ ] Context Menu tab: reorder, rename, show/hide context menu items
  - [ ] Rename Menu/Item (text entry, nested): Rename... button within any tab
- [ ] GLOW Accessibility settings (accessible web form): Preferences (`Ctrl+,`) > GLOW Accessibility
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
- [ ] Look Up (definitions/synonyms, with Add to Dictionary): editor context menu (`Shift+F10`) > Look Up

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
- [ ] OCR Clipboard Image: via Tools menu
- [ ] OCR Screen Capture: via Tools menu
- [ ] OCR Screen Capture target chooser (nested in OCR Screen Capture): whole screen or active window
- [ ] OCR Review (nested in OCR Image, OCR Clipboard Image, OCR Screen Capture): appears after OCR completes

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

## J2. Tools: Quillins (extensions)

The Quillins Manager always opens, even when third-party Quillins are disabled
(SEC-8 `core.third_party_plugins` is locked off for 1.0); it then reports that
state and lists any installed Quillins read-only.

- [ ] Quillins Manager (list, details, Enable/Disable/Reload/Remove): Tools > Quillins > Manage Quillins... (`tools.quillins_manager`)

## K. Tools: keyboard

- [ ] Keymap Editor: via Tools menu
- [ ] Edit Keybinding (text entry, nested in Keymap Editor): Edit Keybinding... button or double-click within Keymap Editor
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
- [ ] Forget API Key (confirmation): via Tools > AI Assistant
- [ ] Ask Quill Chat: via Tools menu
- [ ] Train Writing Style: via Tools menu
- [ ] Writing Assistant: via Tools menu
- [ ] Prompt Studio: via Tools menu
- [ ] Agent Center: via Tools menu
- [ ] Accessibility Tune-Up: via Tools > AI Assistant (Tools > AI Assistant > Accessibility Tune-Up...)
- [ ] AI Hub: via Tools menu
- [ ] Set Up GitHub Copilot: via AI menu (AI > Set Up GitHub Copilot...), or by choosing GitHub Copilot in the AI engine switcher when its SDK is not installed
- [ ] Validate Agents: via AI menu (AI > Validate Agents...). Lints built-in agents by default; Choose Folder/File to validate your own

## R. Tools: BITS Whisperer (speech)

- [ ] Announcement Backend: via Tools menu
- [ ] BITS Model Manager: via Tools menu
- [ ] BITS Model Status: via Tools menu
- [ ] BITS Provider Center: via Tools menu
- [ ] BITS Provider Selection: via Tools menu
- [ ] BITS Readiness Check: via Tools menu
- [ ] BITS Capability Matrix: via Tools menu
- [ ] BITS Download Queue: via Tools menu

## R2. Publishing

- [ ] Publishing Connections: File > Publish > Publishing Connections...
- [ ] Verify Current Publishing Connection: File > Publish > Verify Current Publishing Connection
- [ ] Browse Published Content: File > Publish > Browse Published Content...
- [ ] Edit Publishing Connection: from Publishing Connections
- [ ] Schedule Publish: File > Publish > Schedule Publish...

## S. Help: features and profile

- [ ] Switch Feature Profile: `Alt+Shift+P`
- [ ] Feature Profile Health Check: via Help menu
- [ ] Manage Individual Features: via Help menu (Help > Feature Profiles > Manage Individual Features...)
- [ ] Why Don't I See a Feature?: via Help menu
- [ ] Profiles and Features: via Help menu

## T. Help: startup and support

- [ ] Startup Wizard: via Help menu
  - [ ] GLOW Accessibility Onboarding (accessible web form, from Startup Wizard sequence)
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
- [ ] Remove Quillin confirm (from Quillins Manager, Remove... button)
- [ ] Quillin permission request (from running a third-party Quillin that requests a consent-gated capability: fs.read, fs.write, or net)
- [ ] Site editor sub-dialog (from Manage Remote Sites, New site... or Edit site... button)

## W. Power Tools and recirculated editor conveniences

Editor power-tool conveniences (EDS-1..20). These commands carry no default
keybinding; reach each from its conventional menu home (or the command palette,
`Ctrl+Shift+P`). As of the menu reorg (menus.md §3.7) these commands were
recirculated out of the former power-tools monolith into their natural
menus; the cohesive editor-behavior remainder lives under **Tools > Power
Tools**. Only the commands that present a dialog are listed here; the remaining
power-tool commands act directly on the document and announce their result.

- [ ] Insert Special Character (codepoint prompt): Insert > Insert Special Character
- [ ] Insert File Content (file picker): Insert > Insert File Content
- [ ] Number Lines (start prompt): Format > Transform Lines > Number Lines
- [ ] Hard-Wrap Lines (width prompt): Format > Transform Lines > Hard-Wrap Lines
- [ ] Count Matches (regex prompt): Search > Count Matches
- [ ] Extract Matches (regex prompt): Search > Extract Matches
- [ ] Go to Percent (percentage prompt): Navigate > Go to Percent
- [ ] Infer Indentation (adopt-unit confirm): Tools > Power Tools > Infer Indentation
- [ ] Rename Current File (name prompt): File > Rename Current File
- [ ] Delete Current File (delete confirm): File > Delete Current File

## X. Notebook (Workspace) dialogs

Multi-document workspace commands (§10.4 Milestone 2). All custom surfaces are
`hardened_custom` per the dialog contract.

- [ ] New Notebook (name prompt + file-save picker): File > Notebook > New Notebook
- [ ] New Notebook from Folder (folder picker + name prompt + file-save picker):
  File > Notebook > New from Folder
- [ ] Open Notebook (file-open picker filtered to `.quillnotebook`):
  File > Notebook > Open Notebook
- [ ] Save Snapshot (name prompt): File > Notebook > Save Snapshot
- [ ] Manage Snapshots (list with Rename / Delete buttons): `hardened_custom`
  (wires `apply_modal_ids`): File > Notebook > Manage Snapshots
- [ ] Go to Entry in Notebook (tree navigator — `_show_tree_navigator`):
  Navigate > Go to Entry in Notebook
- [ ] Go to Heading in Notebook (tree navigator — `_show_tree_navigator`):
  Navigate > Go to Heading in Notebook

## Y. Startup-only dialogs

These appear only during a specific startup condition. Test by reproducing the
trigger.

- [ ] Crash Recovery (after an unclean exit)
- [ ] Untrusted Location Warning (opening a file from an untrusted folder)
- [ ] Safe Mode banner / status-bar indicator (when `QUILL_SAFE_MODE=1` is set
  on the environment, or `quill --safe-mode` is passed): the status bar shows
  "Safe Mode — plugins, AI, and network disabled" and a one-shot announcement
  fires on first show. Verified manually by setting the env var before launch
  and confirming the AI / assistant surfaces and watch-folder network calls
  short-circuit per `quill/stability/safe_mode.py`. Cross-reference: the
  pre-release review's N-10 / H-SAFE-1 fixes.

## Maintenance note

This checklist was generated from a full source scrub of `quill/ui/` (chiefly
`quill/ui/main_frame.py`, plus `palette.py`, `assistant_panel.py`,
`assistant_tools.py`, `ai_model_panel.py`, `train_style_dialog.py`, `sticky_notes.py`,
`preview_dialog.py`, and `web_form.py`) and the bindings in
`quill/core/keymap.py`. When you add or change a dialog, update the matching row
here in the same change so this file stays a faithful, complete map.

## Cross-references

- **Safe Mode** — see `quill/stability/safe_mode.py` (env-var contract is
  `QUILL_SAFE_MODE=1`) and `quill/stability/__init__.py` (`SafeModeConfig`,
  `build_safe_mode_config`). When safe mode is active, the AI assistant
  surfaces in section Q, the BITS / Whisperer surfaces in section R, the
  watch-folder network calls in section M, and the Agent Center all
  short-circuit. Manual verification: launch with `set QUILL_SAFE_MODE=1`
  (cmd) / `$env:QUILL_SAFE_MODE=1` (PowerShell) / `--safe-mode` (CLI flag);
  confirm the status-bar banner and the AI/assistant menu items are
  disabled.
