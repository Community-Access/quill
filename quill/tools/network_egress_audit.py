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
from pathlib import Path

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
    "core/mastodon/client.py::_http_json": (
        "Single egress site for the 'Post to Mastodon' feature. Reached only by an "
        "explicit user action -- adding an account (app registration + OAuth token "
        "exchange) or pressing Post -- to the user's own instance. HTTPS-only over a "
        "verified TLS context; the access token travels in the Authorization header, "
        "never the URL."
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
    "core/speech/providers/whispercpp.py::_download_to_file": (
        "User-initiated offline speech-model download (#617) from the Hugging Face "
        "Hub whisper.cpp repo; HTTPS enforced (refuses non-https URLs), verified TLS "
        "context, visible progress, blocked in Safe Mode, sha256-verified when a hash "
        "is known. No silent background downloads."
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
        "Consented online dictionary/thesaurus lookups (DICT-1: Free Dictionary "
        "and Datamuse). Only runs when the user enables online lexical lookups; "
        "HTTPS with a verified TLS context, no API key, graceful offline fallback."
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
}

# ---------------------------------------------------------------------------
# PyGithub egress — manually documented (not AST-scannable)
# ---------------------------------------------------------------------------
# PyGithub (github.com/PyGithub/PyGithub) makes HTTPS calls internally via
# urllib3.  Its call sites never appear in quill/ source as direct
# urllib/socket/requests calls, so the AST scanner cannot find them.
# The integration surface is documented here for auditability.
#
# Entry points (all in quill/core/github/github_provider.py):
#   get_identity()    - GitHub API: GET /user
#   get_repository()  - GitHub API: GET /repos/{owner}/{repo}
#   list_refs()       - GitHub API: GET branches + tags for a repo
#   get_file()        - GitHub API: GET /repos/{owner}/{repo}/contents/{path}
#   save_file()       - GitHub API: PUT /repos/{owner}/{repo}/contents/{path}
#
# Gating: all calls are triggered by explicit user actions in the GitHub
# dialogs (File > Open from Remote > GitHub).  A one-time consent dialog fires
# before any network call on first use.  Tokens are stored in Windows Credential
# Manager only, never logged.  All PyGithub calls are HTTPS.

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
#   Triggered automatically after the Kokoro model files are downloaded
#   (Manage Voices > Download Kokoro), or explicitly from Manage Speech Models >
#   Install Kokoro ONNX, or Tools > Speech > Install Kokoro ONNX.


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


def discover_egress_sites() -> dict[str, str]:
    """Return {"<rel path>::<function>": "<source line text>"} for every call."""
    sites: dict[str, str] = {}
    for path in sorted(_PACKAGE_ROOT.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _callee_name(node) in _EGRESS_CALLEES:
                rel = path.relative_to(_PACKAGE_ROOT).as_posix()
                func_name = _enclosing_function_name(tree, node)
                site = f"{rel}::{func_name}"
                # Same-site duplicates collapse; cross-function duplicates with
                # the same enclosing function are not possible by construction
                # (one entry per function). Two egress calls in the same function
                # would share the key, so keep the first to preserve the prior
                # behavior and surface the collision via _first_seen_at().
                sites.setdefault(site, func_name)
    return sites


def find_unreviewed_egress() -> tuple[set[str], set[str]]:
    """Return (unreviewed_sites, stale_reviewed_entries)."""
    discovered = set(discover_egress_sites())
    reviewed = set(_REVIEWED_EGRESS)
    return discovered - reviewed, reviewed - discovered
