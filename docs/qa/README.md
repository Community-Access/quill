# QA documents -- what to run, and when

Two kinds of document live here. **Sign-off checklists** are for a human at a
keyboard with a screen reader, ticking boxes: numbered steps, exact keys, exact
URLs, one line saying what decides pass or fail. **References** are the longer
documents behind them -- why a test exists, what a bake-off measured, what the
automated suites already cover.

Start with the checklist. Reach for the reference only when a step fails and
you want the background.

## Sign-off checklists

| Document | Covers | Full run | Short run |
| --- | --- | --- | --- |
| [radio-signoff.md](radio-signoff.md) | Quill Radio, all of it | about 90 min | 20 min (ten tests, named at the top) |
| [cast-signoff.md](cast-signoff.md) | QUILL Cast, all of it | about 2 hours | 20 min (ten tests, named at the top) |
| [dialogs.md](dialogs.md) | Every QUILL dialog: opens, keyboard, Escape, focus return | about 2 hours | one section at a time |
| [audio-studio-validation.md](audio-studio-validation.md) | Audio Studio: what only a human with a screen reader can confirm | about 45 min | -- |
| [macos-platform-validation.md](macos-platform-validation.md) | macOS-specific behaviour | about 90 min | -- |

Both app checklists end in a sign-off block: build, date, screen reader,
Windows version, blocks run, and a ship / ship-with-findings / do-not-ship
line. Fill it in and keep it with the release.

**Reporting a failure takes three things**: the test id (`R-57`, `C-71`), what
was said **word for word**, and what you expected to hear. A step that did
nothing at all is the most serious kind of failure -- report it even when
nothing looks broken.

## References

- [radio-3.0-test-plan.md](radio-3.0-test-plan.md) -- the long-form Radio plan:
  every verified URL, the described-audio investigation, the three bugs that
  probing found. `radio-signoff.md` is its fast run.
- [converter-bakeoff.md](converter-bakeoff.md) -- the Word conversion engine
  evidence (MarkItDown, Pandoc, python-docx, and why pydocx is retired).
- [ui-automation.md](ui-automation.md) -- the `tests/uia` pywinauto suite:
  what it covers mechanically, and why it never runs on a live screen-reader
  desktop.

## What the machine already checks

Do not spend a manual pass on these; they fail the build on their own.

```powershell
pytest -m smoke -q                      # fast core checks, seconds
pytest tests/accessibility/ -q          # announcements, SR detection, grammar
python -m quill.tools.platform_report   # every gate, as one scorecard
```

The authoritative dialog inventory is generated, not hand-kept:
`python -m quill.tools.dialog_inventory --write`.

## Release-day plans elsewhere

`docs/release/` holds the release-day documents: `qa-core-journeys.md`,
`screen-reader-test-plan.md`, the fresh-install and upgrade-path regressions,
and the acceptance book in `docs/release/acceptance/`.
