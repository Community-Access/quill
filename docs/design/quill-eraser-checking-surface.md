# one key, one list — Quill Eraser as the whole checking surface

**Status:** proposal / scoping. Nothing here is built.
**Started:** 2026-09-22. Revised the same day after two corrections.

**The ask, in three parts, in the order they arrived:**

1. "It would be cool if we had something like JAWS's Text Analyzer for markdown
   and HTML."
2. "Treat this similar to spell checking — move to next and previous error, get a
   listing of errors, move through errors like spell-check-type scenarios."
3. "We should merge all of this into Eraser." · "Can we extend this for grammar
   checking, or is that too far of a reach — and is there not a way to do this
   that is *magical*?"

---

## 0. Two corrections to the first draft of this document

**Correction one: GLOW already does a third of it.** The first draft of this plan
proposed building a markdown and HTML accessibility rule engine from scratch. It
already exists. `quill/core/glow.py` is 810 lines with thirteen live rules —
`GLOW-MD-HEADING-JUMP`, `GLOW-MD-IMAGE-ALT`, `GLOW-MD-LINK-TEXT`,
`GLOW-MD-HEADING-SPACING`, `GLOW-HTML-HEADING-JUMP`, `GLOW-HTML-IMG-ALT`,
`GLOW-HTML-LINK-TEXT`, `GLOW-HTML-LANG`, `GLOW-HTML-TABLE-HEADERS`,
`GLOW-PLAIN-LANGUAGE`, `GLOW-DENSE-PARAGRAPH`, `GLOW-TAB-INDENT` — with a
`GlowFinding` that already carries `severity` *and* `fixable`, a deterministic
`fix_text`, a non-destructive file-level audit/fix path for DOCX, PPTX, XLSX, PDF
and EPUB through an external engine seam, and six commands wired into the Tools
menu behind the `core.glow` experimental flag.

What GLOW does **not** have is the thing the ask is actually about: its output is
a **report written into a scratch tab**. There is no next, no previous, no "issue
3 of 17", no per-finding fix, no ignore, no undo. You read a list of line numbers
and then go find them yourself. That is the entire gap, and it is an interaction
gap, not a detection gap.

**Correction two: the merge decision is made.** The first draft left "merge with
Quill Eraser or sit beside it?" open and leaned toward a sibling engine. Jeff's
answer: merge all of it into Eraser. That is the right call and it makes the rest
of this document much simpler — and, as §7 argues, the merge *is* the magic. The
consequence is larger than it sounds: **Quill Eraser becomes the single checking
surface in QUILL**, and spelling, hygiene, GLOW's accessibility rules, markup
structure and grammar all become families of findings inside one list.

## 1. The thesis

Right now, a QUILL user who wants to know what is wrong with their document has
to choose an engine before they get an answer:

| To find | You press | And you get |
| --- | --- | --- |
| Misspellings | `F7` | A guided review session — next, previous, change, change all, ignore, undo |
| Extra spaces, punctuation spacing, blank-line runs | Tools ▸ Quill Eraser (no chord) | A findings list dialog — apply fix, ignore, go to, rescan |
| Missing alt text, heading jumps, generic link text | Tools ▸ GLOW Audit Document | A report in a scratch tab. Line numbers. Go find them yourself. |
| Grammar, clarity, style | Tools ▸ AI Grammar & Style (no chord) | A separate AI dialog, a separate result shape |
| Suspect spellings the dictionary missed | Tools ▸ AI Spell Check (no chord) | A third AI dialog |

Five entry points, four result shapes, and a decision the user has to make before
they have any information to make it with. Nobody opens a document thinking "I
would like an accessibility audit specifically." They think *is this any good
yet.*

**The proposal is one key, one list, every engine.** You press one key. You get
one ordered list of everything wrong with the document — a misspelling, a
double space, a heading that skips a level, an image with no alt text, a
their/there, a passive sentence — in document order, each with a plain sentence
saying what it is and why it matters, each with fixes you can apply, ignore, or
turn off forever. You work it to zero. You never learn which engine found which
item, because that is QUILL's problem and not yours.

That is the whole design. Everything below is in service of it.

## 2. Prior art: what to take, what to leave

### 2.1 JAWS Text Analyzer — the origin of the idea

Text Analyzer flags *inconsistencies* as you read: runs of extra spaces,
mismatched or unclosed punctuation, font and attribute changes mid-word,
capitalisation oddities, highlighted text. You choose how it tells you — a sound,
a spoken message, both, or nothing — and a keystroke describes the error at the
cursor once you have heard the cue.

Three things matter for us:

1. **Its vocabulary is typographic, not structural.** It has to be: JAWS reads a
   rendered surface through an accessibility API, so "unclosed bracket" is
   reachable and "this heading skips a level in the source" is not. QUILL holds
   the source and can do strictly better.
2. **Its delivery is ambient.** Excellent for proofreading something somebody
   sent you; poor for auditing something you are writing, where you want a list,
   a count, and a path to zero. Hence the user's own redirection to the
   spell-check model.
3. **It knows nothing about the file.** It cannot tell a fenced code block from
   prose, so in a markdown file half of what it says is noise — the same
   false-positive problem `spellcheck_live.py` already solves for the live
   spelling alert.

So: take the idea (*the editor owes you the defects you cannot see*), take the
delivery choices (sound / speech / both / silent, which `action_feedback.py`
already models exactly), and keep the review session as the primary interaction.
The ambient tier survives as phase 4, off by default.

### 2.2 VS Code — the closest thing to a model for us

VS Code's diagnostics model is the right abstraction and its accessibility work
is the right delivery. Worth copying, in order of value:

- **The diagnostic shape itself** (from the language-server `publishDiagnostics`
  contract): a range, a severity, a source, a machine-readable `code` with a help
  URI, a human message, and optional *related information* pointing at a second
  location. That last field is why `Finding.related` exists in §4.1 — "this link
  text is used twice for different targets" and "this anchor matches no heading"
  are both two-place findings and all three of QUILL's current finding types are
  structurally incapable of expressing them.
- **Code actions as a concept separate from the diagnostic.** One diagnostic can
  offer several fixes, and some need input. This is why `Finding.fixes` is a
  tuple and not a `suggested_text: str | None` — "image has no alt text" has at
  least three answers (draft it with vision, write it myself, mark it decorative)
  and a single replacement string cannot hold that.
- **Go to Next / Previous Problem in File** (F8 and Shift+F8 there) with the
  diagnostic *spoken on arrival*, no panel required. This is precisely the
  interaction the ask names, and §8's traversal chords are the same thing.
- **Accessibility signals** (`accessibility.signals.*`): per-event, independently
  configurable sound *and* announcement, including an "error on line" cue as the
  caret moves. This is the phase-4 ambient tier done properly, and it maps
  one-to-one onto `action_feedback.resolve` — which means QUILL already has the
  setting vocabulary for it and must not invent a second enum.
- **The Accessible View** (Alt+F2): take what would otherwise be a hover or a
  squiggle and put it in a plain readable buffer you can arrow through. QUILL's
  equivalent already exists in spirit — it is what the spelling review's Detail
  box is, and §4.2 keeps it.
- **The Problems panel** as a filterable, sortable, *navigable* list separate
  from the editor. Eraser's `wx.ListCtrl` is already this and needs only a
  Severity column and a family filter.

What **not** to copy: squiggles as the primary signal, hover-dependent detail,
and the badge that says "47 problems" while offering no path through them.

### 2.3 JetBrains IDEs

- **Inspection profiles** — named bundles of rules with per-rule severity,
  switchable per project. Strictly better than Eraser's current flat
  `hygiene_rules_disabled` CSV string, and it is the same shape
  `markdown_profiles.py` already uses for extensions, so the house pattern
  exists. Proposed starting set: **Everyday writing** (structure, inline, prose,
  spelling; media and ARIA off), **Publishing** (adds links, media, tables —
  the default when the document has a publishing target configured),
  **Accessibility review** (every WCAG-mapped rule at every severity, nothing
  suppressed — the one you run before you ship), **Documentation** (adds anchor
  validity, fenced-code-language, duplicate headings, plain language), and
  **Strict**.
- **Alt+Enter at the caret** — one key offering every available fix for whatever
  is under the cursor, with no dialog at all. This is the single best keyboard
  affordance in any editor for this job and QUILL has nothing like it. It is
  §7.6, and the chord is confirmed free.
- **A batch "Inspect Code" producing a tree you work down**, distinct from the
  in-editor experience. Two entry points, one rule engine — which is exactly the
  phase-1/phase-5 split in §10.

### 2.4 Microsoft Word — the accessibility checker and the Editor pane

Word is the mainstream product closest to this feature's *subject matter*, and
its lessons run both ways.

- **Take:** "Keep accessibility checker running while I work" — a background scan
  with a status readout rather than a modal event. And the Inspection Results
  pane's grouping into Errors / Warnings / Tips with a **"Why Fix"** and
  **"How To Fix"** explanation on every single finding. The why-sentence is
  non-negotiable and it is why `Finding.why` is a mandatory field with a gate
  behind it (§9.1): *a rule with no rationale is a rule that gets switched off
  and never switched back on.*
- **Leave:** the pane is a tree you must mouse or tab into, the fix is usually in
  a context menu buried on the item, and a status-bar line is the only ambient
  signal. We beat all three with a review session and a chord.
- **The real lesson is Word's own inconsistency.** Its *Editor* pane — spelling,
  grammar, style and clarity in one reviewable stream with a per-issue card — is
  already the interaction this plan proposes, and Microsoft shipped it *beside*
  a separate Accessibility Checker with a separate pane, separate vocabulary and
  separate verbs. Same document, same user, same question, two products. That
  split is precisely what §1 refuses to reproduce, and Word is the proof that it
  happens by default unless someone decides otherwise.

### 2.5 The lint ecosystems — where the rules come from

We do not have to invent the catalogue. Four bodies of prior art, all with
published, stable rule IDs:

- **markdownlint** (`MD001` onwards) — heading increment, first-line heading,
  multiple top-level headings, no-duplicate-heading, ol-prefix, ul-style,
  list-indent, blanks-around-lists, no-bare-urls, fenced-code-language,
  table-column-count, no-empty-links, link-fragments, no-alt-text,
  no-emphasis-as-heading, no-trailing-spaces. Roughly two dozen of its rules are
  about things a screen-reader user cannot see; those are the starred ones in §5.
- **remark-lint and retext** (the unified ecosystem) — the same for markdown
  syntax trees, plus the `retext-*` prose family: repeated words, indefinite
  article agreement, passive voice, readability, simplify, equality. This is
  where grammar tier 1 (§6.1) gets its rule list.
- **Vale** — severity levels, project-level config, and **inline
  `<!-- vale off -->` suppression comments**. That convention is worth adopting
  wholesale (ESLint and markdownlint use the same idea, so users already know
  it): §10 phase 2 ships `<!-- quill-disable md.heading-increment -->`,
  `<!-- quill-disable-next-line -->` and `<!-- quill-enable -->`. Suppressions
  that live in the file travel with it and explain themselves to the next person
  who opens it, which session-scoped Ignore cannot do.
- **HTML** — html-validate, HTMLHint and the Nu Html Checker for well-formedness;
  **axe-core** and HTML_CodeSniffer for the accessibility half. Every axe rule
  carries a WCAG success criterion, a severity and a help URL, and that mapping
  *is* the "why fix" text we need anyway.

**The licensing and packaging line: rule IDs are cited, never vendored.** No
Node toolchain, no Java, no bundled binary. A finding whose description says
`MD001` and WCAG 1.3.1 is one the user can look up, and that costs us nothing.

### 2.6 Everything else, briefly

**Emacs Flycheck/Flymake and Vim ALE** (`:lnext`, `]d`) — next-diagnostic
traversal, keyboard-only, no panel: proof the model works with no pointing device
anywhere in it. **Visual Studio's Error List** and **Sublime's SublimeLinter** —
nothing new. **Obsidian and Typora**, the two best-known markdown editors —
nothing at all to learn, because neither has an analysis layer; the space is
genuinely empty. **Grammarly and Hemingway** — prose scoring, worth having as a
readability *rule family* but a bad model for the interaction (a grade is not a
path to zero, which is why §11 refuses to ship a score). **LanguageTool** —
discussed and rejected in §6.2.

## 3. What already exists

This is an assembly job, not a greenfield one. The inventory is the plan.

| Piece | Where | What it gives us |
| --- | --- | --- |
| **GLOW audit engine** | `quill/core/glow.py`, `quill/ui/main_frame_glow.py` | Thirteen markdown/HTML/prose rules, `severity` + `fixable`, deterministic `fix_text`, a file-level audit/fix seam for Office and PDF and EPUB, and the non-destructive `-accessible` copy convention |
| **Quill Eraser** | `quill/core/hygiene/{engine,rules,findings,ignored_ranges}.py`, `quill/ui/hygiene_dialog.py`, `main_frame_hygiene.py` | A `HygieneRule` ABC, findings with offsets / line / column / suggestion / `can_auto_fix`, per-rule disable, a confidence floor, code-vs-prose file classification, and a list dialog with Apply Fix / Ignore / Go To / Previous / Next / Rescan |
| **Spelling review session** | `quill/core/spelling/session.py`, `models.py`, `announcements.py`, `quill/ui/spelling_review_dialog.py` | The exact interaction requested: `current()` / `total()` / `position()`, change-all, ignore-all, add-to-dictionary, `undo_last`, wrap-to-beginning, rescan-after-edit with offset shifting, counters, an accessibility announcer |
| **AI grammar and style** | `quill/core/ai/grammar_check.py` | Already returns structured `GrammarIssue(category, original, suggestion, explanation, context)` across grammar / punctuation / clarity / style / word choice, chunked at 40k chars |
| **AI vision** | `quill/core/ai/vision.py` — `describe_image()` | Describes an image file for a blind reader, through the same secured POST path as chat, with an Ollama local-model route and a capability pre-flight. **This is the crown jewel; see §7.3** |
| **Image at the caret** | `quill/core/inline_image_alt.py` | Already answers "what image is the caret inside, and does it have alt text" for markdown *and* HTML |
| **Link inventory** | `quill/core/link_inventory.py` | Parses markdown and HTML links and images into `LinkRecord` / `ImageAltRecord` |
| **Preview-matching slugs** | `markdown_extensions.slugify`, `browser_preview._slugify` | Anchor validation is free — we can compute the exact id the preview will emit |
| **Plain-language lint** | `quill/core/plain_language.py` | Controlled vocabulary with line/column output; GLOW already consumes it |
| **Live-alert suppression** | `quill/core/spellcheck_live.py` | URL, code-span and fence suppression — every prose and grammar rule needs this |
| **Feedback channels** | `quill/core/action_feedback.py` | `sound` / `speech` / `both` / `silent` via one shared `resolve(mode, *, has_sound)` — this *is* JAWS's indicate-with-sound/message/both, already built and already governed |
| **Optional components** | `quill/core/optional_components.py` | A single status model and download flow already carrying node, ffmpeg, pandoc, braille, voices and dictionaries — the shelf a POS tagger goes on (§6.2) |
| **Background work** | `quill/stability/task_manager.py` | `QuillTaskManager` + `wx.CallAfter`, which is how AI findings arrive without blocking (§7.2) |
| **Contrast, ACR, Reveal Codes** | `contrast.py`, `acr.py`, `reveal_codes.py` | Colour maths for HTML rules, a conformance-report renderer for phase 5, and a second place to surface a finding at its position |

The genuine gaps are three, and only three:

1. **One finding vocabulary.** There are currently three — `HygieneFinding`,
   `GlowFinding`, `GrammarIssue` — plus `SpellingIssue`. None can express two
   locations or more than one possible fix.
2. **One review session over all of them.** The spelling session is the model and
   it is already written; it needs generalising off `Misspelling`.
3. **Structural markup rules beyond GLOW's thirteen**, and grammar rules at all
   without an AI provider.

## 4. The merge: Quill Eraser as the one surface

The name is already right. An eraser removes mistakes; it does not care what kind
of mistake. So:

- **Quill Eraser is the product.** One Tools entry, one key, one dialog, one
  list. Tools ▸ Quill Eraser.
- **GLOW keeps its identity where it earns it** — the file-level audit and repair
  of DOCX / PPTX / XLSX / PDF / EPUB on disk is a genuinely different job with a
  genuinely different output (a repaired copy next to the original), and it is
  partly an external engine. Those two commands stay as they are. GLOW's
  *in-editor* audit and fix commands are absorbed: `GLOW-MD-IMAGE-ALT` becomes a
  rule family inside Eraser and `Tools ▸ GLOW Audit Document` goes away.
- **The AI spelling and grammar dialogs are absorbed too.** They stop being
  destinations and become contributors (§7.2).
- **F7 spelling stays exactly where it is.** It is thirty years of muscle memory
  and it must not move. Spelling *also* appears in the Eraser list — the same
  issues, reachable two ways — because the person who wants only spelling should
  not have to wade past passive voice to get it.

### 4.1 The finding vocabulary

One dataclass, in `quill/core/eraser/findings.py`, absorbing all three:

```python
@dataclass(frozen=True, slots=True)
class Finding:
    rule_id: str              # "md.heading-increment", "grammar.their-there"
    family: str               # spelling | hygiene | structure | media | links |
                              # tables | aria | grammar | clarity
    severity: Severity        # error | warning | suggestion
    confidence: Confidence    # high | medium | low
    title: str                # short, spoken first
    why: str                  # ONE plain sentence. Mandatory. See §9.1.
    reference: str            # "MD001", "WCAG 1.3.1", "" — cited, not vendored
    start: int; end: int; line: int; column: int
    fixes: tuple[FixOption, ...]      # zero or more; not one replacement string
    related: RelatedLocation | None   # the *other* place, for two-place findings
    engine: str               # "rules" | "ai" — internal only, never spoken
```

Two things it buys that none of the current three have. **`fixes` is a tuple**,
because "image has no alt text" has at least three answers — draft it with vision
(§7.3), write it myself, or mark it decorative — and a single `suggested_text:
str | None` cannot hold that. **`related` exists**, because "this link text is
used twice for different targets" and "this anchor matches no heading" are both
two-place findings and both currently inexpressible.

`engine` is diagnostic only. It never appears in the UI, never in speech, never
in the list. That is the point of §7.2.

### 4.2 The session

Generalise `quill/core/spelling/session.py` off `Misspelling` and onto `Finding`.
Every verb survives unchanged, which is why this is the cheap half:

| Spelling review today | Quill Eraser |
| --- | --- |
| `current()` / `total()` / `position()` — "issue 3 of 17" | Same |
| Next / Previous, with the wrap-to-beginning prompt | Same |
| Change / Change All | **Fix** / **Fix All of This Kind** |
| Ignore Once / Ignore All | Same wording, same semantics |
| Add to Dictionary (persistent, scoped) | **Never Flag This** — document / folder / everywhere |
| `undo_last` with `_UndoRecord` | Same, unchanged |
| Rescan-after-edit, advancing past the applied change, shifting later offsets | Same, unchanged — and this is the fiddly part that is already debugged |
| Detail box, issue in context | Same, plus **why it matters** and the rule id |

Plus three things spelling does not need: a **findings list** the user can arrow
into (Eraser's `wx.ListCtrl` already, with a Severity column added, sortable and
filterable by family); **Go to Issue**, which closes the dialog and leaves the
caret on the range; and **Next / Previous Issue from the editor with no dialog at
all**, spoken on arrival — the `Ctrl+F7` habit, which is how most people will
actually use this.

### 4.3 QUILL and QUILL Lite — every Eraser feature, both products

**Decision: all Eraser features ship in both.** Not the shared core with a
reduced Lite surface — the whole thing, both places. That is stricter than the
standing family rule requires and it is the right call here, because every
argument for the feature applies at least as hard to the smaller product: a
QUILL Lite user writing a README is exactly the person who will never see the
missing `alt`.

This is also the direction the family rules already push. The rule is that
QUILL Lite may never be ahead of QUILL, and that anything Lite needs goes in the
shared package with a QUILL route added in the same change. Building
`quill/core/eraser/` shared by construction satisfies the core half
automatically; §4.3 is the commitment that the *surface* half is satisfied too,
in the same commit rather than in a follow-up nobody schedules.

What that means concretely, per layer:

- **`quill/core/eraser/`** — shared by construction. Findings, rules, session,
  suppression, every rule family including HTML and ARIA. No product branches
  in core.
- **The review dialog** — one implementation, reached from both. It must not
  import `MainFrame`; `quill/ui/spell_review.py` is the existing precedent for
  running the spelling session against an arbitrary `wx.TextCtrl` from outside
  the frame, and the Eraser dialog follows it.
- **Commands and chords** — the same ids and the same chords in both keymaps.
  `F4`, `Shift+F4`, `Ctrl+Alt+F4` and `Alt+Enter` are free in both, so there is
  no divergence to justify. If one ever appears, rule 11 requires it be a comment
  in `keymap.py` **and** a parity-table row, not one or the other.
- **Grammar** — all three tiers, both products. Tier 2's optional POS component
  is a download, not a product tier; if it is absent the rules are absent, in
  both, identically.
- **Vision-drafted alt text (§7.3)** — both. This one is worth stating out loud
  because it is the feature most likely to get quietly scoped to "the big
  product": it is the single highest-value thing in the plan and it is also the
  cheapest to reach, since `vision.describe_image()` is already shared core.
- **The one real asymmetry** is GLOW's file-level audit and repair of DOCX /
  PPTX / XLSX / PDF / EPUB (§12.2). That is an external engine seam and a
  different job from in-editor checking, and it is *not* an Eraser feature — so
  it is outside this commitment rather than an exception to it. Flag it in the
  parity table as `one_side` with that reason, so the settings-vocabulary audit
  does not report it as a gap.

**Gate.** The parity claim needs a test or it is a sentence. Add a fixture
asserting that every `eraser.*` command id present in QUILL's keymap is present
in QUILL Lite's with the same chord, and that every rule family enabled by default
in one is enabled by default in the other — the same shape as the existing
bound-command and settings-vocabulary gates, and for the same reason: this is
exactly the kind of promise that decays silently.

## 5. The rule catalogue

GLOW's thirteen are the seed. Starred (★) rules below are the "invisible to a
screen reader by definition" core — the ones a sighted author catches with their
eyes in half a second and a blind author ships. External IDs are **cited, not
vendored**: no markdownlint, no Vale, no axe binary, no Node toolchain. A rule
whose description says `MD001` and WCAG 1.3.1 is a rule the user can look up, and
that costs us nothing.

**Markdown — structure.** ★ Heading level skipped (`MD001`, WCAG 1.3.1 — *already
GLOW-MD-HEADING-JUMP*) · ★ no top-level heading or more than one (`MD025`,
`MD041`) · ★ **a bold or italic line used where a heading was meant** (`MD036`) —
it reads identically and is invisible to H navigation; high value, very common ·
duplicate heading text producing ambiguous anchors (`MD024`) · heading with
trailing punctuation (`MD026`) · missing space after the `#` markers (*already
GLOW-MD-HEADING-SPACING*).

**Markdown — links and anchors.** ★ Non-descriptive link text (WCAG 2.4.4 —
*already GLOW-MD-LINK-TEXT*) · ★ **broken in-document anchor**, `[x](#slug)` where
no heading slugifies to `slug` — free, because `slugify` already matches the
preview · ★ empty link (`MD042`) · the same text pointing at two different
targets, and the reverse (needs `related`) · a bare URL as link text (`MD034`) —
the reader spells out every character · a reference link with no definition.

**Markdown — media.** ★ Image with no alt (`MD045`, WCAG 1.1.1 — *already
GLOW-MD-IMAGE-ALT*) · ★ **alt text that is a filename, a bare extension, or the
word "image"** — a false pass that automated checkers count as compliant · alt
opening "image of" / "picture of" · alt over ~150 characters with no long
description · emoji as meaningful content with no alternative · an ASCII-art or
Mermaid block with no prose alternative.

**Markdown — tables.** ★ No header row, or a delimiter row in the wrong place ·
★ **ragged table** (`MD056`) — the renderer silently drops or merges cells and the
announced column headers stop matching the data under them · no caption · a table
nested in a list, which most flavours will not render.

**Markdown — lists.** ★ **A list broken by a stray blank line**, so it renders as
two lists and "list with 5 items" becomes "list with 2 items" then "list with 3
items" · mixed bullet markers (`MD004`) · inconsistent ordered prefix (`MD029`) ·
indentation that silently changes nesting depth (`MD005`, `MD007`).

**Markdown — inline.** ★ **Unclosed emphasis** — a `**` or `_` with no partner on
the line; the direct descendant of JAWS's unmatched-punctuation check, and in
markdown it is worse than cosmetic because the rest of the paragraph changes
meaning · ★ unmatched bracket, parenthesis or quote, suppressed inside code · a
trailing double-space hard break (`MD009`), invisible and the usual answer to "why
did this line break" · mixed straight and curly quotes · raw HTML the target
flavour will escape (`MD033`) · a fenced block with no language (`MD040`) · front
matter that is not valid YAML (`yaml_structure.py` exists).

**HTML.** Everything above, plus: ★ missing `lang` on `<html>` (*already
GLOW-HTML-LANG*), missing or empty `<title>`, duplicate `id` · ★ no `<main>` or
more than one · ★ `<a>` with no accessible name — the icon link that reads as
"link" and nothing else · ★ a `<div>` with a click handler, no role, no `tabindex`
and no key handler (WCAG 2.1.1) · ★ input with no label, and placeholder-as-only-
label (WCAG 1.3.1, 3.3.2) · a radio group with no `<fieldset>`/`<legend>` · ★
`aria-labelledby` / `aria-describedby` / `aria-controls` pointing at an id that
does not exist · ★ `aria-hidden="true"` on a focusable element or containing one ·
an invalid role, a role forbidden on that element, a role duplicating native
semantics · required child roles missing · ★ `<table>` with no `<th>` (*already
GLOW-HTML-TABLE-HEADERS*), `<th>` with no `scope`, a layout table carrying `<th>`
· `<iframe>` with no `title`, `<video>` with no captions track · `<b>`/`<i>` where
`<strong>`/`<em>` was meant, `<br><br>` as a paragraph break · an inline `style`
whose colours fall below 4.5:1 (`contrast.py` already does the maths) · ★
**well-formedness** — an unclosed tag, a mis-nested tag, a stray `</div>`; the
most Text-Analyzer-like HTML rule we can ship and the one most likely to explain
a "why does this page look wrong" mystery.

**Hygiene and prose.** Eraser's seven existing rules, unchanged, plus GLOW's
`GLOW-PLAIN-LANGUAGE`, `GLOW-DENSE-PARAGRAPH` and `GLOW-TAB-INDENT`.

## 6. Grammar — is it too far a reach?

**No. Grammar is not an extension of this feature, it is the same feature.** A
grammar finding has a range, a severity, a message, a suggestion and a reason. So
does a missing `alt`. The `Finding` above holds both without a field changing.
What differs is only the *engine* that produces it — and §7.2 is the argument
that the engine should be invisible.

What *would* be a reach is trying to build an offline LanguageTool. Don't. The
honest shape is three tiers, and two of them are nearly free.

### 6.1 Tier 1 — deterministic, pure Python, no dependency, no model

About fifteen rules, high confidence, no new anything. These are the errors that
survive a spell check because every word in them is spelled correctly, which is
exactly why they are worth catching first:

- **Repeated word** — "the the", "and and" across a line break, where it hides
  best.
- **Indefinite article agreement** — "a hour", "an user". Sound-based, not
  letter-based, with a small exception lexicon.
- **Confused homophones in unambiguous contexts** — `its`/`it's`,
  `your`/`you're`, `their`/`there`/`they're`, `then`/`than`, `lose`/`loose`,
  `affect`/`effect`, `to`/`too`. Only fired where the surrounding two tokens make
  it certain; anything ambiguous is left alone. **This pair is the single highest
  yield in the whole grammar family** — it is the most common error in written
  English and a spell checker is structurally incapable of seeing it.
- **Comma splice** — two independent clauses joined by a comma, detected
  conservatively by looking for a subject pronoun after the comma.
- **Double negative**; **double punctuation** (`,,`, `..` outside an ellipsis);
  **sentence starting lowercase** (Eraser has this already).
- **Subject–verb agreement in simple, local cases** — "he don't", "they was",
  "the data is" (flagged as a suggestion, since usage is genuinely split).
- **Missing terminal punctuation** on a paragraph that is clearly a sentence.
- **Mismatched quotes across a paragraph** — Text Analyzer's rule again.

A week of work, the same rule shape as everything else, and it makes grammar real
for every user including those with AI switched off and those in Safe Mode.

### 6.2 Tier 2 — part-of-speech tagging, one optional component

Everything genuinely grammatical past tier 1 needs to know what the words *are*.
Passive voice, agreement across an intervening phrase ("the *list* of files *are*
missing"), tense consistency, dangling modifiers — none of these are reachable
with regular expressions and pretending otherwise produces a false-positive
machine.

The dependency is small and, importantly, **torch-free**: spaCy's
`en_core_web_sm` is around 12 MB and runs on numpy/Thinc on CPU, which satisfies
the standing rule that local language engines must not require torch. It goes on
the `optional_components.py` shelf next to node, ffmpeg, pandoc and the
dictionaries — the download flow, the status model and the "not installed, here
is what you are missing" copy all already exist. NLTK's perceptron tagger is the
lighter fallback if even that is too much.

The user-facing contract: **tier 2 rules simply do not appear if the component is
not installed.** No nag, no greyed-out row, no "install this to unlock". The list
is shorter and nothing else changes. One line in Download Optional Components
says what it adds.

**LanguageTool** deserves a mention and a rejection. It is the best rule-based
grammar engine in existence, roughly five thousand rules, and `language_tool_python`
makes it reachable — but it needs a JVM, which is a heavy packaging ask, and its
convenient mode talks to a public API, which would be an outbound call on
document text and is a hard no under the network-egress policy regardless of
consent UI. If it is ever revisited, it must be local-server-only and an explicit
opt-in component. Not in this plan.

### 6.3 Tier 3 — the model, which already exists

`quill/core/ai/grammar_check.py` already returns exactly the right shape across
grammar, punctuation, clarity, style and word choice. **It needs no engine work
at all.** It needs to stop being a destination and start being a contributor.

And the division of labour is the honest one: rules do the mechanical, the model
does the judgment. Some things are only ever reachable by a model —

- Is this sentence ambiguous about who did what?
- Does this link text mean anything **in the context of the sentence it is in**?
  A rule can catch "click here"; only a model can catch "the report" appearing
  four times pointing at four different reports.
- **Does this alt text actually describe this image?** A rule can catch alt that
  is a filename. Only a model that can see the image can catch alt that is
  confidently, fluently wrong — and that is worse than missing alt, because every
  automated checker scores it as a pass.

## 7. The magical part

The magic is not any single rule. It is five mechanisms, and they compound.

### 7.1 One key, one list, no decision

This is the whole thing and it is worth restating plainly: **the user never picks
an engine.** Today they must choose between five commands before they have any
information with which to choose. After this, there is one key and one list in
document order, and "misspelled word" and "heading skips a level" and "their
should be there" sit next to each other because they are all just *things wrong
with line 40*. No product does this. Word makes you run Spelling, then Editor,
then Accessibility Checker — three panes, three mental models, three vocabularies
for the same verb.

The ordering is document order, not severity order, because the user is walking
the document and the caret is a place. Severity is a filter and a spoken adjective,
never a sort key that makes you jump around the file.

### 7.2 Progressive arrival — two engines, no mode

The deterministic rules finish in milliseconds. So:

1. You press the key. **The list is already there** and already navigable. You
   start working. Nothing spins, nothing blocks, nothing asks.
2. If AI is configured, the model runs on `QuillTaskManager` in the background
   over the same text. Its findings **merge into the same list at their document
   positions**, and you hear one short line — *"four more issues found"* — once,
   never interrupting what you are reading, and never again for that scan.
3. If AI is off, offline, rate-limited or in Safe Mode, **the list is just
   shorter** and the interaction is byte-for-byte identical. No error, no
   degraded-mode banner, no "AI unavailable" dialog. The `engine` field never
   reaches the UI.

That is the trick: **the user never switches modes, never waits, and never learns
which engine found what.** A findings list that grows while you work it sounds
like a problem, but the session already handles exactly this — `_rescan` with
offset shifting after an applied fix is the same operation, and it is already
written and already debugged.

### 7.3 Draft the alt text you cannot write

This is the crown jewel, and it is most of the way built.

Eraser finds `![](screenshot.png)` on line 40. The fix it offers is **not** an
empty box labelled "write alt text". It is a drafted sentence — already written,
read aloud, editable in place, applied with one key:

> *Issue 3 of 17. Line 40. Image with no alt text: screenshot.png. Suggested
> description: "The QUILL Settings window, with the Accessibility page open and
> the Announcements section expanded." Press Enter to use it, E to edit, D to
> mark the image decorative.*

`vision.describe_image()` already exists, already reads a file from disk, already
base64-encodes it, already goes through the secured POST path with retries, and
already has an **Ollama local-model route with a capability pre-flight** — so this
can run entirely on the user's machine with no document or image leaving it.
`inline_image_alt.image_at_position()` already resolves the image reference at any
offset for markdown and HTML both. The prompt is already written and is already
addressed to a blind reader.

Think about who this is for. A blind author writing documentation with a
screenshot in it **cannot write that alt text at all** — not badly, not
approximately, not with effort. Today the options are ship it empty, ask a
sighted person, or don't use images. No product in this space solves that,
because every product in this space assumes the author can see the image and is
merely being lazy. This is the one feature where QUILL's whole premise pays off,
and it is a dialog away.

The same mechanism extends: describe a chart that has no text alternative,
transcribe text inside a screenshot (the prompt already asks for verbatim
transcription), and — the inverse, which is arguably as valuable — **verify
existing alt text against the actual image** and flag the confidently-wrong ones
that every automated checker scores as a pass.

### 7.4 Speak the difference, not the sentence

When offering a fix, say what **changes**. Not:

> *"Suggested replacement: The list of files that the converter produced are
> missing from the output folder, which means the batch did not complete."*

but:

> *"are, should be, is."*

Three seconds instead of thirty. Press Enter and it is done; press a key to hear
the full sentence if you want it. This is not a nicety — it is the difference
between a feature people use on a long document and one they turn off after the
fourth finding. `quill/core/diffing.py` already exists to compute the delta.

The same discipline everywhere: the title is spoken first and is short, the
*why* sentence is spoken only on request or at higher verbosity, and the rule id
is never spoken unless asked.

### 7.5 The list gets quieter the more you use it

Every linter dies of noise. Three mechanisms against it, in order of how often
they will fire:

- **Suppression is total and automatic** inside fenced blocks, code spans, URLs,
  HTML `<pre>`, and front matter. `spellcheck_live.live_alert_suppressed` is the
  precedent, `hygiene/ignored_ranges.py` is the mechanism, and **every rule ships
  with a test proving it stays quiet in a code fence** (§9.2).
- **Ignore teaches.** Ignore the same rule three times in one document and Eraser
  offers, once, to turn it off for this document. Not a dialog — a line in the
  detail pane and a key.
- **The model triages, it does not only generate.** The highest-value AI job in
  this whole design is not finding new issues; it is **killing false positives**
  — "this rule fired on line 12 but it is fine there" — and ranking: "of these
  forty, these six actually matter." Noise is what kills linters, judgment is
  what models are good at, and nobody points the model at that job.

### 7.6 And one key at the caret

`Alt+Enter`, free, borrowed from JetBrains: no dialog at all. You are typing, you
sense something is off, one key tells you what is under the caret and offers every
fix for it. Combined with §7.3 that means writing an image reference and
immediately getting a drafted description, without leaving the line.

## 8. Keyboard

The F7 row is full and the F9 row belongs to dictation. The **F4 row is very
nearly empty** — only `Ctrl+Shift+F4` (Close Other Documents) is taken — and
`Ctrl+Alt+F4` and `Alt+Enter` are confirmed free.

| Command | Chord | Note |
| --- | --- | --- |
| `tools.eraser_document` | **F4** | Word's F4 is Repeat Last Action, which QUILL does not bind, so rule 1 does not bite. Gives Quill Eraser the chord it has never had. Needs sign-off. |
| `tools.eraser_selection` | **Shift+F4** | Mirrors the existing document/selection pair. |
| `tools.next_issue` / `tools.previous_issue` | *unsettled* | Both natural candidates collide: `Ctrl+F4` is the MDI close-child convention and QUILL is multi-document; `Ctrl+Shift+F9` is dictation pause. See §12.1. |
| `tools.describe_issue_at_cursor` | **Ctrl+Alt+F4** | JAWS's "describe the error" key, restated. |
| `tools.fix_at_cursor` | **Alt+Enter** | §7.6. Free. Likely the best part of the feature. |

`F10` is the menu-bar key and `Shift+F10` the context-menu key; both reserved,
neither touched. `F7` does not move. Every chord must pass
`test_menu_accelerators.py` — including being parseable by `wx.AcceleratorEntry`,
since `Ctrl+Shift+Plus`-style chords are silently dropped and leave the menu
advertising a key that does nothing — plus the bound-command and Quillin-hotkey
gates. Labels come from `self._menu_label(...)`, never a literal.

## 9. Gates

1. **Rule catalogue snapshot.** A fixture listing every rule's id, family,
   severity, default state, external reference and **its one-sentence `why`**. A
   new rule fails the build until it is classified and explained. Same shape as
   `lite_command_coverage.json` and for the same reason: *a rule with no
   rationale is a rule that gets switched off and never switched back on.*
2. **Behavioural coverage.** Every rule gets a positive case, a negative case,
   and **a suppression case inside a code fence**. The third is what actually
   keeps the feature from becoming annoying.
3. **Fix idempotence.** Apply a fix, rescan: the same finding must not reappear
   and a new one must not be created. Eraser's rescan-with-offset-shift is both
   the precedent and the trap.
4. **Engine invisibility.** A test asserting that no user-facing string —
   dialog label, announcement, list column, help text — contains the word "AI",
   "model" or the `engine` value. §7.2 is a promise and promises need gates.
5. **AI-off parity.** The full session runs, and every test passes, with the AI
   provider set to Off and in Safe Mode. The list is shorter; nothing else
   differs.
6. **Product parity (§4.3).** Every `eraser.*` command id in QUILL's keymap is
   present in QUILL Lite's with the same chord, and every rule family enabled by
   default in one is enabled by default in the other. Divergence requires a
   `keymap.py` comment **and** a parity-table row, per rule 11.
7. **GATE-LITE-COVER** — QUILL Lite's handlers classified `covered`, with
   lambda-shaped parametrisation so the AST scan sees the calls.
8. **GATE-REACH** — the dialog reachable from an app entry point and snapshotted.
9. **Dialog inventory, button contract, access keys, menu accelerators** — the
   dialog is dense (Fix, Fix All, Ignore, Ignore All, Never Flag, Go To,
   Previous, Next, Rescan, Close). Ten buttons in one window: expect GATE-14
   collisions and plan for OK/Cancel/Close carrying no mnemonic at all.
10. **F1 help** inline at every construction site, a `surface_help` entry, and a
   regenerated `docs/f1-help-reference.md`. **GATE-SETDOC / GATE-KEYREF** for
   every new setting and chord.
11. **Module size budget** entries — markdown, HTML and grammar rules each want
    their own ceiling rather than one `rules.py` that grows forever.
12. **Performance.** Rules sweep the whole buffer; GATE-PERF's 50 MB synthetic
    document is the ceiling. The scan runs on `QuillTaskManager`, is cancellable,
    and phase 2 introduces a single tokenisation pass the rules read from — a
    regex-per-rule full-document sweep will not survive a large file.
13. **Network egress.** The vision and grammar calls are existing audited call
    sites; confirm no new entry is needed, and that the Ollama route is the
    documented local path.

## 10. Phasing

- **Phase 1 — the merge and the session.** `quill/core/eraser/` with the unified
  `Finding`, the generalised session, GLOW's thirteen rules moved in, Eraser's
  seven kept, spelling joining the list, one dialog, `F4`. **No new rules at
  all.** This is the whole interaction win and it ships on existing detection.
  Lands in **both products in the same commit** (§4.3) — every phase does, and
  the parity gate is written in this phase so no later phase can quietly skip it.
- **Phase 2 — the starred markdown rules and grammar tier 1.** Plus inline
  suppression directives (`<!-- quill-disable md.heading-increment -->`, the
  convention every other linter uses so it is already learned), the tokenisation
  pass, and the performance work.
- **Phase 3 — the magic.** Progressive AI arrival (§7.2), vision-drafted alt text
  (§7.3), speak-the-delta (§7.4), AI triage of rule findings (§7.5), `Alt+Enter`
  (§7.6).
- **Phase 4 — HTML and ARIA in full**, plus grammar tier 2 behind the optional
  POS component, plus the ambient tier: a setting resolved through
  `action_feedback.resolve`, firing only when the caret *enters a line that has a
  finding*, once per line per visit, never on typing, never for `suggestion`
  severity, sound by default because a tone costs a quarter-second and a sentence
  costs three.
- **Phase 5 — beyond the editor.** Folder scans, a report through the existing
  ACR renderer, and `python -m quill.tools.eraser` so the same engine runs in CI.
  Note the recursion: QUILL's own `docs/` tree is a large markdown corpus and
  would be the first real test.

## 11. What this deliberately is not

- **Not a mode.** No "accessibility mode", no "grammar mode". One list.
- **Not AI-dependent.** Every phase works with AI off and in Safe Mode; the AI
  adds findings and judgment, never the interaction.
- **Not a formatter.** It never reflows a document you did not ask it to. Every
  fix is per-finding and undoable.
- **Not a Node or Java toolchain.** Rule IDs are cited, not vendored.
- **Not a score.** No grade, no percentage. A count and a path to zero.

## 12. Open decisions

1. **Next / previous chords.** Both candidates collide (§8). Recommendation: ship
   phase 1 with `F4` and `Shift+F4` only, and settle traversal when the ambient
   tier lands and we know how people actually use it.
2. **Does GLOW's name survive in the editor at all?** The proposal removes
   `Tools ▸ GLOW Audit Document` and keeps `Tools ▸ GLOW Audit File`. That is
   coherent — in-editor checking is Eraser, on-disk document repair is GLOW — but
   it means one product name spans two menus and the `core.glow` experimental
   flag now gates only half of what it used to. Wants a call before phase 1.
3. **Does spelling really join the list, or only appear there?** Recommendation:
   both — `F7` stays a spelling-only session, and the same issues also appear in
   Eraser as the `spelling` family. Costs one filter; avoids taking anything away.
4. **HTML parser.** The stdlib `html.parser` is present, lenient, and gives
   positions; `lxml` is faster and stricter but is a new dependency. The
   well-formedness rules specifically *need* the lenient parser's error recovery
   to report "unclosed tag" usefully. Leaning: stdlib with a position-tracking
   subclass, no new dependency.
5. **Phase 2 rule count.** The starred list is roughly twenty markdown rules plus
   fifteen grammar tier-1 rules — sixty-plus test cases under gate 2. Is that the
   target, or is phase 2 the eight highest-yield ones (skipped heading,
   bold-as-heading, missing alt, filename alt, broken anchor, ragged table,
   unclosed emphasis, their/there)?

## 13. Why this is worth building

Every other product in this space is built for someone who can see the document
and wants a second opinion. This one is built for someone who cannot, and for
whom the defect and the absence of the defect sound exactly alike. Three quarters
of the machinery already exists and is scattered across five commands that each
answer a different quarter of the same question. Putting it behind one key is
mostly deletion — and the thing that comes out the other side, a blind author
getting a usable description drafted for an image they cannot see, in the same
list as their typos, is something nobody else is building.
