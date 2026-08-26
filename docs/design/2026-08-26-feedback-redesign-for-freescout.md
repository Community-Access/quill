# Feedback, redesigned for FreeScout — and the simple form survives

Written 2026-08-26, against
*Community Access Support, FreeScout, Postmark, and GitHub Integration Plan —
Free-Software Baseline* (v4).

**The short version.** The plan makes one rule that QUILL currently breaks in
every app: *FreeScout is authoritative for customer communication, GitHub is
authoritative for engineering work.* Today **Report a Bug writes the customer's
own words straight into a public GitHub repository**, using a token shipped
inside every installer, and gives the reporter no way to be answered. That has
to change.

**What does not change is the form.** Same dialog, same fields, same one
button. A person reporting a problem should not be able to tell that anything
was rearranged behind it. Everything below is about where the submission goes
and what the app has to carry — not about what the user does.

---

## 1. What the plan requires

Five things bear directly on QUILL:

1. **`support@community-access.org` is the public support address**, handled in
   FreeScout, delivered by Postmark. Each agent has their own login; nobody
   shares a password.
2. **A GitHub issue raised from support is a *sanitized engineering summary*
   written by a human agent** — never a pasted transcript.
3. **The privacy rule is mandatory when the repository is public.** Do not copy
   a customer's email address, phone number, transcript, signature, private
   attachments, credentials or account identifiers into GitHub.
   `Community-Access/quill` **is public.**
4. **One repository, seven products, distinguished by labels**:
   `product:quill`, `product:weather`, `product:radio`, `product:cast`,
   `product:social`, `product:beacon`, `product:audio-studio`, plus
   `type:bug` / `type:feature` / `type:accessibility` / `type:documentation`
   and `source:support`.
5. **FreeScout and GitHub own their own statuses.** Closing an issue does not
   close a ticket; support closes the ticket after verifying the outcome with
   the customer.

---

## 2. What QUILL does today, measured against that

| Path | Where it lands | Verdict |
| --- | --- | --- |
| **Report a Bug** (`AppShellFrame.report_app_bug` → `feedback_hub.wx_dialog`) | A GitHub issue, filed with the bundled token | **Breaks the privacy rule and rule 2.** Raw user text into a public repo, no reply channel. |
| **Crash reporter** (`core/diagnostics.py`, fingerprint dedup) | Same | Same, plus it can carry paths, versions and environment detail. |
| **Report Bad Station** (Radio) | Same, prefilled | Same. |
| **Suggest a Station or Podcast** (in-app + web form) | A `pick:suggestion` issue | **Correct as it is.** See §5. |
| **Quillin Hub submit** (`ui/quillin_hub_submit.py`) | `https://hub.quillforall.org` — **does not resolve** | Broken today, independently of this plan. |

Three separate problems, and they are worth naming apart because they have
different fixes:

**(a) The privacy problem.** The repository is public. Somebody describing a
screen-reader failure may name their employer, their assistive technology
configuration, or a document they were working on. That is exactly the material
the plan says to keep in FreeScout. Today it is published, permanently and
searchably, the moment they press Submit.

**(b) The no-answer problem.** A GitHub issue is not a conversation a person
without a GitHub account can join. We built an entire submission server this
week so that nobody needs an account to *suggest a station* — and meanwhile the
person reporting a **bug** is filed into a system where they cannot read the
reply. Fixing the smaller case and leaving the larger one is not a defensible
place to stop.

**(c) The credential problem.** `quill/_feedback_token.py` bakes an
issues-scoped token into every build. Anyone who unzips an installer has it.
Scope limits the damage to issue spam, which is why it was acceptable — but it
stops being necessary the moment submissions go through a server.

---

## 3. The redesign

```
                                                   ┌─ conversation, replies,
Report a Bug        ─┐                             │  attachments, history
Crash report        ─┤                             │
Report Bad Station  ─┼──→ submission server ──→ Postmark ──→ FreeScout ──┤
Feedback / question ─┘    (holds the only            support@             │
                           credential)                                    │
                                                   agent triages, and only
                                                   then, if engineering is
                                                   needed and after sanitising:
                                                            │
                                                            v
                                              GitHub issue: product:*, type:*,
                                                     source:support
```

Three moving parts, two of which already exist.

### 3.1 The app stops filing issues and starts filing tickets

`feedback_hub`'s wx dialog keeps its shape exactly. What changes is the
transport underneath it: instead of `create_issue()` against the GitHub API, it
POSTs to the submission server, which relays to Postmark as a message to
`support@community-access.org`.

The app therefore **carries no credential at all**. `quill/_feedback_token.py`
and the build step that generates it can go, along with the release check that
fails when the token is missing.

Why the server rather than the user's own mail client: a `mailto:` handoff
fails webmail-only visitors and silently loses everybody whose machine has no
handler registered — and a desktop app must not hold SMTP credentials, which is
the same objection as the GitHub token wearing different clothes.

### 3.2 The submission server grows one endpoint

`feedback_hub.server` already runs on `lp.csedesigns.com` holding a credential
and refusing malformed input. `POST /submit/support` is the same shape as
`/submit/picks`: validate, relay, answer in plain English.

This is precisely the *"same process, more endpoints"* step that `magic.md`
deferred on 2026-08-26 — deliberately, so the first deployment was not also
the riskiest. It has now been up and proven, and the FreeScout plan supplies
the reason to take the next step.

What it must do differently from the picks endpoint:

- **Relay to Postmark**, not to GitHub. Different credential, different
  failure modes, same "tell the visitor the truth without showing them the
  provider's error" rule.
- **Set the reply address to whatever the reporter gave**, so FreeScout
  threads the conversation to a real person. This is the field that makes the
  difference between a report and a conversation.
- **Make the email address optional and say so.** Somebody who does not want
  to give one should still be able to report a bug; they simply will not get
  an answer, and the form should say that in those words rather than making
  the field required.
- **Carry the product** as a header or a first line, so the agent's triage step
  (§1.4) starts from the app's own knowledge rather than from guesswork. The
  app already knows it is "Quill Radio 1.0.0".

### 3.3 Triage and escalation stay human

Nothing automatic writes to GitHub. An agent reads the conversation, decides
whether engineering work is needed, searches for an existing issue, and only
then writes a sanitized summary with the labels from §1.4. The plan is explicit
that the AI issue-drafting features stay off for the initial deployment, and
that matches: the sanitising step is the point, and it is the step a human is
there to do.

---

## 4. What this costs, honestly

**Crash fingerprinting becomes less useful, and that is a real loss.**
feedback-hub 1.1.0 deduplicates crashes so the second person to hit a bug lands
on the first person's issue. Routed through FreeScout, two people hitting one
crash are two conversations — correctly, because they are two customer
relationships — and the deduplication has to happen at the escalation step
instead, by an agent searching before creating. The plan says to do exactly
that ("Search before create"), and it explicitly wants the conversations kept
separate. So the capability is not wasted; it moves.

A middle path worth considering rather than deciding here: keep the fingerprint
in the relayed message as a header. FreeScout cannot act on it in Phase 1
without the paid modules, but an agent can search for it, and it costs nothing
to include.

**Somebody has to read the queue.** Today a bug report costs nobody any time
until a maintainer looks at the issue list. A ticket that nobody answers is
worse than an issue nobody reads, because the reporter was told to expect a
reply. This is the genuine new obligation in the plan and it should be accepted
deliberately, not discovered.

**Report a Bug stops working offline-ish.** It already required the network.
No change, but worth stating.

---

## 5. What deliberately does *not* change

**Community Picks suggestions keep going straight to GitHub.** A suggested
radio station is not a support conversation:

- there is no customer relationship to preserve — nobody is waiting for an
  answer beyond "it was added";
- there is nothing personal in it. A station name, a stream address and a
  sentence of description are the whole payload, and the *point* is that it
  becomes public;
- it is already reviewed on a purpose-built accessible review page and consumed
  by `picks-build.yml`. Routing it through a mailbox would mean a human
  retyping structured data that arrived structured.

The plan governs **support**. This is content contribution, and the two should
not be conflated because they happen to both produce issues.

**And the form stays simple.** Both forms — the wx dialog and the web page —
keep their current fields and their current single button. The web suggestion
form shipped today with a full accessibility review applied and it is not being
reopened.

---

## 6. The open question I am not answering here

**Which domain?**

The plan is written for `community-access.org`. QUILL currently serves the
catalogue from `quillforall.org`, the suggestion form from
`quillforall.org/picks/suggest/`, and the submission server's CORS allowlist
names `https://quillforall.org`. The dead Quillin Hub constant points at
`hub.quillforall.org`.

Three readings, and they lead to different work:

1. `community-access.org` is the *organisation's* domain and `quillforall.org`
   stays the *product* domain. Nothing here moves; only support email is new.
2. `quillforall.org` is being retired in favour of `community-access.org`. Then
   the catalogue URL, the signature URL, the CORS allowlist, the form, and the
   bundled fallback all move — and the catalogue URL is baked into shipped
   builds, so old installs must keep resolving.
3. Both, with redirects.

This is a decision, not a detail, and guessing it wrong is expensive in exactly
the way a URL baked into released binaries is expensive. Everything in §3 is
written to be configurable by environment variable so that whichever answer
lands, it is a setting rather than a rebuild.

---

## 7. Suggested order

Small, and each step independently useful:

1. **Create the labels** — the seven `product:*`, the four `type:*`, and
   `source:support`. Costs nothing, blocks nothing, and makes the escalation
   step possible the day FreeScout is up. Can be done now.
2. **`POST /submit/support`** in feedback-hub, behind Postmark, with tests in
   the shape `/submit/picks` already has.
3. **Point `feedback_hub.wx_dialog` at it**, keeping the dialog identical.
4. **Delete the bundled token** and the build step that generates it, once (3)
   is proven in a release.
5. **Fix or retire `hub.quillforall.org`** — unrelated to the plan, but it is
   the third broken submission path in the same subsystem and should not be
   left to be discovered again.
6. **Decide the domain question** (§6) before anything in (2) or (3) ships with
   a hostname in it.

Steps 2–4 are the migration `magic.md` already listed as "the next one, once
this has been up a while". This document is the reason to schedule it.
