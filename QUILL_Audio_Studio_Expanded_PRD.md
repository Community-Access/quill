# QUILL Audio Studio — The Accessible Media Creation Suite
## Comprehensive Product Requirements Document (PRD)

**Document status:** Proposed expansion of an existing QUILL-family product; implementation specification, not an assertion of current functionality.  
**Version:** 1.0 draft  
**Date:** October 25, 2026  
**Product:** QUILL Audio Studio (existing name retained)  
**Working tagline:** *The Audio Works — Capture. Mix. Create. Verify. Publish.*  
**Platform:** Windows 11 first; assess Windows 10 support based on subsystem API requirements.  
**Distribution:** Free and open source; offline-capable core, optional paid third-party cloud services by user choice.  
**Source of requirements:** Existing QUILL plans; conversation requirements for extensive source mixing; accessible media workflows described publicly for MediAccess; ZoomIt/PowerToys source and Microsoft Windows audio APIs; live-show playout lessons from TG Drop Deck (MIT, section 22).

---

# 1. Executive decision and product strategy

## 1.1 Decision

**Expand existing QUILL Audio Studio; do not create another competing QUILL product.** Keep its identity, users, settings, recordings, and integration contracts intact. Add a suite of specialized, task-focused workspaces behind one accessible shell. Existing QUILL Audio Studio capabilities must continue working while subsystems are progressively replaced or enhanced.

## 1.2 Vision

An independent blind or low-vision creator must be able to record and mix numerous sources, control what is privately monitored versus broadcast versus saved, verify screen or camera framing, edit audio and video, generate and inspect images, and publish accessible media **without a mouse, specific screen-reader dependency, mandatory account, or mandatory cloud service**.

## 1.3 Guiding principles

1. **Audio routing is foundational.** Microphones, applications, system audio, screen reader speech, files, virtual devices, and remote sources are peers in the same source model.
2. **Hearing is not broadcasting.** Separate private monitoring, audience output, main mix, and independent track recordings. Screen-reader cues remain private unless explicitly routed otherwise.
3. **Simple by default, powerful on demand.** Common actions are quick; advanced routing and automation remain discoverable.
4. **Native keyboard and accessibility semantics first.** Do not rely on screen-reader scripts to compensate for inaccessible controls.
5. **Non-destructive and recoverable.** No accidental loss of original media, irreversible edits, or silently overwritten takes.
6. **Local-first and transparent.** No undisclosed upload of captured screens, microphones, recordings, or transcript text.
7. **Integrate rather than duplicate.** Reuse QUILL audio, converters, podcasts, provider, and speech services through common APIs.
8. **Source restrictions are real.** Do not claim per-tab capture, separation of output from one screen-reader process, or DRM capture absent validated technical support.
9. **Respect original creators and licenses.** Publicly described workflows inspire independently developed product features; code and branding are used only with permission or suitable licenses.

## 1.4 Out of scope / explicit non-goals

- Reproducing MediAccess source, UI text, branding, or proprietary assets.
- Replacing QUILL Editor, QUILL Radio, or QUILL Cast with incompatible clones.
- Guaranteeing per-participant conferencing audio, browser-tab separation, or per-utterance screen-reader routing without integrations that provide it.
- Circumventing DRM, protected streams, security boundaries, or Windows permissions.
- Requiring virtual audio kernel drivers for baseline operation.
- Assuming AI image generation, hosted transcription, or enhancement services can be delivered at zero operating cost.

# 2. Users, jobs, and scenarios

## 2.1 Personas

- Screen-reader-dependent podcaster working with JAWS, NVDA, or Narrator.
- Blind musician needing full multitrack arrangement and real-time recording.
- Accessibility professional documenting keyboard defects with screenshots, audio, and video.
- Teacher/presenter demonstrating software while privately monitoring screen reader speech.
- Low-vision video creator who needs magnification, framing assistance, and legible controls.
- Casual user converting audio/video and adding captions without learning a DAW.
- QUILL Radio/Cast/Editor user moving assets between familiar tools.

## 2.2 Critical workflows

1. **Clean podcast:** Select mic + remote audio; route JAWS only to headphones; record isolated tracks + clean mix; preview edits; normalize and export.
2. **Accessible demonstration:** Capture application audio and intended screen reader speech; exclude private mixer announcements from published track when physically/logically separable; record screen; annotate defects.
3. **Music session:** Record mic/instruments while playing backing tracks; independently monitor, arm, mute, solo, punch in, and mix multiple tracks.
4. **Webinar:** Hear personal cues, broadcast mic and application demo, suppress notification sounds, switch scenes safely.
5. **Visual confidence:** Frame webcam using spoken guidance, capture region via keyboard, inspect text and visual description, correct before publication.
6. **Convert and publish:** Batch process files, preserve metadata, add captions/chapters, export to accessible formats.

# 3. Functional areas and scope matrix

| ID | Workspace / subsystem | Core deliverables | Priority |
|---|---|---|---|
| AS-001 | Accessible Shell | Task launcher, command palette, universal settings, F1 help, accessible status and notifications | P0 |
| MX-001 | Audio Routing and Mixing Engine | Source discovery, capture, routing matrices, per-source gain/mute/solo, meters, recording, presets | P0 |
| AU-001 | Audio Editor | Single/multitrack nondestructive editor, markers, time navigation, fades, DSP and export | P0-P1 |
| CV-001 | Media Converter | Batch audio/video conversion, metadata, presets, job queue | P1 |
| CP-001 | Capture Studio | Keyboard screenshots, OCR, annotations, scrolling captures, ZoomIt features | P1 |
| VD-001 | Video Studio | Webcam/screen recording, spoken framing, video timeline, captions | P1-P2 |
| AI-001 | AI and Verification | Frame descriptions, image conversation/generation, transcription, captions, quality checks | P1-P2 |
| PB-001 | Publishing | Chapters, show notes, accessible exports, QUILL Cast/Editor handoff | P2 |
| SDK-001 | Shared Platform | API, plug-in interfaces, settings, assets, portable mode and diagnostics | P0-P2 |
| CW-001 | Cart Wall and Running Order | Keyboard soundboard (banks of prepared sounds), two-deck running order with crossfades, live track log; see section 22 | P1-P2 |

# 4. Accessibility-wide requirements

## 4.1 Interaction model

**A11Y-001:** All major workflows usable without pointing device: create, configure, start, stop, review, edit, export, troubleshoot.  
**A11Y-002:** Use native accessible controls where practical (QUILL's wxPython/native-control conventions preferred); supply rich UI Automation metadata for custom timeline, mixer and canvas elements.  
**A11Y-003:** Name/role/value/state/description/shortcut and accurate focus order for all actionable controls.  
**A11Y-004:** Every numeric parameter accepts typed entry in addition to arrow/slider adjustment; value units explicit.  
**A11Y-005:** Verbose, standard and concise speech verbosity profiles; never unsolicited recurring meter announcements while editing.  
**A11Y-006:** JAWS, NVDA and Narrator all supported; no screen reader detection required for core operation. Integration adapters may enhance announcements without becoming dependencies.  
**A11Y-007:** High-contrast, Windows text scaling, zoom, reduced motion, logical reading order, visible focus indicator.  
**A11Y-008:** Progressive disclosure: task wizard, normal mode and advanced routing mode display the same underlying state.  
**A11Y-009:** Context-specific F1 help, searchable command list, discoverable shortcuts, and optional guided mode.  
**A11Y-010:** Accessible diagnostics: source availability and routing restrictions explained in plain language; never fail silently.  
**A11Y-011:** Provide braille-friendly textual timecodes and status; do not hide critical information behind auditory cues alone.  
**A11Y-012:** Status update priorities—critical recording error interruptive, routine meters queryable, progress polite and throttled.  
**A11Y-013:** WCAG 2.2 AA used as a useful interface benchmark where applicable, plus native Windows UIA and keyboard expectations; manual assistive-technology tests mandatory.  
**A11Y-014:** A control's accessible name changes the instant the *user edits* what it represents (rename, reassign, clear), focused or not, so "did that apply?" is answered without tabbing away; it never changes because *playback state* changed while focus is on it (a pad or row is not relabelled "playing" under the user's fingers, which restarts speech mid-sentence). Playback state is answered on demand instead. Acceptance: with NVDA and JAWS on a pad, renaming it is read at once; firing it, and it finishing, produce no re-read. (Source: TG Drop Deck `SoundButton.refresh`, section 22.)  
**A11Y-015:** A live-updating list never removes or reorders the *focused* row; a removal that would take it is held until focus moves, after which it is silent. Measured by TG Drop Deck with an MSAA hook on a `wx.ListCtrl` under NVDA: deleting a row above or below focus raises no focus event, while deleting the focused row moves focus to a row the user did not choose. Acceptance: an up-next list draining during playback never causes an unprompted focus announcement.  
**A11Y-016:** Workspace-local bare-key accelerators (digits, Space, letters) stand down whenever a text-entry control has focus, including composite controls such as `wx.SpinCtrlDouble` whose inner edit raises no child-focus event; the accelerator table is swapped, not vetoed, because on wx 4.2 a frame accelerator fires before `EVT_CHAR_HOOK` can refuse it. Acceptance: typing "3" into a crossfade field never fires pad 3.  
**A11Y-017:** Do not disable a focused button for the length of the work it starts: Windows moves focus silently to the next control, which may then become the default button. Refuse a second press with a spoken line instead, leaving focus where it was. Acceptance: pressing a long-running check twice, then Enter, never activates a neighbouring control.

## 4.2 Application navigation

Home presents tasks rather than only technical studio names: Record audio; Record screen/video; Mix sources; Edit media; Convert media; Capture screenshot; Check webcam; Create/inspect image; Publish. Each task is addressable by the command palette and configurable accelerator. Workspaces are not isolated products. Once CW-001 ships, Home also offers **Run a live show** (Cart Wall and Running Order, section 22).

# 5. Accessible Audio Routing and Mixing Engine (AARME)

## 5.1 Source model

**MX-010:** Enumerate microphones and other Windows input endpoints with stable endpoint identifiers.  
**MX-011:** Enumerate available output endpoints and audio sessions; clearly identify non-capturable and unsupported sessions.  
**MX-012:** Support Windows endpoint loopback (aggregate system playback) and process-tree loopback where OS/build supports it.  
**MX-013:** Explicit sources: microphones; individual processes/app process trees; aggregate system audio; JAWS/NVDA/Narrator sessions where detectable; local playback; media clips; virtual devices; external capture interfaces; supported remote streams.  
**MX-014:** Distinguish source *identity* (logical saved configuration) from session PID and endpoint instance, so scenes survive process/device restarts gracefully.  
**MX-015:** Assign user aliases and stable source hotkey slots; do not silently renumber on device reconnect.  
**MX-016:** Support mono/stereo/multichannel labels, sample-rate conversion and clock drift handling.  
**MX-017:** No arbitrary product-level source cap; expose resource-based performance guidance and overload alerts.  
**MX-018:** Show source status as connected, missing, unsupported, silent, clipped, muted, armed, actively recorded, routed or suspended.

## 5.2 Independent destinations and routing

Each source has a routing matrix with independent sends to:

- **Personal monitor bus:** headphones/speakers for user, with per-bus destination.
- **Audience/live bus:** conference, stream or external transmission *only where an output device or integration is configured*. No promise of directly injecting sound into every application.
- **Main recording bus:** stereo or configured multichannel mixed capture.
- **Isolated recording stems:** pre/post-fader selectable track recording for later repair.
- **User-created buses:** AUX/music/cues/communications/broadcast submix.

**MX-020:** Matrix sends independently enable/disable; per-send gain (and optional pan) may differ.  
**MX-021:** Input/source mute, bus-send mute, monitor mute, and operating-system session mute are separate clearly named operations.  
**MX-022:** Default screen-reader routing: private monitoring ON, audience OFF, main recording OFF; do not silently turn on recording of speech in a new scene.  
**MX-023:** Always preview or confirm a scene that newly routes private audio to public output, without requiring confirmation for safe routine changes.  
**MX-024:** Allow record selection of clean mix, intended narration mix, isolated source tracks, or all; filenames and track names reflect origin and bus.  
**MX-025:** Source duplication into multiple destinations must prevent accidental doubled audio due to aggregate/system plus per-process capture overlap. Provide routing graph warnings.  
**MX-026:** Monitor loopback latency and detect probable feedback; warn or automatically block high-risk feedback routing when safely detectable.  
**MX-027:** Provide a **programme output**: the whole show (cart wall, running order, microphone, captured sources) on one chosen endpoint for another program on the same machine to pick up, distinct from any per-bank or main output. Monitor-only material (cue tones, previews, private screen-reader speech) is never in it. Routing help explains virtual-cable naming in the user's terms ("CABLE Input" is where this app *plays*; "CABLE Output" is what the other program *records*), because TG Drop Deck found users read it backwards first time. `Ctrl+Shift+W` (proposed) reads where every bus currently goes. Acceptance: with banks on one card and the monitor on another, the programme output carries pads *and* microphone, and carries no cue tone.  
**MX-028:** **Cable test:** play a short tone into the chosen output while recording the chosen far-end input, and report one of three results: nothing came back (the two ends are not one cable, or it is muted), it came back with gaps (count and share lost), or it came back clean (with its level). Opens its own streams, never the live path; refused while recording or with any audience route live, with the reason spoken. Acceptance: a deliberately undersized output buffer into a virtual cable is reported as gapped even when the driver reports no underrun.  
**MX-029:** **Mix-minus send** to a call or conferencing program: the programme less one named participant source, so a caller does not hear themselves. The excluded source is held by stable logical identity (MX-014), never list position or display name; if it cannot be resolved the routing report says, in words, that nothing is being excluded. Acceptance: renaming or reordering sources never silently changes who is excluded.

## 5.3 Per-source controls

**MX-030:** Gain adjustment via slider and numeric field with units; channel linkage, pan, trim, polarity option, source enable, mute, solo, solo-safe, arm, monitoring, routing, peak-hold reset.  
**MX-031:** Effects slots: EQ, high-pass, noise gate, compressor, limiter, de-esser/noise reduction where supported, delay/latency adjustment; bypass and undo.  
**MX-032:** User-selectable pre/post-fader bus send and pre/post-FX isolated recording.  
**MX-033:** Link sources into named groups; group volume and mute without losing individual state; relative trim preserved.  
**MX-034:** Ducking (source or bus sidechain) with attack/release, threshold, target, preview and spoken summary.  
**MX-035:** Smooth gain/mute ramps to avoid discontinuities; latency/CPU and dropouts made observable.  
**MX-036:** Accessible peak/RMS/LUFS queries on demand and configurable clipping alerts.  
**MX-037:** All changes reflected simultaneously in accessible text and visual meters, with throttled updates.  
**MX-038:** **Event ducking** in addition to MX-034's level sidechain: beds and the running order duck while a cart one-shot plays, and while the microphone is *open* (keyed by the open state, not by voice level, so the first syllable is never clipped and a cough never ducks the bed). Default depth −9 dB, configurable; a duck shared across output devices so routing beds to a second card does not silently disable it; monitoring is summed after the duck so the presenter's voice never ducks itself; cue and preview buses neither duck nor are ducked. `Ctrl+D` (proposed, cart wall scope) toggles event ducking; the new state is an action outcome (spoken and brailled). Acceptance: rendered-sample tests confirm the duck depth claimed, with no sound card present.  
**MX-039:** Every effect parameter, built-in or from a hosted plug-in (AU-029), is exposed as a row in a native list or a native numeric control, in plain words with real units, so a plug-in whose own window no screen reader can read is still fully operable. The reader voices value changes from the native control; the app does not announce them as well (it speaks only what the reader cannot).

## 5.4 Screen reader speech architecture

**MX-040:** Detect known screen-reader audio processes/sessions where technically possible, but identify that session capture alone cannot classify speech as 'demo' versus 'private mixer notification'.  
**MX-041:** A private versus broadcast speech split requires an explicit technical boundary: separate output devices/speech instances, audio session routing supported by source, or an integration agent that supplies distinct speech streams.  
**MX-042:** If such separation is unavailable, label the feature *not independently routable* and offer safe presets instead of promising impossible speech segregation.  
**MX-043:** Screen-reader speech may be intentionally captured and included for tutorial/demo mode, with clear recording-state feedback.  
**MX-044:** Prefer notifications through existing screen reader output; give users an option to silence announcements during active takes and retrieve status with a shortcut.  
**MX-045:** Automatic privacy reversion when a demonstration-scene ends or live endpoint disconnects, subject to explicit scene policies.

## 5.5 Keyboard system and memorability

**MX-050:** `Ctrl+Alt+M` opens mixer (suggested; configurable/conflict-detected).  
**MX-051:** Mixer-local keys: Up/Down source; Space mute; Left/Right fine gain; Shift+Left/Right coarse gain; S solo; H personal monitor; L audience; R mixed recording; I isolated recording; E effects; P pan; F find; Enter details; F1 help.  
**MX-052:** A configurable prefix mode performs `prefix → source slot → action` with timeouts, cancellation, announcement of selected source, and no injection into focused editor.  
**MX-053:** Press `?` or F1 for current-mode cheat sheet; provide mnemonic alternative and command search for all shortcuts.  
**MX-054:** Distinguish `Space` source mute from `Ctrl+Space` app transport play/pause; shortcuts must be context-aware and user remappable.  
**MX-055:** Persistent source slots survive reconnect; announce aliases (e.g., “2 JAWS, excluded from recording”).  
**MX-056:** Global media controls disabled until explicitly enabled; detect conflicts with screen readers, applications and Windows.  
**MX-057:** Provide optional external controller/MIDI binding at later phase, with equivalent keyboard control.  
**MX-058:** System-wide hotkeys (cart firing from another program, emergency keys) are opt-in, refuse any chord without a modifier (a bare global key steals that key from every program), are handed back with one documented key, and are checked at startup: the app briefly registers each of its own global chords and releases it, and names any chord another program already holds, because a key held elsewhere never arrives and Windows tells nobody. Acceptance: a chord pre-registered by a test process is named in the startup report; the app's own global chords are not reported against themselves. Tests that do this carry the `machine_global` marker.  
**MX-059:** Every safety-critical command (microphone on/off, MUTE AUDIENCE, stop all) has a second default chord, because a screen-reader add-on's keyboard hook can swallow a key invisibly. Acceptance: each such command has two bound chords in the keyboard reference, and the Key Describer names both.

## 5.6 Scenes and safety

**MX-060:** Save/load scenes (Podcast, Accessibility Demo, Online Presentation, Music, Private Editing; unlimited user scenes).  
**MX-061:** Scene includes logical sources, available device resolution strategies, routing matrix, effects, monitoring, level, record-arm states and privacy classification.  
**MX-062:** Preflight and preview show all affected source/destination changes; changed public routes flagged.  
**MX-063:** Missing devices handled through user-selectable fallback, no silent rerouting to live audience.  
**MX-064:** Version scenes and permit undo previous state; scene storage human-readable JSON with schema validation, secrets excluded.  
**MX-065:** Scenes may be exported and imported without exposing credentials or device-specific personal data by default.  
**MX-066:** **Spoken go-public preflight.** Any command that newly sends audio to an audience route (or starts a recording intended for publication) first produces one summary: where it is going, what is in it, whether the microphone is in it, and every problem found, classified **Stop** (will not work; the command does not proceed) or **Warn** (will work and be spoiled: a moved file that will play silence, a microphone absent from the programme, a destination nobody is listening on). Shown in a native read-only text field, spoken and brailled as one announcement, and confirmed with Enter; a preference may skip the confirmation but never the Stop checks. Cart firing never asks: nothing goes between a keypress and a sound. The checks live in `quill/core` with no `wx` and no network, so each is unit-testable. Acceptance: each Warn case is produced by a unit test, and a Stop case cannot be confirmed.

## 5.7 Capture, recording and reliability

**MX-070:** Mix and stems simultaneously, with sample-accurate or measured-corrected synchronization targets.  
**MX-071:** Record to robust, lossless intermediate files and finalize selected outputs non-destructively; crash recovery on interrupted recording.  
**MX-072:** Start/stop/pause, pre-roll, count-in, markers, automatic level test, monitoring feedback test and disk-space preflight.  
**MX-073:** Show disk free space, dropped sample/underrun count, CPU pressure, file size and elapsed time in accessible status.  
**MX-074:** Recording consent and OS privacy permissions respected.  
**MX-075:** No capturing protected streams; explain silence/unavailability without implying bypass capability.  
**MX-076:** Audio device hot plug gracefully degrades or offers an explicit fallback; keep recording recovered tracks where possible.  
**MX-077:** Implement independent monitoring gain to avoid changing recording gain while user adjusts headphone comfort.  
**MX-078:** Provide master emergency MUTE AUDIENCE hotkey separate from STOP ALL RECORDING, both documented and confirmation-free for safety.  
**MX-079:** Nothing opens a microphone except the user's explicit command: not startup, not loading a scene or cart set. Device, gain and monitoring are saved; whether the microphone was *on* is deliberately not. Acceptance: a test asserts the open state is absent from every persisted file and that loading a scene with a microphone source leaves it closed.  
**MX-080:** **Silent-input detection.** A newly opened input that delivers only exact digital zeros for 2.5 s (configurable) is reported, spoken and brailled, as probably blocked (for example by Windows microphone privacy settings), naming where to look; real microphones are never digitally silent, so exact zeros are the test, not a low level. Acceptance: a stub device returning zeros triggers the message once; a quiet room does not.  
**MX-081:** A device that fails to open is retried as **the same device** through another Windows audio API, never silently replaced by a different device. MME truncates names to 31 characters, so a truncated name counts as a match only when exactly one full device name begins with it. Acceptance: two headsets sharing their first 31 characters are never confused; a fallback that succeeds says which API it used.  
**MX-082:** The engine times its own render callback and counts blocks that arrive late beyond a set factor of the buffer period, surfacing the count in MX-073 status, rather than trusting the driver's underrun report. TG Drop Deck measured a fixed 512-frame output into a virtual cable losing up to 7.4 % of the audio while PortAudio reported no underrun. Acceptance: an injected stall is counted.  
**MX-083:** **Live track log.** While recording, every cart one-shot, bed and running-order item that reaches the recorded bus is appended, with its start time, to a CUE sheet written beside the recording with the same base name (`Show 004.wav` → `Show 004.cue`, `TITLE`, `PERFORMER`, `INDEX 01 mm:ss:ff` with **75 frames per second**, not hundredths). Times come from the recording's own written sample count, never the wall clock, so a stall cannot drift the log; each entry is flushed as it is written so a crash leaves a log complete to the last item. Reuse QUILL's existing CUE writer (`quill/core/speech/chapter_io.py`) rather than adding a second. Announced: nothing per entry; the log's path is part of the recording-finished outcome. Acceptance: a forced kill mid-take leaves a valid CUE for everything before the kill; an entry at 0.5 s is written as frame 38 (rounded from 37.5).

# 6. Audio Studio editor, DAW, and podcast production

## 6.1 Project format

**AU-010:** Non-destructive projects reference media assets and edited regions; no overwriting originals.  
**AU-011:** Multi-track, multi-clip timeline; track naming, mute/solo/arm/monitor/pan/volume, sends, effects, groups and bus assignments.  
**AU-012:** Undo/redo and revision snapshots; autosave and recovery.  
**AU-013:** Project bundle export with media consolidation, license/attribution metadata and portability warnings.  
**AU-014:** Shared mixer routing state separated from timeline mix automation, avoiding unexpected live changes when scrubbing project playback.

## 6.2 Accessible editing workflows

**AU-020:** Sample/frame/timecode/beat navigation, typed selection endpoints and named regions.  
**AU-021:** Cut, copy, paste, split, trim, slip, ripple, move, duplicate, reverse, silence, gain, fade and crossfade—keyboard operated.  
**AU-022:** Audition changes before committing, including skip-selection preview and A/B comparison.  
**AU-023:** Accessible list of tracks, clips, markers, regions and effects; navigation independent of waveform.  
**AU-024:** Selection and transport state always queryable; optional speech suppression while playback runs.  
**AU-025:** Markers and chapters with labels; playback loop and punch-in/out.  
**AU-026:** Mixing automation (volume/pan/effect parameters) with textual editable envelope points.  
**AU-027:** Overdub with latency compensation and hardware monitoring warnings.  
**AU-028:** Track freezing/render in place with reversible source and processing chain.  
**AU-029:** Optional VST3 plug-in host considered only after defining accessibility safety contract, sandboxing and crash isolation; inaccessible third-party GUI must never block core editing.

## 6.3 Podcast and music deliverables

**AU-030:** Single-track podcast: trim, silence/filler review, chapter insertion, loudness processing, metadata and export.  
**AU-031:** Multitrack music: instruments/voice/backing tracks, synchronized stems, groups, reverb/delay sends, automation, mastering chain.  
**AU-032:** Source split recording and assembled live mix may be imported directly into new editing project.  
**AU-033:** Audio file review supports silence detection, clip detection, low-level detection and channel imbalance report.  
**AU-034:** Loudness presets may include podcast/audiobook/video platform contexts with user override; avoid claiming universal platform requirements.  
**AU-035:** Opening a recording that has a same-name CUE sheet beside it (MX-083, or one made by another program such as TG Drop Deck) offers its entries as proposed chapters in the Chapter Workbench, using the existing Keep mine / Replace choice; the CUE can also be published with the audio for services that read tracklists. Acceptance: record a show with three running-order items, open the recording, and the Workbench proposes three chapters at the logged times.

# 7. Video Studio and camera confidence

**VD-010:** Capture webcam, desktop, region, window and simultaneous layouts where OS/encoder allow.  
**VD-011:** Spoken preflight checks: face count, horizontal/vertical framing, distance estimate, partial face, lighting, blurred image where model can infer it; uncertainty disclosed.  
**VD-012:** On-device positioning preferred; image frames never uploaded without affirmative permission.  
**VD-013:** Test record and playback before final take.  
**VD-014:** Separate mic, app and system audio tracks from video; use mixer scenes.  
**VD-015:** Trim, split, join, crop and assemble simple video projects with keyboard-entered times.  
**VD-016:** Subtitle/caption editor with segment navigation, timestamps, reading speed estimates and export SRT/VTT; human review required.  
**VD-017:** Video frame explorer permits jump to timecode, describe/zoom, detect text via OCR, and compare selected frames.  
**VD-018:** Audio description drafting and optional narrating track; do not promise perfect visual verification by sampled frames.  
**VD-019:** Screen capture redaction controls for private desktop notifications and selected regions, with preview before broadcast.  
**VD-020:** **Picture health.** While recording video, detect a picture that has gone black or frozen, from frames already in hand (cheap reductions on a subsample), and announce the *change* once a fault has lasted a patience period, then announce recovery; never repeat a standing state. Applies only to sources expected to move, so a still title card is never reported frozen. Acceptance: unplugging a camera mid-take produces one announcement after the patience period and one on recovery. (TG Drop Deck `health.py`; its VD-011-style framing check, `Ctrl+Shift+F` there, independently validates VD-011.)

# 8. Capture Studio and ZoomIt integration

**CP-010:** Technical spike must establish independent compile of permitted ZoomIt modules, third-party dependency inventory and packaging boundaries.  
**CP-011:** Keep ZoomIt-based zoom, annotation, magnification, timers, mirroring and screen recording behind adapter interfaces, not as a replacement shell.  
**CP-012:** Capture full monitor, chosen window, UI Automation control or numerically selected rectangle; keyboard move/resize by defined increments.  
**CP-013:** Save multiple named regions, combine shots, annotate with keyboard-created rectangles, arrows, callouts, highlights and text labels.  
**CP-014:** OCR locally where feasible; offer recognized text in normal read-only selectable editor and copy/export.  
**CP-015:** Scrolling/panoramic capture with preview and explicit warning for incomplete or stitched captures.  
**CP-016:** Accessibility evidence bundle stores image, textual description, window/control details where available, reproduction steps and annotation metadata.  
**CP-017:** Pointer-only actions in upstream code require keyboard-equivalent accessible abstraction before release.  
**CP-018:** Custom drawing surface exposes an accessible object list, focus, selection, order and precise geometry values.

# 9. AI, visual inspection and verification

**AI-010:** Conversational image design: describe requested image, ask clarifying questions through normal chat, preview generated image with a visual model, revise, save metadata and accessible text description.  
**AI-011:** Provider-agnostic adapters: local models where practical, BYOK cloud providers, and optional shared QUILL AI Hub/gateway with permission, quotas and safeguards.  
**AI-012:** Clearly indicate provider, internet requirement, cost basis, estimated charge if available and data sent prior to action.  
**AI-013:** Never auto-upload screen captures, video, recordings, private speech or files.  
**AI-014:** OCR, image description, selected-frame analysis, rough framing checks, transcription/diarization, captions, audio level inspection and optional noise reduction.  
**AI-015:** Every AI-assisted edit is reviewable, reversible and marked as suggested until the user approves.  
**AI-016:** Record model/provider/version and confidence/limitations in optional project provenance metadata.  
**AI-017:** AI-generated alt text includes intended usage context, not merely raw object detection.  
**AI-018:** No automatic publication of model-generated captions or accessibility reports without human review.

# 10. Conversion, publishing and QUILL integration

**CV-010:** Batch convert audio/video; queue, concurrency limits, per-file progress, cancel, resume where technically possible and error logs.  
**CV-011:** Lossless copy/stream-copy when suitable; explicit warnings for lossy transcoding and quality degradation.  
**CV-012:** Presets for speech podcast, music archival, WAV production, compressed sharing, video social publishing and captions.  
**CV-013:** Edit tags, title, artist, album, chapters, artwork, date, track and attribution metadata.  
**CV-014:** Integrate with existing QUILL Converter via a common engine instead of duplicating conversion features.  
**PB-010:** Send completed audio to QUILL Cast as episode asset with chapters, transcript, artwork, title and description.  
**PB-011:** Open asset from QUILL Editor/QUILL Social and return rendered or referenced output to the originating task.  
**PB-012:** QUILL Radio may reuse common playback, device handling and audio services but should not inherit recording permissions automatically.  
**PB-013:** Auphonic is optional through user-provided account/credits and official API; provide local free fallbacks where feasible.  
**PB-014:** Support SRT, WebVTT, plain transcripts, Markdown show notes, and selected structured JSON formats.

# 11. Technical architecture

## 11.1 Preferred approach

Retain QUILL's existing native-accessibility Windows conventions; do not force a replacement web UI. Preferred shell: wxPython/native controls as existing project conventions support. For low-latency capture/mixing, create a separate compiled Windows engine (C++/Rust or similarly appropriate runtime) with small, versioned API boundary; Python UI must not sit inside real-time audio callbacks.

**Subsystems:**

1. **QUILL Shell/UI:** task launcher, mixer view, editors, accessible events, F1, search, preferences.
2. **Audio engine service:** WASAPI endpoints and loopback, audio graph, resampling, routing buses, capture and recovery.
3. **Project/timeline engine:** non-destructive EDL, automation, clip state, undo/history, media indexes.
4. **Media workers:** FFmpeg/ffprobe job processes and optional trusted plug-in processors.
5. **Capture adapter:** licensed ZoomIt/PowerToys-derived components, screenshot/UIA selection and OCR pipeline.
6. **Camera/video service:** video capture, preview, encode, local framing analyzer, caption timeline.
7. **AI service layer:** QUILL Hub provider plugins, policy/consent, cache, local/cloud inference.
8. **Inter-app integration:** QUILL Editor, Converter, Radio, Cast and optional podcast publishing through versioned contracts.
9. **Accessibility service:** UIA controls, announcement queue/throttling, speech visibility policies, keyboard manager.

## 11.2 Internal event/data contracts (illustrative)

`Source`: UUID, user alias, kind, endpoint-id or process identity, channel metadata, capabilities, status.  
`Route`: source-id, bus-id, enabled, send gain/pan, pre/post selection, privacy classification.  
`Bus`: UUID, kind (`monitor`, `audience`, `main-record`, `stem`, `aux`), output endpoint, mix format, meter.  
`Scene`: schema version, logical source selectors, routes, FX, safety flags, restore policy.  
`RecordSession`: UUID, start wall-clock/monotonic clock, media paths, format, stems, recovery state, event log.  
`TimelineProject`: version, clip/track graph, markers, effects and asset manifests, history pointer.

APIs include `enumerate_sources`, `get_source`, `set_source_gain`, `set_source_mute`, `set_route`, `get_routing_matrix`, `apply_scene_preview`, `commit_scene`, `arm_track`, `start_recording`, `stop_recording`, `get_meter_snapshot`, `get_transport`, `subscribe_state`, and `emergency_mute_audience`. Enforce access control and avoid unauthenticated network control.

## 11.3 Engine considerations

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

# 12. Licensing, security, privacy and distribution

**LIC-001:** QUILL Audio Studio application license must be chosen or confirmed against existing repository; do not assume its current license.  
**LIC-002:** ZoomIt source in the Microsoft PowerToys repo carries MIT notice; preserve its copyright/license and review each included component and dependency.  
**LIC-003:** Do not redistribute proprietary Sysinternals binaries merely because MIT source exists; distribute appropriately licensed compiled builds.  
**LIC-004:** FFmpeg configurations have LGPL/GPL consequences; maintain a declared build configuration and meet all applicable conditions.  
**LIC-005:** Confirm licenses for ASIO, codecs, VST hosting, AI model weights, MediaPipe/model assets, fonts and redistributables independently.  
**LIC-006:** Distinct QUILL branding; no suggestion of Microsoft or MediAccess endorsement.  
**LIC-007:** TG Drop Deck is MIT licensed (Copyright © 2026 Tony Gebhard). Code may be copied or adapted into QUILL, which is MIT too, provided the copyright and permission notice travel with it: in the adapted file's header and in the third-party notices. Prefer porting its small pure modules (CUE log, M3U fields, routing and preflight rules) over its UI, whose architecture differs. No TG Studios or TG Drop Deck branding, and no implied endorsement.  
**LIC-008:** Do not inherit TG Drop Deck's dependency choices without separate review: its DSP and VST3 host is Spotify `pedalboard` (GPL-3.0), which would put GPL obligations on any QUILL bundle that ships it; its PyAV wheel carries FFmpeg (LIC-004 applies); its bundled demo sounds are AI-generated (ElevenLabs) with their terms stated in prose only; its face model is YuNet from OpenCV Zoo (MIT); its Mac build links LAME (LGPL).  
**LIC-009:** VB-CABLE (VB-Audio, https://vb-audio.com/Cable/) is **donationware**, not freeware or open source: free for an individual to use with every function, a paid licence (volume prices from about 3.61 EUR a seat) when used in a professional context, and redistributable with a free program only if the user can see it is a VB-Audio product and is in a position to pay -- the distributor must credit www.vb-cable.com and say it is donationware (VB-Audio licensing page, read 2026-10-26; the A+B and C+D cables may not be bundled at all). It installs a Windows audio driver with administrator rights and a reboot. So Studio **does not bundle or install it**: MX-027 to MX-029 work with *any* virtual audio cable the user has installed, VB-CABLE named as one example with its donationware terms stated, and the cable test (MX-028) is what proves a chosen pair works. Where a cable is only wanted to *capture* another program, prefer WASAPI process loopback, which QUILL already has (`quill/platform/windows/process_loopback.py`) and needs no driver.  
**SEC-001:** Local media is private by default; explicit per-task permissions for upload or cloud processing.  
**SEC-002:** Secret keys stored through platform secure storage or approved QUILL vault, not in project JSON, logs, or source repo.  
**SEC-003:** Sandbox untrusted media parsing and plug-ins where viable; pinned dependencies, signed installers and upgrade integrity.  
**SEC-004:** Accessible privacy dashboard: screen capture status, current recording sources, audience routes, cloud services used.  
**SEC-005:** Diagnostics redact paths/usernames/audio content unless explicitly included in support bundle.  
**SEC-006:** No telemetry by default without explicit consent; respect existing QUILL privacy commitments.  
**SEC-007:** Shared configuration files (scenes, cart sets, running orders, imported TG Drop Deck boards) are untrusted input: they never carry network destinations, credentials, or anything acted on at load, and such fields are dropped on import with the drop reported. TG Drop Deck found that a free-text "custom server" field in a shared board file could send a live microphone wherever the file's author chose on one keypress. Acceptance: importing a board containing a stream address imports the sounds and reports the address as ignored.

# 13. Packaging, update and migration

**REL-001:** Preserve existing QUILL Audio Studio user settings and data; implement versioned migration tests.  
**REL-002:** Portable mode stores application-local config and cache with controlled user-selected media directories; warn for OS-level drivers or services needing installation.  
**REL-003:** Installer supports per-user setup where feasible, clean uninstall and separate cache/project retention choices.  
**REL-004:** Offline installers/bundled codec components subject to licensing and size policy; split optional downloadable models.  
**REL-005:** Publish checksums, accessible release notes, dependency notices, known limitations and rollback guidance.  
**REL-006:** No settings reset silently and no unexpected new global hotkeys after upgrade.

# 14. Nonfunctional targets and quality budgets

These are **initial engineering targets pending validation**, not performance guarantees:

- Normal mixer controls respond within 100 ms perceptually; screen reader commands receive status without blocking audio thread.
- Monitoring end-to-end latency reported; selectable safe modes for ordinary USB/headphone devices and low-latency professional rigs.
- No dropped audio for an agreed reference hardware/capture scenario (e.g., 4 sources, 2 buses, 48 kHz stereo, long-duration session); measure rather than assume.
- Project autosave recoverability after forced UI termination, with ability to salvage partially recorded stem containers.
- At least 24-hour stability test for background mixer operation under realistic audio loads and app/device churn.
- Bounded memory/cpu use; 8 GB RAM user profiles tested for core capture/edit/conversion without loading large AI models by default.
- Every failure state accessible, actionable and logged locally with privacy safeguards.
- Cart Wall keypress to first audible sample: target 30 ms or less on a WASAPI shared-mode endpoint on reference hardware, measured from key event to first non-zero output sample; short sounds decoded into memory at assignment, never on the trigger path.

# 15. Testing and accessibility acceptance

## 15.1 Required test matrix

- Windows 11 x64, current supported builds; Windows 10 tested where promised.
- JAWS, NVDA, Narrator; keyboard-only; Windows Magnifier, contrast themes, 200–400% text scaling.
- One monitor and multi-monitor; speakers/headphones; one or multiple microphones; Bluetooth/USB hot-plug; common virtual device where available.
- Desktop apps with audio, browsers, Teams/Zoom-like meeting apps and screen reader sessions; expected isolation limitations documented.
- Single and multiple process trees, source restarts and process ID changes.
- Interruption tests: audio device removed, app closed, disk full, power loss/forced crash, missing codec, cloud service unavailable.

## 15.2 Gate scenarios

**GATE-01 — Private screen reader:** User hears JAWS via headphones while mic and chosen app are recorded; published mix contains no unintended screen-reader speech. Passing requires compatible device/source configuration and verification recording.  
**GATE-02 — Intended demo speech:** User chooses to include screen-reader output; exported demo contains it; private control speech separated only if distinct routes are available.  
**GATE-03 — No mouse mixer:** JAWS, NVDA and Narrator users discover a source, set exact gain, mute, solo, route to each destination and query status without mouse.  
**GATE-04 — Emergency audience mute:** Immediate mute works during running recording and is accessible via memorable key binding.  
**GATE-05 — Crash survival:** Kill UI/process during 20-minute multitrack take; recover available stems and identify missing/corrupt segments, never claiming unavailable samples were recovered.  
**GATE-06 — Accessible edit:** Create two tracks, insert clip, mark start/end, preview removal, apply crossfade, undo and export—all keyboard-only.  
**GATE-07 — Webcam confidence:** Position with on-device spoken guidance, test record, verify generated report and explicit uncertainty.  
**GATE-08 — Screenshot:** Capture a UIA-selected control via keyboard, inspect OCR, add numbered annotation, export both image and textual evidence.  
**GATE-09 — Privacy:** Cloud workflow never transmits screenshot/audio until explicit provider/price/data-sent authorization.  
**GATE-10 — Upgrade:** Existing QUILL Audio Studio files, projects, profiles and common shortcuts survive migration or receive clear mapping/rollback.  
**GATE-11 — Cart Wall on air:** With JAWS, NVDA and Narrator, keyboard only: build a bank of five sounds and one bed, fire overlapping one-shots, toggle the bed, stop the last sound, stop all; no pad is relabelled under focus during playback, a missing file is spoken and brailled, and keypress-to-sound meets the section 14 target.  
**GATE-12 — Programme proof:** Cable test (MX-028) reports clean into a virtual cable; a recording of the far end contains cart, running order and microphone and contains no cue tone, preview or private screen-reader speech.  
**GATE-13 — Show log:** A recorded show with running-order items and cart drops yields a same-name CUE (MX-083) that survives a forced kill and opens as proposed chapters (AU-035).

*(GATE numbers here are this PRD's scenario numbers and are unrelated to repository gates that share a number, such as the module size budget or over-announce gate.)*

## 15.3 Screen-reader speech behavior checklist

For each operation: focus placement; name/role/state; shortcut; change announcement; silent variant; error feedback; braille display; audible interference risk; public-output leakage risk; recovery path. Automated UIA assertions supplemented by human usability tests.

# 16. Delivery roadmap and dependencies

**Phase 0 — Audit and foundations (research spike):** Current QUILL Audio Studio source and persistence schema; license inventory; ZoomIt build; screen reader/Windows process loopback feasibility; source enumeration prototype; capture latency benchmarks; technical decision records. Exit: accepted interface contracts and tested proof-of-concept.

**Phase 1 — Accessible mixer alpha (P0):** Discover sources; independent monitor/main/stem routes; gain/mute/solo; speech privacy defaults; keyboard command model; scenes, meters, preflight and clean recording. Exit: GATE-01 through GATE-05 with documented platform restrictions.

**Phase 2 — Editing and conversion:** Nondestructive single/multitrack timeline, edit preview, captions/transcription basics, converter shared with QUILL Converter, QUILL Cast handoff. Exit: GATE-06; recoverable project format and no loss of existing functionality.

**Phase 3 — Capture, camera, and video:** ZoomIt-based adapter; keyboard capture, OCR, annotation, camera framing/test; screen recording; simple video edits. Exit: GATE-07 and GATE-08.

**Phase 4 — AI and verification:** Conversational image generation, descriptions, visual QA, speech processing/diarization, optional provider integrations, advanced accessibility evidence workflows. Exit: GATE-09 and explicit cloud cost controls.

**Phase 5 — Production hardening:** Rich audio automation, third-party effect hosting, user presets, advanced publish/export, portability, localization, third-party security review, broader device support. Exit: public 1.0 criterion suite and release review.

**Milestone estimates:** Avoid scheduling until Phase 0 repository audit establishes current functionality, team capacity, architecture constraints and test hardware. Break features into work packages with measurable acceptance before committing dates.

# 17. Workstream breakdown for engineering agents

1. **Discovery:** inventory existing repo/services, capabilities and regression test baseline; generate ADRs.
2. **Audio core:** endpoint discovery and process-loopback proof-of-concept; output a reference WAV test.
3. **Graph and buses:** implement explicit source-to-bus routes, safety checks and reusable source identifiers.
4. **Accessible mixer UI:** native source list, command map, numeric control editor, status announcements.
5. **Scene manager:** JSON schema, preflight diff, safe apply, reversion and migration.
6. **Recorder:** split stems, crash recovery, synchronization and verification reports.
7. **Timeline:** non-destructive clip model, accessible list navigation, audition and undo.
8. **Media workers:** conversion/export manifests, queue and error handling.
9. **Capture adapter:** ZoomIt source proof-of-build, UIA selection layer, OCR and annotation objects.
10. **Camera/video:** capture graph, model-driven feedback and transcript/caption timeline.
11. **AI:** configurable providers, privacy gate, costs, local model memory budget and approval-based operations.
12. **Shared QUILL APIs:** artifact handoff and versioned capabilities for Cast, Radio, Converter, Editor.
13. **Accessibility QA:** scripted JAWS/NVDA/Narrator and human test plans for each release gate.
14. **Release:** license audit, reproducible builds, installer, portable package, update/rollback and accessible docs.

All agent tasks must include definition of done, change-risk assessment, unit/integration tests, manual assistive-technology checkpoints, and a rollback plan. Prefer small vertical slices over simultaneous rewrites.

# 18. Risks, tradeoffs and decisions to validate

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
| Cart Wall keys collide with editor, screen-reader or international-layout keys | A pad that never fires, or fires while typing | Workspace-scoped keys (A11Y-016), keymap gates, no `Ctrl+Alt`+letter defaults (AltGr), startup held-key check (MX-058) |
| Adopting a borrowed project's dependencies with its code | GPL obligations on a free MIT bundle | LIC-007/LIC-008 review before any port; port pure modules, not dependency stacks |

# 19. Open validation questions (do not block Phase 0)

1. What is the current QUILL Audio Studio language/module layout, build system and existing project format? Inventory directly from repository.
2. Which specific recording/editing controls already exist, and which are planned only? Build capability inventory, not assumptions.
3. Does QUILL currently use libmpv/FFmpeg for Audio Studio itself, or only other QUILL applications? Discover before refactoring.
4. Which audio endpoint/screen-reader routing arrangements will be supported without any installed virtual device?
5. Which Windows minimum build enables needed process loopback and frame capture APIs?
6. Which existing QUILL keyboard conventions must retain priority over proposed mixer shortcuts?
7. Which supported AI image providers/local models have legal redistribution paths and acceptable resource requirements?
8. Should downstream applications use IPC, Python package library calls, or both for shared audio engine control?
9. Which collaboration/realtime guest recording approaches can provide legitimately separate tracks?
10. Should the Cart Wall offer an optional "TG Drop Deck layout" key profile (its frozen number-row map) for users migrating with years of muscle memory, given that its `Ctrl+Alt` layers can be lost to AltGr on some keyboard layouts?
11. Is the Cart Wall a Studio workspace only, or also reachable from QUILL and Quill Radio through the shared package, as the family rule that QUILL Lite may never be ahead of QUILL would suggest for any shared capability?

# 20. Initial definition of done

A phase is complete only when: a user can perform the advertised task keyboard-only with JAWS, NVDA, and Narrator; the project has automated regression tests and observed human usability results; behavior is accurate under scene/device/app changes; recording/export data is recoverable and verified; privacy and license reviews pass; documentation identifies supported and unsupported capture modes; and no existing QUILL Audio Studio workflows regress.

---

# 21. References

Every link below was chosen because a requirement in this document leans on it. Links to code are for study and, where the licence allows, for adaptation under LIC-001 to LIC-009; nothing is copied without that review. Paths without a web address are in the QUILL repository.

## 21.1 Microsoft PowerToys and Sysinternals

The Capture Studio (section 8) is modelled on PowerToys utilities that are MIT licensed, and on ZoomIt, which ships both in PowerToys and as a Sysinternals tool.

- [PowerToys repository](https://github.com/microsoft/PowerToys) and its [MIT licence](https://github.com/microsoft/PowerToys/blob/main/LICENSE)
- [PowerToys documentation home](https://learn.microsoft.com/windows/powertoys/)
- [ZoomIt in PowerToys: documentation](https://learn.microsoft.com/windows/powertoys/zoomit), [source](https://github.com/microsoft/PowerToys/tree/main/src/modules/ZoomIt), [main implementation and MIT notice](https://github.com/microsoft/PowerToys/blob/main/src/modules/ZoomIt/ZoomIt/Zoomit.cpp) and [developer architecture notes](https://microsoft.github.io/PowerToys/modules/zoomit/) (CP-010, CP-011)
- [ZoomIt, Sysinternals edition](https://learn.microsoft.com/sysinternals/downloads/zoomit): the standalone binary; proprietary licence, so it is studied, never redistributed (LIC-003)
- [Text Extractor](https://learn.microsoft.com/windows/powertoys/text-extractor): on-screen OCR with Windows' own engine; the model for CP-014
- [Crop And Lock](https://learn.microsoft.com/windows/powertoys/crop-and-lock): cropping a window to a region; informs CP-012 and VD-015
- [Screen Ruler](https://learn.microsoft.com/windows/powertoys/screen-ruler): measuring on screen; informs CP-018's spoken geometry
- [Mouse utilities](https://learn.microsoft.com/windows/powertoys/mouse-utilities): pointer highlighting for recorded demonstrations (CP-017 gives each pointer-only action a keyboard equivalent)

## 21.2 Windows audio, capture and recognition

- [Core Audio and WASAPI](https://learn.microsoft.com/windows/win32/coreaudio/wasapi): the AARME engine's foundation (section 5, section 11)
- [Loopback recording](https://learn.microsoft.com/windows/win32/coreaudio/loopback-recording)
- [Application loopback capture sample](https://learn.microsoft.com/en-us/samples/microsoft/windows-classic-samples/applicationloopbackaudio-sample/) and its [source](https://github.com/microsoft/Windows-classic-samples/tree/main/Samples/ApplicationLoopback): per-process capture (MX-013), already in QUILL as `quill/platform/windows/process_loopback.py`
- [Media Foundation](https://learn.microsoft.com/windows/win32/medfound/microsoft-media-foundation-sdk): system codecs and camera capture (section 7)
- [Screen capture with Windows.Graphics.Capture](https://learn.microsoft.com/windows/uwp/audio-video-camera/screen-capture): window and monitor capture without hooks (CP-012); QUILL's current capture helper is `quill/platform/windows/screen_capture.py`
- [Windows.Media.Ocr](https://learn.microsoft.com/uwp/api/windows.media.ocr): local OCR with no download (CP-014, AI-014)
- [UI Automation](https://learn.microsoft.com/windows/win32/winauto/entry-uiauto-win32): capturing a control by its automation element (CP-012) and every custom surface's accessibility (CP-018, section 4)

## 21.3 Accessibility standards and screen readers

- [WCAG 2.2](https://www.w3.org/TR/WCAG22/): the success criteria section 4 maps to
- [EN 301 549 v3.2.1](https://www.etsi.org/deliver/etsi_en/301500_301599/301549/03.02.01_60/en_301549v030201p.pdf): European ICT accessibility requirements, including non-web software (chapter 11)
- [Section 508](https://www.section508.gov/): United States federal accessibility requirements
- [NVDA developer guide](https://www.nvaccess.org/files/nvda/documentation/developerGuide.html): how NVDA reads Windows controls, which decides what Studio must expose rather than script
- [Complete guide to Narrator](https://support.microsoft.com/windows/complete-guide-to-narrator-e4397a0d-ef4f-b386-d8ae-c172f109bdb1)
- `docs/design/table-uia-spike-2026-10.md`: QUILL's measured notes on what NVDA, JAWS and Narrator read from a Rich Edit control; the same limits apply to any text surface Studio hosts

## 21.4 Audio, video and caption formats and loudness

- [FFmpeg](https://ffmpeg.org/) and its [licensing](https://ffmpeg.org/legal.html) (LIC-004)
- [Opus](https://opus-codec.org/), [FLAC](https://xiph.org/flac/) and [LAME (MP3)](https://lame.sourceforge.io/): the export formats in section 6
- [EBU R 128](https://tech.ebu.ch/publications/r128) and [ITU-R BS.1770](https://www.itu.int/rec/R-REC-BS.1770): loudness measurement and targets for the publishing presets
- [WebVTT](https://www.w3.org/TR/webvtt1/): caption output (AI-014, section 7)
- [Podcasting 2.0 namespace](https://github.com/Podcastindex-org/podcast-namespace): chapters, transcripts and other tags PB-010 hands to QUILL Cast
- [PortAudio](https://www.portaudio.com/): the audio layer TG Drop Deck measured against (section 11.3)
- [Icecast](https://icecast.org/): the open streaming server family referred to in section 22 (direct streaming is not adopted; see 22.5)

## 21.5 Virtual audio cables

- [VB-CABLE](https://vb-audio.com/Cable/) and [VB-Audio's licensing and distribution terms](https://vb-audio.com/Services/licensing.htm): donationware, user-installed, never bundled (LIC-009, MX-027 to MX-029)

## 21.6 Speech, recognition and AI

- [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx): the torch-free ONNX runtime QUILL's offline speech and dictation use, and the route for local transcription in Studio (AI-014)
- `quill/core/ai/` and the QUILL AI guide: the provider adapters, consent and cost disclosure AI-011 to AI-013 build on

## 21.7 Independent products studied

- [MediAccess article (independent product reference)](https://hartgenconsultancy.com/introducing-mediaccess-part-1-opening-the-door-to-accessible-media/): publicly described workflows that inspired the scope, not code (LIC-006)
- [TG Drop Deck source (MIT)](https://github.com/tonygeb23/tg-drop-deck), its [licence](https://github.com/tonygeb23/tg-drop-deck/blob/main/LICENSE) and [user guide](https://tgstudios.app/drop-deck-guide/): section 22
- [Spotify pedalboard (GPL-3.0; see LIC-008)](https://github.com/spotify/pedalboard): considered and not adopted

## 21.8 The QUILL family: code and documents this PRD builds on

QUILL Studio is one app of the QUILL family and reuses its shared package rather than copying it. Each app below has an entry point in `quill/apps/`, a packaging shell in `standalone/<app>/`, and a user guide, changelog and PRD in `standalone/<app>/docs/`.

- **QUILL Studio** today: `quill/apps/studio.py`, `quill/apps/studio_*.py`, `quill/ui/audio_studio/`, `standalone/studio/docs/` (user guide, changelog) and the earlier PRD in `docs/audio-studio/prd.md`, which this document expands
- **QUILL**, the editor: `quill/ui/main_frame*.py`, `docs/user guide/userguide.md`, `docs/Product Requirement Documents and Specifications/QUILL-PRD.md`; its AI, OCR and document-intake features are the ones AI-014 and CP-014 should reuse
- **QUILL Cast** (`standalone/cast/`): podcast publishing and playback; the receiving end of PB-010
- **Quill Radio** (`standalone/radio/`): station playback, recording and output-device routing, the closest existing code to AARME's device handling
- **QUILL Transcribe** (`standalone/transcribe/`): transcription and diarization (AI-014)
- **Quill Media Player** (`standalone/player/`): book and media playback, chapters, and the shared slider keys
- **Quill Converter** (`standalone/converter/`): batch media conversion (section 10)
- **QUILL Lite**, **Inkwell**, **Weather** and **Beacon** (`standalone/quilllite/`, `standalone/inkwell/`, `standalone/weather/`, `standalone/beacon/`): family conventions for menus, help and announcements that Studio follows
- Shared rules: `CLAUDE.md` (the family's gates), `quill/core/family_rules.py` (the eleven family rules), `docs/keyboard-reference.md` and `docs/f1-help-reference.md` (generated references Studio's keys and help join)
- Legal: `LICENSE`, `NOTICE`, `docs/legal/THIRD_PARTY_NOTICES.md`, `docs/legal/legal-notices.md` and `docs/legal/trademark-notices.md`

**Important note:** Product behavior, code integration feasibility and final license compliance require an audit of the current QUILL repository and each dependency. This PRD is a specification of intended functionality, not proof all OS/audio sources can be routed independently on every Windows configuration.

---

# 22. Lessons from TG Drop Deck

## 22.1 What it is

[TG Drop Deck](https://github.com/tonygeb23/tg-drop-deck) (Tony Gebhard, TG Studios; MIT; Windows 3.9.0 of 16 October 2026 at the time of reading, with a separate native Mac copy) is an accessible soundboard and playout desk for podcasts, radio and live shows, written in Python and wxPython, screen-reader first and tested with NVDA running. Eighty sounds sit on the number row in four banks of twenty; one-shots overlap, beds loop and toggle; a two-deck running order crossfades; a processed microphone ducks the music; the show can be recorded, sent to another program through a virtual cable, or streamed to Icecast, SHOUTcast or RTMP services. Its working notes are unusually explicit about *measured* accessibility and audio behaviour, many prompted by blind broadcasters' reports, and that evidence is the main thing worth carrying over.

QUILL Audio Studio today narrates, chapters, converts, captions and publishes; it has no live mixer, recorder, cart wall or running order. Sections 5 and 6 plan the mixer and editor. This section adds the **live-show playout** layer TG Drop Deck demonstrates, built on AARME (section 5) rather than beside it. Requirements that belong to an existing area were placed there instead: A11Y-014 to A11Y-017, MX-027 to MX-029, MX-038, MX-039, MX-058, MX-059, MX-066, MX-079 to MX-083, AU-035, VD-020, LIC-007, LIC-008, SEC-007, the section 14 latency target, and GATE-11 to GATE-13.

**Rules every requirement below inherits:** every command has a key or a written reason and appears in a **Live Show** menu and the command palette; chords listed are *proposed* and are allocated in `keymap.APP_KEYMAPS` under the family rules and the menu-accelerator and access-key gates; the app speaks only what the screen reader does not already say, and everything it speaks goes through the announcement service so it is also brailled and written to the status bar; confirmations use the shared `action_feedback` channel (sound, speech, both or silent) while failures and counts are always spoken; every control has authored inline F1 help; nothing here makes a network call.

## 22.2 Cart Wall

**CW-010 — Banks of prepared sounds.**
- *Need:* a presenter who cannot see a grid needs dozens of stings, drops and beds instantly, without leaving the keyboard's home position.
- *Behaviour:* a Cart Wall workspace (a panel, not a dialog, so Escape never closes it) of banks, default four banks of twenty slots, each a native button in a native tab page. A bank has a **kind** (one-shot, bed, or free) that decides behaviour; its **name** is the user's and purely cosmetic, so renaming a bank never changes what it does.
- *Keys:* in the Cart Wall, `1` to `0` fire slots 1 to 10 of the current bank and `Shift+1` to `Shift+0` slots 11 to 20; `Ctrl+Tab` / `Ctrl+Shift+Tab` (and the native `Ctrl+PageDown` / `Ctrl+PageUp`) change bank; firing other banks without switching uses modifier layers set per bank in Preferences, with no `Ctrl+Alt` layer by default (AltGr); all bare keys stand down in text fields (A11Y-016).
- *Announced:* nothing when a sound fires (it is heard, and the focused button already names it); a short help hint once per bank per session, not on every visit.
- *Acceptance:* GATE-11; menu, access-key and documentation-chord gates pass.

**CW-011 — Fire, overlap and toggle.**
- *Need:* drops must never cut each other off; a bed must start and stop on one key.
- *Behaviour:* one-shots overlap freely; a bed-bank slot loops by default and the same key stops it, with only one bed playing at a time; bed fade-in and fade-out are settings in which zero means "exactly as recorded"; separate faders for one-shots, beds and the running order, each routable to its own AARME bus; auditioning a file while assigning it plays on a preview bus that is neither ducked nor ducking.
- *Keys:* `Space` or `Enter` on a slot fires it; fader keys proposed as `F3`/`F4` (one-shots), `F5`/`F6` (beds), `F7`/`F8` (running order), subject to the Studio keymap.
- *Announced:* fader moves are action outcomes (level in dB) because the fader is not focused; bed start and stop are not announced.
- *Acceptance:* two overlapping one-shots both play to the end; a bed toggles; a zero fade starts on the first sample.

**CW-012 — Stop last, stop all.**
- *Need:* a wrong sound must be stoppable alone; everything must be stoppable at once without being stopped by accident.
- *Behaviour:* **Stop last** stops the most recently started sound, and pressed again the one before it. **Stop all** stops every cart and running-order voice and requires a configurable number of presses (default 2, range 1 to 4) within a short window. Neither is MUTE AUDIENCE (MX-078), which stays single-press and confirmation-free.
- *Keys:* Stop last proposed as `Backspace` in the Cart Wall (`Ctrl+Space` is reserved for transport by MX-054); Stop all `Escape` the configured number of times, plus a second chord per MX-059.
- *Announced:* outcome with a count ("Stopped 3 sounds"); "nothing playing" when there was nothing.
- *Acceptance:* one stray Escape at the default setting stops nothing and says how many more presses stop all.

**CW-013 — Assign, rename, properties, clear.**
- *Need:* building a board must be as keyboard-direct as playing it.
- *Behaviour:* firing an empty slot opens a file chooser (WAV, MP3, FLAC, OGG, AIFF, M4A and anything the shared decoder reads); a properties dialog holds name, per-slot level trim in dB, loop, and an optional system-wide chord (MX-058); clear is undoable; sounds are referenced in place, never copied.
- *Keys:* `F2` rename, `Alt+Enter` properties, `Delete` clear, `Ctrl+Z` undo clear, Applications key for the same commands in a context menu.
- *Announced:* the slot's new name is read because its accessible name changes on the edit (A11Y-014); the app adds nothing.
- *Acceptance:* every slot operation is reachable with no pointer, and the slot label updates with focus on it.

**CW-014 — A slot that holds a folder.**
- *Need:* six jingles that all mean "into the news" belong on one key, and the same one twice running sounds broken.
- *Behaviour:* a slot may point at a folder; each press plays a random file from it, never the same file twice running when there is any other; the folder is scanned in the background and at assignment, never on the trigger path.
- *Announced:* nothing on fire; an empty or vanished folder is a spoken failure.
- *Acceptance:* 100 presses on a five-file folder never repeat consecutively and never block the UI thread.

**CW-015 — Find and "what is playing".**
- *Need:* with eighty slots, finding one by name beats remembering its key; and a listener cannot glance at meters.
- *Behaviour:* a search over every bank by name that moves focus to the chosen slot; an on-demand summary of what is playing, with time left on each.
- *Keys:* `Ctrl+F` find; "what is playing" proposed as `Ctrl+L` in the Cart Wall and Running Order.
- *Announced:* the summary is the answer to an explicit request, so it is spoken and brailled.
- *Acceptance:* both work while a bed and two one-shots play.

**CW-016 — Cart sets are the user's files.**
- *Need:* a presenter keeps one board per show, copies them between machines, and must never lose one to the app.
- *Behaviour:* cart sets are human-readable JSON with schema validation, saved atomically (`write_json_atomic`) on change and on exit; paths under the set's own folder are stored relative so a folder of show assets moves intact; the app never overwrites a file that changed on disk since it was read (size, time, then hash) and saves its own changes beside it instead; a file that will not load is copied aside before anything replaces it, and the last-open set is remembered and reopened.
- *Announced:* only when the app had to save beside, or set an unreadable file aside, naming the path.
- *Acceptance:* copying a set over the open one while the app runs, then closing the app, leaves the copied set untouched.

**CW-017 — Relink missing sounds.**
- *Need:* a moved sound library must not cost a rebuilt board.
- *Behaviour:* Relink missing sounds asks for a folder and repairs every missing slot whose file is found there (matched on relative path, then file name), in one pass.
- *Announced:* the outcome with counts: relinked and still missing.
- *Acceptance:* moving a library folder and relinking restores every slot.

**CW-018 — Import a TG Drop Deck board.**
- *Need:* migrating users should not rebuild eighty slots by hand.
- *Behaviour:* read-only import of a TG Drop Deck `board.json` (`"format": 2` as read on 2026-10-26: `slots[]` with `filepath`, `name`, `loop`, `trim_db`, `custom_hotkey`, plus bank names, fader levels and duck depth) into a new cart set, resolving relative paths against the board's folder; tolerant of missing and unknown fields; streaming destinations and keys are never imported (SEC-007).
- *Announced:* outcome with counts of slots imported, files missing, and fields ignored.
- *Acceptance:* TG Drop Deck's own `demo/demo-board.json` imports with every slot in place.

## 22.3 Running order and playout

**PL-010 — A running order list.**
- *Need:* a music show needs a list that cues itself, readable one column at a time.
- *Behaviour:* a native `wx.ListCtrl` report view with columns title (first, so first-letter navigation works and no number precedes it), artist, kind (song or drop), length, scheduled start and own crossfade; title and artist from tags, falling back to the file name. Items can be **skipped** without leaving the list: a Skipped column that is empty for ordinary rows and says "Skipped" otherwise, toggled with `Space`; no check boxes, per QUILL's list convention (TG Drop Deck independently found `wxCheckListBox` ticks invisible to MSAA). No row ever says "playing" (A11Y-014).
- *Keys:* `Enter` play from here; `Space` skip or unskip; `Alt+Up`/`Alt+Down` move; `Alt+Home`/`Alt+End` to top or end; `Delete` remove; `Ctrl+V` paste files from Explorer; jump to the item on air proposed as `Ctrl+Shift+L`.
- *Announced:* the item changing on air is spoken as an outcome (focus is usually elsewhere); skip state is read through the row's own text.
- *Acceptance:* GATE-03-style keyboard-only build and run of a ten-item show with each screen reader.

**PL-011 — Two decks and an honest crossfade.**
- *Need:* songs should hand over like radio, not with gaps or with both fading.
- *Behaviour:* two decks; the next item starts a crossfade length (default 3 s, 0 to 30 s, per-item override) before the outgoing item's **playable end**, which is its duration less trailing digital silence measured once in the background and cached (an MP3's silent tail otherwise swallows the crossfade); the incoming item enters at full level after an anti-click ramp of about 30 ms while the outgoing one rides down; a zero crossfade still overlaps about 0.2 s so a spot butts against the next song; skipped items are stepped over.
- *Acceptance:* rendered-sample tests show the incoming item at level within 30 ms and no gap at zero crossfade.

**PL-012 — Segue now.**
- *Need:* getting out of a track early, on purpose.
- *Behaviour:* cross from what is on air into the selected item at the crossfade length; play the order from the top.
- *Keys:* `Shift+Enter` segue to the selected item; `Ctrl+Shift+Enter` play from the top.
- *Acceptance:* both work with focus on any row.

**PL-013 — Countdown cue on the monitor bus.**
- *Need:* a sighted presenter watches a clock run down; a blind one needs to hear it without the audience hearing it.
- *Behaviour:* optional (off by default), a short tone a set number of seconds before the on-air item's playable end (default 10, range 3 to 60), on the private monitor bus only, never in the programme or the recording, neither ducking nor ducked, with selectable tone and level (default 1 kHz, −6 dBFS); an optional braille flash of the time remaining for users who do not hear the cue; time remaining is also part of "what is playing" (CW-015).
- *Acceptance:* GATE-12 recording contains no cue tone.

**PL-014 — Up next.**
- *Need:* knowing what is coming without walking the running order.
- *Behaviour:* a read-only list of the next unskipped items that drains from the top as items finish, obeying A11Y-015 (the focused row is never removed under the user); when a new item starts, every earlier row leaves at once, so two rows never both claim to be on air; the last row always states the end of the running order.
- *Keys:* proposed `Ctrl+Shift+U`.
- *Acceptance:* the list drains during playback with NVDA focused on a row and produces no unprompted focus announcement.

**PL-015 — Running orders as extended M3U.**
- *Need:* a show worth keeping should open anywhere, and come back here without loss.
- *Behaviour:* save and open running orders as extended M3U (`#EXTINF` with length and "Artist - Title"); state M3U cannot express (kind, skipped, own crossfade) goes on `#QUILL:` comment lines other players ignore; on open, TG Drop Deck's `#DROPDECK:` lines (`kind=drop`, `enabled=0`, `crossfade=N`) are honoured too; paths under the playlist's folder are written relative. Reuse the M3U reading and writing Quill Radio already has rather than adding another.
- *Acceptance:* a running order round-trips without loss here, plays in another M3U player, and a TG Drop Deck M3U opens with its drops and skips intact.

**PL-016 — Drops between songs.** *(P2)*
- *Behaviour:* optionally insert a random drop from a chosen drops folder every N songs, never the same drop twice running.
- *Keys:* insert one random drop now, proposed `Alt+D` in the Running Order.

## 22.4 Engineering lessons worth keeping

Not requirements; evidence from TG Drop Deck's notes to check against our own measurements:

1. **Measure the far end, not the driver.** Its worst audio fault was found by recording the other end of a cable, not from any API report (MX-028, MX-082).
2. **Read each live source once per callback; derive a mix-minus by subtraction**, finishing both sums before any clipping, or each sum gets half a voice.
3. **"Connected" is not "correct".** Most broadcast failures it catalogues raise no error (moved artwork, microphone off the programme, wrong destination), hence a preflight that names Warn cases rather than only Stop cases (MX-066).
4. **Pure rule modules with no `wx` and no network** (its `routing.py`, `preflight.py`, `cuesheet.py`) made every accessibility and safety rule testable one at a time: the same split as `quill/core`.
5. **Never take back a key a user has learned.** It kept an old search key as an alias when it moved; QUILL's rule 5 (a free chord becomes an alias rather than a move) already says so.
6. **A program source is found again by executable after it restarts**, with a settling delay so a closing program cannot say "back" then "closed", and without walking up to the top of the process tree, which it measured capturing nothing (MX-014).
7. **A socket timeout bounds one read, not a conversation**; use a monotonic deadline for any future network check.
8. **Its documentation checker matches every backticked key in the guide against the real accelerator table**, which QUILL already does with the documentation-chord gates.

## 22.5 Considered and not adopted

- **Direct streaming to Icecast, SHOUTcast or RTMP, and stream-key checks:** network egress and stored credentials outside Studio's local-first scope; the audience bus stays device- or integration-based (section 5.2). Revisit only with consent, an egress-audit entry and MX-066.
- **Broadcast picture cards, overlays and camera-in-corner layouts for video platforms:** a streaming feature, not a recording one; section 7 covers capture.
- **A three-level speech setting (all, essential, none):** QUILL's rule is to say less rather than make the user configure how much less; `action_feedback` already chooses the channel for confirmations.
- **Speaking each sound's name as it fires:** the user hears the sound and the focused control already names it.
- **Bundling its AI-generated demo pack:** about 8 MB, terms stated only in prose (LIC-008); Studio starts with an empty wall and a one-key assign flow, and CW-018 imports the pack for anyone who has it.
- **`pedalboard` as the effects and VST3 host:** GPL-3.0 (LIC-008).
- **Its frozen number-row map as the default keymap:** QUILL's family rules allocate keys; offered only as an open question (section 19, question 10).
- **Check-box list for the running order:** QUILL's list convention uses a state column instead (PL-010).
- **In-app feedback with donation prompts:** QUILL has its own feedback channel, and donations only cover AI costs.
- **The Mac copy and its virtual audio driver:** Windows first, and kernel drivers are a non-goal (section 1.4).
- **Portable `userdata` folder and self-update:** QUILL already has both.
- **Porting its UI code:** its single large UI module mixes concerns QUILL keeps apart; port pure modules only (LIC-007).

## 22.6 Phasing

CW and PL depend on Phase 1 of section 16: the programme bus (MX-027), event ducking (MX-038) and the recorder (MX-070 to MX-083). They are a vertical slice for Phase 2: Cart Wall (CW-010 to CW-017) first, then the running order (PL-010 to PL-015), then CW-018 and PL-016. Exit: GATE-11 to GATE-13.
