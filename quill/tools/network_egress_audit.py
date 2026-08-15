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
# The reviewed table moved to its own module under GATE-11 (extract, never
# rebaseline): it is data that grows with every networked feature, while the
# scanner below is logic that does not.
from quill.tools.network_egress_entries import _REVIEWED_EGRESS  # noqa: E402

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
