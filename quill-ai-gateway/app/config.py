"""Environment-driven configuration for the QUILL AI Gateway.

Everything that must never appear in source control (the OpenAI API key,
the database URL, the Redis URL, the Flask session secret) is read from
environment variables here and nowhere else in the codebase. See
``.env.example`` at the repository root for the full list of variables a
deployment must set, and ``README.md`` for how they get there in practice
(an env file *outside* this git-tracked directory, or your host's native
secret-injection mechanism).

This module intentionally does *not* read a ``.env`` file itself in
production — use ``python-dotenv`` only for local development (see
``run.py``), so a forgotten ``.env`` file can never accidentally ship
inside a deployed environment.
"""

from __future__ import annotations

import os


class Config:
    """Base configuration, read once at process start from the environment."""

    # --- Secrets -------------------------------------------------------
    # The only place the real provider key is ever read into memory. Never
    # log this value, never include it in a response, never re-export it.
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

    # Flask's own session/cookie signing key (used for the admin dashboard's
    # login session, not for the bearer-token API auth). Generate with
    # ``python -c "import secrets; print(secrets.token_hex(32))"``.
    SECRET_KEY = os.environ.get("GATEWAY_SECRET_KEY", "")

    # --- Dashboard session cookie (app/routes/dashboard.py) --------------
    # The cookie holds the admin's bearer token (the same credential the
    # JSON API uses -- app/dashboard_auth.py), so it's treated as sensitive
    # as the token itself: httponly (no JS access), SameSite=Lax (blocks
    # cross-site POST forgery of dashboard actions), Secure in production
    # (never sent over plain HTTP -- disabled only for local http:// dev).
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("GATEWAY_DASHBOARD_INSECURE_COOKIE", "") != "1"

    # --- Storage ---------------------------------------------------------
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "postgresql:///quill_ai_gateway")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    # --- OpenAI call shape (see docs/planning/openai.md §8) --------------
    # The nano-class model id is the *only* entry in the hosted-tier
    # allowlist for the initial rollout. This is a code constant, not a
    # gateway_config row, deliberately (see the PRD's §8 rationale: the
    # model string becomes part of a billed API call, so changing it is a
    # reviewed code change, never a runtime admin dial).
    OPENAI_MODEL = os.environ.get("GATEWAY_OPENAI_MODEL", "gpt-5-nano")
    OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_TIMEOUT_SECONDS = float(os.environ.get("GATEWAY_OPENAI_TIMEOUT", "30"))

    # --- Admin allowlist ---------------------------------------------------
    # Comma-separated device_ids (or, once email accounts exist, email
    # addresses) permitted to reach the /admin/* routes. Kept out of the
    # database deliberately -- who can administer the Gateway is a
    # deployment-time decision, not something the Gateway's own admin
    # console should be able to grant to itself.
    ADMIN_ALLOWLIST = frozenset(
        entry.strip()
        for entry in os.environ.get("GATEWAY_ADMIN_ALLOWLIST", "").split(",")
        if entry.strip()
    )

    # --- Device-code flow (RFC 8628) ------------------------------------
    DEVICE_CODE_EXPIRES_SECONDS = int(os.environ.get("GATEWAY_DEVICE_CODE_EXPIRES", "600"))
    DEVICE_CODE_POLL_INTERVAL_SECONDS = int(os.environ.get("GATEWAY_DEVICE_CODE_INTERVAL", "5"))
    PUBLIC_BASE_URL = os.environ.get("GATEWAY_PUBLIC_BASE_URL", "https://gateway.quillforall.org")

    # --- Alerting --------------------------------------------------------
    # A webhook URL (Slack/Discord-compatible incoming webhook, or any
    # endpoint that accepts a JSON {"text": "..."} POST) that the budget
    # alert thresholds (see limits.py) notify. Empty disables alerting
    # (logged locally instead) -- useful for local development.
    ALERT_WEBHOOK_URL = os.environ.get("GATEWAY_ALERT_WEBHOOK_URL", "")

    def validate(self) -> list[str]:
        """Return a list of human-readable problems with this config.

        Called once at app startup (see ``app/__init__.py``); a non-empty
        list means the process refuses to start rather than run with a
        half-configured, silently-broken setup (e.g. no OpenAI key means
        every chat request would fail anyway -- better to fail loudly at
        boot than to accept traffic and fail per-request).
        """
        problems: list[str] = []
        if not self.OPENAI_API_KEY:
            problems.append(
                "OPENAI_API_KEY is not set. The Gateway cannot serve any "
                "chat request without it. Set it via your host's secret "
                "mechanism -- never in a committed file."
            )
        if not self.SECRET_KEY:
            problems.append(
                "GATEWAY_SECRET_KEY is not set. Generate one with "
                '`python -c "import secrets; print(secrets.token_hex(32))"` '
                "and set it via your host's secret mechanism."
            )
        if not self.ADMIN_ALLOWLIST:
            problems.append(
                "GATEWAY_ADMIN_ALLOWLIST is empty -- no one will be able to "
                "reach the /admin/* routes. This is allowed (e.g. for a "
                "brand-new deployment before the first admin registers "
                "their device), but is almost always a configuration "
                "mistake if you're reading this in production."
            )
        return problems


class TestingConfig(Config):
    """Used by the test suite: an in-memory-friendly, secret-free config."""

    TESTING = True
    OPENAI_API_KEY = "test-key-never-used-for-real-calls"
    SECRET_KEY = "test-secret-key"
    SESSION_COOKIE_SECURE = False  # the test client doesn't use HTTPS
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URL", "sqlite:///:memory:")
    REDIS_URL = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/15")
    ADMIN_ALLOWLIST = frozenset({"test-admin-device"})
