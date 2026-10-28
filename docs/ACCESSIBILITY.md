# Accessibility in QUILL

QUILL for All exists because its maintainer is blind, uses a screen reader
every day, and wanted a writing studio built around the keyboard and the ear
from the first line. Accessibility is not a feature of QUILL; it is the reason
the project exists. Everyone, including people who use a screen reader, a
braille display, magnification, high contrast, voice control, a switch or the
keyboard alone, should be able to install QUILL and its companion apps, use
them for real work, read their documentation and contribute to them.

This document covers QUILL and the QuillVille family built from this
repository (QUILL, QUILL Lite, Quill Radio, QUILL Cast, QUILL Transcribe and
the other companion apps), their installers, their documentation and the
website at [quillforall.org](https://quillforall.org/). It describes our
accessibility priorities, what we ask of contributors, how to report a barrier,
how we respond, who owns this work, what we support and test, and what we know
is not yet good enough.

We follow GitHub's
[Open Source Accessibility Framework](https://open-source-accessibility.github.io/Open-Source-Accessibility-Framework/),
an improvement framework, not a certification. Participating in it is not a
claim that QUILL is fully accessible. Our progress is in
[the framework section](#open-source-accessibility-framework) below.

## Priorities

- **Screen reader first.** Every task in every app is designed to work with
  NVDA, JAWS and Narrator on Windows, and with VoiceOver on macOS. QUILL
  speaks only what the screen reader cannot already know (a background result,
  a state change, the outcome of an action), and never repeats a window title,
  a control name or a focus move the reader announces itself.
- **What is spoken is also brailled.** A message that only reaches speech does
  not exist for a deafblind user or anyone reading with speech off, so
  announcements go through the announcement service, which writes braille on
  the same path, and the build fails a speech call that skips braille unless
  it has a recorded reason.
- **Keyboard for everything.** Every command has a key or a written reason why
  not; every enabled menu item shows its key; no two controls in one window
  share an access key; dialogs answer Enter and Escape and give focus back to
  where it was.
- **Names that match what you see.** Our rule is that every control has a real
  label, created immediately before it, because that label is the name Windows screen readers
  speak. Buttons that act on something say what in their visible label.
- **Help where you are.** F1 answers in every window of every app, with the
  window's purpose and then the focused control's own help.
- **Low vision.** The editor follows the colours Windows uses, including high
  contrast themes, offers dark mode, reports its own contrast ratio on request,
  and changes text size with `Ctrl+=`, `Ctrl+-` and `Ctrl+0`.
- **Documentation that works with assistive technology.** Real headings and
  lists, descriptive link text, alternative text for every image, tables with
  header rows, and HTML pages with a language, a skip link and a main landmark.
- **Target.** For the website and the HTML documentation we work toward
  [WCAG 2.2](https://www.w3.org/TR/WCAG22/) Level AA. For the desktop apps we
  apply the same principles through the Windows and macOS accessibility APIs.
  This is a goal that guides our work, not a claim of verified conformance.

## Contributor expectations

These apply to every pull request. [CONTRIBUTING.md](CONTRIBUTING.md) explains
how to set up and run the checks, and the pull request template carries the
same list as a checklist.

### Checks the build runs

Most of QUILL's accessibility rules are enforced in code, so a pull request
that breaks one fails its checks. They run in continuous integration on every
pull request, and `python -m quill.tools.platform_report` runs them all locally
as one scorecard.

- **Accessibility CI** (`.github/workflows/accessibility-ci.yml`) runs
  `tests/accessibility` (announcement grammar, screen reader detection), the
  Windows platform bridge tests and the dialog keyboard contract tests.
- **GATE-13**: an announcement that repeats what the screen reader already says
  (a focus move, a window title) fails the build.
- **GATE-BRAILLE**: a speech call that does not also write braille fails unless
  it is classified with a reason.
- **GATE-14**: two controls in one window with the same access key fail.
- **Menu accelerators**: every enabled menu item must show a working key, and
  no key may be claimed twice in one menu bar.
- **F1 help**: every window and control must have authored help, written
  inline where the control is built.
- **Dialogs**: every modal dialog goes through the shared helper that applies
  the keyboard contract; a Close or Cancel button must be bound so it works in
  a modeless window too.
- **Accessible names** and **surface reachability**: controls must carry names,
  and every window must be reachable from an app entry point.
- **Documentation**: GATE-DOCA11Y keeps rendered pages' tables in the
  accessibility tree and their skip link working; the documentation chord and
  menu gates fail a guide that teaches a key or a menu that does not exist.

### Interface requirements

For any change to a window, dialog, menu or control:

- Do a keyboard-only pass: everything can be reached with Tab, Shift+Tab, the
  arrow keys and access keys; everything can be operated; focus is visible and
  follows a logical order; there is no keyboard trap; Escape closes a dialog
  and focus returns to where it was.
- Give every control a real visible label, created immediately before the
  control, and put the object of an action in a button's label.
- Announce only what the screen reader does not already say, through the
  announcement service, so it reaches braille too.
- Keep system colours and high contrast themes working; never convey meaning
  by colour alone.
- Write F1 help for every new control with `SetHelpText` where it is built.
- Do a screen reader spot check with NVDA, JAWS or Narrator (VoiceOver for
  macOS work), and say in the pull request which reader and version you used.
  The procedures are in [accessibility-testing.md](accessibility-testing.md).

### Documentation and content

- Use one H1 per page, a logical heading hierarchy and real lists.
- Write unique, descriptive link text; never "click here" or "read more".
- Give every image meaningful alternative text, or mark it decorative, and add
  a text description near any diagram.
- Give every table a header row and a sentence before it saying what it holds.
- Put code and commands in fenced blocks, as text, never as pictures.
- Do not convey meaning by colour, position or styling alone.
- Use plain language, and spell out an abbreviation the first time.
- Say "check" and "checked" for check boxes, as screen readers do.
- Regenerate the `.html` and `.epub` beside any Markdown file you change under
  `docs/`.

### Dependencies

A new dependency that users meet (a UI toolkit, a control, a speech or braille
library, a web view, a document converter) needs a short accessibility review
before it is adopted: how it exposes names, roles and states to the Windows and
macOS accessibility APIs, its known accessibility issues upstream, and how
QUILL will work around them. Write the review in the pull request and add the
dependency to [Dependencies and upstream blockers](#dependencies-and-upstream-blockers).

## Reporting accessibility issues

If something in QUILL, its installers, its documentation or the website is
hard or impossible for you to use, please tell us. Accessibility reports are
expertise, not complaints, and partial reports are welcome.

- **Inside any QuillVille app:** Help > Get Help from Support... (`Ctrl+Alt+F2`)
  asks a few questions, then opens your own mail program with the message to
  support@community-access.org already written. Nothing is sent until you
  press Send there, and you do not need a GitHub account.
- **On GitHub:** open an issue with the
  [accessibility issue form](https://github.com/Community-Access/quill/issues/new?template=accessibility.yml).
- **By email, if GitHub is a barrier for you or you would rather not post in
  public:** write to [support@community-access.org](mailto:support@community-access.org),
  or to the accessibility owner at [jeff@jeffbishop.com](mailto:jeff@jeffbishop.com).
  We will file the issue for you if you want one, and keep your details private
  if you ask.

Helpful details, all optional:

- What you were trying to do, and what happened instead.
- Which app and window, and the steps or keys that lead there.
- What your screen reader said, word for word, if you use one, and what you
  expected to hear.
- The app version (Help > About), your Windows or macOS version, and your
  assistive technology and its version, including any braille display.
- How much it gets in your way (see [Severity](#severity)).

You never need to tell us about a disability or diagnosis. Please never include
document text, passwords or keys in a report.

### Severity

Severity describes how strongly a barrier affects your ability to complete a
task. Reporters do not need to choose one; we assign or confirm it in triage.

- **Critical:** you cannot complete a core task, such as installing an app,
  opening, writing or saving a document, or reaching a command at all.
- **Serious:** you can complete the task only with real difficulty or a
  workaround.
- **Moderate:** the task works but is confusing, slow or inconsistent, such as
  speech that is repeated, missing or out of order.
- **Minor:** a small problem with little effect on getting things done.

### How we respond

- We acknowledge every accessibility report within **5 business days**, the
  same target [MAINTAINERS.md](MAINTAINERS.md) sets for every new issue,
  respectfully, and say what happens next.
- We do not ask you to justify your experience or disclose personal
  information. If we need more detail, we ask specific questions about the
  steps and your setup, never whether the barrier is real.
- We label the issue `accessibility`, give it a severity, and say who is
  working on it. Accessibility issues are exempt from the stale bot, so they are
  never closed for inactivity.
- Where we can, we offer a workaround while a fix is in progress, and add the
  barrier to [Known limitations](#known-limitations) if it affects others.
- We post an update on the issue whenever its status or expected timing
  changes, and link the pull request or commit that fixes it.
- Before closing, we write down the outcome: what changed, in which version,
  or why it cannot be fixed yet and what to do instead. When a fix lands we
  invite you, or another person affected, to confirm it works.
- We thank you for the report, and credit you in the release notes only if you
  agree (see [Recognition](#recognition)).

### Resolution expectations

After triage each accessibility issue has a severity, an owner and a status.

- **Critical** barriers are labelled `p0`, which this project defines as a
  release blocker: a release does not ship with a known critical barrier
  unless a workaround is published in [Known limitations](#known-limitations).
- **Serious** barriers are labelled `p1` and are scheduled ahead of feature
  work.
- **Moderate** and **minor** barriers are scheduled with other work, and are
  often good first issues.

If we cannot fix something soon, we say why on the issue, share any
workaround, and keep it open and visible.

## Taking part

Everything in this project can be done asynchronously and in text. There are
no required meetings, calls, cameras or spoken participation.

- **Asynchronous:** issues and pull requests on GitHub,
  [GitHub Discussions](https://github.com/Community-Access/quill/discussions)
  for questions and ideas, the Community Access
  [support hub](https://github.com/Community-Access/support), and email to the
  addresses above.
- **Synchronous:** none is required. If we hold a call or a live event, the
  agenda and materials are posted in advance, notes are posted afterwards in
  text, and everything decided there is written on the issue it concerns.
- **Work that is not code is welcome:** testing with assistive technology,
  reproducing reports, reviewing documentation, translating, and writing
  sign-off records.
- **Accommodations:** if a tool or process we use is a barrier for you, or you
  need an accommodation to contribute, email
  [jeff@jeffbishop.com](mailto:jeff@jeffbishop.com) or
  [support@community-access.org](mailto:support@community-access.org)
  privately. You do not need to explain why.

Everyone who takes part follows the [Code of Conduct](CODE_OF_CONDUCT.md),
which treats dismissing someone's accessibility report, mocking how a person
uses a computer, or sharing someone's disability or assistive technology
without permission as violations.

### How to help

- [Accessibility issues for a first contribution](https://github.com/Community-Access/quill/issues?q=is%3Aopen+label%3Aaccessibility+label%3A%22good+first+issue%22)
  (labelled `accessibility` and `good first issue`).
- [Accessibility issues where we need experienced help](https://github.com/Community-Access/quill/issues?q=is%3Aopen+label%3Aaccessibility+label%3A%22help+wanted%22)
  (labelled `accessibility` and `help wanted`), each saying what experience
  would help.
- [All open accessibility issues](https://github.com/Community-Access/quill/issues?q=is%3Aopen+label%3Aaccessibility).
- Each month an **Accessibility feedback and progress** issue is opened
  automatically (`.github/workflows/accessibility-review.yml`). Comment there
  to tell us what works and what does not; it is our standing feedback loop.

Questions go to GitHub Discussions or to the accessibility owner; the owner
answers them or finds someone who can.

### Collaboration tools we have reviewed

The tools this project asks people to use, and what we know about each. This
is a desk review, made on 2026-10-28, against each tool's own accessibility
documentation and how the tool is used in this project; it is not a test with
assistive technology. If one of them is a barrier for you, the alternative is
always email.

- **GitHub issues, pull requests and Discussions:** usable with a keyboard and
  screen reader; GitHub documents its accessibility at
  [accessibility.github.com](https://accessibility.github.com/documentation).
  Issue forms are standard form fields. Alternative: email, and we file it.
- **Help > Get Help from Support in the apps:** a QUILL dialog, covered by the
  same keyboard, F1 and naming gates as every other window. It hands the
  message to your own mail program, so the last step is as accessible as the
  mail program you already use.
- **Email:** works with any mail program and screen reader.
- **The website and documentation:** static HTML with a language, a skip link
  and a main landmark on every rendered page, plus EPUB copies of every
  document for reading in a book reader.

## Recognition

We credit accessibility contributions, including testing, reports, reviews and
documentation, in release notes and in the contributors list in
[CONTRIBUTING.md](CONTRIBUTING.md), but only with the contributor's consent and
in the form they choose: a name, a GitHub handle, or no credit at all. We
describe the work, never the person: we do not mention anyone's disability,
diagnosis or assistive technology unless they ask us to. The release checklist
in [release/RELEASE.md](release/RELEASE.md) includes this step.

## Ownership and maintenance

Accessibility is owned by **Jeff Bishop**, project maintainer
([@accesswatch](https://github.com/accesswatch) on GitHub,
[jeff@jeffbishop.com](mailto:jeff@jeffbishop.com)).

The accessibility owner:

- triages accessibility reports, assigns severity and keeps them labelled;
- marks suitable issues `good first issue` or `help wanted`, with scope,
  context and acceptance criteria;
- reviews pull requests that touch the interface against the contributor
  expectations above (changes under `quill/ui/` and `tests/accessibility/` are
  routed to the owner for review through
  [CODEOWNERS](https://github.com/Community-Access/quill/blob/main/.github/CODEOWNERS));
- reviews the accessibility of new dependencies before they are adopted;
- keeps this document, the known limitations, the testing records and the
  framework progress current, reviewing them with each monthly feedback and
  progress issue and at each release;
- escalates unresolved accessibility risks to the other maintainers in
  [MAINTAINERS.md](MAINTAINERS.md).

If ownership changes, this section is updated in the same pull request that
changes CODEOWNERS and MAINTAINERS.md.

## Dependencies and upstream blockers

The third-party components that shape what users meet, what each affects, and
what we know about its accessibility. Revisit this list whenever one of them is
added, upgraded or replaced.

- **wxPython 4.3.1** (wxWidgets): every window and control. On Windows it uses
  native Win32 controls, so names, roles and states reach screen readers
  through Microsoft Active Accessibility and UI Automation; a control's name is
  the label created before it. Upstream blocker: a name set in code is not
  read, and a picture-only button has no name, until wxPython exposes
  `SetAccessibleName` (wxWidgets
  [PR #27056](https://github.com/wxWidgets/wxWidgets/pull/27056) and
  [PR #27051](https://github.com/wxWidgets/wxWidgets/pull/27051), both merged
  in September 2026). Tracked in
  [#1693](https://github.com/Community-Access/quill/issues/1693). Mitigation:
  every control gets a real label created before it, and buttons carry their
  object in the visible label. On macOS, VoiceOver ignores wx window names, so
  `quill/ui/accessible_names.py` sets native accessibility labels
  ([#1012](https://github.com/Community-Access/quill/issues/1012)).
- **Prism** (the `prismatoid` package): routes announcements to NVDA, JAWS and
  other screen readers, with speech and braille. Fallbacks: accessible_output2,
  Narrator's UI Automation notifications, VoiceOver, and the system voice.
- **accessible_output2**: the fallback speech and braille output when Prism
  cannot reach the running screen reader.
- **liblouis**: braille translation and back-translation for the optional
  QUILL Braille Pack. Nemeth and UEB mathematics braille are not available yet.
- **Microsoft Edge WebView2** (through `wx.html2`): the AI chat and HTML
  previews, presented as accessible web pages.
- **Pandoc**: renders the documentation to HTML and EPUB through
  `docs/pandoc/quill-accessible.html5`, which adds the language, skip link and
  main landmark that Pandoc's default template lacks, and keeps tables in the
  accessibility tree.
- **pywinauto**: test-only; drives the UI Automation regression suite in
  `tests/uia`. It never runs on a live screen reader desktop.

## Supported environments

What we support, and what has been evaluated:

- **Operating systems:** Windows 10 and Windows 11 (64-bit), which every
  installer requires. macOS builds exist and are under validation
  ([macos-platform-validation.md](qa/macos-platform-validation.md)); treat
  them as less tested than Windows.
- **Screen readers:** NVDA, JAWS and Narrator on Windows; VoiceOver on macOS.
  QUILL's maintainer writes and uses QUILL with a screen reader every day.
  The user guide describes the stable release channel as checked with JAWS and
  NVDA; those checks are not yet recorded per release (see
  [Known limitations](#known-limitations)).
- **Braille:** braille displays through NVDA and JAWS, and Narrator for the
  notifications QUILL sends; QUILL's own Braille mode and Braille Pack for
  braille files.
- **Input:** keyboard, with every command reachable from it. Dictation is built
  in (QUILL Transcribe dictates into other programs). Pointer input works but
  is not the design focus; touch, switch access and voice control software
  have not been specifically tested.
- **Low vision:** Windows high contrast themes and system colours, dark mode,
  an on-request contrast ratio report, and editor text size from 6 to 72
  points. Windows Magnifier and display scaling have not been specifically
  tested.
- **Documentation:** HTML pages in current browsers, and EPUB copies of every
  document.

What is checked automatically on every pull request is listed under
[Checks the build runs](#checks-the-build-runs). The manual procedures, and
the record of which were run in which environment, are in
[accessibility-testing.md](accessibility-testing.md).

## Known limitations

These are the barriers we know about. Please report any we have missed.

- **Manual screen reader testing is not yet recorded per release.** Detailed
  checklists exist (`docs/qa/`), but the sign-off records for QUILL Lite 1.2.0,
  Quill Radio 3.2.0, QUILL Cast 2.0.0 and QUILL Transcribe 1.0.0 are still
  pending, and 316 checks for work from September and October 2026 are listed
  in [screen-reader-checks-2026-10.md](qa/screen-reader-checks-2026-10.md)
  without results. Until they are recorded, treat a combination of app, screen
  reader and version that is not in a record as untested. Help is wanted in
  [#1694](https://github.com/Community-Access/quill/issues/1694).
- **A control without a visible label can be announced without a name** on
  Windows, because the toolkit does not yet let QUILL set one (see
  [#1693](https://github.com/Community-Access/quill/issues/1693)). Our rule is
  that every control has a label; if you find one that does not, please report
  it.
- **The screen reader does not say a paragraph is a heading** by itself in the
  editor, because no Windows edit control exposes paragraph styles. QUILL says
  it for you instead ("Heading 2, Installing") when you arrive on one.
- **Mathematics in braille:** Nemeth and UEB maths braille are not available
  yet. With JAWS, its Math Viewer works once an equation is exported as a
  native Word equation.
- **macOS** is newer than Windows and less tested; its validation checklist is
  still being worked through.
- **Settings search** is not yet available in Quill Converter, the Media Player
  and Inkwell, and it does not search inside dialogs that are not open.
- **Some documents have heading structure** that is harder to navigate than it
  should be (a second top-level heading, or a skipped level). Tracked in
  [#1695](https://github.com/Community-Access/quill/issues/1695).

## Progress updates

We publish accessibility progress in
[accessibility-progress.md](accessibility-progress.md), newest first: what was
completed, what is still open, the known limitations and links to the work.
A scheduled workflow opens an **Accessibility feedback and progress** issue on
the first of each month, with the checklist for writing the next update, and
each release's notes link to the latest one.

Resources from this work that other projects can reuse, such as our issue
form, pull request checklist, test procedures and accessibility gates, are
described in [accessibility-resources.md](accessibility-resources.md).

## Open Source Accessibility Framework

We follow the
[Open Source Accessibility Framework](https://open-source-accessibility.github.io/Open-Source-Accessibility-Framework/)
in its four phases. Progress is self-reported, action by action, against each
action's definition of done, and it is not a certification. The public
tracking issue in the framework's repository will be linked here once it is
open. As of October 2026:

- **Foundational:** this document, and the `accessibility` label, which the
  issue form applies to every report.
- **Workflow:** priorities and contributor expectations above, referenced from
  [CONTRIBUTING.md](CONTRIBUTING.md); the accessibility issue form with
  in-app and email alternatives; severity, response and resolution
  expectations; an accessibility checklist in the pull request templates;
  beginner-friendly and expert-help accessibility issues; an owner;
  documentation checked by the documentation gates; interface requirements
  enforced by the build and by review; and the dependency list above, with its
  upstream blocker tracked.
- **Testing:** automated accessibility checks on every pull request; a review
  of representative documentation; supported environments and known
  limitations above. Documented keyboard, screen reader and manual checks for
  the core tasks are in [accessibility-testing.md](accessibility-testing.md),
  but have not yet been run and recorded, so those three actions are not yet
  complete.
- **Community:** ways to take part and a private route for accommodations; a
  Code of Conduct; a monthly feedback and progress issue; published progress
  updates; shared resources. Crediting contributions publicly waits on
  contributors' consent, and responding to reports under the guidance above is
  ongoing practice.

## Feedback

To suggest an improvement to this document or to how we work, open an issue or
a pull request, comment on the monthly feedback issue, or write to either
address above. Thank you for helping make QUILL usable by everyone.
