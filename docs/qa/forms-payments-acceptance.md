# Forms payment acceptance checklist

Status: automated desktop coverage exists, and the QAF plugin's branch
`feat/qaf-payments` has automated coverage of every contract clause against
fake provider transports. The live checks below are **not recorded as
passed**: no WordPress site has run that branch yet. Run against a QAF plugin
implementing payment contract version 1, using Stripe and PayPal sandbox
credentials. Record plugin version, provider environment, browser, screen
reader, date, tester and evidence.

## On the site, before any form

- In wp-admin, QAF Forms > Payments: every key field has a visible label and
  its hint is read with it; each provider and environment is a fieldset with
  a legend; the readiness table has a caption and header cells; the notice
  after Save, Check Connection or Create Webhook takes focus and is read.
- Save a secret, reload, and confirm the page says only "Saved", with no part
  of the secret in the field, the page source or the REST replies. Remove it
  with its Remove check box.
- Check Connection with a live key saved under test (and the reverse) says
  the key belongs to the other environment. Choosing Live without the
  confirming check box changes nothing.
- Create Webhook for each provider in sandbox; confirm the endpoint appears in
  the provider's dashboard with this site's address, and that the readiness
  table and Verify Payment Setup then say ready.
- A user without `manage_options` or `qaf_manage_payments` gets a refusal from
  `GET /wp-json/qaf/v1/payments/settings` and cannot open the page.

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
- Test on Site on a test-mode form says the test card (Stripe) and sandbox
  account (PayPal) for the providers that form uses, and no others.
- Insert Payment Field's Amount help (F1) names the form's amount fields.
  An amount finer than the currency (`10.005` USD) is refused with a reason.
- Responses read each payment in words ("partly refunded", "PayPal"), and CSV
  keeps the plugin's codes.

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
- With a screen reader, from the keyboard alone: the payment field reads its
  amount and currency; a donation box reads its limits; after sending, focus
  lands on the "Pay" heading; progress comes from the status line, failures
  from the alert, each once; the provider radio buttons and the Pay, Try
  again and Check payment again buttons work with Space and Enter; nothing
  is conveyed by colour alone. Repeat in Windows high contrast.
- Return from a 3-D Secure redirect and confirm the panel says "Welcome back.
  Checking your payment." and then the result.
- A donation below the minimum, a coupon code the form does not take and a
  quantity above its maximum are each refused before saving, with the message
  on the field.
- Switch from card to PayPal after starting a card payment: the Stripe intent
  is cancelled in the dashboard before the PayPal order is made.

Only after both provider flows and the assistive-technology checks pass should
a site administrator configure live credentials and publish an explicitly
live-mode form. This checklist itself is not release sign-off.
