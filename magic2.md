# magic2.md — what the new EdSharp has to teach QUILL

Written 2026-08-26, from EdSharp 5.0 (upstream at
[github.com/JamalMazrui/EdSharp](https://github.com/JamalMazrui/EdSharp), last
pushed the same day) and the working copy at `C:\code\edsharp`.

*The support and Community Picks working notes stay where they were, in
[magic.md](magic.md). Nothing here displaces them.*

**Why this is worth an afternoon.** EdSharp is a text editor written by a blind
developer for blind users, maintained since 2007, and it has just been rebuilt.
Its feature set is thirty years of accumulated answers to "what does somebody
working entirely by ear actually need?" — and version 5.0 re-answers several of
them with things that were not practical to build before.

**The honest baseline.** QUILL has read EdSharp before. `EDS-1` through `EDS-22`
are ported already — the clipboard collector, set operations, regex
count/extract, go-to-percent, non-blank navigation, Key Describer, indent
inference, delete-to-bounds, run file, rename/delete on disk, the HTML and
line-level transforms. `menu_lint.py` even carries a `# §edsharp-ok` escape
hatch from that port. So this document is deliberately **not** a feature list
from the user guide. It is about what 5.0 changed, and about how EdSharp is
*built*, which turns out to be the more transferable half.

---

## The one idea I would take first

**Speak only what the screen reader does not already say.**

From EdSharp's own announcement of 5.0:

> EdSharp now leaves window titles and focus changes to your screen reader,
> which announces them anyway, and speaks only what it alone knows.

This is a regression that was found and fixed, not a design that was obvious.
An app with a direct speech channel to JAWS and NVDA acquires a standing
temptation to narrate, and every narration it adds that the reader was going to
make anyway is a sentence the user must sit through — on every occurrence,
forever.

QUILL has a gate for the opposite failure. `check_announce_gap.py` (GATE-12)
flags a dialog that updates a status label without announcing it — under-
announcing. **There is no gate, and as far as I can find no written rule, for
over-announcing.** That asymmetry is worth closing, because the two mistakes
are not equally visible: a missing announcement is reported as a bug by the
person who needed it, while a duplicated one is absorbed as "this app is
chatty" and never filed.

What that could look like in QUILL, in rising order of cost:

1. **Write the rule down** in `CLAUDE.md` beside the menu-accelerator rule,
   with the list of things the screen reader already announces and the app
   therefore must not: window and dialog titles, focus moves, control names,
   roles and states, selection changes in a list, and the text of a control
   that just received focus.
2. **A gate**, in the shape of the existing ones: flag an `_announce(` whose
   argument is a control's own label or accessible name, or that fires in an
   `EVT_SET_FOCUS` handler, or that repeats a dialog title. Each of those is a
   mechanical pattern, and each is a real way to say something twice.
3. **A verbosity setting** is *not* the answer and should be resisted. It moves
   a decision we are better placed to make onto somebody who has to discover
   the setting exists.

---

## Take now: five things that are cheap and clearly right

### 1. Announce through UIA, not only through a per-reader bridge

`Say.cs` dispatches JAWS COM, then the NVDA controller client, then a **native
UIA notification** — and stops at the first that answers, so a message is never
delivered twice. The third leg is the interesting one: it raises
`UiaRaiseNotificationEvent` against a one-pixel invisible control that owns a
real window handle and answers `WM_GETOBJECT` with a minimal
`IRawElementProviderSimple`. Because the screen reader sees a legitimate UIA
element, the notification reaches **JAWS, NVDA and Narrator alike**, with no
per-reader library at all.

QUILL announces through Prism, falling back to `accessible_output2`
(`quill/platform/windows/prism_bridge.py`). Both are COM bridges to specific
readers. Adding a UIA notification leg would buy three things: **Narrator
support**, which QUILL does not have today by this route; a path that survives
a reader QUILL has no bridge for; and one fewer bundled dependency in the long
run.

The "stops at the first that answers" rule matters as much as the mechanism,
and QUILL's fallback chain should be audited against it — the memory of the
Reveal Codes single-speaker fix says QUILL has met this problem once already,
in one place.

### 2. Generate the keybinding reference from the keymap

EdSharp generates `Hotkeys.md` from the description table inside `EdSharp.cs`,
which is *also* what Key Describer and the alternate menu read. One table, three
consumers, and the documentation cannot drift because it is not written by hand.

QUILL's `docs/.../keybinding-standard.md` is hand-maintained;
`menu_lint.py` references it as prose to justify `Ctrl+Alt+` bindings rather
than generating from it. `DEFAULT_KEYMAP` and `APP_KEYMAPS` already exist as the
single source of truth for what is *bound*. Generating the reference from them
would make one more document unable to lie.

### 3. Add the audit checks QUILL is missing

`auditEdSharp.py` runs fifteen checks before the compiler does, and its
description of them is the best sentence in the project: *"Each check exists
because something once broke."* QUILL has forty-four such tools and the same
culture. Three of EdSharp's fifteen have no QUILL equivalent I can find:

- **`checkAccessKeysUnique`** — every dialog's buttons have distinct access
  keys, with OK and Cancel deliberately having *none*, since Control+Enter and
  Escape serve them. QUILL's `dialog_button_contract.py` checks the Close/Cancel
  binding but not ampersand collisions. Two buttons sharing an access key means
  one of them cannot be reached that way, and nothing announces the loss.
- **`checkCommandsDescribed`** — every command has a description, *and each
  description names the key the code actually binds*. QUILL's
  `_check_binding_label_consistency.py` does this for menu labels; the
  description surface that Key Describer reads is a different table.
- **`checkOptionsDocumented`** — every setting appears in the documentation.
  QUILL has `check_help_coverage.py` for topics, and a settings schema, but I
  found nothing tying the two together. An undocumented setting is one nobody
  can find.

### 4. Dialogs that can describe themselves

`Lbc.cs` — "Layout by Code" — builds dialogs by adding labelled fields in
order rather than through a visual designer, *so that reading order, tab order
and visual order are the same by construction rather than by review*. Every
dialog it builds gets three things free: Control+Enter to accept, Escape to
cancel, and **F1 to describe its fields**.

QUILL has the first two through `dialog_contract` and `apply_modal_ids`, and it
has F1 context help through `topics.json`. What it does not appear to have is
F1 answering *about the field the cursor is in*. That is the difference between
"here is a page about this dialog" and "this box wants a number of minutes,
default thirty" — and the second is what somebody stuck in a field actually
needs.

### 5. Steal the certification habit, not just the gates

From the transition brief, on repository hygiene: *"Certify by PROOF, not
assertion. 'Untracked and left alone' must mean 'and gitignored', verified with
`git check-ignore` over every such path."* And: *"An installer pattern proves a
tracked file is ALLOWED. It never proves an absent file is WANTED."*

QUILL's gates are already proof-shaped. The habit worth importing is applying
the same standard to claims *about the repository* rather than only about the
code — which is exactly the class of thing that let a bundled token, a stale
`.epub`, and an unreachable dialog each ship at some point in this project's
history.

---

## Worth deciding, not worth doing on my own say-so

### Compiler profiles as data

In EdSharp a compiler is a config section, and one choice — Control+Shift+F5 —
brings the run command, the pattern that locates an error, the output to
abbreviate out of the speech, the comment prefix, the default extension, **the
indentation the language uses**, and the interactive shell to open. *"Adding a
compiler needs no code."*

The tutorial explains why this matters and it is not really about compilers:

> Python is the language EdSharp supports most fully, because Python's
> whitespace is the hardest thing about writing code with a screen reader.

QUILL has `external_engine.py` with a deliberately narrow executable allowlist,
which is a security boundary rather than a profile system. Whether QUILL wants
to be a coding editor at all is a product question — but if it does, this is the
right shape, and the "your own indentation still wins; the setting governs only
a file with no indentation yet" rule is worth copying exactly.

### Local AI framed as privacy rather than as a feature

EdSharp 5.0 runs translation between eighteen languages, summarising, and code
assistance on the user's own machine: *"no account, no limit, and nothing sent
anywhere."* The installer offers each model as a checkbox **stating what it does
and how large it is**, and fetches it automatically.

QUILL already has Ollama support and a settled rule that local speech engines
must run torch-free. What is worth taking is the **framing and the packaging**:
optional, honest about size, installed without a manual download, and sold on
privacy rather than on capability. Several gigabytes is a real cost and saying
so plainly is what makes it a fair offer.

### Tutorials organised by who you are

Twelve tutorials, named for people rather than features: Python Developer, NVDA
Add-on Developer, Language Translator, Journal Article Author, Slide Presenter,
Web Researcher, Batch Conversion Operator. *"Read the one that matches what you
are doing; they do not depend on each other."*

QUILL's eleven tutorials are numbered and partly task-shaped already
("Rescue a scanned PDF", "Document to audiobook"), which is most of the way
there. The remaining idea is the *independence* — no ordering, no prerequisites,
each naming the settings worth changing and the keys worth learning up front.

---

## Deliberately not

- **Hungarian notation.** EdSharp's "Camel Type" puts a type prefix on every
  name, and the justification is genuinely interesting: *"The style optimizes
  for hearing code rather than seeing it: a prefix tells you the type as the
  name is spoken."* For a C# codebase with no type hints in the signature line,
  that is a real gain. QUILL is typed Python where `mypy` is a gate and the type
  is already in the declaration; adding prefixes would be redundancy a reader
  hears on every name.

  The *principle* underneath does transfer, and QUILL should hold it
  consciously: **source is read by ear here too.** That argues for the one-line
  condition over the three-line one, for names that disambiguate early rather
  than late, and against decorative comment banners that cost a line of speech
  each.

- **One enormous source file.** EdSharp's `EdSharp.cs` is 557 KB and its author
  defends it: *"its author navigates by search and by structure rather than by
  file, and splitting it would cost more than it saved."* That is an honest
  statement of a personal working style, and QUILL has the opposite constraint
  written into a ratchet — GATE-11, which caught me growing `main_frame.py` by
  two lines only this afternoon. `main_frame.py` is 19,565 lines and the budget
  exists precisely because it got that way. Keep the ratchet.

- **A speech verbosity setting.** See above. The right answer is to say less,
  not to make the user configure how much less.

---

## What QUILL already does better

Worth recording, both for fairness and because these are the things not to
trade away while borrowing:

- **Gates as a ratchet, not just a checklist.** EdSharp's audit runs fifteen
  checks; QUILL runs forty-four, and the module-size budget only ever
  *decreases*. A check that can be satisfied by raising its own threshold is a
  check that will be.
- **Error codes.** Every custom exception in `core`, `io` and `stability`
  carries a unique `QUILL-<DOMAIN>-<SUBSYSTEM>-<REASON>`, enforced by
  `error_code_audit.py`. EdSharp has nothing equivalent, and its transition
  brief describes a day lost to a startup failure that "dies in perfect
  silence".
- **Surface reachability.** GATE-REACH exists because a first-run dialog shipped
  unreachable for two releases with passing tests. EdSharp's audit checks that
  scripts named in config exist, which is the same instinct one step less far.
- **Atomic writes and a crash reporter with fingerprint deduplication.**
- **Signed artifacts** — although see `magic.md`, where the signer was writing
  a sidecar its own verifier could not read until today.

---

## Two process lessons I would put on the wall

From the transition brief, both earned the hard way:

> **"It used to work" plus "it compiles" proves nothing about running.** An
> assembly-name collision and a wrong-version library both compile clean and
> both kill at startup. Test a LAUNCH after build changes, not just the build.

QUILL has `/run` and a smoke suite; the point is the discipline of using them
after *build* changes specifically, which is when the tests are least likely to
notice.

> **Diagnose with instruments that do not depend on the patient.** *"The error
> dialog can share the disease: if its own types depend on the broken library,
> the program that would explain the failure is the failure."*

QUILL's crash reporter lives inside QUILL and submits through code QUILL loads.
Worth checking that the diagnostic path degrades to something that works when
the thing it is diagnosing does not.

---

## Suggested order

Cheap and certain first.

1. Write the **speak-only-what-it-alone-knows** rule into `CLAUDE.md`, then
   build the gate for it. Biggest daily benefit, smallest change.
2. Add **`checkAccessKeysUnique`** as a QUILL gate — a genuine accessibility
   defect class with no current coverage.
3. **Generate the keybinding reference** from `DEFAULT_KEYMAP` / `APP_KEYMAPS`.
4. Add the **UIA notification leg** to the announcement chain, and audit the
   chain for first-answer-wins. This one needs care and real testing with
   JAWS, NVDA and Narrator.
5. **Field-level F1** in dialogs, starting with the dialogs that have numeric or
   format-sensitive fields where the answer is least guessable.
6. Decide the two product questions: **compiler profiles** (is QUILL a coding
   editor?) and **local AI packaging** (does QUILL offer models by checkbox with
   honest sizes?).

Nothing here is blocked on anybody else, and none of it touches the support work
in [magic.md](magic.md).
