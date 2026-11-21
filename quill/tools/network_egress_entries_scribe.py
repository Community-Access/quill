"""GATE-9 entries for Scribe for Documents (quill/core/scribe), kept apart
under GATE-11 like the other feature tables. Merged into ``_REVIEWED_EGRESS``.
"""

from __future__ import annotations

SCRIBE_EGRESS: dict[str, str] = {
    "core/scribe/client.py::_open": (
        "Scribe for Documents REST API (PRD docs/planning/scribe-for-documents-prd.md 7.1), "
        "the one call site for every Scribe request: upload (POST /api/documents, only after "
        "the person pressed Send and Convert in the consent dialog that names Pneuma "
        "Solutions and what is sent; no 'don't ask again'), the person's own document list, "
        "trash, recover, delete, rename, human review, outputs, settings and their choice "
        "lists, account info and billing, and downloads of their own results. Every call "
        "follows a command the person chose, or a job they queued in Scribe Conversions; "
        "nothing runs without a sign-in, a client ID or outside Safe Mode. HTTPS only, "
        "verified TLS, redirects never followed with the bearer token (a download's storage "
        "redirect is fetched without it). Logs methods, document IDs and status codes only; "
        "never tokens, passwords, file contents or response bodies."
    ),
    "core/scribe/channel.py::open": (
        "Scribe for Documents document channel (Phoenix WebSocket, wss://scribeit.io/socket/"
        "websocket, topic documents:<id>): the only way Scribe starts a conversion other "
        "than its free preview. Opened only for a document the person uploaded or chose in "
        "My Scribe Documents, for the length of its conversion, with a 30-second heartbeat; "
        "a drop reconnects and joins again, never uploading again. The access token is in "
        "the address as Phoenix requires and the address is never logged. A PDF password, "
        "when the person typed one, goes in one start_conversion frame and is never kept. "
        "Verified TLS; refused in Safe Mode and without a client ID."
    ),
}
