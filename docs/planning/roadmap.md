# QUILL — Plan of Record (outstanding work)

> **The single planning document, and it tracks only what is still open.** Shipped
> work is not listed here — once something lands it leaves this file; its behavior
> lives in the user guide and `QUILL-PRD.md`. The only other files in
> `docs/planning/` are the large in-flight feature specs, each with open work of
> its own:
>
> - [`quill-native-accessible-table-studio-plan.md`](quill-native-accessible-table-studio-plan.md) — Table Studio (not started).
> - [`eleven-labs.md`](eleven-labs.md) — ElevenLabs / ElevenDesk integration ideas (not started).
>
> **Operating principle:** everything here is in scope to **ship** for 1.0 (except
> a few rows explicitly marked 2.0). Simplicity for the screen-reader user is king.
> QUILL owns the editor, focus, undo, and announcements; AI and every integration
> are optional and off by default. Platform scope is Windows (primary) and macOS
> (supported).

**Last consolidated:** 2026-06-27.

---

## 0. North star

QUILL is a screen-reader-first writing environment, becoming the home for a family
of accessibility products that Blind Information Technology Solutions (BITS) and
CSE Designs built as separate apps. Rather than ship four editors, we **consolidate
their durable value into QUILL** as optional, keyboard-clear, screen-reader-first
feature families — keeping names users know where they carry brand equity (notably
**BITS Whisperer** for speech). Three sibling products still feed open work:
**BITS Whisperer** (`s:\code\bw`, transcription/speech), **GLOW** (`s:\code\glow`,
accessibility audit + agents), and **ChapterForge** (`c:\code\forum`, audio →
chaptered audiobook). The discipline: take what clears QUILL's quality and
accessibility bar, re-home it on QUILL's invariants (atomic storage, the dialog
contract, the announcement grammar, Safe Mode, the network-egress audit), and
leave behind anything superseded or off-mission.

---

## 1. Workstreams (open work)

### 1.1 Verbosity ✅ (complete for 1.0)

The verbosity system is **done for 1.0**: the engine, the eleven `verbosity_*` UI
surfaces, the runtime modes (Quiet / Meeting / Quiet-Undo) with status badges, the
status-query commands (Where am I? / What changed? / Speak Status), mastery
step-down, history, the explain trace, Safe Mode/reset, QVP packs + library +
preview lab, task-aware profiles, and import/export. The high-value polish items
shipped too — **destructive-action confirmation** and, newly, **announcement
anti-spam** (repetition collapse + announcement budget at the `process()`
choke-point, `quill/core/verbosity/throttle.py`).

The remaining "polish backlog" long-tail (the speculative slice of the ~100 addenda
#405–#504) is **deferred to 2.0** — the full distilled backlog, the valuable
candidates (error coaching #416, per-category detail #418, Markdown/Code-aware
#427/#428, "undo available" #502), and the "recommend do not build" list
(Typing/Command Echo, Speech Rate/Pause knobs, Punctuation/Symbol Profiles — the SR
already owns these) are in the Verbosity 2.0 polish backlog at the end of **§5**.

### 1.2 Speech & Dictation — "BITS Whisperer" ✅ (complete for 1.0)

The batch document-to-speech and dictation work is **done for 1.0**:

- **Batch Document-to-Speech** with the full flexibility surface, chaptered MP3 and
  M4B (native chapter atoms), pronunciation dictionaries, text normalization, the
  SSML Builder + native playback, a **dry-run preview**, **separate-file-per-article**
  mode, **long-document chunking**, richer **.docx** extraction
  (tables/footnotes/headers), **chapter-transition sound** resolution from the active
  sound pack, and **configure-once project profiles** (apply-on-open + auto-remember
  on Start, precedence this-run > project > global > defaults).
- **Hold / Locked dictation** with the **Settings panel**, the **History & Review**
  window (insert/copy/discard recovered recordings; doubles as the interactive
  startup-recovery prompt), distinct locked earcons, and one-time onboarding.
- **Subprocess hardening:** the Piper and eSpeak file-synthesis calls no longer flash
  a console window and carry a timeout (a full migration of every `read_aloud`
  subprocess to `stability.safe_subprocess` is an optional internal refactor, not a
  blocker).

**External / courtesy (not QUILL code):** offer ChapterForge the two fixes already
in QUILL's `chapters.py` (non-contiguous gap chapters; ID3-tag clobbering).

The **ElevenLabs / ElevenDesk** premium-cloud-TTS integration is its own workstream,
tracked in [`eleven-labs.md`](eleven-labs.md) — **not started** (the SDK-in-gateway
approach is decided). Dictation's larger later-phase capabilities are **2.0** (§5).

**AI footprint & optimization** is its own measurement-first plan, tracked in
[`QUILL-AI-Optimization-PRD.md`](QUILL-AI-Optimization-PRD.md). Its first concrete
slice **shipped in 0.8.1 Beta 1**: a pinned, SHA-256-verified path for fetching
redistributable components from QUILL's own GitHub release assets
(`quill/core/release_assets.py`), wired as **Tools > Speech > Download Offline Speech
Engine...** (recovery for the bundled whisper.cpp engine). It establishes the
reliable-acquisition foundation (PRD §10.2.3–10.2.4) that any future unbundling builds
on; the engine stays bundled, so capability never depends on a download.

### 1.3 Agentic AI platform (shipped in 0.8.1 Beta 1)

The detailed planning spec was retired once the platform shipped; the AI suite is
now documented in the PRD, the user guide, and the 0.8.1 Beta 1 release notes.

Unify QUILL's AI stack behind one provider-neutral, optional, screen-reader-first
platform whose front door is the **AI Hub**: one provider truth, a Safe Editor Tool
Gateway + Permission Broker, a real tool-calling agent loop, a declarative agent
catalog, an activity log, and an optional harness layer. Supersedes the scattered
AI issues O5/O5b/O6 (#507–#509), O7 Azure (#510), O8/AI-19 Copilot SDK (#511/#523),
O9/SHELL-2 OCR structuring (#512/#524), and AI-11/12/18 (#579–#581). The
Accessibility Agents from GLOW (AX-A..F, #593–#598) become catalog agents here.

### 1.4 Accessibility tooling (from GLOW) — deferred to 2.0

The GLOW accessibility-tooling family is **deferred to QUILL 2.0** (§5); it is not a
1.0 workstream. The GLOW contributions remain `locked_off` (hidden) for 1.0.

### 1.5 Publishing & audiobook ✅ (complete for 1.0)

The ChapterForge **folder-of-audio → one chaptered master** surface is **done for
1.0**. **Build Audiobook from Folder** (Tools > Speech) combines a folder of audio
files into a single chaptered **MP3** or **M4B** master (native chapter atoms),
with book tags and an auto-detected cover (`quill/core/speech/audiobook.py`), plus:

- **In-dialog chapter editing** — rename, reorder (move up/down), and merge adjacent
  chapters before building; titles default to the filenames (natural-sort order).
- **ACX loudness compliance** — a one-click **Normalize to ACX** option applies an
  ffmpeg `loudnorm` pass during the build, and the finished master is measured and
  reported against ACX's RMS/peak window (`quill/core/speech/loudness.py`).

FLAC/Opus *output* is intentionally **not** offered — those formats can't carry the
chapter markers an audiobook needs (they remain accepted as *source* files).

Direct publishing (#140) and the remaining ChapterForge surfaces are tracked under
§5 (2.0).

### 1.6 Platform & distribution

- The Quillin Hub (#517); plugin capability + signing + marketplace (#519).
- **Deferred to 2.0** (tracker #680): the Windows 11 modern primary-menu
  `IExplorerCommand` pass (SHELL-3, #525).

### 1.7 Docs, tutorials & content

One **Documentation & Tutorials** track: user-guide coverage, getting-started
tutorials, the podcast/walkthrough series, and content-quality follow-ups
(#535–#564, #505, #522). Long-horizon ecosystem (#590) and collaboration (#592)
ideas park here.

### 1.8 Structured List Studio

The feature is shipped. Its live screen-reader pass is handled in the normal QA
validation (the #526 sign-off was closed as a matter-of-course test), so no
roadmap-tracked work remains here.

### 1.9 Native accessible Table Studio (not started)

**Spec:** [`quill-native-accessible-table-studio-plan.md`](quill-native-accessible-table-studio-plan.md).
The accessible table-authoring surface (and the CSV-grid half of #514) — planned
design only.

---

## 2. Release gap list (path to green)

What's left between QUILL and a **green, release-ready** state is now just
**routine validation**, handled in the normal QA pass rather than tracked as
release blockers (the same disposition as the closed #506 / #518 / #526):

- **Packaged-build validation** of the optional speech engines (Faster Whisper,
  Vosk) on the real installer, not just from source.
- **Watch Folder queue** — a live repro confirming the by-design priming (drop a
  *new* matching file into a running profile, or enable "Process existing files");
  the "N existing files ignored" monitor hint already shipped.
- **Snapshots vs Versions** — a live repro of the reported empty-submenu render
  (toggle the `core.notebook` / `core.recovery` flags); the user-facing "Versions"
  rename is done.

Verbosity polish is resolved (§1.1 shipped; the long tail is deferred to §5).
Excluded per direction: the AI & Agentic workstream (§1.3) and all table work
(§1.9 + the CSV-grid half of #514).

---

## 3. Planned phase outcomes

What the user will notice as the open work lands, screen-reader experience first.

### Phase 3 — An AI that helps without taking over

One coherent AI Hub; agents that read your selection and propose edits you preview
and undo in one step — never silent changes (§1.3). *Powerful help that stays
reviewable, undoable, and spoken.*

### Phase 4 — Move faster + publish further

Structured Word/CSV views and the Table Studio surface (§1.9); broader publishing,
e.g. direct publishing to external platforms (#140); GLOW family improvements
(§1.4). *Faster keyboard navigation and accessible publishing.*

### Phase 5 — Solid on Windows and macOS

The Quillin hub (§1.6); better docs/tutorials (§1.7). *A dependable,
well-documented product on its supported platforms.*

---

## 4. Feature ledger (by workstream)

### Still open

| Workstream | Open work |
| --- | --- |
| Agentic AI (§1.3) | #507–#512, #523/#524, #579–#581; Accessibility Agents #593–#598. |
| GLOW family (§1.4) | Deferred to 2.0 (§5). GLOW contributions stay `locked_off` for 1.0. |
| Platform & distribution (§1.6) | #517, #519; #525 deferred to 2.0 (#680). |
| Docs & content (§1.7) | #535–#564, #505, #522, #590, #592. |
| Table Studio (§1.9) | Whole feature (`quill-native-accessible-table-studio-plan.md`). |
| ElevenLabs beyond export (§4.2–4.4) | Live streaming Read Aloud, voice management / cloning, and Tier-3 surfaces — all deferred to 2.0 (§5). |

### 4.1 ElevenLabs premium cloud TTS — audio export (**shipped in 1.0**)

**What.** Add **ElevenLabs** as a third provider in QUILL's existing provider-neutral
cloud-TTS layer (`quill/core/ai/cloud_tts.py`, today OpenAI + Gemini), so a user can
export their own documents to natural, audiobook-grade narration. This is the headline
ElevenLabs value for a writing/reading editor (full reasoning in
[`eleven-labs.md`](eleven-labs.md)).

**Why now / why small.** The seam already exists and already feeds Read Aloud *and*
export with cost estimation, chunking, and cancellation; ElevenLabs **STT** already
ships (the `elevenlabs-transcription` Quillin). So this is "register one more provider,"
not a new architecture. Scope for 1.0:

- New **host-owned gateway** `quill/core/ai/elevenlabs_tts.py` — the *only* module that
  imports the official `elevenlabs` SDK (per the decided "SDK inside one gateway"
  posture). It owns credential retrieval (the existing **"ElevenLabs API key"** label),
  rejects alternate `base_url`, translates SDK errors to a stable QUILL error, and is
  cancelable.
- Register `"elevenlabs"` in `cloud_tts.py` (models, voices, default voice/model, a
  conservative cost estimate, `speak_text` / `export_audio` dispatch).
- `elevenlabs` ships as an **optional extra** (`pip install quill[elevenlabs]`); the
  provider is inert/hidden unless the SDK is installed *and* a key is configured. Safe
  Mode and the per-run consent the AI Voice surface already enforces both apply.
- A new **network-egress-audit** entry for the gateway's SDK call site (host
  `api.elevenlabs.io`). No bundled Quillin receives the SDK, key, or audio bytes.

**Sub-decisions (recorded; defaults chosen so this can proceed):**

- *Voice listing.* ElevenLabs voices are account-specific, so the picker can't be a
  static list like OpenAI/Gemini. **Default:** ship a small built-in fallback list plus
  a "Refresh from my account" action that calls `voices.get_all()` on demand. *(Alt:
  always fetch live when the provider is selected.)*
- *Cost estimate.* ElevenLabs bills per character by subscription tier. **Default:** a
  conservative per-1,000-character estimate flagged approximate (mirrors the existing
  OpenAI/Gemini estimate UI), or "unavailable" rather than implying free.
- *Retry posture.* Read-only calls (voices/models) get bounded backoff; **billable
  synthesis is retried at most once and only when no audio was received** — never blind
  re-POST (avoids double-billing).

### 4.2 ElevenLabs live Read-Aloud streaming + continuous consent (decision: **defer to 2.0**)

Live, sentence-by-sentence Read Aloud through ElevenLabs is **one paid API call per
sentence**, so it needs SDK **streaming** (incremental playback, instant cancel,
sentence prefetch, aggressive `tts_cache`) and a **continuous, session/document-scoped
consent model** with a persistent "reading via ElevenLabs (cloud)" indicator — an open
UX question the original spec flagged for a maintainer decision. Higher cost/latency
risk, real new UX surface. **Recommendation:** ship §4.1 export first; revisit live
streaming for 2.0 once the export path proves the gateway.

### 4.3 ElevenLabs voice management — cloning / design / pronunciation (decision: **defer to 2.0**)

"Manage ElevenLabs Voices": instant voice cloning (IVC, recursive audio import as
ElevenDesk does), voice design from a prompt, and listing/attaching ElevenLabs
*server-side* pronunciation dictionaries (kept visibly distinct from QUILL's own local
`speech/pronunciation.py`). Each is a heavier UI + new egress surface and is a Tier-2
companion, not core writing value. **Recommendation:** 2.0.

### 4.4 ElevenLabs Tier-3 surfaces — SFX / voice-changer / history (decision: **defer or skip**)

Sound-effect generation, speech-to-speech (voice changer), and the generation-history
browser are far from a writing editor's core. If ever built, they belong as
**optional, separately-installable Quillins**, not core features. Generation history is
largely redundant once local caching/export exists. **Recommendation:** 2.0 backlog or
skip.

---

## 5. Deferred to QUILL 2.0

Confirmed out of the 1.0 scope. Recorded here so the intent is not lost; items
graduate into the shipping sections above when scheduled for a release.

- **Dictation later phases** — an optional **global Windows key hook** (system-wide
  dictation hotkey), **idle-silence detection** (auto-stop on a pause), and
  **dictation intelligence** (spoken punctuation/commands). Each is a sizable
  capability beyond the keyboard-only Hold/Locked dictation that already ships.
- **BITS Whisperer remainder** (tracker #680) — the consolidation shipped for 1.0
  (four on-device engines, the cloud-as-Quillins framework with OpenAI/Groq/
  ElevenLabs, offline watch transcription, export breadth, dictation). The
  leftovers — a Windows SAPI/WinRT zero-download engine, a consented cloud watch
  action, guided provider onboarding, diarization/live-mic, additional cloud kinds
  (add on demand), and the Whisperer brand decision — moved to #680 when #669
  closed.
- **Platform singleton** (tracker #680) — the Windows 11 modern primary-menu
  `IExplorerCommand` pass (SHELL-3, #525). *(Freeze/compile packaging — PyInstaller
  and Nuitka — is out of scope: the embedded-Python + Inno Setup model is the
  shipping approach.)*
- **Direct publishing (#140)** — publish a finished document/audiobook to WordPress
  and other platforms. A long-term, likely-**Quillin** integration (external-API +
  auth surface), not core editor work; early design lives in
  `docs/design/publishing/`.
- **Remaining ChapterForge surfaces** (out of the 1.0 audiobook vision) — Auphonic
  post-processing, RSS podcast feeds, SFTP publishing, and MusicBrainz / Open
  Library metadata lookup.
- **ElevenLabs beyond export TTS** — live Read-Aloud streaming + continuous-consent
  model (§4.2), voice management / cloning / design / server-side pronunciation
  dictionaries (§4.3), and the Tier-3 SFX / voice-changer / history surfaces (§4.4).
  The 1.0 ElevenLabs slice is export-only cloud TTS (§4.1); everything else here is
  2.0. Full reasoning in [`eleven-labs.md`](eleven-labs.md).
- **Native Google Docs support** — read/write/round-trip Google Docs from within
  QUILL (Drive API, OAuth, accessible doc model). A full external-service +
  auth + sync workstream; spec in
  [`QUILL-Native-Google-Docs-Support-PRD.md`](QUILL-Native-Google-Docs-Support-PRD.md).
- **Verbosity polish-backlog long tail (§1.1)** — the speculative slice of the ~100
  addenda (#405–#504) beyond the shipped core/UI/modes/anti-spam. The full distilled
  backlog (valuable candidates + themed reference + "recommend do not build") is the
  **Verbosity 2.0 polish backlog** subsection at the end of this section —
  consolidated here when the standalone `verbosity-system.md` archive was retired.
  Shipped design lives in PRD §5.91.
- **Accessibility tooling from GLOW (§1.4)** — Document Audit (ACB Large-Print
  Guidelines, Microsoft Accessibility Checker, WCAG 2.2 AA) and the GLOW family
  (#528–#534) plus the WATCH-8 GLOW watch action (#566), re-homed on QUILL's
  invariants. Contributions stay `locked_off` for 1.0. GLOW's
  server/Keycloak/Office-add-in/MCP-deployment surfaces stay in the GLOW product;
  QUILL would take the authoring-time checks. Source: `s:\code\glow` (`glowplan.md`).

### Verbosity 2.0 polish backlog (consolidated)

The verbosity engine, the eleven `verbosity_*` UI surfaces, the runtime modes
(Quiet / Meeting / Quiet-Undo), the status-query commands (Where am I? / What
changed? / Speak Status), mastery step-down, history, the explain trace, Safe
Mode/reset, QVP packs + library + preview lab, task-aware profiles, import/export,
destructive-action confirmation, and **announcement anti-spam** (#408/#409) all
shipped for 1.0 (§1.1). The **shipped design** is documented in **PRD §5.91**.

This section is the consolidated reference for the **deferred** polish-backlog
addenda (#405–#504), absorbed here when the standalone `verbosity-system.md`
archive was retired. Issue numbers are kept so each idea stays findable.

**Valuable candidates (build first if the range reopens):**

- **Error coaching (#416)** — turn an error announcement into a next-step hint.
- **Per-category announcement detail levels (#418)** — independent verbosity per
  category (nav / edit / search / system) on top of the global profile.
- **Markdown-aware (#427) / Code-aware (#428) verbosity** — context-sensitive
  announcements when editing Markdown or source.
- **"Undo available" cues (#502)** and richer **destructive-action warnings (#501)**
  (the confirm dialog ships; the spoken cue is the increment).
- **Boundary announcements (#419)** and **progress-announcement controls (#420)**.
- **Details-on-demand (#417)** beyond the existing status-query commands.

**Themed reference well (speculative; build only on demand):**

- *Settings UX:* searchable settings (#406), recipes (#407), bulk edit (#464), undo
  for settings (#465), change history (#466), export preview (#482), import-conflict
  wizard (#483), "try without applying" (#484), reset granularity (#481),
  explain-my-settings (#446), test-my-settings (#467), recommended settings (#468),
  persona setup (#469).
- *Packs:* community pack preview/diff (#442), trust labels (#443), copy-as-user-
  template (#444), pack-author mode (#461), built-in sample QVPs (#462), conflict
  checker (#445).
- *Modes / recipes:* focus mode (#487), review mode (#488), session profiles (#485),
  time-based quiet hours (#486), temporary boost (#436), training mode (#438).
- *Privacy / support:* privacy controls (#448), private-document mode (#449), export
  support bundle (#447), copy debug summary (#478), report announcement (#479),
  developer trace verbosity (#495), performance knobs (#496).
- *Output niceties:* last-important announcement (#452), pin status (#456), smart
  status rotation (#457), favorites (#455), labels (#473), per-announcement
  suppression (#471/#472), earcons-with-text (#453), learn-sounds mode (#454), status
  badges (#497), braille status cell (#498), before/after announcements (#500).
- *Content / localization:* friendly names (#440/#477), microcopy style (#490),
  use-my-words labels (#491), abbreviation dictionary (#492), localization readiness
  (#493), readability verbosity (#489).
- *Hardware / context:* multi-monitor / presentation safety (#503), screen-reader
  handoff mode (#410), command discovery (#470), contextual help hooks (#439),
  hold-to-explain (#437), confidence-check wizard (#441).

**Recommend do not build** (the screen reader already owns these; QUILL speaks
*alongside* it and must not duplicate or fight its settings): **typing echo (#411)**,
**command echo (#499)**, **speech rate / pause knobs (#450)**, and
**punctuation / symbol profiles (#426)**.
