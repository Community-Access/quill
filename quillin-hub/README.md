# Quillin Hub

The community store and submission service for every shareable QUILL artifact
type. Flask + PostgreSQL, GitHub-native: the Hub validates and guides, GitHub
pull requests remain the transparent publication path, and a sync worker
mirrors what lands on `main` into the storefront.

## What the Hub accepts

The Hub reviews and publishes seven artifact families. Type ids, detection,
and validation all come from one authority in the main repo:
`python -m quill.tools.artifact_validate`.

| Type id | What it is | Upload | Installs into |
| --- | --- | --- | --- |
| `quillin` | Quillin extension (manifest.json + optional handlers) | .zip | Tools > Quillins > Manage Quillins |
| `agent` | Declarative AI agent (quill.agent/1) | .md / .json | AI > AI Library > Agents |
| `verbosity-pack` | Verbosity templates | .qvp.json | Verbosity Library |
| `sound-pack` | QSP earcon pack | .qsp | Settings > Sounds |
| `keyboard-pack` | Keyboard Quill Pack keymap | .kqp | Settings > Keyboard |
| `skill-pack` | Multi-step AI skill | .sqp | AI > AI Library > Skills |
| `pronunciation-dictionary` | Speech pronunciation entries | .json | Pronunciation Dictionaries |

The storefront metadata for each type (labels, tips, install locations) lives
in `app/artifacts/registry.py`; keep its ids in lock-step with
`quill/tools/artifact_validate.py`.

## The Submission Forge

`/forge/submit` takes any accepted file, auto-detects the artifact type
(override available), and runs the audit pipeline in `app/forge/linter.py`:

1. **Validation** -- `quill.tools.artifact_validate --json`, the same checks
   QUILL runs on its own bundled artifacts.
2. **Security scan** (Quillins only) -- Bandit over any Python plus the AST
   `SecurityWatchdog` for capability honesty.
3. **Metadata extraction** -- name/version/description read from the
   artifact's own manifest or front matter, so submitters never retype them.

The result is an accessible Forge Report with pass/fail in plain language and
prefilled GitHub links for the pull-request publication path. Every
submission is recorded in the `submissions` table.

## API

- `GET /api/v1/types` -- artifact types and storefront metadata.
- `GET /api/v1/artifacts[?type=...]` -- all verified artifacts.
- `GET /api/v1/artifacts/<manifest_id>/latest` -- latest verified version.
- `GET /api/v1/plugins...` -- legacy aliases (Quillin extensions only).

## QUILL product tie-in

In the editor, **Tools > Quillins > Submit to Quillin Hub...** runs the same
`artifact_validate` checks locally (picking a Quillin's `manifest.json`
validates the whole folder), reports the result in an accessible dialog, and
opens the Hub's submission page in the browser only on an explicit button
press. QUILL itself makes no network call in that flow.

## Running locally

```bash
pip install -r requirements.txt
pip install -e ..            # the Hub shells out to quill.tools.artifact_validate
set DATABASE_URL=sqlite:///hub.db   # or a PostgreSQL URL
python run.py
```

Smoke test (no PostgreSQL needed):

```bash
python smoke_test.py
```

## Registry sync worker

`worker/sync_to_pages.py` scans the QUILL repository (the bundled
`quill/quillins_bundled` Quillin tree, the AI agents under
`quill/core/ai/agents`, and any `.sqp` skill packs shipped inside
Quillin folders) and upserts them as Verified artifacts. A
`GITHUB_TOKEN` is required.

```bash
GITHUB_TOKEN=... python worker/sync_to_pages.py
```

The seven artifact types and their authoritative validators are
covered by `tests/unit/tools/test_artifact_validate.py` (31 cases:
detection, validation, CLI exit codes, JSON output).
