# QUILL family: meaningful delight without more clutter

**Prepared for:** Jeff Bishop / Community Access  
**Date:** 2026-11-10  
**Status:** Design recommendations for review; not approved scope or implementation claims.  
**Companion:** [GitHub/WordPress completion and AI vision](./complete.md).

## 1. The aim

The family should feel considerate: it remembers what matters, tells the truth, makes the next useful action easy, and lets people recover without a struggle.

Delight can be a small moment: returning to the exact sentence you left, hearing that a recording actually contains the microphone, finding a completed file immediately, or changing a setting and understanding the result. These moments earn their place because they remove effort or uncertainty.

**Recommendation:** improve a small number of shared interaction contracts and apply them carefully in each app. Keep every app's purpose and familiar layout. A shared behavior does not require a shared dashboard, a new assistant, or another window.

### The admission test for a proposed change

Keep an idea only when we can answer:

1. What real task or recurring frustration does it address?
2. What does the person do before and after the change?
3. Which existing control, store or command can carry it?
4. Can it reduce decisions, interruptions or steps?
5. Can a person discover and use it by keyboard, speech and braille?
6. How will we observe that it helped?
7. What should we remove, simplify or avoid adding in exchange?

Feature count, cleverness, engagement time and AI usage are not success measures. Task success, confidence, retained work and low effort are.

## 2. What the source already provides

This is a targeted source-and-document survey, not a live usability test. Presence of a module is not proof of complete adoption or acceptance in every app.

| Foundation inspected | Consequence for this plan |
| --- | --- |
| [App launcher and release gates](./quill/core/app_launcher.py) | Apps already open one another. Improve context and outcomes rather than proposing a second launcher |
| [Action feedback](./quill/core/action_feedback.py) | Sound/speech/both/silent already exist. Improve consistency without replacing established defaults |
| [Notifications](./quill/core/notifications.py) | Durable notices and actionable targets already exist. A new family inbox needs to prove value beyond this |
| [Session restoration](./quill/core/session_restore.py), [recovery triage](./quill/core/recovery_triage.py) | Restore and recovery already address real problems. Extend continuity without restoring clutter or silently discarding meaningful work |
| [Shared preferences](./quill/core/family_preferences.py) | Sharing is deliberately narrow and opt-in. Do not casually synchronize keys, focus behavior or account state |
| [Quick Actions](./quill/core/quick_actions.py) | User ordering/default actions already have a mechanism. Preserve deliberate arrangements instead of adding automatic menu reshuffling |
| [Audio routing](./quill/core/app_sound_route.py) | Audit existing ownership/routing before adding family-wide media control |
| [Family data contract](./docs/design/FAMILY-DATA.md) | Shared state has ownership/versioning obligations; a new convenience cannot risk another app's data |
| [Radio surface design](./docs/planning/radio-surface-design.md) | A favorites-first surface and controls one action away are deliberate. Do not restore permanent button rows |
| [Current Studio plan](./docs/planning/QUILL-Studio-PRD.md), [recording/preview proposals](./docs/planning/studio-demo-roadmap-proposals.md) | Rehearsal/routing/verification already have accepted or proposed scope. Connect proposals to that work rather than rebuilding it |
| [Reviewing documents by ear](./docs/design/2026-10-04-plancake-lessons.md) | Notes, exact places, safe saves and outcome-only feedback already have a detailed design history |
| [Command Key design](./docs/design/command-key.md), [AI family design](./docs/design/codex.md) | Discovery, Ask and task engines have a shared home. Reuse them |
| [Beacon purpose](./standalone/beacon/README.md), [Social purpose](./standalone/social/README.md) | Exact-place saving and context-preserving reading already have product homes; avoid duplicating whole products |

Some planning/app overview documents describe older release states. Before implementation, verify current source, packaged behavior, accepted decisions and public release gates. Recommendations for Studio, Cast, Player, Beacon or Social do not authorize exposing a gated app or assuming its live integration is complete.

## 3. The five changes I would prioritize

| Rank | Proposal | Why it matters | First place to prove it |
| --- | --- | --- | --- |
| 1 | FUX-01: Return to the exact place | People spend less effort reconstructing their own work | QUILL Lite reading/editing, then Cast or Player |
| 2 | FUX-04: Useful, truthful completion | A job ends with a result the person can find and act on | Converter batch, then Transcribe export |
| 3 | FUX-06: Lists that respect the reader | Background work stops moving the thing someone is trying to read | Radio browsing, then Cast/Social/Workbench lists |
| 4 | FUX-07: Text always goes to the intended place | Dictation and abbreviation expansion feel dependable | Transcribe and Inkwell |
| 5 | FUX-03: Know where sound is coming from and going | Listening and recording become less confusing and more verifiable | Radio plus Studio rehearsal |

These rankings reflect expected user value from the surveyed architecture, not measured severity. If observation finds a frequent lost-work, misleading-state or inaccessible-control defect, that defect comes first.

## 4. Sixteen proposals worth considering

### FUX-01 — Return to the exact place, with a useful way back

**Moment:** “I was interrupted. Let me continue without finding everything again.”

**Change:** Preserve the meaningful place, not only an open file or URL: document passage and selection, podcast episode/time, transcript segment, selected station/category, or list item/filter. When navigating elsewhere, preserve the origin so Back returns to the exact source.

**Keep it small:** Use existing restoration and navigation. No mandatory Start screen. A normal reopen can simply restore the place; show a choice only when recovery, several competing sessions or a changed resource makes one necessary.

**Important detail:** A timestamp/line number may drift. Use existing stable identifiers or Beacon location resolution where appropriate; if exact recovery fails, say what was restored and offer the nearest verified place. Do not guess silently.

**First pilot:** Read a long document, follow a link or open an associated recording, then return. Repeat after restart and after the source has changed.

**Acceptance**

- [ ] The original passage/item and reading context are restored where supported.
- [ ] Missing/moved content remains visible and understandable.
- [ ] Live radio is not represented as a seekable recording.
- [ ] A recovered recording or draft is not automatically played, sent or published.
- [ ] Observe time and wrong turns needed to resume, compared with the current app.

**Existing overlap:** session restoration, Beacon locations, and the Workbench context-bookmark proposals. This extends their reach and consistency.

### FUX-02 — Carry the work between apps, including the reason

**Moment:** “Transcribe this part of my recording,” or “Open that transcript in QUILL.”

**Change:** Handoffs carry an explicit source, selected range, intended destination and useful metadata. A receiving app opens the right object at the right place and makes the originating app reachable again.

**Examples:** A Studio time selection becomes a Transcribe task; its result opens in QUILL with source time references. A Cast passage saved in Beacon returns to the episode at the relevant point. A Converter output opens in the intended installed player.

**Keep it small:** Put the action where the object is already selected. Reuse the existing launcher/deep links and product boundaries. No required family portal.

**Acceptance**

- [ ] Distinguish passing a reference, making a copy and creating a transformed output.
- [ ] Preserve the original and explain where the new artifact lives.
- [ ] Unavailable/gated destinations offer a useful save/export path without an installation detour.
- [ ] Do not change the receiving app's playback, microphone or account choice unexpectedly.
- [ ] Return to the origin restores its selection.
- [ ] Exercise portable installs, missing apps, duplicate names, changed files and unavailable remote resources.

**Existing overlap:** sibling launch, Beacon, Studio/Transcribe plans and AI mission handoff. The extra value is a dependable artifact/context contract.

### FUX-03 — Make audio ownership understandable

**Moment:** “Something is playing. Which app is it? Is the screen reader going into my recording?”

**Change:** Within the relevant app, expose a concise, on-demand account of active media, playback destination, recording inputs and monitored versus recorded sound. When another family app requests media control, make the consequence explicit at the point of conflict.

**Keep it small:** Reuse status cells, transport commands and existing audio-routing controls. No permanent family mixer floating over every app.

**Design details**

- A reliable “What is playing/recording here?” command, reachable through existing command discovery; assign any new shortcut only after a family key audit.
- Distinguish pausing a player from stopping a recording or muting a monitor.
- On device loss, report the actual affected route. Do not silently move a private monitor or microphone to a new destination.
- Headphone/device return can offer a deliberate recovery of the previous route.
- Ducking or pausing another app is a user choice; preserve configured accessibility feedback and Weather alert policies.

**Acceptance**

- [ ] Play Radio while rehearsing a Studio recording and determine each route without sight.
- [ ] Listen back to a real short test capture to verify what entered the recording.
- [ ] Identify and recover a disconnected input/output device.
- [ ] OS/device limitations are stated; a configured route is not reported as proof of captured audio.

**Existing overlap:** app sound routing and Studio's source/bus/rehearsal plans. Improve the common explanation and conflict behavior.

### FUX-04 — Finish with the actual result and the next useful action

**Moment:** “It says complete. Where is my file, and did every item work?”

**Change:** The end of a job provides an understandable receipt: what succeeded, where it went, what is partial and the next appropriate action. “Converted 4 of 5 files. One needs attention. Open results / Retry failed.”

**Keep it small:** Extend existing task results and durable notices. A successful single-file save usually needs only its normal confirmation and reachable result; do not open a report window every time.

**Acceptance**

- [ ] A completed output can be opened or located with keyboard commands from its result.
- [ ] Result identity survives duplicate file names; show enough path/source information to distinguish them.
- [ ] Keep successful items when retrying failures.
- [ ] Cancellation says what exists, what is incomplete and what can resume.
- [ ] Output validation is reported separately from processing completion.
- [ ] A delayed result does not steal focus from the document someone is now writing.
- [ ] After missing the spoken notification, the same useful result remains reachable.

**Existing overlap:** notifications, recent problems, task/AI activity and batch result infrastructure.

### FUX-05 — Recovery that speaks in terms of the person's work

**Moment:** “I changed the wrong thing. Can I get back?”

**Change:** Undo/recovery names the action and object: “Undo changing this paragraph,” “Restore the previous export settings,” or “This remote publication cannot be undone here; open the published item.”

**Keep it small:** Improve existing undo, checkpoints and recovery surfaces. Avoid another universal history database that stores every piece of private content.

**Acceptance**

- [ ] The proposed recovery names what will change and what cannot be restored.
- [ ] Local edits preserve ordinary undo grouping and selection.
- [ ] Recoverable drafts and original files are distinct from disposable caches.
- [ ] Destructive or remote actions are not labelled undoable until recovery is verified.
- [ ] Review ambiguous duplicates instead of silently declaring one copy worthless.
- [ ] Include failures during undo and recovery, not only successful cases.

**Existing overlap:** recovery triage, local undo, Workbench history and AI checkpoints. The proposal improves predictability and language across them.

### FUX-06 — Let lists update without moving the reader

**Moment:** “I was reading that episode/post/station, and a refresh moved everything.”

**Change:** Maintain focus and selection by stable item identity. Gather new arrivals without replacing the item being read. Let the person reveal new content deliberately; when the selected object disappears, explain that fact and choose a predictable neighbor.

**Keep it small:** Use a shared update/selection contract in existing lists. A small “new items available” state is enough; no animated feed or automatic resorting.

**Acceptance**

- [ ] Refreshes do not move focus, restart details reading or repeatedly announce unchanged data.
- [ ] The person controls when arrivals enter the current sorted reading list.
- [ ] Genuine object changes remain inspectable with a timestamp.
- [ ] Filtering/sorting retains the selection where valid and explains when it no longer matches.
- [ ] Expired/deleted content remains recognizable as such; no fabricated details.
- [ ] Test slow responses arriving out of order, reconnect, paging and multiple windows.

**First pilot:** Radio browsing, then episode/timeline and Workbench lists. Existing products may already implement much of this; audit adoption before coding.

### FUX-07 — Protect the destination of dictated and expanded text

**Moment:** “I started dictating a message, but focus changed.”

**Change:** Transcribe and Inkwell keep the intended application/control visible and understandable before text insertion. If focus or target identity changes ambiguously, retain the captured text and offer a deliberate insertion or copy action.

**Keep it small:** Use existing Dictate Here and expansion controls. Do not ask for confirmation before every normal phrase or collect an ongoing keystroke history.

**Acceptance**

- [ ] The user can determine the current target and whether insertion is live or pending.
- [ ] Alt+Tab, dialogs, closed controls and application restart cannot redirect a pending insertion silently.
- [ ] Ambiguous targets preserve text instead of losing it.
- [ ] An expansion supports the existing literal/escape path and usable undo where the target allows it.
- [ ] Password/secure controls follow explicit platform-supported restrictions. Unknown platform state is not advertised as a proven secure-target detector.
- [ ] Explain target failures without reading private text aloud unexpectedly.
- [ ] Test with actual supported receiving applications and assistive tools.

**Why this ranks highly:** trust in system-wide input determines whether people will use the feature at all.

### FUX-08 — Let people hear or see what a setting will do

**Moment:** “What does this option change? I don't want to break my setup.”

**Change:** For settings with meaningful observable effects, offer a short reversible preview: sample feedback, reading verbosity, export example or layout behavior. Show the setting's current value, where it applies and whether it is shared.

**Keep it small:** Use the existing settings/help surface and the narrow shared-preference contract. Many settings need only a better sentence.

**Acceptance**

- [ ] Preview has a clear end/cancel and restores prior state.
- [ ] Shared versus app-only scope is understandable before applying.
- [ ] Nothing silently synchronizes keys, focus behavior, microphone choices or credentials.
- [ ] A setting that needs restart says so; avoid pretending the preview is applied.
- [ ] No extra confirmation for ordinary reversible choices.
- [ ] People can undo the change without remembering the old value.

**Existing overlap:** Preferences Search, action feedback, sound previews, and shared preferences.

### FUX-09 — Give the first useful task a clear beginning

**Moment:** “I installed this. What can I do successfully right now?”

**Change:** Empty states offer one or two actions that match the app's purpose, plus an optional tiny sample. A person can complete a useful task before learning the product's whole vocabulary.

**Examples:** Converter: choose files and a practical output. Radio: browse stations or add a known address. Transcribe: dictate into a scratch document or try a short bundled clip. Studio: record and listen to a short rehearsal.

**Keep it small:** No compulsory tour, account funnel, feature carousel, pop-up sequence or mandatory sample library.

**Acceptance**

- [ ] First-task wording is a genuine action with a keyboard path and visible label.
- [ ] Sample content is clearly marked, removable and never mixed into personal work.
- [ ] Declining the sample leaves the normal app ready to use.
- [ ] First tasks do not require a network, account or download unless intrinsic; name that dependency before asking.
- [ ] Observe time to first successful result and the places where new users stop.

**Existing overlap:** tutorials/help. The proposal joins them to the empty state instead of creating a parallel training product.

### FUX-10 — Help that explains the selected situation

**Moment:** “Why can't I do this here?” or “What does that word mean?”

**Change:** Existing F1 and command discovery answer the question for the selected object and current state: what this is, what Enter does, which actions are available and why another action is unavailable.

**Keep it small:** Reuse the command catalogue and help engine. No separate search assistant or second command system.

**Acceptance**

- [ ] A disabled action has a readable reason and next step.
- [ ] Existing users retain menu paths and stable command identities.
- [ ] Search matches familiar intent/synonyms as well as exact labels.
- [ ] Context help knows source/live/file/draft/selection state where relevant.
- [ ] Help does not interrupt focus reading or open irrelevant product documentation.
- [ ] A short explanation can be expanded into a worked example or tutorial.

**Existing overlap:** Command Key, F1 help, Workbench help and AI Ask. Audit consistent application across products.

### FUX-11 — Rehearse the real outcome before a long job

**Moment:** “I don't want to record an hour before finding the microphone was wrong.”

**Change:** Offer a small, representative trial using the exact proposed setup. Play/read/inspect the resulting sample and explain what was actually verified.

**Examples:** Studio captures ten seconds with current routes; Converter processes a representative input segment; Transcribe tries a chosen clip with names/language; a document export renders a representative page/table where practical.

**Keep it small:** “Try a sample” within the normal task, not another wizard. Cache a successful trial only for the configuration it actually tested.

**Acceptance**

- [ ] A sample does not replace the full result or alter the source.
- [ ] Input devices, formats and relevant settings match the eventual job.
- [ ] Sample limits are explicit; one successful page or clip does not prove the whole artifact.
- [ ] If the setup changes, earlier evidence is labelled stale.
- [ ] Every audition/preview has a nonvisual inspection path where meaningful.

**Existing overlap:** Studio preflight/rehearsal and other preview work. Integrate with those accepted plans.

### FUX-12 — Compare changes in a way people can actually inspect

**Moment:** “Is that improvement better, or just different?”

**Change:** A meaningful transformation offers a focused comparison using the same selected passage or media segment. Explain what changed and let the user keep either version.

**Examples:** Loudness/denoise audition, transcript correction with source playback, AI rewrite compared paragraph by paragraph, format conversion with metadata/loss warnings.

**Keep it small:** Add a comparison action to the existing result/preview. Avoid mandatory review after every trivial edit.

**Acceptance**

- [ ] Preserve original and proposed versions until the person decides.
- [ ] Repeated playback compares the same region without restarting the whole file.
- [ ] Explain level matching where an audio comparison would otherwise favor the louder result.
- [ ] Text changes have heading/paragraph/changed-item navigation and source references.
- [ ] State format loss, omissions and uncertain semantic judgments plainly.
- [ ] “Keep this” applies exactly the reviewed result, not a newly regenerated version.

**Existing overlap:** document comparison, Studio preview and Workbench before/after plans. Family adaptation is the improvement.

### FUX-13 — Be clear about live, downloaded, cached and unavailable

**Moment:** “Is this current? Will it still work when I lose internet?”

**Change:** Present the object's relevant freshness and availability as ordinary readable state, with a useful action.

**Examples:** “Forecast issued 40 minutes ago; update failed.” “Episode downloaded and playable offline.” “Station disconnected; reconnecting.” “Draft saved on this computer; not published.”

**Keep it small:** Extend existing status and details. No connectivity dashboard.

**Acceptance**

- [ ] Source/observation/retrieval times are distinguishable where they matter.
- [ ] Cached data is not represented as a current observation.
- [ ] Reconnect behavior does not replay a send, restart a recording or mark remote items read.
- [ ] Users can deliberately prepare selected media/documents for offline use.
- [ ] Storage/expiry behavior is discoverable and controllable.
- [ ] Weather retains official wording and configured warning policies; summaries do not substitute for the authoritative alert.

**Why it matters:** accurate ordinary state creates more confidence than elaborate “smart” recommendations.

### FUX-14 — Navigate meaningful structure, not just distances

**Moment:** “Take me to the next idea, chapter, speaker or finding.”

**Change:** Where structural metadata exists, let the person move through it with consistent interaction language: heading, chapter, speaker turn, marker, result, note or changed block. Clearly label model-generated structure.

**Keep it small:** Reuse each app's existing outline/list and the shared keymap/help conventions. Do not force every object into a new tree.

**Acceptance**

- [ ] Available structure is navigable and announced with name/type/position.
- [ ] Next/previous commands preserve expected playback/reading behavior.
- [ ] Distinguish timed transcript evidence from estimated alignment.
- [ ] Preserve navigation after edits where anchors can be remapped; explain otherwise.
- [ ] Never silently reassign established shortcut keys.
- [ ] Readable tables/lists accompany graphs, waveforms and visual timelines.

**Existing overlap:** document outlines, media chapters, transcript markers, Beacon and Workbench structure.

### FUX-15 — Keep maintenance away from the moment that matters

**Moment:** “I'm about to record. Please don't make me manage software.”

**Change:** Installation/update/component checks explain what the current task needs and defer disruptive maintenance when recording, dictation or important background work is active.

**Keep it small:** Improve current updater/runtime flows. No new family store or all-app installer requirement.

**Acceptance**

- [ ] Identify the affected app/component and the exact useful capability it enables.
- [ ] A download/update failure leaves user files and the current usable setup intact.
- [ ] No forced restart during protected work.
- [ ] Show progress and a usable retry without stealing focus.
- [ ] Shared-runtime compatibility and portable installations are respected.
- [ ] Update notes emphasize changed user behavior and stable learned controls.
- [ ] App availability respects current release gates; installing one app does not quietly install the family.

**Existing overlap:** shared runtime, installer, update and migration work. This is a user experience contract across it.

### FUX-16 — Turn a problem into a recoverable next step

**Moment:** “Something failed. I don't know whether to retry or start over.”

**Change:** Failure messages state the affected task, what was preserved, what is uncertain and one or two useful next actions. “Could not save to this folder. Your recording is still available. Choose another folder.”

**Keep it small:** Improve existing error language, Recent Problems and activity results. Keep diagnostic detail expandable.

**Acceptance**

- [ ] Preserve work before offering retry, alternate destination or export.
- [ ] Avoid “try again” when retry could duplicate a remote action.
- [ ] A support report can include versions and error context without sending private content by default.
- [ ] The user can inspect/redact included information and copy/save a report without sending it.
- [ ] Distinguish an unsupported feature, denied permission, unavailable dependency and transient failure.
- [ ] Return focus to a useful control after recovery.
- [ ] Confirm actual recovery; do not only dismiss the error.

**Existing overlap:** coded errors, stability/task management, recent problems and notification targets.

## 5. How these improvements should feel in each app

These are focused applications of the shared proposals, not commitments to add entire new subsystems.

| App | Meaningful improvement | What the person experiences | Scope caution |
| --- | --- | --- | --- |
| QUILL | Reading/review continuity with reliable comparison | Follow a source, annotate a passage, inspect a proposed revision and return to the exact place | Reuse editor focus/undo/notes; do not add a competing workspace shell |
| QUILL Lite | Start and resume with minimal ceremony | Open, write/read, find your place and recover a draft without being pushed through setup | Preserve its lightweight purpose; add discoverable depth only where needed |
| Radio | Stable browsing and understandable transport ownership | Favorites remain predictable; live connection/recording state is truthful; audio routes can be identified | Respect the accepted favorites-first surface and existing transport model |
| Cast | A queue that respects listening context | Resume the episode at its real position, know what is offline and inspect arrivals without losing the current item | Preserve user order/default actions; do not build an engagement feed |
| Player | Read/listen through meaningful structure | Reach a chapter/marker, compare a short segment and return to playback without hunting | Verify supported media/structure and product release status |
| Studio | A recording someone can verify independently | Rehearse exact sources, listen back, fix a route and start the long recording with evidence | Follow existing capture/preview/routing scope; do not equate a session mixer with a complete production engine |
| Converter | Results prepared for a chosen use | Choose a practical destination/profile, understand format changes, audition a sample and open finished outputs | Explain the preset's actual transformations; preserve originals; avoid a huge device-preset catalogue |
| Transcribe | Reliable target and source-linked corrections | Know where dictation will go; keep words if focus moves; jump from uncertain text to the relevant audio | Honor language/model availability and real timing evidence |
| Inkwell | Expansion that helps without surprising | Know when expansion is active, insert literally when intended and recover an unwanted expansion | Preserve privacy and target-app boundaries; avoid passive typing surveillance |
| Weather | Trustworthy current state and predictable alerts | Hear when information was issued, distinguish an update failure and rehearse the configured alert experience | Retain official warnings and user alert policy; no invented safety assurances |
| Beacon | Save a meaningful place and return reliably | Capture source plus selected location, reopen the right app, and understand when only a fallback was found | Reuse existing Universal Location Descriptor logic; no duplicate bookmark system |
| Social | Read at the user's pace and publish deliberately | New posts wait to be revealed; a draft's account/audience/attachments stay clear; partial publication is recoverable | Network capabilities differ; source/mock behavior is not proof of live acceptance |

## 6. Three family journeys worth making exceptional

### Journey A: “I heard something worth keeping”

1. Hear a useful episode or recording passage.
2. Save the exact location and an optional short note using the existing capture path.
3. Open it later from Beacon.
4. Continue in the appropriate media app at the verified place.
5. Open a related transcript or document without losing the origin.

**Delight:** one thought survives the movement between apps.

**Prove it:** interrupted playback, missing local media, changed source, offline use and a failed exact-location match are all understandable.

### Journey B: “I need to record something and trust the result”

1. Choose the recording sources already exposed by Studio.
2. Make a short rehearsal and inspect/listen to the captured result.
3. Start recording; see/hear honest progress without unnecessary interruption.
4. Finish with the file location and playable result.
5. If desired, hand the relevant file/range to Transcribe, then open the transcript in QUILL.
6. Convert or export a suitable deliverable with its provenance and limitations retained.

**Delight:** people can produce and verify their own work without relying on someone sighted.

**Prove it:** device loss, low disk space, partial export, absent destination app and interruption each preserve the usable artifacts.

### Journey C: “I have twenty minutes and want to continue”

1. Open the app and reach the last meaningful place with ordinary startup behavior.
2. New background results are available without displacing the current task.
3. Get a short situation explanation only when needed.
4. Do a useful piece of work.
5. Leave knowing whether the draft, position, recording or result was saved.

**Delight:** continuity feels natural; resuming does not become a setup task.

**Prove it:** changed files, unavailable accounts, multiple windows and large result sets do not break context or invent completion.

## 7. Where AI could earn its place

The AI connection and larger mission design remain in [complete.md](./complete.md). These family improvements should remain useful without AI.

| Appropriate addition | What must stay deterministic |
| --- | --- |
| Suggest chapter names or a brief recap of a user-selected passage | Source position, actual saved location and playback state |
| Explain a conversion choice in terms of the intended use | Actual codec/settings, output validation and file identity |
| Suggest a clearer paragraph while comparing it with the original | Which version was approved and exactly what is applied |
| Help turn a recording into an edited transcript and publication draft | Source boundaries, timestamps where verified, consent and publication actions |
| Explain a real error and suggest the next supported step | Preserved work, recorded error facts, actual retry/result |
| Adapt a tutorial explanation to the selected task | Commands available, permissions, keyboard paths and the user's progress |

- [ ] Keep the existing Ask/Choose Your AI/task infrastructure.
- [ ] Use the user's deliberately selected connection and supported capabilities.
- [ ] Clearly mark generated structure and uncertainty.
- [ ] Require no AI call for knowing the current window, target, file, task status or audio route.
- [ ] Keep private drafts/media out of model context unless needed and authorized.
- [ ] Do not expand this UX plan into another generic chat product.

## 8. Interaction contracts to apply across every pilot

### Keyboard, focus and speech

- Stable tab order, visible focus and accessible names/descriptions.
- Type-ahead and text editing keep their established meaning.
- Restore focus to the originating control after dialogs.
- Background updates do not steal focus or interrupt reading.
- Speak only outcomes the screen reader does not already communicate; retain discoverable full detail.
- Respect the established sound/speech/both/silent behavior and error policies.
- Every essential state is available as text and through braille; sound and color are supplementary.
- Choose new keys only after checking existing family/app bindings, aliases and assistive-tool conflicts.
- Treat keyboard-only, screen-reader, braille, magnification and high-contrast use as normal task paths.
- Keep web/help/exported HTML at WCAG 2.2 AA; native behavior also needs platform/manual validation.

### Identity, changes and confidence

- Name the relevant object, account/destination and actual result.
- Distinguish local draft, prepared change, processing, saved output and remotely published state.
- Use confirmations at meaningful consequence boundaries; routine safe actions should not be slowed by warnings.
- Show unavailable actions with useful explanations according to each app's existing surface rules.
- Respect stored user choices and current release gates.
- Preserve originals/drafts and state recovery limits honestly.
- Keep local defaults local unless the user chooses the narrow supported sharing path.

### Performance and durability

- Immediate control response; long work is cancellable and visibly/textually active.
- Bound large lists, histories and caches without silently losing meaningful work.
- Separate media/documents from caches and configuration.
- Version and preserve shared data, including unknown fields used by a newer sibling app.
- No new telemetry service is needed to observe usability improvements.
- Do not infer behavior in real receiving applications or frozen builds from unit tests alone.

## 9. What I would deliberately leave out

These are design recommendations to keep the scope useful.

- A required family dashboard, new home app or launcher before someone can use an installed product.
- A second universal notification/history/task centre overlapping existing notices, recent problems and activity.
- Automatically rearranged menus, renamed familiar controls or continually changing default actions.
- A new panel/button for every useful command; prefer existing menus, context actions, status and help.
- Mandatory account creation or cloud synchronization to listen, read, write, convert or use local tools.
- A “smart” default that silently changes audio destinations, publication accounts, dictation targets or billing.
- Large settings migrations in the name of consistency; share only behavior that truly means the same thing.
- Streaks, badges, engagement reminders or dashboards that reward time spent.
- An AI approval ceremony for ordinary reads and harmless local actions.
- Animations, decorative sound or welcome messages that slow real work or compete with a screen reader.
- A claim that all companions are shipped because their source exists.
- Replacement of an app's useful personality with one compulsory layout.

## 10. Delivery order

| Stage | Scope | Exit |
| --- | --- | --- |
| A: observe | Watch a small set of real tasks in the current packaged builds; audit existing features | Evidence of friction and a baseline; avoid implementing an already solved behavior again |
| B: prove the basics | FUX-04 results and FUX-06 stable lists in two appropriate apps | Clearer completion, fewer lost selections and no added modal steps |
| C: continuity and input | FUX-01 resume and FUX-07 intended target | Useful work retained through interruptions and real receiving-app scenarios |
| D: verify media | FUX-03 audio clarity plus FUX-11 rehearsal and FUX-12 comparison | Independently verifiable recording/listening tasks |
| E: connect the family | FUX-02 handoff and FUX-14 structure | Two real cross-app journeys with correct return/context and missing-app recovery |
| F: simplify the rest | Settings, first-task guidance, contextual help, freshness and maintenance | Remove redundant controls/prompts; preserve learned behavior |

Roll out in the shared layer when semantics match. Keep app-specific behavior where it matters. Social and independently packaged/migrating apps may need adapters rather than assumptions about a common shell.

### For each pilot

- [ ] Identify the existing implementation/accepted requirement and the precise remaining gap.
- [ ] Record one realistic before/after task.
- [ ] Define the proposed control/command and what gets simpler.
- [ ] Name supported app/build/platform boundaries.
- [ ] Specify failure, cancellation, restart and multi-window behavior.
- [ ] Observe keyboard/screen-reader users and at least one relevant braille/scaling path.
- [ ] Run meaningful checks for any implementation changes; document actual manual results.
- [ ] Update help/examples and remove stale directions.
- [ ] Confirm that the improvement does not add a mandatory step to the everyday path.
- [ ] Accept, revise or drop the proposal on evidence.

## 11. How we will know it helped

Use local pilot notes and consenting participants; this plan does not require passive usage tracking.

| Measure | What to observe |
| --- | --- |
| Completion | Can the person finish the task independently? |
| Resume effort | Time/actions needed to regain the original passage, item or task |
| Focus stability | Unexpected selection moves, lost place and focus recovery |
| Trust | Can the person accurately say where text, audio and files are going? |
| Recovery | Does failure preserve work and lead to a successful next action? |
| Discoverability | Can a new user find the useful action without memorizing the manual? |
| Speech/braille burden | Duplicate speech, interruptions, excessive row length and missing state |
| Effort | Dialogs, keypresses, decisions and avoidable context switches |
| Practical benefit | Does the improvement solve a recurring problem rather than merely impress in a demo? |

Set numerical acceptance targets after measuring the current behavior. Test first-time and experienced users separately: a useful explanation for the first session can become noise in the hundredth.

## 12. Decisions for Jeff

These are prioritization decisions for later; they do not block producing this document.

1. Choose two packaged-app pilots and the real users/tasks to observe.
2. Confirm whether to start with truthful results/stable lists or a more urgent observed lost-work/input issue.
3. Choose one cross-app journey to make exceptional before adding more handoff types.
4. Confirm the shared behavior boundaries, especially audio ownership, preferences and target-app text insertion.
5. Promote only the accepted proposals into the relevant product PRDs and release backlogs.

**My recommendation:** start by making the family dependable at the transitions—between tasks, between apps, between devices, and between a command and its result. That is where a small change can make the whole family feel more thoughtful.
