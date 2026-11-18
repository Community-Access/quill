# QAF payment plugin contract, versions 1 and 2

This is the interface required by QUILL's Stripe, PayPal and Square desktop
integration. Version 1 is Stripe and PayPal with one connection each.
Version 2 (2026-11-18) adds Square as a third provider and any number of
named **connections** per provider, chosen by the payer or by rule; it is
described under [Version 2](#version-2-square-and-connections) below, and
everything in version 1 still holds.
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

## Version 2: Square and connections

### Square

`square` joins `stripe` and `paypal` in `providers`. Square takes `usd`,
`cad`, `gbp`, `aud`, `jpy` and `eur`, and a location charges only in its own
country's currency, which the plugin checks against the connection's
location at publication. A Square `statement_descriptor` (sent as
`statement_description_identifier`) is at most 20 characters. The smallest
card payment is one minor unit.

The plugin renders Square's Web Payments SDK card field, creates the payment
with the Payments API (`POST /v2/payments`) on the server with an idempotency
key per attempt, sets `autocomplete` from `capture`, confirms and reconciles
with the `payment.updated` and `refund.updated` webhooks (verified with the
subscription's signature key over the notification URL and the exact body,
`x-square-hmacsha256-signature`), and refunds through the Refunds API. The
sandbox and production environments each have their own application id,
access token, location id and signature key, kept in the site's options or
`wp-config.php`, never in the form.

### Connections

A connection is one set of credentials for one provider, with its own name,
mode, currency and descriptor. A form names a connection by **reference**:

- the bare provider (`stripe`, `paypal`, `square`) for that provider's
  default connection, which is what every version 1 form uses; or
- the provider, a colon and a slug (`stripe:events`, `square:downtown`):
  lower-case letters, digits and hyphens, at most 40.

The provider is in the reference so the desktop can check currencies and
descriptors offline.

### Choosing a connection

`model.extensions.payments` may hold either of these, never both:

```json
{"connections": ["stripe:events", "paypal", "square:downtown"]}
```

By selection: the payer chooses, in this order, only when more than one is
offered; the first is the default. A connection that is not ready is not
offered.

```json
{
  "rules": [
    {"when": {"amount_over": "500"}, "use": "stripe:large-gifts"},
    {"when": {"field": "fund", "equals": "building"}, "use": "square:building"},
    {"when": {"currency": "cad"}, "use": "stripe:canada"},
    {"when": {"from": "2026-12-01", "until": "2026-12-31"}, "use": "stripe:campaign"}
  ],
  "otherwise": "stripe:events"
}
```

By rule: checked in order on the server against the submitted answers and
the amount the server worked out; the first match takes the payment. A rule
whose connection is not ready is skipped, and `otherwise` is required, so a
payment always has somewhere to go. Amounts are decimal strings in major
units, compared exactly. `field`/`equals` matches a choice's value or label.
Dates are the site's local calendar day, both ends inclusive and either end
optional.

`providers` is still written, as the providers those connections belong to,
so a version 1 plugin reading a version 2 form falls back to each provider's
default connection. QUILL refuses to publish a form that names connections
or rules to a version 1 site.

### Readiness route

Version 2 returns `"contract_version": 2`, `square` under `providers`, and:

```json
{
  "connections": [
    {"id": "stripe:events", "name": "Stripe: Events", "test_mode": true,
     "configured": true, "webhook_ready": true}
  ]
}
```

Each provider's default connection is listed too, under its bare reference.
No key, token, location id or signature key is ever in a row; QUILL keeps
only these six fields from each. QUILL refuses to publish when a referenced
connection is missing, not ready, or in a different mode from the form: a
form never mixes test and live connections.

### Entries, refunds and safety

The entry's `payment` object gains `connection` (the reference that took the
money) and `connection_name`. Reports group by connection, and a refund goes
back through the connection that took the payment, never the form's current
one. The plugin refuses to delete a connection that a published form uses,
naming the forms, and shows which forms a change to a connection affects
before saving it.
