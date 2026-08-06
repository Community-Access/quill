# Section — Tools: AI writing & analysis (`tools.*`, AI subset)

The **AI writing and analysis** tools: the conversation front door (Ask Quill),
document-scoped repairs (Improve Reading Order, Accessibility Tune-Up),
proofreading (grammar, style, spell check), single-shot transforms (expand,
generate table of contents, translate, thesaurus), the configuration surfaces
(AI Hub, AI Model, AI Connection, Switch Engine, AI Library, Session Branches),
and the vision tool (Describe Image). Finish **Part 0** first.

This section covers **only** the AI writing/analysis commands. The other two
`tools.*` sub-sections cover **speech/OCR/read-aloud** (`section-tools-speech.md`)
and **compare/keymap/macros/utilities** (`section-tools-misc.md`). Do not test
speech, transcription, or plain OCR here.

Surface reference (label + shortcut + gate) is
`../../planning/signoff/SIGNOFF-editor.md` → `tools.*`. Read §2–§3 of `README.md`
for the scenario layout and the Pass/Fail/Blocked/N-A +
Works/Surface-exact/Accessible boxes. Menu paths below are the **live** AI menu as
built by the app; where the SIGNOFF label and the on-screen menu label differ
(for example, SIGNOFF `Ask Quill Chat` appears in the menu as **Ask Quill…**),
the header prints the SIGNOFF command id and the **Do this** step prints the menu
label you will actually hear — flag any mismatch under **Surface-exact**.

Common inputs used below (copy the `../qa-samples/` folder onto the machine
first): `reading-order.txt` (the out-of-order tea recipe), `formatting.md`,
`plain.txt`.

## Before you start (read once — applies to every scenario here)

- **AI must be configured.** Every command in this section needs a working AI
  **provider** — either a **local** engine (for example an on-device model, no
  key) or a **cloud** provider with an API key. Set one up in **TAI-01 / TAI-02**
  *before* running the rest. If **no provider is configured and the Set Up AI
  wizard cannot be completed** on the test machine, mark the affected scenario
  **Blocked** and say so — a feature that only routes you to "Set Up AI" is not a
  failure of that feature.
- **AI is OFF in Safe Mode.** If QUILL was launched with `--safe-mode` (or
  `QUILL_SAFE_MODE=1`), every AI feature is disabled and must say so plainly and
  send nothing. Run this section in a **normal** build; a separate Safe-Mode pass
  (see `../qa-core-journeys.md` JOURNEY-005 TC-005d) confirms the refusal.
- **Confirmation before anything is sent.** No AI feature may transmit your
  document without consent. That consent takes two forms in QUILL, both of which
  you must observe: (a) a **standing per-provider share consent** granted once in
  the Set Up AI wizard — a feature routes you back to setup if it is missing; and
  (b) for **Improve Reading Order**, an additional **per-run** confirmation that
  names the provider/host and the approximate size before it sends (TAI-07). If a
  feature ever sends the whole document to a remote host with neither consent in
  place, that is a release-blocking failure.
- **Results open as a NEW, unsaved document where the feature reflows or
  generates whole-document text** (Improve Reading Order; the "open in a new
  document" option of Translate). Proofreading and transform tools instead show a
  review/correction dialog you apply into the current document. Each scenario
  states which behaviour to expect — hold it to that.
- **[GATED future.ai].** Scenarios tagged **[GATED future.ai]** are behind the
  `future.ai` feature flag and are **absent from a public 1.0 build**. On a public
  build mark them **N/A** (do not fail them for being missing); only run them on a
  dev/admin build where the flag is on.

---

## TAI-01 — AI Connection (`tools.ai_connection`)

*What & why.* The provider/connection settings dialog — where a cloud provider,
host, model, and API key are entered and verified. This is the plumbing that every
other scenario depends on, so run it first.

**Before you start**
- QUILL open, any document. Have your provider details ready (or a local engine
  installed).

**Do this**
1. Open the **Command Palette** (Tools ▸ Command Palette, or its shortcut) and run
   **AI Connection** — the surface is also reached from **AI Model** (TAI-03) via
   its connection button.
2. Tab through the fields (provider, host, model, key); enter your provider;
   activate **Verify**/**Test** if offered; confirm with **OK**.

**You should see and hear**
- Every field is labelled and keyboard-complete. On confirm QUILL announces the
  outcome in substance — "Updated AI connection settings. Ready." on a good
  connection, or "…Needs attention." with a plain-language reason if verification
  failed. **Escape** cancels with "AI connection settings cancelled" and changes
  nothing. The API key is stored in the platform secret store (Credential Manager /
  DPAPI), never echoed or written in plain text.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TAI-02 — AI Hub (`tools.ai_hub`)

*What & why.* The single configuration front door: engines, provider keys, session
branches, and services (OCR/Datalab) all live here on tabs. The friendlier way to
do what TAI-01 does, plus engine and session management.

**Before you start**
- QUILL open, any document.

**Do this**
1. **AI menu (Alt, A) ▸ AI Hub…**.
2. Tab across the tabs (Engines, Sessions, Services, …); read the controls; make
   no change; close with **Escape** or the Close button.

**You should see and hear**
- The Hub opens as a keyboard-navigable, announced dialog; tabs and their controls
  are labelled and reachable by keyboard alone. Closing returns focus to the
  editor. Any Services (OCR/Datalab) values you save take effect without a restart.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TAI-03 — AI Model (`tools.ai_model`)

*What & why.* The combined **AI Model & Connection** dialog — pick the model and
jump to the connection settings from one place.

**Before you start**
- A provider configured (TAI-01/02).

**Do this**
1. Run **AI Model** from the Command Palette.
2. Read the model control; use the button that opens **Connection** settings to
   confirm it reaches the TAI-01 dialog; close.

**You should see and hear**
- The model dialog is labelled and keyboard-operable; its connection button opens
  the AI Connection dialog and returns cleanly. Selecting a model is announced.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TAI-04 — Switch AI Engine (`tools.ai_switch_engine`, Ctrl+Alt+Shift+E)

*What & why.* Round-robin to the next available AI engine without opening a dialog —
the power-user quick switch, mirrored on the status bar.

**Before you start**
- AI on, with at least one engine available (ideally two, so the round-robin has
  somewhere to go).

**Do this**
1. Press **Ctrl+Alt+Shift+E**.

**You should see and hear**
- QUILL announces the engine it switched to (in substance "Switched to <engine>");
  the status bar's AI cell updates to match. With AI off it says AI is turned off
  rather than switching silently. With only one engine it reports there is nothing
  to switch to rather than erroring.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TAI-05 — Ask Quill Chat (`tools.ask_quill_chat`, Alt+Q)

*What & why.* The conversation front door — ask questions, request edits, and let
QUILL act on the current document through its tool catalog. The everyday "talk to
the assistant."

**Before you start**
- A provider configured **and** its share consent granted in Set Up AI. Open
  `formatting.md` so there is a document to ask about.

**Do this**
1. Press **Alt+Q**, or **AI menu ▸ Ask Quill…**.
2. Type a question in the composer (for example "How many headings does this
   document have?") and send it.

**You should see and hear**
- The chat opens as a keyboard-navigable, announced dialog with a labelled composer
  and a readable transcript. If AI is off, not configured, or the provider has **no
  standing share consent**, QUILL routes you to **Set Up AI** first rather than
  sending anything. Sent, the answer appears in the transcript and is announced;
  any change it proposes to your document goes through a review step, not a silent
  edit. Re-invoking while it is open just brings the existing chat forward.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TAI-06 — Ask Quill: Voice Conversation (`tools.ask_quill_conversation`)

*What & why.* The same chat, but spoken: answers can play aloud with transport
controls and a spoken question can be captured — falling back to text plus
screen-reader announcements when voice I/O is unavailable.

**Before you start**
- Provider configured and consented (as TAI-05). Text-to-speech available for the
  spoken-answer path; if not, the text fallback still applies.

**Do this**
1. **AI menu ▸ Ask Quill by Voice…** (or run **Ask Quill: Voice Conversation** from
   the Command Palette).
2. Send a question; if TTS is available, use the transport controls on the spoken
   answer.

**You should see and hear**
- The dialog opens exactly like TAI-05 with voice mode on; the same setup/consent
  routing applies. With TTS available the answer plays with keyboard-operable
  transport; without it, the answer is shown as text and announced — never a silent
  dead end. **Note:** if no TTS engine is present, confirm the fallback is spoken by
  the screen reader, not merely displayed.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TAI-07 — Improve Reading Order (`tools.ai_reading_order`)

*What & why.* Send the whole document to your provider to repair a jumbled reading
order (columns, sidebars, out-of-sequence lines) and open the reflowed result as a
**new, unsaved** document — never touching the original. This is the flagship
confirm-before-send flow; it mirrors `../qa-core-journeys.md` **JOURNEY-005**.

**Before you start**
- Provider configured; **not** Safe Mode. Open **`reading-order.txt`** (a four-step
  tea recipe printed out of order, one step broken across a mid-sentence line
  break; the file records the intended order for you to check against). Do **not**
  send the tester's note block to the AI.

**Do this**
1. **AI menu ▸ More ▸ Improve Reading Order…**.
2. Read the confirmation dialog. First choose **No** (default) to prove it cancels;
   then re-invoke and choose **Yes**.

**You should see and hear**
- **Before anything is sent**, a confirmation names the provider and approximate
  size, in substance: "QUILL will send this document — about 1 page — to
  <provider>(host) to repair its reading order… The result opens as a new, unsaved
  document; your current document is not changed… Send the document now?" Default is
  **No**; choosing No announces **"Improve Reading Order cancelled — nothing was
  sent."**
- On **Yes**: a progress status speaks ("Improving reading order… this can take a
  moment."); on success a **new, unsaved** document opens, announced "Reading order
  improved — opened as a new unsaved document (Save As to keep it)." The four steps
  read **First → Second → Third → Fourth**, the broken "Third … steep …" step is
  rejoined into one sentence, wording is unchanged, and the original
  `reading-order.txt` is untouched on disk and in its tab.
- **Guards:** in Safe Mode it says "Improve Reading Order is unavailable in Safe
  Mode" and sends nothing; a document over the page limit is refused with the
  over-limit message and sends nothing.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TAI-08 — Check Grammar with AI (`tools.check_grammar_ai`)

*What & why.* A quick, read-only grammar pass over the selection (or the whole
document) using the built-in grammar prompt, shown in a result dialog.

**Before you start**
- Provider configured. Open `plain.txt`; optionally select a paragraph (with no
  selection the whole document is used).

**Do this**
1. **AI menu ▸ Proofread ▸ Check Grammar with AI…**.

**You should see and hear**
- QUILL announces "Checking grammar with <model>…"; on completion a **read-only**
  result dialog presents the AI's grammar notes, announced and keyboard-navigable.
  With nothing to check it says "No text to check grammar for." If AI is not
  configured it routes to setup rather than failing silently. **Note:** this
  variant reports findings; it does not auto-apply edits (contrast TAI-10/TAI-11).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TAI-09 — AI Grammar and Style Check (`tools.ai_grammar_style`, Ctrl+Alt+Shift+G)

*What & why.* A structured grammar-and-style review of the whole document that you
step through and apply issue by issue.

**Before you start**
- Provider configured. Open `plain.txt` (or any prose document).

**Do this**
1. Press **Ctrl+Alt+Shift+G**, or **AI menu ▸ Proofread ▸ Grammar and Style
   Check…**.
2. Walk the issues; accept some fixes; confirm/close.

**You should see and hear**
- QUILL announces "AI grammar check running…"; if none are found it says "AI grammar
  check: no issues found." Otherwise a keyboard-navigable issues dialog opens; the
  fixes you accept are applied into the **current document** and QUILL announces the
  count ("AI grammar check: N fix(es) applied"); accepting none says so. An empty
  document is reported, not sent.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TAI-10 — AI Spell Check (`tools.ai_spell_check`, Ctrl+Alt+Shift+S)

*What & why.* A whole-document AI spelling pass presented as a batch of corrections
to review and apply.

**Before you start**
- Provider configured. Open `plain.txt`; optionally type an obvious misspelling so
  there is something to catch.

**Do this**
1. Press **Ctrl+Alt+Shift+S**, or **AI menu ▸ Proofread ▸ Spell Check…**.
2. Review the corrections; apply; confirm.

**You should see and hear**
- QUILL announces "AI spell check running…"; with no issues it says "AI spell check:
  no issues found." Otherwise a corrections dialog opens (labelled, keyboard-
  navigable); applying updates the document and announces "AI spell check: N
  correction(s) applied"; applying none says so. An empty document is reported.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TAI-11 — AI Spell Check Interactive (`tools.ai_spell_check_interactive`, Ctrl+Alt+Shift+I)

*What & why.* The same spell check, but paragraph by paragraph — you accept or
reject each correction as you go, instead of one batch.

**Before you start**
- Provider configured. Open a multi-paragraph document (e.g. `plain.txt`, three
  paragraphs).

**Do this**
1. Press **Ctrl+Alt+Shift+I**, or **AI menu ▸ Proofread ▸ Spell Check
   Interactive…**.
2. Step through each paragraph; accept some corrections and skip others; finish.

**You should see and hear**
- An interactive dialog walks the paragraphs; each proposed correction is announced
  with context and is accept/skip by keyboard. Accepted corrections are applied into
  the current document and the running count is announced. Reaching the end closes
  cleanly; an empty document is reported rather than sent.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TAI-12 — Expand Selection (`tools.ai_expand_selection`)

*What & why.* Elaborate the selected passage into a fuller version, offered for
insert or replace through the agent result dialog.

**Before you start**
- Provider configured. Open `plain.txt` and **select one sentence** (with no
  selection it uses the current paragraph and says so).

**Do this**
1. **AI menu ▸ Transform Selection ▸ Expand Selection**.
2. In the result dialog, read the expanded text; choose **Insert** or **Replace**,
   or close without applying.

**You should see and hear**
- QUILL announces "Expand: generating…"; on completion a result dialog shows the
  expanded text, keyboard-navigable, with **Insert** and **Replace** actions — no
  silent edit. With no selection and an empty paragraph it says "Select text
  first." Applying a change lands it in the current document.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TAI-13 — Generate Table of Contents (`tools.ai_generate_toc`)

*What & why.* Build a table of contents from the whole document's headings, offered
for insertion through the result dialog.

**Before you start**
- Provider configured. Open **`formatting.md`** (six headings, H1–H6 in order).

**Do this**
1. **AI menu ▸ Transform Selection ▸ Generate Table of Contents**.
2. Read the generated TOC; choose **Insert** where you want it, or close.

**You should see and hear**
- QUILL announces it is generating; the result dialog presents a TOC that reflects
  the document's six headings in order, keyboard-navigable, with an insert action.
  It works on the **whole document** (not a selection). An empty document is
  reported.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TAI-14 — Translate Selection (`tools.ai_translate_selection`, Ctrl+Alt+Shift+T)

*What & why.* Translate the selected text into a chosen language, then either
replace the selection or open the translation as a new document.

**Before you start**
- Provider configured. Open `plain.txt` and **select a paragraph**. Target language:
  **Spanish** (or any you can verify).

**Do this**
1. Press **Ctrl+Alt+Shift+T**, or **AI menu ▸ Translate ▸ Translate Selection…**.
2. Choose the target language; run the translation; then choose **Replace
   selection** on one pass and **Open in new document** on another.

**You should see and hear**
- A labelled translation dialog: pick language and provider by keyboard. **Replace**
  swaps just the selected text and announces "Translation applied." **Open in new
  document** opens the translation as a **new unsaved** buffer, announced "Opened
  translation (<language>) in new document," leaving the original untouched. With no
  selection it says "No selection text to translate."

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TAI-15 — AI Thesaurus (`tools.ai_thesaurus`, Ctrl+Alt+Shift+H)

*What & why.* Context-aware synonyms for the selected word — it reads the
surrounding sentence so suggestions fit the sense, and one click replaces the word.

**Before you start**
- Provider configured. Open `plain.txt` and **select a single word**.

**Do this**
1. Press **Ctrl+Alt+Shift+H**, or **AI menu ▸ More ▸ AI Thesaurus…**.
2. Read the synonym list; pick one and **Replace**, or close.

**You should see and hear**
- The thesaurus dialog opens with the selected word and its context sentence shown;
  the synonym list is announced and keyboard-navigable; choosing one replaces the
  selected word in the document. With no configured provider it routes to setup.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TAI-16 — Accessibility Tune-Up (`tools.ai_accessibility_agent`)

*What & why.* An accessibility agent that proposes fixes to the current document
(headings, alt text, structure) and, on apply, writes them in and drops a report in
a new named tab so you can see exactly what changed.

**Before you start**
- Provider configured. Open **`formatting.md`** (has headings, a list, an image with
  alt text — material for the agent to reason about).

**Do this**
1. **AI menu ▸ Accessibility Tune-Up…**.
2. Read the announced plan; review the proposed changes in the dialog; **Apply**, or
   close without applying.

**You should see and hear**
- On open, QUILL **announces the plan** in substance (what it intends to check/fix).
  The dialog is keyboard-navigable and its findings are announced. On **Apply**, the
  changes land in the current document, a status line reports "Accessibility Tune-Up
  applied N changes; M findings remain," and a **new named tab** ("Accessibility
  Tune-Up - <document>") holds the report. Closing without applying changes nothing.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TAI-17 — AI Library (`tools.ai_library`)

*What & why.* The unified manager for Prompts, Skills, and Agents — one tabbed
place to browse, edit, and promote them. (Prompt Studio and Agent Center now
redirect here; see TAI-18/TAI-19.)

**Before you start**
- QUILL open, any document.

**Do this**
1. **AI menu ▸ AI Library…**.
2. Tab across the Prompts / Skills / Agents tabs; read the list and its verbs
   (add/edit/…); close.

**You should see and hear**
- The manager opens as a keyboard-navigable, announced dialog; each tab's list and
  its action buttons are labelled and reachable by keyboard. Closing returns focus
  to the editor.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TAI-18 — Prompt Studio (`tools.ai_prompt_studio`)

*What & why.* A retired entry point kept alive during the deprecation window:
invoking it must **redirect** to the AI Library (Prompts), never dead-end.

**Before you start**
- QUILL open. This command has no menu item — reach it from the **Command Palette**.

**Do this**
1. Run **Prompt Studio** from the Command Palette.

**You should see and hear**
- The **AI Library** opens (the Prompts surface) — the same dialog as TAI-17 — rather
  than a missing or broken window. Any old keybinding or palette entry lands in the
  new manager.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TAI-19 — Agent Center (`tools.ai_agent_center`)

*What & why.* Like TAI-18, a retired entry point that must **redirect** to the AI
Library (Agents) instead of dead-ending.

**Before you start**
- QUILL open. No menu item — reach it from the **Command Palette**.

**Do this**
1. Run **Agent Center** from the Command Palette.

**You should see and hear**
- The **AI Library** opens (the Agents surface) — the same dialog as TAI-17 — cleanly,
  with no missing window or error.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TAI-20 — AI Session Branches (`tools.ai_session_browser`)

*What & why.* Browse the branch tree of your most recent writing session and jump
between or compare branches — the record of an Ask Quill conversation.

**Before you start**
- Ideally, hold an Ask Quill conversation first (TAI-05) so a session exists. Then
  also test the **empty** case on a fresh profile.

**Do this**
1. Run **AI Session Branches** from the Command Palette.

**You should see and hear**
- With a saved session: a keyboard-navigable branch tree opens, announced, with
  jump/compare actions. With **none**: a clear, **announced dialog** (not just a
  status line) says "No saved AI writing sessions yet…" and points you to Ask Quill —
  it does not fail silently.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TAI-21 — Writing Assistant (`tools.ai_assistant`) **[GATED future.ai]**

*What & why.* The multi-tool writing assistant dialog (prompts, run-Python tools,
document/selection context). Behind the `future.ai` flag for 1.0.

**Before you start**
- **[GATED future.ai]** — on a public build this is **N/A**. On a dev/admin build
  with the flag on: provider configured; **not** Safe Mode. Open `plain.txt`.

**Do this**
1. Run **Writing Assistant** from the Command Palette (or its AI-menu item if the
   flag exposes one).

**You should see and hear**
- On a public build: absent → mark **N/A** (confirm its absence in
  `gated-absence.md`). On a flagged build: the assistant dialog opens, keyboard-
  navigable and announced, seeded with the current selection/document. In **Safe
  Mode** it refuses with "Writing assistant is unavailable in safe mode" and opens
  nothing.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TAI-22 — Continue Writing (`tools.ai_continue_writing`) **[GATED future.ai]**

*What & why.* Continue the prose from your selection (or the whole document) by
opening the Writing Assistant pre-seeded with a "continue" prompt.

**Before you start**
- **[GATED future.ai]** — public build = **N/A**. Flagged build: provider
  configured; open `plain.txt` and place the caret at the end (or select a
  passage).

**Do this**
1. **AI menu ▸ Transform Selection ▸ Continue Writing** (flagged builds), or the
   Command Palette.

**You should see and hear**
- On a flagged build the Writing Assistant opens with a continuation prompt built
  from your text; with nothing to continue from it says "Nothing to continue from.
  Type some text first." With AI off it announces AI is disabled. On a public build,
  **N/A**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TAI-23 — Fix Grammar (`tools.ai_fix_grammar`) **[GATED future.ai]**

*What & why.* Grammar fix for the selection/paragraph/document via the Writing
Assistant, seeded with a "grammar" prompt.

**Before you start**
- **[GATED future.ai]** — public build = **N/A**. Flagged build: provider
  configured; open `plain.txt` and select a sentence (or none, to use the
  paragraph).

**Do this**
1. **AI menu ▸ Transform Selection ▸ Fix Grammar** (flagged builds), or the Command
   Palette.

**You should see and hear**
- On a flagged build the assistant opens seeded with the grammar prompt, and QUILL
  announces the scope it is checking ("Checking grammar in <scope>…"); with nothing
  to check it says so. With AI off it announces AI is disabled. Public build =
  **N/A**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TAI-24 — Rewrite Selection (`tools.ai_rewrite_selection`) **[GATED future.ai]**

*What & why.* Rewrite the selected passage, offered for insert/replace via the agent
result dialog (same mechanism as Expand).

**Before you start**
- **[GATED future.ai]** — public build = **N/A**. Flagged build: provider
  configured; open `plain.txt` and **select a sentence**.

**Do this**
1. **AI menu ▸ Transform Selection ▸ Rewrite Selection** (flagged builds), or the
   Command Palette.

**You should see and hear**
- On a flagged build QUILL announces "Rewrite: generating…"; a result dialog offers
  the rewritten text with **Insert**/**Replace** — no silent edit. With no selection
  it uses the current paragraph and says so, or asks you to select text. Public
  build = **N/A**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TAI-25 — Summarize Selection (`tools.ai_summarize_selection`) **[GATED future.ai]**

*What & why.* Summarize the selection (or the document) into a result dialog offered
for insert/replace.

**Before you start**
- **[GATED future.ai]** — public build = **N/A**. Flagged build: provider
  configured; open `formatting.md` (or select a passage in `plain.txt`).

**Do this**
1. **AI menu ▸ Transform Selection ▸ Summarize Selection** (flagged builds), or the
   Command Palette.

**You should see and hear**
- On a flagged build QUILL announces it is generating; a result dialog presents the
  summary, keyboard-navigable, with **Insert**/**Replace**. An empty document is
  reported. Public build = **N/A**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TAI-26 — Describe Image (`tools.describe_image`, Ctrl+Shift+Grave, I) **[GATED future.ai]**

*What & why.* Send an image (file, clipboard, or screen capture) to the provider's
**vision** model and get a written description you can insert, copy, or discard —
alt text on demand. Behind `future.ai` for 1.0.

**Before you start**
- **[GATED future.ai]** — public build = **N/A**. Flagged build: a provider with a
  **vision-capable** model configured. Have an image ready (for example
  `qa-samples/red-circle.png`, or any picture). Chord: **Ctrl+Shift+Grave** then
  **I**.

**Do this**
1. Open via the chord, or **Tools menu ▸ Reading and Dictation ▸ Describe Image…**.
2. Pick the image source (file / clipboard / screen capture). If the style picker
   appears, choose a style. Wait for the description.
3. In the review dialog choose **Insert**, **Copy**, **Try a different prompt…**, or
   **Discard**.

**You should see and hear**
- On a flagged build: a keyboard-navigable image-source picker, then a progress
  dialog ("Asking the model to describe the image…"), then a review dialog with the
  written description — announced, with Insert/Copy/retry/Discard actions. If AI is
  off it says "AI is turned off…"; if no vision provider is connected it says "No AI
  provider is connected…" and describes nothing. Cancelling the picker announces
  "Image description cancelled." Public build = **N/A**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TAI-27 — Prompt Library (`tools.prompt_library`)

*What & why.* A library of reusable AI prompts you can run on your text and import/export as `.pqp` files.

**Before you start**
- AI provider configured (else the dialog shows a "not configured" guard at open — verify that path too). A scratch document with a sentence selected.

**Do this**
1. Open **Tools ▸ AI ▸ Prompt Library** (or Command Palette → "Prompt Library").
2. Tab through the list and its add/edit/import/export controls; run a prompt against the selection.

**You should see and hear**
- The dialog is keyboard-navigable and announced; entries have names; running a prompt sends only on your action and returns a result (as a new/unsaved doc or an insert, per the prompt). With no AI configured, it says so at open rather than failing later. **Note:** confirm the exact spoken wording against the build.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TAI-28 — Skill Library (`tools.skill_library`)

*What & why.* Multi-step AI "skills" (a chain of steps) you can run on a document, with intermediate step output and a cancel button.

**Before you start**
- AI provider configured. A scratch document.

**Do this**
1. Open **Tools ▸ AI Assistant ▸ Skill Library…** (or Command Palette → "Skill Library").
2. Pick a skill; run it; watch the per-step progress; try **Cancel** mid-run.

**You should see and hear**
- Keyboard-navigable list; each step's progress/name is announced; intermediate outputs are reachable; Cancel stops cleanly. With no AI configured, an early guard says so at open. **Note:** verify exact announcements.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TAI-29 — Run Agent on Selection (`tools.run_agent`)

*What & why.* Run a configured AI agent against the currently selected text.

**Before you start**
- AI provider configured; not Safe Mode. Select a sentence in a scratch document.

**Do this**
1. Select text, then run **Run Agent on Selection** (Tools ▸ AI, or Command Palette → "Run Agent").
2. Pick the agent if prompted; confirm any send; wait for the result.

**You should see and hear**
- The selection (not the whole document) is what is sent; a send is confirmed before it leaves; progress is announced; the agent result opens in its result view / a new unsaved doc. Safe Mode / no-provider refuses and sends nothing. **Note:** verify exact wording.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TAI-30 — Train Writing Style (`tools.train_writing_style`)

*What & why.* Teach the AI your writing style from sample text so later AI writing matches your voice.

**Before you start**
- AI provider configured. Sample text available (e.g. `formatting.md` or your own).

**Do this**
1. Open **Train Writing Style** (Tools ▸ AI, or Command Palette).
2. Follow the prompts to supply/confirm the sample; complete the flow.

**You should see and hear**
- Keyboard-navigable, announced steps; it confirms what it will learn from before doing so; on completion it says the style profile was saved. No content is sent without your action. **Note:** verify exact wording and where the profile is stored.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TAI-31 — Open Writing Instructions (`tools.writing_instructions`) [GATED future.ai]

*What & why.* Edit the standing "writing instructions" the AI applies to your writing tasks. Present only when `future.ai` is on — on a public build, mark **N/A** (verify absence in `gated-absence.md`).

**Before you start**
- A build with `future.ai` enabled; AI provider configured. Otherwise N/A.

**Do this**
1. Open **Writing Instructions** (Tools ▸ AI, or Command Palette → "Writing Instructions").
2. Tab through the fields; edit the instruction text; save.

**You should see and hear**
- Labelled, keyboard-complete editor for the instructions; saving is announced and persists to the next AI writing action. On a public build the command is absent. **Note:** verify exact wording.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

### Section sign-off
- Tester:
- Screen reader(s) + version(s):
- Build / commit tested:
- Environment (E1–E6):
- Date:
- Scenarios passed / total: ___ / 31
- Release blockers found (must be zero to ship):
- Result: Pass / Pass-with-notes / Fail
- Notes:
