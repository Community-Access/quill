# QUILL QC2: the whole family, made dependable

| | |
|---|---|
| Status | Remaining work after the QC pass. Completed changes and validation are in qc3.md. |
| Date | 2026-09-30 |
| Scope | QUILL, Quill Radio, Quill Cast, QUILL Lite, shared core, UI, I/O, stability, documentation, tests, and release gates. |
| Purpose | Find bugs, design risks, performance traps, accessibility gaps, and UX improvements before they become another user study. |
| Companion | `qc.md` is the detailed Cast redesign. This document is the wider quality and product review. |

## 0. How to read this

This is deliberately more disciplined than a wish list. Every item carries one of
these confidence labels:

- **Confirmed** means the behavior or structural condition is visible in the
  current source tree.
- **Confirmed user report** means the source documents the problem as an actual
  observed behavior, even if a partial mitigation now exists.
- **Conditional risk** means the source has no direct failure proof, but the
  current ownership or shutdown contract leaves a credible failure path.
- **Recommendation** means a product or architecture improvement, not a claim
  that the current implementation is broken.
- **Existing strength** means a pattern worth protecting and reusing.

Priority has two dimensions. **P0** is an acceptance blocker when the condition
is present: silent data loss, an inaccessible primary workflow, focus theft, or
an operation that cannot be cancelled or recovered. **P1** is a high-risk fix
for the next quality pass. **P2** is important architecture, performance, or
UX work. **P3** is polish after the contracts are sound.

Accessibility is not a separate section at the end. In this memo, accessibility
means that the user can perceive the state, understand what happened, operate
it from the keyboard, keep their place, recover from failure, and use speech,
braille, visual, and earcon output without one channel contradicting another.

## 1. Executive assessment

QUILL has unusually good accessibility infrastructure for a growing desktop
product. The shared `AppShellFrame`, dialog contract, F1 help engine, keymap
labels, announcement rules, braille and earcon support, tray handling, and
Radio's reviewable Now Playing field are the right foundations. The strongest
next step is to make those foundations the ownership boundary for every
background operation and every app surface.

The main risk is not a missing button. It is that a background result, a timer,
a close request, a settings write, or a focus restoration can outlive the
surface that owns it. The user then gets one of four bad experiences:

1. nothing is said;
2. something is said after it is no longer relevant;
3. focus lands in a container instead of the thing they can use; or
4. the app quietly accepts a change that was never persisted.

The next quality pass should therefore prioritize these five contracts:

1. **Every operation has an owner and a lifetime.**
2. **Every outcome has a structured, accessible result.**
3. **Every close path is idempotent and observable without blocking exit.**
4. **Every focus move has a remembered origin and a safe return target.**
5. **Every expensive read, parse, search, or download can report progress and
   be cancelled without leaving a half-updated model.**

The broad review found no reason to throw away the current architecture. It did
find several places where the architecture is expressed by convention rather
than by a shared contract. Those are the places most likely to regress as the
family grows.

## 2. Findings at a glance

| ID | Priority | Confidence | Area | Finding |
|---|---:|---|---|---|
| F-01 | P2 | Remaining UX integration | Lite settings | Failure feedback, dirty state, truthful Preferences results, and retry are implemented. Direct Retry/Open Settings Folder activity controls and broader writer adoption remain. |
| F-02 | P1 | Remaining adoption | Background work | Adopt the implemented lifetime token in short-lived surfaces using shared managers; add reviewable activity retention. Manager shutdown already suppresses queued and late delivery. |
| F-04 | P1 | Confirmed user report | Lite focus | The source documents an intermittent Alt+Tab focus race. The one-shot deferred focus repair can still lose the native activation race. |
| F-05 | P1 | Confirmed | Lite performance | `DocumentFrame.load()` reads and decodes plain and rich files synchronously on the UI path. A size warning does not make the actual read non-blocking. |
| F-06 | P1 | Confirmed | Shutdown | Radio and Cast intentionally swallow most teardown and final-save exceptions. This protects exit, but it also hides cleanup failures and can make the next session inherit stale or incomplete state. |
| F-07 | P2 | Confirmed | Core dispatch | `CommandRegistry` uses plain mutable dictionaries and sets without a declared UI-thread-only registration rule or synchronization. |
| F-08 | P2 | Confirmed | Maintainability | `quill/ui/main_frame.py` is still about 19,254 lines, with Radio at about 2,295 lines and Cast at about 939 lines. The extraction direction is right, but the remaining ownership surface is too large for safe change. |
| F-09 | P2 | Recommendation | Cast performance | The planned whole-library search, transcript search, feed refresh, and download state need an incremental index and bounded background work before they become a UI scan. |
| F-10 | P2 | Recommendation | Cross-app UX | QUILL has shared mechanisms for announcements, help, dialogs, menus, and trays, but not one shared operation/result/activity model. Similar actions can still explain success, failure, and progress differently. |
| F-11 | P2 | Recommendation | Persistence | `--new-instance` Lite windows share settings, so the documented last-writer-wins behavior can overwrite window preferences from another process. |
| F-12 | P2 | Recommendation | Release quality | Many important guarantees live in planning documents or manual sign-off lists. Convert the most important ones into behavioral or source-contract tests so a later refactor cannot quietly remove them. |

None of these findings calls for a broad rewrite. Each is best addressed at the
nearest shared boundary, then adopted by the apps.

## 3. What is already working well

### 3.1 Shared shell and accessibility infrastructure

`quill/ui/app_shell.py` already contains several patterns that should become the
family default:

- common speech, braille, earcon, and status paths;
- F1 context help installation;
- shared modal dialog handling and modal-stack tracking;
- deferred close confirmation outside `EVT_CLOSE`;
- tray restoration and deferred tray exit;
- menu labels derived from the active keymap;
- global and media hotkey registration with guarded teardown;
- shared task-manager access and app feature handling.

This is a strong base. QC2 should extend it rather than have each app invent a
second lifecycle framework.

### 3.2 Radio's reviewable Now Playing field

`quill/apps/radio_now_playing.py` is a model for accessible dynamic text:

- the field is a read-only multiline `wx.TextCtrl`, not an unreviewable label;
- updates are skipped when the text is unchanged;
- updates are deferred while the field has focus;
- elapsed position is available on demand instead of being rewritten every
  second;
- the status bar remains a separate scan surface.

Cast should use the same rule for episode title, podcast, playback state, and
position. QUILL should use the same rule for any dynamic status that a user may
need to review word by word.

### 3.3 Recovery locking is already guarded

The current recovery callers acquire the file lock and release it in
`finally` blocks. That is not a current bug to "fix" blindly. A context manager
could make the invariant harder to forget in future code, but the immediate
quality work belongs in recovery UX and test coverage, not in changing a working
lock lifecycle without a failing case.

### 3.4 Defensive close behavior has a reason

The broad exception handling in Radio and Cast shutdown exists so a failed tray,
hotkey, controller, or optional Quillin cleanup cannot prevent the user from
closing the app. That is a valid accessibility decision: a close command must
not turn into a frozen or permanently trapped window.

The improvement is observability, not removing the guards. Cleanup errors should
be captured in a safe diagnostic result and surfaced at the next useful moment,
while the close itself remains reliable.

## 4. P0 acceptance contracts

These are the conditions that should block a release when violated. They are
product contracts, not a claim that every one is currently failing.

### 4.1 No silent state-changing action

If an action changes a file, setting, queue, subscription, recording, download,
playback state, feature state, or recovery state, the user gets one concise
outcome through the appropriate channels:

- the focused control's own native announcement is not duplicated;
- the app speaks only the result or a reason it could not happen;
- the result is available in braille and a reviewable status surface;
- the result includes the object and the next useful action when one exists;
- background results do not steal focus.

A generic "done" is not enough. The result should answer: **what happened,
to what, and what can I do now?**

### 4.2 No focus theft and no focus abandonment

Every surface records the initiating control before opening a dialog, peer window,
search state, picker, or modeless panel. On success, cancellation, error, and
close, focus returns to a valid target in the originating surface unless the
user deliberately moved elsewhere.

A background refresh must never move focus. Activation repair must not steal
focus from a text field, menu, dialog, or other interactive control that the
user deliberately selected.

### 4.3 No unbounded or un-cancellable busy state

Any operation that can take long enough for a user to wonder whether it worked
must show an accessible state with:

- operation name and current object;
- determinate progress when known, otherwise a truthful busy state;
- cancel when cancellation is safe;
- retry or recovery when it fails;
- a stable place to review the result after focus moves away.

A busy cursor, a changing label, or a silent background thread is not a
progress contract.

### 4.4 Close always reaches a known state

Every close path must be safe when invoked by Alt+F4, the File menu, a tray menu,
Windows logoff, a peer-window close, and an already-running close request. It
must be idempotent and must distinguish:

- work that must be stopped or committed before the window disappears;
- best-effort cleanup that must not block exit;
- failures that should be recorded for the next launch.

The user should never have to guess whether a close command was ignored, vetoed,
minimized to the tray, or completed.

## 5. Detailed findings and fixes

### F-01. Integrate settings failures with Activity/Problems

The silent-failure bug is fixed. Session values remain active, the status
message retains a dirty-state warning, Preferences reports truthfully, reopening
Preferences retries, and queued warnings are flushed before shutdown. Tested
changes are recorded in [QC3](qc3.md).

Remaining work:

- Add direct Retry and Open Settings Folder actions to the proposed shared
  Activity/Problems surface. The current retry route is reopening Preferences.
- Apply the persistence outcome contract to shared settings and app history
  writers, with their own failure-injection tests.
- Verify the spoken result with NVDA, JAWS, and Narrator, including configured
  announcement throttling and a hidden status bar.

### F-02. Adopt lifetime guards in short-lived surfaces

The shared guard and shutdown suppression are implemented and tested; see
[completed changes](qc3.md). Remaining work:

- Supply a distinct `UiLifetimeToken` for each short-lived surface that borrows
  an app manager, and invalidate it before destroying that surface.
- Integrate terminal results with the proposed reviewable Activity/Problems
  store. A retained task future is not a user-facing history.
- Exercise actual window close/reopen paths and verify no stale announcements
  or updates. Direct timers and `wx.CallAfter` outside TaskManager still need
  their own lifetime checks.

### F-04. Lite activation can still lose focus

**Evidence:** `quill/apps/lite_shell.py` documents a real intermittent Alt+Tab
report and uses one `wx.CallAfter(self.return_focus_to_document)` to repair
focus after activation. The guard correctly preserves a real text field or
dialog focus.

**Impact:** the mitigation is thoughtful, but native activation ordering can
still replace the focus after that one deferred callback. The result is a
window that looks active while typing goes nowhere useful. This is a primary
accessibility failure, not cosmetic polish.

**Fix shape:** centralize activation settling in a reusable focus helper:

- track the active child and intended editor control;
- defer until the shell, MDI client, and child report stable visibility;
- use a bounded second check only when focus is still on a container;
- abort if a dialog, menu, find box, or other interactive control has taken
  focus;
- do not announce the focus move because the screen reader already reports it;
- record a diagnostic counter for repeated failed repairs.

The same helper can serve companion apps that restore focus after a peer window
or modal closes.

**Tests:** repeated Alt+Tab cycles, Alt+Tab during Find, Alt+Tab while a menu is
open, activation during child creation, activation after closing a child, and
NVDA keyboard smoke tests for typing immediately after return.

### F-05. Lite file opening is synchronous on the UI path

**Evidence:** `quill/apps/lite_window_file.py::DocumentFrame.load()` calls
`Path.read_text()`, `Path.read_bytes()`, RTF safety scanning, and the editor load
path directly. The public load method is reached from the window-opening flow.

**Impact:** large plain-text files, slow network folders, antivirus scanning,
large RTF files, or a damaged file can make the window stop responding. A
listener cannot tell whether opening is working, and a sighted user sees a
frozen frame. A size confirmation is useful policy, but it does not solve the
latency after confirmation.

**Fix shape:** split open into a worker preparation phase and a UI commit phase:

1. capture the path and a document-open generation;
2. read, decode, and scan on the worker;
3. show an accessible busy state with the filename and Cancel when safe;
4. on the UI thread, discard a result whose generation is stale;
5. commit the decoded text or sanitized RTF atomically to the control;
6. restore document memory, language, spelling, and the caret only after the
   commit succeeds;
7. on failure, keep the original empty or previous document state and offer
   Retry, Open as Plain Text, or Leave Open.

Rich Edit control mutation must remain on the UI thread. The expensive file and
scan work does not have to.

**Tests:** a delayed reader, cancellation, open-then-close, two opens in quick
succession, malformed RTF, large-file latency budget, and focus after success
and failure.

### F-06. Shutdown is reliable but not observable enough

**Evidence:** Radio and Cast protect optional shutdown, final stats/library
writes, controller shutdown, hotkey removal, and tray removal with broad
exception handlers. Both shut down the task manager without waiting for all
workers.

**Impact:** this is correct for the immediate close experience, but a failed
final write can be indistinguishable from a successful one. A stale recording
marker, incomplete resume state, or missing podcast library flush can then
appear as a problem on the next launch. The user receives neither a useful
explanation nor a recovery path.

**Fix shape:** add a shared shutdown report with three classes:

- **must-record:** markers, resume state, and user-owned data writes;
- **best-effort:** tray and global hotkeys, optional controllers, analytics;
- **background:** work that can finish later but can no longer touch the closed
  surface.

Each guarded action records a stable internal error code and a user-safe summary.
The close path still completes. On the next launch, the app can say one concise
sentence such as `The previous session could not finish saving playback state.`
with a Details and Retry path. Never put document content, stream URLs, or
credentials in that diagnostic record.

**Tests:** inject failures into each class, assert that close still completes,
assert that required failure state is retained, and verify the next-launch
message is spoken once and is reviewable later.

### F-07. Command registration needs an explicit thread contract

**Evidence:** `quill/core/commands.py::CommandRegistry` stores commands in plain
mutable dictionaries and sets. `register`, `replace`, `list`, and `run` do not
synchronize or assert an owning thread.

**Impact:** this is safe if registration and dispatch are UI-thread-only. It is
not safe as a future-facing contract if Quillins, plugin discovery, or a worker
can register while the palette, menu builder, or key handler is reading. A
registry race can produce missing commands, duplicate checks that pass twice,
or a menu snapshot that disagrees with dispatch.

**Fix shape:** choose and document one model:

- preferred for the current app: registration is complete on the UI thread and
  all later mutations are marshalled there; assert this in development/tests;
- or, if background registration is a requirement: use a lock and immutable
  snapshots for reads, then notify surfaces to rebuild on the UI thread.

Do not add a lock without deciding how menu and palette snapshots become
consistent. The user-visible contract is more important than the primitive.

**Tests:** concurrent registration/listing if background registration is
supported, otherwise a thread-affinity assertion and a Quillin registration
smoke test.

### F-08. The largest modules still hide ownership boundaries

**Evidence:** current measured sizes are approximately:

- `quill/ui/main_frame.py`: 19,254 lines;
- `quill/apps/radio.py`: 2,295 lines;
- `quill/apps/podcasts.py`: 939 lines;
- `quill/apps/lite.py`: 595 lines.

Radio and Lite already use mixins and extracted modules, and the repository has
module-size budgets. The risk is that the main ownership class still knows too
much about commands, focus, dialogs, persistence, peers, and lifecycle.

**Impact:** large files increase the chance that a focus, menu, or shutdown fix
works in one route but misses a sibling route. They also raise review cost and
make it harder to identify which code owns a timer or callback.

**Fix shape:** extract by lifetime and invariant, not by arbitrary line count:

- document/session lifetime;
- surface/window lifetime;
- operation/task lifetime;
- persistence and recovery;
- command registration and menu rendering;
- status, announcement, braille, and earcon output;
- peer-window registry and focus return.

Every extracted module should have a narrow host protocol and a focused test.
Keep the module-size budget as a ratchet, but do not split code into thin files
that only move the ambiguity around.

## 6. App-specific review

### 6.1 QUILL editor

#### Protect the editor surface

The native text editor is the product's strongest accessibility decision. New
features should continue to wrap the editor rather than replace it with a
custom-drawn writing surface. Every new panel, preview, assistant, or browser
must have a direct keyboard route back to the document and a deterministic focus
return.

#### Make background work feel attached to the document

AI, OCR, watch-folder work, indexing, conversion, spell checking, and external
engine operations should show an operation name, target document, current step,
and cancellation state. The result belongs in a reviewable activity history,
not only in a transient status message.

A user who returns to QUILL after a minute should be able to answer three
questions without reconstructing the past:

- Is the document safe?
- What changed?
- What can I undo or retry?

#### Keep the status bar details-on-demand

The existing status and F6 conventions are valuable. Extend them consistently:
a compact headline on the default surface, a focusable details surface, and a
single action to repeat the last important announcement. Do not turn every
background event into a speech interruption.

#### Do not let the main frame become the integration bus

The size of `main_frame.py` is a maintainability warning even where behavior is
correct. New command handlers should continue to land in feature mixins or
services, with `MainFrame` acting as composition and routing. A new feature is
not complete until its teardown, focus return, F1 help, menu label, status
result, and test are owned by the same feature boundary.

### 6.2 Quill Radio

#### Existing strengths

Radio already demonstrates several family-level answers:

- a reviewable, guarded Now Playing field;
- a focusable status bar reached through F6;
- searchable or browsable station surfaces;
- explicit playback and recording state;
- peer windows with deliberate focus return;
- deferred close confirmation through the shared shell;
- a shared path for adding or removing the playing station from Favorites.

Keep these as shared patterns when Cast or future apps need the same behavior.

#### Make long-running radio work observable

Recording, scheduled recording, catalog refresh, weather monitoring, feed
refresh, reminders, and stream recovery can all continue while the user works
elsewhere. Each should have a single activity representation:

- state: queued, running, paused, retrying, completed, cancelled, failed;
- object: station, recording, catalog, or schedule;
- progress: determinate or explicitly indeterminate;
- next action: stop, retry, open folder, review details, or dismiss;
- output: speech/braille/status wording from the same result object.

A timer or controller callback should never be the only place that knows what
happened.

#### Keep metadata calm

Radio's now-playing update discipline is exactly right. Do not weaken it by
adding elapsed time, bitrate, or other values that rewrite the focused field.
Those facts belong in on-demand status or a details window. If metadata is
missing, say less rather than repeatedly announcing that it is missing.

#### Audit optional subsystem failures

The shutdown path intentionally protects the user from optional teardown
failures. Add failure injection tests around the controller, recorder, scheduler,
tray, hotkeys, and peer-window registry. The goal is not to show an error dialog
while closing. The goal is to prove that the next session can explain a failed
marker or incomplete write without exposing implementation details.

### 6.3 Quill Cast

`qc.md` is the detailed Cast redesign and should remain the source of truth for
its new surface. QC2 adds the following repo-wide constraints.

#### Search must be an index, not a scan disguised as a feature

The planned single search box is excellent UX, but searching podcasts, episodes,
notes, transcripts, and folders can become an accidental full-library scan on
every pause. Build it as an incremental index:

- feed and episode changes update the affected records;
- transcript indexing is a cancellable background task;
- search results carry type, location, and state;
- the UI receives immutable result snapshots;
- an index rebuild has progress, cancellation, and a clear offline/error state;
- stale results identify themselves and cannot overwrite a newer query.

Typing must remain responsive, and the result list must announce a stable count
once per settled query rather than once per keystroke.

#### Downloads need a real job surface

A Downloads menu is not enough for a listener who cannot see a spinner. Every
item should expose state, percentage or indeterminate progress, bytes when
useful, pause/cancel/retry, destination, and the reason for failure. A failed
item must remain in a reviewable list until the user dismisses it or retries it.

The download surface should not require the user to keep the menu open. It also
must not announce every byte update. Use milestones and on-demand details.

#### Feed refresh needs per-feed truth

A single `Refresh All` result such as "done" hides partial failure. Report
success, offline, authentication, parser, and rate-limit outcomes per feed,
with a summary count. New episode discovery should not silently change the
meaning of Inbox or Favorites; the list heading and status should say when the
underlying data was refreshed.

#### Empty, loading, and offline states are product surfaces

Cast's places should remain stable even when empty. Each empty state should say
what the place is, why it is empty, and one reachable next action. Loading
should identify the object being loaded. Offline should preserve locally
available content and state what will happen when connectivity returns.

These states need keyboard focus behavior and screen-reader wording, not only
visual placeholder text.

#### Keep object names in transport actions

The action label must say `Play Thursday's episode`, `Stop The Daily`, or
`Remove The Daily from Favorites`, not only `Play`, `Stop`, or `Remove`. Radio's
shared control-label rule and Cast's `transport_intent` tests should become one
family helper where the object is known.

### 6.4 QUILL Lite

#### Preserve the small product boundary

Lite must remain an editor-first product, not a second QUILL. The family parity
rule is valuable: a capability that Lite needs should move into shared code and
QUILL should receive the same capability when appropriate. Do not solve a Lite
problem by creating an isolated implementation that later drifts.

#### Make MDI tradeoffs explicit

The MDI design gives stable document numbers and a useful Window menu, but MDI
children do not appear in Alt+Tab. That is an intentional tradeoff, not a bug
by itself. The product should make the route obvious through:

- a predictable Window menu;
- Ctrl+Tab and Ctrl+F6 parity;
- Alt+digit routes for the first nine documents;
- a title that includes the document number;
- a first-run or F1 explanation that does not interrupt typing.

The focus repair in `lite_shell.py` still deserves the regression tests described
in F-04.

#### Make multi-instance persistence honest

`--new-instance` is useful, but two processes writing one settings file means the
last process to close can overwrite window state from the other. Options, in
increasing complexity:

1. document the scope clearly and exclude volatile window state from the shared
   settings write;
2. merge settings fields using a per-field last-modified record;
3. give each instance a session-local window-state file and merge only stable
   preferences;
4. discourage concurrent instances only when a conflicting write is detected.

Atomic writes prevent half-written JSON. They do not prevent a valid older
snapshot from replacing a valid newer snapshot.

#### Give file opening the same care as autosave

Lite already treats recovery and autosave seriously. Opening should receive the
same explicit state machine: requested, reading, decoded, committed, failed, or
cancelled. That makes the large-file fix testable and makes focus behavior
predictable.

## 7. Shared UX improvements

### 7.1 A structured action result

Introduce a small shared result model rather than having every feature invent a
sentence at each call site. It could contain:

- `action`: save, play, follow, export, refresh, open, recover;
- `object_name`: the user-facing object;
- `outcome`: completed, blocked, cancelled, failed, partial;
- `summary`: concise sentence for status and speech;
- `reason`: why it was blocked or failed;
- `next_actions`: retry, undo, open, details, or dismiss;
- `operation_id`: correlation for logs and background tasks;
- `importance`: whether it is spoken immediately or only made reviewable.

Render the same result into speech, braille, a status cell, a visual label, and
an activity row. The wording can still be app-specific, but the information
shape should be stable.

This directly addresses the recurring user report that a button did nothing.
It also supports GATE-13: a native control announcement remains native, while
the result renderer says only what the control cannot.

### 7.2 An accessible Activity and Problems surface

A shared Activity surface would collect active and recent operations across the
current app:

- active downloads, recordings, imports, scans, saves, and refreshes;
- completed and failed results;
- retry, cancel, undo, open destination, and details actions;
- timestamps and object names;
- bounded retention;
- no document content or secrets in the record.

This should not become a noisy notification feed. Announce important transitions
once, then make everything reviewable on demand through a list with a stable
keyboard shape.

### 7.3 Progress as a first-class accessible control

Use one shared progress model and renderer:

- `phase`: preparing, reading, parsing, downloading, writing, finalizing;
- `current` and `total` when determinate;
- `message`: the current object and phase;
- `can_cancel`, `can_pause`, and `can_retry`;
- `last_announced_milestone` to prevent speech storms;
- `owner_token` to prevent stale delivery.

A progress dialog is only one renderer. The same operation should be visible in
an activity list and a compact status cell, so closing a dialog does not destroy
access to the result.

### 7.4 Focus memory per surface

Every reusable surface should have a small focus record:

- initiating window and control;
- last meaningful control in the surface;
- selected object identity, not only a row index;
- return action for success, cancellation, and failure;
- whether returning focus is still safe.

This is particularly important for Cast search results, Radio peer windows,
Lite MDI children, file pickers, and QUILL side panels. Returning to a row index
after the list changed is not enough; return by stable object identity and choose
the nearest valid row when the object disappeared.

### 7.5 Repeat last important announcement

A consistent command should repeat the last important app result, not the last
thing the screen reader already read. It should be available in QUILL, Radio,
Cast, and Lite with the same concept and different app vocabulary only where
necessary.

The stored message should be the structured result, so the app can render it in
speech, braille, and a details surface. It should not capture arbitrary document
text or credentials.

### 7.6 A real status hierarchy

Keep three levels distinct:

1. **Immediate outcome:** one concise speech/braille announcement.
2. **Compact status:** current app state, reachable through the standard status
   route such as F6 where applicable.
3. **Details:** a reviewable window or activity row with full explanation and
   next actions.

This prevents two opposite failures: silence when the result matters, and a
constant stream of progress messages that makes the app tiring to use.

### 7.7 Settings that answer tasks

The settings model is broad and powerful. The UX should add:

- one searchable settings view with exact labels and aliases;
- task recipes such as `Prepare for dictation`, `Quiet background work`,
  `Set up podcast downloads`, or `Make the editor high contrast`;
- a preview of changes before applying them;
- one undo action for a recipe or multi-setting change;
- a clear distinction between current session state and persisted state;
- a direct retry when a settings write fails.

A recipe must be a visible composition of existing settings, not a hidden mode
that changes unrelated behavior.

### 7.8 Better first-run paths

First-run experiences should be task-oriented and skippable. The first screen
should answer:

- what can I do here;
- what is the first useful action;
- what key or menu reaches it;
- how do I return without losing my place.

Radio's Browse Stations route and Cast's Add Podcast route should both work
without requiring a user to understand the data model first. An empty library
should be an invitation with one primary action, not a dead list.

### 7.9 Offline and failure states are not exceptions to UX

Every networked app needs stable wording and controls for:

- offline at startup;
- offline during refresh;
- authentication required;
- rate limited;
- partial success;
- stale local data;
- retry queued;
- permanently unsupported content.

The user should be able to continue with local content, understand what is
stale, and retry without reconstructing the original action.

### 7.10 Feature switches must remove ambiguity

The existing feature and dispatch gates are a good foundation. A disabled
feature should:

- remove all routes that would falsely imply it is available;
- retain one discoverable explanation in Customize Features or Help;
- explain why a command is unavailable when a surface can show disabled rows;
- stop background work and polling associated with the feature;
- restore the feature without leaving stale menu items or status cells.

A feature switch that hides a button but leaves a key, palette command, timer, or
tray entry is an accessibility failure because the user cannot see the route
that still exists.

## 8. Performance plan

Performance work should measure user-visible budgets, not only function duration.
A fast worker that leaves the UI frozen or the screen reader silent is not a
fast feature.

### 8.1 Add launch and interaction budgets

Measure cold and warm startup for QUILL, Radio, Cast, and Lite:

- process start to first usable window;
- first focusable control;
- first spoken title;
- first document or library content;
- time to open the command palette;
- time to open Settings;
- time to return focus after a peer or dialog closes.

Keep the measurements in a diagnostic mode and add a small regression threshold
for each app. Do not make the normal launch noisy.

### 8.2 Move expensive reads off the UI thread

The Lite open path is the immediate case. The same audit should cover:

- document conversion and format parsing;
- RTF safety scans;
- podcast feed parsing and transcript indexing;
- OPML import/export and backup creation;
- catalog refresh;
- OCR and image description;
- large settings or history migration.

The UI thread should own controls and model commits. Workers should produce
immutable preparation results with a cancellation token and an owner generation.

### 8.3 Coalesce dynamic updates

Use equality checks, debounce, and milestone reporting for:

- search queries;
- playback position;
- feed refresh counts;
- download bytes;
- catalog status;
- repeated settings changes;
- speech and braille status updates.

Never solve a speech storm by suppressing all outcomes. Preserve a reviewable
latest state and announce meaningful transitions.

### 8.4 Bound memory and indexing

For large libraries and documents:

- index incrementally;
- cap transcript and search result memory;
- avoid retaining full duplicate strings in UI rows and model snapshots;
- paginate or virtualize where a list can grow without a practical bound;
- make cache eviction observable in diagnostics;
- keep user data out of logs.

A 50 MB document budget already exists in the core performance tests. Add
comparable budgets for Cast library search and feed refresh, and for opening a
large Lite file after the asynchronous path lands.

### 8.5 Treat polling as a resource with a policy

Every timer should declare:

- owner and shutdown method;
- interval and reason;
- whether it runs while hidden or minimized;
- offline behavior;
- whether duplicate ticks are coalesced;
- what happens when the callback outlives the surface.

This applies to Lite's inbox, Radio's recording and monitoring timers, Cast's
feed checks, and shared update checks.

## 9. Test and gate proposals

The repository already has strong gates. QC2 should add only the gates that
protect recurring failure classes.

### 9.1 Accessibility and focus

- **Outcome contract test:** every state-changing command returns or emits a
  result with object, outcome, and next action.
- **Focus lifetime test:** every dialog, peer, picker, search mode, and modeless
  panel has success, cancel, failure, and close focus paths.
- **No stale delivery test:** invalidated surface tokens suppress worker
  callbacks and announcements.
- **Dynamic text test:** focused reviewable fields do not rewrite under the
  reader; unchanged text is not written again.
- **Context-menu parity test:** lists and trees expose the same action set by
  keyboard, menu, and context menu where the action is applicable.
- **Feature-route test:** disabling a feature removes its menu, key, palette,
  tray, status, and background routes.
- **Screen-reader acceptance matrix:** NVDA, JAWS, and Narrator for the primary
  workflows, with speech, braille, focus, and keyboard results recorded
  separately.

### 9.2 Lifecycle and persistence

- close while a worker is queued, running, failing, and reporting progress;
- close while a timer tick is queued;
- close twice and close through every route;
- forced OS close where the event cannot be vetoed;
- tray restore and tray exit;
- peer-window destruction and app shutdown;
- read-only settings directory and failed atomic write;
- corrupt, partial, or old settings JSON;
- two Lite instances writing settings;
- recovery offer dismissed, recovered, failed, and retried.

### 9.3 Performance

- cold and warm startup thresholds per app;
- first usable focus threshold;
- large plain-text and RTF open;
- Cast search over a synthetic library with transcript content;
- feed refresh with slow, failing, and partial sources;
- download queue with many items;
- bounded memory under repeated search and open/close cycles.

The tests should fail on a user-visible regression, not on a machine-specific
microsecond difference.

### 9.4 Documentation and generated references

Keep the existing generated reference gates authoritative for keybindings, F1
help, settings documentation, site links, dialog inventory, reachability, and
surface fixtures. Add a review rule for any new operation or feature:

- it appears in the user-facing help model;
- its disabled and failure states are documented;
- its keyboard route is generated or tested;
- its dialog or peer surface is inventoried;
- its manual sign-off row names the actual entry route.

Planning documents can explain intent, but they should not be the only place a
release guarantee exists.

## 10. Staged roadmap

### Stage 1: remove silent and stale outcomes

1. Integrate settings failure actions with Activity/Problems and verify screen readers.
2. Adopt the shared UI lifetime token in short-lived surfaces and activity history.
3. Add shutdown failure capture for required writes and stale markers.
4. Add the Lite activation/focus regression matrix.
5. Add a focused large-file opening test and choose the asynchronous design.

### Stage 2: make the shared contracts reusable

1. Introduce the structured action result.
2. Introduce the shared Activity/Problems model.
3. Introduce the progress model with cancellation and owner invalidation.
4. Introduce the focus-memory helper.
5. Standardize repeat-last-important-announcement and details-on-demand.
6. Decide and enforce the CommandRegistry thread-affinity model.

### Stage 3: apply the contracts to each app

1. Complete the Cast one-window redesign from `qc.md`.
2. Give Cast downloads, feed refresh, search, and offline states the shared
   operation model.
3. Give Radio recording, scheduling, catalog, and recovery the same activity and
   failure model.
4. Move Lite open, inbox, autosave, and multi-instance persistence to explicit
   lifetime contracts.
5. Keep QUILL's editor, AI, OCR, conversion, and watch-folder work on the same
   progress and recovery primitives.

### Stage 4: pay down ownership and performance debt

1. Extract `main_frame.py` by lifetime and invariant.
2. Reduce Radio and Cast orchestration modules without duplicating behavior.
3. Add launch, search, feed, and large-document performance budgets.
4. Make every timer declare owner, policy, and shutdown behavior.
5. Convert the most important planning promises into behavioral gates.

### Stage 5: product delight after reliability

1. Searchable settings and task recipes.
2. Focus, review, and session profiles built from existing settings.
3. Richer queue and activity views.
4. Better first-run guidance with skippable task paths.
5. Cross-app personalization that never changes keyboard or screen-reader
   fundamentals without an explicit user choice.

## 11. Definition of truly excellent

QUILL and its companion apps will feel excellent when a listener or writer can
answer these questions without seeing the source, remembering a hidden mode, or
repeating an action in hope:

- What is focused?
- What is this control going to act on?
- Did it work?
- If it did not work, why not?
- What can I do next?
- Where did my focus go?
- Can I undo, retry, cancel, or recover?
- What is still running after I leave this window?
- What will survive closing the app?
- Can I review the answer through speech, braille, keyboard, or sight?

That is the common product language the family needs. The architecture is close:
Radio has several of the right patterns, Cast now has a coherent target shape,
Lite has a clean small-product boundary, and QUILL has the deepest shared
infrastructure. QC2's work is to turn those good local answers into explicit
lifetime, result, focus, progress, and persistence contracts that every app can
keep.
