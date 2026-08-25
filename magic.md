# magic.md — nobody should ever require a GitHub account

Working notes for the next session. Written 2026-08-25.

**The one line that matters:** *"Nobody should ever require a GitHub account."*
Everything below is in service of that.

---

## Where things stand

| Route | Account needed? | Status |
| --- | --- | --- |
| Quill Radio → **Community > Suggest a Station or Podcast…** | **No** | Working. Files a real issue with the bundled issues-only token, reads back the number. |
| **quillforall.org/picks/suggest/** | **Yes**, for the final press | Live and working, but hands the visitor to GitHub's pre-filled issue form. This is the bit to fix. |
| `workers/picks-submit.js` (Cloudflare) | No | Written and ready — **but you would rather not have a Cloudflare account, so this is now a dead end. Delete it once the replacement lands.** |

The rest of the pipeline is done and proven end to end: suggestion → `pick:approved`
label → `picks-build.yml` → validated → signed → PR → merged → deployed →
serving. Team-FM went the whole way and is live in the catalogue (52 picks).

---

## Why the web page still asks for an account

Not for want of trying — it is a platform fact:

> **GitHub Pages serves files. It cannot accept a POST.** Something has to
> receive the submission and hold a credential that can write to the repo, and
> that credential can never live in the public page. GitHub's own secret
> scanning would revoke a published token within minutes, and rightly.

So the question was never "server or no server". It is **whose small process**.

---

## The answer: put it in feedback-hub, host it on lp

Your two suggestions turn out to be better together than the Cloudflare plan.

`Community-Access/feedback-hub` already describes itself as:

> Multi-framework GitHub issue submission library. Native UI per framework,
> **centralized GitHub backend**.
> — wxPython apps (ChapterForge, QUILL) · Flask apps (GLOW) · CLI / headless

Today "centralized backend" means *GitHub is the backend* and **every client
carries its own token**. That is why Radio ships one inside the binary and why
the website cannot submit at all.

Giving feedback-hub a small **server** component makes the phrase true:

```
Radio "Report a Bug"   ─┐
Radio "Suggest…"       ─┤
quillforall.org form   ─┼──→  feedback-hub server on lp  ──→  GitHub issue
GLOW / Cast / Social   ─┘        (holds the only token)
```

**It solves a bigger problem than the one we started with.** The bundled token
ships in every installer, so anyone who unzips one can extract it. Once
submission goes through a server, the apps can stop carrying a credential at
all — and the token can be rotated without shipping a release.

---

## What is already known about the box

Surveyed over SSH on 2026-08-25 (read-only; nothing was changed).

- `lp.csedesigns.com` → `107.175.91.158`, reachable as `ssh lp`
  (`~/.ssh/config` → user `jeffbis`, key `id_ed25519_lp`). Host is `bishoplink`.
- **Docker Compose**, three projects sharing the box:
  - `web` → `/home/jeffbis/app/web/docker-compose.prod.yml` (8 containers)
  - `askbits` → `/home/jeffbis/askbits/deploy/shared-host/docker-compose.yml`
  - `adp` → `/home/jeffbis/adp/deploy/shared-host/docker-compose.yml`
- **Caddy terminates 80/443** in `web-caddy-1`, config bind-mounted from
  `/home/jeffbis/app/web/Caddyfile`. Automatic HTTPS already working.
- `jeffbis` **is in the `docker` group** — containers can be managed without
  sudo. **Passwordless sudo is NOT available**, so anything needing root has to
  wait for you.
- Python 3.12.3 on the host.

---

## Three decisions to make before any of it is built

I did not guess these, because this is a public endpoint holding a GitHub token
on a box already running three production services.

### 1. Where does it answer?

| Option | DNS work | Notes |
| --- | --- | --- |
| **`lp.csedesigns.com/submit/…`** ← recommended | none | No new certificate, smallest blast radius, reversible by deleting a Caddy block. |
| `submit.csedesigns.com` | one A record → `107.175.91.158` | Cleaner name, and easier to move off the box later. |

### 2. How much, first?

| Option | Notes |
| --- | --- |
| **Picks endpoint only** ← recommended | Small, contained, unblocks the page the same day. Proves the shape before anything depends on it. |
| Full feedback-hub server | Right destination, but migrating Report a Bug at the same time means the first deployment is also the riskiest one. |

Do the first, then migrate Report a Bug to it once it has been up a while.

### 3. Which repo?

| Option | Notes |
| --- | --- |
| **`Community-Access/feedback-hub`** ← recommended | Where you asked for it, and where Cast, Social, GLOW and ChapterForge can all reach it. Separate release cadence from QUILL. |
| `quill` alongside `workers/` | Convenient today, wrong home tomorrow. |

**Recommended combination: a path on `lp.csedesigns.com`, picks-only, code in
`feedback-hub`.**

---

## The build, once those are settled

1. **`feedback_hub/server.py`** — one endpoint. Validates, then files the issue.
   Reuses the existing `feedback_hub` validation rather than growing a second
   copy, and reuses `quill.core.pick_suggestion.parse_issue_body`'s format so
   `picks-build.yml` still has exactly one shape to read.
   - Refuses anything without the ```` ```json pick ```` block: approving such
     an issue later would publish nothing.
   - Rate-limits per IP (one a minute, twenty a day).
   - CORS locked to `https://quillforall.org`.
   - Token from the environment, never from a file in the image.
2. **A container** in the `web` compose project, plus a `handle_path` block in
   the Caddyfile. Follow whatever `askbits` does — it is the closest existing
   shape.
3. **One constant** in `docs/site/picks/suggest/suggest.js`:
   ```js
   var SUBMIT_URL = "https://lp.csedesigns.com/submit/picks";
   ```
   Everything else is already built and shared with the in-app dialog.
4. **Delete `workers/picks-submit.js` and `workers/README.md`.** Two ways to do
   one thing is one too many.
5. **Update the page copy.** It currently says the GitHub step "is being
   removed" — once it is, that paragraph and the whole `#other-ways` fallback
   need rewriting to match.

### If a spam challenge is ever needed

**Turnstile, never reCAPTCHA.** Turnstile is usually invisible and needs no
puzzle. reCAPTCHA's image grids are precisely the barrier this project exists to
remove — a spam control that locks out blind users to keep out bots has failed
at the only job that matters here. Written down because it is the kind of
decision that gets made hastily at 2am.

---

## Loose ends, unrelated to the above

- **Catalogue-rebuild PRs sit at `action_required`.** GitHub holds workflows on
  `github-actions[bot]` PRs for manual approval, so auto-merge never fires and
  every rebuild waits for a click. Fix is a repo setting: *Settings → Actions →
  General → require approval for outside collaborators only*. I did not change
  it — it is a security setting and yours to make.
- **`PICKS_SIGNING_KEY` is not set**, so the catalogue is published unsigned.
  The app verifies and **fails closed**, falling back to the bundled copy and
  recording why in Recent Problems — so nothing is broken, but the fetched list
  is not being used until the secret exists. Base64 Ed25519 seed, as a repo
  secret.
- **Issue #1444** is the Team-FM test suggestion, approved and closed. Team-FM
  is genuine data and is live in the catalogue; the issue can stay as the record
  of the first end-to-end run.
- **A stale `hub.quillforall.org`** is referenced in
  `quill/ui/quillin_hub_submit.py` but does not resolve. Worth deciding whether
  the Quillin Hub is coming, or whether that constant should point somewhere
  real — possibly at the same server this note is about.
- **Radio's menu bar is full.** 149 accelerators; `Ctrl+Alt+Shift` is entirely
  exhausted, letters and digits alike. The next menu item needs a submenu or a
  palette-only home, not another chord hunt.

---

## One thing worth remembering from today

The https-only rule I wrote for catalogue addresses would have **excluded
Team-FM**, which is http-only — and measuring it showed **41% of the 400
most-played stations** in the directory Radio already browses are http-only too.
A rule written to protect listeners would have quietly excluded exactly the
small community stations this project exists for.

The protection belongs where it actually helps: the catalogue *itself* arrives
over https and signed, so nobody can substitute the list. An individual http
stream risks only itself. Still refused everywhere: `javascript:`, `file:`,
`data:` — and on the review page an attacker-controlled `href` is the other way
to run script on a page holding a token.

Worth remembering because it was only found by looking up a real station
instead of reasoning about the rule.
