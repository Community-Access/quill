# Bundled feedback-hub GitHub token — design

## Problem

The "Report a Bug" dialog (and the crash-recovery auto-report path) needs a
GitHub token to file an issue against `Community-Access/quill` via the
bundled `feedback_hub` package. `quill/core/feedback_token.py` only resolves
a token from QUILL's own encrypted token store (populated only if a user
manually signs in to GitHub for the unrelated repo-browser feature) or from
a short list of environment variables no ordinary user will ever set. An
ordinary user (e.g. Michael) has neither, so `effective_github_token()`
returns `""` and the dialog can't push. `feedback_hub.resolve_token()` is
explicitly designed to accept the app's own bundled, narrowly-scoped PAT as
a candidate ("safe to bundle issues-only fine-grained PATs in desktop apps:
worst case misuse is filing extra issues, not code/repo access") — QUILL
never wired that half up.

## Decision: interim client-side bundled token, real hub proxy later

Standing up `quillin-hub` as a live, publicly deployed proxy (the more
secure long-term design, where the raw token never leaves a server) is a
separate infrastructure project (subdomain, container, hosting, database)
that cannot land inside this release cycle. For 0.9.0, QUILL instead bundles
a single, narrowly-scoped GitHub token directly into the shipped app,
matching exactly the risk model `feedback_hub`'s own docstring already
describes and accepts.

## Design

**Token creation (manual, GitHub web UI only — no API/CLI path exists):**
Jeff creates a fine-grained PAT scoped to `Community-Access/quill` only,
with **Issues: read/write** and no other permission. He sets it locally as
`QUILL_FEEDBACK_GITHUB_TOKEN` before running a build; it is never committed,
never pasted into chat, and never given a broader scope than issues.

**Generated module (mirrors the existing `quill/_build_info.py` pattern):**

- `tools/generate_feedback_token.py` — reads `QUILL_FEEDBACK_GITHUB_TOKEN`
  from the environment and writes `quill/_feedback_token.py` containing
  `BUNDLED_TOKEN = "<value>"`. Unlike `generate_build_info.py`, this never
  hard-fails: a missing env var writes `BUNDLED_TOKEN = ""` so ordinary dev
  checkouts, tests, and CI runs without the secret are unaffected.
- `quill/_feedback_token.py` is gitignored, same as `_build_info.py`.

**Wiring:**

- `quill/core/feedback_token.py::effective_github_token()` imports
  `BUNDLED_TOKEN` from the generated module (best-effort: falls back to `""`
  if the module doesn't exist, e.g. an unbuilt dev checkout) and passes it
  as the first candidate to `feedback_hub.resolve_token(BUNDLED_TOKEN)`,
  ahead of the existing env-var fallback. A user's personally-configured
  token (from the secure store) still takes priority over the bundled one,
  unchanged from today.
- `scripts/build_windows_distribution.py` and `scripts/build_macos.sh` each
  gain a best-effort call to `tools/generate_feedback_token.py`, run
  alongside (immediately after) the existing `generate_build_info.py` call.

**Testing:** a unit test in `tests/unit/core/test_feedback_token.py` (new)
covering: bundled token used when present and no stored token exists; stored
token still wins over the bundled one; empty bundled token falls through to
the existing env-var path unchanged.

## Explicitly out of scope

- Deploying `quillin-hub` or any new server endpoint.
- Token rotation tooling, rate limiting, or abuse monitoring for the shared
  token (accepted risk, matching `feedback_hub`'s stated model).
- Any change to the crash-recovery auto-report flow's behavior beyond
  picking up the same token resolution change.
