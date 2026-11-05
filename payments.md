# Payments in QUILL Forms: Stripe first, PayPal second

This is the pre-implementation design plan for adding real payment collection to
QUILL's accessible forms (QAF) and the WordPress publishing pipeline. Stripe is
the favored, first-class provider; PayPal is the supported secondary. The plan
is grounded in the shipped forms architecture — the QAF model, the BFL source
language, `qaf_site.py` publishing, and the QAF WordPress plugin contract — and
in QUILL's non-negotiable safety model (consent, egress audit, DPAPI secrets,
Safe Mode).

## 1. Why this matters

QUILL's form model already *names* commerce: the field-type registry in
`quill/core/forms/model.py` includes `payment`, `product`, `quantity`, `price`,
`total`, and `coupon`. Today those are schema placeholders — a form author can
declare them, but no money can move. Meanwhile the WordPress publishing path
(`quill/core/forms/qaf_site.py` → QAF plugin REST, `qaf/v1` with `baf/v1`
legacy) is mature: create/update forms, entries retrieval, draft/active status.

Completing payments turns QUILL's screen-reader-first form builder into the only
fully accessible end-to-end order/donation/registration pipeline we know of:
author in BFL, publish to WordPress, take payment through Stripe or PayPal,
review entries with payment status — all keyboard-first.

## 2. Product decisions (fixed)

1. **Stripe is primary.** Default provider for any new payment field; richest
   feature set (Payment Element, Payment Intents, webhooks, test mode).
2. **PayPal is secondary.** Offered as an additional/alternative checkout
   (PayPal Buttons / Orders API v2), never the default unless the author
   explicitly chooses it or Stripe is unconfigured.
3. **Server-side money, client-side nothing.** All provider API calls that
   touch secrets or move money happen in the QAF WordPress plugin (PHP), not
   in QUILL the desktop app. QUILL ships configuration and reads status.
4. **QUILL never stores card data.** PCI scope stays with Stripe/PayPal hosted
   fields. The desktop app and the plugin never see PAN/CVC.
5. **Accessibility is the headline.** The checkout embed must remain usable
   with NVDA/JAWS/Narrator; we prefer Stripe's Payment Element and PayPal's
   accessible button markup, and we document the screen-reader flow.

## 3. Current state (verified in-repo)

- **Model**: `quill/core/forms/model.py` — `MODEL_VERSION = 1`, 64 field
  types including the six commerce types; `semantic_errors()` validates ids,
  structure, expressions, choices. JSON Schema at
  `quill/core/forms/schema/form.schema.json`.
- **BFL**: `bfl_lexer.py` (faithful port of QAF's PHP lexer), `bfl_read.py`
  (source-preserving reader), `bfl_write.py` (canonical emitter),
  `qaf_parser.py` (PHP-oracle parser). Conformance suite under
  `tests/unit/core/forms/fixtures/conformance/` with an optional PHP harness
  (`baf_php_harness.php`).
- **Publishing**: `qaf_site.py` — `publish_body()` sends title, description,
  status, `bfl_source`, and the model under `config.form_model`;
  `create_form()` / `update_form()` POST to `qaf/v1/forms`;
  `list_responses()` maps plugin "entries" to `Response` objects.
- **Transport**: every WordPress call goes through
  `quill/core/wordpress/api.py` (`WordPressApi`, `send_to_site()` is "the one
  place a WordPress site is reached"). Auth kinds: `app_password`, `bearer`
  (WordPress.com), `none`; secrets are repr-hidden.
- **Safety rails**: `quill/tools/network_egress_audit.py` +
  `network_egress_entries.py` (every outbound call site must be reviewed);
  feature catalog privacy strings (`core.wordpress` = "network after
  confirmation", `core.forms` = "Runs on this computer."); DPAPI-backed secret
  stores (`quill/core/secrets.py`, patterned after
  `quill/core/github/token_store.py`); Safe Mode disables network features.
- **No Stripe/PayPal code exists anywhere in the tree today.**

## 4. Architecture

### 4.1 Layering

```
quill/core/forms/payments.py      ← provider-neutral payment config model (new)
quill/core/forms/model.py         ← payment field semantics + validation (extend)
quill/core/forms/schema/*.json    ← schema for payment config (extend)
quill/core/forms/bfl_*.py         ← BFL syntax for payment fields (extend)
quill/core/forms/qaf_site.py      ← publish payment config to plugin (extend)
quill/core/payments/              ← provider adapters: stripe.py, paypal.py (new)
quill/ui/forms_payments_dialogs.py← setup/status dialogs (new)
QAF WordPress plugin (PHP)        ← checkout render, intents/orders, webhooks
```

- `quill/core/payments/` is wx-free and strict-typed (joins the `mypy
  quill/core quill/io` scope automatically).
- Provider adapters talk to Stripe/PayPal **only** for configuration
  validation and status reads initiated by an explicit user action (e.g.
  "Verify keys", "Fetch payment status"). Checkout and money movement stay in
  the plugin.

### 4.2 Payment configuration model (provider-neutral)

New module `quill/core/forms/payments.py`:

```python
PaymentProvider = Literal["stripe", "paypal"]

@dataclass(frozen=True, slots=True)
class PaymentConfig:
    providers: tuple[PaymentProvider, ...]   # ordered; stripe first by default
    currency: str                            # ISO 4217, default "usd"
    mode: str                                # "payment" (one-time) | "donation"
    capture: str                             # "automatic" | "manual"
    statement_descriptor: str = ""
    test_mode: bool = True                   # authors start in test mode
```

Stored in the form model under `model["payments"]` (new reserved top-level
key, version-gated), and per-field options on `payment` fields (amount source:
fixed, `price`/`total` expression, user-entered donation amount with min/max).

Validation joins `semantic_errors()`:

- a `payment` field requires a resolvable amount source;
- `total` fields must reference `price`/`quantity`/`coupon` expressions that
  type-check;
- a form with any `payment` field must carry `model["payments"]` with at least
  one provider;
- currency must be ISO-4217; donation min ≤ max; only one `payment` field per
  form (v1 constraint, matching Stripe one-intent-per-submission).

### 4.3 BFL syntax

Extend the lexer/readers/writer symmetrically (and `qaf_parser.py` for oracle
parity) with payment modifiers, e.g.:

```
payment "Registration fee" amount=total currency=usd providers=stripe,paypal
product "T-shirt" price=25.00
quantity "How many?" min=1 max=10
total "Order total"
```

Round-trip (`bfl_read` → model → `bfl_write`) must be byte-stable; add
conformance fixtures mirroring the existing suite layout.

### 4.4 Plugin REST contract (QUILL ↔ QAF plugin)

Extend `publish_body()` so `config.form_model` carries `payments`. Add new
narrow routes (plugin side, with QUILL clients in `qaf_site.py`):

- `GET  /qaf/v1/payments/settings` — which providers the site has configured
  (publishable key presence, PayPal client-id presence, webhook health),
  **never returning secrets**.
- `POST /qaf/v1/payments/settings` — set Stripe publishable key, PayPal
  client id, provider order, test/live mode. Secret keys (Stripe secret,
  PayPal secret) are set **on the WordPress side only** (wp-admin page the
  plugin provides); QUILL can send them optionally over the authenticated
  REST channel but the default documented flow keeps secrets in wp-admin.
- `GET  /qaf/v1/entries?form_id=…` — entries gain `payment` metadata:
  `{provider, status, amount, currency, receipt_url, transaction_id}`.

Plugin responsibilities (spec'd here, implemented in the QAF plugin repo):
Stripe Payment Intent creation on submit, Payment Element render inside the
form block, webhook endpoint for `payment_intent.succeeded` /
`checkout.session.completed`; PayPal Orders v2 create/capture + webhook; entry
state machine `pending → paid | failed | refunded`.

### 4.5 QUILL-side provider adapters

`quill/core/payments/stripe.py`, `quill/core/payments/paypal.py`:

- `verify_credentials()` — explicit user action "Verify keys" calls
  Stripe `GET /v1/balance` (secret key, only when the user chose to manage
  secrets from QUILL) or validates publishable-key shape offline; PayPal
  OAuth token round-trip.
- `fetch_payment_status(transaction_id)` — status read for the Responses
  window, explicit "Refresh payment status" action.
- Both call sites registered in `quill/tools/network_egress_entries.py` with
  trigger + consent rationale; both refuse in Safe Mode; both route errors
  through `CodedError` subclasses (`QUILL-PAY-STRIPE-*`, `QUILL-PAY-PAYPAL-*`).
- Transport: stdlib `urllib` over the existing verified-SSL helpers (no new
  runtime dependency on `stripe`/`paypalrestsdk` SDKs — the two calls we make
  are trivial REST and the SDKs would bloat the audit surface).

### 4.6 Secrets

- New DPAPI-backed stores patterned on `github/token_store.py`:
  `quill/core/payments/key_store.py` holding (per provider, per site):
  publishable/client id (non-secret, plain settings) and optionally the
  secret key (DPAPI; only if the author opts to manage secrets from QUILL).
- Secrets never enter the form model, BFL source, logs, `repr`, or crash
  reports (extend `quill/stability/redaction.py` patterns for `sk_live_`,
  `sk_test_`, `rk_`, PayPal client secrets).

### 4.7 Feature gating and consent

- New feature `core.forms_payments` in `feature_catalog.py`: label "Form
  Payments", `maturity="advanced"`, privacy "network after confirmation",
  dependencies `("core.forms", "core.wordpress")`, default off in Essential.
- Payment setup/verify/status actions each show explicit confirmation naming
  the destination (Stripe/PayPal/site), mirroring "Nothing reaches a site
  without Save Draft to Site or Publish."
- Safe Mode refuses all payment network actions with the standard message
  shape.

### 4.8 UI flows (QUILL and QUILL Lite, shared commands)

Commands live in shared `FormsCommands` so QUILL Lite gets them through
`LiteWordPressHost` with zero divergence (family rule 10):

1. **Insert Payment Field** — palette/menu insert of `payment`/`product`/
   `quantity`/`total`/`coupon` BFL stanzas with guided prompts.
2. **Form Payments Setup…** — dialog: provider order (Stripe default),
   currency, mode, test/live toggle, publishable key / client id fields,
   "Verify keys" button, link to wp-admin secrets page. Native-first dialog,
   `dialog_contract` compliant, every control labeled + `SetHelpText`.
3. **Test Payment on Site** — opens the published form in the browser in test
   mode with Stripe test-card guidance announced and documented.
4. **Responses window** — new Payment column (status, amount, provider);
   "Refresh payment status" action; CSV export includes payment metadata.

### 4.9 Accessibility acceptance

- Document the NVDA flow through Stripe Payment Element and PayPal buttons on
  the published page (docs/qa checklist addition, manual pass).
- QUILL-side dialogs covered by the standard gates: dialog inventory snapshot,
  access keys, menu accelerators, F1 help, announce-only-what-the-SR-doesn't.

## 5. Implementation phases

### Phase 1 — core model + BFL (no network)
- `quill/core/forms/payments.py` (config model + validation)
- `model.py` semantic rules, `form.schema.json` payments block
- BFL lexer/read/write/oracle-parser support + conformance fixtures
- Round-trip and schema tests

### Phase 2 — publish transport + plugin contract
- `qaf_site.py`: payments in `publish_body()`, payments-settings client,
  entries payment metadata mapping into `Response`
- Contract doc for the plugin (`docs/design/forms-payments-plugin-contract.md`)
  specifying routes, payloads, webhook behavior, entry state machine
- Payload tests against recorded fixtures

### Phase 3 — provider adapters + secrets
- `quill/core/payments/{stripe,paypal,key_store}.py`
- Egress audit entries, redaction patterns, Safe Mode refusal, CodedErrors
- Unit tests with fake transports (no live network in tests)

### Phase 4 — UI
- Setup dialog, insert commands, responses payment column, test-on-site flow
- Dialog inventory + dialogs.md + access-key + F1 gates
- Source-contract and behavior tests; QUILL Lite parity via shared commands

### Phase 5 — docs + release
- User guide section (author a paid form end-to-end, Stripe test cards)
- Feature catalog copy, changelog, release notes
- WordPress regression checklist additions (docs/qa)

## 6. Testing strategy

- Model/validation: table-driven tests beside existing
  `test_forms_model_json.py` patterns; invalid-config fixtures.
- BFL: round-trip byte-stability + conformance fixture pairs (`.bfl` ↔
  `.model.json`) in the existing fixture layout.
- Publishing: `publish_body()` golden payloads; entries-with-payment mapping.
- Adapters: injected fake `urlopen`/transport; assert no call without the
  explicit-action flag; Safe Mode refusal tests.
- Gates: `ruff`, scoped `mypy` (new core modules are strict), egress audit,
  dialog inventory, access keys, F1 help audits all green.

## 7. Out of scope (v1)

- Subscriptions/recurring billing (Stripe Billing) — v2.
- Apple Pay/Google Pay wallets beyond what Payment Element enables by default.
- Refund issuance from QUILL (status display only; refunds happen in the
  provider dashboard; entry status reflects webhooks).
- Multi-payment forms (more than one `payment` field).
- Non-WordPress form hosting.

## 8. Risks and mitigations

- **Plugin repo is separate** — the PHP side ships from the QAF plugin
  project. Mitigation: Phase 2 contract doc is the source of truth; QUILL
  features degrade gracefully (payments config publishes; if the plugin
  predates payments, the settings route 404s and QUILL reports "the site's
  QAF plugin does not support payments yet — update the plugin").
- **Provider API drift** — keep the QUILL-side surface tiny (verify + status)
  so drift risk concentrates server-side where the plugin pins API versions.
- **Accessibility of hosted fields** — Stripe Payment Element is the most
  screen-reader-tested option; the acceptance checklist verifies it per
  release.

## 9. Attribution and narrative

Release notes present this as the forms family growing into commerce:
"QUILL Accessible Forms can now take payment — Stripe first, PayPal too —
with the same keyboard-first, screen-reader-first discipline as the rest of
the product." Forms/QAF lineage (BAF → QAF) is already credited in-tree; no
new third-party design attribution is required beyond Stripe/PayPal trademark
usage in docs.
