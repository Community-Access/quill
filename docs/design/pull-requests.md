# Pull requests you can hear: the plan

*Plan of record, started 2026-11-09. QUILL and QUILL Lite, one shared
implementation (rule 10). Cited as `pull-requests.md <section>`.*

## 1. Why this, and why now

QUILL already turns a pull request into something you can walk. You hear the
whole pull request in one sentence ("Approved, 2 checks failing, 1 open thread,
3 commits behind main"), you walk an outline of files, threads and checks,
you comment on a line or a range, suggest a change, keep comments pending and
send one review. GitHub Guide chapter 5 describes all of it, and it is solid.

What it does not do yet is **tell you what changed**. Today a change sounds
like one of these:

- "Difference 2 of 5. Text changed at line 41." Then, if you ask for more:
  "Change: changed 'count>10' to 'count>=10'."
- "Difference 3 of 5. 3 lines replaced with 5 at line 80."
- "Added line 42: `        return total`" (with every space read, or not,
  depending on your screen reader).

A sighted reviewer glances at a red-and-green block and knows in a second that
a number went from 10 to 20, or that a function moved, or that 30 lines are
the same edit made 30 times. A screen-reader user hears quoted fragments and
line counts, and has to rebuild the meaning in their head. That is the gap.

Changes come in every size: **one character** (`>` became `>=`), **one name**
(`count` became `total`), **one line**, **a block** (a new function),
**many places at once** (the same rename in 14 files), **a move** (code that
went somewhere else unchanged) and **nothing that matters** (indentation,
line endings). Each deserves its own kind of sentence.

The goal is that a blind developer reviews a pull request **faster and with
more confidence than they could on the website**, and enjoys it: never
overwhelmed, never lost, always able to go one level deeper.

## 2. Principles

1. **Say what happened, not where the bytes are.** "The limit went from 10 to
   20" before "line 41". The line number is always there, second.
2. **Gist first, detail one key away.** Every change has three depths: the
   *gist* (one short sentence), the *change* (before and after), and the
   *characters* (spelled, with punctuation named). You choose how deep, change
   by change. No verbosity setting decides it for you (GATE-13's rule: say
   less, rather than making people configure how much less).
3. **The size of the sentence matches the size of the change.** One character
   gets one short sentence. A 200-line new file gets a sentence about its shape,
   not 200 lines read aloud.
4. **Punctuation is content in code.** In a change description, QUILL names
   the characters that changed ("greater-than became greater-than-or-equal"),
   whatever the screen reader's punctuation level, the way dictation's "hear
   the punctuation" already does. The full line still reads as normal text.
5. **Never hide, never guess.** Anything summarised can be expanded to the
   exact text. A heuristic ("this looks like a rename") says it is a heuristic
   when it is not certain, and the plain diff is always one key away.
6. **Your place is sacred.** Reading never changes anything on GitHub. Leaving
   and coming back returns you to the same change. "Viewed" and "visited" are
   yours.
7. **Speech, braille and sound together.** Every sentence goes through the
   announcement service (GATE-BRAILLE). Braille gets a compact form that fits a
   40-cell display. Sounds are optional cues, never the only signal.
8. **Delight is in the timing.** The right sentence at the right moment, a
   soft tone instead of a word you have heard a hundred times, and a moment of
   celebration when you have reviewed everything.

## 3. The experience, from the reviewer's chair

A walk-through of what it should feel like. Keys in this section are proposals
(section 9 lists them and the rules they answer to).

**Opening.** Pull request #42 opens. You hear the one sentence you hear today,
then one more: **the shape**.

> "Review loaded for pull request #42. Approved, 2 checks failing, 1 open
> thread. 7 files: 4 source, 2 tests, 1 doc. Mostly in src/billing. Biggest:
> invoice.py, 48 lines added."

**The story, if you want it.** Press **What Is This Pull Request?** and hear
the author's description, read as text with its headings and lists, then
QUILL's own plain account of the changes, file by file, in a sentence each:

> "invoice.py: new function round_total, and the tax rate changes from 0.2 to
> 0.25. test_invoice.py: 3 new tests. README.md: one paragraph reworded."

**Walking the changes.** In the review, **Next Change** and **Previous Change**
walk every change in the pull request, across files, in order. Each change is
its gist:

> "invoice.py, change 2 of 5. The tax rate went from 0.2 to 0.25. Line 14."

> "invoice.py, change 3 of 5. New function round_total, 9 lines, at line 30."

> "utils.py. One character: greater-than became greater-than-or-equal, in
> `if count >= limit`. Line 7."

> "12 lines moved, unchanged, from line 80 to line 20."

> "Formatting only: indentation, 6 lines."

**Going deeper.** On any change, **Tell Me More** gives the before and after:

> "Before: `TAX_RATE = 0.2`. After: `TAX_RATE = 0.25`."

and **Spell the Change** gives the characters that differ, with punctuation
named, then puts you in the details field where you can arrow by character.

**The same edit, many times.** When a pull request repeats one edit, QUILL says
it once:

> "The same change in 14 places across 6 files: print( became logger.info(.
> Press Enter to list them."

**Commenting where you are.** Comment on This Change attaches to exactly the
lines of the change you are on, with the gist in the comment window's title:
"Comment on: the tax rate went from 0.2 to 0.25". A suggestion starts with the
new text already in the box.

**Keeping track.** **Mark File Viewed** sets GitHub's own "Viewed" checkbox,
so your progress shows on the website too. Progress is one sentence away:
"3 of 7 files viewed; 2 comments pending."

**Finishing.** When you have walked every change, you hear a short, warm sound
and: "That's every change. 2 comments pending. Compose your review?" Enter
opens Compose Review with them listed.

## 4. Describing a change

This is the heart of the plan: one shared describer,
`quill/core/change_describer.py`, wx-free and strict-typed, used by the pull
request review, the diff window, Compare Documents, local Git changes (Review
Changes in project tasks) and Story Studio's revisions. One engine means one
way of hearing a change everywhere in the family.

### 4.1 What it takes and gives

- Input: the old and new text of one hunk (or one Compare group), the file's
  language if known, and the line numbers.
- Output: a `ChangeDescription` with `kind`, `gist` (one sentence, at most
  about 15 words before the location), `detail` (before and after),
  `characters` (the spelled difference), `braille` (a compact form), `lines`
  (exact range for comments) and `confidence` for anything heuristic.

### 4.2 The kinds, smallest to largest

Each kind has a fixed sentence pattern, so you learn the shapes by ear.

| Kind | Detected by | Gist |
| --- | --- | --- |
| Character | one line, one changed span of at most 3 characters inside a token | "One character: greater-than became greater-than-or-equal, in `if count >= limit`." |
| Case | the change is letter case only | "Capital letter: `Total` was `total`." |
| Number | a numeric literal changed and nothing else | "10 became 20, in `limit = 20`." |
| Text | a string literal changed | "The text "Save" became "Save As"." |
| Name | one identifier changed, in one line | "`count` renamed to `total`." |
| Token | a few tokens changed in one line | "In line 41: `>` became `>=` and `10` became `limit`." |
| Line added or removed | one whole line | "Line added: `return total`." |
| Lines | a short block (2 to 5 lines) | "3 lines added after `def save(self):`: …" (the first line, then "and 2 more") |
| Block | a block with a recognisable start | "New function `round_total`, 9 lines." / "Removed class `LegacyExporter`, 40 lines." |
| Moved | removed lines reappear elsewhere unchanged (or nearly) | "12 lines moved, unchanged, from line 80 to line 20." |
| Repeated | the same token change in several places | "The same change in 14 places: `print(` became `logger.info(`." |
| Formatting | whitespace or line endings only | "Formatting only: indentation, 6 lines." |
| File | added, deleted, renamed, binary, generated | "New file, tests/test_invoice.py, 3 tests." / "Renamed from util.py, unchanged." |

### 4.3 How the parts are found

- **Tokens, not words.** Code is split into identifiers, numbers, strings,
  operators and punctuation (a small tokenizer per language family, falling
  back to a generic one), so `count>10` is three tokens, not one "word".
  Prose (Markdown, plain text, comments inside code) keeps word-level
  description, which already works well.
- **Character spans** come from `difflib` on the line, as Compare Documents'
  `InlineChange` already does, trimmed to token boundaries for the gist.
- **Blocks** are recognised by their first line: the language servers QUILL
  already ships answer "what symbol starts here" for Python, JavaScript,
  TypeScript, HTML, CSS and JSON; a light pattern list covers the rest
  (`def`, `function`, `class`, `fn`, headings in Markdown). Without either, the
  gist says "N lines added" and quotes the first line.
- **Moves** are matched by normalised line hashes across a file and across the
  pull request, with a minimum of 3 lines so trivial lines do not match.
- **Repeats** group identical token-level changes; a group of 3 or more is said
  once.
- **Generated and lock files** (`package-lock.json`, `*.min.js`, snapshot
  files, `.ipynb` output) are recognised and summarised in one line, with the
  full diff still one key away.

### 4.4 Saying characters

A **character vocabulary**, shared with dictation's "hear the punctuation":
"greater-than", "greater-than-or-equal" (said for `>=`), "not-equal" (`!=`),
"arrow" (`->`, `=>`), "open bracket", "close brace", "backquote", "space",
"tab", "nothing" (for an empty side). Two characters that look alike are
told apart: "hyphen" against "en dash", "straight quote" against "curly
quote", "letter O" against "zero" when the change is between them. Unicode
changes name the character ("non-breaking space became space").

### 4.5 Length and pacing

- The gist is short enough to hear while arrowing: at most about 15 words
  before the location, and the location last.
- A quote of code inside a sentence is capped (about 60 characters, then "and
  more"); the full line is in Tell Me More.
- A change you have already heard, heard again, gives the gist only once more,
  then "same as before" if nothing moved.

## 5. The pull request at a glance

### 5.1 The shape sentence

After the existing one-sentence summary: the number of files by kind (source,
tests, docs, config, generated), the area they are mostly in (the deepest
common folder holding most of the change), and the biggest change. Built from
data the review already loads (file list, additions, deletions), so no new
requests.

### 5.2 What Is This Pull Request?

A window (or the details pane, from the outline's top row) with:

1. the title, author, branch into base, and age;
2. the description, rendered from Markdown to readable text with headings
   and lists kept (the same renderer the GitHub windows use for issues);
3. **Changes in plain words**: one sentence per file, built from the change
   describer's gists, biggest first, with generated files folded into one line;
4. linked issues and what they say they close.

Optionally, with consent and an AI chosen in Choose Your AI, **Explain This
Pull Request** asks the AI for a summary, bounded and cited the way
`diff_explanation.py` already bounds a diff explanation. It is a button, never
automatic, and it says which AI was asked.

## 6. Walking and reviewing

### 6.1 One walk across everything

**Next Change** and **Previous Change** move through every change of every
file in outline order; **Next File** and **Previous File** jump files. The
outline follows along, so the tree always shows where you are, and Tab still
reads the details. The existing Next Unresolved and Next Unvisited stay.

### 6.2 Three depths, three keys

- **Gist**: what you hear when you arrive.
- **Tell Me More**: before and after, each as a line you can read.
- **Spell the Change**: the differing characters, named; focus moves into the
  details field at the first changed character so arrows can inspect it.

Pressing Tell Me More twice is Spell the Change, matching the family's "press
twice for more" habit (Which AI Am I Using).

### 6.3 Before and after

On any change, **Before and After** toggles the details field between the old
text and the new, keeping the cursor on the same line, so a reviewer can
arrow through either version. On a multi-line change this is the closest thing
to side-by-side that works by ear.

### 6.4 Viewed, and progress

- **Mark File Viewed** uses GitHub's own viewed state (GraphQL
  `markFileAsViewed` / `unmarkFileAsViewed`), so it agrees with the website.
  It is a write, so it needs sign-in, and it says so.
- The outline row for a viewed file says "viewed"; a file that changed after
  you marked it says "changed since viewed" (GitHub's `DISMISSED` state).
- **Review Progress** says one sentence: files viewed, changes walked,
  comments pending, threads you opened.

### 6.5 Finishing well

When the walk reaches the last change, a soft completion sound and one
sentence: what you did and what is next. If comments are pending, Enter opens
Compose Review with them listed by gist, not just by line.

## 7. Commenting

- **Comment on This Change** anchors to the change's exact lines (the
  existing `anchor_for` and `lines_for_range` already know GitHub's rules), and
  the window's title is the change's gist.
- **Suggest a change** starts with the new text in the box, with the change
  already made, so the reviewer edits rather than retypes.
- **Pending comments** list by gist ("On: the tax rate went from 0.2 to 0.25")
  as well as by line, so a review can be checked before it is sent.
- **Quick replies**: on a thread, a short list of the replies people send most
  ("Done.", "Good catch, fixed in the next commit.", "Could you say more?"),
  editable, and saved per person. Never sent without the person choosing.
- **Reading a thread** says who said what, in order, with code blocks and
  suggestions announced as such ("Suggestion: replace line 14 with …").

## 8. Sound, braille and the screen reader

- **Optional line cues.** In Patch lines, a soft high tone for an added line,
  a low one for a removed line, nothing for unchanged. With cues on, the words
  "Added line" and "Removed line" shorten to the line number. Off by default;
  turned on in the sound scheme, never required to understand anything.
- **Braille form.** Each gist has a compact braille rendering: `+14 0.2→0.25`,
  `~7 > → >=`, `mv 80→20 12L`. The full sentence is a press of a routing key
  or Tell Me More away. Arrow characters fall back to `->` on displays and
  tables that lack them.
- **Nothing the screen reader already says** (GATE-13): focus moves are not
  announced; the gist is the tree row's own text where possible, so the
  screen reader reads it as part of the row, and is only announced when the
  change is reached by a command that does not move focus.
- **Punctuation in full lines** is left to the screen reader; only the
  change description names characters.

## 9. Keys, menus and help

All keys are window-local (the review and diff windows), so they cannot claim
an editor chord, and each follows the family rules (`quill/core/family_rules.py`).
Proposals, to be checked against the window's existing access keys (GATE-14):

No bare letters: in a tree, typing a letter jumps to the next row starting
with it, and reviewers use that to find a file by name.

| Command | Proposal | Note |
| --- | --- | --- |
| Next Change / Previous Change | `Ctrl+Alt+Shift+.` / `Ctrl+Alt+Shift+,` | Compare Documents' Next and Previous Difference: the same idea gets the same key (F8 is Start Selection in the editors) |
| Next File / Previous File | `Ctrl+Down` / `Ctrl+Up` | |
| Tell Me More (twice: Spell the Change) | `F2` | |
| Before and After | `Ctrl+B` | |
| Mark File Viewed | `Ctrl+Shift+V` | toggles |
| Comment on This Change | `Enter` on a change row; `Alt+L` as today | |
| What Is This Pull Request? | a free access letter (`Alt+W` is Request Reviewers) | |
| Review Progress | `Ctrl+Shift+P` | |

Every command is also on the window's menu or context menu with its key in the
label (the menu accelerator rule), has F1 help written at the construction
site, and appears in What Can I Say Here for the review window, so "next
change" and "what changed here" work from Say or Type a Command.

## 10. Documentation

Documentation is part of the feature, written as it is built:

- **GitHub Guide chapter 5** is rewritten as a story: "Your first review",
  from opening to sending, with every kind of change heard once, then the
  reference sections as they are now.
- **A sound gallery**: a page, "What a change sounds like", listing every kind
  in section 4.2 with its example sentence and braille form, so a person can
  learn the shapes before meeting them.
- **A lesson** in Help > Tutorials: review a small practice pull request
  (a fixture repository, so it works offline) with five planted changes, one
  of each size.
- **Release notes** tell it as the story it is, with "try this" lines.

## 11. Testing

- **A corpus of real changes**: about 200 hunks taken from public pull
  requests in several languages, each with the expected kind and gist,
  checked into `tests/fixtures/pull_requests/`. The describer must keep
  passing it; a change to a sentence is a reviewed change to the fixture.
- **Property tests**: a gist never exceeds its length; every description
  round-trips to the exact lines it came from; nothing heuristic is stated as
  certain.
- **Performance**: a 300-file, 20,000-line pull request describes in under a
  second on the reference machine, off the UI thread (task manager), with the
  outline usable while it works. GATE-PERF gains a case.
- **Screen-reader checks** in `docs/qa/` for every new window and sentence,
  with NVDA, JAWS, Narrator and VoiceOver.
- The existing gates: GATE-13 (no over-announcing), GATE-14 (access keys),
  GATE-BRAILLE, help audits, the dialog contract, and QUILL Lite's coverage
  gate for every new handler.

## 12. Phases

Each phase ships on its own and is useful on its own.

| Phase | What | Size |
| --- | --- | --- |
| 1 | The change describer (section 4) with its corpus, used by the diff window's Differences list and Compare Documents. Character vocabulary shared with dictation. | large |
| 2 | Walking: Next/Previous Change and File across the pull request, three depths, Before and After, comment on this change. | large |
| 3 | The shape sentence and What Is This Pull Request? (without AI). Quick replies. Pending comments by gist. | medium |
| 4 | Viewed (GitHub's own state), Review Progress, finishing well, line cues and braille forms. | medium |
| 5 | Moves, repeats and generated files across the whole pull request; Explain This Pull Request with consent. | medium |
| 6 | Docs: chapter 5 as a story, the sound gallery, the practice lesson; release notes. | medium, alongside each phase |

## 13. Open decisions for Jeff

1. **Names.** "Next Change", "Tell Me More", "Spell the Change", "Before and
   After", "What Is This Pull Request?" Are these the words you want?
2. **Line cues.** Off by default (proposed), or on by default with words
   dropped when they are on?
3. **Viewed on GitHub.** Use GitHub's own viewed state (proposed, it syncs with
   the website), or keep "viewed" on this computer only?
4. **The AI summary.** Include Explain This Pull Request in phase 5 (proposed),
   or leave AI out of reviewing entirely?
5. **Where the describer is used first.** Pull requests and Compare Documents
   together (proposed), or pull requests only to start?
6. **The practice repository.** A fixture shipped with QUILL (works offline,
   proposed), or a real public repository on GitHub?

## 14. Progress log

- **2026-11-09.** Plan written, from GitHub Guide chapter 5, `diff_lines.py`,
  `compare_service.py` and `pr_summary.py` as they are on `main`. Nothing built
  yet.
