"""Quill Radio's reviewed outbound call sites.

Split from :mod:`quill.tools.network_egress_entries` under GATE-11 -- extract,
never rebaseline -- and it is a real seam: Radio reaches more networks than
anything else in the family (station directories, stream resolvers, YouTube,
song metadata, the ACB schedule), so it is the block that grows, and it grows
for reasons that have nothing to do with the editor's or Cast's.

The review *is* the entry. Each string records what is sent, what comes back,
what triggers it, and what Safe Mode does -- so a reader can tell whether a
call site is still doing what somebody once agreed it could.
"""

from __future__ import annotations

RADIO_EGRESS: dict[str, str] = {
    "core/radio/youtube.py::_default_resolver": (
        "Quill Radio's YouTube stations (#1268): asks yt-dlp for the audio stream "
        "URL behind a YouTube page the listener saved as a station, so the player "
        "and the recorder can treat it like any other stream. download=False -- "
        "nothing is written to disk here; the media itself is streamed by the "
        "player, or captured by ffmpeg for a recording the listener asked for. "
        "Reached only for a station the listener explicitly added after accepting "
        "the one-time consent + rights notice (RadioHistory.youtube_consented), "
        "and only once yt-dlp has been installed on demand (never bundled). "
        "Re-resolved on every play because YouTube's stream addresses expire; the "
        "resolved URL is never persisted. Refused when QUILL_SAFE_MODE=1."
    ),
    "core/radio/youtube.py::_default_search_resolver": (
        "Quill Radio's YouTube search source in Find Stations: runs a "
        "'ytsearchN:<query>' through yt-dlp so YouTube videos appear alongside "
        "the radio directories. Triggered ONLY by the listener typing a search "
        "and only while the YouTube source is switched on -- Search Sources... "
        "gates the fan-out itself, so a listener who turns YouTube off stops "
        "this request happening at all rather than having its results discarded. "
        "Refused in Safe Mode. Flat (extract_flat='in_playlist'), so the whole "
        "result set is one request and no video's audio is resolved until it is "
        "actually played. download=False: nothing is written to disk, and only "
        "the query text is sent -- no account, credential, or identifier. Uses "
        "yt-dlp's keyless extraction rather than the YouTube Data API, which "
        "would require every listener to create a Google Cloud project and paste "
        "an API key in front of a search box."
    ),
    "core/radio/youtube.py::_default_playlist_resolver": (
        "Quill Radio's YouTube playlists: lists the videos in a playlist link the "
        "listener pasted, so the playlist can be browsed. Deliberately a FLAT "
        "listing (extract_flat='in_playlist'): it returns each entry's id and "
        "title without visiting any video's page, so opening a fifty-video "
        "playlist is one request rather than fifty -- far less traffic than the "
        "listener implied by asking for a list -- and no video's audio is resolved "
        "until it is actually played (that goes through _default_resolver above, "
        "with its own re-resolve-on-every-play rule). download=False, so nothing "
        "is written to disk. Reached only from an explicit paste of a playlist "
        "link, after the same one-time consent + rights notice YouTube stations "
        "already require, and only once yt-dlp has been installed on demand "
        "(never bundled). Refused when QUILL_SAFE_MODE=1."
    ),
    "core/radio/acb_calendar.py::_fetch_ics": (
        "Single egress site for the ACB Media programme schedule: one HTTPS "
        "GET of ACB's My Calendar iCalendar export (their REST API is off, so "
        "the ICS feed is the data path), parsed locally by core/radio/ics.py "
        "with no dependency and no second request -- the feed names streams by "
        "category and the stream addresses are already bundled in "
        "core/radio/acb_media.py, so nothing is looked up. Reached when the "
        "listener opens the ACB Media Schedule window and its cache has aged "
        "out (one hour), or when they press Refresh; there is no background "
        "timer. Verified TLS context, bounded timeout, and the response is "
        "text only. Safe Mode answers from the cache and never fetches."
    ),
    "core/radio/youtube_channels.py::_flat_entries": (
        "Single egress site for following a YouTube channel with no Google "
        "account: yt-dlp enumerates a channel's uploads and playlists FLATLY "
        "(extract_flat), so a four-thousand-video channel costs one request "
        "rather than four thousand stream resolutions. Reached only by adding a "
        "channel or opening one of its folders, and paged with a More... node "
        "so no level is unbounded. yt-dlp is never bundled -- it installs on "
        "demand behind the existing one-time YouTube consent and rights notice, "
        "and its absence is reported in words. A video's real stream is resolved "
        "at play time by the existing youtube.py path, not here. Disabled in "
        "Safe Mode via refuse_in_safe_mode."
    ),
    "core/radio/my_servers.py::_fetch": (
        "Single egress site for servers the LISTENER adds by hand: Icecast's "
        "status-json.xsl and SHOUTcast's /stat and /7.html, read to list what "
        "that server is currently serving. Reached only by adding a server or "
        "opening one; no credential is ever attached and nothing but a GET is "
        "sent. NOTE, DELIBERATE EXCEPTION: this is the one site that accepts "
        "plain http as well as https. A large share of small Icecast boxes are "
        "http on a high port and always have been, and refusing them would "
        "refuse the community stations, churches and reading services this "
        "branch exists to reach. The address is one the user typed. Bounded "
        "timeout and response size; disabled in Safe Mode."
    ),
    "core/radio/wikidata.py::_fetch": (
        "Single egress site for Explore (Wikidata): one SPARQL query per browse "
        "axis, returning call signs and the city/owner/network/format that "
        "groups them. OFF BY DEFAULT and labelled as derived -- Wikidata "
        "supplies only the organisation, and every playable stream still comes "
        "from Radio Browser. Cached for a week because a SPARQL query per "
        "expand would be unreasonable. Descriptive User-Agent (the endpoint "
        "requires one), HTTPS-only over a verified TLS context with a bounded "
        "timeout and size; disabled in Safe Mode."
    ),
    "core/radio/musicbrainz.py::_fetch": (
        "Single egress site for song-history enrichment: release, year and "
        "length for an artist/title pair Quill Radio already logged. STRICTLY "
        "OPT-IN, never blocking playback, and degrading to nothing on any "
        "failure. MusicBrainz's documented one-request-per-second limit is "
        "enforced inside this module rather than trusted to callers, and their "
        "required descriptive User-Agent is sent. Results cached for a month. "
        "HTTPS-only over a verified TLS context; disabled in Safe Mode."
    ),
    "core/radio/internet_archive.py::_fetch": (
        "Single egress site for the Internet Archive browse branch: "
        "advancedsearch.php for a collection's sub-collections and recordings, "
        "and the item metadata endpoint for one item's files. Keyless. Reached "
        "only by expanding an Archive folder or opening an item; results are "
        "cached (core/radio/directory_cache.py) because the Archive's own "
        "automated-access policy asks for caching, and that policy's other "
        "requirements are honoured here too -- a descriptive User-Agent naming "
        "the tool and version, one request at a time, and Retry-After respected "
        "on HTTP 429 rather than retried blindly. HTTPS-only over a verified TLS "
        "context with a bounded timeout and response size. Disabled in Safe Mode "
        "via refuse_in_safe_mode."
    ),
    "core/radio/media_download.py::_fetch_to_file": (
        "Saving a bounded recording to a file: a LibriVox or Gutenberg chapter, "
        "a rights-safe Internet Archive item, a ccMixter upload, or a podcast "
        "episode. Reached only when the listener chooses Download on a row, and "
        "only after core/radio/downloadable.can_download has affirmatively "
        "allowed that source -- an unknown source is refused rather than "
        "guessed at, and a live stream is refused outright because there is no "
        "file. Resumable via a Range header on a .part file, read in bounded "
        "chunks so a cancel takes effect inside a file, capped at "
        "MAX_FILE_BYTES, HTTPS/HTTP with a bounded timeout and a Quill Radio "
        "User-Agent. No new hosts: every address comes from a directory the "
        "browse tree already reached."
    ),
    "core/radio/audiopub.py::_fetch": (
        "AudioPub (audiopub.site) community audio, Discover shelf only: one "
        "GET to /quickfeed/api?page=N (50 randomized items) plus playback of "
        "the audio URLs those rows carry. Reached only by expanding the "
        "AudioPub branch; deliberately uncached (the server shuffles, and "
        "uploaders keep the rights to their audio, so nothing is stored). "
        "HTTPS-only over a verified TLS context with bounded timeout and "
        "size. Disabled in Safe Mode."
    ),
    "core/radio/free_music.py::_fetch": (
        "Single egress site for three keyless music directories: Audius "
        "(trending and trending-by-genre; an app_name parameter identifies the "
        "caller, there is no key or token), Mixcloud (categories and a "
        "category's shows -- METADATA ONLY, Mode A: no stream URL is ever "
        "extracted and playing a show opens it in the user's own browser), and "
        "ccMixter (Creative Commons uploads, whose rows carry a direct audio URL "
        "and an explicit licence). Reached only by expanding one of those "
        "branches; cached via core/radio/directory_cache.py. HTTPS-only over a "
        "verified TLS context with bounded timeout and size, and HTTPException "
        "is caught alongside OSError because ccMixter emits an oversized HTTP "
        "header at larger page sizes. Disabled in Safe Mode."
    ),
    "core/radio/gutendex.py::_fetch": (
        "Single egress site for Project Gutenberg audiobooks via Gutendex, "
        "keyless. Reached only by expanding that branch; cached for a week via "
        "core/radio/directory_cache.py. A descriptive User-Agent is required "
        "rather than polite -- Gutendex answers HTTP 403 to an anonymous "
        "fetcher. HTTPS-only over a verified TLS context with a bounded timeout "
        "and response size. Disabled in Safe Mode via refuse_in_safe_mode."
    ),
    "core/radio/link_finder.py::_http_get_text": (
        "Single egress site for 'Find Streams from a Website...': fetches the "
        "one page the user typed to look for a station's own stream link "
        "(audio/source tags, playlist-shaped hrefs). Reached only by the "
        "explicit Scan button, which states the exact URL before fetching. "
        "HTTPS-first over a verified TLS context, bounded timeout and "
        "response size; on a certificate *hostname* failure only, _fetch_html "
        "retries the www-toggled host (still fully verified) and then the "
        "plain-http entry point so the server's own redirect can land on its "
        "valid https home (the www.magic104.com case) -- verification is "
        "never relaxed. Disabled in Safe Mode via "
        "link_finder.refuse_in_safe_mode."
    ),
    "core/radio/triton.py::_fetch_api": (
        "Follow-on egress for 'Find Streams from a Website...' when the scanned "
        "page is a Triton Digital / StreamTheWorld web player (e.g. the "
        "player.listenlive.co network). Such players compute their stream URL "
        "in JavaScript, so it never appears in the page HTML; this resolves the "
        "callsign the page advertises to a real playable mount through Triton's "
        "JS-free provisioning API (playerservices.streamtheworld.com). One "
        "HTTPS GET, reached only from the same explicit Scan button and only "
        "for pages that look like Triton players (triton.page_is_triton_player). "
        "HTTPS-only over a verified TLS context, bounded timeout and response "
        "size. Disabled in Safe Mode via triton.refuse_in_safe_mode."
    ),
    "core/radio/tunein.py::_fetch": (
        "Single egress site for the TuneIn directory source (via RadioTime's "
        "open OPML endpoints opml.radiotime.com): search, browse, and resolving "
        "a station guide id to its playable stream. Reached only by explicit "
        "user actions (a TuneIn search/browse in the station browser, or playing "
        "a TuneIn result) -- never a background poll. No API key or auth; "
        "partnerId=RadioTime is the web player's own public partner string. "
        "Returns only what the user searched for / a page already advertises, "
        "the same shape as the Triton provisioning API above. HTTPS-only over a "
        "verified TLS context, bounded timeout and response size. Disabled in "
        "Safe Mode via tunein.refuse_in_safe_mode. (Reverses the prior TuneIn "
        "non-goal; approved 2026-07-17, PRD §5.84f.)"
    ),
    "core/radio/iheart.py::_fetch": (
        "Single egress site for the iHeart directory source, reaching two "
        "public iHeart endpoints, no API key or auth: (1) the XML sitemap "
        "(www.iheart.com/sitemap.xml + its livestations sub-sitemap, two GETs "
        "to refresh the station list) plus a lazy per-station page GET to "
        "extract the stream the page already embeds (revma.ihrhls.com HLS or a "
        "StreamTheWorld redirect) -- used by Search; and (2) iHeart's free, "
        "keyless JSON content API (us.api.iheart.com: GET /content/genre for "
        "the browsable genre list, GET /content/liveStations?genreId= for one "
        "genre's live stations, each row already carrying its own stream URLs "
        "so no per-station page fetch) -- used by the Browse Stations genre "
        "tree. robots permits /sitemap/ and /live/. Reached only by an explicit "
        "Refresh, browse-expand, or play action -- never a background poll, and "
        "never a bulk crawl. HTTPS-only over a verified TLS context, bounded "
        "timeout and response size. Disabled in Safe Mode via "
        "iheart.refuse_in_safe_mode."
    ),
    "core/radio/m3u_catalog.py::_fetch": (
        "Single egress site for the Community M3U catalog source: the public "
        "junguler/m3u-radio-music-playlists GitHub repo -- one GET to "
        "api.github.com for the genre listing (git tree) and one GET to "
        "raw.githubusercontent.com for a chosen genre's .m3u playlist, parsed "
        "into stations. No API key or auth. Reached only by an explicit browse "
        "or Refresh action, never a background poll and never a bulk crawl (one "
        "genre at a time); the ~1.7 GB repo is read on demand, never bundled or "
        "redistributed. HTTPS-only over a verified TLS context, bounded timeout "
        "and response size. Disabled in Safe Mode via m3u_catalog.refuse_in_safe_mode."
    ),
    "core/radio/xiph.py::_fetch": (
        "Single egress site for the Xiph/Icecast public directory source "
        "(dir.xiph.org, the long-running keyless Icecast yellow pages): one GET "
        "for the /genres index and one GET for a /genres/<name> page, whose "
        "station cards each advertise a directly-playable stream URL. No API key "
        "or auth (the directory has no JSON/OPML API, so its public HTML is "
        "read). Reached only by an explicit browse or Refresh action, never a "
        "background poll and never a bulk crawl (one genre at a time). HTTPS-only "
        "over a verified TLS context, bounded timeout and response size. Disabled "
        "in Safe Mode via xiph.refuse_in_safe_mode."
    ),
    "core/radio/radio_browser.py::_http_json": (
        "Single egress site for the Internet Radio feature: station search, "
        "tag/country lists, and click-through vote registration against "
        "radio-browser.info, a free, keyless, community-run station directory. "
        "Reached only by explicit user actions (search box submit, opening the "
        "station browser, playing a station) -- never a background poll. "
        "HTTPS-only over a verified TLS context with a bounded timeout. "
        "Disabled in Safe Mode via radio_browser.refuse_in_safe_mode."
    ),
    "core/radio/wxindex_http.py::_default_fetch": (
        "Single egress site for the NOAA Weather Radio (WeatherIndex) directory: "
        "states, stations, search, and detail. HTTPS-only over a verified TLS "
        "context with a bounded timeout. Disabled in Safe Mode via "
        "`wxindex_http.refuse_in_safe_mode`."
    ),
    "core/radio/soma_fm.py::_http_text": (
        "Single egress site for the SomaFM station source (a free, keyless, "
        "curated directory), blended into the same Browse Stations search "
        "results as RadioBrowser -- fetches the channel list, and, only for "
        "channels matching the user's search text, resolves that channel's "
        ".pls playlist to a real stream URL. Reached only by an explicit "
        "search box submit, never a background poll. HTTPS-only over a "
        "verified TLS context with a bounded timeout. Disabled in Safe Mode "
        "via soma_fm.refuse_in_safe_mode."
    ),
    "core/radio/icy.py::read_stream_title": (
        "What's Playing / announce-track-titles: one short side connection to "
        "the SAME stream URL the user is already playing (no third party), "
        "reading only the first ICY metadata block. Runs off-thread on a "
        "playback-driven cadence or the explicit What's Playing command; "
        "callers are blocked in Safe Mode with the rest of Internet Radio."
    ),
    "core/radio/station_status.py::_http_get_text": (
        "What's Playing free fallback (#1111): reads the current track from the "
        "station server's own Icecast/SHOUTcast status endpoint "
        "(/status-json.xsl, /stats, /7.html) on the SAME host the user is "
        "already streaming (no third party). Reached only when the ICY tap and "
        "the player's in-band title both gave nothing; runs off-thread on the "
        "same playback-driven cadence / What's Playing command as the ICY read, "
        "reads one small bounded response, and is refused in Safe Mode via "
        "read_server_now_playing's safe_mode guard."
    ),
}


__all__ = ["RADIO_EGRESS"]
