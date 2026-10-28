# Accessibility Progress Updates

What has changed in QUILL's accessibility, what is still open, and what we
know is not yet good enough. The newest update is first. Our commitments are
in [ACCESSIBILITY.md](ACCESSIBILITY.md).

A new update is written each month, prompted by the **Accessibility feedback
and progress** issue that `.github/workflows/accessibility-review.yml` opens on
the first of the month, and each release's notes link to the latest one. Counts
are counts of work, not a score: no number here says how accessible QUILL is.

## October 2026

### Completed

- **We adopted the Open Source Accessibility Framework.** QUILL now has an
  [ACCESSIBILITY.md](ACCESSIBILITY.md) with priorities, contributor
  expectations, severity, response and resolution expectations, an owner, a
  dependency list and known limitations; an improved accessibility issue form
  with an email route; an accessibility checklist in the pull request
  templates; documented [core-task tests](accessibility-testing.md); and
  [resources other projects can reuse](accessibility-resources.md).
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
  1.2.0, Quill Radio 3.2.0, QUILL Cast 2.0.0 and QUILL Transcribe 1.0.0 are
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
