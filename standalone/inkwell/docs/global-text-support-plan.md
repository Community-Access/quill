# Inkwell Global Text Assistant Support Plan

**Status:** Implementation in progress for unreleased 1.0.0  
**Date:** 2026-09-17  
**Scope:** Windows desktop applications, browser edit fields, and other user-facing text surfaces

This plan is part of the 1.0.0 scope. 1.0.0 has not been released; the status
ledger distinguishes implemented foundation from unfinished integration and
live certification. See [Implementation Status](IMPLEMENTATION_STATUS.md).

## Executive decision

Expand Inkwell from a system-wide abbreviation expander into a capability-based global text assistant. Reuse QUILL's existing pure text engines and shared abbreviation/snippet formats, then add a Windows target and transaction layer that can safely inspect and replace text outside the QUILL editor.

Browser extensions are **not** the baseline. A user who clicks into a browser edit field, or navigates to it with a screen reader, has already given Inkwell a focused target. Standard HTML `input`, `textarea`, and browser-exposed text controls should be handled through the same native Windows target path used for other edit controls. An optional browser extension is justified only when a requested capability cannot be provided reliably through UI Automation or keyboard/clipboard operations, such as DOM-aware selection/context, complex rich editing, canvas editors, or protected page behavior.

The product promise is capability-based, not universal: Inkwell should say what the focused target can safely support and why an operation is unavailable. It must never claim that every surface accepting keystrokes is a document editor.

### Optional Clipman companion

Inkwell's native target and transaction paths are the standalone baseline. Clipman
may provide opt-in clipboard-history and rich-format conveniences, but it is
never required for global expansion, insertion, replacement, or any other
certified native capability. Inkwell must continue to work when Clipman is not
installed, not running, disabled, incompatible, or stopped during an operation.

The detailed boundary, coexistence rules, privacy requirements, and test matrix
live in [`clipman-optional-integration.md`](clipman-optional-integration.md).

## Goals and user promise

### Goals

- Expand abbreviations and snippets wherever a supported external text target is focused.
- Apply selected-text operations such as case changes, selection expansion, line transforms, spelling replacement, and review-first grammar fixes.
- Support explicit dictation insertion into a validated external target.
- Preserve the current credential, secure-surface, privacy, focus, and accessibility protections.
- Give Word, Outlook, Notepad, Edge, Chrome, Firefox, terminals, dialogs, and ordinary edit fields a common baseline plus target-specific certification where needed.
- Keep QUILL's editor behavior unchanged and prevent double expansion in QUILL-owned windows.

### Non-promises

Inkwell will not promise arbitrary editing for:

- Password fields, credential managers, sign-in surfaces, UAC, the secure desktop, lock screens, or other protected targets.
- An elevated application when Inkwell does not have matching privilege.
- Canvas-only or owner-drawn editors without a tested text contract.
- Remote desktop, virtualized, streamed, or terminal surfaces whose text semantics cannot be verified.
- Rich-format preservation through a generic plain-text adapter.
- Silent cloud analysis of external document content.

### User-visible capability language

Every operation should resolve to one of these outcomes:

- **Supported:** the target exposes the requested text capability and the operation completed.
- **Text-only:** the operation completed but rich formatting or native semantic state was not available.
- **Clipboard fallback:** the operation used a bounded, user-visible clipboard transaction.
- **Needs review:** text was captured but could not be safely applied after a focus or content change.
- **Unsupported:** the target does not expose enough information for the operation.
- **Protected:** policy blocked the operation.
- **Elevated:** the target requires matching privilege.
- **Cancelled:** the user or target cancelled the operation.

## Current state

Inkwell already has a strong global expansion foundation:

- [`quill/apps/inkwell.py`](../../../quill/apps/inkwell.py) owns the tray service, settings, Quick Insert, Expand Now, and lifecycle.
- [`quill/ui/inkwell_expansion.py`](../../../quill/ui/inkwell_expansion.py) handles expansion lifecycle, field prompts, focus restoration, injection selection, usage persistence, announcements, and library reloads.
- [`quill/core/abbreviations.py`](../../../quill/core/abbreviations.py) provides the shared schema-v2 abbreviation library, including app scoping, case behavior, variables, fields, choices, cursor placement, and usage data.
- [`quill/platform/windows/expansion_hook.py`](../../../quill/platform/windows/expansion_hook.py) provides the low-level keyboard hook, bounded buffer, injected-event filtering, worker dispatch, navigation resets, watchdog recovery, and existing expansion safety checks.
- [`quill/platform/windows/text_target.py`](../../../quill/platform/windows/text_target.py), [`foreground.py`](../../../quill/platform/windows/foreground.py), and [`text_injector.py`](../../../quill/platform/windows/text_injector.py) provide target heuristics, elevation checks, foreground identity, Unicode `SendInput`, and optional clipboard paste.
- `QuillHandlesOwnExpansion` keeps Inkwell out of QUILL's own editor so the native editor path does not expand twice.

QUILL also has reusable editor engines, but they are currently bound to QUILL's document and controls:

- [`quill/core/snippets.py`](../../../quill/core/snippets.py) provides persistent snippets, search, starter packs, fields, choices, date/time values, and cursor placement.
- [`quill/core/selection.py`](../../../quill/core/selection.py) provides pure word, line, sentence, paragraph, and block spans plus expand/shrink behavior.
- [`quill/core/transforms.py`](../../../quill/core/transforms.py), `line_ops.py`, and `format_ops.py` provide pure text transformations.
- [`quill/core/spellcheck.py`](../../../quill/core/spellcheck.py) provides misspelling detection, suggestions, dictionaries, and ignore behavior.
- [`quill/core/ai/grammar_check.py`](../../../quill/core/ai/grammar_check.py) and `diff_review.py` provide structured review and application models.
- [`quill/core/speech/dictation/controller.py`](../../../quill/core/speech/dictation/controller.py) is a wx-free dictation state machine with injected services.
- [`quill/core/action_feedback.py`](../../../quill/core/action_feedback.py) defines consistent sound/speech/silent outcome behavior.

### Root gap

The current global path can type an expansion, but it cannot safely implement arbitrary external editing because it lacks a contract for:

- Stable focused-target identity.
- Selection and surrounding-text snapshots.
- UIA text-range and read-only capability detection.
- Replacement transactions and stale-target detection.
- Clipboard format preservation and ownership conflict handling.
- Target-native undo grouping.
- Rich-text semantics.
- Structured failure reasons.

`SendInput` is an input mechanism, not a semantic document API. It cannot by itself read a selection, preserve rich formatting, or guarantee that the target's undo stack contains exactly one operation.

## Architecture

### Layer 1: target-neutral core contract

Add a wx-free contract for external text operations. The exact module name can be chosen during implementation, but it should live under `quill/core` and contain no Windows, wx, COM, or browser imports.

The contract should model at least:

```text
TargetSnapshot
  target_id: stable window/control identity
  process_id and process_name
  window_handle or platform reference
  control identity/class and accessible role
  elevation and protection state
  read_only state
  capabilities
  captured_at and revision/sequence information

SelectionSnapshot
  full_text or selected_text, when available
  selection_start and selection_end, when available
  caret position, when available
  surrounding context, when authorized and bounded
  source target snapshot

TextReplacement
  expected source text and range
  replacement text
  resulting caret/selection
  requested formatting mode
  operation label

OperationResult
  status: applied, unsupported, protected, stale, cancelled, failed
  capability used
  fallback used
  affected character count
  target-safe reason code
  user-facing message without document content
```

The contract must distinguish `unknown`, `unsupported`, and `denied`. An unknown provider must not be treated as an editable document merely because it accepts keystrokes.

### Layer 2: Windows target and transaction adapters

Extend the Windows platform boundary around:

- [`text_target.py`](../../../quill/platform/windows/text_target.py) for focused-target discovery, UIA patterns, read-only state, capability confidence, and policy classification.
- [`foreground.py`](../../../quill/platform/windows/foreground.py) for identity capture, focus transitions, and just-in-time revalidation.
- [`text_injector.py`](../../../quill/platform/windows/text_injector.py) for checked input results and text-only insertion.
- A new `clipboard_transaction.py` for bounded read/copy/paste/restore cycles, format preservation, sequence checks, and contention outcomes.
- New target-specific modules only where the generic contract is insufficient, such as `office_word.py`, `office_outlook.py`, `browser_bridge.py`, and `terminal.py`.
- An optional clipboard-provider boundary for history or rich-format enhancements. It must not grant target editability, replace the native transaction, or become a runtime dependency.

The transaction layer owns the lifecycle:

1. Capture the focused target and its capabilities.
2. Capture the selection/context using the strongest available mechanism.
3. If user interaction is required, keep the captured data bounded and do not mutate yet.
4. Restore or reacquire focus and revalidate target identity.
5. Confirm that the source range/content is still the captured source.
6. Perform one replacement or insertion through the strongest available adapter.
7. Verify the operation result where possible.
8. Restore clipboard state if it was used, unless the user changed it during the transaction.
9. Return a structured outcome and announce only the outcome information the screen reader does not already provide.

No operation may issue an implicit `Ctrl+A` to discover document content. A clipboard fallback must be explicit, bounded, whole-cycle retried, and able to abort on ownership or focus changes.

### Layer 3: Inkwell assistant services

Keep `ExpansionHook` responsible for observing and dispatching low-level keyboard input. Do not turn the hook into the semantic editing engine. Inkwell should own:

- Global trigger matching and expansion policy.
- Capability-aware command dispatch.
- Quick Insert for abbreviations and snippets.
- Field and choice prompts.
- Review flows for spelling and AI actions.
- Dictation lifecycle integration.
- User settings, pause/kill switch, status, announcements, and recovery.

Global commands must use a bound target/session service. Do not register raw `MainFrame` methods as global handlers and do not broaden QUILL's existing safe global-hotkey allowlist by accident.

## Capability model

Capabilities are independent. A target may support insertion but not selection reading, or plain replacement but not rich formatting.

| Capability | Meaning |
|---|---|
| `insert_text` | Insert text at the focused caret. |
| `expand_trigger` | Observe a trigger and replace it with an abbreviation/snippet result. |
| `read_selection` | Read the currently selected text with a trusted target association. |
| `replace_selection` | Replace a known selection without writing into a stale target. |
| `read_context` | Read bounded surrounding text for selection, spacing, or context-aware templates. |
| `plain_text` | Operate on plain text without claiming formatting preservation. |
| `rich_text` | Preserve or intentionally modify target-native formatting. |
| `native_undo` | Group the change in the target's native undo model. |
| `dictation_target` | Keep a stable insertion target through a dictation session. |
| `browser_dom` | Use browser page/DOM semantics beyond the native control contract. |

Capability confidence should include the evidence used: UIA pattern, known control class, target adapter, keyboard/clipboard probe, or extension protocol. The UI can then explain why a feature is unavailable without exposing raw implementation details.

## Reuse plan

### Abbreviations

Reuse the existing schema-v2 library and matching rules. Add a common rendered-result shape containing:

- Rendered text.
- Cursor offset or cursor placement instruction.
- Required fields and choices.
- Context values actually available to the target.
- Source entry and usage metadata.

Existing variables such as date/time, clipboard, and cursor placement can be made global when their data is available. App scoping remains useful. QUILL-only context such as filename, document title, line number, or editor word-at-cursor must be capability-gated rather than filled with guesses.

Automatic expansion should remain conservative and fast. It should not read arbitrary external document content merely to decide whether a trigger exists.

### Snippets

Reuse [`quill/core/snippets.py`](../../../quill/core/snippets.py) for storage, search, rendering, fields, choices, and cursor markers. Add a global context provider that can supply selection and clipboard values first, followed by date/time and foreground application metadata.

Global snippet execution must:

- Keep QUILL's snippet format compatible.
- Distinguish user snippets from contributed snippets.
- Define deterministic abbreviation/snippet collision precedence.
- Show the entry type, category, and source in Quick Insert.
- Gate every placeholder by an available capability.
- Never grant a Quillin arbitrary external document access just because it contributes a snippet.

Recommended collision order: user abbreviation, user snippet, then permissioned contributed entries. Collisions should be visible in the picker and deterministic in trigger expansion.

### Selection, transforms, spelling, and review

Reuse the pure engines with an external `TextSnapshot` rather than copying QUILL's document mutation code:

- Selection spans and descriptions from `selection.py`.
- Case transforms from `transforms.py`.
- Line and whitespace operations from `line_ops.py` and `format_ops.py`.
- Misspelling detection and suggestions from `spellcheck.py`.
- Structured grammar issues and accepted-fix application from `grammar_check.py` and `diff_review.py`.
- Feedback resolution from `action_feedback.py`.

Every external write must pass through the target transaction. Rich formatting commands are separate: a generic adapter must not claim to preserve formatting when it only replaces Unicode text.

### Dictation

Reuse `DictationController`, insertion normalization, and session concepts. Implement an external `DictationServices` adapter that captures the target identity and caret/selection at start, stops on focus loss by default, and sends failed or stale insertion to review or clipboard rather than writing into a new target.

## Native Windows baseline

The first implementation should support the strongest common behavior for ordinary Windows controls:

- Win32 Edit and RichEdit controls.
- Notepad and WordPad where their current control exposes the expected semantics.
- Standard dialog edit fields that are not secure or credential-like.
- Common Scintilla-based controls where capability probes are reliable.
- UIA `Edit` and `Document` controls exposing usable Value/Text/Selection patterns.
- Console and terminal insertion only where the target's semantics are explicitly certified.

The target probe should prefer, in order:

1. A dedicated target adapter with verified semantics.
2. UIA TextPattern, ValuePattern, SelectionPattern, and control metadata.
3. Known native edit/control classes with conservative behavior.
4. An explicit keyboard/clipboard fallback for a single safe operation.
5. Unsupported or protected status.

The current heuristic that treats unknown UIA `Pane` or `Custom` controls as editable must not be sufficient for selected-text commands. It may remain part of the legacy expansion path only while the new assistant uses a positive capability policy.

## Browser strategy: native first, extension by exception

### Default path

For Edge, Chrome, and Firefox, a focused browser edit field is a valid target even when focus was obtained by mouse click or screen-reader navigation. The assistant should attempt the generic native path first:

1. Capture the foreground browser window and focused UIA element.
2. Identify whether the element is a browser-exposed `Edit`, `Document`, or another positively identified text control.
3. Use native UIA text/selection/value patterns when available.
4. If the field does not expose a usable range, use a bounded keyboard/clipboard transaction only when it can preserve the user's selection and revalidate the same focused element.
5. Perform plain-text insertion or replacement and report the actual fallback used.
6. Do not install, require, or prompt for an extension merely because the target is a browser.

This baseline is intended to cover ordinary search boxes, address-like edit fields, `input`, `textarea`, and accessible browser-hosted fields. It also covers many contenteditable fields when the browser exposes enough native text semantics. The product must measure and certify the actual behavior instead of assuming that the browser process name implies support.

### Optional extension path

A signed and permissioned extension is an enhancement, not a prerequisite. Consider it only after native probing demonstrates a real capability gap, and only for a declared capability such as:

- DOM-aware selection and context that UIA cannot provide.
- Reliable range replacement in complex `contenteditable` editors.
- Rich-text or HTML-preserving operations.
- Canvas/editor surfaces with no native text range.
- Browser-specific page events or editor state that cannot be observed natively.
- A protected or virtualized page integration that has an explicit product and security design.

Reuse the transport and registration patterns in [`quill/apps/beacon/native_messaging.py`](../../../quill/apps/beacon/native_messaging.py) and the existing browser bridge only as infrastructure. Define a neutral Inkwell assistant protocol rather than coupling semantics to Beacon capture payloads.

The extension must be optional, separately permissioned, origin-aware, and fail closed. It must not inspect or mutate browser chrome, password inputs, extension stores, protected pages, or arbitrary page content. The native path must continue to work when the extension is absent, disconnected, unavailable for the current browser, or declined by the user.

### Browser certification matrix

Certify the native path independently for:

- Edge, Chrome, and Firefox search/address-style fields.
- HTML `input` and `textarea`.
- Accessible `contenteditable` fields.
- Webmail compose/reply fields, including Outlook on the web.
- Password fields and protected pages, which must be refused.
- Pages where UIA reports only a generic `Pane` or `Custom` surface.

If an extension is later added, certify its DOM path separately. Do not use extension test success as evidence that the native path is correct.

## Target families

### Notepad and standard Windows controls

Use these as the first live certification targets because plain-text semantics are easiest to verify. Certify expansion, explicit selected replacement, transforms, spelling replacement, snippet prompts, dictation insertion, focus restoration, undo behavior, clipboard restoration, and credential refusal.

### Word

Treat live Word as a dedicated adapter, not a process-name heuristic. Start with a plain-text selection/replacement baseline through the generic transaction where it is safe. Add Office COM/TOM integration for stable range identity, rich replacement, formatting, and undo grouping only after a separate design for Office versions, bitness, Protected View, read-only documents, and COM cleanup.

The existing `.docx` readers and writers are file I/O and do not provide live Word selection access.

### Outlook

Treat classic Outlook compose/reply controls separately from new Outlook's WebView/browser surface:

- Classic Outlook may require WordEditor-aware range handling.
- New Outlook should first use the browser/native field path; an extension is optional only for a measured DOM capability gap.
- Reading panes, signatures, quoted replies, protected content, account dialogs, and compose fields need separate tests.

### Terminals and consoles

Provide insertion or paste only where explicitly certified. Do not assume that shell input, a terminal scrollback buffer, a TUI widget, and a document selection have the same semantics. Terminal actions must be separately configured and must explain when native undo or selection replacement is unavailable.

### Dialogs and custom controls

Standard non-secure edit fields may use the native baseline. Unknown, read-only, owner-drawn, or credential-like fields require positive capability evidence. A custom control that accepts keystrokes is not automatically safe for reading or replacing text.

### Elevated targets

Detect elevation mismatch and explain it. Matching elevation is the first supported option. Signed `uiAccess` deployment, brokering, and installer changes are separate security/release work. Never auto-elevate or weaken secure-surface exclusions.

## Global feature set

### Phase A baseline

- Existing abbreviation expansion, preserved and regression-tested.
- Global Quick Insert for abbreviations and snippets.
- Explicit insert and replace-selection commands for supported plain-text targets.
- Selected-text case transforms.
- Selection expansion/shrink where text and offsets are available.
- Safe line/whitespace transforms where the target can provide the required text range.
- Spelling suggestions and one-word replacement.
- Accessible field and choice prompts with target revalidation before insertion.

### Phase B review features

- Review-first grammar and style checks for bounded selected text.
- Accepted-fix application as one replacement transaction.
- External dictation insertion with focus-loss recovery and review fallback.
- Persistent global-action recovery that does not assume the target's `Ctrl+Z` is reliable.

AI and networked actions require explicit per-action consent, bounded content, visible progress/outcome, stale-target rejection, and the existing network egress/privacy controls.

### Later target-specific features

- Rich Word/Outlook replacement and native undo grouping.
- Browser DOM-aware context, rich HTML preservation, and complex editor support.
- Terminal-specific selection semantics.
- Additional adapters for known custom controls.

## Safety, privacy, and accessibility requirements

### Safety

- Keep existing credential, password, sign-in, UAC, lock-screen, and secure-desktop exclusions fail closed.
- Capture target identity before every read and revalidate immediately before mutation.
- Abort if focus, process, control identity, selection, source text, or clipboard ownership changed.
- Never silently select the entire document.
- Never mutate before a prompt/review flow is accepted.
- Keep automatic expansion narrower than explicit user-invoked editing.
- Return captured text for review or copy when safe application fails; do not retry blindly against a new target.
- Check `SendInput` results and report partial or failed injection.

### Privacy

- Do not place document text, selections, snippets containing document text, or dictation transcripts in logs, telemetry, crash bundles, or Quillin metadata.
- Require explicit consent before external text leaves the device.
- Keep offline spelling and transforms offline.
- Bound all captured content by operation and size.
- Make pause, disable, target exclusions, clipboard fallback, and AI consent visible in Inkwell settings.

### Screen readers and braille

Reuse the existing announcement, screen-reader detection, braille, modal, and focus-restoration infrastructure. Inkwell should announce action outcomes and failures, not repeat the focused control's name, role, state, selection, or text that NVDA, JAWS, or Narrator already reports. Prompts must restore focus to the initiating external target after completion or cancellation.

All new commands need an accessible name, a predictable keyboard route, cancellation behavior, and an outcome message that distinguishes protected, unsupported, stale, and successful operations.

## Definitive implementation breakdown

The following work packages are the definitive implementation breakdown. A
work package is not complete until its code, focused tests, and stated exit
evidence exist. The sequence is dependency order, not product priority:
Word, Outlook, browsers, and standard Windows controls remain first-class
target families. The native contract is shared so those families do not grow
separate, incompatible editing implementations.

| ID | Work package | Primary surfaces | Depends on | Exit criterion |
|---|---|---|---|---|
| W0 | Contract and policy | `quill/core/external_text.py` (new), `quill/core/expansion/targets.py`, this plan, Inkwell PRD | None | Capability names, snapshots, reason codes, explicit/automatic policy, placeholder rules, and collision rules are approved and covered by wx-free tests. |
| W1 | Native target probe | `quill/platform/windows/text_target.py`, `foreground.py` | W0 | A focused target returns identity, privilege, protection, read-only state, UIA evidence, and independent capabilities; unknown `Pane`/`Custom` controls are not treated as editable for explicit reads or writes. |
| W2 | Text transaction | `quill/platform/windows/text_transaction.py` (new), `clipboard_transaction.py` (new), `text_injector.py` | W1 | Selection capture, target revalidation, replacement, checked injection, clipboard ownership/format handling, timeout, and stale-target aborts pass fake platform tests. |
| W3 | Assistant runtime | `expansion_hook.py`, `quill/ui/inkwell_expansion.py`, `quill/apps/inkwell.py`, Inkwell settings | W2 | Global dispatch can bind a validated target session without adding semantic editing work to the hook or changing hook latency/watchdog behavior. |
| W4 | Shared snippets and prompts | `quill/core/snippets.py`, expansion fields, Quick Insert, Quillin contribution boundary | W0 and W3 | Abbreviations and snippets share the global rendered-result contract; fields, choices, context capabilities, usage, and collisions behave deterministically. |
| W5 | Plain-text commands | `selection.py`, `transforms.py`, `line_ops.py`, `format_ops.py`, `spellcheck.py`, `action_feedback.py` | W2 and W4 | Insert, replace, selection, transform, spelling, feedback, and recovery commands use one external transaction and preserve one-operation semantics. |
| W6 | Common-control certification | `tests/uia`, new Windows target fixtures, Notepad/WordPad/native controls | W1-W5 | Live Windows evidence covers insert, replacement, snippets, transforms, spelling, dictation, focus return, undo behavior, clipboard recovery, and refusal cases. |
| W7 | Browser native certification | `text_target.py`, `text_transaction.py`, browser target fixtures | W1-W6 | Edge, Chrome, and Firefox ordinary edit fields pass with no extension installed, including mouse focus and screen-reader focus; gaps are recorded by capability. |
| W8 | Optional browser capability bridge | `quill/apps/beacon/native_messaging.py`, `capture_bridge.py`, browser extension paths | W7 plus measured gap | An extension exists only for a named native-path gap, uses least privilege and origin checks, and native operation remains functional when it is absent. |
| W9 | Word and Outlook adapters | new `office_word.py`, `office_outlook.py`, Office fixtures | W1-W5 | Each advertised Word/Outlook capability has a dedicated adapter, version/privilege/read-only policy, stale-range handling, and live certification. |
| W10 | Dictation and release hardening | dictation controller adapter, screen-reader bridges, settings, docs, manual matrix | W3-W9 as applicable | External dictation, AI consent, accessibility outcomes, elevation behavior, privacy controls, and target-specific release claims pass their gates. |
| W11 | Optional Clipman companion | opt-in provider boundary, native fallback, settings, tests, and `clipman-optional-integration.md` | W2 and native baseline | Clipman absence, stop, disablement, incompatibility, disconnect, clipboard contention, and hotkey coexistence leave the native path fully usable. |

### Stage gates

1. **No external write before W2.** A capability probe may report support, but
  no selected-text command or review flow may mutate a target until the
  transaction layer can revalidate it.
2. **No extension before W7.** The native browser path must be implemented and
  measured first. An extension proposal must name the missing capability and
  the target surfaces it will cover.
3. **No universal target claim.** A process name, successful keystroke, or
  source-contract test is not certification. Advertise only the capabilities
  supported by live target evidence.
4. **No silent content transfer.** Local transforms remain offline. AI,
  browser bridge, and any other outbound path require explicit consent,
  bounded content, visible progress, and stale-target rejection.
5. **No companion prerequisite.** Clipman may enhance an explicit clipboard
  action, but its absence or failure must never block a certified native
  operation or cause Inkwell to start a companion process.

### Phase 0: Contract and product matrix

- Define the capability enum, target snapshot, selection snapshot, replacement request, result status, and reason codes.
- Define target confidence and explicit versus automatic operation policy.
- Capture the browser native-first decision in the Inkwell PRD and user guide.
- Create the target matrix and release terminology in this plan.
- Define abbreviation/snippet collision and placeholder capability rules.

**Estimate:** M, 1-2 weeks.

### Phase 1: Native target and transaction layer

- Add UIA TextPattern/ValuePattern/SelectionPattern probing and read-only classification.
- Add stable foreground/control identity and just-in-time revalidation.
- Add checked Unicode injection results.
- Build clipboard transactions with bounded retry, format preservation where available, sequence/ownership checks, timeout, and safe abort.
- Preserve the existing expansion hook latency and watchdog behavior.

**Estimate:** L, 3-6 weeks.

### Phase 2: Global snippets and plain-text commands

- Move global matching behind an assistant matcher interface.
- Add shared snippet loading, Quick Insert result types, field prompts, and capability-gated context.
- Add target-aware command dispatch separate from QUILL's document command registry.
- Implement plain-text insertion, replacement, selection operations, transforms, spelling, feedback, and recovery.
- Keep QUILL-owned expansion excluded.

**Estimate:** L, 3-6 weeks.

### Phase 3: Common-control and browser-native certification

- Certify Notepad, WordPad, standard Windows edit fields, and supported RichEdit/Scintilla controls.
- Certify Edge, Chrome, and Firefox native edit fields without extensions.
- Test ordinary `input`, `textarea`, search fields, and accessible `contenteditable` controls.
- Record capability gaps instead of filling them with broad browser heuristics.

**Estimate:** L, 3-6 weeks including live Windows validation.

### Phase 4: Optional browser capability bridge

- Add an extension only for gaps demonstrated by Phase 3.
- Reuse Beacon native-messaging framing and registration patterns, but define an Inkwell-specific, least-privilege protocol.
- Implement origin and target checks, explicit permissions, disconnect handling, and DOM selection/replacement only for declared supported editors.
- Keep native operation available when the extension is absent.

**Estimate:** L to XL, 4-8 weeks depending on DOM/rich-editor scope and browser packaging.

### Phase 5: Word and Outlook adapters

- Define Office version, bitness, Protected View, read-only, and COM lifecycle policy.
- Implement and certify Word selection/range identity, plain/rich replacement, and undo grouping.
- Implement classic Outlook WordEditor flows.
- Validate new Outlook through the native browser path first and add an extension only if needed.
- Test compose, reply, signatures, quoted text, reading panes, and security dialogs.

**Estimate:** L to XL, 4-8 weeks per adapter family.

### Phase 6: Dictation, terminals, privilege, and accessibility release hardening

- Adapt dictation to external targets and stale-target recovery.
- Certify terminal insertion/paste behavior separately.
- Complete normal/elevated behavior and document any `uiAccess` decision separately.
- Run NVDA, JAWS, and Narrator keyboard/focus/announcement acceptance.
- Update the [Inkwell PRD](prd.md), [user guide](userguide.md), and [QUILL PRD](../../../docs/Product%20Requirement%20Documents%20and%20Specifications/QUILL-PRD.md).

**Estimate:** L, 3-6 weeks plus target availability and manual test time.

The phases are dependency order, not product priority. Word, Outlook, browsers, and standard controls remain first-class target families; the generic native contract is the shared foundation that prevents three incompatible implementations.

## Testing and certification

### Core unit tests

Add tests for:

- Capability merging, confidence, and reason codes.
- Abbreviation/snippet precedence and placeholder gating.
- Selection snapshots, stale revisions, and target identity changes.
- Transform offsets and one-replacement semantics.
- Spelling replacement and grammar/diff application.
- Dictation focus loss, cancellation, and review fallback.
- Feedback modes, including missing sound and silent behavior.

### Windows platform tests

Add fake API tests for:

- UIA pattern discovery and read-only/provider classification.
- Known control classes and unknown `Pane`/`Custom` behavior.
- Foreground identity changes and elevation mismatch.
- Credential and secure-surface denial.
- Unicode, surrogate, dead-key, AltGr, and keyboard-layout input.
- Partial `SendInput` results and watchdog recovery.
- Clipboard contention, non-text formats, user copies during a transaction, timeout, and restoration failure.
- Hook injection filtering and lifecycle.

Real clipboard and system-resource tests must use the repository's `machine_global` grouping rules.

### Live target tests

Use opt-in Windows fixtures with deterministic launch and cleanup. Do not put document content in test logs.

| Target family | Required live scenarios |
|---|---|
| Notepad/WordPad | Insert, replace selection, snippets, transforms, spelling, dictation, undo, focus return. |
| Native edit/dialog fields | Keyboard and screen-reader focus, read-only refusal, cancellation, secure-field denial. |
| Edge/Chrome/Firefox native path | Search/input/textarea/contenteditable, click focus, screen-reader focus, selection replacement, extension absent. |
| Optional browser extension | DOM selection/context, rich/contenteditable cases, origin checks, disconnects, protected/password refusal. |
| Word | Plain/rich selection replacement, undo grouping, read-only, Protected View, version/bitness matrix. |
| Outlook | Classic WordEditor compose/reply, new Outlook native path, signatures, quoted text, reading pane, security dialogs. |
| Terminals | Insert/paste only where certified, shell/TUI distinction, focus loss, no false selection claims. |
| Elevated/custom | Matching elevation, mismatch refusal, positive capability probes, unsupported fallback wording. |

### Manual accessibility acceptance

With NVDA, JAWS, and Narrator, verify:

- Mouse focus and screen-reader navigation both establish the same supported target.
- Commands do not steal focus unexpectedly.
- Prompts have deterministic focus and return focus on close.
- Announcements report outcomes without duplicating control names, roles, states, or selected text.
- Keyboard-only cancellation and emergency stop work.
- Braille and high-contrast behavior remain usable.
- Clipboard changes and restoration are understandable without exposing document content.
- Failure wording distinguishes unsupported, protected, elevated, stale, and cancelled.

## Effort summary

For one experienced Windows engineer, excluding procurement and app licensing delays:

- Contract, capability model, documentation, and pure tests: **M, 1-2 weeks**.
- Native target probing and clipboard transaction: **L, 3-6 weeks**.
- Global snippets, commands, transforms, spelling, and review flows: **L, 3-6 weeks**.
- Common-control and browser-native certification: **L, 3-6 weeks**.
- Optional browser extension: **L-XL, 4-8 weeks**, only if Phase 3 proves it necessary.
- Word and Outlook adapters: **L-XL, 4-8 weeks each**, depending on rich editing and Office matrix.
- Dictation, terminals, elevation, and screen-reader certification: **L, 3-6 weeks**.

A useful 1.0.0 release is the native plain-text baseline plus certified browser edit fields, with no extension requirement. Rich Word/Outlook behavior and browser DOM enhancements should ship as separately tested capabilities rather than being implied by the baseline.

## Release gates

Do not claim full global text-assistant support until all of the following are true:

- The target contract and reason codes are implemented and unit-tested.
- The native transaction layer revalidates target identity and protects clipboard state.
- Existing abbreviation expansion and QUILL ownership behavior remain green.
- Notepad/standard controls and browser-native fields pass live Windows tests.
- Each advertised Word, Outlook, terminal, or extension capability has its own certification evidence.
- Secure, credential, elevated, protected, and unsupported cases fail safely.
- NVDA, JAWS, and Narrator manual acceptance covers the advertised target matrix.
- The native baseline passes with Clipman absent, stopped, disabled, and
  incompatible; companion behavior is tested separately from that baseline.
- PRD, user guide, support matrix, tests, and known limitations agree.

This roadmap should be tracked as a new target-aware Inkwell subsystem. It should not be implemented by making the keyboard hook larger or by treating browser process detection as proof that a text control is available.
