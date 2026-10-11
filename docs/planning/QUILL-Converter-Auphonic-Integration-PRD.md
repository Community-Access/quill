# Quill Converter + Auphonic Integration -- MVP Product Requirements

**Status:** Proposed; not implemented  
**Date:** October 5, 2026  
**Scope:** Optional, multi-file audio post-production through the user's own
Auphonic account

## 1. Product summary

Add a small, explicit Auphonic workflow to Quill Converter. A user selects
local audio files and chooses whether to process them as separate productions
(one per file) or as one multitrack production (one file per track, in queue
order). The user chooses the account's default settings or a saved preset,
reviews one confirmation for the whole submission, and lets Auphonic process
the files. Quill Converter reports progress and saves the resulting audio
file or files locally without changing the sources.

This is an opt-in online service, separate from the existing local Convert
workflow. Local conversion remains the default and continues to work without an
account or network connection. Nothing is uploaded by opening the app, checking
an account, selecting a preset, or adding a file to the queue.

The first release intentionally exposes the Auphonic service's existing
account presets rather than inventing a new processing interface. Named QUILL
recipes, custom signal-processing controls, and content-generation features
are future work.

## 2. Repository context and implementation direction

- The released Converter is a local-first app with an explicit requirement that
  conversion does not upload media. Its existing behavior and packaging are
  described in [the Converter product requirements](../../standalone/converter/docs/prd.md).
- QUILL already has a wx-free Auphonic simple-API client in
  [`quill/core/publish/auphonic.py`](../../quill/core/publish/auphonic.py).
  It supports account and preset lookup, a single-file upload, production
  status polling, and result downloads.
- The Audio Studio's Publish dialog already provides a user-entered Auphonic
  API token, account/preset lookup, an upload confirmation, background
  progress, cancellation, and result downloads in
  [`quill/ui/audio_studio/publish_dialog.py`](../../quill/ui/audio_studio/publish_dialog.py).
- The API token is stored in Windows Credential Manager using the existing
  `CREDENTIAL_TARGET`; it is not a QUILL setting. The Converter integration
  should reuse this credential and client rather than add a second token store,
  duplicate HTTP implementation, SDK, OAuth flow, or OAuth broker.
- The Auphonic call site is already documented in the network-egress inventory.
  Any new or moved call site must remain covered by that audit.
- The existing client currently starts a production with one uploaded file.
  Multitrack mode requires extending that same service client and verifying
  Auphonic's supported multitrack API contract; it must not be approximated by
  submitting the tracks as separate jobs.
- The Simple API also exposes a limited set of processing options directly,
  including adaptive filtering, leveling, loudness normalization, noise
  reduction, and automatic cutters. The JSON API supports explicit output-file
  configuration and multitrack algorithms. The MVP should expose only a small
  plain-language subset of these capabilities.

This proposal is a scoped exception to the released Converter's
no-media-upload requirement, not a change to the existing conversion behavior.
Until this feature is implemented and released, the shipped app remains exactly
as currently specified: local conversion only.

## 3. Users and problem

The target user has one or more audio recordings that would benefit from
Auphonic post-production and wants to submit them without navigating a
visually complex web workflow. The user may rely on a keyboard and screen
reader and needs to know exactly what will be sent, which account, preset, and
basic processing choices will be used, how each job is progressing, and where
results were saved.

## 4. Goals

1. Offer a straightforward, accessible path from selected queued audio files
   to either separate Auphonic productions or one multitrack production.
2. Reuse the user's own Auphonic account, saved credentials, and saved presets.
3. Make every media upload an informed, explicit user action.
4. Keep processing and downloads off the UI thread, cancellable where the
   service permits, and understandable by screen reader.
5. Save results as new local files; never replace, modify, or delete the source.
6. Keep the first implementation narrow enough to build on the current client.

## 5. MVP scope

### 5.1 Entry point and input

- Add a keyboard-reachable **Process with Auphonic...** command to the
  Converter, available from the selected queue items and an appropriate menu
  or command-search surface.
- Accept one or more queued, existing audio files when no other Converter task
  is running. Reject video files and files containing video streams, even if
  they also contain audio. Use the existing media probe and audio format
  knowledge where possible.
- If a selection contains unsupported or ineligible files, skip those entries
  and identify them before confirmation; process the eligible audio files.
  Block submission if no eligible files remain.
- Let the user choose one of two modes:
  - **Separate productions:** create one production per eligible input file,
    using the same selected preset for every file in the batch.
  - **One multitrack production:** make each eligible file one track. Track
    names default to the filenames, and track order follows the Converter
    queue. Use one preset for the multitrack production.
- Multitrack mode requires the minimum number and types of tracks accepted by
  Auphonic. Validate these constraints before upload and explain any
  ineligible selection.
- In multitrack mode, default the production title and result-folder name to
  the first eligible track's filename; allow the user to edit the title before
  submission.
- Finalize the accepted input-format list against Auphonic's current API
  behavior during implementation. Unsupported, unreadable, or zero-length
  inputs must fail before upload with a speakable explanation.
- Do not accept folders, playlists, URLs, or video/multitrack source projects
  in this first release. Multitrack mode means multiple ordinary audio files
  submitted as separate tracks.

### 5.2 Account and preset

- Use the existing Auphonic API-token credential. If it is not available,
  provide a secure password-style token entry with a link or plain-language
  direction to obtain the token from Auphonic.
- Allow the user to check the account and load its saved presets without
  uploading media.
- Offer the account's default preset and the user's saved presets. A separate
  production batch uses one preset for all its jobs; multitrack mode has its
  own single preset choice. Show the account name and available credits when
  returned by the API; do not imply that QUILL can estimate the final charge
  unless Auphonic supplies a reliable estimate.
- Reuse the existing Windows Credential Manager target. Never write the token
  into `converter.json`, another settings file, a log, a report, or a
  diagnostics bundle. Follow the existing credential-save behavior and make
  any decision to remember a newly entered token clear to the user.
- Preset/account errors must be visible and actionable. Do not silently use a
  default preset after a failed lookup.

### 5.3 Basic processing and output

- Keep the default workflow small and plain-language: preset, a compact
  **Basic processing** group, and one output-format choice. Do not display
  raw API fields, LUFS values, or DSP terminology on the main surface.
- Offer two processing modes:
  - **Use preset settings** (default): use the selected Auphonic preset as-is.
  - **Quick cleanup**: enable Auphonic adaptive filtering, adaptive leveling,
    and loudness normalization using Auphonic's service defaults.
- In Quick cleanup, provide an optional **Reduce background noise** switch,
  off by default. Use automatic noise reduction; do not expose reduction
  amounts or individual denoising algorithms in the MVP. Explain that it may
  change quiet background sounds.
- Allow one output-format choice per production: **Use preset outputs**
  (default) or one verified format. Initial candidates are MP3, WAV, FLAC,
  AAC, and Opus; finalize the list against Auphonic and the result downloader.
  Multiple custom formats, bitrate, sample rate, and multitrack stem export
  are out of scope for the first implementation.
- When a format is selected, request it explicitly through Auphonic's
  production API. For multitrack, download the final mixdown only.
- For separate-file productions, pass through source title, basic available
  tags, and chapter marks where the input reader and Auphonic API support
  them. Do not add metadata or chapter-editing controls to the basic surface.
  In multitrack mode, use the editable production title and do not combine
  chapter marks or other metadata from separate tracks.
- Keep processing mode, noise-reduction choice, output format, and metadata
  behavior clear in the batch confirmation. Any override of the selected
  preset must be stated plainly.

### 5.4 Confirmation and upload

- Show one accessible confirmation for the entire submission naming:
  - Auphonic as the external service;
  - the eligible files and any skipped files;
  - whether this will create separate productions or one multitrack production;
  - the selected account preset(s) or account default;
  - the processing mode, optional noise reduction, and output format(s);
  - for multitrack, track names/order and the production title;
  - that the media will be uploaded and processed using the user's Auphonic
    account and credits;
  - the destination folder for downloaded results.
- Canceling this confirmation makes no upload request for any selected file.
- Do not upload the file as part of account checks or preset loading.
- Use HTTPS with normal certificate verification, bounded timeouts, and the
  existing Auphonic client. No credentials or media content may be written to
  logs.
- Auphonic processing is unavailable in Safe Mode.

### 5.5 Progress, cancellation, and failures

- Run account calls, upload, status polling, and downloads on the existing
  background-task infrastructure; all widget changes return to the UI thread.
- Run separate productions sequentially, one at a time; do not submit the
  whole batch concurrently.
- Show and announce the current filename or production, overall batch progress,
  upload progress, Auphonic processing, result download, per-item outcome,
  final summary, cancellation, and failure. Keep progress available in the
  Converter status surface while the window is minimized.
- Poll production status at a polite interval with an overall timeout. A
  failure for one separate production must be recorded and reported, then the
  batch continues with the remaining files. Report a service-reported failure
  as a failure, not as an empty successful result.
- Stopping during upload aborts the current upload when possible and prevents
  later files from being submitted. For any production already accepted by
  Auphonic, stop local polling/download and explain that the remote production
  may continue. Keep its minimal job record so the user can resume it later.
- A timeout or network failure must identify the phase that failed and tell
  the user whether the upload or remote production may already have started.
  Do not offer a blind retry that could create a duplicate production.
- Keep the UI responsive throughout. Do not block shutdown without an explicit
  user-facing choice.

### 5.6 Results and local files

- Save returned audio results under the Converter's selected output directory;
  when none is set, use its normal default destination. For separate jobs, put
  each file's results in its own source-named subfolder. For multitrack, use a
  folder named after the editable production title.
- Never overwrite an existing file, the source, or files outside the chosen
  output location. Validate returned filenames and download destinations
  before writing. Use safe, collision-resistant names and clean up incomplete
  downloads after cancellation or failure.
- The MVP downloads supported audio result files only. If the service returns
  other artifact types, leave them out and say how many were not downloaded;
  do not imply that transcripts, captions, or reports were saved.
- On success, announce the number and location of files and offer to open the
  output folder using the Converter's existing behavior. The final batch
  summary lists each input's outcome and any skipped items.
- Persist only the minimum local state required to resume accepted productions
  after Converter exits. Store the Auphonic production ID, mode, input display
  names/track order, preset label, output location, and enough batch state to
  report outcomes. Do not persist credentials or media contents. Use the
  repository's atomic-write and recovery conventions.
- On the next launch, show pending Auphonic work and offer an explicit
  **Resume** action. Do not contact Auphonic automatically at startup.
- Remove a pending record after its result has been downloaded and reported,
  or after the user explicitly dismisses it. Do not build a full completed-job
  history in the MVP.

## 6. Accessibility and interaction requirements

- Every new control has an explicit accessible name and useful F1 help.
- All functions, including account setup, preset selection, confirmation,
  progress, cancellation, and result review, are usable by keyboard.
- Every menu item follows Converter's menu-accelerator policy: show a working,
  non-conflicting keyboard route, and make the route discoverable in Keyboard
  Shortcuts and command search.
- Modal surfaces use the Converter host's accessible dialog contract, with
  explicit affirmative/cancel actions, Escape behavior, deterministic focus,
  and focus return.
- Announce action outcomes and meaningful background state changes only; do
  not repeat control names, focus announcements, or other information the
  screen reader already supplies.
- Show long status and error details in a reviewable text surface rather than
  relying only on transient speech or visual progress.

## 7. Privacy, security, and network policy

- Local conversion remains local. Auphonic is a distinct, optional network
  operation initiated by an explicit command and confirmed for each
  batch or multitrack production.
- Disclose that the selected media is sent to Auphonic, is processed under the
  user's Auphonic account, and is subject to Auphonic's own handling and
  retention terms. QUILL must not promise deletion or retention behavior it
  cannot control.
- Do not contact Auphonic automatically at startup, on queue insertion, or
  while a dialog opens. An account check is a separate, user-initiated request
  and must never upload media.
- Pending jobs discovered at startup are displayed without network access.
  Polling or downloading resumes only after the user chooses **Resume**.
- Use the existing credential store and reviewed network client. Never include
  the API token, authorization header, media bytes, or sensitive file content
  in logs or support diagnostics.
- Restrict result URLs and filenames to the expected HTTPS/API response
  contract; reject unsafe schemes, unexpected hosts, path traversal, and
  writes outside the output directory.
- Keep the existing three network paths and privacy statements accurate by
  updating the Converter requirements, network-egress audit, Safe Mode tests,
  and user-facing disclosure when implementation begins.
- No telemetry, QUILL-hosted proxy, QUILL-paid processing, or third-party
  account creation is part of this feature.

## 8. Explicit non-goals for the MVP

- OAuth, browser sign-in, client secrets, or a QUILL OAuth broker.
- Advanced processing controls such as custom LUFS/true-peak targets,
  denoising strength/method, reverb or breath reduction, speech isolation,
  per-track algorithm settings, and preview-before-upload.
- Automatic silence, filler, cough, or music cutting; these can remove or
  alter source content and need a separate accessible review design.
- Transcription, captions, translation, diarization, generated chapters,
  show notes, audiograms, publishing, and QUILL Cast workflows.
- Video input/processing, URL input, folder recursion, multitrack stem export,
  and multiple custom output formats per production.
- Completed-production history, webhooks, or notifications after the app has
  closed. Minimal active-job persistence and explicit resume are in scope.
- A new HTTP dependency, generalized online-services framework, or changes to
  the local FFmpeg conversion engine.

These capabilities may be considered after the MVP is shipped and evaluated;
they are not implied by acceptance of this PRD.

## 9. Acceptance criteria

1. Multiple eligible audio files can be submitted either as sequential
    one-production-per-file jobs with one shared preset, or as one multitrack
    production with filename-based track names and queue order. The account
    default and saved presets are available.
2. Account and preset checks work without uploading a media file.
3. One confirmation covers all eligible files, skipped files, mode, preset,
    and destination; canceling it produces no upload request.
4. The existing token is reused across the Audio Studio and Converter, and a
   new token is never written to Converter settings or logs.
5. Separate productions run sequentially; a failed file does not prevent
    remaining eligible files from processing, and the final report identifies
    every success, failure, and skipped file.
6. Upload, remote processing, and download run without freezing the UI and
    expose accessible per-job and overall progress and outcomes.
7. Stopping prevents unsubmitted files from starting and clearly explains that
    an accepted Auphonic production may continue remotely.
8. Accepted jobs survive app restart as minimal local records. Startup does not
    contact Auphonic; choosing **Resume** does. Successful resume downloads the
    result and clears the pending record.
9. Successful jobs save only supported audio result files to their designated
    output folders, never overwrite existing files, and leave the sources
    unchanged.
10. Failed, timed-out, malformed, or cancelled operations are reported as
     such; incomplete output files are not presented as successful results.
11. Ineligible selected files are skipped and identified before confirmation;
     no upload proceeds if there are no eligible files or the multitrack
     selection is invalid.
12. Users can retain the selected preset's processing or choose Quick cleanup;
     the optional noise-reduction switch is off by default. A verified output
     format can override the preset outputs, and the confirmation describes
     those choices.
13. Separate-file productions pass through available basic source metadata
     and chapter marks where supported; multitrack productions do not merge
     metadata from their tracks.
14. The feature is unavailable in Safe Mode, and no Auphonic request occurs
     without the corresponding explicit user action.
15. Keyboard-only and screen-reader acceptance covers account setup, both
     modes, queue-order track review, preset choice, batch confirmation,
     upload, waiting, stop, restart/resume, error, success, and opening the
     result folder.
16. Tests cover single-file and multitrack client workflows, basic processing
     and output selection, metadata/chapter pass-through, batch sequencing and
     continue-on-failure, egress/audit registration, token and job-state
     persistence boundaries, confirmation-before-upload, safe result paths,
     explicit resume, and Converter UI behavior without live credentials.

## 10. Success measures

- A first-time user can complete either a separate-file batch or a multitrack
  production, choose basic processing and output options, and save results
  without using Auphonic's web interface or a mouse.
- A returning user can reuse the saved credential and preset choice without
  re-entering a token.
- In usability testing, participants can tell before upload which file,
  account, preset, and credit source will be used, and after processing where
  the results were saved.
- No network call is made by local conversion or by merely opening/checking
  the Auphonic UI.

Do not add product telemetry to measure these outcomes.

## 11. Delivery sequence

1. **Contract and safety:** verify Auphonic's separate-file and multitrack API
   behavior, basic algorithm overrides, supported output formats, metadata
   and chapter pass-through, track limits, result metadata, polling,
   cancellation, restart behavior, and download URLs; update the egress
   inventory and define safe result-file handling.
2. **Account and selection:** reuse the existing credential, account check,
   saved-preset list, queue-order track model, and audio eligibility rules.
3. **Production lifecycle:** implement one batch confirmation, basic
   processing/output choices, sequential separate jobs, multitrack
   submission, continue-on-failure reporting, metadata/chapter pass-through,
   minimal atomic job persistence, explicit resume, result downloads, and
   accessible progress/errors.
4. **Release readiness:** update the Converter's product requirements,
   user guide, help text, Safe Mode, persistence, and network tests, plus
   packaging/release notes; verify manually with NVDA or JAWS and a real
   Auphonic test account.

Do not begin later-phase features until these acceptance criteria pass and the
MVP has been evaluated.

## 12. References

- [Initial Auphonic integration proposal](../../quill-auphonic-integration-proposal.md)
- [Current Quill Converter product requirements](../../standalone/converter/docs/prd.md)
- [Existing Auphonic API client](../../quill/core/publish/auphonic.py)
- [Existing Audio Studio Auphonic workflow](../../quill/ui/audio_studio/publish_dialog.py)
- [Auphonic Simple API](https://auphonic.com/help/api/simple_api.html)
- [Auphonic JSON API production details](https://auphonic.com/help/api/details.html)
- [Auphonic multitrack API](https://auphonic.com/help/api/multitrack.html)
