# QUILL free hosted AI: Luna 6, the two editors, and the gateway that already exists

Status: **partly shipped**, 2026-09-23. Moved here from the repository root the
same day (the root-layout gate sanctions no design notes there, and this is the
design of record for a live service rather than a scratch plan). Supersedes
nothing; it is the execution layer under
[`docs/planning/openai.md`](../planning/openai.md) (the QUILL AI Gateway PRD,
1,466 lines, still correct in every structural decision) and re-prices it for
GPT-6 Luna.

Read this if you are about to build any part of free hosted AI. Read the PRD if
you want to know *why* the server looks the way it does. This document answers
three questions the PRD does not: **what is actually built today**, **what the
new model economics change**, and **what the smallest product that delivers real
value looks like** — which, on the current evidence, was QuillLite. It shipped
there first and reached QUILL on 2026-09-23; section 5.4 records how, and what
that cost.

---

## 1. The single most important fact

**The server is built. The client is not.**

`quill-ai-gateway/` is 47 tracked files, roughly 3,450 lines of application code
and tests: device-code auth, a quota engine, a model registry, an admin JSON
API, a server-rendered admin dashboard, Docker and Caddy deployment files,
migrations, and a test suite that runs on in-memory SQLite and fakeredis with no
external services.

On the QUILL side of the wire there is **nothing**. No `GatewayBackend`, no
`"quill_gateway"` provider id, no sign-in surface, no quota display, no settings
field, no egress-audit entry. A code search for `quillforall`, `ai_gateway` or
`hosted_ai` across `quill/` returns only unrelated hits on `tool_gateway`.

And QuillLite has no AI at all — not a backend, not a command, not a menu item,
not one import of `quill.core.ai` across its 45 modules.

So the work is not "design a hosted AI service." It is: **re-price the built
service for Luna 6, close four specific holes in it, and build the client half
for the first time — starting with the product that has none.**

---

## 2. What exists today, precisely

### 2.1 The gateway server (`quill-ai-gateway/`)

| File | Lines | What it already does |
|---|---:|---|
| `app/models.py` | 290 | Full schema: `users`, `devices`, `usage_events`, `monthly_usage_summary`, `feature_flags`, `gateway_config`, `gateway_models`, `user_feature_caps`, `diagnostic_records`, `admin_actions` |
| `app/limits.py` | 575 | The quota engine: hourly, daily and monthly caps per user *and* per device, per-feature monthly sub-caps, a per-user cost ceiling, a global budget cap with auto-pause, 50/75/90/100% alerting, and input-token and chunk-count rejection |
| `app/auth.py` | 207 | RFC 8628 device-code flow, SHA-256 token hashing (the raw token is never stored), `require_auth`, `require_admin` against an environment allowlist |
| `app/routes/admin.py` | 309 | Models on/off/default, every config key, user usage, user status, user delete, device revoke, feature flags, spend |
| `app/routes/dashboard.py` | 349 | Server-rendered HTML admin console, no JavaScript |
| `app/routes/chat.py` | 163 | The one inference endpoint, `POST /v1/chat` |
| `app/prompts.py` | 57 | Five fixed server-side system prompts; the client supplies only a user prompt |
| `app/openai_client.py` | 58 | The only file that ever reads `OPENAI_API_KEY` |
| `tests/` | 585 | 45 tests over the quota engine, the size safeguards, the auth flow, the registry, the admin API and the dashboard |

Three design decisions in there are worth naming, because everything below
depends on them holding.

1. **The client never sends a system prompt.** `app/prompts.py`'s `TEMPLATES`
   live in code, not in the admin-tunable config table, precisely so a patched
   client cannot smuggle an unapproved use through an approved `feature` id.
2. **The client never picks a model.** `resolve_default_model()` reads the one
   enabled default row; the request body has no model field at all.
3. **Every number is a database row, not a constant.** `resolve_limit()` reads
   `gateway_config` through a 30-second Redis cache, with hardcoded fail-safes
   used only against an unseeded database — and those fail-safes are
   deliberately the *conservative* values, so a missing row can never make the
   service more permissive than intended.

### 2.2 The seams on the QUILL side

The PRD's section 0 inventory is still accurate. Verified today:

- `quill/core/ai/backend.py` — the `AIBackend` ABC (`is_available`, `respond`,
  `respond_stream`). A `GatewayBackend` is a drop-in subclass.
- `quill/core/ai/assistant.py:149` — `make_default_backend()`, the cascade a
  gateway backend slots into.
- `quill/core/ai/providers.py` — `ALL_PROVIDERS`, currently
  `off, ollama, ollama_cloud, openai, claude, openrouter, gemini, custom`.
- `quill/core/assistant_ai.py` — `save_provider_api_key` /
  `load_provider_api_key`: Windows Credential Manager first, DPAPI-encrypted
  JSON fallback, target `QUILL:assistant:<provider>:api-key`.
- `quill/core/ai/device_login.py` (174 lines) — a working, wx-free,
  injected-poster RFC 8628 state machine using the exact
  `pending / slow_down / authorized / denied / expired` vocabulary that the
  gateway's `poll_device_token()` returns. The two halves were written against
  each other and have never been connected.
- `quill/core/auth/` — the Token Manager package (PKCE, flows, provider
  registry, `QUILL-AUTH-*` coded errors, refresh) from the BARD program.
- `quill/core/ai/admin_policy.py` — organization allow/block over provider ids.
- `quill/tools/network_egress_audit.py` — GATE-9. One new reviewed entry needed.

### 2.3 QuillLite

`quill/apps/lite*.py` is 45 modules and does not import `quill.core.ai` once.
Feature areas live in `quill/core/lite/features.py` (`AREAS`,
`APP_ID = "quilllite"`), so a new switchable area is the established way to add
a surface a user can turn off entirely.

---

## 3. The economics, recomputed against what we actually enforce

The briefing models 3,500 input and 500 output tokens per request. **The gateway
does not permit that.** `max_input_tokens` is seeded at 1,500
(`migrations/002_seed_gateway_config.sql`). So the real per-request worst case is
lower than modelled:

| Assumption | Input cost | Output cost | Cost per request |
|---|---:|---:|---:|
| Briefing model (3,500 in / 500 out) | $0.00035 | $0.00025 | **$0.00060** |
| Gateway cap (1,500 in / 500 out) | $0.00015 | $0.00025 | **$0.00040** |

At the enforced cap, with the seeded 100 requests per user per month:

| Users | Utilization | Requests per month | Luna 6 cost |
|---:|---:|---:|---:|
| 500 | 30% (realistic) | 15,000 | **$6.00** |
| 500 | 100% (worst case) | 50,000 | **$20.00** |
| 1,000 | 30% | 30,000 | **$12.00** |
| 1,000 | 100% | 100,000 | **$40.00** |

The pricing row already seeded in `migrations/002_seed_gateway_config.sql` is
`('gpt-5-nano', 'GPT-5 Nano', true, true, 0.10, 0.50)` — **$0.10 and $0.50 per
million, which is exactly Luna 6's price.** The cost math needs no change at all.
Only the `model_id` and `label` change, and that is one `UPDATE`, or one click in
the admin dashboard.

### 3.1 The two numbers that are wrong today

**The global budget cap is too tight.** `global_monthly_budget_usd` is seeded at
$25.00, and the 500-user worst case is $20.00. That is 25% headroom. Any
reasoning-token leakage (below) doubles the bill and trips the auto-pause, which
turns hosted AI off *for everyone* — the loudest possible failure. Raise it to
**$40 at 500 users, $80 at 1,000** and keep the alert thresholds where they are.
A budget cap should be a backstop that never fires in normal operation, not a
ceiling normal operation leans on.

**The per-user cost ceiling never binds.** `monthly_cost_cap_usd` is $0.15, but a
user who exhausts all 100 requests at the full input cap spends $0.040. The
ceiling sits 3.75x above anything reachable, so it is decoration. Tighten it to
**$0.08** — still double the reachable worst case, so it cannot false-trip a
legitimate user, but now a genuine anomaly (a model change, a pricing change, a
bug that stops counting requests) meets a second fence before the global one.

### 3.2 Reasoning tokens are the whole risk

Luna 6 defaults to **medium** reasoning, and reasoning tokens bill as output
tokens. At roughly 800 reasoning tokens per request — a modest estimate for
medium on a short task — per-request cost goes from $0.00040 to $0.00080.
**Reasoning at its default setting doubles the entire service bill**, invisibly,
with nothing in the response to show for it.

There is a second, worse failure mode. `max_output_tokens` caps *total* output
including reasoning. If reasoning consumes the 500-token budget, the user
receives an **empty response and is charged for it**. That reads as "QUILL's AI
is broken," and it is exactly the shape of bug that never gets filed, only
abandoned.

The decision (section 5.3) is therefore: reasoning effort is a per-feature **code
constant** set at the floor, and the gateway detects an empty completion and
refuses to charge for it.

### 3.3 Things not worth doing

- **Prompt caching.** Cached input is $0.01 per million, a 90% saving — on a
  cache hit. Our prefix is a roughly 60-token fixed template followed by unique
  user text. It will never hit. Skip it; do not add a `cached_tokens` column for
  it.
- **Batch and Flex at 50%.** Saves $3 to $10 a month on an interactive product,
  and the latency disqualifies every feature in scope. Revisit only if a
  background "summarize this folder overnight" feature is ever built.
- **A multi-provider cost router.** Groq GPT-OSS-20B saves about $9 a month and
  costs a 131K context window plus a second integration to maintain. The
  briefing's call is correct: keep the abstraction, do not build the router. See
  section 8.3 for the one-click-fallback version, which is worth building for
  *availability*, not for cost.

---

## 4. The threat that actually costs money

Per-user quotas are solved. The gateway's `check_request_allowed()` is a good
piece of work: it fails closed, increments atomically so concurrent requests
cannot race past a cap, and rejects a blocked user before incrementing anything
so their retries do not pollute rate-limit windows meant for legitimate traffic.

**None of that matters if accounts are free to mint.**

`POST /v1/device/code` requires no authentication, is not rate limited, and
`confirm_device_code()` creates a brand-new pseudonymous `User` — with a fresh
100-request, $0.08 allowance — for anyone who posts a form to `/connect`. The
whole flow is three HTTP requests and scripts in about fifteen lines. The
per-user cap is not a cost bound; it is a cost *quantum*. The only real bound
today is the global budget cap, which means the first sustained abuse ends with
hosted AI switched off for every legitimate user.

This is the one hole that must close before any public beta. In order of cost to
build:

1. **Rate-limit registration by IP.** Redis counters on `/v1/device/code` and
   `/connect` — say 5 per hour and 20 per day per IP, 50 per day per /24. Cheap,
   reuses the `_increment_and_check` primitive that already exists, and stops the
   unsophisticated case outright.
2. **A new-account allowance ramp.** A user's first 48 hours carry a reduced cap
   (15 requests); the full 100 unlocks afterward. A throwaway-account farm then
   yields 15 requests per account instead of 100 — a 6.7x cost increase for the
   attacker — and a legitimate new user, who is exploring rather than grinding,
   almost never notices. One `resolve_limit` branch on `User.created_at`, with
   `new_account_hours` and `new_account_request_cap` as ordinary `gateway_config`
   rows.
3. **A human step on `/connect` that is not free to script.** A constraint, not a
   preference: **no image CAPTCHA and no audio CAPTCHA, ever.** This is an
   accessibility-first product and those are the canonical accessibility failure.
   Two acceptable options: a hashcash-style proof-of-work the browser computes
   (fully accessible, no third party, no data leaves us, costs an attacker CPU
   per account), or Cloudflare Turnstile in managed mode (usually invisible, has
   a real accessibility story, but puts a third party in the sign-in path).
   **Recommend proof-of-work** — it keeps the sign-in page self-contained and
   dependency-free, which matters for a page a screen-reader user may reach from
   an unfamiliar device.
4. **Email verification as an unlock, not a gate.** Anonymous registration keeps
   the small allowance forever; verifying an email raises it to the full 100 and
   makes the quota follow the person across devices. `User.email` and
   `email_verified_at` already exist in the schema for exactly this. Deliberately
   last — "no account required" is the accessibility win, and it must survive.

Measures 1 and 2 are a day of work between them and remove most of the exposure.
Ship those with Phase 1, measure 3 before public beta, and measure 4 only if the
data says so.

### 4.1 The rest of the token model

**The provider key.** Never in the client, never in the repository, read in
exactly one file (`app/openai_client.py`). This is already right, and it is the
reason the gateway exists at all. The contrast worth keeping in mind: the bundled
GitHub feedback token (`quill/core/feedback_token.py`) *is* in every installer,
and its own docstring explains that this is only tolerable because its scope
bounds the damage to issue spam. An OpenAI key has no such bound. It never ships.

**The gateway session token.** Opaque, 32 bytes from `secrets.token_urlsafe`,
stored server-side only as a SHA-256 hash, and revocable with effect on the very
next request because `require_auth` looks the device row up every time.
Client-side it goes into the existing secure store at
`QUILL:assistant:quill_gateway:api-key` — Credential Manager first,
DPAPI-encrypted JSON fallback. No new secure-storage code, one new target string.

**Replay from another machine.** A leaked token works anywhere. Do *not* hard-bind
it to an IP: that breaks roaming, mobile tethering, and every user behind
carrier-grade NAT, and locking someone out of their assistive tooling because
they moved rooms is a worse outcome than the abuse it prevents. Instead: record
first-seen and last-seen coarse network (/16 and ASN) on the device row, set
`abuse_flag = "anomalous_device"` when one token is used from many distinct /16s
in a day, and let the existing `device_hourly_request_cap` bound the blast radius
to 8 requests an hour. Flag, review, revoke — never auto-lock.

**Rotation.** Missing entirely. Add `POST /v1/device/rotate` (authenticated by
the current token, returns a new one, replaces the hash in a single transaction)
and have the client rotate any token older than 180 days. Without it there is no
answer to "a token may have leaked but I am not sure" short of forcing a full
re-registration.

**Extraction from the client machine.** DPAPI ties the ciphertext to the
logged-in Windows user, so extraction requires already being that user. The blast
radius is one user's monthly allowance, revocable in one dashboard click.
Accepted risk, documented, not further engineered.

---

## 5. Decisions

### 5.1 No tools. No web search. No file search. Ever, on the free tier.

The briefing is right that tool calls are now the dominant financial risk: OpenAI
web search at $10 per 1,000 calls would be $500 a month against $30 of inference
on the same 50,000 requests — **sixteen times the model cost.**

The decision is stronger than "do not enable it by default." The free hosted tier
sends a chat completion with a `messages` array and nothing else. No `tools`, no
`tool_choice`, no `web_search_options`, no hosted file search, no attachments, no
`store`.

This is not left to reviewer discipline. **Build a request-shape gate:** a test in
`quill-ai-gateway/tests/test_openai_request_shape.py` that captures the JSON body
`app/openai_client.complete()` would send and asserts its top-level keys are
exactly the allowlist — `model`, `messages`, `max_completion_tokens`,
`reasoning_effort` — and fails on any addition. A key that costs $10 per thousand
calls should not be addable without a test turning red.

BYOK users keep everything. Web research (`quill/core/ai/web_research.py`), the
agent tool loop, the whole gateway of editor tools — all of that stays exactly as
it is for someone using their own key. The free tier is a narrower product, not a
crippled one, and the difference is stated plainly in the UI.

### 5.2 Context is scoped on the client, before the request exists

The cheapest token is the one never sent. Three rules, enforced client-side and
re-checked server-side:

- **Selection first.** Summarize, Rewrite, Proofread and Explain operate on the
  **selection**. With no selection they use the **current paragraph, or the
  current heading's section** — never the document. If the resolved text exceeds
  the client's cached `max_input_tokens`, the command says so and offers either
  the first N characters or a switch to a BYOK provider. It never silently
  truncates.
- **Local retrieval for document Q&A.** "Ask about this document" chunks the
  document **locally**, scores chunks against the question with plain keyword
  overlap (BM25-shaped; no embeddings, no extra dependency, no extra API call),
  and sends the best three. Three is `max_chunks_per_request`, already enforced
  server-side, and already un-routable-around because the chunk count is checked
  independently of the token count.
- **Nothing is implicit.** No AI call on typing, on save, on open, on idle, or on
  focus. Every request is a command the user invoked. This is a cost rule, a
  trust rule and a screen-reader rule at once.

The client reads its thresholds from `GET /v1/config` once per session, so an
admin raising a limit takes effect without a client release.

### 5.3 Reasoning effort is a code constant, per feature, at the floor

Same rationale as `app/prompts.py`: a dial that changes what a billed API call
costs is a reviewed code change, not a runtime admin knob. Add a
`REASONING_EFFORT` mapping beside `TEMPLATES`:

| Feature | Effort | Why |
|---|---|---|
| `rewrite` | `none` | Transformation, not inference |
| `proofread` | `none` | Transformation, not inference |
| `summarize` | `none` | Extraction from supplied text |
| `explain` | `none` | Short explanation of supplied text |
| `document_qna` | `low` | The one feature with genuine synthesis; measure before keeping it above `none` |
| `chat` | `none` | **Not shipped.** Open-ended chat is not part of the free tier |
| `alt_text` | `none` | **Not shipped.** Switched off in the database; see 5.7 |

Two mechanical changes in `app/openai_client.py` go with this: `max_tokens`
becomes `max_completion_tokens` (reasoning models reject the older parameter), and
`reasoning_effort` is passed explicitly rather than left to default.

And one guard: if the response text is empty while
`usage.completion_tokens_details.reasoning_tokens` is greater than zero, **do not
charge the user's quota**. Log it, return the ordinary "having trouble, try
again" error, and alert. Billing a user for a blank answer is worse than the
outage it disguises.

### 5.4 QuillLite ships first, and QUILL ships in the same change

QuillLite is the right first client. It has no AI at all, so there is no existing
surface to reconcile, no provider picker to extend, no agent harness to reason
about, and no BYOK user whose configuration might break. It is the smallest
honest test of "does free hosted AI deliver value."

But **CLAUDE.md is explicit: QuillLite may never be ahead of QUILL.** A capability
the small product has and the big one does not is backwards, and invisible —
nobody opens QUILL and notices the absence of a thing they have only ever seen
elsewhere. So:

- `GatewayBackend` and the five feature calls live in **`quill/core/ai/`**,
  shared.
- QUILL gets the same five commands and `"quill_gateway"` in `ALL_PROVIDERS` **in
  the same change**, surfaced through the AI Hub next to the BYOK providers.
- Any divergence in chords is a comment in `keymap.py` *and* a parity-table row
  (family rule 11).

This is family rule 10 working as designed: value flows both ways, violations flow
one.

**Status, 2026-09-23: QUILL has it, and it is QUILL's *default* AI.** The debt
this section anticipated was real for about two weeks and is now paid, and it was
paid further than "surfaced through the AI Hub next to the BYOK providers" — which
would have buried a free, zero-configuration service one dialog deep behind the
very providers it exists to make unnecessary.

- The four wx modules moved out of `quill/apps/lite_ai*.py` into
  `quill/ui/hosted_ai_service.py`, `hosted_ai_dialogs.py`, `hosted_ai_pad.py` and
  `hosted_ai_commands.py`. `DocumentAiMixin` became `HostedAiMixin` with three
  hooks — which window a frame is parented to, which control holds the document,
  and which object holds the settings and the switch — because those are the only
  three things the two editors do differently.
- `quill/ui/main_frame_hosted_ai.py` is QUILL's adapter and its three overrides.
  It has **no commands of its own**, and a test asserts that absence: a second
  implementation is how this rule gets broken quietly, far more easily than a
  missing feature.
- Three of the five chords are QuillLite's, unchanged: `Ctrl+Alt+G` (the pad),
  `Ctrl+Alt+Z` (ask about this document) and `Ctrl+Alt+Shift+K` (the agreement).
  All three were free on QUILL's side, so family rule 2 applied with nothing to
  arbitrate. **Usage and Sign In could not keep theirs**: `Ctrl+Alt+Shift+F7` to
  `F12` are the six QuillVille sibling launchers in QUILL
  (`app_keymaps.SIBLING_APP_ACCELERATORS`), and QuillLite — being the editor on
  its own — has none to launch, so F9 and F10 are free over there and spoken for
  here. QUILL uses `Ctrl+Alt+Shift+F2` and `F4`, and both divergences carry a
  `DIVERGENCES` row in `lite/parity.py` plus a comment in `keymap.py` (rule 11).
  A chord claimed twice means one of the pair silently never fires, which is worse
  than a divergence somebody can read about — exactly the argument
  `cmd_spelling_voice_settings` already made about the same six keys.
- **The AI menu now opens with them**, and the whole provider-and-agent surface
  moved behind `Show advanced AI features`. A fresh install starts in Basic; an
  install that had already run the wizard or stored a provider key stays in
  Advanced, because an update must never take working menus away from somebody
  using them. The derived answer is written to the onboarding state once rather
  than re-derived, so a menu cannot lengthen as a side effect of a key pasted into
  an unrelated feature.
- One sentence could not be shared and is a hook rather than a literal: the
  feature switch is a Customize Features area in QuillLite and the Use AI item in
  QUILL's own menu. Every *other* route sentence was rewritten to name a row that
  exists in both ("Connect or Sign Out in the AI menu"), and QuillLite's row was
  renamed from "Sign In or Out" to match — a row named two ways is a sentence that
  is wrong in one of the two products.

### 5.5 The five commands, and nothing else

"Lite, simplistic, but enough that it provides value." Five:

1. **Summarize** — selection or current section, a few plain sentences.
2. **Rewrite** — clearer and shorter, meaning and tone preserved, replacing the
   selection through the ordinary undo stack.
3. **Proofread** — spelling, grammar and punctuation, returning corrected text.
4. **Explain** — what this passage means, in plain language.
5. **Ask about this document** — one question, answered from the three
   best-matching local chunks, with "the document does not say" as an allowed and
   expected answer.

Deliberately excluded from the free tier: chat with history, agents and the tool
loop, translation, cloud TTS, streaming, and any multi-turn context. Each of
those is a multiplier on cost, a multiplier on complexity, or both.

**And images. Not in QuillLite at all** — see 5.7, which is a decision rather
than an omission.

Every result lands in a **result window, not the document**: the text, the tokens
used, the remaining allowance, and three buttons — Replace selection, Copy, Close.
AI never edits a document without a keystroke saying so. Section 12 is the
full screen-by-screen specification.

### 5.6 No images in QuillLite. Tracked, not forgotten.

QuillLite is a text editor. It has no image model, no picture control, nowhere
an image lives, and adding one to reach a describe-this-picture feature would
be building an image pipeline in order to justify an AI call — which is the
wrong order to do anything in.

So images are out of QuillLite entirely, and the server reflects that rather
than merely not offering it:

- The `alt_text` feature keeps its id and its prompt template, but ships with
  its flag **off**, its per-feature cap at **zero**, and `daily_image_cap` at
  **zero**. Off in one place and uncapped in another is one flag flip away from
  being live and unlimited at the same time.
- It carries a stored `disabled_reason`, and the refusal path now uses it.
  Being told *"describing pictures is not a shipped feature yet"* is a
  completely different fact from *"temporarily paused while we review unusual
  activity"*, and the second sends somebody to support over a feature that does
  not exist.
- The three image-sized limits (`max_image_bytes`, `max_image_edge_px`,
  `daily_image_cap`) are grouped on the console's Limits page under **Not in
  use yet**, shown rather than hidden, so nobody has to wonder whether they are
  doing something. They are not.

**Tracked as a future feature**, with its own entry in the task list at the end
of this document. When it is built it belongs in QUILL first — Glow and Inkwell
are where pictures actually live — and it needs its own cap tuning informed by
real Phase 3 usage data, because a vision call costs several times what a text
call does. Two open questions travel with it: whether the client resizes before
sending (it must), and whether alt text is a *free-tier* feature at all or a
bring-your-own-key one.

### 5.7 Privacy text must be written before the first byte is sent

This feature transmits the user's own writing to OpenAI. That is a fair trade for
a free service and most users will take it, but only if we describe it exactly.

We have got this wrong before — shipped privacy text that claimed more than the
code did was a Radio 3.0 ship blocker. Do not repeat it. Before Phase 1 ships to
anyone outside the team:

- `docs/legal/PRIVACY.md` (and its `.html` and `.epub` renders) gains a hosted-AI
  section stating what is sent (the selected text, or three excerpts and a
  question), to whom (OpenAI, by way of QUILL's gateway), what is stored (usage
  metadata only — feature, model, token counts, cost, timestamp; never prompt or
  document text), for how long (13 months), and what the one exception is
  (`diagnostic_records`: explicit per-incident opt-in, 30-day hard expiry enforced
  by a cron job rather than by policy).
- The sign-in surface says the same thing in two sentences *before* the device
  code appears, not behind a link.
- The claim and the schema are checked against each other. `app/models.py`'s
  module docstring already carries the invariant — "no column in this file may
  ever hold prompt text, document text, or a full AI response" — and it is
  currently true. It must stay true, and the privacy text must not outrun it.

---

## 6. Gaps in the built server, ranked

These are the concrete deltas. Four of them were things this request asked for
that did not exist.

> **All twelve are now done** (2026-09-23), along with three more found while
> building them: the new-account ramp could exceed the normal allowance, every
> post-gate failure path charged the user for a request that never happened, and
> a feature's stored `disabled_reason` was never shown to anybody. The table is
> kept as the record of what was wrong and why it mattered; section 16.1 is the
> list of what was built. The gateway suite went from 45 tests to 205.

| # | Gap | Where | Priority |
|---|---|---|---|
| 1 | **No way to reset a user's usage.** Nothing clears the Redis counters or the monthly summary | `app/routes/admin.py`, `app/limits.py` | **Asked for. Phase 1** |
| 2 | **No way to set a per-user cap.** `User.monthly_request_cap`, `monthly_cost_cap_usd` and `UserFeatureCap` all exist in the schema with no route that writes them; `AdminAction`'s docstring even lists `set_quota` as an action | `app/routes/admin.py` | **Asked for. Phase 1** |
| 3 | **Unlimited free account minting** (section 4) | `app/auth.py`, `app/routes/device.py` | **Phase 1** |
| 4 | **No way to find a user.** Users are pseudonymous UUIDs, so when someone writes to support saying "my AI stopped working" there is no lookup | `app/routes/admin.py`, client UI | **Phase 1** |
| 5 | No token rotation endpoint | `app/routes/device.py` | Phase 2 |
| 6 | `max_tokens` will be rejected by a reasoning model, and `reasoning_effort` is never sent | `app/openai_client.py` | **Phase 1** |
| 7 | An empty completion with reasoning tokens still charges the user | `app/routes/chat.py` | **Phase 1** |
| 8 | No request-shape gate; nothing stops a future `tools` key | `tests/` | **Phase 1** |
| 9 | Pending device grants live in a process-local dict, so two Gunicorn workers cannot complete each other's flows | `app/auth.py` | **Phase 1 — a correctness bug at any real deployment, not a scale concern** |
| 10 | `gateway_models` has no `base_url` or key-source column, so "swap providers" is a deploy, not a click | `app/models.py`, `app/openai_client.py` | Phase 3 |
| 11 | Reasoning tokens are not recorded separately in `usage_events` | `app/models.py` | Phase 2 |
| 12 | **Nothing validates a config write.** `dashboard.update_config` accepts any float, so `0.15` typed as `15` raises every user's cost ceiling a hundredfold behind a green success message | `app/routes/dashboard.py`, `app/routes/admin.py` | **Phase 1 (13.1)** |

On gap 1, one detail is easy to get wrong: **resetting usage must clear both the
Redis counters and the `MonthlyUsageSummary` row.** Clearing only the counters
leaves `total_cost_usd` intact, so the per-user cost ceiling keeps rejecting the
user and the reset appears not to have worked. Clearing only the summary leaves
the request counters in place. Reset does both, in one transaction, and writes an
`AdminAction` row.

On gap 12, the fix is small and is the highest-value single item in the whole
console: per-key metadata (unit, minimum, maximum, a sentence), a plain-English
rejection when a value is out of range, and a typed confirmation showing the
before-and-after monthly cost whenever a change more than doubles it. Section 13
specifies it.

On gap 4, the fix has a client half: QUILL and QuillLite display a short,
speakable **support ID** (the first eight characters of the user id, grouped like
`A1B2-C3D4`) in the AI panel and in About, and the dashboard gains
`GET /admin/users?q=<prefix>`. Without this, every support conversation about
hosted AI is unresolvable.

---

## 7. Client architecture

### 7.1 New modules

```
quill/core/ai/gateway_client.py    HTTP client: /v1/config, /v1/quota, /v1/chat.
                                   Injected poster, verified TLS, one egress site.
quill/core/ai/gateway_backend.py   GatewayBackend(AIBackend). is_available()
                                   answers from the stored token plus cached config.
quill/core/ai/gateway_session.py   Token storage, sign-in state, support ID,
                                   rotation, sign-out. Wraps device_login.py
                                   pointed at the gateway's endpoints.
quill/core/ai/gateway_context.py   Selection resolution, local chunking, keyword
                                   retrieval, client-side size pre-check.
quill/core/ai/gateway_errors.py    QUILL-AI-GATEWAY-* coded errors (GATE-EC).
```

All five are `wx`-free, strict-typed, and in scope for `mypy quill\core`.

### 7.2 Wiring into what exists

- `providers.py`: add `"quill_gateway"` to `ALL_PROVIDERS`;
  `provider_requires_api_key("quill_gateway")` is **False** (it needs a session
  token, not a key, and that distinction is what keeps "Needs key" from being
  announced at someone who has never had a key); `default_host_for_provider`
  returns the gateway base URL.
- `assistant.py:149`: `make_default_backend()` gains `GatewayBackend` in the
  cascade, and must respect `_note_backend_fallback` — silently answering from a
  different engine than the user chose is already a named rule here.
- `availability.py`: gateway-specific unavailability reasons (signed out, quota
  exhausted with a reset time, globally paused) resolve through
  `describe_ai_availability` like everything else, so every surface says the same
  sentence.
- `admin_policy.py`: `"quill_gateway"` is an ordinary provider id, so a managed
  install can block it with no new code.
- **Safe Mode** (`QUILL_SAFE_MODE=1`) disables hosted AI along with the rest of
  AI. Existing invariant, no exception.
- **GATE-9**: exactly one new `_REVIEWED_EGRESS` entry, its rationale being "an
  explicit AI command the user invoked, or the sign-in flow the user started."

### 7.3 QuillLite surface

- A new switchable area in `quill/core/lite/features.py`: id `hosted_ai`, **off by
  default**. A feature that sends your writing to a third party is not on until
  you say so — and a switched-off area owns nothing, so there is no token file, no
  menu and no settings row until it is enabled.
- One new menu, `AI`, with the five commands plus Sign In, Sign Out and Usage.
  Every enabled item carries a keyboard route in its label via
  `self._menu_label(...)`, and no key collides anywhere in the menu bar
  (`test_menu_accelerators.py`).
- One sign-in dialog and one result window. The device code is announced as
  grouped characters and re-announced on demand, because it is read aloud and
  typed back.
- Under GATE-LITE-COVER every new handler needs a behavioural test that **calls**
  it — written as `(lambda w: w.cmd_ai_summarize(), ...)`, not as a parametrized
  handler name, or the AST scan cannot see it. Then regenerate with
  `python -m quill.tools.lite_command_coverage --write`.

Section 12 specifies every one of these surfaces in full.

### 7.4 Accessibility requirements on the new surfaces

These are gates in this repository, not aspirations. Any UI work here goes through
the accessibility specialists before it is considered done.

- **GATE-13**: announce the *result* — the answer arrived, the quota changed, the
  request failed. Never announce a window title, a focus move, or a control name
  the reader already says. A long request announces once when it starts and once
  when it finishes, never on a timer.
- **GATE-14**: no duplicate access keys within a window. OK, Cancel and Close carry
  none.
- **GATE-&lt;APP&gt;-HELP**: every new control gets inline `SetHelpText` at its
  construction site, or the help audit files it as `missing` and the build fails.
  Help set anywhere else proves nothing.
- **Dialogs** go through `_show_modal_dialog`, never `ShowModal()` directly, and
  Close buttons are bound via `dialog_contract.bind_close_button`.
- **Never block the editor.** A hosted request runs on
  `stability.task_manager.QuillTaskManager` and returns to the UI thread through
  `wx.CallAfter`. Typing continues throughout. This is not negotiable for a tool
  people write in.
- **The dashboard** is already no-JavaScript server-rendered HTML, which is the
  right foundation, but it still needs a real accessibility pass before it is used
  in anger: status must never be carried by colour alone, and every chart needs a
  data-table twin.

---

## 8. Configuration changes

### 8.1 `gateway_models`

```sql
UPDATE gateway_models SET enabled = false, is_default = false
 WHERE model_id = 'gpt-5-nano';

INSERT INTO gateway_models (model_id, label, enabled, is_default,
                            input_cost_per_million_usd,
                            output_cost_per_million_usd)
VALUES ('gpt-6-luna', 'GPT-6 Luna', true, true, 0.10, 0.50);
```

Confirm the exact model id string against the provider's own model list before
running this. It is the string that goes into a billed API call.

### 8.2 `gateway_config`

| Key | Seeded | Proposed | Why |
|---|---:|---:|---|
| `global_monthly_budget_usd` | 25.00 | **40.00** | 25% headroom over the 500-user worst case is not headroom (3.1) |
| `monthly_cost_cap_usd` | 0.15 | **0.08** | 3.75x above anything reachable is decoration (3.1) |
| `max_input_tokens` | 1500 | 1500 | Keep. It is the context discipline (5.2) |
| `max_output_tokens` | 500 | 500 | Keep, now sent as `max_completion_tokens` |
| `max_chunks_per_request` | 3 | 3 | Keep |
| `monthly_request_cap` | 100 | 100 | Keep |
| `daily_request_cap` | 20 | 20 | Keep |
| `hourly_request_cap` | 8 | 8 | Keep |
| `new_account_hours` | — | **48** | New (4.2) |
| `new_account_request_cap` | — | **15** | New (4.2) |
| `registration_hourly_cap_per_ip` | — | **5** | New (4.1) |
| `registration_daily_cap_per_ip` | — | **20** | New (4.1) |
| `feature_cap.proofread` | — | **60** | New feature |
| `feature_cap.explain` | — | **60** | New feature |

### 8.3 Availability fallback, not cost fallback

Keep Gemini 2.5 Flash-Lite and Groq GPT-OSS-20B as `gateway_models` rows that are
**configured and disabled**. The reason is not the $9 a month; it is that a Luna
outage becomes a dashboard click instead of a deploy. Making that real needs gap
10 (a `base_url` and a key-source column), because `openai_client.py` currently
hardcodes one base URL and one key. Groq is OpenAI-compatible and needs only those
two columns; Gemini would need a second adapter and is therefore a later, larger
decision.

---

## 9. Phases

Each phase has an acceptance criterion that is a fact about the system, not a
feeling about it.

**Phase 0 — Verify the built server.** Run the existing 45 tests. Stand the
service up locally against SQLite and fakeredis. Walk the device flow by hand.
Read `app/limits.py` end to end. *Accepted when:* `pytest` is green in
`quill-ai-gateway/`, and one device has registered, spent quota, hit a limit, and
been reset by hand at the database level.

**Phase 1 — Close the gaps, and build the QuillLite client.** Server: gaps 1, 2,
3, 4, 6, 7, 8, 9. Client: the five modules in 7.1, the QuillLite `hosted_ai` area,
the five commands, sign-in, the result window, the usage display, the support ID.
QUILL gets the same five commands and the provider id in the same change. Privacy
text written and shipped (5.7). Console: gap 12's validation, the cost calculator
(13.3), and the reset-allowance and per-person-cap controls (13.6). Behind
`future.ai_gateway`, internal only.
*Accepted when:* a tester signs in from a clean install with no API key and no
account, summarizes a selection, asks a question about a document, exhausts a
daily cap and is told exactly when it resets, and an admin resets their usage from
the dashboard and the tester's next request succeeds. And: the request-shape test
fails if `tools` is added to the outgoing body.

**Phase 2 — Operate it.** Token rotation (gap 5). Reasoning tokens recorded
separately (gap 11). The alert webhook wired to somewhere a human reads. Cron jobs
scheduled (`cleanup-expired`, `reconcile-usage`, partition maintenance). A
dashboard accessibility pass by the accessibility specialists (13.10), plus the
remaining console pages: settings-that-are-not-knobs (13.4), safety checks (13.8)
and the glossary (13.9). The runbook for "the spend alert fired at 2am" written
down. *Accepted when:* a 90% budget alert
has fired in a drill, and the person on call knew what to do from the runbook
alone.

**Phase 3 — Small public beta.** Proof-of-work on `/connect` (4.3). Remove the
feature flag for a bounded cohort. Raise the budget cap deliberately. Watch
`usage_events` for a month: real tokens per request, real requests per user, real
abuse flags. *Accepted when:* thirty days of data exist, and the caps in 8.2 have
been re-derived from that data rather than from this document's estimates.

**Phase 4 — General availability.** Open registration. Publish the numbers.
Revisit the allowance — the briefing is right that at these prices the interesting
move is to make the free tier *more* useful rather than to pocket the savings, and
Phase 3's data is what says how much more.

**Phase 5 — Optional.** Email-verified accounts for multi-device continuity (4.4).
Availability fallback made real (8.3). Only if the data asks for them.

---

## 10. Budget

| Scenario | Modelled inference | Recommended cap | Authorize |
|---|---:|---:|---:|
| 500 users, 30% utilization | $6/month | $40/month | **$50/month** |
| 500 users, 100% utilization | $20/month | $40/month | $50/month |
| 1,000 users, 30% | $12/month | $80/month | **$100/month** |
| 1,000 users, 100% | $40/month | $80/month | $100/month |

The briefing's instinct — authorize roughly 3x the modelled spend — is right, and
the gap between "modelled" and "cap" is deliberate: the cap is what auto-pauses
the service, so it needs enough room that it only fires on something genuinely
wrong. Serving a thousand people for well under $1,200 a year is a real number,
and at that price the constraint on this program is operational care, not money.

---

## 11. Open questions for Jeff

1. **Hosting.** The PRD recommends the server already running GLOW and
   `quillin-hub`, mirroring GLOW's Docker Compose plus Caddy shape. Confirm — and
   confirm `gateway.quillforall.org` as the hostname (it is already the default in
   `app/config.py`).
2. **Proof-of-work or Turnstile** for `/connect` (4.3). The recommendation is
   proof-of-work, to keep a third party out of the sign-in path.
3. **Where budget alerts go.** `GATEWAY_ALERT_WEBHOOK_URL` takes a Slack or
   Discord compatible incoming webhook. Left empty, alerts are logged locally and
   nobody sees them.
4. **The `gpt-6-luna` model id string**, verified against the provider's own model
   list rather than against a briefing.
5. **Does QuillLite's free AI require the QUILL installer's presence**, or is it
   fully standalone? It affects nothing in the design, but it decides whether
   sign-in lives in one place or two for a user who runs both.
6. **The support-ID question.** Displaying eight characters of the user id makes
   support possible, and is a small deanonymization vector for anyone who can see
   the user's screen. The recommendation is to ship it; it is worth a deliberate
   yes.

---

## 12. The QuillLite experience, screen by screen

This section is the specification, not a sketch. Where it names a keystroke, a
sentence, or a tab order, that is the thing to build.

### 12.1 Three findings from the keymap that decide the design

Before any screen: the QuillLite command table
(`quill/core/lite/commands.py`, 900-odd rows) and QUILL's `DEFAULT_KEYMAP` are
both dense. Measured today, the chords free in **both** tables are:

`Ctrl+Alt+G`, `Ctrl+Alt+Z`, `Ctrl+Alt+Shift+K`. **Three.**

Family rule 2 says a command both products have keeps the same chord, so a
design needing six entry points cannot have them. That is not a constraint to
work around; it is the answer. **One chord opens one surface, and everything
lives inside it.** Which is the better design anyway: one consent surface, one
place that shows what will be sent, one place that shows what is left, one
result view.

Second finding: QuillLite's menu bar is **generated from the command table**,
not hand-appended, and two menus (Clipboard, Spelling) were *demoted* from
top-level to submenus on the explicit reasoning that a top-level menu is "two
more things to walk past on every Alt press." `test_menu_shape_against_microsoft.py`
pins the top-level order to Word, WordPad and Notepad — none of which has an AI
menu. So: **Tools > AI**, a submenu, exactly like Tools > Spelling. Not a
tenth top-level menu.

Third: the surface must not block the editor, and a modal dialog does. So the
AI pad is a **`wx.Frame`, modeless** — which is precisely the case CLAUDE.md
warns about: a `wx.Frame` does not answer `ID_CANCEL` for free, so its Close
button must be bound through `dialog_contract.bind_close_button` or it ships
doing nothing. And per the Radio close-modal gotcha, closing it never opens a
confirmation from inside `EVT_CLOSE` on wxMSW. Closing discards. No prompt.

### 12.2 Turning it on

Hosted AI is a feature **area**, id `hosted_ai`, **off by default**
(`quill/core/lite/features.py`). Off means it owns nothing: no menu, no status
cell, no token file, no settings rows, nothing on disk.

It is turned on where every other area is, in **Tools > Customize Features**
(`Ctrl+Alt+F10`), which is a filter-as-you-type list. The area's description —
what the reader reads when the user arrives on the row — is the whole consent
story in one paragraph:

> **AI help (sends your text to QUILL's servers).** Summarize, rewrite,
> proofread or explain the passage you have selected, and ask questions about
> the document you have open. The text you select is sent over the internet to
> QUILL, and on to OpenAI, which produces the answer. QUILL stores how many
> requests you made and how many words they used — never the text itself, and
> never the answer. This is free, with a monthly allowance. Off until you turn
> it on.

Turning it on adds Tools > AI, one status-bar cell and one Preferences page.
It does **not** sign anyone in and does not make any network call. Nothing
reaches the network until section 12.3 completes.

Turning it off signs out, deletes the stored token, removes the menu and the
cell, and tells the gateway to revoke the device. An area that is off owns
nothing, and a revoked token is the only kind worth leaving behind.

### 12.3 Signing in

**Tools > AI > Sign In** (no chord; rule 9 — this is done once).

A modeless `wx.Frame`, "QUILL AI Sign-In", with a single vertical flow. Tab
order is exactly reading order, which is the only tab order this window is
allowed to have.

**Step 1, before any network call.** The window opens showing what is about to
happen, and focus lands on the first paragraph:

> QUILL's free AI is hosted by QUILL. To use it you need to connect this
> computer once.
>
> There is no account, no password and no email address. QUILL will show you
> an eight-character code. Open the web page on any device — this one, a phone,
> anything with a browser — and type the code.
>
> When you use AI, the text you selected is sent to QUILL and on to OpenAI.
> QUILL records how many requests you make and how big they were. QUILL does
> not record what you wrote or what came back.

Then: **Show me my code** (default), **Read the privacy page** (opens
`docs/legal/PRIVACY.md`'s hosted-AI section in the help viewer), **Cancel**.

No network call has happened yet. That matters: a user who reads this and
changes their mind has sent nothing.

**Step 2, the code.** `Show me my code` posts `/v1/device/code` on the task
manager. On success the window's content is replaced in place — focus does not
jump to a new window — and a status line updates, which is exactly the case
GATE-12 wants announced and GATE-13 permits (a label change on unfocused text
is what the reader does not say):

> Your code is A B C D dash 1 2 3 4. Go to quillforall.org slash connect and
> type it. QUILL is waiting; this window will say when you are connected.

The code is displayed in a read-only text field, **not** a static label, so the
user can review it character by character with arrow keys, select it and copy
it. That single choice is the difference between a code a screen-reader user
can verify and one they have to trust.

Three buttons: **Say the code again** (re-announces, grouped and spelled:
"Alpha, Bravo, Charlie, Delta, dash, one, two, three, four"), **Copy the code**,
**Cancel**.

The code alphabet already excludes `I L O U 0 1 5 8` (`app/auth.py`'s
`_USER_CODE_ALPHABET`) because those are the characters people mishear and
mistype. Keep that; it is load-bearing.

**Step 3, polling.** The client polls `/v1/device/token` at the server-supplied
interval, honouring `slow_down` — `quill/core/ai/device_login.py` already
implements this state machine exactly. Polling is silent. **No progress chatter,
no ticking, no "still waiting" every five seconds.** One announcement when the
state changes, and not before.

**Step 4, connected.** Content replaces in place; status line announces once:

> Connected. You have 100 AI requests this month. Your support ID is A1B2-C3D4 —
> QUILL support will ask for this if you ever need help.

Focus moves to **Close**, which is the only button left.

**Failures**, each one sentence, each saying what to do:

| What happened | What is said |
|---|---|
| Code expired (15 minutes) | "That code has expired. Choose Show me my code for a fresh one." |
| Denied at the web page | "The connection was refused at the web page. Choose Show me my code to try again." |
| No internet | "QUILL could not reach the internet. Check your connection and try again." |
| Gateway down | "QUILL's AI service is not answering right now. Try again later — nothing is wrong with your computer." |
| Registration throttled (§4.1) | "Too many computers have connected from this network recently. Try again in an hour." |

The last one is the abuse throttle speaking, and it must not read as a fault in
the user's machine.

### 12.4 Tools > AI

| Label | Key | What it does |
|---|---|---|
| `&AI Assistant...` | `Ctrl+Alt+G` | Opens the pad (12.5) |
| `&Ask About This Document...` | `Ctrl+Alt+Z` | Opens the pad on the Ask tab (12.7) |
| — separator — | | |
| `&Usage...` | — | How much is left, and when it resets (12.9) |
| `&Sign In...` / `Sign &Out` | — | Whichever applies; never both |

Five rows. Every enabled row carries its key in the label via
`self._menu_label(...)`, so the menu shows whatever is *actually* bound and
follows a rebind. No two `&` letters collide inside Tools (GATE-14). Signed
out, the four AI rows are **dimmed, not removed** — the same call the Markdown
and HTML tag rows make, and for the same reason: a dimmed row announces itself
as unavailable the moment a reader arrives on it, and a vanished row leaves
somebody hunting the menus for a feature they know the app has.

`Ctrl+Alt+Z` is spent on Ask About This Document because it is the one command
whose input is a question rather than the selection, so it is the one worth
reaching without going through the pad's action list first.
`Ctrl+Alt+Shift+K` stays unspent. Both must be re-checked against both tables
at build time; `test_family_rules_and_gates.py` and
`test_menu_accelerators.py` are what catch a collision.

### 12.5 The AI Assistant pad

`Ctrl+Alt+G`. A modeless `wx.Frame` titled "AI Assistant". It never takes
focus on its own, never blocks typing, and is the only surface any of the five
features is reached through.

Opening it does **not** make a network call.

Tab order, top to bottom:

1. **What will be sent** — read-only multi-line text, focused on open. The
   reader reads it, so QUILL announces nothing (GATE-13). It holds the resolved
   input, resolved the moment the pad opened:

   - a selection, if there is one;
   - otherwise the current paragraph;
   - otherwise, in a document with headings, the current heading's section.

   Never the whole document. Above the field, a one-line summary: *"About to
   send: 412 words from your selection."*

2. **Change what is sent** — a three-way choice (Selection / This paragraph /
   This section). Present only when more than one is available. This exists so
   that the answer to "why did it summarize the wrong thing" is a control, not
   a support ticket.

3. **What do you want done?** — a single-selection list, five rows, arrow keys.
   Not a combo box: a list is one keystroke to hear all five.

   | Row | What the reader hears when arriving on it |
   |---|---|
   | Summarize | "Summarize. A few plain sentences saying what this passage says." |
   | Rewrite | "Rewrite. The same meaning, clearer and shorter." |
   | Proofread | "Proofread. Spelling, grammar and punctuation corrected, wording left alone." |
   | Explain | "Explain. What this passage means, in plain language." |
   | Ask a question about the document | "Ask a question. Type a question; QUILL finds the parts of the document that answer it." |

   Those sentences are the controls' inline `SetHelpText`, which is also what
   F1 reads, which is also what the generated `docs/f1-help-reference.md`
   renders. One sentence, written once, reaching three places.

4. **Your question** — a text field, **shown only when the fifth row is
   selected.** Shown, not enabled-and-empty: a field that is present but
   meaningless is a stop on every Tab cycle forever.

5. **Send** (default button) / **Close**.

6. **Allowance** — read-only status text, last in the order because it is
   reference, not action: *"94 of 100 requests left this month. 17 of 20 left
   today."* It updates after every send.

**While it runs.** Send disables, the status line changes to *"Working…"*, and
the work runs on `QuillTaskManager`. The editor stays completely live — the
user can type, save, switch documents, close the pad. Nothing is announced
during the wait. A request that has run 10 seconds updates the status line once
more: *"Still working. Press Close to stop waiting; this will not cost you a
request if it has not finished."*

**When it finishes.** The result window opens (12.6). Because focus moves to a
new window, the screen reader announces the window and reads the result itself
— so **QUILL announces nothing** (GATE-13: never announce what the reader
already says). The pad's Allowance line updates silently behind it.

If the user closed the pad while it ran, the result window still opens, but it
does **not** take focus. The pad's absence is not a cancellation, and stealing
focus from someone who has gone back to typing is worse than any benefit.

### 12.6 The result window

A modeless `wx.Frame`, titled with the action — "Summary", "Rewrite",
"Proofread", "Explanation", "Answer". Focus lands on the result text, which the
reader reads. Nothing is announced on top of that.

1. **The result** — read-only, multi-line, arrow-navigable, selectable,
   focused on open. Read-only because AI output is a proposal. Editing happens
   in the document.
2. **Replace my selection** — present **only** when the request came from a
   selection and that selection still exists and is unchanged. Applies through
   the ordinary undo stack, so `Ctrl+Z` takes it back like any edit. Announces
   the outcome, which is a state change with no focus move: *"Replaced. Press
   Control Z to undo."*
3. **Copy** — to the clipboard. *"Copied."*
4. **Insert below** — puts the result under the current paragraph, with a blank
   line. For summaries and answers, which usually want to live beside the text
   rather than replace it.
5. **Try again** — reopens the pad with the same input and the same action
   selected. Costs another request, and the button's help text says so:
   *"Sends the same text again. This uses one more of your requests."*
6. **Close**.
7. **What this used** — read-only: *"Used 1 request. 93 of 100 left this month.
   Sent 412 words, received 96."* Last in tab order. Present on every result,
   because a free allowance the user cannot see themselves spending is one they
   will be surprised to run out of.

**AI never edits a document without a keystroke saying so.** Nothing in this
window applies automatically, on a timer, or on close.

### 12.7 Ask about this document

`Ctrl+Alt+Z`, or the fifth row of the pad. Same pad, one difference: the input
is a question, and the "What will be sent" field shows **what the local
retrieval chose**, before sending:

> About to send 3 excerpts from this document (about 900 words), and your
> question.
>
> Excerpt 1, from "Background": ...
> Excerpt 2, from "Method": ...
> Excerpt 3, from "Results": ...

The chunking and the scoring are local (§5.2): plain keyword overlap, no
embeddings, no extra API call, no extra dependency. Showing the excerpts is not
a debug affordance — it is the only way a user can tell the difference between
"the AI got it wrong" and "it never saw the right paragraph," and that
distinction decides whether they rephrase or give up.

Three is `max_chunks_per_request`, read from `/v1/config`, enforced again
server-side, and un-routable-around because the chunk count is checked
independently of the token count.

The prompt instructs the model to answer only from the excerpts and to say so
plainly when they do not contain the answer (`app/prompts.py`'s
`document_qna` template already does exactly this). "The excerpts do not say"
is a correct and expected answer, and the result window presents it as one
rather than as a failure.

### 12.8 The status bar cell

QuillLite's status bar is a catalogue of twelve cells, each with a label and
one F1 sentence (`quill/apps/lite_status_cells.py`). Hosted AI adds the
thirteenth, present only while the area is on:

```python
StatusCell(
    "ai",
    "AI Allowance",
    "How many free AI requests you have left this month, and when the count "
    "starts again. Press Enter to open the AI Assistant.",
)
```

Its label is one of: `AI 94/100`, `AI: none left`, `AI: signed out`,
`AI: paused`, `AI: offline`. It follows the bar's existing `ratchet_width`
sizing so it cannot push the row to wrap. Changing it announces, which is
correct and is GATE-12's cure: a label change on an unfocused control is
precisely what the screen reader does not say.

### 12.9 Every state the user can be in, and the exact sentence

| State | Status cell | What is said, and where |
|---|---|---|
| Ready | `AI 94/100` | Nothing. Silence is the correct announcement for "working normally" |
| Daily cap reached | `AI 94/100` | On send: "You have used today's 20 requests. They start again at midnight. You have 94 left this month." |
| Monthly cap reached | `AI: none left` | On send: "You have used this month's 100 free requests. They start again on the 1st of October. You can add your own API key in Preferences to keep going now." |
| Hourly cap reached | `AI 94/100` | On send: "That is 8 requests this hour, which is the limit. Try again at the top of the hour." |
| Passage too long | `AI 94/100` | On open: "That selection is about 3,100 words, and the free limit is about 1,100. Select less, or choose This paragraph." No request is sent, so nothing is spent |
| Account under review | `AI 94/100` | On send: "Your account is under a routine review, so a smaller daily limit applies until it clears. Contact support with your support ID A1B2-C3D4." |
| Account paused | `AI: paused` | On send: "This account has been paused. Contact support with your support ID A1B2-C3D4." |
| Service paused globally | `AI: paused` | On send: "QUILL's free AI is paused for everyone right now. Check quillforall.org/status. Your own API key still works if you have one." |
| Device revoked | `AI: signed out` | On send: "This computer has been signed out. Choose Tools, AI, Sign In to connect it again." |
| Signed out | `AI: signed out` | Menu rows dimmed; on send: unreachable |
| Offline | `AI: offline` | On send: "QUILL could not reach the internet. Nothing was sent and nothing was used." |
| Upstream error | `AI 94/100` | "QUILL's AI service had trouble with that one. Nothing was used — try again in a moment." |
| Safe Mode | (no cell) | The area is unavailable entirely; the existing Safe Mode wording covers it |

Two rules run through that whole table.

**Every message says what to do next.** Not one of them ends at the problem.

**A request that did not happen never costs anything, and the message says so.**
"Nothing was sent and nothing was used" appears verbatim wherever it is true,
because the user cannot see the counter move and has no way to verify it
otherwise. This is the client half of the server-side rule in §5.3 about never
charging for an empty answer.

### 12.10 Usage, and signing out

**Tools > AI > Usage** opens a small modeless frame:

> **This month**
> 94 of 100 requests left. Starts again 1 October.
>
> **Today**
> 17 of 20 left.
>
> **This computer**
> Connected 3 September. Support ID A1B2-C3D4.

Buttons: **Sign out this computer**, **Copy support ID**, **Close**.

*Sign out* deletes the local token and calls `DELETE /v1/devices/<id>` so the
server revokes it too. Confirmation is inline — a second button that appears
saying "Yes, sign out" — **not** a modal dialog raised from a close handler,
which is the wxMSW trap that made Alt+F4 do nothing in Radio while playing.

The **support ID** is the first eight characters of the pseudonymous user id,
grouped `A1B2-C3D4`, and it is the entire answer to "someone wrote to support
and we cannot find them" (gap 4). It appears here, in the About dialog, and in
the sign-in confirmation. It is deliberately short enough to read aloud over a
phone.

### 12.11 Preferences

One page, "AI", present only while the area is on. Four controls, and no more:

1. **Use QUILL's free AI** — checkbox. The master switch, separate from the
   feature area: the area decides whether the feature exists, this decides
   whether it is on today.
2. **Or use my own API key** — button, opening the existing BYOK connection
   surface. This is the escape hatch every limit message points at, so it has
   to be one press away from where the message was read.
3. **Show what will be sent before sending** — checkbox, **on by default**. Off
   makes the pad send on `Ctrl+Alt+G`-then-Enter without the review step, for
   someone who has made the trade knowingly. Never off by default: the review
   step is the consent.
4. **Say the result when it arrives** — checkbox, **off by default**. On,
   QUILL speaks the result rather than relying on the reader's focus
   announcement. Off by default because on is a double-speak bug for most
   screen-reader users — the same single-speaker rule the Reveal Codes
   navigation had to learn.

Any new settings field must be paired or classified in the settings-vocabulary
audit (`quill/tools/settings_vocabulary_audit.py`), documented for GATE-SETDOC,
and given a Key Describer title if it carries a chord.

### 12.12 What QUILL says, and what it leaves to the reader

GATE-13, applied to this feature specifically, because over-announcing is the
failure nobody files:

| Event | QUILL announces? |
|---|---|
| Pad opens | **No.** The reader says the window and reads the focused field |
| Arrow through the action list | **No.** The reader reads the row and its help |
| Result window opens | **No.** The reader says the window and reads the result |
| Sign-in status changes in place | **Yes.** A label change on unfocused text is exactly what the reader does not say |
| Request finished, pad already closed | **Yes.** A background result with no focus change |
| Request failed | **Yes.** An outcome, with no focus change |
| Replace / Copy / Insert succeeded | **Yes.** An action's outcome |
| Allowance changed | **Yes**, via the status cell label |
| Polling for the device code | **No.** Not once, not every five seconds |
| Request in progress | **Once** at 10 seconds, and not again |

`check_over_announce.py` flags an announce inside an `EVT_SET_FOCUS` handler,
an announce of `GetTitle()`, and an announce of a `title=` literal. None of the
"Yes" rows above is any of those.

### 12.13 What this costs the build

Every one of these gates applies to the surfaces above, and each one fails the
build rather than filing a bug:

- **GATE-LITE-COVER** — every new handler needs a behavioural test that
  **calls** it, written as `(lambda w: w.cmd_ai_assistant(), ...)`. A
  parametrized handler *name* is invisible to the AST scan, and that is exactly
  the shape of test that let the F8 extend-selection bug through with a key, a
  label, a handler and a passing test. Then
  `python -m quill.tools.lite_command_coverage --write`.
- **Dialogs imported at module scope must be patched in the module that
  imported them**, not where they are defined. `tests/unit/apps/conftest.py`'s
  `DialogRecorder` names both ends of every entry point for that reason, and
  its fixtures answer **cancel** by default — which is the branch to write
  first here, because "user closed the pad mid-request" is a real path.
- **GATE-REACH** — the pad, the result window, the sign-in frame and the usage
  frame must each be reachable by imports from an app entry point. Tests do not
  count as callers. Re-snapshot with
  `python -m quill.tools.surface_reachability_audit --write`.
- **GATE-&lt;APP&gt;-HELP** — inline `SetHelpText` at each construction site, or
  the audit files it `missing`. Help set anywhere else is `help-elsewhere` and
  proves nothing. And `ensure_help_provider()` must run at activation, or every
  help string written above is dead.
- **Menu accelerators**, **GATE-14 access keys**, **GATE-DESCRIBE**,
  **GATE-KEYREF**, **documentation chords** — the ordinary tax on any new
  surface.
- **Module size budget** — new modules, not new sections of `lite_window.py`.

---

## 13. The administrative console, in plain language

The request is that every setting, knob, cost factor and gate be available in
plain language as part of the server's administrative infrastructure. That is
worth stating as a principle, because it decides a dozen smaller questions:

> **Every number that can cost money, change what a user gets, or turn something
> off is visible in the console, named in plain English, explained in one
> sentence, and shown with what happens if you change it. A setting that is not
> tunable is shown anyway, read-only, with the reason it is locked and the file
> it lives in.**

The console that exists today is a good foundation — server-rendered HTML, no
JavaScript, skip link, `aria-current`, flash messages with `role="status"` and
`role="alert"`, status words never carried by colour alone. The Limits page
already shows each row's `description` rather than only its key. What it does
not do is explain consequences, offer safe ranges, validate anything, or show
the protections that are not rows in a table.

### 13.1 A real gap first: nothing validates a config write

`dashboard.update_config` accepts **any float**. Typing `15` into
`monthly_cost_cap_usd` where `0.15` was intended is a hundredfold increase in
every user's cost ceiling, accepted silently with a cheerful green flash.
`max_input_tokens` will accept `1000000`. `global_monthly_budget_usd` will
accept `99999`.

This is the highest-value fix in the whole console, and it is small. Give every
key a metadata row — unit, minimum, maximum, step, and a sentence — and:

- reject out-of-range values with a plain sentence rather than a stack trace:
  *"Requests per person per month must be between 0 and 1,000. You typed
  10,000."*
- require a **typed confirmation** for any change that more than doubles the
  modelled monthly cost, showing the before and after (13.3);
- show the range next to the field, so the bound is known before the mistake.

### 13.2 The Limits page, rewritten

Not one flat alphabetical table of raw keys. Four grouped cards, each row a
`<fieldset>` with a real `<label>`, in this shape:

> ### How much each person gets
>
> **Free requests per person, per month**
> Current: **100**
> Each person may make this many AI requests between the 1st and the end of the
> month. The count starts again automatically on the 1st.
> Safe range 0 to 1,000. At 100, 500 people at full use costs about **$20 a
> month**. Raising this to 200 would cost about **$40**.
> `monthly_request_cap`
> [ 100 ] (Save)

Every row carries: the plain name, the current value **with its unit**, one
sentence of what it does, the safe range, **the cost consequence in dollars**,
the raw key in small text (kept — it is what appears in logs, the audit trail
and the API), and the field.

The four cards:

**How much each person gets** — requests per month, per day, per hour; per
device per hour; the per-feature ceilings; the new-account ramp.

**How big one request can be** — words in, words out, how many document
excerpts, image size. Stated in **words as well as tokens**, because nobody
thinks in tokens: *"about 1,100 words (1,500 tokens)"*.

**How much this may cost** — the per-person cost ceiling and the global monthly
budget, each with what happens when it is reached. The global one says plainly:
*"When total spending reaches this, QUILL's free AI switches off for everyone
until an admin turns it back on. You are alerted at 50%, 75% and 90% first."*

**Who may sign up** — the registration throttles and the new-account ramp, with
the sentence that explains why they exist: *"Anyone can connect a computer
without an account, which is deliberate — it is what makes this usable for
someone who has never had an API key. These limits are what stop one person
scripting a thousand of those."*

### 13.3 The cost calculator, on the page

The single most valuable thing the console could gain, and it does not exist.
Computed server-side on render (no JavaScript, consistent with the rest), from
the current config and the default model's pricing:

> ### What today's settings cost
>
> One request at the size limit: **$0.00040**
> (1,500 tokens in at $0.10 per million, 500 out at $0.50 per million)
>
> | People | If everyone uses everything | If a third do |
> |---|---|---|
> | 100 | $4.00 a month | $1.20 |
> | 500 | $20.00 a month | $6.00 |
> | 1,000 | $40.00 a month | $12.00 |
>
> Your budget cap is **$40.00 a month**, which covers 500 people at full use
> with room to spare, or 1,000 people at a third.
>
> Right now: **214 people connected**, **$4.18 spent this month**, 10% of the
> cap.

And on every Save that changes a cost-relevant number, the confirmation says
what moved:

> Free requests per person changed from 100 to 250.
> 500 people at full use: **$20.00 → $50.00 a month.**
> Your budget cap is $40.00, which this now exceeds. Raise the cap, or this
> will pause the service partway through the month.

That last sentence is the one that prevents the specific failure where an admin
generously raises an allowance and accidentally schedules an outage.

### 13.4 A new page: settings that are not knobs

Everything that affects cost or safety but is deliberately in code. Shown
read-only, with the reason and the file, because a protection the operator
cannot see is one they will assume is missing — or worse, assume is a dial they
already checked.

> ### Fixed by code, not by this console
>
> These cannot be changed here on purpose. Each one changes what a paid API
> call does, so changing it is a code review and a deploy, not a text box.
>
> **How hard the model thinks** — `none` for summarize, rewrite, proofread and
> explain; `low` for document questions.
> Thinking time is billed at the output rate and is invisible in the answer.
> Left at the provider's default (`medium`), this roughly **doubles the entire
> bill** and can consume the whole answer budget, leaving the user a blank
> reply they have been charged for.
> `app/prompts.py` · `REASONING_EFFORT`
>
> **What QUILL asks the model** — five fixed instructions, one per feature,
> shown in full below.
> The desktop app sends only the user's text. It never sends its own
> instructions. That is what stops a modified copy of QUILL using this service
> for something it was not opened for.
> `app/prompts.py` · `TEMPLATES`
> *(each of the five rendered verbatim, so the operator can read exactly what
> is being asked on every user's behalf)*
>
> **What is allowed in a request to OpenAI** — `model`, `messages`,
> `max_completion_tokens`, `reasoning_effort`. Nothing else.
> No web search, no file search, no tools, no attachments. Web search alone
> costs **$10 per thousand calls** — on this traffic that would be **$500 a
> month against $30 of actual AI**. A test fails the build if any other key is
> added.
> `app/openai_client.py` · `tests/test_openai_request_shape.py`
>
> **What is never stored** — no prompt text, no document text, no answers.
> The database has no column that could hold them. The one exception is a
> troubleshooting record a user opts into per incident, which is redacted and
> deleted after 30 days by a scheduled job.
> `app/models.py`

### 13.5 The Models page, with the honest caveat

The page exists: enable, disable, choose the default. Two additions.

**Pricing is a claim, not a fact.** The `input_cost_per_million_usd` and
`output_cost_per_million_usd` columns are what *we told the gateway* the
provider charges. Every cost figure in this console — the per-user ceiling, the
spend total, the budget cap, the calculator — is derived from them. If the
provider changes its prices and nobody updates the row, every number on every
page is quietly wrong and the budget cap protects nothing. The page must say so
next to the fields, and Phase 2 should add a monthly reminder to check.

**Changing the default model is a cost change.** Switching the default shows
the same before-and-after the config page does: *"GPT-6 Luna ($0.10/$0.50) →
Claude Haiku 4.5 ($1.00/$5.00). 500 people at full use: $20.00 → $200.00 a
month. Your cap is $40.00."*

### 13.6 The person's page

Every control asked for, phrased as the thing the operator actually wants to do.
Each writes an `admin_actions` row; each asks for a reason, because "who
disabled this user and why" is the question this table exists to answer.

> ### Person A1B2-C3D4
> Connected 3 September 2026 · 2 computers · 47 requests this month · $0.019
>
> **Give this person their allowance back**
> Sets this month's count back to zero. Use it when someone ran out for a
> reason that was not their fault. This clears both the running count and the
> running cost total — if only one were cleared, the other would keep refusing
> them and the reset would look broken.
> [ Reason ] (Reset allowance)
>
> **Give this person a different allowance**
> Overrides the normal monthly limit for this person only. Leave blank to use
> the normal limit.
> Requests per month [ 100 ] · Cost ceiling [ $0.08 ] · (Save)
>
> **Pause this person** — they can no longer use AI. Reversible. They are told
> to contact support.
> **Put under review** — a smaller daily limit until cleared. Reversible. Use
> when something looks unusual but you are not sure.
> **Remove permanently** — deletes the account and every computer signed in on
> it. Usage history is kept, with no name attached to it. Not reversible.
>
> **Their computers**
> Windows desktop · last used 2 hours ago · (Sign out) (Issue a new token)
> Sign out stops that computer immediately, on its very next request. Issue a
> new token replaces the one it holds without signing it out, for when a token
> may have leaked but you are not certain.

Above all of it, the lookup that makes the page reachable at all (gap 4): a
search field taking a support ID prefix, because a person writing to support
has eight characters and nothing else.

### 13.7 The switches page

Feature flags, named as switches, with the big one visually and structurally
separate:

> **Summarize** · On · (Turn off)
> **Rewrite** · On · (Turn off)
> **Proofread** · On · (Turn off)
> **Explain** · On · (Turn off)
> **Questions about documents** · On · (Turn off)
> **Pictures (alt text)** · On · (Turn off) — QUILL only; QuillLite has none
>
> ---
> ### Turn everything off
> Stops every AI request from every person immediately. They are told the
> service is paused and pointed at the status page, and that their own API key
> still works. Nothing is lost; nobody's allowance is spent while it is off.
> [ Reason ] (Turn off all AI)

When the budget cap auto-pauses the service, this page must say so in those
words rather than showing a switch that an admin flipped:

> **All AI is OFF.** Turned off automatically at 09:14 on 18 October, because
> spending reached the $40.00 monthly cap. Nobody turned this off by hand.
> Before turning it back on, check the Overview page and consider raising the
> cap — otherwise it will pause again within the hour.

That last clause matters: resuming without raising the cap re-pauses almost
immediately, and an operator who does not know that will think the switch is
broken.

### 13.8 A new page: safety checks

The request was that the *gates* be visible in plain language too. They are
currently invisible — they are tests and code paths, and an operator has no way
to know whether they are holding. One page, one row each, each a plain sentence
and a state:

| Check | State | What it protects |
|---|---|---|
| No web search, no tools | **Holding** | The only things ever sent are the model name, the text, and two size limits. Web search would cost $10 per thousand calls — more than everything else combined |
| Nobody is charged for a blank answer | **On** | If the model spends its whole budget thinking and returns nothing, the request is not counted against anyone |
| Sign-ups are throttled | **On** · 3 blocked today | Anyone can connect without an account. This is what stops one person scripting a thousand of them |
| New accounts start small | **On** · 15 requests for 48 hours | A throwaway account is worth a sixth of a real one, which makes farming them uneconomic |
| Spending pauses itself | **Armed at $40.00** · at 10% | If spending reaches the cap, everything switches off without waiting for anyone to read an alert |
| Alerts reach a human | **Configured** / **NOT CONFIGURED** | Without this, the first three alerts are logged where nobody reads them and the first you hear of it is the service switching off |
| Nothing anyone wrote is stored | **Holding** | The database has no column that can hold document text, prompts or answers |
| Old troubleshooting records are deleted | **Ran 3 hours ago** | The one exception to the line above expires after 30 days, by a job rather than by policy |
| Usage totals agree with the event log | **Ran 3 hours ago** | A crash can leave the running totals slightly behind; this catches it |

The two rows with a live state — alerts configured, jobs last run — are the
ones that rot silently, and both have a specific failure mode the sentence
names. An alert webhook that was never set is not a missing nicety; it is the
difference between noticing at 50% and noticing when the service stops.

### 13.9 Overview, Audit log, and the glossary

**Overview** keeps its budget gauge and monthly trend, and gains: people
connected, requests this month, the cost calculator's "right now" line, and any
safety check not in its normal state, at the top, as a `role="alert"` banner.

**Audit log** rows read as sentences rather than as columns: *"18 October,
09:14 — the service turned itself off because spending reached the $40.00 cap."*
*"3 September, 14:02 — admin `f3a8…` reset A1B2-C3D4's allowance. Reason: ran
out during a demo."* The structured columns stay underneath for filtering; the
sentence is what is read.

**A glossary page**, linked from every page's footer, defining in one line each:
token, input token, output token, reasoning token, request, allowance, cap,
ceiling, budget, throttle, device, support ID, feature flag, BYOK. The console
is operated by whoever is awake, not only by whoever built it.

### 13.10 The console's own accessibility

The foundation is right — server-rendered, no JavaScript, no build step, skip
link, `aria-current`, flashes with correct roles, status never carried by colour
alone. Before it is used in anger it needs a real pass by the accessibility
specialists, covering at minimum:

- every `<table>` a real `<caption>` and `<th scope>` (the existing ones have
  this; new pages must too);
- the budget gauge and the monthly trend each paired with a **data table**, not
  only a bar width — a percentage encoded solely as a CSS width is invisible;
- every form control a real `<label>`, not only `aria-label`;
- destructive actions (remove a person, turn everything off) requiring a typed
  confirmation rather than relying on a JavaScript `confirm()` this console
  cannot use;
- every error summarised at the top of the page and linked to the field, since
  a page reload loses the reader's position otherwise;
- focus visible at 3:1 against its background, and never removed.

### 13.11 What this adds up to

| Page | Today | After |
|---|---|---|
| Overview | Budget gauge, trend, counts | Plus live cost, plus any safety check out of normal state |
| Models | Enable, disable, set default | Plus the pricing caveat, plus before-and-after cost on a default change |
| Limits | Flat table of every key | Four grouped cards, plain names, units, safe ranges, dollar consequences, validated input, confirmation on big changes |
| — | — | **New:** the cost calculator |
| — | — | **New:** settings that are not knobs, and why |
| Users | List, usage, status, delete | Plus support-ID lookup, reset allowance, per-person caps, token rotation |
| Feature flags | Toggles | Plain-language switches; auto-pause explained as auto-pause |
| — | — | **New:** safety checks |
| Audit log | Rows | Rows that read as sentences |
| — | — | **New:** glossary |

Three of those pages are new, three are rewrites, and the highest-value single
item is the smallest: validating what an admin types before it becomes every
user's cost ceiling.

---

## 14. Running the server: keys, admin access, email, and DNS

Section 13 is what the console should *say*. This is how you get into it, what
secrets it holds, and what has to happen on the host and in DNS before any of it
is reachable.

### 14.1 How you authenticate to make changes

There is **no admin password and no separate admin account.** There is one
credential, and it is the same bearer token an ordinary QUILL install holds.

The whole model in five lines:

1. You connect a computer through the **ordinary device-code flow** — the same
   one every user goes through. It gives you a `device_id` and a bearer token.
2. You put that `device_id` into `GATEWAY_ADMIN_ALLOWLIST` in the server's
   environment file, and restart.
3. The JSON API (`/admin/*`) authenticates every request independently:
   `Authorization: Bearer <your token>`, then a check that your device is on the
   allowlist. Nothing is cached, so removing you from the list takes effect on
   your very next request.
4. The dashboard (`/dashboard/*`) is the same credential with a session on top.
   You paste the token once at `/dashboard/login`; it is kept in a signed,
   HttpOnly, SameSite=Lax, Secure cookie so you are not re-pasting it on every
   page. Validity is re-checked on every request, not just at login — a revoked
   device is signed out of the dashboard immediately.
5. Every state-changing action writes an `admin_actions` row: who, what, when,
   and why.

**Why the allowlist is an environment variable and not a database row.** Who may
administer the Gateway must not be something the Gateway's own console can grant
to itself. If an admin account were a row, then compromising one admin session
would let an attacker mint more; as an environment variable it takes shell access
to the host and a restart. The cost is that adding an admin is a deploy step,
which at the number of admins this will ever have is the right trade.

**The bootstrap, and the deadlock that used to be in it.** The allowlist
starts empty, which means nobody can reach `/admin/*` — including you. That is
fine, because step 1 does not need admin access: registration is open to anyone.
Register first, add your id second, restart third.

It was not fine until 2026-09-23. `Config.validate()` reported an empty
allowlist as a *problem*, and `create_app` refuses to boot on any problem — so a
brand-new deployment could not start at all. Registering needs the service
running; running needed the allowlist. Neither could go first. It surfaced the
first time the stack was stood up on the real host, and nowhere else: every test
in the suite builds the app through `TestingConfig`, where that branch is
skipped. `Config.warnings()` now carries it instead — shouted at ERROR level in
the first screen of `docker compose logs`, but never fatal — and
`tests/test_startup.py` pins both directions.

```bash
# On the host, with the service running:
curl -s -X POST https://ai.community-access.org/v1/device/code
#  -> note "user_code": e.g. "BKRT-3927"

# In a browser, anywhere: https://ai.community-access.org/connect?code=BKRT-3927
# Click Confirm.

curl -s -X POST https://ai.community-access.org/v1/device/token \
     -H 'Content-Type: application/json' \
     -d '{"device_code":"<the device_code from the first call>"}'
#  -> {"status":"authorized","token":"<KEEP THIS>","device_id":"<THIS GOES IN THE ALLOWLIST>"}
```

Then put the `device_id` in `.env` and restart:

```bash
cd ~/quill-ai-gateway
sed -i 's/^GATEWAY_ADMIN_ALLOWLIST=.*/GATEWAY_ADMIN_ALLOWLIST=<device_id>/' .env
docker compose -f docker-compose.prod.yml up -d
```

Sign in at `https://ai.community-access.org/dashboard/` by pasting the **token**, not
the device id.

**If you lose the token**, you are not locked out of the machine — you have SSH.
Register a fresh device, swap the id in `.env`, restart. Revoke the old one from
the console afterwards.

**Section 17 is the step-by-step version of all of this**, including how to
reach the dashboard through an SSH tunnel before the DNS record exists.

**The known weakness, stated plainly:** the dashboard login is a paste-a-secret
form, which is not a good sign-in experience and is the worst part of this
design. The upgrade path is already on the host — Keycloak runs there for GLOW —
and wiring the dashboard in as an OIDC client is a task in section 17, not
something to invent now.

### 14.2 The provider API key: yes, you define it on the server

**Yes — and it is the entire reason this service exists.** The key lives in the
server's environment and nowhere else. It is read in exactly one file
(`app/openai_client.py`), never sent to a client, never stored in the database,
never written to a log, and never included in an error message — the upstream
error handler deliberately interpolates only the exception's *type* name so that
a future change in the HTTP library cannot start echoing headers into a log.

On the host it comes from `~/quill-ai-gateway/.env`, which Docker Compose reads:

```bash
cd ~/quill-ai-gateway
nano .env          # set OPENAI_API_KEY=sk-...
chmod 600 .env     # it is the most sensitive file on the machine
docker compose -f docker-compose.prod.yml up -d   # re-reads .env
```

**Rotating it** is the same three lines: edit, `up -d`, done. The key is read
once at process start, so a restart is required — which is correct. A key that
could be swapped without a restart would have to be re-read per request from
somewhere mutable, and every "somewhere mutable" is a worse place for it.

**Should the key be editable from the dashboard?** No, and it is worth writing
down why so the question does not come back. A key in the database is a key in
every backup, in every `pg_dump`, and readable by anything with database access.
The premise of this whole service is that exactly one thing holds the provider
key; a text box in a web console widens that to the database, the backups, and
whoever can read either.

**But you cannot look at it to check it, which is a real cost**, and a wrong key
shows up as a 502 on somebody's first ever request rather than as an error at
deploy time. So the console has a button — and the API a route — that closes
that gap without ever revealing the secret:

```
POST /admin/test-key
  -> {"status":"ok","model":"gpt-6-luna","message":"The key works and gpt-6-luna answered."}
  -> {"status":"failed", ...}          the provider refused it
  -> {"status":"not_configured", ...}  no key is set at all
```

It sends the shortest possible completion, costs a fraction of a cent, and never
echoes the key. Run it after every deploy and after every rotation.

Also run `flask --app run.py check-config`, which reports out-of-range limits, a
budget cap that normal use can reach, a missing default model, and an
unconfigured alert webhook. It exits non-zero, so it can be a deploy step rather
than something somebody remembers.

### 14.3 This service sends no email. That is deliberate, and it stays that way.

No SMTP host, no mail-provider account, no Postmark, nothing that needs one.

It falls out of two decisions that were made for other reasons:

- **Sign-in is the device-code flow.** A person reads eight characters into a web
  page. There is no address to verify, no password to reset, and no confirmation
  to deliver. This was chosen because pasting a 51-character API key is the wall
  a screen-reader user hits on day one — the fact that it also removes email
  entirely is a bonus that turned out to be worth as much.
- **Alerts go to a webhook, not an inbox.** `GATEWAY_ALERT_WEBHOOK_URL` takes
  anything that accepts a JSON `{"text": "..."}` POST: a Slack or Discord
  incoming webhook, or a self-hosted **ntfy** topic — which needs no account at
  all and can push to a phone. That is the recommendation: ntfy, because a budget
  alert is exactly the kind of thing you want on a phone at 2am and exactly the
  kind of thing you do not want to depend on a mail provider's deliverability
  for.

No mail provider is one fewer account, one fewer secret, one fewer bill, one
fewer thing in the DNS zone (no SPF, no DKIM, no DMARC), and no deliverability
problem to debug at the exact moment something is already wrong.

**The one thing that would need email** is the optional Phase 5 identity
upgrade — verifying an address so an allowance follows a person across devices.
Three ways to keep the property if that day comes, best first:

1. **Do not build it.** Its purpose is multi-device continuity and
   anti-farming; the new-account ramp and the sign-up throttle already do the
   anti-farming half, and multi-device continuity may simply not be a problem
   worth an email dependency.
2. **Use the help desk that is already there.** FreeScout runs on this host with
   a working mailbox. A verification request is a low-volume, human-paced flow;
   routing it through an existing mailbox is not elegant but adds no new vendor.
3. **Then, and only then, a transactional provider.** If it is ever genuinely
   needed, it is a Phase 5 decision with its own review — not something to
   provision now against a feature that may never ship.

### 14.4 Where it goes: lp.csedesigns.com

The host (`lp.csedesigns.com`, hostname `bishoplink`, `107.175.91.158`) already
runs eighteen containers, including a Caddy instance that terminates TLS for
everything on the machine. There is 90 GB free. The gateway's footprint is
small: a Python image, a Redis with no persistence, and a Postgres.

**How it attaches.** Caddy (`web-caddy-1`, from the compose project in
`~/app/web`) reaches other services **by container name over the shared
`web_default` network**. `askbits-web` already works exactly this way — it sits
on both its own project network and `web_default`. `docker-compose.prod.yml`
does the same and deliberately does *not* publish a host port: publishing 8000
would work and would also expose the service directly, bypassing the headers,
HSTS and the `X-Forwarded-For` rewrite that the sign-up throttle depends on for
its accuracy.

**A subdomain of its own, not a path under `lp.csedesigns.com`.** That name is
already a permanent-redirect block pointing at letitglow.app, with a couple of
path matchers pinned inside it for the feedback and picks endpoints. Hanging an
API off another path in there means every new route has to out-rank a `redir`
that matches everything — the trap that cost an afternoon when the picks
endpoint went in. A separate name has no ordering to reason about, gets its own
certificate, and can move to another machine later by changing one DNS record.

### 14.5 DNS: exactly what you need to do

**Done, 2026-09-23.** `ai.community-access.org` resolves to `107.175.91.158`
and the service answers on it over HTTPS.

| Type | Name | Value |
|---|---|---|
| `A` | `ai` (in `community-access.org`) | `107.175.91.158` |

Three things *not* to do:

- **No `AAAA` record.** The host has no public IPv6. An `AAAA` pointing at
  nothing gives every IPv6-capable client a broken first attempt and a delay
  before it falls back — which on a slow connection looks exactly like the app
  hanging.
- **No `CNAME` to `lp.csedesigns.com`.** It would resolve, but it chains the new
  name's fate to a hostname that already has a redirect block and its own
  history. An `A` record to the address is one hop and one thing to reason about.
- **Nothing else.** No MX (the service sends no mail, 14.3), no TXT, no CAA
  change needed unless `community-access.org` already publishes a CAA that
  excludes Let's Encrypt — worth a one-line check:
  `dig CAA community-access.org +short` should be empty or include
  `letsencrypt.org`. It was, and the certificate issued first time.

**Why this name.** `community-access.org` rather than `csedesigns.com`: the
support address is already `support@community-access.org` and the help desk is
already `helpdesk.community-access.org`, so the name somebody is asked to type
into a phone belongs to the same organisation as the name they write to when it
goes wrong. It is short, which matters because it is printed in QUILL's sign-in
window and read aloud to somebody about to type it on a different device.
`gateway.quillforall.org` was the PRD's assumption and is no longer used
anywhere.

**Then, in order — and the order matters:**

```bash
# 1. Wait for the record. Do not skip this.
dig +short ai.community-access.org          # must print 107.175.91.158

# 2. Append the site block and reload Caddy.
cat ~/quill-ai-gateway/Caddyfile.example >> ~/app/web/Caddyfile
docker exec web-caddy-1 caddy reload --config /etc/caddy/Caddyfile

# 3. Confirm the certificate and the service together.
curl -s https://ai.community-access.org/healthz     # {"database":"ok","redis":"ok"}
```

**Do not reload Caddy before DNS resolves.** Caddy asks Let's Encrypt for a
certificate the moment the block loads; a name that does not yet point at the
machine fails the challenge, backs off, and retries on a lengthening timer — so
the site stays broken for a while *after* you fix the DNS, which is a confusing
twenty minutes to spend.

### 14.6 First run, in order

```bash
cd ~/quill-ai-gateway
cp .env.example .env
nano .env         # OPENAI_API_KEY, GATEWAY_SECRET_KEY, POSTGRES_PASSWORD,
                  # GATEWAY_PUBLIC_BASE_URL=https://ai.community-access.org
chmod 600 .env

docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec web flask --app run.py init-db
docker compose -f docker-compose.prod.yml exec web flask --app run.py seed-config
docker compose -f docker-compose.prod.yml exec web flask --app run.py check-config
```

Generate the session key with
`python -c "import secrets; print(secrets.token_hex(32))"`.

`check-config` will report the missing alert webhook until you set one. That is
not pedantry: without it, the 50%, 75% and 90% budget warnings go to a log
nobody reads, and the first you hear of a runaway month is the service switching
itself off.

Then do 14.1 to make yourself an admin, and `POST /admin/test-key` to confirm
the provider key works before a single user ever touches it.

### 14.7 Day to day

```bash
# The two scheduled jobs (add to cron on the host).
0  3 * * * cd ~/quill-ai-gateway && docker compose -f docker-compose.prod.yml \
             exec -T web flask --app run.py cleanup-expired
30 3 * * * cd ~/quill-ai-gateway && docker compose -f docker-compose.prod.yml \
             exec -T web flask --app run.py reconcile-usage

# Logs, health, and a config sanity check.
docker compose -f docker-compose.prod.yml logs -f web
curl -s https://ai.community-access.org/healthz
docker compose -f docker-compose.prod.yml exec web flask --app run.py check-config
```

Everything else — limits, models, people, switches — is the console. That is the
point of section 13.

---

## 15. Summary

The expensive half of this project is already written and has been sitting
untouched. Luna 6 does not change its architecture; it makes the numbers
comfortable enough that the question shifts from "can we afford this" to "can we
operate it carefully." The answer to the second question is four specific fixes —
reset usage, per-user caps, registration throttling, user lookup — plus the
discipline never to send a tool call and never to send a whole document.

The client half has never been started, and QuillLite is the right place to start
it: no AI today, so nothing to reconcile, and five commands is a complete product
for someone who has never heard of an API key. The family rule means QUILL gets
those same five in the same change, which is as it should be.

What a blind writer who has never seen an API key gets at the end of Phase 1:
install QuillLite, turn on one feature, read eight characters aloud into a
browser, and have an assistant. That is the whole point, and the rest of this
document is what it takes to make that safe, affordable and operable.

---

## 16. Tasks

Status as of 2026-09-23. `[x]` means done and covered by a passing test;
`[ ]` means not started; `[~]` means started and not finished, with what is
missing named.

### 16.1 Server — done this session

The gateway test suite is **205 passing** (was 45).

- [x] **Luna 6 as the default model.** `migrations/003`, `config.py`, `cli.py`.
      The seeded price columns were already $0.10 / $0.50 per million, so the
      cost math needed no change — only the id and label.
- [x] **`max_completion_tokens` instead of `max_tokens`**, and
      `reasoning_effort` sent explicitly. Reasoning models reject the older
      parameter outright, so every request would have failed.
- [x] **Reasoning effort floored per feature in code** (`prompts.py`:
      `REASONING_EFFORT`), with `ALLOWED_EFFORTS` capped at `low`. Left at the
      provider's default this roughly doubles the entire bill, invisibly.
- [x] **The no-tools gate.** `tests/test_openai_request_shape.py` pins the
      outgoing body to exactly `model`, `messages`, `max_completion_tokens`,
      `reasoning_effort`, and fails on any addition. Web search alone would be
      ~$500/month against ~$30 of model usage.
- [x] **Nobody is charged for a request that did not happen.** The counters
      increment before the size check, the model lookup and the upstream call,
      so all four failure paths refund (`limits.refund_request`). This was a
      live bug: an oversized selection or a provider outage cost the user one of
      their hundred, invisibly.
- [x] **No charge for an empty answer.** If the model spends its whole output
      budget reasoning and returns nothing, the user's counters are refunded and
      the real cost is still recorded against the global budget — the provider
      billed us even though the user got nothing.
- [x] **Registration throttling per internet address** (`check_registration_allowed`).
      This was the hole: anonymous sign-up meant an allowance was a cost
      *quantum*, not a cost bound.
- [x] **The new-account ramp** — 15 requests for the first 48 hours, then 100.
      Makes a farmed account worth a sixth of a real one.
- [x] **Ramp bug found and fixed.** It could give a *new* account a **higher**
      cap than an established one if the monthly cap were lowered below the ramp
      value — turning the anti-farming measure into a reason to keep making
      fresh accounts. Now `min(ramp, normal)`, with a regression test.
- [x] **Reset a person's allowance** (`reset_user_usage` + route + audit row).
      Clears the Redis counters **and** the running cost total together; either
      alone produces a reset that looks as though it silently failed.
- [x] **Per-person caps** — `monthly_request_cap`, `monthly_cost_cap_usd`,
      per-feature. The columns existed with no route that wrote them.
- [x] **Find a person by support ID.** `User.support_id` (`A1B2-C3D4`) plus
      `GET /admin/users?q=`. Without it, "somebody wrote to support" was
      unanswerable.
- [x] **Token rotation** — `POST /v1/device/rotate` (client, proof-of-possession)
      and `POST /admin/devices/<id>/rotate` (operator). The answer to "this may
      have leaked but I am not certain".
- [x] **Pending device grants moved to Redis.** They were a process-local dict
      and Gunicorn runs two workers, so roughly half of all sign-ins would have
      failed intermittently with "that code wasn't recognized".
- [x] **Config validation** (`config_schema.py`). Both write paths accepted any
      float, so `0.15` typed as `15` raised every user's cost ceiling a
      hundredfold behind a green success message. Now range-checked, with a
      typed/explicit confirmation for any change that more than doubles cost.
- [x] **The cost model** (`costing.py`) — per-request cost, monthly projections,
      and before-and-after impact of a proposed change.
- [x] **Proofread and Explain** added; the shipped set is the five.
- [x] **Feature refusals say why** — the stored `disabled_reason` is used
      instead of a generic "temporarily paused", so a never-built feature does
      not send somebody to support.
- [x] **`flask check-config`** — reports out-of-range limits, a budget cap
      normal use can reach, a missing default model, and an unconfigured alert
      webhook. Exits non-zero so it can be a deploy step.
- [x] **`POST /admin/test-key`** — proves the provider key works without ever
      revealing it.
- [x] **The two wrong numbers corrected**: budget cap $25 → $40 (25% headroom
      over the worst case is not headroom), per-user ceiling $0.15 → $0.08 (it
      sat 3.75× above anything reachable, so it was decoration).
- [x] **Deployment files** — `docker-compose.prod.yml` (joins the host's shared
      `web_default` Caddy network, publishes no port), `Caddyfile.example`,
      `.env.example`, `migrations/003`.
- [x] **Two standing caps per network** (`migrations/005`), because of something
      worth writing down plainly: confirming a device code creates a brand-new
      pseudonymous **user**, not another device on an existing account. Two
      computers are therefore two accounts with a full allowance each, and five
      are five. The per-IP throttle limits how *fast* somebody connects
      machines and does nothing about connecting one more every few days. So:
      a standing cap on active devices per address (6, and signing one out frees
      its place), and a monthly request ceiling shared by everybody behind one
      address (600) which does not care how many accounts sit behind it. Both
      set generously — they are aimed at one household running six laptops
      through the free tier, never at an office.
- [x] **A schema divergence, found by running a migration.** `init-db`
      (SQLAlchemy) and the `.sql` migrations produced *different* schemas: the
      SQL declares `updated_at NOT NULL DEFAULT now()`, the models carried only
      a Python-side default. So a database created the documented way failed any
      plain-`psql` insert that did not name the column, while the identical
      insert through SQLAlchemy succeeded — a trap for whoever next reaches for
      psql, which `migrations/README.md` tells them to do. Models now declare
      `server_default`; migration 005 brings existing databases into line.
- [x] **Two more bugs, found only by running it on the real host.** Neither was
      reachable from the test suite, which is the argument for standing a thing
      up before believing it works:
      - **The service refused to boot with an empty admin allowlist** — a
        deadlock on every brand-new deployment (see 14.1). Fixed, with
        `tests/test_startup.py` pinning both directions.
      - **`GET /v1/config` reported a hardcoded five features.** The moment
        Proofread and Explain were added, the desktop client was being told
        about two features it could no longer reach while two it *could* reach
        went unmentioned. Now driven from the feature table.
- [x] **A third bug, found by reading the first real request back out of the
      database.** `monthly_usage_summary.total_cost_usd` was `NUMERIC(10, 4)`,
      and a request costs about **$0.000028**. `record_usage` accumulates by
      reading that column back, adding, and writing it again — so every write
      rounded the new total straight back to `0.0000` and it never moved off
      zero. **That made the per-user cost ceiling inert**: it is checked against
      this column, so it could never trip however much somebody used, and the
      Redis request counters were the only thing actually bounding anybody. The
      fence I tightened from $0.15 to $0.08 in section 3.1 was doing nothing at
      all. Widened to `NUMERIC(14, 8)` (`migrations/004`), the host's recorded
      total repaired with `reconcile-usage`, and four tests added — three of
      which fail against the old precision, checked by reverting it.

      Worth naming the shape: four decimal places is a sensible precision for
      money, and the wrong precision for *this* money. Nothing was ever
      over-charged and nothing was lost — `usage_events` and the global spend
      counter both kept full precision throughout — but one of the two fences
      was not there, silently, and no test in the suite would ever have said
      so.

### 16.2 Server — remaining

- [x] **The console's HTML.** All nine pages render. New: *Safety checks*,
      *Fixed by code*, *Glossary*. Rewritten: *Limits* (grouped, explained,
      costed, validated), *Users* (support-ID search), the person's page (reset,
      per-person caps, per-device sign-out and token rotation), *Switches*
      (plain-language, never-built kept separate from paused, auto-pause shown
      as auto-pause), *Audit log* (rows read as sentences).
- [x] **53 page-level tests** covering all nine pages, including the structural
      accessibility properties that do not need a human to check: every table
      has a caption, every input has a real `<label for>`, every status badge
      contains a word and not just a colour, no page uses JavaScript, and each
      limit field points at both its explanation and its safe range through
      `aria-describedby`.
- [ ] **A real screen-reader pass on the console.** The tests above pin
      structure; they cannot tell you whether the Limits page is *pleasant* to
      move through with twenty-five headings, or whether the shown-once token
      is actually catchable. The accessibility-lead agent was asked for this
      and died on a session limit before reporting, so it is still owed.
- [x] Update `quill-ai-gateway/README.md` — Luna 6, the five features, the new
      console pages, the new admin endpoints, and why reset clears both halves.
- [ ] Update `docs/planning/openai.md` §8/§23 to match the shipped defaults, or
      add a note pointing at this document as the authority on numbers.
- [ ] Pin exact versions in `requirements.txt` before the first real deploy (it
      currently uses ranges and says so).
- [ ] Decide on `tiktoken` for real token counting. The current 4-chars-per-token
      heuristic only ever over-estimates, so it is safe, but it rejects
      borderline requests a real tokenizer would allow.

### 16.3 Deployment — what only you can do

- [x] **DNS done** (2026-09-23): `ai.community-access.org` → `107.175.91.158`,
      Caddy block appended and reloaded, certificate issued, and a real
      `summarize` request answered over HTTPS end to end. No `AAAA`, because the
      host has no IPv6 and a dead one adds a delay to every IPv6-capable
      client.
- [x] **The OpenAI API key is installed** (2026-09-23), taken from the "Open
      AI Key" entry in `D:\keys.txt` and piped straight into the host's `.env`
      over SSH — never printed, never written to a local file, never passed as
      a command-line argument (which would have put it in the process list and
      the shell history). `.env` is `0600`. `POST /admin/test-key` answers
      **ok**.
- [x] Public hostname settled: **`ai.community-access.org`**, which is now the
      default in `app/config.py`, in the client's `DEFAULT_BASE_URL`, and in
      `Caddyfile.example`.
- [ ] Pick where budget alerts go (14.3). **ntfy** is the recommendation — no
      account, pushes to a phone, no mail provider.
- [x] **`gpt-6-luna` is confirmed real** — it answered a live request. That
      was an open question; the key test settled it.
- [x] **`reasoning_effort: "none"` is confirmed accepted.** No rejection appears
      in the logs, and a real summarize request came back with
      `reasoning_tokens = 0` — so the floor is genuinely being applied and the
      doubled bill is genuinely being avoided, rather than the retry path
      quietly falling back to provider-default effort.

### 16.4 Deployment — sequence once the above is answered

- [x] Code deployed to `~/quill-ai-gateway` on the host (2026-09-23).
- [x] `.env` created from the example, `chmod 600`, with the session key and
      the Postgres password **generated on the host** so neither ever passed
      through a transcript.
- [x] **The stack is up and running**: `postgres`, `redis` and `web`, joined to
      the shared `web_default` network, publishing no host port — so it is
      reachable from Caddy and from nowhere else until the DNS record and the
      Caddy block exist.
- [x] `init-db` and `seed-config` run — 33 rows seeded. `check-config` runs and
      correctly reports the one outstanding problem (no alert webhook).
- [x] **End-to-end walk done on the host**: registered a device through the real
      device-code flow, confirmed it on `/connect`, polled, got a token, read
      `/v1/quota` and `/v1/config`, and loaded all nine console pages. The
      new-account ramp is live (`monthly_request_cap: 15`), images and chat
      report off, and the Limits page computes **$0.00040** per request — the
      number this document predicted in section 3.
- [x] **Real key installed and the service verified against the real
      provider.** `POST /admin/test-key` answers ok. A real `summarize` request
      through `/v1/chat` returned a correct summary in 95 tokens in / 37 out,
      cost `$0.000028`, decremented the quota to 14 of 15 (the new-account ramp
      doing its job), and recorded a usage event with `reasoning_tokens = 0`.
      The whole path — auth, quota, size check, prompt, provider, refund logic,
      metering — works end to end on the host.
- [ ] **Replace the bootstrap admin device.** One was registered to prove the
      flow works, and its token was printed to a terminal — so it must not be
      the admin credential once this is publicly reachable. Register your own,
      put that `device_id` in `GATEWAY_ADMIN_ALLOWLIST`, restart, then revoke
      `7c14b5d3-7c20-419a-ae9a-155945ab3502` from the console. Nothing is
      exposed yet (no DNS, no Caddy block), so this is a before-go-live task
      rather than an urgent one.
- [ ] Wait for DNS, **then** append the Caddy block and reload. Not before —
      Caddy asks for a certificate the moment the block loads, and a failed
      challenge backs off on a lengthening timer.
- [ ] Register your own device, add its id to `GATEWAY_ADMIN_ALLOWLIST`, restart
      (14.1).
- [ ] `POST /admin/test-key`.
- [ ] Add the two cron jobs (14.7).

### 16.5 Client — QuillLite is done

Built 2026-09-23. **QUILL's existing AI was not touched**: no change to
`ALL_PROVIDERS`, none to `make_default_backend()`'s cascade, none to any BYOK,
agent or local-model path. Either of the first two would alter what an installed
QUILL does on its next launch, which is a decision to take deliberately rather
than as a side effect of shipping QuillLite's version.

**Shared, in `quill/core/ai/` — so QUILL can reach all of it:**

- [x] `gateway_errors.py` — the `QUILL-AI-GATEWAY-*` family. Every one carries a
      `user_hint` naming the next step, because a screen-reader user hears only
      the sentence we wrote.
- [x] `gateway_context.py` — what gets sent, decided before a request exists:
      selection → paragraph → section (**never the document**), local chunking
      and keyword retrieval for document questions, and a size refusal phrased
      in *words* rather than tokens.
- [x] `gateway_client.py` — the one egress site, with every HTTP failure mapped
      to a coded error that keeps the server's own sentence. The device-code
      flow **reuses** `device_login.py` through a twenty-line dialect adapter
      rather than growing a second RFC 8628 state machine.
- [x] `gateway_session.py` — token in the OS credential store under the existing
      `QUILL:assistant:<provider>:api-key` shape (no new secure-storage code),
      everything non-secret in `<data>/ai/gateway.json`.
- [x] `gateway_backend.py` — an `AIBackend` so QUILL can reach the hosted tier.
      Deliberately unregistered; see above.

**QuillLite:**

- [x] `hosted_ai` switchable area, **off by default**, whose description *is* the
      consent notice. An area that is off owns nothing — no menu, no keys, no
      token on disk, no network call of any kind.
- [x] Tools > **AI** submenu (not a tenth top-level menu — Clipboard and
      Spelling were demoted from the bar for exactly this reason).
- [x] Four chords. Both keymaps are saturated: measured across Ctrl+Alt,
      Ctrl+Shift, Alt+Shift and Ctrl+Alt+Shift, the chords free in *both*
      editors are `Ctrl+Alt+G`, `Ctrl+Alt+Z` and a few Ctrl+Alt+Shift function
      keys. So family rule 2 decided this, not taste: the two short ones went to
      the daily commands and rule 9 sent the once-per-computer pair to
      `Ctrl+Alt+Shift+F9`/`F10`. QuillLite has **no** keyless command rows, so a
      chord each was not optional.
- [x] Four modeless `wx.Frame` windows — pad, result, sign-in, usage. Modeless
      because a modal blocks the editor, which is the one thing a writing tool
      may not do; every Close goes through `bind_close_button`, and nothing is
      ever shown modally from a close handler.
- [x] The pad shows **what will be sent** before it is sent, including the actual
      excerpts chosen for a document question — the only way somebody can tell
      "the AI got it wrong" from "it never saw the right paragraph".
- [x] An answer never reaches a document on its own, and Replace is withheld
      when the text it came from moved while the request was in flight.
- [x] GATE-LITE-COVER: **205 handlers, 205 covered, 0 shape-only.** Tests written
      as `(lambda w: w.cmd_ai_assistant(), ...)` — a parametrized handler *name*
      is invisible to the AST scan.
- [x] GATE-9 egress entry, F1 purposes for all four windows, the feature area in
      the user guide, profile counts corrected (18 → 19 areas) and `hosted_ai`
      explicitly removed from the WordPad and Notepad profiles — "WordPad, but it
      sends your writing to a server" is a profile whose name has stopped being
      true.
- [x] 40 core tests and 14 behavioural ones. `mypy quill/core quill/io` clean
      across 1,067 files.

**Deviations from section 12, stated rather than quietly dropped:**

- [ ] **No status-bar cell.** Section 12.8 specified a thirteenth cell. QuillLite's
      status bar is deliberately a *fixed* twelve, and a cell that appears only
      when an area is on needs rebuild-on-toggle machinery that module was
      explicitly not built for. The allowance shows in the pad, the result
      window and the Usage window instead. Worth doing properly later; not worth
      half-doing now.
- [ ] **QUILL's own menu wiring.** The capability is shared and reachable; the
      provider registration and cascade entry are a separate, deliberate change.

### 16.6 Before anyone outside the team uses it

- [ ] **Privacy text** (5.7). `docs/legal/PRIVACY.md` and its `.html`/`.epub`
      renders gain a hosted-AI section: what is sent, to whom, what is stored
      (metadata only), for how long, and the one opted-in exception. Shipped
      privacy text that claimed more than the code did was a Radio 3.0 ship
      blocker — do not repeat it.
- [ ] The same two sentences on the sign-in surface, before the code appears,
      not behind a link.
- [ ] Accessibility pass on the console by the specialist agents (13.10).
- [ ] A runbook for "the spend alert fired at 2am", proven by a drill.

### 16.7 Known weaknesses to fix later

- [ ] **The dashboard login is a paste-a-secret form.** It is the worst part of
      the design (14.1). Keycloak already runs on this host for GLOW; wiring the
      dashboard in as an OIDC client is the intended upgrade.
- [ ] **Proof-of-work on `/connect`** before public beta (4.3). No image or
      audio CAPTCHA, ever — that is the canonical accessibility failure, in an
      accessibility-first product.
- [ ] **`gateway_models` has no `base_url` / key-source column**, so "swap to a
      fallback provider" is a deploy rather than a click. Groq is
      OpenAI-compatible and needs only those two columns.
- [ ] Coarse-network anomaly flagging for a token used from many distinct /16s
      in a day (4.1). Flag and review — never auto-lock, which would strand a
      roaming user.
- [ ] Monthly reminder to check the model price columns against the provider's
      actual prices. Every cost figure in the console derives from them; if they
      drift, the budget cap protects nothing.

### 16.8 Images — deferred on purpose

Not a gap; a decision (5.6). Tracked here so it is not quietly forgotten.

- [ ] Describing pictures is **not in QuillLite at all** and is off on the
      server: flag disabled with a reason, per-feature cap zero,
      `daily_image_cap` zero.
- [ ] When it is built it belongs in **QUILL first** — Glow and Inkwell are
      where pictures actually live.
- [ ] It needs its own cap tuning from real Phase 3 usage data; a vision call
      costs several times what a text call does.
- [ ] Two open questions travel with it: the client must resize before sending,
      and it may belong in the bring-your-own-key tier rather than the free one.

---

## 17. Signing in to the console

Section 14.1 explains *why* admin access works the way it does. This is the
runbook: the exact steps, in the state the service is actually in.

### 17.1 There is no password

The credential is a **device bearer token** — the same kind every QUILL install
holds — and authorisation is an **environment variable on the server**. Both
halves are needed: a valid token that is not on the allowlist gets `403`, and an
allowlisted id with no token gets `401`.

The allowlist is an environment variable rather than a database row on purpose:
who may administer the Gateway must not be something the Gateway's own console
can grant to itself. Compromising an admin session would then let an attacker
mint more admins; as an environment variable it takes shell access to the host
and a restart.

Four facts that follow, and are worth knowing before something goes wrong:

- **Every request re-checks both.** Nothing is cached, so removing somebody from
  the allowlist, or revoking their device, takes effect on their very next
  request — not at their next login, and with no propagation delay.
- **The dashboard is not a second login.** It is the same token, remembered in a
  signed, HttpOnly, SameSite=Lax, Secure cookie so it is not re-pasted on every
  page. Validity is re-checked on every page load, so a revoked device is signed
  out of the browser immediately too.
- **Losing the token does not lock you out of the machine.** You have SSH.
  Register a fresh device, swap the id in `.env`, restart.
- **The bootstrap is not a deadlock** — but it was until 2026-09-23. See 14.1.

### 17.2 Signing in today, before DNS exists

The container publishes no port on the host (correct: Caddy reaches it over the
shared `web_default` docker network, and publishing 8000 as well would let
traffic bypass the headers, the HSTS and the `X-Forwarded-For` rewrite the
sign-up throttle depends on). So a browser needs a tunnel.

The host itself can route to the container, so forward to the container's
address rather than to a host port. **Look the address up rather than copying
one** — it changes whenever the container is recreated:

```bash
# On your machine:
IP=$(ssh lp 'docker inspect quill-ai-gateway-web-1 \
      --format "{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}"' | awk '{print $1}')
ssh -L 8001:$IP:8000 lp
```

Leave that session open, then in a browser: **http://localhost:8001/dashboard/**

Paste the bearer token of an allowlisted device. Browsers treat `localhost` as a
trustworthy origin, so the `Secure` session cookie should be accepted over plain
HTTP there.

**If the login bounces straight back to the form**, that is the cookie being
rejected rather than the token being wrong. Temporarily:

```bash
ssh lp 'cd ~/quill-ai-gateway && \
  printf "\nGATEWAY_DASHBOARD_INSECURE_COOKIE=1\n" >> .env && \
  docker compose -f docker-compose.prod.yml up -d web'
```

**Take that line out again before DNS goes live.** It exists for local `http://`
development, and on a publicly reachable service it means the cookie carrying an
admin credential can travel unencrypted.

The JSON API needs none of this — it is a bearer header with no cookie, so it
works from inside the container directly:

```bash
ssh lp 'cd ~/quill-ai-gateway && docker compose -f docker-compose.prod.yml exec -T web \
  curl -s localhost:8000/admin/spend -H "Authorization: Bearer <token>"'
```

### 17.3 Signing in once DNS is up

`https://ai.community-access.org/dashboard/`, paste the token. That is the whole
thing, and it is how it should be done from then on — the tunnel above is
scaffolding for the gap between "the service runs" and "the service has a name".

### 17.4 Making a device an admin

The first time, and every time somebody new needs access:

```bash
ssh lp
cd ~/quill-ai-gateway

# 1. Start a registration and read out the code.
docker compose -f docker-compose.prod.yml exec -T web python -c "
import requests, json
r = requests.post('http://localhost:8000/v1/device/code', timeout=10).json()
print('CODE:', r['user_code'])
print('DEVICE_CODE:', r['device_code'])"

# 2. Confirm it. Before DNS: through the tunnel at
#    http://localhost:8001/connect  — or with curl, which is equivalent:
docker compose -f docker-compose.prod.yml exec -T web \
  curl -s -X POST localhost:8000/connect -d "code=<CODE from step 1>" >/dev/null

# 3. Collect the token. This is the only time it is ever shown.
docker compose -f docker-compose.prod.yml exec -T web python -c "
import requests
t = requests.post('http://localhost:8000/v1/device/token',
                  json={'device_code': '<DEVICE_CODE from step 1>'}, timeout=10).json()
print('device_id:', t['device_id'])
print('token:    ', t['token'])"
```

Then put the `device_id` — not the token — in the allowlist and restart:

```bash
nano ~/quill-ai-gateway/.env      # GATEWAY_ADMIN_ALLOWLIST=id1,id2,...
docker compose -f docker-compose.prod.yml up -d web
```

Two things that trip people up. **Poll only once**: the device code is
single-use, so a second call to `/v1/device/token` returns `expired` and the
token is gone — the registration has to start over. And **the allowlist takes
ids, the login takes the token**; they are different strings and only one of
them is a secret.

### 17.5 Before this is publicly reachable

**Replace the bootstrap admin device.** One was registered on 2026-09-23 to
prove the flow worked end to end, and its token was printed to a terminal — so
it is not a credential, it is a demonstration. It is harmless while the service
has no DNS record and no Caddy block, and it stops being harmless the moment
either exists.

1. Register your own device (17.4).
2. Put *its* id in `GATEWAY_ADMIN_ALLOWLIST`, restart.
3. Confirm you can reach the dashboard with your own token.
4. Revoke `7c14b5d3-7c20-419a-ae9a-155945ab3502` from the Users page, and remove
   its id from the allowlist.

Do all four. Revoking without removing the id leaves a dead entry that looks
like access; removing the id without revoking leaves a live token that merely
is not an admin any more.

### 17.6 The known weakness

**Paste-a-secret is the worst part of this design**, and it is worth being
honest about rather than discovering later: the token is 43 characters of
base64, which is unpleasant to handle and unpleasant to read aloud, and it is
pasted into a form that looks exactly like a phishing target.

It is acceptable today because there are one or two operators and the service is
not public. It stops being acceptable at the point where a third person needs
access, or where somebody has to be talked through it on a phone.

The upgrade is already on the host: **Keycloak** runs there for GLOW, and wiring
the dashboard in as an OIDC client is the intended replacement — a real sign-in
screen, no secret to handle, and account removal that does not need a deploy.
Tracked in 16.7.
