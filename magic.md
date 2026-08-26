# magic.md — nobody should ever require a GitHub account

Working notes. Started 2026-08-25; the original goal was met 2026-08-26 and the
work has since grown a second strand (support email, FreeScout). Both are
below, next steps first.

**The one line that started it:** *"Nobody should ever require a GitHub
account."* That is now true of the suggestion form. It is **not** yet true of
Report a Bug, which is the next strand.

---

## Next steps

Ordered. Each says plainly who it needs, because several are blocked on
something only Jeff has.

### Blocked on Jeff

*(Steps 1, 2 and 5 are done. They keep their numbers so references from
earlier notes still line up.)*

1. ~~DNS for the help desk.~~ **Done 2026-08-26.** Jeff added the record at
   Namecheap and it is published, not merely cached — `helpdesk` A
   `107.175.91.158` answers identically from Google, Cloudflare, Quad9 and from
   `dns1.registrar-servers.com` itself.

2. ~~The Caddy block for the help desk.~~ **Done 2026-08-26, and the help desk
   is now reachable.** The block from `deploy/helpdesk/caddy-snippet.conf` is a
   new top-level site block in `~/app/web/Caddyfile`, added after the DNS
   check, validated, and applied with `caddy reload` — never `restart`, and
   `web-caddy-1` still shows the same uptime it had before, which is the proof
   that the four other applications behind it never dropped a connection.

   Let's Encrypt issued on the second attempt. The first finalize came back
   `403 unauthorized` *after* the challenge had already succeeded
   (`authz_status: valid`, served to five validation vantage points) — a known
   transient on Let's Encrypt's side, not a configuration fault. Caddy retried
   sixty seconds later and got the certificate. Worth knowing so nobody rips up
   a working block over the first error in the log.

   Verified, all four arms:

   | Check | Result | What it proves |
   | --- | --- | --- |
   | `/` | 302 to **`https://`**`/login` | FreeScout builds absolute URLs as https, so `X-Forwarded-Proto` and `ENABLE_SSL_PROXY` agree. The failure this rules out is silent: an http redirect off an https page, refused by the browser as mixed content, with nothing in any log naming the cause. |
   | `/login` | 200, cookie `secure; httponly` | The application is actually served, and knows it is behind TLS. |
   | `POST /postmark/inbound` | 401 from the bridge's own Basic auth | The matcher routes *past* FreeScout. A 404 here would have meant Postmark burning ten retries over ten hours on a path that was never going to work. |
   | `http://` | 308 to `https://` | Automatic redirect is on. |

   The four neighbours on that Caddy (`lp.csedesigns.com`, `glow.bits-acb.org`,
   `letitglow.app`, `csedesigns.com`) were re-checked after every reload and
   are unchanged, including `POST`-only `/submit/picks` still answering 405 to
   a GET.

3. **Postmark.** Two halves, and the account is the only accepted service cost
   in the plan.
   - *Outbound*: a Server API token, entered in FreeScout's own interface
     (Manage, then Settings, then Mail) rather than in a file, so rotating it
     never needs a container restart. Send the test message before telling
     anybody the address exists.
   - *Inbound*: the `community-access.org` sending domain verified (DKIM TXT
     and Return-Path CNAME), and an MX record pointing at
     `inbound.postmarkapp.com`. Postmark generates the exact values.

   **Everything except mail can be configured now**, and should be — the site
   is up, so users, teams, folders, tags, canned replies, business hours and
   branding are all reachable at `https://helpdesk.community-access.org/login`
   with the admin account `jeff@jeffbishop.com` created during install.

   One warning that matters more than it looks: **do not rely on "Forgot
   password".** That link sends mail, and mail is exactly what is not
   configured yet, so it will appear to work and quietly deliver nothing. Until
   Postmark is in, the only offline way back into a locked-out account is a
   shell one:

   ```bash
   cd ~/helpdesk
   # A second admin, if the first password is lost. There is no
   # freescout:reset-password command -- create-user is the whole toolkit.
   docker compose exec -u nginx app sh -c \
     'cd /www/html && php artisan freescout:create-user --role=admin \
        --firstName=X --lastName=Y --email=x@example.org --password=...'
   ```

4. **The `action_required` repo setting.** Catalogue-rebuild pull requests
   (currently [#1449](https://github.com/Community-Access/quill/pull/1449) and
   [#1450](https://github.com/Community-Access/quill/pull/1450)) sit unmerged
   because GitHub holds workflow runs on `github-actions[bot]` pull requests
   for manual approval, so auto-merge never fires. The repository's policy is
   `first_time_contributors`, and the bot counts as one.

   Left alone deliberately: it is a security setting on a public repository and
   it is yours to make. Loosening it to `first_time_contributors_new_to_github`
   would still block genuinely new throwaway accounts, which is the actual
   attack. Approving the two waiting runs clears today's backlog either way.

5. ~~The domain question.~~ **Answered 2026-08-26: both.**
   `community-access.org` is the organisation, `quillforall.org` is the
   product. This was the cheapest of the three answers and the one everything
   already assumed, so **nothing moves** — the catalogue URL, the signature
   URL, the CORS allowlist, the web form and the bundled fallback all stay
   exactly where they are, and no redirect has to be maintained indefinitely
   for old installs. Support email is simply new.

   It also unblocks step 8, which was waiting only on this.

### Ready to build, not blocked

*(Step 6 is done. It keeps its number so references from earlier notes
still line up.)*

6. ~~The Postmark-to-Maildir bridge.~~ **Built and proven, 2026-08-26.**
   `feedback_hub.mailbridge` receives the webhook and writes the raw RFC-822
   message into a Maildir; a Dovecot container exposes that Maildir on the
   project's private network only; FreeScout fetches it in its ordinary way.

   Feeding FreeScout *real email* was the whole point — its threading
   (`Message-ID`, `In-Reply-To`, `References`), duplicate detection, auto-reply
   and bounce handling, and conversation reactivation are the reason to run
   FreeScout at all, and creating tickets through its API instead would have
   meant reimplementing every one of them. So the bridge writes the message out
   byte for byte and parses nothing.

   Proven on the box: a webhook POST produced exactly one Maildir message with
   `Message-ID` intact, a repeat POST was answered 200 and wrote nothing, and
   FreeScout's own IMAP credentials fetched it back unchanged. 40 tests.

   It needs Postmark credentials to *carry real mail*, not to be finished.
   `deploy/helpdesk/make-credentials.sh` prints the webhook URL to paste into
   Postmark and the IMAP settings to paste into FreeScout.

7. **Get the token out of every installer.** Mostly done, 2026-08-26.

   The exposure was never a token *in the repository* — there is none, and
   `quill/_feedback_token.py` is gitignored. It is that the build compiles one
   into **every installer**, so anybody who unzips one has it. Issues-only
   scope on a single repository bounds that to issue spam, which is why it was
   tolerable; it stopped being necessary the moment a server could hold the
   credential instead.

   1. ~~`POST /submit/feedback` in feedback-hub.~~ **Done and live.** Any app
      can now file a report through the server, which holds the only token.
      Reports arrive already carrying `product:*`, `type:*` and `source:app`
      labels; crash fingerprints are relayed intact, so deduplication survives.
   2. ~~Point the dialog at it.~~ **Done.** Both call sites pass
      `submission_kwargs()`; the dialog is otherwise untouched — same fields,
      same button, same words, because only the transport moved.
   3. **Delete `quill/_feedback_token.py`, `tools/generate_feedback_token.py`,
      the release check and the `QUILL_FEEDBACK_GITHUB_TOKEN` secret** — but
      *only after* a release has shipped with the server path and been seen to
      work. Until then the token remains the fallback for a build that cannot
      reach the server, which is exactly the safety net worth keeping through
      one release cycle.

   **What this also buys, and the real reason for the shape:** once submission
   is a POST to a URL, where a report ends up stops being the app's business.
   Moving Report a Bug from a GitHub issue to a support conversation in
   FreeScout is now a change on the *server* — no release, no version skew, and
   no installed copy left behind still filing into the wrong place. That
   migration waits on Postmark (step 3), not on any app.

   The reasoning, the costs and what deliberately does *not* change are in
   [the feedback redesign document](docs/design/2026-08-26-feedback-redesign-for-freescout.md).

8. **Decide what `hub.quillforall.org` is.** It does not resolve, and
   `quill/ui/quillin_hub_submit.py` no longer offers the dead button — the
   local validation, which is the useful half, still runs and `HUB_IS_LIVE`
   re-enables the button in one line. Either the Quillin Hub is coming, or that
   constant should point at the server this file is about.

   **No longer blocked**: step 5 answered "both", so `quillforall.org` is
   staying and `hub.` under it remains a name worth using. The question is now
   only whether the Hub is a thing that exists, not whether its domain
   survives.

9. **`PICKS_SIGNING_KEY`.** The catalogue is still published unsigned; the app
   verifies, fails closed, falls back to the bundled copy and records why in
   Recent Problems. Nothing is broken, but the fetched list is not being used.

   **Read this before setting it**, because until today setting it alone would
   not have worked. The signer wrote a two-line sidecar while the app's
   `read_minisig` requires three lines with a `key id:` between them — so CI
   would have signed and published successfully and every app would have
   refused the file as unreadable, which looks exactly like working software.
   Fixed: it now signs through `sign_artifact()`, the same function that writes
   every other signature in the project.

   The secret must be the **seed for the existing publisher key in
   `quill-pub.key`**, not a new keypair — a new one would have to replace a key
   that Quillin and release signatures already depend on. The script now
   refuses a stranger rather than trusting whoever runs it to have known that.

### Smaller, and genuinely optional

10. **Radio's menu bar is full.** 149 accelerators, and `Ctrl+Alt+Shift` is
    exhausted, letters and digits alike. The next menu item needs a submenu or
    a palette-only home, not another chord hunt.

11. **`suggest_pick_dialog.py` disagrees with the web form.** Line 90 still
    says an address "must start with https", which the web form deliberately
    stopped requiring. The in-app `wx.Choice` also does `SetSelection(0)`,
    reproducing the silent-default problem the web form just removed — and the
    page claims the in-app route "does exactly the same thing", which is
    currently true in the bad sense too.

### Newly asked for, 2026-08-26

12. **Bring `quillville.org` onto the server.** The good news is that this is
    the cheapest possible version of this job, and it is worth saying why
    before anyone plans it like step 5.

    **Nothing depends on it today.** The domain is *parked*: the apex answers
    `192.64.119.211` and redirects to `www`, which is
    `parking.d.parity.domains` serving a Namecheap holding page. And nothing in
    the QUILL tree points at it — searching every `.py`, `.json` and `.md` for
    a `quillville.org` URL returns no matches at all. "QuillVille" exists in
    the codebase purely as a **menu name** (`quill/ui/quillville_menu.py`,
    appended as `&QuillVille` by `apps/weather.py`, `apps/inkwell.py` and the
    rest), never as an address.

    That is the exact opposite of the `quillforall.org` situation step 5 was
    weighing. No URL is compiled into a shipped build, so there is no version
    skew, no installed copy left pointing at the old place, and **no redirect
    debt to carry indefinitely**. Moving it is a DNS change and a Caddy block,
    and that is genuinely all.

    Its DNS is at `dns1`/`dns2.registrar-servers.com` — the same Namecheap
    account, and the same screen, as the `helpdesk` record just added.

    1. **Two A records, not one.** `@` and `www`, both to `107.175.91.158`.
       Both names go in the one site block so a single certificate covers the
       pair, and — the step 2 rule again, which cost nothing there only because
       it was obeyed — **both must resolve before the block is added**, or the
       failed validations spend a budget that is five per hostname per hour.
    2. **Pick the canonical direction.** Parking currently sends apex to
       `www`. Recommend reversing it: `quillville.org` canonical, `www`
       redirecting to it, which is what `letitglow.app` on this same box
       already does.
    3. **Decide what it serves** — the one real question here, and yours.
       If it is a static site (the natural reading, given QuillVille is the
       cross-app launcher and download hub), it needs **no new container at
       all**: Caddy already bind-mounts `~/app/web/www` to `/srv/www`, so a
       `root * /srv/www/quillville` plus `file_server` is the whole deployment,
       and updating the site is copying files. If it needs to be an
       application, it is a container beside the other six and a
       `reverse_proxy`, like the help desk.

    Whoever writes that block: **do not edit the Caddyfile with `sed -i`.** See
    the fifth trap below — it is new, it was found today, and it is silent.

---

## Where things stand

| Route | Account needed? | Status |
| --- | --- | --- |
| Quill Radio, Community menu, Suggest a Station or Podcast | **No** | Working. Files an issue with the bundled issues-only token. |
| `quillforall.org/picks/suggest/` | **No** | **Fixed 2026-08-26.** Posts to the submission server, which files the issue. |
| `lp.csedesigns.com/submit/picks` | — | **Live.** feedback-hub 1.2.0, one container beside the four apps already on the box. |
| Help desk, `helpdesk.community-access.org` | — | **Reachable and serving, 2026-08-26.** DNS live, Caddy block in, Let's Encrypt certificate issued to 2026-11-24. Configurable now; waiting only on Postmark to carry mail. |
| Inbound mail, Postmark to FreeScout | — | **Built and proven.** Waiting only on Postmark credentials to carry real mail. |
| Report a Bug, every app | **No** | **Routed through the server**, so a build needs no token. Still files a GitHub issue until Postmark lands. |
| `workers/picks-submit.js` (Cloudflare) | — | **Deleted.** Two ways to do one thing is one too many. |

The picks pipeline is proven end to end: suggestion, `pick:suggestion` label,
review, `pick:approved`, `picks-build.yml`, validated, signed, pull request,
merged, deployed, serving. Issues
[#1448](https://github.com/Community-Access/quill/issues/1448) and
[#1451](https://github.com/Community-Access/quill/issues/1451) were filed by
the server with no account involved, then closed.

### How the pieces fit together

Four kinds of client — Report a Bug and Suggest inside Quill Radio, the web
form on quillforall.org, and eventually GLOW, Cast and Social — all send to one
small server on `lp.csedesigns.com`. That server is the only thing holding a
credential. Today it files GitHub issues for picks; once next step 7 lands it
will also relay support messages to Postmark, which delivers them into
FreeScout, where a person answers. Escalation from a FreeScout conversation to
a GitHub issue stays a human decision, made after sanitising.

---

## What is deployed on lp.csedesigns.com

Five applications now share the box, behind one Caddy that terminates TLS.
`jeffbis` is in the `docker` group but has **no passwordless sudo**, so
everything added is a container and the only thing needing a person is a Caddy
edit.

| Piece | Where | Notes |
| --- | --- | --- |
| Submission server | `~/feedback-hub` | feedback-hub 1.2.0, `feedback-hub-submit:8095`, two gunicorn workers, 192 MB cap. |
| Help desk | `~/helpdesk` | FreeScout 1.8.219 and MariaDB 11.4, `helpdesk-app:80`, 1 GB and 512 MB caps. |
| Caddy route, picks | `~/app/web/Caddyfile` | A `@picks_submit` matcher on `lp.csedesigns.com` and `/submit/*`. |
| Inbound bridge | `~/feedback-hub/deploy/helpdesk` | `helpdesk-mailbridge:8096`, 256 MB cap. Writes the raw message into a Maildir. |
| Local IMAP | same | Dovecot, `helpdesk-imap:143`. No published ports, and **not** on the shared edge network. |
| Caddy route, help desk | `~/app/web/Caddyfile` | **Live.** A top-level `helpdesk.community-access.org` block covering FreeScout and the `/postmark/*` webhook, both written as `handle` so page order is run order. Access log at `/data/helpdesk-access.log`. |

Backup of the Caddyfile before this work: `~/app/web/Caddyfile.bak.2026-08-26`,
and immediately before the help desk block went in,
`~/app/web/Caddyfile.bak.pre-helpdesk.2026-08-26`.
Runbooks live in the feedback-hub repository, at `deploy/README.md` and
`deploy/helpdesk/README.md`.

---

## Traps found on the way, all now written down

Five things that were silently broken, or would have been. Each is recorded
here because each looked exactly like working software.

**`redir` was shadowing every handler in that Caddy block.** Caddy sorts
directives by a fixed order and `redir` ranks *above* `handle` and
`handle_path`, so a bare redirect at the foot of a site block does not run
last — it runs first, and every handler above it is dead code. That had already
happened to `/ggg*`, which never served anything; the links only kept working
because the redirect landed on a working `/ggg` on the canonical host. Fixed by
wrapping the redirect in `handle { }`.

**The catalogue signer wrote a sidecar its own verifier could not read.** See
next step 9. Setting the secret alone would have published a signed catalogue
that every app refused.

**The FreeScout image regenerates its configuration on every recreate, and
blanks `APP_KEY`.** FreeScout encrypts stored mailbox passwords with that key,
so a rotation makes the saved Postmark credentials undecryptable and **inbound
mail stops silently** — mail nobody knows they are not receiving. Fixed by
bind-mounting the host's copy so it is authoritative. The same image also
writes a database driver name Laravel 5.5 does not define, whose only symptom
is an endless redirect to `install.php`. Both are documented in
`deploy/helpdesk/README.md`.

**Three accessibility mechanisms the suggestion form was about to rely on do
not work on NVDA or JAWS.** `role="alert"` plus focus reads the whole error
list twice with the first reading clipped, and an unchanged alert may not fire
at all — so resubmitting the same errors announces nothing. Clearing and
rebuilding a live region in one task announces nothing either, which would have
silenced every repeated rate-limit refusal the server produces *by design*. And
disabling the focused submit button strands the keyboard thirteen tab stops
away, announced by nothing. All three replaced.

**`sed -i` silently disconnects the Caddyfile from the running Caddy.** Found
2026-08-26, while making a one-word header change that appeared to do nothing.

Docker bind-mounts a *single file* by inode. `sed -i` does not edit in place
despite its name — it writes a temporary file and renames it over the target,
which produces a **new inode**. The container keeps the old one. From that
moment the host file and the running configuration are two different files, and
nothing says so.

What makes it worse than an ordinary mistake is that every check still passes.
`caddy validate` reads the host file and says *Valid configuration*.
`caddy reload` re-reads `/etc/caddy/Caddyfile` — the container's inode, the old
one — and reports success. So the edit is confirmed twice and applied never.
It was caught only by comparing `stat -c %i` on both sides after a change
refused to take effect; the two inodes were 541630 and 544502.

Two rules follow:

- **Append with `>>`, rewrite with `>`.** Both keep the inode. To edit,
  transform to a temp file and then `cat tmp > Caddyfile` — the redirect
  truncates the existing inode rather than replacing it. Never `sed -i`, and
  never `mv` a new file over it.
- **The repair needs a container recreate**, because a bind mount can only be
  re-bound that way — and that is a restart of the Caddy fronting every
  site on the box, so it is a deliberate act, not a reflex.

Left in a safe state on the day: the host file and the container's copy were
made byte-identical (both `md5 72620e1c1544ba9999d412330bb437e8`), so the
divergence cannot change behaviour and a recreate whenever convenient is a
no-op. The one-word header improvement that started it was reverted rather than
forced, because a cosmetic duplicate header is not worth restarting every
production site on the box. **The inodes are still split until that recreate happens** —
so the next person to edit this file must do the recreate first, or their
change will vanish exactly as this one did.

*(The cosmetic issue itself, for whoever picks it up: FreeScout already sends
`X-Content-Type-Options: nosniff`, and the Caddy block sends it too, so it
appears twice. Harmless. The fix is `?X-Content-Type-Options nosniff` —
set-only-if-absent — which keeps the fallback if FreeScout ever stops sending
it.)*

---

## Settled, so please do not re-litigate

- **The bundled token stays.** Rotation was offered on 2026-08-26 and declined.
  It is scoped to issues on one repository, so the worst an extraction buys is
  issue spam. The option stays open precisely because the server exists —
  rotating later is one `.env` edit and a restart, not a release — but it is
  not being taken.
- **A path on `lp.csedesigns.com`, picks only, code in feedback-hub.** The
  three questions this file opened with, all taken as recommended.
- **Picks suggestions keep going straight to GitHub**, and are not moving to
  the help desk. A station suggestion has no customer relationship to preserve
  and nothing personal in it — the *point* is that it becomes public — and it
  is already consumed by a workflow. Routing structured data through a mailbox
  would mean a person retyping it. The plan governs support; this is content
  contribution, and the two should not be conflated because both produce
  issues.
- **The forms stay simple.** Both of them, the wx dialog and the web page. What
  changes is where a submission goes, never what the person filling it in has
  to do.
- **Turnstile, never reCAPTCHA.** The endpoint supports Turnstile and it is
  switched off, because a challenge nobody needs is a barrier nobody asked for.
  If spam ever arrives, that is the switch. reCAPTCHA's image grids are
  precisely the barrier this project exists to remove: a spam control that
  locks out blind users to keep out bots has failed at the only job that
  matters here.
- **The "What is it?" radio group starts unanswered.** It was a `<select>` with
  a pre-selected first option, which can never express "not answered" — and it
  is the one answer on the form whose wrong value is invisible to the person
  who gave it, silently filing a podcast's feed under `stream_url`. Do not
  restore a default.

---

## One thing worth remembering

The https-only rule written for catalogue addresses would have **excluded
Team-FM**, which is http-only — and measuring it showed **41% of the 400
most-played stations** in the directory Radio already browses are http-only
too. A rule written to protect listeners would have quietly excluded exactly
the small community stations this project exists for.

The protection belongs where it actually helps: the catalogue *itself* arrives
over https and signed, so nobody can substitute the list. An individual http
stream risks only itself. Still refused everywhere: `javascript:`, `file:` and
`data:` — and on the review page an attacker-controlled `href` is the other way
to run script on a page holding a token.

Worth remembering because it was only found by looking up a real station
instead of reasoning about the rule.
