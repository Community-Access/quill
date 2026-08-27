# radio.md — a station that runs itself

Working notes, started 2026-08-26. **Plan only. Nothing has been installed.**

The ask: put Icecast on `lp.csedesigns.com`, serve it at
`radio.bits-acb.org`, and have an automated process — with AI in it — keep the
station configured, programmed and playing.

Written after a **read-only survey of the box**, so the numbers below are
measured rather than assumed. No configuration was changed and no container was
touched.

---

## The one rule everything else follows from

**The AI writes the schedule. The AI never touches the stream.**

A radio station is judged on one thing: whether sound comes out. Every other
quality is a rounding error next to silence. So the model must sit where its
failure is invisible — choosing what plays *next hour*, not what plays *this
second*. If it is slow, rate-limited, down, hallucinating or simply wrong, the
station keeps playing yesterday's schedule and nobody hears a thing.

The corollary, and the rule I would write in stone:

> **Nothing reaches the stream that has not been rendered to a file on disk
> first.**

That single constraint buys review, retry, caching, a fallback, and a recording
of exactly what went out — and it removes the model from the realtime path
entirely. Every design below is downstream of it.

---

## What is actually on the box

Surveyed 2026-08-26, read-only.

| | |
| --- | --- |
| Capacity | 10 vCPU, 12 GB RAM (**6.2 GB available**), **102 GB free** on `/` |
| Already installed on the host | `ffmpeg`, `ffprobe` |
| **Not** installed | `icecast2`, `liquidsoap` |
| Containers running | 17 — helpdesk (5), feedback-hub (1), Ask BITS (3), the `web` stack (7), `adp-app` (1) |
| Edge | Caddy 2-alpine terminates TLS for every hostname; bind-mounts `~/app/web/www` to `/srv/www` |
| System cron | Two jobs only: a nightly feedback backup and a weekly disk check |
| The real scheduler | **Hermes Agent**, 17 jobs, all `ok` — see its own section below |

Four things in that survey matter more than the rest:

1. **`glow.bits-acb.org` already resolves to `107.175.91.158`.** A
   `bits-acb.org` subdomain already points at this box, so the DNS ask for
   `radio.` is a known quantity on a screen somebody has already used.
2. **`bits-acb.org` itself is on WordPress.com** (`192.0.78.184`,
   `192.0.78.194`), so the zone is managed there rather than at Namecheap
   like `community-access.org`. Different screen, same one-record change.
   `radio.bits-acb.org` does not resolve today.
3. **There is already audio on this box.** The GGG podcast is served from its
   own Caddy container at `lp.csedesigns.com/ggg/feed.xml`. A station is not
   the first audio here, and that feed is a content source that already exists.
4. **Ask BITS already has the right database tables and does not use them.**
   Its README says entities for *weeks, episodes, attachments and AI drafts*
   exist in the schema and nothing writes to them, with "the show archive
   (weeks, episode audio, synchronised transcripts)" and "the AI drafting
   pipeline" listed as not built. A station is the missing consumer of exactly
   those tables. This is the strongest argument that the two projects are one
   project.

---

## Three processes, not one

The most common way this goes wrong is thinking Icecast *is* the station. It is
not. It is a socket multiplexer: it takes one incoming stream and fans it out to
listeners. **Icecast with no source client plays nothing**, and an empty mount
answers 404, which looks exactly like a broken install.

```
  library on disk ─┐
  pre-rendered     ├─→  source client  ──→  Icecast  ──→  Caddy (TLS)  ──→  listeners
  speech files    ─┘    (Liquidsoap)        one mount        radio.bits-acb.org
                              ^
                              │ reads a playlist file
                              │
                        the programmer  ←── AI, on a schedule, off the audio path
```

**1. Icecast** — the streaming server. One small container, no published host
ports, on the private network, reached by Caddy by container name. This is the
same shape as `helpdesk-app` and needs no new thinking.

**2. The source client** — the thing that actually plays content and sends one
continuous stream. **Liquidsoap** is the standard answer and the right one here,
because of exactly one feature: its **fallback chain**. You declare an ordered
list of sources and it plays the first one that is available:

```
live input  →  today's scheduled playlist  →  a safety rotation  →  a tone
```

Each layer covers the failure of the one above it. That chain is what makes the
"AI never touches the stream" rule enforceable rather than aspirational, and it
is why the answer is not a shell script looping `ffmpeg`.

**3. The programmer** — what decides *what* plays. A cron job that writes a
playlist file for tomorrow. This is where AI belongs, and the only place it
belongs.

---

## Icecast behind Caddy is not an ordinary reverse proxy

Five differences, each of which has bitten somebody:

- **These are long-lived connections, not requests.** A listener holds one
  connection for hours. Caddy handles it, but the **access log writes one line
  per disconnect**, and a station with real listeners produces a log that
  dwarfs `helpdesk-access.log`. Give it its own log file or turn logging off
  for that host, decided before launch rather than after the disk alert.
- **No buffering.** Caddy streams responses with no `Content-Length` by
  default, so this generally just works — but it must be **verified with a
  real audio client**, not `curl -I`. A buffered stream sounds like it works
  for ten seconds and then stutters forever.
- **Icecast's admin endpoints must not be reachable.** `/admin/*` and
  `/status-json.xsl` are the interesting ones. Block them at the Caddy layer
  by path, not merely behind Icecast's own password — the same "route past the
  application" discipline the `/postmark/inbound` matcher already uses in the
  helpdesk block.
- **The certificate rule from `magic.md` step 2 applies unchanged.** DNS must
  resolve *before* the site block is added. Five failed validations per
  hostname per hour is the budget, and it is spent by a block that loads before
  the record does.
- **Restarting the source disconnects every listener.** Config changes need a
  maintenance window or Liquidsoap's own reload semantics — the same discipline
  as `caddy reload`, never `restart`.

---

## Bandwidth: the host, the limits, and the one control that matters

**Bandwidth, not CPU.** Icecast's own cost is negligible and one Liquidsoap
encode is a fraction of a core; this box has ten. The bill is listeners, and the
listener bill is paid to RackNerd.

### The host

| | |
| --- | --- |
| Provider | **RackNerd** (KVM VPS) |
| Datacentre | Dallas, Texas — `AS36352`, ColoCrossing/HostPapa range |
| Reverse DNS | `mail.mountainsyeuan.com` — a stale generic PTR, not ours |
| OS | Ubuntu 24.04.4 LTS, KVM, hostname `bishoplink` |
| Port speed | 1 Gbps (RackNerd's standard for KVM plans) |

### RackNerd's bandwidth policy, as documented

Three details, and the first one is the important one:

1. **Exceeding the allowance powers the VPS off.** Not throttling, not an
   overage invoice — RackNerd's stated behaviour is that at 100% utilisation
   the VPS is *turned off until the meter resets on the 1st*. Warning emails
   are sent as the limit approaches.
2. **Inbound is counted as well as outbound**, and the meter resets on the 1st
   of each month, California time.
3. **Extra bandwidth is bought a la carte at $7/year per 1 TB of monthly
   transfer**, by opening a sales ticket. There is no automatic overage
   purchase — it must be arranged in advance.

Provenance, stated honestly: (1) and (3) come from an official RackNerd reply on
LowEndTalk and RackNerd's own blog, not from a formal SLA page. Worth confirming
in a ticket before the station carries real listeners, because the whole risk
model below rests on it.

### What that means here, and it is severe

**This VPS is not just the radio station.** Powering it off takes down the help
desk, its database, the inbound mail bridge, the submission server, Ask BITS,
GLOW, `letitglow.app` and `csedesigns.com` — until the 1st of the next month.
A bandwidth overage is therefore not a radio outage. It is a **total outage of
everything this project runs**, with a fixed, non-negotiable duration that can
be as long as four weeks.

That single fact should drive every decision in this section. It is also the
strongest argument for the mitigation at the end.

### The measured baseline

From the interface counters on `eth0` over 4.14 days of uptime:

| | |
| --- | --- |
| Received | 1.26 GB |
| Transmitted | 0.53 GB |
| Total | 1.80 GB, about **434 MB/day** |
| Extrapolated | roughly **13 GB per 30 days** |

Everything currently on this box — five websites, a help desk, a Q&A site, two
MCP servers, a podcast feed — uses about 13 GB a month. Whatever the allowance
turns out to be, essentially all of it is available for radio.

Note that Liquidsoap talking to Icecast costs nothing: both are containers on
the private network, so the source stream never crosses `eth0`. Only listeners
count.

### The cost per listener

Sustained, 24/7. A connected listener costs the same asleep as awake — this is
the number people get wrong, because a stream is not a download that ends.

| Bitrate | Per listener per month | Max sustained listeners at 3 TB | at 6 TB | at 12 TB |
| --- | --- | --- | --- | --- |
| 32 kbps | 10.4 GB | 289 | 578 | 1,157 |
| 48 kbps | 15.6 GB | 192 | 385 | 771 |
| 64 kbps | 20.7 GB | 144 | 289 | 578 |
| 96 kbps | 31.1 GB | 96 | 192 | 385 |
| 128 kbps | 41.5 GB | 72 | 144 | 289 |

Those are ceilings with nothing left over. Plan against **half** of them.

### What is still unknown, and exactly where to read it

RackNerd's published KVM range tops out around 12 GB RAM / 7 vCore / 300 GB /
**6 TB per month**. This box is 10 vCPU / 12 GB / 144 GB, which matches no
standard plan — so it is a promotional or custom configuration and **its
allowance cannot be inferred from the public plan table**. It is also not
readable from inside the VM: the counters above are since boot, and the
provider's meter lives in the panel.

**Jeff, this is the one number I need from you**: sign in at `my.racknerd.com`,
open the VPS under Services, and the bandwidth meter shows *used of allowance*
for the current month. The original order email lists the same figure. It is
almost certainly between 3 TB and 12 TB, and the table above covers that whole
range, so the plan does not change shape whatever it says — only the ceiling
moves.

### The 64 kbps question, and the 100-listener case

Proposed 2026-08-26: cap the stream at 64 kbps to protect bandwidth. **The
answer is yes, but not for the reason given** — and the reason matters, because
it changes what else you should do.

**The 100-listener case, worked.** One hundred people listening *concurrently,
around the clock, all month* — not a hundred listeners a day, a hundred
connections open at every moment including 4am:

| | |
| --- | --- |
| Sustained rate | **6.4 Mbps** out, continuous |
| Monthly transfer | **2.09 TB**, including the 13 GB everything else uses |
| Against a 3 TB allowance | **70%** — survivable, uncomfortable, no room for a spike |
| Against 6 TB | **35%** — comfortable |
| Against 12 TB | **17%** — trivial |

So the honest answer to "what if we had 100 people listening around the clock"
is: **that is fine, and at 6 TB it is not even close.** It is also a genuinely
large community talk station — a hundred simultaneous listeners at four in the
morning is a real achievement, not a base case.

**But the bitrate is not the money lever.** Dropping 64 → 48 kbps at 100
concurrent saves 518 GB a month. At RackNerd's a-la-carte rate of $7/year per
TB/month, that saving is worth **$3.63 a year**. Trading audio quality for four
dollars is a bad trade, and it is the kind of trade that gets made by accident
when the bitrate is treated as the safety control.

**The client cap is the safety control.** It is the only thing here that turns
an unbounded risk into arithmetic:

> bitrate × client cap × 30 days = a number you can guarantee, and it cannot be
> exceeded no matter how popular, how linked-to, or how badly scraped the
> station gets.

At 64 kbps, each listener slot costs 20.7 GB a month. So the cap follows
directly from the allowance, spending at most 60% of it on radio:

| Allowance | Budget at 60% | Client cap at 64 kbps |
| --- | --- | --- |
| 3 TB | 1.8 TB | **~85** |
| 6 TB | 3.6 TB | **~170** |
| 12 TB | 7.2 TB | **~345** |

That is the number to put in Icecast's `<clients>`, and it is why reading the
allowance out of the panel is step 0 rather than a detail.

### The recommendation

**64 kbps mono MP3, one public mount, capped from the allowance.**

- **64 rather than 48** because the saving is worth less than the quality, and
  MP3 is not a strong codec at low rates — 48 starts showing artifacts on
  sibilance and under any music bed, and speech clarity is the entire product
  for this audience.
- **Mono, explicitly.** 64 kbps *stereo* MP3 for speech sounds worse than 64
  mono and costs exactly the same. This is the one free win available.
- **MP3 rather than HE-AAC or Opus** for the public mount, because universal
  client support beats efficiency when the audience includes old phones, older
  screen readers and hardware radios. An Opus mount at 32 kbps can be added
  later for the QUILL apps, whose mpv engine handles it natively, at a third of
  the bandwidth and better quality — but as a second mount, never the only one.
- **Buy the headroom rather than shaving the bitrate.** $7/year per TB is
  cheaper than every alternative, including the alternative of being wrong.

Two things the steady-state arithmetic above does not capture:

1. **Reconnects cost extra.** Icecast's burst-on-connect sends a chunk of
   buffered audio the moment a client attaches, so a listener on a flaky mobile
   connection reconnecting every few minutes costs meaningfully more than their
   bitrate implies. Keep `burst-size` modest and do not treat the table as an
   exact bill.
2. **Concurrency is not audience.** A hundred *concurrent* is the pessimistic
   planning ceiling. A station that peaks at 100 and averages 25 uses about
   530 GB a month — a quarter of the figure above. Plan the cap against the
   peak, and expect the invoice to reflect the average.

**The spike is the risk** — a link from ACB, a conference mention, an event, or
a badly-behaved scraper holding connections open. Which is why the single most
important control in this entire document is:

> **Set Icecast's per-mount client limit, and set it from the bandwidth
> allowance rather than from optimism.**

`<clients>` in the mount configuration caps concurrent listeners. When it is
reached, new listeners are refused and existing ones keep listening. That turns
a runaway into "the station was busy" — an annoyance — instead of the entire
server being powered off until the 1st, which is a catastrophe. Compute the cap
from the allowance, leave 40% headroom, and revisit it when the allowance
changes.

Three supporting measures, in order of value:

1. **Buy headroom in advance.** At $7/year per 1 TB/month, an extra 2 TB costs
   $14 a year. Against the cost of every service on the box being dark for
   three weeks, this is the cheapest insurance available anywhere in this
   project.
2. **Alert at 60% and 80% of the allowance.** Install `vnstat` (not currently
   present) and add a `no_agent` Hermes job in exactly the shape
   `memory-alert` and `disk-space-watchdog` already have — 9,106 and 2,275
   clean runs between them. This is the highest-value single job in the whole
   plan, because it is the one that prevents the outage described above, and
   the mechanism already exists and is proven.
3. **One mount to start: 64 kbps mono MP3.** Universal support, good speech
   quality, and a predictable bill once the client cap is set. A 32 kbps Opus
   mount for the QUILL apps can follow later. See the worked case below for why
   64 rather than 48, and why the cap — not the bitrate — is the control that
   matters.

---

## Where the AI actually goes

Three jobs, in increasing order of risk. Ship them in this order, and do not
start the next one until the previous has run unattended for a week.

### 1. Programming — low risk, most of the value

Pick tomorrow's schedule from the library. Apply the rules a human programmer
would: nothing repeats within N hours, day-parting (news in the morning, longer
features at night), a station ID at the top of each hour, a hard cap on how much
of one series runs back to back.

A cron job, one model call, a playlist file written to disk. If the call fails,
**the file from yesterday is still there and still plays.** That is the whole
safety story, and it is why this job is first.

Start it **deterministic** — a plain weighted shuffle with the same rules in
Python, no model at all. Run that for a week. Then let the model propose a
schedule and diff it against what the deterministic one would have chosen. You
learn what the model is adding before you depend on it.

### 2. Continuity — medium risk, and QUILL already owns the hard part

Short spoken links: station identification, "coming up next", time checks,
weather. Generated as text, rendered to audio **ahead of time, to files**, and
scheduled like any other item.

The speech stack is not new work. QUILL already ships Kokoro, Piper, eSpeak and
SAPI voices with a catalogue in `quill/core/voice_catalog.py`, the box already
carries a `speech-models` volume and a DAISY pipeline container, and Quill Audio
Studio already exists for editing what comes out. The station is a new consumer
of a pipeline this project has already built and shipped.

Pick **one voice and keep it**. A station's voice is its identity, and a
listener who has learned one synthetic voice is served badly by a plan that
changes it every release.

### 3. A synthetic presenter — high risk, and where it becomes a product

A host that reads news, the weather, listener questions from Ask BITS, or
segment introductions between items. This is the difference between a jukebox
and a station, and it is where the failure modes are real:

- **A hallucinated fact read aloud in a confident voice is worse than a typo**,
  because there is no visual cue that it is a machine and nothing to re-read.
- **Names and acronyms get mispronounced** — and this audience's names include
  ACB, BITS, NVDA, JAWS, brand names and the names of community members.
- **Stale content sounds authoritative.** "This morning's weather" from a
  cached file at 6pm.

The mitigations are all the same shape: every spoken word derives from a source
document rather than from the model's memory, the templates constrain what can
be said, a pronunciation dictionary is maintained by hand, and **every generated
file is kept** so a person can hear what actually went out. That last one is
non-negotiable — a station that cannot answer "what did it say at 3am?" cannot
be corrected.

---

## The bot: Hermes — and it is a better fit than anything I would have proposed

Answered 2026-08-26: **Hermes Agent**, from Nous Research, v0.20.5, installed at
`~/.hermes` on `lp.csedesigns.com` and running right now. My earlier guess (Ask
BITS) was wrong, and wrong in a useful direction — Ask BITS is a *content
source*; Hermes is an *operator*.

It is not a toy, and it is not new here. It has been running since May.

| | |
| --- | --- |
| Version | Hermes Agent v0.20.5 (2026.8.19), MIT, `hermes-agent.nousresearch.com` |
| Running | `hermes gateway run` since 22 Aug, plus a dashboard TUI process |
| Scheduler | **17 cron jobs, every one reporting `ok`** |
| Track record | `docker-watchdog` has completed **27,320 runs**; `memory-alert` 9,106; `disk-space-watchdog` 2,275 |
| Skills | 24 categories installed, including `devops`, `media`, `creative`, `autonomous-ai-agents` |
| Reach | One gateway process serving Telegram, Discord, Slack, WhatsApp, Signal and CLI; MCP client (`agentmail-mcp` attached) |

### Why this changes the plan for the better

**Hermes already draws the exact line this document opened with.** Its cron jobs
carry a `no_agent` flag, and the box is already running both kinds:

| Kind | Examples on this box | Runs |
| --- | --- | --- |
| `no_agent: true` — a plain script, no model in the loop | `docker-watchdog`, `memory-alert`, `disk-space-watchdog`, `ssl-cert-monitor`, `volume-backup` | 27,320 / 9,106 / 2,275 / 95 / 14 |
| agent-driven — a natural-language prompt, a model decides | `daily-health-digest`, `weekly-hermes-backup`, `hermes-self-update`, `email-command-bridge` | 98 / 14 / 14 / 9,106 |

That is not a coincidence I am reading into it — it is the same architecture
this plan needs, already load-bearing and already proven at five-figure run
counts. The station maps onto it directly:

- **The audio path is `no_agent` scripts.** Watchdogs for Icecast and
  Liquidsoap, in exactly the shape `docker-watchdog` already has, on the same
  five-minute tick that has fired 27,320 times without an incident.
- **The programming is an agent job.** One nightly prompt that writes tomorrow's
  playlist file, in the shape `daily-health-digest` already has.
- **Nothing has to be invented.** No new scheduler, no new alerting, no new
  delivery mechanism, no new place to look when something breaks.

### Two capabilities worth designing around

**`email-command-bridge` runs every 15 minutes and is agent-driven** — it has
fired 9,106 times. The gateway also speaks Telegram, Discord, Slack, WhatsApp
and Signal. So "text the station manager" is not a feature to build; it is a
prompt to write. *"Push tonight's interview to the top of the hour"* becomes a
message rather than a deployment, and the reply comes back on the same channel.

For an accessibility-first station that is not a gimmick. It means the person
running the station can run it from a phone, by typing a sentence, with a screen
reader, from anywhere — which is a materially better operator experience than
any web console anybody would build.

**Skills are how it gets taught.** Hermes creates and refines skills from
experience and follows the `agentskills.io` standard, with `media`, `devops` and
`creative` categories already installed. A `radio-programming` skill is the
natural home for the station's rules — day-parting, repeat windows, hour
structure — rather than a prompt pasted into a cron job. Write the rules once,
in one place, versioned.

### The risks that come with it, named now

1. **Hermes runs as `jeffbis`, which is in both `docker` and `sudo`.** An agent
   with a shell in the `docker` group effectively has root on this host. That is
   already true today and is not created by the radio station — but "let the bot
   keep the station configured" is a much larger blast radius than "let the bot
   write a playlist file", and the difference should be a deliberate choice
   rather than a side effect. **Recommendation: the station's agent jobs write
   files. Restarting containers stays with `no_agent` scripts whose contents a
   human wrote.**
2. **`hermes-self-update` runs weekly, agent-driven.** The thing operating the
   station updates itself every Sunday at 03:00. Fourteen clean runs is a good
   record, but a station is the first service here whose failure is audible to
   the public within seconds. At minimum the Icecast and Liquidsoap watchdogs
   must be `no_agent` scripts, so a bad Hermes update cannot take the audio down
   with it — the fallback chain and the watchdog are precisely the layers that
   must not depend on the agent being healthy.
3. **Every job currently delivers `local`** — output to files on the box.
   Fine for a watchdog nobody reads. Not fine for a station: the jobs that
   matter should deliver somewhere Jeff actually sees, which the gateway already
   supports.
4. **The learning loop cuts both ways.** A self-improving agent that adjusts its
   own skills is exactly what you want for programming quality and exactly what
   you do not want touching an encoder. The `no_agent` boundary is the control,
   and it is worth writing into the station's skill file in words.

---

## Content — talk only, decided 2026-08-26

**No music.** Jeff's call, and it is the right one for three reasons beyond the
obvious: it removes performance licensing entirely (SoundExchange, ASCAP, BMI —
the expensive, ongoing, per-play kind), it halves the bitrate the station needs,
and it matches what this audience actually turns up for. A community talk
station is what BITS is; a jukebox is not.

One honest correction to "no copyright issues", because it changes what the
programmer may pick up rather than what the station is: **what music avoids is
*performance* licensing, not copyright.** A recorded show, a conference session,
a guest interview and someone else's podcast are all still somebody's work.
Rebroadcasting a third-party podcast under BITS's call sign needs the same
permission it always did — the difference is that permission is a one-time email
to a named person rather than a licensing body and a per-play royalty. So the
rule for the library is simply: **everything in it is ours, or we have a "yes"
from whoever made it, recorded next to the file.**

That also removes a whole category of AI risk. A programmer choosing from a
library where every item is cleared cannot commit a licensing error, no matter
how badly it chooses.

What exists already:

- **The GGG podcast**, already served from this box.
- **Ask BITS**, whose questions and answers are exactly the material a
  community talk station is made of, and whose schema is already waiting.
- **ACB Media**, whose schedule is published as an ICS feed with categories that
  map to stream names — already researched, and a natural affiliation.
- **QUILL's own material** — the tutorials, the podcast episodes and the release
  walkthroughs already written and recorded for the apps.
- **Synthesised segments** built from text this project already owns: user
  guides read aloud, release notes, the FAQ, Ask BITS answers. Cheap, endless,
  and cleared by definition.

Still to decide deliberately rather than drift into:

- **Do not rebroadcast other stations' streams.** The TuneIn decision was about
  *linking* to streams from a directory, which is a different act from relaying
  one under your own call sign. Rebroadcast needs permission, in writing, per
  station — and ACB Media is the obvious first ask, because affiliation is a
  conversation rather than a technicality.
- **A bed of quiet music under speech is still music.** Intro stings, beds and
  outros are the usual way a "no music" station acquires a licensing problem
  by accident. Use production music with an explicit licence, or synthesise
  tones, and record the licence next to the file like everything else.

---

## Tie-in with Quill Radio and Cast

The station is the first piece of content this project both *makes* and *plays*,
and almost all of the plumbing is already shipped:

- **It gets a Community Picks entry** in the `quillville-picks` catalogue, so it
  appears in Radio's Community menu on every install. That pipeline is built,
  reviewed, signed and proven end to end.
- **Now Playing works for free** if Liquidsoap sets ICY metadata — Radio's
  What's Playing template (#1068) already reads it.
- **Recording works for free** — Radio 1.1.0 shipped DVR and raw recording.
- **It is the honest test case** for every accessibility claim the Radio app
  makes, because it is the one station whose metadata, titles and stream
  behaviour are ours to get right.

One naming decision to make **once**, before anything is published:

> **The mount point is part of the URL**, and that URL goes into the picks
> catalogue, into listeners' favourites, and into any app that adds it. Renaming
> `/stream` to `/live` later is the `quillforall.org` problem in miniature.
> Choose it on day one and never move it.

---

## Suggested order

Each step is independently useful, and each is reversible until the one after
it.

0. **Read the bandwidth allowance out of the RackNerd panel** and set the
   Icecast client cap from it. Content is settled — talk only — so this is the
   last non-technical blocker, and it is a two-minute job rather than a
   decision. While in there, consider the $7/year-per-TB top-up.
1. **DNS.** `radio.bits-acb.org` A → `107.175.91.158`, at WordPress.com where
   the `bits-acb.org` zone lives. Confirm it resolves from more than one
   resolver before step 3, exactly as the helpdesk record was confirmed.
2. **Icecast**, one container, private network, no host ports, memory-capped
   like the helpdesk pair. Prove it locally on the box first — a mount, a
   password, a test source, a listener over the private network. Nothing public
   yet.
3. **The Caddy block**, only after step 1 resolves. Separate access log,
   `/admin/*` and `/status-json.xsl` blocked by path, verified with a real
   client rather than `curl -I`.
4. **Liquidsoap**, with the full fallback chain from day one — and **prove the
   failover by killing each layer in turn** while listening. A fallback that
   has never been tested is a fallback that does not exist.
5. **The library and ingest.** A directory, `ffprobe` for duration, and
   **loudness normalisation with `ffmpeg loudnorm` to about −16 LUFS**. Without
   it a listener gets a quiet interview followed by a track that takes their
   head off, which for someone wearing headphones all day is not a cosmetic
   problem.
6. **Three `no_agent` Hermes jobs**, cloned from the ones already running:
   an Icecast/Liquidsoap watchdog on the `docker-watchdog` five-minute tick, a
   bandwidth alert in the `memory-alert` shape, and a nightly "did the station
   play what it was told to" check. **These come before any AI**, because they
   are what makes the AI safe to add.
7. **The deterministic scheduler.** Still `no_agent` — a weighted shuffle with
   the station's rules, in Python. One week unattended.
8. **The `radio-programming` skill and the agent job**, diffed against (7)'s
   output before it is trusted with a single hour of air time.
9. **Pre-rendered station IDs and continuity**, one voice, kept files.
10. **Operator commands over the gateway** — reuse `email-command-bridge`, and
    add Telegram or Signal if wanted. Cheap, and it is what makes the station
    runnable from a phone with a screen reader.
11. **The catalogue entry**, so it appears in Quill Radio — last, because it is
    the step that tells the world it exists.

---

## Traps worth writing down before they cost anything

- **Icecast plays nothing on its own.** An empty mount 404s, and the first
  reaction is always to assume the install is broken.
- **Liquidsoap 2.x broke a great deal of 1.x syntax**, and most examples on the
  web are 1.x. Pin the image by digest, the way `helpdesk-app` is pinned, and
  expect the first config to fight back.
- **ICY metadata is latin-1 by convention.** A title with an accent turns to
  mojibake in some clients. Test with a real accented title, not with ASCII.
- **Memory is not free here.** 6.2 GB available today, and `web-keycloak-1` is
  already reporting unhealthy. Cap the new containers, following the
  1 GB / 512 MB precedent the helpdesk set.
- **The disk fills silently.** A library plus kept generated speech plus an
  archive of what went out is a directory that only grows. 102 GB free is a lot
  until something writes to it every hour of every day. Decide the retention
  policy in step 5, not in six months.
- **The Caddyfile rules from `magic.md` apply unchanged**: no `sed -i`, and the
  split inodes from that trap mean whoever edits it next **does the recreate
  first**, or the edit is invisible to the running Caddy.
- **Five other production sites share this box.** The help desk went in without
  dropping a connection because every reload was checked against its neighbours.
  A radio station is a heavier neighbour than anything else here, and it is the
  first service whose *normal* operation consumes a shared resource
  continuously.

---

## Open questions, all yours

1. ~~**Which bot?**~~ **Answered 2026-08-26: Hermes.** See its section above.
   What remains is narrower: how much authority it gets. My recommendation is
   in that section — agent jobs write files, `no_agent` scripts touch
   containers.
2. ~~**Bandwidth allowance**, and the behaviour on overage.~~ **Half answered.**
   The provider is RackNerd and the overage behaviour is documented above — the
   VPS is powered off until the 1st, which takes every other service with it.
   The remaining half is the allowance figure, readable only from
   `my.racknerd.com`.
3. ~~**What is it allowed to play?**~~ **Answered 2026-08-26: talk only, no
   music.** The residual question is narrower and cheaper: which third parties
   say yes, starting with ACB Media.
4. **Whose station is it?** The hostname says BITS; the tooling, the voices and
   the player are QUILL's; Ask BITS holds the schema. That decides where the
   code lives and who is on the hook at 3am — and it is the same
   organisation-versus-product question `magic.md` step 5 answered for domains,
   asked again about a service.
5. **Live or automated-only?** A fallback chain that includes a live input costs
   nothing to build now and is very awkward to retrofit — but it implies a human
   with an encoder, a password, and a slot. Worth deciding early even if the
   answer is "not yet".
