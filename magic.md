# magic.md — nobody should ever require a GitHub account

Working notes. Started 2026-08-25; the original goal was met 2026-08-26 and the
work has since grown a second strand (support email, FreeScout) and, later the
same day, a third (the domain and the brand: `quillforall.org` becomes
`quillville.org`, with the apps at the centre of it). All three are below, next
steps first.

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
   in the plan. **The step-by-step is now its own section: *Postmark, step by
   step*, below.** Three things from it belong here, because they change what
   this step is:
   - *Sending* needs **`community-access.org` verified — the apex, not the
     `helpdesk` subdomain**, because the address is `support@community-access.org`
     and Postmark verification does not cascade to subdomains. Two DNS records
     at Namecheap, DKIM TXT and a Return-Path CNAME, whose values Postmark
     generates. Then a Server API token, entered in FreeScout's own interface
     rather than in a file, so rotating it never needs a container restart.
     Send the test message before telling anybody the address exists.
   - *Receiving* is **not** the same question, and the domain already has mail:
     five Namecheap `eforward` MX records are live on it today. Replacing them
     with `inbound.postmarkapp.com` would send every address at the domain into
     a bridge that serves one, and 403 stops Postmark retrying — so the
     recommendation is a single Namecheap forwarder into Postmark and **no MX
     change at all**. Reasoning in step 4 of that section.
   - *Cost*: **inbound processing starts at Postmark's Pro plan, $16.50 a
     month.** The free plan sends 100 a month and cannot receive at all.

   **Everything except mail can be configured now**, and should be — the site
   is up, so users, teams, folders, tags, canned replies, business hours and
   branding are all reachable at `https://helpdesk.community-access.org/login`
   with the admin account `jeff@jeffbishop.com` created during install.

   **The install-time password for `jeff@jeffbishop.com` is not recoverable.**
   There is no `ADMIN_PASS` in the compose file — it was typed once during
   `freescout:create-user`, and only the bcrypt hash is in the database. It can
   be replaced, never read back.

   So a **temporary second admin** was created on 2026-08-26,
   `jeff+hd@jeffbishop.com` (id 2), and its login verified end to end. The
   credential is at **`C:\Users\jeffbis\helpdesk-temp-login.txt`**, deliberately
   *outside this repository*: `magic.md` is tracked in `Community-Access/quill`,
   which is **public**, so a live admin password here would be one
   `git commit -am` away from permanent public history — on a help desk that is
   now reachable from the internet. That file carries the reset steps too:
   sign in, set a new password on the original account from Manage → Users,
   delete the temporary admin, delete the file.

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

   **Superseded 2026-08-26 by step 14.** Half of this still stands —
   `community-access.org` is the organisation — but the product half does not:
   `quillforall.org` is being renamed to `quillville.org`. The redirect debt
   this answer was written to avoid is now accepted deliberately. Read step 14
   rather than this paragraph.

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

   **No longer blocked**: step 5 answered "both", so the question is now only
   whether the Hub is a thing that exists, not whether its domain survives.

   **Amended by step 14.** `hub.quillforall.org` is not the name to revive —
   the product domain is becoming `quillville.org`. Recommend a **path, not a
   subdomain**: `quillville.org/hub`. One certificate, one site, one place to
   reason about, and the Hub reads as a part of the town rather than a
   separate one. A subdomain is worth its own certificate only when it is a
   separate application, which is the test `helpdesk.` passes and this does
   not.

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

### Newly asked for, 2026-08-26 (second batch)

13. **A public support form, served by the submission server itself.** Asked
    for as *"an HTML form that looks like the one in the app, submitting
    tickets the same way"* — and the answer is that it is the cheapest piece
    left in this whole file, for a reason worth writing down.

    **The in-app form is not hand-built.** `feedback_hub.wx_dialog` renders
    `schemas/quill.json` — categories, and for each field a name, label, type,
    `required`, `max_length` and placeholder (`_schema.py`, `FieldSchema` and
    `AppSchema`). The server already imports that module. So the web page is
    not a *copy* of the dialog that will drift from it by the second release;
    it is a **second renderer of the same schema**, and one test asserting both
    produce the same field set keeps it that way.

    Three facts remove the friction that usually makes this a project:

    - **No Caddyfile edit.** The existing matcher is `host lp.csedesigns.com` +
      `path /submit/*`, written as `handle` and not `handle_path`. A page at
      `GET /submit/report` is already routed, with its path intact. Given the
      fifth trap below and the four neighbours on that Caddy, *not touching it*
      is worth real money.
    - **No CORS.** The page is served by the same origin it posts to, so
      `PICKS_ALLOWED_ORIGINS` stops applying to it and an entire class of
      failure disappears. Keep it under `/submit/` — everything else on that
      site block ends at the `redir` to `letitglow.app`.
    - **No new dependency.** feedback-hub is `dependencies = []` on purpose.
      Render with `html.escape` and f-strings, the same way `_reply` writes
      JSON.

    **Make it a plain form post, not a `fetch`.** This is where the web form
    should be *better* than `picks/suggest/`, not a copy of it. A
    server-rendered `<form method="post">` whose result is a new page means the
    three mechanisms recorded in the traps below — `role="alert"` plus focus
    reading the list twice with the first reading clipped, an unchanged alert
    not firing at all on a resubmit, and a cleared-and-rebuilt live region
    announcing nothing — are simply **not in play**. Errors come back as a page
    with a summary at the top and focus on it. It works with JavaScript off,
    and it is less code than the version that needs the workarounds.

    That needs one change to `_handle_feedback`: accept
    `application/x-www-form-urlencoded` alongside JSON, and content-negotiate
    the reply (JSON for the app, HTML for a browser). Everything else —
    `validate_entry`, the app allowlist, the size cap, the rate limiter — is
    reused untouched.

    **The route to FreeScout is the same one, which is the point.** Both paths
    converge on one relay: today the POST becomes a GitHub issue, and once
    Postmark lands (step 3) it becomes mail into the bridge and a conversation
    in the help desk, with the reporter's optional email as the reply address.
    One server change flips the desktop dialog and the web form together, and
    no installed build notices.

    Four things the web form must handle that the app does not:

    1. **Product.** The app knows it is "Quill Radio 1.0.0"; a visitor does
       not. Render a select from the existing `feedback_apps` allowlist, which
       keeps the "any app name is junk" protection rather than adding a
       free-text field beside it.
    2. **Missing metadata.** No version, no platform string — the dialog fills
       those in from the running process. The agent asks. Not a blocker.
    3. **Bots.** `/submit/feedback` has no Turnstile because desktop apps reach
       it, and a public page is reachable by anything. **Turnstile stays off** —
       that is settled below and this does not reopen it. The switch is
       `TURNSTILE_SECRET`, it is already wired for picks, and it gets thrown if
       spam actually arrives. Explicitly **not** a honeypot field: that is the
       exact mechanism that broke the BITS PMPro checkout for anyone using
       autofill, which is most screen-reader users.
    4. **The rate limit is per address.** Four a minute and forty a day. A
       training centre or a school behind one NAT will trip that, and the
       person who trips it is told the button does not work. The web budget
       should be raised or keyed separately from the desktop one.

    **What it does not give**, and should not be sold as giving: ticket
    *history*. Viewing your own past conversations is FreeScout's paid
    **End-User Portal** module, and the free-software baseline rules it out.
    This is the submit half only; replies arrive by email, which for a
    screen-reader user is arguably the better end of that trade.

    **Worth knowing before that trade is made permanent.** The End-User Portal
    is **$12.99**, once, with lifetime updates, and its login is a **magic
    link, not a password**: the visitor types an email address, gets a link
    valid for an hour, and a customer record is created if none existed.

    The licence covers **one FreeScout instance**, which is all there is — and
    the number of *websites* is not what it counts, so the contact-form widget
    can sit on `quillville.org`, `community-access.org` and anywhere else from
    the one purchase. It is transferable between domains through a
    `Deactivate License` button, so nothing here is made harder by step 14.
    Two caveats: there are no refunds, and one key cannot cover a staging
    instance as well as production. The modules are themselves AGPL-3.0; the
    one-instance rule is asked for rather than enforced, and one is genuinely
    all this needs.

    One design consequence if it is bought: the portal's *Submit a Ticket*
    writes into the database directly, without sending mail — so it does
    **not** travel the Postmark-to-Maildir path that step 6 built, and it is a
    second intake route rather than a replacement for step 13. The desktop apps
    still need the relay, because a wx dialog cannot post to a web widget. That
    is a *better* accessibility story than any password form — nothing to
    remember, nothing to type twice, no CAPTCHA — and it would close the
    history gap without adding an account to remember. It is the one paid
    module in this whole system that buys something the free path genuinely
    cannot, so it deserves a deliberate yes or no rather than being ruled out
    by the baseline in passing. Step 13 does not depend on the answer either
    way: the form is the submit half, and the portal, if bought, sits beside
    it.

14. **`quillforall.org` becomes `quillville.org`, and the site is rebranded
    around the family.** Asked for on 2026-08-26, and it **reverses step 5**.

    Say that plainly rather than leaving two answers in one file. Step 5 chose
    "both, and nothing moves", and its whole argument was that no redirect
    would have to be maintained indefinitely for old installs. That answer is
    **withdrawn**. The cost it avoided is now being **accepted deliberately**:
    `quillforall.org` has to keep answering for as long as any shipped build is
    running, which is forever in practice, and everything below is written to
    make that obligation as small and as boring as it can be.

    #### What actually depends on the old name

    | Reference | Where | Moves? |
    | --- | --- | --- |
    | `PICKS_URL` | `quill/core/community_picks.py:39` | **Compiled into every shipped build.** This is the whole problem. |
    | `PICKS_SIGNATURE_URL` | same file, line 48 | Derived from `PICKS_URL`; same problem. |
    | Egress audit text | `quill/tools/network_egress_entries.py:139` | Gate entry; must match whatever the code says. |
    | Schema `$id` | `quill/core/schemas/community_picks.json:3` | An identifier, never fetched. Cosmetic — and changing it is a format decision, so leave it. |
    | `website` default | `tools/generate_build_info.py:98` | New builds only. |
    | `website = "https://quillforall.org"` | `build/version.toml:15` | **The value that actually ships**, and the file is gitignored and local. It will not appear in any diff, any review or any CI check — the person cutting the release edits it on their own machine or the installer keeps saying the old name. |
    | `hub.quillforall.org` | `quill/ui/quillin_hub_submit.py:39`, README, PRD, site pages | Dead today; see step 8. |
    | The site itself | `docs/site/**`, published by `github-pages.yml` | All of it. |
    | `"_Submitted from quillforall.org._"` | `docs/site/picks/suggest/suggest.js:452` | And the test that pins it. |
    | CORS allowlist | `PICKS_ALLOWED_ORIGINS` on the server | Both origins during the move. |

    Two things make this smaller than the list looks. `urllib` follows
    redirects by default, so a 301 on the catalogue URL *does* work for builds
    already in the field — and the catalogue is verified against a bundled
    signing key, so which host served it is not a security question. And
    `FORMAT` in `community_picks.py` is already the string
    **`quillville-picks`**: the brand is in the data format that ships today,
    so this is consolidating a name, not inventing one.

    #### The one constraint that decides the shape

    **GitHub Pages allows one custom domain per repository.** The site cannot
    answer on both names from Pages, which is why the interesting question is
    not "how do we rename" but "which name leaves Pages".

    **Plan A — recommended. QuillVille moves to the box; the old name stays on
    Pages.**

    - `quillville.org` and `www` are served by Caddy from `/srv/www/quillville`
      exactly as step 12 describes. Nothing there changes.
    - `quillforall.org` **stays exactly where it is on GitHub Pages**, keeps its
      custom domain, keeps its DNS, and keeps serving `/picks/v1/picks.json`
      and its `.minisig` as the same static files it serves today. Its human
      pages become short redirect stubs.
    - **Shipped builds therefore see no change at all.** No DNS move, no new
      certificate, no propagation window, no redirect hop, and `picks-build.yml`
      is untouched. The one URL compiled into released binaries is the one
      thing that does not move — which is the rule this project has already
      paid to learn twice.
    - It also makes `quillville.org/support` a *real path*: Caddy can
      `handle /support*` and `reverse_proxy` it to `feedback-hub-submit:8095`,
      so step 13's form is same-origin under the brand name, with no CORS and
      no second hostname to explain over the phone.
    - Cost, stated honestly: the new site needs a way to reach the box. That is
      an `rsync` step and an SSH deploy key held as a repository secret — the
      first credential this arrangement has needed on the GitHub side, and it
      should be a key that can write one directory and nothing else.

    **Plan B — cheaper, and I do not recommend it. The custom domain moves to
    `quillville.org`; `quillforall.org` moves to the box as a permanent 301.**

    - No new deploy path: the existing workflow publishes under a new name.
    - But the catalogue URL compiled into every shipped build now depends on a
      redirect from a Caddyfile that a person edits by hand, forever. It works —
      `urllib` follows it — and it makes a shipped feature depend on the one
      file in this whole system with a documented history of silent breakage.
    - `quillville.org/support` cannot be reverse-proxied from Pages. The form
      would have to be a static page whose `<form action>` points at
      `lp.csedesigns.com`. That does work with no JavaScript and needs no CORS
      (a form navigation is not a `fetch`), but the confirmation page appears on
      a different hostname than the one the person typed.
    - And there is a real, if small, window: between flipping the Pages custom
      domain and the old name resolving to the box, `quillforall.org` returns
      Pages' 404. Bounded by lowering the TTL a day ahead, and low-stakes
      because the catalogue is cached for 24 hours and a failed fetch already
      falls back to the bundled copy — but it exists, and Plan A does not have
      it.

    #### The fix that stops this being a question a third time

    Independent of A or B, and worth doing in the same release: give the
    catalogue the same treatment the submission server already has. A
    `QUILL_PICKS_URL` environment override mirroring
    `QUILL_FEEDBACK_SERVER_URL`, and — the useful half — point *new* builds at a
    stable alias such as `picks.quillville.org` that is a DNS record rather than
    a site. Then the next rename is a CNAME, and no future note has to open with
    "this is compiled into every installer".

    #### Where support lives

    - **`quillville.org/support`** is the address to publish. Under Plan A it is
      a real path proxied to feedback-hub, so the form, the confirmation and the
      errors all stay on the brand domain.
    - **`helpdesk.quillville.org` redirects to `helpdesk.community-access.org`.**
      One A record and one three-line Caddy block:
      `redir https://helpdesk.community-access.org{uri} permanent`.
    - **Redirect, never `reverse_proxy`.** FreeScout builds absolute URLs — that
      is exactly what the step 2 check on `/` proved when it answered `302` to
      an `https://` login URL. Proxying a second hostname into it produces links
      and cookies for the *other* host, and the symptom is an intermittently
      broken login rather than an error anybody can read.
    - Put one sentence on `/support` saying the help desk is run by **Community
      Access**. A hostname changing mid-flow is alarming when it is a surprise
      and unremarkable when it was announced a line earlier.

    #### The rebrand, in one rule

    Three names, and they stop being re-litigated once they are written down:

    - **QuillVille** is the *place* — the site, the launcher, the download hub,
      the front door. It is not an app and it never ships as one.
    - **The apps keep their own names** — QUILL, Quill Radio, QUILL Cast, Quill
      Weather, Quill Social, Quill Beacon, QUILL Audio Studio, Quill Inkwell.
      QuillVille is where they live, not what they are called.
    - **Community Access** is the *organisation* — support, governance, legal,
      the help desk. This is the half of step 5's answer that survives intact.

    "All apps at the centre" is an information-architecture change, not a visual
    one. Today `docs/site/index.html` is QUILL's landing page with the others
    mentioned; it should become the family's, with each app a peer entry
    carrying the four things a visitor actually wants — what it is, download,
    documentation, what changed — and QUILL as one of them rather than the
    subject. `quillville_menu.py` already appends `&QuillVille` to every app, so
    the site would finally be the place that menu implies.

    Two constraints on whoever does it. The site is **HTML only** by design —
    `github-pages.yml` renders every doc through pandoc and publishes no
    Markdown — so a rebrand is a change to the hand-built shell in `docs/site/`,
    not a new generator. And the picks pages carry a full accessibility review
    that was expensive to get right; reuse that shell, that stylesheet and those
    patterns rather than starting a marketing redesign that quietly regresses
    heading structure and skip links.

    #### Suggested order

    Each step is independently useful and independently reversible:

    1. **Two A records** for `quillville.org` and `www`, both `107.175.91.158`.
       Both must resolve *before* any Caddy block is added — five failed
       validations per hostname per hour is the budget, and step 2 only cost
       nothing because that rule was obeyed.
    2. **The Caddy block**, apex canonical and `www` redirecting to it, serving
       `/srv/www/quillville`, with a placeholder page. Nothing points at it yet,
       so this is free to get wrong.
    3. **`helpdesk.quillville.org`** — one record, one `redir` block. Smallest
       possible piece, and it makes the help desk reachable under the brand the
       day the brand exists.
    4. **Publish the site to the box** alongside Pages, unchanged in content.
       Both names now serve the same site. Nothing has been renamed yet.
    5. **Rebrand** the site under QuillVille with the family at the centre, and
       ship it to the box only. Compare the two side by side for as long as you
       like.
    6. **`/support`**: the Caddy handle, and step 13's form behind it.
    7. **Turn `quillforall.org` into stubs** — human pages become a zero-second
       meta refresh plus a visible link and a `rel=canonical`. Zero seconds
       matters: WCAG fails a *timed* refresh and treats a zero-delay one as a
       redirect. **`/picks/v1/` is not touched**, and that is the whole trick.
    8. **`QUILL_PICKS_URL` and the stable alias**, in the next release.
    9. **Update the references** in the table above, including the egress-audit
       entry and the test that pins the suggestion form's footer line.

    And the standing Caddyfile rules apply to every block above: **no `sed -i`**
    (fifth trap), and the split inodes from that trap mean the next person to
    edit that file **does the recreate first**, or their edit is invisible to
    the running Caddy.

---

## Postmark, step by step

Asked on 2026-08-26: *"do I have to set up Postmark for the subdomain, or just
for `community-access.org`?"* The answer is short, so it goes first, and the
rest of this section is the order to do things in.

### The short answer

| Name | Does Postmark need it? | Why |
| --- | --- | --- |
| `community-access.org` | **Yes — this is the one.** | It is the domain in the `From` address, `support@community-access.org`. Sending authentication is per **domain**, and the address is at the apex. |
| `helpdesk.community-access.org` | **No. Nothing at all.** | It is a *web* hostname. Postmark never sends as it and never receives for it; its only role in mail is hosting the webhook URL the bridge listens on. |
| `quillville.org`, `quillforall.org` | **No**, unless a `From` address ever lives there | Step 14 publishes support at `quillville.org/support`, but the *address* stays `support@community-access.org`, so nothing is added here. |

The subdomain question has a real trap behind it, which is why it is worth
being explicit rather than assuming the obvious. **Verifying a domain in
Postmark does not cover its subdomains.** Postmark's own words: *"To send a
fully authenticated email, each subdomain you want to send from will have to be
added to Postmark individually"* — because DKIM and the Return-Path are
domain-specific, and are kept separate on purpose so that a subdomain's sending
reputation is its own. So if anyone ever decides to send as
`support@helpdesk.community-access.org`, that is a **second** domain in
Postmark with its own DKIM record and its own Return-Path, not a free
inheritance from the apex. Sending from the apex, as planned, needs one entry
and one pair of records.

Receiving is a different question with a different answer, and it is the only
genuinely hard decision in this section: it depends on **where the MX for
`community-access.org` points**, which today is not Postmark. That is step 4.

### Before anything: what it costs, which is not what the plan assumed

Step 3 of *Next steps* calls the Postmark account "the only accepted service
cost". Still true, but the number is not zero, and the reason is exactly the
half this system depends on:

| Plan | Price | Emails | Inbound processing |
| --- | --- | --- | --- |
| Developer | **$0** | 100 / month | **No** |
| Basic | $15 / month | 10,000 | **No** |
| **Pro** | **$16.50 / month** | 10,000 | **Yes** |
| Platform | $18 / month | 10,000 | Yes |

**Inbound starts at Pro.** The free plan can send, can verify domains, and is
enough to prove outbound end to end — but it cannot receive, and receiving is
what `feedback_hub.mailbridge` exists for. Check the figures at
<https://postmarkapp.com/pricing> at signup rather than trusting this table;
Postmark has been repriced before.

The honest alternative, so this is a decision rather than a default: a real
IMAP mailbox somewhere cheap (Namecheap Private Email is about a dollar a
month) plus the **free** Postmark plan for outbound would cost roughly a dollar
a month instead of $16.50, and FreeScout would fetch that mailbox directly — no
bridge, no Dovecot, one fewer moving part. What it gives up is one vendor for
both directions, Postmark's inbound parsing and spam scoring, and the bridge
that is already built, tested and proven on the box. The recommendation is
**Pro**: the expensive part of inbound is already paid for in work, and 100
outbound messages a month will not survive contact with auto-replies.

### Step 1 — The account, the server, and approval

1. Sign up at <https://postmarkapp.com>. Use an address that will still be read
   in two years; it is where deliverability warnings go.
2. Create **one Server**, named something like `Community Access help desk`. A
   Server carries both directions: a *Default Transactional* stream for
   outbound and a *Default Inbound* stream for inbound. Postmark allows **one
   inbound stream per server, and one domain on that stream**, which is why
   this is one server rather than two.
3. Copy the **Server API token** — *Servers → your server → API Tokens*. It is
   not the Account API token; the account token cannot send, and the error it
   produces says nothing useful.
4. **Expect a manual approval, and plan around it.** Postmark reviews every new
   account, usually inside 24 hours on a weekday. Until it is approved you can
   only send to domains you have added and verified; everything else is
   refused. You *can* verify domains, configure inbound, set webhooks and send
   to the sink address `test@blackhole.postmarkapp.com` while waiting, which is
   why DNS is step 2 and not step 5.

### Step 2 — Verify `community-access.org` for sending

The DNS half, at Namecheap, on the same *Advanced DNS* screen where the
`helpdesk` A record went in.

1. In Postmark: *Sender Signatures → Add Domain* → `community-access.org`, then
   open its **DNS Settings** page. Postmark generates both values; nothing
   below is guessable, so copy them from that page rather than from here.
2. In Namecheap: *Domain List → Manage → **Advanced DNS** → Add New Record*.

| Purpose | Type | Host (Namecheap) | Value |
| --- | --- | --- | --- |
| DKIM | TXT | the selector Postmark shows, e.g. `20260826123456pm._domainkey` | the long `k=rsa; p=MIGf…` string, exactly as shown |
| Return-Path | CNAME | `pm-bounces` (Postmark's default; use whatever its page says) | `pm.mtasv.net` |
| DMARC, optional but recommended | TXT | `_dmarc` | `v=DMARC1; p=none; rua=mailto:jeff@jeffbishop.com` |

Three things that bite people on that screen:

- **Namecheap's Host field takes the label only, never the whole name.** Type
  `pm-bounces`, not `pm-bounces.community-access.org`; Namecheap appends the
  domain itself, and a full name entered here becomes
  `pm-bounces.community-access.org.community-access.org`, which verifies never
  and looks exactly like a Postmark fault.
- **No SPF record is required**, and adding one fixes nothing here. The
  Return-Path CNAME points at `pm.mtasv.net`, which already carries Postmark's
  SPF, so bounces are SPF-aligned to the domain — that is the whole purpose of
  the CNAME. If an SPF record is ever added for other reasons, the mechanism is
  `include:spf.mtasv.net`.
- **DKIM keys are 1024-bit**, so the TXT value fits in a single string and
  Namecheap will not have to split it.

Then verify — Postmark's page has a **Verify** button; it says up to 48 hours
and is usually minutes. Confirm from outside as well, the way the `helpdesk`
record was confirmed rather than assumed:

```bash
dig +short TXT <selector>._domainkey.community-access.org
dig +short CNAME pm-bounces.community-access.org      # -> pm.mtasv.net.
```

Nothing here touches the existing MX records, so no mail behaviour changes at
this step. Sending is now authenticated; nothing is sending yet.

### Step 3 — Point FreeScout's outbound at Postmark

**FreeScout sends from two places, and both need this.** System notifications
(password resets, invitations, alerts to agents) go through the global mail
settings; replies to customers go through the mailbox's own. Configuring only
one of them is the usual cause of "some of our email works".

*Manage → Settings → Mail* — and then again at *Manage → Mailboxes →
`support@community-access.org` → Connection Settings → Sending Emails*:

```
Driver / Mail method:  SMTP
Host:                  smtp.postmarkapp.com
Port:                  587
Encryption:            TLS   (STARTTLS)
Username:              <Server API token>
Password:              <the same Server API token>
From:                  support@community-access.org
```

The token is username *and* password — that is Postmark's documented SMTP
scheme, not a placeholder that got pasted twice by mistake. Ports 25 and 2525
also work if 587 is ever blocked. Check that **SMTP is enabled** on the
transactional stream's settings page; it can be switched off, and the failure
then is an authentication error that reads like a bad token.

It goes in FreeScout's interface rather than in `.env` deliberately, so that
rotating the token never needs a container restart. One consequence worth
knowing, and it is the third trap in this file: FreeScout encrypts stored
mailbox passwords with `APP_KEY`, so if that key is ever regenerated these
credentials become undecryptable and mail stops **silently**. The host's copy of
`.env` is bind-mounted precisely so that cannot happen; do not undo it.

Test in this order:

1. Send FreeScout's test message to `test@blackhole.postmarkapp.com`. It is
   dropped at the far end but appears in Postmark's Activity, which proves
   authentication, TLS and the stream without needing account approval.
2. Once approved, send to a real outside address and read the headers: expect
   `dkim=pass` for `community-access.org` and a Return-Path at
   `pm-bounces.community-access.org`.

Only after that is anybody told the address exists.

### Step 4 — The MX decision, which is the real question

Today `community-access.org` already receives mail, and not through Postmark:

```
community-access.org  MX 10  eforward1.registrar-servers.com
                      MX 10  eforward2.registrar-servers.com
                      MX 10  eforward3.registrar-servers.com
                      MX 15  eforward4.registrar-servers.com
                      MX 20  eforward5.registrar-servers.com
```

That is **Namecheap's free email forwarding**, already switched on for the
domain. Whatever aliases are configured behind it work today and are the thing
at risk. Look at them before choosing: *Domain List → Manage → **Domain** tab →
Redirect Email*.

| | Route A — forward `support@` into Postmark | Route B — give the domain's MX to Postmark |
| --- | --- | --- |
| DNS change | **None** | Replace all five MX records with `inbound.postmarkapp.com`, priority 10 |
| Namecheap *Mail Settings* | stays `Email Forwarding` | becomes `Custom MX` |
| Other addresses at the domain | **Keep working** | **Stop working** — see below |
| What Postmark receives | only what is forwarded | everything addressed to the domain |
| Reversible in | seconds; delete one forwarder | a DNS change and a propagation wait |

**Route B has a consequence that has to be said out loud.** With the domain's
MX at Postmark, *every* address at `community-access.org` reaches the bridge —
and the bridge answers `403` to any recipient outside its allowlist, which is
`support@community-access.org` alone. Postmark documents that 403 **stops
retries**. So mail to `jeff@community-access.org`, or to any alias forwarded
today, would be accepted by Postmark and then dropped: no bounce to the sender,
and nothing in a mailbox anybody reads. That is correct behaviour for a bridge
and a disaster for a domain with other addresses on it.

**Recommended: Route A.** In *Redirect Email*, add one forwarder:

```
support   ->   <your-inbound-hash>@inbound.postmarkapp.com
```

The hash address is on the inbound stream's settings page. Allow about an hour
for a new Namecheap forwarder to become real.

One change makes Route A robust, and it is a single line in
`~/feedback-hub/deploy/helpdesk/.env`:

```
MAILBRIDGE_RECIPIENTS=support@community-access.org,<your-inbound-hash>@inbound.postmarkapp.com
```

Why: the bridge matches on `OriginalRecipient` — the envelope address Postmark
actually delivered to — **together with** the `To`, `Cc` and `Bcc` header
addresses. A forwarded message still carries `To: support@community-access.org`,
so it matches on the header and works without this change. But a message that
reaches support by **Bcc** has the address in no header at all, and its envelope
recipient is the hash address, so it would be refused `403` and lost. Adding the
hash address to the allowlist makes the envelope truthful again on the forwarded
path, and costs nothing else.

Take Route B only if `community-access.org` is to be a Postmark-only mail
domain. If it is, the inbound domain goes on the stream as
`community-access.org`; Postmark requires inbound domains to be unique across
all of Postmark, and typically recommends a dedicated subdomain for exactly the
reason above.

### Step 5 — Configure the inbound stream

*Servers → your server → Default Inbound Stream → Settings.*

1. **Webhook URL.** Run the generator on the box and paste what it prints:

   ```bash
   cd ~/feedback-hub/deploy/helpdesk && ./make-credentials.sh
   ```

   It produces
   `https://<user>:<password>@helpdesk.community-access.org/postmark/inbound`.
   Credentials in the URL is what Postmark supports and documents
   (`https://username:password@example.com/inboundhook`); it travels only over
   TLS, and step 2 of *Next steps* already proved that path answers `401` from
   the bridge's own Basic auth rather than 404 from FreeScout. The script is
   idempotent and refuses to regenerate a live credential, because rotating it
   breaks inbound until Postmark is updated to match — and mail that stops
   arriving is the hardest failure to notice.

2. **Tick "Include raw email content in JSON payload".** Not optional, and the
   single most likely thing to be forgotten. The bridge writes the raw RFC-822
   message out byte for byte — that is how FreeScout keeps threading, duplicate
   detection and bounce handling — and without `RawEmail` in the payload there
   is nothing to write. The bridge answers `5xx` and says so in as many words,
   so Postmark keeps retrying and the mail lands the moment the box is ticked:
   nothing is lost, but nothing arrives until it is.

3. **Route B only:** set the inbound domain to `community-access.org` on the
   same page, and only after the MX record resolves.

What to expect from Postmark afterwards, all of which the bridge was written
against: **200** is the only success; anything else is retried **10 times over
about 10.5 hours**; a **403** stops retries immediately; Postmark waits up to
**2 minutes** for a response, and the payload limit is 50 MB. Spam is scored by
SpamAssassin and passed through as `X-Spam-Status`, `X-Spam-Score` and
`X-Spam-Tests` — the bridge records the verdict and delivers anyway, on purpose.

### Step 6 — Point FreeScout at the local IMAP

The same `make-credentials.sh` output carries this half. *Manage → Mailboxes →
`support@community-access.org` → Connection Settings → Fetching Emails*:

```
Protocol: IMAP      Server: helpdesk-imap      Port: 143
Encryption: none    (the connection never leaves a private Docker network)
Username: freescout-support
Password: <printed by the script>
```

### Step 7 — Prove it end to end, in this order

Each step fails in a different place, which is the point of doing them
separately:

1. `dig +short TXT <selector>._domainkey.community-access.org` and the
   Return-Path CNAME both answer, and Postmark shows the domain verified.
2. FreeScout's test message reaches `test@blackhole.postmarkapp.com` and appears
   in Postmark Activity.
3. From an outside address, email `support@community-access.org`. Then, in
   order: Postmark's **Activity → Inbound** shows it; the bridge logs one write
   (`docker compose logs mailbridge --tail 20`); the Maildir gains exactly one
   file; FreeScout shows a new conversation within one scheduler cycle.
4. Reply from FreeScout. It leaves through Postmark (Activity → Outbound),
   arrives, and the reply **threads** in the original client — that is
   `In-Reply-To` surviving the round trip, and it is the entire reason for
   feeding FreeScout real mail rather than posting to its API.
5. Reply back to that reply, and confirm it lands on the **same** conversation
   rather than opening a second one.
6. Use Postmark's manual retry on the inbound message and confirm the bridge
   answers 200 and writes **nothing** — the duplicate guard, proven again with
   real mail rather than a synthetic POST.

### When it works, say so in three places

- Delete the temporary admin `jeff+hd@jeffbishop.com` and the credential file at
  `C:\Users\jeffbis\helpdesk-temp-login.txt`. "Forgot password" becomes a real
  route back in the moment outbound mail works, which is the only reason that
  temporary account existed.
- Mark step 3 of *Next steps* done, and *Where things stand* with it.
- Step 7 of *Next steps* — moving Report a Bug from a GitHub issue to a support
  conversation — is unblocked from that moment, and it is a change on the server
  only.

### How this was checked, which is not the same as read

Every value above was checked against **this deployment** rather than only
against Postmark's documentation, because the two disagree in the places that
matter and the documentation cannot know what is already on the box:

- `src/feedback_hub/mailbridge.py` in `S:\code\feedback-hub` — the recipient
  allowlist really does default to `support@community-access.org` alone;
  `recipients_of` really does union `OriginalRecipient` with the `To`, `Cc` and
  `Bcc` header addresses, which is what makes the forwarding route work and
  what leaves the Bcc hole; and the `403`-stops-retries, `5xx`-is-retryable
  split is the code's, not an inference from Postmark's docs.
- `deploy/helpdesk/make-credentials.sh` — the webhook URL shape, the IMAP
  username `freescout-support`, and the refusal to regenerate a live credential.
- `deploy/helpdesk/README.md` — the SMTP values already recorded there, and the
  `APP_KEY` trap that makes them fragile.
- **Live DNS**, queried rather than assumed: the five `eforward` MX records on
  `community-access.org` are real and answering today, which is the whole basis
  of step 4. `quillville.org` and `quillforall.org` carry the same forwarding
  MX and no TXT records at all.

The pricing table is the weakest line here — it is a reading of Postmark's
pricing page on 2026-08-26, and the plan names have changed before. Confirm it
at signup.

### The documentation this was written from

- [How do I verify a domain?](https://postmarkapp.com/support/article/1046-how-do-i-verify-a-domain) — DKIM TXT, and the `pm-bounces` → `pm.mtasv.net` Return-Path CNAME
- [How to send from subdomains?](https://postmarkapp.com/support/article/1198-how-to-send-from-subdomains) — verification does **not** cascade to subdomains
- [How do I set up DKIM for Postmark?](https://postmarkapp.com/support/article/1091-how-do-i-set-up-dkim-for-postmark) — 1024-bit keys, up to 48 hours to verify
- [Why is it not required to include Postmark in our own SPF record?](https://postmarkapp.com/support/article/1102-why-is-it-not-required-to-include-postmark-in-our-own-custom-spf-record) — and `include:spf.mtasv.net` if one is ever wanted anyway
- [Send email with SMTP](https://postmarkapp.com/developer/user-guide/send-email-with-smtp) — `smtp.postmarkapp.com`, ports 25/2525/587, token as username *and* password
- [Configure an inbound server](https://postmarkapp.com/developer/user-guide/inbound/configure-an-inbound-server) — the InboundHash address, and Basic auth in the webhook URL
- [Inbound domain forwarding](https://postmarkapp.com/developer/user-guide/inbound/inbound-domain-forwarding) — MX to `inbound.postmarkapp.com` at priority 10, subdomain recommended
- [Inbound webhook](https://postmarkapp.com/developer/webhooks/inbound-webhook) — 200 expected, 403 stops retries, 10 retries over ~10.5 hours, SpamAssassin headers
- [How does the account approval process work?](https://postmarkapp.com/support/article/1084-how-does-the-account-approval-process-work) — under 24 hours, and `test@blackhole.postmarkapp.com`
- [Pricing](https://postmarkapp.com/pricing) — inbound processing starts at Pro
- [Namecheap: free email forwarding](https://www.namecheap.com/support/knowledgebase/article.aspx/308/2214/how-to-set-up-free-email-forwarding/) — *Domain* tab, Redirect Email, up to 100 aliases, about an hour to take effect
- [Namecheap: custom MX records](https://www.namecheap.com/support/knowledgebase/article.aspx/322/2237/how-can-i-set-up-mx-records-required-for-mail-service/) — *Advanced DNS*, Mail Settings → Custom MX

---

## Where things stand

| Route | Account needed? | Status |
| --- | --- | --- |
| Quill Radio, Community menu, Suggest a Station or Podcast | **No** | Working. Files an issue with the bundled issues-only token. |
| `quillforall.org/picks/suggest/` | **No** | **Fixed 2026-08-26.** Posts to the submission server, which files the issue. |
| `lp.csedesigns.com/submit/picks` | — | **Live.** feedback-hub 1.2.0, one container beside the four apps already on the box. |
| Help desk, `helpdesk.community-access.org` | — | **Reachable and serving, 2026-08-26.** DNS live, Caddy block in, Let's Encrypt certificate issued to 2026-11-24. Configurable now; waiting only on Postmark to carry mail. |
| Inbound mail, Postmark to FreeScout | — | **Built and proven.** Waiting only on Postmark credentials to carry real mail — and on a **Pro** plan, because inbound processing is not on the free or Basic tiers. Setup is *Postmark, step by step*, above. |
| `support@community-access.org` | — | **Not receiving yet.** The domain's MX is Namecheap forwarding today; the recommendation is to leave it there and forward `support@` into Postmark, rather than move the MX. Step 4 of that section. |
| Report a Bug, every app | **No** | **Routed through the server**, so a build needs no token. Still files a GitHub issue until Postmark lands. |
| `workers/picks-submit.js` (Cloudflare) | — | **Deleted.** Two ways to do one thing is one too many. |
| Public support form on the web | **No** | **Planned, step 13.** A second renderer of the schema the wx dialog already uses; served by feedback-hub itself, so same-origin and no CORS. |
| `quillville.org` | — | **Parked, step 12.** Owned, pointing at Namecheap's holding page, nothing depends on it. |
| `quillville.org/support` | **No** | **Planned, step 14.** The address to publish once the form and the brand site exist. |
| `helpdesk.quillville.org` | — | **Planned, step 14.** One record and one `redir` to `helpdesk.community-access.org`. Redirect, never proxy. |

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
