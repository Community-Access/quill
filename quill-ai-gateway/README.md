# QUILL AI Gateway

A small, boring, private Flask service that lets the open-source [QUILL](https://github.com/Community-Access/quill)
desktop client offer free, hosted AI features **without ever embedding a
shared provider API key in the open-source client**.

**Read these first, in this order:**

1. [`quill-ai-gateway-spec.md`](../docs/Product%20Requirement%20Documents%20and%20Specifications/quill-ai-gateway-spec.md)
   — the current plan and the authority on every
   number, the deployment runbook (section 14), and the task list (section
   16). Where it and the PRD disagree about a value, this document wins.
2. [`../docs/planning/openai.md`](../docs/planning/openai.md) — the original
   product requirements document, and still the authority on *why* the
   architecture looks the way it does.

This README is the *how to run it*. If something here seems arbitrary, one of
those two almost certainly explains the reasoning.

## The one-sentence version

QUILL's desktop client holds a QUILL-issued token, never an OpenAI key;
this service is the only thing that ever holds the real key, it checks a
user's quota *before* every OpenAI call rather than after, and it never
charges anybody for a request that did not happen.

## Architecture at a glance

```
QUILL desktop client
      │  HTTPS, Bearer <gateway-token>
      ▼
This Flask app  ──────────────────────────►  OpenAI (GPT-6 Luna)
      │                                       no tools, no web search, ever
      ├── PostgreSQL   (users, devices, usage history, admin config)
      └── Redis        (rate-limit counters, config cache, pending sign-ins)
```

**Five features**, all of them working on a passage the user selected or a
question about a document they have open: summarize, rewrite, proofread,
explain, and questions-about-documents. Open-ended chat and describing
pictures both exist as ids in the schema and ship **switched off**, each with
a stored reason the refusal path actually shows — "this was never built" and
"temporarily paused" are completely different facts, and confusing them sends
somebody to support over a feature that does not exist.

**This service sends no email.** No SMTP, no mail provider, nothing that needs
one. Sign-in is the device-code flow, so there is no address to verify and no
password to reset; alerts go to a webhook. See `quill-ai-gateway-spec.md`
section 14.3.

- **`app/config.py`** — every environment variable this service reads, and
  nothing else. Read this to see exactly what a deployment must configure.
- **`app/models.py`** — the full data model (matches PRD §5 exactly).
- **`app/auth.py`** — OAuth 2.0 Device Authorization Grant (RFC 8628) sign-in,
  matching QUILL's existing `device_login.py`/`copilot_auth.py` client-side
  pattern, plus the bearer-token verification every route depends on.
- **`app/limits.py`** — the quota engine. **Every number a user can hit a
  limit on lives here**, and every one of those numbers is admin-tunable
  live from `gateway_config` (see below) — nothing is a hardcoded constant
  except the fail-safe defaults used only if the config table is empty.
- **`app/model_registry.py`** — which OpenAI models are turned on, and
  which one is the active default. An admin can add a model, disable one
  that's misbehaving, or switch the default, all without a deploy.
- **`app/prompts.py`** — the fixed, server-side-only system prompt per
  feature, **and how hard the model may think about it**. The client only
  ever supplies a user prompt or question, never a system prompt — that is
  what stops a modified client smuggling an unapproved use through an
  approved feature. Reasoning effort is in this file for the same reason and
  is the more expensive one to get wrong: reasoning tokens bill at the output
  rate and never appear in the answer, so a model left at its provider's
  default roughly **doubles the entire bill** invisibly.
- **`app/config_schema.py`** — what every tunable limit *means* in plain
  language, and what it may be set to. This is what stops `0.15` typed as
  `15` raising every user's cost ceiling a hundredfold behind a green success
  message, and what lets the console group and explain limits instead of
  listing raw database keys.
- **`app/costing.py`** — what the current settings actually cost, and what a
  proposed change would cost. Every figure derives from the Models page's
  price columns, which are what this gateway was *told* the provider charges,
  not what it charges.
- **`app/openai_client.py`** — the *only* place this codebase ever talks to
  OpenAI. If you are auditing "does the key ever leak", this is the one file
  to check. It is also where the outgoing request body is built, and that
  body is a fixed allowlist of four keys: `model`, `messages`,
  `max_completion_tokens`, `reasoning_effort`. No tools, no web search, no
  file search, no attachments. `tests/test_openai_request_shape.py` fails the
  build if anything else appears — web search alone bills at $10 per thousand
  calls, which on this traffic would be roughly sixteen times the entire rest
  of the bill.
- **`app/routes/`** — the four blueprints: `device` (auth), `chat` (the one
  inference endpoint), `client_config` (read-only config/quota for the
  client's status display), `admin` (everything an operator needs).
- **`app/cli.py`** — operational commands (`init-db`, `seed-config`,
  `check-config`, `cleanup-expired`, `reconcile-usage`). Run `check-config`
  after every deploy: it reports out-of-range limits, a budget cap that normal
  use can reach, a missing default model, and an unconfigured alert webhook,
  and exits non-zero so it can be a deploy step rather than something somebody
  remembers.

## Quick start (local development)

```bash
cd quill-ai-gateway
python -m venv .venv
.venv/Scripts/activate        # or: source .venv/bin/activate on macOS/Linux
pip install -r requirements-dev.txt

cp .env.example .env
# Edit .env: set a real OPENAI_API_KEY and a generated GATEWAY_SECRET_KEY.
# For local dev, DATABASE_URL can point at a local Postgres, or you can
# skip Postgres entirely for a quick look by using SQLite:
#   DATABASE_URL=sqlite:///dev.db
# Redis is required even locally -- run one with Docker if you don't have
# it installed: docker run -p 6379:6379 redis

flask --app run.py init-db
flask --app run.py seed-config
flask --app run.py run              # or: python run.py
```

Register your own device (so you can reach `/admin/*`):

1. `curl -X POST http://localhost:5000/v1/device/code` — note the `user_code`.
2. Visit `http://localhost:5000/connect?code=<user_code>` in a browser,
   click Confirm.
3. `curl -X POST http://localhost:5000/v1/device/token -d '{"device_code": "<device_code>"}' -H 'Content-Type: application/json'`
   — note the `device_id` in the response.
4. Add that `device_id` to `GATEWAY_ADMIN_ALLOWLIST` in `.env`, restart.

## The admin dashboard (no file editing, no `curl` required)

Once you have an admin device id in `GATEWAY_ADMIN_ALLOWLIST` (above),
open `http://localhost:5000/dashboard/` in a browser. Sign in by pasting
the same bearer token your device registered with (this is *not* a
second password — see `app/dashboard_auth.py`'s docstring). From there:

- **Overview** — this month's spend against the budget cap, a monthly
  request-volume trend, and account totals.
- **Models** — turn a model on or off, or change which one is the active
  default.
- **Limits** — every `gateway_config` row, editable, live (no restart).
- **Users** — view usage, set a user's status (active/reduced/review/
  blocked — reversible), or permanently remove a user.
- **Feature flags** — pause one feature, or hit the global "Hosted AI"
  kill switch.
- **Audit log** — every admin action taken anywhere (API or dashboard),
  who did it, and when.
- **Safety checks** — the protections that are not rows in a table, and
  whether they are holding: the no-tools gate, the no-charge-for-nothing rule,
  sign-up throttling, the budget auto-pause, whether alerts actually reach a
  human, and when the scheduled jobs last ran.
- **Fixed by code** — everything that affects cost or safety and is
  deliberately *not* editable here, shown read-only with the reason and the
  file: reasoning effort per feature, all five prompt templates verbatim, and
  the outgoing-request allowlist. A protection an operator cannot see is one
  they will assume is missing.

The dashboard is plain, server-rendered HTML — no JavaScript, no build
step, fully keyboard- and screen-reader-operable. See
`docs/planning/openai.md`'s dashboard section for the full accessibility
rationale (it follows this project's dataviz skill: status colors are
never the only signal, every chart has a data-table twin, focus is always
visible).

## Running the tests

```bash
cd quill-ai-gateway
pip install -r requirements-dev.txt
pytest
```

The suite uses an in-memory SQLite database and `fakeredis` — no external
services required (see `tests/conftest.py`). **141 tests** cover the quota
engine, the large-document safeguards, the device-code auth flow, the model
registry, the admin API, the admin dashboard, and four things worth naming
because each one was a live bug:

- `test_openai_request_shape.py` — the outgoing body never grows a `tools` key.
- `test_refunds.py` — nobody is charged for a request that did not happen. The
  counters increment *before* the size check, the model lookup and the
  upstream call, so all four failure paths refund.
- `test_signup_protection.py` — registration throttling and the new-account
  ramp, including that the ramp can never give a new account a *larger*
  allowance than an established one.
- `test_config_guardrails.py` — `0.15` typed as `15` is refused with a
  sentence, and a change that more than doubles the bill needs explicit
  confirmation.

## Deployment

Recommended: **the same server already running GLOW**, using the exact
same shape GLOW's `web/` service already proves out on that host --
Docker Compose + Caddy reverse proxy (see `/s/code/glow/web/` for the
precedent this mirrors: `docker-compose.yml`, `Caddyfile.example`,
`.env`-file secret injection).

```bash
cp .env.example .env
# Fill in OPENAI_API_KEY, GATEWAY_SECRET_KEY, GATEWAY_ADMIN_ALLOWLIST,
# and set POSTGRES_PASSWORD (used only by docker-compose.yml's postgres
# service; not read by the app itself, which uses DATABASE_URL).

docker compose up -d --build
docker compose exec web flask --app run.py init-db      # first deploy only
docker compose exec web flask --app run.py seed-config  # first deploy only; safe to re-run
```

Then append `Caddyfile.example`'s block to the Caddy instance already
terminating TLS for GLOW on this host, and `caddy reload`.

**Without Docker** (a plain Gunicorn process, if that's a better fit for
this host):

```bash
pip install -r requirements.txt
flask --app run.py init-db      # first deploy only
flask --app run.py seed-config  # first deploy only; safe to re-run later
gunicorn -w 2 -b 127.0.0.1:8001 'app:create_app()'
```

and point the reverse proxy at `127.0.0.1:8001` instead of a Docker
service name.

### A nicer admin login later: Keycloak

The dashboard's v1 login (README above: "paste your admin token") is
deliberately the simplest thing that works today. GLOW already runs a
Keycloak instance on this server for its own admin login
(`/s/code/glow/web/docker-compose.keycloak.yml`) — wiring the dashboard
into that same realm as an OIDC client is the natural upgrade once a
nicer login screen (SSO, no token-pasting) is worth the added
complexity. Not built yet; `app/dashboard_auth.py`'s docstring notes this
as the intended next step.

**Secrets:** set `OPENAI_API_KEY`, `GATEWAY_SECRET_KEY`, `DATABASE_URL`,
and `GATEWAY_ADMIN_ALLOWLIST` through whatever mechanism already injects
secrets for GLOW/`quillin-hub` on this host — an environment file kept
outside any git-tracked directory, or the platform's secret store if it's
a managed one. **Never** commit a filled-in `.env`. See PRD §6 for the
full secret-management plan, including the key-rotation runbook.

### Running scheduled jobs

Add to cron (adjust paths/venv activation for your setup):

```cron
# Daily: delete expired diagnostic records (PRD §4.4 retention).
0 3 * * * cd /path/to/quill-ai-gateway && .venv/bin/flask --app run.py cleanup-expired

# Nightly: reconcile monthly_usage_summary against the durable event log,
# in case a crash ever left the running aggregate slightly behind
# (app/limits.py::record_usage's docstring explains why this is a safety
# net, not a routine necessity).
30 3 * * * cd /path/to/quill-ai-gateway && .venv/bin/flask --app run.py reconcile-usage
```

Partition maintenance for `usage_events` (production/Postgres only) is a
manual monthly task — see `migrations/README.md`.

## Operating the service day to day (the admin API)

Every route below requires `Authorization: Bearer <your-admin-device-token>`,
and your device must be in `GATEWAY_ADMIN_ALLOWLIST`.

| I want to... | Call |
|---|---|
| See every configured model | `GET /admin/models` |
| Turn a model off (e.g. it's misbehaving) | `PUT /admin/models/<model_id>/enabled` `{"enabled": false}` |
| Add a new model and make it the default | Insert a `gateway_models` row (see `migrations/002_seed_gateway_config.sql` for the shape), then `PUT /admin/models/<model_id>/default` |
| Change a limit (e.g. raise the monthly cap once traffic looks safe) | `GET /admin/config` to see current values, then `PUT /admin/config/<key>` `{"value": <number>}` |
| See how much one user has used | `GET /admin/users/<user_id>/usage` |
| Turn off a user's hosted-AI access (reversible) | `PUT /admin/users/<user_id>/status` `{"status": "blocked", "reason": "..."}` |
| Permanently remove a user | `DELETE /admin/users/<user_id>` |
| Revoke one of a user's devices | `PUT /admin/devices/<device_id>/status` `{"status": "revoked"}` |
| Pause one feature (e.g. images) while keeping others on | `PUT /admin/feature-flags/alt_text` `{"enabled": false, "reason": "..."}` |
| **Pause everything** (the emergency kill switch) | `PUT /admin/feature-flags/hosted_ai` `{"enabled": false, "reason": "..."}` |
| Check current spend against the budget cap | `GET /admin/spend` |
| **Find someone from the support ID they quoted** | `GET /admin/users?q=A1B2` |
| **Give someone their allowance back** | `POST /admin/users/<user_id>/usage/reset` `{"reason": "..."}` |
| **Give someone different limits** | `PUT /admin/users/<user_id>/caps` `{"monthly_request_cap": 250}` (null clears an override) |
| **Replace a device's token without signing it out** | `POST /admin/devices/<device_id>/rotate` |
| **Check the provider key actually works** | `POST /admin/test-key` |

Two of those deserve a note.

**Reset** clears the Redis request counters *and* the running cost total in one
transaction. Doing either alone produces a reset that appears to have silently
failed: counters alone leaves the per-user cost ceiling still refusing them,
cost alone leaves them still out of requests. It deliberately does **not** touch
the global spend counter — that money was really spent, and a per-person
courtesy must never quietly edit the number the budget cap protects everybody
with.

**Config writes are range-checked**, and a change that more than doubles the
modelled monthly bill is refused with `409 needs_confirmation` unless you send
`"confirm": true`. A script that really means it says so; a mistyped decimal
point does not.

Every one of these writes an `admin_actions` audit row — "who did what and
when" is always answerable later (`SELECT * FROM admin_actions ORDER BY
created_at DESC`).

## The "start small and learn" philosophy

This service ships with deliberately conservative initial-rollout limits
(100 requests/user/month, a $25/month global budget cap — see PRD §8.1 and
§13 for the full reasoning). **Every one of those numbers is a
`gateway_config` row, not a constant in code** — raising them as the
service proves itself safe in production is a `PUT /admin/config/<key>`
call, never a code change or a redeploy.

## Full API reference

See PRD §24 for the complete request/response contract (every endpoint,
every status code, every error shape) that this codebase implements.
