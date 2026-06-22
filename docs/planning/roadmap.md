# QUILL 1.0 — Consolidated Plan of Record

> **This is the single 1.0 plan.** It replaces the old per-issue "planning
> archive" dump. Work is organized by **workstream**, not by issue id. Each
> workstream says what has shipped, what is next, and where its detailed spec
> lives. The GitHub tracker is reconciled to match this plan: superseded,
> duplicate, and content-free issues are closed with a pointer here; only real,
> actionable work stays open. Live status and counts live in
> [`program-tracker.md`](program-tracker.md).
>
> **Operating principle:** everything in this plan is in scope to **ship** for
> 1.0 (the old "2.0 deferral" framing is dropped). Simplicity for the
> screen-reader user is king. QUILL owns the editor, focus, undo, and
> announcements; AI and every integration are optional and off by default.

**Last consolidated:** 2026-06-21 against branch `feature/beta-2`.

---

## 0. North star

QUILL is a screen-reader-first writing environment. It is becoming the home for
a family of accessibility products that Blind Information Technology Solutions
(BITS) and CSE Designs have built as separate apps. Rather than ship four
editors, we **consolidate their durable value into QUILL** as optional,
keyboard-clear, screen-reader-first feature families — keeping the names users
already know where they carry brand equity (notably **BITS Whisperer** for
speech).

Three sibling products feed this plan:

| Product | Source repo | What it is | Where it lands in QUILL |
| --- | --- | --- | --- |
| **BITS Whisperer** | `s:\code\bw` | Accessibility-first audio transcription: ~18 providers (cloud + on-device), AI translation/summarization, live-mic transcription, speaker diarization, plugins, 7 export formats. | **Speech & Dictation** workstream (§2), keeping the BITS Whisperer brand. The offline core already shipped in QUILL (#617 S0–S4); the rest of BW's value is consolidated here. |
| **GLOW** | `s:\code\glow` | Multi-surface accessibility toolkit: Document Audit (ACB Large-Print Guidelines, Microsoft Accessibility Checker, WCAG 2.2 AA), accessibility agents, Office add-in, MCP server, watch action. | **Accessibility Tooling** (§4) and the **Agentic AI** agent catalog (§3). |
| **ChapterForge** | `c:\code\forum` | Turns a folder of MP3s into one chaptered audiobook/podcast master, screen-reader-first. | **Publishing & Audiobook** workstream (§5), beside DAISY export. |

The discipline for every consolidation: take what clears QUILL's quality and
accessibility bar, re-home it on QUILL's invariants (atomic storage, the dialog
contract, the announcement grammar, Safe Mode, the network-egress audit), and
**leave behind** anything superseded by what QUILL already ships or that does not
serve the screen-reader-first mission.

---

## 1. Verbosity system (Phase 2 — in progress)

**Spec:** [`verbosity-system.md`](verbosity-system.md). **The big in-flight workstream.**

Per-action, channel-aware, user-customizable announcements that replace the
single `announcement_verbosity` knob.

- **Shipped (pure-domain core):** sub-PR 1.1 foundation (#361), 1.2 engine +
  runtime modes (#362), 1.3 QVP packs + library + preview (#363). 220 tests.
- **Next:** sub-PR 1.4 — the wxPython UI (prefs panel, token editor, library,
  history viewer, preview lab, about) (#364); then 1.5 call-site migration + the
  `VerbositySettings` fields (#365); then 1.6 final UX polish (#366).
- **Polish backlog:** the ~100 "addendum" ideas are deduplicated and triaged into
  a small set of themed features in `verbosity-system.md` (§ "Polish backlog").
  Each survivor is a checklist item there, not a separate issue.

## 2. Speech & Dictation — "BITS Whisperer" (partly shipped)

**Spec:** [`dictation-and-speech.md`](dictation-and-speech.md). **Brand: BITS Whisperer** (`s:\code\bw`).

- **Shipped (#617 S0–S4):** dictation honesty, the offline STT foundation,
  whisper.cpp + Faster Whisper engines, offline transcription, transcript and
  caption formats, speaker attribution, dictate-at-cursor, mic selection, the
  model manager, and the installer component.
- **Also shipped (WATCH-9):** Watch Folder can auto-transcribe arriving audio
  on-device — the **Transcribe audio (Whisperer)** watch action
  (`watch_transcribe.py` + wx-free `speech/transcribe.py`) writes a sibling
  `.txt` per file, offline and consent-free.
- **To consolidate from BITS Whisperer:** the broader provider matrix (cloud +
  on-device tiers) behind QUILL's network-egress audit and Safe Mode;
  export-format breadth (SRT/VTT); and the guided provider/model onboarding.
  These were the old `bw_*` "BITS Whisperer" tier IDs (BW-1..10, WATCH-8/9) —
  now folded here, not deferred.
- **Open:** #617 epic context, #663 offline voice commands (S5). Tracked as one
  consolidation issue, not the old per-ID stubs (#515, #567–#577, now closed).

## 3. Agentic AI platform (planned — PRD ready)

**Spec:** [`quill_end_to_end_agentic_ai_prd.md`](quill_end_to_end_agentic_ai_prd.md). Implementation-grounded delta plan.

Unify QUILL's already-deep AI stack behind one provider-neutral, optional,
screen-reader-first platform whose front door is the **AI Hub**: one provider
truth, a Safe Editor Tool Gateway + Permission Broker, a real tool-calling agent
loop, a declarative agent catalog, an activity log, and an optional harness layer
(Copilot SDK, Claude Agent SDK, OpenAI Agents SDK, MS Agent Framework, LangGraph,
OpenHands).

This PRD **supersedes** the scattered AI planning issues: O5/O5b/O6 AI Hub +
stack unification, O7 Azure provider, O8/AI-19 **GitHub Copilot SDK**, O9/SHELL-2
OCR structuring, and AI-11/12/18. The **Accessibility Agents** from GLOW
(Accessibility Editor, Screen-Reader UX Reviewer, Braille/BRF assistant) become
catalog agents here (the launch set already promotes `accessibility_agent.py`).
The old per-ID AX-A..F stubs are consolidated into the tracking issue **#675**.

## 4. Accessibility tooling (from GLOW)

**Source:** `s:\code\glow` (`glowplan.md`). Consolidate GLOW's durable, in-editor accessibility value.

- **Document Audit** — evaluate the current document against ACB Large-Print
  Guidelines, Microsoft Accessibility Checker rules, and WCAG 2.2 AA, returning a
  scored, navigable findings report with remediation guidance. Lands as an
  in-QUILL audit surface (and an agent in §3).
- **GLOW family:** the seven GLOW capabilities (the old #528–#534 stubs) plus the
  WATCH-8 GLOW watch action (#566), re-homed on QUILL's invariants and tracked in
  the consolidated issue **#674** rather than as bare per-ID stubs.
- **Out of QUILL's scope:** GLOW's server/Keycloak/Office-add-in/MCP-deployment
  surfaces stay in the GLOW product; QUILL takes the authoring-time checks.

## 5. Publishing & audiobook

**Specs:** DAISY (shipped, `quill/io/daisy.py`); ChapterForge (`c:\code\forum`).

- **Shipped:** DAISY 2.02 text-only export (#251).
- **ChapterForge integration:** turn a folder of audio (or a document's sections)
  into a chaptered audiobook/podcast master — screen-reader-first, ties to the
  DAISY/talking-book story and the BITS Whisperer transcription stack.
- **Direct publishing (#140):** WordPress and other platforms — kept as a
  long-term, likely-Quillin integration (external-API + auth surface), not core
  editor work.

## 6. Braille mode (shipped — Phases 3/4)

**Spec:** [`braille-mode-backlog.md`](braille-mode-backlog.md).

Proofing, validation, restore-your-place, and selection-aware back-translation
shipped (#238–#242, #246). Remaining braille ideas live in the backlog doc and
the verbosity braille channel.

## 7. Navigation & editor

- Quick Navigation enhancements (#513); un-gate the structured Word view + CSV
  grid (#514); extract `main_frame_statusbar.py` (#521, GATE-11 decomposition).

## 8. Platform & distribution

- Live installer smoke on Windows 10/11 (#506); macOS to shipping quality (#518);
  native RTF editing (#516); the Quillin Hub (#517); plugin capability + signing +
  marketplace (#519); the Windows 11 primary-menu pass (#525); **packaging/freeze
  evaluation** (the old PKG-1 — Nuitka/PyInstaller hardening, now a real 1.0
  distribution item).
- **Out of scope:** Linux/Unix (#520, #565, #589). Platform scope is Windows
  (primary) and macOS (supported).

## 9. Docs, tutorials & content

The old Tier-6 DOC/POD/TUT/CQ backlog (#535–#564) is consolidated into one
**Documentation & Tutorials** track: user-guide coverage, getting-started
tutorials, the podcast/walkthrough series, and the content-quality (CQ) follow-ups
(spell-check preload #527, SR sign-off across NVDA/JAWS/Narrator #526). Tracked as
a themed track, not 30 separate stubs.

---

## 10. Issue consolidation ledger

The tracker was reconciled to this plan on 2026-06-21. Disposition buckets:

**Kept open (real, actionable workstreams):** the verbosity sub-PRs and
§-section partials (#364–#366 and the sections they close); the **Speech &
Dictation / BITS Whisperer** workstream (#617/#663 plus the retained BW tier
markers #515/#566–#577, kept as the consolidation backlog); the **GLOW
integration** — both the GLOW family epics (#528–#534) and the **Accessibility
Agents** AX-A..F (#593–#598); platform #506/#516/#517/#518/#519/#521/#525 and
**PKG-1** packaging/freeze (#599); navigation #513/#514 (and NAV-10 #578);
publishing #140; in-flight QA #526/#527; long-horizon ecosystem/collaboration
ideas (#590/#592).

**Folded into the plan, then closed** (substance now lives in a spec, not a stub):

- The **100 verbosity addenda (#405–#504)** → `verbosity-system.md` polish backlog.
- **AI** placeholders AI-11/12/18 (#579–#581), O5–O9 + in-flight Copilot/SHELL-2
  (#507–#512, #523/#524) → the Agentic AI PRD (§3), which is their detailed home.
- **Tier-6 DOC/POD/TUT/CQ** (#535–#564) → Docs & Tutorials track (§9).
- Meta/archive issues: the old roadmap/master-backlog/verbosity-archive
  placeholders (#505, #522, #602) → superseded by this plan.

**Removed — below the 1.0 quality bar** (closed, not in the plan):

- **Localization L10N-1 (#591)** — already delivered (the i18n display-language
  switcher and submission-ready translation workflow shipped).
- **FEAT-12..18 (#582–#588)** — content-free stubs whose only source was the
  now-deleted `planning.md`; no recoverable design intent. If a real feature
  behind one resurfaces, it re-enters through the relevant workstream above.
- **Linux/Unix LINUX-1/2 + O17 (#520, #565, #589)** — not a platform target.
- Within the verbosity addenda, the screen-reader-redundant ideas are recorded
  as **"recommend do not build"** in the polish backlog rather than silently
  dropped: **Typing Echo** and **Command Echo** (the screen reader already echoes
  keys/typing; QUILL doing so double-speaks — the right answer is the
  Screen-Reader Handoff mode), **Speech Rate/Pause knobs** (QUILL does not own the
  SR voice), **Punctuation/Symbol Profiles** (a core SR setting; duplicating it
  fights the SR), and the **"Final Recommendation"** meta-issue.

---

## 11. Source repos for the consolidations

These external repos are the design source for the integrations above; QUILL
takes the durable, accessibility-first value and re-homes it on QUILL's
invariants.

- **BITS Whisperer:** `s:\code\bw` (transcription/speech; brand retained).
- **GLOW:** `s:\code\glow` (`glowplan.md`; accessibility audit + agents).
- **ChapterForge:** `c:\code\forum` (audio → chaptered audiobook/podcast).
