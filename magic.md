# magic.md — nobody should ever require a GitHub account

Done. Written 2026-08-25, finished 2026-08-26.

**The one line that mattered:** *"Nobody should ever require a GitHub account."*

As of today the web form needs no account, no sign-in, and no third party. A
visitor fills it in, presses **Send suggestion**, and a labelled issue appears
in the repo. Verified end to end: issue
[#1448](https://github.com/Community-Access/quill/issues/1448) was filed by the
server with no account involved, then closed.

---

## Where things stand now

| Route | Account needed? | Status |
| --- | --- | --- |
| Quill Radio → **Community > Suggest a Station or Podcast…** | **No** | Working. Files a real issue with the bundled issues-only token. |
| **quillforall.org/picks/suggest/** | **No** | **Fixed.** POSTs to `https://lp.csedesigns.com/submit/picks`, which files the issue. |
| **`https://lp.csedesigns.com/submit/picks`** | — | **Live.** `feedback_hub.server` 1.2.0, one container beside the three apps already on the box. |
| `workers/picks-submit.js` (Cloudflare) | — | **Deleted.** Two ways to do one thing is one too many. |

The whole pipeline is proven: suggestion → `pick:suggestion` → review →
`pick:approved` → `picks-build.yml` → validated → signed → PR → merged →
deployed → serving.

---

## What was built

### The server — `Community-Access/feedback-hub` 1.2.0

`feedback_hub.server` is a zero-dependency WSGI application. One endpoint, one
health check, holding the only token.

It solves a bigger problem than the one we started with. feedback-hub already
called itself a "centralized GitHub backend", but every client carried its own
token — which is why Quill Radio ships one inside its installer, extractable by
anyone who unzips it, and why the website could not submit at all. With a
server in the path the apps can eventually stop carrying a credential, and the
token rotates by editing one `.env` rather than by shipping a release.

```
Radio "Report a Bug"   ─┐
Radio "Suggest…"       ─┤
quillforall.org form   ─┼──→  feedback-hub server on lp  ──→  GitHub issue
GLOW / Cast / Social   ─┘        (holds the only token)
```

Scope is deliberately **picks only**. Report a Bug still submits directly from
each app; migrating it at the same time would have made the first deployment
also the riskiest one.

**What it refuses**, each with a test rather than a comment: a body with no
```` ```json pick ```` block (such an issue looks fine in the review queue and
publishes *nothing* when approved, so the failure would surface days later as
"why is my station not in the list?"); two blocks; a kind that is not
`stream`/`podcast`; a missing name or address; an address whose scheme is not
the web; anything over 32 KB. `http://` is accepted on purpose.

Rate limit: one a minute, twenty a day per address, in memory. A **refused**
attempt is not counted. The address is the **last** `X-Forwarded-For` entry —
a client can send a header of its own and the proxy appends to it, so the first
entry is whatever the client claimed.

51 tests, against the WSGI callable itself rather than a wrapper, so what is
tested is what gunicorn runs. 112 tests in the repo, all green.

### The deployment — `lp.csedesigns.com`

- `~/feedback-hub`, `deploy/docker-compose.yml`, container `feedback-hub-submit`,
  two gunicorn workers, 192 MB cap, no published ports, joined to the existing
  `web_default` network. Follows the `askbits` shared-host pattern exactly.
- Token in `~/feedback-hub/deploy/.env`, mode 600, never in the image.
- Caddy: a `@picks_submit` matcher on `lp.csedesigns.com` + `/submit/*`,
  reverse-proxying to `feedback-hub-submit:8095`. Backup at
  `~/app/web/Caddyfile.bak.2026-08-26`; validated, then **reloaded**, not
  restarted.
- Runbook: `deploy/README.md` in feedback-hub.

### The page — `docs/site/picks/suggest/`

`SUBMIT_URL` set, `connect-src` added, copy rewritten to lead with the
accountless route, and the accessibility work from a full specialist review
applied (see below).

---

## Two things found on the way that were not on the list

### `redir` was shadowing every handler in that Caddy block

The site block for `lp.csedesigns.com` ended with a bare
`redir https://letitglow.app{uri} 301`. Caddy sorts directives by a fixed order
and **`redir` sits above `handle`/`handle_path` in it** — so the redirect did
not run last, it ran *first*, and every handler above it was dead code.

That had already happened to `/ggg*`: it never served anything. The links only
kept working because the redirect landed on a working `/ggg` on the canonical
host, which is exactly the kind of accident that hides a bug for months.

Fixed by wrapping the redirect in `handle { }`, making it the last arm of the
same mutually exclusive group. `/ggg/` on lp now serves directly (200) as
originally intended, everything else still redirects identically, and
`letitglow.app` and `csedesigns.com` are untouched.

### The accessibility review found three broken mechanisms, not one

The page's planned flow relied on `role="alert"` plus focus, a rebuilt
`role="status"` container, and a disabled submit button. All three fail
specifically on NVDA and JAWS:

- **`role="alert"` + `.focus()` reads everything twice**, first reading usually
  clipped. Worse, an alert whose content has not changed may not fire at all —
  so resubmitting with the same errors announces nothing. Now: focus only, onto
  a heading, which also leaves the list there to re-read.
- **Clearing and rebuilding a live region in one task announces nothing.** The
  empty state never reaches the accessibility tree, so a repeated identical
  message — two rate-limit refusals in a row, which the limiter produces *by
  design* — is silently swallowed. Now: cleared on one tick, written on the
  next.
- **Disabling the focused button blurs it and sets no sequential starting
  point**, so the next Tab restarts at the top of the document — thirteen stops
  back through every field just filled in, announced by nothing. Now:
  `aria-disabled` plus a guard flag, which is what actually prevents a double
  send.

Also: the site had **no form styling at all**, which was not neutral — browser
defaults put the Safari input border at 1.45:1 and the dark-mode Chrome field
interior at 1.69:1; `.hint` was used seven times and defined nowhere. And
without a `forced-colors` block, "Sent" and "Not sent" looked identical in
Windows High Contrast — on the exact platform this audience uses. All fixed in
`assets/style.css`, which benefits every form on the site.

---

## Still open, and yours to decide

- **Rotate the token.** The server currently holds the *same* issues-only token
  that ships inside every QUILL installer, because that got it live today. Mint
  a fresh fine-grained PAT (Issues: read and write on `Community-Access/quill`,
  nothing else), put it in `~/feedback-hub/deploy/.env`, `docker compose ...
  restart`, and revoke the old one at the next Radio release. Nothing else
  needs to change — that is the point of the server.
- **Catalogue-rebuild PRs sit at `action_required`.** GitHub holds workflows on
  `github-actions[bot]` PRs for manual approval, so auto-merge never fires.
  Fix is a repo setting: *Settings → Actions → General → require approval for
  outside collaborators only*. Not changed — it is a security setting and
  yours to make.
- **`PICKS_SIGNING_KEY` is not set**, so the catalogue is published unsigned.
  The app verifies and fails closed, falling back to the bundled copy and
  recording why in Recent Problems. Base64 Ed25519 seed, as a repo secret.
- **A stale `hub.quillforall.org`** in `quill/ui/quillin_hub_submit.py` still
  does not resolve. Now that there is a server, the obvious answer is a second
  endpoint on it — but that is the "more endpoints" step, deliberately not
  taken today.
- **Report a Bug still carries a bundled token in every app.** Moving it to the
  server is the next migration, once this has been up a while.
- **Radio's menu bar is full.** 149 accelerators; `Ctrl+Alt+Shift` is entirely
  exhausted. The next menu item needs a submenu or a palette-only home.
- **`<select id="kind">` is semantically load-bearing.** It decides which JSON
  key lands in the catalogue (`stream_url` vs `feed_url`). A sighted visitor
  sees the mismatch at a glance; somebody using a screen reader heard that
  string once, five fields ago. Converting it to a radio group was recommended
  and is a product decision, so it was left as a select — with the inert
  `required` removed, a hint added, and the choice restated in the
  confirmation.

---

## One thing worth remembering

The https-only rule written for catalogue addresses would have **excluded
Team-FM**, which is http-only — and measuring it showed **41% of the 400
most-played stations** in the directory Radio already browses are http-only
too. A rule written to protect listeners would have quietly excluded exactly
the small community stations this project exists for.

The protection belongs where it actually helps: the catalogue *itself* arrives
over https and signed, so nobody can substitute the list. An individual http
stream risks only itself. Still refused everywhere: `javascript:`, `file:`,
`data:` — and on the review page an attacker-controlled `href` is the other way
to run script on a page holding a token.

Worth remembering because it was only found by looking up a real station
instead of reasoning about the rule.

**And, once and permanently: Turnstile, never reCAPTCHA.** The endpoint
supports Turnstile and it is switched off, because a challenge nobody needs is
a barrier nobody asked for. If spam ever arrives, that is the switch — not
reCAPTCHA, whose image grids are precisely the barrier this project exists to
remove.
