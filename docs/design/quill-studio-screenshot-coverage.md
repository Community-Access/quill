# QUILL Studio screenshot requirements: coverage and remaining work

Audit date: 2026-10-26. Target application version: **2.0.0**. This is an implementation audit, not release certification.

## Answer and scope

**The screenshot requirements in both source PRDs are not yet complete.** The implementation provides a useful first capture-and-inspection journey. It does not yet pass the expanded PRD's GATE-08, which requires keyboard UIA-control capture, OCR, a numbered annotation, and image plus evidence export.

This audit examines the user-supplied `QUILL_Studio_PRD.md` and `QUILL_Audio_Studio_Expanded_PRD.md` in the main checkout. The former consolidates the latter; their requirements remain visible below rather than being reduced to the smaller first milestone. The user's later instructions authorize configurable screenshot hotkeys, rich editable/custom prompts, any configured image-capable provider, and explicitly approved optional automatic AI. Those instructions supersede the older blanket ban on automatic uploads; they do not authorize unconsented sharing.

The implementation is on branch `agents/continue`, whose initial screenshot milestone is commit `4b385a57`; the rename is commit `529884ec`. The main-checkout changelog the user linked does not include the branch's screenshot feature entries at audit time. Read the [branch changelog](../../standalone/studio/docs/CHANGELOG.md) for implemented behavior. No screenshot release has been published.

Status terms: **Partial** means working pieces exist but the whole requirement is not satisfied; **Pending** means no delivered end-to-end workflow; **Unverified** means implementation or research exists but required outcome evidence is missing. An automated test passing does not substitute for blind-user acceptance.

## Consolidated capture requirements

| Requirement | Status | Present behavior and remaining work |
|---|---|---|
| CAP-001: capture modes and metadata | Partial | Named visible window, active window, display, full desktop, guided portions, optional exact rectangle, one-shot delay, PNG, clipboard copy and source/hash/time evidence exist. UIA element, semantic logical region, scrolling capture, timed sequences and actual scale-factor evidence remain. A single delay is not a sequence. |
| CAP-002: Screenshot Inspector | Partial | Dimensions, selectable local OCR, available engine confidence, editable prompts, grounded follow-ups, image copy and description export exist. Missing structured element/position list, guaranteed OCR reading order, independent clipping/overlay checks, comparison, semantic target search, keyboard zoom/crop and redaction. AI suggestions are not those tools. |
| CAP-003: annotations and presentation tools | Pending | No keyboard annotation objects, anchoring/revalidation, verbal preview, layering, magnification, pointer/focus highlight, break timer or spoken countdown. |
| CAP-004: integrated capture workspace | Partial | Native menu, command palette, in-app accelerators, opt-in global keys, capture delay, local OCR, AI inspection and PNG clipboard copy exist. Missing persistent named workspaces, recording, zoom/annotation, image resizing/conversion and broader clipboard transformations. |
| CAP-005: Capture and Dictate | Pending | No screenshot-plus-dictation/transcript package or issue-tracker/HTML export journey. Existing transcription elsewhere in QUILL does not complete this workflow. |
| CAP-006: comprehensive preflight | Partial | Invalid bounds, changed monitor topology, closed/minimized windows, changed window process and moved/resized guided-region source fail explicitly; uniform pixels and API limitations are recorded. Missing independent checks/corrections for occlusion, overlays, pointer obstruction, notifications, masking, unexpected titles and semantic completeness. |

## Visual inspection requirements relevant to screenshots

| Requirement | Status | Present behavior and remaining work |
|---|---|---|
| VIS-001: understand on-screen content | Partial | Saved/reopened PNGs and newly captured windows/regions can be inspected with OCR or shared AI. No combined UIA/OCR/vision pipeline or unified live/window/webcam/video-frame command. |
| VIS-002: layered structured answers | Partial | Rich presets request scene, text, controls, quality, privacy and chart explanations. Replies are selectable text; structured navigable result layers, measured boxes and contrast calculations remain. A model inventing a location is not measured evidence. |
| VIS-003: artifact-grounded conversation | Partial | Requests verify the same image hash, use an immutable temporary copy and retain prior conversation for follow-ups. Source evidence is recorded for new captures. Video frame references and cross-image comparison remain; reopening an image does not guarantee restoration of all original source metadata. |
| VIS-004: deterministic evidence before interpretation | Partial | Full image decode, nonzero dimensions, SHA-256, bounds and source identity checks exist. No UIA intersections, exhaustive text/completeness checks or video/audio proofs. Uniform-pixel reporting does not prove protected-content detection. |
| VIS-005: blind camera coach | Pending; later camera work | Not implemented by the still-screenshot milestone. |
| VIS-006: configured providers and privacy | Partial | Shared provider adapters, provider-specific credentials, configured image-capable models, provider/model/endpoint consent, AI Off, Safe Mode and offline capture/OCR are reused. Live-provider acceptance, cost estimates and complete provider/price disclosure remain. |
| VIS-007: accessible visual revisions | Pending | No reversible keyboard/natural-language crop, annotation adjustment, background editing or versioned visual-edit workflow. Prompt editing does not edit the image. |
| VIS-008: accessibility authoring | Partial | Reviewable alt-text, extended-description, chart/text prompts and text export exist. Measured caption contrast/safe-area checks and video/audio-description authoring remain. |

## Expanded PRD capture requirements

| Requirement | Status | Present behavior and remaining work |
|---|---|---|
| CP-010: upstream compile and inventory spike | Unverified | Official source/license research is documented. No independent build of permitted upstream modules or completed dependency/packaging inventory. No upstream code has been imported. |
| CP-011: zoom/presentation adapter | Pending | No integrated zoom, annotation, magnification, timer, mirroring or screen-recording adapter. Current still capture uses existing Windows/Pillow dependencies. |
| CP-012: capture targets and geometry | Partial | Full monitor, chosen window, guided portions and optional numeric rectangle exist. UIA control selection and dedicated keyboard move/resize increments remain. |
| CP-013: named regions, combining, annotation | Pending | The in-session repeat recipe is not multiple saved named regions. No combined shots or keyboard annotations. |
| CP-014: local OCR | Partial | Shared offline OCR returns selectable text; description export includes observations and confidence when supplied. Real-engine availability/quality and complete copy/export acceptance need testing. |
| CP-015: scrolling/panoramic capture | Pending | No stitching, preview or partial-stitch recovery/warnings. |
| CP-016: accessibility evidence bundle | Partial | PNG plus JSON/Markdown evidence, source metadata and unverified observations exist. Reproduction steps, control details, annotation metadata and a bundled package remain. |
| CP-017: keyboard alternatives to upstream pointer actions | Unverified | Current controls are native and keyboard-oriented; no upstream pointer surface has been integrated. This does not prove keyboard parity for the future adapter. |
| CP-018: accessible drawing-object model | Pending | No drawing surface or object list, focus, selection, order or editable geometry model. |

Expanded AI-011/012/013/014/016/017/018 are partially covered by shared providers, explicit sharing, OCR/description, source/model labels and reviewable text. Quotas/gateway, estimated cost, richer provenance, contextual authoring acceptance and publication review gates are not complete. AI-010 image generation and AI-015 reversible image-edit acceptance remain separate work.

## Verification requirements and release gates

| Requirement | Status | Present behavior and remaining work |
|---|---|---|
| VERIFY-001: complete evidence report | Partial | JSON plus readable Markdown include image identity, dimensions, hash, decode results and unverified observations. No complete user-goal/configuration/steps/error/provenance/export schema covering the whole PRD. |
| VERIFY-002: result states and Strict Publish | Partial | Objective checks are distinguished from unverified visual/privacy findings. No full state machine or Strict Publish gate/waiver workflow. |
| VERIFY-003: comprehensive preflight | Partial | Geometry and source checks exist; full privacy/semantic preflight, storage estimates and practice-video checks do not. |
| VERIFY-004/005/006: recording/export/routing proof | Pending; later audiovisual work | Still-image decode/hash evidence is not recording recovery, media sampling, audiovisual timing or external privacy-isolation proof. |
| VERIFY-007: guided verification questions | Partial | Readable capture guidance and framing prompts help users choose and review sources. No complete actionable issue list with jump-to-target/frame/track and correction history. |
| VERIFY-008: release benchmark | Unverified | Mandatory checks and human outcome evidence are not all complete. Do not claim screenshot release readiness. |
| Expanded GATE-08: UIA capture plus numbered annotation | Not passed | UIA selection and annotation are missing, so OCR and PNG evidence alone cannot pass it. |
| Expanded GATE-09: authorized cloud transmission | Partial | Consent refusal, AI Off, Safe Mode, exact-image grounding and queued automatic-permission revocation are tested. Live-provider/price disclosure and network observation acceptance remain. |
| Expanded GATE-10 and consolidated upgrade/accessibility gates | Unverified | Source identity/version/legacy regressions have tests. Installed/portable upgrade, rollback, shortcut behavior and actual JAWS/NVDA/Narrator/braille outcomes remain. |

## Guided capture for blind users

Users must not need to calculate pixels to obtain a useful first screenshot. The first recommendation is **the whole named window**. Studio derives its dimensions. One display is appropriate for several windows on that screen; full desktop includes every display and can expose unrelated content.

Guided region selection names a window/display, then offers **Whole source**, **Top half**, **Bottom half**, **Left half**, **Right half**, or **Middle quarter**. Whole source is the default. A readable capture plan explains exclusions and the next review step. Exact coordinates remain optional advanced settings, rather than a prerequisite. Portions refer to the source rectangle, not to recognized controls: “top half” cannot guarantee an entire toolbar or dialog is included.

A guided region is a screen-area capture. Unlike direct whole-window capture, an overlapping application or notification may appear. If its anchor window moves, resizes, closes or changes process before capture, the request fails and asks for refreshed selection. The implementation does not silently enlarge the region or choose another source.

After capture, review local OCR and, if authorized, use the framing prompt. Ask “Is any text cut off?”, “Is the whole dialog visible?” or “What should I change before sharing?” Findings remain uncertain. Content-aware UIA selection and correction are still necessary to complete the PRD's more demanding guided-capture requirements.

## Cross-cutting screenshot acceptance

| Requirements | Status and evidence still needed |
|---|---|
| UX-001/002/004/008; A11Y-004/008 | Partial: named sources, guided portions, optional typed geometry, readable plan and inspection steps exist. No complete guided/standard/advanced workspace with structured OCR-element navigation or correction loop. |
| UX-003; A11Y-009 | Partial: Capture menu, command palette, configurable in-app keys, global manager and authored F1 help exist. Full F6 workspace landmarks and end-to-end shortcut collision/AT acceptance remain. |
| UX-005; A11Y-014/015/016/017 | Partial: busy chat rejects duplicate submissions without disabling its focused action. Source refresh preserves missing selections. Real focus stability, composite-field input and refresh behavior require AT testing; these tests do not certify all shell interactions. |
| UX-006; A11Y-005/011/012 | Partial: shared speech/braille/text announcements and selectable guidance are reused. Full verbosity modes, searchable screenshot-event history and measured announcement behavior remain unverified. |
| UX-007; A11Y-001/002/003/006/007/010/013 | Unverified: native controls, names/help, scrolling layout and explicit errors exist. JAWS/NVDA/Narrator, braille, contrast, 200–400% scaling, visible focus, keyboard-only completion and 8 GB hardware require outcome logs. |
| TRAY-001/003/004 | Partial: opt-in global screenshot actions work without restoring Studio; registration failure is reported. A dedicated take-screenshot tray entry, background job/verification summaries and full tray accessibility remain. Global keys are not equivalent to completing the tray menu. |
| Expanded SEC-004; consolidated privacy preflight | Partial: consent and AI state are checked. No unified accessible privacy dashboard or independently proved absence of sensitive screenshot content. |
| Expanded REL-001–006; consolidated seamless upgrade | Unverified: stable identities/data paths and version-consistency regressions exist. Installed upgrade/rollback, portable acceptance, signed release assets/checksums and complete release documentation require release evidence. |
| Expanded sections 14, 15.1 and 20 | Unverified: no complete resource, hardware, fault-injection or observed blind-user outcome matrix. Required capture gates must pass before claiming this phase complete. |

## Next small steps, in order

1. Finish the guided-selection usability run with totally blind keyboard users and the required screen readers; test mixed-DPI display changes and source movement.
2. Add shared UIA discovery/selection and structured OCR locations, with safe handling of protected/offscreen elements and no claim that inferred controls are real accessible controls.
3. Add nondestructive keyboard crop/zoom/redaction and an accessible annotation-object list; preserve originals, preview in text and verify exports.
4. Add named region/workspace persistence, sequence/scrolling capture, comparison and evidence-bundle reproduction steps.
5. Close GATE-08 plus provider/privacy/installer/resource acceptance before calling the screenshot requirements complete. Proceed to the separately scoped video-with-optional-sound demo after that acceptance decision.

The UIA work should extend the existing shared Windows boundaries rather than create another automation engine. [External target inspection](../../quill/platform/windows/external_target.py) already reads bounded focused-element identity, role and password state; [selection capture](../../quill/platform/windows/selection_capture.py) reads bounded selected text with identity checks; [text target inspection](../../quill/platform/windows/text_target.py) queries editability. These are useful foundations, but none currently provides screenshot control enumeration, bounding-rectangle selection and capture. Their presence must not be counted as delivery of CAP-001/CP-012.

See the [implementation ledger](./quill-studio-capture-milestone.md) for architecture and test limits and the [user guide](../../standalone/studio/docs/userguide.md) for current workflows.
