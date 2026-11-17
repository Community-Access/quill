# Accessibility Progress Updates

What has changed in QUILL's accessibility, what is still open, and what we
know is not yet good enough. The newest update is first. Our commitments are
in [ACCESSIBILITY.md](ACCESSIBILITY.md).

A new update is written each month, prompted by the **Accessibility feedback
and progress** issue that `.github/workflows/accessibility-review.yml` opens on
the first of the month, and each release's notes link to the latest one. Counts
are counts of work, not a score: no number here says how accessible QUILL is.

## November 2026 (to 17 November)

This entry is written partway through the month and will be finished at its
end.

### Completed

- **Controls without a label of their own can now be named** (2026-11-09).
  QUILL moved to wxPython 4.3.2 (wxWidgets 3.3.4), the first release with
  `SetAccessibleName`, and names such a control with it instead of a
  workaround, so a screen reader reads the name straight from the control.
  The code and its tests are done; the by-ear check is still open in
  [#1693](https://github.com/Community-Access/quill/issues/1693).
- **F1 help everywhere in the GitHub Workbench** (2026-11-10): what the
  window and the focused control are for, Shift+F1 for every action with its
  key, Alt+F1 for the GitHub word under the cursor, and a Help and Learning
  branch of the tree. QUILL Lite has the same. See the CHANGELOG entry "Help
  everywhere in the GitHub Workbench".
- **Ctrl+Alt+F2 opens Get Help from Support in the nightly keyboard run.** The
  continuous integration (CI) user interface automation run had sent the
  chord in a way that lost Ctrl and Alt; with the modifiers held down
  explicitly it has passed every night since 2026-11-12, and the test no
  longer expects a failure
  ([#1703](https://github.com/Community-Access/quill/issues/1703)). A person
  still needs to press it on a real machine.
- **Enter saves Settings** (2026-11-17). Settings had no default button, so
  after Find a setting took you to a setting, Enter did nothing. It now does
  what OK does. The nightly keyboard run of "Change a setting" found it, and
  also found that OK could offer to move your data folder when you had not
  touched it; that is fixed too.
- **QUILL run from source on a Mac no longer restarts in a loop** (2026-11-17),
  reported by Marco Zehe
  ([#1836](https://github.com/Community-Access/quill/issues/1836)).

The full detail of every change is in the
[CHANGELOG](https://github.com/Community-Access/quill/blob/main/CHANGELOG.md).

### In progress and open

- **The nightly keyboard run of "Write and save" fails some nights.** On the
  runner, Windows' own Save As dialog sometimes stays open after Enter and
  Alt+S. It does not happen every night and has not been seen on a real
  machine; it needs a look on one.
- **Recorded screen reader testing** still has no results; help is wanted in
  [#1694](https://github.com/Community-Access/quill/issues/1694).

### Known limitations

See [Known limitations](ACCESSIBILITY.md#known-limitations) in ACCESSIBILITY.md.

### How to help

As in October, below.

## October 2026

### Completed

- **We adopted the Open Source Accessibility Framework.** QUILL now has an
  [ACCESSIBILITY.md](ACCESSIBILITY.md) with priorities, contributor
  expectations, severity, response and resolution expectations, an owner, a
  dependency list and known limitations; an improved accessibility issue form
  with an email route; an accessibility checklist in the pull request
  templates; documented [core-task tests](accessibility-testing.md); and
  [resources other projects can reuse](accessibility-resources.md). 20 of
  the framework's 24 actions are done, as recorded in
  [our tracking issue](https://github.com/open-source-accessibility/Open-Source-Accessibility-Framework/issues/53).
- **Every accessibility report gets a response and an outcome** (from
  2026-10-29). The accessibility-reports workflow acknowledges every report,
  reminds the owner after 5 business days without a reply, reopens a report
  closed without a documented outcome (a merged fix or an `Outcome:` line),
  and invites the reporter to confirm a fix. Past reports are not reopened:
  earlier gaps such as #804 and #999, closed without a written outcome, are
  history that the rule now prevents. See "How we respond" in
  [ACCESSIBILITY.md](ACCESSIBILITY.md#how-we-respond).
- **Tables are real tables in rich text** (2026-10-26). A screen reader, Word
  and WordPad all read them as tables, and saved as RTF or Word the first row
  stays marked as the header row. Insert Table (`Ctrl+Alt+T`) asks whether the
  first row is a header, and in an HTML document marks header cells so a
  screen reader announces each cell's column. See the CHANGELOG entry
  "Tables, What's New and sliders: the latest work".
- **The arrow keys read a table cell by cell** (2026-10-26), in both QUILL and
  QUILL Lite: Up and Down move within a column and say the cell, and leaving
  the table says "Out of table".
- **What QUILL speaks also reaches a braille display** (2026-10-17). A new
  build gate, GATE-BRAILLE, fails any speech call that does not also write
  braille on the same path. See the CHANGELOG entry "GATE-BRAILLE: what QUILL
  speaks also reaches a braille display".
- **QUILL Lite's braille goes through QUILL's burst coalescer, and spoken AI
  answers are prepared for speech** (2026-10-16), so a burst of messages does
  not flood the braille display and Markdown symbols are not read aloud. See
  the CHANGELOG entry "Five small fixes: braille bursts, speech-safe answers,
  Markdown kept, fallbacks asked, the watchdog in QUILL Lite".

The full detail of every change is in the
[CHANGELOG](https://github.com/Community-Access/quill/blob/main/CHANGELOG.md).

### In progress and open

- **Recorded screen reader testing.** The sign-off records for QUILL Lite
  2.0.0, Quill Radio 3.2.0, QUILL Cast 2.0.0 and QUILL Transcribe 1.0.0 are
  pending, and the 316 checks in
  [screen-reader-checks-2026-10.md](qa/screen-reader-checks-2026-10.md) have no
  results yet. The QUILL Transcribe screen reader pass in Outlook, Word,
  Notepad and the browsers blocks its 1.0.0 release. Help is wanted in
  [#1694](https://github.com/Community-Access/quill/issues/1694).
- **Naming unlabelled controls** waits on an upstream change in wxWidgets
  reaching wxPython; tracked in
  [#1693](https://github.com/Community-Access/quill/issues/1693), with the
  workaround described there.
- **Heading structure in five documents**, a good first issue:
  [#1695](https://github.com/Community-Access/quill/issues/1695).
- There were no open issues with the `accessibility` label before these three
  were filed. 110 issues carry the label in total, all closed; the most recent
  was closed in August 2026.

### Known limitations

See [Known limitations](ACCESSIBILITY.md#known-limitations) in ACCESSIBILITY.md.

### Lessons learned

- Most of QUILL's accessibility work this autumn was recorded in the
  CHANGELOG but not labelled as accessibility issues, which makes it hard to
  find from the issue tracker. From now on, accessibility work that has an
  issue gets the `accessibility` label, and each update here links to it.

### How to help

Issues labelled
[accessibility](https://github.com/Community-Access/quill/issues?q=is%3Aopen+label%3Aaccessibility);
report a barrier with the
[accessibility issue form](https://github.com/Community-Access/quill/issues/new?template=accessibility.yml),
from inside any app with Help > Get Help from Support... (`Ctrl+Alt+F2`), or
by email to [support@community-access.org](mailto:support@community-access.org).
