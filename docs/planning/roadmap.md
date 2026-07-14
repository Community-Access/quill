# QUILL — Plan of Record (outstanding work)

> **The single planning document — it tracks only what is still open**, plus the
> register of **locked / hidden** features (consolidated here from the retired
> `deferred-locked-features.md`). Shipped work is not listed here; once something
> lands it leaves this file and its behavior lives in the user guide and
> `QUILL-PRD.md`. The large in-flight feature specs that once kept their own files
> have all shipped and been retired to git history (Table Studio → PRD §5.4.14; Hey
> QUILL voice interaction → PRD §5776 + user guide; Accessible Vault → PRD §5.89d).
>
> The Accessible Vault plan has been **retired**: Phases 0–7 shipped (feature-complete
> for 0.9.0, no open work) and the feature now lives in `QUILL-PRD.md` §5.89d and the
> user guide. The Audio Studio shipped the same way (PRD, user guide, release notes;
> only the human validation pass remains, in `audio-studio-roadmap.md`).
>
> **Operating principle:** everything here is in scope to **ship** for 1.0 (except
> rows explicitly marked 2.0). Simplicity for the screen-reader user is king. QUILL
> owns the editor, focus, undo, and announcements; AI and every integration are
> optional and off by default. Platform scope is Windows (primary) and macOS
> (supported).

**Last consolidated:** 2026-07-05 (Audio Studio roadmap completed and folded into the
canonical docs; libmpv hosted on assets-v1 and surfaced in Download Optional
Components; completed sections — Accessible Vault, Quillin Hub, libmpv hosting —
removed from this file).

---

## 0. North star

QUILL is a screen-reader-first writing environment, becoming the home for a family
of accessibility products that Blind Information Technology Solutions (BITS) and
CSE Designs built as separate apps. Rather than ship four editors, we **consolidate
their durable value into QUILL** as optional, keyboard-clear, screen-reader-first
feature families. The consolidation itself is **done** — BITS Whisperer, GLOW, and
ChapterForge (now the Audio Studio) all live in QUILL; the only sibling still feeding
open work is **GLOW**'s extended family (§5). The discipline: take what clears QUILL's quality and
accessibility bar, re-home it on QUILL's invariants (atomic storage, the dialog
contract, the announcement grammar, Safe Mode, the network-egress audit), and leave
behind anything superseded or off-mission.

---

## 1. Open workstreams

### 1.1 AI footprint & optimization — remaining wiring + build/hardware sign-off

The measurement-first effort to make QUILL's full AI + speech feature set install
small, start fast, and run on a cheap CPU-only laptop. The durable design (principles,
reliable-acquisition model, host/redistribution rules, size/RAM reference) lives in
[`QUILL-PRD.md`](../Product%20Requirement%20Documents%20and%20Specifications/QUILL-PRD.md)
§5.25f. The wx-free cores (runtime-memory policy, upgrade advisor, cloud↔local
fallback, footprint sampler) and the Vosk unbundle + self-hosting have shipped and
are unit-tested. **Still open:**

- **Live-app sign-off (smoke test)** of the now-wired runtime-memory policy (the
  idle-sweep timer firing, a real model unloading), the model upgrade hint in the AI
  model dialog, and the offline cloud↔local fallback announcement on a real failure.
- **Phase 1 installer-size delta** — **Pandoc unbundled 2026-07-03** (the single largest
  component, ~220 MB unpacked) and **the braille pack unbundled the same day** (PR #800):
  both now download a pinned, SHA-256-verified build on demand the first time they are
  needed (braille was found safe to unbundle — the pack is a detection marker + BRF-profiles
  source; the actual `import louis` translation is external and unaffected). Remaining
  candidates are ruled out: `win32more` is a real dependency of the screen-reader layer
  (`prismatoid`) and Windows OCR — not removable without breaking accessibility; `vosk` and
  non-en enchant dictionaries already download on demand. Concrete new quant catalog entries
  (q5/q8, int8_float16) still need real pinned files + SHA-256 hashes.
- **Phase 0 committed numbers** — per-engine peak RSS and cold-start/first-output
  timings. The measurement harness now exists: `python scripts/footprint_live.py
  --merge-baseline` runs each installed engine in an isolated subprocess and merges
  real timings + peak RSS into the baseline (degrades to notes, never fabricates).
  What remains is a **live run on a reference machine** with the engines/models
  installed, plus the short manual runtime-behavior pass in
  [`phase0-live-signoff-checklist.md`](footprint/phase0-live-signoff-checklist.md).
- **macOS offline-speech parity** — a mac `whisper-cli`, or Faster Whisper as the mac
  default — the tracked cross-platform gap.

### 1.2 GLOW — open remainder

GLOW shipped for 0.9.0 (canonical: PRD §5.92, user guide, release notes). Open:
only the *extended* family — ACB large-print document audit (#528–#534) and the
WATCH-8 watch action (#566) — see §5.

### 1.3 Platform & distribution

- **Copilot OAuth deploy nicety**: register a GitHub OAuth App and provide its
  client id via `QUILL_GITHUB_CLIENT_ID` at build time to light the in-app
  spoken device-code Copilot sign-in (the Copilot/GitHub CLI sign-in already
  works without it — enhancement, not blocker). Everything else in this
  workstream (Quillin Hub + signing #517/#519, agent harnesses) shipped;
  canonical docs: `docs/signing.md`, `docs/release/quillin-hub-deployment.md`,
  PRD §5.84e.
- **Deferred to 2.0** (tracker #680): the Windows 11 modern primary-menu
  `IExplorerCommand` pass (SHELL-3, #525).

### 1.4 Docs, tutorials & content

One **Documentation & Tutorials** track: user-guide coverage, getting-started
tutorials, the podcast/walkthrough series, and content-quality follow-ups
(#535–#564, #505, #522). Long-horizon ecosystem (#590) and collaboration (#592)
ideas park here.

### 1.5 Table Studio — open follow-ups

Table Studio shipped as an experimental opt-in (canonical: PRD §5.4.14, user
guide, release notes; a macOS NSAccessibility bridge design note is preserved
at `docs/design/table-studio-macos-nsaccessibility.md`). Open: make the CSV a
first-class editable *document tab* (retire the legacy `CsvGridSurface`), and a
real screen-reader validation pass on a packaged build.

### 1.6 ElevenLabs — remaining 2.0 extras

Everything 1.0-scoped shipped. What remains is 2.0-deferred — live streaming
Read Aloud refinements, voice management, server-side pronunciation, Tier-3
surfaces — all in §5. Voice **cloning** stays deliberately descoped.

---

## 2. Locked / hidden features (register)

These features are gated `locked_off=True` in `quill/core/feature_catalog.py` and must
**not** appear in shipping user-facing docs (user guide, release notes, control
reference, PRD). Authoritative state is the catalog; this register is the human summary
(consolidated from the retired `deferred-locked-features.md`). When a feature unlocks,
move its preserved content back into the relevant doc.

**Currently locked (as of 0.9.0 Beta 1):**

- `core.rich_text_lens` — **Rich Text Lens** (native wxPython rich-text editing for
  `.rtf`). Locked pending fuller screen-reader testing; RTF opens as plain text
  meanwhile. Docs must not claim native RTF editing ships.
- `future.publishing` — **Publishing** send path (publishing connections + provider-aware
  remote publishing). Locked while the providers framework is reviewed; the read-only
  inbound half ships. Release notes already frame this as *future*.
- `core.third_party_plugins` — **Third-Party Plugins** loader (SEC-8). Locked until the
  plugin sandbox, signing, and review process ship. Release notes frame third-party
  Quillins / a marketplace as *future*.
- `core.bw_whisperer` — **BITS Whisperer** brand menu (plus `core.bw_transcription`,
  `core.bw_providers`, `core.bw_insights` sub-flags, the `quill/core/bw_providers.py`
  backend, the hidden Whisperer menu, and its commands/settings). This gates only the
  **superseded branded presentation** — the phased-rollout / Provider Center / Status Page
  surface that the shipped flat **Tools > Speech** menu replaced. It does **not** gate the
  speech or agentic-AI *capabilities*, which ship as plain, always-on features.
  **Decision: keep it as-is (locked, inert).** It builds nothing at runtime and ships
  nothing, so there is no benefit to removing it and real risk in the ~1000-line untangle
  (its handlers are coupled to the *shared* `bw_speech.py` and speech settings that the
  live speech service uses). Leave it locked until there is a concrete reason to touch it.

**All voice and speech *capabilities* are shipped and baked in** — offline dictation,
transcription and captions, read-aloud across SAPI 5 / DECtalk / Piper / eSpeak / Kokoro
and the ElevenLabs cloud voice, batch document-to-speech, and audiobook building. Hands-free
**voice interaction** also shipped: `core.voice_commands` was unlocked for Hey QUILL
(push-to-talk, conversation mode, wake word, Ask Quill routing) — no speech-adjacent lock remains.

> **Docs framing.** GLOW ships as an experimental opt-in (2026-07-02) and its preserved user-facing content
> has been restored into the user guide ("GLOW Workflows Inside QUILL"), glossary, help
> topics, and PRD §5.92 — the §2.1 preservation block this file used to carry is gone
> because the real docs now own it. The **BITS Whisperer** brand is retired — earlier
> drafts named a "BITS Whisperer speech suite" / "Tools > Speech > Whisperer"; that is
> now the flat **Tools > Speech** menu and a plain "private, on-device speech suite,"
> with no brand to restore.

---

## 3. Release gap list (path to green)

What's left between QUILL and a **green, release-ready** state is now just **routine
validation**, handled in the normal QA pass rather than tracked as release blockers
(the same disposition as the closed #506 / #518 / #526):

- **Packaged-build validation** of the optional speech engines (Faster Whisper, Vosk)
  on the real installer, not just from source.
- **Watch Folder queue** — a live repro confirming the by-design priming (drop a *new*
  matching file into a running profile, or enable "Process existing files").
- **Snapshots vs Versions** — a live repro of the reported empty-submenu render (toggle
  the `core.notebook` / `core.recovery` flags); the user-facing "Versions" rename is done.
- **Save As conversion (shipped 2026-07-04)** — the manual JAWS/NVDA spot checks for the
  Save As conversion / window-title / export-fidelity fix (the retired plan's Task 9);
  the step-by-step script is SAVE-001 in
  [`docs/release/screen-reader-test-plan.md`](../release/screen-reader-test-plan.md), and
  the converter verdicts live in [`docs/qa/converter-bakeoff.md`](../qa/converter-bakeoff.md).

Excluded per direction: all table work (§1.5 + the CSV-grid half of #514).

---

## 4. Planned phase outcomes

What the user will notice as the remaining open work lands, screen-reader
experience first.

- **Move faster + publish further.** The CSV document-tab consolidation (§1.5);
  direct publishing to external platforms (#140, gated in §2); the extended
  GLOW family (§5). *Faster keyboard navigation and accessible publishing.*
- **Solid on Windows and macOS.** Footprint sign-off on real hardware (§1.1),
  macOS offline-speech parity, better docs/tutorials (§1.4). *A dependable,
  well-documented product on its supported platforms.*

---

## 5. Deferred to QUILL 2.0

Confirmed out of 1.0 scope. Recorded so the intent is not lost; items graduate into the
open sections above when scheduled.

- **Dictation later phases** — an optional **global Windows key hook** (system-wide
  dictation hotkey), **idle-silence detection** (auto-stop on a pause), and **dictation
  intelligence** (spoken punctuation/commands). Each is sizable beyond the keyboard-only
  Hold/Locked dictation that ships.
- **Voice interaction / Hey QUILL** — **shipped 0.9.0** (all four phases + refinements:
  push-to-talk Voice Command, Voice Conversation Mode with sounders + VAD, always-listening
  "Hey QUILL" wake word, Ask Quill routing). Canonical docs: PRD §5776 "Voice input",
  user guide "Voice Interaction". Commands stay bounded by the agent safe-tool allowlist.
  The one open follow-up is a dedicated low-power keyword spotter for the wake word.
- **BITS Whisperer remainder** (tracker #680) — the consolidation shipped for 1.0; the
  leftovers (a Windows SAPI/WinRT zero-download engine, a consented cloud watch action,
  guided provider onboarding, diarization/live-mic, additional cloud kinds, and the
  Whisperer brand decision) moved to #680 when #669 closed. See also the `bw_whisperer`
  cleanup in §2.
- **Platform singleton** (tracker #680) — the Windows 11 modern primary-menu
  `IExplorerCommand` pass (SHELL-3, #525). *(Freeze/compile packaging — PyInstaller /
  Nuitka — is out of scope: the embedded-Python + Inno Setup model is the shipping
  approach.)*
- **Direct publishing (#140)** — publish a finished document/audiobook to WordPress and
  other platforms; a long-term, likely-**Quillin** integration; early design in
  `docs/design/publishing/`.
- **Remaining ChapterForge surfaces** — Auphonic post-processing, RSS podcast feeds,
  SFTP publishing, and MusicBrainz / Open Library metadata lookup.
- **ElevenLabs Tier-2/3 extras** — live streaming Read-Aloud refinements (SDK streaming,
  sentence prefetch, an aggressive `tts_cache`, a persistent "reading via ElevenLabs
  (cloud)" indicator); voice management / cloning / design / server-side pronunciation
  dictionaries; and the SFX / voice-changer / generation-history surfaces (if ever built,
  as **optional Quillins**, not core). QUILL narrates with the account's existing voices
  and does **not** clone.
- **Native Google Docs support** — read/write/round-trip Google Docs (Drive API, OAuth,
  accessible doc model); spec in
  [`QUILL-Native-Google-Docs-Support-PRD.md`](QUILL-Native-Google-Docs-Support-PRD.md).
- **Extended GLOW family (§1.2)** — the core GLOW suite **shipped (experimental opt-in) for
  0.9.0** (PRD §5.92); what stays future is the extended family: ACB Large-Print
  Guidelines / Microsoft Accessibility Checker / WCAG 2.2 AA document-audit profiles
  (#528–#534) and the WATCH-8 GLOW watch action (#566), re-homed on QUILL's invariants.
  GLOW's server/Keycloak/Office-add-in/MCP surfaces stay in the GLOW product
  (`s:\code\glow`); QUILL takes the authoring-time checks.
- **OCR / document-conversion depth extras** — the supported tool **shipped complete
  for 0.9.0** (all three tiers, the AI Hub Services tab, Review Mode v1, temp-file
  management; canonical spec now **PRD §5.93** — the standalone OCR planning PRD is
  retired). Remaining depth, on demand: the full §12-style review *workspace*
  (outline tree, per-block accept/edit, table review/CSV export, re-run pages in
  accurate mode, OCR dictionary), Datalab advanced options (page ranges, max pages,
  word/table bounding boxes, block IDs, extras, processing region, usage warnings),
  additional providers (Azure Document Intelligence, Mistral OCR, AWS Textract,
  Google Document AI, local Marker/Chandra), a provider comparison view, on-prem
  endpoint guidance, and an optional Ctrl+Shift+O shortcut.
- **Verbosity polish-backlog long tail** — the speculative slice of the ~100 addenda
  (#405–#504) beyond the shipped core/UI/modes/anti-spam; the shipped design lives in
  **PRD §5.91**. Full backlog below.

### Verbosity 2.0 polish backlog (consolidated)

The verbosity engine and its full 1.0 surface shipped (design in **PRD §5.91**). This is
the consolidated reference for the **deferred** polish-backlog addenda (#405–#504),
absorbed here when the standalone `verbosity-system.md` archive was retired. Issue
numbers are kept so each idea stays findable.

**Valuable candidates (build first if the range reopens):**

- **Error coaching (#416)** — turn an error announcement into a next-step hint.
- **Per-category announcement detail levels (#418)** — independent verbosity per category
  (nav / edit / search / system) on top of the global profile.
- **Markdown-aware (#427) / Code-aware (#428) verbosity** — context-sensitive
  announcements when editing Markdown or source.
- **"Undo available" cues (#502)** and richer **destructive-action warnings (#501)** (the
  confirm dialog ships; the spoken cue is the increment).
- **Boundary announcements (#419)** and **progress-announcement controls (#420)**.
- **Details-on-demand (#417)** beyond the existing status-query commands.

**Themed reference well (speculative; build only on demand):**

- *Settings UX:* searchable settings (#406), recipes (#407), bulk edit (#464), undo for
  settings (#465), change history (#466), export preview (#482), import-conflict wizard
  (#483), "try without applying" (#484), reset granularity (#481), explain-my-settings
  (#446), test-my-settings (#467), recommended settings (#468), persona setup (#469).
- *Packs:* community pack preview/diff (#442), trust labels (#443), copy-as-user-template
  (#444), pack-author mode (#461), built-in sample QVPs (#462), conflict checker (#445).
- *Modes / recipes:* focus mode (#487), review mode (#488), session profiles (#485),
  time-based quiet hours (#486), temporary boost (#436), training mode (#438).
- *Privacy / support:* privacy controls (#448), private-document mode (#449), export
  support bundle (#447), copy debug summary (#478), report announcement (#479), developer
  trace verbosity (#495), performance knobs (#496).
- *Output niceties:* last-important announcement (#452), pin status (#456), smart status
  rotation (#457), favorites (#455), labels (#473), per-announcement suppression
  (#471/#472), earcons-with-text (#453), learn-sounds mode (#454), status badges (#497),
  braille status cell (#498), before/after announcements (#500).
- *Content / localization:* friendly names (#440/#477), microcopy style (#490),
  use-my-words labels (#491), abbreviation dictionary (#492), localization readiness
  (#493), readability verbosity (#489).
- *Hardware / context:* multi-monitor / presentation safety (#503), screen-reader handoff
  mode (#410), command discovery (#470), contextual help hooks (#439), hold-to-explain
  (#437), confidence-check wizard (#441).

**Recommend do not build** (the screen reader already owns these; QUILL speaks
*alongside* it and must not duplicate or fight its settings): **typing echo (#411)**,
**command echo (#499)**, **speech rate / pause knobs (#450)**, and **punctuation / symbol
profiles (#426)**.

---

## 6. Feature ledger (open work by workstream)

| Workstream | Open work |
| --- | --- |
| AI footprint & optimization (§1.1) | Live-app smoke test; Phase 1 installer-size build; Phase 0 committed numbers; macOS speech parity. |
| GLOW (§1.2) | **Shipped 0.9.0 (experimental opt-in).** Extended family (ACB audit profiles #528–#534, WATCH-8 #566) in §5. |
| OCR / document conversion (PRD §5.93) | **Free local tiers shipped 0.9.0.** Cloud tier, OCR Review Mode, Services tab in §5. |
| Platform & distribution (§1.3) | Copilot OAuth client id (deploy nicety); #525 deferred to 2.0 (#680). |
| Docs & content (§1.4) | #535–#564, #505, #522, #590, #592. |
| Table Studio (§1.5) | **Shipped 0.9.0 (experimental opt-in).** Open follow-ups: CSV as an editable document tab; real screen-reader validation pass. |
| ElevenLabs 2.0 extras (§1.6) | Live streaming Read Aloud, voice management, Tier-3 — all §5. |
| Audio Studio | **Shipped during the beta (all ten roadmap items).** Open: the human validation pass (`audio-studio-roadmap.md`) + episode-24 audio regeneration. |
| Locked features (§2) | Voice Commands, Rich Text Lens, Publishing (send), Third-Party Plugins (`bw_whisperer` kept locked/inert — not removed). |
