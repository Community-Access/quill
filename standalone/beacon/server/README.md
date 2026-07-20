# QuillSync reference server

A runnable reference for the hosted QuillSync tier (PRD 45.2 tier 3, 45.5,
45.9). Built on the Python stdlib (`http.server` + `sqlite3`) so the contract
is provable locally with no external infrastructure.

PRD 45.5 names the production stack: FastAPI + PostgreSQL + S3-compatible
object storage + Redis for push-hint fanout, with Postmark for magic-link
email. This reference is the same shape, backed by sqlite and the
filesystem, and is wire-compatible with the QuillSync client
(`quill_beacon.sync`) for the commit/object format.

## What it stores

- Account email and registered devices (with revocable per-device tokens).
- Single-use, short-lived magic-link token *hashes* (the raw token is never
  persisted; PRD 45.9).
- An append-only commit graph per account (parent links, manifest).
- Content-addressed encrypted object blobs.

The server **cannot** read private content: blobs are encrypted client-side
with per-object DEKs wrapped by the user's vault key (PRD 23.3, 45.3). Search
stays local.

## Run

```
python -m server            # http://127.0.0.1:8751
```

Set `POSTMARK_API_KEY` in the environment to send real magic-link email via
Postmark (`server.mailer.PostmarkMailer`). Without it, the `LoggingMailer`
prints the link to stdout -- enough to exercise the full flow in development.

## API

| Method | Path | Auth | Body / Query | Returns |
|---|---|---|---|---|
| POST | /auth/request | - | `{"email": "..."}` | `{"ok": true}` (sends magic link) |
| GET | /auth/verify | - | `?token=...&device=...` | `{"device_id", "device_token", "account"}` |
| POST | /sync/push | Bearer | `{"commits": [...], "objects": {hash: b64}}` | `{"ok", "new_commits"}` |
| POST | /sync/pull | Bearer | `{"have": [...]}` | `{"commits": [...], "objects": {hash: b64}}` |
| GET | /sync/hints | Bearer | - | `{"new": N}` |

`server/client.py` is a thin `requests` client for these endpoints, used by
the QuillSync client as the hosted transport.

## Tests

```
python -m unittest tests.test_server
```