# Optional Clipman Companion Integration

**Status:** Design; optional enhancement only  
**Date:** 2026-09-17  
**Scope:** Inkwell global text operations on Windows

## Decision

Inkwell must be fully useful without Clipman. Clipman is an optional companion
provider for users who want clipboard-history or rich-format conveniences; it
is not an Inkwell dependency, runtime service, or prerequisite for any native
text operation.

A user may run Inkwell alone, Clipman alone, both together, or neither. Starting
or stopping one application must not be required to start, stop, or recover the
other. If Clipman is absent, stopped, disabled, incompatible, or disconnected,
Inkwell uses its native target and clipboard paths or reports an honest
unsupported result for an enhancement-only capability.

This means:

- No Clipman package, import, process launch, database read, settings-file read,
  server connection, or Clipman credential is required by Inkwell.
- The wx-free external-text contract remains Clipman-free. Clipman must never
  appear in `quill/core/external_text.py` or grant editability to an unknown
  target.
- Native UI Automation, Win32, keyboard, and bounded clipboard transactions
  remain the source of truth for target identity, selection, replacement, and
  revalidation.
- Optional integration is opt-in and can be disabled without uninstalling
  either application.

The integration is therefore a capability provider boundary, not a shared
implementation boundary. Inkwell may use a supported, versioned local protocol
in a future implementation, but it must not couple to Clipman's internal C#
assemblies, process memory, files, database schema, or implementation classes.

## What works without Clipman

The standalone Inkwell baseline includes all capabilities that have native
certification evidence:

- Global abbreviation and snippet expansion into a validated target.
- Explicit text insertion and plain-text selection replacement.
- Selection, case, line, whitespace, and spelling operations supported by the
  target's capability snapshot.
- Native UIA or Win32 text access where available.
- A bounded Inkwell-owned clipboard fallback for an explicit operation when the
  native text range is unavailable.
- Target identity, privilege, protection, read-only, selection, source-text,
  and clipboard-sequence revalidation.
- Existing focus restoration, screen-reader announcements, privacy controls,
  and failure outcomes.

The native clipboard fallback is an operation transaction, not clipboard
history. It saves only the formats needed for the current operation, checks
clipboard ownership and sequence changes, and restores state only when doing so
is safe. It does not require a clipboard manager to be installed or running.

Clipman-only conveniences may be unavailable when Clipman is not enabled. That
must be surfaced as an enhancement unavailable message, never as a failure of
the underlying Inkwell text command.

## Optional capabilities

Clipman may add capabilities such as:

- Choosing a previous clipboard item for an explicit insert or paste action.
- Restoring a prior clipboard item after a user-visible recovery flow.
- Preserving or selecting rich clipboard formats when the target and the
  provider both explicitly support them.
- Providing user-requested clipboard history context to an Inkwell prompt.

Clipman does not provide proof that the focused window is editable. It does not
replace the target probe, selection snapshot, transaction layer, or stale-target
checks. In particular, a Clipman history item must never be used to infer that
an unknown `Pane`, `Custom`, terminal, or protected control accepts a safe
replacement.

Real-time typing, expansion matching, target discovery, and semantic editing
remain Inkwell responsibilities. Clipman's clipboard capture loop is not an
Inkwell input path, and Inkwell must not use Clipman Server or Clipman CLI as a
low-latency typing dependency.

## Provider boundary and negotiation

The future optional provider should live outside the core contract, for example
under the Windows or Inkwell application boundary. Its public surface should
be small and capability-based:

1. Check whether optional integration is enabled by the user.
2. Perform a short, passive handshake against a supported local protocol.
3. Negotiate a protocol version and the specific operation capabilities.
4. Return bounded clipboard data or an explicit provider outcome.
5. Close the request without retaining Inkwell target or document state.

The provider must report distinct states for:

- `disabled`: no probe and no connection attempt.
- `not_installed`: no optional provider is available.
- `not_running`: the provider is installed but is not active; Inkwell does not
  start it.
- `incompatible`: the handshake or required capability is not supported.
- `available`: the negotiated capability is ready for this operation.
- `disconnected`: the provider stopped or lost the connection during the
  operation.

A provider capability is advertised only after the user setting, handshake,
protocol version, privacy policy, and operation-specific format support all
agree. Provider availability must never alter the native `TargetSnapshot` or
upgrade `UNKNOWN` evidence to `CONFIRMED` evidence.

Routing follows this order:

1. Use the native target adapter and Inkwell transaction for semantic text
   operations.
2. Use the optional provider only when the user explicitly requests an
   enhancement it owns, or when an explicit transaction asks it for a bounded
   clipboard format or restore operation.
3. If no mutation has occurred and the provider fails, use the native fallback
   only when the original target is revalidated. Otherwise return a stale,
   cancelled, or provider-unavailable result without retrying against a new
   target.

No provider failure may turn a successful native operation into a silent no-op,
and no fallback may hide a stale-target or clipboard-ownership change.

## Coexistence rules

Inkwell and Clipman must have independent ownership of their application state.
The following rules prevent duplicate capture, hotkey races, and competing
paste actions:

| Surface | Inkwell behavior | Coexistence rule |
| --- | --- | --- |
| Clipboard capture | Uses a bounded, explicit transaction only when an operation needs it. | Inkwell does not subscribe to Clipman's history events or require its watcher. Clipman may continue its own capture independently. |
| Clipboard storage | Keeps only operation-scoped state needed for safe restore. | Inkwell never reads or writes Clipman's history store, cache, or database. |
| Keyboard hooks | Uses its existing expansion and command routes. | Inkwell does not register Clipman's hotkeys, and it does not assume Clipman's hotkeys exist. A collision is reported or disabled; neither application steals the key. |
| Paste | Performs one explicit paste/injection transaction when selected by the user or required by a certified fallback. | Clipman and Inkwell must not issue competing paste actions for one command. There is one operation owner. |
| Restore | Restores only after a sequence and ownership check. | A Clipman change during the transaction produces `CLIPBOARD_CHANGED`; Inkwell does not overwrite the newer clipboard owner. |
| Focus | Revalidates the original target immediately before mutation. | A provider callback cannot redirect an operation to the provider window or to a newly focused target. |
| Lifecycle | Starts and stops independently. | Inkwell never launches, supervises, or requires Clipman. Provider loss degrades only the optional capability. |
| Network and credentials | Uses existing Inkwell consent and egress rules. | Clipman sync consent is not transitively granted by Inkwell, and Inkwell never handles Clipman credentials. |

## Rich formats and clipboard ownership

Rich clipboard support is an enhancement, not a precondition for plain-text
editing. The transaction must choose a format deliberately:

- If the target advertises plain-text support only, Inkwell requests plain text
  and reports a text-only outcome.
- If both target and optional provider support a declared rich format, the user
  may explicitly choose the rich operation. The operation still captures the
  target identity and revalidates it before paste or replacement.
- If the provider returns formats that cannot be verified or bounded, Inkwell
  falls back to plain text or reports unsupported; it does not guess.
- A clipboard sequence number, ownership marker, and bounded timeout protect
  every read, write, and restore. Any unexpected change aborts restoration.
- Clipboard contents are never placed in logs, telemetry, crash bundles, or
  provider diagnostics.

The optional provider must not make a clipboard transaction appear atomic when
another application can observe or change the clipboard. The operation result
must retain the existing `CLIPBOARD_CHANGED`, `STALE_TARGET`, and
`ADAPTER_UNAVAILABLE` distinctions.

## Privacy and protected targets

Clipman history can contain more text than the current Inkwell operation. For
that reason, optional history access is disabled until the user enables it and
is still subject to the operation's target and privacy policy.

- Password, credential, sign-in, UAC, secure-desktop, lock-screen, and other
  protected targets never supply text to Clipman or Inkwell enhancement code.
- The provider receives only the bounded item or format requested for the
  current user action, not the complete Inkwell document or clipboard history.
- Local history access does not grant consent for AI, server sync, telemetry,
  or any other outbound transfer.
- AI and networked actions retain their separate explicit-consent gate,
  visible progress, bounded-content rule, and stale-target rejection.
- Disabling the provider stops new requests. It does not delete Clipman data,
  change Clipman settings, or require an Inkwell restart for native operations
  to continue.

## Detection and lifecycle behavior

Detection must be passive and cheap:

- When integration is disabled, Inkwell does not probe for Clipman.
- When enabled, Inkwell performs a bounded handshake only when an operation
  needs an optional capability. It never auto-starts Clipman.
- A missing executable, stopped process, incompatible protocol, timeout, or
  provider crash is an ordinary unavailable state, not an Inkwell startup
  failure.
- The provider is disconnected after each operation unless a documented,
  user-enabled session is required. Long-lived clipboard monitoring is not an
  implicit side effect of enabling a single enhancement.
- Uninstalling Clipman or removing its configuration leaves Inkwell's native
  commands and settings valid. The next request simply resolves to the native
  path or an enhancement-unavailable result.

Suggested user setting: **Use optional Clipman enhancements**. It should be
off by default for a new installation, clearly describe that Clipman is not
required, and expose a status such as `Disabled`, `Unavailable`, or `Ready`.
The setting must not hide native Inkwell commands when it is off.

## Test matrix

The following cases are required before shipping an optional provider:

| Scenario | Required result |
| --- | --- |
| Clipman is not installed | Native Inkwell expansion, insertion, replacement, and supported transforms pass; no import or launch is attempted. |
| Clipman is installed but stopped | Native behavior is unchanged; optional status is `not_running`; no auto-start occurs. |
| Clipman is running but integration is disabled | No handshake or history access occurs; native behavior is unchanged. |
| Clipman is running and enabled | Only negotiated, explicitly requested capabilities are available; target checks still come from Inkwell. |
| Provider protocol is incompatible | Optional capabilities are hidden or return `ADAPTER_UNAVAILABLE`; native commands remain usable. |
| Provider disconnects before mutation | The original target is revalidated and native fallback is used only if safe; otherwise no mutation occurs. |
| Provider disconnects after clipboard change | Inkwell does not overwrite the newer clipboard owner and returns a clipboard-change outcome. |
| User changes focus during a provider request | The original target fails revalidation; nothing is inserted into the new target. |
| Rich format is unavailable or ambiguous | Plain text is used only when explicitly allowed; otherwise the operation is reported unsupported. |
| Password or protected target is focused | No text is captured or sent to the provider. |
| Elevation or privilege does not match | The operation is denied or reported elevated, independent of provider availability. |
| Hotkey collision exists | Inkwell and Clipman retain independent bindings; neither silently steals the other binding. |
| Clipman is uninstalled while Inkwell remains | Inkwell continues without restart and without stale provider state. |

The automated suite should include a fake provider for handshake, capability,
format, timeout, disconnect, and ownership-conflict paths. A separate
no-Clipman test environment must run the complete native contract and
transaction tests with the provider package, process, files, and environment
variables absent.

## Acceptance gates

The optional integration is not ready until all of these are true:

1. A clean Inkwell installation passes the native global-text tests with no
   Clipman installation or process.
2. The core external-text contract has no Clipman import or provider-specific
   state.
3. Turning the optional setting off prevents provider probing and leaves native
   command routing intact.
4. Provider absence, stop, incompatibility, timeout, and disconnect are tested
   as ordinary outcomes.
5. Clipboard sequence, target identity, source text, privilege, and protected
   state are revalidated exactly as they are without the provider.
6. Rich-format and history features are documented as optional capabilities,
   not as part of the Inkwell baseline promise.
7. No Inkwell log, telemetry event, crash bundle, or consent record contains
   document text, clipboard history, or Clipman credentials.
8. Manual keyboard and screen-reader testing covers Inkwell alone and both
   applications running together, including hotkey, focus, paste, restore, and
   cancellation behavior.

The native-only path is the release blocker. Clipman integration may be
omitted, disabled, or removed without delaying or invalidating standalone
Inkwell text assistance.
