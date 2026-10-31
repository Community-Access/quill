# Accessibility Testing for QUILL's Core Tasks

This page is the short, repeatable accessibility test for QUILL: the core
tasks a new user must be able to complete, the keyboard-only, screen reader,
manual and documentation checks for each, and the record of every run. It is
part of QUILL's [accessibility commitments](ACCESSIBILITY.md).

It does not replace the detailed plans. Those go much deeper, and this page
points to them:

- [qa-core-journeys.md](release/qa-core-journeys.md): nine end-to-end editor
  journeys with sample files and exact expected speech.
- [screen-reader-test-plan.md](release/screen-reader-test-plan.md): one case
  for every accessibility, focus and keyboard fix.
- [dialogs.md](qa/dialogs.md): every QUILL dialog, by keyboard.
- The app sign-off sheets in [docs/qa](qa/README.md) for QUILL Lite, Quill
  Radio, QUILL Cast and QUILL Transcribe.

## What the build already checks

Do not spend a manual pass on what the machine checks; those rules fail the
build on their own. They are listed under "Checks the build runs" in
[ACCESSIBILITY.md](ACCESSIBILITY.md#checks-the-build-runs): the accessibility
suite, the dialog keyboard contract, unique access keys, menu keys, F1 help,
announcement and braille parity, and the documentation gates. They run on every
pull request in `.github/workflows/accessibility-ci.yml` and
`.github/workflows/pr-ci.yml`, and locally with:

```powershell
pytest tests/accessibility -q
python -m quill.tools.platform_report
```

Automated checks find some barriers, never all. The checks below need a person.

## The core tasks

These are the tasks every new user meets in their first session. Each check
list below covers all of them.

1. **Install and first run**: run the installer, start QUILL, and get through
   the setup wizard to an empty document.
2. **Open a document and move by heading**: open a Markdown or Word file with
   File > Open (`Ctrl+O`), and move through its headings with Next Heading
   (`Ctrl+Alt+H`) and the screen reader's own heading keys.
3. **Write, format and save**: type a paragraph, make a line a heading, save
   with `Ctrl+S`, and save a copy in another format with File > Save As.
4. **Find and replace**: find a word with `Ctrl+F`, then replace it with
   `Ctrl+H`.
5. **Change a setting**: open Preferences (`Ctrl+,`), find a setting with
   "Find a setting", change it, and close with OK.
6. **Get help and report a problem**: press F1 on a control, then open Help >
   Get Help from Support... (`Ctrl+Alt+F2`) and review the report without
   sending it.

## Keyboard-only checks

Run each core task with the mouse unplugged or untouched. For every link and
control the task uses:

- [ ] It can be reached with Tab and Shift+Tab, the arrow keys, its access key
      or a menu.
- [ ] It can be operated from the keyboard: Enter, Space, the arrow keys where
      expected, and its shortcut if it has one.
- [ ] A visible focus indicator is always present: the caret in text, the
      focus rectangle or highlight on controls and list rows, including in a
      high contrast theme.
- [ ] Focus order is logical: it follows the visual and reading order, with no
      jumps.
- [ ] There is no keyboard trap: focus can move into and out of every dialog,
      list, tree, editor and menu, Escape closes a dialog, and focus returns to
      where it was.
- [ ] The task can be completed end to end.

## Screen reader checks

Run each core task with a screen reader: NVDA, JAWS or Narrator on Windows
(VoiceOver for macOS builds), and with a braille display if you use one.

- [ ] Every control is announced with a name that matches its visible label
      and purpose, and its role (button, edit, check box, list, tab).
- [ ] States are announced: checked, not checked, selected, expanded,
      collapsed, disabled, read-only.
- [ ] Lists, trees and tab groups say what they are and where you are in them.
- [ ] Outcomes the reader cannot see are announced once: a file saved, a search
      with no match, a background task finished, an error with what to do next.
- [ ] Nothing is said twice: QUILL does not repeat a window title, a control
      name or a focus move the reader already announced.
- [ ] What is spoken also appears on the braille display.
- [ ] In the editor, the reading order is the document's order, and headings
      are announced with their level.
- [ ] The task can be completed end to end.

## Manual checks

For each core task:

- [ ] **Keyboard:** the keyboard-only checks above pass.
- [ ] **Descriptive text:** window titles, headings, control labels, status
      messages and error messages say what they are for; an error names the
      specific problem and the next step.
- [ ] **Plain language:** no unexplained jargon; abbreviations are spelled out
      on first use in dialogs and help.
- [ ] **Text size and zoom:** with the editor at a large size (`Ctrl+=` up to
      24 point or more) and with Windows "Make text bigger" at 200 percent, no
      text is cut off, no control overlaps another, and nothing is lost.
- [ ] **Magnification:** with Windows Magnifier at 200 percent or more, focus
      and the caret stay in view as you move.
- [ ] **Contrast and colour:** in the default theme, dark mode and a Windows
      high contrast theme, text and controls are readable, focus is visible,
      and colour is never the only way something is shown.
- [ ] The QUILL key then `Shift+C` (Announce Contrast Ratio) reports a ratio of
      at least 4.5 to 1 for the editor text.

## Documentation checks

For every documentation change, and for a representative set before each
release (the README, CONTRIBUTING.md, ACCESSIBILITY.md, the user guide's
getting-started chapter, the latest release notes, and the issue and pull
request templates):

- [ ] **Structure:** one H1, no skipped heading levels, real lists.
- [ ] **Alternatives:** every image has meaningful alternative text or is
      marked decorative; every diagram has a text description nearby.
- [ ] **Links:** link text says where it goes; no "click here" or bare URLs as
      link text; in-page links resolve.
- [ ] **Captions:** every video has captions, and every podcast episode has a
      transcript (GATE-SITE-LINKS fails an episode without one).
- [ ] **Tables:** a header row, and a sentence before the table saying what it
      holds; rendered pages keep tables in the accessibility tree
      (GATE-DOCA11Y).
- [ ] **Code blocks:** code and commands are text in fenced blocks, never
      pictures, and long commands are explained in prose.
- [ ] The `.html` and `.epub` copies are regenerated
      (`python scripts/check_docs_artifacts.py`).

## Test record

Each run is recorded here: the date, who ran it, the build, the environment,
and the result of each check. A check nobody has run says "not yet run".
Failures are filed as issues with the `accessibility` label and linked from
the result. Copy the template below for each run.

```text
### <task number and name> -- <keyboard | screen reader | manual>

Date:
Run by:
QUILL version (Help > About):
Windows version:
Screen reader and version (and braille display, if any):

Result: pass, or each failure with what was heard and its issue number.
```

### Runs so far

| Task | Keyboard-only | Screen reader | Manual |
| --- | --- | --- | --- |
| 1. Install and first run | Not yet run | Not yet run | Not yet run |
| 2. Open a document and move by heading | Not yet run | Not yet run | Not yet run |
| 3. Write, format and save | Not yet run | Not yet run | Not yet run |
| 4. Find and replace | Not yet run | Not yet run | Not yet run |
| 5. Change a setting | Not yet run | Not yet run | Not yet run |
| 6. Get help and report a problem | Not yet run | Not yet run | Not yet run |

Help running these is wanted in
[issue #1694](https://github.com/Community-Access/quill/issues/1694).

### Documentation review, 2026-10-28

A review of the documentation's Markdown sources, made while adopting the
Open Source Accessibility Framework. It was an automated scan of all 393
Markdown files in the repository plus a reading of the representative set
above; it was not a screen reader test of the rendered pages.

- **Structure:** no skipped heading levels in the README, CONTRIBUTING.md,
  ACCESSIBILITY.md, the user guide or the current release notes. Five other
  documents have a second H1 or a skipped level; tracked in
  [issue #1695](https://github.com/Community-Access/quill/issues/1695).
  Several long design documents and PRDs combine parts under more than one H1;
  they are references for developers and are left as they are for now.
- **Alternatives:** no Markdown image without alternative text. The eight
  places the scan flagged as HTML images without `alt` were prose about the
  `<img>` element, not images.
- **Links:** no "click here", "read more" or "here" link text found.
- **Captions:** no embedded video in the Markdown documentation. Podcast
  episodes and transcripts are kept in step by GATE-SITE-LINKS.
- **Tables:** every table is a Markdown table with a header row; rendered
  tables keep their table role (GATE-DOCA11Y).
- **Code blocks:** all code is text. 133 fenced blocks have no language name,
  which does not affect how they are read, so they are left as they are.
