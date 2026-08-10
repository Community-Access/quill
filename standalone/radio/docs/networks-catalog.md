# Networks catalog for Quill Radio's browse tree

An exhaustive, accuracy-checked catalog of radio "networks" worth surfacing,
and **how each can be added** using open sources only (Radio Browser — already
integrated, so no new network-egress site — plus each broadcaster's own public
streams). No competitor data or curated lists are copied.

## The one distinction that matters

A "network" is one of three very different things, and they must be handled
differently:

1. **Broadcasters with tune-in streams** (BBC, NPR members, CBC, ABC Australia,
   Fox News Radio, Bloomberg…). These have real, playable streams and belong as
   one-click browse nodes.
2. **Syndication / content networks** (Westwood One, NBC News Radio, ABC News
   Radio, Premiere). These produce *programming carried by affiliate stations* —
   there is **no single stream to tune to**. Surfacing them means searching
   their **affiliates** (which are in Radio Browser / iHeart / TuneIn), not
   inventing one URL.
3. **Station groups / owners** (iHeartMedia, Audacy, Cumulus). Ownership, not a
   listening destination — their stations are already reachable by name/genre.

**Timely caveat (verified Aug 2026):** **CBS News Radio is being shut down** —
CBS announced on 2026-03-20 that service to its ~700 remaining affiliates ends
2026-05-22. Do **not** build a "CBS" network node; CBS-owned local radio became
**Audacy** back in 2017, and CBS News Radio the syndicated service is ending.

## Add method legend

- **RB** = curated Radio Browser query (reuses `radio_browser.py`; no new egress
  site; no keys) — the default.
- **Direct** = the broadcaster publishes a stable public stream URL.
- **Built-in** = already shipped in Quill Radio.
- **Affiliates** = a *search* entry (syndicator has no single stream).

## US news / talk

| Network | Add method | Notes |
| --- | --- | --- |
| NPR (member stations) | RB (tag `npr`, `public radio`) | NPR's own API needs a key + is on-demand |
| Fox News Radio | Direct (`radio.foxnews.com`) + RB | national 24/7 talk stream |
| CNN (audio) | RB / TuneIn | CNN audio via aggregators |
| Bloomberg Radio | Direct + RB | own national stream |
| Westwood One | **Affiliates** | Cumulus syndication (news/sports/music formats); no single stream |
| NBC News Radio | **Affiliates** | syndicated news service; carried by affiliates |
| ABC News Radio (US) | **Affiliates** | syndicated; disambiguate from ABC Australia |
| CBS News Radio | **excluded** | ending 2026-05-22 |

## US station groups (stations reachable already)

| Group | Add method | Notes |
| --- | --- | --- |
| iHeartMedia | Built-in | the iHeart browse branch |
| Audacy (ex-CBS Radio / Entercom) | RB | acquired CBS Radio 2017 |
| Cumulus Media | RB | owns Westwood One |
| Townsquare / Beasley / Salem | RB | by name |

## US public radio (beyond NPR)

| Network | Add method |
| --- | --- |
| American Public Media (APM) / Minnesota Public Radio | RB |
| PRX / GBH / PRI | RB |
| Marquee independents: KEXP, KCRW, WNYC, WBEZ, WFMU | RB / Direct |

## US sports

| Network | Add method | Notes |
| --- | --- | --- |
| ESPN Radio | RB / Direct | iHeart-distributed national feed |
| CBS Sports Radio | **Affiliates** | Audacy |
| Fox Sports Radio | **Affiliates** | iHeart / Premiere |
| Westwood One Sports | **Affiliates** | event-based (NFL, NCAA) |

## International public broadcasters (the strongest candidates — real streams)

All are RB-addable by name/country; most also publish Direct streams.

| Country | Network | Streams |
| --- | --- | --- |
| UK | **BBC** | Radio 1/1Xtra/2/3/4/4 Extra/5 Live/6 Music/Asian Network, **World Service** (global), local | 
| Canada | **CBC / Radio-Canada** | CBC Radio One/Music, ICI Première/Musique |
| Australia | **ABC** | Radio National, triple j, ABC News, Classic, local |
| Ireland | **RTÉ** | Radio 1, 2FM, lyric fm, RnaG |
| New Zealand | **RNZ** | National, Concert |
| Japan | **NHK World** | English + Japanese |
| Germany | **Deutschlandfunk / Deutschlandradio**, **Deutsche Welle (DW)** | national + international |
| France | **Radio France** (France Inter/Info/Culture/Musique, **FIP**), **RFI** | national + international |
| Austria | ORF (Ö1, FM4) |
| Switzerland | SRF, RTS, Radio Swiss (Jazz/Classic/Pop) |
| Italy | RAI Radio 1/2/3 |
| Spain | RTVE / RNE |
| Netherlands | NPO Radio 1/2/4 |
| Nordics | NRK (NO), DR (DK), SR (SE), YLE (FI) |
| Belgium/Portugal/Greece | VRT/RTBF, RTP, ERT |
| US international | Voice of America, Radio Free Europe/RL |
| Korea/India/S. Africa | KBS World, AIR/Akashvani, SABC |

## Music / theme networks

| Network | Add method | Notes |
| --- | --- | --- |
| SomaFM | Built-in | via SomaFM's own `channels.json` |
| Radio Paradise | Direct | publishes stream + a public JSON API |
| FIP (Radio France) | Direct/RB | genre-blend music |
| KEXP, dublab, NTS | RB / Direct | tastemaker stations |
| Radio Swiss Jazz/Classic/Pop | Direct/RB | commercial-free |

## Recommended implementation

A **Networks** branch in Browse Stations, grouped:

- **Public broadcasters** (BBC, CBC, ABC AU, RTÉ, RNZ, NHK, DW, Deutschlandfunk,
  Radio France, RFI, ORF, SRF, RAI, RTVE, NPO, NRK, DR, SR, YLE, VOA, …) — each a
  curated **RB** query; the ones with a clean public stream can add a **Direct**
  entry too.
- **US news/talk** (NPR, Fox News Radio, Bloomberg, CNN) — RB/Direct.
- **Syndicators** (Westwood One, NBC News Radio, ABC News Radio, CBS/Fox Sports)
  — an **"…affiliates" search** node that runs a name search, honestly labeled
  "programming carried by local stations", **not** a fake single stream.
- SomaFM stays where it is (or moves under Networks > Music).

RB-query nodes reuse `radio_browser.py`, so the whole section adds **no new
network-egress site** (keeps `network_egress_audit` green), needs no API keys,
and never hard-codes an expiring stream URL. New source module:
`quill/core/radio/networks.py` (the curated query table), wired into
`browse_tree_dialog.py` and `directory_search.py`, with tests and docs.

## Sources

- [Westwood One to Drop NBC News Radio — Radio World](https://www.radioworld.com/news-and-business/westwood-one-to-drop-nbc-news-radio)
- [CBS News Radio — Wikipedia](https://en.wikipedia.org/wiki/CBS_News_Radio)
- [Former Westwood One News affiliates spread the wealth — Inside Radio](https://www.insideradio.com/free/former-westwood-one-news-affiliates-spread-the-wealth-among-network-providers/article_48cde23e-edad-11ea-9e58-831051b8422d.html)
- [Fox News Radio — Wikipedia](https://en.wikipedia.org/wiki/Fox_News_Radio) / [radio.foxnews.com](https://radio.foxnews.com/)
- [BBC World Service — Wikipedia](https://en.wikipedia.org/wiki/BBC_World_Service)
- [Public Broadcasters by Country 2026 — World Population Review](https://worldpopulationreview.com/country-rankings/public-broadcasters-by-country)
- [Live News Radio — TuneIn](https://tunein.com/radio/Live-Stream-News-Radio-c57922/)
