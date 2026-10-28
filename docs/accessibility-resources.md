# Accessibility Resources Other Projects Can Reuse

QUILL is built by and for screen reader users, and much of how it stays
accessible is written down as files and tests that other projects can copy.
This page lists them: what problem each solves, what you need to use it, where
it does not apply, and where to find it. Everything here is under QUILL's MIT
license unless the file says otherwise. Our own accessibility commitments are
in [ACCESSIBILITY.md](ACCESSIBILITY.md).

**Maintained by** the accessibility owner named in
[ACCESSIBILITY.md](ACCESSIBILITY.md#ownership-and-maintenance), currently Jeff
Bishop ([@accesswatch](https://github.com/accesswatch)). These resources are
reviewed with each monthly accessibility feedback and progress issue, and
whenever the file they describe changes. Report a problem with one through the
[accessibility issue form](https://github.com/Community-Access/quill/issues/new?template=accessibility.yml).

## Project process

### Accessibility issue form

- **Where:** [.github/ISSUE_TEMPLATE/accessibility.yml](https://github.com/Community-Access/quill/blob/main/.github/ISSUE_TEMPLATE/accessibility.yml)
- **Solves:** reports that arrive without the steps, the screen reader and its
  version, or what was heard, so they cannot be reproduced.
- **How it works:** only the description is required; it asks for what the
  screen reader said word for word, offers an email route for people who
  cannot or will not use GitHub, never asks about disability, and applies the
  `accessibility` label.
- **Needs:** GitHub issue forms. Change the app list and the contact address.
- **Does not fit:** projects without a desktop app may want browser fields
  instead of the app list.

### Pull request accessibility checklist

- **Where:** [.github/pull_request_template.md](https://github.com/Community-Access/quill/blob/main/.github/pull_request_template.md)
- **Solves:** accessibility review that depends on the reviewer remembering
  to ask.
- **How it works:** separate groups for documentation changes and interface
  changes, each item checkable or marked N/A, and a notes field for which
  screen reader and version the contributor tested with.
- **Needs:** nothing beyond GitHub. The interface items are specific to a
  wxPython desktop app; replace them with your toolkit's equivalents.

### ACCESSIBILITY.md

- **Where:** [ACCESSIBILITY.md](ACCESSIBILITY.md)
- **Solves:** having nowhere public to say what a project commits to, how to
  report a barrier and what happens next.
- **How it works:** follows the section order of the Open Source
  Accessibility Framework: priorities, contributor expectations, reporting
  and severity, response, ownership, dependencies, supported environments and
  known limitations.
- **Does not fit:** it is not a conformance statement and makes no WCAG
  conformance claim.

### Monthly accessibility feedback and progress issue

- **Where:** [.github/workflows/accessibility-review.yml](https://github.com/Community-Access/quill/blob/main/.github/workflows/accessibility-review.yml)
- **Solves:** progress updates and reviews of known limitations that are meant
  to recur and quietly stop.
- **How it works:** on the first of each month a scheduled workflow opens one
  public issue with the review checklist and an invitation to give feedback,
  and closes the previous month's issue.
- **Needs:** GitHub Actions with `issues: write`, and an `accessibility` label.
- **Limits:** it creates the reminder, not the update. A person still writes
  the progress entry.

## Testing

### Core-task test procedures and record

- **Where:** [accessibility-testing.md](accessibility-testing.md), with the
  deeper plans in [release/qa-core-journeys.md](release/qa-core-journeys.md)
  and [release/screen-reader-test-plan.md](release/screen-reader-test-plan.md)
- **Solves:** manual testing that is never written down, so nobody knows what
  was tested with which screen reader.
- **How it works:** keyboard-only, screen reader, manual and documentation
  check lists for six core tasks of a desktop writing app, and a record
  template that captures the date, build, Windows version, screen reader and
  version, and what was heard.
- **Limits:** written for Windows screen readers (NVDA, JAWS, Narrator) and a
  desktop app. Web projects should add landmarks and reflow checks.

### Screen reader sign-off sheets

- **Where:** [qa/README.md](qa/README.md) and the sheets it lists
- **Solves:** release testing that has no clear pass or fail.
- **How it works:** numbered steps with exact keys and the speech to expect,
  a short run and a full run, and a sign-off block (build, date, screen reader,
  Windows version, ship or do not ship).
- **Lesson learned:** writing the expected speech down word for word is what
  makes a failure reportable; "it sounded wrong" is not.

## Gates that enforce accessibility in code

These are Python tests and tools for a wxPython app, but each idea carries to
any desktop toolkit. Each runs in continuous integration and fails the build.

### Do not announce what the screen reader already says (GATE-13)

- **Where:** [quill/tools/check_over_announce.py](https://github.com/Community-Access/quill/blob/main/quill/tools/check_over_announce.py)
- **Solves:** "chatty" apps. Over-announcing is rarely reported as a bug;
  people just learn to dislike the app.
- **How it works:** flags an announcement inside a focus handler, and an
  announcement of a window title.
- **Lesson learned:** a verbosity setting is not the fix; saying less is.

### Speech also reaches braille (GATE-BRAILLE)

- **Where:** [quill/tools/braille_parity_audit.py](https://github.com/Community-Access/quill/blob/main/quill/tools/braille_parity_audit.py)
- **Solves:** messages that are only spoken, which do not exist for a
  deafblind user or anyone reading with speech off.
- **How it works:** walks the code for every speech call and fails unless
  braille is written on the same path, or the call is classified with a reason.

### Unique access keys per window (GATE-14)

- **Where:** [quill/tools/check_access_keys.py](https://github.com/Community-Access/quill/blob/main/quill/tools/check_access_keys.py)
- **Solves:** two controls sharing an `&` mnemonic, where Windows cycles
  between them and one silently cannot be reached. The first sweep found 128
  collisions across 76 windows.
- **Lesson learned:** OK, Cancel and Close need no access key at all; Enter
  and Escape already serve them, and the letters they free resolve collisions
  elsewhere.

### Every menu item shows its key

- **Where:** [tests/unit/ui/test_menu_accelerators.py](https://github.com/Community-Access/quill/blob/main/tests/unit/ui/test_menu_accelerators.py)
- **Solves:** walking a menu to discover a command has no shortcut, and two
  items claiming one key so that one never fires.

### Rendered documentation keeps its tables and skip link (GATE-DOCA11Y)

- **Where:** [tests/unit/docs/test_generated_doc_a11y.py](https://github.com/Community-Access/quill/blob/main/tests/unit/docs/test_generated_doc_a11y.py)
  and the Pandoc template [pandoc/quill-accessible.html5](https://github.com/Community-Access/quill/blob/main/docs/pandoc/quill-accessible.html5)
- **Solves:** Pandoc's default styles give tables a block display, which
  removes tables from the accessibility tree, and its default template has no
  language, skip link or main landmark.
- **Needs:** Pandoc 3.10 or newer. Useful to any project that publishes
  documentation with Pandoc.

### Every internal link on the site resolves (GATE-SITE-LINKS)

- **Where:** [tests/unit/docs/test_site_links.py](https://github.com/Community-Access/quill/blob/main/tests/unit/docs/test_site_links.py)
- **Solves:** broken links and podcast episodes without transcripts on a
  static site, found by nobody because nothing checked.

## Related resources

- [Open Source Accessibility Framework](https://open-source-accessibility.github.io/Open-Source-Accessibility-Framework/),
  which this project follows.
- [Accessibility Toolkit](https://github.com/open-source-accessibility/accessibility-toolkit),
  the framework's reference examples.
- [GitHub accessibility documentation](https://accessibility.github.com/documentation).
- [Community Access](https://community-access.org/), which makes QUILL, and its
  [GIT Going with GitHub](https://community-access.org/git-going-with-github/)
  course for screen reader users.
