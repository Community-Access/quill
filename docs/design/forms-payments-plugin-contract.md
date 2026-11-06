# QAF payment plugin contract, version 1

This is the interface required by QUILL's Stripe/PayPal desktop integration.
The PHP checkout implementation ships separately in the QAF WordPress plugin.
An existing QAF installation is **not** assumed to implement this contract:
QUILL refuses paid-form publication when the capability route is absent,
malformed, unconfigured, or in a different test/live mode.

## Model and publication

The existing form model stays at version 1. Payment configuration lives in
`model.extensions.payments`, sent unchanged as `model` and
`config.form_model` by the existing form create/update routes. BFL carries
the same object in `@extensions`. No new syntax or schema fork is needed.

```json
{
  "providers": ["stripe", "paypal"],
  "currency": "usd",
  "mode": "payment",
  "capture": "automatic",
  "test_mode": true
}
```

Providers are ordered, unique, and limited to `stripe` and `paypal`.
Stripe is the default. Mode is `payment` or `donation`; capture is
`automatic` or `manual`. The optional `statement_descriptor` is at most
22 characters and must also satisfy the provider's own rules.
Credentials, card details and webhook secrets never belong in the model.

Exactly one `payment` field is allowed. Its `props.amount` is a positive
finite number in major currency units, `"donation"`, or `"#field_id"` naming
a `total`, `price`, `calculation`, `number`, or `currency` field. Optional
`donation_min` and `donation_max` are positive numbers, minimum no greater
than maximum. Donation bounds apply only to a donation amount.

The plugin must validate configuration again on publication and on checkout.
Evaluate products, quantities, totals, coupons and references on the server;
never trust a submitted price, currency, total or successful-payment flag.
Use decimal arithmetic and provider currency precision rules, not binary
floating point, to turn major units into provider amounts. Reject unsupported
currencies, capture modes, descriptors and configurations without silently
changing them. A disabled or hidden checkout cannot bypass a required payment.

## Readiness route

Authenticated `GET /wp-json/qaf/v1/payments/settings` returns:

```json
{
  "contract_version": 1,
  "test_mode": true,
  "providers": {
    "stripe": {"configured": true, "webhook_ready": true},
    "paypal": {"configured": false, "webhook_ready": false}
  }
}
```

Only administrators or a dedicated payment-management capability may read
this route. Apply WordPress REST authentication and authorization. Never
return secret keys, access tokens, card data or full provider responses.
`configured` means credentials are verified for the stated environment;
`webhook_ready` means the matching endpoint and verification secret are set
and verified. Do not report readiness merely because a text field is nonempty.
QUILL checks every selected provider and requires an exact boolean mode match.
Legacy `baf/v1` alone does not advertise this payment contract.

All provider credentials, publishable keys and client IDs are configured in
the plugin's WordPress administration screens. QUILL does not write a payment
settings route, keep provider credentials, or call provider APIs directly.
The authenticated WordPress connection remains its only transport.

## Entries

`GET /qaf/v1/entries?form_id=...` may add this object to each entry:

```json
{
  "payment": {
    "provider": "stripe",
    "status": "paid",
    "amount": "25.00",
    "currency": "USD",
    "receipt_url": "https://example.org/receipt",
    "transaction_id": "pi_example"
  }
}
```

Amount is a decimal **string in major units**, never an implicit minor-unit
integer. Status is `pending`, `authorized`, `paid`, `failed`, `cancelled`,
`partially_refunded`, or `refunded`. Missing payment metadata means unknown,
not paid. QUILL displays the reported values without claiming fresh provider
verification; Refresh Payment Status reloads entries from the site.
The desktop retains only the six documented scalar fields, hides metadata
from the response representation, and includes it in deliberate CSV/Word exports.
Receipt URLs are text, not automatically opened by QUILL.

## Checkout and authoritative state

The plugin renders Stripe Payment Element and/or PayPal checkout on the
published HTTPS page. Provider-hosted controls handle payment credentials.
Stripe Payment Intents and PayPal Orders v2 are created on the server, with
environment-specific credentials, idempotency keys, and durable entry/attempt
associations. Prevent duplicate charges on resubmission and concurrent requests.

Verify webhook signatures with the provider's supported verification process,
check account/environment, transaction, currency and amount against the saved
attempt, deduplicate event IDs, and apply transitions atomically. Out-of-order
events must not downgrade a paid or refunded entry to pending. Browser return
URLs and PayPal order approval alone never establish payment completion.
Manual authorization remains `authorized` until capture succeeds. Partial
refunds must not be represented as a complete refund. Checkout failures retain
an intelligible entry state and an accessible retry path.

See [Stripe status verification](https://docs.stripe.com/payments/payment-intents/verifying-status)
and [PayPal webhook verification](https://developer.paypal.com/api/rest/webhooks/rest/).

## Release acceptance

Before claiming checkout support for a plugin release, exercise both providers
in sandbox mode: success, cancellation, decline, additional authentication,
pending/authorized states, duplicate submission, replayed and out-of-order
webhooks, partial/full refunds, and wrong-environment credentials. Check that
no secrets appear in REST replies, logs or exports. Verify keyboard and screen
reader behavior using the [payment checklist](../qa/forms-payments-acceptance.md).
These live plugin/provider checks are separate from QUILL's fake-transport tests.
