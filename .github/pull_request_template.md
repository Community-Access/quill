## Summary

Describe what changed and why.

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Accessibility improvement
- [ ] Documentation update
- [ ] Refactor

## Validation

- [ ] `ruff check .`
- [ ] `pytest -q`
- [ ] Docs artifacts regenerated (if applicable)

## Accessibility checklist

Accessibility is the reason QUILL exists. Please read the
[contributor expectations in ACCESSIBILITY.md](https://github.com/Community-Access/quill/blob/main/docs/ACCESSIBILITY.md#contributor-expectations)
and check each item that applies to your change. Write N/A beside an item that
does not apply (for example, the interface group for a documentation-only
change).

### Checks

- [ ] `pytest tests/accessibility -q` passes
- [ ] `python -m quill.tools.platform_report` passes (access keys, menu keys, F1 help, announcement and braille gates)

### Interface changes (any window, dialog, menu, control or announcement)

- [ ] Keyboard only: everything is reachable and operable, focus is visible and follows a logical order, there is no keyboard trap, and Escape closes a dialog with focus returned to where it was
- [ ] Every new control has a real visible label created immediately before it; a button that acts on something says what in its label
- [ ] No two controls in a window share an access key, and every enabled menu item shows its key
- [ ] Announcements say only what the screen reader cannot already know, and go through the announcement service so they reach braille too
- [ ] Every new control has F1 help written with `SetHelpText` where it is built
- [ ] Modal dialogs go through `_show_modal_dialog`; Close and Cancel buttons are bound with `bind_close_button`
- [ ] High contrast themes and system colours still work, and colour is not the only way anything is shown
- [ ] Screen reader spot check done (say which screen reader and version below: NVDA, JAWS, Narrator, or VoiceOver for macOS)

### Documentation changes (Markdown, help text, release notes, the website)

- [ ] One H1 per page, and headings do not skip levels
- [ ] Link text is unique and descriptive (no "click here" or "read more")
- [ ] Images have meaningful alternative text or are marked decorative; diagrams have a text description nearby
- [ ] Tables have a header row and a sentence before them saying what they hold
- [ ] Code and commands are text in fenced blocks, never pictures
- [ ] Meaning is not carried by colour, position or styling alone
- [ ] Check boxes are "checked", never "ticked"; plain language, with abbreviations spelled out on first use
- [ ] Keys and menu paths the text teaches are the ones the app binds

### Dependencies

- [ ] A new dependency that users meet has a short accessibility review below, and is added to "Dependencies and upstream blockers" in `docs/ACCESSIBILITY.md`

### Accessibility notes

<!-- What you tested, with what (for example NVDA 2026.3 on Windows 11), what you could not test, and any follow-up issues. -->

## Risks / follow-ups

List any known risks, edge cases, or follow-up work.
