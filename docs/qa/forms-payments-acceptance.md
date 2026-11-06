# Forms payment acceptance checklist

Status: automated desktop coverage exists; the live checks below are **not
recorded as passed**. Run against a QAF plugin implementing payment contract
version 1, using Stripe and PayPal sandbox credentials. Record plugin version,
provider environment, browser, screen reader, date, tester and evidence.

## Desktop, in both QUILL and QUILL Lite

- Insert a fixed payment and a bounded donation; undo, save, reopen and check
  that settings and amounts survive. Reject invalid amounts and duplicate fields.
- Reach setup, insert and verify commands from the keyboard. Check labels,
  unique access keys, Tab order, F1 help, Enter/Escape and cancellation.
- With NVDA, JAWS and Narrator, verify focus and results are spoken once and
  brailled; test high contrast and 200 percent display scaling.
- Verify cancel sends no request; Safe Mode blocks verify, publish, test and
  status refresh. Local setup and insertion still work.
- Verify old plugins, authorization failures, unavailable webhooks and mismatched
  test/live mode produce useful refusals. Live-mode confirmation names real money.
- Change only the local document to test mode while the site remains live;
  Test on Site must refuse to open checkout.

## Published checkout, each provider

- Tab into and out of hosted payment fields and PayPal buttons without a trap.
  Verify accessible names, amounts, currency, error messages and focus recovery.
- Complete success, decline, cancellation and additional-authentication flows
  using provider test credentials. Never enter real card details in a test form.
- Verify a browser redirect or PayPal approval alone does not mark an entry paid.
- Check pending and manual-authorization states, successful capture, partial/full
  refunds, and failures. Refresh Payment Status and compare the entry with the
  provider's sandbox record, including amount, currency and transaction ID.
- Repeat submission, deliver a webhook twice and out of order, and send invalid
  signatures. Verify one charge per attempt and no false paid-state transition.
- Reject altered client-side totals, quantities, currency and payment flags.
- Export responses to CSV and Word; inspect metadata and confirm no provider
  secrets or card details appear in responses, exports, logs or error reports.

Only after both provider flows and the assistive-technology checks pass should
a site administrator configure live credentials and publish an explicitly
live-mode form. This checklist itself is not release sign-off.
