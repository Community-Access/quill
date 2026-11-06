# Payments in QUILL Forms: implementation and boundaries

QUILL and QUILL Lite share payment authoring, configuration, site readiness
checks and response reporting. Stripe is the initial provider, with PayPal
available alone or in either display order. New configurations use test mode.

## Implemented desktop path

- `quill/core/forms/payments.py` owns the configuration and semantic rules.
  `model.semantic_errors` combines them with QAF v1's structural rules.
- Existing BFL `@extensions` and field modifiers round-trip payment settings
  without a schema version change. The upstream QAF conformance suite checks
  the original base contract; dedicated payment tests check stricter authoring
  rules, including the rejection of incomplete payment placeholders.
- The shared Forms commands expose Insert Payment Field, Form Payments Setup,
  and Verify Payment Setup. They use the existing accessible native field and
  report dialogs; each field has a label and F1 help. Edits remain local and
  replace the document once, for one undo step. Cancellation preserves it.
- Publish Form names payment mode, currency and providers in its confirmation.
  Before sending a paid form it verifies the plugin contract, selected provider
  readiness, webhook readiness and matching test/live mode.
- Test on Site checks the **published** configuration and refuses live payment
  forms. Local test mode is never evidence that the published form is safe to test.
- Responses show payment status, amount, currency and provider in their accessible
  list rows. Read, CSV and Word exports include the available payment metadata.
  Refresh Payment Status confirms the destination and rereads site entries.
- Network commands use the existing WordPress worker/transport, error reporting,
  credentials and Safe Mode refusal. Local form editing remains available offline.

## Decisions replacing the initial proposal

The initial root-level payment plan proposed a new top-level model key,
additional BFL syntax, desktop provider adapters, and optional desktop secret
storage. The implemented boundary uses the existing extension mechanism and
keeps **all provider credentials and verification in WordPress**. There is no
desktop Stripe/PayPal key store, direct provider API, or payment-settings write
route. This follows the original server-owned checkout decision and avoids
two independent credential/mode configurations.

Payment status is part of each response's existing accessible list row rather
than introducing a second table control. Reusable native dialogs provide the
setup flow; no new custom window class or duplicated Lite implementation is needed.
The Form Payments feature is advanced, depends on Forms and WordPress, and is
off in Essential. Lite follows its existing Forms area visibility.

## External requirements and limits

The QAF PHP plugin must implement the [versioned contract](forms-payments-plugin-contract.md).
This repository does not implement or deploy its checkout, provider APIs or
webhooks. Missing capability is an explicit refusal, not a successful publish.
Live sandbox and assistive-technology acceptance remain required on a compatible
site; unit tests cannot establish that a payment was collected or a hosted field
is accessible. See the [acceptance checklist](../qa/forms-payments-acceptance.md).

Recurring payments, refunds issued from QUILL, multiple checkout fields per
form, and non-WordPress payment hosting are outside this version.

## Verification

Run the Forms core tests, shared authoring/publishing tests and Lite adapter
tests; then run Ruff, scoped mypy, the network-egress and error-code audits,
the Forms/menu/accessibility gates, generated-reference checks, and documentation
artifact checks. Tests use injected sites and do not charge accounts.

The [user guide](../user%20guide/wordpress-and-forms/wordpress-forms-09-forms-on-the-web-and-paper.md)
describes authoring, test mode and entry review.
