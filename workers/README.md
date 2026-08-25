# picks-submit: removing the GitHub account from the suggest page

Deploying this makes <https://quillforall.org/picks/suggest/> work for anybody,
with **no GitHub account and no sign-in** — they fill the form, press Send, and
the suggestion becomes a labelled issue.

## Why this exists at all

GitHub Pages is static. It serves files; it cannot receive a submission. Some
process, somewhere, has to accept the POST and hold a credential that can write
to the repo — and that credential can never live in the public page, because
the page is readable by everyone (GitHub's own secret scanning would revoke a
published token within minutes, and rightly).

So the choice is not "server or no server". It is "whose small process". This
is the smallest honest one: about eighty lines, on a free tier, doing exactly
one thing.

## Deploying it (about five minutes, free)

You need a Cloudflare account — the free plan is enough — and a GitHub
fine-grained personal access token scoped to `Community-Access/quill` with
**Issues: read and write** and nothing else.

```bash
npx wrangler login
npx wrangler deploy workers/picks-submit.js --name picks-submit
npx wrangler secret put GITHUB_TOKEN     # paste the fine-grained PAT
```

Wrangler prints a URL like `https://picks-submit.<your-subdomain>.workers.dev`.
Put it in one place:

```js
// docs/site/picks/suggest/suggest.js
var SUBMIT_URL = "https://picks-submit.<your-subdomain>.workers.dev";
```

Commit that one line. The form, its validation and the issue body are already
shared with the in-app dialog, so nothing else changes — the page simply stops
sending anyone to GitHub.

## Optional, and worth it if volume grows

**Rate limiting.** Create a KV namespace and bind it as `PICKS_RATE`:

```bash
npx wrangler kv namespace create PICKS_RATE
```

One suggestion per IP per minute and twenty a day. Without the binding the
Worker still runs; it simply does not rate-limit.

**A challenge.** If bots ever find it:

```bash
npx wrangler secret put TURNSTILE_SECRET
```

**Turnstile, never reCAPTCHA.** Turnstile is usually invisible and requires no
puzzle. reCAPTCHA's image grids are precisely the barrier this whole project
exists to remove — a spam control that locks out blind users to keep out bots
has failed at the only job that matters here.

## What it refuses

- Anything that is not a POST of JSON with a title and a body.
- A body with no ```` ```json pick ```` block: approving such an issue later
  would publish nothing, so it is turned away at the door rather than left to
  clutter the review queue.
- More than the rate limit, when a KV namespace is bound.
- Cross-origin requests from anywhere but `https://quillforall.org`.

## If you would rather not run a Worker

The page works today without one — it hands the suggestion to GitHub's
pre-filled issue form, which needs a free GitHub account for the final press.
And the in-app route (**Community > Suggest a Station or Podcast…**) has never
needed an account, because Quill Radio carries its own issues-only token.
