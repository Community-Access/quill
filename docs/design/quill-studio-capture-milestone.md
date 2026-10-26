# QUILL Studio: screenshot milestone and ecosystem review

Date: 2026-10-26. Status: implementation and verification ledger, not a release announcement.

## Agreed sequence

The consolidated QUILL Studio PRD supplied for this work is the design baseline. The user's immediate order takes precedence over the broad phase numbering: preserve the existing application, rename it, complete a useful screenshot/AI/verification journey, then build a recorded video demonstration with optional audio in small increments.

The rename is committed on local main as `529884ec`. Capture work is developed separately. No release was published, no installed application was overwritten, and the target version is 2.0.0, renumbered from the unpublished 2.2.0 build at the user's request.

## Ecosystem boundaries examined

- **Studio shell:** [shared application](../../quill/apps/studio.py), [native audiobook UI](../../quill/ui/audio_studio/), library tree, initial focus, F6 status, tray, command palette, app preferences, update lookup and lifecycle. New capture commands enter through a separate mixin; the old journeys remain.
- **Audiobook state:** [library, history, queue and book preferences](../../quill/core/audio_studio/), and [job files](../../quill/core/speech/job_file.py). Existing paths, stable identifiers, job format and voice configuration are retained. Capture does not migrate books or create a second audio engine.
- **Shared speech and media:** [speech](../../quill/core/speech/), [audio](../../quill/core/audio/), [media](../../quill/core/media/), and publishing. Editor, Studio, Radio, Cast, Converter, Player and Transcribe use shared services in this package. Screenshot work neither records audio nor changes output devices or routing.
- **Existing visual services:** [screen capture](../../quill/platform/windows/screen_capture.py), [local OCR](../../quill/io/ocr.py), [vision transport](../../quill/core/ai/vision.py), [vision prompts](../../quill/core/ai/vision_prompts.py) and [Editor image commands](../../quill/ui/main_frame_image.py). Studio reuses these services and the configured provider's credential storage; it does not deploy a separate model.
- **Accessibility and reliability:** [announcement service](../../quill/core/announce/), [application shell](../../quill/ui/app_shell.py), dialog contracts, context help, [task manager](../../quill/stability/task_manager.py), atomic storage, cancellation and UI-lifetime guards. All new controls are native wx controls with text equivalents; image interpretation is never the only way to inspect file evidence.
- **Global keyboard services:** [shared registration and dispatch](../../quill/ui/main_frame_hotkeys.py), [hotkey manager](../../quill/ui/global_hotkeys_dialog.py), app keymaps, and family chord inventories. Studio's capture allowlist excludes arbitrary editor commands and does not take QUILL's show/hide key. Inkwell's existing hooks remain independent.
- **Companion apps:** Beacon's browser-content capture bridge is a different workflow and is not used as a screenshot upload channel. Social and other standalone wrappers are not imported into the Studio UI. Cross-app exchange continues through shared services and saved assets.
- **Packaging:** [standalone Studio](../../standalone/studio/), [native launcher registry](../../scripts/build_native_launcher.py) and [runtime application registry](../../quill/core/runtime_apps.py). The installer AppId, runtime ref id, application identity, executable/package names, release filenames and shared profile are intentionally stable. New display branding is not a second product installation.

## Implemented screenshot path

Capture offers named visible windows, individual displays, the full virtual desktop, an active window after a delay, and a rectangle entered as physical-pixel coordinates. Negative monitor coordinates are supported. Window labels include their title and process identity. Minimized windows require restoration. Refresh preserves target identity; a disappeared window does not silently become a desktop capture.

Named windows use the window-handle backend. Display topology and window process identity are rechecked. Target loss, a disconnected display, invalid bounds, capture errors and incorrect rectangle dimensions are failures rather than reasons to broaden the capture. Protected or GPU-rendered content may still be blank despite a successful API call; uniform pixels are reported as evidence, not treated as proof of privacy or success.

Screenshots receive unique PNG filenames. The image is reopened, fully decoded, measured and SHA-256 hashed. Verification reports are saved as JSON and readable Markdown. Clipboard copy and description export are explicit actions. Saved PNGs can be reopened for inspection.

## AI and conversation

Seven screenshot-specific prompt styles cover orientation, controls, text/errors/tables, framing problems, possible sensitive information, alt text and charts. The existing image prompt library remains available, including user-defined prompts. A user may edit the instructions and ask an independent question. Responses arrive asynchronously into the same native conversation window, without replacing the selected screenshot. Follow-ups use the same verified image snapshot and prior observations.

**Configured AI providers.** Screenshot AI uses QUILL's shared AI connection settings, model selection, provider-specific credentials and vision transport: OpenAI, Google Gemini, Anthropic Claude, OpenRouter, Ollama (local or cloud), and compatible custom endpoints. Select the provider and an image-capable model through the shared AI setup. Studio does not require Ollama or maintain a separate provider configuration. Provider/model image support still applies; a text-only model cannot inspect screenshots. Changing the connection pauses previously approved automatic uploads.

Manual AI requests require approval naming the effective provider, model and endpoint. Local OCR does not send an image to AI. Safe Mode and the global AI switch block AI while allowing local capture and verification. Confidence is shown only when the OCR backend supplies it; unavailable confidence is not invented.

Automatic AI is off by default. Enabling it requires separate approval covering future user-triggered screenshots, including desktop captures. Consent is tied to the effective provider/model/endpoint. Changing that connection pauses automatic inspection. The saved automatic prompt can be updated explicitly. Permission, cancellation and the global AI switch are rechecked before a queued upload. Disabling automatic mode does not recall a request already sent.

Each AI request uses a private temporary copy whose bytes match the reviewed screenshot hash. It does not recapture the screen or accidentally substitute the user's newly active window. Temporary copies are removed on success or failure. AI findings remain unverified observations in exported reports.

## Global screenshot hotkeys

The Capture menu exposes a native global-hotkey manager for active-window capture, full-desktop capture, repeating the last selected target and cancelling a pending capture. Global capture keys are opt-in and configurable. Registration failures are reported, and only successfully registered keys dispatch. Registration is removed on exit. Immediate capture does not restore Studio before determining the active target.

The ordinary in-app capture shortcuts are distinct from system-wide registration. No short key is silently claimed from another application by default. Real screen-reader and other-application conflicts still require the acceptance run below.

## Objective checks and remaining release gates

Automated checks cover saved-byte hashing and decode, corruption, replacement after review, stale window identity, disconnected displays, invalid/negative rectangles, window-backend selection, consent refusal, Safe Mode, global registration failures, editable prompt/question flow and image-grounded follow-ups. An opt-in Windows integration test creates its own native window, selects it by handle, captures it and checks expected pixel content. It captures only the fixture window.

The rename also passed runtime/launcher identity, version consistency, legacy context-help and installer-identity checks. Existing library/resume and narration-wizard regressions were exercised. These checks are evidence of source behavior, not a claim that an installed upgrade was tested.

Before release, complete and record:

1. JAWS, NVDA, Narrator and braille: source selection, numeric region, errors, conversation review, typing during responses, close/Escape focus return and global keys from another application.
2. Actual mixed-DPI/multiple-monitor hardware, protected windows, GPU content, remote desktop and display disconnect while a capture is pending.
3. Installer upgrade, rollback and portable runs with old books/jobs/voices; native launcher compilation and shortcut cleanup on both installation scopes.
4. A user-approved live vision-provider run, supported-model errors, offline behavior, latency/cost review and long conversations. Automated tests use provider doubles and do not upload the user's desktop.
5. Windows OCR availability and recognition quality on representative real applications. OCR semantics and keyboard operability cannot be proved from image pixels.
6. Resource measurements on the required 8 GB baseline and review of all accessibility/manual-verification comments.

## Explicitly later work

This slice does not close every CAP/VIS/VERIFY requirement in the full PRD. UIA-element capture, scrolling/sequence capture, redaction/annotation editing, visual zoom/crop editing and screenshot comparison remain separate work. Video recording, microphone/system/process audio routing, privacy isolation, rehearsal and audiovisual export verification are the next production milestone. No AI claim turns those pending checks into a verified result.

## Engineering reference research

[ZoomIt documentation](https://learn.microsoft.com/en-us/windows/powertoys/zoomit) provides useful references for scrolling capture/OCR, zoom and annotations, DemoType, DemoMirror, webcam overlays, recording and post-recording trimming. The [Windows source](https://github.com/microsoft/PowerToys/blob/main/src/modules/ZoomIt/ZoomIt/Zoomit.cpp) identifies its license as MIT, and the [PowerToys license](https://github.com/microsoft/PowerToys/blob/main/LICENSE) requires preserving notices when code is reused. The [Mac source](https://github.com/microsoft/Zoomit-Mac) is also useful for capture lifecycle, accessibility and platform-specific permission research.

No ZoomIt code or binary has been incorporated in this screenshot slice. Reuse decisions must identify the exact upstream revision, per-file and dependency licenses, retained notices, native-helper boundary and tests. User-facing Studio workflows remain native tasks rather than referrals to an external production application.

The [Pillow API](https://pillow.readthedocs.io/en/stable/reference/ImageGrab.html) documents selected-window and multi-monitor still capture. [Windows Graphics Capture](https://learn.microsoft.com/en-us/windows/apps/develop/media-authoring-processing/screen-capture) is a candidate for the later video-session backend; it has not been implemented by this slice.
