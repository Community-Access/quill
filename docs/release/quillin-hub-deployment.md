# Quillin Hub deployment runbook

The Quillin Hub is a Flask app that serves the Quillin, AI agent, and
skill-pack storefront. This is the runbook for going from "the
container builds" to "the storefront is serving verified artifacts".

## Topology

- One Flask process (Gunicorn, 4 workers).
- One PostgreSQL database.
- One cron job (or scheduled worker) running `worker/sync_to_pages.py`
  against the QUILL GitHub repository.
- Public static assets served by the reverse proxy (nginx / Caddy).

The Hub is a read-heavy storefront with a low write rate (one
submission per publisher per release). 4 workers is plenty.

## Environment

| Var | Purpose |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy URL. `postgresql://hub:<pw>@db/hub` in production, `sqlite:///<tmp>/hub.db` in tests. |
| `SIGNING_PUBLIC_KEY_PATH` | Path to the rotated publisher public key. Overrides the bundled `quillin-hub/quill-pub.key`. |
| `GITHUB_TOKEN` | Used by the sync worker to enumerate the QUILL repo. Without it, the worker logs a 401 and skips the run. |
| `SECRET_KEY` | Flask session secret. Generate with `python -c "import secrets; print(secrets.token_hex(32))"`. |
| `UPLOAD_FOLDER` | Where submitted artifacts land. Must be writable by the Flask process. Defaults to a tmp dir in dev. |

## Bootstrap

```bash
# 1. Apply the schema.
flask --app quillin-hub/app db upgrade

# 2. Seed the publisher public key if rotating.
# (otherwise the bundled quillin-hub/quill-pub.key is used)
cp /secure/quill-pub.key /srv/hub/quill-pub.key
chmod 0644 /srv/hub/quill-pub.key
export SIGNING_PUBLIC_KEY_PATH=/srv/hub/quill-pub.key

# 3. Run the sync worker once to populate the storefront.
GITHUB_TOKEN=$(cat /secure/gh.token) python -m quillin-hub.worker.sync_to_pages

# 4. Start the app.
gunicorn -w 4 -b 0.0.0.0:8000 'quillin-hub.app:create_app()'
```

## Reverse proxy

nginx snippet:

```nginx
server {
    listen 443 ssl http2;
    server_name hub.quillforall.org;

    ssl_certificate     /etc/letsencrypt/live/hub.quillforall.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/hub.quillforall.org/privkey.pem;

    client_max_body_size 40m;   # 32 MB submission + 8 MB signature + headers

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

`client_max_body_size` is the headline knob: 32 MB submission cap
matches `quillin-hub/app/forge/forms.py::_MAX_UPLOAD_BYTES`. 40 MB
leaves room for the sidecar and multipart overhead.

## Health check

The Hub has no `/healthz` endpoint today. Add one if you're putting
this behind a load balancer:

```python
@web_bp.route("/healthz")
def healthz():
    return {"ok": True}, 200
```

(Tracked for a follow-up; not in the launch cut.)

## Smoke test

`quillin-hub/smoke_test.py` is the post-deploy verification. It uses
a throwaway SQLite DB, signs test artifacts with a throwaway
keypair, and exercises every route + the real Submission Forge
pipeline. Run it from a clean checkout:

```bash
pip install -e ../   # the main QUILL package
pip install -r requirements.txt
python smoke_test.py
# 22/22 checks passed
```

Any failure means a regression in either the storefront or the
Forge; do not roll forward until it is green.

## Sync worker

`worker/sync_to_pages.py` enumerates the QUILL GitHub repo and upserts
every Quillin, AI agent, and skill pack into the Hub's `artifacts`
table. The worker is idempotent: it filters by `manifest_id` and
upserts, so it is safe to run on a cron every 15 minutes.

```cron
*/15 * * * * cd /srv/hub && GITHUB_TOKEN=$(cat /secure/gh.token) /usr/bin/python3 -m quillin_hub.worker.sync_to_pages >> /var/log/hub-sync.log 2>&1
```

What it does, per run:

- Lists `quill/quillins_bundled/*` and upserts each as a `quillin`.
- For each Quillin directory, lists any `*.sqp` and upserts them as
  `skill-pack` artifacts (so skill packs are reachable both from
  the parent Quillin and from the standalone search).
- Lists `quill/core/ai/agents/*` and upserts each `.md` and `.json`
  as an `agent` artifact, reading front matter / JSON metadata.
- For every single-file artifact (agent or skill pack), reads the
  matching `<file>.minisig` sidecar from main and stores the key id
  in `signer_key_id` for the storefront badge.

The worker **does not** verify the signature against the public key
when syncing from main -- main is post-review by definition, and the
sidecar is the human-readable provenance. The desktop app does the
actual verification at download time.

## Submission Forge cap

The Submission Forge accepts artifacts up to 32 MB
(`_MAX_UPLOAD_BYTES` in `app/forge/forms.py`). Anything bigger is
rejected with "archive expands beyond the 32 MB submission limit".
Larger artifacts should land via a GitHub PR using the prefilled
links the Forge generates on the report page.

## Failure modes

- **DB connection drops** -- Gunicorn workers will 500. The reverse
  proxy should retry on 502/503/504 with a 1 s backoff. PostgreSQL
  reconnects are handled by SQLAlchemy.
- **Sync worker 401** -- the GitHub token rotated or expired. The
  worker prints "Skipping <root>: 401" for every root. Rotate the
  token and re-run.
- **Bad sidecar floods the Forge** -- the `audit_submission` returns
  FAIL and the artifact does not become a row. No cleanup needed.
- **Database migration** -- the schema is currently managed by
  `db.create_all()` in dev. For production, switch to
  `flask --app quillin-hub/app db upgrade` with a real migrations
  directory (deferred to the next cut).

## Rollback

There is no in-place schema migration framework yet, so "rollback" is
a redeploy against the previous commit. The storefront is
forward-compatible: an artifact row in the DB renders even if its
backing code path is missing. The Forge is the only place where
runtime changes can break submissions, and a Forge regression is
surfaced immediately by the smoke test.
