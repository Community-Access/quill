# Family UX: the decisions on the pilots

**Date:** 2026-11-19
**Decided by:** Claude, at Jeff's request ("make good choices"), closing complete.md 3.2.
**Source:** the family UX plan "meaningful delight without more clutter" (2026-11-10). It was `complete2.md` and merged into `complete.md` on 2026-11-18. Its FUX ids, journeys and section 12 are cited here and can be read in git history (`git show b7c6a1a04^:complete2.md`).

The plan asked five questions and blocked nothing. Here are the answers, with reasons, so the work can start without another round of asking.

## 1. The two pilots: Quill Cast and QUILL Lite

| Pilot | Who is observed | The tasks |
| --- | --- | --- |
| **Quill Cast** | Jeff's testers who already report on Cast (Chris among them), using the installed build | Resume an episode stopped yesterday. Browse new arrivals while an episode plays. Change a podcast's speed and hear it take effect. |
| **QUILL Lite** | The same testers, plus one person new to the family | Reopen a long document and get back to the sentence you left. Recover a draft after closing without saving. Find and use one command without the manual. |

**Why these two:** both are released and packaged, both are used every day, and both have reported problems that are exactly what the plan is about. Chris's speed report on 2026-11-19 was a truthful-result failure: the app said "saved", and the old speed kept playing. They also cover both halves of the family, media and text. Studio, Player, Beacon and Social are left out, because a pilot on an app that is gated or still migrating would measure its release state rather than the design.

## 2. What to start with: truthful results and stable lists, unless something worse is seen

Start with **FUX-04** (finish with the actual result) and **FUX-06** (lists that do not move under the reader), in that order and in both pilots.

There is one standing exception, as the plan itself says. If observation finds lost work, a misleading state or an input that goes to the wrong place, that defect comes first and is fixed before any of the planned work. The 2026-11-19 Cast speed fix (#1942) was one of these and is already done. Defects are not batched behind design work.

## 3. The one cross-app journey: A, "I heard something worth keeping"

The journey runs from Cast to a saved place to QUILL. You hear a passage, save the exact place with a short note, come back to it later, and open the related transcript or notes in QUILL without losing where it came from.

**Why A:** it uses the first pilot, it has one clear "did it work?" moment (the place you come back to is the place you saved), and it exercises the handoff the family already has (the app launcher and session restore) rather than adding a new kind of handoff. Journey B depends on Studio, which is not a pilot. Journey C is continuity inside one app, and the pilots already cover that. Beacon takes part only once it is released. Until then, the saved place is Cast's own bookmark plus a note in QUILL, and no other handoff types are added before this one works.

## 4. Where shared behavior stops

- **Audio ownership.** Each app owns its own playback and recording. No app pauses, ducks or reroutes another app's audio unless the person chooses it, either at the moment or as a setting they turned on. Weather's configured alerts keep their own policy. "What is playing or recording here?" is answered by each app about itself. There is no family mixer.
- **Preferences.** What the family shares stays as narrow and opt-in as `family_preferences.py` makes it today. Keys, focus behavior, accounts and billing are never synchronized. A shared setting is added only when it means exactly the same thing in every app that reads it (the settings-vocabulary gate already asks this).
- **Inserting text into another app** (Transcribe, Inkwell, Dictate Here). Text is inserted only into the target that was current when the input began. If the target's identity changes, or cannot be confirmed, the text is kept and offered as Insert or Copy. It is never typed somewhere else, and never read aloud unasked. A secure or password field is refused only where the platform can tell, and nothing claims to detect one where it cannot.

## 5. What is promoted

- **Accepted and promoted:** FUX-04 and FUX-06 for the two pilots, and journey A. They are recorded in the Quill Cast PRD (23.33) and the QUILL Lite PRD (the section of the same name), and they are tracked as one row in `complete.md` Part 3.
- **Accepted as rules, with no new work:** the boundaries in section 4. They describe how the family already behaves and are the test any later proposal must pass.
- **Not promoted yet:** FUX-01, 02, 03, 05 and 07 to 16. They stay proposals in the source plan until the pilots give evidence for them. Section 9's "leave out" list stands as it is.
