# Networks and directories from BlindRadio

Branch `feat/br-dirs`, 2026-11-07. Part of the BlindRadio ideas program
(`docs/design/blindradio-review-2026-11-07.md`). BlindRadio is by serrebidev,
MIT licensed: https://github.com/serrebidev/blindradio.

## What was built

### Curated networks with direct stream addresses

- `quill/data/radio_networks.json`: 20 networks, 516 channels, each pinned to the
  operator's own published stream. Taken from BlindRadio's
  `crates/blindradio-core/data/networks.json` (current head for the English
  networks; commit `f398c69a`, 2026-10-30, for Sunshine Live, Planet Radio, Radio
  Record, PulsRadio and Radio Swiss, which BlindRadio later dropped when it trimmed
  to English-language networks). The file carries an `attribution` line, the full
  MIT notice (`license`), the date it was last checked, and for every network an
  `origin` saying where its addresses came from. `quill/data/radio_networks.LICENSE.txt`
  carries the same notice beside it. `quill/data` ships whole (the wheel packages
  `quill`; the runtime inventory copies `quill/data`), so nothing else is needed
  to package it.
- Networks carried: BBC (66 services), ABC Australia by region (49), Radio Swiss
  (3), Minnesota Public Radio and YourClassical (16), WFMU and its side channels
  (5), WFUV (1), Big R Radio (46), NTS with its Infinite Mixtapes (18), Nightride
  FM (7), Power Hitz (15), Radio Record (90), PulsRadio (8), Sunshine Live (7),
  Planet Radio and FFH (31), Global UK (Capital, Heart, Smooth, Classic FM, LBC,
  Radio X, Gold: 39), Triple M (39), ARN Australia (12), NZME (53), K-LOVE (9),
  Air1 (2).
- `quill/core/radio/curated_networks.py`: loads and validates the snapshot
  (`problems()` names duplicate ids, plain HTTP with no reason, a missing origin
  or a missing MIT notice), turns a channel into a `RadioStation` with a stable
  `station_uuid` of `net:<network>:<channel>`, and searches the channels by name.
  Listing a curated network makes no network call.
- `quill/core/radio/networks.py`: `catalog()` merges the curated networks into the
  existing Radio Browser query networks. A curated network that declares
  `replaces` takes the query's id and its place in the list, so the BBC is one
  folder, not two, and anything remembered against `network:bbc` still lands on
  the BBC. Replaced deliberately: `bbc`, `abc-au`, `apm` (now "Minnesota Public
  Radio and YourClassical"), `big-r-radio`. A curated id that collides with a query
  it did not declare it replaces is dropped (tested). Two new groups: Commercial
  radio (Global UK, Triple M, ARN, NZME) and Christian radio (K-LOVE, Air1).
  Curated network folders show their channel count before they are opened.
- Channels are ordinary stations in the tree, so favorites, recording,
  scheduling, What's Playing and the context menu all work as for any leaf.
- Find Stations gains a **Networks** source (no network; it reads the table).
- `scripts/refresh_radio_networks.py`: the hand-run probe and refresh tool.
  It checks each address the way BlindRadio did: GET, HTTP 200, audio content
  type, 4096 bytes read, connection closed. An HLS address passes when its
  playlist (and first variant) is served and the newest segment reads 4096 bytes.
  One retry per failure. `--refresh` reads the operators' own lists for NTS
  (`www.nts.live/api/v2/mixtapes`) and Radio Record (`www.radiorecord.ru/api/stations/`)
  and merges them, keeping a channel's id when its address moves; for the BBC
  (`rms.api.bbc.co.uk/v2/experience/inline/stations`) it is a roster check only,
  because that API names services but carries no stream address. `--upgrade-http`
  tries HTTPS for every HTTP row, `--drop-dead` removes failures, `--write` saves
  with LF endings. It refuses to run under pytest or when `CI` is set. The app
  never runs it.

### Directories

- **IPRD**, the International Public Radio Directory (`quill/core/radio/iprd.py`,
  `quill/core/radio/browse_iprd.py`): a new root branch "IPRD (Public Radio
  Directory)" with By Country and By Genre (the 100 most-used genres), each list
  100 stations at a time with a "More..." row that says "showing 100 of 4,012".
  Find Stations, Find in this folder and the federated search all reach it. The
  catalogue is one 2 MB gzipped GET, made only when a folder under the branch is
  opened or a search runs, kept for a day in the directory cache (trimmed) and ten
  minutes in memory. Safe Mode refuses it out loud.
- **TuneIn**: Music, Talk, Sports and Local Radio were already in the tree (they
  are TuneIn's own root), and "More Stations" (`nextStations`) already opened the
  next page, because its link carries the offset. Added: a station TuneIn files
  under both "Local Stations" and "Stations" is listed once. Tests now pin the
  paging.
- **iHeart markets**: already shipped (By City, `/api/v2/content/markets`, then
  stations by `marketId`). Nothing to add.

### Terms checks

- **IPRD: added.** The project is MIT licensed, describes itself as a "public
  listing of internet radios from all around the world", and publishes the
  catalogue on GitHub Pages; github.io has no robots restriction on it.
- **Internet-Radio.com: not added.** Its terms of use (internet-radio.com/terms/enduser/)
  say a listener may stream the stations "solely by means of the audio player
  embedded in the site or any third party media player facilitated by the site",
  and the acceptable use policy forbids reproducing or copying any part of the
  site. There is no API: BlindRadio reads its HTML pages. robots.txt also
  disallows `/playlist.m3u` and `/playlist.xspf`, the very links the site uses to
  hand a station to a player. Reading its listing into another app's browse tree
  is not a use those terms allow.
- **radio.net tag browse: not added.** The API host BlindRadio uses,
  `prod.radio-api.net`, serves a robots.txt of `Disallow: /` for every agent, and
  radio.net's terms (radio.net/terms-and-conditions, section on use) permit use
  "for private purposes of locating and playing Audio Sources" and forbid "any
  further use", including "making available to the public". Quill Radio already
  accepts a pasted radio.net page through Find Streams; that is unchanged.

### Left out of the snapshot, and why

- **SomaFM**: retired in Quill Radio on 2026-10-31 (its terms no longer approve new
  third-party clients; `models.is_retired_somafm_station`). Not carried, and a
  test asserts it stays out. Its `channels.json` refresh path was therefore not
  built.
- **1.FM**: `api.1cloud.fm/api/channels` answered keyless on 2026-11-07, but the
  2026-10-25 ruling in `networks.py` was that 1.FM publishes no station list a
  player may use. Left as the existing Radio Browser query; worth a fresh terms
  read before switching it to the API.
- **181.FM and Radio Paradise**: Quill Radio already carries both whole, from
  their own lists.
- **Bauer brands** (none were in the source list) and anything needing a key.
- **Seasonal channels**: Big R Radio's Halloween Channel and four Christmas
  channels, Radio Record's Christmas and Christmas Chill, Planet Radio's
  FFH Weihnachtsradio and Weihnachtsklassiker.
- **Probe failures on 2026-11-07**: none of BlindRadio's own rows failed. The
  Radio Record API lists 25 channels whose `stream_128` answers 404 (mostly artist
  shows); the refresh adds them and the probe drops them every time, which is why
  the network has 90 rather than 115. PulsRadio's host (`icecast.pulsradio.com`)
  refuses roughly one TLS handshake in three; all eight channels play on a retry
  and are kept.
- **BBC services the BBC lists but the snapshot lacks**: 5 Sports Extra 1 to 3,
  6 Indie Forever, Live News, Radio Wales Extra, CBeebies Radio (BlindRadio found
  their audio 403 outside the UK), and CWR, Hereford and Worcester, Radio Solent
  Dorset (BlindRadio found no address). Not invented.

### HTTPS

Every address is HTTPS except one. The probe upgraded 68 BlindRadio rows from
HTTP (65 BBC, 3 Triple M) because the same host served the stream over HTTPS.
WFUV stays HTTP with its reason recorded in the row: its HTTPS host sends an
incomplete certificate chain, so a verified TLS connection fails, and the same
stream over HTTP answers audio.

## User guide text

Replace item 21 in the Browse Stations list with:

> 21. **Networks**: well-known broadcasters, grouped by type. Many of them, the
>     BBC, WFMU and Global's Capital and Heart among them, list every channel the
>     broadcaster runs, each going straight to its own stream.

Add after item 25 (Live365), renumbering what follows:

> 26. **IPRD (Public Radio Directory)**: an open list of about 24,000 stations
>     from every country, by country and by genre.

Replace the **Networks** paragraph under "What is in each branch" with:

> - **Networks** groups well-known broadcasters: public broadcasters such as the
>   BBC, NPR, CBC, ABC Australia, Radio France and Deutschlandfunk, plus US news
>   and talk, US public radio, sports, music, commercial radio, Christian radio
>   and syndicators. Many of them list the broadcaster's own channels, each going
>   straight to the broadcaster's own stream: the BBC's national, local and
>   digital services, the ABC by region, Minnesota Public Radio and YourClassical,
>   WFMU and its side channels, WFUV, Radio Swiss, Global's Capital, Heart, Smooth,
>   Classic FM, LBC, Radio X and Gold, Triple M, ARN and NZME, K-LOVE and Air1,
>   and music networks such as Big R Radio, NTS and its Infinite Mixtapes,
>   Nightride FM, Power Hitz, Radio Record, PulsRadio, Sunshine Live and Planet
>   Radio. These folders say how many channels they hold before you open them,
>   and open at once, because the list comes with Quill Radio. Seasonal channels
>   are left out so a network never goes quiet in January. The rest of the
>   networks search the station directory for the broadcaster's name. A
>   syndicator such as Westwood One has no single stream, so it opens a search
>   across the stations that carry it, and its name tells you so.

Add after the **Live365** paragraph:

> - **IPRD (Public Radio Directory)** has **By Country** and **By Genre**. A long
>   list shows a hundred stations at a time; the last row, **More...**, says how
>   many there are and opens the next hundred. The whole directory is fetched the
>   first time you open a folder in it and kept for a day, so moving around it
>   afterwards needs no wait.

Under TuneIn, add one sentence:

> Music, Talk, Sports and Local Radio list their first stations and then **More
> Stations**, which opens the next page.

Find Stations sources list (the sentence that names them): add **IPRD** and
**Networks** after laut.fm.

## PRD text

> - Curated networks (2026-11-07; `quill/core/radio/curated_networks.py`,
>   `quill/data/radio_networks.json`, `scripts/refresh_radio_networks.py`). The
>   Networks branch carries 20 networks whose channels are pinned to each
>   operator's own published stream, from BlindRadio's curated table (MIT, notice
>   kept in the data file and beside it), each with a recorded origin. A curated
>   network that `replaces` a Radio Browser query takes its id and place (BBC,
>   ABC, MPR, Big R Radio), so no network is shown twice and saved browse
>   positions still resolve. Listing them makes no request; playing one reaches
>   only the operator's stream. Every address is HTTPS unless the row states why
>   not. A hand-run tool re-probes every address (GET, 200, audio type, 4096 bytes,
>   close) and refreshes NTS and Radio Record from their own keyless APIs; it never
>   runs in the app, tests or CI. Seasonal-only channels, Bauer brands, keyed
>   streams and SomaFM (retired) are excluded.
> - IPRD directory (2026-11-07; `quill/core/radio/iprd.py`, `browse_iprd.py`).
>   The International Public Radio Directory, an MIT-licensed open catalogue on
>   GitHub Pages, as a root branch: By Country and By Genre (top 100), paged 100
>   at a time with a counted More... row, and a Find Stations source. One reviewed
>   egress site, fetched only on a user's open or search, cached a day.
> - Directories considered and refused (2026-11-07): Internet-Radio.com (its terms
>   limit streaming to its own player or players it facilitates and forbid copying
>   the site; HTML scraping only) and radio.net's tag browse (its API host's
>   robots.txt disallows everything, and its terms permit private use only).

## CHANGELOG line

> - **More networks, straight to the broadcaster's stream; IPRD** (2026-11-07).
>   Networks now lists every channel of the BBC, the ABC by region, MPR and
>   YourClassical, WFMU, WFUV, Radio Swiss, Global's UK brands, Triple M, ARN,
>   NZME, K-LOVE, Air1, Big R Radio, NTS and its Infinite Mixtapes, Nightride FM,
>   Power Hitz, Radio Record, PulsRadio, Sunshine Live and Planet Radio, 516
>   channels in all, each checked to answer audio. The list comes from BlindRadio
>   by serrebidev. Browse Stations gains IPRD, the open Public Radio Directory,
>   by country and genre, a hundred at a time. Find Stations searches both. TuneIn
>   no longer lists a station twice when it is both local and in a category.

## Third-party notice

Text for THIRD_PARTY_NOTICES (through `quill/data/third_party/components.json`,
which renders it; not edited on this branch):

```
BlindRadio network table
Copyright (c) 2026 serrebidev
https://github.com/serrebidev/blindradio
License: MIT
Used for: the curated network list and stream addresses in
quill/data/radio_networks.json (from crates/blindradio-core/data/networks.json
and docs/radio-directory-sources.md), and the probe rule used by
scripts/refresh_radio_networks.py.

MIT License

Copyright (c) 2026 serrebidev

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

Suggested `components.json` entry: id `blindradio-networks`, group data,
licenses `["MIT"]`, copyright "Copyright (c) 2026 serrebidev", homepage
https://github.com/serrebidev/blindradio, products `["radio", "quill"]` (or
whichever products ship the Radio core), delivery bundled. IPRD's catalogue is
read at run time, not shipped, so it needs no notice.

## Keys, settings, egress

- Keys added: none. The new branch and the networks are tree rows; every
  existing Browse Stations key applies.
- Settings added: none. Two registries gained entries with epoch bumps so
  existing profiles see them once: `browse_visibility` epoch 6 (`iprd`) and
  `search_sources` epoch 4 (`iprd`, `networks`).
- Egress rows added: `core/radio/iprd.py::_fetch` in
  `quill/tools/network_egress_entries_radio.py`. The refresh tool lives in
  `scripts/`, outside the app and outside the audit's scope, and is never run by
  the app.

## Not done or not verified

- Not heard through mpv: the probe checks HTTP and bytes, not playback. The
  BBC and ABC rows are HLS; Quill Radio's mpv path plays HLS, but these exact
  streams were not played here.
- Each operator's own terms for third-party players were not read one by one;
  the list relies on BlindRadio's sourcing notes (each address is the
  operator's own published stream) plus the exclusions above. Global, ARN and
  NZME run their own apps and could follow Bauer's lead; if one does, delete
  that network's entry.
- ARD's geo-limit (from 2026-10-01) does not touch this list; no ARD network is
  curated.
- No screen-reader pass of the new branch was done on this machine.
- The integrator should regenerate THIRD_PARTY_NOTICES from components.json
  with the entry above, and fold the user-guide, PRD and CHANGELOG text in.
