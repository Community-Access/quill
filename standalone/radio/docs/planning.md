# Quill Radio Planning Notes

Yes. I would expand QUILL Radio beyond traditional broadcast directories, but treat these as **different provider classes**, because a station directory, police-scanner network, repeater database, and remotely controlled radio receiver work very differently.

The most important rule is that **directory access and audio playback rights are separate**. A source may permit searching its metadata without permitting QUILL to resolve, embed, cache, or redistribute its streams.

## Best additions to pursue

| Source                         | What it adds                                                                        | Access outlook                                                        | QUILL priority              |
| ------------------------------ | ----------------------------------------------------------------------------------- | --------------------------------------------------------------------- | --------------------------- |
| **FMSTREAM**                   | Large international radio catalog with direct station streams                       | Noncommercial database API available with a free key and usage limits | **Very high**               |
| **SHOUTcast Directory**        | Independent internet stations and genre-based browsing                              | Official partner API application                                      | **High**                    |
| **Icecast Directory**          | Independent and community-hosted streams                                            | Public directory; formal reuse expectations should be confirmed       | **High**                    |
| **RadioDNS**                   | Station names, logos, identifiers, metadata, service following                      | Open broadcast-radio standards                                        | **High for enrichment**     |
| **Radioplayer**                | Broadcast stations, search, location, now playing, schedules and on-demand programs | Approved commercial or strategic partner access                       | **High partnership target** |
| **airable**                    | Curated radio, podcast and music-service catalogs                                   | Business API, negotiated access                                       | Medium                      |
| **Radioline Business**         | Worldwide station and podcast catalog                                               | Partner API                                                           | Medium                      |
| **RepeaterBook**               | Amateur-radio repeaters, frequencies, modes and locations                           | Approved application integration; licensing depends on use            | **High for ham metadata**   |
| **OpenWebRX/Receiverbook**     | Public remotely controlled SDR receivers                                            | Open ecosystem, but receiver operators control access                 | **High experimental value** |
| **OpenMHz**                    | Public-safety radio calls and archives                                              | Partnership required for third-party API use                          | Medium/high                 |
| **NWS and NOAA Weather Radio** | Alerts, forecasts and transmitter locations                                         | Official government APIs and data                                     | **Very high**               |
| **IAAIS reading services**     | Accessible radio-reading services for people with print disabilities                | No general API; direct partnership and curated catalog                | **Mission-critical**        |

## 1. FMSTREAM should probably be next

FMSTREAM is one of the strongest fits for QUILL. It maintains a large international catalog, connects listeners directly to broadcaster streams rather than proxying the audio, and offers a database API for noncommercial use through a free API key with query limits. It also preserves broadcaster restrictions such as geoblocking. ([FMStream][1])

For QUILL, this could add:

* Long-tail local and international stations missing from iHeart and TuneIn.
* Multiple stream alternatives for a station.
* Codec, bitrate and stream-health information.
* Country, language, genre and location browsing.
* A second source for validating Radio Browser records.

I would place **FMSTREAM alongside Radio Browser**, not underneath it. QUILL could merge both catalogs into one canonical station result while showing provenance such as “Radio Browser,” “FMSTREAM,” or both.

## 2. Add SHOUTcast and Icecast webcasters

The **SHOUTcast Directory API** is explicitly intended for websites, applications and media players, although developers must apply as API partners and comply with its branding and reporting agreement. ([SHOUTcast][2])

That would add a great deal of independent programming:

* Community radio.
* Hobby stations.
* Genre-focused internet stations.
* International webcasters.
* Specialist music and talk channels.

The **Icecast directory**, operated through the Xiph ecosystem, is another valuable source of independently hosted streams. It is publicly browsable, although I would confirm automated reuse expectations before depending on its directory feed in production. ([Icecast][3])

These sources are especially useful because iHeart and TuneIn tend to emphasize established broadcasters and commercial aggregators. SHOUTcast and Icecast expose the independent “long tail.”

## 3. Use RadioDNS to make the catalog smarter

RadioDNS is not primarily another giant listening directory. It is an open standards framework connecting broadcast radio with internet-delivered information such as:

* Full station and service names.
* Logos and descriptions.
* Program information.
* Alternative streaming services.
* Universal presets.
* Service following between broadcast and internet reception.

That makes it an excellent **metadata-enrichment and station-identity provider**. ([RadioDNS][4])

For example, QUILL could recognize that:

* An FM station record from the FCC,
* a stream from Radio Browser,
* a station entry from FMSTREAM, and
* a RadioDNS service

all represent the same station.

## Police, fire and public-safety feeds

There is no broadly open, nationwide police-scanner catalog with unrestricted third-party playback.

### Broadcastify

Broadcastify remains the largest obvious source, but—as discussed—its catalog and audio policies make a broad QUILL scanner experience difficult without a negotiated partnership.

### OpenMHz

OpenMHz is worth approaching. It focuses on individual radio calls from trunked public-safety systems rather than only continuous mixed scanner streams. Its software is open source, but its published service terms restrict its API to its own website and applications unless permission is obtained. The open-source code therefore does not automatically make the hosted audio service open for QUILL. ([OpenMHz][5])

A partnership could provide a much better accessible experience than traditional scanner audio:

* Browse systems, talkgroups and agencies.
* Listen to one transmission at a time.
* Filter police, fire, EMS, dispatch and operations.
* Follow selected talkgroups.
* Present timestamps and available call metadata.
* Avoid several simultaneous conversations being mixed together.

### RadioReference

RadioReference is valuable primarily as a **frequency and radio-system database**, not as an open audio source. Its API program is designed largely for scanner programming and approved radio-related applications. Free developer access generally requires every end user to authenticate with an active RadioReference Premium subscription; directory-style applications can require separate licensing. ([RadioReference Support][6])

It could still enrich QUILL with:

* Agency and department names.
* Trunked systems.
* Talkgroups.
* Conventional frequencies.
* County and statewide system organization.

But it should not be treated as a free replacement for Broadcastify audio.

### A QUILL Community Feeds program

The best long-term solution may be for QUILL to operate a **feed-owner federation** rather than depending entirely on a scanner monopoly.

Feed providers could submit:

* A direct Icecast, SHOUTcast, HLS or other supported stream.
* Feed name and geographic coverage.
* Agencies and talkgroups included.
* Optional delay information.
* Availability schedule.
* Provider contact.
* Rights attestation.
* Terms, attribution and permitted uses.

QUILL would index the feed but audio would continue coming directly from the provider. This could also support volunteer fire departments, emergency-management offices, universities, transit agencies and local governments that publish their own feeds.

## Amateur radio and repeater listening

This needs to be divided into **repeater information** and **actual audio**.

### RepeaterBook for metadata

RepeaterBook is probably the best first integration for amateur-radio repeater information. Its ecosystem supports application partnerships and machine-readable data used by radio-programming applications. Public data may be used for personal, educational and certain noncommercial purposes, while broader commercial usage requires licensing. Written approval would still be wise for QUILL’s specific integration. ([RepeaterBook][7])

QUILL could let users search by:

* City, county, state or distance.
* Frequency and offset.
* Analog FM, DMR, D-STAR, System Fusion and other modes.
* Tone or digital code.
* Emergency and linked networks.
* Open, closed or uncertain operational status.
* Club and repeater sponsor.

But a repeater entry usually **does not include a public listening stream**.

### EchoLink

EchoLink connects validated amateur-radio operators and stations over the internet. It has station and node lookup capabilities, but it is an authenticated amateur service rather than an anonymous public streaming directory. ([EchoLink][8])

A QUILL integration might therefore provide:

* Search and discovery.
* “Open in EchoLink.”
* Authenticated connection for licensed users.
* Accessible node and conference browsing.

It should not assume that every QUILL user can anonymously listen.

### AllStarLink

AllStarLink publishes node information and status data and is a major network for linking amateur-radio repeaters. Its node-status software is open source, but I did not find a clearly documented, general-purpose passive-listening API intended for third-party radio players. ([AllStarLink][9])

Start with node lookup and external launching. Direct connection or audio integration should be discussed with AllStarLink.

### BrandMeister

BrandMeister exposes API capabilities for authenticated users and applications involving account, repeater and talkgroup configuration. It is not primarily a public streaming-audio service. ([BrandMeister News][10])

It is useful for identifying:

* DMR repeaters.
* Talkgroups.
* Network status.
* Repeater configuration.

It would be an enrichment or licensed-user feature rather than a general listening directory.

## Public software-defined radio receivers

This is where QUILL could do something genuinely distinctive.

### OpenWebRX and Receiverbook

OpenWebRX provides a browser-based, multi-user radio receiver. Its related Receiverbook directory helps people locate publicly available receivers around the world. ([OpenWebRX][11])

### KiwiSDR

KiwiSDR operators can list public receivers in a worldwide directory. These receivers can cover amateur radio, international shortwave, utility stations, aviation, maritime communications and other spectrum depending on location and antenna. ([KiwiSDR][12])

### WebSDR

WebSDR allows multiple users to tune independently through the same remote receiver. ([WebSDR][13])

### UberSDR

UberSDR is another open-source receiver platform with public instances and client capabilities, including audio-oriented access. ([UberSDR][14])

These are not ordinary station streams. The user chooses:

* Receiver location.
* Frequency.
* Mode such as AM, FM, USB or LSB.
* Filter width.
* Tuning step.
* Band.

A fully accessible QUILL receiver interface could be transformational for blind radio enthusiasts. It could provide structured keyboard controls such as:

> Receiver: Northern Arizona
> Frequency: 146.520 MHz
> Mode: FM
> Step: 5 kHz
> Signal strength: moderate
> Tune up/down, enter frequency, save channel, scan range

Initial integration should use **open-in-browser or operator-opt-in connections**, because a receiver being publicly visible does not necessarily authorize another application to embed or automate it.

## Aviation, rail and maritime

### LiveATC

LiveATC is the major aviation-audio directory, but its terms specifically prohibit automated retrieval, direct stream linking and dedicated third-party desktop or mobile applications without permission or a contractual arrangement. ([LiveATC][15])

It is worth proposing an accessibility partnership, but should not be reverse-engineered.

### RailroadRadio.net

RailroadRadio.net maintains a public rail-feed directory, but I found no formal public API. It should be approached for permission or a partnership rather than scraped. ([Railroad Radio][16])

### Maritime and airband through SDR

Public SDR receivers may be the more practical open path for maritime, aviation, amateur and shortwave listening. QUILL could offer curated presets such as:

* Marine VHF calling and weather channels.
* Local aviation approach frequencies.
* Amateur calling frequencies.
* International shortwave broadcasters.
* Time-signal and utility stations.

The available frequencies would depend on each receiver’s hardware, location and operator rules.

## Weather and emergency information

This should be a first-class QUILL provider, not merely another internet station.

The National Weather Service offers official APIs for alerts, forecasts and observations, while NOAA provides Weather Radio transmitter and coverage information. ([National Weather Service][17])

Instead of relying on unreliable rebroadcast streams, QUILL can create its own accessible **Weather Radio mode**:

* Continuous local conditions and forecast.
* Immediate severe-weather interruptions.
* County and polygon-based alerts.
* User-defined locations.
* Watches, warnings and advisories.
* Per-location voices.
* Repeat and acknowledgement controls.
* System-tray alerts.
* Local NOAA Weather Radio frequency and transmitter details.
* Links to available official live broadcasts where provided.

There is not a single nationwide NOAA live-audio API equivalent to a station directory, although some local NWS offices publish live broadcast links. ([National Weather Service][18])

## Radio-reading services

This category deserves special emphasis because it aligns directly with QUILL’s mission.

The International Association of Audio Information Services represents services that transform newspapers, magazines and other print information into audio for people who cannot effectively read conventional print. ([IAAIS][19])

There does not appear to be a unified listening API, so QUILL could create the missing directory through:

* IAAIS collaboration.
* Direct provider outreach.
* A self-service submission portal.
* Stream validation.
* Country, state and service-area metadata.
* Program schedules.
* Eligibility and authentication information.
* Local telephone and smart-speaker access information.
* Provider-controlled corrections.

This could become the definitive accessible directory of radio-reading services rather than another partial import.

## Commercial partnership targets

These are worth contacting after the open integrations are established:

### Radioplayer

Radioplayer’s partner API supports station discovery, geographic search, live metadata, schedules, on-demand programming and recommendations. It requires an approved account and API credentials. ([Radioplayer Developer Hub][20])

### airable

airable offers curated radio and podcast data through APIs for device manufacturers and other commercial partners. ([Airable Now][21])

### Radioline Business

Radioline offers its worldwide radio and podcast database to approved partners through custom API arrangements. ([Radioline][22])

### vTuner and myTuner

Both are potential catalog partners, although their access models are oriented toward approved devices, applications and licensed partners rather than unrestricted public APIs. ([vTuner][23])

## Recommended implementation order

### Build or begin now

1. **FMSTREAM integration**
2. **SHOUTcast API application**
3. **Icecast directory adapter**
4. **RadioDNS enrichment**
5. **NWS alerts and NOAA Weather Radio directory**
6. **RepeaterBook partnership request**
7. **Public SDR discovery prototype**
8. **QUILL Community Feed manifest**
9. **Reading-services submission directory**

### Pursue as strategic partnerships

1. Radioplayer
2. OpenMHz
3. radio.net
4. IAAIS
5. airable
6. Radioline
7. AllStarLink and EchoLink
8. RailroadRadio.net

### Do not integrate without an explicit agreement

* Broadcastify
* LiveATC
* Radio Garden internal endpoints
* OpenMHz hosted API
* RadioReference beyond its approved use cases
* Any directory that requires scraping or extracting protected playback URLs

## Provider architecture I recommend

QUILL should not assume every integration behaves like TuneIn. Each provider should declare one or more capabilities:

* **Catalog:** search and browse records.
* **Resolver:** return an authorized playable stream.
* **Metadata enricher:** logos, call signs, schedules and now-playing data.
* **Interactive receiver:** tune frequency, mode and filter.
* **Authenticated network:** EchoLink, premium service or licensed-user account.
* **External launch:** open an official website or application.
* **User/provider submission:** independently supplied and rights-attested feed.

Every canonical QUILL record should retain:

* Source and source record ID.
* Direct broadcaster identity.
* Metadata provenance.
* Playback authorization method.
* Attribution requirements.
* Geographic restrictions.
* Authentication requirements.
* Permitted caching period.
* Stream health and last validation.
* Codec, bitrate and latency.
* Whether recording is permitted.
* Whether the source is a station, mixed scanner feed, individual radio call, repeater, remote receiver or generated information service.

My strongest next combination would be **FMSTREAM + SHOUTcast + NOAA/NWS + RepeaterBook metadata + an accessible public-SDR prototype**. Together, those would expand QUILL well beyond another conventional radio aggregator and begin turning it into a unified accessible listening, discovery and radio-exploration platform.

[1]: https://fmstream.org/about.htm "About fmstream.org"
[2]: https://directory.shoutcast.com/Developer "
    SHOUTcast - API
"
[3]: https://www.icecast.org/docs/icecast-latest/yp/ "Listing in a YellowPage Directory - Icecast Docs"
[4]: https://radiodns.org/introduction/features/metadata/ "Service and Programme Metadata – RadioDNS"
[5]: https://openmhz.com/?utm_source=chatgpt.com "OpenMHz"
[6]: https://support.radioreference.com/hc/en-us/articles/18844460198932-Database-Web-Service-API "Database Web Service API – RadioReference Support"
[7]: https://www.repeaterbook.com/index.php/about/partners "RepeaterBook.com - Who We Partner With and Why It Matters"
[8]: https://www.echolink.org/?utm_source=chatgpt.com "Introducing EchoLink"
[9]: https://stats.allstarlink.org/?utm_source=chatgpt.com "AllStarLink Active Nodes List"
[10]: https://news.brandmeister.network/author/f4bwg/page/2/?utm_source=chatgpt.com "Oliver F4BWG – Page 2"
[11]: https://www.openwebrx.de/ "OpenWebRX web-based software defined radio | Homepage"
[12]: https://kiwisdr.com/info/?utm_source=chatgpt.com "KiwiSDR Operating Information"
[13]: https://websdr.org/background.html?utm_source=chatgpt.com "WebSDR.org - background information"
[14]: https://ubersdr.org/ "UberSDR - Software Defined Radio Platform"
[15]: https://www.liveatc.net/legal/ "Terms of Use | LiveATC.net"
[16]: https://www.railroadradio.net/?utm_source=chatgpt.com "RailroadRadio.net"
[17]: https://www.weather.gov/documentation/services-web-api?utm_source=chatgpt.com "API Web Service"
[18]: https://www.weather.gov/hnx/wxradio?utm_source=chatgpt.com "NOAA Weather Radio"
[19]: https://www.iaais.org/?utm_source=chatgpt.com "IAAIS: Home"
[20]: https://developers.radioplayer.org/api-reference "Radioplayer Partner API (WRAPI)"
[21]: https://www.airablenow.com/ "airable | internet media catalogues"
[22]: https://business.radioline.co/?utm_source=chatgpt.com "Radioline"
[23]: https://www.vtuner.com/services.asp?utm_source=chatgpt.com "Featured Products"
