# Inkwell 1.0.0 Implementation Status

**Release state:** 1.0.0 is not released. Implementation is in progress.

This is the status of the current checkout, not a release claim. The standalone
folder contains the product wrapper, packaging, installers, and documentation;
the application and Windows adapters live in the shared `quill` package. A
foundation can be implemented and unit-tested without being advertised as
support for every Windows target. Live target, browser, Office, and screen-reader
evidence is still required before those capabilities are released.

## Executive summary

- The 1.0.0 abbreviation expander and standalone packaging path are implemented,
  but 1.0.0 has not shipped.
- The native external-text contract, target probe, selection capture, checked
  injection, and bounded clipboard transaction are implemented as a shared
  foundation with focused tests.
- The global assistant command set, target-family adapters, live certification,
  and optional Clipman provider are not complete.
- Clipman is optional. Inkwell's native path must remain usable when Clipman is
  absent, stopped, disabled, incompatible, or disconnected.

## Status meanings

- **Implemented foundation:** code and focused automated tests exist; live target
  certification or full user-facing integration may still be outstanding.
- **Partial:** some integration exists, but the work package exit criteria are
  not met.
- **Certification pending:** the shared code exists, but no release support claim
  is made until the required Windows or assistive-technology evidence exists.
- **Not started:** no implementation or certification evidence exists in this
  checkout.
- **Design only:** the boundary is documented, but the runtime provider or
  adapter is not implemented.

## Work package status

| Package | Current state | Evidence in this checkout | Remaining release gate |
| --- | --- | --- | --- |
| W0 Contract and policy | Implemented foundation | [`external_text.py`](../../../quill/core/external_text.py), target policy, and boundary tests | Keep capability, reason-code, placeholder, and collision policy aligned with the intended 1.0.0 command set. |
| W1 Native target probe | Implemented foundation; certification pending | [`external_target.py`](../../../quill/platform/windows/external_target.py), advisory [`text_target.py`](../../../quill/platform/windows/text_target.py), and [`test_external_target.py`](../../../tests/unit/platform/windows/test_external_target.py) | Live UIA/native behavior for common controls, read-only fields, protected targets, and elevation. |
| W2 Text transaction | Implemented foundation; certification pending | [`text_transaction.py`](../../../quill/platform/windows/text_transaction.py), [`clipboard_transaction.py`](../../../quill/platform/windows/clipboard_transaction.py), and focused transaction tests | Live checked mutation, clipboard contention, focus changes, undo behavior, and screen-reader outcomes. |
| W3 Assistant runtime | Partial | [`inkwell_expansion.py`](../../../quill/ui/inkwell_expansion.py), [`text_runtime.py`](../../../quill/platform/windows/text_runtime.py), and [`test_text_runtime.py`](../../../tests/unit/platform/windows/test_text_runtime.py) bind global expansion to a validated target transaction. | Wire and test the complete explicit assistant command surface without adding semantic work to the hook callback. |
| W4 Shared snippets and prompts | Partial | [`snippets.py`](../../../quill/core/snippets.py), expansion fields, [`test_snippets.py`](../../../tests/unit/core/test_snippets.py), and [`test_fields.py`](../../../tests/unit/core/expansion/test_fields.py) cover shared storage and prompt primitives. | Complete global capability gating, collision precedence, context policy, Quillin boundaries, and cancellation behavior. |
| W5 Plain-text commands | Core engines only | Shared selection, transform, line, format, spelling, grammar-review, and feedback engines exist. | Route explicit global insert, replacement, transform, spelling, and review actions through one external transaction. |
| W6 Common-control certification | Not started | No live Notepad, WordPad, native-control, or screen-reader certification evidence is recorded here. | Add Windows fixtures and certify each advertised capability, including refusal and recovery cases. |
| W7 Browser native certification | Not started | Native browser-first policy is documented; no Edge, Chrome, or Firefox evidence is recorded. | Certify ordinary edit fields with mouse focus, screen-reader focus, no extension, and protected-page refusal. |
| W8 Optional browser bridge | Gated, not started | The optional path is documented and Beacon transport can be reused if a measured gap exists. | First complete W7, then name a native capability gap before building an extension. |
| W9 Word and Outlook adapters | Not started | No dedicated live Word or Outlook adapter is present. | Design and certify version, privilege, read-only, Protected View, COM/WebView, stale-range, and cleanup behavior. |
| W10 Dictation and release hardening | Not started for the global assistant | Existing 1.0 UI and dictation foundations do not constitute external-target release evidence. | Bind dictation to a stable external target, complete privacy/accessibility gates, and perform manual NVDA, JAWS, and Narrator acceptance. |
| W11 Optional Clipman companion | Design only | [`clipman-optional-integration.md`](clipman-optional-integration.md) defines the boundary; the native clipboard transaction is independent. | Add an opt-in provider, negotiation, disconnect, ownership, hotkey, privacy, and no-Clipman test matrix without making it a dependency. |

## What is complete inside this folder

- The standalone launcher, portable/installed data-root behavior, package metadata,
  PyInstaller entry point, release script, installers, icon, and documentation
  renderer are present.
- The user-facing documentation now distinguishes unreleased 1.0.0 work from
  future work and states that Clipman is optional.
- Markdown documents are the source. Matching HTML and EPUB files are generated
  by [`render_docs.ps1`](../scripts/render_docs.ps1).

## Work that must return to the shared package

The next implementation slices cannot be completed by editing the standalone
shell alone:

- Finish global snippets, transforms, spelling, grammar review, and dictation
  command wiring in `quill`.
- Add target-family routing and certification for native controls, browsers,
  terminals, Word, and Outlook.
- Add optional Clipman negotiation and coexistence tests while keeping the
  native-only path independent.
- Run live Windows, browser, Office, clipboard, and screen-reader acceptance.

The detailed requirements and sequencing remain in
[`global-text-support-plan.md`](global-text-support-plan.md). The optional
provider boundary is in
[`clipman-optional-integration.md`](clipman-optional-integration.md).
