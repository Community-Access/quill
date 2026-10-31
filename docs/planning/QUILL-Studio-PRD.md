# QUILL Studio — Accessible Media Creation and Verification
## Consolidated Product Requirements Document (planning)

**Version:** 1.1 consolidated plan · **Date:** 2026-10-26 · **Status:** Design specification for work not yet built. What QUILL Studio already does is specified in its shipped-features PRD, [`standalone/studio/docs/prd.md`](../../standalone/studio/docs/prd.md); a requirement moves there when it ships and leaves one line here.

**Product decision:** Rename **QUILL Audio Studio** to **QUILL Studio**, maintaining the *same* application, shared source implementation, library, workflows, installation continuity and user data. The larger name reflects expansion from audiobooks into sound, images, screen demonstrations, video, live production, AI-assisted visual understanding and independently verifiable publishing. *(The rename itself is delivered: commit `529884ec`.)*

> **North-star acceptance criterion:** A person who is totally blind, using only a keyboard, JAWS/NVDA/Narrator or braille, can independently capture, construct, inspect, correct, record, mix, export, and verify a media artifact without relying on inaccessible visual confirmation. Deterministically provable properties must be machine-tested; uncertain visual/semantic judgments must be labeled and escalated rather than represented as guarantees.

**Next to build:** the recorded demonstration in [section 7A](#7a-record-a-demonstration-version-1-next-to-build): one window or the whole desktop, with chosen sounds, saved as one video file.

## 1. Decisions and evidence hierarchy

1. **Current implementation baseline:** the in-repo Studio documents: [`standalone/studio/docs/prd.md`](../../standalone/studio/docs/prd.md) (shipped requirements, including the 2.0.0 screen-capture section 4.14), the user guide, `CHANGELOG.md` and the 1.0 and 2.0 release notes beside it, and the capture ledger [`docs/design/quill-studio-capture-milestone.md`](../design/quill-studio-capture-milestone.md). These are documentation and source evidence, **not proof that each feature was tested in an installed build**.
2. **Expansion baseline:** the earlier *QUILL Audio Studio Expanded PRD* (2026-10-25) is merged into this document. Each of its requirements now sits in the section it belongs to, under a new ID where one was needed; [Appendix A](#appendix-a-requirement-id-trace) maps every old ID to its new home, or to the requirement that absorbed it. References to external products remain only as engineering evidence and licensing record (sections 10C, 13.2 and 21), never as user-facing feature referrals (section 19). The earlier Studio PRD is [`docs/audio-studio/prd.md`](../audio-studio/prd.md).
3. **Availability:** QUILL Studio 2.0.0 (the unpublished 2.2.0 build renumbered with the rename) is **built, not yet released**. Never market anything here, or in the 2.0.0 notes, as publicly shipped until confirmed.
4. **Conflict rule:** Preserve working user journeys and the shared `quill.apps.studio` implementation; these consolidated additions supersede any prior plan to create another app or to call the expanded application QUILL Audio Studio indefinitely. Windows 11-first expansion is not a decision to remove current macOS audiobook functionality. Where the merged expanded material conflicts with this document's own requirements, this document wins and the conflict is noted in place.
5. **External-tool scope:** The product specification describes QUILL Studio functionality in its own terms. VB-CABLE is the only named optional external tool/integration. Existing internal implementation dependencies are governed by engineering and license compliance, not presented as recommended companion products.
6. **Supersedes:** the committed copy of the earlier consolidated proposal, [`docs/design/quill-studio-prd.md`](../design/quill-studio-prd.md), and its coverage audit [`docs/design/quill-studio-screenshot-coverage.md`](../design/quill-studio-screenshot-coverage.md), which predates the capture work in commit `5cc0023f`.
7. **Cart Wall withdrawn:** Cart Wall (CW-001 to CW-009) withdrawn 2026-10-31 at the owner's decision. The running order (PL-001 to PL-007) and the Drop Deck engineering evidence in section 10C stay. CW-007's rule that Studio never writes over a user's file moved to PL-008, and SG-11 went with the cart wall.

### 1.1 How to read this document

- **Who this is for.** This is an engineering plan, not wording to copy into
  the app. A technical name here does not make it an appropriate button, menu
  item, announcement or help message. Section 3.1 sets the language and
  simplicity requirements for the actual experience.
- **Delivered.** A requirement the code now satisfies is replaced by one line, *Delivered: …*, naming the shipped requirement in `standalone/studio/docs/prd.md` (cited as *Studio PRD AS-n*). A requirement the code satisfies only in part keeps its full text, followed by a *Delivered so far* line and a *Remaining* line, so the planning text always says what is still to build.
- **IDs.** This document's own IDs are unchanged. Merged requirements take the prefix of the section they joined: the expanded audio-engine requirements MX-010 to MX-083 become MX-110 to MX-183 (add 100), the running order restarts at PL-001 (the cart wall, CW-001 to CW-009, was withdrawn on 2026-10-31), and the expanded gate scenarios become SG-01 to SG-13 so they cannot be confused with the repository's numbered gates (GATE-11, GATE-13 and so on in `CLAUDE.md`). Appendix A is the full trace.
- **Chords** named anywhere in this document are proposals until allocated in `keymap.APP_KEYMAPS["studio"]` and passed by the menu-accelerator, access-key, documentation-chord and family-rule gates.

### 1.2 Users

- Screen-reader-dependent podcaster working with JAWS, NVDA, or Narrator.
- Blind musician needing full multitrack arrangement and real-time recording.
- Accessibility professional documenting keyboard defects with screenshots, audio, and video.
- Teacher/presenter demonstrating software while privately monitoring screen reader speech.
- Low-vision video creator who needs magnification, framing assistance, and legible controls.
- Casual user converting audio/video and adding captions without learning a DAW.
- QUILL Radio/Cast/Editor user moving assets between familiar tools.

### 1.3 Non-goals

- Replacing QUILL Editor, QUILL Radio, or QUILL Cast with incompatible clones.
- Guaranteeing per-participant conferencing audio, browser-tab separation, or per-utterance screen-reader routing without integrations that provide it.
- Circumventing DRM, protected streams, security boundaries, or Windows permissions.
- Requiring virtual audio kernel drivers for baseline operation.
- Assuming AI image generation, hosted transcription, or enhancement services can be delivered at zero operating cost.
- Reproducing any other product's source, UI text, branding or proprietary assets (LIC-006).

## 2. Preserve the existing application's layout and behavior

### 2.1 Existing shell: evolution, not replacement

Keep the startup **book/library tree with initial focus**, Favorites, In Progress, Recently Played, Inbox, existing folders, accessible status bar (F6 and arrow navigation), full menu bar, application tray, command palette (`Ctrl+Shift+P`), F1 help, existing preferences and shared voices, the narration/build wizard, Chapter Workbench, Book Tools, Sleep Timer, Play Queue, and converter/publisher. Do not displace current keyboard expectations.

**Home design:** One application main frame with a default **Library** workspace and a simple **Create** task menu/button. Add, in sensible order: Record audio, Mix audio, Record a demonstration, Capture or inspect screen, Edit audio/video, Create an image, Run a live show, Convert, Publish and Verify. The original three journeys—**Narrate Documents, Build From Recordings, Edit a Book**—remain first-class, identically named entry points. Users may pin their most-used workflows; startup may reopen the last workspace but should not silently change existing defaults.

**Menus:** File (projects/library/import/export), Create (old and new journeys), Capture, Audio, Video, AI & Visual Inspector, Tools, View, Help. **Do not steal existing Alt menu mnemonics**; keep Alt+B Book Tools, Alt+V View, Alt+I Voices if their established menus remain. Add new commands and mnemonics only after collision testing against every window/control. Existing command palette indexes legacy and new commands. Existing `Ctrl+,` preferences and safe mode stay functional.

**Shell structure:** Native wxPython controls for tree, tables, menus, dialogs, inputs and progress. Specialized audio/video canvases supply a *parallel structured list/tree representation* with UIA roles, names, values, relationships and fully equivalent actions. A canvas or waveform is never the only means to discover/edit content. Hide visual complexity until requested rather than presenting a giant dashboard.

*Status:* a **Capture** menu now exists (Studio PRD AS-93) and the Studio wizard offers a fourth entry, Capture a screenshot (Studio PRD AS-7, AS-8). The Create menu, the task home and the other new menus remain to build.

### 2.2 Seamless rename and upgrade

- *Delivered:* display name, documentation, Start Menu shortcut, installer metadata and tray name are QUILL Studio, with the old shortcuts removed on upgrade (commit `529884ec`, `tests/unit/apps/test_studio_rename.py`; Studio PRD section 1 and P-1). *Remaining:* old names as discoverable aliases in Help and search.
- *Delivered:* `quill.apps.studio`, the shared pipelines, `%APPDATA%\Quill`, the installer AppId and runtime identity are retained (commit `529884ec`; Studio PRD REL-1 to REL-6, P-1). *Remaining:* an installed upgrade and rollback test with old books, jobs and voices (scenario D, section 15).
- Introduce an optional `studio-project` folder/schema for new productions and one-way/versioned migrations only after automated round-trip tests. Legacy `.quilljob` and existing books remain readable and editable.
- Preserve installer's ability to upgrade in place and portable zip's ability to run independently; detect and resolve old/new shortcut collisions; offer rollback and retain user data.
- Preserve macOS-supported legacy journeys. Windows-only mixer/capture functions are reported as unsupported with clear explanations, never causing the legacy app to fail at launch.
- Cross-app features (QUILL Editor, Radio, Cast, Lite, Transcribe) must communicate by stable shared APIs/asset exchange, not tight UI imports.
- Preserve existing user settings and data across every later upgrade with versioned migration tests; portable mode keeps application-local config and warns before anything needing an OS-level driver or service; per-user install, clean uninstall and separate cache/project retention choices; offline installers and bundled codecs subject to licensing and size policy, with optional models downloaded separately; checksums, accessible release notes, dependency notices, known limitations and rollback guidance with every release.

## 3. Core interaction model for totally blind users

**UX-001** Every workflow has an explicit start, review, action, independent verification and result step. Keyboard-only navigation must permit correction at any step.

**UX-002** Every parameter has editable numeric/text representation, unit, min/max, current value and reset command. Spatial operations accept coordinates, edges, sizes, offsets, timestamps and relative instructions rather than dragging.

**UX-003** Include **F6 workspace landmarks** (cycling between library, editor, sources, buses, verification report, status bar without breaking legacy F6 status behavior), carefully chosen configurable chords, context help, accelerator reference, shortcut conflict detection, and a searchable command palette. Make shortcuts discoverable *and* configurable. Avoid consuming typical JAWS/NVDA/Narrator or OS shortcuts by default.

**UX-004** The ordinary editing path uses named lists and clear actions, not a
required spreadsheet or a picture of a timeline. An optional advanced view may
show sources and outputs as a matrix and recordings as tracks and regions;
both views operate on the same saved work. Camera controls have textual labels,
and screenshot elements are available in a readable list. Every important
command is reachable from menus, the command palette and a keyboard route.

**UX-005** Never disrupt text fields with live-show hotkeys; swap active accelerators when focus is in composite edit controls. Do not reorder/remove a focused row during background activity. Do not disable the currently focused action button while a long-running task executes; handle double activation safely.

**UX-006** Announce outcomes and information the screen reader does not already provide; offer additional detail on demand rather than a routine speech-verbosity setting. High-frequency meter feedback is on-demand/threshold-based rather than repetitive speech. All important status remains reviewable as text/braille and in a searchable event log. Reuse current live status bar and speech/braille announcement service.

**UX-007** Whole-app accessibility regression testing must involve JAWS, NVDA and Narrator, keyboard-only testers who are totally blind, Windows scaling/high contrast, 8 GB RAM devices, multiple sound drivers, offline and portable configurations. Accessibility success is evidenced by executable test scripts and actual user outcome logs, not simply a WCAG checklist.

**UX-008** Start with a clear, task-focused experience and sensible defaults.
Offer extra guidance on request and an optional advanced view, both using the
same saved work. Do not make people choose a mode before starting, hide basic
actions behind advanced settings, or require an advanced view to use a screen
reader. People who need precise controls can open them and return without
losing work.

**UX-009** A control's accessible name changes the instant the *user edits* what it represents (rename, reassign, clear), focused or not, so "did that apply?" is answered without tabbing away; it never changes because *playback state* changed while focus is on it (a running-order row is not relabelled "playing" under the user's fingers, which restarts speech mid-sentence). Playback state is answered on demand instead. Acceptance: with NVDA and JAWS on a running-order row, renaming it is read at once; playing it, and it finishing, produce no re-read. (Source: TG Drop Deck `SoundButton.refresh`, section 10C.)

**UX-010** A live-updating list never removes or reorders the *focused* row; a removal that would take it is held until focus moves, after which it is silent. Measured by TG Drop Deck with an MSAA hook on a `wx.ListCtrl` under NVDA: deleting a row above or below focus raises no focus event, while deleting the focused row moves focus to a row the user did not choose. Acceptance: an up-next list draining during playback never causes an unprompted focus announcement.

**UX-011** Workspace-local bare-key accelerators (digits, Space, letters) stand down whenever a text-entry control has focus, including composite controls such as `wx.SpinCtrlDouble` whose inner edit raises no child-focus event; the accelerator table is swapped, not vetoed, because on wx 4.2 a frame accelerator fires before `EVT_CHAR_HOOK` can refuse it. Acceptance: typing a space into a title field never skips the selected running-order item.

**UX-012** Do not disable a focused button for the length of the work it starts: Windows moves focus silently to the next control, which may then become the default button. Refuse a second press with a spoken line instead, leaving focus where it was. Acceptance: pressing a long-running check twice, then Enter, never activates a neighbouring control.

**UX-013** An announcement raised by a menu command waits until the menu has closed and focus has settled, so the screen reader's own focus announcement never talks over it. Outcome sentences put the state first ("Recording started") and never read out a full path; the path is in the status bar and the report. Acceptance: starting a recording from the menu with NVDA and JAWS, "Recording started" is heard whole. (Source: TG Drop Deck `CHANGELOG.md` lines 40-55, where reading the file path cut off "Recording started"; ours, REC-016.)

**UX-014** A control kept in step with a list selection, such as a mute or solo check box that shows the selected row's state, is updated under a guard, so a change the app makes never runs the handler meant for a change the user makes. `SetValue` on a `wx.CheckBox` can raise `EVT_CHECKBOX` and write the shown value back. Acceptance: arrowing through the Mixer's list of sources changes no mute state. (Source: TG Drop Deck `CLAUDE.md` lines 249-262, where arrowing past rows muted them silently.)

**UX-015** Every Studio preference has a behavioural test that changes it and observes an effect; a setting that is saved and loaded but read by nothing fails. This goes beyond the settings-vocabulary gate, which checks names only. Acceptance: one test per preference, and removing the code that reads a preference fails its test. (Source: TG Drop Deck `CHANGELOG.md` lines 742-753 and `mac/CLAUDE.md` lines 725-730, where "Hear yourself through" was saved, loaded and read by nothing.)


*Delivered so far (UX-005, UX-012):* the screenshot editor, inspector and note dialogs refuse a second press with a spoken line instead of disabling the focused button (Studio PRD AS-113). *Remaining:* the same contract across every long-running action in the shell.

### 3.1 Keep the everyday path simple

These are proposed product requirements, not a claim that the new workflows
are already built.

- **Start with a person's goal.** Offer actions such as **Record my voice**,
  **Improve a recording**, **Put recordings together**, **Add captions** and
  **Save a video**. Existing audiobook journeys remain easy to find. Do not
  open with an empty technical workspace or require a person to understand
  tracks, buses, codecs or a production timeline before doing a first task.
- **Ask only what the task needs.** Choose safe defaults, explain any
  consequential choice in one short sentence and let the user review the
  result before replacing, uploading or publishing anything. Avoid a chain of
  confirmations for reversible choices; ask explicitly when material is
  deleted, overwritten, sent online or published.
- **Name the result, not the machinery.** Examples for design and usability
  testing, not final strings or key assignments:

  | Instead of leading with | Start with | Extra detail when requested |
  |---|---|---|
  | Input routing / bus | Choose what to record | Sources, destinations and separate outputs |
  | Destructive or ripple edit | Remove this part | Whether later sound moves; edit scope |
  | Encoder / container | Save as MP3 or Save as video | Format, codec and quality |
  | Diarization | Who is speaking | Speaker detection and its limits |
  | Loudness normalization | Make speech easier to hear | Measured level and target |
  | Verification / probe | Check my finished file | File properties and checks performed |

- **Make help useful at the point of need.** F1 explains the current control;
  optional more-detail help explains unfamiliar terms with examples. The
  screen reader already announces focus and control names; speak only what it
  does not already say. Errors say what happened, whether work was saved and
  what the person can try next.
- **Advanced is an invitation, not a different product.** Show precise time,
  source/output choices, track controls, effects and batch options when
  requested, with descriptions and keyboard access. Advanced changes are
  reflected in the simple view when it can represent them; otherwise the
  simple view explains the limitation without discarding or rewriting work.
  Switching views never resets settings, changes an output or hides errors.
- **Test the experience, not just the labels.** In moderated keyboard and
  screen-reader tests, a first-time user records a short message, removes a
  mistake, saves a copy and locates it without knowing production jargon.
  Another user mixes speech and music, and an experienced user sets precise
  levels and time ranges. Record task completion, missteps, needed help and
  actual output; test JAWS, NVDA and Narrator and retain the results. A simple
  default is not accepted if it silently changes work, excludes advanced
  users or requires sighted assistance.

## 4. Persistent tray and background control

**TRAY-001** Extend the existing tray rather than starting a second daemon. Tray menu must expose: Open QUILL Studio, recording status, Start/stop/pause recording, marker, mute mic, mute public bus, private monitor toggle, active scene, take screenshot, instant replay, recent projects, current background jobs, verification summary, Safe Mode state, Preferences, Exit.

**TRAY-002** Maintain existing opt-in Alt+F4-to-tray and safe close rules. Recording can continue with window minimized/hidden; exit/Windows logoff prompts and checkpoints active sessions as technically feasible.

**TRAY-003** Tray icon has reliable accessible name and descriptive status via Windows shell/UIA; no action accessible solely via right-click. All tray operations are also available through main-frame menus, global hotkeys (opt-in), and command palette.

**TRAY-004** Global hotkeys use runtime collision detection, a keyboard-accessible configuration screen and clear feedback when another application intercepts a chord. Emergency stop is separately discoverable and robust. Global hotkeys should not steal keys needed for screen readers.

**TRAY-005** Status: `Recording 00:12:31; microphone live; application audio live; screen-reader audio private; frames dropped 0; disk estimated 43 minutes remaining`. The live status must be queryable without stealing focus or contaminating recordings.

**TRAY-006** System-wide hotkeys (transport and emergency keys used from another program) are opt-in, refuse any chord without a modifier (a bare global key steals that key from every program), are handed back with one documented key, and are checked at startup: the app briefly registers each of its own global chords and releases it, and names any chord another program already holds, because a key held elsewhere never arrives and Windows tells nobody. Acceptance: a chord pre-registered by a test process is named in the startup report; the app's own global chords are not reported against themselves. Tests that do this carry the `machine_global` marker.

**TRAY-007** Every safety-critical command (microphone on/off, MUTE AUDIENCE, stop all) has a second default chord, because a screen-reader add-on's keyboard hook can swallow a key invisibly. Acceptance: each such command has two bound chords in the keyboard reference, and the Key Describer names both.


**TRAY-008** No settings reset silently and no unexpected new global hotkeys after upgrade.

*Delivered so far:* the tray offers Take a screenshot, Review screenshot and Cancel pending screenshot (Studio PRD AS-112) and Studio > Minimize to Tray, Ctrl+Alt+T (Studio PRD AS-66); four opt-in system-wide screenshot keys with no defaults, configured in a keyboard-accessible manager that reports a chord another program holds (Studio PRD AS-111), which is TRAY-004's collision feedback for that allowlist. *Remaining:* everything else in TRAY-001 (recording, markers, mutes, scenes, jobs, verification, Safe Mode state), TRAY-003's accessible-status audit, TRAY-004's emergency stop, TRAY-005, TRAY-006 and TRAY-007. Section 7A adds the first recording items.

## 5. Audio source routing, recording and VB-CABLE

**MX-001** Native capture: microphones, Windows render endpoints, system loopback, supported per-process/process-tree loopback, local media players, virtual input/output devices and supported remote sources. Show what can actually be captured and why something cannot.

**MX-002** Separate **private monitor**, **program/live broadcast**, **main recording**, **isolated stems**, **cue/preview**, and user AUX buses. Each source/bus has independent gain, mute, solo, monitor, record-arm, per-destination send and destination device. Source/list aliases are stable across reconnects.

**MX-003** Default screen reader speech to **private only**. Allow intentional recording/broadcast of screen reader speech for demonstration, but require explicit destination choice and audible/text confirmation. No unsupported promise of independent per-utterance splitting from one screen-reader process.

**MX-004** Integrate **VB-Audio VB-CABLE** as a user-installed and supported optional solution—never silently bundle/install a driver or require it for basic microphone/loopback work. Detect CABLE endpoints, allow named source/destination mapping and provide wizard-based test/recovery. Spell out the counterintuitive nomenclature: *CABLE Input* is the Windows playback device QUILL sends to; *CABLE Output* is the Windows recording device another app receives from.

**MX-005** **Routing Setup Wizard**: choose desired outcome (podcast, conference call, demo, livestream, accessibility test), discover sources, choose device(s) and optional VB-CABLE routing, play safe probe to chosen destination, measure return capture where feasible, check feedback/double-capture, show routing diagram *as an accessible textual bus table*, optionally verify with a second participant/receiving app, save preset. State whether a complete end-to-end test was possible; no false-positive passed badge from mere endpoint detection.

**MX-006** On device removal, driver sample-rate changes, process restart, crash or OS default-device switch: preserve identity and project settings; announce degradation, protect active media files, attempt a configured fallback *only when privacy routing cannot become broader*. Record start/stop/event stamps and sample dropouts to integrity log.

**MX-007** Provide audio-interface ASIO/WASAPI shared/exclusive capabilities based on tested feasibility, buffering/latency diagnostics, clock-drift correction, and feedback loop detection. Favor a native real-time helper process for timing-critical capture/mixing, bridged to wxPython by versioned IPC; do not do real-time DSP on the GUI thread.

**MX-008** Cue, user monitoring and verification speech may never enter public/recording buses unless users expressly select them; lock default privacy behavior and enforce negative routing assertions in test harness.

The expanded PRD's **Accessible Audio Routing and Mixing Engine (AARME)** requirements follow. They refine MX-001 to MX-008 rather than replace them; where both speak to the same point (for example MX-003 and MX-122 on screen-reader privacy), both apply.

### 5.1 Source model

**MX-110** Enumerate microphones and other Windows input endpoints with stable endpoint identifiers.

**MX-111** Enumerate available output endpoints and audio sessions; clearly identify non-capturable and unsupported sessions.

**MX-112** Support Windows endpoint loopback (aggregate system playback) and process-tree loopback where OS/build supports it.

**MX-113** Explicit sources: microphones; individual processes/app process trees; aggregate system audio; JAWS/NVDA/Narrator sessions where detectable; local playback; media clips; virtual devices; external capture interfaces; supported remote streams.

**MX-114** Distinguish source *identity* (logical saved configuration) from session PID and endpoint instance, so scenes survive process/device restarts gracefully.

**MX-115** Assign user aliases and stable source hotkey slots; do not silently renumber on device reconnect.

**MX-116** Support mono/stereo/multichannel labels, sample-rate conversion and clock drift handling.

**MX-117** No arbitrary product-level source cap; expose resource-based performance guidance and overload alerts.

**MX-118** Show source status as connected, missing, unsupported, silent, clipped, muted, armed, actively recorded, routed or suspended.

### 5.2 Independent destinations and routing

Each source has a routing matrix with independent sends to:

- **Personal monitor bus:** headphones/speakers for user, with per-bus destination.
- **Audience/live bus:** conference, stream or external transmission *only where an output device or integration is configured*. No promise of directly injecting sound into every application.
- **Main recording bus:** stereo or configured multichannel mixed capture.
- **Isolated recording stems:** pre/post-fader selectable track recording for later repair.
- **User-created buses:** AUX/music/cues/communications/broadcast submix.

**MX-120** Matrix sends independently enable/disable; per-send gain (and optional pan) may differ.

**MX-121** Input/source mute, bus-send mute, monitor mute, and operating-system session mute are separate clearly named operations.

**MX-122** Default screen-reader routing: private monitoring ON, audience OFF, main recording OFF; do not silently turn on recording of speech in a new scene.

**MX-123** Always preview or confirm a scene that newly routes private audio to public output, without requiring confirmation for safe routine changes.

**MX-124** Allow record selection of clean mix, intended narration mix, isolated source tracks, or all; filenames and track names reflect origin and bus.

**MX-125** Source duplication into multiple destinations must prevent accidental doubled audio due to aggregate/system plus per-process capture overlap. Provide routing graph warnings.

**MX-126** Monitor loopback latency and detect probable feedback; warn or automatically block high-risk feedback routing when safely detectable.

**MX-127** Provide a **programme output**: the whole show (running order, microphone, captured sources) on one chosen endpoint for another program on the same machine to pick up, distinct from any per-source or main output. Monitor-only material (cue tones, previews, private screen-reader speech) is never in it. Routing help explains virtual-cable naming in the user's terms ("CABLE Input" is where this app *plays*; "CABLE Output" is what the other program *records*), because TG Drop Deck found users read it backwards first time. `Ctrl+Shift+W` (proposed) reads where every bus currently goes. Acceptance: with the running order on one card and the monitor on another, the programme output carries the running order *and* the microphone, and carries no cue tone.

**MX-128** **Cable test:** play a short tone into the chosen output while recording the chosen far-end input, and report one of three results: nothing came back (the two ends are not one cable, or it is muted), it came back with gaps (count and share lost), or it came back clean (with its level). Opens its own streams, never the live path; refused while recording or with any audience route live, with the reason spoken. Acceptance: a deliberately undersized output buffer into a virtual cable is reported as gapped even when the driver reports no underrun.

**MX-129** **Mix-minus send** to a call or conferencing program: the programme less one named participant source, so a caller does not hear themselves. The excluded source is held by stable logical identity (MX-114), never list position or display name; if it cannot be resolved the routing report says, in words, that nothing is being excluded. Acceptance: renaming or reordering sources never silently changes who is excluded.

### 5.3 Per-source controls

**MX-130** Gain adjustment via slider and numeric field with units; channel linkage, pan, trim, polarity option, source enable, mute, solo, solo-safe, arm, monitoring, routing, peak-hold reset.

**MX-131** Effects slots: EQ, high-pass, noise gate, compressor, limiter, de-esser/noise reduction where supported, delay/latency adjustment; bypass and undo.

**MX-132** User-selectable pre/post-fader bus send and pre/post-FX isolated recording.

**MX-133** Link sources into named groups; group volume and mute without losing individual state; relative trim preserved.

**MX-134** Ducking (source or bus sidechain) with attack/release, threshold, target, preview and spoken summary.

**MX-135** Smooth gain/mute ramps to avoid discontinuities; latency/CPU and dropouts made observable.

**MX-136** Accessible peak/RMS/LUFS queries on demand and configurable clipping alerts.

**MX-137** All changes reflected simultaneously in accessible text and visual meters, with throttled updates.

**MX-138** **Event ducking** in addition to MX-134's level sidechain: the running order ducks while the microphone is *open* (keyed by the open state, not by voice level, so the first syllable is never clipped and a cough never ducks the music). Default depth −9 dB, configurable; a duck shared across output devices so routing the running order to a second card does not silently disable it; monitoring is summed after the duck so the presenter's voice never ducks itself; cue and preview buses neither duck nor are ducked. `Ctrl+D` (proposed, Live Show scope) toggles event ducking; the new state is an action outcome (spoken and brailled). Acceptance: rendered-sample tests confirm the duck depth claimed, with no sound card present.

**MX-139** Every effect parameter, built-in or from a hosted plug-in (EDIT-008), is exposed as a row in a native list or a native numeric control, in plain words with real units, so a plug-in whose own window no screen reader can read is still fully operable. The reader voices value changes from the native control; the app does not announce them as well (it speaks only what the reader cannot).

### 5.4 Screen reader speech architecture

**MX-140** Detect known screen-reader audio processes/sessions where technically possible, but identify that session capture alone cannot classify speech as 'demo' versus 'private mixer notification'.

**MX-141** A private versus broadcast speech split requires an explicit technical boundary: separate output devices/speech instances, audio session routing supported by source, or an integration agent that supplies distinct speech streams.

**MX-142** If such separation is unavailable, label the feature *not independently routable* and offer safe presets instead of promising impossible speech segregation.

**MX-143** Screen-reader speech may be intentionally captured and included for tutorial/demo mode, with clear recording-state feedback.

**MX-144** Prefer notifications through existing screen reader output; give users an option to silence announcements during active takes and retrieve status with a shortcut.

**MX-145** Automatic privacy reversion when a demonstration-scene ends or live endpoint disconnects, subject to explicit scene policies.

### 5.5 Keyboard system and memorability

**MX-150** `Ctrl+Alt+M` opens mixer (suggested; configurable/conflict-detected).

**MX-151** Mixer-local keys: Up/Down source; Space mute; Left/Right fine gain; Shift+Left/Right coarse gain; S solo; H personal monitor; L audience; R mixed recording; I isolated recording; E effects; P pan; F find; Enter details; F1 help.

**MX-152** A configurable prefix mode performs `prefix → source slot → action` with timeouts, cancellation, announcement of selected source, and no injection into focused editor.

**MX-153** Press `?` or F1 for current-mode cheat sheet; provide mnemonic alternative and command search for all shortcuts.

**MX-154** Distinguish `Space` source mute from `Ctrl+Space` app transport play/pause; shortcuts must be context-aware and user remappable.

**MX-155** Persistent source slots survive reconnect; announce aliases (e.g., “2 JAWS, excluded from recording”).

**MX-156** Global media controls disabled until explicitly enabled; detect conflicts with screen readers, applications and Windows.

**MX-157** Provide optional external controller/MIDI binding at later phase, with equivalent keyboard control.



### 5.6 Scenes and safety

**MX-160** Save/load scenes (Podcast, Accessibility Demo, Online Presentation, Music, Private Editing; unlimited user scenes).

**MX-161** Scene includes logical sources, available device resolution strategies, routing matrix, effects, monitoring, level, record-arm states and privacy classification.

**MX-162** Preflight and preview show all affected source/destination changes; changed public routes flagged.

**MX-163** Missing devices handled through user-selectable fallback, no silent rerouting to live audience.

**MX-164** Version scenes and permit undo previous state; scene storage human-readable JSON with schema validation, secrets excluded.

**MX-165** Scenes may be exported and imported without exposing credentials or device-specific personal data by default.

**MX-166** **Spoken go-public preflight.** Any command that newly sends audio to an audience route (or starts a recording intended for publication) first produces one summary: where it is going, what is in it, whether the microphone is in it, and every problem found, classified **Stop** (will not work; the command does not proceed) or **Warn** (will work and be spoiled: a moved file that will play silence, a microphone absent from the programme, a destination nobody is listening on). Shown in a native read-only text field, spoken and brailled as one announcement, and confirmed with Enter; a preference may skip the confirmation but never the Stop checks. Playing the next item in the running order never asks: nothing goes between a keypress and a sound. The checks live in `quill/core` with no `wx` and no network, so each is unit-testable. Acceptance: each Warn case is produced by a unit test, and a Stop case cannot be confirmed.

### 5.7 Capture, recording and reliability

**MX-170** Mix and stems simultaneously, with sample-accurate or measured-corrected synchronization targets.

**MX-171** Record to robust, lossless intermediate files and finalize selected outputs non-destructively; crash recovery on interrupted recording.

**MX-172** Start/stop/pause, pre-roll, count-in, markers, automatic level test, monitoring feedback test and disk-space preflight.

**MX-173** Show disk free space, dropped sample/underrun count, CPU pressure, file size and elapsed time in accessible status.

**MX-174** Recording consent and OS privacy permissions respected.

**MX-175** No capturing protected streams; explain silence/unavailability without implying bypass capability.

**MX-176** Audio device hot plug gracefully degrades or offers an explicit fallback; keep recording recovered tracks where possible.

**MX-177** Implement independent monitoring gain to avoid changing recording gain while user adjusts headphone comfort.

**MX-178** Provide master emergency MUTE AUDIENCE hotkey separate from STOP ALL RECORDING, both documented and confirmation-free for safety.

**MX-179** Nothing opens a microphone except the user's explicit command: not startup, not loading a scene, a running order or a saved setup. Device, gain and monitoring are saved; whether the microphone was *on* is deliberately not. Acceptance: a test asserts the open state is absent from every persisted file and that loading a scene with a microphone source leaves it closed.

**MX-180** **Silent-input detection.** A newly opened input that delivers only exact digital zeros for 2.5 s (configurable) is reported, spoken and brailled, as probably blocked (for example by Windows microphone privacy settings), naming where to look; real microphones are never digitally silent, so exact zeros are the test, not a low level. Acceptance: a stub device returning zeros triggers the message once; a quiet room does not.

**MX-181** A device that fails to open is retried as **the same device** through another Windows audio API, never silently replaced by a different device. MME truncates names to 31 characters, so a truncated name counts as a match only when exactly one full device name begins with it. Acceptance: two headsets sharing their first 31 characters are never confused; a fallback that succeeds says which API it used.

**MX-182** The engine times its own render callback and counts blocks that arrive late beyond a set factor of the buffer period, surfacing the count in MX-173 status, rather than trusting the driver's underrun report. TG Drop Deck measured a fixed 512-frame output into a virtual cable losing up to 7.4 % of the audio while PortAudio reported no underrun. Acceptance: an injected stall is counted.

**MX-183** **Live track log.** While recording, every running-order item that reaches the recorded bus is appended, with its start time, to a CUE sheet written beside the recording with the same base name (`Show 004.wav` → `Show 004.cue`, `TITLE`, `PERFORMER`, `INDEX 01 mm:ss:ff` with **75 frames per second**, not hundredths). Times come from the recording's own written sample count, never the wall clock, so a stall cannot drift the log; each entry is flushed as it is written so a crash leaves a log complete to the last item. Reuse QUILL's existing CUE writer (`quill/core/speech/chapter_io.py`) rather than adding a second. Announced: nothing per entry; the log's path is part of the recording-finished outcome. Acceptance: a forced kill mid-take leaves a valid CUE for everything before the kill; an entry at 0.5 s is written as frame 38 (rounded from 37.5).

**MX-184** An excluded process, such as the screen reader, is held by executable name, not only by process ID. While capturing, Studio checks at least every 2 s that the excluded process is still alive; when it is gone, that sound is muted at once and the capture reopens to exclude the new process. The muted gap is spoken and marked, and the recording never carries the reader in the meantime. Today exclusion is fixed to the reader's process ID when the setup is chosen (`quill/ui/studio_demo_dialog.py:531`, `quill/apps/studio_streaming.py:54`), so a restarted NVDA or JAWS is recorded, or heard by listeners, and nothing says so. Acceptance: restarting a fixture "reader" mid-recording leaves its tone absent from the whole file. (Source: TG Drop Deck `dropdeck/proccapture.py` lines 240-243 and 401-416: Windows opens a process-loopback capture for a process that does not exist, and one whose process has closed keeps running silently; neither raises.)

**MX-185** A microphone source has a channel choice: input 1, input 2, or both mixed. The default is both mixed for a device with two or more inputs. A level meter cannot show that a microphone is in one ear, so the spoken check reports it (REC-021). Today `quill/platform/windows/demo_audio.py:394` records `min(2, device.channels)` channels as they arrive, so a two-input interface with the microphone on input 1 makes a left-only demonstration. Acceptance: a fixture with signal on input 1 only records it in both channels at the default. (Source: TG Drop Deck `CHANGELOG.md` lines 1196-1233; line 668 notes that Zoom folds an input wider than two channels to mono.)

**MX-186** Mixer source queues fill to 100 ms before first use and again after running dry, so a source whose packets arrive in bursts (loopback polled every 10 ms against 20 ms mix blocks) is not zero-filled into tiny gaps, which are heard as a change in pitch. Gaps and drops are counted and shown in MX-173 status. Today `_take` in `quill/platform/windows/live_stream.py` zero-fills whatever is short with no priming, and `push` drops the oldest audio silently once a source is 2 s ahead (lines 91-93). Acceptance: a fixture source delivering 10 ms bursts into the 20 ms mix produces no zero-filled block after priming. (Source: TG Drop Deck `dropdeck/mixer.py` lines 700-716 and `dropdeck/streamout.py` lines 1633-1646.)

**MX-187** Device listing asks about each device on its own and leaves out, and logs, only a device it cannot describe, so one undecodable name (a Bluetooth headset named after a phone) never empties the whole microphone list. Today `quill/platform/windows/demo_audio.py:200` and `resolve_microphone` call `sd.query_devices()` for every device at once. Acceptance: a stub that raises on one index still lists the others. (Source: TG Drop Deck `dropdeck/mixer.py` lines 38-50.)

**MX-188** Any thread that opens a PortAudio or WASAPI stream first enters the multithreaded COM apartment, and never uninitialises an apartment it did not open. Today the spoken check's probe (`quill/platform/windows/screen_recorder_check.py:208`) runs on a background task while the setup dialog is open, and the microphone reconnect (`quill/platform/windows/demo_audio.py:440-441`) reopens on its watch thread; neither initialises COM. Verify on hardware first. Acceptance: the probe and the reconnect both succeed with a modal dialog open. (Source: TG Drop Deck `CLAUDE.md` lines 1042-1066: a worker-thread WASAPI open with a wx dialog up failed three times out of three with a misleading WDM-KS error, and worked once the worker had a multithreaded apartment.)


## 6. Audio editing, recording and demonstrations

**EDIT-001** Timeline with cursor in samples/timecode, accessible track-region list, inserts, slips, trims, splits, ripples, ripple exclusions, fades, crossfades, markers, named chapters, envelope automation, gain/pan, sidechain/ducking, silence detection, punch-in/out, loop recording, multi-take comping, noise removal and reversible processing.

**EDIT-002** Professional but discoverable controls: Ctrl+J-like configurable jump to time, seek by frame/second/minute/marker, read region start/end/duration/peak, preview before/after, undo history, nondestructive saves and autosave. Dedicated accessible keyboard tutorials embedded in help.

**EDIT-003** Effects chain list with order, enable/bypass, presets and explicitly typed parameters; loudness/true-peak/peak/noise-floor/waveform statistics spoken and recorded as text. Record per-source stems for post-production, including optional separated screen-reader track if physically or process-isolated.

**DEMO-001** Guided **Record a Demonstration** workflow: name demo, select application/window/display, choose full window or deterministic crop, choose pointer/focus highlight, select audio sources and microphone, explicitly include/exclude screen reader, privacy scan, trial recording, visual/audio preflight, start/pause/marker/stop, review timeline and output validation.

**DEMO-002** Support **audio-only demo**, **screen-and-audio demo**, **webcam + screen** and **screenshot sequence with narrated audio**. Users can record spoken descriptions then convert into captions, chapter bookmarks, slide callouts and accessible accompanying transcript.

**DEMO-003** Optional interaction-event track: keyboard shortcuts (privacy-safe redaction), focused accessible role/name, application changes, pointer/click annotations; synchronize it with captured frames/audio. Sensitive keystrokes and password fields are never logged; warn when determining sensitivity is impossible.

**DEMO-004** Automatic scene suggestions: remove dead time, create intro/outro, flag silence, clipping and mismatched audio; AI may propose edits but applies none without explicit review, undo and preview.

**EDIT-004** Project bundle export with media consolidation, license/attribution metadata and portability warnings.

**EDIT-005** Shared mixer routing state separated from timeline mix automation, avoiding unexpected live changes when scrubbing project playback.

**EDIT-006** Overdub with latency compensation and hardware monitoring warnings.

**EDIT-007** Track freezing/render in place with reversible source and processing chain.

**EDIT-008** Plan an optional VST3 plug-in host after defining and validating the accessibility safety contract, sandboxing and crash isolation; inaccessible third-party GUI must never block core editing. The detailed compatibility and release conditions are in PP-009.

**EDIT-009** Multitrack music: instruments/voice/backing tracks, synchronized stems, groups, reverb/delay sends, automation, mastering chain.

**EDIT-010** Audio file review supports silence detection, clip detection, low-level detection and channel imbalance report.

**EDIT-011** Loudness presets may include podcast/audiobook/video platform contexts with user override; avoid claiming universal platform requirements.

**EDIT-012** Opening a recording that has a same-name CUE sheet beside it (MX-183, or one made by another program such as TG Drop Deck) offers its entries as proposed chapters in the Chapter Workbench, using the existing Keep mine / Replace choice; the CUE can also be published with the audio for services that read tracklists. Acceptance: record a show with three running-order items, open the recording, and the Workbench proposes three chapters at the logged times.

## 6A. Recording-to-production parity: detailed workflows

**Status and scope:** The following are planned requirements, not a claim that Studio currently implements or has tested them. They refine, rather than replace, sections 5–10B. They capture the user workflows described in the [MediAccess Part 2 article](https://hartgenconsultancy.com/introducing-mediaccess-part-2-from-recording-to-finished-production/), studied as public product evidence, not as code, interface text or a promise to reproduce another product. Existing delivered capabilities remain governed by the shipped-features PRD. The accepted release order and the limited first demonstration-recording milestone in section 7A are unchanged; these requirements belong to subsequent recording, editing, caption and publishing increments. No exact shortcuts, supported devices, service pricing or release dates are implied.

### 6A.1 From first recording to synchronized sources

**PP-001 — A small first success.** Offer a guided microphone-only path: select a device, explicitly open it for a short test, adjust the selected Windows input level where supported, hear the test, record, pause/resume, stop, name the destination and open the result for review. Reuse a shared accessible Windows sound-control surface where available, distinguishing system input level from Studio's recording and monitoring gains and providing a safe recovery path for screen-reader output. Explain low level, clipping and background noise without claiming every defect is detected. Provide a configurable, conflict-checked global start/stop route, an optional pre-start cue and a distinct pause/resume action. Paused time is absent from recorded media; show when a level control is unavailable or changes a system-wide setting. A first recording does not require setting up tracks, video, an account or cloud services.

**PP-002 — Mix and retain sources.** A user can select microphone and system output together, set their independent contributions, make and hear a test, and record a mix without a hardware mixer. If isolated stems are selected, save them in addition to the mix against the same session clock, including video-only and separate microphone/system audio when requested and supported. State explicitly which outputs exist and whether synchronization was measured, corrected or is unknown; do not imply screen-reader speech was included when its output was not captured.

**PP-003 — Interface inputs.** Discover and name individual inputs on supported audio interfaces, including ASIO where a licensed, distributable and tested adapter is available. Let the user select inputs, monitor a mix and retain individual WAV stems on one capture clock; disclose sample rate, channel mapping, latency and unavailable inputs. Test the actual driver/device combinations, clock drift and alignment rather than promising universal ASIO support. Failure to open an input is reported and never silently substitutes a different device.

### 6A.2 Precise, nonvisual audio editing

**PP-004 — Listen, locate and preview.** Navigate by configurable coarse-to-fine time increments, including subsecond steps, and item and track boundaries. Offer quiet movement, spoken/brailled time, a short audio audition or continued playback from the new position. Provide held-key continuous audible scrubbing with predictable release/stop behavior and a fallback where a screen reader or global shortcut intercepts keys. Set selection boundaries, audition the selection and preview the proposed join with context on both sides before committing a deletion; adjustments and cancellation leave audio unchanged.

**PP-005 — Personal bookmarks.** Maintain named bookmarks per file or project, with create, list, rename, delete and exact-time navigation. Persist each change atomically as soon as it is accepted, without saving or exporting media; report persistence failures. Bookmarks are fixed timeline times, do not follow ripple edits, are distinct from exported chapter marks and never alter audio. Explain what happens when an edit leaves one beyond the new duration: retain its stored time and report it as outside the playable range until the user moves or removes it. Reopening restores the same names and times.

**PP-006 — Items and tracks.** Split nondestructively; name, select, copy, cut, paste, move, join and remove items with session undo/redo. Provide an accessible ordered track/item list, empty track creation, importing, recording a new track while monitoring the project, track naming, mute, multi-track solo, gain, pan, tone, duplication, reordering and exact item nudges. Support gain, pan and tone for either an entire track or a selected passage. Find tracks by name or number and allow up to ten user-assigned, conflict-checked track-jump shortcuts. Warn that speaker monitoring can bleed into a microphone and offer headphones or an explicit alternative.

**PP-007 — Replace without ripple.** An overwrite of a copied item begins at the destination item's start, affects only the destination track for the copied duration and leaves the shared project clock and all other tracks unchanged. Explain how much destination material will be replaced, including any portion extending beyond the original item; preview and confirm before commit. Preserve non-overlapped material, handle gaps and track ends explicitly, and apply an optional short boundary transition only where sufficient material exists. Undo restores the original arrangement exactly.

**PP-008 — Choose project or direct editing.** Default to a recoverable nondestructive project whose original media is preserved and whose edits survive reopening; export produces a separate listening copy. Offer a clearly labeled, explicitly chosen direct-file mode for a supported audio format: Save replaces the source only after a confirmation describing the irreversible consequence, and Save As writes a separately named copy. Preflight format, write permission and space; use a recoverable temporary output and atomic replacement where supported, never destroy the original on failed rendering or replacement, and report errors. Session undo/redo is available while editing; do not promise recovery of the previous file after an explicitly confirmed successful overwrite.

**PP-009 — Levels, analysis, transitions and plug-ins.** Provide selected-passage gain in dB, independently readable left/right peak meters, three-band low/mid/high equalization, and local analysis for peaks, silence, potential clipping, stereo balance and low/mid/high spectral distribution. Describe these as measurements or indications, not guaranteed repairs. Provide auditionable fade-in and fade-out shapes and a crossfade whose safe duration is limited by available material and preserves intended project timing; report a shortened or unavailable transition. After the EDIT-008 safety gates, target installed 64-bit Windows VST3 effects through an isolated host, with an accessible list, bypass and controls for parameters the effect actually exposes. Distinguish discovery, load success and accessible parameter coverage; report crashes, unsupported effects and missing parameters. Do not promise accessibility of a plug-in's own window, presets, licensing or routing, nor support VST2, 32-bit or other formats as part of this target. Explain third-party code and trust risks and record licensing/redistribution decisions before release.

**PP-010 — Speech over music.** Given a selected speech interval and an independently selected background track, preview and apply editable gain automation that lowers the background by a user-specified dB amount, fades down and restores it using user-specified durations. Retain both sources and their alignment; reject or explain impossible intervals and transition lengths, and allow reversal without altering source media.

**PP-011 — Chapters and audio delivery.** Edit named, time-based export chapters independently of PP-005 navigation bookmarks. For arbitrary local recordings, reuse the family's chapter workbench and offer reviewable pause-based or transcript/topic-based proposals, with explicit sidecar versus embedding choices; preserve authored chapters and audio on cancellation or failure, and disclose any cloud transcription before use. Render a user-selected set of tracks separately or export the whole project; state which output contains which tracks and chapters and report unsupported chapter/container combinations. Offer lossless WAV/FLAC for further editing and MP3 for a smaller listening copy, explaining the quality and compatibility trade-offs. Verify output streams, duration and chapter metadata where applicable; keep the project and source files.

### 6A.3 Captions, visuals and finished video

**PP-012 — One transcript, multiple outputs.** Transcribe selected audio or video with an explicitly chosen available local or consented online provider. Preserve timed segments and editable speaker labels in a reopenable caption project; allow keyboard navigation, playback of the corresponding media and correction without retranscribing. Export plain text, timestamped text, SRT/VTT and the editable project from the same corrected content. A no-separate-key hosted option is a product goal only if a funded, privacy-reviewed service is actually available; otherwise disclose setup, provider, credentials, cost and availability and retain local/offline options where supported. Never embed shared service secrets in the client or imply online processing is free.

**PP-013 — Caption timing and outputs.** Review individual captions against matching audio with an optional non-exported cue at their scheduled start. Adjust one caption or shift the set, preview the result, and validate negative times, reversed durations and overlaps. An optional provider may propose timing for a user-selected short clip after explicit consent; disclose exactly what is sent and require acceptance of the suggestion. Export an SRT/VTT sidecar, optional selectable subtitles in a supported video container, or burned-in captions; also support a still image plus audio and captions as an MP4. Report empty captions, overlaps and excessive reading speed. Inspect the *rendered* result at chosen times for presence, cropping and possible occlusion, distinguishing objective checks from uncertain visual descriptions. No transcript or model result is represented as proof of accurate wording or placement.

**PP-014 — Screen, camera and screenshot confidence.** Combine an explicitly selected display or named window with selected microphone/system sources and an optional webcam inset with accessible position and size controls. If the requested window cannot be captured, stop and explain; never silently capture the full display instead. A short test can check audible balance and measured A/V alignment and, with the user's consent, periodically report uncertain face/framing observations. For screenshots, preserve the existing named-window/display, delayed capture, cue, naming and inspection workflows; optional grounded questions and revisions must preserve the original, save a separate version and offer comparison. Exact text, numbers and image revisions require human review rather than a guarantee from AI.

**PP-015 — Inspect and repair video.** At the current project time or across a selected range, describe user-requested frames or sampled moments with their positions on the full project clock; allow follow-up questions and direct inspection of a chosen moment. Report sample intervals and uninspected spans; sampling cannot prove every frame. Independently of cloud analysis, offer local media inspection for duration, dimensions, frame rate, audio presence, decoding errors, persistent borders, black intervals and unusually static intervals. Findings are review candidates, not automatically defects. Offer previewable border removal and audio normalization to a separate copy or a proposed repair plan, preserving the source; explain uncertainty, require approval and verify the resulting file.

**PP-016 — Publishing presets and conversion.** Offer understandable video export presets for existing project settings, general publishing while retaining source dimensions and frame rate where supported, a smaller sharing copy bounded by 1280 × 720, and a higher-quality intermediate for further editing. Explain the readability, quality and file-size trade-offs; no preset uploads or chooses a destination. Verify the actual encoded size, frame rate and streams, and report any required deviation. Convert supported audio, video and images to separate files with format guidance including WAV/FLAC, MP3/M4A, MP4 and PNG/JPEG; identify unsupported conversions and never silently overwrite the source.

**PP-017 — Image creation and review.** Start with purpose, audience and content, offer reviewable written approaches, then generate only after explicit user approval and any required provider consent. Describe the generated artifact, support focused questions and specific revisions, compare versions, and save a named accepted copy with provenance and accessible description. Preserve earlier versions and warn that generated text and numbers may be incorrect.

### 6A.4 Assistance, service boundaries and acceptance

**PP-018 — Help and learning.** Keep native keyboard and screen-reader controls usable without a learning mode. Provide extra contextual guidance on request rather than automatically repeating control information or introducing a routine speech-verbosity setting; mirror application announcements to braille. Focus-specific help explains purpose, operation, expected outcome and checks, and Escape returns focus to the originating control. The local guide and searchable command palette remain available offline; preserve the family's F1 and keybinding conventions instead of copying another product's shortcut assignments.

**PP-019 — Optional online finishing.** Provide an optional native finishing workflow for selected edited audio, a whole file or suitable tracks, using a supported processing provider only after a privacy, licensing and feasibility review. Before transmission show exact material, destination, credentials/account requirements, likely charges or quota and obtain per-action consent; show progress, failure and cancellation. Import the result as a separate asset, retaining the originals and project. A third-party companion application is not required or presented as a prerequisite (section 19); no specific service integration or bundled allowance is promised.

**PP-020 — Offline and consent boundary.** Basic recording, playback, project/direct editing, conversion, local analysis, help and command search must not require an online account or a network request. Cloud visual description, generation, transcription, timing suggestions and finishing are separate opt-in actions, with their own disclosure and failure handling. Offline or service failure must not block local work or pretend an online result exists.

**Acceptance for this increment:** In addition to section 15's release gates, automated tests and keyboard/JAWS, NVDA and Narrator acceptance must demonstrate:

1. Make and audition a mic-only test, pause a take, reopen it and confirm the paused interval is absent; exercise failed device and output-write paths.
2. Record a known mic/system test signal and individually selected interface inputs to mix and stems; measure alignment, independent level changes and correct failure reporting.
3. Audition a selection and delete-join before commit; test subsecond movement and held-key release. Persist a bookmark, ripple-delete before it, reopen and verify its original fixed time, including the out-of-range case.
4. Overwrite one item with a different-length copied item, assert exact affected interval and unchanged other tracks and clock, then undo. Duplicate, reorder, mute/solo and nudge tracks/items using keyboard alone.
5. Test direct Save, Save As, declined confirmation and injected render/replace failures; verify the original survives failures. Reopen a nondestructive project and confirm the source is unchanged.
6. Measure selected gain, three-band controls, fade shapes, crossfade boundaries and ducking envelope on synthetic audio; test VST3 discovery versus actual load, exposed parameters, inaccessible GUI and isolated crash without losing the project.
7. Correct a timed transcript once, reopen and export each text/subtitle form; audition and shift caption timing, inspect validation errors and verify a rendered still-image-plus-audio video with captions. Confirm no review cue is exported.
8. Reject an unavailable named window without desktop fallback; inspect specified final-video frames and local analysis findings, verify a separate repaired copy, and label unsampled intervals and uncertain descriptions.
9. Exercise every video preset and selected-track export by probing the resulting files. Confirm source preservation, no implicit upload, and explicit handling of unsupported chapter metadata.
10. With network access blocked, complete local editing and help. For each optional service, verify exact-data consent, cancellation, error reporting and preservation of local originals; check focus return and avoid duplicate announcements when requesting guidance.

**Source coverage trace:** First recording and source mixing → PP-001–003; listening, bookmarks, items, project/direct modes → PP-004–008; level, analysis, transitions and effects → PP-009; multitrack, replacement and ducking → PP-006–007 and PP-010; chapters/output → PP-011; online finishing → PP-019; screen, webcam and screenshot → PP-014; transcript/captions → PP-012–013; picture/video understanding and repair → PP-014–015; video presets and conversion → PP-016; image creation → PP-017; help and local/online boundary → PP-018–020. Studio uses on-demand guidance in place of the article's automatically spoken learning mode, in line with the family announcement rule. The article's vendor-specific account arrangements, price, dates and single-screen-reader support are evidence about that product, not Studio commitments.

## 6B. Professional power without professional complexity

**Status:** Proposed additions, not shipped behavior. Study [REAPER's user guide](https://www.reaper.fm/userguide.php) for editing, routing, takes, automation, actions and rendering, and [OSARA's documentation](https://osara.reaperaccessibility.com/) for nonvisual track, item, envelope and meter feedback. These sources show useful techniques, not deficiencies in either product; no comparative accessibility or performance superiority is claimed without testing. REAPER is licensed separately and OSARA is GPL-2.0: use ideas only, not their source code, interface wording, keymaps, assets or branding without a separate licence review. Studio must not require either product or an extension.

**Product decision:** Keep Studio free and usable for local recording, editing, effects, project saving and export without a subscription, account, trial or feature-unlock payment. Optional hosted services may have actual costs, account requirements or quotas; disclose these before consent and never promise unlimited free cloud processing. Ship accessibility as part of Studio, not as a separately installed accessibility layer. The accepted section 7A milestone and phase order remain unchanged.

**SIMPLE-001 — Progressive workspaces.** Start with three plain-language tasks: record a voice, improve an existing recording, and combine recordings. Each leads to a short accessible path with safe defaults; an explicit multitrack workspace reveals tracks, routing, takes and automation without changing the saved project or blocking return to the simple view. Provide a searchable command palette and a task-oriented local guide. Do not equate fewer controls with fewer capabilities: expert operations remain reachable by keyboard, and mode changes cannot discard edits.

**SIMPLE-002 — A trustworthy place in the project.** Provide on-demand “where am I?” reporting of selected track/item, position, selection, transport, mute/solo/arm and relevant edit/ripple mode. Use named tracks and items, real accessible lists, spoken/brailled on-demand meters and warnings for clipping. Announce state changes the reader cannot infer, not a duplicate of focus/selection speech. Support noncontiguous selection and expose exactly what is selected before a group action; no waveform or color is required.

**SIMPLE-003 — Explain an edit before committing.** For delete, move, ripple, overwrite and grouped edits, offer a concise preflight identifying affected time ranges and tracks, whether later material shifts, and the expected duration change. Audition before/after joins and retain a human-readable undo history; cancel or undo restores clip placement, automation and selection. Provide project snapshots and an audible A/B comparison without overwriting media. Never alter other tracks unless the chosen scope explicitly includes them.

**SIMPLE-004 — Takes without a maze.** Record multiple takes at a selected interval, name and audition them in a list against the same project clock, choose or assemble a final performance, and keep the original takes for later revision. Explain monitoring, count-in and latency compensation, report unavailable input or missed recording, and preserve the project if recording is interrupted. Quick retake must not delete the previous take.

**SIMPLE-005 — Routing that proves itself.** Express sources, destinations and sends as accessible named lists with a readable “what reaches this output?” summary, private versus program labels, independent monitor gain, mute/solo and feedback-loop warnings. Provide a local test signal and recorded test to verify the actual path; report unavailable or unverified isolation rather than claiming privacy based on configuration alone. Keep an advanced routing view for complex arrangements without making it mandatory for a voice-and-music mix.

**SIMPLE-006 — Automation by intention and by point.** Offer task actions such as fade, lower music under speech and return it, alongside an accessible time/value/easing point list for gain, pan and supported effect parameters. Show affected interval, resulting values and existing automation conflicts before replacing points; preview, undo and preserve neighboring automation. No destructive edit or model-generated suggestion is applied silently.

**SIMPLE-007 — One job, many outputs.** Name project regions, choose the complete mix, selected tracks or selected regions, and define an explicit batch of output files with format, destination, track/region mapping and chapter behavior. Preview filenames and collisions; avoid silent overwrite, write outputs recoverably, and report success or failure for each file. Reopen or independently probe the outputs and list unverified properties. Simple export remains one action with explainable defaults; batch options are optional.

**SIMPLE-008 — Safer repeatable actions.** Let users save a named, reviewable sequence of supported local commands with explicit inputs, scope and conflict-checked shortcut. Preview all intended edits and output paths; require confirmation for deletion, overwrite, cloud transmission and publishing, preserve normal undo boundaries, and stop with the failed step identified. Do not permit imported presets or sequences to silently execute scripts, install plug-ins, send media or bypass consent.

**SIMPLE-009 — Above-and-beyond verification.** Provide an optional production check that combines local decode and signal measurements with explicit user review: missing or muted sources, clipping, unexpected silence, output duration, chapters, caption timings and actual file properties. Findings are actionable and navigable to their source; uncertain content, visual descriptions and unsampled spans remain labeled unknown. An offline test project can exercise the whole workflow without microphones, accounts or uploading a real recording.

**SIMPLE-010 — Measure simplicity and access.** In moderated keyboard-only studies with blind and low-vision participants, time and record completion of first voice recording, mistake removal, voice-plus-music mix and export. Capture missteps, unassisted completion, reversibility and screen-reader/braille outcomes for JAWS, NVDA and Narrator. Establish a baseline before setting numerical targets; no “simpler” or “better” claim is a release gate substitute for measured results. Test with assistive technology both on and off, and include existing Studio audiobook journeys.

**Acceptance:** Automated tests cover edit-scope previews, noncontiguous selections, take retention, routing isolation and failure, automation boundaries, collision-safe batch rendering and macro consent/rollback. User tests demonstrate each SIMPLE-010 journey from a clean profile without a paid dependency, verify the on-demand context and real output, then reopen the project and repeat an edit. Online-service failures must not break local workflows. Manual screen-reader results and unsupported cases remain recorded until verified.

## 6C. Accessible media finishing, conversion and transcription

**Status:** Requirements below are proposed, not a claim that the complete
workflow exists. Studio already exposes Convert Audio through the shared
conversion dialog and Generate Captions (Offline) for a selected audio or video
file, producing SRT or VTT when the selected local provider returns timed
segments. The latter is disabled in Safe Mode. The standalone Converter
offers additional video and batch capabilities; the existence of the shared
engine does not prove that every standalone option is reachable from Studio or
that a completed file is reimported into a Studio project.

GoldWave's published feature descriptions inform this work: timed and
level-triggered recording, edit operations, effect previews and presets, noise
and click repair, cue-based splitting, folder-preserving batches and
foot-pedal playback. Audacity's documentation describes real-time effects and
track mixing. Adapt the ideas, not their code, artwork, text, keymaps or
branding. See section 6B for REAPER and OSARA. The objective is a free,
independently usable local workflow with accessible proof, not an unmeasured
claim that Studio is superior.

**FIN-001 — Predictable shared conversion.** Studio must invoke the same
maintained conversion services as QUILL Converter for audio-to-audio,
video-to-audio and video-to-video, rather than copying format logic or
depending on a separately installed application. Probe the actual source,
available decoders, encoders and container combinations before offering an
output; list unavailable choices with a useful reason. Support is conditional
on the local tools, codecs, media and legal permissions: no product promise
of literally every format, DRM removal or successful decoding of damaged
files. A still-image-plus-audio video workflow is separately specified in
PP-013 and must not be inferred from audio-to-video support in Converter.

**FIN-002 — A round trip that preserves work.** From a project item, selection
or explicit file, review the chosen source, time range, destination, preset,
tracks and any conversion losses before starting. Never overwrite source media;
handle name collisions explicitly, write recoverably and retain originals.
Return a successful, independently probed output to the project only after
the user accepts it, preserving the original and a reversible project edit.
Failure, cancellation, app exit, missing tools and unavailable codecs leave the
project and source intact, show an actionable error, and never report success.
Persist or clearly report recoverable job state; do not silently relaunch work.

**FIN-003 — Batch work with usable feedback.** Support a keyboard-operable
queue of files or project regions, optional folder hierarchy preservation,
per-item destination and collision review, cancel/retry and per-item outcomes.
Report progress and completion without interrupting navigation; distinguish
failed, cancelled, skipped and successfully verified outputs. Presets identify
their processing and permit before/after audition, bypass and undo.

**FIN-004 — Audio and video transcription.** Reuse the shared speech provider
interfaces and local file transcription/caption services, plus QUILL
Transcribe capabilities where actually supported, rather than maintaining a
second engine. Accept supported audio and video, select the intended audio
track and language, and retain an explicit mapping between source time and
transcript time. Offer local installed models without an account; disclose and
obtain consent before a model download. Offer cloud providers only by explicit
action and prior consent identifying provider, exact data, destination,
retention where known, estimated cost or unknown cost, and cancellation.
Never silently fall back from local processing to a network provider.

**FIN-005 — Reviewable results, not automatic truth.** Present transcript
segments with timestamps, editable text and speaker labels when the provider
actually supplies them; mark missing timing, uncertain recognition and
unavailable diarization as such. Keyboard navigation, adjustable playback
speed, optional user-configured pedal control and short audio context let a
person review and correct each segment. Link edits to project time, preserve
the original recognition result and undo corrections. Export plain text and
supported timed caption formats; validate cue ordering, bounds and overlap
before an optional subtitle or burned-caption export. Neither a transcript nor
a caption proves accuracy without review.

**FIN-006 — AI assistance under user control.** When a compatible provider is
enabled, offer separately requested summaries, chapter suggestions, title and
show-note drafts, transcript cleanup, speaker or timing suggestions and
visual descriptions. Show source scope, provider and uncertainty, then preview
and approve each change; do not invent speakers, facts, visual events or
timestamps or silently edit media. AI processing must never be required for
recording, local editing or conversion. Consent, cost and data disclosure
apply to each outbound action; failure preserves editable local work.

**FIN-007 — Measurable acceptance.** Exercise audio-to-audio, video-to-audio
and video-to-video with actual locally available codecs, independent output
probing, project reimport and undo. Test unsupported codec, encrypted or
corrupt media, missing executable, destination collision, partial batch,
cancellation and restart without source loss or false success. Test local
audio and video transcription with no network, an absent model, an empty
timed result, speaker/timing capability gaps, editable SRT/VTT round trips and
cloud refusal, expiry and failure. Verify every outbound request is preceded
by its own consent and local work remains usable offline. Record keyboard,
JAWS, NVDA and Narrator acceptance separately; do not mark the work delivered
until evidence exists.


## 7. Screen capture and accessible visual tools

**CAP-001** *Delivered:* keyboard-triggered capture of the full desktop, a display, the active window, a named window, a UI Automation element, a guided portion or an exact rectangle; scrolling capture; timed and repeated captures; file and clipboard destinations; timestamp, window identity, coordinates, scale factor and success metadata (Studio PRD AS-93 to AS-104). Its one gap is CAP-007.

**CAP-002** **Screenshot Inspector**: identify dimensions, OCR all text with confidence and reading order, list detected UI elements and their positions, detect cut-off text and overlays, compare screenshots, ask follow-up questions about the image, find target by text/semantic description, zoom/crop via keyboard, run redaction and export alt text or detailed description.
*Delivered so far:* dimensions, local OCR with engine confidence in engine reading order, grounded follow-up questions, pixel comparison, find-by-recognised-text anchors, keyboard crop and preview zoom, redaction, alt-text prompts and description export (Studio PRD AS-103, AS-105, AS-108). *Remaining:* a listed inventory of detected UI elements and positions inside the inspector, deterministic cut-off and overlay detection, semantic target search, and a guaranteed reading order.

**CAP-003** Annotate *without drawing*: choose arrow/rectangle/spotlight/highlight/text callout, anchor to recognized UI element or percentage/coordinates, define size/style/order, preview verbally, revalidate target still exists, render to PNG/JPEG and optional layered project. Add visual magnification, cursor/focus highlight, presentation break timer and spoken countdown.
*Delivered so far:* all five annotation kinds plus numbered boxes, anchoring to named areas, recognised text or percentages, size by 1 percent steps, the text edit plan as verbal preview, PNG/JPEG/WEBP render, layered project, preview magnification and a spoken pre-capture countdown (Studio PRD AS-100, AS-108). *Remaining:* anchoring to a UI Automation element, style choices, reordering, target revalidation, cursor and focus highlight, and a presentation break timer.

**CAP-004** Provide built-in, keyboard-accessible region snipping, screen recording, zoom and annotation, capture timers, OCR, image inspection, image resizing, format conversion, clipboard transformations, command discovery, shortcut-conflict detection, and saved recording/capture workspaces. Implement these as integrated QUILL Studio capabilities with one command registry, one accessibility model and shared project state.
*Delivered so far:* region snipping, zoom, annotation, timers, OCR, inspection, resizing, format conversion, command palette coverage, registration-failure reporting for global keys, and saved capture setups (Studio PRD AS-93 to AS-111). *Remaining:* screen recording (section 7A), clipboard transformations beyond copying the image, and conflict detection against screen readers and the rest of the family.

**CAP-005** Offer **Capture and Dictate**: press screenshot hotkey, speak a description/comment, local or optional cloud transcription, return a paired screenshot + verified transcript + timestamp, copy/paste as package or export to HTML/Markdown/issue tracker. Maintain microphone routing privacy while capturing.
*Delivered so far:* a spoken note recorded on an explicit Start through the shared microphone lock, recognised locally, tied to the screenshot's hash with a timestamp, reviewed before use, and carried into the evidence bundle's Markdown and HTML (Studio PRD AS-109, AS-110). *Remaining:* a one-key capture-then-dictate flow, optional cloud recognition, a copy-as-package action, and issue-tracker export.

**CAP-006** Capture preflight: protected window/black frame, minimized/occluded content, focus lost, unexpected monitor, unexpected app title, cropping off edge, masking failures, overlapping tooltip/dialog, pointer obstruction and notifications. Report detected risks and attempt a correction or offer exact deterministic commands. Capture APIs' limitations must be exposed.
*Delivered so far:* refusal on a closed, minimized or hung window, a changed process or title, a changed display layout, a moved region source and invalid bounds; uniform-pixel reporting; stated API limitations (Studio PRD AS-99, AS-103). *Remaining:* occlusion, overlays, focus loss, pointer obstruction, notifications, masking failures, and offered corrections.

**CAP-007** **Semantic regions.** Capture a recognised part of a window (a toolbar, a dialog, a document area, a pane) found through UI Automation landmarks and OCR, rather than a geometric portion. Guided portions (Studio PRD AS-98) are geometry and cannot promise that a toolbar or dialog is wholly inside them; a semantic region must say how it was found and fail rather than guess when the landmark is ambiguous.

## 7A. Record a Demonstration, version 1 (next to build)

**Status:** built 2026-10-29 on branch `feat/studio-demo-recording`, not yet released; see section 7A.7 for what differs from this specification and what is still unverified. **Priority:** next. It is the first vertical slice of DEMO-001 and DEMO-002 (a screen-and-audio demonstration), the *screen recording* part of CAP-004, the first recording items of TRAY-001, and VERIFY-005 for one file. It reuses the capture picker, target identity rules, evidence reports, F1 help and hotkey services that shipped in 2.0.0 (Studio PRD section 4.14), and the shared FFmpeg.

**User story.** *I am a blind presenter. I choose Edge from the same list I use for screenshots, turn on "Edge's sound" and "my microphone", leave my screen reader out, hear one spoken summary that says everything is ready, press one key, demonstrate, press the same key, and am told the file is saved, how long it is, and that its picture and sound were checked. Nothing private I hear went into it unless I asked.*

### 7A.1 The journey

1. **Capture > Record a demonstration…** (also the command palette, the tray, and the Studio wizard's Capture entry) opens the Record a demonstration dialog.
2. Choose the target, sound sources and levels, frame rate, pointer and file location (REC-002 to REC-008, REC-010).
3. **Check and start** runs the spoken check (REC-011). Its result is the focused text of the dialog; Stop items block; Enter starts.
4. A countdown (default 3 seconds, 0 to 10), then recording. Studio hides to the tray by default for a display or desktop target.
5. Pause, resume, add a marker, mute the microphone, ask for status, or stop: from system-wide keys if the user assigned them, from the tray, or from the Recording status window (REC-013).
6. On stop, Studio finalizes the file, checks it independently, and speaks the result (REC-014). The result window offers Play, Open folder, Copy path and Inspect a frame (which opens the existing Screenshot Inspector on a frame extracted from the video).

### 7A.2 Requirements

**REC-001 — Entry points.** Capture > Record a demonstration…; the command palette; a tray item; and a fifth Studio wizard entry, *Record a demonstration (screen and sound, saved as one video)*, which opens the same dialog the way the Capture entry opens Capture screen (Studio PRD AS-7, AS-8). One recording at a time: a second request is refused with a spoken reason, as a second pending screenshot is today (Studio PRD AS-100). A screenshot may still be taken while recording.

**REC-002 — Choosing the target: reuse the capture picker.** The Target list is the one Capture screen builds (`list_capture_targets`, Studio PRD AS-94, AS-95), including Refresh, Show all windows and Window properties, restricted in version 1 to **a named window, one display, or the full desktop**. Active window after the delay, guided regions and UI Automation elements are not offered in version 1 (section 7A.4). Identity rules are Studio PRD AS-99's: the target is resolved again at Check and start and when recording begins, and a closed, minimized or hung window, a changed process or title, or a changed display layout stops the start with a spoken reason. A recording never broadens to a larger area than the user chose. Recording Studio's own window is allowed with a warning that the recording will show Studio's controls.

**REC-003 — Video capture backend.** One backend per target kind, chosen by Studio, with the choice and its known limits written into the evidence report:

| Target | Backend | Why | Known limits |
|---|---|---|---|
| Display, full desktop | FFmpeg `ddagrab` (DXGI Desktop Duplication) when the bundled build has it; otherwise FFmpeg `gdigrab` on the display's rectangle | GPU duplication sustains 30 to 60 frames a second at 1080p with little CPU and draws the pointer shape; `gdigrab` is in every Windows FFmpeg build | Records everything on that screen, including notifications and other windows; protected content and the secure desktop (UAC, lock screen) appear black and are never bypassed |
| Named window | **Windows.Graphics.Capture** (WGC), through a small capture helper that writes raw frames to FFmpeg's standard input | Captures that window's own content even when other windows partly cover it, follows it when it moves, and has a pointer on/off switch | Needs Windows 10 version 1903 or later (`GraphicsCaptureSession.IsSupported`) and a Direct3D 11 device; delivers frames only when the window changes, so FFmpeg must produce a constant frame rate; Windows 11 may draw a yellow capture border unless border removal is permitted; a minimized window delivers no new frames |

**GDI versus Windows.Graphics.Capture.** GDI (`gdigrab`, or `PrintWindow` as the screenshot path uses) is a CPU copy that is cheap to integrate and already bundled, but a GDI *window* capture returns black or stale frames for hardware-accelerated and DirectComposition content (browsers, modern apps), and a GDI *region* capture records whatever is on top of the window. WGC is the API Windows provides for recording one window and is the version 1 choice for window targets. QUILL has no WGC binding today: the `winrt-*` packages it already ships for OCR cover WinRT but not the Direct3D interop (`IGraphicsCaptureItemInterop::CreateForWindow`) that turns a window handle into a capture item, so spike **S1** decides between a pywinrt-plus-comtypes helper in Python and a small native helper executable built the way the native launcher is. Either must move frames to FFmpeg without touching wx. **There is no silent fallback:** if WGC is unavailable or fails, the window target is reported unavailable and the dialog offers, as an explicit choice with a spoken warning that other windows and notifications on that screen will be recorded, the display that contains the window.

**REC-004 — Frame rate.** 15, 24, 30 (default) or 60 frames a second; 60 only for display targets on `ddagrab`. The output is constant frame rate (FFmpeg duplicates frames when the source is still and drops them when it falls behind), and the evidence report records the requested rate, the measured capture rate, and the counts of duplicated and dropped frames.

**REC-005 — Size.** Native resolution by default; an optional ceiling of 1080p or 720p, keeping the aspect ratio. H.264 needs even dimensions, so an odd width or height is padded by one pixel and the report says so.

**REC-006 — Pointer.** *Include the mouse pointer* is on by default for displays and windows (`ddagrab`'s pointer drawing, WGC's `IsCursorCaptureEnabled`, `gdigrab`'s `draw_mouse`). Click highlighting, keystroke display and focus highlighting are not in version 1 (CAP-003, DEMO-003).

**REC-007 — Sound sources.** Each source is a row in a native list with its own on/off state (a state column, not a check box, per QUILL's list convention), a level from −60 to +12 dB (default 0 dB, typed or adjusted with the arrow keys, units spoken), and a live meter that is queried on demand rather than spoken continuously (UX-006):

| Source | How it is captured | Default | Notes |
|---|---|---|---|
| **That application's sound** | WASAPI process loopback of the target window's process tree, by the process ID the picker already holds | On for a window target; absent for display and desktop targets, where the user picks applications from a list of running processes that are playing sound | Windows 10 version 2004 or later. Extends `quill/platform/windows/process_loopback.py`, which today opens a 16 kHz mono capture only to measure loudness for the dictation gate; version 1 adds a PCM capture API (48 kHz stereo, timestamped packets to a sink) beside it and keeps the gate's behaviour unchanged |
| **System sound** | WASAPI endpoint loopback of a chosen playback device (the default device unless the user picks another) | Off | Everything that device plays: the screen reader, notifications, Studio's own sounds. Choosing it together with "screen reader left out" is a preflight Warn, because a loopback of the whole device cannot subtract the screen reader; the Warn names Application sound as the way to exclude it. Choosing it together with an application's sound is a Warn about doubled audio (MX-125) |
| **Microphone** | The shared input device (`load_input_device`) through `sounddevice` at 48 kHz, holding QUILL's shared microphone lock (`quill/core/dictation_owner.py`) for the whole recording | Off until the user turns it on (MX-179) | Another QUILL recording or dictation holds the lock: preflight Stop, naming the holder. Whether the microphone was on is never saved (MX-179); device and level are |
| **Screen reader speech** | Process loopback of the running reader's process tree: JAWS (`jfw.exe`, whose voice runs in the `fsSynth32.exe` it starts), NVDA or Narrator, detected as `process_loopback.READER_PROCESSES` and `sr_detect` do today | Off (MX-003). Turning it on asks for confirmation in words and in speech: "Your screen reader's speech will be in the recording, including anything it reads while you record" | Captures *everything* the reader says, which is why it is off by default (MX-140 to MX-142). While it is on, Studio says nothing through the reader except failures (REC-016), and marks each failure's moment in the marker list so it can be cut later |

**Private monitoring stays out.** Studio does not reroute anything the user hears: the screen reader, Studio's cues and every other sound keep playing where they always do. Only the sources turned on above are recorded. Studio's own sounds (countdown, start, pause, marker, stop) come from the Studio process, which is never a captured source, so they cannot reach the file unless *System sound* is on; when it is, Studio suppresses its own sounds for the length of the recording and says so in the preflight. A unit test asserts that the Studio process ID is never in the capture set. Program and private buses, VB-CABLE output and stems for live use are MX-002 and section 5, not version 1.

**REC-008 — Recording and encoding pipeline.**
- Video: one FFmpeg process per segment, writing **Matroska** (`.mkv`) so that a crash leaves a playable file up to the last flushed cluster.
- Sound: each source is captured on its own thread to its own 48 kHz WAV per segment, every packet stamped with the Windows performance counter, as is the first video frame, so the sources are aligned by measurement rather than assumed to start together.
- *Needs a code fix (2026-10-31):* the code does not use the performance counter. Each packet is placed by the wall clock (`time.time()` in `quill/platform/windows/process_loopback.py:429-437` and `quill/platform/windows/demo_audio.py:397`), and the counter that `GetBuffer` returns is thrown away. REC-022 says how this is to be fixed.
- **Pause** closes the current segment of every stream; **Resume** starts the next. A pause is never encoded as frozen video.
- **Stop** joins the segments (FFmpeg concat), mixes the enabled sources with their levels and measured offsets (`volume` and `amix`, with a limiter so the sum cannot clip), and writes the final **MP4: H.264 video, AAC-LC 192 kbit/s 48 kHz stereo, `+faststart`**. An option, *Also keep each source as its own WAV*, writes the per-source files beside it for later editing (default off).
- Target audio/video alignment: within one frame at 30 frames a second, over a 30-minute recording on reference hardware. This is a measured target (spike **S5**), not a promise.

**REC-009 — Encoding through the bundled FFmpeg.** FFmpeg is found with `quill.core.speech.ffmpeg.find_ffmpeg()` (its allowlist and search order: `QUILL_APP_ROOT\tools\ffmpeg`, the runtime's own `tools\ffmpeg`, then the data folder's) and run as a separate, unmodified program through the safe-subprocess wrapper with an argument list. Studio's release build refuses to build without it (Studio PRD P-4). Capabilities are **probed, never assumed** (`-encoders`, `-filters`, `-devices`), exactly as Convert Audio probes formats (Studio PRD AS-88): the preferred video encoder is `libx264` (preset `veryfast`, CRF 23, `yuv420p`), then Media Foundation `h264_mf`; hardware encoders are a later opt-in. If no H.264 encoder or `gdigrab` is present, Record a demonstration is unavailable and says why, pointing at Voices > Get FFmpeg.
*Licensing (LIC-004).* The bundled FFmpeg is the gyan.dev essentials build, configured `--enable-gpl --enable-version3`, so it is GPL-3.0-or-later; `libx264` inside it is GPL too. Studio runs it as a separate program, so Studio's own MIT code is unaffected, and the GPL text and source offer already ship beside every `ffmpeg.exe` (gated by `scripts/check_ffmpeg_notices.py`). A switch to an LGPL-only build would lose `libx264` and leave `h264_mf`. Videos Studio produces are the user's and carry no licence obligation from FFmpeg's copyright licence; codec patent licensing for H.264 and AAC encoders is a separate question to confirm before release (LIC-005). Nothing in this feature changes `docs/legal/`; any new bundled component would.

**REC-010 — File name and location.** Default folder: the user's Videos folder, `QUILL Studio` subfolder, falling back to `studio-recordings` in the data folder when Videos is unavailable (portable mode keeps the data-folder default). The folder is an absolute path the user can change, remembered in the app-local preferences. File name: `Demo - <short target name> - <YYYY-MM-DD HHMMSS>.mp4`, where the short name is the picker's spoken label (Studio PRD AS-95) with characters Windows forbids removed, at most 60 characters. An existing file is never overwritten (` (2)` is added). Segments live in a hidden `.studio-recording-<id>` folder beside the output and are deleted only after the final file passes REC-014. Beside the video: `<name>.verification.json` and `<name>.verification.md` (the AS-103 pattern), and `<name>.markers.txt` when markers were added.

**REC-011 — The spoken check before recording.** *Check and start* runs every check below in the background, then puts one summary into a read-only text field and moves focus to it, so the screen reader reads it once; Studio does not announce it as well (GATE-13). The summary says, in this order: what will be recorded, which sounds are in it and which are left out (always naming the screen reader's state), where the file goes, then every problem, each marked **Stop** (the recording will not work; Enter does nothing until it is fixed) or **Warn** (it will work and may be spoiled). The same structure as MX-166; the checks live in `quill/core` with no wx and no network so each is unit-tested.

| Check | Stop when | Warn when |
|---|---|---|
| Target | Closed, minimized, hung, identity changed, or the display layout changed | Window is Studio itself; target is a full desktop with more than one display |
| Video backend | The one-second trial grab fails | Every pixel of the trial grab is the same colour (possibly protected or black content) |
| Each chosen sound source | It cannot be opened, or the microphone lock is held | It delivers only exact digital zeros for 2.5 seconds (probably blocked, for example by Windows microphone privacy; MX-180); an application that is simply quiet is reported as quiet, not as a fault |
| Screen reader rules | — | System sound is on while the screen reader is left out; screen reader speech is on (a reminder of what that records) |
| Doubled sound | — | System sound and an application's sound are both on (MX-125) |
| FFmpeg | Not found, or no H.264 encoder | Only `gdigrab` is available for a display target (higher CPU) |
| Storage | The folder cannot be written | Free space is below the estimate for 30 minutes at the chosen settings plus 1 GB |
| System-wide keys | — | None are assigned: the recording will be controlled from the tray or by returning to Studio; an *Assign keys…* button opens the shared hotkey manager |

**REC-012 — Test recording.** A *Record a 5-second test* button records the exact setup to a temporary file, then reports the same post-recording checks as REC-014 (streams, frame count, each source's level) and offers to play it. The test file is deleted when the dialog closes. This is version 1's form of PREFLIGHT-001.

**REC-013 — Start, pause and stop from the keyboard and the tray.** Commands (each in the Capture menu, the command palette and the tray; chords are **proposals**, see 7A.3):

| Command | Proposed chord | Behaviour |
|---|---|---|
| Record a demonstration… / Stop and save | `Ctrl+Alt+Shift+R` | Opens the dialog when idle; while recording, stops and saves (REC-014) |
| Pause / Resume recording | `Ctrl+Alt+Shift+P` | Closes or opens a segment (REC-008) |
| Add a marker | `Ctrl+Alt+Shift+B` | Writes the elapsed time and an optional short label to the marker list |
| Mute / unmute the microphone in the recording | `Ctrl+Alt+Shift+U` | Mutes the microphone source only; the device stays open and the muted interval is in the markers |
| Recording status | `Ctrl+Alt+Shift+T` | Speaks the TRAY-005 line: elapsed time, sources live, screen reader in or out, dropped frames, disk time left |
| Emergency stop and save | `Ctrl+Alt+Shift+End` | A second chord for Stop and save, because a screen reader's keyboard hook can swallow a key invisibly (TRAY-007) |
| Discard this recording | none (menu and tray only) | Asks for confirmation; deletes the segments. No chord because it is rare and destructive (family rules 8 and 9) |

While recording, focus is in the application being demonstrated, so the in-app chords only work when Studio is focused. The same commands therefore join Studio's **opt-in system-wide allowlist** (`CAPTURE_HOTKEY_COMMANDS`, Studio PRD AS-111) with **no defaults**: the user assigns them in the shared hotkey manager, the preflight warns when none are assigned, and a chord another program holds is reported. Tray items for recording act **without restoring Studio's window**, unlike the screenshot items, so the window does not appear in the recording or take focus. The tray tooltip carries the status line. A small **Recording status** window (non-modal, never stealing focus, reachable from the tray and the taskbar) holds Pause, Stop and save, Add marker and the status text; during a display recording Studio's windows are excluded from capture with `SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE)` (Windows 10 version 2004 or later; verified in spike **S4**).

**REC-014 — Independent check and spoken result after recording.** After Stop, Studio reopens the final file with `ffprobe` and FFmpeg, never trusting the recorder's own counters, and checks: exactly one video and one audio stream; duration within one second of the measured recording time less pauses; frame count within 2 percent of rate × duration; a decode of the first, middle and last two seconds with no errors; black-frame detection on sampled intervals; each enabled source's level from its WAV (exact silence flagged, as in REC-011); and the SHA-256 of the file. The result uses VERIFY-002's states: **Verified** (every objective check passed), **Needs review** (a Warn: dropped frames above 1 percent, a silent source, black intervals, a failure moment marked during recording), or **Failed** (a missing stream or decode errors; segments are kept and the reason given). The spoken outcome is one sentence, for example: *"Demonstration saved, 2 minutes 41 seconds, 1920 by 1080 at 30 frames a second. Picture and sound checked. Microphone and Edge sound present; screen reader left out. Saved in Videos, QUILL Studio."* The same text, with every check, is written to the verification report and shown in the result window.

**REC-015 — Failure handling.** Every failure is spoken once (failures are always spoken, whatever the feedback setting), written to the status bar and the verification report, and given a marker at its moment. Nothing is silently replaced.

| Event | What Studio does |
|---|---|
| The target window closes | Stops video at that moment, keeps every segment, finalizes the file up to the close, and says so; the result is Needs review |
| The window is minimized | WGC delivers no new frames, so the video holds the last frame: Studio warns once, marks the interval, and keeps recording; restoring resumes live frames |
| The window moves to another display | WGC follows it; nothing to do |
| A display is disconnected or changes resolution | Closes the segment and pauses, with the reason spoken; the user may resume on the display that remains (a new segment) or stop |
| A sound device is unplugged | That source is filled with silence and marked; the same device is reopened by identity if it returns, never replaced by a different one (MX-181) |
| The recorded application or the screen reader quits | That source ends and is marked; if the same executable starts again, it is found again by name after a settling delay (the dictation gate's rescan, section 10C.4 lesson 6) |
| Disk space runs low | A warning at 2 minutes of space left at the current rate; at 200 MB Studio stops and saves |
| FFmpeg exits unexpectedly | Recording stops; the segments already written are finalized; the result is Needs review or Failed with the reason |
| Studio crashes or the power fails | On the next launch Studio offers *Recover unfinished recording* for each `.studio-recording-*` folder it finds, and finalizes it the same way |
| Secure desktop, lock screen or protected content | Recorded as black, never bypassed; detected afterwards by REC-014's black-frame check and reported |
| Capture falls behind | Dropped frames are counted; above 5 percent over 10 seconds Studio warns once |

*Needs a code fix (2026-10-31).* Two rows of this table describe the intended behaviour, not what the code does yet. A recorded program or screen reader that quits is never noticed, so it is not marked and is not found again (REC-019). System sound from a sound card that is lost is never reopened (REC-020). The user guide describes both as working (`standalone/studio/docs/userguide.md:848-849`) and carries a known-limitations note until the code is fixed.

**REC-016 — Announcements, F1 help and keys.** Studio speaks only what the screen reader cannot (GATE-13) and routes everything through the announcement service, so it is also brailled (GATE-BRAILLE): the countdown; *Recording* once at the start; pause, resume, marker and microphone mute as action feedback through the shared `action_feedback` setting (sound, speech, both or silent; a sound with no clip in the pack speaks); every failure, always spoken; the result after stop; and the status line on request. When screen reader speech is a recorded source, the start, pause, marker and mute confirmations are sounds, not speech, whatever the setting, and only failures speak. Every control in the setup dialog, the Recording status window and the result window carries authored inline `SetHelpText`, joins Studio's `surface_help` catalogue and its help-audit snapshot, and answers F1 with the window's purpose and then the control's help. Dialogs use the host's modal contract (the Recording status window is a modeless frame whose Close button is bound with `dialog_contract.bind_close_button`), access keys are unique per window (GATE-14), menu labels render the bound chord through `_menu_label`, and the new keys land in `APP_KEYMAPS["studio"]`, the generated keyboard reference (GATE-KEYREF) and the Key Describer's titles (GATE-DESCRIBE).

**REC-017 — Privacy and safety.** Nothing is uploaded; no AI runs during or after recording unless the user asks (Inspect a frame uses the Screenshot Inspector's existing consent, Studio PRD AS-106). No network call is added, so the network egress audit is unchanged. While recording, the window title begins *Recording –*, and the tray tooltip says so. Safe Mode allows recording (it is local) and disables the system-wide keys, as it does for screenshots. Nothing opens a microphone except the user's explicit choice (MX-179).

**REC-018 — Where the code goes.** A wx-free `quill/core/demo_recording.py` for the plan, the preflight rules, file naming, the FFmpeg argument builders and the parsing of `ffprobe` results (strict mypy, unit-tested); `quill/platform/windows/screen_recorder.py` for the WGC helper and FFmpeg process control; the PCM capture API added to `process_loopback.py` and a new `endpoint_loopback.py` for system sound; `quill/apps/studio_demo.py` as the Studio mixin (menu, tray, commands, hotkey allowlist entries) with its dialogs in `quill/ui/studio_demo_*.py`. Background work runs on the task manager; UI updates go through `wx.CallAfter`; new exceptions inherit `CodedError` (GATE-EC); new surfaces must be reachable from the Studio entry point (GATE-REACH) and listed in the dialog inventory; module size budgets apply.

**REC-019 — Notice when a recorded program quits.** Every process capture checks that its target is alive before it opens, and then at least every 2 s on a monotonic clock. A process that is gone ends the source with a spoken failure, which starts the find-again rescan in REC-015. Acceptance: kill a fixture process mid-recording, and within 3 s there is one failure line, then one "found again" line after it restarts. Verify on hardware first. *Needs a code fix (2026-10-31):* `quill/platform/windows/process_loopback.py:425-447` loops until `stop()` is called, and the rescan in `quill/platform/windows/demo_audio.py:348-369` runs only once the capture returns. Windows raises nothing when the process quits, so the capture never returns: the program records silence with no event and is never found again. REC-015, the user guide (`standalone/studio/docs/userguide.md:848`) and the `demo_audio.py` docstring (lines 11-14) all say otherwise. (Source: TG Drop Deck `dropdeck/proccapture.py` lines 240-243 and 401-416, and `CHANGELOG.md` line 2128, which notices a quit within a couple of seconds by polling `alive(pid)`.)

**REC-020 — Reopen a lost sound card.** A system-sound (endpoint) loopback that ends is reopened by endpoint ID when that endpoint returns or changes format, and the failure line names the device. An unplugged headset, a Bluetooth reconnect or a sample-rate change in Sound settings all end the WASAPI client. Acceptance: disabling and re-enabling the endpoint mid-recording gives one failure line, one recovery line, and marked silence in between. *Needs a code fix (2026-10-31):* `quill/platform/windows/demo_audio.py:353-360` looks up a process name for a device source; that name is empty, so the loop polls forever and never reopens, and the failure line says the program "quit or its sound ended". REC-015's row for an unplugged device and the user guide (`standalone/studio/docs/userguide.md:849`) say it is reopened. (Source: TG Drop Deck `dropdeck/streamout.py` lines 195-235, and `CHANGELOG.md` lines 1052-1062, where a device change killed the send and lost 57.7 percent of the audio.)

**REC-021 — Say when a source is in one ear.** The spoken check (REC-011) and the after-check (REC-014) report any source whose one channel is more than 30 dB below the other ("Microphone is only in the left ear"). REC-014's level check passes a one-ear microphone today, because its peak is fine. Acceptance: a fixture with signal on one channel is reported; a centred mono source is not. (Source: TG Drop Deck `CHANGELOG.md` lines 1196-1233, where the Help check says whether the two channels differ; ours, MX-185.)

**REC-022 — Time sources by the sound, not the wall clock.** Source timing uses the capture API's own position (the WASAPI QPC position from `GetBuffer`, PortAudio's `inputBufferAdcTime`) against a monotonic clock, never `time.time()`. At stop, each source's sample count is compared with the session's monotonic length; a source off by more than 20 ms is stretched to fit (FFmpeg `aresample=async` or `atempo`), and the correction is written to the verification report. Filling gaps with silence is for real outages only, not for drift. This is how REC-008's alignment target, MX-116's drift handling and spike S5 are to be met. Acceptance: a fixture source at 48,010 Hz stays within one video frame over 30 minutes. Today `WavStream.write` (`quill/platform/windows/demo_audio.py:94-97`) inserts silence once wall time leads the sample count by 50 ms, so a slow device clock gets a 50 ms hole every few minutes and a fast one slides late; the mix applies only a start offset (`quill/core/demo_recording_ffmpeg.py:282-287`); and `time.time()` can jump when the system clock syncs. These effects come from reading the code, not from measurement. (Source: TG Drop Deck `dropdeck/streamout.py` lines 93-110, and `CHANGELOG.md` lines 763-764 and 889-890: the sound is the master clock, because a machine that stalls makes a wall-clock file shorter.)

**REC-023 — Count glitches while they happen.** Each sound source counts discontinuities, overflows, and any stretch longer than 0.5 s with no callback. The first of each kind is spoken during the recording, not only at the end, and every count goes in the report. Today `quill/platform/windows/process_loopback.py:430-432` checks only the silent flag and ignores the data-discontinuity flag; the microphone callback ignores its `status` (`quill/platform/windows/demo_audio.py:396`); and the microphone watchdog (`demo_audio.py:429-443`) checks only `stream.active`, so a stream that stops calling back while it still reports active records silence without a word. Acceptance: an injected 1 s callback stall is spoken once. (Source: TG Drop Deck `CHANGELOG.md` lines 522 and 1008, and `dropdeck/recorder.py` lines 381-392; ours, MX-173, MX-182 and VERIFY-004.)

**REC-024 — One stream's failure never ends the others.** A failure in the video, the camera or any one sound source is reported against that stream by name and never stops the rest. Acceptance: killing the camera's FFmpeg leaves the screen and every sound source recording, and the result is Needs review, naming the camera. (Source: TG Drop Deck `CLAUDE.md` lines 546-552 and `CHANGELOG.md` line 518, where one handler shared by two recorders let a disk fault on the MP4 abandon the WAV mid-write; ours, REC-015.)

### 7A.3 Keys and the family rules

The chords in REC-013 are proposals. They are three-modifier Studio app keys, free in Studio today (Studio's taken `Ctrl+Alt+Shift` letters are A, D, F, H, I, L, O, S, X and F4 to F6), and follow the shipped capture keys' pattern. Before adoption: allocate them in `APP_KEYMAPS["studio"]`, not `DEFAULT_KEYMAP` (rule 7: editor chords are for the editor); give every command a key or a written reason (rule 8; Discard has a reason); keep the rare ones off short chords (rule 9); and check them against JAWS, NVDA and Narrator, the family's other apps, and keyboard layouts where `Ctrl+Alt` is AltGr, since a `Ctrl+Alt+Shift` letter can become `AltGr+Shift` and type a character instead. `Ctrl+Alt+Shift+R` was this document's original proposal for start/stop demo (section 12).

### 7A.4 Out of scope for version 1

Webcam and picture-in-picture; guided regions, UI Automation elements and several windows as targets; editing, trimming and chapters inside Studio (section 10B); captions and transcripts (DEMO-002's conversion step); the interaction-event track (DEMO-003); pointer click highlighting and zoom (CAP-003, VID-012); program and private buses, VB-CABLE output and live streaming (sections 5 and 10A); several audio tracks inside the MP4 (the optional per-source WAVs serve later editing); hardware encoders, HDR and more than 60 frames a second; audio-only demonstrations; AI review of the video beyond Inspect a frame; publishing; macOS.

### 7A.5 Spikes before building

- **S1** Window capture: a WGC capture of one window handle to raw frames, in Python (pywinrt plus comtypes interop) and as a native helper; measure CPU and memory at 1080p30 on an 8 GB machine without a discrete GPU.
- **S2** The bundled FFmpeg's real capabilities: `ddagrab`, `gdigrab`, `libx264`, `h264_mf`, and constant-frame-rate behaviour with sparse WGC frames.
- **S3** PCM process loopback at 48 kHz stereo from `process_loopback.py`, and endpoint loopback for system sound, without changing the dictation gate.
- **S4** `WDA_EXCLUDEFROMCAPTURE` on Studio's windows with `ddagrab` and `gdigrab`.
- **S5** Audio/video alignment over 30 minutes, measured with a flash-and-tone fixture.

### 7A.6 Acceptance tests

*Automated, no hardware:*
1. File naming: forbidden characters removed, 60-character cap, no overwrite.
2. FFmpeg argument builders for `ddagrab`, `gdigrab` and raw-frame input: frame rate, pointer, size ceiling, odd-dimension padding, levels and offsets in the mix.
3. Each preflight Stop and Warn in REC-011 is produced by a unit test, and a Stop cannot be confirmed.
4. System sound with the screen reader left out produces the Warn; the Studio process is never in the capture set; the microphone's on state is absent from every persisted file.
5. `ffprobe` result parsing: a missing audio stream is Failed, a duration mismatch is Needs review, a clean file is Verified.
6. Recovery finds a `.studio-recording-*` folder and finalizes it.

*Integration, Windows, opt-in, marked `machine_global` where they touch real devices:*
7. Record a fixture window that animates a counter and plays a known tone from its own process for 5 seconds with application sound on: the MP4 has one video and one audio stream, lasts 5 ± 0.5 seconds at 30 frames a second ± 5 percent, contains the tone at its frequency, and its frames are not uniform.
8. Privacy: a second fixture process standing in for the screen reader plays a different tone and is left out: that tone is absent from the file (the controlled test of VERIFY-006).
9. Pause and resume: two segments joined; the duration excludes the pause.
10. Closing the fixture window mid-recording leaves a finalized file up to the close, a marker, and one spoken failure.
11. A stub sound source that raises mid-recording becomes marked silence; killing FFmpeg leaves a recoverable file.

*Manual, with JAWS, NVDA, Narrator and a braille display:*
12. The whole journey keyboard-only, starting and stopping with system-wide keys from Edge and again from the tray; the preflight summary is read once, not twice; the countdown, the result and F1 on every control are heard and brailled.
13. With screen reader speech on: only the intended speech and Studio's failure lines are in the file.
14. The Key Describer names every chord; the setup and status windows work in high contrast and at 200 percent text scaling.
15. On an 8 GB machine without a discrete GPU, a 30-minute 1080p30 display recording drops under 1 percent of frames and stays within REC-008's alignment target.

### 7A.7 As built (2026-10-29)

The journey above is what ships, with these differences, each deliberate:

- **Window targets record the window's screen area**, through desktop duplication cropped to the window (or the GDI grabber when duplication cannot reach that display). Windows.Graphics.Capture (spike S1) is not implemented, so a covering window is recorded and moving the window is not followed. The spoken check says so as a Warn on every window target rather than hiding it, and the user guide names it. REC-003's "no silent fallback" holds: nothing is substituted without being said.
- **Display backend selection is measured, not assumed.** `ddagrab`'s `output_idx` is matched to the chosen display by DXGI device name on the default adapter (`screen_recorder.dxgi_output_index`); a display on another adapter, or the multi-display full desktop, uses `gdigrab`.
- **System sound can leave the screen reader out.** Process loopback's *exclude* mode records everything except one process tree, so "System sound" defaults to "everything except your screen reader" and the REC-011 Warn appears only when the user turns that off. Studio's own cues are muted for the recording and restored afterwards.
- **Sounds you hear** (`quill/platform/windows/audio_sessions.py`, `quill/ui/studio_demo_sounds.py`) mutes, unmutes and sets the volume of any program's Windows audio session, the MX-121 "operating-system session mute", kept separately named from "left out of the recording".
- **Camera and face framing were brought into version 1** (7A.4 had them out of scope). FFmpeg's DirectShow input records the camera to its own segment, overlaid in a chosen corner at a chosen width, or alone ("Camera only"). Framing advice uses Windows' own `Windows.Media.FaceAnalysis.FaceDetector`, reached through the WinRT ABI directly (`quill/platform/windows/face_detect.py`), so it adds no package, model download, network call or AI consent. One FFmpeg process owns the camera and tees small grey frames to the detector during a recording. Advice is from the presenter's side ("move a little to your left"), with a mirrored-camera switch; `quill/core/demo_camera.py` holds the wording and the steadiness rule.
- **Keys.** Record or stop is `Ctrl+Alt+Shift+V`, not `R`, which is Quill Radio's system-wide show/hide. Every command has a Studio app key (including Discard, `Ctrl+Alt+Shift+Delete`, because the menu-accelerator rule admits no exception; it still confirms). The recording commands join `RECORDING_HOTKEY_COMMANDS`, opt-in with no defaults.
- **Markers from a key are unnamed** ("Marker 3"); the Recording status window's button asks for a label. Prompting from a system-wide key would take focus from the demonstrated program.
- **Recovery is announced, not offered modally**, at launch: the status line names the count and Capture > Recover unfinished recordings finishes them.

Code: `quill/core/demo_recording.py` (plan, preflight, summary, naming, persistence), `demo_recording_ffmpeg.py` (argument builders), `demo_recording_verify.py` (REC-014), `demo_camera.py`; `quill/platform/windows/screen_recorder.py`, `demo_media.py`, `demo_audio.py`, `audio_sessions.py`, `face_detect.py`, and the PCM API added to `process_loopback.py` (the dictation gate is unchanged); `quill/apps/studio_demo.py`; `quill/ui/studio_demo_*.py`.

Verified on the build machine: a 5-second display recording with a tone-playing process as application sound, paused and resumed, came back Verified (one H.264 and one AAC stream, length and frame count within tolerance, the tone present); the camera overlay, offsets, mixing, concat and recovery paths run against the real FFmpeg on synthetic inputs (`tests/integration/test_demo_recording_finish.py`); the face detector runs on live camera frames. Not yet verified: a positive face detection with a person in front of the camera, a live microphone or camera recording, acceptance tests 12 to 15 (screen readers, braille, high contrast, 8 GB hardware), and spike S5's 30-minute alignment.

## 8. AI Visual Inspector and blind-first visual confidence

**VIS-001** Dedicated **Understand What Is On Screen** command for live window, selected region, screenshot, imported image, webcam frame and video frame. Use both UI Automation structure and OCR, then vision model(s); never silently assume model interpretations are proven.

**VIS-002** Answers organized in layers: brief scene summary; objects/people/layout; extracted exact text; UI controls and state; precise coordinates/bounding boxes; colors/contrast; image quality; likely composition issues; warnings and uncertainty; user's follow-up question. Provide keyboard navigation through each result.

**VIS-003** **Conversation grounded to artifact**: “Is my entire dialog visible?”, “What does the red error say?”, “Where is the camera pointing?”, “Is the face centered?”, “What changed from last screenshot?”, “Describe the chart and axes.” Preserve image hash, source, region, frame index and corresponding evidence so the user can ask follow-ups without accidental cross-image confusion.

**VIS-004** For deterministic claims, prefer pixel/math/metadata/UIA/OCR validation. Examples: pixel dimensions, capture rect within display, text detected, named application matching intended window, frame blackness threshold, audio/video sync and element bounding-box intersection. Combine with AI to identify semantic content, but report uncertainty in plain English.

**VIS-005** **Blind camera coach**: startup frame analysis, face/object position and crop, horizon/orientation, headroom, lighting, motion, blur, exposure and background distractions; give incremental directional corrections, recheck after every user adjustment. Never assert that a person is visible if visual evidence is insufficient; provide no-face/no-confidence warnings.

**VIS-006** Optional provider adapters for local vision models when hardware capable, user-supplied cloud vision API keys and accessible provider settings. Show image/data selected for sharing, where it goes, estimate costs when possible, consent, privacy and safe mode. Offline capture/edit should never depend on AI service being available.

**VIS-007** Accessible visual revisions: user instructs “move annotation right 30 pixels”, “crop left until no toolbar”, “use a darker caption box”, “replace image background” (when integrated provider supports image editing); preserve originals, preview changes, verify export dimensions and report visually uncertain aspects. Every operation reversible, with stable artifact versions and provenance.

**VIS-008** Visual accessibility authoring: meaningful alt text, extended description, transcript, video audio description track, caption contrast and safe-area inspection, and readable chart/table reconstruction with confidence caveats. Provide a reviewable text representation separate from the rendered visual.

**VIS-009** Conversational image design: describe requested image, ask clarifying questions through normal chat, preview generated image with a visual model, revise, save metadata and accessible text description.

**VIS-010** No automatic publication of model-generated captions or accessibility reports without human review.


*Delivered so far:* for still screenshots, VIS-003's grounding (the same image by hash, prior conversation kept, no recapture), VIS-006's shared providers with per-request consent naming provider, model and endpoint, AI Off and Safe Mode, and offline capture independent of AI (Studio PRD AS-105 to AS-107); VIS-008's alt-text and extended-description prompts. *Remaining:* everything for live windows, webcam and video frames; VIS-002's structured layers and measured boxes; VIS-004's combined UIA and OCR evidence; cost estimates; VIS-005, VIS-007, VIS-009 and VIS-010.

## 9. Verification Center: near-100% independently verifiable path

**VERIFY-001** Each workflow produces a machine-readable and screen-reader-readable **Evidence Report** (`.json` plus `.md/.html`) with: user goal; source identity; steps completed; configuration; file hashes; audio routing graph; intended tracks; actual tracks; media codec; dimensions; duration; timing; error logs; AI findings; verification status; unresolved risks; export location.

**VERIFY-002** Use explicit result states: **Verified** (objective automated check passed), **Verified with external loopback** (downstream captured sample passed), **Needs human judgment**, **Not verified**, **Failed**. Never collapse AI semantic confidence into “Verified.” A failed/unknown check blocks an optional **Strict Publish** profile until fixed or consciously waived with recorded explanation.

**VERIFY-003** Preflight checks: target app/window identity; correct crop; nonblack test frames; expected source activity; privacy isolation; VB-CABLE send/return; available storage; supported format; clipping/noise; camera framing; actual 5–10-second practice capture; ask user whether playback sounded right; track any checks that cannot be automated.

**VERIFY-004** During recording: recoverable segment files, heartbeat, dropped frames, source disconnect, timestamp jitter, data flow, disk capacity, peak detection, rendering progress, marker log and route changes. Never say “recording safely” when no frames/samples are actually arriving.

**VERIFY-005** After recording: reopen exported media independently, decode first/middle/last sections, confirm expected audio/video streams, positive sample/frame counts, timestamp monotonicity, stream alignment, expected duration, loudness, freeze/black frame sampling, audible mic samples, absence of disallowed sources where technically testable, user-selected screenshot frame comparisons, and hash final exports.

**VERIFY-006** For public/private mix isolation, distinguish *routing configuration verified* from *actual external output verified*. If possible capture audio after the virtual cable and assert intended audio tone present and private cue absent using known test signals. During real content, privacy leakage cannot always be conclusively proven; preserve safe defaults and clearly disclose that limitation.

**VERIFY-007** **Guided verification questions**: “What can I prove?”, “What still needs checking?”, “What does the image actually show?”, “What should I fix next?”, “Replay the ten seconds around this warning.” Every issue has jump-to-time/frame/track and suggested action. Confirmation is not one opaque Pass button.

**VERIFY-008** Release benchmark: 100% of mandatory machine-testable checks executed; 0 silent failures; 0 inaccessible critical controls; 0 published strict-profile outputs with failed mandatory checks; truthfully disclose all model-dependent visual judgments. This is a robust *verification pathway*, not an impossible claim of 100% semantic accuracy.

**VERIFY-009** **Measured sync.** The test recording (REC-012) embeds a flash-and-tone fixture, and the check measures the audio/video offset at the start, middle and end of the *decoded* file and reports drift per minute. Container timestamps are not evidence of sync: an encoder setting can fix the headers and move the real sync the wrong way. REC-014 checks duration and decoding, not sync. Acceptance: a fixture recording offset by 40 ms is reported within 5 ms. (Source: TG Drop Deck `CLAUDE.md` lines 518-526 and `tools/check_recording.py`, which measures sync at five points from frames carrying their own capture time; ours, REC-022 and spike S5. Proposed in the review as VERIFY-012; VERIFY-009 is the next free ID.)

*Delivered so far (still images only):* every screenshot has a JSON and Markdown evidence report separating verified checks from unverified observations, and the evidence bundle has a strict mode that blocks until human review or a recorded waiver (Studio PRD AS-103, AS-109). *Remaining:* the Evidence Report for every other workflow, the full result-state model, and every recording, routing and export check. Section 7A's REC-014 is VERIFY-005 for one video file.

## 9A. Rehearse, detect, automatically repair, and prove readiness before recording

**Product promise:** A creator should not discover, after a 30-minute presentation, a defect that a short rehearsal could have detected. **QUILL Studio must diagnose failures, safely repair those it controls, and give exact accessible recovery instructions for everything else.** It must never treat a failed test as success merely because it can explain the problem.

**PREFLIGHT-001 — Rehearse before commitment.** Every Record Audio, Record Demonstration, Camera, Screen Capture, and Live Show journey includes **Test My Setup**. A configurable 5–15-second rehearsal captures the intended video region and actual selected audio output(s), with countdown, pause/cancel, visible/tray/announced status, and safe temporary files. Rehearsals can include a spoken script, slide change, app switching, mic sample, private cue, and recording destination test. No need to start a full project or overwrite prior material.

**PREFLIGHT-002 — Tiered readiness.** Issue a per-project report with **Ready**, **Ready with explicit limitations**, or **Not ready**. Strict/assured mode cannot start long recording when mandatory check fails; ordinary mode permits a deliberate override with an evidence note, except for non-overridable privacy/consent safeguards. Never say that AI inferred an inherently unobservable visual fact with certainty.

**PREFLIGHT-003 — Remediation engine.** Every failed check has structured `issue_id`, observed evidence, likely cause, severity, verified safe auto-fix choices, permissions, affected devices/apps, next manual action, retry hook, rollback, and plain-language explanation. Workflow is: **detect → explain briefly → attempt permitted safe repair → retest from actual source through destination → verify → resume**. Suppress repeated warning chatter; users can read the full diagnostic log at will.

**PREFLIGHT-004 — Automatic repair policy.** Auto-fix silently only when reversible, local, privacy-preserving, and scoped entirely to QUILL Studio settings, e.g. restoring a previously verified encoder preset, correcting its own capture rectangle to known valid bounds, clearing stale target handles, restoring a missing user-approved session source, choosing a known functioning app-local output fallback, or relaunching a crashed capture worker while preserving fragments. Changes to Windows default devices, another application's settings, virtual cable configuration, operating-system permissions, microphone/camera access, driver installation, cloud sharing, public routing, or publish destination require explanation and explicit consent. Never broaden screen-reader or private-audio routing as fallback.

**PREFLIGHT-005 — Guided manual repair.** If an issue cannot safely be fixed directly, offer one-action keyboard-focused instructions stating the exact Windows/app dialog, accessible control names when stable, navigation sequence, expected result, and **Retest** command. Provide **Open Relevant Settings** where trustworthy deep-links are available. Avoid fictitious clicks, blanket admin prompts, automatic driver installs, or claiming that third-party settings have changed.

**PREFLIGHT-006 — Failure-to-fix examples and tests:**

| Failed check | Safe software action | Assisted action / honest limitation | Proof of repair |
|---|---|---|---|
| Wrong display/window or partially cropped target | Restore saved HWND target, recompute crop inside capture bounds, show named content region | Help bring a minimized/occluded app foreground; ask which monitor/window is intended | Capture a fresh frame; validate window identity, bounds, visible content and image dimensions; AI judge occlusion with caveat |
| Black/protected video frames | Reinitialize capture, try supported capture API in project scope | Explain DRM/permission/secure-desktop restrictions; never bypass protection | Actual decoded nonblack motion-bearing trial frames |
| Silent microphone/muted channel | Restore QUILL-local fader/arm, use preapproved active mic | Guide hardware mute, Windows mic access and device choice | Recorded test speech has expected time-aligned nonzero signal and intelligibility check |
| Screen reader or private sounds entering published bus | Force known-safe private-routing preset, mute public feed pending retest | Explain VB-CABLE/Windows endpoint setup; never silently reroute sensitive output to public | Isolated pilot tone/cue does not appear in downstream public loopback, within stated test limits |
| VB-CABLE disconnected or incorrectly mapped | Rebind explicitly approved named endpoints, preserve isolation lock | Give step-by-step routing fix; driver installation remains user-initiated | Confirm send/receive path using a recorded loopback probe; do not infer from driver name alone |
| Mic clipping, too quiet, high noise | Adjust QUILL-local gain/limiter/compressor or suggest safer source levels | Guide physical gain, mic distance or environment changes | New trial sample passes stated level/peak/noise thresholds; assess speech content cautiously |
| Camera face off-center, low light, blur | Adjust available QUILL-controlled crop/zoom/exposure within capability | Provide spoken directional movement coaching and ask user to recheck | Multiple freshly captured frames pass threshold checks; AI judgments explicitly qualified |
| Disk low, invalid codec, missing output path | Allocate safe segment size, select compatible encoder, restore last known accessible destination | Ask permission for alternate volume/location; never delete user media automatically | Real sample file writes, closes, reopens, decodes and reports available headroom |
| Audio/video out of sync or dropped frames | Adjust app-owned capture buffers/preset and retest | Offer reduced resolution/frame rate or source isolation | Trial A/V timestamps and sample/frame continuity fall within documented tolerance |
| Inaccessible dialog/control during workflow | Fall back to accessible native alternative if already implemented | Present defect report and keyboard-reachable escape; do not gate essential completion on inaccessible UI | JAWS/NVDA/Narrator automation and blind-user path retested |

**PREFLIGHT-007 — Recurring checks and change detection.** Record **Setup Fingerprint** including source device identities, output bus, virtual cable mappings, process/window target, resolution, sample rate, source mute state, encoder, storage and privacy policy. Revalidate after driver/device change, app restart, Windows output change, scene switch, and restore from system sleep. Before a long presentation, offer a quick rehearsal when fingerprint differs from last good session.

**PREFLIGHT-008 — Inflight safety and recovery.** While recording, continuously monitor input levels, actual frames and samples, disk headroom, encoder health, missing application window, clipping and timestamp drift. Announce critical issues privately, preserve existing segments, recover only within authorized policy, and mark all affected intervals. Expose **Pause and Fix**, **Continue with Warning**, and **Stop and Save** by keyboard and tray. A fallback must never secretly introduce private content into the program feed.

**PREFLIGHT-009 — Verify the repair, not the intention.** A successful API return or changed setting is not sufficient: every repair must run a new downstream measurement against the relevant media and source/destination. Report **Fix attempted**, **Retest passed**, **Retest failed**, or **Cannot independently test**. Use precise timestamps and evidence for both initial and final results.

**PREFLIGHT-010 — Wizard user experience.** The action sequence is **Choose production goal → Configure sources and visual framing → Test My Setup → Review and fix issues → Rehearse and audition → Start full session → Monitor → Finish and independently validate → Export and verify**. Default guided mode should accomplish ordinary demonstrations with minimal Tab navigation, while advanced controls remain exposed to power users. At any step F1 explains what can fail and what QUILL can repair.

**PREFLIGHT-011 — Measurable acceptance criteria.** Regression harness injects at least: unplugged mic, VB-CABLE lost endpoint, incorrect capture monitor, black frame, muted mic, disk nearly full, malformed output codec, source restart, screen-reader leak, and interrupted capture. Every injected condition must produce a keyboard-reachable diagnosis, a safe automatic fix or exact next action, an actual retest, and truthful evidence state. Zero silent failures in critical preflight paths; no public audio leak in controlled privacy tests; no false Ready state for machine-detectable critical failures. Fully blind users must complete and recover the journeys with keyboard and speech/braille feedback alone.

## 10. Video studio, live playout and publishing

**VIDEO-001** Screen/video capture at measured frame rate, webcams/capture cards where available, resolution/framerate control, audio/video synchronized timeline, keyboard cut/trim/fade, title and caption overlays positioned numerically, scenes, image cards, B-roll, preview at explicit timecode, transcript-linked edits and audio-description track.

**VIDEO-002** Offer a readable scene list showing order, contents, start/end and accessible visual inspection; segment video into navigable shots with OCR/image-change cues. Control camera and crops through named anchors as well as coordinates.

**VIDEO-003** **Picture health.** While recording video, detect a picture that has gone black or frozen, from frames already in hand (cheap reductions on a subsample), and announce the *change* once a fault has lasted a patience period, then announce recovery; never repeat a standing state. Applies only to sources expected to move, so a still title card is never reported frozen. Acceptance: unplugging a camera mid-take produces one announcement after the patience period and one on recovery. (TG Drop Deck `health.py`; its VIS-005-style framing check, `Ctrl+Shift+F` there, independently validates VIS-005.)

**VIDEO-004** **Colour tagging.** Every H.264 output converts RGB to YUV with the BT.709 matrix and tags BT.709 primaries, transfer and matrix with limited range (`-colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv`, with the matrix also given to the scaler). A player that has to guess the range guesses wrong, and a blind presenter cannot see the washed-out result. REC-014 reads the tags back. Today `quill/core/demo_recording_ffmpeg.py:375` sets none of them. Acceptance: a test decodes white, red and blue patches as Y 235, 63 and 32. (Source: TG Drop Deck `CLAUDE.md` lines 353-367, which measured BT.601 conversion on HD pictures: pure red came out at Y 81 where BT.709 wants 63.)


**LIVE-001** Adopt an accessible **running order**, queued tracks, dual deck/crossfade, ducking, emergency silence, mic talkover, playlist and live scene changes; guard against bare-key activations while typing and background updates that steal focused rows. Preserve private preview/cue path.

**LIVE-002** Support recording live program and stems simultaneously, reliable long-running scheduling, output to virtual cable or documented streaming integration, metadata/now-playing and QUILL Radio/Cast handoffs through shared contracts.

**PUB-001** Reuse current audiobook quality checks, chapter workbench, built-in conversion pipeline, audiobook rendering, RSS feed, metadata and publishing services. Extend to MP4/MKV, social clip profiles, VTT/SRT captions, transcript/description packages and accessibility verification bundle.

**PUB-002** Publish screen includes concise review: title, destination, privacy, rights, captions, transcript, alt text, credits, encoder settings, estimated cost, test results and user confirmation. Export atomic temp-to-final with failure rollback and no silent overwrite.

**PUB-003** Integrate with existing QUILL Converter via a common engine instead of duplicating conversion features.

**PUB-004** Lossless copy/stream-copy when suitable; explicit warnings for lossy transcoding and quality degradation.

**PUB-005** Send completed audio to QUILL Cast as episode asset with chapters, transcript, artwork, title and description.

**PUB-006** Open asset from QUILL Editor/QUILL Social and return rendered or referenced output to the originating task.

**PUB-007** QUILL Radio may reuse common playback, device handling and audio services but should not inherit recording permissions automatically.


*Note:* PB-013 of the expanded PRD (optional Auphonic mastering through the user's own account) is already shipped (Studio PRD AS-59).

## 10A. Integrated live broadcasting, meetings, demonstrations and audience interaction

**Product scope:** Live production is an embedded **QUILL Studio** journey, not an optional external production app. Named **distribution destinations and meeting services** (YouTube Live, Icecast, SHOUTcast, Zoom, Microsoft Teams) are user-chosen endpoints, not competitor comparisons or required companion media-authoring tools. **VB-CABLE remains the only explicitly recommended optional external *routing utility*.** All core broadcasting controls, scene creation, mixing, rehearsal, failure recovery, recording, and evidence review live in QUILL Studio.

### 10A.1 Live Broadcast workspace: inherit current shell

**BCAST-001 — Entry and continuity (P0).** Add **Create > Start a Live Broadcast...** and **Create > Join or Present in a Meeting...** to the existing Create journey, menu and command palette. Keep library startup focus and legacy shortcuts intact. A live session uses the same source lists, private/program/record buses, Chapter/Timeline markers, project saves, accessible notifications, F6 status navigation, tray integration and Verification Center. User-configurable presets: Live demo, audio-only radio, video livestream, interview/guest show, interactive meeting, hybrid broadcast + archive.

**BCAST-002 — Keyboard-controlled show desk (P0).** Provide structured lists for Scenes, Sources, Outputs, Guests, Chat/Questions, Soundboard, Running Order, and Health/Verification. Keyboard commands for Preview, Take/Go Live, transition, fade, talkover/duck, mic mute, guest mute, private cue, push-to-talk (optional), hold screen, emergency stop-to-slate, record marker and instant replay. All numeric fades, gains, positions, delays and scene durations have accessible text entry; never require dragging, spatial hit testing or a visually monitored multiview. Explicit **Preview scene** versus **On-air scene** state. Require confirmation or arm/disarm on destructive/public actions. When typing in chat, text-edit keys must not trigger hotkeys.

**BCAST-003 — Program/monitor mix (P0).** Maintain independent buses: **Private monitoring** (screen reader, rehearsal cues), **Program broadcast**, **Local master recording**, **Isolated guest/source tracks**, **Caller/guest mix-minus**, **Preview/cue**, and optional remote confidence monitor. Explicit rules for injecting screen-reader speech into a tutorial intentionally while excluding production-only announcements. Test feedback, echo, double capture, and accidental disclosure, including with VB-CABLE where installed. Never silently reroute private content to public outputs.

### 10A.2 Broadcast output destinations and adapters

**BCAST-010 — YouTube Live (P1).** User-authenticated live event setup where authorized; stream URL/key workflow when full account API integration is not configured; video/audio ingest profile checks; title/privacy/visibility/schedule and selected caption approach; test stream/preview status; start/stop publishing controls; network and audience-state monitoring. Scope and quota/authorization requirements are resolved by a versioned YouTube adapter. Do not describe encoder connection alone as proof that the public audience sees the stream. Read/chat integration is separate from stream transport and must honor permissions, quota and moderation API limits.

**BCAST-011 — Icecast and SHOUTcast (P1).** Audio-only streaming source-client support: hostname/port/mount or stream ID, authentication, TLS where supported, codec/bitrate/sample rate/channel controls, reconnect policies, now-playing/artist/title metadata, program delay, scheduled playout, fallback playlist and locally recorded master. Validate protocol and metadata variant **per server**, rather than promising one configuration works identically on every Icecast/SHOUTcast deployment. Include listener/relay health where server API data is available, and an independent listener loopback with measured delay when possible. Preserve QUILL Radio interoperability.

**BCAST-012 — Microsoft Teams (P1/P2).** Support two clearly distinct paths: **meeting participant/presenter** using the configured application microphone/camera and permitted screen-share, with VB-CABLE as an optional audio feed path; and **event/meeting encoder ingest** using RTMP-In or SRT-In **only when the tenant/meeting policy, organizer role and meeting options enable it**. Detect/test ingest availability, check account/admin prerequisites, validate format settings, explain exact user actions when settings cannot be changed by Studio, and capture downstream evidence. Do **not** rely on retired Teams live events as the default path; target current meetings and town halls. Meeting/chat/attendee controls are enabled only where supported through authorized API or accessibility-safe user interaction; never claim unrestricted remote control of Teams UI.

**BCAST-013 — Zoom (P1/P2).** Support meeting/presentation via Studio audio routing and screen/camera sharing using user-approved endpoint selection, optional VB-CABLE, and permitted SDK integrations. Distinguish ordinary Zoom desktop-client meeting participation from deeper Meeting SDK raw-media capabilities; the latter are conditioned on version, host authorization, app approval and recording/streaming permissions. Ensure guest/host consent, expose whether screen audio and participant tracks are actually separable, and fall back cleanly to supported device-based routing. Never promise participant isolation or automatic remote meeting controls without successful permissions and loopback verification.

**BCAST-014 — Custom RTMP/RTMPS, SRT and compatible destinations (P2).** Support generic endpoint profiles, TLS/keys/secrets, bitrate ladder/preset validation, transport state, retry/backoff, local recording and reconnect after short network loss. All destinations use a common `BroadcastDestination` adapter: `capabilities`, `preflight`, `connect`, `start`, `health`, `pause_if_supported`, `stop`, `evidence`. Never imply that pause or private test mode exists on a destination that does not support it.

**BCAST-015 — Multiple outputs (P2).** Allow simulcast profiles (e.g. YouTube video + Icecast audio + local archive) within measured CPU, bandwidth and account limits. Per-output status and recovery; no single health indicator disguising a failed secondary output. No cross-posting chat or identities without user confirmation and platform authorization.

### 10A.3 Live chat, Q&A, audience and guest experience

**CHAT-001 (P1).** **Chat Console** is a native accessible list with source, sender (where available), message text, timestamp, threading/role where available, and stable focused row. Read at a controlled rate; filters for questions, moderator actions and mentions; searchable history; copy quote; reply where permitted; flag question for later. Default announcements are private, never auto-added to the show audio. Offer optional *intentional* read-aloud of selected audience comments with preview first.

**CHAT-002 (P1/P2).** API-based chat support for YouTube when permitted; authorized meeting chat/Q&A for Zoom and Teams if supported by the chosen integration. Where APIs or policies prohibit access, state **Chat unavailable through this integration** and offer a documented fallback—do not scrape inaccessible or protected interfaces or claim that messages were received. Recognize latency, message ordering, rate limits and moderation permissions.

**CHAT-003 (P2).** Moderation workflows: mute/silence locally, mark handled, keyword/safety filters, trusted co-host roles, approval before on-air reading; poll/question queue, guest invitation/return feed where supported, and accessible handoff between speakers. Preserve privacy, protect tokens, and warn before archiving audience-identifiable messages.

### 10A.4 Preflight, proof and automatic recovery for a live event

**BCAST-020 — Rehearsal-first invariant (P0).** The journey must be **Create show → Select destinations → Configure sources and scenes → Test privately → Inspect audio/video/chat paths → Apply safe automatic fixes → Retest → Explicitly arm stream → Go Live → Monitor and recover → End safely → Verify archive and publish**. Support a timed rehearsal of 30–90 seconds using dummy content and private test destinations wherever supported. Clearly warn when test content would reach a public endpoint; never go live without explicit user confirmation.

**BCAST-021 — Rehearsal checks (P0).** Test microphone presence and speech level, source isolation, VB-CABLE directionality, camera placement/lighting through deterministic frame properties and AI-assisted interpretation, complete selected-window capture bounds, slide readability/OCR, monitor versus program mix, sample rate/codecs, timing drift, available disk and CPU, network upload margin, upstream authentication and permission, test ingest acceptance, chat connection (where available), and remote audience loopback (where possible). Show per-check **Verified**, **Externally loopback verified**, **Needs judgment**, **Cannot verify**, **Failed**.

**BCAST-022 — Repair loop (P0).** Attempt safe self-repair (mute state within Studio, stale endpoint reconnection, encoder profile correction, source rebind, resampler correction, restore private-audio preset, switch to approved backup network/destination, bounded bitrate reduction). Re-run the *same failed check with fresh media*. For external settings/permissions requiring human consent or administrator control, open the appropriate workflow where supported and give short screen-reader-accessible steps, then retest. Do not claim resolution on the strength of an API acknowledgement alone.

**BCAST-023 — Live watchdog (P0).** Monitor encoded packets, silence/clipping, dropped frames, ingest connection, receive/playback confirmation where observable, output mismatch, source disappearance, local archive file growth, drift, and CPU/disk/network thresholds. Severity model: informational → warn privately → auto-recover within user-approved limits → prompt user → switch to safe scene/slate or end only as configured. Log faults, actions, outcomes and timecodes in a searchable Evidence Report. Emergency stop and private mic mute must stay responsive even when the chat/AI provider or encoder is stalled.

**BCAST-024 — Independent verification (P0).** Start local recording before public transmission if enabled; record main program and selectable stems, with crash-safe segmentation. Verify final exports by reopening and decoding. For destination verification, differentiate (a) local encoder running, (b) upstream server accepting bytes, (c) broadcaster status API reporting live, (d) independently captured downstream media, and (e) actual audience reception—which cannot generally be guaranteed. Avoid **100% guaranteed broadcast** claims when transport/platform/recipient facts are unobservable; instead provide maximum available objective evidence and explicit uncertainties.

**BCAST-025 — Accessible session operator (P0).** Main and tray accessible status: `OFFLINE / TESTING / ARMED / LIVE / RECONNECTING / ENDING / ENDED`; destinations with state; elapsed time; live scene; mic and private/public routing; stream and local-recording status; warnings; next step. One key to ask **Where am I in the show?** and **What does the audience currently receive?** Answers must say when based only on local/ingest indicators. No unrequested spoken alerts on the broadcast bus.

**BCAST-026 — A slow link never stalls the saved copy (P0).** The stream encoder and the saved copy each have their own bounded queue and writer thread, so one stalling never stalls the other or the mix. Overflow is counted and said once. A half-speed link drops nothing for about 30 s while listeners fall 30 s behind, and only then loses audio, so the growing delay is said once when it passes a set threshold. Acceptance: throttling the stream pipe to half speed for 2 minutes leaves the saved copy complete and without gaps. *Needs a code fix (2026-10-31):* `quill/platform/windows/live_stream.py:289-297` writes to both FFmpeg pipes with blocking writes on the one mixer thread, so a slow ingest stalls the saved copy too. The module docstring (lines 12-13) says the copy "keeps recording through a reconnect"; that holds for a dropped connection, not for a slow one. (Source: TG Drop Deck `dropdeck/streamout.py` lines 13-17 and 1690-1700. Proposed in the review as BCAST-024, which was taken.)

**BCAST-027 — "On air" only once audio has left the machine (P0).** "On air" and "Back on air" are said only after the server has accepted at least 2 s of encoded audio; a connection that has sent nothing is not a broadcast. Going on air is one sentence, because a second interrupts the first. An authentication refusal at any attempt, not only the first, stops the retries and says why. Today `quill/platform/windows/live_stream.py:326` says "The stream is back on air" as soon as `_connect()` returns. Acceptance: a fixture server that accepts the connection and then reads nothing produces no on-air line; one that refuses the password on the third retry stops there with the reason. (Source: TG Drop Deck `CLAUDE.md` lines 738-758 and its 3.8.4 changelog entry; ours, BCAST-023. Proposed in the review as BCAST-025, which was taken.)

### 10A.5 Audio and video demonstration examples and acceptance tests

1. **YouTube live demonstration:** A totally blind presenter selects an Edge window, runs short preflight, verifies screen bounds and title visibility via OCR and AI with caveats, broadcasts intentional screen-reader demo speech but excludes QUILL cues, monitors audience questions privately, and records local video/audio/captions. Starting live requires clear confirmation and the result records ingest and downstream-verification levels.
2. **Icecast/SHOUTcast radio show:** Presenter chooses an audio-only profile, privately cues tracks, talks over music, plays station IDs, shows now-playing metadata and listener checks, connects securely, and records the master plus mic/music stems. An unplugged input triggers safe recover/retest and an accessible on-air warning.
3. **Teams town hall:** A presenter discovers whether RTMP-In/SRT-In is permitted; if not, the app explains how to participate using allowed meeting capture/share and audio devices. It must never misleadingly report an RTMP feed as active when the tenant forbids ingest.
4. **Zoom tutorial:** A host sets mic/program feed through approved routing, selects screen/camera sharing, tests echo and private speech leakage, verifies authorization for capture, speaks with guests and saves separate tracks only when technically available. During an interruption, user can issue **Pause and Fix**, recover, and resume with a marked discontinuity.
5. **Mixed audience experience:** Live questions from an available authorized chat connector enter a stable keyboard list; presenters can prioritize, cue and read them aloud intentionally. Private chat/screen-reader announcements never leak to the program mix by default.

### 10A.6 Engineering deliverables and release order

- **P0 foundation:** Shared program/private/record buses; Live workspace, reliable local show/record loop, trial run, end-to-end objective checks, fault recovery, complete keyboard/tray operation and explicit readiness states.
- **P1 audio broadcast:** Icecast/SHOUTcast and generic streaming profiles; native playlist and running order, metadata, listener confidence loopback, chat/Q&A infrastructure.
- **P1/P2 video and meetings:** YouTube Live endpoint and authorized chat; Teams RTMP-In/SRT-In and desktop-client paths; Zoom desktop-client routes, then permission-scoped SDK paths. Ship each capability only when tested against representative accounts/permissions.
- **P2 advanced:** Simulcast, participant/guest stems where supported, moderation, remote co-producer accessibility, scheduled broadcasts and redundancy.

**Specific pass criteria:** a totally blind keyboard-only user can create, test, run, inspect and end each supported session without visual assistance; no critical preflight defect silently passes; no unconsented private-audio leak in controlled tests; every failure has clear spoken/braille diagnosis and safe fix or recovery path; final recording passes independent decoding; public-reception claims reflect only actually observed evidence.

---

## 10B. Full professional, nonvisual video editing environment

**Status:** Proposed expansion, not a currently implemented capability. **Scope:** A professional, nondestructive nonlinear video editor integrated in the existing QUILL Studio shell and shared project/verification services. Users who are totally blind must be able to complete every supported edit with keyboard, screen reader and/or braille; graphical affordances are supplementary. This work must not replace the existing audiobook Chapter Workbench or alter its shortcuts.

### 10B.1 Video projects, media and timeline

- **VID-001 — Project model:** Named projects containing sources, nested sequences, audio/video tracks, annotations, effects, transitions, chapter and caption tracks, metadata, routing and verification history. Preserve immutable originals. Save edits as operations with autosave, journaling, recoverable undo/redo and portable relinking of missing assets. Separate the project file from source media and render outputs.
- **VID-002 — Import and conform:** Import video, screen recordings, still images, animation sequences, audio files, captions and recordings produced within QUILL Studio. Inspect duration, stream types, frame size, frame/sample rate, timebase, rotation, audio channels, color metadata and decode health. Warn of variable frame rate and resampling/conform operations without altering originals.
- **VID-003 — Multitrack timeline:** Multiple ordered video and audio tracks; clip order, in/out points, source offset, synchronization links, lock, mute/visibility, enabled state, track groups, gaps, markers, named sections and nested sequences. Show a human-readable track/clip list and a detailed property inspector alongside any visual timeline. No essential action may depend on scrubbing or dragging a waveform.
- **VID-004 — Exact navigation:** Move by frame, second, marker, chapter, clip boundary, transition boundary, detected speech segment, caption, and scene change. Provide editable `HH:MM:SS:FF` or rational timecode, with explicit handling of drop-frame and non-drop-frame formats. Announce playhead location and selected clip context on demand.
- **VID-005 — Fundamental editing:** Split, lift, extract, insert, overwrite, move, duplicate, trim, ripple trim, roll, slip, slide, ripple delete, shuffle/swap, grouped moves, snap, detach/relink audio, align, synchronize and restore. Display the expected downstream timing change before destructive-looking ripple operations; provide preview, undo and comparison.
- **VID-006 — Playback:** Full preview, loop selection, shuttle controls, jog frame-by-frame, adjustable speed with optional pitch preservation, A/B edit preview, render preview cache and audio-only review mode. Announce dropped-preview-frame warnings without talking over program audio unless requested.

### 10B.2 Image composition, effects and graphics

- **VID-007 — Composition:** Numeric crop, trim to canvas, rotation, position, scale, aspect preservation, anchor, flip, opacity, stacking order, masks and picture-in-picture. Express positioning as named screen zones plus exact pixels or percentages, with user-selected output aspect ratios and safe areas.
- **VID-008 — Titles and overlays:** Fully keyboard-editable static and animated titles, lower thirds, intro/outro cards, watermarks, callouts, arrows, numbered highlights, focus boxes, blurs/redactions, subtitles and credits. Template selection must expose font, size, position, contrast, timing and safe-area properties through accessible fields.
- **VID-009 — Transitions:** Cut, dissolve, dip/fade, wipe and configurable transition durations, plus transitions between audio tracks and sequences. Recalculate timeline duration and validate overlap/handles. The editor must explain a transition's before/after frames and which clips it affects.
- **VID-010 — Effects:** Brightness, contrast, saturation, white balance, color correction, sharpening, blur, stabilization when supported, speed/reverse, freeze frame, chroma key, noise cleanup and privacy blur. Provide presets with readable explanations, numeric controls and an effects bypass A/B test. Never claim that automatic visual correction has been definitively proven by AI alone.
- **VID-011 — Keyframes:** Accessible keyframe list per property with timestamp, easing curve, numeric value, interpolation type and next/previous navigation. Offer operations to add/copy/move/delete keyframes and preview motion via descriptive before/middle/after snapshots. Include safe motion and flashing warnings.
- **VID-012 — Zoomed demos:** Keyboard-select an application panel or OCR/UIA element, animate a crop/zoom following the selected region, and expose actual coordinates and zoom ratio. Validate that the target remains inside the final crop over sampled frames; report uninspected intervals rather than asserting full coverage.
- **VID-013 — Color and export:** Explicit aspect ratio, orientation, frame rate, bitrate/quality mode, codec/container, audio layout, HDR/SDR metadata where supported; provide meaningful defaults for demonstrations, courses, presentations and short-form media. Verify actual rendered properties using an independent probe of the output file.

### 10B.3 Audio, spoken narrative and captions

- **VID-014 — Embedded professional audio:** Every video project supports multiple isolated audio tracks, microphone narration, screen-reader-demonstration audio where intentionally routed, guest audio, music, ducking, fades, equalization, noise reduction, loudness targeting, limiting, channel mapping and stem export. Reuse the application's common audio mixer; don't create a second competing sound engine.
- **VID-015 — Record narration into a timeline:** Punch-in/punch-out, countdown or optional silent haptic/visual count-in, takes, retakes, voice-over replacement, automatic gap alignment, prerecorded narration and local recording in parallel. Rehearse and verify private-vs-program mix before any take.
- **VID-016 — Transcript-driven editing:** Search speaker-labeled transcripts; navigate from text to timecode, remove approved ranges, locate fillers/silences and propose edits. All edits are presented as a reviewable list and confirmed against the resulting media; transcript confidence and known omission risks must be shown.
- **VID-017 — Caption workstation:** Automatic draft captions with manual correction; SRT/VTT import/export; caption lanes, segmentation, readable timings, speaker labels, terminology glossary and caption placement. Check overlap, missing durations, excessive reading speed and uncovered speech regions; speech-to-text output alone does not establish caption accuracy.
- **VID-018 — Audio description:** Author or generate candidate descriptions with reserved narration gaps, independent audio-description track, ducking and language variants. Verify presence, timing and mix levels objectively; semantic adequacy requires review.

### 10B.4 AI as a controllable assistant, not an invisible editor

- **VID-019 — Ask what is visible:** For any frame or bounded time span, return a structured description identifying text, windows, controls, foreground objects, cursor location, framing, relative placement and possible occlusions. Combine OCR, accessibility tree/UIA evidence and image analysis when available; label evidence provenance and uncertainty.
- **VID-020 — Compare visual states:** Summarize before/after edits; compare source frame to final render and report text clipping, missing controls, aspect/crop changes, unintended overlays, transitions and likely blank/black frames. Explicitly distinguish full-frame deterministic checks from sampled or model-inferred checks.
- **VID-021 — Propose, preview, approve:** Natural-language requests such as “find when I open Settings, remove 15 seconds of inactivity, zoom to the settings panel, add a title and verify it” must resolve to a previewable edit plan with timecodes, target tracks, effects, uncertainties and rollback. Require approval before content deletion, audio rerouting, broadcasting or publishing.
- **VID-022 — Local/cloud choice:** Support configured AI services with clear local vs cloud indicators, consent before uploading frames/transcripts, redaction options, resource-use estimates and graceful offline fallback. No fabricated report that an entire video was visually examined when only samples were inspected.
- **VID-023 — Reusable templates:** Demonstration, tutorial, lecture, podcast-with-video, music session and live-replay workflows with named scenes and standard intro/outro/caption/safe-area defaults. Templates cannot bypass accessibility or verification gates.

### 10B.5 Preflight and proof of outcome: before and after editing

- **VID-024 — Trial-run first:** Before long recording, offer a short end-to-end rehearsal of the exact intended screen/window/camera, audio stems and routing, scenes, microphone levels, narration, captions and sample encode. Playback and describe representative frames; prompt for fixes, apply safe reversible fixes and **retest the captured result**. Always state residual uncertainty.
- **VID-025 — Edit preflight:** Detect offline/missing source media, incompatible frame rates, broken links, silent/overloaded tracks, wrong output geometry, caption drift, unsafe title bounds and inadequate disk headroom. Offer one-action safe repairs; explain and guide through anything requiring user consent or Windows configuration.
- **VID-026 — Render verification:** On export, decode the complete file to check for corruption and expected duration; validate frame dimensions, frame/sample rate, channel layout, black/frozen-frame candidates, A/V sync thresholds, unexpected silence, peak/loudness limits, caption coverage and metadata. Run targeted visual inspections on flagged and representative frames, not only the first frame. Produce a navigable **Verified / Warning / Unknown / Failed** report with per-claim evidence and tests performed.
- **VID-027 — Privacy gate:** For demonstrations, detect likely unintended private notifications, account details and screen-reader speech leakage in sampled material. Warn that absence of a detection is **not** proof of absence; require manual confirmation or stronger controls for sensitive productions. Never silently transmit captured screen data.
- **VID-028 — Accessible final review:** Provide a chapter/scene inventory, timecoded descriptions, text extracted from captured visuals, a transcript, track and cue inventory, sampled frame audit, and A/B render comparison. Explain which intervals were machine-checked exhaustively and which judgments were sampled or AI-assisted. Allow rechecking a specific time span on demand.
- **VID-029 — Publishing gate:** Do not display an unconditional “perfect” or “100% verified” status. Separate technical validation from semantic/aesthetic claims and user sign-off. Publishing confirms destinations, file integrity and returned server receipts when available; successful ingest does not prove all viewers received the content.

### 10B.6 Keyboard workflows and stable layout

- **VID-030 — Workspace:** Entry via **Create > Edit Video**, main project bin, track list, clip inspector, preview-information panel, Verification Center and existing status bar. Preserve legacy starting focus, Ctrl+Shift+P and F6 status semantics. Navigation between regions must be predictable, with focus restored after dialogs.
- **VID-031 — Structured timeline:** Up/Down change tracks or rows; Left/Right move through clips or frames in an explicit navigation mode; Enter opens clip actions; context menu lists every operation; text fields handle precise time values. Provide a discoverable mode indicator, keyboard shortcut reference and editable shortcuts without collisions with JAWS/NVDA/Narrator.
- **VID-032 — Feedback:** Commands announce action and its effect (“trimmed clip 3 by 2.5 seconds; project now 4 minutes 12 seconds”); current selection and absolute/relative position available on demand. Important messages available in status history and braille. Never stream every-frame descriptions unsolicited.
- **VID-033 — Tray controls:** While recording, rendering, or verifying, tray reports progress, pause/resume, safe stop, last error, and currently active privacy/program buses. Work may continue minimized when safe; long tasks must be cancellable and resumable where practical.
- **VID-034 — Recovery:** Autosave prior to structural edits and at safe intervals; crash restoration must open with an accessible review of recovered edits, orphaned takes and media files. Recovery must never silently overwrite a successful prior render.

### 10B.7 Minimum acceptance scenarios

1. **Blind timeline editing:** With only a keyboard and JAWS, NVDA or Narrator, independently import a 30-minute screen recording with multiple audio stems; find a named dialog via transcript and visual inspection; cut a 15-second mistake; ripple close the gap; undo and redo; verify that the remaining audio/video still aligns.
2. **Accessible composition:** Add an opening title, lower third, privacy blur and picture-in-picture camera view; change every property numerically; produce a spoken description of each edited composition; verify text bounds and disclose sampled intervals.
3. **Frame-precise effects:** Add two transitions and keyframed zoom; traverse the effects/keyframe list, adjust time/value/easing, preview at each keyframe, and detect when a crop excludes an intended interface element.
4. **Captioned tutorial:** Generate caption drafts, correct words and timecodes without a mouse, run automated structural checks, export video with captions plus independent VTT/SRT, and examine coverage/uncertainty reports.
5. **End-to-end verified render:** Rehearse a short test before a 30-minute session, fix failed device/window/routing checks, record, edit, render, independently decode the complete export, compare output with the approved project, and identify any warnings before publishing.
6. **Recovery and migration:** Force-stop editing mid-operation; reopen to recovered project with no damaged original media, then open and use preexisting audiobook workspaces unchanged. Test portable and installed modes.
7. **Low-resource behavior:** On a supported 8 GB RAM machine, perform basic trim, captions review and standard export with progress and user-controlled preview quality; clearly report when costly effects or AI models need more resources.

**Definition of done:** All above scenarios pass with totally blind testers and documented assistive technologies; no workflow-critical mouse interaction, unlabeled custom control, inaccessible preview-only property, unexplained auto-edit or unverified success claim is accepted. Automated regression includes output probing, decoding, sample comparisons, keyboard command collisions and UI accessibility tests.

## 10C. Live-show playout: running order

This section carries the expanded PRD's lessons from TG Drop Deck. It details LIVE-001's running order. It is engineering evidence and a licensing record (LIC-007, LIC-008), not a user-facing referral to another product (section 19). Thanks to Tony Gebhard (TG Studios), who wrote TG Drop Deck and published it under the MIT licence at [github.com/tonygeb23/tg-drop-deck](https://github.com/tonygeb23/tg-drop-deck), for publishing the measurements and fixes this section and the requirements that cite it are built on.

### 10C.1 What it is

[TG Drop Deck](https://github.com/tonygeb23/tg-drop-deck) (Tony Gebhard, TG Studios; MIT; Windows 3.9.0 of 16 October 2026 at the time of reading, with a separate native Mac copy) is an accessible soundboard and playout desk for podcasts, radio and live shows, written in Python and wxPython, screen-reader first and tested with NVDA running. Eighty sounds sit on the number row in four banks of twenty; one-shots overlap, beds loop and toggle; a two-deck running order crossfades; a processed microphone ducks the music; the show can be recorded, sent to another program through a virtual cable, or streamed to Icecast, SHOUTcast or RTMP services. Its working notes are unusually explicit about *measured* accessibility and audio behaviour, many prompted by blind broadcasters' reports, and that evidence is the main thing worth carrying over.

QUILL Studio today narrates, chapters, converts, captions and publishes; it has no live mixer or running order. Sections 5 and 6 plan the mixer and editor. This section adds the **live-show playout** layer TG Drop Deck demonstrates, built on AARME (section 5) rather than beside it. Requirements that belong to an existing area were placed there instead: UX-009 to UX-012, MX-127 to MX-129, MX-138, MX-139, TRAY-006, TRAY-007, MX-166, MX-179 to MX-183, EDIT-012, VIDEO-003, LIC-007, LIC-008, SEC-001, the section 13.1 latency target, SG-12 and SG-13.

**Rules every requirement below inherits:** every command has a key or a written reason and appears in a **Live Show** menu and the command palette; chords listed are *proposed* and are allocated in `keymap.APP_KEYMAPS` under the family rules and the menu-accelerator and access-key gates; the app speaks only what the screen reader does not already say, and everything it speaks goes through the announcement service so it is also brailled and written to the status bar; confirmations use the shared `action_feedback` channel (sound, speech, both or silent) while failures and counts are always spoken; every control has authored inline F1 help; nothing here makes a network call.

### 10C.3 Running order and playout

**PL-001 — A running order list.**

- *Need:* a music show needs a list that cues itself, readable one column at a time.
- *Behaviour:* a native `wx.ListCtrl` report view with columns title (first, so first-letter navigation works and no number precedes it), artist, kind (song or drop), length, scheduled start and own crossfade; title and artist from tags, falling back to the file name. Items can be **skipped** without leaving the list: a Skipped column that is empty for ordinary rows and says "Skipped" otherwise, toggled with `Space`; no check boxes, per QUILL's list convention (TG Drop Deck independently found `wxCheckListBox` check marks invisible to MSAA). No row ever says "playing" (UX-009).
- *Keys:* `Enter` play from here; `Space` skip or unskip; `Alt+Up`/`Alt+Down` move; `Alt+Home`/`Alt+End` to top or end; `Delete` remove; `Ctrl+V` paste files from Explorer; jump to the item on air proposed as `Ctrl+Shift+L`.
- *Announced:* the item changing on air is spoken as an outcome (focus is usually elsewhere); skip state is read through the row's own text.
- *Acceptance:* SG-03-style keyboard-only build and run of a ten-item show with each screen reader.

**PL-002 — Two decks and an honest crossfade.**

- *Need:* songs should hand over like radio, not with gaps or with both fading.
- *Behaviour:* two decks; the next item starts a crossfade length (default 3 s, 0 to 30 s, per-item override) before the outgoing item's **playable end**, which is its duration less trailing digital silence measured once in the background and cached (an MP3's silent tail otherwise swallows the crossfade); the incoming item enters at full level after an anti-click ramp of about 30 ms while the outgoing one rides down; a zero crossfade still overlaps about 0.2 s so a spot butts against the next song; skipped items are stepped over.
- *Acceptance:* rendered-sample tests show the incoming item at level within 30 ms and no gap at zero crossfade.

**PL-003 — Segue now.**

- *Need:* getting out of a track early, on purpose.
- *Behaviour:* cross from what is on air into the selected item at the crossfade length; play the order from the top.
- *Keys:* `Shift+Enter` segue to the selected item; `Ctrl+Shift+Enter` play from the top.
- *Acceptance:* both work with focus on any row.

**PL-004 — Countdown cue on the monitor bus.**

- *Need:* a sighted presenter watches a clock run down; a blind one needs to hear it without the audience hearing it.
- *Behaviour:* optional (off by default), a short tone a set number of seconds before the on-air item's playable end (default 10, range 3 to 60), on the private monitor bus only, never in the programme or the recording, neither ducking nor ducked, with selectable tone and level (default 1 kHz, −6 dBFS); an optional braille flash of the time remaining for users who do not hear the cue; time remaining is also part of the answer to "Where am I in the show?" (BCAST-025).
- *Acceptance:* SG-12 recording contains no cue tone.

**PL-005 — Up next.**

- *Need:* knowing what is coming without walking the running order.
- *Behaviour:* a read-only list of the next unskipped items that drains from the top as items finish, obeying UX-010 (the focused row is never removed under the user); when a new item starts, every earlier row leaves at once, so two rows never both claim to be on air; the last row always states the end of the running order.
- *Keys:* proposed `Ctrl+Shift+U`.
- *Acceptance:* the list drains during playback with NVDA focused on a row and produces no unprompted focus announcement.

**PL-006 — Running orders as extended M3U.**

- *Need:* a show worth keeping should open anywhere, and come back here without loss.
- *Behaviour:* save and open running orders as extended M3U (`#EXTINF` with length and "Artist - Title"); state M3U cannot express (kind, skipped, own crossfade) goes on `#QUILL:` comment lines other players ignore; on open, TG Drop Deck's `#DROPDECK:` lines (`kind=drop`, `enabled=0`, `crossfade=N`) are honoured too; paths under the playlist's folder are written relative. Reuse the M3U reading and writing Quill Radio already has rather than adding another.
- *Acceptance:* a running order round-trips without loss here, plays in another M3U player, and a TG Drop Deck M3U opens with its drops and skips intact.

**PL-007 — Drops between songs.** *(P2)*

- *Behaviour:* optionally insert a random drop from a chosen drops folder every N songs, never the same drop twice running.
- *Keys:* insert one random drop now, proposed `Alt+D` in the Running Order.

**PL-008 — Running orders, scenes and setups are the user's files.**

- *Need:* a presenter keeps one running order per show, copies them between machines, and must never lose one to the app.
- *Behaviour:* running orders, Mixer scenes (MX-160 to MX-165) and saved recording setups are saved atomically on change and on exit (`write_json_atomic` for JSON; the same temporary-file-and-replace for PL-006's M3U); paths under the file's own folder are stored relative, so a folder of show assets moves intact; the app never overwrites a file that changed on disk since it was read (size, time, then hash) and saves its own changes beside it instead; a file that will not load is copied aside before anything replaces it; and the last-open running order is remembered and reopened.
- *Announced:* only when the app had to save beside a file, or set an unreadable one aside, naming the file.
- *Acceptance:* copying a running order, or a scene, over the open one while the app runs, then closing the app, leaves the copied file untouched.
- *Source:* this is the rule withdrawn CW-007 carried, kept when the cart wall was withdrawn on 2026-10-31; TG Drop Deck `CLAUDE.md` lines 798-823.

### 10C.4 Engineering lessons worth keeping

Not requirements; evidence from TG Drop Deck's notes to check against our own measurements:

1. **Measure the far end, not the driver.** Its worst audio fault was found by recording the other end of a cable, not from any API report (MX-128, MX-182).
2. **Read each live source once per callback; derive a mix-minus by subtraction**, finishing both sums before any clipping, or each sum gets half a voice.
3. **"Connected" is not "correct".** Most broadcast failures it catalogues raise no error (moved artwork, microphone off the programme, wrong destination), hence a preflight that names Warn cases rather than only Stop cases (MX-166).
4. **Pure rule modules with no `wx` and no network** (its `routing.py`, `preflight.py`, `cuesheet.py`) made every accessibility and safety rule testable one at a time: the same split as `quill/core`.
5. **Never take back a key a user has learned.** It kept an old search key as an alias when it moved; QUILL's rule 5 (a free chord becomes an alias rather than a move) already says so.
6. **A program source is found again by executable after it restarts**, with a settling delay so a closing program cannot say "back" then "closed", and without walking up to the top of the process tree, which it measured capturing nothing (MX-114).
7. **A socket timeout bounds one read, not a conversation**; use a monotonic deadline for any future network check.
8. **Its documentation checker matches every backticked key in the guide against the real accelerator table**, which QUILL already does with the documentation-chord gates.

### 10C.5 Considered and not adopted

- **Direct streaming to Icecast, SHOUTcast or RTMP, and stream-key checks:** network egress and stored credentials outside Studio's local-first scope; the audience bus stays device- or integration-based (section 5.2). Revisit only with consent, an egress-audit entry and MX-166.
- **Broadcast picture cards, overlays and camera-in-corner layouts for video platforms:** a streaming feature, not a recording one; section 10 covers video capture.
- **A three-level speech setting (all, essential, none):** QUILL's rule is to say less rather than make the user configure how much less; `action_feedback` already chooses the channel for confirmations.
- **Speaking each sound's name as it fires:** the user hears the sound and the focused control already names it.
- **Bundling its AI-generated demo pack:** about 8 MB, terms stated only in prose (LIC-008).
- **`pedalboard` as the effects and VST3 host:** GPL-3.0 (LIC-008).
- **Check-box list for the running order:** QUILL's list convention uses a state column instead (PL-001).
- **In-app feedback with donation prompts:** QUILL has its own feedback channel, and donations only cover AI costs.
- **The Mac copy and its virtual audio driver:** Windows first, and kernel drivers are a non-goal (section 1.3).
- **Portable `userdata` folder and self-update:** QUILL already has both.
- **Porting its UI code:** its single large UI module mixes concerns QUILL keeps apart; port pure modules only (LIC-007).

### 10C.6 Phasing

PL depends on Phase 1 of section 14: the programme bus (MX-127), event ducking (MX-138) and the recorder (MX-170 to MX-183). It is a vertical slice for Phase 2: the running order (PL-001 to PL-006, and PL-008) first, then PL-007. Exit: SG-12 and SG-13.


*Reconciliation with this document.* **Direct streaming** is adopted in section 10A (BCAST-011, BCAST-014), on exactly the conditions 10C.5 named (consent, a network egress audit entry, a go-public preflight such as MX-166, and credentials in secure storage, never in a shared file per SEC-001). UX-006 now follows the repository's over-announce rule (GATE-13): provide details on request rather than a three-level speech setting.

## 11. Technical design and component boundaries

Use the existing `quill.apps.studio` shared package, wxPython shell and shared data store. Introduce independently tested service boundaries, not a duplicated QUILL runtime:

- **StudioShell**: wxPython windows, keyboard command registry, tray, native UIA, wizard/workspaces, command palette, progress and help.
- **ProjectService**: manifests, durable asset database, edit lists, autosave, backups, old `.quilljob` import, paths and provenance.
- **AudioGraphService**: device discovery, WASAPI/process-loopback/virtual cable adapters, buses, DSP, monitored outputs, stems, realtime recording helper.
- **CaptureService**: Windows Graphics Capture / supported desktop APIs, screenshots, window/element binding, annotations, frame capture, privacy/exclusion policy.
- **TimelineService**: synchronized audio/video, nondestructive edits, markers, versioned undo and deterministic renders.
- **IntelligenceService**: OCR, UIA data, local/cloud ASR, vision providers, grounded Q&A, scene description, caption/alt-text suggestions.
- **VerificationService**: preflight/inflight/postflight objective assertions, evidence manifest, independent decoder probe, privacy test, risk reporting.
- **PublishingService**: existing audiobook/podcast exports plus new audio/video/description packages; reuses the existing media conversion and shared QUILL services.
- **CrossAppContracts**: stable serialized media asset handoff to QUILL Editor, Cast, Radio, Lite, Transcribe.

**Engineering:** Typed contracts, structured logs, crash recovery, no audio DSP on wx event loop, bounded queues, watchdog, UI-thread-only UI updates, lazy-loaded AI models, opt-in provider calls, Windows Credential Manager or equivalent secure storage, supported installer/portable flavors, subprocess sandboxing and process permission checks. Maintain license and distribution compliance for the existing media processing stack and any bundled dependencies. Avoid co-installing drivers without informed user action. Preserve existing media dependency license checks.

### 11.1 Audio engine considerations

- WASAPI render/capture/endpoint loopback; Windows process loopback for compatible OS versions. See Microsoft sample.
- Separate engine process where feasible for UI crash resilience; watchdog and recoverable stems.
- Source capture timestamping, resampling, monotonic transport clock and clock drift correction.
- Float32 mixing internally, fixed buffer scheduling, zero allocation/locks in real-time callback where practical.
- Backpressure telemetry rather than audio-engine stalls when UI or transcription is slow.
- Adaptive process/endpoint reconnection; stable logical identity for scene mappings.
- Windows audio output endpoints are not equivalent to permission to transmit into arbitrary meetings; expose virtual device or host-app integration requirements.
- High-DPI UI and capture scaling correct across monitors and display layout changes.
- Let the device choose the render buffer size where the API allows it, rather than fixing one. TG Drop Deck measured (10 runs per size, into VB-CABLE): 512 frames lost audio in 7 of 10 runs, 2048 and device-chosen in none, and device-chosen kept the 22 ms latency of 512 where 2048 cost 85 ms. Repeat the measurement on the AARME engine before choosing a number.
- Do not resolve "system default" through MME: TG Drop Deck measured the default output at about 200 ms through MME against 22 ms for the same card under WASAPI. List WASAPI endpoints first and resolve the default there.


### 11.2 Internal event and data contracts (illustrative)

`Source`: UUID, user alias, kind, endpoint-id or process identity, channel metadata, capabilities, status.  
`Route`: source-id, bus-id, enabled, send gain/pan, pre/post selection, privacy classification.  
`Bus`: UUID, kind (`monitor`, `audience`, `main-record`, `stem`, `aux`), output endpoint, mix format, meter.  
`Scene`: schema version, logical source selectors, routes, FX, safety flags, restore policy.  
`RecordSession`: UUID, start wall-clock/monotonic clock, media paths, format, stems, recovery state, event log.  
`TimelineProject`: version, clip/track graph, markers, effects and asset manifests, history pointer.

APIs include `enumerate_sources`, `get_source`, `set_source_gain`, `set_source_mute`, `set_route`, `get_routing_matrix`, `apply_scene_preview`, `commit_scene`, `arm_track`, `start_recording`, `stop_recording`, `get_meter_snapshot`, `get_transport`, `subscribe_state`, and `emergency_mute_audience`. Enforce access control and avoid unauthenticated network control.


## 12. Keyboard model and discoverability specification

Keep all established chords. Reserve a **command registry**, not scattered handlers, for new shortcuts. Propose, subject to conflict testing: `Ctrl+Shift+P` command palette (existing), `Ctrl+,` preferences (existing), `F1` contextual help, `F6` existing status access, `Ctrl+Alt+Shift+R` start/stop demo (taken up by section 7A, REC-013), `Ctrl+Alt+Shift+V` inspect current visual, `Ctrl+Alt+Shift+K` read verification, and user-configurable recording marker, mic/program mute and emergency stop. `Ctrl+Alt+Shift+S` capture screenshot is now Studio's shipped Capture screen key (Studio PRD AS-93). These are suggestions only—**do not install untested shortcuts automatically**. Screen reader pass-through and keyboard focus safety win over mnemonic cleverness. Every shortcut can be read from the menu and searched in a keyboard reference; conflicts identified with OS, other QUILL apps, screen readers and system-wide shortcuts.

Examples of speech results: “Window Microsoft Edge, 1280 by 720, target visible; browser address bar not within crop; two possible notification overlays; capture ready with warnings.” “Recording started; screen and microphone active, JAWS private; VB-CABLE output verified by loopback.” “Export completed; audio, 2 minutes 41 seconds, captions present; 12 seconds may have clipped titles; verification needs review.”

## 13. Accessibility, privacy and reliability nonfunctional requirements

- No unannounced focus changes, background updates reordering focused rows, unlabeled icon-only controls, inaccessible custom scrollbars, drag-only editing or silent errors.
- Checkpoints and incremental recording segments to survive process crash/power loss where media APIs and storage permit. Atomic exports and safe recovery workflow.
- Audio processing and UI accessibility remain functional with cloud AI disconnected; explicitly degrade optional features.
- Guarantee no unsolicited capture/upload, screenshot sharing, microphone recording or public routing. Show live capture indicator; sensitive windows may be excluded by setting/policy.
- Provide text-based self-diagnostics that can be copied/sent with private fields redacted and user review. Logs include no raw transcript, keys, audio or screenshot without opt-in.
- Quantitative performance budgets and stress tests on 8GB/no-GPU Windows machines; document latency/dropped-frame targets **only after hardware benchmarks**, not guessed promises.
- JAWS, NVDA, Narrator and keyboard-only manual user testing required for every major workflow and migration.

### 13.1 Initial engineering targets

These are **initial engineering targets pending validation**, not performance guarantees:

- Normal mixer controls respond within 100 ms perceptually; screen reader commands receive status without blocking audio thread.
- Monitoring end-to-end latency reported; selectable safe modes for ordinary USB/headphone devices and low-latency professional rigs.
- No dropped audio for an agreed reference hardware/capture scenario (e.g., 4 sources, 2 buses, 48 kHz stereo, long-duration session); measure rather than assume.
- Project autosave recoverability after forced UI termination, with ability to salvage partially recorded stem containers.
- At least 24-hour stability test for background mixer operation under realistic audio loads and app/device churn.
- Bounded memory/cpu use; 8 GB RAM user profiles tested for core capture/edit/conversion without loading large AI models by default.
- Every failure state accessible, actionable and logged locally with privacy safeguards.
- Playout keypress (play or segue in the running order) to first audible sample: target 30 ms or less on a WASAPI shared-mode endpoint on reference hardware, measured from key event to first non-zero output sample; the start of the next item is decoded ahead, never on the trigger path.


### 13.2 Licensing

**LIC-001** QUILL Audio Studio application license must be chosen or confirmed against existing repository; do not assume its current license.

**LIC-002** ZoomIt source in the Microsoft PowerToys repo carries MIT notice; preserve its copyright/license and review each included component and dependency.

**LIC-003** Do not redistribute proprietary Sysinternals binaries merely because MIT source exists; distribute appropriately licensed compiled builds.

**LIC-004** FFmpeg configurations have LGPL/GPL consequences; maintain a declared build configuration and meet all applicable conditions.

**LIC-005** Confirm licenses for ASIO, codecs, VST hosting, AI model weights, MediaPipe/model assets, fonts and redistributables independently.

**LIC-006** Distinct QUILL branding; no suggestion of Microsoft or MediAccess endorsement.

**LIC-007** TG Drop Deck is MIT licensed (Copyright © 2026 Tony Gebhard). Code may be copied or adapted into QUILL, which is MIT too, provided the copyright and permission notice travel with it: in the adapted file's header and in the third-party notices. Prefer porting its small pure modules (CUE log, M3U fields, routing and preflight rules) over its UI, whose architecture differs. No TG Studios or TG Drop Deck branding, and no implied endorsement.

**LIC-008** Do not inherit TG Drop Deck's dependency choices without separate review: its DSP and VST3 host is Spotify `pedalboard` (GPL-3.0), which would put GPL obligations on any QUILL bundle that ships it; its PyAV wheel carries FFmpeg (LIC-004 applies); its bundled demo sounds are AI-generated (ElevenLabs) with their terms stated in prose only; its face model is YuNet from OpenCV Zoo (MIT); its Mac build links LAME (LGPL).

**LIC-009** VB-CABLE (VB-Audio, https://vb-audio.com/Cable/) is **donationware**, not freeware or open source: free for an individual to use with every function, a paid licence (volume prices from about 3.61 EUR a seat) when used in a professional context, and redistributable with a free program only if the user can see it is a VB-Audio product and is in a position to pay -- the distributor must credit www.vb-cable.com and say it is donationware (VB-Audio licensing page, read 2026-10-26; the A+B and C+D cables may not be bundled at all). It installs a Windows audio driver with administrator rights and a reboot. So Studio **does not bundle or install it**: MX-127 to MX-129 work with *any* virtual audio cable the user has installed, VB-CABLE named as one example with its donationware terms stated, and the cable test (MX-128) is what proves a chosen pair works. Where a cable is only wanted to *capture* another program, prefer WASAPI process loopback, which QUILL already has (`quill/platform/windows/process_loopback.py`) and needs no driver.


### 13.3 Security

**SEC-001** Shared configuration files (scenes, running orders, saved setups) are untrusted input: they never carry network destinations, credentials, or anything acted on at load, and such fields are dropped on import with the drop reported. TG Drop Deck found that a free-text "custom server" field in a shared board file could send a live microphone wherever the file's author chose on one keypress. Acceptance: opening a running order or scene containing a stream address opens the rest and reports the address as ignored.


## 14. Priority and incremental roadmap

**Accepted execution order (2026-10-26):** rename, then a small verifiable screenshot milestone, then the recorded demonstration with optional sound (section 7A), before the broader phases below. This order supersedes the phase headings' order without removing any requirement.

**Phase 0 — Rename safely and preserve behavior:** Name/UI/installer/tray metadata changes, no code forks, migration+regression suite, keyboard registry, baseline screenshots/AT tests, untouched three old journeys. Ship nothing until a user can upgrade and open old books/jobs. *Status:* the rename is delivered in code (`529884ec`); the installed upgrade, rollback and assistive-technology runs are still open.

**Phase 1 — Verified recording foundation:** Recorder shell and project format, source discovery, mic/system/process loopback, VB-CABLE detection and test wizard, private/program/stem buses, tray transport controls, short practice capture and Evidence Report v1. This has higher value than image generation first. *Status:* section 7A delivers its first slice (mic, system and process loopback into one recording, tray transport, a test recording and a verification report) without buses or VB-CABLE.

**Phase 2 — Demonstration and capture:** Window/screenshots, numerical cropping, OCR, AI visual inspector and grounded conversation, redaction, annotation, spoken screenshot dictation, demo recording, synchronized user narration, first-class export verification. *Status:* the screenshot half is delivered in code (Studio PRD section 4.14); demo recording is section 7A.

**Phase 3 — Editing and production:** Accessible multitrack editor, clip operations/effects, image/video timeline, text-driven visual callouts, reusable scenes, captions/transcripts, audio description and the live running order.

**Phase 4 — Advanced creation and services:** Webcam coach, richer visual editing/generation, streaming/publishing targets, app extensions, model/plugin adapters, deeper QUILL Radio/Cast interoperability.

**Exit gates per phase:** Reproduce existing behaviors; prove each new task with blind-user end-to-end scenario; accessible action coverage and logs; no private-audio leak in controlled test; deterministic report; installer/portable tests; undo/recovery; regression in Safe Mode and offline.

## 15. Key acceptance scenarios

### A. Blind presenter creates a verified software demonstration
1. Start from QUILL Studio home → Create → Record a Demonstration, keyboard only.
2. Select exact app by accessible window name and choose crop by window bounds; verify title/size and no unexpected overlap.
3. Choose mic and application/process audio; select whether JAWS narration is explicitly part of demonstration; private studio cues excluded.
4. Run 10-second test, review first/middle/last frames using OCR+AI and hear return mix; report pass/fail/uncertain separately.
5. Record demo with hotkey marker, tray status, stop, review transcript and frames, repair an annotation by numerical position.
6. Export MP4, SRT/VTT, transcript and Evidence Report; reopen file and check real streams, frame count, duration, levels and caption sync.
7. Publish only after summary of verified/unverified attributes and explicit approval.

### B. Blind podcaster uses VB-CABLE with private cues
1. Guided mapping identifies CABLE Input as QUILL output and CABLE Output as receiver input; source and destination are read as words.
2. Play isolated test tone, test downstream capture and report dropouts/levels.
3. Route mic, music, remote call to program and stems; screen-reader/studio announcements go private.
4. Capture a rehearsal; verify expected program signal and that dedicated test cue is absent from program output.
5. On cable/device disconnect, recording fails safe, reports exact problem, preserves recoverable stems and offers tested reconnection steps.

### C. Blind creator captures, annotates and verifies an image
1. Trigger capture, pick application/window/element via keyboard, inspect OCR/UIA and detected crop boundaries.
2. Add callout to element by its accessible name, not mouse drag; edit offset and dimensions numerically.
3. Ask AI what is visible and compare original with new render, preserving uncertainty.
4. Export PNG plus description, alt text and evidence report; verify intended resolution, dimensions, text position checks, and absence of known redactions failures.

### D. Upgrade and legacy continuity
1. Upgrade Audio Studio 1.0 or prerelease 2.2 config to QUILL Studio without clearing `%APPDATA%\Quill`.
2. Open old library, run legacy Narrate Documents, Build From Recordings, Edit a Book and existing shortcuts.
3. Check command palette, status bar F6, tray, sleep timer, play queue, engines, offline/portable data and Safe Mode.
4. Roll back a failed upgrade with user projects, voices and books intact.

### 15.1 Gate scenarios

**SG-01 — Private screen reader:** User hears JAWS via headphones while mic and chosen app are recorded; published mix contains no unintended screen-reader speech. Passing requires compatible device/source configuration and verification recording.

**SG-02 — Intended demo speech:** User chooses to include screen-reader output; exported demo contains it; private control speech separated only if distinct routes are available.

**SG-03 — No mouse mixer:** JAWS, NVDA and Narrator users discover a source, set exact gain, mute, solo, route to each destination and query status without mouse.

**SG-04 — Emergency audience mute:** Immediate mute works during running recording and is accessible via memorable key binding.

**SG-05 — Crash survival:** Kill UI/process during 20-minute multitrack take; recover available stems and identify missing/corrupt segments, never claiming unavailable samples were recovered.

**SG-06 — Accessible edit:** Create two tracks, insert clip, mark start/end, preview removal, apply crossfade, undo and export—all keyboard-only.

**SG-07 — Webcam confidence:** Position with on-device spoken guidance, test record, verify generated report and explicit uncertainty.

**SG-08 — Screenshot:** Capture a UIA-selected control via keyboard, inspect OCR, add numbered annotation, export both image and textual evidence.

**SG-09 — Privacy:** Cloud workflow never transmits screenshot/audio until explicit provider/price/data-sent authorization.

**SG-10 — Upgrade:** Existing QUILL Audio Studio files, projects, profiles and common shortcuts survive migration or receive clear mapping/rollback.

**SG-12 — Programme proof:** Cable test (MX-128) reports clean into a virtual cable; a recording of the far end contains the running order and the microphone and contains no cue tone, preview or private screen-reader speech.

**SG-13 — Show log:** A recorded show with running-order items and drops (PL-007) yields a same-name CUE (MX-183) that survives a forced kill and opens as proposed chapters (EDIT-012).


*(SG numbers are this PRD's scenario numbers and are unrelated to repository gates that share a number, such as the module size budget or over-announce gate.)* *Status:* every feature SG-08 needs now exists (UIA element capture, OCR, numbered annotation, image and evidence export: Studio PRD AS-97, AS-105, AS-108, AS-109); the scenario itself has not been run with screen readers.

### 15.2 Required test matrix

- Windows 11 x64, current supported builds; Windows 10 tested where promised.
- JAWS, NVDA, Narrator; keyboard-only; Windows Magnifier, contrast themes, 200–400% text scaling.
- One monitor and multi-monitor; speakers/headphones; one or multiple microphones; Bluetooth/USB hot-plug; common virtual device where available.
- Desktop apps with audio, browsers, Teams/Zoom-like meeting apps and screen reader sessions; expected isolation limitations documented.
- Single and multiple process trees, source restarts and process ID changes.
- Interruption tests: audio device removed, app closed, disk full, power loss/forced crash, missing codec, cloud service unavailable.


### 15.3 Screen-reader speech behavior checklist

For each operation: focus placement; name/role/state; shortcut; change announcement; silent variant; error feedback; braille display; audible interference risk; public-output leakage risk; recovery path. Automated UIA assertions supplemented by human usability tests.


## 16. Open design decisions requiring engineering tests

- Exact supported Windows API and build matrix for process loopback and window capture, audio exclusions, hardware GPU requirement and DRM behavior.
- Whether a chosen virtual cable allows external receiver monitoring/probing without introducing echo or temporary public leakage; include isolated test mode.
- Licensing, attribution and redistribution compliance for existing packaged dependencies, without introducing additional named third-party tools into the product workflow.
- Live streaming integration interfaces per destination; don't promise guaranteed per-app injection or per-participant capture.
- AI providers, model sizes, CPU 8GB suitability, OCR accuracy, camera guidance frequency and privacy terms.
- Precise keyboard assignments and screen-reader conflicts measured with NVDA, JAWS and Narrator.
- Consistent current macOS support and compatibility for existing journeys as Windows-specific capture expands.
- Project schema and shared-service release policy across independently updated QUILL apps.
- The demo recorder's window backend (section 7A.5, spike S1): a pywinrt helper in Python or a native helper executable.

### 16.1 Risks and mitigations

| Risk | Consequence | Mitigation |
|---|---|---|
| Same-process screen reader speech mixed with private notifications | Accidental voice leakage into output | Separate endpoints/speech instances where possible; honest capability labeling; safe scene defaults |
| Process capture limitation or OS build mismatch | Missing or partial app audio | OS feature detection; aggregate or device-level fallback with warning |
| Mixing endpoint loopback with per-process sources | Double audio in saved recording | Graph provenance checks and overlap warnings |
| Complex DAW surface inaccessible | Primary use case fails | Native accessible track/clip lists; numeric time model; expert-user testing |
| Python UI starves audio engine | Dropouts | Compiled real-time core, IPC, no expensive UI work in capture callback |
| Protected media/copyright | Incomplete capture or legal exposure | No bypass; platform-compliant error and docs |
| FFmpeg or codec licensing | Installer compliance failure | SBOM, pinned build flags and release license checklist |
| Third-party plugin crashes | Lost session | Isolate or disable plugins, test crash recovery |
| Cloud API costs | Unanticipated expense | BYOK, quotas, per-task consent/cost disclosure; free offline baseline |
| Scope expansion | Endless partial features | P0 gates, release train, regressions against current product |
| Live Show workspace keys collide with editor, screen-reader or international-layout keys | A key that never fires, or fires while typing | Workspace-scoped keys (UX-011), keymap gates, no `Ctrl+Alt`+letter defaults (AltGr), startup held-key check (TRAY-006) |
| Adopting a borrowed project's dependencies with its code | GPL obligations on a free MIT bundle | LIC-007/LIC-008 review before any port; port pure modules, not dependency stacks |


### 16.2 Open questions carried from the expanded PRD

Questions 1 to 3 of the expanded PRD (current module layout, which controls exist, whether Studio uses FFmpeg itself) are answered by the repository: the Studio is `quill.apps.studio` over the shared `quill` package; its shipped controls are Studio PRD sections 4.1 to 4.14; and it bundles FFmpeg for conversion and builds (Studio PRD P-4). The rest stay open:

4. Which audio endpoint/screen-reader routing arrangements will be supported without any installed virtual device?
5. Which Windows minimum build enables needed process loopback and frame capture APIs?
6. Which existing QUILL keyboard conventions must retain priority over proposed mixer shortcuts?
7. Which supported AI image providers/local models have legal redistribution paths and acceptable resource requirements?
8. Should downstream applications use IPC, Python package library calls, or both for shared audio engine control?
9. Which collaboration/realtime guest recording approaches can provide legitimately separate tracks?


## 17. Development backlog, issue-ready epics

| Epic | Phase | Essential done criteria |
|---|---:|---|
| STUDIO-RENAME | 0 | *Delivered in code* (`529884ec`); installed-upgrade acceptance open (scenario D) |
| STUDIO-SHELL | 0 | Legacy library initial focus, F6/status, menu and command palette stable |
| STUDIO-KEYS | 0 | Searchable, configurable, collision-tested keyboard registry |
| STUDIO-TRAY | 1 | Recording/status/scene/mute reachable from tray and keyboard without focus loss |
| STUDIO-ROUTING | 1 | Isolated stems and private/program buses; independent routing test |
| STUDIO-VBCABLE | 1 | Endpoint wizard, readable directionality, test audio, recovery |
| STUDIO-RECORD | 1 | Crash-resilient capture, timing and media decode QA |
| STUDIO-VERIFY | 1 | Evidence manifest and explicit Verified/Unknown/Failed reporting |
| STUDIO-SNIP | 2 | *Delivered in code:* numerical crop, named-window screenshot and redaction (Studio PRD AS-94 to AS-109); assistive-technology acceptance open |
| STUDIO-DEMO-REC | 2 | **Next.** Section 7A: one window or the desktop with chosen sounds to one verified MP4; REC-001 to REC-018 and the 7A.6 tests pass |
| STUDIO-VISION | 2 | OCR+UIA+AI grounded questions, artifact provenance and uncertainty |
| STUDIO-DEMO | 2 | Narrated screen demonstration, private speech policies, review/edit/export |
| STUDIO-EDIT | 3 | Nonvisual multitrack edit with reversible effect/region operations |
| STUDIO-PRODUCTION-PARITY | 1–4 | PP-001 to PP-020 delivered in their corresponding recording, editing, visual and publishing increments; section 6A acceptance and service/plug-in safety gates pass |
| STUDIO-SIMPLE-PRO | 1–4 | SIMPLE-001 to SIMPLE-010, the free local-workflow policy and section 6B acceptance demonstrated in the corresponding phases |
| STUDIO-MEDIA-FINISH | 2–4 | FIN-001 to FIN-007 shared conversion, accessible review, opt-in AI and acceptance; section 7A remains the next milestone |
| STUDIO-VIDEO | 3 | Professional accessible NLE with precise multitrack edits, effects, captions and verification |
| STUDIO-VIDEO-EDIT | 3 | Ripple/roll/slip/slide edit operations, frame-precise navigation, nondestructive undo/redo |
| STUDIO-VIDEO-COMPOSE | 3 | Picture-in-picture, numeric crop/position, titles, lower thirds, transitions and keyframes |
| STUDIO-VIDEO-AI | 3-4 | Timecoded visual inspection, proposed edit plans with human approval and provenance |
| STUDIO-VIDEO-QA | 3 | Full-file decode, AV sync, caption and output validation, honest uncertainty report |
| STUDIO-LIVE | 1 | Live workspace, preview, running order and public bus |
| STUDIO-PLAYOUT | 2-3 | Section 10C: PL-001 to PL-006 and PL-008, then PL-007; SG-12 and SG-13 |
| STUDIO-ON-AIR | 1 | Offline/test/armed/live/reconnect states, independent output health and tray commands |
| STUDIO-RADIO-STREAM | 1 | Icecast/SHOUTcast secure source-client streaming, metadata, loopback and recovery |
| STUDIO-YOUTUBE-LIVE | 2 | Authenticated or stream-key video ingest, private rehearsal and audience chat where authorized |
| STUDIO-TEAMS | 2 | Policy-aware RTMP/SRT event ingest plus permitted meeting-presenter routing |
| STUDIO-ZOOM | 2 | Permission-aware meeting audio/video paths, optional later SDK integration |
| STUDIO-LIVE-CHAT | 2 | Stable keyboard list, private notifications, moderation and explicit on-air reading |
| STUDIO-PUBLISH | 3 | Media/accessibility bundles and strict publish gate |
| STUDIO-CAMERA | 4 | Blind framing coach with incremental rechecks |

## 18. Requirements trace and notable gaps found

**Already documented in today's product artifacts:** Book-centered library; wizard; narration and assembly; chapter workbench; speech/voice engine sharing; source converter; ACX analysis; publishing; tray and close policy; configurable Studio app sounds; command palette; status bar with F6; accessible announcements and braille; portable/shared runtime; and, since 2.0.0, screen capture of windows, displays, the desktop, guided regions and UI Automation elements, scrolling and repeated capture, saved capture setups, the Screenshot Inspector with local OCR and consented AI, the screenshot editor and evidence bundle, spoken screenshot notes, opt-in global screenshot keys and tray screenshot items (Studio PRD section 4.14). These must remain.

**Expanded PRD already anticipated:** Audio graph, independent monitoring, optional virtual cable, screen reader isolation, video/capture, advanced editing, AI, screen annotation, live playout, accessibility acceptance. These are not assumed already shipping.

**Live broadcasting extended:** Native YouTube Live, Icecast/SHOUTcast, Zoom and Teams destination workflows; chat/Q&A and guest paths; transport/permissions distinctions; rehearsals, safe automatic repair, live monitoring, private/program mix isolation, simultaneous archival recording and verifiable output evidence.

**Expanded full video editing:** Nondestructive professional nonlinear editing, structured screen-reader timeline, slip/slide/ripple/roll, effects, keyframes, picture-in-picture, transcript editing, captions, audio description, AI-assisted proposals, trial runs, independent export verification and detailed acceptance tests.

**Newly made explicit here:** Exact QUILL Studio rename; no breaking navigation; independent *verification center and graded evidence*; detailed VB-CABLE setup; assistant-powered visual comparison and evidence grounding; accessible captured-element/annotation positioning; guided narrated demonstrations; screenshots+dictation; persistent tray command model; concrete release gates and compatibility scenarios.

## 19. Supported external integration and self-contained feature policy

**VB-CABLE** is the sole explicitly named optional third-party routing utility in the QUILL Studio user-facing specification. YouTube, Icecast, SHOUTcast, Zoom and Microsoft Teams are supported transmission/meeting destinations rather than recommended companion production software. Official reference: [VB-Audio VB-CABLE](https://vb-audio.com/Cable/). QUILL Studio must remain fully usable for basic capture, recording and editing when VB-CABLE is absent. Detect it when present; provide accessible routing configuration, test signals, loopback verification, clear installation guidance when requested, device-disconnect recovery and truthful privacy/isolation status. Never install or reroute the driver silently.

All other functionality—including screenshot creation, OCR, annotations, screen/video capture, visual understanding, image generation workflows, audio mixing, transcription, command discovery, tray controls, video/audio conversion, guided rehearsal and remediation—must appear as native QUILL Studio tasks, not referrals to or comparisons with other products.

The existing application's internal runtime libraries, codecs and services may continue to be used where already implemented; their legal notices remain in engineering/build documentation. This policy removes named external-tool feature comparisons, not the obligation to document dependencies and licenses accurately.

The links to PowerToys, Sysinternals, TG Drop Deck and the other products in sections 10C, 13.2 and 21 are of that second kind: engineering evidence and licence record, kept so a requirement can be traced to what informed it. They are not feature referrals and do not appear in the product's user-facing text.

## 20. Final product direction

QUILL Studio should *feel like the familiar accessible audiobook application* until the user chooses a new production task. From there it becomes a complete accessible media workstation with precise audio routing, repeatable keyboard operation, independently interrogable visuals, optional AI assistance and **evidence-backed outcomes**. Protect existing users, design first for total blindness, and prefer auditable proofs over optimistic “looks good” claims.

## 21. References

Every link below was chosen because a requirement in this document leans on it. Links to code are for study and, where the licence allows, for adaptation under LIC-001 to LIC-009; nothing is copied without that review. Paths without a web address are in the QUILL repository.

### 21.1 Microsoft PowerToys and Sysinternals

Screen capture (section 7) was first scoped against PowerToys utilities that are MIT licensed, and ZoomIt, which ships both in PowerToys and as a Sysinternals tool. It is now built natively (CAP-004, Studio PRD section 4.14) and no upstream code was imported, so these remain study references.

- [PowerToys repository](https://github.com/microsoft/PowerToys) and its [MIT licence](https://github.com/microsoft/PowerToys/blob/main/LICENSE)
- [PowerToys documentation home](https://learn.microsoft.com/windows/powertoys/)
- [ZoomIt in PowerToys: documentation](https://learn.microsoft.com/windows/powertoys/zoomit), [source](https://github.com/microsoft/PowerToys/tree/main/src/modules/ZoomIt), [main implementation and MIT notice](https://github.com/microsoft/PowerToys/blob/main/src/modules/ZoomIt/ZoomIt/Zoomit.cpp) and [developer architecture notes](https://microsoft.github.io/PowerToys/modules/zoomit/) (CAP-004; LIC-002, LIC-003)
- [ZoomIt, Sysinternals edition](https://learn.microsoft.com/sysinternals/downloads/zoomit): the standalone binary; proprietary licence, so it is studied, never redistributed (LIC-003)
- [Text Extractor](https://learn.microsoft.com/windows/powertoys/text-extractor): on-screen OCR with Windows' own engine; the model for CAP-002
- [Crop And Lock](https://learn.microsoft.com/windows/powertoys/crop-and-lock): cropping a window to a region; informs CAP-001 and VID-007
- [Screen Ruler](https://learn.microsoft.com/windows/powertoys/screen-ruler): measuring on screen; informs CAP-003's spoken geometry
- [Mouse utilities](https://learn.microsoft.com/windows/powertoys/mouse-utilities): pointer highlighting for recorded demonstrations (UX-002 and CAP-003 give each pointer-only action a keyboard equivalent)

### 21.2 Windows audio, capture and recognition

- [Core Audio and WASAPI](https://learn.microsoft.com/windows/win32/coreaudio/wasapi): the AARME engine's foundation (section 5, section 11)
- [Loopback recording](https://learn.microsoft.com/windows/win32/coreaudio/loopback-recording)
- [Application loopback capture sample](https://learn.microsoft.com/en-us/samples/microsoft/windows-classic-samples/applicationloopbackaudio-sample/) and its [source](https://github.com/microsoft/Windows-classic-samples/tree/main/Samples/ApplicationLoopback): per-process capture (MX-113), already in QUILL as `quill/platform/windows/process_loopback.py`
- [Media Foundation](https://learn.microsoft.com/windows/win32/medfound/microsoft-media-foundation-sdk): system codecs and camera capture (section 10)
- [Screen capture with Windows.Graphics.Capture](https://learn.microsoft.com/windows/uwp/audio-video-camera/screen-capture): window and monitor capture without hooks (CAP-001); QUILL's still capture uses `quill/platform/windows/screen_capture.py` and `studio_capture.py`; video recording would add WGC (section 7A, REC-003)
- [Windows.Media.Ocr](https://learn.microsoft.com/uwp/api/windows.media.ocr): local OCR with no download (CAP-002, VIS-001)
- [UI Automation](https://learn.microsoft.com/windows/win32/winauto/entry-uiauto-win32): capturing a control by its automation element (CAP-001) and every custom surface's accessibility (CAP-003, section 3)

### 21.3 Accessibility standards and screen readers

- [WCAG 2.2](https://www.w3.org/TR/WCAG22/): the success criteria section 3 maps to
- [EN 301 549 v3.2.1](https://www.etsi.org/deliver/etsi_en/301500_301599/301549/03.02.01_60/en_301549v030201p.pdf): European ICT accessibility requirements, including non-web software (chapter 11)
- [Section 508](https://www.section508.gov/): United States federal accessibility requirements
- [NVDA developer guide](https://www.nvaccess.org/files/nvda/documentation/developerGuide.html): how NVDA reads Windows controls, which decides what Studio must expose rather than script
- [Complete guide to Narrator](https://support.microsoft.com/windows/complete-guide-to-narrator-e4397a0d-ef4f-b386-d8ae-c172f109bdb1)
- `docs/design/table-uia-spike-2026-10.md`: QUILL's measured notes on what NVDA, JAWS and Narrator read from a Rich Edit control; the same limits apply to any text surface Studio hosts

### 21.4 Audio, video and caption formats and loudness

- [FFmpeg](https://ffmpeg.org/) and its [licensing](https://ffmpeg.org/legal.html) (LIC-004)
- [Opus](https://opus-codec.org/), [FLAC](https://xiph.org/flac/) and [LAME (MP3)](https://lame.sourceforge.io/): the export formats in section 6
- [EBU R 128](https://tech.ebu.ch/publications/r128) and [ITU-R BS.1770](https://www.itu.int/rec/R-REC-BS.1770): loudness measurement and targets for the publishing presets
- [WebVTT](https://www.w3.org/TR/webvtt1/): caption output (VID-017, section 10)
- [Podcasting 2.0 namespace](https://github.com/Podcastindex-org/podcast-namespace): chapters, transcripts and other tags PUB-005 hands to QUILL Cast
- [PortAudio](https://www.portaudio.com/): the audio layer TG Drop Deck measured against (section 11.1)
- [Icecast](https://icecast.org/): the open streaming server family referred to in section 10C (direct streaming was not adopted there; section 10A now adopts it, see 10C.5)

### 21.5 Virtual audio cables

- [VB-CABLE](https://vb-audio.com/Cable/) and [VB-Audio's licensing and distribution terms](https://vb-audio.com/Services/licensing.htm): donationware, user-installed, never bundled (LIC-009, MX-127 to MX-129)

### 21.6 Speech, recognition and AI

- [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx): the torch-free ONNX runtime QUILL's offline speech and dictation use, and the route for local transcription in Studio (VIS-001)
- `quill/core/ai/` and the QUILL AI guide: the provider adapters, consent and cost disclosure VIS-006 build on

### 21.7 Independent products studied

- [MediAccess article (independent product reference)](https://hartgenconsultancy.com/introducing-mediaccess-part-1-opening-the-door-to-accessible-media/): publicly described workflows that inspired the scope, not code (LIC-006)
- [MediAccess Part 2: recording to finished production](https://hartgenconsultancy.com/introducing-mediaccess-part-2-from-recording-to-finished-production/): workflow evidence and coverage trace in section 6A; not a claim about Studio's implemented features or a product integration
- [REAPER user guide](https://www.reaper.fm/userguide.php) and [OSARA documentation](https://osara.reaperaccessibility.com/): professional editing and nonvisual workflow research for section 6B, not dependencies or source-code imports
- [GoldWave feature overview](https://goldwave.com/goldwave.php) and [Audacity audio editing documentation](https://support.audacityteam.org/audio-editing): independent workflow research for section 6C, not dependencies or source-code imports
- [TG Drop Deck source (MIT)](https://github.com/tonygeb23/tg-drop-deck), its [licence](https://github.com/tonygeb23/tg-drop-deck/blob/main/LICENSE) and [user guide](https://tgstudios.app/drop-deck-guide/): section 10C
- [Spotify pedalboard (GPL-3.0; see LIC-008)](https://github.com/spotify/pedalboard): considered and not adopted

### 21.8 The QUILL family: code and documents this PRD builds on

QUILL Studio is one app of the QUILL family and reuses its shared package rather than copying it. Each app below has an entry point in `quill/apps/`, a packaging shell in `standalone/<app>/`, and a user guide, changelog and PRD in `standalone/<app>/docs/`.

- **QUILL Studio** today: `quill/apps/studio.py`, `quill/apps/studio_*.py`, `quill/ui/audio_studio/`, `standalone/studio/docs/` (user guide, changelog, and the shipped-features PRD `standalone/studio/docs/prd.md`) and the earlier PRD in `docs/audio-studio/prd.md`, which this document expands
- **QUILL**, the editor: `quill/ui/main_frame*.py`, `docs/user guide/userguide.md`, `docs/Product Requirement Documents and Specifications/QUILL-PRD.md`; its AI, OCR and document-intake features are the ones VIS-001 and CAP-002 should reuse
- **QUILL Cast** (`standalone/cast/`): podcast publishing and playback; the receiving end of PUB-005
- **Quill Radio** (`standalone/radio/`): station playback, recording and output-device routing, the closest existing code to AARME's device handling
- **QUILL Transcribe** (`standalone/transcribe/`): transcription and diarization (VID-016, VID-017, CAP-005)
- **Quill Media Player** (`standalone/player/`): book and media playback, chapters, and the shared slider keys
- **Quill Converter** (`standalone/converter/`): batch media conversion (section 10)
- **QUILL Lite**, **Inkwell**, **Weather** and **Beacon** (`standalone/quilllite/`, `standalone/inkwell/`, `standalone/weather/`, `standalone/beacon/`): family conventions for menus, help and announcements that Studio follows
- Shared rules: `CLAUDE.md` (the family's gates), `quill/core/family_rules.py` (the eleven family rules), `docs/keyboard-reference.md` and `docs/f1-help-reference.md` (generated references Studio's keys and help join)
- Legal: `LICENSE`, `NOTICE`, `docs/legal/THIRD_PARTY_NOTICES.md`, `docs/legal/legal-notices.md` and `docs/legal/trademark-notices.md`


### 21.9 Screen and window recording (section 7A)

- [Windows.Graphics.Capture namespace](https://learn.microsoft.com/uwp/api/windows.graphics.capture): `GraphicsCaptureSession`, `IsCursorCaptureEnabled` and `IsBorderRequired` for REC-003 and REC-006
- [Desktop Duplication API](https://learn.microsoft.com/windows/win32/direct3ddxgi/desktop-dup-api): what FFmpeg's `ddagrab` uses for display targets
- [PrintWindow](https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-printwindow): the still-screenshot window renderer, `quill/platform/windows/screenshot_window.py`
- [SetWindowDisplayAffinity](https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-setwindowdisplayaffinity): `WDA_EXCLUDEFROMCAPTURE`, keeping Studio's own windows out of a display recording (REC-013)
- [FFmpeg devices: gdigrab](https://ffmpeg.org/ffmpeg-devices.html#gdigrab) and [FFmpeg filters: ddagrab](https://ffmpeg.org/ffmpeg-filters.html#ddagrab)
- `quill/core/speech/ffmpeg.py` (how QUILL finds its FFmpeg) and `scripts/check_ffmpeg_notices.py` (the notice gate LIC-004 relies on)
- `quill/platform/windows/process_loopback.py`, `quill/platform/windows/sr_detect.py` and `quill/core/dictation_owner.py`: process loopback, screen-reader detection and the shared microphone lock that REC-007 builds on
- QUILL Studio's shipped capture code: `quill/apps/studio_capture.py`, `quill/platform/windows/studio_capture.py`, `quill/platform/windows/screenshot_uia.py`, `quill/core/studio_capture.py` and `quill/ui/studio_capture_dialog.py`

### 21.10 Broadcast destinations named in section 10A

These are the destinations' own developer documents, cited so each adapter starts from the platform's terms; they are endpoints, not companion products (section 19).

- [YouTube Live Streaming API](https://developers.google.com/youtube/v3/live/getting-started) (BCAST-010, CHAT-002)
- [Icecast documentation](https://icecast.org/docs/) and [SHOUTcast](https://www.shoutcast.com/) (BCAST-011)
- [Microsoft Teams platform documentation](https://learn.microsoft.com/microsoftteams/platform/) (BCAST-012)
- [Zoom Meeting SDK](https://developers.zoom.us/docs/meeting-sdk/) (BCAST-013)
- [SRT, the Secure Reliable Transport protocol](https://github.com/Haivision/srt) (BCAST-012, BCAST-014)

### 21.11 Studio documents this plan depends on

- [`standalone/studio/docs/prd.md`](../../standalone/studio/docs/prd.md): what QUILL Studio already does; every *Delivered* line here points into it
- [`docs/design/quill-studio-capture-milestone.md`](../design/quill-studio-capture-milestone.md): the screenshot milestone's implementation and verification ledger, including the acceptance runs still owed
- [`docs/design/quill-studio-screenshot-coverage.md`](../design/quill-studio-screenshot-coverage.md) and [`docs/design/quill-studio-prd.md`](../design/quill-studio-prd.md): the earlier coverage audit and consolidated proposal this document supersedes
- [`docs/qa/screen-reader-checks-2026-10.md`](../qa/screen-reader-checks-2026-10.md): the family's open screen-reader checks
- `quill/core/radio/playlist_formats.py`: Quill Radio's playlist formats, which PL-006 reuses for M3U
- [`docs/Product Requirement Documents and Specifications/QUILL-PRD.md`](<../Product Requirement Documents and Specifications/QUILL-PRD.md>): the editor's PRD


**Important note:** Product behavior, code integration feasibility and final license compliance require an audit of the current QUILL repository and each dependency. This PRD is a specification of intended functionality, not proof all OS/audio sources can be routed independently on every Windows configuration.


## Appendix A. Requirement ID trace

Old IDs are the expanded PRD's unless marked *(C)*, the earlier consolidated proposal's. *Absorbed* means the requirement's substance is already in the named requirement, so it was not repeated. *Delivered* means it moved to `standalone/studio/docs/prd.md`.

| Old ID | New ID or home | Note |
|---|---|---|
| *(C)* UX-001 to UX-008, TRAY-001 to TRAY-005, MX-001 to MX-008, EDIT-001 to EDIT-003, DEMO-001 to DEMO-004, VIS-001 to VIS-008, VERIFY-001 to VERIFY-008, PREFLIGHT-001 to PREFLIGHT-011, VIDEO-001 to VIDEO-002, LIVE-001 to LIVE-002, PUB-001 to PUB-002, BCAST-001 to BCAST-025, CHAT-001 to CHAT-003, VID-001 to VID-034 | Unchanged | Partly delivered items carry a *Delivered so far* line |
| *(C)* CAP-001 | Delivered | Studio PRD AS-93 to AS-104; its semantic-region gap is the new CAP-007 |
| *(C)* CAP-002 to CAP-006 | Unchanged, with *Remaining* lines | Delivered parts: Studio PRD AS-97 to AS-111 |
| *(C)* Section 2.2, first two bullets | Delivered | Commit `529884ec`; Studio PRD section 1, P-1, REL-1 to REL-6 |
| *(C)* STUDIO-RENAME, STUDIO-SNIP | Delivered in code | Section 17 |
| — | CAP-007 | New: semantic regions |
| — | REC-001 to REC-018 | New: section 7A |
| — | MX-184 to MX-188, REC-019 to REC-024, BCAST-026, BCAST-027, VIDEO-004, VERIFY-009, UX-013 to UX-015, PL-008 | New, 2026-10-31: the audio-lessons review; each cites its source |
| AS-001 to SDK-001, CW-001 (scope matrix rows) | Dropped | A table of workspaces, not requirements; each workspace is a section here. The cart wall (CW) itself was withdrawn on 2026-10-31 |
| A11Y-001 | Absorbed by UX-001 | |
| A11Y-002 | Absorbed by section 2.1 (shell structure) | |
| A11Y-003, A11Y-007 | Absorbed by section 13 and UX-007 | |
| A11Y-004 | Absorbed by UX-002 | |
| A11Y-005, A11Y-011, A11Y-012 | Absorbed by UX-006 | |
| A11Y-006, A11Y-013 | Absorbed by UX-007 | |
| A11Y-008 | Absorbed by UX-008 | |
| A11Y-009 | Absorbed by UX-003 | |
| A11Y-010 | Absorbed by MX-001 and section 13 | |
| A11Y-014, A11Y-015, A11Y-016, A11Y-017 | UX-009, UX-010, UX-011, UX-012 | |
| MX-010 to MX-018 | MX-110 to MX-118 | Section 5.1 |
| MX-020 to MX-029 | MX-120 to MX-129 | Section 5.2; MX-127 to MX-129 are the VB-CABLE-related programme output, cable test and mix-minus |
| MX-030 to MX-039 | MX-130 to MX-139 | Section 5.3 |
| MX-040 to MX-045 | MX-140 to MX-145 | Section 5.4 |
| MX-050 to MX-057 | MX-150 to MX-157 | Section 5.5 |
| MX-058, MX-059 | TRAY-006, TRAY-007 | System-wide keys and second safety chords belong with the tray and global keys |
| MX-060 to MX-066 | MX-160 to MX-166 | Section 5.6 |
| MX-070 to MX-083 | MX-170 to MX-183 | Section 5.7 |
| AU-010, AU-011, AU-012 | Absorbed by EDIT-001, VID-001 | |
| AU-013 | EDIT-004 | |
| AU-014 | EDIT-005 | |
| AU-020 to AU-026 | Absorbed by EDIT-001, EDIT-002 | |
| AU-027 | EDIT-006 | |
| AU-028 | EDIT-007 | |
| AU-029 | EDIT-008 | |
| AU-030, AU-032 | Absorbed by EDIT-001, EDIT-003 and PUB-001 | |
| AU-031 | EDIT-009 | |
| AU-033 | EDIT-010 | |
| AU-034 | EDIT-011 | |
| AU-035 | EDIT-012 | |
| VD-010, VD-013, VD-014 | Absorbed by VIDEO-001, VID-014, VID-024 | |
| VD-011, VD-012 | Absorbed by VIS-005, VIS-006 | |
| VD-015 | Absorbed by VID-005, VID-007 | |
| VD-016 | Absorbed by VID-017 | |
| VD-017 | Absorbed by VID-019, VID-020 | |
| VD-018 | Absorbed by VID-018 | |
| VD-019 | Absorbed by VID-008, VID-027 | |
| VD-020 | VIDEO-003 | |
| CP-010, CP-011, CP-017 | Dropped | Superseded by CAP-004: capture is built natively; no ZoomIt code was imported. LIC-002 and LIC-003 stay in case that changes |
| CP-012 | Delivered (CAP-001) | Studio PRD AS-94 to AS-98 |
| CP-013 | Absorbed by CAP-003, CAP-004 | Named setups delivered: Studio PRD AS-102 |
| CP-014 | Absorbed by CAP-002 | Local OCR delivered: Studio PRD AS-105 |
| CP-015 | Delivered (CAP-001) | Studio PRD AS-101 |
| CP-016 | Absorbed by VERIFY-001 | Screenshot evidence bundle delivered: Studio PRD AS-109 |
| CP-018 | Absorbed by CAP-003 | |
| AI-010 | VIS-009 | |
| AI-011, AI-012, AI-013 | Absorbed by VIS-006, VID-022 | |
| AI-014 | Absorbed by VIS-001, VID-016, VID-017 | |
| AI-015, AI-016 | Absorbed by VIS-007, VID-021 | |
| AI-017 | Absorbed by VIS-008 | |
| AI-018 | VIS-010 | |
| CV-010, CV-012, CV-013 | Absorbed by PUB-001 | Convert Audio already shipped: Studio PRD AS-88 to AS-91 |
| CV-011 | PUB-004 | |
| CV-014 | PUB-003 | |
| PB-010 | PUB-005 | |
| PB-011 | PUB-006 | |
| PB-012 | PUB-007 | |
| PB-013 | Delivered | Auphonic mastering: Studio PRD AS-59 |
| PB-014 | Absorbed by PUB-001 | |
| REL-001 to REL-005 | Absorbed by section 2.2 | |
| REL-006 | TRAY-008 | |
| SEC-001 to SEC-006 | Absorbed by section 13 and VIS-006 | |
| SEC-007 | SEC-001 | Section 13.3 |
| LIC-001 to LIC-009 | Unchanged | Section 13.2 |
| GATE-01 to GATE-13 | SG-01 to SG-13 | Section 15.1; SG-11 withdrawn with the cart wall on 2026-10-31 |
| CW-010 to CW-018 | CW-001 to CW-009, withdrawn | Withdrawn on 2026-10-31 at the owner's decision; CW-007's rule continues as PL-008 |
| PL-010 to PL-016 | PL-001 to PL-007 | Section 10C.3 |
| Sections 1.3, 2.2, 16, 17, 20 (principles, workflows, roadmap, workstreams, definition of done) | Absorbed by the north star, section 15, section 14, section 17 and section 14's exit gates | |
| Section 11.1 (preferred approach) | Absorbed by MX-007 and section 11 | |
| Sections 11.2, 11.3, 14, 15.1, 15.3, 18, 19, 21, 22 | Sections 11.2, 11.1, 13.1, 15.2, 15.3, 16.1, 16.2, 21, 10C | |
