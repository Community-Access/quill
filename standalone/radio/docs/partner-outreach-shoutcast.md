# SHOUTcast API partner request -- process notes and submission

Prepared 2026-08-12 for the directory-expansion workstream in `planning.md`
(item 1b: SHOUTcast and Icecast webcasters).

> **Status: sent 2026-08-12.** Awaiting a reply and a `dev_id`. The text below is
> the submission of record -- keep it in step with anything that changes about
> how Quill Radio would use the directory, since it is what we have told them.
>
> Two commitments were made in this email that are ours to honour if access is
> granted: SHOUTcast results carry a visible **and spoken** "SHOUTcast" source
> label, and if SHOUTcast asks that stations from their directory not be
> recorded, we enforce that **per source** rather than app-wide. Neither is built
> yet -- there is nothing to build until there is a key -- but both are promises,
> not aspirations, and belong in the implementation ticket.

## How the submission actually works

**There is no web form.** Both SHOUTcast pages that describe developer access say
the same thing, in the same words:

> "If you would like to become a SHOUTcast API Partner, please send us an email
> with details about your company and your proposed application."

- Developer/API page: <https://directory.shoutcast.com/Developer>
- Become a partner: <https://www.shoutcast.com/partners> ("We'll get back to you asap.")

So the deliverable is an **email**, not a set of form fields. The two things they
explicitly ask for are *details about your company* and *your proposed
application*; the draft below covers both and then answers the questions a
directory operator will ask next whether or not they were requested.

### Two things to know before sending

1. **The developer wiki they link to is offline.** Both
   `wiki.shoutcast.com` and the `wiki.winamp.com` mirror fail to resolve
   (`ENOTFOUND`) as of 2026-08-12, so the documented endpoint reference,
   rate limits, and any published attribution rules are currently unreadable.
   The draft therefore *asks* for the current terms rather than asserting we
   have met them.
2. **A `dev_id` is required for every API call**, and the Terms of Use
   (<https://directory.shoutcast.com/TermsOfUse>) separately prohibit
   "robots, spiders, or offline readers" against the site and its content. That
   is precisely why the partner key matters: it is the thing that authorizes the
   access the general terms otherwise forbid. Do not prototype against the
   directory without it.

### Fill these in before sending

| Field | Value |
| --- | --- |
| From address | *(confirm which address you want the partnership tied to)* |
| Organisation | Community Access / Blind Information Technology Solutions (BITS) |
| Reply-to for technical follow-up | *(same, or a maintainer alias)* |

## Draft email

> **Subject:** SHOUTcast API Partner request -- Quill Radio, a free accessible radio app for blind listeners

Hello,

I would like to request SHOUTcast API Partner access for **Quill Radio**, a free,
open-source internet radio application for Windows built specifically for blind
and low-vision listeners.

**About us.** Quill Radio is published by Community Access and developed by Blind
Information Technology Solutions (BITS). It is released under the MIT licence at
<https://github.com/Community-Access/quill-radio>. It is free, carries no
advertising, has no subscription or in-app purchase, and is not monetised in any
way -- it exists because mainstream radio apps are frequently unusable with a
screen reader.

**About the application.** Quill Radio is a desktop app whose entire interface is
designed for keyboard and screen-reader use (NVDA, JAWS, and Narrator). Every
list, dialog, and control is reachable and announced; there is no mouse-only
surface anywhere in it. Version 2.2.0 is current.

Finding a station is the part of internet radio that is hardest without sight, so
the app already searches several directories at once and merges them into one
keyboard-navigable result list: Radio Browser, SomaFM, iHeart, TuneIn, the NOAA
Weather Radio transmitter list, and a curated directory of radio reading services
for people with print disabilities. **Every result is labelled with the directory
it came from**, both visually and in what the screen reader announces, so a
listener always knows the source of what they are about to play.

**What we would like to do with the SHOUTcast API.** SHOUTcast is the obvious gap
in that list. The established aggregators skew toward large commercial
broadcasters, and the independent, community, hobby, and specialist stations our
users ask for most are exactly the long tail SHOUTcast carries. Concretely we
would use the API to:

- Search stations by name, genre, and keyword.
- Browse by genre.
- Show bitrate, codec, and listener metadata so a listener can choose a stream
  that suits their connection.
- Play the station by connecting **directly to the broadcaster's own stream
  URL**.

**How we would handle your data and your streams.**

- **No proxying or re-hosting.** Audio is played by connecting the listener's own
  machine directly to the broadcaster's stream. We never relay, mirror, or
  re-serve anyone's audio.
- **Attribution.** SHOUTcast results would be labelled "SHOUTcast" in the results
  list and in the spoken announcement, exactly as the existing sources are. If
  you have specific branding, logo, or wording requirements, tell us and we will
  implement them as specified.
- **Caching.** We cache directory responses briefly to keep the interface
  responsive for screen-reader navigation, and to avoid issuing a request per
  keystroke while someone types a search. We will cache for whatever period your
  terms require.
- **Modest, human-driven volume.** Requests are made in response to a person
  searching or browsing. There is no background crawling, no bulk export, and no
  attempt to mirror the directory.
- **No scraping.** We have read your Terms of Use and will not use automated
  access against the website. API access under a partner key is the only route we
  intend to use.

**Two things I want to raise directly rather than leave you to discover.**

1. **Quill Radio can record a stream.** Users can record what they are listening
   to, and schedule a recording in advance, which is a genuinely important
   accessibility feature -- it is how a blind listener time-shifts a programme
   they cannot otherwise catch. Recordings are made locally on the listener's own
   machine, for their own use, and are never uploaded, shared, or redistributed
   by us. If SHOUTcast requires that stations sourced from your directory be
   excluded from recording, we can enforce that per-source; I would rather agree
   the rule with you now than have it become a surprise later.
2. **Key handling in a distributed desktop app.** Quill Radio is installed on end
   users' machines, so any `dev_id` we ship can in principle be extracted from
   the package. We will follow whatever practice you prefer -- an application-
   specific key, a proxied arrangement, or key rotation. Please tell us what you
   expect here.

**What we need from you.** A `dev_id` for the Directory API, the current
developer documentation, and your attribution and reporting requirements. I
should mention that the developer wiki linked from
<https://directory.shoutcast.com/Developer> (`wiki.shoutcast.com`) does not
currently resolve, so I have not been able to read the published endpoint
reference or terms -- a current copy would be very welcome.

I am happy to provide a build of the application, a demonstration, or anything
else that would help you evaluate the request.

Thank you for your time.

*(name)*
Community Access / Blind Information Technology Solutions (BITS)
<https://github.com/Community-Access/quill-radio>

## If there is no reply

The partners page promises a reply "asap" but the address is not published, so
the request may need routing through the general support path
(<https://www.shoutcast.com/support>) or the Winamp/SHOUTcast forums, where staff
have historically answered `dev_id` requests. Icecast (`planning.md` item 1b) has
no such gate and can proceed independently -- do not let the SHOUTcast reply
block the rest of the directory-expansion workstream.
