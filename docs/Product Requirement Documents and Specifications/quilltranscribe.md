# QUILL Transcribe - Product Requirements Document

**Working product name:** QUILL Transcribe  
**Product family:** QuillVille / QUILL  
**Document type:** Product Requirements Document and implementation blueprint  
**Status:** Proposed; architecture and scope for product review  
**Last updated:** 2026-10-13 (as-built notes in 7.2, 7.4, 10.3 and 15.2)  
**Initial platform:** Windows desktop  
**Proposed product identifier:** `QuillTranscribe`

## 1. Executive decision

QUILL Transcribe is a tray-first Windows application for speaking text into the
text field the person is using now. It brings QUILL's existing dictation
engines, model choice, vocabulary, and screen-reader-first interaction to
Outlook, web forms in Edge, Chrome, and Firefox, Notepad, Word, and other
supported Windows text-entry surfaces.

This is a focused product shell over the QUILL framework, not a new speech
recognition stack. QUILL and QUILL Lite already provide dictation and audio-file
transcription. QUILL Inkwell already hosts the shared "Dictate Anywhere"
workflow: it runs in the tray, owns a user-selected system-wide key, uses the
shared dictation controller, and types through a guarded external-document
adapter. The product gap is that this capability is one item inside Inkwell,
whose main purpose is abbreviation expansion. QUILL Transcribe gives
cross-application transcription a dedicated, recognizable, independently
launchable home without creating a second implementation.

### Recommended product decisions

1. **Make QUILL Transcribe the focused shell and product identity for
   Dictate Anywhere.** Keep QUILL Inkwell's abbreviation-expansion product
   intact. Inkwell and the QUILL editors become clients of the same
   cross-application dictation service and shared settings; they must not start
   competing recognizers or register duplicate transcription hotkeys.
2. **Keep all speech logic in the shared QUILL packages.** Reuse
   `quill.core.windows_dictation`, the external document port, model catalogue,
   model store, and task manager. Extract a shared shell-neutral service only
   where necessary; do not fork or copy the controller, recognizers, or text
   injection logic.
3. **Make the system tray a required, first-class entry point.** The tray menu
   must start and stop transcription, reveal the main window, show the selected
   model and current state, and open settings. If Windows cannot provide a
   usable tray, keep a visible, keyboard-accessible window and explain the
   limitation rather than hiding the application.
4. **Local processing is the default.** The person chooses the exact supported
   model. A cloud model is absent from the choices unless its credential is
   configured, and no speech is sent to a network provider without explicit
   consent for that action.
5. **Do not silently retarget text.** When the foreground text target changes,
   pause insertion and require an intentional resume/retarget action before
   writing into the new field.

## 2. Product statement and promise

### 2.1 Vision

Let people dictate into the Windows application they already use, with the
accuracy, model choice, accessibility, and privacy controls they expect from
QUILL.

### 2.2 Product promise

> Choose your model, press your key, speak, and see your words in the field
> you chose. Your speech stays on your PC unless you explicitly choose otherwise.

### 2.3 Position in the family

| Product | Primary job | Relationship to QUILL Transcribe |
|---|---|---|
| QUILL | Write, edit, organize, and work with documents | Keeps in-editor dictation and file transcription; can launch or configure the shared cross-app service |
| QUILL Lite | Accessible plain-text and rich-text editing | Keeps its own editor workflows; can configure and invoke the same cross-app service |
| QUILL Inkwell | Abbreviation expansion across applications | Continues expansion; routes Dictate Anywhere to the one shared transcription owner |
| QUILL Transcribe | Speak into other applications and fields | Dedicated tray-first product for cross-application dictation and transcript delivery |

QUILL Transcribe is not a replacement for QUILL or QUILL Lite, and it is not a
new location for features that belong in the editors. A standalone install must
work without either editor being installed.

## 3. Problem and opportunity

People who dictate into an editor still have to switch workflows when they need
to write an email, complete a web form, answer a message, enter a note in a
desktop program, or fill a document in Word. A general-purpose dictation feature
is often difficult to configure, does not expose the model that is doing the
recognition, or gives screen-reader users too little feedback about whether the
microphone is active and where words will go.

QUILL has already built the difficult shared components: offline engines,
downloadable models, phrase composition, language and vocabulary settings,
file transcription, task cancellation, and a guarded adapter for typing into
other programs. QUILL Transcribe turns those components into a discoverable,
dedicated workflow and gives the user a consistent way to select and trust the
model.

## 4. Goals

1. Start and stop dictation without leaving the foreground application.
2. Insert recognized speech at the caret in supported text fields across
   applications.
3. Let the user select and retain a specific supported model, language,
   microphone, and dictation profile.
4. Make microphone, recognition, pause, target, and error states understandable
   without relying on sight.
5. Provide a usable keyboard-accessible system-tray menu and a compact main
   window.
6. Keep local models and audio processing on the device by default.
7. Preserve QUILL's voice vocabulary, My Words and Phrases, punctuation,
   formatting, and familiar outcome language where those features are safe in
   an external field.
8. Keep the current QUILL, QUILL Lite, and Inkwell capabilities available while
   establishing one owner for cross-app capture and insertion.
9. Ship as a standalone Windows application with a signed installer and
   portable package using the repository's release and update mechanisms.

## 5. Non-goals

The initial release will not:

- Replace Windows Voice Access, Windows voice typing, or accessibility APIs.
- Read, index, summarize, or modify the contents of the target application.
- Provide a general-purpose writing assistant, grammar checker, or editor.
- Execute voice commands that require reading or searching the target
  application's document.
- Install a browser extension, Outlook add-in, Word add-in, or application
  plugin to make ordinary text insertion work.
- Record continuously, start listening at login, or capture audio before an
  explicit start action.
- Upload audio or transcript history for analytics, training, support, or
  telemetry.
- Support arbitrary user-supplied model binaries, model code, or inference
  plugins in version 1.0.
- Promise insertion into every control in every application. Password fields,
  elevated applications, protected surfaces, and inaccessible/custom controls
  may be refused with a clear explanation.
- Replace the existing file-transcription workflow in QUILL or QUILL Lite.

## 6. Audiences and jobs to be done

### 6.1 Screen-reader-first writer

"I need to write an email or fill in a form without moving my hands from the
keyboard. Tell me when you are listening, where the words will go, and whether
they were inserted."

### 6.2 Model-conscious user

"I have a preferred local model, language, and microphone. Do not silently
change them because another model is installed or a request failed."

### 6.3 Privacy-conscious user

"I want offline transcription by default. If an online model is available, tell
me what will be sent before the first request and let me opt out."

### 6.4 Cross-application professional

"I use Outlook, a browser, Word, Notepad, and line-of-business software. I want
the same start/stop gesture and correction vocabulary everywhere."

### 6.5 QUILL family user

"I already use QUILL or QUILL Lite. I want my language, vocabulary, and model
preferences to work in other applications without setting up a second speech
system."

## 7. Core experience

### 7.1 First launch and setup

The first-run experience is short, keyboard-first, and optional to complete in
one pass. It should:

1. Explain that QUILL Transcribe writes into the currently focused application
   and does not read that application's document.
2. Identify available microphones and let the user test/select one.
3. List the supported models already installed, clearly marking local versus
   network-backed operation, language support, download size, and license/source
   information.
4. Allow exact model selection. If a model requires a download, show its size
   and require a deliberate download action. Verify the pinned files before
   making the model available.
5. Offer to choose a system-wide start/stop key. No system-wide transcription
   key is registered until the user chooses one; the tray menu remains a
   keyboard-accessible alternative.
6. Check for hotkey conflicts using the shared Windows probe. Explain that
   Windows can say a key is already in use but cannot reliably identify the
   other application.
7. Offer an optional launch-at-login setting, off by default.
8. Run a brief microphone and target test without sending audio to a provider.

Every step has Skip, Back, and Finish actions. Skipping setup must not leave a
microphone open or install a model in the background.

### 7.2 Live dictation workflow

1. The person places focus in a supported text field.
2. The person starts dictation from the chosen global key or the tray menu.
3. Before opening the microphone, the application verifies that the foreground
   target is not a password field, an unsupported application, an elevated
   process, or one of QUILL Transcribe's own controls.
4. The application gives one concise state cue (screen-reader announcement,
   sound, or both according to the shared feedback setting) and starts capture.
5. Speech is recognized by the selected model and processed by the shared
   dictation composer. Phrases are inserted at the caret without moving focus.
6. If the target loses focus or becomes unsafe, the application pauses delivery,
   retains any uncommitted phrase only for the current session, and explains how
   to resume or discard it. It never silently sends the phrase to a different
   application or field.
7. The user stops from the same key, the tray menu, or the spoken stop phrase.
   The current recognized phrase is flushed when safe; the microphone closes.
8. The application reports the outcome once, without repeating text that the
   screen reader already echoes from the target field.

Start, stop, and resume actions are idempotent. A repeated start must not open a
second microphone session or another recognizer.

**As built, 2026-10-13: the wait is not silent.** Between step 5's pause and the
inserted text a large model can take seconds. With **Tick while a phrase is being
worked on** (a shared dictation setting, `windows_dictation_working_tick`, on by
default in QUILL Transcribe and off in the editors), a soft tick plays once a
second from the first second until the text arrives or recognition fails, and
the first wait of four seconds in a session also says "Still working on that
phrase." The clock starts when the recogniser hands the finished phrase to the
model, not when speech starts. *What you hear after each phrase* is the cap:
nothing means no tick and no sentence; words only means no tick and the sentence
at four seconds, once per wait. A sound pack without the tick also speaks the
sentence at four seconds, once per wait. The setting off is silence. The
sentence is only said while its wait is open, and the read-back that follows a
phrase interrupts it.

**As built, 2026-10-15: the command word (dictation plan D-1).** A command in
another program starts with the command word, **QUILL** by default
(`windows_dictation_command_prefix`), matched forgivingly as the first word
after a pause. An utterance classified as a command never reaches the
insertion step (step 7): if what follows the word is not a command, nothing is
typed, the error cue plays, and "QUILL type that" types the refused words once.
**Strict mode** (`windows_dictation_command_prefix_required`) is on by default
in QUILL Transcribe and off in the editors: a bare command is typed as words,
except the stop phrase. **Command mode** ("QUILL command mode", or the Command
Key pressed twice) takes commands without the word until "dictation mode" or
`windows_dictation_command_timeout` seconds (8, from 5 to 30) with no command,
which ends with a falling tone and no speech; the State field and the tray
name say "Command mode". The **Command Key** (`command_hotkey`) is a second
system-wide key, empty until chosen, offered in setup beside Record Key and in
File > Command Key... (Ctrl+Alt+Shift+K); the window's Dictation menu has the
editors' Speak a Command on F11.

### 7.3 Tray-first operation

The Windows notification-area icon is required for version 1.0. Its accessible
name and tooltip expose the product name and concise current state, for example
"QUILL Transcribe - Ready" or "QUILL Transcribe - Listening".

The keyboard-operable tray menu provides:

- Start Dictation / Stop Dictation, with state reflected in the menu.
- Pause / Resume when the foreground target changes.
- Show QUILL Transcribe.
- Select Model.
- Select Microphone.
- Open Dictation Settings.
- Open Model Library / Manage Installed Models.
- Transcribe Audio File (when enabled in the release scope).
- View Help and Keyboard Shortcuts.
- Check for Updates.
- Exit.

Hiding or minimizing the main window does not stop an active session. Exiting
does stop capture, flushes or discards pending audio according to the user's
explicit choice, releases global hotkeys, and removes the tray icon. If the
tray is unavailable, closing the window must not make the application
unreachable: keep the window visible or minimize it to the taskbar and announce
the fallback.

### 7.4 Main window

The main window is a compact, resizable, standard wxPython window, not a
custom-drawn dashboard. It includes:

- A large, clearly named current-state control: Ready, Listening, Paused,
  Recognizing, or Error.
- The selected model and microphone.
- A Start/Stop control that is operable by keyboard and has a state-specific
  accessible name.
- A target-safety explanation when a session cannot start or continue.
- Direct access to model, microphone, language, hotkey, privacy, and dictation
  settings.
- A help surface describing what is supported and what the app does not read.

The window is not raised automatically when a global hotkey starts dictation.
The user keeps focus in the target application.

**As built, 2026-10-13: the editors' keys.** Inside the window, a dictation
command QUILL Transcribe shares with QUILL and QUILL Lite answers the editors'
chord (family rule 2): Ctrl+F11 start or stop, Alt+Shift+F6 Dictation Settings,
Alt+Shift+F10 My Words and Phrases, Ctrl+Shift+F11 Switch Dictation Language,
Shift+F5 Transcribe a Recording, Shift+F11 Recent Phrases. Version 1.0's Ctrl+D,
Ctrl+, and Ctrl+O remain as second keys (rule 5). Live Transcript, Dictation
Context, Dictation Status and Tidy Dictated Text are not offered, each with its reason in
`quill/core/transcribe/parity.py` (rule 11), and `tests/unit/ui/test_transcribe_dictation_parity.py`
holds the menu to that table.

**As built, 2026-10-13: Recent Phrases (D-5 slice).** The editors' window and
code (`windows_dictation_tools.open_recent_phrases`): the last 20 phrases of the
run, newest first, memory only. Insert Again types the phrase into the program
the person goes back to, through the shared external document's checked
keystrokes and a one-shot field lock, so a password field, an elevated program,
a QUILL window or a moved focus refuses it exactly as it would a dictated
phrase. Copy puts it on the clipboard. Keeping the list on disk is the rest of
D-5.

### 7.5 Model selection and lifecycle

The user can choose a specific model from the shared, approved QUILL dictation
catalogue. Each entry presents:

- Exact model and engine name.
- Local or network-backed operation.
- Supported languages.
- Installed/download-required status.
- Download size and required disk space.
- A concise latency/quality description grounded in available evidence.
- Model source, license, and any relevant restrictions.
- Whether it supports streaming preview or returns a phrase after a pause.

The selected model is sticky. QUILL Transcribe does not switch engines because
another engine is faster, a model download completes, or a request fails.
Fallback is a separate, visible action and announces the model actually used.
Uninstalled models are not selectable as if they were ready.

Downloads are user initiated, pinned to immutable upstream revisions, verified
by SHA-256, resumable where the shared model store supports it, cancellable, and
installed atomically. A failed or cancelled download never leaves a model
marked as usable.

Cloud models:

- Are not listed as usable choices until a credential is configured.
- Use the shared secure credential store; keys never appear in settings files,
  logs, crash reports, or the interface after entry.
- Require explicit consent for the selected network action, including a clear
  statement that speech audio will leave the device and the destination
  provider.
- Show connection/progress state and report errors without a success-shaped
  fallback.
- Are never selected automatically, even if the user has configured a key.

### 7.6 Dictation settings and profiles

The product uses the shared `DictationPreferences` vocabulary and settings
loader. Version 1.0 should expose, at minimum:

- Model and speech language.
- Microphone/device.
- Start/stop hotkey and optional hold-to-talk behavior.
- Pause sensitivity and phrase preview mode.
- Automatic punctuation, capitalization, and spoken punctuation.
- Filler removal.
- My Words and Phrases / rewrite corrections, with Import and Export (Markdown
  or CSV, merge only, preview first; dict.md D-12).
- Number, date, and dash formatting where supported.
- Phrase feedback: speech, sound, both, or silent, following shared
  `action_feedback` guarantees.
- Optional named profiles for common contexts such as email, notes, and forms.

Profiles may change correction and formatting choices, but cannot bypass target
safety or cloud consent. Profiles are explicit user choices; automatic
application-sensitive profiles are out of scope until a privacy review proves
they can be implemented without reading document content.

### 7.7 Safe external text delivery

QUILL Transcribe treats the foreground application as a write-only target. It
does not read the text already in the field, scrape a browser DOM, inspect email
bodies, or infer surrounding prose.

Before a session and before each phrase is committed, the target adapter checks
that:

- A supported text-entry target is focused.
- The target is still the one the user authorized for this session, unless the
  user explicitly retargeted.
- The target is not a password/secret field.
- The target is not running elevated when QUILL Transcribe is not elevated.
- The target is not one of the application's own windows.

If a check fails, do not inject partial content. Pause and report why. A
"Resume in the current field" action explicitly approves a new eligible target.
The application may identify a supported application or control class for
diagnostics, but it must not log the target's text, title if it may contain
private content, or user-entered values.

The external document adapter may retain only the text QUILL Transcribe itself
inserted in the current target session, and only as long as required for safe
spacing and the supported "Scratch that" command. It may issue backspaces only
if the same target remains focused and the remembered inserted range is still
the suffix it wrote. Otherwise it refuses the undo and explains why. It never
claims to provide document undo when the target application does not expose it.

Use the existing checked text-injection boundary. If an injection is incomplete
or uncertain, say that the phrase may be incomplete; do not announce success.
Do not add an unreviewed clipboard-paste fallback that overwrites or leaks the
user's clipboard.

### 7.8 Commands and correction

Only commands that do not need to read the target application are available
while dictating into another program. The initial safe command set includes:

- Stop dictation.
- Scratch that, subject to the same-window and same-target safety checks.
- Spell a word / spelling mode.
- Capitalization and spacing modes.
- Supported language switch.
- Spoken punctuation and paragraph breaks.
- Help / list dictation commands.

**As built, 2026-10-13.** Also, because they only insert: "insert snippet",
"insert abbreviation" and "paste clip" (D-8 slice), from the family's own
snippet, abbreviation and copy-tray files, typed as one phrase that "scratch
that" removes whole. Blanks are typed as "[name]" with no prompts, and a
`${cursor}` mark is dropped; prompted fields are the rest of D-8. "What can I
say" while dictating answers in one spoken sentence rather than opening a window
that would take the focus and pause dictation, and the Dictation Commands window
lists exactly the commands that work in another program, with the person's own
phrases (D-7).

**As built, 2026-10-15: review before it is typed (D-2).** "QUILL review that"
backspaces the last phrase (or takes the words held while paused) into the
shared **Review Dictation** window (Shift+F4, the editors' chord). While it is
open the controller writes into the window's text, never into the target, so
nothing is typed until Insert, and the locked field is not asked (an expected
pause, no "Dictation paused"). After the command word, "make it shorter" and any
other non-command is an AI instruction, and "insert it", "what changed", "read
it back", "undo that change", "back to what I said" and "discard it" act on the
review. Insert brings the locked field's window forward and types the words once
through the same `LockedTarget` and `send_text_checked` path as a phrase; a
refusal types nothing, is said, and leaves the words in Recent Phrases. The AI
is the family's direct route only (QUILL's ChatGPT sign-in or the own key),
asked once for consent with No as the default; only the words in the review
and the instruction are sent, never anything read from the target. With no
route, or in Safe Mode, AI is off and the window edits and inserts by hand.

Commands such as "select that", "correct the last word", "go to the heading",
"replace this paragraph", or commands that inspect selection/document context
are refused in external targets. The refusal is brief, consistent, and tells
the user that the command is available in a QUILL document but not in another
application.

### 7.9 Audio-file transcription

The existing QUILL and QUILL Lite file-transcription pipeline is a natural
second workflow for QUILL Transcribe, but it must not delay or complicate the
core tray-first live-dictation release.

**Recommended 1.0 inclusion if the current shared pipeline can be reused
without an editor dependency:** choose an audio file, choose the exact model,
show accessible cancellable progress, review the result in a read-only/multiline
text control, then explicitly copy, save as text, open in QUILL, or insert into
the currently authorized external text target. Insertion is a separate
confirmation and must revalidate the target immediately before writing.

If that integration cannot meet the same safety and accessibility contract,
ship it in 1.1. Do not duplicate `FileTranscriber`, audio decoding, duration
handling, or worker orchestration inside the new app.

### 7.10 Transcript retention and actions

The default is no transcript history and no retained raw audio. The current
phrase buffer is discarded after successful delivery or session exit, except
for the minimum current-session text required by safe correction behavior.

Optional transcript history is off by default, local-only, user-visible, and
clearable. If enabled, the user chooses whether to save transcript text; audio
recording is a separate opt-in and is never implied by enabling text history.
History is never synchronized or uploaded in version 1.0.

User-directed output actions include:

- Continue typing into the authorized field.
- Copy a reviewed transcript, with an explicit action and no background
  clipboard monitoring.
- Save a transcript to a user-selected file.
- Open a transcript in QUILL or QUILL Lite when installed.

## 8. Accessibility and interaction requirements

1. Stock wxPython controls and standard Windows accessibility APIs are used for
   the main window and dialogs. No custom-drawn writing or model-selection
   controls.
2. Every action is keyboard reachable; the tray menu is usable without a mouse.
   The user can open the main window, change the selected model, start/stop,
   pause/resume, and exit using documented keyboard routes.
3. The main window, dialogs, tray menu, and model rows have descriptive names,
   roles, state, help, deterministic focus, Enter behavior, Escape behavior,
   and reviewable text. Any modal follows QUILL's dialog contract and inventory.
4. F1 explains the purpose of the current window and then the focused control's
   help. Help is authored at control construction sites and included in the
   generated help reference.
5. Announce only information not already conveyed by the screen reader.
   Announce state transitions, target refusal, model changes, completion,
   failure, and cancellation. Do not duplicate the words a target field already
   speaks.
6. Listening state is available non-visually through a concise speech/sound
   setting and visually through text/icon state; color alone never carries it.
7. Do not steal focus when a session starts, a phrase arrives, a download
   completes, or a target changes. Use an accessible status surface and
   announcement.
8. Respect high-contrast themes, scaling, increased text size, reduced motion,
   and the system color scheme.
9. Avoid rapid progress speech. Download/file progress is coarse and
   meaningful; live phrase output is not accompanied by a second announcement
   of the same text.
10. Document and test with NVDA, JAWS, Narrator, keyboard-only navigation, and
    high-contrast mode. Manual verification is required for shipped UI.

## 9. Privacy, security, and safety

### 9.1 Audio and network

- The microphone opens only after a start action and closes on stop, exit,
  device loss, fatal error, or timeout policy.
- Local models process audio on the device. No network request is made for
  audio recognition in local mode.
- Cloud transcription requires provider configuration and per-action consent;
  consent identifies the provider and states that audio is transmitted.
- Network calls are recorded in the repository's egress audit and pass through
  the shared consent boundary.
- No telemetry, usage analytics, audio collection, or transcript collection.

### 9.2 Data minimization

- Never log audio samples, recognized phrases, target text, clipboard content,
  API keys, or raw exception text containing user data.
- Diagnostics contain operational categories and error codes, not transcript
  content or field values.
- Do not observe the system clipboard continuously.
- Do not save raw audio unless the user explicitly starts a separately named
  recording action and selects a destination.
- Settings and history use validated schemas and atomic writes; credentials use
  Windows Credential Manager/DPAPI via the shared secrets facade.
- The one exception to keeping dictated words in memory only (D-2, 2026-10-15):
  words open in Review Dictation are written to
  `transcribe-dictation-review.json` in the data folder while the window is
  open, so a crash loses nothing, and the file is deleted on Insert or Discard.

### 9.3 Safe Mode and shutdown

Safe Mode disables global hooks, microphone activation, model downloads, and
networked transcription. Shutdown cancels active jobs, stops the audio device,
unregisters every hotkey, destroys the tray icon, and leaves no hidden listener.
Each lifecycle path is tested, including forced application close and Windows
logoff.

## 10. Architecture and reuse

### 10.1 Product shell

The product source belongs under `quill/` so it is visible to repository-wide
accessibility, security, reachability, help, and public-surface gates. The
standalone packaging shell belongs under `standalone/quilltranscribe/`.

Proposed ownership:

| Layer | Proposed location | Responsibility |
|---|---|---|
| Product entry point and shell | `quill/apps/transcribe/` | Frame, menus, tray integration, first-run, settings and command wiring |
| Shared speech logic | `quill/core/windows_dictation/` | Existing controller, engines, preferences, model catalogue/store, transcript and file pipeline |
| External text target | `quill/ui/windows_dictation_external.py` and `quill/platform/windows/` | Existing target eligibility checks and checked text injection; extract only shell-neutral contracts if needed |
| Shared process/IPC ownership | `quill/core/ipc.py` plus a narrowly scoped owner protocol | Ensure one capture/controller/hotkey owner and route requests from QUILL, Lite, and Inkwell |
| Standalone package | `standalone/quilltranscribe/` | Launcher, installer, portable build, icons, release docs |
| Tests | `tests/unit/apps/`, `tests/unit/ui/`, `tests/integration/`, `tests/a11y/` | Pure controller, shell contracts, injection safety, lifecycle and manual accessibility gates |

These names are proposals, not a mandate to create every directory. The
implementation should follow the nearest existing app pattern and keep new
modules below the repository's module-size budgets.

### 10.2 Existing QUILL components to reuse

- `quill.core.windows_dictation.controller.DictationController` for the shared
  dictation state machine.
- `quill.core.windows_dictation.preferences.DictationPreferences` and the
  shared settings loader for model, language, composition, feedback, and
  command behavior.
- `quill.core.windows_dictation.engines`, `model_catalog`,
  `model_store`, `model_loader`, and the OpenAI provider gating for engine
  discovery and lifecycle.
- `quill.core.windows_dictation.anywhere` for the shared external-dictation
  preferences/handoff shape.
- `quill.ui.windows_dictation_external.ExternalDocument` and the Windows
  foreground/UIA/text-injection adapters for write-only, checked delivery.
- `quill.stability.task_manager.QuillTaskManager` for bounded cancellable
  background work; marshal every UI callback through `wx.CallAfter` or
  `wx.CallLater`.
- `quill.ui.app_shell.AppShellFrame`, the Inkwell hotkey picker, and
  `quill.apps.beacon.tray.TrayIcon` as patterns for shell, key conflict, and
  tray behavior.
- `quill.core.windows_dictation.file_transcribe.FileTranscriber` and
  `audio_file.py` if the file workflow is included.

QUILL Transcribe must not import `wx` into `quill.core`. The core receives
ports; the Windows/UI shell supplies capture, feedback, target, and insertion
adapters. Do not introduce shared mutable-state locking in core; preserve the
snapshot/worker model and explicit cancellation.

### 10.3 Single-owner rule

There is one microphone capture session and one cross-application insertion
owner per interactive user session. The product must not create one global
hotkey in QUILL, another in Lite, and a third in Inkwell for the same feature.

Before implementation, choose and test one of these compliant arrangements:

1. **Preferred:** QUILL Transcribe owns the service and tray when installed;
   QUILL, Lite, and Inkwell use an authenticated local IPC request to show it,
   configure it, start/stop it, or hand off settings. IPC carries commands and
   preference identifiers only, never transcript text or audio.
2. **Fallback for the first increment:** reuse the existing Inkwell
   single-instance owner and expose a dedicated QUILL Transcribe launch/brand
   mode only if it is genuinely the same process and cannot register a second
   listener. The two product labels must not result in two independent
   controllers.

The owner has a clear lifecycle, request validation, same-user access checks,
and an explicit response for unavailable/not-installed/refused requests. Do not
build an unauthenticated local network endpoint.

**As built (1.0, and 2026-10-13).** Version 1.0 took the fallback: an owner
lock (`quill/core/dictation_owner.py`) that QUILL Transcribe holds while it runs
and Inkwell takes only for its own session. That covered insertion into other
programs and left the microphone unguarded: QUILL's and QUILL Lite's Ctrl+F11
could open a second capture session while QUILL Transcribe listened. Since
2026-10-13 a second lock of the same kind, the microphone lock, is taken by
whichever of QUILL, QUILL Lite, QUILL Transcribe and Inkwell opens the
microphone, through the shared dictation controller, and let go on stop, on an
error, when the window closes and, by the kernel, when the program exits. A
second start is refused with the name of the program listening and the key that
stops it, as that program has it bound ("QUILL Lite is dictating. Press Ctrl+F11
in QUILL Lite to stop it, then try again."). QUILL's Locked Dictation (Ctrl+F9)
takes the same lock while it records. It is a
separate lock because QUILL Transcribe holds the owner lock for as long as it
runs, and the editors must still dictate while it waits in the tray. QUILL
Lite's window now claims itself as QUILL's does, so QUILL Transcribe refuses to
type into either editor and points to Ctrl+F11.

### 10.4 Threading and operations

- UI thread owns every wx widget and does not block on model load, audio I/O,
  transcription, or downloads.
- Audio capture and inference run on the appropriate existing worker path.
- HTTP operations use the shared async/network conventions and consent gate.
- Cancellation is checked at bounded points; cancelling a file job or stopping
  live dictation stops work and reports the outcome.
- Every worker reports exactly one terminal state: complete, cancelled, or
  failed. Errors remain errors; never return an empty transcript as apparent
  success.
- Partial phrase delivery is tracked so retry or stop cannot duplicate text.

## 11. Settings, data, and migration

Use one canonical shared dictation preference model and a small product-owned
settings namespace for product-specific details such as tray startup and the
chosen external hotkey. Follow QUILL's schema validation, backup, atomic-write,
and version-migration rules.

Proposed data ownership:

| Data | Policy |
|---|---|
| Model files | Shared verified QUILL dictation model store; one copy when feasible |
| Provider credentials | Shared secrets facade, never product settings or logs |
| Dictation preferences | One canonical preference shape; changes in one client are visible to the others |
| Global hotkey ownership | One active owner and one conflict-checked setting |
| Transcript history | Off by default, local-only, explicit opt-in and clear action |
| Raw audio | Not retained by default; separately named explicit recording only |
| Usage analytics | None |

Migration from the current Inkwell Dictate Anywhere settings must be
non-destructive and idempotent. Preserve the selected engine, language,
microphone, corrections, and user hotkey when valid. On collision or invalid
configuration, retain the old data, explain the conflict, and ask the user to
choose a replacement; do not silently register an old default globally.

If QUILL Transcribe is removed, it must not delete shared model files,
credentials, or QUILL/Inkwell settings without a separate, explicit user
choice.

## 12. Compatibility and supported targets

### 12.1 Initial compatibility matrix

The release team must maintain a tested matrix, not promise universal support.
Initial candidates:

- Microsoft Outlook text-entry fields.
- Microsoft Word body and supported text controls.
- Notepad and standard Windows edit controls.
- Edge, Chrome, and Firefox web text fields and common form controls.
- Other applications whose controls accept checked Windows text injection and
  pass the target-safety tests.

The initial release does not require browser extensions. Browser versions,
Outlook variants, protected document modes, remote desktops, virtual machines,
and unusual custom controls are individually recorded as supported, best-effort,
or unsupported based on test evidence.

### 12.2 Explicit refusal cases

At minimum, refuse or pause before microphone start or phrase insertion when:

- The focused field is identified as a password/secret input.
- Windows blocks injection because the target is elevated.
- Focus is in QUILL Transcribe itself or another protected internal surface.
- The focus moves to a different top-level target during a session.
- The target cannot safely accept text or checked injection reports incomplete.
- The selected model/device is unavailable or the chosen language is unsupported.

Every refusal says what happened and offers a safe next action. It does not
pretend the text was inserted.

## 13. Performance and reliability targets

Targets are measured on a documented reference Windows machine and published
with the test environment; model latency is reported per model rather than
hidden in one product-wide average.

- Starting or stopping capture through the tray or hotkey produces an
  acknowledged state change within 500 ms at p95, excluding cold model load.
- With a selected model already loaded, a phrase-ending pause is reflected in
  the target or an explicit error within 2 seconds at p95 for the reference
  workload. Streaming models report their mode and progress honestly.
- Cold model-load time is measured and announced; it must not freeze the UI.
- A 30-minute continuous dictation soak has no lost committed phrase, duplicate
  insertion, unbounded memory growth, or capture continuing after stop.
- A changed/invalid target never receives text from a phrase started for a
  different target.
- A task cancellation completes within a bounded interval established by the
  active engine, releases the microphone, and leaves no success-shaped result.
- Model downloads show size/progress, verify hashes, and can be cancelled and
  retried without corrupting the active installation.

The 500 ms and 2 second values are product goals, not claims that every model
can meet them. If a model cannot meet a goal, label its expected behavior and
offer a better-matched choice rather than suppressing the measurement.

## 14. Acceptance criteria for version 1.0

The release is ready only when all applicable criteria pass:

1. A clean standalone install launches without QUILL or QUILL Lite installed.
2. The tray icon and keyboard-operable tray menu expose all required actions;
   loss/unavailability of the tray leaves the app reachable.
3. No global dictation hotkey is registered before the user chooses one.
   Conflicts are detected, explained, and recoverable.
4. At least one bundled local engine works offline from first launch, and the
   chosen model is visible before and during use.
5. The user can select and retain a specific model and supported language; the
   engine does not silently change.
6. Model download is opt-in, pinned, integrity-verified, cancellable, and
   recoverable.
7. Live speech is inserted at the caret in each claimed supported app with the
   selected model and shared composition preferences.
8. Password fields, elevated targets, the product's own windows, and targets
   that lose authorization do not receive text.
9. A focus change pauses delivery and requires explicit retarget/resume; a
   partial injection is reported honestly and never described as complete.
10. Stop and shutdown close the microphone, release hotkeys, cancel work, and
    remove tray resources.
11. Cloud models cannot be selected without a configured credential, and no
    audio is transmitted without explicit action consent.
12. No audio, transcript, target text, provider key, or clipboard data appears
    in logs, diagnostics, analytics, or support bundles.
13. Screen-reader, keyboard-only, high-contrast, scaling, and manual UI
    regression passes are documented for NVDA, JAWS, and Narrator.
14. Core/unit tests cover the controller, external target safety, lifecycle,
    model selection, migration, and error paths; UI source/behavior tests cover
    tray and dialog contracts; integration tests cover process ownership and
    text insertion.
15. All product modules are reachable from an app entry point; public API,
    F1-help, dialog inventory, key ownership, privacy/egress, and release gates
    pass.
16. The standalone release is signed, versioned, and distributed through the
    repository's documented release/update mechanism.

## 15. Test strategy

### 15.1 Unit and contract tests

- Dictation state transitions: start, stop, pause, resume, target change,
  device loss, model error, cancellation, and shutdown.
- Correctly selected model is the one passed to the recognizer; no automatic
  fallback or hidden auto-selection.
- Destination preflight refuses protected fields and the process's own windows.
- Target changes between recognition and injection do not redirect text.
- "Scratch that" only removes the final text written by the current session to
  the same target.
- Partial injection, empty speech, recognition failure, and cancellation have
  distinct terminal outcomes.
- No worker directly touches wx; callbacks marshal to the UI thread.
- Settings migration preserves data, rejects invalid/hijacked values, and
  never writes credentials or transcript text to settings.
- Safe Mode creates no microphone session, global hook, or network request.

### 15.2 Integration and manual tests

- Actual tray interaction and taskbar behavior on supported Windows versions.
- Checked insertion in every application listed as supported in the release
  compatibility matrix.
- NVDA, JAWS, and Narrator feedback for start, stop, phrase delivery, pause,
  target refusal, and errors.
- Screen-reader typing echo is not duplicated by QUILL Transcribe.
- Model setup, download, deletion, update, failure, and low-disk-space paths.
- Microphone unplug/replug, permission denial, sleep/resume, user switching,
  logoff, and application forced exit.
- Two clients attempting to start at the same time yield one owner, one
  recognizer, and a clear response to the second request. Automated since
  2026-10-13 against real operating-system locks: QUILL Lite's window and QUILL
  Transcribe in one test (`tests/unit/apps/test_transcribe_app.py`), and two
  controllers in `tests/unit/core/test_dictation_microphone_and_tick.py`.
- Cloud consent refusal produces no request; consent acceptance sends only the
  audio required by the chosen provider.

## 16. Delivery plan

### Phase 0 - Product and architecture validation

- Verify the current Inkwell Dictate Anywhere path against Outlook, browsers,
  Word, Notepad, and target-safety cases.
- Agree on the single-owner/IPC arrangement and Inkwell migration behavior.
- Confirm product name, icon family, supported Windows baseline, and release
  channel.
- Freeze the version 1.0 support matrix and model list.

### Phase 1 - QUILL Transcribe 1.0

- Dedicated standalone shell, first-run setup, required tray menu, state UI,
  key selection/conflict handling, model/microphone/language settings.
- Shared live dictation controller and external-target adapter, with safe
  retarget/resume behavior.
- Local model path first; cloud model path only if shared consent, credential,
  and egress gates are already complete.
- Shared Inkwell/QUILL/Lite preference handoff and one-owner lifecycle.
- Signed installer and portable package, F1 reference, user guide, and
  compatibility matrix.
- Include audio-file transcription only if the recommended 1.0 criteria in
  section 7.9 are satisfied without duplicating the existing pipeline.

### Phase 2 - 1.1 follow-up

Candidates, each gated by user research and privacy review:

- Full file-to-text workflow if deferred from 1.0.
- Optional local transcript history and user-selected save rules.
- Named per-context profiles with explicit manual switching.
- Richer model comparison using reproducible local benchmarks.
- Better recovery for applications whose text targets expose incomplete UIA.
- Additional accessible onboarding and in-product diagnostics.

No candidate becomes committed scope until its shared-core ownership, tests,
privacy impact, documentation, and QUILL/QUILL Lite parity are reviewed.

## 17. Risks and mitigations

| Risk | Mitigation |
|---|---|
| A second app duplicates Inkwell's existing Dictate Anywhere implementation | Treat this as a dedicated product surface over the current shared path; establish a single controller/hotkey owner before adding a second entry point |
| A focus change sends words to the wrong field | Lock the target per session, pause on change, revalidate at commit, require explicit retarget |
| Screen readers echo typed text and the app repeats it | Default external read-back to sound/status; test NVDA, JAWS, and Narrator; announce outcomes, not inserted words |
| A global key steals a key from another app | No default global registration; shared conflict probe/picker; allow tray-only use |
| Model switches unexpectedly after failure | Keep exact selection sticky; make fallback an explicit action; announce the engine used |
| User assumes a supported app means every custom field works | Publish per-application/version/control compatibility evidence and clear unsupported-target messages |
| Cloud credential presence is mistaken for consent | Separate credential availability from per-action audio consent; never list unavailable providers as selectable |
| Transcript or audio appears in support diagnostics | Data minimization tests and a redaction audit; no speech payloads in logs |
| Coexisting QUILL, Lite, Inkwell, and Transcribe processes compete for the mic/hotkey | One-owner service/IPC contract with integration tests and migration |
| Tray service exits or becomes hidden | Tray availability check, keyboard-operable menu, visible fallback, and startup/shutdown lifecycle tests |

## 18. Decisions to confirm before implementation

These are product decisions, not reasons to block this proposal:

1. **Name:** QUILL Transcribe is the requested working name; confirm final
   casing, icon, and product identifier before installer/brand assets are
   generated.
2. **Owner architecture:** Prefer a dedicated product shell and one shared
   service owner, with Inkwell as a client. Confirm whether IPC is the version
   1.0 boundary or whether the first release can reuse Inkwell's single
   process.
3. **Version 1.0 file workflow:** Include file transcription only if the current
   `FileTranscriber` can be reused with safe external insertion and review; else
   ship live dictation first and deliver file transcription in 1.1.
4. **Cloud model catalogue:** Include only providers already covered by the
   shared credential, consent, privacy, and network-egress contracts.
5. **Compatibility claims:** Final supported application/version matrix must be
   based on Windows and screen-reader testing, not assumed from a successful
   generic `SendInput`.

## 19. Source architecture references

- QUILL product requirements: `docs/Product Requirement Documents and Specifications/QUILL-PRD.md`
- QUILL Lite product requirements: `standalone/quilllite/docs/PRD.md`
- Existing Dictate Anywhere client: `quill/apps/inkwell_dictation.py`
- Inkwell system-wide keys: `quill/apps/inkwell_keys.py`
- External target adapter: `quill/ui/windows_dictation_external.py`
- Shared external preferences/handoff: `quill/core/windows_dictation/anywhere.py`
- Shared controller and engine/catalogue modules:
  `quill/core/windows_dictation/`
- Existing tray shell pattern: `quill/ui/app_shell.py` and
  `quill/apps/beacon/tray.py`
- Windows hotkey conflict probe: `quill/platform/windows/hotkey_owner.py`
- Repository release and signing policy: `docs/release/RELEASE.md` and
  `docs/code-signing.md`
