# QUILL Studio — Accessible Media Creation and Verification
## Consolidated Product Requirements Document

**Version:** 1.0 consolidated proposal · **Date:** 2026-10-26 · **Status:** Design specification, not a claim of implemented functionality

**Product decision:** Rename **QUILL Audio Studio** to **QUILL Studio**, maintaining the *same* application, shared source implementation, library, workflows, installation continuity and user data. The larger name reflects expansion from audiobooks into sound, images, screen demonstrations, video, live production, AI-assisted visual understanding and independently verifiable publishing.

> **North-star acceptance criterion:** A person who is totally blind, using only a keyboard, JAWS/NVDA/Narrator or braille, can independently capture, construct, inspect, correct, record, mix, export, and verify a media artifact without relying on inaccessible visual confirmation. Deterministically provable properties must be machine-tested; uncertain visual/semantic judgments must be labeled and escalated rather than represented as guarantees.

## 1. Decisions and evidence hierarchy

1. **Current implementation baseline:** `prd(20261026-191850).md`, `userguide(1).md`, `CHANGELOG.md`, `release-notes-1.0.md` and `release-notes-2.2.md` supplied by the project. These are documentation evidence, **not proof that each feature was tested in an installed build**.
2. **Expansion baseline:** `QUILL_Audio_Studio_Expanded_PRD(1).md` (2026-10-25). Its unconflicted functional requirements remain in scope, but references to external products or third-party software are not adopted; only VB-CABLE is retained as an explicitly named optional external tool. In particular retain its requirements for routing, editor, live playout, video, capture, AI, packaging, auditability, and complete keyboard operation.
3. **Availability:** Release notes describe 2.2.0 as **built, not yet released**, and some CHANGELOG items as **unreleased**. Never market these as publicly shipped until confirmed.
4. **Conflict rule:** Preserve working user journeys and the shared `quill.apps.studio` implementation; these consolidated additions supersede any prior plan to create another app or to call the expanded application QUILL Audio Studio indefinitely. Windows 11-first expansion is not a decision to remove current macOS audiobook functionality.
5. **External-tool scope:** The product specification describes QUILL Studio functionality in its own terms. VB-CABLE is the only named optional external tool/integration. Existing internal implementation dependencies are governed by engineering and license compliance, not presented as recommended companion products.

## 2. Preserve the existing application's layout and behavior

### 2.1 Existing shell: evolution, not replacement

Keep the startup **book/library tree with initial focus**, Favorites, In Progress, Recently Played, Inbox, existing folders, accessible status bar (F6 and arrow navigation), full menu bar, application tray, command palette (`Ctrl+Shift+P`), F1 help, existing preferences and shared voices, the narration/build wizard, Chapter Workbench, Book Tools, Sleep Timer, Play Queue, and converter/publisher. Do not displace current keyboard expectations.

**Home design:** One application main frame with a default **Library** workspace and a simple **Create** task menu/button. Add, in sensible order: Record audio, Mix audio, Record a demonstration, Capture or inspect screen, Edit audio/video, Create an image, Run a live show, Convert, Publish and Verify. The original three journeys—**Narrate Documents, Build From Recordings, Edit a Book**—remain first-class, identically named entry points. Users may pin their most-used workflows; startup may reopen the last workspace but should not silently change existing defaults.

**Menus:** File (projects/library/import/export), Create (old and new journeys), Capture, Audio, Video, AI & Visual Inspector, Tools, View, Help. **Do not steal existing Alt menu mnemonics**; keep Alt+B Book Tools, Alt+V View, Alt+I Voices if their established menus remain. Add new commands and mnemonics only after collision testing against every window/control. Existing command palette indexes legacy and new commands. Existing `Ctrl+,` preferences and safe mode stay functional.

**Shell structure:** Native wxPython controls for tree, tables, menus, dialogs, inputs and progress. Specialized audio/video canvases supply a *parallel structured list/tree representation* with UIA roles, names, values, relationships and fully equivalent actions. A canvas or waveform is never the only means to discover/edit content. Hide visual complexity until requested rather than presenting a giant dashboard.

### 2.2 Seamless rename and upgrade

- Display name, product documentation, Start Menu shortcut, installer metadata, taskbar/tray accessible names become **QUILL Studio**; old names can remain as discoverable aliases in Help and search.
- Retain `quill.apps.studio`, all shared `quill` audio pipelines, stored book identities, stable library paths, job files, `%APPDATA%\Quill`, portable `data/storage-mode.json`, secrets, voice packs and shared QuillVille runtime. Do not fork duplicate engines.
- Introduce an optional `studio-project` folder/schema for new productions and one-way/versioned migrations only after automated round-trip tests. Legacy `.quilljob` and existing books remain readable and editable.
- Preserve installer's ability to upgrade in place and portable zip's ability to run independently; detect and resolve old/new shortcut collisions; offer rollback and retain user data.
- Preserve macOS-supported legacy journeys. Windows-only mixer/capture functions are reported as unsupported with clear explanations, never causing the legacy app to fail at launch.
- Cross-app features (QUILL Editor, Radio, Cast, Lite, Transcribe) must communicate by stable shared APIs/asset exchange, not tight UI imports.

## 3. Core interaction model for totally blind users

**UX-001** Every workflow has an explicit start, review, action, independent verification and result step. Keyboard-only navigation must permit correction at any step.

**UX-002** Every parameter has editable numeric/text representation, unit, min/max, current value and reset command. Spatial operations accept coordinates, edges, sizes, offsets, timestamps and relative instructions rather than dragging.

**UX-003** Include **F6 workspace landmarks** (cycling between library, editor, sources, buses, verification report, status bar without breaking legacy F6 status behavior), carefully chosen configurable chords, context help, accelerator reference, shortcut conflict detection, and a searchable command palette. Make shortcuts discoverable *and* configurable. Avoid consuming typical JAWS/NVDA/Narrator or OS shortcuts by default.

**UX-004** Editing models: spreadsheet-like source/bus matrix; sortable but stable source list; timeline with tracks/regions as rows and named edit fields; camera controls with textual labels; screenshot canvas with OCR-based element list. Every important command available from menu, command palette, and keyboard accelerators where appropriate.

**UX-005** Never disrupt text fields with live-show hotkeys; swap active accelerators when focus is in composite edit controls. Do not reorder/remove a focused row during background activity. Do not disable the currently focused action button while a long-running task executes; handle double activation safely.

**UX-006** Provide three announcement levels: concise, standard, detailed. High-frequency meter feedback is on-demand/threshold-based rather than repetitive speech. All important status remains reviewable as text/braille and in a searchable event log. Reuse current live status bar and speech/braille announcement service.

**UX-007** Whole-app accessibility regression testing must involve JAWS, NVDA and Narrator, keyboard-only testers who are totally blind, Windows scaling/high contrast, 8 GB RAM devices, multiple sound drivers, offline and portable configurations. Accessibility success is evidenced by executable test scripts and actual user outcome logs, not simply a WCAG checklist.

**UX-008** Offer **guided mode** (plain-language steps), **standard mode** (compact task screens) and **advanced mode** (matrix, buses, automation), backed by the *same saved state*. No accessibility tax for obtaining professional functions.

## 4. Persistent tray and background control

**TRAY-001** Extend the existing tray rather than starting a second daemon. Tray menu must expose: Open QUILL Studio, recording status, Start/stop/pause recording, marker, mute mic, mute public bus, private monitor toggle, active scene, take screenshot, instant replay, recent projects, current background jobs, verification summary, Safe Mode state, Preferences, Exit.

**TRAY-002** Maintain existing opt-in Alt+F4-to-tray and safe close rules. Recording can continue with window minimized/hidden; exit/Windows logoff prompts and checkpoints active sessions as technically feasible.

**TRAY-003** Tray icon has reliable accessible name and descriptive status via Windows shell/UIA; no action accessible solely via right-click. All tray operations are also available through main-frame menus, global hotkeys (opt-in), and command palette.

**TRAY-004** Global hotkeys use runtime collision detection, a keyboard-accessible configuration screen and clear feedback when another application intercepts a chord. Emergency stop is separately discoverable and robust. Global hotkeys should not steal keys needed for screen readers.

**TRAY-005** Status: `Recording 00:12:31; microphone live; application audio live; screen-reader audio private; frames dropped 0; disk estimated 43 minutes remaining`. The live status must be queryable without stealing focus or contaminating recordings.

## 5. Audio source routing, recording and VB-CABLE

**MX-001** Native capture: microphones, Windows render endpoints, system loopback, supported per-process/process-tree loopback, local media players, virtual input/output devices and supported remote sources. Show what can actually be captured and why something cannot.

**MX-002** Separate **private monitor**, **program/live broadcast**, **main recording**, **isolated stems**, **cue/preview**, and user AUX buses. Each source/bus has independent gain, mute, solo, monitor, record-arm, per-destination send and destination device. Source/list aliases are stable across reconnects.

**MX-003** Default screen reader speech to **private only**. Allow intentional recording/broadcast of screen reader speech for demonstration, but require explicit destination choice and audible/text confirmation. No unsupported promise of independent per-utterance splitting from one screen-reader process.

**MX-004** Integrate **VB-Audio VB-CABLE** as a user-installed and supported optional solution—never silently bundle/install a driver or require it for basic microphone/loopback work. Detect CABLE endpoints, allow named source/destination mapping and provide wizard-based test/recovery. Spell out the counterintuitive nomenclature: *CABLE Input* is the Windows playback device QUILL sends to; *CABLE Output* is the Windows recording device another app receives from.

**MX-005** **Routing Setup Wizard**: choose desired outcome (podcast, conference call, demo, livestream, accessibility test), discover sources, choose device(s) and optional VB-CABLE routing, play safe probe to chosen destination, measure return capture where feasible, check feedback/double-capture, show routing diagram *as an accessible textual bus table*, optionally verify with a second participant/receiving app, save preset. State whether a complete end-to-end test was possible; no false-positive passed badge from mere endpoint detection.

**MX-006** On device removal, driver sample-rate changes, process restart, crash or OS default-device switch: preserve identity and project settings; announce degradation, protect active media files, attempt a configured fallback *only when privacy routing cannot become broader*. Record start/stop/event stamps and sample dropouts to integrity log.

**MX-007** Provide audio-interface ASIO/WASAPI shared/exclusive capabilities based on tested feasibility, buffering/latency diagnostics, clock-drift correction, and feedback loop detection. Favor a native real-time helper process for timing-critical capture/mixing, bridged to wxPython by versioned IPC; do not do real-time DSP on the GUI thread.

**MX-008** Cue, user monitoring and verification speech may never enter public/recording buses unless users expressly select them; lock default privacy behavior and enforce negative routing assertions in test harness.

## 6. Audio editing, recording and demonstrations

**EDIT-001** Timeline with cursor in samples/timecode, accessible track-region list, inserts, slips, trims, splits, ripples, ripple exclusions, fades, crossfades, markers, named chapters, envelope automation, gain/pan, sidechain/ducking, silence detection, punch-in/out, loop recording, multi-take comping, noise removal and reversible processing.

**EDIT-002** Professional but discoverable controls: Ctrl+J-like configurable jump to time, seek by frame/second/minute/marker, read region start/end/duration/peak, preview before/after, undo history, nondestructive saves and autosave. Dedicated accessible keyboard tutorials embedded in help.

**EDIT-003** Effects chain list with order, enable/bypass, presets and explicitly typed parameters; loudness/true-peak/peak/noise-floor/waveform statistics spoken and recorded as text. Record per-source stems for post-production, including optional separated screen-reader track if physically or process-isolated.

**DEMO-001** Guided **Record a Demonstration** workflow: name demo, select application/window/display, choose full window or deterministic crop, choose pointer/focus highlight, select audio sources and microphone, explicitly include/exclude screen reader, privacy scan, trial recording, visual/audio preflight, start/pause/marker/stop, review timeline and output validation.

**DEMO-002** Support **audio-only demo**, **screen-and-audio demo**, **webcam + screen** and **screenshot sequence with narrated audio**. Users can record spoken descriptions then convert into captions, chapter bookmarks, slide callouts and accessible accompanying transcript.

**DEMO-003** Optional interaction-event track: keyboard shortcuts (privacy-safe redaction), focused accessible role/name, application changes, pointer/click annotations; synchronize it with captured frames/audio. Sensitive keystrokes and password fields are never logged; warn when determining sensitivity is impossible.

**DEMO-004** Automatic scene suggestions: remove dead time, create intro/outro, flag silence, clipping and mismatched audio; AI may propose edits but applies none without explicit review, undo and preview.

## 7. Screen capture and accessible visual tools

**CAP-001** Keyboard-triggered full screen, active window, named application, UIA element, logical region, selected rectangle by numbers, scrolling capture where possible, and timed/sequence captures. Clipboard and file destinations; timestamp, application/window identity, coordinates, scale factor and capture-success metadata.

**CAP-002** **Screenshot Inspector**: identify dimensions, OCR all text with confidence and reading order, list detected UI elements and their positions, detect cut-off text and overlays, compare screenshots, ask follow-up questions about the image, find target by text/semantic description, zoom/crop via keyboard, run redaction and export alt text or detailed description.

**CAP-003** Annotate *without drawing*: choose arrow/rectangle/spotlight/highlight/text callout, anchor to recognized UI element or percentage/coordinates, define size/style/order, preview verbally, revalidate target still exists, render to PNG/JPEG and optional layered project. Add visual magnification, cursor/focus highlight, presentation break timer and spoken countdown.

**CAP-004** Provide built-in, keyboard-accessible region snipping, screen recording, zoom and annotation, capture timers, OCR, image inspection, image resizing, format conversion, clipboard transformations, command discovery, shortcut-conflict detection, and saved recording/capture workspaces. Implement these as integrated QUILL Studio capabilities with one command registry, one accessibility model and shared project state.

**CAP-005** Offer **Capture and Dictate**: press screenshot hotkey, speak a description/comment, local or optional cloud transcription, return a paired screenshot + verified transcript + timestamp, copy/paste as package or export to HTML/Markdown/issue tracker. Maintain microphone routing privacy while capturing.

**CAP-006** Capture preflight: protected window/black frame, minimized/occluded content, focus lost, unexpected monitor, unexpected app title, cropping off edge, masking failures, overlapping tooltip/dialog, pointer obstruction and notifications. Report detected risks and attempt a correction or offer exact deterministic commands. Capture APIs' limitations must be exposed.

## 8. AI Visual Inspector and blind-first visual confidence

**VIS-001** Dedicated **Understand What Is On Screen** command for live window, selected region, screenshot, imported image, webcam frame and video frame. Use both UI Automation structure and OCR, then vision model(s); never silently assume model interpretations are proven.

**VIS-002** Answers organized in layers: brief scene summary; objects/people/layout; extracted exact text; UI controls and state; precise coordinates/bounding boxes; colors/contrast; image quality; likely composition issues; warnings and uncertainty; user's follow-up question. Provide keyboard navigation through each result.

**VIS-003** **Conversation grounded to artifact**: “Is my entire dialog visible?”, “What does the red error say?”, “Where is the camera pointing?”, “Is the face centered?”, “What changed from last screenshot?”, “Describe the chart and axes.” Preserve image hash, source, region, frame index and corresponding evidence so the user can ask follow-ups without accidental cross-image confusion.

**VIS-004** For deterministic claims, prefer pixel/math/metadata/UIA/OCR validation. Examples: pixel dimensions, capture rect within display, text detected, named application matching intended window, frame blackness threshold, audio/video sync and element bounding-box intersection. Combine with AI to identify semantic content, but report uncertainty in plain English.

**VIS-005** **Blind camera coach**: startup frame analysis, face/object position and crop, horizon/orientation, headroom, lighting, motion, blur, exposure and background distractions; give incremental directional corrections, recheck after every user adjustment. Never assert that a person is visible if visual evidence is insufficient; provide no-face/no-confidence warnings.

**VIS-006** Optional provider adapters for local vision models when hardware capable, user-supplied cloud vision API keys and accessible provider settings. Show image/data selected for sharing, where it goes, estimate costs when possible, consent, privacy and safe mode. Offline capture/edit should never depend on AI service being available.

**VIS-007** Accessible visual revisions: user instructs “move annotation right 30 pixels”, “crop left until no toolbar”, “use a darker caption box”, “replace image background” (when integrated provider supports image editing); preserve originals, preview changes, verify export dimensions and report visually uncertain aspects. Every operation reversible, with stable artifact versions and provenance.

**VIS-008** Visual accessibility authoring: meaningful alt text, extended description, transcript, video audio description track, caption contrast and safe-area inspection, and readable chart/table reconstruction with confidence caveats. Provide a reviewable text representation separate from the rendered visual.

## 9. Verification Center: near-100% independently verifiable path

**VERIFY-001** Each workflow produces a machine-readable and screen-reader-readable **Evidence Report** (`.json` plus `.md/.html`) with: user goal; source identity; steps completed; configuration; file hashes; audio routing graph; intended tracks; actual tracks; media codec; dimensions; duration; timing; error logs; AI findings; verification status; unresolved risks; export location.

**VERIFY-002** Use explicit result states: **Verified** (objective automated check passed), **Verified with external loopback** (downstream captured sample passed), **Needs human judgment**, **Not verified**, **Failed**. Never collapse AI semantic confidence into “Verified.” A failed/unknown check blocks an optional **Strict Publish** profile until fixed or consciously waived with recorded explanation.

**VERIFY-003** Preflight checks: target app/window identity; correct crop; nonblack test frames; expected source activity; privacy isolation; VB-CABLE send/return; available storage; supported format; clipping/noise; camera framing; actual 5–10-second practice capture; ask user whether playback sounded right; track any checks that cannot be automated.

**VERIFY-004** During recording: recoverable segment files, heartbeat, dropped frames, source disconnect, timestamp jitter, data flow, disk capacity, peak detection, rendering progress, marker log and route changes. Never say “recording safely” when no frames/samples are actually arriving.

**VERIFY-005** After recording: reopen exported media independently, decode first/middle/last sections, confirm expected audio/video streams, positive sample/frame counts, timestamp monotonicity, stream alignment, expected duration, loudness, freeze/black frame sampling, audible mic samples, absence of disallowed sources where technically testable, user-selected screenshot frame comparisons, and hash final exports.

**VERIFY-006** For public/private mix isolation, distinguish *routing configuration verified* from *actual external output verified*. If possible capture audio after the virtual cable and assert intended audio tone present and private cue absent using known test signals. During real content, privacy leakage cannot always be conclusively proven; preserve safe defaults and clearly disclose that limitation.

**VERIFY-007** **Guided verification questions**: “What can I prove?”, “What still needs checking?”, “What does the image actually show?”, “What should I fix next?”, “Replay the ten seconds around this warning.” Every issue has jump-to-time/frame/track and suggested action. Confirmation is not one opaque Pass button.

**VERIFY-008** Release benchmark: 100% of mandatory machine-testable checks executed; 0 silent failures; 0 inaccessible critical controls; 0 published strict-profile outputs with failed mandatory checks; truthfully disclose all model-dependent visual judgments. This is a robust *verification pathway*, not an impossible claim of 100% semantic accuracy.

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

**LIVE-001** Adopt accessible **cart wall**, named banks, queued tracks, running order, dual deck/crossfade, hotkey-triggered audio cues, ducking, emergency silence, mic talkover, playlist and live scene changes; guard against bare-key activations while typing and background updates that steal focused rows. Preserve private preview/cue path.

**LIVE-002** Support recording live program and stems simultaneously, reliable long-running scheduling, output to virtual cable or documented streaming integration, metadata/now-playing and QUILL Radio/Cast handoffs through shared contracts.

**PUB-001** Reuse current audiobook quality checks, chapter workbench, built-in conversion pipeline, audiobook rendering, RSS feed, metadata and publishing services. Extend to MP4/MKV, social clip profiles, VTT/SRT captions, transcript/description packages and accessibility verification bundle.

**PUB-002** Publish screen includes concise review: title, destination, privacy, rights, captions, transcript, alt text, credits, encoder settings, estimated cost, test results and user confirmation. Export atomic temp-to-final with failure rollback and no silent overwrite.

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

### 10A.5 Audio and video demonstration examples and acceptance tests

1. **YouTube live demonstration:** A totally blind presenter selects an Edge window, runs short preflight, verifies screen bounds and title visibility via OCR and AI with caveats, broadcasts intentional screen-reader demo speech but excludes QUILL cues, monitors audience questions privately, and records local video/audio/captions. Starting live requires clear confirmation and the result records ingest and downstream-verification levels.
2. **Icecast/SHOUTcast radio show:** Presenter chooses an audio-only profile, privately cues tracks, talks over music, plays station IDs, shows now-playing metadata and listener checks, connects securely, and records the master plus mic/music stems. An unplugged input triggers safe recover/retest and an accessible on-air warning.
3. **Teams town hall:** A presenter discovers whether RTMP-In/SRT-In is permitted; if not, the app explains how to participate using allowed meeting capture/share and audio devices. It must never misleadingly report an RTMP feed as active when the tenant forbids ingest.
4. **Zoom tutorial:** A host sets mic/program feed through approved routing, selects screen/camera sharing, tests echo and private speech leakage, verifies authorization for capture, speaks with guests and saves separate tracks only when technically available. During an interruption, user can issue **Pause and Fix**, recover, and resume with a marked discontinuity.
5. **Mixed audience experience:** Live questions from an available authorized chat connector enter a stable keyboard list; presenters can prioritize, cue and read them aloud intentionally. Private chat/screen-reader announcements never leak to the program mix by default.

### 10A.6 Engineering deliverables and release order

- **P0 foundation:** Shared program/private/record buses; Live workspace, reliable local show/record loop, trial run, end-to-end objective checks, fault recovery, complete keyboard/tray operation and explicit readiness states.
- **P1 audio broadcast:** Icecast/SHOUTcast and generic streaming profiles; native playlist/cart wall, metadata, listener confidence loopback, chat/Q&A infrastructure.
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

## 12. Keyboard model and discoverability specification

Keep all established chords. Reserve a **command registry**, not scattered handlers, for new shortcuts. Propose, subject to conflict testing: `Ctrl+Shift+P` command palette (existing), `Ctrl+,` preferences (existing), `F1` contextual help, `F6` existing status access, `Ctrl+Alt+Shift+R` start/stop demo, `Ctrl+Alt+Shift+S` capture screenshot, `Ctrl+Alt+Shift+V` inspect current visual, `Ctrl+Alt+Shift+K` read verification, and user-configurable recording marker, mic/program mute and emergency stop. These are suggestions only—**do not install untested shortcuts automatically**. Screen reader pass-through and keyboard focus safety win over mnemonic cleverness. Every shortcut can be read from the menu and searched in a keyboard reference; conflicts identified with OS, other QUILL apps, screen readers and system-wide shortcuts.

Examples of speech results: “Window Microsoft Edge, 1280 by 720, target visible; browser address bar not within crop; two possible notification overlays; capture ready with warnings.” “Recording started; screen and microphone active, JAWS private; VB-CABLE output verified by loopback.” “Export completed; audio, 2 minutes 41 seconds, captions present; 12 seconds may have clipped titles; verification needs review.”

## 13. Accessibility, privacy and reliability nonfunctional requirements

- No unannounced focus changes, background updates reordering focused rows, unlabeled icon-only controls, inaccessible custom scrollbars, drag-only editing or silent errors.
- Checkpoints and incremental recording segments to survive process crash/power loss where media APIs and storage permit. Atomic exports and safe recovery workflow.
- Audio processing and UI accessibility remain functional with cloud AI disconnected; explicitly degrade optional features.
- Guarantee no unsolicited capture/upload, screenshot sharing, microphone recording or public routing. Show live capture indicator; sensitive windows may be excluded by setting/policy.
- Provide text-based self-diagnostics that can be copied/sent with private fields redacted and user review. Logs include no raw transcript, keys, audio or screenshot without opt-in.
- Quantitative performance budgets and stress tests on 8GB/no-GPU Windows machines; document latency/dropped-frame targets **only after hardware benchmarks**, not guessed promises.
- JAWS, NVDA, Narrator and keyboard-only manual user testing required for every major workflow and migration.

## 14. Priority and incremental roadmap

**Phase 0 — Rename safely and preserve behavior:** Name/UI/installer/tray metadata changes, no code forks, migration+regression suite, keyboard registry, baseline screenshots/AT tests, untouched three old journeys. Ship nothing until a user can upgrade and open old books/jobs.

**Phase 1 — Verified recording foundation:** Recorder shell and project format, source discovery, mic/system/process loopback, VB-CABLE detection and test wizard, private/program/stem buses, tray transport controls, short practice capture and Evidence Report v1. This has higher value than image generation first.

**Phase 2 — Demonstration and capture:** Window/screenshots, numerical cropping, OCR, AI visual inspector and grounded conversation, redaction, annotation, spoken screenshot dictation, demo recording, synchronized user narration, first-class export verification.

**Phase 3 — Editing and production:** Accessible multitrack editor, clip operations/effects, image/video timeline, text-driven visual callouts, reusable scenes, captions/transcripts, audio description, live carts and running order.

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

## 16. Open design decisions requiring engineering tests

- Exact supported Windows API and build matrix for process loopback and window capture, audio exclusions, hardware GPU requirement and DRM behavior.
- Whether a chosen virtual cable allows external receiver monitoring/probing without introducing echo or temporary public leakage; include isolated test mode.
- Licensing, attribution and redistribution compliance for existing packaged dependencies, without introducing additional named third-party tools into the product workflow.
- Live streaming integration interfaces per destination; don't promise guaranteed per-app injection or per-participant capture.
- AI providers, model sizes, CPU 8GB suitability, OCR accuracy, camera guidance frequency and privacy terms.
- Precise keyboard assignments and screen-reader conflicts measured with NVDA, JAWS and Narrator.
- Consistent current macOS support and compatibility for existing journeys as Windows-specific capture expands.
- Project schema and shared-service release policy across independently updated QUILL apps.

## 17. Development backlog, issue-ready epics

| Epic | Phase | Essential done criteria |
|---|---:|---|
| STUDIO-RENAME | 0 | Name changes without broken profiles, books, jobs or shortcuts |
| STUDIO-SHELL | 0 | Legacy library initial focus, F6/status, menu and command palette stable |
| STUDIO-KEYS | 0 | Searchable, configurable, collision-tested keyboard registry |
| STUDIO-TRAY | 1 | Recording/status/scene/mute reachable from tray and keyboard without focus loss |
| STUDIO-ROUTING | 1 | Isolated stems and private/program buses; independent routing test |
| STUDIO-VBCABLE | 1 | Endpoint wizard, readable directionality, test audio, recovery |
| STUDIO-RECORD | 1 | Crash-resilient capture, timing and media decode QA |
| STUDIO-VERIFY | 1 | Evidence manifest and explicit Verified/Unknown/Failed reporting |
| STUDIO-SNIP | 2 | Keyboard numerical crop, named-window screenshot and redaction |
| STUDIO-VISION | 2 | OCR+UIA+AI grounded questions, artifact provenance and uncertainty |
| STUDIO-DEMO | 2 | Narrated screen demonstration, private speech policies, review/edit/export |
| STUDIO-EDIT | 3 | Nonvisual multitrack edit with reversible effect/region operations |
| STUDIO-VIDEO | 3 | Professional accessible NLE with precise multitrack edits, effects, captions and verification |
| STUDIO-VIDEO-EDIT | 3 | Ripple/roll/slip/slide edit operations, frame-precise navigation, nondestructive undo/redo |
| STUDIO-VIDEO-COMPOSE | 3 | Picture-in-picture, numeric crop/position, titles, lower thirds, transitions and keyframes |
| STUDIO-VIDEO-AI | 3-4 | Timecoded visual inspection, proposed edit plans with human approval and provenance |
| STUDIO-VIDEO-QA | 3 | Full-file decode, AV sync, caption and output validation, honest uncertainty report |
| STUDIO-LIVE | 1 | Live workspace, accessible cart wall, preview, running order and public bus |
| STUDIO-ON-AIR | 1 | Offline/test/armed/live/reconnect states, independent output health and tray commands |
| STUDIO-RADIO-STREAM | 1 | Icecast/SHOUTcast secure source-client streaming, metadata, loopback and recovery |
| STUDIO-YOUTUBE-LIVE | 2 | Authenticated or stream-key video ingest, private rehearsal and audience chat where authorized |
| STUDIO-TEAMS | 2 | Policy-aware RTMP/SRT event ingest plus permitted meeting-presenter routing |
| STUDIO-ZOOM | 2 | Permission-aware meeting audio/video paths, optional later SDK integration |
| STUDIO-LIVE-CHAT | 2 | Stable keyboard list, private notifications, moderation and explicit on-air reading |
| STUDIO-PUBLISH | 3 | Media/accessibility bundles and strict publish gate |
| STUDIO-CAMERA | 4 | Blind framing coach with incremental rechecks |

## 18. Requirements trace and notable gaps found

**Already documented in today's product artifacts:** Book-centered library; wizard; narration and assembly; chapter workbench; speech/voice engine sharing; source converter; ACX analysis; publishing; tray and close policy; configurable Studio app sounds; command palette; status bar with F6; accessible announcements and braille; portable/shared runtime. These must remain.

**Expanded PRD already anticipated:** Audio graph, independent monitoring, optional virtual cable, screen reader isolation, video/capture, advanced editing, AI, screen annotation, live playout, accessibility acceptance. These are not assumed already shipping.

**Live broadcasting extended:** Native YouTube Live, Icecast/SHOUTcast, Zoom and Teams destination workflows; chat/Q&A and guest paths; transport/permissions distinctions; rehearsals, safe automatic repair, live monitoring, private/program mix isolation, simultaneous archival recording and verifiable output evidence.

**Expanded full video editing:** Nondestructive professional nonlinear editing, structured screen-reader timeline, slip/slide/ripple/roll, effects, keyframes, picture-in-picture, transcript editing, captions, audio description, AI-assisted proposals, trial runs, independent export verification and detailed acceptance tests.

**Newly made explicit here:** Exact QUILL Studio rename; no breaking navigation; independent *verification center and graded evidence*; detailed VB-CABLE setup; assistant-powered visual comparison and evidence grounding; accessible captured-element/annotation positioning; guided narrated demonstrations; screenshots+dictation; persistent tray command model; concrete release gates and compatibility scenarios.

## 19. Supported external integration and self-contained feature policy

**VB-CABLE** is the sole explicitly named optional third-party routing utility in the QUILL Studio user-facing specification. YouTube, Icecast, SHOUTcast, Zoom and Microsoft Teams are supported transmission/meeting destinations rather than recommended companion production software. Official reference: [VB-Audio VB-CABLE](https://vb-audio.com/Cable/). QUILL Studio must remain fully usable for basic capture, recording and editing when VB-CABLE is absent. Detect it when present; provide accessible routing configuration, test signals, loopback verification, clear installation guidance when requested, device-disconnect recovery and truthful privacy/isolation status. Never install or reroute the driver silently.

All other functionality—including screenshot creation, OCR, annotations, screen/video capture, visual understanding, image generation workflows, audio mixing, transcription, command discovery, tray controls, video/audio conversion, guided rehearsal and remediation—must appear as native QUILL Studio tasks, not referrals to or comparisons with other products.

The existing application's internal runtime libraries, codecs and services may continue to be used where already implemented; their legal notices remain in engineering/build documentation. This policy removes named external-tool feature comparisons, not the obligation to document dependencies and licenses accurately.

## 20. Final product direction

QUILL Studio should *feel like the familiar accessible audiobook application* until the user chooses a new production task. From there it becomes a complete accessible media workstation with precise audio routing, repeatable keyboard operation, independently interrogable visuals, optional AI assistance and **evidence-backed outcomes**. Protect existing users, design first for total blindness, and prefer auditable proofs over optimistic “looks good” claims.


## 21. Accepted execution order and current implementation ledger

The user has prioritized a small, verifiable screenshot milestone immediately after the rename, before video demonstration recording and optional sound. This execution order supersedes the order of the broad phase headings above without removing any longer-term requirement.

The rename is committed on local main as `529884ec`. Preserve the existing installation, runtime, data and audiobook workflows. The screenshot milestone adds explicit named-window, display, full-desktop, active-window and numeric-region selection; configurable global screenshot hotkeys; local OCR; image-grounded AI conversation with rich editable prompt styles and user-defined prompts; and optional automatic AI following explicit connection-specific approval. It saves objective file evidence separately from uncertain model findings.

Implementation and verification are tracked in [the screenshot milestone and ecosystem review](./quill-studio-capture-milestone.md). That ledger identifies what has been tested and what remains unverified. Do not mark the whole CAP, VIS or VERIFY epics complete based on this slice. In particular, real screen-reader acceptance, installed upgrade testing, live AI-provider runs, UIA-element and scrolling capture, annotation/redaction editing, video/audio routing and recorded-demo verification remain separate gates.

Automatic AI must remain off by default, honor Safe Mode and AI Off, use a named approved provider/model/endpoint, stop unsent work when permission is revoked and never silently switch to a new provider or screenshot. Users may extend a preset, save a custom prompt, ask their own question and converse about the same image without recapturing their desktop.
