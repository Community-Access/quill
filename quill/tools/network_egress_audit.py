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
})

# Reviewed, allowed egress sites: "<relative path>::<enclosing function>" mapped
# to the reason the call is not silent. Update this when adding a network call.
_REVIEWED_EGRESS: dict[str, str] = {
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
    "core/radio/link_finder.py::_fetch_html": (
        "Single egress site for 'Find Streams from a Website...': fetches the "
        "one page the user typed to look for a station's own stream link "
        "(audio/source tags, playlist-shaped hrefs). Reached only by the "
        "explicit Scan button, which states the exact URL before fetching. "
        "HTTPS-only over a verified TLS context, bounded timeout and response "
        "size. Disabled in Safe Mode via link_finder.refuse_in_safe_mode."
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
    "core/mastodon/client.py::_http_json": (
        "Single egress site for the 'Post to Mastodon' feature. Reached only by an "
        "explicit user action -- adding an account (app registration + OAuth token "
        "exchange), opening the compose dialog or switching accounts (a one-time "
        "unauthenticated limit lookup: GET /api/v2/instance for Mastodon 4.0+ / "
        "glitch-soc, falling back to GET /api/v1/instance -> max_toot_chars for "
        "non-Mastodon forks like GoToSocial / Pleroma / Akkoma; cached for the "
        "process lifetime), or pressing Post -- to the user's own instance. "
        "HTTPS-only over a verified TLS context; the access token travels "
        "in the Authorization header, never the URL. The instance-limit lookup is "
        "unauthenticated and falls back to the default 500 on any failure."
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
    "core/updates.py::fetch_releases": (
        "Fetches release notes for an update the user is already reviewing."
    ),
    "core/updates.py::download_release_asset": (
        "User chooses to download an offered update; verified TLS, visible progress."
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
    "core/speech/ffmpeg_install.py::_download_zip": (
        "User-initiated optional ffmpeg download (#617) from the official Gyan.dev "
        "Windows build linked by ffmpeg.org; HTTPS enforced (refuses non-https), "
        "verified TLS context, visible progress, blocked in Safe Mode. ffmpeg is not "
        "bundled (GPL/LGPL); QUILL only downloads it on an explicit action."
    ),
    "core/speech/piper_install.py::_download_zip": (
        "User-initiated optional Piper TTS engine download (#669) from the pinned "
        "rhasspy/piper GitHub release (piper_windows_amd64.zip). HTTPS enforced "
        "(refuses non-https), verified TLS context, visible progress, blocked in "
        "Safe Mode, Windows-only. No SHA-256 pin (relies on HTTPS + official GitHub "
        "release asset). Triggered only by an explicit 'Download Piper Engine' action "
        "from the Voice Browser dialog."
    ),
    "core/speech/espeak_install.py::_download_msi": (
        "User-initiated optional eSpeak-NG TTS engine download (#669) from the pinned "
        "espeak-ng GitHub release (x64 MSI). HTTPS enforced (refuses non-https), "
        "verified TLS context, visible progress, blocked in Safe Mode, Windows-only. "
        "MSI is then extracted admin-free via msiexec /a (no elevation, no registry). "
        "Triggered only by an explicit 'Download eSpeak-NG' action from the Voice "
        "Browser dialog."
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
    "core/tesseract_install.py::_download": (
        "User-initiated optional local Tesseract OCR engine download (free-first "
        "document conversion, Tier 2) from QUILL's own pinned assets-v1 release "
        "asset (byte-identical re-publish of the official UB-Mannheim installer, "
        "Apache-2.0). HTTPS enforced (refuses non-https), verified TLS context, "
        "SHA-256 pinned (SEC-6), visible progress, blocked in Safe Mode, "
        "Windows-only. The verified installer is then launched visibly for the "
        "user to complete — never a silent install or elevation. Triggered only "
        "by an explicit 'Install Local OCR Engine' action from Tools > OCR and "
        "Document Conversion."
    ),
    "core/pandoc_install.py::_download": (
        "User-initiated optional Pandoc download (footprint unbundle, PRD "
        "10.2.x): Pandoc is no longer bundled, so the first document conversion "
        "that needs it — or an explicit 'Download Optional Components' action — "
        "fetches the official jgm/pandoc Windows build over verified HTTPS. "
        "HTTPS enforced (refuses non-https), verified TLS context, SHA-256 "
        "pinned (SEC-6) to the exact release asset, visible progress, blocked "
        "in Safe Mode, Windows-only. Extracted to the app-data tools directory; "
        "core plain-text/Markdown editing never triggers it."
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
    "ui/main_frame.py::_run": (
        "Piper voice model download (_download_piper_voice) or Kokoro model download "
        "(_download_kokoro_models). Both are triggered only when the user clicks "
        "'Download Voice...' in the Voice Browser dialog (Manage Voices & Reading Aloud). "
        "Piper fetches .onnx and .onnx.json from HuggingFace piper-voices; Kokoro fetches "
        "model and voices files from GitHub releases. Both use HTTPS, show a progress dialog "
        "with Cancel, and reopen Manage Voices via switch_to_ok on completion."
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
        "verified HTTPS to resolve the current win-x64 zip filename. Runs only on an "
        "explicit 'Download Node.js runtime' action in the Quillins settings panel; "
        "blocked in Safe Mode; Windows-only. No user data is sent."
    ),
    "core/node_install.py::_download_node_zip": (
        "User-initiated Node.js LTS runtime download (Node Quillin support). Streams "
        "the official nodejs.org win-x64 zip (URL resolved from SHASUMS256.txt by "
        "_fetch_node_zip_url) over verified HTTPS with a visible progress callback. "
        "Same gating as _fetch_node_zip_url: explicit action, Safe Mode blocked, "
        "Windows-only. QUILL never redistributes the binary."
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
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        parents = build_parent_map(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _callee_name(node) in _EGRESS_CALLEES:
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
