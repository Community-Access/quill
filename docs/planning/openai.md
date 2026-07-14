# The QUILL AI Gateway — Product Requirements Document

**Status:** Draft PRD, v1.0. **Author:** Claude Fable 5. **Date:** 2026-07-05.
**Scope:** Initial rollout (100 requests/user/month, document Q&A only,
single Flask service on Jeff's existing server) plus the scaling path
toward a broader public beta. Grounded in QUILL's actual current AI code
(cited throughout as `file.py:function`), not a generic proposal. A
reference implementation of the API contract in §24 lives in
`quill-ai-gateway/` at the repository root.

**Document map:** §0 grounds every decision in existing QUILL code. §1–3
are the product case and architecture. §4–5 are privacy and data. §6–12
are security, auth, and BYOK. §13–15 are cost, document handling, and
images. §16 is the stack decision. §17–21 are UX, phases, risks. §22–23
are the launch checklist and defaults recap. §24 is the API contract the
Flask implementation follows exactly.

**One-line thesis:** QUILL's desktop client never holds a shared provider
key. It holds a QUILL-issued token. The QUILL AI Gateway is the only thing
that ever talks to OpenAI, and it enforces every quota, budget, and kill
switch server-side because the client — being open source — cannot be
trusted to enforce anything about itself.

---

## 0. Where this plugs into QUILL today (read this first)

QUILL already has the exact seam a hosted backend needs, and reusing it is
most of the client-side work:

- **`AIBackend` ABC** (`quill/core/ai/backend.py`) — `is_available() ->
  (bool, str|None)`, `respond(prompt) -> str`, `respond_stream(prompt,
  on_delta)`. Every feature (`assistant.py`, `document_qa.py`, `vision.py`,
  `conversation.py`, `chat_session.py`, `agent_tools.py`) already calls
  through this interface or through `assistant_ai.generate_assistant_response`,
  which `ProviderChatBackend` wraps. **A `GatewayBackend(AIBackend)` is a
  drop-in fourth option** in `Assistant.make_default_backend()`'s cascade
  (`assistant.py:104`), sitting next to `ProviderChatBackend`,
  `SimpleChatBackend`, `FoundationModelsBackend`, `LlamaCppBackend`.
- **Provider catalog** (`quill/core/ai/providers.py`) — `ALL_PROVIDERS`,
  `default_host_for_provider`, `provider_requires_api_key`. Add
  `"quill_gateway"` as a new provider id here rather than inventing a
  parallel settings surface. It's the provider that needs *no* user-supplied
  API key (`provider_requires_api_key("quill_gateway") == False`) but *does*
  need a Gateway session token.
- **Credential storage** (`quill/core/assistant_ai.py`) — Windows Credential
  Manager first, DPAPI-encrypted JSON fallback
  (`save_provider_api_key`/`load_provider_api_key`, target
  `f"QUILL:assistant:{provider}:api-key"`). The Gateway session token stores
  under the identical pattern — target
  `"QUILL:assistant:quill_gateway:api-key"" `— so no new secure-storage code
  is needed, only a new target string.
- **Device auth** (`quill/core/ai/device_login.py` +
  `quill/core/ai/copilot_auth.py`) — a working, wx-free OAuth 2.0 Device
  Authorization Grant (RFC 8628) state machine, already bound once to
  GitHub's real endpoints. This is reused almost verbatim for Gateway sign-in
  (§7) — new `DeviceFlowConfig` pointed at the Gateway's own
  `/device/code`/`/device/token` endpoints, same polling/backoff/expiry
  logic, same screen-reader-friendly `announce_device_code()` pattern.
- **Egress audit (GATE-9)** (`quill/tools/network_egress_audit.py`) — every
  new `urlopen`/`urlretrieve`/SDK-client call site needs a
  `_REVIEWED_EGRESS` entry stating what user action triggers it and why it
  isn't silent. The Gateway's HTTP call site gets exactly one entry here.
- **Admin allow/block list precedent** (`quill/core/ai/admin_policy.py`) —
  `AdminPolicy.is_allowed(provider_id)` / `filter_providers()` already let an
  organization-managed install restrict which providers appear. The Gateway
  admin console (§10) is the server-side, per-user analog of this same idea.
- **Cost/quality tiering precedent** (`quill/core/ai/free_models.py`) —
  `cost_tier_for()`, `is_free_model()`, `best_free_writing_model()` already
  classify models by cost and steer users toward free options. This is
  *advisory* today (client-side hinting), not enforcement — the Gateway plan
  below is what turns "advisory" into "actually can't exceed."
- **Deployment precedent** (`quillin-hub/`) — a real, already-deployed Flask
  service (Gunicorn behind a reverse proxy, env-var config, a minisign-style
  signing-key rotation story, a post-deploy smoke test). Its *operational*
  conventions are reusable even though its stack (Flask, Postgres, no Redis,
  no per-request auth) doesn't match what an inference gateway needs.

**What is 100% new** (confirmed by code search, not assumed): any per-user
usage/token/spend metering, any rate limiter, any request-proxying backend
service, any device-fingerprint/registration concept beyond OAuth user
accounts, and any billing/budget-cap logic. None of this exists in QUILL
today. This document designs all of it.

---

## 1. Executive summary

QUILL is free, open source, and accessibility-first. Its AI features today
are entirely bring-your-own-key (BYOK): the user pastes an OpenAI/Claude/
Gemini/OpenRouter key, or runs a fully local model (Ollama, llama.cpp,
Apple Foundation Models). That's the right default and it stays the
default. But it means a screen-reader user who has never touched an API
key before, and doesn't know what one is, hits a wall on day one of AI
features.

The QUILL AI Gateway adds a second option — "Use QUILL's free hosted AI" —
without ever putting a shared provider key inside the open-source client.
The client authenticates to the Gateway with a QUILL-issued token (device-
code flow, reusing `copilot_auth.py`'s pattern); the Gateway is a small,
boring, private Flask service (on the same server that already runs GLOW and
`quillin-hub`) that owns the real OpenAI key, checks the
requesting user's quota in Postgres/Redis *before* calling OpenAI, and logs
only enough metadata (never document content, never prompts, by default)
to answer "who's driving cost" and "is this abusive." Every limit is
enforced server-side; the client only *displays* remaining allowance.

The magic — free AI that just works for someone who has never heard of an
API key — is entirely a server-side engineering and operations problem.
The client-side change is small and mostly wiring into seams that already
exist.

## 2. Recommended architecture

```
┌─────────────────────┐        HTTPS, Bearer <gateway-token>       ┌──────────────────────────┐
│   QUILL desktop      │ ─────────────────────────────────────────▶ │   QUILL AI Gateway        │
│  (open source, MIT)  │                                            │  (private, closed infra)  │
│                      │ ◀───────────────────────────────────────── │                            │
│  GatewayBackend(     │   JSON: {text, tokens_in, tokens_out,       │  Flask + Postgres +        │
│    AIBackend)        │          remaining_quota, status}          │  Redis + secret manager    │
└─────────────────────┘                                            └───────────┬────────────────┘
                                                                                 │ HTTPS
                                                                     server-side only, never
                                                                     reachable from the client
                                                                                 ▼
                                                                     ┌──────────────────────────┐
                                                                     │  OpenAI (nano-class model)│
                                                                     └──────────────────────────┘
```

Nothing about this replaces BYOK. `ALL_PROVIDERS` grows by one entry;
existing users who configure their own key never touch the Gateway at all.
`AdminPolicy.is_allowed()` (already-existing code) lets an organization
disable the Gateway provider entirely if they want every user on BYOK or
local-only.

### Request flow (one document-Q&A call, concretely)

1. User selects a paragraph, presses the Ask-Quill shortcut.
2. `Assistant.answer()` (or `document_qa.ask_document()`) builds its prompt
   exactly as it does today — no change to prompt construction.
3. `make_default_backend()` resolves to `GatewayBackend` because the active
   provider is `"quill_gateway"`.
4. `GatewayBackend.respond(prompt)` POSTs to
   `POST https://gateway.quillforall.org/v1/chat` with:
   `Authorization: Bearer <token>`, body `{feature: "document_qna", prompt,
   max_tokens, device_id}`.
5. Gateway: authenticates the token → looks up the user row → checks
   monthly/daily/hourly quota in Redis (fast path) → if within budget, calls
   OpenAI's nano model with a **server-side prompt wrapper** (the gateway
   owns the system prompt for each feature, not the client, so a modified
   client can't smuggle an unapproved use through an approved feature id) →
   records usage (tokens, cost estimate, feature, timestamp) → returns the
   text plus updated quota numbers.
6. `GatewayBackend` returns the text to `Assistant` exactly like any other
   backend would; `Assistant`/`document_qa.py`/`vision.py` are unmodified.
7. QUILL's status bar shows "14 of 50 free requests left this month" from
   the `remaining_quota` field in the response — display only, never
   enforcement.

## 3. Threat model

| Threat | Mitigation |
|---|---|
| Someone decompiles the open-source client looking for a shared key | There is none to find. The client never contains a provider key — only, at most, a per-user Gateway token the user themself obtained, stored in the OS credential store. |
| A user patches their local client to skip quota display or claim a fake feature id | Irrelevant — the client's opinion of its own quota is never trusted. Every check happens server-side against the authenticated token's row in Postgres/Redis. A patched client can lie to itself, not to the Gateway. |
| A leaked Gateway token is used from a script, not QUILL | Token is scoped to a device registration (§7); rate limits are per-device and per-user; anomaly detection (§9) flags a token suddenly making requests with unfamiliar client fingerprints/timing patterns. Revoke-one-device without affecting the user's other devices. |
| Provider key leaks from the Gateway itself | Key lives only in a secret manager (§6), injected as an env var at process start, never written to disk, logs, or version control; rotated on a schedule and on any suspicion; the process has no code path that could return the key value to a client response. |
| Cost runaway (single user, or aggregate) from a bug or bulk-abuse | Hard per-user monthly/daily/hourly caps (§8) enforced *before* the OpenAI call, plus a global monthly budget cap that pages an admin and can auto-pause hosted AI entirely (§10) if breached. |
| Prompt injection via document content asking the model to reveal its system prompt or perform an unapproved action | Each feature has its own fixed server-side prompt template (the client cannot supply an arbitrary system prompt to the Gateway) and the Gateway only ever returns model text to the client — it never executes tools or Gateway-side actions on the model's say-so. (QUILL's own agent tool loop, `SafeEditorToolGateway`, already only runs client-side, locally, with per-action confirmation — the Gateway has no equivalent and shouldn't get one in v1.) |
| A user's private document content ends up in a breach of the usage database | Usage records store metadata only — token counts, feature id, timestamps, cost — never prompt/document text, by default (§4, §5). A breach of the usage DB reveals "user X asked 12 document-Q&A questions in June," not what was in any of them. |
| Screen-reader users get a worse experience than sighted users under abuse controls (e.g. CAPTCHAs, lockouts on retry) | Explicit design constraint throughout (§9): no CAPTCHA anywhere in this flow; retry-tolerant rate limiting distinguishes "many similar requests in a burst" (normal for someone re-issuing a command while learning) from "sustained high-volume automation." |
| Supply-chain: a compromised dependency in the Gateway process exfiltrates the OpenAI key from memory | Minimal dependency surface (Flask, one HTTP client, one DB driver, one Redis client); dependency-audit-and-sbom-style pinning (QUILL's CI already does this for the client — mirror it for the Gateway repo); the Gateway never installs unreviewed third-party packages at request time. |

## 4. Privacy model

**Design rule: store the least data that lets you answer the questions in
§4.1. Never store document content or full prompts unless the user
explicitly opts in per-incident for troubleshooting.**

### 4.1 Questions the system must be able to answer without reading private content

- How many requests did this user make this month? → `usage_counter` rows,
  summed by `(user_id, month)`.
- Which feature is driving cost? → `usage_counter.feature` grouped, summed
  by `estimated_cost_usd`.
- Has this user exceeded their limit? → compare the same sum against
  `user.monthly_request_cap`/`user.monthly_cost_cap_usd`.
- Is this device behaving suspiciously? → `device.request_timestamps` (a
  bounded ring buffer in Redis) feeding the anomaly heuristics in §9.
- What is total hosted AI spend this month? → `SUM(estimated_cost_usd)`
  across all users for the current month, cached in Redis, refreshed on
  write.
- Can we cut this user off without affecting everyone else? → `user.status`
  is a per-row enum (`active`/`reduced`/`review`/`blocked`); every quota
  check reads this row first.
- Can we shut off image analysis while leaving document Q&A enabled? →
  `feature_flag` table, keyed by feature id, checked before the per-user
  quota check.
- Can we prove QUILL isn't publishing/exposing private prompts? → because
  by default the schema (§5) has no column capable of holding one. This is
  a structural guarantee, not a policy promise: the "prove a negative" case
  is much stronger when the data literally isn't there.

### 4.2 Identity model

- **Pseudonymous by default.** A user is a UUID (`user.id`) created at
  device registration (§7). No email, no name, no account required for the
  free hosted tier.
- **Optional account upgrade** (future): if QUILL ever wants "move my
  quota to a new computer" without re-registering from scratch, an email
  magic-link can be attached to the pseudonymous UUID later. This is
  additive, never required.
- **Device identity is separate from user identity.** One user, multiple
  devices; the Gateway can disable one device (a stolen laptop) without
  touching the user's other devices or their quota history.
- **Hashed correlation fields where a raw value would be too identifying.**
  IP address is never stored raw in the long-lived usage table — only a
  salted hash (`sha256(ip + rotating_salt)`) with a short TTL in Redis for
  rate-limiting purposes, discarded from long-term storage.

### 4.3 What's redacted, and where

- Server access logs: no request body logged at all (structured logging
  emits `{user_id, feature, tokens_in, tokens_out, status}`, never the
  prompt).
- Error logs / crash reports: any exception message from the OpenAI SDK is
  scrubbed for the pattern `sk-[A-Za-z0-9]{20,}` before it's written
  anywhere, as defense in depth against the key ever appearing in a
  traceback (it shouldn't, since the SDK client is constructed once at
  startup from the env var and never re-serializes the key, but scrub
  anyway — mirrors QUILL's own `quill/stability/redaction.py` pattern
  client-side).
- Diagnostic opt-in mode: a user can explicitly turn on "Include redacted
  request details in diagnostic logs" (mirroring the existing client-side
  crash-report consent pattern) for a support case; even then, the prompt
  text is truncated and PII-scrubbed before it's written, and the record
  auto-expires (§4.4).

### 4.4 Retention

| Data | Retention | Reason |
|---|---|---|
| `usage_counter` rows (metadata only) | 13 months | one full year of trend data + a buffer month for billing reconciliation |
| Redis rate-limit counters | rolling window sizes only (1h/1d/30d) | no need to keep past the window they enforce |
| IP hash (rate-limiting) | 24 hours | abuse detection only needs recent behavior |
| Opt-in diagnostic records (redacted prompt) | 30 days, or until the support case closes, whichever is sooner | explicit troubleshooting use only |
| Device registration record | until revoked or 12 months inactive | lets a returning user's device still work without re-registering |
| Provider key in secret manager | until rotated (see §11 rotation schedule) | not user data, but noted here for completeness |

### 4.5 User-visible privacy explanation (what ships in the client UI)

A single, plain-language paragraph shown the first time a user turns on
hosted AI, and reachable anytime from the AI Hub's Services tab:

> "QUILL's free hosted AI sends only what's needed to answer your request —
> the selected text or question, not your whole document unless you choose
> that — to QUILL's own server, which asks OpenAI's smallest model and
> sends the answer back. QUILL does not save your questions or documents.
> We do keep a small record of how many requests you've made and which
> feature you used, so we can be fair about the free allowance and stop
> abuse — never what you asked or what came back. You can always use your
> own API key instead, or a fully local model, and QUILL never sends
> anything anywhere without your say-so."

## 5. Data model

```sql
-- Identity ---------------------------------------------------------------
CREATE TABLE users (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    status                TEXT NOT NULL DEFAULT 'active',   -- active | reduced | review | blocked
    -- NULL means "use the live global default from gateway_config" (below) --
    -- a per-user override is only set when an admin deliberately changes one
    -- user's allowance; nobody's cap silently drifts when the global default
    -- changes, and nobody needs a per-row migration when it does.
    monthly_request_cap   INT,
    monthly_cost_cap_usd  NUMERIC(8,4),
    -- optional, nullable, additive identity upgrade (never required):
    email                 TEXT UNIQUE,
    email_verified_at     TIMESTAMPTZ
);

-- Every tunable number in §8 lives here, not in code, so an admin can
-- change any limit instantly (no redeploy, no restart) from the admin
-- console (§10). `resolve_limit(user_id, key)` = the user's override in
-- `users`/`user_feature_caps` if set, else this table's `value`, else the
-- hardcoded fail-safe in code (belt-and-suspenders if this table is ever
-- empty on a fresh install). Seeded at first deploy with the "start small"
-- values in §8/§23; every row is editable from day one.
CREATE TABLE gateway_config (
    key                   TEXT PRIMARY KEY,      -- e.g. 'monthly_request_cap'
    value                 NUMERIC NOT NULL,
    description           TEXT NOT NULL,         -- shown in the admin console next to the field
    updated_by            TEXT,
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Per-feature caps, same "global default + optional per-user override"
-- shape as monthly_request_cap above, but keyed by feature since features
-- have independent monthly allowances (§8).
CREATE TABLE user_feature_caps (
    user_id               UUID NOT NULL REFERENCES users(id),
    feature               TEXT NOT NULL,
    monthly_cap           INT NOT NULL,           -- explicit per-user override only; no NULL rows
    PRIMARY KEY (user_id, feature)
);

CREATE TABLE devices (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id               UUID NOT NULL REFERENCES users(id),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at          TIMESTAMPTZ,
    status                TEXT NOT NULL DEFAULT 'active',   -- active | revoked
    label                 TEXT,                             -- "this computer" style, user-editable
    token_hash            TEXT NOT NULL UNIQUE              -- sha256 of the bearer token; never store raw
);

-- Usage (metadata only; NO prompt/document/response columns exist) -------
CREATE TABLE usage_events (
    id                    BIGSERIAL PRIMARY KEY,
    user_id               UUID NOT NULL REFERENCES users(id),
    device_id             UUID NOT NULL REFERENCES devices(id),
    feature               TEXT NOT NULL,        -- document_qna | summarize | rewrite | alt_text | chat | agent
    model                 TEXT NOT NULL,        -- e.g. "gpt-5-nano"
    tokens_in             INT NOT NULL,
    tokens_out            INT NOT NULL,
    estimated_cost_usd    NUMERIC(10,6) NOT NULL,
    status                TEXT NOT NULL,        -- allowed | throttled | blocked
    abuse_flag            TEXT,                 -- null | high_volume | repeated_large_prompt | anomalous_device
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
) PARTITION BY RANGE (created_at);   -- monthly partitions; drop partitions past retention (§4.4)

CREATE INDEX ON usage_events (user_id, created_at);
CREATE INDEX ON usage_events (feature, created_at);

-- Aggregates refreshed on write, read by admin console and client status --
CREATE TABLE monthly_usage_summary (
    user_id               UUID NOT NULL REFERENCES users(id),
    year_month            TEXT NOT NULL,         -- '2026-07'
    request_count         INT NOT NULL DEFAULT 0,
    total_cost_usd        NUMERIC(10,4) NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, year_month)
);

-- Feature flags / kill switches ------------------------------------------
CREATE TABLE feature_flags (
    feature               TEXT PRIMARY KEY,      -- document_qna | summarize | ... | hosted_ai (global)
    enabled               BOOLEAN NOT NULL DEFAULT true,
    disabled_reason        TEXT,
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Opt-in diagnostic records (separate table; never joined into usage_events) --
CREATE TABLE diagnostic_records (
    id                    BIGSERIAL PRIMARY KEY,
    usage_event_id        BIGINT REFERENCES usage_events(id),
    redacted_prompt       TEXT NOT NULL,          -- PII-scrubbed, truncated
    redacted_response     TEXT,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at            TIMESTAMPTZ NOT NULL    -- enforced by a daily cleanup job, §4.4
);

-- Admin actions audit trail ------------------------------------------------
CREATE TABLE admin_actions (
    id                    BIGSERIAL PRIMARY KEY,
    admin_id              TEXT NOT NULL,
    action                TEXT NOT NULL,          -- disable_user | disable_device | set_quota | rotate_key | ...
    target                TEXT NOT NULL,          -- user_id / device_id / feature id / "global"
    reason                TEXT,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Redis holds only ephemeral, reconstructable state: sliding-window rate
counters (`ratelimit:{user_id}:{window}`), the current-month running total
per user (write-through cache of `monthly_usage_summary`, source of truth
is Postgres), and the salted-IP-hash sets for abuse heuristics (§9).

## 6. Secret management plan

- **Where the OpenAI key lives:** on Jeff's existing server (per §16), the
  same place GLOW's and `quillin-hub`'s own credentials already live —
  whatever mechanism that already is (an environment variable set outside
  any git-tracked directory, or that host's secret store if it's a managed
  platform). If a managed cloud is used instead, use its native secret
  manager (AWS Secrets Manager / Azure Key Vault / GCP Secret Manager /
  Fly.io Secrets / Doppler). Never a `.env` file committed to git, never a
  Kubernetes ConfigMap (must be a Secret if k8s is ever used), never baked
  into a container image layer.
- **How the process gets it:** injected as an environment variable at
  container/process start by the platform's secret-injection mechanism.
  The Gateway code reads `os.environ["OPENAI_API_KEY"]` exactly once, at
  startup, into a module-level client object; the raw string is never
  logged, never included in any response, never written to disk.
- **What never touches the repo:** the key itself, obviously, but also no
  *real* value in any `.env.example`; use `OPENAI_API_KEY=sk-REPLACE-ME`
  placeholders only, exactly like `quillin-hub`'s existing env-var
  documentation pattern.
- **CI/CD:** the Gateway's own CI pipeline (separate repo, or a private
  path in a monorepo — recommendation: separate private repo, since this
  service's deployment secrets must never be reachable by QUILL's public,
  contributor-open-source CI) injects the secret only at deploy time via
  the hosting platform's secret store, never as a GitHub Actions secret
  exposed to a workflow triggered by a public PR (the exact category of
  leak GATE-9-style audits exist to prevent client-side; the Gateway needs
  its own equivalent CI hygiene, just server-side).
- **Rotation:** scheduled quarterly, plus immediately on any suspicion.
  Rotation procedure: mint the new key at OpenAI → set it as the *secondary*
  env var → deploy a version of the Gateway that tries primary-then-
  secondary → confirm success rate unaffected for 24h → revoke the old key
  at OpenAI → remove it from the secret store → deploy again with only the
  new key as primary. This avoids any request-serving downtime during
  rotation.
- **Encryption at rest:** every recommended secret store above encrypts at
  rest by default; verify this is on (it is, for all four options named)
  rather than re-implement encryption.
- **Access control:** exactly two people (the maintainer + one backup) can
  read the secret value from the platform's UI/CLI; every other team
  member gets deploy access without secret-read access where the platform
  supports that separation where the host is a managed platform; on a
  self-administered server, this is simply "only Jeff (and one backup
  person) can read the value," enforced by file permissions/shell access
  rather than a platform IAM feature.

### 6.1 Concretely, on a self-administered Unix server: the real options

Jeff's server is a real Unix box, not a managed PaaS, so "the platform's
secret manager" above needs a concrete Unix-native answer. In increasing
order of operational weight — pick the lightest one that meets the
moment, not the heaviest one available:

| Option | How it works | When it's the right call |
|---|---|---|
| **`.env` file + restrictive permissions** (what `quill-ai-gateway/` ships with today) | A file outside any git-tracked directory, `chmod 600`, owned by the service's own Unix user (not root, not a shared account); `docker-compose.yml`/`run.py` read it via `env_file:`/`python-dotenv`. Exactly the pattern GLOW's `web/.env` already uses on this host. | The default. Zero new infrastructure, matches proven practice, appropriate for a service this size with two people who can reach the box at all. |
| **Docker named secrets** (`docker secret` / Compose's `secrets:` key) | The secret is mounted as a file inside the container's filesystem (`/run/secrets/openai_api_key`) rather than an environment variable — avoids the key ever appearing in `docker inspect`'s environment dump or a process's `/proc/<pid>/environ`. | Worth adopting if `docker inspect`/`ps` visibility of env vars ever becomes a real concern — a small code change (`Config` reads a `_FILE`-suffixed path if present, matching the common `SOME_VAR_FILE` convention) away from the current `.env` approach. |
| **`systemd-creds` / `LoadCredentialEncrypted=`** (if running as a systemd unit instead of Docker) | systemd encrypts the credential at rest using a machine-specific key (optionally TPM-backed) and decrypts it only into the unit's private, unlinked runtime directory — never written to disk in plaintext, never visible to other users on the box even briefly. | The strongest *Unix-native, no-third-party-service* option. Natural fit if this deployment ever moves off Docker Compose onto a plain systemd unit; overkill to adopt before that move. |
| **age/sops-encrypted file, checked into the private ops repo** | The secret is encrypted with `age` (or `sops` using `age` as the backend) against the deploying admin's public key; the *encrypted* blob is safe to commit, decrypted only at deploy time (`sops exec-env` or `age -d`) into the process environment. | Useful once more than one person needs to deploy and a shared, versioned, auditable secrets file (who changed what, when) is worth the setup — a natural fit if this project grows contributors with deploy access. |
| **A real secrets manager (HashiCorp Vault / OpenBao, self-hosted)** | Dynamic secret leasing, short-TTL credentials, and a full access-audit log; the app fetches the key at startup via a Vault Agent sidecar instead of reading an env var at all. | The right answer at real organizational scale (many services, many operators, compliance requirements) — deliberately **not** recommended for this project's current size; naming it here is "think broadly," not "build this now." |

**Recommendation for the initial rollout:** the first row — a `.env`
file with `600` permissions, owned by a dedicated `gateway` Unix user
(see the Dockerfile's `USER gateway`), matching what's already proven on
this exact host for GLOW. Revisit this table if the operational picture
changes (more deployers, a compliance requirement, or genuine unease
about `.env`-file handling) rather than pre-building capability the
project doesn't need yet — the same "start small and learn" principle
that governs the quota numbers (§8.1) applies to infrastructure choices
too.

## 7. Authentication and onboarding

**Recommendation: OAuth 2.0 Device Authorization Grant, reusing
`device_login.py` + `copilot_auth.py`'s pattern almost verbatim**, because:

- It's already implemented, tested, and screen-reader-friendly
  (`announce_device_code()`, `describe_login_result()`) — zero new UI-flow
  design risk.
- It needs no password, no CAPTCHA, no browser SDK embedded in the desktop
  client — the user reads a short code, opens any browser (their phone is
  fine), confirms, and QUILL's background poll picks up the authorization.
  This is explicitly good for accessibility: no in-app OAuth popup/webview
  to navigate with a screen reader.
- Email/GitHub/Google login are all viable as the *identity provider*
  behind the device-code flow's confirmation page, decided later without
  changing the client-side flow at all — the confirmation page is a
  Gateway-hosted web page, not part of the open-source client.

**Recommended first-beta identity provider: none required.** The simplest
accessible flow for a free-tier beta is **anonymous device registration**:
the confirmation page just asks "Is this you? [Confirm]" with no login at
all, and a device is registered with a fresh pseudonymous `user_id`. This
maximizes ease of first use at the cost of "a blocked user can just
re-register" — acceptable for a beta with modest hosted allowances and
the abuse controls in §9; revisit adding a lightweight identity (email
magic link) if abuse-by-reregistration becomes a real problem in practice.

### Flow, concretely

1. Client calls `POST /v1/device/code` → Gateway returns
   `{device_code, user_code, verification_uri, verification_uri_complete,
   interval, expires_in}` (identical shape to `DeviceCodeGrant` in
   `device_login.py`).
2. QUILL announces: "To connect QUILL's free AI, go to
   gateway.quillforall.org/connect and enter code ABCD-1234. This window
   updates automatically — no need to come back here." (mirrors
   `announce_device_code()`).
3. Client polls `POST /v1/device/token` every `interval` seconds
   (`run_device_login()`'s existing backoff/expiry logic, unchanged).
4. On confirm, Gateway creates a `users` row (or reuses one if the browser
   session already has a Gateway cookie — same-user-multiple-devices path)
   and a `devices` row, returns a bearer token.
5. Client stores the token via `save_provider_api_key("quill_gateway",
   token)` — the existing per-provider Credential-Manager-first pattern,
   target `"QUILL:assistant:quill_gateway:api-key"`. No new secure-storage
   code.
6. Every subsequent Gateway request sends `Authorization: Bearer <token>`;
   the Gateway looks up `devices.token_hash = sha256(token)` (never stores
   the raw token) to resolve `user_id`/`device_id`.

### New computer / compromised device

- **New computer:** run device registration again; it's a *new* device row
  under a *new* pseudonymous user by default (anonymous mode has no way to
  say "same person, second computer" without an identity provider — this
  is the honest tradeoff of the zero-friction anonymous path, and worth
  stating to the user plainly: "Free hosted AI allowance is per device
  during the beta.").
- **If/when email-linked accounts ship:** device registration on a second
  computer offers "Already have a QUILL AI account? Enter your email to
  get a link" — confirming via the magic link attaches the new device to
  the existing `user_id`, so quota is shared correctly across the user's
  computers.
- **Compromised device:** admin console (§10) or a client-side "This isn't
  my computer anymore" button both call `DELETE /v1/devices/{id}`, which
  flips `devices.status = 'revoked'`; the next request with that token's
  hash is rejected immediately, no propagation delay (checked against
  Postgres directly for this specific, low-frequency path — not cached).

## 8. Server-side quota model

**Every check below happens in the Gateway before the OpenAI call is made,
using the cheapest available signal first** (Redis counter check, ~1ms)
before falling through to anything requiring a database round-trip.

**Every number in this table is a row in `gateway_config` (§5), not a
constant in code.** An admin changes any of them from the admin console
(§10) and it takes effect on the *next request* — no redeploy, no
restart, no code change. The values below are the seeded starting point
for the initial rollout, deliberately conservative per "start small and
learn": prove the system holds up at a small scale before opening the
tap, rather than guessing a generous number on day one and having to walk
it back.

| Limit | Config key | Seeded default (initial rollout) | Enforcement point |
|---|---|---|---|
| Monthly request quota per user | `monthly_request_cap` | **100 requests** | Redis counter `ratelimit:{user_id}:month`, TTL to month boundary; source of truth reconciled nightly against `monthly_usage_summary` |
| Daily request quota per user | `daily_request_cap` | 20 requests | Redis counter, 24h TTL |
| Hourly rate limit per user | `hourly_request_cap` | 8 requests | Redis sliding window |
| Hourly rate limit per device | `device_hourly_request_cap` | 8 requests | same, keyed by device_id — catches one compromised token spamming without punishing the user's other devices |
| Per-feature monthly cap | `feature_cap.<feature>` (one row per feature) | document_qna 60, summarize 60, rewrite 60, alt_text 15, chat 60 (these are ceilings *within* the 100 monthly total, not additive — the monthly total is still the binding cap for a user who mixes features) | Redis counter per `(user_id, feature, month)`, checked alongside the monthly total |
| Max input tokens per request | `max_input_tokens` | **1,500 tokens (~6,000 characters, roughly 1,000 words)** | checked after tokenizing the prompt server-side, before the OpenAI call — see §14.1 for why this is deliberately tight for the free tier |
| Max output tokens per request | `max_output_tokens` | 500 tokens | passed as `max_tokens` to the OpenAI call, hard cap |
| Max document chunk count per document-Q&A request | `max_chunks_per_request` | 3 chunks (see §14 — the client only ever sends relevant chunks, never a whole document) | validated server-side against the request body; a request claiming more chunks than this is rejected outright, not silently truncated |
| Max image size | `max_image_bytes` / `max_image_edge_px` | 3 MB, longest edge 1600px (client resizes before sending — see §15) | rejected with a clear message if exceeded, checked before the file is even fully read into memory (streaming size check, not "read then reject") |
| Max images per day per user | `daily_image_cap` | 5 | Redis counter |
| Max estimated monthly cost per user | `monthly_cost_cap_usd` | $0.15 (nano-class pricing makes 100 requests at these token caps land well under this — see §13; the cap is a backstop, not the binding constraint) | computed running total in `monthly_usage_summary`, checked before each request once the user is within 90% of it (cheap early-exit skip below that) |
| Global monthly budget cap | `global_monthly_budget_usd` | **$25/month for the initial rollout** (see §13's recalculated projection) | checked against a Redis-cached sum, refreshed every write; crossing 100% flips `feature_flags.hosted_ai.enabled = false` automatically pending admin review |
| Emergency kill switch | n/a (boolean, not numeric) | on/off | `feature_flags` row `hosted_ai`, checked first, before any per-user logic — one admin action pauses everything |
| Model allowlist | `allowed_models` (comma-separated, but the initial rollout ships with exactly one) | `{"gpt-5-nano"}` only for hosted tier, never client-selectable | request body's model field, if present at all, is ignored — the Gateway decides the model per feature |
| Prompt/system-template allowlist | n/a (code, not config — see rationale below) | one fixed template per `feature` id, server-side only | client sends `{feature, prompt}`; Gateway looks up the fixed template for `feature` and wraps the client's prompt in it — the client cannot supply its own system prompt |

Two rows are deliberately **not** admin-tunable at runtime: the model
allowlist's *contents* (an admin can only shrink/grow which models are
*permitted*, never point the Gateway at an arbitrary model string typed
into a form — that string becomes part of a billed API call, so it stays
a reviewed code change) and the prompt templates (same reasoning — a
template is effectively the system prompt every user's request runs
through; changing it is a product decision with real behavior
consequences, not a quota dial, so it stays in code review like any other
prompt-engineering change).

### 8.1 Why 100/month to start

500 users × 100 requests × the tightened per-request cost ceiling (§13)
projects to roughly **$3–5/month in the realistic-average case**, with a
**worst-case ceiling around $75/month** if every single user maxed every
cap every month (500 × 100 × ~$0.0015 worst-case-per-request cost at
these tighter token limits) — both comfortably inside a $25 budget cap
that still leaves headroom to notice a real problem before it becomes an
expensive one. This is intentionally small: the first rollout's job is to
prove the auth flow, the quota enforcement, and the abuse controls work
correctly against real traffic, not to maximize how much free usage
QUILL can offer on day one. Raising the cap later is a one-line
`gateway_config` update once real usage data says it's safe — there is no
reason to guess big and walk it back instead of starting small and
raising it deliberately.

### Degradation messages (client-facing, exactly these or close to them)

- "You've used your free QUILL AI allowance for this month. It resets on
  the 1st, or you can add your own API key to continue right away."
- "This selection is too large for the free tier — try a shorter passage,
  or switch to your own API key for full documents."
- "Image analysis is temporarily paused while we review unusual activity
  on hosted AI — document Q&A and rewriting are still available."
- "Hosted AI is paused for everyone right now while we look into something
  — check quillforall.org/status, or use your own API key in the
  meantime."
- "You've reached today's free limit. It resets at midnight, or add your
  own API key to keep going now."

Every one of these is generated from the Gateway's structured error
response (`{status: "quota_exceeded", scope: "monthly"|"daily"|"hourly"|
"feature"|"global", reset_at, message}`), and `GatewayBackend` translates
`scope` + `reset_at` into the exact wording — the wording lives in one
place (the client's i18n catalog, `_()`-wrapped like every other QUILL
string) so it's translatable, not hardcoded Gateway-side strings shown
verbatim.

## 9. Abuse detection and cutoff model

Explicit constraint carried through every control here: **no CAPTCHA, ever,
anywhere in this flow.** QUILL is an accessibility-first product; a CAPTCHA
is close to a hard blocker for many blind users and is the wrong tool for
this problem regardless.

| Signal | What it catches | Response |
|---|---|---|
| Hourly rate limit (§8) | Simple volume abuse | Soft 429 with `reset_at`; never a ban on first hit |
| Repeated near-identical large prompts in a short window | Someone hammering the same big request (scripted abuse, or a runaway retry loop in a bug) | After 5 near-duplicate large prompts in 10 minutes, flag `abuse_flag = 'repeated_large_prompt'` on those events and silently drop the per-request cost cap to force the smallest model/shortest response for that user for the next hour — a soft, invisible throttle before any hard block |
| Repeated failed-auth attempts (bad/expired token) | Credential stuffing, a broken client build | 5 failures in 5 minutes from one IP → temporary IP-level soft rate limit (not a block) for 15 minutes; does not affect other users sharing that IP (e.g. NAT/VPN/campus network) beyond a slightly lower ceiling |
| Token-budget anomaly (this device's average tokens-per-request is a big outlier vs. its own 7-day baseline) | A device suddenly being used very differently (compromised token, or automated scripting against a stolen token) | Flag for the admin review queue (below); do not auto-block — legitimate use also produces occasional big outliers (a user finally tries document Q&A on a long chapter after a week of short rewrites) |
| IP soft limits | Loose signal only, one input among several, never a sole trigger | Contributes to the review-queue score, never blocks alone (shared IPs are common and innocent — libraries, schools, screen-reader user groups on shared connections) |
| Admin review queue | Aggregates the above into a ranked list an admin can glance at | A device/user entering `status = 'review'` gets a **reduced**, not zero, quota (e.g. 5 requests/day) while an admin looks — legitimate users barely notice; determined abuse gets throttled to uneconomical levels without a hard, sudden cutoff that could catch an innocent user badly |
| Blocklist / allowlist | Manual, admin-set | `users.status = 'blocked'` short-circuits every check with a clear, honest message — never a silent failure that looks like a bug |

### Explicitly protecting legitimate screen-reader usage patterns

- **Retry tolerance:** the near-duplicate-prompt heuristic requires *large*
  prompts repeated *many* times in a *short* window — a user re-issuing
  "summarize this" three times because they didn't hear the result clearly
  the first time, or is learning the keyboard shortcut, never approaches
  this threshold (5 large duplicates in 10 minutes is a lot of repetition
  for a human retry pattern, easily distinguishable from a script).
- **Burst-then-idle is normal, not suspicious:** the hourly limit (8/hour
  at the initial rollout's tighter default) is still generous enough that
  a focused editing session doesn't trip it in ordinary use, and the
  daily/monthly caps are the actual binding constraint for normal use —
  hourly exists only to stop a true runaway loop, not to throttle
  legitimate rapid work. If real usage during the initial rollout shows
  the tighter hourly number *does* clip legitimate bursts, that's exactly
  the kind of signal this beta is designed to surface — raise
  `hourly_request_cap` in `gateway_config` (§8), no code change needed.
- **No behavioral biometrics, no keystroke-timing analysis:** anything that
  profiles *how* someone types or interacts risks flagging atypical-but-
  legitimate assistive-technology usage patterns as "bot-like." This
  system deliberately limits itself to request volume/size/timing at the
  API layer, never client-side interaction telemetry.

## 10. Admin console requirements

**Built:** `quill-ai-gateway/app/routes/dashboard.py` — an accessible,
server-rendered web UI (no JavaScript, no build step; every action is a
plain `<form>` POST) at `/dashboard/`, covering every bullet below. Login
bridges the existing admin bearer-token credential into a browser session
(`app/dashboard_auth.py`) rather than inventing a second auth system —
see §10.1 for the full design and the accessibility rationale, and the
`quill-ai-gateway/README.md`'s "admin dashboard" section for how to use
it day to day. What follows was the original requirements list this
implements; it's kept as the spec the dashboard is checked against, not
replaced by the "built" note above.

A small internal web UI (or, for the first beta, a CLI + a handful of
authenticated API endpoints — a full UI is a nice-to-have, not a beta
blocker) that can, for any user/device/feature:

- View a usage summary (`monthly_usage_summary`, request counts, cost) —
  **never** a document/prompt viewer, because that data doesn't exist to
  view (§4, §5).
- Set `users.status` to `active`/`reduced`/`review`/`blocked`.
- Set `devices.status` to `active`/`revoked`.
- Toggle any row in `feature_flags` (per-feature or the global
  `hosted_ai` switch).
- Adjust `monthly_request_cap`/`monthly_cost_cap_usd` for one user
  immediately (e.g. lower a suspicious account's cap to near-zero without
  fully blocking them).
- **Permanently remove a user** — a distinct, harder action from setting
  `status = 'blocked'` (which is reversible and the everyday way to "turn
  off a user's hosted AI usage"). Removal deletes the user's row and
  their devices outright; it's for a user who asks to be forgotten, or
  for cleaning up a clearly-abusive account rather than leaving it
  dormant. `usage_events` rows keep their `user_id` for aggregate
  reporting integrity (they're metadata-only per §4, so retaining them
  after removal carries no meaningful privacy cost); a literal
  right-to-be-forgotten request that requires erasing even that linkage
  is a separate anonymization step, not this endpoint's default behavior.
- **Turn a model on or off, and choose which enabled model is the active
  default.** `gateway_models` (§5) is the admin-tunable model registry:
  each row is one model the Gateway is permitted to call, with an
  `enabled` flag and an `is_default` flag (exactly one enabled row is
  ever the default, enforced in application code in a single transaction
  — see §5's `gateway_models` note). Disabling a misbehaving model is one
  toggle; switching which model requests actually use is one more. Adding
  a *new* model (a different model id/cost entirely) is a deliberate,
  reviewed action — inserting a `gateway_models` row with its real
  per-token cost rates — since a wrong cost rate would silently corrupt
  every subsequent cost calculation for that model; this is intentionally
  not a one-field admin-console edit the way a numeric limit is.
- **Edit any `gateway_config` row (§5/§8) — every global limit in the
  system, live, no redeploy.** This is the console's most-used screen day
  to day: a form listing every tunable (monthly/daily/hourly caps,
  per-feature caps, token limits, image limits, cost caps, budget cap),
  each with its current value, its `description`, and a save button that
  writes the new value plus `updated_by`/`updated_at`. This is precisely
  the mechanism that makes "start small and learn, then raise the limits
  once they're proven safe" a one-field edit instead of a code change and
  a deploy.
- Trigger a key-rotation runbook (documented procedure, §6/§11 — not
  necessarily a one-click UI action, but the console should show "key age"
  so it's visible when rotation is due).
- Block by IP range or device fingerprint (device fingerprint here means
  `device_id`, not a browser-canvas-style fingerprint — QUILL has no such
  mechanism and shouldn't build one).
- View the total current-month spend against the global budget cap, with
  the same 50/75/90/100% alerting thresholds as §13.
- Every admin action writes an `admin_actions` row (§5) — the admin
  console itself is audited, so "who disabled this user and why" is always
  answerable.

### 10.1 The dashboard, concretely: pages, auth, and the accessibility design

**Auth (v1, built):** the dashboard's "sign in" form takes the same admin
device bearer token the JSON API already checks against
`GATEWAY_ADMIN_ALLOWLIST` (`app/auth.py`) — pasted once, then held in
Flask's signed, `HttpOnly`+`Secure`+`SameSite=Lax` session cookie
(`app/config.py`). This is a deliberate "simplest thing that actually
works" choice: no new credential, no CAPTCHA, no password to forget. Every
dashboard request re-validates the token against the live allowlist and
device status on every page load (`app/dashboard_auth.py`'s
`dashboard_login_required`), so a revoked device is logged out of the
dashboard exactly as fast as it's locked out of the JSON API — there is no
separate, longer-lived "dashboard session" trust boundary to reason about.

**Auth (planned upgrade):** GLOW already runs a Keycloak instance on this
same server for its own admin login (real-oidc, magic-link fallback,
per-user accounts). Wiring the Gateway dashboard into that same realm as
a second OIDC client is the natural next step once "paste a token" stops
being good enough — noted here as the intended direction, not yet built
(`app/dashboard_auth.py`'s docstring points back to this paragraph).

**Pages, each mapping directly to a bullet above:**

| Page | Requirement it satisfies |
|---|---|
| Overview | Spend vs. budget cap, monthly request-volume trend, account totals — see the visualization design below |
| Models | Enable/disable a model, choose the active default (§10's model-registry bullet) |
| Limits | Every `gateway_config` row, editable, live — the "one field, no redeploy" requirement |
| Users | Usage summary, set `status`, or permanently remove — the two *distinct* actions this section requires |
| Feature flags | Per-feature pause, plus the global `hosted_ai` kill switch |
| Audit log | Every `admin_actions` row, most recent first |

**The budget/usage visualization design** (produced with this project's
dataviz skill, not ad hoc): the spend-vs-budget number is a stat tile —
a single headline value, not a chart, per that skill's "pick the form"
step — paired with a native `<progress>` element and, critically, a full
sentence stating the percentage in text (`aria-label` and visible copy
both), so nothing here depends on perceiving the bar's fill or color.
Status (good/warning/serious/critical at 0/75/90/100% of budget) uses the
skill's *reserved* status palette, distinct from any categorical series
color, and is **never color-alone** — every status indicator pairs an
icon, a color, and a text word. The monthly request-volume trend is a
plain-HTML bar chart (an ordered list of labeled `<li>` bars, each
direct-labeled with its number) immediately followed by a `<table>` with
the identical numbers — the chart is illustrative reinforcement, the
table is the source of truth a screen reader reads without needing to
parse a `<canvas>` or SVG at all. No JavaScript, and therefore no charting
library, is used anywhere on the page.

## 11. Secret management — see §6 (kept together intentionally; this
section number preserved for the deliverable checklist below)

## 12. BYOK plan

BYOK is not new to QUILL — it's the *existing, default* mode for every
provider today (`providers.py`, `assistant_ai.py`). The Gateway plan
changes nothing about it; it only adds a fifth (well, first-among-equals)
provider option that needs no key at all. Recorded here for completeness
against the requested deliverable list:

- Key entry: unchanged, existing `assistant_ai.save_provider_api_key()`
  flow.
- Storage: unchanged, existing Windows Credential Manager /
  DPAPI-encrypted-fallback pattern (`assistant_ai.py:653/623`, per-provider
  variant at `:738/711`). On Windows this is already Credential-Manager-
  first with DPAPI fallback exactly as requested; macOS already falls back
  to Keychain (`dpapi.py` cross-platform shim, per the research above).
- Transport: BYOK calls go **directly to the provider**, never through the
  Gateway — this is the existing behavior (`ProviderChatBackend` → raw
  `urllib` calls in `assistant_ai.py`) and should stay that way. Routing
  BYOK traffic through the Gateway would mean QUILL's server sees BYOK
  users' prompts, which is a privacy regression with no benefit (the whole
  point of BYOK is the user's own trust relationship with their own
  provider).
- Responsibility notice: already exists in QUILL's provider setup copy
  (per `provider_api_key_storage_hint()` in `providers.py:141`); extend it
  with one line noting that BYOK usage is billed by the provider directly
  and is entirely separate from the free hosted allowance.
- Separate tracking: BYOK usage is not tracked by the Gateway at all (it
  never sees BYOK traffic). If QUILL wants local BYOK usage stats for the
  user's own awareness, that's a client-side-only feature (e.g. counting
  local API calls in `settings.json`-adjacent local state) — out of scope
  for this plan, which is specifically about the *hosted* allowance.

## 13. Cost-control model — initial rollout, then scaling to 500 MAU

**Assumptions grounded in the plan above, at the initial-rollout defaults
from §8:** nano-class model only (`gpt-5-nano`-equivalent pricing class),
max 500 output tokens, max 1,500 input tokens, chunked document Q&A (not
whole-document sends — see §14), capped-and-cached summaries, 100
requests/user/month.

### Per-request cost ceiling (worst case, at the tightened hard caps)

At nano-class pricing (illustrative — use the actual current published
rate at implementation time, these numbers are a planning estimate, not a
quote): roughly $0.05–$0.15 per **million** input tokens and $0.40–$0.60
per million output tokens is typical for the smallest current-generation
models. At the initial-rollout per-request caps (1,500 in / 500 out), one
worst-case request costs on the order of **$0.0004–$0.0007** — noticeably
cheaper than the original 4,000/800 caps this plan started with, because
the free tier's per-request ceiling is deliberately tight (§14.1). Real
average requests (shorter selections, not maxed-out documents) will be
meaningfully cheaper still — call it **$0.0002** average, a deliberately
conservative planning number.

### Initial rollout projection (start here)

| Assumption | Value |
|---|---|
| Monthly active users, initial rollout | 50 (a soft-launch scale — invite a small group, watch it work, then open up) |
| Monthly request cap per user | 100 |
| Average requests/user/month (most users well under the cap) | 20 (20% of the cap — a cautious first-rollout assumption) |
| Average cost/request | $0.0002 |
| **Projected monthly spend at average usage** | **50 × 20 × $0.0002 = $0.20/month** |
| Worst case: every one of the 50 users maxes every cap every month | 50 × 100 × $0.0007 = **$3.50/month** |

**Recommended initial-rollout budget cap: $25/month.** Even the worst
case above ($3.50) sits well inside it — the $25 figure is chosen not
because the math demands it, but because it's a round, comfortable number
that an admin can watch trip *only* if something is genuinely wrong
(a bug causing runaway retries, or real abuse), never as a routine
ceiling that legitimate small-scale usage bumps into.

### Scaling projection — 500 MAU, once the initial rollout has proven out

Once `gateway_config`'s `monthly_request_cap` is deliberately raised
(§8.1) and the user base has grown, the same math scales linearly:

| Assumption | Value |
|---|---|
| Monthly active users | 500 |
| Average requests/user/month | 60 (an "occasional AI helper" usage pattern, not a power-user assumption) |
| Average cost/request (assuming caps are raised back toward the original 4,000/800 token ceiling once trust is established) | $0.0005 |
| **Projected monthly spend at average usage** | **500 × 60 × $0.0005 = $15/month** |
| Worst case: every user maxes every cap every month (at the original, more generous 500/month cap) | 500 × 500 × $0.002 = **$500/month** |

At this scale, a $250/month budget cap (15x headroom over the realistic
projection, well under the theoretical worst case) is the appropriate
setting — but this is a *later* config change made deliberately, informed
by what the initial rollout actually measured, never the starting point.

### The governing principle

The hard per-user caps in §8 (all live-tunable via `gateway_config`, §8.1,
§10), not the global budget cap, are the primary defense against runaway
cost at every scale; the global cap is always the backstop that catches
"our per-user math was wrong," never the everyday control. Scale the
global cap up in step with the per-user caps, never ahead of them.

### Alerting thresholds (percentages are the same at either scale; dollar
### amounts shown for both the initial-rollout $25 cap and the later $250
### scaling-stage cap from the projection above)

| Threshold | Initial rollout ($25 cap) | Scaling stage ($250 cap) | Action |
|---|---|---|---|
| 50% | $12.50 | $125 | Informational Slack/email/webhook to the maintainer — no action needed, just visibility |
| 75% | $18.75 | $187.50 | Same alert, escalated tone; review the usage-by-feature breakdown for anything unexpected |
| 90% | $22.50 | $225 | Alert + recommend tightening per-user caps for the remainder of the month via the admin console (§10) rather than waiting for the hard stop |
| 100% | $25 | $250 | `feature_flags.hosted_ai.enabled` auto-flips to `false`; every client sees "Hosted AI is paused while we review unusual activity" (§8); BYOK and local models are entirely unaffected, since they never touch this budget |

### Recommended defaults recap (also see §8's full table)

- Free monthly allowance: **100 requests/user for the initial rollout**
  (§8.1) — expected real average usage far below that; raise deliberately
  via `gateway_config` once proven safe, scaling toward 500/user as
  adoption grows (§13's scaling projection).
- Initial-rollout global budget cap: **$25/month**. Scaling-stage cap
  (once raised): $250/month.
- Fallback when the cap is reached: **pause hosted AI, not the app** — BYOK
  and local-model paths keep working; the client's messaging always
  mentions "add your own key to continue now" as the immediate workaround.

### Cost levers, if adoption outpaces the plan

1. Lower the per-user monthly cap (500 → 250) — a config change, no
   deploy.
2. Add response caching for genuinely repeat-safe operations (e.g. two
   users summarizing the exact same publicly-shared document text) —
   marginal savings, not the primary lever, and only safe where no user-
   specific context is in the prompt.
3. Raise the global budget cap once real usage data justifies it — the
   whole point of measuring first is not guessing this number twice.

## 14. Document Q&A strategy

**Never "send the whole document every time."** The plan distinguishes
four scopes, matching how `document_qa.py` and `assistant.py` already let a
user scope a question, and adds a consent step before anything server-side
is involved:

| Scope | What's sent to the Gateway | Local work first |
|---|---|---|
| Selected text | Exactly the selection, verbatim, **truncated client-side to the current `max_input_tokens` config value before it's even sent** (§14.1) | none needed — it's already small |
| Current paragraph/section | The paragraph/section text only (QUILL already has section-boundary logic from `extract_sections` used by the Audio Studio's chaptering — reuse it to find "the current section" rather than inventing new boundary detection) | none |
| Whole document | **Chunked locally first.** QUILL already parses documents into sections; a lightweight local retrieval step (even simple keyword/heading-overlap scoring, no embedding model required for v1) picks the top N sections most relevant to the question, capped at the Gateway's `max_chunks_per_request`/`max_input_tokens` limits (§8), and *those* chunks are sent — never the raw whole document | chunk + rank locally |
| Document collection (e.g. a Vault) | Same chunking principle, but scored across multiple documents; explicitly flagged as a v2/later feature, not part of the first beta — the complexity of cross-document ranking isn't justified until whole-document Q&A is proven out | out of scope for beta |

### 14.1 Large-document safeguards (defense in depth — three independent layers)

The free hosted tier is the one place QUILL must be strict about input
size, because every extra input token is metered cost on someone else's
card. Three layers, each independently sufficient, deliberately
redundant:

1. **Client-side pre-check, before the consent dialog even appears.**
   `GatewayBackend` (or whichever feature is about to call it) measures
   the candidate text's length *before* offering to send it. If a
   selection/section/chunk-set exceeds the current `max_input_tokens`
   value (the client fetches this once per session from the Gateway's
   `/v1/config` endpoint, so it always reflects the live admin-set value,
   never a stale hardcoded guess), QUILL never shows the consent dialog
   at all — it shows the degradation message from §8 immediately
   ("This selection is too large for the free tier — try a shorter
   passage, or switch to your own API key for full documents.") This is
   the layer that saves the round-trip and the user's time, but it is
   **not** the security boundary — a modified or malicious client can
   skip it entirely, which is exactly why layers 2 and 3 exist.
2. **Server-side hard reject, before tokenizing counts as "trusted."**
   Every `/v1/chat` request has its request body size checked against a
   generous absolute byte ceiling (e.g. 64KB) *before* any parsing or
   tokenization happens — this stops a trivial "send a 500MB body" attack
   from even reaching the tokenizer. Then the actual prompt is tokenized
   server-side (never trusting a client-reported token count) and
   compared against `max_input_tokens`; over the limit is an immediate
   `400` with the same degradation message, before any OpenAI call is
   attempted. This is the real boundary — it holds even against a client
   that skips layer 1 entirely.
3. **Chunk-count ceiling, independent of per-chunk size.** A
   document-Q&A request can't route around the token limit by sending
   many small chunks instead of one big one — `max_chunks_per_request`
   (§8) caps the chunk *count* independently of the combined token check,
   so "3 chunks of 1,500 tokens each" is still rejected as a whole even
   though no single chunk looks large.

All three checks run **before** the Gateway calls OpenAI — never as a
post-hoc cleanup after an expensive call has already happened. A request
that fails any of them is billed nothing (rejecting is free; only the
actual OpenAI call has a cost), which is also why layer 2 matters even
though layer 1 exists: a well-behaved client's UX benefit (skip the round
trip) doesn't help contain cost if a bad actor skips it, so the server
never relaxes its own check based on trusting the client did one already.

### Consent, explicitly

Before the *first* time in a session that any text leaves the local
machine for hosted AI, QUILL shows (once, dismissible, screen-reader
clear): "This will send the selected text (about N words) to QUILL's
hosted AI. Continue?" — mirroring the exact pattern QUILL already uses for
other consented network actions (e.g. the Audio Studio's book-lookup
consent dialog, "QUILL will contact Open Library and MusicBrainz...").
Whole-document mode's consent message states plainly that several
excerpts (not the whole document) will be sent, and names roughly how much
("about 3 short excerpts, roughly 800 words total").

### Caching

Short summaries can be cached **locally, client-side, keyed by a hash of
the exact input text** — if a user asks for the same paragraph's summary
twice, the second call never leaves the machine. This is a pure client-
side optimization (a small local cache in QUILL's existing app-data
directory, same pattern as other local caches like `translate_sections.py`'s
translation cache) and needs no Gateway-side change.

## 15. Image and alt-text strategy

Builds directly on the existing `vision.py describe_image()` — same
function signature, same per-provider multimodal body builders, only the
transport target changes to the Gateway when `quill_gateway` is the active
provider.

- **User confirmation before every image send** — already exists in
  spirit (image description is always an explicit user action, never
  automatic); make the consent copy explicit that the image itself, not
  just a description of it, leaves the machine: "Send this image to
  QUILL's hosted AI for a description? The image file itself will be
  uploaded."
- **Max image size: 4 MB, longest edge resized to 2048px client-side
  before sending** (not server-side rejection after upload — resizing
  locally saves the user's bandwidth and avoids uploading data that will
  just be rejected). `vision.py` already handles HEIC→JPEG conversion;
  add a resize step alongside it.
- **Daily image limit: 20/user** (§8) — generous for normal alt-text-
  authoring workflows, restrictive enough to bound vision-model cost,
  which is meaningfully higher per-call than text.
- **Alt text vs. long description:** both are existing prompt variants in
  `vision.py` (`DEFAULT_IMAGE_DESCRIPTION_PROMPT` and presumably a longer
  variant) — the Gateway's fixed per-feature template (§8) has one entry
  for each, both nano-class, both capped output tokens (shorter for alt
  text, longer for full description).
- **Editing workflow:** unchanged from today — QUILL always inserts
  generated alt text into an editable field for the user to review/adjust
  before it's committed, never silently.
- **Privacy notice, specific to images:** stated plainly and separately
  from the general hosted-AI notice, since images are qualitatively more
  sensitive than short text excerpts — "unless you use your own API key or
  a local vision model, this image is sent to OpenAI's servers to generate
  a description."

## 16. Recommended stack

**Updated recommendation: host it on Jeff's existing server, on Flask.**
Jeff already operates a server running Flask for GLOW and for
`quillin-hub` (a real, in-repo precedent — see §0 and the table below).
Reusing known-good, already-operated infrastructure beats standing up a
new platform (Fly.io) and a new framework (FastAPI) for a service this
size: one less thing to learn, one less thing to pay for, one less set of
ops runbooks to write from scratch. The async/auto-OpenAPI advantages
FastAPI would bring don't matter much here — the Gateway's request volume
(tens of requests/second at most, per §13's projections) doesn't need
async concurrency to stay responsive, and a hand-written OpenAPI schema
for the one or two client-facing routes is a small, one-time cost.
Everything else in this plan (the Postgres schema in §5, the Redis
rate-limiting model in §8/§9, the quota/abuse logic) is framework-agnostic
and ports to Flask with no design changes — only the route-handler syntax
differs.

| Component | Choice | Why |
|---|---|---|
| Web framework | **Flask** | matches the framework already running GLOW and `quillin-hub` on Jeff's server — one runtime, one set of ops knowledge, no new platform to learn; use `Flask-Limiter` (Redis-backed) for the rate-limit checks and plain SQLAlchemy for Postgres, the same combination `quillin-hub` already proves out |
| Database | **PostgreSQL** | matches `quillin-hub`'s existing choice; partitioned `usage_events` table (§5) scales fine for this volume |
| Rate limiting | **Redis** | sub-millisecond counter checks are the right tool for "check before every OpenAI call"; `quillin-hub` doesn't use Redis today, but this service's access pattern (many small counter checks) genuinely needs it where the storefront didn't — add it as a new dependency on the existing server, it's a lightweight service to run alongside Postgres |
| Secrets | Whatever secret-injection mechanism the existing server already uses for GLOW/`quillin-hub`'s own credentials (environment variables set outside the deployed code, a local `.env` **outside** any git-tracked directory, or the platform's secret store if the host is a managed one) | see §6 — the mechanism matters less than the invariant: never in a repo, never in a file that gets git-added by habit |
| Structured logging | Python `structlog` or stdlib `logging` with a JSON formatter + a redaction filter (mirrors `quill/stability/redaction.py`'s existing scrub-pattern approach, ported server-side) | never emits prompt/document text by construction, not just by discipline |
| Admin console | **Built**: a Flask-templated, server-rendered dashboard (Jinja2, no JS) at `/dashboard/`, session-auth bridged over the existing admin bearer token — §10.1 has the full design | keeps the same small stack, no separate frontend build pipeline |
| Deployment | **Built**: Docker Compose (`docker-compose.yml`: web + redis + postgres) on Jeff's existing server, same shape as GLOW's own `web/docker-compose.yml` on that host, behind the same Caddy instance (`Caddyfile.example`) | zero new infrastructure to provision or learn; the Gateway becomes a third small service on infra that's already monitored and maintained |
| CI/CD | Separate private repository from the open-source QUILL client; deploy secrets scoped to that private repo only, never triggered by a public-repo PR — a simple `git pull` + process-restart deploy (matching a small self-hosted setup) is entirely adequate at this scale, no need for a container-orchestration pipeline | prevents exactly the class of leak GATE-9 exists to catch client-side, while staying as simple as the existing GLOW/`quillin-hub` deploys |
| Monitoring/alerting | Whatever uptime/monitoring already watches GLOW and `quillin-hub` on that server, extended to this service's `/healthz` endpoint (the `quillin-hub` runbook calls out a `/healthz` gap as a to-do — build this service's `/healthz` from day one) + the budget-threshold alerts (§13) via a simple webhook to Slack/email/Discord | reuses existing monitoring instead of standing up new tooling |
| Backups | Whatever Postgres backup routine already covers GLOW/`quillin-hub`'s databases, extended to this one, with the retention policy (§4.4) additionally enforced via a scheduled cleanup job | standard practice, no custom backup tooling needed |
| Key rotation | Documented runbook (§6), executed manually on a quarterly calendar reminder — full automation isn't justified until rotation frequency increases | matches the realistic operational capacity of a small open-source project |
| Incident response | A one-page runbook: "how to flip the global kill switch," "how to rotate the key under suspicion," "who to notify," kept in the private Gateway repo's `docs/` — mirrors the spirit of QUILL's own `crash_report.py`/incident patterns without needing new tooling | keeps the plan realistic in scope for the team size |

**If Jeff's existing server ever needs to be swapped for managed hosting**
(e.g. outgrowing a single box), everything above ports cleanly to Fly.io or
similar — the Postgres/Redis/Flask combination is supported everywhere;
nothing in this plan is tied to one host.

## 17. User experience flows

1. **First AI use, no BYOK key configured yet:** AI Hub shows two paths
   side by side — "Use QUILL's free hosted AI (recommended for most
   people)" and "Use your own API key or a local model." Choosing hosted
   triggers the device-code flow (§7) inline, with the code and URL
   announced clearly.
2. **Ongoing use — the "magical" usage display, in three places (§17.2).**
   status bar, AI Hub, and About Quill all show "38 of 100 free requests
   left this month" whenever hosted AI is active — always visible, never
   requiring a separate check, similar in spirit to how GitHub Copilot
   surfaces its own usage in an editor status bar.
3. **Approaching a limit:** at 90% of the monthly cap, one gentle one-time
   notice: "You're close to this month's free AI limit (90 of 100 used).
   Add your own API key anytime to keep going without limits."
4. **Hitting a limit:** the exact degradation messages in §8, always
   paired with the two live workarounds (wait for reset, or switch to
   BYOK) — never a dead end.
5. **Switching to BYOK later:** existing flow, unchanged; the AI Hub lets
   a user add a personal key at any time without losing their hosted-tier
   history (both are just providers in the same `ALL_PROVIDERS` list).
6. **Admin pauses a feature:** any user attempting that feature sees a
   specific, honest message (§8) naming what's paused and why, never a
   generic error.

### 17.2 The usage display, concretely (client-side implementation, not yet built)

This is specified precisely here as the contract a future client change
implements against `GET /v1/quota` (§24); it is **not** part of the Flask
service in `quill-ai-gateway/` (which is server-only) — it's a follow-on
QUILL desktop client (`quill/ui/`) change, tracked separately.

- **Status bar** (mirroring how GitHub Copilot shows its own usage in an
  editor status bar): a small, always-visible status-bar segment reading
  e.g. "AI: 38/100" when hosted AI is the active provider, hidden
  entirely when BYOK/local is active (BYOK usage isn't tracked by the
  Gateway at all — §12 — so there's nothing to show). Screen-reader
  accessible on demand: focusing or activating the segment announces the
  fuller sentence ("38 of 100 free AI requests left this month, resets
  August 1st"), matching QUILL's existing convention of pairing every
  visual status with an announced/readable equivalent (§18). Polled from
  `GET /v1/quota` once per session and refreshed after every `/v1/chat`
  response (which already returns a `remaining_quota` snapshot, §24 — no
  extra round trip needed for the common case).
- **AI Hub:** a dedicated "Hosted AI usage" line on the Services/Provider
  tab wherever `quill_gateway` is configured — the same numbers as the
  status bar, plus the reset date and current `status`
  (active/reduced/review/blocked) in plain language, plus a direct link
  to "Add your own API key" for when the free tier isn't enough.
- **Help > About Quill:** one line in the existing About dialog's
  Overview tab (§0's `info_pages.py`/`about_info.py` — the existing
  `AboutInfo` dataclass gains one new, optional field, e.g.
  `hosted_ai_usage_summary: str`, populated only when hosted AI is
  configured) — "Hosted AI: 38 of 100 free requests used this month."
  Chosen for About specifically because it's the place a user already
  looks to understand "what is this copy of QUILL, and what's it doing" —
  a natural, low-effort second surface for the same information, not a
  new concept.
- **Never enforcement, only display:** every one of these three surfaces
  reads `GET /v1/quota`, which is explicitly informational (§24) — the
  client never uses these numbers to block a request itself; the
  authoritative check always happens server-side on the next real
  `/v1/chat` call (§8's core invariant, repeated here because it applies
  to display code too: a client that shows "5 requests left" and is wrong
  by one is a cosmetic bug; a client that *enforces* "5 requests left" and
  is wrong is a security bug).

## 18. Accessibility requirements

- Device-code screen-reader announcement: exact code and URL read once,
  clearly, with the option to repeat it (reuses `announce_device_code()`
  verbatim — no new design needed).
- No CAPTCHA anywhere in onboarding or abuse handling (§9, restated here
  because it's a hard requirement, not a nice-to-have).
- Quota status is always available as text a screen reader can read
  on-demand (a labeled control, not a purely visual progress bar) —
  matches QUILL's existing UI convention of pairing every visual status
  with an announced/readable equivalent.
- Degradation messages (§8) are full sentences, never bare error codes or
  HTTP status numbers surfaced to the user.
- Consent dialogs (§14, §15) follow QUILL's existing modal dialog contract
  (`_show_modal_dialog`, `apply_modal_ids`) — no new dialog pattern
  introduced.
- The image-send consent and the whole-document-Q&A consent are
  distinguishable from each other in wording (a screen reader user
  quickly moving through dialogs must be able to tell "this one's about
  an image" from "this one's about text" without extra navigation).

## 19. Implementation phases

**Phase 0 — Gateway skeleton (no client changes yet)**
Stand up the private repo: Flask app, Postgres schema (§5), Redis
counters, device-code endpoints (§7), one hardcoded test feature
(`echo`) that doesn't call OpenAI at all — prove the auth + quota
plumbing works end to end before any real model cost is involved.

**Phase 1 — One real feature, document Q&A**
Wire the real OpenAI nano-model call behind the `document_qna` feature
id, with the full quota/budget/kill-switch stack from §8 live. Add
`GatewayBackend(AIBackend)` client-side, add `"quill_gateway"` to
`ALL_PROVIDERS`, wire the device-code onboarding flow into the AI Hub.
Ship behind a QUILL feature flag (`future.ai_gateway`, following the
existing `locked_off` pattern other in-progress features use), internal
testing only.

**Phase 2 — Remaining features + admin console**
Add `summarize`/`rewrite`/`chat` features (they reuse the same
infrastructure, just new template rows). Build the admin console (§10)
past bare API endpoints into an actual internal page. Add the alerting
webhooks (§13).

**Phase 3 — Image/alt-text**
Add the `alt_text` feature, the client-side image resize step, and the
per-image consent flow (§15) — deliberately last, since vision calls
cost more and need their own careful cap tuning informed by real Phase
1/2 usage data.

**Phase 4 — Public beta**
Remove the internal-only flag, publish the privacy explanation (§4.5)
prominently, open the checklist in §21, monitor the §13 alert
thresholds closely for the first month.

**Phase 5 (later, not beta-blocking) — Optional identity upgrade**
Email magic-link account linking for multi-device quota continuity
(§7), only if the anonymous-per-device model proves limiting in
practice.

## 20. Open questions

1. **Hosting target confirmation:** Jeff's existing server (already
   running GLOW and `quillin-hub`) is the recommendation (§16) — confirm
   it has the headroom for a third small service (a few hundred MB of
   RAM, negligible CPU at this request volume) before committing.
2. **Legal/ToS:** does QUILL need a short hosted-AI-specific terms
   addendum (separate from the general project license), given this is
   the first QUILL service that handles even pseudonymous usage data at
   scale? Recommend a one-page addendum, not a rewrite of anything
   existing.
3. **Rate-limit tuning:** the numbers in §8 are informed planning
   estimates, not measured data — expect to tune them after Phase 1's real
   usage, not treat them as final.
4. **Does `future.publishing`'s existing `locked_off` review-gate pattern**
   (used elsewhere in QUILL for staged feature rollout) generalize cleanly
   to `future.ai_gateway`, or does the Gateway's server-side kill switch
   make the client-side flag partially redundant? (Recommendation: keep
   both — client flag controls whether the *UI* offers hosted AI at all;
   server flag controls whether *requests* succeed. They answer different
   questions and both are cheap to keep.)
5. **Whole-document local chunking quality:** is simple heading/keyword
   overlap scoring (§14) good enough for the first beta, or does it need
   a proper local embedding model sooner than planned? Recommend shipping
   the simple version first and measuring whether users complain about
   answer relevance before adding embedding-model complexity.
6. **Does the Gateway ever need to support streaming responses** (`
   respond_stream`) for a good UX on longer document Q&A answers, or is
   blocking `respond()` acceptable for a nano-class, capped-output-token
   first beta? Recommend blocking-only for Phase 1, revisit if latency
   feedback says otherwise.

## 21. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Adoption is far higher than the 500-MAU planning assumption, budget cap trips constantly | The 100%-cap auto-pause (§8/§13) is a safety net, not meant to be hit routinely; if it's tripping in week one, that's a strong, cheap signal to raise the cap deliberately rather than a failure |
| A single compromised device token is used for sustained abuse before detection | Hourly per-device limit (§8) + token-budget anomaly flagging (§9) bound the damage to a small window even in the worst case, and device revocation (§7) is immediate |
| The anonymous-registration model gets abused via mass re-registration to reset quotas | Track registration rate per IP-hash (soft, non-blocking per §9) as an early warning; the real backstop is that even unlimited *free-tier* re-registration is bounded by the global budget cap (§13) — worst case it costs money, not that it exposes data or breaks the service |
| Team bandwidth to operate a new always-on service is limited (small open-source project) | Deliberately boring stack (§16), deliberately manual-but-documented key rotation (§6), a genuinely small feature surface for the first beta (§19 Phase 1 is one feature) — this plan is sized to what a small team can actually run, not to an enterprise SRE org |
| Users don't understand the difference between hosted and BYOK modes, causing support burden | The single-paragraph privacy explanation (§4.5) plus the two-path onboarding UI (§17.1) are both designed to make the distinction explicit at the moment of choice, not buried in settings |

## 22. Beta launch checklist

- [ ] Gateway repo exists, private, separate from the open-source QUILL
      client repo.
- [ ] OpenAI key lives only in the platform secret manager; verified not
      present in any repo, `.env.example`, container image layer, or CI
      log by manual review before first deploy.
- [ ] `/healthz` endpoint exists and is monitored.
- [ ] Device-code auth flow works end to end against the real
      `device_login.py`/`copilot_auth.py`-pattern client code.
- [ ] All §8 quota limits are live and tested (including the "reject
      before calling OpenAI" ordering — never call the provider first and
      check quota after).
- [ ] Global budget cap + 50/75/90/100% alerts are wired to a real
      notification channel, tested with a manual trigger.
- [ ] Admin console (or the bare API-endpoint equivalent for beta) can
      disable a user, disable a device, disable a feature, and flip the
      global kill switch — all four manually exercised once before
      launch.
- [ ] Privacy explanation (§4.5) copy is finalized, translatable
      (`_()`-wrapped client-side), and reviewed for plain language.
- [ ] Every consent dialog (§14, §15) is screen-reader tested (this piece
      genuinely should get a JAWS/NVDA pass before shipping, same
      standard as the rest of QUILL).
- [ ] `network_egress_audit.py`'s `_REVIEWED_EGRESS` has an entry for the
      Gateway HTTP call site.
- [ ] `GatewayBackend` unit-tested with a stubbed Gateway response
      (mirrors how other backends are tested today) and, separately,
      smoke-tested against a real staging Gateway instance.
- [ ] Retention cleanup job (§4.4) is scheduled and verified to actually
      delete expired rows, not just documented as a policy.
- [ ] Incident-response one-pager (§16) exists in the Gateway repo.
- [ ] Key rotation runbook (§6) has been dry-run at least once before
      launch, not left untested until the first real rotation is needed.

## 23. Recommended defaults for the initial rollout (summary)

- **Auth:** OAuth device-code flow, anonymous registration (no email/
  account required), reusing `device_login.py`/`copilot_auth.py`.
- **Model:** one nano-class model, hardcoded server-side allowlist of one.
- **Monthly allowance:** **100 requests/user** (start small — §8.1),
  ~$0.0002 average cost/request.
- **Hard caps (all live-tunable via `gateway_config`, §5/§8/§10):** 1,500
  input tokens, 500 output tokens, 20/day, 8/hour, 5 images/day,
  $0.15/user/month cost ceiling, max 3 chunks per document-Q&A request.
- **Global budget cap:** **$25/month** with 50/75/90/100% alerting,
  scaling to $250/month only once usage at the 100/month tier has been
  observed and the cap is deliberately raised (§13).
- **First feature shipped:** document Q&A only (Phase 1); everything else
  follows once that's proven stable.
- **Data retention:** usage metadata 13 months, rate-limit counters
  1h–30d rolling, no prompt/document content stored unless explicitly
  opted in per-incident, 30-day expiry even then.
- **Fallback when limits are hit:** always BYOK or local model, never a
  dead end — the free hosted tier is a convenience on top of the existing
  BYOK product, never the only path.
- **Large-document safeguards:** three independent layers (§14.1) —
  client-side pre-check (skips the round trip), server-side hard reject
  on real tokenized size (the actual boundary), and an independent
  chunk-count ceiling that can't be routed around with many small chunks.

## 24. API reference (contract between the client and the Gateway)

This is the concrete interface `GatewayBackend` (client) and the Flask
app (server, §16) implement against. Every endpoint requires
`Authorization: Bearer <token>` except device registration itself.
Content type is `application/json` throughout.

### `POST /v1/device/code`

Start device-code registration (§7). No auth required (this *is* the
auth bootstrap).

Request body: `{}` (empty — nothing to send yet).

Response `200`:
```json
{
  "device_code": "opaque-string",
  "user_code": "ABCD-1234",
  "verification_uri": "https://gateway.quillforall.org/connect",
  "verification_uri_complete": "https://gateway.quillforall.org/connect?code=ABCD-1234",
  "interval": 5,
  "expires_in": 600
}
```

### `POST /v1/device/token`

Poll for authorization (§7). No auth required.

Request body: `{"device_code": "opaque-string"}`.

Response `200` (authorized):
```json
{"status": "authorized", "token": "opaque-bearer-token", "device_id": "uuid"}
```

Response `428` (still pending — the client keeps polling at `interval`):
```json
{"status": "pending"}
```

Response `429` (`slow_down` — client must increase its polling interval):
```json
{"status": "slow_down"}
```

Response `410` (expired or denied):
```json
{"status": "denied"}
```
or
```json
{"status": "expired"}
```

### `GET /v1/config`

Returns the currently-active tunable limits relevant to the client (a
public subset of `gateway_config` — never internal-only rows like the
model allowlist's exact string). The client calls this once per session
and uses it for the layer-1 pre-check in §14.1, so it always reflects
whatever an admin has most recently set.

Response `200`:
```json
{
  "max_input_tokens": 1500,
  "max_output_tokens": 500,
  "max_chunks_per_request": 3,
  "max_image_bytes": 3145728,
  "max_image_edge_px": 1600,
  "hosted_ai_enabled": true,
  "feature_flags": {"document_qna": true, "summarize": true, "rewrite": true, "alt_text": true, "chat": true}
}
```

### `GET /v1/quota`

Returns the authenticated user's current usage against their limits —
this is what powers the client's "38 of 100 free requests left this
month" status display (§17.2). Never enforced client-side; purely
informational.

Response `200`:
```json
{
  "monthly_request_cap": 100,
  "monthly_requests_used": 38,
  "daily_request_cap": 20,
  "daily_requests_used": 3,
  "reset_at": "2026-08-01T00:00:00Z",
  "status": "active"
}
```

### `POST /v1/chat`

The one real inference endpoint. Every feature (document Q&A, summarize,
rewrite, chat) uses this same route with a different `feature` value;
the Gateway looks up the fixed server-side prompt template for that
`feature` (§8) rather than accepting an arbitrary system prompt from the
client.

Request body:
```json
{
  "feature": "document_qna",
  "prompt": "the user's question or selected text",
  "chunks": ["optional additional context chunks, if the feature uses them"],
  "device_id": "uuid"
}
```

Response `200` (allowed):
```json
{
  "status": "allowed",
  "text": "the model's answer",
  "tokens_in": 340,
  "tokens_out": 120,
  "remaining_quota": {"monthly": 61, "daily": 16, "hourly": 6}
}
```

Response `422` (input too large — layer 2 of §14.1 rejected it):
```json
{
  "status": "rejected",
  "reason": "input_too_large",
  "message": "This selection is too large for the free tier — try a shorter passage, or switch to your own API key for full documents.",
  "max_input_tokens": 1500,
  "tokens_counted": 2400
}
```

Response `429` (quota exceeded):
```json
{
  "status": "quota_exceeded",
  "scope": "monthly",
  "reset_at": "2026-08-01T00:00:00Z",
  "message": "You've used your free QUILL AI allowance for this month. It resets on the 1st, or you can add your own API key to continue right away."
}
```

Response `503` (feature or global kill switch off):
```json
{
  "status": "unavailable",
  "scope": "global",
  "message": "Hosted AI is paused for everyone right now while we look into something — check quillforall.org/status, or use your own API key in the meantime."
}
```

### `DELETE /v1/devices/{device_id}`

Revoke a device (§7's "compromised device" flow). Authenticated as the
owning user (or an admin — see the admin-only routes below).

Response `204`: no body.

### Admin-only routes (§10), gated to an admin allowlist via the same
### device-code login, separate from any user-facing token's permissions

- `GET /admin/config` / `PUT /admin/config/{key}` — read/write any
  `gateway_config` row.
- `GET /admin/users/{id}/usage` — the usage summary for one user (never
  prompt content — see §4).
- `PUT /admin/users/{id}/status` — set `active`/`reduced`/`review`/
  `blocked`.
- `PUT /admin/devices/{id}/status` — set `active`/`revoked`.
- `PUT /admin/feature-flags/{feature}` — enable/disable one feature or
  the global `hosted_ai` switch.
- `GET /admin/spend` — current-month total spend vs. the global budget
  cap.

---

*This plan intentionally leaves generic backend engineering (exact Flask
route signatures beyond the contract in §24, exact SQLAlchemy models
beyond the schema in §5, deployment scripts) for the implementation phase
— the goal here was to make every architectural and policy decision
concrete and grounded in QUILL's actual code, not to pre-write the
Gateway's entire source. The actual Flask implementation lives in
`quill-ai-gateway/` at the repository root (a sibling to `quillin-hub/`,
matching that precedent) and implements this contract.*
