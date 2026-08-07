# QUILL documentation index

This folder holds all of QUILL's documentation. The full repository map —
every folder, key document, and convention — is
[`REPO-GUIDE.md`](../REPO-GUIDE.md) at the repository root; this page is the
quick index for the docs tree itself.

## Start here

- [User guide](user%20guide/userguide.md) — the end-user manual (also ships
  inside the app).
- [QUILL-PRD](Product%20Requirement%20Documents%20and%20Specifications/QUILL-PRD.md)
  — the product requirements document, the canonical description of what
  QUILL is and does. Feature specifications live beside it.
- [Control reference](CONTROL_REFERENCE.md) — every help topic and
  keystroke. Generated from `quill/core/help/topics.json`; do not hand-edit.

## Release and QA

- [release/](release/RELEASE.md) — the release runbook, plus the
  **Acceptance Test Book** (`release/acceptance/`, interactive runner at
  `release/acceptance/interactive/index.html`), the sample-document corpus
  (`release/qa-samples/`), upgrade-path runbooks, and the screen-reader and
  core-journey test plans.
- [planning/](planning/roadmap.md) — the roadmap, the 1.0.0 readiness
  ledger (`planning/RELEASE-1.0.0-READINESS.md`), the generated sign-off
  inventories (`planning/signoff/`, interactive at
  `planning/signoff/interactive/index.html`), and active planning notes.
- [qa/](qa/dialogs.md) — cross-release QA references: the manual dialog
  checklist, UI automation notes, platform validation, bake-offs.
- [release notes/](release%20notes/) — per-release notes and the GitHub
  release bodies.

## Community and policy

- [CONTRIBUTING](CONTRIBUTING.md) · [CODE_OF_CONDUCT](CODE_OF_CONDUCT.md) ·
  [SECURITY](SECURITY.md) · [GOVERNANCE](GOVERNANCE.md) ·
  [MAINTAINERS](MAINTAINERS.md)
- [legal/](legal/) — privacy, responsible AI use, trademarks, third-party
  notices.
- [signing](signing.md) — artifact signing workflow for Quillin Hub
  publishers and operators.

## Feature areas and the rest

- [apps/](apps/) — companion app docs. [quillins/](quillins/) — the
  extension (Quillin) scripting contract. [tutorials/](tutorials/) —
  step-by-step tutorials. [translations/](translations/) — localization.
- [engineering/](engineering/) — deep-dives and post-mortems.
  [design/](design/) — design notes. [math/](math/), [audio-studio/](audio-studio/),
  [podcast/](podcast/) — feature-area material.
- [site/](site/) — the website content published via GitHub Pages.
- superpowers/ — internal plans and specs written during AI-assisted
  development.

## Conventions

Every Markdown file under `docs/` ships generated `.html` and `.epub`
siblings; after editing a file, regenerate both (CI enforces parity):

```powershell
pandoc file.md -f gfm -t html5 -s -o file.html
pandoc file.md -f gfm -t epub3 -o file.epub
```
