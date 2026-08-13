"""No-silent-network gate (GATE-9).

Every outbound network call in Quill must be deliberate, reviewed, and tied to
an explicit user action or an explicitly consented background check. This gate
inventories every egress call site in the ``quill`` package via AST and fails if
a new one appears that is not recorded in ``_REVIEWED_EGRESS`` with a rationale.

The rationale for each site documents *what triggers it* and *why it is not a
silent call* (a user action, a visible progress/consent surface, or an opt-in
setting). A reviewer adding a new network call must add it here, which forces a
conscious decision and a code-review touchpoint.

This is the structural half of GATE-9. The runtime half — asserting the AI chat
path shows provider, model, and scope before any cloud call — lands with the
provider-wiring work (AI-13), where that call path first exists.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from quill.tools.platform_guard import build_parent_map, platform_for_node
from quill.tools.source_cache import read as source_text

_PACKAGE_ROOT = Path(__file__).resolve().parents[1]

# Egress function names. A call whose function is one of these (by attribute or
# bare name) counts as a network call for inventory purposes.
_EGRESS_CALLEES = frozenset({
    "urlopen",
    "urlretrieve",
    # The ElevenLabs SDK does its HTTP internally (httpx), so no urlopen appears at
    # the call site. Treat constructing the SDK client as the reviewable egress
    # marker — it is the single point where QUILL hands off to the SDK's network
    # path — so the gateway still gets a recorded, reviewed entry below.
    "ElevenLabs",
    # Private/authenticated podcast feeds fetch through this single wrapper
    # (quill/core/podcasts/feed_auth.py) instead of a bare urlopen, so it builds
    # its own opener (opener.open) and no plain ``urlopen`` name appears at the
    # call site. Treat the wrapper as the reviewable egress marker so every
    # private-feed fetch site is still inventoried below.
    "urlopen_auth_safe",
    # The audio-converter URL import (quill/core/audio/url_import.py) hands off to
    # yt-dlp, which does all its HTTP internally. Constructing ``yt_dlp.YoutubeDL``
    # is the single point where QUILL enters that network path, so treat it as the
    # reviewable egress marker (mirrors the ElevenLabs SDK marker above).
    "YoutubeDL",
})

# Module-qualified HTTP egress: a call like ``requests.get(...)`` or
# ``httpx.post(...)``. Matched on the *module + method* pair (never the bare
# attribute) so an ordinary ``some_dict.get(...)`` is not mistaken for a network
# call. Covers the high-level HTTP clients that do their own socket work
# internally, so no ``urlopen`` ever appears at the call site.
_EGRESS_HTTP_MODULES = frozenset({"requests", "httpx", "urllib3"})
_EGRESS_HTTP_METHODS = frozenset({
    "get",
    "post",
    "head",
    "put",
    "delete",
    "patch",
    "request",
    "Session",
    "Client",
})
# A ``requests``/``httpx`` Session/Client kept on an attribute named ``session``
# (the QuillSync/Beacon server-client pattern ``self.session.post(...)``). Matched
# only when the immediate receiver attribute is literally ``session`` so a random
# ``.get()`` cannot trip the gate.
_EGRESS_SESSION_METHODS = frozenset({
    "get",
    "post",
    "head",
    "put",
    "delete",
    "patch",
    "request",
})


def _is_qualified_egress(call: ast.Call) -> bool:
    """Return True for a module-qualified or session-object HTTP egress call.

    ``requests.get(...)`` / ``httpx.post(...)`` / ``urllib3.request(...)`` match on
    the module + method pair; ``<obj>.session.post(...)`` matches the Session
    pattern. Bare ``obj.get(...)`` never matches (no qualifying receiver).
    """

    func = call.func
    if not isinstance(func, ast.Attribute):
        return False
    receiver = func.value
    if (
        isinstance(receiver, ast.Name)
        and receiver.id in _EGRESS_HTTP_MODULES
        and func.attr in _EGRESS_HTTP_METHODS
    ):
        return True
    if (
        isinstance(receiver, ast.Attribute)
        and receiver.attr == "session"
        and func.attr in _EGRESS_SESSION_METHODS
    ):
        return True
    return False


# Reviewed, allowed egress sites: "<relative path>::<enclosing function>" mapped
# to the reason the call is not silent. Update this when adding a network call.
_REVIEWED_EGRESS: dict[str, str] = {
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
    "core/audio/url_import.py::_default_download": (
        "The Universal Audio Converter's optional URL import (#1255 §4.6): "
        "downloads the best-audio stream of a user-pasted http(s) link via yt-dlp "
        "(YouTube and the many sites yt-dlp supports) so the converter can turn it "
        "into a local audio file. Reached only by an explicit user action — pasting "
        "a link into 'Convert from URL...' and accepting the consent + rights "
        "notice — and only after yt-dlp has been installed on demand (never "
        "bundled). yt-dlp performs the HTTP itself and reaches arbitrary media "
        "hosts by design; no QUILL credential is ever sent. Disabled in Safe Mode "
        "(url_import.download_audio refuses when QUILL_SAFE_MODE=1) and gated off "
        "when the future.url_import feature is disabled."
    ),
    "core/library/http.py::fetch_bytes": (
        "Single egress site for the accessible book libraries (Part 4): keyword "
        "search of Project Gutenberg (Gutendex), Google Books, the NLS BARD "
        "public catalogue (api.nlsbard.loc.gov, a no-key POST JSON search), OPDS "
        "browsing (Standard Ebooks / Feedbooks), and downloading a chosen book's "
        "plain-text / EPUB file so it opens in QUILL's reader. Reached only by an "
        "explicit user action (searching the Library or downloading a book); no "
        "key or credential is ever sent. HTTPS-only over a verified TLS context "
        "with a bounded timeout and a size cap; disabled in Safe Mode."
    ),
    "core/ai/onboarding.py::pull_ollama_model": (
        "Streams Ollama's own /api/pull endpoint to download a model, the same "
        "call the 'ollama pull' CLI command makes. Reached only from the AI "
        "Setup Wizard's explicit Pull button on a curated-but-missing model row "
        "(Model step, local Ollama path). Defaults to http://localhost:11434 -- "
        "the same address every other Ollama call in this file already talks "
        "to -- and is user-overridable to a remote Ollama host via the wizard's "
        "own server-address field, matching that same existing pattern. Not "
        "HTTPS-enforced because localhost/LAN Ollama servers are plain HTTP by "
        "default (no TLS to verify); no secret travels in the request. Absent "
        "in Safe Mode along with the rest of AI setup."
    ),
    "core/publish/auphonic.py::_request": (
        "Single egress site for Auphonic post-production: preset list, account/"
        "credit check, production upload/start, status poll, result download. "
        "Reached only from the publish dialog's explicit buttons and the AI Hub "
        "Services tab's 'Check Account and Credits' button. "
        "Requires the user's own API token from the OS credential vault "
        "(Windows Credential Manager / macOS Keychain; never settings); every "
        "use is an explicit publish action in a dialog "
        "that names the service; absent in Safe Mode. HTTPS-only, verified TLS, "
        "bounded timeout."
    ),
    "core/metadata_lookup.py::_http_json": (
        "Single egress site for the Audio Studio's 'Look up book details' button "
        "(Open Library + MusicBrainz, both free and keyless). Reached only by that "
        "explicit button press; the UI names both services before the first call. "
        "Only the user-typed title/author is sent. HTTPS-only over a verified TLS "
        "context with a bounded timeout; MusicBrainz's 1-req/s courtesy limit is "
        "throttled in code. Disabled in Safe Mode with the rest of the Studio's "
        "network surfaces."
    ),
    "core/metadata_lookup.py::fetch_cover": (
        "Companion to the lookup above: downloads the chosen match's jacket image "
        "from covers.openlibrary.org (same free, keyless Open Library service) as "
        "cover.jpg next to the audio folder. Reached only after the user picks a "
        "match in the consented lookup flow and confirms the cover download. "
        "HTTPS-only over a verified TLS context with a bounded timeout. Disabled "
        "in Safe Mode with the rest of the Studio's network surfaces."
    ),
    "core/podcasts/download_queue.py::_fetch_chunked": (
        "Single egress site for downloading a podcast episode's audio file. "
        "Reached only via the dedicated download worker, itself only fed by "
        "explicit user actions (Download, auto-download on a show the user "
        "set to download mode) -- never a silent background fetch the user "
        "didn't opt into for that show. HTTPS-only over a verified TLS "
        "context with a bounded timeout; supports resumable Range requests "
        "for the per-item pause/resume controls."
    ),
    "core/podcasts/feed_reader.py::_fetch_once": (
        "Single egress site for podcast subscribing/refreshing: fetches one "
        "feed's raw RSS/Atom bytes (feedparser then parses locally, no "
        "further network activity). Reached only by explicit user actions "
        "(Add by Feed URL, iTunes search result subscribe, a scheduled/"
        "manual feed refresh for an already-subscribed show). HTTPS-only "
        "over a verified TLS context with a bounded timeout and response "
        "size. Private-feed Basic-auth credentials come from the OS "
        "credential store, sent only to that host. Disabled in Safe Mode via "
        "refuse_in_safe_mode; _fetch_feed_bytes retries transient failures."
    ),
    "core/podcasts/opml_import.py::_probe_once": (
        "Single egress site for the OPML import reachability check: one "
        "bounded GET per imported feed, reading only the first 2 KB to learn "
        "whether the feed still answers. Never silent and never automatic -- "
        "reached only when the user ticks 'Check that each feed is "
        "reachable' in Import OPML, which states that it makes one request "
        "per feed, shows live progress, and can be cancelled mid-sweep. "
        "Concurrency is bounded (8 workers) with a short timeout; a 401/403 "
        "counts as reachable so a private feed is never reported dead. "
        "Refused entirely in Safe Mode (validate_feeds returns 'not checked' "
        "for every feed instead of connecting). Its purpose is the pruning "
        "report: which subscriptions died, so they can be pruned. probe_feed "
        "retries transient failures -- one 503 must not prune a live feed."
    ),
    "core/podcasts/chapters.py::_fetch_chapters_bytes": (
        "Single egress site for podcast chapter navigation: fetches one "
        "episode's Podcasting 2.0 JSON chapters document (parsed locally, no "
        "further network activity). Reached only when the user opens the "
        "Chapters view for an episode that has a chapters_url. HTTPS-only "
        "over a verified TLS context with a bounded timeout and response "
        "size. Disabled in Safe Mode via chapters.refuse_in_safe_mode."
    ),
    "core/adp/client.py::ask": (
        "Single egress site for the pre-release ADP Assistant (the typed "
        "assistant is un-gated for testing; only hands-free ADP Voice Mode "
        "stays locked behind a signed unlock code): POSTs the user's typed or "
        "explicitly routed question to the hosted ADP catalog service and "
        "returns the answer. Reached only when the user presses Ask (or has "
        "explicitly enabled hands-free question routing in ADP Settings). "
        "HTTPS enforced in code over a verified TLS context with a bounded "
        "timeout; the per-app bearer key is either the user's override in the "
        "OS credential vault or the key baked into the build. Voice never "
        "leaves the device (no /api/speak, no /api/transcribe). Raises in Safe "
        "Mode."
    ),
    "core/podcasts/acb_media_podcasts.py::_fetch_opml_bytes": (
        "Single egress site for the ACB Media podcast directory: fetches "
        "ACB's published OPML subscription list (parsed locally; feeds it "
        "names are fetched only when the user later refreshes those shows). "
        "Reached only when the user runs Podcasts: Subscribe to ACB Media "
        "Podcasts explicitly. HTTPS-only over a verified TLS context with a "
        "bounded timeout and response size. Disabled in Safe Mode via "
        "feed_reader.refuse_in_safe_mode."
    ),
    "core/podcasts/transcripts.py::_fetch_transcript_bytes": (
        "Single egress site for podcast transcripts: fetches one episode's "
        "Podcasting 2.0 transcript file (VTT/SRT/JSON, parsed locally, no "
        "further network activity) and caches the parsed text so reopening "
        "never re-fetches. Reached only when the user opens the transcript "
        "view for an episode that has a transcript_url. HTTPS-only over a "
        "verified TLS context with a bounded timeout and response size. "
        "Disabled in Safe Mode via refuse_in_safe_mode."
    ),
    "core/podcasts/itunes_search.py::_fetch_once": (
        "Single egress site for Add Podcast's search: iTunes' free, keyless "
        "podcast search API. Reached only by the explicit Search action in "
        "the Add Podcast dialog. HTTPS-only over a verified TLS context with "
        "a bounded timeout. Disabled in Safe Mode via refuse_in_safe_mode; "
        "_http_json retries transient failures rather than saying 'no results'."
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
    "core/weather/_http.py::http_json": (
        "Single egress chokepoint for QUILL Weather (the top-level Weather "
        "menu, a text-first accessible weather view -- QUILL-Weather-PRD.md). "
        "Free, no-account providers are reached through it: Zippopotam.us and "
        "Nominatim/OpenStreetMap (geocoding.py -- resolve or search a US ZIP, "
        "city, county, or address the user typed into coordinates and a "
        "pick-list), the National Weather Service api.weather.gov (nws.py -- "
        "point metadata, period forecast, latest observation, and active "
        "watches/warnings/advisories), and Open-Meteo -- api.open-meteo.com "
        "for the extended daily outlook and current cloud cover, and "
        "air-quality-api.open-meteo.com for the current air-quality index "
        "(open_meteo.py). Reached only by an explicit user action "
        "(adding a location, opening Weather Now, or Refresh); the refresh "
        "cadence never polls alerts more than once per 30 seconds per NWS "
        "guidance. HTTPS-only over a verified TLS context with a bounded "
        "timeout and an identifying User-Agent (which NWS requires); no key or "
        "credential is ever sent. Disabled in Safe Mode via "
        "nws.refuse_in_safe_mode / geocoding.refuse_in_safe_mode."
    ),
    "core/mastodon/client.py::_http_payload": (
        "Single egress site for QUILL's Mastodon support (both _http_json and "
        "http_json_list funnel through it). Reached only by an explicit user action "
        "-- adding an account (app registration + OAuth token exchange), the compose "
        "dialog's one-time unauthenticated instance-limit lookup, pressing Post, or "
        "the read/interact features (view a profile, follow/unfollow, see who "
        "favourited/boosted a post, manage lists and add a user to one, read "
        "filters) -- always to the user's own instance. HTTPS-only over a verified "
        "TLS context; the access token travels in the Authorization header, never "
        "the URL."
    ),
    "core/dectalk_runtime.py::download_dectalk_runtime": (
        "User explicitly installs the optional DECTALK voice runtime; download "
        "runs with a verified TLS context and visible progress."
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
    "core/updates.py::fetch_update_manifest": (
        "Update check; gated by the user's update-check setting and shown in the "
        "update UI. Verified TLS."
    ),
    "core/updates.py::fetch_latest_release": (
        "Update check against GitHub Releases; same update setting and UI."
    ),
    "core/updates.py::fetch_app_releases": (
        "Per-app update check: lists the shared Community-Access/quill releases to "
        "find THIS app's own asset (Quill-Radio-*, Quill-Weather-*, ...) so each "
        "QuillVille app updates independently. Same gating as fetch_releases -- the "
        "app's 'check for updates' action or its throttled once-a-day startup check. "
        "Verified TLS."
    ),
    "core/updates.py::fetch_releases": (
        "Fetches release notes for an update the user is already reviewing (Help > "
        "Check for Updates) or, for the standalone companion apps (Quill Radio, "
        "QUILL Cast), a throttled once-a-day automatic startup check gated by each "
        "app's own 'check for updates automatically on launch' Preferences toggle "
        "(on by default, one checkbox away from off) -- silent unless a genuine "
        "update is found, per AppShellFrame.check_for_app_updates(silent_no_update=)."
    ),
    "core/updates.py::download_release_asset": (
        "User chooses to download an offered update; verified TLS, visible progress."
    ),
    "core/companion_install.py::fetch_companion_asset": (
        "Lists the Community-Access/quill GitHub releases to find a sibling app's "
        "installer/portable asset, only after the user answers 'yes, get it' to the "
        "offer shown when they try to open a companion app (Quill Radio/Weather/Cast, "
        "or QUILL) that is not installed. Verified TLS; the asset bytes themselves go "
        "through the already-reviewed updates.download_release_asset path."
    ),
    "core/glow_updates.py::fetch_glow_manifest": (
        "Opt-in GLOW engine update check (GLOW-8); runs only when the user invokes "
        "'Check for GLOW Updates' or enables the GLOW auto-check setting. Fetches a "
        "signed manifest over a verified TLS context and host-allow-listed HTTPS URL."
    ),
    "core/ai/elevenlabs_tts.py::_client": (
        "Constructs the host-owned ElevenLabs SDK client (roadmap §4.1, audio "
        "export only). The SDK performs HTTP via httpx, so this construction is the "
        "reviewed egress marker. Only runs when the user has selected the ElevenLabs "
        "AI Voice provider, configured an 'ElevenLabs API key', and invoked Export "
        "Document as Audio; the key is passed explicitly (never from the environment) "
        "and the SDK talks only to api.elevenlabs.io. Optional 'elevenlabs' extra; "
        "Safe-Mode and consent are enforced by the AI Voice surface."
    ),
    "core/ai/oauth_poster.py::_real_opener": (
        "OAuth 2.0 device-flow form POST (AI-19 accessible sign-in). Runs only "
        "when the user starts a provider/Copilot device login from the onboarding "
        "dialog; the device_login state machine itself stays poster-free so this "
        "is the single, explicit egress site. Verified TLS context; posts a "
        "urlencoded form to the provider's configured device/token endpoints and "
        "parses the JSON reply (including the OAuth error body on HTTP error)."
    ),
    "core/assistant_ai.py::_fetch_models_from_endpoint": (
        "User-initiated model discovery from the AI Connection dialog (Verify "
        "Connection / List Models). HTTPS uses a verified context."
    ),
    "core/assistant_ai.py::_post_chat": (
        "AI generation against the user's explicitly configured provider (AI-13). "
        "Only runs when the user has set up an AI connection and invokes an "
        "assistant action; HTTPS uses a verified context and cloud endpoints are "
        "HTTPS-enforced by _validate_endpoint_security."
    ),
    "core/assistant_ai.py::_post_chat_stream": (
        "Streaming variant of AI generation (AI-14). Same gating as _post_chat: "
        "only runs against the user's explicitly configured, non-off provider on "
        "an explicit assistant action, with HTTPS enforced for cloud endpoints by "
        "_validate_endpoint_security and a verified TLS context."
    ),
    "core/release_assets.py::_download_resumable": (
        "User-initiated on-demand fetch of a redistributable runtime component "
        "(currently the MIT whisper.cpp engine) from QUILL's own pinned, "
        "SHA-256-verified GitHub release asset (PRD 10.2.4). HTTPS enforced "
        "(refuses non-https), retry/resumable, bytes verified by SHA-256 before "
        "use, visible progress, blocked in Safe Mode. Supplements the installer "
        "bundling; capability never depends on it."
    ),
    "core/speech/piper_install.py::_download_piper_voice_files": (
        "Fallback fetch of a Piper voice (.onnx + .onnx.json) from the upstream "
        "rhasspy/piper-voices files over verified HTTPS, used only when the voice "
        "is not on QUILL's own assets-v1 mirror (the mirror, SHA-verified via "
        "release_assets, is preferred). Runs only on an explicit user 'download "
        "voice' action; refuses non-HTTPS; verified TLS context. Shared by the "
        "read-aloud UI and Audio Studio so the egress lives in one place."
    ),
    "core/speech/piper_install.py::_download_zip": (
        "User-initiated optional Piper TTS engine download (#669) from the pinned "
        "rhasspy/piper GitHub release (piper_windows_amd64.zip). HTTPS enforced "
        "(refuses non-https), verified TLS context, visible progress, blocked in "
        "Safe Mode, Windows-only. No SHA-256 pin (relies on HTTPS + official GitHub "
        "release asset). Triggered only by an explicit 'Download Piper Engine' action "
        "from the Voice Browser dialog."
    ),
    "core/datalab_ocr.py::_default_opener": (
        "Consent-gated Tier-3 cloud OCR (Datalab Chandra Convert API; PRD §5.93). "
        "Reached ONLY from the Import/Convert escalation flow after an explicit "
        "per-upload consent dialog that names the service and warns about "
        "sensitive documents (filename heuristic adds a second warning). BYOK: "
        "the API key lives in the credential vault / DATALAB_API_KEY, never "
        "settings.json, and travels only in the X-API-Key header. HTTPS "
        "enforced (refuses non-https endpoints), verified TLS context, blocked "
        "in Safe Mode, cancellable while polling. Logs job state transitions "
        "and page counts only — never file contents, OCR output, keys, or "
        "response bodies."
    ),
    "core/speech/cloud_transcribers.py::transcribe_rest": (
        "User-initiated cloud transcription via a Quillin-declared, host-vetted "
        "provider kind (#669: Groq, ElevenLabs, ...). HTTPS enforced (refuses "
        "non-https), verified TLS context, API key from the credential store, "
        "endpoint is always one of the vetted CLOUD_REST_SPECS (never arbitrary), "
        "blocked in Safe Mode, and only runs on explicit consented transcription."
    ),
    "core/speech/providers/vosk.py::_download_zip": (
        "User-initiated offline Vosk speech-model download (#669) from the official "
        "alphacephei.com model archive; HTTPS enforced (refuses non-https), verified "
        "TLS context, visible progress, blocked in Safe Mode, MD5-verified against the "
        "catalog's pinned hash, and zip-slip-guarded on extract. No silent downloads."
    ),
    "core/ai/model_manager.py::_download": (
        "User-initiated local AI model download; verified TLS for HTTPS, visible progress callback."
    ),
    "core/lexical.py::_http_get_json": (
        "Consented online dictionary/thesaurus/encyclopedia lookups (DICT-1: Free "
        "Dictionary and Datamuse; #897: Wikipedia's keyless REST summary endpoint). "
        "Only runs when the user enables online lexical lookups; HTTPS with a "
        "verified TLS context, no API key, graceful offline fallback."
    ),
    "core/publishing_clients.py::verify_connection": (
        "User-initiated publishing connection verification from the Publishing "
        "Connections dialog. Runs only when the user explicitly verifies a saved "
        "connection; remote endpoints are HTTPS-enforced and HTTPS uses a verified "
        "TLS context."
    ),
    "core/publishing_clients.py::_request_json": (
        "User-initiated publishing browse, open, create, update, and schedule "
        "requests from the Publish menu and publishing dialogs. Runs only when "
        "the user explicitly loads, sends, or schedules content through a saved "
        "connection; remote endpoints are HTTPS-enforced and HTTPS uses a "
        "verified TLS context."
    ),
    "apps/beacon/feeds.py::fetch_feed": (
        "Quill Radio/Beacon podcast subscribe + refresh: fetches one feed's raw "
        "RSS/Atom bytes (parsed locally afterwards) via requests.get. Reached only "
        "by an explicit user action -- Add by Feed URL, an iTunes search-result "
        "subscribe, or a manual/scheduled refresh of a show the user already "
        "subscribed to. Bounded timeout; no credential is sent."
    ),
    "apps/beacon/feeds.py::fetch_chapters": (
        "Beacon podcast chapter navigation: fetches one episode's Podcasting 2.0 "
        "JSON chapters document (parsed locally) via requests.get, only when the "
        "URL is not already inline JSON. Reached only when the user opens the "
        "Chapters view for an episode that advertises a chapters URL. Bounded "
        "timeout; no credential is sent."
    ),
    "apps/beacon/health.py::default_fetcher": (
        "Beacon link-health revalidation: an optional HTTP HEAD (requests.head, "
        "follow-redirects) used to check whether a saved feed/link is still live. "
        "Returned to callers only when the user has network checks on; the module "
        "itself never imports requests, and revalidate() runs on an explicit "
        "'check links' action. Bounded timeout; no body is downloaded."
    ),
    "apps/beacon/server_client.py::__init__": (
        "Constructs the hosted QuillSync server client's requests.Session (the "
        "reviewable handoff marker for the session-based push/pull/hints calls "
        "below). No network call happens here; the Session is only exercised by "
        "the sync actions, each an explicit user-initiated QuillSync operation "
        "against the user's own account, authenticated with their device token."
    ),
    "apps/beacon/server_client.py::push": (
        "Hosted QuillSync push: POSTs the user's local sync commits/objects to "
        "their configured QuillSync server (self.session.post). Reached only from "
        "an explicit Sync action on an account the user signed into; the device "
        "bearer token travels in the Authorization header. Bounded timeout."
    ),
    "apps/beacon/server_client.py::pull": (
        "Hosted QuillSync pull: POSTs the client's 'have' set and downloads the "
        "server's newer objects (self.session.post). Reached only from an explicit "
        "Sync action on the user's own signed-in account; device bearer token in "
        "the Authorization header. Bounded timeout."
    ),
    "apps/beacon/server_client.py::hints": (
        "Hosted QuillSync hints: GETs lightweight sync hints from the user's "
        "QuillSync server (self.session.get) as part of an explicit Sync action. "
        "Device bearer token in the Authorization header; bounded timeout."
    ),
    # server_client.py also has request_magic_link/verify_magic_link, whose HTTP
    # verb is called on a locally-aliased ``s = session or requests`` name
    # (``s.post`` / ``s.get``); an AST scan cannot resolve that alias, so those two
    # sites are not discovered by the gate. They are the account sign-in exchange
    # (magic-link request + verify), reached only when the user explicitly signs
    # in to a QuillSync account, over the user-supplied server base URL, bounded
    # timeout. Documented here for auditability alongside the discovered sites.
    "ui/main_frame_quillins_host.py::fetch": (
        "Quillin host 'net' capability bridge. A Quillin can only reach this "
        "method when its manifest declares the default-deny 'net' capability AND "
        "the user grants explicit per-action consent at the runtime consent gate "
        "(_EditorHostServices reaches fetch only after the host's capability + "
        "consent check passes); there is no silent path."
    ),
    # feedback_hub is an optional external library (not in quill/); its urlopen
    # call is not found by this AST scan but is documented here for auditability.
    # Two explicit-user-action call sites reach it:
    #   report_bug() -> FeedbackDialog._on_submit -> create_issue -> urlopen
    #   _send_crash_report() -> core.issue_submit.submit_crash_issue -> submit
    #       -> create_issue -> urlopen
    # The crash-report path requires an explicit consent confirmation, sends
    # only a REDACTED log summary (stability.redaction), and runs only when a
    # GitHub token is configured. Both fall back to the legacy browser/manual
    # path when feedback_hub or a token is absent.
    # #622: the crash-submit flow adds a third path:
    #   sys.excepthook -> quill.__main__._install_excepthook
    #       -> _try_offer_crash_submit (builds the redacted payload via
    #          stability.crash_submit.build_crash_report_payload)
    #       -> wx.CallAfter(schedule) -> CrashReportDialog.show()
    #       -> on Send: quill.core.issue_submit.submit_crash_issue -> submit
    #          -> create_issue -> urlopen
    # The dialog path runs only when (a) wx is alive, (b) the user has the
    # `auto_ask_crash_submit` setting enabled (default True during the beta
    # phase), and (c) the user explicitly clicks **Send report** after
    # reviewing the redacted preview. The default button is **Don't send**
    # so an accidental dialog open does not send anything. When the GitHub
    # token is absent the report is copied to the clipboard instead. The
    # local crash file is always saved regardless of the user's choice.
    # Every step is wrapped in try/except so the handler can never prevent
    # the standard interpreter traceback from firing.
    # Browser read-aloud (Experimental, opt-in): QUILL itself makes NO network
    # call here -- it writes a self-contained local HTML page (quill/core/
    # browser_reader.py) and opens it in the user's browser. The AST scan finds
    # no egress in quill/ for this feature, and there is no _REVIEWED_EGRESS
    # entry because there is no in-package call site. It is documented here for
    # auditability: when the user chooses one of the browser's "Online (Natural)"
    # voices, the *browser* (not QUILL) sends the selected text to the voice
    # service (e.g. Microsoft's Edge cloud voices) to synthesize speech. Path:
    #   read_document_in_browser() (gated behind edge_read_aloud_enabled AND
    #   experimental_acknowledged) -> write local page -> open_preview_url().
    # On-device voices stay fully local. The settings copy and docs/legal/PRIVACY.md both
    # disclose the cloud-voice behavior, and the page is deleted on app exit
    # (_cleanup_browser_reader_files) so no plaintext copy lingers.
    "io/http_transport.py::download_url": (
        "Open-from-URL action. Triggered by an explicit user action from the "
        "Remote Sites dialog (Open from URL); fetches the resource the user "
        "named with a verified TLS context, default _MAX_BYTES cap, and visible "
        "progress callback."
    ),
    "io/s3_sigv4.py::signed_request": (
        "S3 transport. Triggered only by an explicit user action from the "
        "Remote Sites dialog (Open from / Save to / Save Copy to) against a "
        "user-configured S3 site. Uses AWS Signature V4 over a verified TLS "
        "context; cloud endpoints are HTTPS-only."
    ),
    "io/s3_sigv4.py::signed_streaming_download": (
        "S3 streaming download. Same gating and TLS guarantees as signed_request; "
        "streams the response body to a temp file with a visible progress callback."
    ),
    "io/webdav_transport.py::_request": (
        "WebDAV transport. Triggered only by an explicit user action from the "
        "Remote Sites dialog against a user-configured WebDAV site. Uses "
        "urllib with a verified TLS context; HTTP allowed only when the user "
        "explicitly opts in (LAN-only) and HTTPS by default for cloud endpoints."
    ),
    "io/webdav_transport.py::download": (
        "WebDAV file download. Same gating and TLS guarantees as _request; "
        "streams the response body to a temp file with a visible progress callback."
    ),
    "core/ai_chat.py::_post_json": (
        "AI chat request. Triggered only by an explicit user action in the Ask AI "
        "dialog (Tools > Ask AI or Alt+Q). The provider, model, and prompt are "
        "chosen by the user in the dialog before sending. HTTPS enforced for cloud "
        "providers; local Ollama uses HTTP on localhost only. No silent background calls."
    ),
    "core/ai_chat.py::_get_json": (
        "AI model list fetch. Triggered when the Ask AI dialog opens or when the "
        "user changes the provider selector, to populate the model list. Same HTTPS "
        "guarantee as _post_json."
    ),
    "core/contributors.py::fetch_contributors": (
        "Developer tooling only — not called at runtime. The About screen uses the "
        "baked-in CONTRIBUTORS tuple; this function is only invoked manually by a "
        "developer running `python -m quill.core.contributors` to refresh that tuple. "
        "There is no silent runtime path."
    ),
    "core/ai/tts.py::request_speech": (
        "OpenAI TTS speech synthesis. Triggered only by an explicit user action: "
        "AI > Read Selection Aloud or AI > Read Document Aloud. The user must have "
        "configured an OpenAI-compatible provider and API key in AI Hub. Request is "
        "HTTPS-only (TTS_ENDPOINT is a hardcoded openai.com URL); no silent background calls."
    ),
    "core/ai/gemini_tts.py::request_speech_pcm": (
        "Google Gemini 2.5 TTS speech synthesis. Triggered only by an explicit user "
        "action: AI Voice read-aloud or export with the provider set to Gemini. The user "
        "must have configured a Gemini API key. HTTPS-only (endpoint is a hardcoded "
        "generativelanguage.googleapis.com URL); the key travels in the x-goog-api-key "
        "header, never in the URL; no silent background calls."
    ),
    "core/ai/transcription.py::_post_audio": (
        "OpenAI Whisper audio transcription/translation. Triggered only by an explicit "
        "user action: AI > Transcribe Audio File or AI > Translate Audio File. The user "
        "must have configured an OpenAI API key; the file is chosen interactively by the "
        "user in AITranscribeDialog. HTTPS with a verified TLS context; 25 MB size guard."
    ),
    "core/ai/diarization.py::_diarize_deepgram": (
        "Deepgram Nova-3 speaker diarization. Triggered only when the user explicitly "
        "enables speaker diarization in AITranscribeDialog and invokes the transcription "
        "action. A Deepgram API key is required. HTTPS with a verified TLS context; "
        "no silent background calls."
    ),
    "core/ai/translation.py::_translate_libretranslate": (
        "LibreTranslate local/self-hosted translation. Triggered only when the user "
        "explicitly selects LibreTranslate as the provider in AI Hub Translation settings "
        "and invokes an AI > Translate command. Default URL is localhost:5000; the user "
        "must configure an external URL to make this a remote call, so consent is "
        "embedded in the provider configuration UI."
    ),
    "core/node_install.py::_fetch_node_zip_url": (
        "User-initiated Node.js LTS runtime download (Node Quillin support). Fetches "
        "a small SHASUMS256.txt index (~5 KB) from nodejs.org/dist/latest-v{N}.x/ over "
        "verified HTTPS to resolve the current win-x64 zip filename AND its SHA-256. "
        "Runs only on an explicit 'Download Node.js runtime' action in the Quillins "
        "settings panel; blocked in Safe Mode; Windows-only. No user data is sent. "
        "The zip itself is then fetched + SHA-verified through the shared "
        "release_assets.download_verified core."
    ),
    "tools/generate_emoji_catalog.py::_fetch": (
        "Dev-only maintainer tool, never imported by the shipped app (quill.core.emoji_data "
        "reads only the committed quill/data/emoji_catalog.json this script produces offline "
        "ahead of time -- no runtime network call exists for the emoji picker). Fetches "
        "Unicode's emoji-test.txt, CLDR's English annotations, and iamcal/emoji-data's "
        "emoticon table, run by hand by a maintainer regenerating the catalog for a new "
        "Unicode emoji version (roughly annual). HTTPS-only (enforced by the function itself)."
    ),
    "tools/generate_emoji_catalog.py::_openai_batch_descriptions": (
        "Same dev-only tool as above, same never-shipped-at-runtime boundary. Sends batches "
        "of emoji names/categories/keywords (no user data, no document content) to the "
        "OpenAI chat completions API to generate original visual descriptions, only when a "
        "maintainer explicitly passes --api-key or sets OPENAI_API_KEY while running the "
        "script by hand; omitting the key skips this call entirely and falls back to a "
        "mechanical description with zero network calls."
    ),
    "core/github/items_provider.py::download_artifact_to_file": (
        "Reached only from GitHub Items' Actions... > View Artifacts... > Download "
        "Selected/All (user-initiated, requires a signed-in account -- the same gate as "
        "every other write/download action in that dialog). The one deliberate exception "
        "to 'every GitHub call goes through PyGithub': the artifact endpoint 302-redirects "
        "to a signed URL on a different host, and the Authorization header is dropped by "
        "hand for that second request (never forwarded to the redirect target) rather than "
        "trusting an auto-redirect-following opener or PyGithub's private Requester "
        "internals. HTTPS-enforced on both the initial URL and the redirect target."
    ),
    "core/spotify/auth.py::_token_request": (
        "Single egress site for Spotify's OAuth 2.0 Authorization-Code-with-PKCE "
        "sign-in: POSTs a urlencoded form to accounts.spotify.com/api/token to "
        "redeem the authorization code and to refresh the access token. Reached "
        "only from an explicit user sign-in (Connect Spotify) and the lazy token "
        "refresh that a subsequent explicit browse/play action triggers -- never "
        "a silent background poll. Gated behind the future.spotify feature flag "
        "(experimental), a one-time network-access consent, and Safe-Mode refusal "
        "(auth.refuse_in_safe_mode). No client secret exists (PKCE); the injected "
        "opener stays test-only and the default performs the real request over a "
        "verified TLS context (HTTPS enforced in code) with a bounded timeout. "
        "The code_verifier travels in the POST body, never a URL."
    ),
    "core/spotify/client.py::_request": (
        "Single egress site for the Spotify Web API (search, the signed-in "
        "profile, saved shows/episodes/tracks, and playlists -- the Radio/Cast "
        "browse surfaces). Reached only from explicit user browse actions after "
        "sign-in; same future.spotify flag + one-time consent + Safe-Mode gating "
        "as the token exchange above. HTTPS-only (api.spotify.com) over a verified "
        "TLS context with a bounded timeout; the access token travels in the "
        "Authorization: Bearer header, never in the URL. The injected opener is "
        "test-only; the lazy, lock-guarded token refresh goes through the already "
        "reviewed core/spotify/auth.py::_token_request site."
    ),
}

# ---------------------------------------------------------------------------
# PyGithub egress — manually documented (not AST-scannable)
# ---------------------------------------------------------------------------
# PyGithub (github.com/PyGithub/PyGithub) makes HTTPS calls internally via
# urllib3.  Its call sites never appear in quill/ source as direct
# urllib/socket/requests calls, so the AST scanner cannot find them.
# The integration surface is documented here for auditability.
#
# Entry points in quill/core/github/github_provider.py (single-file browse/write):
#   get_identity()    - GitHub API: GET /user
#   get_repository()  - GitHub API: GET /repos/{owner}/{repo}
#   list_refs()       - GitHub API: GET branches + tags for a repo
#   get_file()        - GitHub API: GET /repos/{owner}/{repo}/contents/{path}
#   save_file()       - GitHub API: PUT /repos/{owner}/{repo}/contents/{path}
#
# Entry points in quill/core/github/items_provider.py (issues/PRs/branches/
# commits/tags/releases/workflow runs viewer, plus its write actions):
#   fetch_issues/fetch_pulls/fetch_branches/fetch_commits/fetch_tags/
#   fetch_releases/fetch_workflow_runs/fetch_pull_diff/fetch_file_text/
#   fetch_issue_comments/search_items - GitHub API: GET (read-only)
#   update_items()          - GitHub API: PATCH issue state, POST labels
#   create_issue()          - GitHub API: POST /repos/{owner}/{repo}/issues
#   create_pull_request()   - GitHub API: POST /repos/{owner}/{repo}/pulls
#   merge_pull_request()    - GitHub API: PUT .../pulls/{n}/merge
#   rerun_workflow_run()    - GitHub API: POST .../actions/runs/{id}/rerun
#   create_comment()        - GitHub API: POST .../issues/{n}/comments
#   edit_comment()          - GitHub API: PATCH .../issues/comments/{id}
#   delete_comment()        - GitHub API: DELETE .../issues/comments/{id}
#
# Entry points in quill/core/github/repo_admin.py (repository lifecycle;
# every method requires an authenticated token -- no anonymous path):
#   create_repository()        - GitHub API: POST /user/repos or /orgs/{org}/repos
#   fork_repository()          - GitHub API: POST .../forks
#   rename_repository()        - GitHub API: PATCH /repos/{owner}/{repo} (name)
#   set_visibility()           - GitHub API: PATCH /repos/{owner}/{repo} (private)
#   set_default_branch()       - GitHub API: PATCH /repos/{owner}/{repo} (default_branch)
#   set_branch_protection()    - GitHub API: PUT .../branches/{branch}/protection
#   remove_branch_protection() - GitHub API: DELETE .../branches/{branch}/protection
#   delete_branch()            - GitHub API: DELETE .../git/refs/heads/{branch}
#   commit_files()             - GitHub API: POST .../git/trees, .../git/commits,
#                                 then PATCH .../git/refs/heads/{branch} (fast-forward
#                                 only -- refused, not force-pushed, if the branch
#                                 has moved since it was read)
#
# Gating: all calls are triggered by explicit user actions in the GitHub
# dialogs (File > Open from Remote > GitHub, the GitHub Items viewer's
# Batch.../Actions... menus, and Tools > GitHub). A one-time consent dialog
# fires before any network call on first use. Every write in items_provider.py
# and every method in repo_admin.py additionally requires a signed-in token --
# the anonymous/read-only session is refused outright -- and every write is
# named explicitly in its own confirmation dialog before it runs; the four
# highest-consequence repo_admin.py actions (rename, delete a branch, and
# anything else routed through TypedConfirmDialog) require retyping the exact
# name/number rather than a plain Yes/No. Tokens are stored in the OS secure
# credential store only (Windows Credential Manager / macOS Keychain), never
# logged. All PyGithub calls are HTTPS.

# ---------------------------------------------------------------------------
# Spotify Web Playback SDK egress (inside the WebView) — manually documented
# ---------------------------------------------------------------------------
# Playing Spotify Premium audio is only possible through Spotify's own Web
# Playback SDK, which QUILL hosts in a hidden wx.html2.WebView (Edge/WebView2
# on Windows -- quill/ui/spotify/web_player.py). Two network activities happen
# INSIDE that WebView2 browser process, performed by the SDK / page JavaScript,
# not by any urllib/requests call in quill/ source -- so the AST scanner above
# cannot see them. They are documented here for auditability:
#
#   1. The page loads the SDK script from https://sdk.scdn.co/spotify-player.js
#      and the SDK opens its own connections to open.spotify.com / *.scdn.co to
#      stream the DRM-protected audio (Encrypted Media Extensions inside the
#      browser engine). QUILL never sees, decodes, or stores that audio.
#   2. window.quillSpotifyPlay(uri) issues one fetch() to
#      https://api.spotify.com/v1/me/player/play?device_id=... (PUT, the user's
#      Bearer token in the Authorization header, the chosen spotify: URI in the
#      body) to point the SDK device at what to play.
#
# Gating: the whole feature is behind the future.spotify feature flag
# (experimental), a one-time network-access consent (spotify_consent.json),
# Safe-Mode refusal, and -- the Web Playback SDK being Premium-only -- a Spotify
# Premium account. The hidden WebView is created only after the user explicitly
# connects Spotify and starts playback; nothing reaches Spotify before that.
# The access token the page uses is fetched through the reviewed
# core/spotify/auth.py::_token_request / client.py::_request sites above.
#
# ---------------------------------------------------------------------------
# pip subprocess egress (on-demand engine installs) — manually documented
# ---------------------------------------------------------------------------
# The three optional speech-engine installs below each run the runtime's own pip
# in a subprocess (`python -m pip install --only-binary=:all: --target <user dir>
# <pkg> ...`).  The network call is performed by pip reaching PyPI / pythonhosted,
# not by an urlopen in quill/ source, so the AST scanner above cannot see them;
# they are documented here for auditability.
#
# All three share the same gating pattern: explicit user action only, behind a
# visible confirmation and progress dialog, blocked in Safe Mode, wheel-only
# (no build backend / arbitrary code), installed into a user-writable engine-pack
# folder (no admin), no silent path.
#
# quill/core/speech/engine_install.py::install_faster_whisper
#   Installs faster-whisper>=1.0 and huggingface_hub>=0.20 (~110 MB).
#   Triggered: Tools > Speech > Whisperer > Download Faster Whisper engine.
#
# quill/core/speech/engine_install.py::install_vosk
#   Installs vosk>=0.3.45 (~50 MB).
#   Triggered: Manage Speech Models > Install Vosk, or Tools > Speech > Install Vosk.
#
# quill/core/speech/engine_install.py::install_kokoro_onnx
#   Installs kokoro-onnx>=0.5.0 and soundfile>=0.14.0 (~20 MB + onnxruntime transitive).
#   Triggered automatically alongside the Kokoro model files via
#   Help > Download Optional Components.
#
# quill/core/ai/sdk_install.py::install_pack
#   On-demand install of an optional agentic SDK pack (GitHub Copilot SDK,
#   Claude Agent SDK, or OpenAI Agents SDK) into <app data>/ai-packs/<pack>,
#   wheel-only via `python -m pip install --only-binary=:all: --target <dir>
#   <requirement>`. Same gating as the speech engines: explicit user action only
#   (the AI engine switcher / Copilot onboarding dialog), visible progress,
#   blocked in Safe Mode, no admin, no silent path. The SDKs are deliberately not
#   bundled in the installer (large, fast-moving, one-of-three).
#
# quill/core/pdf_ocr_install.py::install_pdf_ocr_support
#   On-demand install of the free PDF/Office text-extraction pack (MarkItDown,
#   pdfplumber, pypdf; ~30 MB) into <app data>/engine-packs/pdf-ocr, wheel-only,
#   same gating as the speech engines. Triggered: Help > Download Optional
#   Components > "PDF and Office text extraction". #909's original bug (a build
#   with no PDF/Office text extractor anywhere) is fixed by this being one click
#   away on every install, not by forcing it onto installs that never need it.
#
# quill/core/speech/providers/whispercpp.py::_download_to_file
#   whisper.cpp GGML model download (#617), fetched via
#   huggingface_hub.hf_hub_download (repo_id/filename/revision), same library
#   quill/core/speech/providers/fasterwhisper.py::_download_repo already uses
#   via snapshot_download. Neither call is an urlopen/urlretrieve, so the AST
#   scanner cannot see them; documented here for auditability. Both are
#   user-initiated (Manage Speech Models > Download), blocked in Safe Mode,
#   HTTPS-only (the Hub SDK never falls back to plaintext), and sha256-verified
#   when a hash is known.

# ---------------------------------------------------------------------------
# git subprocess egress (Vault Sync, Sync Folder with GitHub) — manually documented
# ---------------------------------------------------------------------------
# `git pull`/`git push` run in a subprocess (`git -C <root> pull/push ...`);
# the network call is performed by the user's own git installation reaching
# their configured remote (typically, but not necessarily, github.com), not
# by an urlopen in quill/ source, so the AST scanner above cannot see it.
# QUILL never stores or injects a credential for these calls -- both features
# rely entirely on the user's own git installation and its own credential
# handling (an SSH key, or a stored HTTPS credential via the system git
# credential manager), exactly as running `git push` from a terminal already
# would outside QUILL. This is the deliberate "reuse git as the sync engine
# instead of building QUILL's own" design (see quill/core/git_sync.py); the
# much larger custom-sync-engine design in the retired
# docs/planning/quill-sync-plan.md was not built.
#
# quill/core/vault/sync.py::run_vault_sync
#   Commits, pulls, and pushes an Accessible Vault over its git remote.
#   Triggered: Tools > Vault > Sync Vault (explicit user action only).
#   Blocked in Safe Mode. Conflicts are listed, never auto-resolved.
#
# quill/core/git_sync.py::sync_folder_via_git, ::init_repo_with_remote
#   The general-purpose form: commits, pulls, and pushes *any* folder the
#   user chooses (delegating to run_vault_sync above for the actual
#   commit/pull/push), plus `git init`/`git remote add origin <url>` when the
#   chosen folder is not yet set up -- only after an explicit confirmation
#   dialog states exactly what will run. Triggered: Tools > Sync Folder with
#   GitHub... (explicit user action only). Blocked in Safe Mode.
#
# quill/core/local_git.py (Tools > Local Git; 0.9.0 Beta 3, docs/planning/
# github.md section 4) -- listed here for the same subprocess-boundary
# auditability, though unlike the two entries above this module makes **no
# network calls at all**: status, diff, stage/unstage, branch list/switch,
# stash, blame, bisect, and interactive rebase are all local-only git
# operations (no push/pull/fetch anywhere in the module). Executable
# resolution goes through quill/core/git_binaries.py's allowlist
# (git/git.exe/gh/gh.exe only). Blocked in Safe Mode out of caution
# (consistent with every other git-touching command), even though nothing
# here actually reaches the network.
#
# quill/core/github/gh_bridge.py (Tools > GitHub > Codespaces.../Create
# Codespace.../Ask Copilot for a Command.../Explain a Command...; 0.9.0
# Beta 3, docs/planning/github.md section 1's Tier 3) -- `gh codespace
# list/create/stop/delete/ssh` and `gh copilot suggest/explain` run in a
# subprocess exactly like git_sync.py's git calls above; the network call
# (when one happens -- listing/creating/stopping/deleting a codespace, or
# Copilot's own API call for a suggestion) is performed by the user's own
# `gh` installation reaching api.github.com and Copilot's service using
# `gh`'s own stored auth, not by an urlopen in quill/ source. QUILL never
# stores or injects a credential for these calls. Gated on the same
# executable allowlist as local_git.py above, Safe Mode, and (for
# create-codespace specifically) an explicit confirmation naming the cost/
# quota implication before the call runs -- Codespaces is the one GitHub
# integration command in QUILL with a real dollar cost. **Needs live-device
# verification** (see the module's own docstring): unit-tested with a fake
# `gh` runner, not yet exercised against a real `gh` install, a real
# Codespaces-enabled repository, or real Copilot CLI access.

# ---------------------------------------------------------------------------
# ffmpeg subprocess egress (Sound Enhancements relay: Radio + Podcasts) — manually documented
# ---------------------------------------------------------------------------
# quill/core/audio_enhance.py::EnhanceRelay.start
#   Spawns `ffmpeg -i <source> -af <filters> ... pipe:1` in a subprocess
#   (build_relay_command) so the source (a live radio stream or a podcast
#   episode) is filtered (EQ preset / compressor) before playback, exactly
#   like radio recording's
#   existing ffmpeg subprocess (core/radio/recording.py, already documented
#   in module_size_budgets.json, not a new pattern). Not an urlopen in quill/
#   source, so the AST scanner above cannot see it. The source is never
#   attacker-controlled shell text -- it's the station or episode the user
#   already chose to play, passed as one argv element (never through a
#   shell). Reached only when the user turns on Playback > Sound
#   Enhancements... (off, and this relay never starts, by default). ffmpeg's
#   own bytes never leave the machine either: they're written to a
#   127.0.0.1-only loopback HTTP server (_RelayHTTPServer) that the existing
#   player engine reads from instead of the source's own URL -- no new
#   remote surface, just a local relay in front of a fetch the engine would
#   otherwise make itself.


def _enclosing_function_name(tree: ast.AST, target: ast.AST) -> str:
    """Return the nearest enclosing def/async-def name for ``target``."""
    best = "<module>"
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for descendant in ast.walk(node):
                if descendant is target:
                    best = node.name
                    # Keep walking: a more deeply nested function is a better
                    # match, and ast.walk visits outer nodes first.
    return best


def _callee_name(call: ast.Call) -> str | None:
    func = call.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


@dataclass(frozen=True)
class EgressSite:
    """One discovered egress call site: its enclosing function and platform tag."""

    function: str
    #: ``"darwin"`` when the call sits inside a ``sys.platform == "darwin"``
    #: branch (Mac-only, never exercised on the Windows dev box); ``""`` otherwise.
    platform: str


@lru_cache(maxsize=1)
def _scan_egress() -> dict[str, EgressSite]:
    """Scan the package once, returning ``{site: EgressSite}`` for every call.

    ``discover_egress_sites`` (the function-to-name map the gate enforces on) and
    ``discover_egress_platforms`` (the Mac-only tagging the review surfaces) both
    derive from this single pass so the two views cannot drift apart. Cached for
    the process lifetime: the scan parses every module in the package, and a
    single gate run or test session calls the derived views several times.
    """
    sites: dict[str, EgressSite] = {}
    for path in sorted(_PACKAGE_ROOT.rglob("*.py")):
        source = source_text(path)  # 60% of this scan is disk I/O
        tree = ast.parse(source, filename=str(path))
        parents = build_parent_map(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and (
                _callee_name(node) in _EGRESS_CALLEES or _is_qualified_egress(node)
            ):
                rel = path.relative_to(_PACKAGE_ROOT).as_posix()
                func_name = _enclosing_function_name(tree, node)
                site = f"{rel}::{func_name}"
                # Same-site duplicates collapse; cross-function duplicates with
                # the same enclosing function are not possible by construction
                # (one entry per function). Two egress calls in the same function
                # would share the key, so keep the first to preserve the prior
                # behavior.
                sites.setdefault(site, EgressSite(func_name, platform_for_node(parents, node)))
    return sites


def discover_egress_sites() -> dict[str, str]:
    """Return ``{"<rel path>::<function>": "<enclosing function name>"}``.

    The gate enforces that every key here is reviewed in ``_REVIEWED_EGRESS``.
    The value is the enclosing function name (kept for parity with prior
    behaviour; the platform tag lives in :func:`discover_egress_platforms`).
    """
    return {site: record.function for site, record in _scan_egress().items()}


def discover_egress_platforms() -> dict[str, str]:
    """Return ``{site: platform}`` -- ``"darwin"`` for Mac-only sites, ``""`` else.

    Informational, not enforcement: the reviewed-set gate is key-based and
    unaffected by platform. A Mac-only egress site cannot be exercised on the
    Windows dev box or in Windows CI, so surfacing it here lets a reviewer see
    which reviewed entries only show their real behaviour on a Mac.
    """
    return {site: record.platform for site, record in _scan_egress().items()}


def find_unreviewed_egress() -> tuple[set[str], set[str]]:
    """Return (unreviewed_sites, stale_reviewed_entries)."""
    discovered = set(discover_egress_sites())
    reviewed = set(_REVIEWED_EGRESS)
    return discovered - reviewed, reviewed - discovered
