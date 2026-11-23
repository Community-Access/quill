# Family interaction contracts

Every family feature (each FUX proposal and family journey from the family UX plan) is held to this checklist before its pull request merges. It comes from section 8 of the family UX plan, "meaningful delight without more clutter" (2026-11-10; read it with `git show b7c6a1a04^:complete2.md`), with the decisions in [2026-11-19-family-ux-pilots.md](2026-11-19-family-ux-pilots.md).

Where a gate already checks an item, the gate is named; those items need no extra proof in the pull request. For each other item, the pull request says how it was met, or writes N/A with a reason.

## Keyboard, focus and speech

- [ ] Tab order is stable, focus is visible, and every control has an accessible name and, where it helps, a description. (Access keys: GATE-14.)
- [ ] Type-ahead and text editing keep their established meaning.
- [ ] Focus returns to the control that opened a dialog. (`_show_modal_dialog`, the dialog inventory gate.)
- [ ] Background updates never take focus or interrupt reading. (FUX-06; GATE-13.)
- [ ] Speech says only outcomes the screen reader does not already say, once; the full detail stays reachable. (GATE-13, GATE-12.)
- [ ] The person's sound, speech, both or silent choice and the error policies are respected.
- [ ] Every essential state is available as text and through braille; sound and colour only add to it.
- [ ] A new key is chosen only after checking the app's and the family's existing keys, their aliases, and screen-reader keys. (`test_menu_accelerators.py`, the family menu chord snapshot.)
- [ ] Keyboard only, screen reader, braille, magnification and high contrast are each a normal way through the task.
- [ ] Help, exported HTML and the website stay at WCAG 2.2 AA; native behaviour is also checked by hand.

## Identity, changes and confidence

- [ ] The result names the object, the account or destination, and what actually happened. (FUX-04.)
- [ ] A local draft, a prepared change, work in progress, a saved file and something published are told apart.
- [ ] Confirmations appear only where the consequence matters; routine, safe actions are not slowed by warnings.
- [ ] An unavailable action says why, following the app's own rules for greyed or hidden items.
- [ ] Stored choices and current release gates are respected.
- [ ] Originals and drafts are kept, and what recovery can and cannot do is stated honestly.
- [ ] Local defaults stay local unless the person chooses the narrow, supported way to share them. (`family_preferences.py`.)

## Performance and durability

- [ ] Controls respond at once; long work can be cancelled and says, in text, that it is still working.
- [ ] Large lists, histories and caches are bounded without silently losing meaningful work.
- [ ] Media and documents are kept apart from caches and configuration.
- [ ] Shared data is versioned and kept intact, including fields a newer sibling app added. (GATE-DATAFMT.)
- [ ] No new telemetry service.
- [ ] Behaviour in real receiving apps or in a frozen build is not assumed from unit tests alone; the pull request lists what still needs a live check.

## Where shared behaviour stops

These rules are already decided (section 4 of the pilot decisions), and a feature must not cross them:

- [ ] Each app owns its own audio. Nothing pauses, ducks or reroutes another app's sound unless the person chooses it.
- [ ] Keys, focus behaviour, accounts and billing are never synchronised between apps.
- [ ] Text goes only to the target that was current when the input began; otherwise it is kept and offered as Insert or Copy. (FUX-07.)

## What a feature must not add

From section 9 of the plan:

- [ ] No required dashboard, home app or launcher, and no second notification, history or task centre.
- [ ] No menus that rearrange themselves, no renamed familiar controls, and no default actions that keep changing.
- [ ] No new panel or button where a menu, a context action, the status bar or help would do.
- [ ] No required account or cloud sync for local work, and no "smart" default that silently changes where audio, text, publishing or billing goes.
- [ ] No streaks, badges, engagement reminders, decorative sound or welcome messages.
