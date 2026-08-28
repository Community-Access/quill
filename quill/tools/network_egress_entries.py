"""Every reviewed outbound call site, and why each one is allowed.

Extracted from ``network_egress_audit`` under GATE-11 (extract, never
rebaseline), and it is a real seam rather than a convenient one: this file is
**data** -- which sites have been reviewed and the reasoning for each -- and it
grows every time a feature reaches the network. The tool that walks the source
tree looking for *unreviewed* sites is logic, and it changes almost never.

Adding an entry here is the review. The text is the record of what was checked:
what is sent, what comes back, what triggers it, and how it behaves in Safe Mode.
"""

from __future__ import annotations

from quill.tools.network_egress_entries_radio import RADIO_EGRESS

_REVIEWED_EGRESS: dict[str, str] = {
    # Quill Radio's, split out under GATE-11 -- see the module beside this one.
    **RADIO_EGRESS,
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
    "core/community_picks.py::_fetch": (
        "Single egress site for the Community Picks catalogue: one HTTPS GET of "
        "https://quillforall.org/picks/v1/picks.json, a static file on QUILL's "
        "own GitHub Pages site. Nothing about the listener is sent -- no query, "
        "no identifier, no cookie, only the User-Agent -- and the response is "
        "parsed locally; nothing in it is fetched until the user picks it. "
        "Reached only when the user opens Community > Community Picks. "
        "Bounded timeout and response size over a verified TLS context, and a "
        "copy of the catalogue ships with the app, so refusing this call in "
        "Safe Mode (checked by the caller in community_picks_wiring) leaves the "
        "picker working from the bundled list rather than empty."
    ),
    "ui/radio/suggest_pick_dialog.py::_post_issue": (
        "The one place QUILL sends something OUT rather than fetching: a POST "
        "to api.github.com creating an issue on Community-Access/quill, so "
        "somebody can suggest a station without a GitHub account. What leaves "
        "the machine is exactly what the user typed into the dialog (kind, "
        "name, address, description, language, and why) plus the app name and "
        "version -- composed by core/pick_suggestion.issue_body, which is pure "
        "and unit-tested, so what is sent can be read in one function. It is "
        "authenticated with the bundled issues-only token already used by "
        "Report a Bug (fine-grained, one repo, Issues read/write, nothing "
        "else). Reached only on an explicit Send Suggestion press, after local "
        "validation; refused entirely in Safe Mode by open_suggest_dialog. A "
        "failed post never retries silently -- it offers the browser instead."
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
    "core/podcasts/apple_podcasts.py::_fetch": (
        "Single egress site for browsing Apple Podcasts without a key: the "
        "public store-services genre tree (MZStoreServices .../genres?id=26), "
        "the per-storefront chart feeds (rss.marketingtools.apple.com), and the "
        "lookup that turns a chart row's collection id into its RSS feedUrl. "
        "Reached only by an explicit browse action or by activating a show; the "
        "lookup is lazy, never a bulk pre-fetch. Genre tree and charts are "
        "cached on disk (core/radio/directory_cache.py) so re-opening a branch "
        "makes no request at all. HTTPS-only over a verified TLS context with a "
        "bounded timeout and response size. Disabled in Safe Mode via "
        "refuse_in_safe_mode. Apple remains the DEFAULT and the only keyless "
        "directory; the 2026-08-13 decision against Podcast Index was reversed "
        "on 2026-08-20 and it is now opt-in behind the listener's own key."
    ),
    "core/podcasts/itunes_search.py::_fetch_once": (
        "Single egress site for Add Podcast's search: iTunes' free, keyless "
        "podcast search API. Reached only by the explicit Search action in "
        "the Add Podcast dialog. HTTPS-only over a verified TLS context with "
        "a bounded timeout. Disabled in Safe Mode via refuse_in_safe_mode; "
        "_http_json retries transient failures rather than saying 'no results'."
    ),
    "core/podcasts/podcast_index.py::_fetch_once": (
        "The single Podcast Index site: the search and the catalogue "
        "(podcast_index_catalog -- a show's fact sheet, its episodes WITHOUT "
        "subscribing, trending, the taxonomy). Reached only by an explicit "
        "Search or by opening a Podcast Index branch, which Choose Browse "
        "Sources can switch off (hidden means never contacted); answers are "
        "cached. HTTPS-only, verified TLS, bounded timeout, retried once, "
        "refused in Safe Mode. CREDENTIALS (2026-08-23): the APP's own "
        "key/secret, baked in at build time into a gitignored module -- it "
        "identifies the app to a PUBLIC-data directory, authorises nothing, "
        "reads no account, sends no listener data. A listener's own key wins."
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
