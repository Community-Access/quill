# Community Picks: a curated, living catalogue Radio reads from the web

**Status:** proposal, 2026-08-25. Nothing here is built yet.

## What this is for

Jeff wants a curated listing of stations, podcasts and places that Quill Radio
offers from the **Community** menu, exactly as the ACB Media Podcasts picker
does: see what is on offer, read a description, choose the ones you want, and
have them land in Favorites and Subscriptions in the order you arranged them.

Three things make it more than a bundled list:

1. **It updates without a release.** Adding a station on a Tuesday reaches
   everybody on Tuesday, not at the next installer.
2. **Anybody can suggest an addition**, and nothing appears until Jeff
   approves it.
3. **It is one file**, so the same catalogue can serve Radio, Cast and
   whatever comes next.

## The happy accident: most of this already exists

This repo has already solved this shape once, for Quillins. Reusing it means
no new infrastructure, no server, and no new trust decisions.

| Need | Already in the repo |
| --- | --- |
| Static hosting that updates on merge | `.github/workflows/github-pages.yml` deploys `docs/site/**` to Pages on every push to `main` |
| A JSON feed the app reads from that site | `docs/site/updates/` already serves the app-updater feed |
| A structured public submission form | `.github/ISSUE_TEMPLATE/quillin_submission.yml` |
| **Filing a GitHub issue for a user with no GitHub account** | the bundled issues-only token behind Report a Bug (`core/feedback_token.py`, `AppShellFrame.report_app_bug`) |
| An in-app "submit" dialog to model the surface on | `quill/ui/quillin_hub_submit.py` |
| A domain | `quillforall.org` (`hub.quillforall.org` is already in use) |
| Age-aware caching of a fetched directory | `core/radio/acb_calendar.py`, `core/podcasts/directory_cache.py` |
| **Podcasts in Favorites, with episodes** | already works — see below |
| Picking, ordering, A-Z-until-moved | `core/podcasts/pick_list.py` (built 2026-08-25 for the ACB picker) |

### Favorites already exposes podcasts richly

This part needs no design at all. Radio favorites can hold a **place** — a
favorite that opens a browse branch instead of playing a stream
(`favorites.place_station`, stored as `browse:<node id>`). The browse tree
already understands `mypodcastshow:<feed-url>` and renders it as **Episodes**
(`core/radio/browse_sources.py`, `row_actions.py`). So a podcast saved as a
place favorite opens straight into its episode list, with the same row actions
as any other podcast view.

The picker just has to create those places. Nothing new.

## The file format

JSON, not OPML. OPML is a subscription-list format: it carries podcasts well
and has no vocabulary at all for a radio stream, a browse place, or the
curation metadata (who suggested it, when it was added) this needs. We keep
full OPML support for podcast import/export — this is a different job.

`https://quillforall.org/picks/v1/picks.json`

```json
{
  "format": "quillville-picks",
  "version": 1,
  "updated": "2026-08-25T16:00:00Z",
  "title": "QuillVille Community Picks",
  "description": "Stations, podcasts and places the community recommends.",
  "collections": [
    {
      "id": "acb-media",
      "title": "ACB Media",
      "description": "Everything ACB Media broadcasts and publishes.",
      "items": [
        {
          "id": "acb-media-1",
          "type": "stream",
          "title": "ACB Media 1",
          "description": "Mainstream ACB programming and community events.",
          "language": "en",
          "tags": ["blindness", "community"],
          "stream_url": "https://broadcast.acbmedia.org/acbmedia1",
          "homepage": "https://www.acbmedia.org/",
          "added": "2026-08-25"
        },
        {
          "id": "acb-community-podcast",
          "type": "podcast",
          "title": "ACB Community",
          "description": "Content from ACB sponsored community events.",
          "language": "en-US",
          "feed_url": "https://pinecast.com/feed/acb-community",
          "homepage": "https://acb-community.pinecast.co",
          "added": "2026-08-25"
        },
        {
          "id": "librivox-shelf",
          "type": "place",
          "title": "LibriVox Audiobooks",
          "description": "Public-domain audiobooks read by volunteers.",
          "node_id": "librivox",
          "added": "2026-08-25"
        }
      ]
    }
  ]
}
```

### Rules the format commits to

- **`id` is stable and forever.** It is how "already added" is detected, so a
  renamed station is the same pick and a re-run adds nothing twice.
- **`type` is open.** A client **must ignore an item whose `type` it does not
  understand**, and skip it silently. That is what lets a `video` or `book`
  type ship later without breaking Radio 3.0.
- **The URL path carries the version** (`/picks/v1/`). A breaking change means
  `/v2/`, and v1 clients keep reading a file that still means what it meant.
  `version` inside the document is for diagnostics, not negotiation.
- **`added` is a date, not a timestamp**, and exists so the app can offer
  *"3 new since you last looked"* — the thing that makes a living catalogue
  feel alive rather than merely present.
- **Descriptions are the publisher's or the curator's**, never generated.

Per-type required fields: `stream` → `stream_url`; `podcast` → `feed_url`;
`place` → `node_id`. Everything else is optional.

A JSON Schema lives at `quill/core/schemas/community_picks.json`, validated in
CI exactly as `extension.json` is for Quillins.

## How the app reads it

Mirroring `acb_calendar.py`, which already got this right:

- One reviewed egress site, so the network-egress gate stays honest.
- **A bundled copy ships with the app**, so the picker works on first run,
  offline, and if the site is ever down. The fetched copy supersedes it.
- `ETag` / `If-None-Match`, cached under the app data dir with its age. The
  summary line says how old the copy is, the way the ACB schedule does.
- **Off in Safe Mode**, via `refuse_in_safe_mode`.
- A fetch that fails is a sentence and a stale-but-usable list, never a dead
  window.

### Should it be signed?

**Yes, and this is the one genuinely new trust decision.** This file causes the
app to subscribe to feeds and add stations — anyone who could replace it could
point users at content they did not choose. GitHub Pages over HTTPS with a
custom domain is decent, but the repo already has Ed25519 artifact signing
(`quill/tools/signing.py`) and an update-feed key, so a detached
`picks.json.sig` verified against a bundled public key costs one CI step and
removes the question. Recommend shipping signed from day one; verification
failure falls back to the bundled copy and says so in Recent Problems.

## Suggestions, and approval

**Nobody should need a GitHub account to suggest a radio station.** An earlier
draft of this document routed suggestions through the Quillin flow, which opens
a pre-filled issue in the browser — and that quietly requires the person to have
a GitHub login, create one, and understand what an issue is. For somebody who
just heard a good station and wants to pass it on, that is not a submission
flow, it is a wall.

Radio already solved this. **Report a Bug files a real GitHub issue for users
who have never configured anything**, using a bundled, fine-grained,
issues-only token (`quill/core/feedback_token.py`,
`tools/generate_feedback_token.py`, `AppShellFrame.report_app_bug`). A release
build *fails* if that token is missing, precisely so the channel is never
quietly broken in the field.

So:

1. **Community > Suggest a Station or Podcast…** — an ordinary accessible wx
   dialog, one we control and can make good with a screen reader, rather than a
   web form somebody else designed. Type, title, URL, description, language,
   and why it belongs.
2. **It checks what it can before sending**: is the feed or stream reachable,
   does it already exist in the catalogue, is the URL well-formed. Rejecting a
   duplicate here costs one dialog; rejecting it after moderation costs a
   round trip through a person.
3. **It posts the issue itself, with the bundled token.** No account, no
   browser, no login — the submitter stays in Radio and gets a confirmation
   with the issue number. Falls back to opening a pre-filled issue in the
   browser only when the token is absent (dev builds) or the post fails, so
   the flow degrades instead of dying.
4. **`.github/ISSUE_TEMPLATE/community_pick.yml`** still exists, for people who
   *do* live on GitHub and would rather file it there. Same fields, so both
   routes produce the same machine-readable body.
5. **Jeff approves by adding the `pick:approved` label.** That is the whole
   moderation UI, and it is auditable forever.
6. **A workflow rebuilds the catalogue.** On label or issue close,
   `picks-build.yml` merges the approved issues with a hand-curated
   `docs/picks-source.json` (Jeff's own additions, which need no issue),
   validates against the schema, signs, and writes
   `docs/site/picks/v1/picks.json`. The existing Pages workflow deploys it
   because `docs/**` changed.

Time from "Jeff clicks a label" to "in everybody's app": one workflow run plus
whatever the client's cache TTL is.

## Suggesting from the website, with no app and no account

Wanted: somebody hears about Quill Radio, visits quillforall.org, and suggests
a station — no download, no GitHub, no login.

**The hard limit is worth stating plainly: GitHub Pages is static and cannot
receive a submission.** It serves files. Something, somewhere, has to accept
the POST and hold a credential that can write to the repo — and that credential
can never be in the page, because the page is public: GitHub's own secret
scanning would revoke a published token within minutes, and rightly. So the
question was never "server or no server". It was **whose small process**.

Three shapes were considered, and the form markup is identical in all three;
only where it submits differs.

| | Submitter needs | We run | Verdict |
| --- | --- | --- | --- |
| **`mailto:` handoff** | a mail client | nothing at all | Shipped first, as the stopgap. Perfectly accessible — it is their own client — but it fails webmail-only visitors, and Jeff retypes every one into the review page's Add form. |
| **A serverless function** | nothing | a Cloudflare account | Written (`workers/picks-submit.js`, ~80 lines) and **not taken**: it required an account with a vendor this project has no other reason to depend on, for a process small enough to run beside the ones we already run. |
| **A hosted form service** | nothing | an account | Rejected. A third party in the path, and their accessibility is theirs, not ours. |

**What was actually built, 2026-08-26: a fourth shape.** The submission server
lives in `Community-Access/feedback-hub` (1.2.0, `feedback_hub.server`) and
runs as one small container on `lp.csedesigns.com`, beside the three
applications already there. `https://lp.csedesigns.com/submit/picks` accepts
the POST, validates it, and files the labelled issue.

That is a better answer than the Worker for a reason that has nothing to do
with hosting. feedback-hub already described itself as a "centralized GitHub
backend", but every client carried its own token — which is why Quill Radio
ships one inside its installer, extractable by anyone who unzips it, and why
the website could not submit at all. Giving feedback-hub a server makes the
phrase true, and the apps can stop carrying a credential:

```
Radio "Report a Bug"   ─┐
Radio "Suggest…"       ─┤
quillforall.org form   ─┼──→  feedback-hub server on lp  ──→  GitHub issue
GLOW / Cast / Social   ─┘        (holds the only token)
```

Scope today is deliberately **picks only**. Report a Bug still submits directly
from each app; migrating it at the same time would have made the first
deployment also the riskiest one. `workers/picks-submit.js` has been deleted —
two ways to do one thing is one too many.

Two details of the endpoint matter for this audience:

* **Turnstile, never reCAPTCHA**, if a spam challenge is ever needed. Turnstile
  is usually invisible and requires no puzzle; reCAPTCHA's image grids are
  exactly the barrier this whole project exists to remove. A spam control that
  locks out blind users to keep out bots has failed at the only job that
  matters here. The endpoint supports Turnstile and it is switched off, because
  a challenge nobody needs is a barrier nobody asked for.
* **Rate-limited per address** — one a minute, twenty a day — so a bad
  afternoon costs a handful of closed issues rather than a repo full of them.
  A *refused* attempt is not counted, so being over the minute limit cannot
  push somebody over the day limit for retrying. The address is the **last**
  `X-Forwarded-For` entry, not the first: a client can send a header of its own
  and the proxy appends to it, so the first entry is whatever the client
  claimed.

The public form and the in-app Suggest dialog produce the **same
machine-readable issue body**, so the pipeline behind them is one thing.

## The review page

Labelling issues in GitHub's own web UI is the obvious answer and the wrong
one: that UI is hover-heavy, deeply nested and largely unusable with a screen
reader — the reason this repo carries a whole suite of agents that exist to
keep Jeff out of it. A review surface he cannot comfortably use is a review
surface that does not get used, and then the catalogue never grows.

So: **`https://quillforall.org/picks/review/`** — one static, accessible page
on the same Pages site. No server, no backend, no database.

### How it works

- **Sign in** by pasting a GitHub fine-grained personal access token, scoped to
  `Community-Access/quill` with **Issues: read/write** and nothing else. The
  page verifies it with `GET /user`, shows *"Signed in as jeffbis"*, and offers
  **Sign out**.
- **Held in `sessionStorage` by default** — gone when the tab closes.
  *"Keep me signed in on this device"* opts into `localStorage`. On a shared
  machine the default is the safe one.
- **The list** is every open issue labelled `pick:suggestion`, newest first,
  fetched straight from `api.github.com`. Each is an `<article>` with a real
  heading, the parsed fields (type, title, URL, description, language, why),
  and a link to the source.
- **Per suggestion: Approve · Decline · Needs info · Edit then approve.**
  Approve adds `pick:approved` and closes. Edit lets Jeff correct a title or
  tighten a description *before* it reaches the catalogue, because the
  submitter's wording becomes user-facing text.
- **After an action, focus moves to the next suggestion** and a live region
  says *"Approved ACB Media 3. Four remaining."* Keyboard-only throughout; no
  hover, no drag, no icon-only buttons.

Approving is what triggers `picks-build.yml`, so the path from *"that looks
good"* to *"it is in everybody's Radio"* is one button and one workflow run.

### Adding a pick from the page

The review page is also where Jeff **adds** picks of his own, without waiting
for anybody to suggest one and without editing JSON by hand. Same form as the
public one: type, title, URL, description, language, collection.

It does this by **creating an issue already labelled `pick:approved`** — not by
committing to `picks-source.json` directly. Two reasons, and both matter:

* The token stays **Issues-only**. Writing to the repo would need
  `contents: write`, which is a much larger thing to leave in a browser.
* There is then exactly **one** path into the catalogue. Suggested-and-approved
  and added-by-Jeff arrive the same way, so `picks-build.yml` has one input to
  understand and the history of why every entry exists is in one place.

`picks-source.json` stays in the repo for bulk work — pasting in forty stations
at once is a pull request, not forty form submissions.

### Why this is secure enough

- **The page holds no secret of its own.** It is static HTML and JavaScript;
  anyone can read all of it and learn nothing.
- **Authority is GitHub's, not ours.** Only a token with write access can add
  a label. There is no permission logic on the page to get wrong — the API
  simply refuses.
- **Minimum scope, short life.** One repo, Issues only, an expiry date. A
  leaked token can file and label issues in one repo and do nothing else.
- **The token never goes anywhere but `api.github.com`**, over HTTPS, from
  Jeff's own origin. No analytics, no third-party scripts, no CDN.

### The one real threat, and the rule that closes it

Suggestions are written by the public and displayed on a page that holds a
token. **Any script injection on that origin steals it.** So:

> Every field from an issue is rendered with `textContent`, never `innerHTML`,
> and URLs are shown as text with the scheme checked (`https:` only) before
> anything becomes a real link.

Plus a strict `Content-Security-Policy` (`default-src 'none'`,
`connect-src https://api.github.com`, `script-src 'self'`), which also means a
successful injection could not exfiltrate anything anyway. Belt and braces,
and both are cheap.

If that still feels like too much token to leave in a browser, the fallback
costs nothing: approve from the phone's GitHub app, or run
`gh issue edit <n> --add-label pick:approved`. The page is a convenience over
an API that is already safe, not the thing holding the door shut.

### What the bundled token costs

It ships inside the installer, so it is extractable by anyone who cares to
look. That is a known, accepted trade for Report a Bug and the reasoning
carries over unchanged: the token is a fine-grained PAT scoped to
`Community-Access/quill` with **Issues: read/write and nothing else**, so the
worst case is issue spam in one repo — visible, revocable, and rate-limited by
GitHub. It cannot read code, cannot write code, and cannot touch releases.

Worth adding for picks specifically: the dialog should refuse an obviously
empty or duplicate submission locally, so the cheapest spam is also the
easiest to stop before it leaves the machine.

## What would need building

| Piece | Size | Notes |
| --- | --- | --- |
| `community_picks.json` schema + `core/community_picks.py` (fetch, cache, validate, parse) | small | mirrors `acb_calendar.py` |
| Bundled fallback copy + build wiring | small | |
| Picker dialog | **reuses the ACB picker** | same two-list surface, different source |
| Apply picks → Favorites places + Subscriptions | small | `place_station` + `add_show` |
| `picks-source.json` + `picks-build.yml` + schema CI | medium | |
| Issue form + `pick:approved` label | small | `label-sync.yml` already exists |
| In-app Suggest… dialog | small | `quillin_hub_submit.py` is the template |
| Signing + verification | small | key infrastructure exists |
| "New since you last looked" | small | needs a `picks_last_seen` in history |

The single biggest saving is that the **picker dialog is the same dialog**. If
it is built once for ACB Media with the source passed in, Community Picks is
mostly a second menu item and a different URL.

## Decisions (agreed 2026-08-25)

1. **One catalogue, several collections.** "ACB Media", "Reading Services",
   "Music" are groups inside one file, so there is one URL, one fetch, one
   cache and one signature to verify.
2. **`"retired": true` retires a pick centrally.** A retired item stops being
   *offered* — it disappears from the picker — and **nothing a user already
   added is touched**. Their favorite stays, their subscription stays. Taking
   something out of a shop window is not the same as reaching into somebody's
   house, and a catalogue that could delete a listener's favorites would be
   one worth refusing to fetch. The picker may optionally note *"2 picks you
   have were retired"* in the summary line, and does nothing about it.
3. **Cache for a day, Refresh always available.** Long enough that opening the
   picker is instant and the site is not hammered; short enough that an
   approval lands the same day. The summary line always says how old the copy
   is, as the ACB schedule does, so "is this current?" is never a guess.
4. **One file serves both apps, via `"apps"`.** An item may carry
   `"apps": ["radio", "cast"]`; absent means every app. Cast is never offered
   a radio stream it cannot play, and Radio is never offered something that
   only makes sense in Cast — without maintaining two catalogues that drift.
