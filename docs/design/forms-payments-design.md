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
- The authoring rules match the plugin's, so a site refusal after a clean
  Check This Form is rare. Since 2026-11-07 that includes amounts with more
  decimal places than the currency has (refused, never rounded: `10.005` USD,
  `2000.5` JPY) and the statement descriptor's floor and character set (5 to
  22 printable ASCII characters with at least one letter).
- The shared Forms commands expose Insert Payment Field, Form Payments Setup,
  and Verify Payment Setup. They use the existing accessible native field and
  report dialogs; each field has a label and F1 help. Edits remain local and
  replace the document once, for one undo step. Cancellation preserves it.
  Insert Payment Field's Amount help lists the form's own amount fields
  (`payments.amount_sources`), so an author need not remember an id.
- Publish Form names payment mode, currency and providers in its confirmation.
  Before sending a paid form it verifies the plugin contract, selected provider
  readiness, webhook readiness and matching test/live mode.
- Test on Site checks the **published** configuration and refuses live payment
  forms. Local test mode is never evidence that the published form is safe to test.
  When it opens a test-mode payment form it says the published test card for
  Stripe and the sandbox account for PayPal, for the providers that form uses.
- Responses show payment status, amount, currency and provider in their accessible
  list rows, in words ("partly refunded", "PayPal") rather than the plugin's codes.
  Read and Word exports use the same words; CSV keeps the codes, which sort and
  filter. Refresh Payment Status confirms the destination and rereads site entries.
- Network commands use the existing WordPress worker/transport, error reporting,
  credentials and Safe Mode refusal. Local form editing remains available offline.
- The diagnostic redaction rules cover the payment secrets a pasted site error
  could carry (Stripe `sk_`, `rk_live_`/`rk_test_`, `whsec_`; PayPal `A21AA`
  access tokens), although QUILL holds none of them.

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

With that boundary, the plan's remaining desktop items were closed on
2026-11-07: the test-card guidance from Test on Site (plan 4.8, item 3), the
redaction patterns (plan 4.6), the plugin's precision and descriptor rules on
the desktop, and payment status in words. The plan's adapters, key store and
egress entries are not built, by the decision above.

## The plugin side

The QAF plugin implements contract version 1 on its branch `feat/qaf-payments`
(local to the plugin repository; not yet released or tried on a live site):

- `GET qaf/v1/payments/settings`, administrators or `qaf_manage_payments`
  only, booleans and the mode, never a key. A provider counts as configured
  only after Check Connection succeeded for the exact keys stored now (the
  check is tied to a hash of them), and its webhook as ready only after the
  site created the endpoint or verified a signed event.
- Payment settings validated in `QAF_Form::set_model`, so every way a model
  reaches the site is checked, and again at checkout.
- Amounts worked out on the server from the model: fixed amounts, donations
  with bounds, number fields, and totals from products, linked quantities,
  coupons, shipping, tax and calculations, ignoring any submitted total,
  price, currency or paid flag. Integer minor units; extra precision refused.
- Stripe Payment Intents with the Payment Element, PayPal Orders v2 with
  server-side capture or authorization, both over REST with idempotency keys
  per attempt. A resent page reuses its entry and attempt.
- Webhooks verified (Stripe signing secret with a five-minute window; PayPal
  verify-webhook-signature over the exact bytes), recorded once, matched to
  the attempt's environment, amount and currency, and applied through a
  transition table with compare-and-set writes. Late or replayed events
  cannot downgrade paid or refunded entries; partial refunds stay partial.
- `qaf_payment_paid` fires once per paid entry, for fulfilment.
- wp-admin QAF Forms > Payments: write-only secrets (or constants in
  `wp-config.php`), test and live mode with a confirming check box, Check
  Connection, Create Webhook, readiness, and a payments report with totals.
- The plugin's own admin guide is `docs/payments-admin-guide.md` in its
  repository.

## External requirements and limits

This repository does not implement or deploy the checkout, provider APIs or
webhooks; the plugin does, under the [versioned contract](forms-payments-plugin-contract.md).
Missing capability is an explicit refusal, not a successful publish.
Live sandbox and assistive-technology acceptance remain required on a compatible
site; unit tests on either side cannot establish that a payment was collected
or a hosted field is accessible. See the [acceptance checklist](../qa/forms-payments-acceptance.md).

Recurring payments, refunds issued from QUILL, multiple checkout fields per
form, and non-WordPress payment hosting are outside this version.

## Verification

Run the Forms core tests, shared authoring/publishing tests and Lite adapter
tests; then run Ruff, scoped mypy, the network-egress and error-code audits,
the Forms/menu/accessibility gates, generated-reference checks, and documentation
artifact checks. Tests use injected sites and do not charge accounts. The
plugin's payment tests (`tests/unit/Payments/` in its repository) use fake
provider transports and never reach Stripe or PayPal.

Chapter 18 of the [QUILL user guide](../user%20guide/quill-guide/quill-guide-18-taking-payments.md),
"Taking payments with your forms", and Chapter 16 of QUILL Lite's teach the
whole process. The shorter [manual section](../user%20guide/wordpress-and-forms/wordpress-forms-09-forms-on-the-web-and-paper.md)
describes authoring, test mode and entry review.
