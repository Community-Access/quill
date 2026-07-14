# Math in QUILL: plan of record

Status: in progress. Steps 1, 2, 4, 5, and 7 of the build order (section 5)
have shipped (see `docs/superpowers/plans/2026-07-05-math-feature-completion.md`
for steps 4-5's implementation plan). Step 3 (MathCAT speech/braille) is
deferred: MathCAT has no pip-installable Python binding — the only existing
"Python interface" is the GPL v2 NVDA add-on (Python 3.11/wxPython 4.2.2-only,
not reusable), so real integration means QUILL building its own PyO3/maturin
binding against the MIT-licensed `libmathcat` Rust crate and shipping a
compiled native wheel per platform — a native-build-pipeline decision on par
with the existing `table_uia` C++ provider, deferred until that's decided.
Step 6 (DAISY MathML export) is explicitly skipped: `quill/io/daisy.py` is a
DAISY 2.02 *text-only* writer (no OPF/NCX/EPUB3), which has no real MathML
rendering/speech support in any DAISY 2.02 player, so embedding raw `<math>`
there would be inert markup, not real accessibility — equations already
export as readable literal text, which is left as-is until MathCAT (step 3)
can produce real spoken math.

What shipped: Math AutoCorrect-style abbreviations (seeded from the
DAISY-published Word list) in the `math-equations` Quillin's manifest;
`quill/core/math/` (canonical MathML model + a `latex2mathml`-backed LaTeX
bridge, the `math` optional extra, unit-tested); the `math-tutor` AI agent
(`quill/core/ai/agents/math-tutor.md`); the `math-equations` Quillin switched
to MathJax's own default delimiters (`\(...\)` inline, single-line `$$...$$`
display) so browser preview and HTML export render equations with zero
template changes; and `quill/io/docx_math.py`, which splices real `<m:oMath>`
Word equations into the native docx writer via a one-equation Pandoc round
trip (falling back to literal text if Pandoc is unavailable), with regression
tests locking in the (already-correct) docx read-side fidelity via both the
MarkItDown and Pandoc read engines. Written 2026-07-05 from a source-site deep-dive
(online.math.uh.edu/typing-math-in-ms-word/ and everything it links to:
Microsoft's Math AutoCorrect and UnicodeMath/LaTeX linear-format docs, Unicode
Technical Note 28, the DAISY Math AutoCorrect code list, and DAISY's MathCAT
project for NVDA/JAWS math speech and braille) plus a read of QUILL's current
math support.

## 0. Where we actually are today

There is already a bundled Quillin: `quill/quillins_bundled/math-equations/`
(`com.quill.bundled.math-equations`, Ctrl+Shift+E, Insert menu). It prompts for
LaTeX or MathML text and inserts it verbatim, wrapped in `$...$` / `$$...$$`
for LaTeX or raw for MathML starting with `<math`. That is the entire feature.
Its own README already flags the biggest gap: **nothing renders it** — no
MathJax/KaTeX in `browser_preview.py` or `io/export.py`, so a reader sees
literal `$E=mc^2$` text, not a formatted equation. There is also:

- No Math AutoCorrect-style shortcuts (`\alpha` -> `alpha`, `\sqrt` -> a
  radical template) — QUILL already has a general smart-trigger/abbreviation
  dispatch mechanism (see memory: Quillin Insert Automation,
  `=name(args)` triggers + contributed abbreviations) that a math Quillin
  could plug into instead of reinventing input handling.
- No MathML/OMML awareness in `quill/io` (docx equations are OMML —
  `<m:oMath>` — embedded in the WordprocessingML XML; grep of `quill/io` and
  `quill/core` for `oMath`/`OMML`/`MathML` found nothing outside the math
  Quillin itself).
- No math speech/braille integration — QUILL relies on JAWS/NVDA for text
  speech generally, but neither screen reader speaks a literal `$x^2+1$`
  string as math; they need real MathML plus (for NVDA) MathCAT, or Word's
  own equation object plus JAWS Math Viewer. A plain-text QUILL document has
  no way to hand either screen reader real math semantics.

So "bring more magic" is three separable problems, not one:

1. **Fast, ergonomic input** of math as you type.
2. **Faithful storage and round-trip** through QUILL's document model and
   every import/export path (docx, markdown, HTML, PDF read, DAISY, RTF).
3. **Accessible output** — sighted rendering in previews/exports, and actual
   spoken/brailled math for screen reader users, not just "the LaTeX source
   read as English words."

## 1. What the source material actually establishes

Read directly, not from training-data memory, via WebFetch on 2026-07-05:

- **Math AutoCorrect** (Word): a fixed table of `\name` -> Unicode substitution
  codes (`\alpha` -> α, `\sqrt` -> the radical structure, etc.), triggered by
  a following space, editable by the user, and independently listed by DAISY
  at `daisy.org/MSMathCodes`. This is a good, screen-reader-tested UX pattern
  we can copy without needing Word at all.
- **Linear format math** (UnicodeMath and LaTeX): Word can render a typed
  linear string like `x^2/(y+1)` or `\frac{x^2}{y+1}` into a proper equation
  object. UnicodeMath is documented in the open **Unicode Technical Note 28**
  (unicode.org/notes/tn28) — a real, implementable spec, not a proprietary
  black box. LaTeX linear format is just... LaTeX math syntax.
- **Accessibility, concretely**:
  - JAWS reads Word's native equation objects out of the box; it also has a
    dedicated **Math Viewer** (Insert+Spacebar+Equals) for exploring an
    equation structurally.
  - NVDA 2026.1+ ships **MathCAT** built in; earlier versions need the MathCAT
    add-on. MathCAT's job: take **MathML** in, produce speech strings (in
    multiple languages, with configurable verbosity/engine commands),
    **braille** (Nemeth, UEB Technical, CMU, and other math braille codes),
    and structural navigation (Nvda+Alt+M) commands.
  - **MathCAT is MIT-licensed, fully offline, and has a published Rust crate,
    a Python interface, and a C/C++ FFI** (confirmed via WebFetch against the
    MathCAT repo/docs, not assumed). That is the single most important fact
    in this whole investigation: **QUILL can embed the same math-speech/braille
    engine NVDA uses, directly in-process, without depending on which screen
    reader the user runs.**
  - Word's linear-format LaTeX is a documented but Microsoft-flavored subset;
    real interop for import/export is better served by full LaTeX-math
    parsing (there's a large existing ecosystem: `pylatexenc`, `latex2mathml`,
    `sympy`) than by trying to clone Word's exact grammar.

## 2. The magic worth building, ranked

Ranked by (accessibility impact for a screen-reader-first product) x
(feasibility without wx doing anything exotic) x (how much reuses stuff QUILL
already has).

### Tier 1 — do this first, highest leverage

**A. Math AutoCorrect-equivalent smart triggers.**
Ship a table of `\alpha`, `\sqrt`, `\frac`, `\sum`, `\int`, `\ge`, `\to`, …
(seed from the DAISY-published Word list, which is itself derived from Word's
built-in table, so shortcuts are muscle-memory compatible with anyone coming
from Word) as contributed abbreviations/smart triggers in the existing insert
automation system. Typing `\alpha ` mid-sentence becomes `α`; typing
`\sqrt(x)` becomes a linear-format square root the user can later upgrade to a
full equation. Almost zero new architecture — this is exactly what the smart
trigger dispatch was built for. Biggest bang for the least risk.

**B. A real MathML data model + MathCAT-powered speech/braille, decoupled
from any screen reader.**
This is the actual "magic": embed MathCAT (Python interface, offline, MIT) in
`quill/core` behind a small `quill/core/math/` package:
- `mathml.py` — canonical in-memory representation is MathML (the same
  input MathCAT and every screen reader math engine already expects).
- `latex_bridge.py` — LaTeX <-> MathML conversion using an existing, mature
  library (evaluate `latex2mathml` first: pure Python, no native build, MIT-
  license family; fall back to `pylatexenc` + a small MathML serializer if
  coverage is thin). This is what turns `\frac{x}{y}` typed inline into a
  structure MathCAT can speak.
- `speech.py` — thin wrapper around the MathCAT Python bindings:
  `mathml_to_speech(mathml, *, language, braille_code) -> str`. Exposed to
  the UI as "Speak this equation" / "Describe this equation" — works
  identically whether the user runs JAWS, NVDA, VoiceOver, or nothing at all,
  because QUILL is doing the math-to-speech conversion itself and handing
  Prism a plain string to announce. **This is the feature the source article
  doesn't have an equivalent for anywhere else** — Word depends entirely on
  which AT you happen to run; QUILL would not.
- Braille: MathCAT's Nemeth/UEB-Technical output feeds QUILL's existing
  braille pipeline (liblouis pack, per Build Tools memory) for a literal
  braille math display, independent of JAWS/NVDA braille support too.

**C. Fix the rendering gap the existing Quillin already flagged.**
Add MathJax (or KaTeX — smaller, faster, no MathML output mode complexity;
MathJax has better MathML fidelity which matters more here since MathML is
our canonical form) to `browser_preview.py`'s HTML template and `io/export.py`
HTML export, gated the same way other optional web content is (local
vendored copy, no CDN fetch — check `network_egress_audit.py`, since a CDN
`<script src>` is a new outbound call site and would need an audit entry and
explicit consent per this repo's own network-egress rule). Sighted users get
real rendered equations in preview/export; screen reader users are unaffected
either way since they get MathCAT speech instead of DOM/AT interrogation of
the rendered math.

### Tier 2 — real magic, more surface area

**D. docx OMML round-trip.** Word's native equations are OMML
(`<m:oMath>`), not MathML or LaTeX. Pandoc already converts OMML <-> its own
internal math AST <-> LaTeX-ish delimited math in Markdown/HTML output — this
means **QUILL may already get most of docx-equation-to-editable-text for
free** through the existing `quill/io/pandoc.py` bridge, since Pandoc is
already a Tier-1 dependency for doc conversion. Verify empirically (round-
trip a docx with a native Word equation through
`convert_document_with_pandoc(..., to="gfm")` and see what the math renders
as) before writing any bespoke OMML parser. If Pandoc's math fidelity is good
enough, the OMML problem is a non-problem — just wire the existing bridge
into the docx open/save path for equation-bearing runs, rather than adding a
new format layer to `quill/io`.

**E. Ink/handwriting equation entry.** Out of scope for a screen-reader-first
product — this is a sighted-only Word feature (draw with mouse/stylus,
convert to math) with no accessible analogue. Skip; note why in the plan so
it isn't re-proposed later.

**F. AI-assisted math.** QUILL already has an agent catalog
(`quill/core/ai/agents/*.md`) and free-model infrastructure. A `math-tutor`
or `equation-explainer` agent (`default_scope: selection`, low risk, no
document mutation — pure explanation) could take a selected equation
(LaTeX/MathML) and produce a plain-language walkthrough, which is itself an
accessibility win independent of MathCAT (MathCAT describes structure; an AI
agent can explain meaning/derivation on request). Cheap to add once (B) gives
us a canonical MathML/LaTeX equation to hand the agent. Must stay read-only
(`modify_document: deny` or `ask`) per the agent standards linter's rule that
mutating permissions can never be `allow`.

**G. Cross-format export fidelity.** Once MathML is the canonical in-memory
form: DAISY export (`quill/io/daisy.py`) can emit real MathML (DAISY/EPUB3
supports MathML natively — this directly serves QUILL's existing DAISY
Talking Book export, issue #251), RTF math is genuinely hard (RTF has no good
math object model) and should probably degrade to the linear LaTeX/UnicodeMath
text form rather than trying to fake an OMML-in-RTF equivalent.

### Explicitly out of scope

- Reimplementing Word's Equation Editor UI (visual structure-building
  toolbox with fraction/radical/matrix templates drawn as nested boxes) is a
  multi-month wx custom-control project for marginal benefit over typed
  LaTeX/UnicodeMath + AutoCorrect-style shortcuts. Revisit only if user
  testing says typed math input isn't enough.
- Ink equations (see D above).
- Building a math-speech engine from scratch. MathCAT already exists, is
  MIT-licensed, and is the literal engine NVDA itself ships — there is no
  version of "build our own" that beats "embed the real thing."

## 3. Should this be a Quillin?

Split it — this is not an all-or-nothing question:

- **Input ergonomics (Tier 1-A, smart triggers/abbreviations) and the caret-
  level insert command (already-existing `math-equations` Quillin) stay a
  Quillin.** That is exactly what the Quillin capability model
  (`ui.prompt`, `editor.write`, `ui.command`) is for, it is already built,
  and it needs no core changes.
- **The MathML data model, LaTeX<->MathML bridge, and MathCAT speech/braille
  engine (Tier 1-B) must live in `quill/core/math/`, not in a Quillin.**
  Quillins are sandboxed extensions with a narrow capability surface
  (`ui.*`, `editor.read/write`, no arbitrary native library loading per the
  extension schema/manifest model); embedding a compiled MathCAT binding and
  wiring it into the braille pipeline and Prism announcements is core
  platform work, same tier as `quill/platform/windows/prism_bridge.py` or
  `quill/stability`. The Quillin then becomes a thin UI layer that calls
  `quill.core.math` the same way the Table/CSV Studio's UIA provider is core
  and its menu commands are thin.
- **Rendering (Tier 1-C) is a core change** to `browser_preview.py` and
  `io/export.py`, not something a Quillin's capability model can reach.
- **docx OMML (Tier 2-D)** is core (`quill/io`), reusing the existing
  `quill/io/pandoc.py` bridge.
- **The AI agent (Tier 2-F)** is a plain `.md` agent file, no code at all.

So the honest shape of "is this a Quillin": no, it's a small **core module**
(`quill/core/math/`) with a **Quillin as its keyboard-facing front door**,
exactly mirroring how Table/CSV Studio has a native C++ UIA provider (core)
plus command surface (thin), or how the insert-automation smart-trigger
system is core infrastructure that the `insert-character` and
`math-equations` Quillins merely call into.

## 4. Cross-platform reality check

- **MathCAT**: Rust crate + Python bindings, MIT, offline — builds on
  Windows/macOS/Linux equally. No platform lock-in. This is what makes the
  "cross-platform" ask real instead of aspirational: MathCAT is precisely
  the mechanism that makes math speech NOT depend on JAWS (Windows-only) or
  NVDA (Windows-only) — it works the same in-process on macOS too, where
  QUILL currently has no equivalent to Prism's Windows screen-reader bridge
  for math specifically.
- **LaTeX/MathML conversion libraries** (`latex2mathml`, `pylatexenc`) are
  pure-Python or have wheels for all three platforms already.
- **MathJax** (Tier 1-C) is pure JS running inside whatever the preview
  renders in — already platform-agnostic since `browser_preview.py` opens a
  system/chosen browser.
- **Pandoc** (Tier 2-D) is already a cross-platform external tool dependency
  QUILL depends on.
- Net: everything in Tier 1 and most of Tier 2 is naturally cross-platform.
  The only inherently Windows-flavored piece anywhere in this plan is JAWS's
  Math Viewer, which QUILL doesn't need to touch at all — MathCAT
  speech/braille sidesteps it entirely.

## 5. Suggested build order (small, reviewable PRs)

1. **Smart-trigger math shortcuts** (Tier 1-A). Pure data + reuse of existing
   dispatch. Smallest possible PR, immediate daily-use value.
2. **`quill/core/math/` MathML + LaTeX bridge**, unit-tested in isolation
   (no MathCAT yet, no UI) — get the data model and LaTeX<->MathML conversion
   right first, since everything else depends on it.
3. **MathCAT integration** behind `quill/core/math/speech.py` + a "Speak
   equation" / "Describe equation" command wired through the existing
   `math-equations` Quillin (add a second contributed command, don't fork a
   new Quillin). Validate on real JAWS/NVDA per this repo's screen-reader
   test-plan convention, since this is exactly the kind of feature that needs
   ears on it, not just tests passing (see project memory: no UI automation
   substitutes for a live screen-reader check).
4. **MathJax rendering** in preview/export (Tier 1-C) — needs a
   `network_egress_audit.py` entry if any remote fetch is involved; prefer
   vendoring the MathJax bundle to avoid that entirely.
5. **Verify Pandoc's existing OMML fidelity empirically**, then wire docx
   equation round-trip (Tier 2-D) only if the built-in fidelity check shows
   it's worth a dedicated code path.
6. **DAISY MathML export** (Tier 2-G), since the DAISY writer already exists
   and this is a small addition once (2) produces canonical MathML.
7. **`math-tutor` AI agent** (Tier 2-F) — a Markdown file, whenever wanted;
   no dependency ordering on the rest.

Steps 1 and 7 can ship independently of everything else and of each other.
Steps 2-6 are a dependency chain (3 needs 2, 4 benefits from 2 but doesn't
strictly need it, 5 and 6 both need 2).

## 6. Open questions for whoever picks this up

- Confirm MathCAT's Python binding packaging story (PyPI wheel vs.
  build-from-source via the Rust crate) before committing to step 3 — the
  WebFetch research confirmed bindings exist but not their exact
  distribution mechanism; check the MathCAT repo's `INSTALL`/CI config
  directly when this step starts.
- Pick `latex2mathml` vs. `pylatexenc`-plus-serializer for the LaTeX bridge
  by running both against a representative equation corpus (fractions,
  sums/integrals with limits, matrices, nested scripts) and comparing MathML
  output quality — don't guess, benchmark at step 2.
- Decide MathJax vs. KaTeX for step 4 by checking actual MathML-output
  fidelity needed for round-tripping rendered equations, since QUILL's
  canonical form is MathML, not the rendering library's native format.
