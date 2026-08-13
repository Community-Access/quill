# Quill Inkwell changelog

## 1.0.0 -- 2026-08-11

First release. Abbreviation expansion in every Windows application, sharing one
library with QUILL.

### Added

- **System-wide expansion.** A low-level keyboard hook recognises an
  abbreviation as you finish typing it and replaces it in whatever application
  has focus. Expansions are typed as synthesised keystrokes and never touch the
  clipboard.
- **One shared library.** Inkwell and QUILL read and write the same
  `abbreviations.json`. An abbreviation added in either app works in both, with
  no import or sync; the file is re-read whenever it changes on disk.
- **Per-abbreviation settings.** Each entry carries its own category, trigger
  mode (a space or punctuation, a space only, punctuation only, or never), speech
  mode, sound override, trailing-space behaviour, and case sensitivity. Schema
  version 2, backward and forward compatible.
- **Quick Insert.** A type-to-filter picker over every enabled abbreviation,
  ordered by how often each is used, reachable from the window (Ctrl+K) or from
  anywhere (Ctrl+Alt+Shift+K). The only way to reach an entry whose trigger mode
  is Never.
- **New from Clipboard.** Ctrl+Shift+N turns whatever is on the clipboard into a
  new abbreviation, pre-filled.
- **Fill-in fields.** `${field:Label}` and `${field:Label=default}` make an
  expansion ask before it finishes; a label used twice is asked once and filled
  everywhere. The form is the same one QUILL's editor uses, so a template
  behaves identically in both.
- **Categories** with a filter in the manager, and a category column in both
  lists.
- **Variables** in expansions: `${date}`, `${time}`, `${datetime}`, `${day}`,
  `${month}`, `${year}`, `${username}`, `${clipboard}`, `${cursor}`.
- **Case preservation.** `Btw` capitalises and `BTW` shouts, for entries that
  are not case sensitive.
- **Exclusions.** Password managers, the Windows sign-in and lock surfaces, the
  credential prompt, and the UAC dialog are permanently excluded, plus any
  applications the user adds.
- **Paste fallback** for the few applications that drop synthetic keystrokes;
  the previous clipboard contents are always restored.
- **Tray residence**, start-with-Windows, start-minimized, and a close button
  that keeps expansion running.
- **Safe Mode support.** `QUILL_SAFE_MODE=1` prevents the keyboard hook from
  being installed at all.

### Working everywhere you can type

- **Expands only where text is accepted.** Before replacing anything, Inkwell
  checks that the focused element takes text, so backspaces never land in a list
  doing type-ahead or a page where Backspace means "go back". Where it cannot
  tell, it goes ahead -- a missed expansion is the more annoying failure.
- **AltGr characters no longer break expansion.** Windows reports AltGr as
  Ctrl+Alt, and treating that as a command wiped the buffer mid-word on every
  layout that uses it -- German, Polish, Spanish, Portuguese, the Nordic
  layouts. AltGr is now recognised as typing.
- **Backspace immediately after an expansion takes it back**, restoring the
  abbreviation. The offer lasts a few seconds and only in the window where the
  expansion happened.
- **Expand on demand** with Ctrl+Alt+Shift+X (or the Abbreviations menu): expands
  the word before the cursor without waiting for a space or punctuation, so it
  works mid-word, at the end of a line, and for entries set never to expand on
  their own.
- **Quick Insert from anywhere** with Ctrl+Alt+Shift+K.
- **Per-application delivery.** The clipboard-paste route can be turned on for
  one stubborn program (`paste_processes` in `inkwell.json`) instead of globally,
  so no other application has its clipboard borrowed.
- **The hook repairs itself.** Windows silently removes a keyboard hook that
  responds too slowly; Inkwell re-installs its own every few minutes so expansion
  cannot quietly die for the rest of a session.
- **One expander per window.** QUILL's editor expands from the document itself,
  so Inkwell stays out of it rather than expanding the same word a second time.
  QUILL marks its own window; the marker identifies the actual window, so a
  development run and a renamed build are covered alike.
- **Elevated windows are explained, not silently broken.** A normal-privilege
  program cannot see keys typed into an administrator window, so Inkwell says so
  the first time focus lands in one.

### Notes

- Inkwell keeps no clipboard history, by design.
- The keystroke buffer is bounded at 64 characters, held in memory only, cleared
  constantly, and never written anywhere. See the user guide's Privacy section
  and the PRD's security contract.
