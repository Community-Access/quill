# BlindRadio review for Quill Radio

Reviewed 2026-11-07, from github.com/serrebidev/blindradio (MIT, Rust, pushed 2026-11-08 UTC).
Read through the GitHub API only; nothing was cloned or run.

## What it is

A Rust screen-reader-first radio player: an egui-style desktop app (`crates/blindradio`) over a
core crate (`crates/blindradio-core`) with its own decoders, HLS, time-shift ring buffer and 13
directory sources. Because it is Rust and Quill Radio is Python over mpv, almost nothing is
portable as code. What is worth taking is data, endpoints and behaviour ideas. The MIT licence
allows reuse of its data with the copyright notice kept.

## Directories, by risk

Low risk means a public, documented or openly served API, used the way the operator intends.

### Low risk: add

- **Curated network table** (`crates/blindradio-core/data/networks.json`, 76 networks, 868
  direct stream URLs). Quill's `networks.py` builds networks by Radio Browser query, so a
  network is only as good as Radio Browser's rows. BlindRadio's table pins each channel to
  the operator's own published stream, with the source of each in
  `docs/radio-directory-sources.md`. Networks Quill does not have at all: WFMU and its side
  channels, Global UK (Capital, Heart, Smooth, Classic FM, LBC, Radio X), Big R Radio (51),
  Sunshine Live, Planet Radio/FFH (33), Nightride FM, Power Hitz, Radio Record (92),
  PulsRadio, MPR/YourClassical channels, ABC Australia by region, K-LOVE/Air1, NZME,
  Triple M/ARN, Radio Swiss, WFUV, NTS Infinite Mixtapes. Recommended form: a reviewed
  snapshot with an attribution line, re-checked by our own probe, not a live pull from
  their repo.
- **Operator APIs that list their own channels** (keyless, documented or plainly public):
  SomaFM `channels.json`, 1.FM `api.1cloud.fm/api/channels`, NTS `api/v2/mixtapes`,
  Radio Record `radiorecord.ru/api/stations/`, WHFF AzuraCast `api/stations`, BBC
  `rms.api.bbc.co.uk/v2/experience/inline/stations`. These keep the table current
  without scraping.
- **Internet-Radio.com and IPRD**: two directories Quill lacks; both are open listings.
  Worth a short terms check before adding.
- **radio.net tag browse** (`/stations/tags`, `/stations/by-tag`): public pages; Quill only
  touches radio.net incidentally.
- **Extra browse paths on directories Quill already has**: TuneIn `c=music|talk|sports|local`
  with `nextStations` paging; iHeart `/api/v2/content/markets` and `marketId`.

### Low risk: song history from a stream URL

All keyless, and found from the stream URL so they work for directory stations too:

- AzuraCast `https://<host>/api/nowplaying/<shortcode>` (documented API, `song_history`).
- KEXP `api.kexp.org/v2/plays/?ordering=-airdate` (order is required or it can be stale).
- BBC `rms.api.bbc.co.uk/v2/services/<id>/segments/latest?limit=10` (400 above 10).
- Radio Paradise `api.radioparadise.com/api/nowplaying_list_v2022?chan=N&list_num=N`.
- Live365 `api.live365.com/station/<mount>` `current-track` and `last-played`.
- laut.fm `/station/<name>/last_songs` (Quill already calls api.laut.fm; check it reads this).
- Triton `np.tritondigital.com/public/nowplaying?mountName=...` (undocumented; Quill already
  has `triton.py`; their tip: strip `_SC` and `AAC` from the mount name, 65 of 94 then work).

### Medium risk: only with care

- **Live365 full list via page data**: the station list API answers Unauthorized, so they read
  React Router data out of `live365.com/listen/...` pages. Works, but it is scraping a closed
  list. Quill's `live365.py` already uses the sitemap; prefer that.
- **Big R Radio, Power Hitz, PulsRadio, Planet Radio**: stream tables read from each site's own
  player script or HTML. The streams are the operator's, but the list is scraped, so it breaks
  silently. Fine as a snapshot, not as a live source.

### High risk: do not add

- **Online Radio Box** (`sources/orb.rs`): their own research says the terms forbid it and
  robots.txt disallows `/json/*`; the author added it anyway. Conflicts with our
  no-competitor-data rule.
- **Airable**: catalogue behind an NDA; using a radio's token would pose as a licensed device.
- **vTuner**: personal-use terms, half the sample dead.
- **101.ru**: IP-bound JWT URLs. **DI.fm / RadioTunes**: subscriber keys only.
- **Bauer stations** (Absolute, KISS, Magic, Planet Rock and the Irish brands): withdrawn from
  third-party apps by the broadcaster. Their list leaves them out, and so should ours.
- **ARD**: since 2026-10-01 its live streams are geo-limited to Germany for third parties;
  expect 1LIVE and others to fail abroad. Worth a station-health note, not a removal.
- **Radio Garden** (Cloudflare refuses non-browsers) and **Zeno** (no stream URLs): nothing to use.

## Features worth considering

Already in Quill Radio, no action: time-shift, recording, sleep timer, equalizer, Radio Browser,
TuneIn, iHeart, SHOUTcast, Icecast/Xiph, Live365, laut.fm, Radio Paradise, 181.fm, song
recognition (AcoustID), YouTube, playlist import and export, global hotkeys, update check.

Not in Quill Radio:

1. **Dial tuning**: the station under focus starts playing, neighbours stay connected so moving
   is near instant, and soft hiss covers the gap. The biggest idea in the project. With mpv it
   would mean a small pool of pre-opened players; a setting, off by default, and a careful
   GATE-13 read so focus changes do not double-speak.
2. **Segment bookmarks in the time-shift buffer**: every ICY title change marks the buffer, so
   the user can jump between songs and save the current, previous, next or every segment to
   its own file. Builds on `timeshift.py` and `recording_split.py`.
3. **Adaptive cushion**: after an underrun the buffer refills deeper (3 s, then 9, up to 15) and
   earns the normal size back after a clean minute. Maps onto mpv `cache-secs` /
   `demuxer-readahead-secs`.
4. **Scrobbling** to ListenBrainz and last.fm/Libre.fm for songs heard a minute or more. Needs
   consent, a network-egress audit row and stored tokens through DPAPI.
5. **AudD recognition** as a second engine beside AcoustID, for talk-free music stations with no
   titles. User's own token; egress row.
6. **Per-station time-shift length** (global default 30 min, override per station).
7. **Audio device follow**: re-attach when a lost output device returns (check `mpv_devices.py`
   first; may already be covered).

Not worth taking: their decoders, HLS and ring buffer (mpv already does this), minisign updates
(Quill has its own signed feed), the egui UI.

## Suggested order

1. Song-history sources (AzuraCast, KEXP, BBC, Radio Paradise list, Live365, Triton mount tip):
   small, keyless, immediately audible in What's Playing.
2. Curated network snapshot with per-URL probe and attribution.
3. Segment bookmarks.
4. Adaptive cushion.
5. Dial tuning, as a designed feature with its own PRD section.
6. Scrobbling and AudD, each behind consent and an egress entry.
