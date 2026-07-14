# QUILL Quillins and scripting documentation

_Consolidated on 2026-06-13, last refreshed 2026-07-04 to point at the unified Quillin Hub. Sections preserve each source in full. The scripting contract section also governs the QUILL Developer Console (QDC); code references to "docs/quillins.md" by section number point inside the scripting-contract section below._


---

<!-- Source: docs/quillins.md -->

# Quillin Tutorial — build your first Quillin

This is a hands-on, build-it-from-scratch tutorial for Quillin contributors. By
the end you will have authored, linted, tested, and prepared a real Quillin for
submission — starting from a zero-capability snippet and growing into an
out-of-process Python handler.

It pairs with three references you'll reach for along the way:

- [`scripting.md`](scripting.md) — the full design + authoring reference (§13
  schema, §14 API, §15 the deterministic generation contract).
- [`quillin-submission.md`](quillin-submission.md) — the submission process.
- [`quillin-code-of-conduct.md`](quillin-code-of-conduct.md) — the Author
  Covenant every Quillin must keep.

> **Prerequisite:** a working QUILL dev checkout (`pip install -e ".[ui,dev]"`,
> Python 3.12). The linter itself is `wx`-free, so `pip install -e .` is enough
> to lint.

---

## 1. What you're building

A Quillin called **Word Count Tools** (`com.example.wordcount`). It will:

1. start as a **Layer 1** snippet that inserts a heading (no code, no
   capabilities), then
2. grow a **Layer 2** Python handler that counts the words in the selection and
   **announces** the result.

Along the way you'll see the two ideas that make Quillins safe: **declare the
minimum** and **announce every outcome**.

---

## 2. Anatomy of a Quillin

A Quillin is one directory:

```
word-count-tools/
  manifest.json     # the contract — required
  extension.py      # Python entry module — only for Layer 2
  README.md         # required for submission
  LICENSE           # required (or a "license" field in the manifest)
```

The `manifest.json` always starts with the schema discriminator and an identity:

```json
{
  "schema": "quill.extension/1",
  "id": "com.example.wordcount",
  "name": "Word Count Tools",
  "version": "0.1.0"
}
```

- **`schema`** is always `"quill.extension/1"`.
- **`id`** is reverse-DNS *you control*. `com.quill.*` is reserved for
  first-party bundled Quillins.
- **`version`** is `MAJOR.MINOR.PATCH` and you bump it on every change.

---

## 3. Step 1 — a Layer 1 snippet (no capabilities)

Create the directory and a manifest that contributes one snippet command.
Snippets are declarative text with placeholders — **no code runs**, so a
snippet-only Quillin needs **no capabilities** at all.

`manifest.json`:

```json
{
  "schema": "quill.extension/1",
  "id": "com.example.wordcount",
  "name": "Word Count Tools",
  "version": "0.1.0",
  "author": "Your Name",
  "description": "Insert a word-count heading and count words in the selection.",
  "license": "MIT",
  "min_quill_version": "1.0.0",
  "contributes": {
    "commands": [
      {
        "id": "ext.wordcount.heading",
        "title": "Insert Word Count Heading",
        "run": { "snippet": "## Word count for ${filename}\n\n${cursor}" }
      }
    ],
    "menus": [
      { "parent": "Format", "command": "ext.wordcount.heading" }
    ]
  }
}
```

Two rules you just used:

- **Command ids are namespaced under `ext.`** so they can never collide with a
  built-in QUILL command.
- **Menu parents** are a fixed set: `File`, `Edit`, `Format`, `Tools`,
  `Navigate`, `View`, `Help`.

### Snippet placeholders

| Placeholder | Expands to |
| ----------- | ---------- |
| `${selection}` | the current selection (empty if none) |
| `${clipboard}` | the clipboard text (requires `clipboard.read` capability) |
| `${date}` | today's date in the user's configured format |
| `${time}` | current time in the user's configured format |
| `${filename}` | the current document's file name (e.g. `notes.txt`) |
| `${title}` | the document's file name stem without extension (e.g. `notes`) |
| `${line_number}` | current line number, 1-indexed |
| `${word_at_cursor}` | the word immediately surrounding the insertion point |
| `${uuid}` | a fresh UUID4 generated at expansion time |
| `${cursor}` | where the caret lands after insertion |

**Common patterns:**

```json
// Front matter header
"run": { "snippet": "---\ntitle: ${title}\ndate: ${date}\n---\n\n${cursor}" }

// Wrap selected word in bold
"run": { "snippet": "**${word_at_cursor}**${cursor}" }

// Insert a unique anchor ID
"run": { "snippet": "id=\"${uuid}\"${cursor}" }

// Annotate the current line
"run": { "snippet": "<!-- line ${line_number}: ${word_at_cursor} -->${cursor}" }
```

### Lint it

```powershell
python -m quill.tools.quillin_lint path\to\word-count-tools --strict
```

You'll get a couple of warnings (no README, no LICENSE). Add a `README.md` and a
`LICENSE` file (or keep the manifest `license` field) and re-run until it's
green. **That clean `--strict` run is your submission bar for Layer 1.**

You now have a complete, useful Quillin with zero code and zero capabilities.
Most Quillins never need more than this.

---

## 4. Step 2 — a Layer 2 Python handler

Now add real logic: count the words in the selection and announce the count.
Handlers run **out-of-process**, behind QUILL's capability + consent gate —
see the accuracy note in §4b before you rely on that gate for anything
security-sensitive.

### 4a. Declare what you need

A handler command requires two things in the manifest: a top-level `main` module
and the `ui.command` capability. To read the selection and announce a result you
also need `editor.read` and `ui.announce`. **That's the minimum — declare
nothing more.**

Add to `manifest.json`:

```json
  "capabilities": ["editor.read", "ui.announce", "ui.command"],
  "main": "extension.py",
```

and a second command in `contributes.commands`:

```json
      {
        "id": "ext.wordcount.count",
        "title": "Count Words In Selection",
        "run": { "handler": "count_words" }
      }
```

Wire it to a context-menu entry (only when there's a selection) and a hotkey:

```json
    "context_menu": [
      { "command": "ext.wordcount.count", "when": "editor.hasSelection" }
    ],
    "hotkeys": [
      { "command": "ext.wordcount.count", "binding": "Ctrl+Shift+W" }
    ]
```

`when` guards accept `always`, `editor.hasSelection`, `editor.hasText`, or
`editor.empty`. Hotkey conflicts are **rejected**, never silently overridden.

### 4b. Write the handler

`extension.py`:

```python
"""Word Count Tools — a Layer 2 Quillin handler."""

from __future__ import annotations


def register(api):
    """Entry point: QUILL calls this once to register handlers."""
    api.register_command("count_words", count_words)


def count_words(api):
    """Count words in the selection and announce the result."""
    selection = api.get_selection()
    if not selection.strip():
        api.announce("Nothing selected.")
        return
    count = len(selection.split())
    api.announce(f"{count} word{'s' if count != 1 else ''} selected.")
```

What to notice:

- **`register(api)`** is the single entry point. It binds the handler name used
  in the manifest (`"count_words"`) to a Python function.
- The handler receives the **`QuillExtensionApi`** (`api`). Calling an `api`
  method you didn't declare a capability for is rejected by the host. **This is
  not the same as a security sandbox**: the worker process is plain Python with
  no import restriction, so nothing technically stops a handler from importing
  `os`/`socket`/`subprocess` directly instead of going through `api`. The real
  enforcement today is the linter, human review, and the Author Covenant below
  — use `api` for everything anyway, because that's the contract reviewers
  check against and what makes a Quillin portable to a real sandbox later.
- **It announces its outcome in every path** — success *and* the empty-selection
  case. A silent success is a bug under the Author Covenant.

### 4c. The capability surface (Layer 2)

The API you can call maps directly onto declared capabilities:

| You call | Capability required | Notes |
| -------- | ------------------- | ----- |
| `api.get_text()` / `api.get_selection()` / `api.get_cursor()` | `editor.read` | |
| `api.insert_text(...)` / `api.replace_selection(...)` | `editor.write` | edits join normal undo |
| `api.announce(...)` | `ui.announce` | the spoken/braille outcome |
| `api.get_clipboard()` / `api.set_clipboard(...)` | `clipboard.read` / `clipboard.write` | |
| `api.read_file(...)` / `api.write_file(...)` | `fs.read` / `fs.write` | **consent-gated** at runtime |
| `api.fetch(...)` | `net` | **consent-gated** at runtime |
| `api.log(...)` | none | never reaches announcements |

`fs.*` and `net` prompt the user on **every** use. Design for a graceful,
announced refusal — never assume access is granted.

---

## 5. Test your Quillin

Mirror the bundled Quillin's test
([`tests/unit/core/test_quillins_bundled_markdown.py`](../tests/unit/core/test_quillins_bundled_markdown.py)).
A good Layer 2 test validates the manifest, builds a conflict-free contribution
registry, and drives the handler against a fake API:

```python
import json
from pathlib import Path

from quill.core.quillins.validation import parse_manifest
from quill.core.quillins.registry import build_registry


def _manifest():
    path = Path("path/to/word-count-tools/manifest.json")
    return parse_manifest(json.loads(path.read_text(encoding="utf-8")))


def test_manifest_is_valid_and_registry_has_no_conflicts():
    manifest = _manifest()
    registry = build_registry([manifest])
    assert "ext.wordcount.count" in registry.commands


class _FakeApi:
    def __init__(self, selection):
        self._selection = selection
        self.announced = []

    def get_selection(self):
        return self._selection

    def announce(self, message):
        self.announced.append(message)


def test_handler_counts_and_announces():
    from importlib import import_module  # or exec the extension module directly

    api = _FakeApi("one two three")
    # call your count_words(api) here and assert:
    # assert api.announced == ["3 words selected."]
```

For real confidence, also drive the handler through the **out-of-process host**
(see [`tests/integration/test_quillins_host_integration.py`](../tests/integration/test_quillins_host_integration.py)),
which exercises the actual worker process, capability gate, and consent flow.

---

## 6. Lint, then check everything

```powershell
python -m quill.tools.quillin_lint path\to\word-count-tools --strict
pytest -q path\to\your\test_word_count.py
```

The linter applies three independent lenses, so a mistake is caught by whichever
sees it first:

1. **Schema check** — your manifest validated against the published JSON Schema
   (`quill/core/schemas/extension.json`), made executable inside the linter.
2. **Manifest validation** — the same contract validator the loader enforces
   (this is what flags "a handler command requires `main` + `ui.command`").
3. **Structure & capability hygiene** — your `main` exists, README + license are
   present, and every consent-gated capability is surfaced for review.

---

## 7. Submit

1. Open the **Quillin submission** issue — its form scaffolds the
   `manifest.json` and records your Author Covenant acknowledgement.
2. Open a PR using the **Quillin submission** PR template and complete its
   checklist.
3. The `Quillin Verify` workflow re-runs the linter in `--strict` mode on your
   Quillin. Green check → ready for human review; red → fix and push.

Review focuses on what machines can't fully judge: real accessibility (does
every action announce a clear outcome; is it keyboard-complete?), capability
justification (is each one necessary and transparent?), and honesty (readable
source, no silent network, behaviour matches description).

The full process, review criteria, and acceptance checklist live in
[`quillin-submission.md`](quillin-submission.md).

---

## 8. Recap — the rules that matter

- **Start at Layer 1.** Snippets cover most needs with zero code and zero
  capabilities.
- **Declare the minimum.** A handler needs `main` + `ui.command`; add `editor.*`,
  `clipboard.*`, `fs.*`, or `net` only when you actually use them.
- **Announce every outcome.** Success and failure both speak.
- **`fs.*` and `net` are consent-gated.** Handle refusal gracefully.
- **Namespace ids under `ext.`**, use a reverse-DNS `id` you control, and
  version honestly.
- **Lint `--strict`, test, then submit.** A clean linter run is the bar.

Welcome aboard — your first Quillin is exactly how QUILL stays *Quality, Usable,
Inclusive, Lightweight, Literate.*


---

<!-- Source: docs/quillins.md -->

# QUILL Scripting & Quillins — Design & Implementation

Status: **Implemented (framework foundation)** · Branch: `edsharp`

This document is both the design rationale and the authoritative authoring
reference for **Quillins**, QUILL's extension framework. The framework described
here is **implemented and tested in the codebase** (`quill/core/quillins/*` and
`quill/ui/main_frame_quillins.py`); see the Implementation Status map in §0a for
the module-by-module mapping. Third-party Quillin **execution** is deliberately
gated off for QUILL 1.0 by the SEC-8 `core.third_party_plugins` feature flag
(`locked_off`), so a shipping 1.0 build discovers and runs no third-party code
while the framework, the Quillins Manager, and the full test bar are in place.

## 0a. Implementation status (module map)

Every design element below is backed by a shipping, wx-free `quill/core` module
(plus one `quill/ui` mixin) and a test. The neutral technical terms
(`extension`, `quill.extension/1`, `ext.*`, `QuillExtensionApi`) are the stable
wire/code identifiers; the experience speaks of **Quillins**.

| Design element (this doc) | Module | Tests |
| --- | --- | --- |
| Manifest model, capability catalogue, errors (§4, §5, §14.1) | `quill/core/quillins/model.py` | `tests/unit/core/test_quillins_model.py` |
| Manifest validation (§13) | `quill/core/quillins/validation.py` | `tests/unit/core/test_quillins_validation.py` |
| Published JSON Schema (§13) | `quill/core/schemas/extension.json` | `tests/unit/core/test_quillins_protocol.py` (schema⇄validator agreement) |
| Layer 1 snippet expansion (§14.3) | `quill/core/quillins/snippets.py` | `tests/unit/core/test_quillins_snippets.py` |
| Contribution merge + conflict detection (§4, §15) | `quill/core/quillins/registry.py` | `tests/unit/core/test_quillins_registry.py` |
| Discovery, enable/disable, SEC-8 gate (§6) | `quill/core/quillins/loader.py` | `tests/unit/core/test_quillins_loader.py` |
| RPC framing (§3) | `quill/core/quillins/protocol.py` | `tests/unit/core/test_quillins_protocol.py` |
| Out-of-process host + capability/consent gate (§5, §6) | `quill/core/quillins/host.py` | `tests/unit/core/test_quillins_host.py`, `tests/integration/test_quillins_host_integration.py` |
| Out-of-process worker + `QuillExtensionApi` (§5, §14.4) | `quill/core/quillins/host_worker.py` | `tests/integration/test_quillins_host_integration.py` |
| Tools ▸ Quillins menu, runtime, Quillins Manager dialog (§7, §17) | `quill/ui/main_frame_quillins.py` | `tests/unit/ui/test_main_frame_quillins.py`, A11Y-4 dialog inventory |
| Bundled Quillin (Tier C: Layer 1 snippet + Layer 2 handler) | `quill/quillins_bundled/markdown-helpers/` | `tests/unit/core/test_quillins_bundled_markdown.py` |
| Bundled Quillin: Insert Character | `quill/quillins_bundled/insert-character/` | `tests/unit/core/test_quillins_bundled_insert_character.py` |
| Bundled Quillin: Line Tools (6 cursor-aware line operations) | `quill/quillins_bundled/line-tools/` | `tests/unit/core/test_quillins_bundled_line_tools.py` |
| Bundled Quillin: Text Tools (HTML-to-Markdown + text transforms) | `quill/quillins_bundled/text-tools/` | `tests/unit/core/test_quillins_bundled_text_tools.py`, `test_quillins_bundled_text_tools_html.py` |
| Extended host API (cursor offsets, status, choices, storage) | `quill/core/quillins/host.py`, `host_worker.py` | `tests/unit/core/test_quillins_host_extended.py` |
| **Node.js runtime** — `"runtime": "node"` manifest field, node runner, `@quill/api` package (§9, issue #158) | `quill/plugins/node_quillin_runner.py`, `quill/core/quillins/model.py`, `quill/core/quillins/validation.py`, `packages/@quill/api/` | `tests/unit/core/test_quillins_node_runtime.py`, `tests/unit/plugins/test_node_quillin_runner.py` |
| Bundled Quillin: Word Count (Node) — Layer 2 handler in JavaScript | `quill/quillins_bundled/word-count-node/` | `tests/unit/core/test_quillins_bundled_word_count_node.py`, `tests/unit/tools/test_quillin_lint_node.py` |

A complete, loadable **bundled Quillin** ships in
[`quill/quillins_bundled/markdown-helpers/`](../quill/quillins_bundled/markdown-helpers/):
a `manifest.json` contributing a Layer 1 front-matter snippet
(`ext.mdh.frontmatter`) and a Layer 2 bold-selection handler (`ext.mdh.bold`),
plus an `extension.py` entry module.
`tests/unit/core/test_quillins_bundled_markdown.py`
validates the manifest, builds a conflict-free contribution registry, expands the
snippet, and drives the handler — and the same directory loads and runs through
the real out-of-process host worker. As a **Tier C bundled Quillin** it ships
enabled (gated by the on-by-default `core.bundled_quillins` flag, wholly
independent of the SEC-8 third-party lock) and is the canonical template for
authoring a new Quillin.

### Submitting a Quillin

Authoring a Quillin for submission is governed by three companion pieces:

- **[Quillin Author Covenant](quillin-code-of-conduct.md)** — the code of
  conduct for Quillin *code*: accessibility (announce every outcome,
  keyboard-complete), capability minimization and honesty, no silent network or
  telemetry, privacy, security (no obfuscation, no attempts to exceed declared
  capabilities, no malware), licensing, and namespace etiquette. Every
  submission attests to it.
- **[Submission guide](quillin-submission.md)** — the end-to-end author journey:
  directory layout, manifest authoring, self-lint, tests, the PR template, and
  the review criteria.
- **The submission linter** — `python -m quill.tools.quillin_lint <dir> --strict`
  (`quill/tools/quillin_lint.py`) applies three lenses: an *executable* check of
  the published JSON Schema (`quill/core/schemas/extension.json`), the contract
  validator the loader enforces, and a structure/capability-hygiene gate. The
  `Quillin Verify` workflow (`.github/workflows/quillin-verify.yml`) runs it on
  every submission, so a Quillin cannot land without passing.

This document is a design plan turned reference; where it describes future,
optional, or 2.0-scale work it says so explicitly (the QuickJS evaluator in §9,
and the internal modularization in §16).

## Naming: Quillins

QUILL's plugins are branded **Quillins**. Throughout this document "Quillin" and
"Quillins" are the product-facing name for a QUILL extension in everything a user
reads or hears: menus, the manager dialog, announcements, capability prompts, and
documentation. The neutral technical terms — `extension`, the `quill.extension/1`
manifest schema, the `ext.*` command namespace, and the `QuillExtensionApi` —
remain unchanged in code, schemas, and APIs, so wire formats stay stable while the
experience speaks of Quillins. Where this document describes schema or code, it
uses the technical term; where it describes what a person sees or hears, it says
Quillin.


## 0. Provenance and inspiration

This capability is QUILL's answer to the scripting/add-in model pioneered by
earlier accessible, screen-reader-first Windows editors that exposed almost
their entire object model to add-in code.

Those editors typically scripted the host application in **the host's own
language**: when the application was written in C#/.NET, the add-in language was
a .NET language, so the scripting language matched the platform object model and
its class library. The faithful translation of that design for QUILL is to
expose **QUILL's own object model**, which is **Python** &mdash; see the language
decision below.

## 1. Goals and non-goals

### Goals

- Let power users add **menu items**, **context-menu entries**, and **hotkeys**
  that run custom actions, without rebuilding QUILL.
- Keep the **writing path plain-text-first** and the **screen-reader-first**
  guarantees intact: extensions must never degrade NVDA/JAWS/Narrator parity.
- Make extensions **safe by default**: no ambient filesystem, network, or
  subprocess access unless explicitly declared and user-granted, consistent with
  QUILL's existing consent gates, DPAPI secret handling, and "no silent network
  calls" rule.
- Make extensions **authorable by blind power users** &mdash; the same audience
  those editors served &mdash;
  with plain-text manifests, readable Python, and accessible install/enable UX.
- Preserve the architecture boundary: `quill/core` and `quill/io` stay
  UI-framework-agnostic; only `quill/ui` and `quill/platform/windows` touch `wx`.

### Non-goals (explicitly out of scope for the first iteration)

- A live rich-text/RTF editing surface (a standing QUILL design exclusion).
- Arbitrary native code plugins or replacing core UI widgets.
- A general-purpose marketplace / auto-update of third-party extensions (later).
- JavaScript as the *primary* extension language for deep host integration; Node.js
  is supported as an alternative handler runtime (see §9), but the rich bidirectional
  `QuillExtensionApi` (§5, §14.4) remains Python-only.

## 2. Language decision (resolved)

**Two-layer model, with Python as the scripting language, not JavaScript.**

Rationale: QUILL's platform object model is Python, so scripting it in Python is
the lowest-friction, most powerful, most debuggable, and most maintainable
option — and it is the faithful analogue of scripting a .NET editor in a .NET
language. Choosing JavaScript as the primary language would mean maintaining
a second runtime and a permanent Python⇄JS marshalling layer purely to script an
application that is already Python. JavaScript's only strong advantage
(familiarity) does not outweigh that cost.

A comparison of the options considered (Python, embedded JavaScript via
QuickJS/V8, Lua via `lupa`, WASM via Extism, declarative-only) is retained in
Appendix A.

## 3. Architecture: three layers

### Layer 1 — Declarative manifest (safe, covers the common ~70%)

A static, schema-validated manifest (JSON, validated like every other QUILL
store under `quill/core/schemas/`) that **maps** menu items, context-menu
entries, and hotkeys onto:

- existing built-in QUILL command IDs (the same IDs used in
  `quill/core/keymap.py`), and/or
- text **snippets / templates** (no executable code).

This layer is **non-Turing-complete and safe by construction** — there is no
code execution at all, so it can do nothing except invoke commands QUILL
already trusts and insert literal text. Most real
"add a menu item / bind a key / add a right-click action" requests are satisfied
here with effectively zero risk.

### Layer 2 — Python extension API (real logic, isolated, bidirectional)

For genuine custom logic, an extension ships a Python entry point that QUILL runs
**out-of-process** (mirroring the existing OCR worker-process precedent in the
concurrency model) behind a **capability-gated RPC bridge**. The extension never
imports `wx` and never touches the editor widget directly; it talks to a narrow,
versioned API object and all UI effects are marshalled back onto the UI thread
via `wx.CallAfter`.

Set `"runtime": "python"` (the default when the field is absent) to use this path.

### Layer 3 — Node.js extension runtime ("context in, actions out")

For teams more comfortable with TypeScript/JavaScript, a Quillin may set
`"runtime": "node"` in its manifest. The `main` field then names a `.js` file
(compiled from TypeScript by the author). QUILL spawns `node <main.js>` via the
existing `external_engine.py` allowlist and consent gate, sending one JSONL
request and receiving one JSONL response:

```text
  QUILL → Node:  {"method": "handlerName", "params": {"capabilities": [...], "context": {...}}}
  Node → QUILL:  {"result": null, "actions": [{"type": "announce", "args": ["Done"]}]}
```

The context is pre-populated with editor state (selection, text, cursor offset).
The handler queues *actions* — `replace_selection`, `insert_text`, `announce`,
`set_status`, `open_buffer` — that QUILL dispatches after the process exits. This
"context in, actions out" model is simpler than the Python bidirectional protocol;
it works well for stateless text-processing handlers. Interactive handlers that
need mid-execution prompts or round-trips should use the Python runtime.

The `@quill/api` npm package (`packages/@quill/api/`) provides TypeScript types
and a `runtime.js` shim that implements the stdio protocol for extension authors.

```text
+------------------+        capability-gated RPC         +-----------------------+
|  QUILL UI thread | <--------------------------------> | Extension host worker |
|  (wx, main_frame)|   (stdio/pipe, JSON messages)      | (out-of-process Python)|
+------------------+                                     +-----------------------+
        |  registers menu/hotkey/context hooks                   |
        |  marshals results via wx.CallAfter                     | user extension code
        v                                                        v
   core command dispatch                                  QuillExtensionApi (v1)
```

## 4. Manifest schema (Layer 1 sketch)

Stored per-extension under `%APPDATA%\Quill\extensions\<id>\manifest.json`,
schema-validated, atomic-written, with `.bak`/recovery like other stores.

```jsonc
{
  "schema": "quill.extension/1",
  "id": "com.example.wraptools",
  "name": "Wrap Tools",
  "version": "1.0.0",
  "author": "Jane Power-User",
  "license": "MIT",
  "capabilities": ["editor.read", "editor.write"],   // requested permissions
  "contributes": {
    "commands": [
      { "id": "ext.wraptools.fence", "title": "Wrap In Code Fence",
        "run": { "snippet": "```\n${selection}\n```" } }
    ],
    "menus": [
      { "parent": "Format", "command": "ext.wraptools.fence" }
    ],
    "context_menu": [
      { "when": "editor.hasSelection", "command": "ext.wraptools.fence" }
    ],
    "hotkeys": [
      { "command": "ext.wraptools.fence", "binding": "Ctrl+Shift+Grave, F" }
    ]
  },
  "main": "extension.py"   // optional; presence triggers Layer 2 host
}
```

Notes:

- `hotkeys[].binding` reuses QUILL's existing binding grammar, including the
  **QUILL Key** chord prefix (`Ctrl+Shift+Grave, …`). Conflicts are detected with
  the existing `find_keymap_conflict` logic and reported to the user; extension
  bindings never silently override user/default bindings.
- `menus[].parent` / `context_menu[]` register through the existing menu and
  context-menu construction paths in `quill/ui`, honouring the project rule to
  **defer menu mutations until menus are closed**.
- A `command.run.snippet` with no `main` is pure Layer 1 (no code execution).

## 5. The Python extension API (Layer 2 sketch)

A single, versioned, capability-checked facade — no direct widget access:

```python
class QuillExtensionApi:        # v1, passed to the extension's register()
    # editor.read
    def get_text(self) -> str: ...
    def get_selection(self) -> str: ...
    def get_cursor(self) -> CursorAddress: ...     # line, column, percent
    # editor.write   (all routed through core commands + undo history)
    def replace_selection(self, text: str) -> None: ...
    def insert_text(self, text: str) -> None: ...
    # ui (always marshalled to the UI thread)
    def announce(self, message: str) -> None: ...  # screen-reader announcement
    def register_command(self, command_id: str, title: str, handler) -> None: ...
    # fs / net only if capability granted + user-consented at install/run
    def read_file(self, path: str) -> str: ...     # requires "fs.read"
    def fetch(self, url: str) -> Response: ...      # requires "net" + consent gate
```

Design rules:

- Every method maps to an existing core operation so extension edits flow through
  **command + history** (undoable) and through the **announcement engine** for
  consistent NVDA/JAWS/Narrator output.
- All editor mutations go through `quill/core`; the extension process holds **no**
  `wx` reference and **no** direct buffer handle.
- The API is **versioned** (`v1`); breaking changes ship a new version while old
  extensions keep working against the old facade.

## 6. Security & consent model

- **Default deny.** No capability ⇒ no filesystem, no network, no subprocess.
  Pure-snippet extensions need no capabilities at all.
- **Declared + granted.** Capabilities are listed in the manifest and **shown to
  the user at install/enable time**; network/file capabilities additionally pass
  through QUILL's existing per-action **consent gate** with visible progress and
  outcome (no silent network calls).
- **Isolation.** Layer 2 runs out-of-process; a crash or hang in an extension
  cannot take down the editor or corrupt the buffer (the UI side owns the buffer).
- **No secrets to extensions.** Extensions never receive DPAPI-protected secrets
  or document content over the wire unless a capability + consent explicitly
  authorise it; **no document content is ever logged**.
- **Signing/trust (later).** A future iteration may add signature/trust prompts
  and a per-extension audit log.

## 7. Accessibility of the authoring experience

- Manifests are plain JSON and extensions are plain `.py` — both fully readable in
  QUILL itself, following that same authoring philosophy.
- The **Quillins Manager** dialog uses stock controls
  (`wx.ListBox` / `wx.TextCtrl` read-only review panes, explicit default buttons,
  consistent Escape/Close handling, focus returned to the editor on close) per
  the project's dialog/accessibility rules, and is registered in `dialogs.md`.
- Errors from extension code surface as **announced**, reviewable text (a
  read-only multiline control), never as transient-only message boxes.

## 8. Packaging

- Bundled with the existing Windows distribution builder / Inno Setup component
  model. Layer 1 + Layer 2 (Python host) need **no new native runtime** because
  the interpreter already ships with QUILL.
- The optional QuickJS snippet evaluator (Appendix B) would be the *only* item
  that adds a native dependency, which is why it is deferred and optional.

## 9. Node.js runtime support (shipped, issue #158)

**Status: implemented and tested.** The `"runtime": "node"` field is in the
manifest schema, the validator, and the loader. `quill/plugins/node_quillin_runner.py`
drives node handlers through `external_engine.run_request`.

### 9.1 How Node.js Quillins work

Set `"runtime": "node"` and point `"main"` at a `.js` file. QUILL sends a single
JSONL request with the method (handler function name), the declared capabilities
list, and a context dict. The Node process must write exactly one JSONL response:

```json
{"result": null, "actions": [
  {"type": "announce",          "args": ["5 words"]},
  {"type": "replace_selection", "args": ["new text"]},
  {"type": "insert_text",       "args": ["inserted"]},
  {"type": "set_text",          "args": ["full replacement"]},
  {"type": "open_buffer",       "args": ["content", "Title"]},
  {"type": "set_status",        "args": ["status message"]}
]}
```

Or on error:

```json
{"error": "Something went wrong"}
```

### 9.2 The `@quill/api` package

Published Quillins use the `@quill/api` npm package (`packages/@quill/api/`):

```typescript
import { runHandler, QuillinContext } from '@quill/api/runtime';

runHandler({
  wordCount(ctx: QuillinContext): void {
    const words = (ctx.getText() || ctx.getSelection()).trim().split(/\s+/).length;
    ctx.announce(`${words} words`);
  },
});
```

The package ships `index.d.ts` for full TypeScript typing and `runtime.js` for
the stdio event loop. Bundled Quillins may inline the shim for zero npm dependency
(see `quill/quillins_bundled/word-count-node/extension.js`).

### 9.3 Consent and security

Node Quillins go through the same `external_engine.py` consent gate as AI
engines: the master external-engines switch must be on, and `node` must be on
PATH (or a full path supplied). The executable allowlist is enforced in both
`configure_engine` and `probe_engine` — a tampered config cannot launch arbitrary
programs.

If the user does not have Node.js installed, `run_node_command` returns an
`EngineResult` with `unavailable=True` and a plain-language error; QUILL announces
it rather than crashing.

### 9.4 Limitations vs. Python Layer 2

- No mid-execution API calls. The handler cannot call `get_text()` during
  execution; all read state is passed in the context at invocation time.
- No interactive prompts. `ui.prompt`, `ui.choices` are Python-only in v1.
- No storage API. The `storage` capability is Python-only in v1.
- No async-safe cancellation. Long Node handlers block until process exit or
  the `external_engine` timeout fires.

For anything interactive or that needs mid-execution reads, use `"runtime": "python"`.

### 9.5 QuickJS (not shipped, deferred)

The earlier plan to embed QuickJS as a `.js` snippet evaluator was superseded by
the Node subprocess model, which covers the TypeScript developer audience more
directly without adding a native binary dependency.

## 10. Phasing / milestones

Status note: **M1–M3 are implemented and tested** (see §0a). M4 remains optional
future work. Third-party execution stays gated off for 1.0 (SEC-8).

1. **M1 — Manifest + loader (Layer 1): _Done._** Schema, validation, load/enable/
   disable, command/menu/context/hotkey registration, conflict detection,
   Quillins Manager dialog. No code execution.
2. **M2 — Python host (Layer 2): _Done._** Out-of-process worker, RPC bridge,
   `QuillExtensionApi v1` with `editor.read`/`editor.write`/`announce`/
   `register_command`, undo/announcement integration through the host services.
3. **M3 — Capabilities + consent: _Done._** `fs.read`/`fs.write`/`net`,
   install-time disclosure, per-action consent gate. (A per-extension audit log
   remains a future enhancement.)
4. **M4 — Node.js runtime (Layer 3): _Done_ (issue #158).** `"runtime": "node"` manifest field,
   `node_quillin_runner.py`, `@quill/api` npm package, bundled `word-count-node` proof Quillin.
   75 tests. Node is optional and consent-gated; Python remains the default runtime.
5. **M5 (optional / 1.1+) — QUILL Developer Console (QDC).** Embedded Python REPL plus
   TypeScript bridge for live introspection and automation. Not yet implemented; see
   `docs/userguide.md` for the PRD.

## 11. Testing strategy

Status note: **this strategy is implemented** — the test files are listed in the
§0a map. The bar below is what those tests enforce.

- `quill/core` (manifest model, schema validation, snippet expansion, capability
  checks, conflict detection, loader/SEC-8 gating): real unit tests, wx-free,
  strict mypy. The schema artifact and the hand-rolled validator are asserted to
  agree (capability enum, menu parents, schema id).
- UI registration (menu/context/hotkey wiring, Manager dialog): source-contract
  tests (`tests/unit/ui/test_main_frame_quillins.py`) plus the A11Y-4 dialog
  inventory/contract guard for the Quillins Manager dialog.
- Host/RPC bridge: integration tests
  (`tests/integration/test_quillins_host_integration.py`) spawn the real worker
  subprocess and exercise read/write/announce, the capability-denied path, the
  consent-denied path, network-with-consent, handler-error isolation, and main-
  module path containment.
- Security: explicit tests that an undeclared capability is rejected (in-worker
  and at the dispatcher), that consent defaults to deny, and that diagnostic
  `log` output never reaches user announcements.
- **Node runtime (issue #158):** 75 new tests across four files:
  `test_quillins_node_runtime.py` (26 tests — manifest model and schema round-trip),
  `test_node_quillin_runner.py` (31 tests — dispatch, protocol content, failure modes),
  `test_quillin_lint_node.py` (11 tests — linter accepts node manifests, rejects
  mismatched extensions), `test_quillins_bundled_word_count_node.py` (15 tests —
  manifest correctness + protocol simulation + optional real-Node integration).
  Two real-node integration tests are `skipif(shutil.which("node") is None)` so
  they run in environments with Node but never block CI that doesn't have it.

## 12. Open questions for review

1. Distribution: local folder install only for 2.0, or a curated gallery later?
2. Do we want per-extension **profiles** (tie enablement to QUILL feature
   profiles) in the first cut, or global enable/disable only?
3. Hotkey precedence when an extension binding conflicts with a user rebinding —
   reject (proposed) vs. prompt-to-override?
4. Should Layer 1 snippets support the existing snippet token system, unifying
   "snippets" and "extension snippets" into one engine?
5. Minimum capability set for M2 — is `editor.read` + `editor.write` + `announce`
   enough to be useful, deferring `fs`/`net` to M3?

---

## 13. Manifest JSON Schema (normative)

This is the authoritative, machine-validatable contract for `quill.extension/1`
manifests. It is the schema that will live under `quill/core/schemas/` and be
enforced by the loader. AI or human authors can validate a generated manifest
against this before submission.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://quill.app/schemas/extension/1.json",
  "title": "QUILL Extension Manifest",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema", "id", "name", "version"],
  "properties": {
    "schema": { "const": "quill.extension/1" },
    "id": {
      "type": "string",
      "description": "Reverse-DNS unique id, e.g. com.example.wraptools.",
      "pattern": "^[a-z0-9]+([._-][a-z0-9]+)*$",
      "minLength": 3,
      "maxLength": 128
    },
    "name": { "type": "string", "minLength": 1, "maxLength": 80 },
    "version": {
      "type": "string",
      "description": "Semantic version MAJOR.MINOR.PATCH.",
      "pattern": "^\\d+\\.\\d+\\.\\d+$"
    },
    "author": { "type": "string", "maxLength": 120 },
    "description": { "type": "string", "maxLength": 400 },
    "license": { "type": "string", "maxLength": 64 },
    "min_quill_version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+$",
      "description": "Lowest QUILL version this extension supports."
    },
    "capabilities": {
      "type": "array",
      "uniqueItems": true,
      "items": {
        "enum": [
          "editor.read",
          "editor.write",
          "ui.announce",
          "ui.command",
          "ui.prompt",
          "ui.status",
          "ui.choices",
          "ui.log",
          "storage",
          "fs.read",
          "fs.write",
          "net",
          "clipboard.read",
          "clipboard.write",
          "settings.own.read",
          "settings.own.write",
          "settings.core.read",
          "settings.core.write",
          "document.directives",
          "document.events"
        ]
      }
    },
    "runtime": {
      "type": "string",
      "enum": ["python", "node"],
      "description": "Extension runtime. Defaults to 'python'. Use 'node' for Node.js handlers; main must then be a .js file."
    },
    "main": {
      "type": "string",
      "description": "Relative path to the entry module. .py for python runtime (default); .js for node runtime.",
      "pattern": "^[A-Za-z0-9_./-]+\\.(py|js)$"
    },
    "contributes": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "commands": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["id", "title"],
            "properties": {
              "id": {
                "type": "string",
                "pattern": "^ext\\.[a-z0-9]+([._-][a-z0-9]+)*$",
                "description": "Must be namespaced under ext. to avoid colliding with built-in command ids."
              },
              "title": { "type": "string", "minLength": 1, "maxLength": 80 },
              "run": {
                "type": "object",
                "description": "How the command executes. Exactly one of snippet or handler.",
                "oneOf": [
                  {
                    "additionalProperties": false,
                    "required": ["snippet"],
                    "properties": {
                      "snippet": {
                        "type": "string",
                        "description": "Literal text inserted/replacing selection. Supports ${selection}, ${clipboard}, ${date}, ${time}, ${filename} placeholders. No code execution."
                      }
                    }
                  },
                  {
                    "additionalProperties": false,
                    "required": ["handler"],
                    "properties": {
                      "handler": {
                        "type": "string",
                        "description": "Name of the handler function. For python runtime: registered via api.register_command. For node runtime: exported function in the runHandler map. Requires main + ui.command capability."
                      }
                    }
                  }
                ]
              }
            }
          }
        },
        "menus": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["parent", "command"],
            "properties": {
              "parent": {
                "type": "string",
                "description": "Top-level menu title to attach under, e.g. File, Edit, Format, Tools, Help.",
                "enum": ["File", "Edit", "Format", "Tools", "Navigate", "View", "Help"]
              },
              "command": { "type": "string", "description": "A command id contributed above or a built-in command id." }
            }
          }
        },
        "context_menu": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["command"],
            "properties": {
              "command": { "type": "string" },
              "when": {
                "type": "string",
                "description": "Optional visibility guard.",
                "enum": ["always", "editor.hasSelection", "editor.hasText", "editor.empty"]
              }
            }
          }
        },
        "hotkeys": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["command", "binding"],
            "properties": {
              "command": { "type": "string" },
              "binding": {
                "type": "string",
                "description": "QUILL binding grammar. Supports the QUILL Key chord prefix, e.g. 'Ctrl+Shift+Grave, F'. Conflicts are rejected, never silently overridden."
              }
            }
          }
        }
      }
    },
    "categories": {
      "type": "array",
      "uniqueItems": true,
      "items": {
        "enum": [
          "writing", "accessibility", "braille", "productivity",
          "developer", "formatting", "navigation", "ai",
          "integration", "education", "utilities"
        ]
      },
      "description": "Taxonomy labels for the Quillins Manager filter."
    },
    "requires": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id"],
        "properties": {
          "id": { "type": "string", "description": "Fully-qualified id of the required Quillin." },
          "min_version": { "type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$", "description": "Minimum version of the dependency." }
        }
      },
      "description": "Other Quillins that must be installed and valid before this one loads."
    },
    "net_allowed_hosts": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Restrict the net capability to these hostnames or *.domain.com wildcard patterns."
    }
  },
  "allOf": [
    {
      "$comment": "A handler-based command requires an entry module (main).",
      "if": {
        "properties": {
          "contributes": {
            "properties": {
              "commands": {
                "contains": { "properties": { "run": { "required": ["handler"] } } }
              }
            }
          }
        }
      },
      "then": { "required": ["main"] }
    },
    {
      "$comment": "Node runtime requires a .js main; python runtime (default) requires a .py main.",
      "if": { "properties": { "runtime": { "const": "node" } }, "required": ["runtime"] },
      "then": { "properties": { "main": { "pattern": "^[A-Za-z0-9_./-]+\\.js$" } } },
      "else": {
        "if": { "required": ["main"] },
        "then": { "properties": { "main": { "pattern": "^[A-Za-z0-9_./-]+\\.py$" } } }
      }
    }
  ]
}
```

## 14. Extension authoring reference (humans and AI)

This section is the complete, self-contained reference an author needs. It is
written so an LLM can produce a valid, working extension from this document
alone, with no access to QUILL source.

### 14.1 Capability catalogue

| Capability | Grants | Consent | Notes |
| --- | --- | --- | --- |
| `editor.read` | Read buffer text, selection, cursor address | Install-time disclosure | Required by `get_text`, `get_selection`, `get_cursor` |
| `editor.write` | Insert text, replace selection (undoable) | Install-time disclosure | All writes flow through core command + history |
| `ui.announce` | Send screen-reader announcements | Install-time disclosure | Required by `announce` |
| `ui.command` | Register `handler` commands invoked from menus/hotkeys | Install-time disclosure | Required when `run.handler` is used |
| `fs.read` / `fs.write` | Read/write files by path | Per-action consent gate | Paths validated; no access outside granted scope |
| `net` | Outbound HTTP(S) | Per-action consent gate, visible progress | No silent network calls — ever |
| `clipboard.read` / `clipboard.write` | Read/write the system clipboard | Install-time disclosure | |
| `ui.status` | Set the status bar message | Install-time disclosure | Required by `set_status`; not consent-gated |
| `ui.choices` | Show a native single-choice dialog and receive the user's pick | Install-time disclosure | Required by `show_choices` |
| `storage` | Per-extension persistent key/value store (in-memory, per session) | Install-time disclosure | Required by `get_storage`, `set_storage`, `delete_storage`; isolated per extension id |

A pure snippet-only extension declares **no** capabilities.

### 14.2 Contribution reference

- **commands** — declare an `ext.*`-namespaced id + human title; `run` is either a
  `snippet` (Layer 1, no code) or a `handler` (Layer 2, requires `main` +
  `ui.command`).
- **menus** — attach a command under a fixed top-level menu (`parent`). Menu
  mutation is deferred until menus close (project rule).
- **context_menu** — attach a command to the editor right-click menu, optionally
  guarded by a `when` predicate.
- **hotkeys** — bind a command using QUILL's binding grammar, including the QUILL
  Key chord prefix `Ctrl+Shift+Grave, <key>`. Conflicts are detected with the
  same logic as user keymaps and **rejected with an announced message**.

### 14.3 Snippet placeholder reference (Layer 1)

| Placeholder | Expands to |
| --- | --- |
| `${selection}` | Current selection (empty string if none) |
| `${clipboard}` | Current clipboard text (requires `clipboard.read`) |
| `${date}` | Current date in the user's configured format |
| `${time}` | Current time in the user's configured format |
| `${filename}` | Current document file name (empty if unsaved) |
| `${title}` | Document file name stem without extension (empty if unsaved) |
| `${line_number}` | Current line number (1-indexed) |
| `${word_at_cursor}` | Word immediately surrounding the insertion point |
| `${uuid}` | A fresh UUID4 generated at expansion time |
| `${cursor}` | Final cursor position marker after insertion |

### 14.4 Python API reference (Layer 2, `QuillExtensionApi` v1)

Every extension's entry module defines a top-level `register(api)` function.
QUILL calls it once when the extension loads. All methods are synchronous from
the extension's perspective; UI effects are marshalled onto the UI thread by the
host. Methods raise `CapabilityError` if the required capability was not granted.

| Method | Capability | Returns | Description |
| --- | --- | --- | --- |
| `api.register_command(command_id, handler)` | `ui.command` | `None` | Bind a `handler` name (referenced by `run.handler`) to a callable `handler(ctx)` |
| `api.get_text()` | `editor.read` | `str` | Full document text |
| `api.get_selection()` | `editor.read` | `str` | Selected text (`""` if none) |
| `api.get_cursor()` | `editor.read` | `CursorAddress` | `.line` (1-based), `.column` (1-based), `.percent` (0–100) |
| `api.insert_text(text)` | `editor.write` | `None` | Insert at cursor (undoable) |
| `api.replace_selection(text)` | `editor.write` | `None` | Replace selection, or insert if none (undoable) |
| `api.announce(message)` | `ui.announce` | `None` | Screen-reader announcement via the announcement engine |
| `api.read_file(path)` | `fs.read` | `str` | Read a text file (consent-gated) |
| `api.write_file(path, text)` | `fs.write` | `None` | Write a text file (consent-gated) |
| `api.fetch(url, *, method="GET", body=None)` | `net` | `Response` | HTTP(S) request (consent-gated, visible progress) |
| `api.get_clipboard()` | `clipboard.read` | `str` | Clipboard text |
| `api.set_clipboard(text)` | `clipboard.write` | `None` | Set clipboard text |
| `api.get_cursor_offset()` | `editor.read` | `int` | Cursor position as a character offset from the start of the document |
| `api.get_selection_range()` | `editor.read` | `dict` | Selection bounds as `{"start": int, "end": int}` character offsets; `start == end` when no selection |
| `api.set_cursor(offset)` | `editor.write` | `None` | Move the cursor to a character offset |
| `api.replace_range(start, end, text)` | `editor.write` | `None` | Replace the text between `start` and `end` offsets with `text` (undoable) |
| `api.set_status(message)` | `ui.status` | `None` | Set the editor status bar text; no consent gate |
| `api.show_choices(title, items)` | `ui.choices` | `str \| None` | Show a native single-choice dialog; returns the selected string or `None` if cancelled |
| `api.get_storage(key)` | `storage` | `str \| None` | Get a persisted value for `key`; returns `None` if not set |
| `api.set_storage(key, value)` | `storage` | `None` | Store `value` under `key`; both must be strings |
| `api.delete_storage(key)` | `storage` | `None` | Remove `key` from storage; no-op if not present |

`handler(ctx)` receives a `ctx` exposing the same read/write/announce surface
scoped to the invocation, so a handler typically reads, computes, and writes back.

Error types an author may see: `CapabilityError`, `ConsentDeniedError`,
`ConflictError` (hotkey/menu), `ApiVersionError`.

### 14.5 Worked example A — snippet-only (no capabilities, no code)

`manifest.json`:

```json
{
  "schema": "quill.extension/1",
  "id": "com.example.fence",
  "name": "Code Fence",
  "version": "1.0.0",
  "contributes": {
    "commands": [
      { "id": "ext.fence.wrap", "title": "Wrap In Code Fence",
        "run": { "snippet": "```\n${selection}\n```\n${cursor}" } }
    ],
    "context_menu": [ { "when": "editor.hasSelection", "command": "ext.fence.wrap" } ],
    "hotkeys": [ { "command": "ext.fence.wrap", "binding": "Ctrl+Shift+Grave, F" } ]
  }
}
```

### 14.5a Worked example A2 — new placeholders in action

Demonstrates `${title}`, `${line_number}`, `${word_at_cursor}`, and `${uuid}`.

`manifest.json`:

```json
{
  "schema": "quill.extension/1",
  "id": "com.example.context-inserts",
  "name": "Context Inserts",
  "version": "1.0.0",
  "contributes": {
    "commands": [
      {
        "id": "ext.context-inserts.front-matter",
        "title": "Insert Front Matter",
        "run": { "snippet": "---\ntitle: ${title}\ndate: ${date}\n---\n\n${cursor}" }
      },
      {
        "id": "ext.context-inserts.bold-word",
        "title": "Bold Word at Cursor",
        "run": { "snippet": "**${word_at_cursor}**${cursor}" }
      },
      {
        "id": "ext.context-inserts.line-anchor",
        "title": "Insert Line Anchor",
        "run": { "snippet": "<!-- anchor:${uuid} line:${line_number} -->${cursor}" }
      }
    ],
    "menus": [
      { "parent": "Insert", "command": "ext.context-inserts.front-matter" },
      { "parent": "Format", "command": "ext.context-inserts.bold-word" },
      { "parent": "Insert", "command": "ext.context-inserts.line-anchor" }
    ],
    "context_menu": [
      { "command": "ext.context-inserts.bold-word", "when": "editor.hasText" }
    ]
  }
}
```

Token behaviour at runtime:

- `${title}` — for `notes.md` expands to `notes`; empty string when the buffer is unsaved.
- `${word_at_cursor}` — cursor inside `hello` → `hello`; between words → empty string.
- `${line_number}` — always 1-indexed regardless of how the file renders.
- `${uuid}` — generates a different UUID4 on every invocation, so two calls always produce distinct anchors.

### 14.6 Worked example B — Python handler

`manifest.json`:

```json
{
  "schema": "quill.extension/1",
  "id": "com.example.titlecase",
  "name": "Title Case",
  "version": "1.0.0",
  "capabilities": ["editor.read", "editor.write", "ui.announce", "ui.command"],
  "main": "extension.py",
  "contributes": {
    "commands": [
      { "id": "ext.titlecase.run", "title": "Title Case Selection",
        "run": { "handler": "title_case" } }
    ],
    "menus": [ { "parent": "Format", "command": "ext.titlecase.run" } ],
    "hotkeys": [ { "command": "ext.titlecase.run", "binding": "Ctrl+Shift+Grave, T" } ]
  }
}
```

`extension.py`:

```python
def register(api):
    def title_case(ctx):
        text = ctx.get_selection()
        if not text:
            ctx.announce("Title Case: no selection")
            return
        ctx.replace_selection(text.title())
        ctx.announce("Title Case applied")
    api.register_command("title_case", title_case)
```

### 14.7 Worked example C — Node.js handler (Layer 3)

A Node.js Quillin sets `"runtime": "node"` and `"main"` to a `.js` file.
QUILL sends a single JSONL request; the process writes one JSONL response with
a list of actions and exits.

`manifest.json`:

```json
{
  "schema": "quill.extension/1",
  "id": "com.example.shout",
  "name": "Shout",
  "version": "1.0.0",
  "runtime": "node",
  "capabilities": ["editor.read", "editor.write", "ui.announce", "ui.command"],
  "main": "extension.js",
  "contributes": {
    "commands": [
      { "id": "ext.shout.run", "title": "Shout Selection",
        "run": { "handler": "shout" } }
    ],
    "menus": [ { "parent": "Format", "command": "ext.shout.run" } ]
  }
}
```

`extension.js` (inline runtime shim, no npm required):

```javascript
process.stdin.resume();
process.stdin.setEncoding('utf8');
let raw = '';
process.stdin.on('data', chunk => { raw += chunk; });
process.stdin.on('end', () => {
  const req = JSON.parse(raw.trim());
  const method = req.method;
  const ctx = req.params.context;

  const handlers = {
    shout(context) {
      const text = context.selection || context.text || '';
      if (!text.trim()) {
        return [{ type: 'announce', args: ['Shout: no text'] }];
      }
      return [
        { type: 'replace_selection', args: [text.toUpperCase()] },
        { type: 'announce', args: ['Selection converted to upper case'] }
      ];
    }
  };

  if (!handlers[method]) {
    process.stdout.write(JSON.stringify({ error: `unknown handler: ${method}` }) + '\n');
    process.exit(1);
  }
  const actions = handlers[method](ctx);
  process.stdout.write(JSON.stringify({ result: null, actions }) + '\n');
});
```

Or using the `@quill/api` npm package (for authors who use npm):

```javascript
const { runHandler } = require('@quill/api/runtime');

runHandler({
  shout(ctx) {
    const text = ctx.getSelection() || ctx.getText();
    if (!text.trim()) {
      ctx.announce('Shout: no text');
      return;
    }
    ctx.replaceSelection(text.toUpperCase());
    ctx.announce('Selection converted to upper case');
  },
});
```

**Node.js vs. Python runtime — when to use each:**

| Need | Use |
| --- | --- |
| Simple text transform | Either |
| npm ecosystem (markdown parsers, etc.) | Node |
| Mid-execution prompts (`show_choices`) | Python |
| Storage between invocations | Python |
| TypeScript types and IDE support | Node + `@quill/api` |
| Existing Python library | Python |

## 15. AI authoring guide — deterministic generation contract

This section gives an AI agent an unambiguous procedure to generate a valid
extension. Following it should yield a manifest that passes §13 and an entry
module that loads under §14.4.

**Generation checklist (must all hold):**

1. `schema` is exactly `"quill.extension/1"`.
2. `id` is reverse-DNS, lowercase, matches the §13 pattern, and is globally unique.
3. `version` is `MAJOR.MINOR.PATCH`.
4. Every contributed command `id` starts with `ext.` and is unique within the file.
5. Every `menus[].command`, `context_menu[].command`, and `hotkeys[].command`
   references either a contributed command id or a documented built-in id.
6. If **any** command uses `run.handler`, then `main` is present **and**
   `capabilities` includes `ui.command`.
7. `capabilities` is the minimal set: include a capability **iff** an API method
   or placeholder in the extension requires it (see §14.1, §14.3, §14.4).
8. Hotkey `binding` uses the QUILL grammar; prefer the QUILL Key prefix
   (`Ctrl+Shift+Grave, <letter>`) to avoid clashing with built-ins.
9. **Python runtime (default):** The entry module defines exactly one top-level
   `register(api)` and registers every `handler` name referenced by the manifest.
   No `wx` import; all host access through the granted `api` methods.
10. **Node.js runtime** (`"runtime": "node"`): `main` must be a `.js` file. The
    script reads one JSONL line from stdin and writes one JSONL line to stdout,
    then exits. The response must be `{"result": null, "actions": [...]}` or
    `{"error": "..."}`. Handler names in `runHandler({...})` must match the
    `run.handler` values in the manifest.
11. No direct filesystem/network/subprocess/clipboard access except through the
    granted API surface (Python: `api` methods; Node: actions only — no fs/net in
    Node handlers in v1).

**Minimal-capability decision table:**

| If the extension… | Declare |
| --- | --- |
| only inserts literal/snippet text | *(none)* |
| reads buffer/selection/cursor | `editor.read` |
| inserts or replaces text | `editor.write` |
| speaks to the screen reader | `ui.announce` |
| has any `run.handler` command | `ui.command` + `main` |
| reads/writes files | `fs.read` / `fs.write` |
| makes network requests | `net` |
| touches the clipboard | `clipboard.read` / `clipboard.write` |
| uses cursor offsets or `replace_range` | `editor.read` and/or `editor.write` (already covers these methods) |
| sets status bar text | `ui.status` |
| shows a choice dialog | `ui.choices` |
| persists data between invocations | `storage` |

**Machine-readable contract summary (for prompt embedding):**

```text
--- PYTHON RUNTIME (default) ---
ENTRYPOINT: register(api) -> None              # exactly one, top-level
HANDLER:    handler(ctx) -> None               # ctx mirrors api read/write/announce
WRITES:     undoable, via core commands only
THREADING:  api is sync; UI effects marshalled by host (never call wx)
DENY:       no capability => no fs/net/subprocess/clipboard
NAMESPACE:  command ids must start with "ext."
CONFLICTS:  hotkey/menu conflicts are rejected + announced, never overridden
VERSION:    target QuillExtensionApi v1

--- NODE.JS RUNTIME ("runtime": "node") ---
MANIFEST:   "runtime": "node",  "main": "<file>.js"
PROTOCOL:   stdin  -> one JSONL line: {"method":"<handler>","params":{"capabilities":[...],"context":{...}}}
            stdout <- one JSONL line: {"result":null,"actions":[...]} | {"error":"<msg>"}
ACTIONS:    replace_selection(text), insert_text(text), set_text(text),
            open_buffer(content, title), announce(message), set_status(message)
RUNTIME:    process reads stdin, dispatches handler, writes stdout, exits 0
DENY:       no mid-execution API calls; no fs/net in v1 Node handlers
NAMESPACE:  same ext.* command id rules apply
```

---

## 16. Internal modularization — core as a framework

A deliberate, longer-horizon consequence of this design: the **contribution
grammar** defined here (commands, menus, hotkeys, context-menu entries) is the
same vocabulary QUILL already uses *internally* to wire up its built-in
features. That makes it a natural blueprint for decomposing the
`quill/ui/main_frame.py` "god object" into self-registering **first-party
feature modules**, leaving `quill/core` as a genuine framework.

### 16.1 Two tiers, one vocabulary

There are **two tiers of extension**, sharing one contribution grammar but
differing in **trust level and API breadth** — not in how they appear to users.

| | First-party feature modules | Third-party extensions |
| --- | --- | --- |
| Trust | Trusted, shipped, reviewed | Untrusted |
| Process | In-process | Out-of-process (Appendix B) |
| API breadth | Rich, synchronous host API (editor, dialogs, settings, undo, workers, platform, announcements) | Narrow, capability-gated `QuillExtensionApi` (§5) |
| Isolation | None needed (trusted code) | Process separation + capability/consent gate (§6); not an OS-level sandbox |
| Registration | Same contribution grammar (§4) | Same contribution grammar (§4) |

The crucial rule: **first-party features must NOT be routed through the
out-of-process, capability-gated path.** Built-ins need rich,
synchronous, in-process access; forcing them across the RPC bridge would be a
severe downgrade in capability, latency (per-keystroke operations!), and
complexity for zero security benefit, since the code is already trusted.

### 16.2 What this enables

- An internal `register(host)` module interface, where `host` exposes the rich
  trusted API. Related commands (line-ops, EDS parity, search, formatting…) are
  extracted from `main_frame.py` into self-registering modules.
- `quill/core` keeps only the framework: document model, command registry,
  keymap, event bus, feature gating, and the announcement engine.
- The contribution grammar (this document) becomes the single registration
  mechanism for both tiers.

### 16.3 Honest limits (do not over-rotate)

- **Do not pluginize the editor surface or the accessibility / announcement
  engine.** The plain-text `wx.TextCtrl` writing path and NVDA/JAWS/Narrator
  parity are the framework's central guarantee, not a plugin. Delegating them is
  how accessibility regresses.
- `main_frame.py` is deeply entangled (shared mutable state, wx id maps, ordering
  dependencies). Decompose **incrementally and opportunistically, behind
  characterization tests** — never a big-bang "everything is a plugin" rewrite.
- Feature profiles already deliver much of the user-facing modularity benefit, so
  the refactor's justification is **maintainability**, not new capability.
- This is a **2.0-scale effort**, sequenced after user-facing wins.

### 16.4 The migration playbook

The concrete, sequenced procedure for moving first-party code off the
`main_frame.py` god object and onto this contribution grammar — pilot selection,
the `register(host)` module shape, the host-facade surface, characterization-test
discipline, and a wave-by-wave order — lives in a dedicated companion document:
**`docs/quillins.md`**. Read this section for the *why*; read that
document for the *how*.

## 17. Seamless use, transparent governance

Extensions should be **indistinguishable from built-in features at the point of
use**, while remaining **fully auditable and controllable** in management.

### 17.1 Seamless at the point of use

A user should never be able to tell, while writing, whether a command came from
core, a bundled module, or a third-party extension. All of them:

- appear in the same menus, command palette, and context menus;
- bind through the same keymap (and surface in the key-describer / learning
  mode);
- announce outcomes through the same announcement engine with NVDA/JAWS/Narrator
  parity;
- respect the same feature-gating and Settings UI.

That uniformity is exactly *why* both tiers share one contribution grammar
(§16.1). No second-class citizens; no "bolted-on" feel.

### 17.2 Transparent where it matters (non-negotiable)

Seamlessness hides the *seam*, never the *capabilities*. Consistent with QUILL's
"no silent network calls", per-action consent, and DPAPI rules:

- A **Quillins Manager** lists every installed Quillin, its publisher, and
  its granted capabilities, so the user can audit, disable, or revoke.
- **Capability prompts** (§6) surface the first time an untrusted extension wants
  something sensitive (network, filesystem beyond the document, clipboard, running
  executables). Trusted first-party modules do not prompt; third-party ones do.
- **Provenance is visible on demand** (e.g. in command-palette details or a
  "Where did this come from?" affordance), even though it is invisible by default.

Principle: **users should not have to *think* about whether something is an
extension during normal use, but must always be *able to find out* and *control
it* when trust or accessibility is at stake.** Hiding the seam is a UX win;
hiding capabilities or network access would violate QUILL's privacy-first
contract.

## 18. Declarative dialogs & accessibility enforcement

Extensions may contribute **dialogs**, but they **describe** dialogs
declaratively — they never instantiate a `wx` widget. QUILL renders them. This
makes inaccessible or unsafe UI **structurally impossible** rather than merely
discouraged.

### 18.1 The mechanism

QUILL already has the right primitive: `show_web_form` (`quill/ui/web_form.py`)
builds a dialog from a **field spec** using vetted stock controls
(`wx.TextCtrl`, `wx.ListBox`, `wx.Dialog`) with consistent focus, a default
button, and Escape/Close handling. (The EDS `DLG-1` migrations already use it.)

An extension contributes a dialog description:

```json
{
  "dialog": "calculate_date",
  "title": "Calculate Date",
  "fields": [
    { "id": "anchor", "label": "Start date", "type": "text" },
    { "id": "offset", "label": "Days to add", "type": "number" },
    { "id": "unit",   "label": "Unit", "type": "choice",
      "choices": ["days", "weeks", "months"] }
  ]
}
```

…and receives back a plain dict (`{anchor, offset, unit}`). It never creates a
control, sets a sizer, or manages focus.

### 18.2 Why this enforces accessibility without risk

- **Accessibility is structural, not requested.** Every dialog comes from QUILL's
  one renderer, so it inherits stock-control usage, focus return to editor,
  label/announcement parity, and the **A11Y-4 dialog-contract guard**
  automatically. An extension *cannot* produce an inaccessible dialog because it
  cannot produce a dialog at all — only a description of one.
- **No untrusted code in the UI thread.** Third-party logic stays out-of-process
  (Appendix B); only data crosses the boundary. A buggy or malicious extension
  cannot freeze the UI, draw a custom-painted control, or break screen-reader
  focus.
- **`dialogs.md` stays truthful.** Because the renderer is central, contributed
  dialogs are enumerable and can be registered into the manual regression map the
  same way native dialogs are.

### 18.3 Constrained vocabulary is the safety property

- The field-type catalogue is intentionally **finite**: text, multiline
  read-only, number, choice, checkbox, file-pick-with-consent, list. Allowing
  "arbitrary layout" or "custom control" would forfeit the guarantee — so it is
  not allowed. That finiteness *is* the safety property.
- Genuinely novel custom UI is **out of scope** for extensions; it must be a
  first-party module reviewed against A11Y-4 (§16.1), not an out-of-process
  extension.
- Anything sensitive a dialog *triggers* (network, file write, run executable)
  still passes through capability prompts (§6). An accessible dialog never
  bypasses consent.

---

## 19. Design principles carried from the editor proposals (rtf.md)

The native-RTF, Compose-mode, keyword, and grammar proposals in `rtf.md` share a
through-line: take a capability the rest of the industry built for the eye and
make QUILL the place where it finally *speaks*. Quillins are an extensibility
system, but the same principles apply, and applying them is what turns a competent
plugin model into a delightful, screen-reader-first one. This section adapts those
principles to Quillins.

### 19.1 Spoken-first: every Quillin action announces its outcome

The defining rtf.md rule is that every action reports its consequence aloud, in the
shared announcement grammar, so a blind user never has to re-derive what happened.
Quillins adopt this as a hard contract, not an option:

- Installing, enabling, disabling, updating, or removing a Quillin announces the
  result and the new state ("Enabled Title Case. 4 Quillins active.").
- Granting or revoking a capability speaks exactly what changed ("Granted network
  access to Weather Insert. This Quillin can now make outbound requests, with a
  prompt each time.").
- A Quillin command that completes speaks its outcome through the same engine
  built-ins use, so `api.announce` is not a courtesy but the expected closing act
  of every handler; the authoring guide (§15) should treat a silent handler as a
  smell.
- Failures surface as announced, reviewable text (a read-only multiline control),
  never a transient-only beep, mirroring §7 and the rtf.md "speak the consequence"
  rule.

This is the single most important enhancement: a Quillin that cannot be heard is a
second-class citizen, and QUILL's promise is that there are none.

### 19.2 The Quillins Manager as an accessible tree

rtf.md argues the outline *is* the document and that QUILL already ships the right
primitive: the accessible tree-navigator (`_NavigatorNode` and
`_show_tree_navigator` in `quill/ui/main_frame.py`, used today for the heading
outline, EPUB chapters, and the misspelling list). The Quillins Manager should
reuse that exact pattern rather than a flat list:

- A tree groups Quillins by provenance (First-party, Installed) and, within each,
  by capability footprint (No capabilities, Editor only, Filesystem, Network,
  Clipboard), so a user can hear "everything that can reach the network" as one
  branch.
- Each node speaks its essentials on focus: name, publisher, version, enabled
  state, and granted capabilities, the way rtf.md has each tree node announce its
  title, level, and state.
- Arrow keys walk the structure; expanding a capability branch is how a user
  audits risk by ear, the accessible answer to a sighted user scanning a column of
  permission icons.
- A live, read-only detail pane sits beside the tree (exactly as the YAML
  structure editor and the rtf.md Compose preview place detail beside structure),
  showing the selected Quillin's manifest, capabilities, and provenance.

### 19.3 A rich, spoken context menu on the manager tree

Following the rtf.md Compose-mode context menu, right-clicking a Quillin in the
manager opens a structure menu where every item is keyboard reachable and every
action announces its outcome and confirms only what is destructive:

| Menu item | Action | Spoken outcome |
| --- | --- | --- |
| Enable / Disable | Toggles the Quillin | "Disabled Title Case. 3 Quillins active." |
| Review Capabilities | Speaks and shows the granted capability set | reads the capability list |
| Revoke Capability... | Removes a granted capability (confirm) | "Revoked network access from Weather Insert." |
| Inspect Manifest | Opens the manifest in a read-only review pane | "Showing manifest for Title Case." |
| Where Did This Come From? | Speaks provenance and publisher | "Title Case, first-party, shipped with QUILL." |
| View Commands and Bindings | Lists the Quillin's commands and hotkeys | reads each command and its binding |
| Update / Reinstall | Re-reads the Quillin from disk | "Reloaded Title Case from disk." |
| Remove... | Uninstalls the Quillin (confirm) | "Removed Title Case. 3 Quillins active." |

Reordering-style, instantly reversible actions (enable, disable) never prompt;
capability revocation and removal confirm through a native accessible dialog, per
the rtf.md "friction only where loss is possible" rule.

### 19.4 Provenance and capabilities as spoken objects

rtf.md reframes keywords from visual chips into spoken objects a user can hear,
filter, and jump through. Quillins apply the same move to provenance and
capabilities, which are otherwise the classic "colored badge you must see":

- "Read capabilities here" speaks the granted capabilities of the focused Quillin
  on demand, the analogue of rtf.md's "Read keywords here."
- "Go to capability" lists every Quillin that holds a given capability ("network: 2
  Quillins; filesystem: 1"), so a user can audit by capability rather than by
  Quillin, entirely by keyboard and entirely spoken.
- Provenance is announced on demand, never implied: a one-key "Where did this come
  from?" affordance (already promised in §17.2) speaks publisher and trust tier.

The principle is identical to rtf.md's keywords: take state the industry shows as a
glanceable badge and make it something a blind power user can add up, audit, and
act on by ear.

### 19.5 The adapter discipline: Quillins behind a stable, swappable seam

rtf.md's grammar design refuses to hand-roll an engine and instead wraps a real
one (Harper) behind a pure `quill/core` adapter that emits stable typed records,
so the engine can be swapped without touching the app. Quillins already embody the
same discipline, and this document should name it as the shared pattern:

- The `QuillExtensionApi` is the adapter seam (§5): every method maps to an
  existing core operation, so a Quillin never sees a `wx` widget and the host can
  evolve behind a versioned facade exactly as the grammar adapter hides Harper.
- The contribution grammar (§4) is the single registration vocabulary for both
  first-party modules and Quillins (§16), the same "one protocol, many
  implementations" idea rtf.md applies to its editor-surface protocol.
- New host capabilities (a future grammar engine, a Compose-mode surface, a
  keyword store) should be exposed to Quillins as additional capability-gated
  adapter methods, never as raw access, keeping the seam stable as QUILL grows.

### 19.6 Honest limits, stated plainly

rtf.md states its constraints rather than hiding them, and §16.3 already does this
well. Carrying the principle forward, three limits bind Quillins specifically:

- A Quillin can never become the editor surface, the announcement engine, or the
  accessibility path; those are the framework's central guarantee (§16.3), exactly
  as rtf.md refuses to pluginize the writing path.
- A Quillin can only *describe* UI, never draw it (§18); the finite field
  vocabulary is the safety property, the same way rtf.md's accessible preview is
  structured text rather than an opaque rendering.
- Anything that cannot be made fully spoken and keyboard-driven is out of scope for
  a Quillin and must be a reviewed first-party module instead.

---

## 20. Skill Quill Pack (.sqp) — multi-step AI workflows in plain text

A `.sqp` (Skill Quill Pack) file is the natural extension of a `.pqp` prompt pack: instead of one static instruction, a skill is a Markdown document whose headings define sequential steps and whose special fenced blocks control data flow, branching, and output handling.

**Design principle.** A skill should be readable — and editable — by anyone who can use a text editor. There is no GUI skill builder, no node graph, no DSL reference card. You open the file in QUILL, read each step like a recipe, change any instruction, and save. That is the whole authoring loop.

### 20.1 File format (quill.skill/1)

A `.sqp` file is a Markdown document with a YAML front matter block followed by level-1 headings that define steps.

```markdown
---
schema: quill.skill/1
name: My Skill
description: Does something useful.
author: Your Name
version: 1.0.0
parameters:
  - name: tone
    label: Tone
    type: choice
    choices: [formal, casual]
    default: formal
---

# Step 1: Do the first thing

Write a {parameters.tone} paragraph about {selection}.

# Step 2: Refine

Polish this text:
{step1.output}

```output
format: text
label: Final result
accept_into: selection
```
```

### 20.2 Front matter fields

| Field | Required | Description |
| --- | --- | --- |
| `schema` | yes | Must be `quill.skill/1` |
| `name` | yes | Display name in the Skill Library |
| `description` | recommended | One-line description |
| `author` | recommended | Author name |
| `version` | no | Semver string (default `1.0.0`) |
| `parameters` | no | List of parameter declarations |

### 20.3 Parameters

Each parameter in the `parameters` list has these fields:

| Field | Description |
| --- | --- |
| `name` | Internal name, used as `{parameters.name}` |
| `label` | Shown to user in the parameter dialog |
| `type` | `text`, `multiline`, `choice`, `bool`, `number` |
| `choices` | Required when `type` is `choice`: `[a, b, c]` |
| `default` | Default value |

### 20.4 Steps

Each `# Heading` at depth 1 defines one step. The body between headings is the prompt template. Steps are numbered 1-based in document order.

**Variable interpolation.** Step prompts and input blocks may reference:

| Variable | Value |
| --- | --- |
| `{selection}` | Current editor selection (full document if empty) |
| `{document}` | Full document text |
| `{title}` | Document title |
| `{clipboard}` | System clipboard text at skill-start time |
| `{step1.output}` | Output from step 1; `{step2.output}` from step 2, etc. |
| `{parameters.name}` | Value of declared parameter `name` |

### 20.5 Special fenced blocks

**`input`** — appends literal data to the prompt (keeps the instruction prose clean):
```
```input
{selection}
```
```

**`condition`** — evaluates before the step's prompt; jumps to a named step:
```
```condition
if: "{step1.output}" contains "question"
then: step2
else: step3
```
```

Supported operators: `contains`, `equals`, `starts_with`, `ends_with`, `length_gt`, `length_lt`, `is_empty`.

**`output`** — on the last step, controls how the result is presented:
```
```output
format: text
label: Rewritten paragraph
accept_into: selection
```
```

`format` values: `text`, `list`, `json`. `accept_into` values: `selection` (replaces editor selection on Accept), `clipboard`, `none`.

**`use-prompt`** — delegates to a named prompt in the Prompt Library instead of sending a new instruction:
```
```use-prompt
name: Improve Clarity
input: {step1.output}
```
```

### 20.6 Execution model

1. QUILL collects parameter values (shows dialog if any parameter lacks a default).
2. Steps execute in order. Each step's prompt template is interpolated with the current context, the prompt is sent to the AI (synchronously; no streaming), and the response is stored as `{stepN.output}`.
3. If a `condition` block is present, its result determines which step runs next.
4. After the final step, the `output` block controls the result presentation.
5. Every step announces "Running step N of M..." and the result announces "Skill complete."
6. No document text changes without explicit Accept in the result dialog.
7. Nested `use-skill` calls are bounded to depth 2 to keep execution predictable.

### 20.7 Validation tool

```powershell
python -m quill.tools.sqp_validator path/to/skill.sqp
python -m quill.tools.sqp_validator path/to/directory/ --strict
```

Exit 0 on clean; exit 1 on errors. `--strict` also warns about missing `description` and `author`.

### 20.8 Quillin distribution

A Quillin may ship `.sqp` files alongside its manifest. QUILL discovers them the same way it discovers `prompts.json` — at Skill Library load time. The bundled `ai-writing-skills` Quillin ships four sample skills: Accessible Rewrite, Research and Draft, Meeting Notes to Action Items, Argument Strengthener.

### 20.9 Schema and implementation

| File | Role |
| --- | --- |
| `quill/core/skill_pack.py` | `SkillPack` dataclass, `.sqp` parser, `validate_skill()`, `run_skill()` |
| `quill/tools/sqp_validator.py` | CLI validator: `python -m quill.tools.sqp_validator` |
| `quill/quillins_bundled/ai-writing-skills/` | Four bundled `.sqp` skills |
| `tests/unit/core/test_skill_pack.py` | 23 tests covering parsing, validation, runner, branching, bundled files |

---

## Appendix A — Language options considered

| Option | Pros | Cons | Verdict |
| --- | --- | --- | --- |
| **Python (embedded, app's own language)** | No new runtime; whole object model already Python; best debugging/docs/stdlib; faithful analogue of scripting a .NET editor in a .NET language; easiest to maintain | In-process execution would share fate with the UI on a crash; running out-of-process at least contains faults, though Python itself still has no real language-level sandbox — see §6 | **Chosen (Layer 2)** |
| **JavaScript (QuickJS / V8 via `py_mini_racer`)** | Familiar to most; strong sandbox (isolates / no ambient I/O); QuickJS tiny | Permanent Python⇄JS marshalling; cross-boundary stack traces; native build/packaging dependency; async/wx impedance | Optional future snippet evaluator only |
| **Lua (`lupa`/LuaJIT)** | Classic embeddable scripting; tiny; easy to sandbox | Small user base among QUILL power users; another language to learn; weak text-tooling stdlib | Rejected |
| **WASM (Extism / Wasmtime)** | Strongest sandbox; language-agnostic | Heavy; complex host bindings; hard to author/debug; overkill | Rejected for 2.0 |
| **Declarative-only (manifest)** | Safest; covers ~70% of requests; trivially accessible to author | Not Turing-complete; power users hit a ceiling | **Chosen (Layer 1), paired with Python** |

## Appendix B — Why out-of-process

QUILL's concurrency model already runs OCR in a separate worker process and
marshals UI updates through `wx.CallAfter`. Reusing that pattern for the
extension host gives real fault isolation (a runaway extension can't corrupt the
buffer or freeze the editor). It does **not** give security isolation: Python
has no reliable language-level sandbox, and `host_worker.py` today is a plain
interpreter process with no import restriction. A handler that wanted to
bypass `api` and call `os`/`subprocess`/`socket` directly could. The real
boundary right now is review (linting, the Author Covenant, and — until a
trust/signing model ships — keeping third-party loading `locked_off`, SEC-8),
not a technical sandbox.
The UI side remains the sole owner of the editor buffer; the extension side only
ever sends intents over the RPC bridge.


---

<!-- Source: docs/quillins.md -->

# Submitting a Quillin

This is the end-to-end guide for authoring a Quillin and submitting it to QUILL.
It is the human companion to three machine-enforced pieces:

- the normative manifest **JSON Schema**,
  [`quill/core/schemas/extension.json`](../quill/core/schemas/extension.json),
- the **submission linter**, `python -m quill.tools.quillin_lint`, and
- the automated **verification workflow**,
  [`.github/workflows/quillin-verify.yml`](../.github/workflows/quillin-verify.yml).

Before you start, read the [Quillin Author Covenant](quillin-code-of-conduct.md)
— every submission attests to it — and the authoring reference in
[`scripting.md`](scripting.md) (§13 schema, §14 authoring reference, §15 the
deterministic AI-authoring contract).

## 1. What a Quillin is

A Quillin is a small, capability-declared extension described by a
`manifest.json` (`schema: "quill.extension/1"`). It comes in two layers:

- **Layer 1 — snippet only.** Declarative text insertion with placeholders
  (`${selection}`, `${clipboard}`, `${date}`, `${time}`, `${filename}`,
  `${title}`, `${line_number}`, `${word_at_cursor}`, `${uuid}`, `${cursor}`).
  **No code, no capabilities** (except `clipboard.read` when `${clipboard}` is
  used). This covers most needs and is the safest, fastest path to acceptance.
- **Layer 2 — Python handler.** A `main` entry module registers handler
  functions via `api.register_command`. Requires the `ui.command` capability and
  runs **out-of-process** behind QUILL's capability + consent gate.

## 2. Directory layout

A Quillin is one directory:

```
my-quillin/
  manifest.json     # required — the contract
  extension.py      # required only for Layer 2 (matches manifest "main")
  README.md         # required for submission
  LICENSE           # required (or declare "license" in the manifest)
```

The bundled
[`quill/quillins_bundled/markdown-helpers/`](../quill/quillins_bundled/markdown-helpers/)
is the canonical template — copy it.

## 3. Author the manifest

Minimum fields: `schema`, `id`, `name`, `version`. Strongly recommended for any
submission: `author`, `description`, `license`, `min_quill_version`.

- **`id`** — reverse-DNS you control, e.g. `com.example.mytool`. `com.quill.*`
  is reserved for first-party bundled Quillins.
- **`version`** — `MAJOR.MINOR.PATCH`, bumped on every change.
- **`capabilities`** — declare the **minimum**. Snippet-only Quillins declare
  none. `fs.read`, `fs.write`, and `net` are **consent-gated**: every use prompts
  the user at runtime, so design for a graceful, announced refusal.
- **`contributes`** — `commands` (each `run` has *exactly one* of `snippet` or
  `handler`), plus optional `menus` (parents: File, Edit, Format, Tools,
  Navigate, View, Help), `context_menu` (with an optional `when` guard), and
  `hotkeys` (QUILL binding grammar; conflicts are rejected, never silently
  overridden). Command ids must be namespaced under `ext.`.
- A command using `run.handler` **requires** a top-level `main` module and the
  `ui.command` capability.

## 4. Self-lint before you submit

Run the linter — the same tool CI runs — and fix everything:

```powershell
python -m quill.tools.quillin_lint path\to\my-quillin --strict
```

It applies three independent lenses:

1. **Schema check** — your manifest is validated against the published JSON
   Schema artifact (made executable inside the linter), so your errors match
   what editors and external tools see.
2. **Manifest validation** — the same contract validator the loader enforces,
   catching rules the schema does not encode (e.g. handler ⇒ `main` +
   `ui.command`).
3. **Structure & capability hygiene** — confirms your `main` module exists, a
   README and license are present, and surfaces every consent-gated capability
   for deliberate review.

`--strict` (used by CI) treats warnings as failures. A clean `--strict` run is
the bar for submission.

## 5. Write tests

Mirror the bundled Quillin's test
([`tests/unit/core/test_quillins_bundled_markdown.py`](../tests/unit/core/test_quillins_bundled_markdown.py)):
validate the manifest, build a conflict-free contribution registry, expand any
snippet, and drive any handler. Handler Quillins should also be exercised through
the real out-of-process host (see
[`tests/integration/test_quillins_host_integration.py`](../tests/integration/test_quillins_host_integration.py)).

## 6. Accept the Author Covenant

Read [`quillin-code-of-conduct.md`](quillin-code-of-conduct.md) and confirm your
Quillin keeps every promise: accessibility (announce outcomes, keyboard-complete),
capability minimization and honesty, no silent network or telemetry, privacy,
security (no obfuscation, no attempts to exceed declared capabilities, no
malware), licensing, namespace etiquette, and maintenance.

## 7. Open the submission PR

1. Add your Quillin directory to the submission area and stage **only** your own
   files (never `git add -A`).
2. Open a pull request using the **Quillin submission** PR template and complete
   its checklist.
3. The `Quillin Verify` workflow runs `quillin_lint --strict` over the Quillins
   your PR changes. A red check blocks merge; fix and push again.

## 8. Review and acceptance

A maintainer reviews against this guide and the Covenant. Review focuses on what
machines cannot fully judge:

- **Accessibility in practice** — does every action announce a clear outcome; is
  it fully keyboard-operable?
- **Capability justification** — is each declared capability genuinely needed and
  used transparently? Consent-gated capabilities get the most scrutiny.
- **Security and honesty** — readable source, no obfuscation, no attempts to
  exceed declared capabilities, no silent network, behaviour matches description.
- **Quality** — clear naming, sensible menu/hotkey placement, tests present.

Outcomes: **accepted** (listed and/or bundled), **changes requested**, or
**rejected** with a reason. Security or accessibility violations are
non-negotiable rejections.

## 9. Updates, versioning, and removal

- **Updates** are new PRs that bump `version` and re-pass `--strict` + review.
- **Deprecation** — mark it in your README and bump a MAJOR version for breaking
  changes.
- **Removal** — a Quillin that violates the Covenant (especially security or
  accessibility) may be delisted or unbundled without notice per the Covenant's
  enforcement section.

## Quick checklist

- [ ] `manifest.json` valid: `python -m quill.tools.quillin_lint <dir> --strict` is green
- [ ] Minimum capabilities declared; consent-gated use is justified and announced
- [ ] Every command announces its outcome and is keyboard-operable
- [ ] `README` and license present; `id` is reverse-DNS you control
- [ ] Tests added (manifest + registry + snippet/handler; host round-trip for handlers)
- [ ] Author Covenant upheld and attested in the PR


---

<!-- Source: docs/quillins.md -->

# Quillin Author Covenant

This Covenant is the **code of conduct for Quillin code** — the technical and
ethical promises every Quillin must keep to be bundled with, or listed for, QUILL.
It complements (and does not replace) the community
[`CODE_OF_CONDUCT.md`](../CODE_OF_CONDUCT.md), which governs how people behave;
this document governs how *Quillins* behave.

QUILL is **Quality, Usable, Inclusive, Lightweight, Literate** — a
screen-reader-first editor. A Quillin extends that editor, so it inherits those
values. By submitting a Quillin (see
[`quillin-submission.md`](quillin-submission.md)) you attest that it upholds
every promise below. Verification is partly automated
(`python -m quill.tools.quillin_lint`) and partly human review; both must pass.

## 1. Accessibility is non-negotiable

- **Announce every outcome.** Every command reports its result as text, so a
  screen-reader user knows what happened (NVDA/JAWS/Narrator parity). A silent
  success is a bug.
- **Keyboard-complete.** Everything a Quillin offers is reachable and operable
  from the keyboard alone. No mouse-only affordance, no focus traps.
- **Plain-text first.** Respect the editor's plain-text-first writing surface;
  do not fight the stock controls QUILL relies on for accessibility.
- **No flashing, no surprise focus changes.** Do not move focus unexpectedly or
  produce content that could trigger photosensitive reactions.

## 2. Capability honesty and minimization

- **Declare the minimum.** Request only the capabilities you actually use.
  A snippet-only Quillin declares none.
- **No capability laundering.** Do not request a broad capability to do a narrow
  thing, and never attempt to act beyond what you declared. The host worker
  process does not technically prevent this today (it is plain Python, not an
  OS-level sandbox) — that makes this rule a matter of trust and review, not
  enforcement, which is exactly why violating it is grounds for immediate
  removal.
- **`fs.*` and `net` are consent-gated.** If you request filesystem or network
  access, expect every use to pass a per-action consent prompt, and design for a
  graceful, announced outcome when the user says no.

## 3. No silent network, no telemetry

- **No silent network calls.** Every outbound request is an explicit, opt-in,
  per-action event with visible progress and an announced outcome. This mirrors
  QUILL's own non-negotiable rule.
- **No telemetry, analytics, tracking, or beaconing** of any kind.
- **No document content leaves the device** without an explicit, per-action
  consent gate the user can decline.

## 4. Privacy and data handling

- **Treat document content as private.** Never log it, never transmit it without
  consent, never persist it outside what the user asked for.
- **No secrets in the manifest or code.** Do not embed credentials, tokens, or
  keys. Do not phone home for "activation".
- **Be transparent about what you store** and where, and keep it inside QUILL's
  sanctioned storage conventions.

## 5. Security and integrity

- **No obfuscation.** Ship readable source. Minified, encoded, or deliberately
  obscured handler code will be rejected.
- **No sandbox escape attempts**, no spawning unsanctioned subprocesses, no
  loading remote code at runtime, no monkey-patching QUILL internals.
- **No malware, ever** — no destructive behaviour, ransomware, cryptominers,
  credential harvesting, or anything that harms the user or their data.
- **Fail safe.** Errors surface as announced, reviewable text — never a silent
  failure and never a crash that takes the editor down.

## 6. Licensing and attribution

- **Declare a license** (manifest `license` field and/or a `LICENSE` file) and
  ship a `README`.
- **Respect copyright.** Only include content and dependencies you have the
  right to distribute, and attribute third-party material correctly.

## 7. Naming and namespace etiquette

- **Use a reverse-DNS `id`** you control (e.g. `com.example.mytool`); do not
  squat on `com.quill.*`, which is reserved for first-party bundled Quillins.
- **Namespace commands under `ext.`** (enforced) and choose clear, honest,
  Title-Case command names. No misleading or impersonating titles.

## 8. Maintenance and good citizenship

- **Version honestly** using `MAJOR.MINOR.PATCH`; bump on every change.
- **Keep it lightweight.** Do only what you describe; no scope creep, no
  bundling unrelated functionality.
- **Be responsive** to security reports and accessibility regressions.

## Enforcement

A Quillin that violates this Covenant may be **rejected, delisted, or unbundled**
without notice, and repeated or malicious violations may bar an author from
future submissions. Security and accessibility violations are treated as the most
serious. Report concerns through the process in
[`SECURITY.md`](../SECURITY.md) (for security) or by opening an issue (for
accessibility or conduct).

Keeping this Covenant is what lets QUILL ship Quillins **seamlessly at the point
of use and transparently where it matters**.


---

<!-- Source: docs/quillins.md -->

# Converting QUILL features into bundled Quillins — a flexibility proof

Status: **Proposed roadmap (2.0-scale, demonstration- and maintainability-driven)**
· Companion to `docs/quillins.md` (esp. §6 security, §16 modularization) and
`docs/quillins.md` · Sample artifact:
[`examples/quillins/markdown-helpers/`](../examples/quillins/markdown-helpers/)

> **This is the bolder sibling of `docs/quillins.md`.** That plan
> moves built-in features onto the contribution *grammar* but keeps them
> **trusted and in-process** (the rich `Host` facade). This roadmap takes the
> step that actually *proves the platform*: re-express a curated set of real
> QUILL features as **genuine Quillins** — `register(api)`, out-of-process,
> capability-gated — ship them **bundled and enabled**, and **delete their
> implementation from core**. If QUILL can host its own features through the same
> narrow door it offers strangers, the extension platform is real, not a brochure.

## 1. What this proves, and why it is worth doing

The Quillins framework is fully built and tested (`quill/core/quillins/*`), but
in QUILL 1.0 it runs **zero** real extensions: third-party execution is locked
off (SEC-8) and every shipping feature lives in core/UI Python. The framework is
therefore proven only by its own unit/integration tests and one worked example
([`examples/quillins/markdown-helpers/`](../examples/quillins/markdown-helpers/)).

Converting real features into Quillins delivers three things a test suite cannot:

1. **A flexibility proof.** Exercising the contribution grammar, capability
   catalogue, consent gate, out-of-process isolation, and packaging against
   *features users already rely on* shows the platform can carry production
   weight — the strongest possible signal to third-party authors.
2. **A smaller core.** Each converted feature's algorithm, tests, menu wiring,
   and handler leave `quill/core`/`quill/ui`. The god object
   (`quill/ui/main_frame.py`) shrinks and `quill/core` keeps only what other core
   code still needs.
3. **A living dogfood.** Bundled Quillins are run on every launch, so the
   framework's hot paths stay exercised and honest rather than dormant behind a
   locked flag.

This is a **demonstration + maintainability** effort. It adds no user-facing
capability (the features already exist), so it is sequenced **after** 1.0
user-facing work and proceeds opportunistically — every step leaves the suite
green and the accessibility contract intact, or it does not land.

## 2. Three trust tiers (read this before proposing any conversion)

The migration plan established two tiers; this roadmap needs a third. Keeping
them straight is the whole game.

```
  Tier A — CORE GUARDRAILS            Tier B — FIRST-PARTY MODULES        Tier C — BUNDLED QUILLINS
  editor surface, announcement        register(host): trusted,            register(api): trusted-AUTHOR but
  engine, lifecycle, registry         in-process, rich Host facade        run through the SAME sandboxed,
  (never pluginized — §2 of           (quillin-migration-plan.md)         out-of-process, capability-gated
  migration plan)                                                         path as third-party Quillins
       │                                     │                                     │
       └─────────── one contribution grammar / one registry / one keymap ─────────┘
```

- **Tier A — core guardrails.** Unchanged from `quillin-migration-plan.md` §2:
  the `wx.TextCtrl` editor surface, the NVDA/JAWS/Narrator announcement engine,
  app lifecycle/frame construction, and the contribution registry/keymap itself.
  These are never converted.
- **Tier B — first-party in-process modules.** The subject of
  `quillin-migration-plan.md`. Trusted code, no sandbox, rich facade, sub-ms
  latency. The right home for anything latency-sensitive or wx-bound that is
  still command-shaped.
- **Tier C — bundled Quillins (NEW, this roadmap).** Real Quillins authored by
  the QUILL project, shipped *inside* the install tree, and enabled by a
  **separate trusted mechanism** — they are **not** discovered from
  `%APPDATA%\Quill\extensions\` and are therefore **unaffected by the SEC-8
  third-party lock**. They run through the identical out-of-process, capability,
  and consent machinery as third-party code, which is exactly why they are a
  valid proof of it.

> **Non-negotiable boundary (restated from `scripting.md` §16.1).** Tier B exists
> precisely so trusted per-keystroke built-ins are *not* forced across an RPC
> bridge. Tier C is for features where the out-of-process round-trip is
> acceptable (on-demand, not per-keystroke) **and** the whole point is to demo the
> extension path. Converting a hot-path feature to Tier C to "be pure" would wreck
> latency for zero gain — that belongs in Tier B.

## 3. The enabling work the platform needs first (honest prerequisites)

Tier C does not exist yet. Wave 0 builds it. None of this weakens SEC-8.

| Prerequisite | What it is | Where it touches |
| --- | --- | --- |
| **Bundled-extensions root** | A read-only `extensions/` directory staged *inside* the install tree, discovered separately from the per-user `%APPDATA%` root. | New branch in `quill/core/quillins/loader.py` (`bundled_extensions_root()` alongside `extensions_root()`), path-contained like today. |
| **Trusted-enable path** | Bundled Quillins ship **enabled** without the `core.third_party_plugins` flag (which stays `locked_off`). A distinct, on-by-default `core.bundled_quillins` gate, or an explicit bundled-manifest allowlist. | `quill/core/quillins/loader.py` discovery gate; `quill/core/features.py` feature definition. |
| **Worker imports its own modules** | A bundled Quillin may ship pure-Python helpers next to `extension.py` and import them. | Already supported — `host_worker.py` loads `main` and sibling files within the path-contained extension dir. Confirm + test. |
| **Capability pre-grant for trusted authors** | Bundled Quillins still *declare* capabilities and still hit the **consent gate** for `fs.*`/`net` (the proof must be real); non-consent-gated caps (`editor.*`, `ui.*`, `clipboard.*`) may be pre-granted so a shipped feature does not nag on first use. | `loader.grant_capabilities` seeded for bundled ids; consent path unchanged. |
| **Packaging** | The installer stages the bundled `extensions/` tree and registers it as a component. | `scripts/build_windows_distribution.py`, `installer/quill.iss`. |
| **Latency budget** | Measure cold-load + warm-invoke round-trip for an on-demand command; set a published budget (e.g. warm invoke < 50 ms) below which Tier C is acceptable. | New perf test under `tests/perf`. |

**Wave 0 exit criterion:** the existing `examples/quillins/markdown-helpers`
sample, promoted to a bundled Quillin, ships enabled in a build, appears in
**Tools ▸ Quillins Manager**, and runs end-to-end — with the third-party flag
still `locked_off`.

## 4. Candidate selection — what can become a Quillin

A feature is a Tier C candidate iff **all** hold:

- **Command-shaped:** stable id, title, handler, optional menu/hotkey/context.
- **Capability-expressible:** its effect is reachable through the catalogue
  (`editor.read/write`, `ui.announce/command`, `clipboard.read/write`, and —
  consent-gated — `fs.read/write`, `net`). If it needs anything outside that
  catalogue, it cannot be a Quillin by construction.
- **No `wx`, no platform API, no tight editor/selection-state coupling.** Pure
  logic over text/clipboard/files.
- **Latency-tolerant:** invoked on demand, never on every keystroke.
- **Deterministic & characterization-testable** before the move.

### Candidate catalogue (grounded in today's code)

| Feature(s) | Current home | Verdict | Target |
| --- | --- | --- | --- |
| Line transforms: number lines, hard-wrap | `quill/ui/features/line_transforms.py` (already Tier B) | ✅ Strong — pure text, already extracted | Tier C "Text Tools" |
| `set_lines_first_not_second`, `set_lines_common` | `quill/ui/main_frame_power_tools.py` | ✅ Strong — pure set algebra over two buffers | Tier C "Text Tools" |
| `count_regex_matches`, `extract_regex_matches` | `quill/ui/main_frame_power_tools.py` | ✅ Good — pure regex over text (uses `regex`, a runtime dep the worker can ship) | Tier C "Text Tools" |
| HTML-clipboard → Markdown paste | `quill/core/html_to_markdown.py` + `paste_html_as_markdown` | ✅ Good — pure transform + `clipboard.read`; helper vendored into the Quillin | Tier C "Markdown Tools" |
| Insert date/time, calculate-and-insert-date | `insert_date_time`, `calculate_and_insert_date` | ✅ Good — Layer 1 snippet (`${date}`/`${time}`) or a small handler, no caps / `editor.write` | Tier C "Insert Tools" |
| Front-matter / boilerplate snippets | sample Quillin | ✅ Already a Layer 1 Quillin (the worked example) | Tier C (ship it) |
| Read-only guard, `speak_*`, key describer, indent announce | `quill/ui/main_frame_power_tools.py` | ❌ No — announcement-engine / wx / live-event coupled (Tier A/B) | Stay core |
| `run_current_file`, `run_target_at_cursor`, file rename/delete | `quill/ui/main_frame_power_tools.py` | ❌ No — process execution / shell / filesystem beyond the consent model's intent | Stay core |
| Dictation, OCR, AI assistant, watch folders, sticky-notes UI, spell-check | various `quill/ui`, `quill/platform` | ❌ No — wx UI, platform bindings, background services, or models | Stay core |

The pattern is clear: **the power-tool text transforms are the ideal proving
ground** — many are already pure functions or one mixin method away from it, and
several already passed through Tier B (`line_transforms.py`), so the path from
inline → Tier B → Tier C is a graded, low-risk ramp.

## 5. The conversion procedure (per feature, strangler-fig)

Mirrors `quillin-migration-plan.md` §5/§8 but the target is the **Quillin path**,
and the algorithm **moves out of core** rather than staying behind a facade.

1. **Pin behavior first.** Add/extend a characterization test asserting the
   feature's current observable behavior (handler output for representative
   input, announcement text, menu/hotkey placement). For an already-extracted
   helper, the existing core test is the baseline.
2. **Author the bundled Quillin.** Create
   `quill/quillins_bundled/<name>/` (or the chosen install-tree home) with a
   `manifest.json` (`quill.extension/1`, `ext.*` ids, declared capabilities) and
   `extension.py`. **Vendor the pure algorithm into the Quillin** — move the
   wx-free helper (e.g. the relevant function from `quill/core/html_to_markdown.py`)
   into a sibling module the Quillin imports, and move its unit tests alongside.
   "Thin core, fat Quillin": core keeps a function only if other *core* code still
   calls it.
3. **Register it as bundled.** Add the Quillin to the bundled-manifest allowlist
   so it ships enabled (Wave 0 machinery).
4. **Delete the old wiring.** Remove the mixin handler body, the inline command
   registration, and the menu/hotkey wiring from core/UI in the *same* PR — no
   dead duplicate.
5. **Re-pin through the Quillin.** Convert the characterization test to load the
   bundled Quillin through `ExtensionHost`, invoke the command, and assert the
   **identical** output/announcement. (This is exactly the shape of
   `tests/unit/core/test_quillins_example.py` + the live host smoke test.)
6. **Verify the bar.** `ruff format`/`check`; strict `mypy` on any touched
   `quill/core`; dialog/inventory/egress gates green; public-surface fixture
   regenerated if a `MainFrame` method disappeared.

Rollback at any step is a single-directory + single-PR revert.

## 6. Wave-by-wave sequencing

| Wave | Scope | Exit criterion |
| --- | --- | --- |
| **0 — Platform** | Build Tier C: bundled-extensions root, trusted-enable gate, packaging, latency budget (§3). | The promoted `markdown-helpers` Quillin ships **enabled**, shows in the Manager, runs end-to-end; third-party flag still `locked_off`; perf budget published and met. |
| **1 — Text Tools** | Convert 3–5 pure text transforms (`set_lines_*`, number/wrap lines, trim/case/sort if present) into ONE bundled "Text Tools" Quillin; delete their core helpers. | Each command loads + invokes through the host with byte-identical output; core LOC for those features removed; suite green. |
| **2 — Insert Tools** | Convert date/time + snippet/boilerplate inserters into a bundled "Insert Tools" Quillin (mostly Layer 1, zero capabilities). | Snippets expand identically; no consent prompts (no gated caps); menu homes match `menus.md`. |
| **3 — Gated proof** | Convert one **consent-gated** feature (e.g. an online lookup over `net`, or a file-backed action over `fs.*`) to a bundled Quillin. | The real shipped Quillin triggers the **consent gate** before its first network/file action and degrades gracefully on denial — proving the gated path in production. |
| **4 — Markdown Tools** | Convert HTML→Markdown paste, vendoring `html_to_markdown` into the Quillin; retire the core helper if no other core caller remains. | `clipboard.read` capability exercised; conversion fidelity tests move alongside the Quillin. |
| **N — Re-evaluate** | Measure core LOC removed and Manager dogfood coverage; decide the stop point. | A documented tally of features now served by bundled Quillins, with the guardrail set (§2) explicitly *not* converted. |

Each wave is multiple small PRs. Stop converting the moment a feature would have
to cross a guardrail (§2) or a latency budget (§3) — that feature belongs in Tier
A/B, and saying so is part of the honest result.

## 7. Done criteria & honest limits

**Done looks like:** a Tier C mechanism shipping a handful of QUILL's own
text/insert/markdown features as **bundled, enabled, sandboxed Quillins**; their
algorithms and tests living *in the Quillins*, not in `quill/core`/`quill/ui`; the
**Tools ▸ Quillins Manager** listing real, running, project-authored Quillins on a
default build; and a published latency budget the out-of-process path meets.

**Honest limits — what this roadmap deliberately does NOT claim:**

- **Not everything becomes a Quillin.** The editor surface, announcement engine,
  lifecycle, dictation/OCR/AI/watch/spell-check, and every wx/platform-bound or
  per-keystroke feature stay in Tier A/B *by design* (§2, §4). A platform proven
  by converting *suitable* features is the goal; converting *all* features is an
  anti-goal that would regress accessibility and latency.
- **SEC-8 is untouched.** Third-party discovery/execution remains `locked_off`.
  Tier C is trusted-author, install-tree, separately gated code — the proof works
  precisely *because* it reuses the sandbox without unlocking strangers.
- **No new user-facing capability.** Justification is flexibility-demonstration
  and maintainability; sequence after 1.0 user-facing work; every wave stays
  green and accessible or it does not land.
- **Latency is a real constraint, not a footnote.** If Wave 0's measurement shows
  the out-of-process round-trip is too slow for a candidate's expected use, that
  candidate stays Tier B. The budget decides, not the aspiration.


---

<!-- Source: docs/quillins.md -->

# Migrating QUILL's first-party code onto the Quillins contribution grammar

Status: **In progress — Wave 0 + Pilot 1 shipped; Host facade + Wave 2 line
transforms landed** · Companion to `docs/quillins.md` (esp. §16) and
`menus.md` (§3.7 + Phase 5) · Scope: **internal refactor, 2.0-scale,
maintainability-driven**

> Read `docs/quillins.md` §16 for the *why* (one vocabulary, two tiers). This
> document is the *how*: a concrete, low-risk, reversible procedure for moving
> built-in features out of the `quill/ui/main_frame.py` god object and onto the
> same **contribution grammar** (commands, menus, hotkeys, context-menu entries)
> that Quillins already use — turning `quill/core` into a genuine framework.

## 1. The one insight this plan rests on

The Quillins framework already defines, validates, and wires a contribution
vocabulary: a **command** (`id`, `title`, a handler), its placement in **menus**
and the **context menu**, and its **hotkey** binding, all merged with conflict
detection (`quill/core/quillins/registry.py`). QUILL's built-ins are wired with
*the same concepts*, but by hand, inline, inside one 20k-line class.

So the migration is not "rewrite features". It is: **express each existing
feature as a self-registering module that contributes commands through one host
facade**, and delete the corresponding hand-wiring from `main_frame.py`.

```
            ┌─────────────── one contribution grammar ───────────────┐
            │                                                         │
  first-party feature module                          third-party Quillin
  register(host)  ── rich, in-process host ──►   register(api) ── narrow, gated API
  (trusted, no sandbox)                           (untrusted, out-of-process, §6)
            │                                                         │
            └────────► same commands / menus / hotkeys / palette ◄────┘
```

The crucial rule (restated from §16.1, non-negotiable): **first-party modules run
in-process against a rich host facade. They are NEVER routed through the
sandboxed, capability-gated, out-of-process Quillin path.** That path exists for
*untrusted* code; forcing trusted per-keystroke built-ins across an RPC bridge
would wreck latency and capability for zero security gain.

## 2. Guardrails — what must NOT be migrated

These are load-bearing for QUILL's identity. Decomposing them is how
accessibility regresses (see §16.3):

- **The editor surface.** The plain-text `wx.TextCtrl` writing path stays a
  first-class, hand-owned widget. It is not a plugin and gets no `register(host)`.
- **The accessibility / announcement engine.** NVDA/JAWS/Narrator parity is the
  framework's central guarantee. It is *called by* migrated modules; it is not
  itself pluginized.
- **App lifecycle & frame construction.** Startup ordering, tab management, the
  single-instance guard, crash recovery, and the menu *bar* skeleton remain core.
- **Anything with deep shared-mutable-state coupling** that cannot be covered by
  a characterization test first (see §5). If you can't pin its behavior, you
  can't safely move it yet.

When in doubt: a feature is a migration candidate iff it is **command-shaped** —
it has a stable id, a title, a handler, and (optionally) a menu/hotkey/context
placement — and its handler can reach everything it needs through the host
facade (§4).

## 3. Target shape of a migrated module

A first-party feature module is a small, self-contained file exposing one
top-level `register(host)` that contributes its commands. It mirrors the Quillin
`register(api)` shape so the mental model is identical, but `host` is the **rich
trusted facade**, not the narrow capability-gated `QuillExtensionApi`.

```python
# quill/ui/features/line_ops.py  (illustrative target)
"""Line operations, migrated off main_frame.py onto the contribution grammar."""

from quill.core.contributions import Host  # the first-party host facade (§4)


def register(host: Host) -> None:
    host.add_command(
        id="lines.number",
        title="Number Lines",
        handler=_number_lines,
        menu=("Format",),          # optional placement
        context=("editor.hasText",),
        # no default hotkey: user binds via the Keymap Editor
    )


def _number_lines(ctx: Host) -> None:
    text = ctx.get_text()
    numbered = "\n".join(f"{i + 1}\t{line}" for i, line in enumerate(text.splitlines()))
    with ctx.undo_group("Number Lines"):
        ctx.set_text(numbered)
    ctx.announce("Numbered lines")
```

The module imports **no `wx`** directly for its *logic*; UI effects go through the
host facade, exactly as the Power Tools handlers already centralize their edits. (A
module may still live under `quill/ui/` and use `wx` for genuinely bespoke UI, but
that UI must pass A11Y-4 review — it is first-party, not a sandboxed extension.)

## 4. The first-party host facade

This is the single piece of *new* core surface the migration introduces, and both
halves have now **landed**. The registration half (Wave 0):
`quill/core/contributions.py` (wx-free) provides a `FirstPartyRegistrar` that
emits an `ExtensionManifest` merged through the shared `build_registry`. The
execution half (Wave 2): the same module defines the wx-free `Host` protocol —
`get_text`, `get_selection`, `is_read_only`, `set_status`, `announce`, `prompt`,
`transform_block` — implemented live by `MainFrameHost`
(`quill/ui/contribution_host.py`), a thin adapter that delegates to existing
`MainFrame` helpers so migrated handlers behave byte-for-byte like the inline
code they replace. The richer breadth below (more editor primitives, services) is
the trusted superset of `QuillExtensionApi`, filled in per wave as features move:

| Group | Methods (illustrative) | Notes |
| --- | --- | --- |
| Registration | `add_command`, `add_menu`, `add_context`, `add_hotkey` | Same grammar as `Contributions`; conflicts routed through `build_registry` |
| Editor read | `get_text`, `get_selection`, `get_cursor`, `get_lines` | |
| Editor write | `set_text`, `insert_text`, `replace_selection`, `undo_group(label)` | All writes go through core command + history (undoable) |
| Announce | `announce`, `set_status` | The one announcement engine; never bypassed |
| Services | `settings`, `document`, `dialogs.show_web_form`, `workers`, `platform` | Rich, synchronous, in-process — the trusted breadth |

Two design rules keep this honest:

1. **The registration quartet is shared with Quillins.** `add_command` /
   `add_menu` / `add_hotkey` feed the *same* `ContributionRegistry`
   (`quill/core/quillins/registry.py`) so first-party and third-party
   contributions collide-detect against each other and the host keymap uniformly.
   First-party ids are *not* forced under `ext.` — they keep their existing
   namespaces (`lines.*`, `power.*`, …); only third-party ids carry `ext.`.
2. **The breadth gap is the only difference between tiers.** `host` exposes
   settings/workers/platform/dialogs; `api` does not. That asymmetry *is* the
   trust boundary — there is no second registration mechanism, no second menu
   builder, no second keymap.

## 5. Strategy: strangler-fig, behind characterization tests

Never a big-bang "everything is a plugin" rewrite (§16.3). Each feature is moved
in a self-contained, individually revertible step:

1. **Pin behavior first.** Write/extend a characterization test that asserts the
   feature's *current* observable behavior (command id registered, menu present,
   handler output for representative input, announcement text). The existing
   `test_power_tools_command_wiring.py` is the template: it reads source text and asserts
   the wiring contract without constructing the full frame.
2. **Introduce the facade seam.** Land `quill/core/contributions.py` + its
   `MainFrame` adapter with **zero behavior change** — `main_frame.py` keeps
   working; the facade just wraps what it already does.
3. **Move one feature.** Extract its handler(s) into a `register(host)` module;
   replace the inline registration/menu/hotkey wiring in `main_frame.py` with a
   single `register(module, host)` call.
4. **Delete the old wiring.** The inline command registration, menu append, and
   handler body leave `main_frame.py`. The line count drops; the test stays green.
5. **Repeat.** One feature (or one cohesive mixin) per PR.

Rollback at any step is a single-file revert because each module is independent.

## 6. Pilot selection

Pick first movers that are **already command-shaped and already extracted into a
mixin**, so the migration is mechanical and the risk is near zero. The codebase
hands us an ideal pilot:

- **Pilot 1 — Power Tools (`power.*`).** `quill/ui/main_frame_power_tools_menu.py`
  already centralizes the commands as a `(id, label, handler)` table
  (`_power_tools_command_table`) and the handlers already live on one mixin
  (`PowerToolsActionsMixin`). That table *is* a contribution list in all but name —
  converting it to `host.add_command(...)` calls is a near-syntactic transform,
  and `test_power_tools_command_wiring.py` already pins the contract.

  **This pilot and the menu-consolidation plan are the same work.** `menus.md`
  §3.7 groups these under `Power Tools` and **recirculates** most of its
  commands into their conventional homes (Insert/Edit/Format/Search/Navigate/File
  and the Compare/Read-Aloud Tools submenus). Done by hand against today's inline
  `wx.Menu().Append(...)` wiring that is a fiddly, error-prone move across hundreds
  of lines. Done *through the contribution grammar* it is a **pure data edit**:
  each command already carries a `menu=(...)` placement tuple, so recirculating
  `power.number_lines` from the Power Tools submenu to `Format` is changing one tuple —
  the registry re-files it, the palette and Keymap Editor are untouched, and the
  collision detector still guards it. Migrate Power Tools first (Wave 1), then the
  menus.md §3.7 recirculation becomes the motivating, low-risk demonstration that
  "menus as data" works. The two plans should land together.
- **Pilot 2 — line operations & "speak …" commands.** Self-contained, pure-ish
  text transforms with clear announcements and no dialog dependencies.
- **Pilot 3 — formatting commands** that contribute under the `Format` menu.

Defer: anything touching tab lifecycle, the watch service, AI/assistant flows, or
shared mutable selection state until the facade has proven itself on Pilots 1–3.

## 7. Wave-by-wave sequencing

Status legend: ✅ shipped · ⏳ future.

| Wave | Scope | Exit criterion | Status |
| --- | --- | --- | --- |
| 0 | Land `quill/core/contributions.py` (wx-free facade: `FirstPartyRegistrar` + `FirstPartyCommand` + `build_first_party_registry`) feeding the **same** `build_registry` as Quillins | Facade unit-tested (`tests/unit/core/test_contributions.py`); `main_frame.py` unchanged in behavior; public-surface fixture stable | ✅ Shipped |
| 1 | Pilot 1 (Power Tools `power.*`) — **lands the menus.md §3.7 rename + recirculation as data** | Power Tools table + menu recirculation **derived from** the declarative `POWER_TOOLS_COMMANDS` manifest (each command carries its recirculated home Insert/Edit/Format/Search/Navigate/File or the renamed `Power Tools` remainder); `test_power_tools_command_wiring.py` reads the manifest and is green; live menu byte-for-byte identical | ✅ Shipped |
| 2 | Line-ops + speak/status commands | Each command a module; characterization tests green | 🔄 In progress — `Host` facade + adapter shipped; the line-transforms group (`power.number_lines`, `power.hard_wrap_lines`) migrated to `quill/ui/features/line_transforms.py` and removed from the mixin (§9 worked example). Remaining line/speak/status commands future |
| 3 | Format-menu commands | `Format` contributions all flow through the registry | ⏳ Future |
| 4 | Navigate/View read-only commands | … | ⏳ Future |
| 5 | Tools utilities that already use `show_web_form` | Dialogs stay A11Y-4-registered; `dialogs.md` rows unchanged | ⏳ Future |
| N | Re-evaluate; stop when `main_frame.py` is a thin shell of lifecycle + surface | `quill/core` is the framework; remaining `main_frame.py` is guardrail code (§2) | ⏳ Future |

Each wave is multiple small PRs, not one large one.

> **Wave 0 / Pilot 1 — what actually shipped.** `quill/core/contributions.py` is
> the wx-free first-party facade: a `FirstPartyRegistrar` collects
> `add_command(...)` declarations and emits an `ExtensionManifest` merged through
> the *same* `build_registry` (`quill/core/quillins/registry.py`) used for
> Quillins, so first-party ids and any Quillin contribution collide-detect
> uniformly (verified by `test_first_party_and_quillin_collide_through_one_registry`).
> First-party ids keep their namespaces (`power.*`) and may attach under the whole
> bar (`FIRST_PARTY_MENU_PARENTS` is a superset of the narrow third-party
> `MENU_PARENTS`). The Power Tools pilot (`quill/ui/main_frame_power_tools_menu.py`) is the
> first consumer: its 33 commands are declared once as `POWER_TOOLS_COMMANDS`, and
> both the palette registration table and the menu recirculation (one
> `_append_power_tools_group` loop instead of eight hand-written helpers) derive from
> that data. The handler resolves by convention (`power.number_lines` →
> `self.number_lines`), so the data and behavior cannot drift. Waves 2–N repeat
> this mechanically, one command group per PR.

## 8. Per-feature migration checklist

For every feature moved:

- [ ] Characterization test pins current id(s), menu/hotkey placement, handler
      output, and announcement text **before** any move.
- [ ] New module exposes exactly one top-level `register(host)`.
- [ ] Logic reaches the editor/settings/announcer **only** through the host
      facade; no new direct `MainFrame` attribute reach-ins.
- [ ] All writes use `host.undo_group(...)` so behavior stays undoable and
      announced identically.
- [ ] Inline registration/menu/hotkey/handler code is **removed** from
      `main_frame.py` in the same PR (no dead duplicate).
- [ ] Command ids and bindings still collide-detect via the shared registry
      (no silently-overridden hotkey — §4 rule 1).
- [ ] If the feature owns a dialog: `dialog_inventory.json` regenerated, the
      A11Y-4 gate green, `dialogs.md` row unchanged (the dialog didn't move for
      the user, only in code).
- [ ] `ruff format`/`check` clean; strict `mypy` green on the new wx-free core
      facade and any `quill/core` touched; targeted `pytest` green.
- [ ] If a public `MainFrame` method disappeared, regenerate the public-surface
      fixture and review the diff.

## 9. Worked example — migrating `power.number_lines`

**Before** (conceptually, in `main_frame_power_tools_menu.py` + `PowerToolsActionsMixin`):

```python
# table row
("power.number_lines", "Number Lines", self.number_lines)
# registration loop calls self.commands.register(id, label, handler, binding)
# and the menu builder appends + binds the same id
```

**After** (`quill/ui/features/eds_line_ops.py`):

```python
def register(host):
    host.add_command(
        id="power.number_lines",
        title="Number Lines",
        handler=_number_lines,
        menu=("Format",),         # recirculated home (menus.md §3.7), not a deep
                                  # "Tools > Power Tools > Lines" chain
    )

def _number_lines(ctx):
    if ctx.is_read_only():
        ctx.set_status("Document is read-only")
        return
    ...                       # same body as today's PowerToolsActionsMixin.number_lines
    ctx.announce("Numbered lines")
```

and in `main_frame.py`, the Power Tools block collapses to:

```python
from quill.ui.features import eds_line_ops
eds_line_ops.register(self._contribution_host)
```

The user sees the command in its **new, conventional home** (Format, per
menus.md §3.7) instead of three levels deep under a single power-tools submenu — same palette entry, same key-bindability, same announcement.
The maintainer sees one fewer responsibility in the god object, a module they can
read in isolation, **and** the menu recirculation expressed as one `menu=` tuple
rather than hand-edited `wx.Menu` plumbing. The menu-consolidation win and the
god-object-shrink win arrive in the same diff.

> **✅ Shipped (Wave 2 first cut).** This example is real:
> `quill/ui/features/line_transforms.py` now owns the `power.number_lines` and
> `power.hard_wrap_lines` handlers as pure `host`-driven functions (no `wx`, no
> `MainFrame` reach-in); they were deleted from `PowerToolsActionsMixin`. The Power Tools
> registration table resolves those two ids to the feature handlers via the live
> `MainFrameHost`, while the declarative `POWER_TOOLS_COMMANDS` manifest still owns
> their `Format > Transform Lines` placement. Behaviour is verified identical by
> `tests/unit/ui/test_contribution_host.py` (fake-host logic) plus a live
> `MainFrame` smoke test; the full suite stays green. The remaining Power Tools groups
> are mechanical repeats of this same move.

## 10. Done criteria & honest limits

**Done looks like:** `quill/core` carries the document model, command registry,
keymap, event bus, feature gating, the announcement engine, **and** the shared
contribution registry + host-facade protocol; the majority of command-shaped
features live in self-registering modules; `main_frame.py` is a thin shell of
lifecycle, the editor surface, and guardrail code (§2).

**This refactor does not add user-facing capability.** Its justification is
maintainability and testability (§16.3). Feature profiles already deliver most of
the user-visible modularity, so this is sequenced **after** user-facing wins and
proceeds **opportunistically** — every wave must leave the suite green and the
accessibility contract intact, or it does not land.


---

<!-- Source: docs/quillins.md -->

# The Quillin Hub

The Quillin Hub (`hub.quillforall.org`; service code in `quillin-hub/`)
is the community store and submission service for **every** shareable
QUILL artifact type, not just Quillin extensions. Seven artifact
families are accepted for review and publication:

| Type id | Label | Authoritative validator |
| --- | --- | --- |
| `quillin` | Quillin extension | `quill.tools.quillin_lint` |
| `agent` | AI agent (`quill.agent/1`) | `quill.tools.agent_lint` |
| `verbosity-pack` | Verbosity pack (`.qvp.json`) | `quill.core.verbosity.qvp` |
| `sound-pack` | QSP earcon pack | `quill.core.sound_pack` |
| `keyboard-pack` | Keyboard Quill Pack (`.kqp`) | `quill.tools.kqp_validator` |
| `skill-pack` | Skill Quill Pack (`.sqp`) | `quill.core.skill_pack` |
| `pronunciation-dictionary` | Pronunciation dictionary | `quill/tools/artifact_validate.py::_validate_pronunciation` |

## One validation authority

`python -m quill.tools.artifact_validate <path> [--type ID] [--strict] [--json]`
detects the artifact type (by suffix, manifest sniffing, or schema
markers) and dispatches to the per-type validator listed above. The
Hub's Submission Forge, the in-app submission check, and CI all run
this same tool, so an author never sees three different verdicts.
Exit codes follow the validator convention: `0` pass, `1` issues,
`2` not found/undetectable. `--json` emits the machine-readable
report the Forge consumes.

## In-app: check before you ship

**Tools > Quillins > Submit to Quillin Hub...** runs the identical
`artifact_validate` checks locally and reports pass/fail in an
accessible hardened dialog. Picking a Quillin's `manifest.json`
validates the whole folder (the accessible alternative to a
directory picker). The Hub website opens in the browser only on the
explicit **Open the Quillin Hub** button -- QUILL itself makes no
network call anywhere in the flow.

## Publication: GitHub-native, transparent by design

The Hub does not store artifacts. Every submission is reviewed in the
Hub's Submission Forge, then published via a pull request to
`Community-Access/quill`. Review stays transparent; authors keep
attribution; readers can audit every change.

## Where to read more

- The PRD section "The Quillin Hub -- community distribution for every
  shareable artifact" (PRD section 5.83a) is the canonical product spec.
- The user guide's "The Quillin Hub: sharing what you make" section
  walks through the in-app check end to end.
- Per-type authoring tutorials live alongside the bundled Quillin that
  ships with each format; the seven types and their authoritative
  validators are listed in PRD section 5.83a, and the validator is one
  command, `python -m quill.tools.artifact_validate <path>`.


# New in 0.6.0: Insert Automation contributions, Quillin Preferences, and per-Quillin settings

QUILL 0.6.0 extends the Quillin manifest with three new contribution types and six new capabilities. These are the most significant additions to the Quillins platform since launch.

## Abbreviation contributions

A Quillin can contribute typed abbreviations to the Insert Automation registry. These expand after a delimiter (space, period, comma, etc.) exactly like user-defined abbreviations — except user abbreviations always win if there is a conflict.

### Declarative abbreviation

No entry module required. QUILL expands the `expansion` text directly, supporting the same placeholders as snippet commands:

```json
{
  "contributes": {
    "abbreviations": [
      {
        "trigger": "qbug",
        "expansion": "Title:\nBuild:\nScreen reader:\nWindows version:\nSteps to reproduce:\n\nExpected result:\n\nActual result:\n\nNotes:\n${cursor}",
        "description": "Insert a QUILL bug report template",
        "category": "Templates",
        "enabled_by_default": true
      }
    ]
  }
}
```

Required fields: `trigger`, `description`, and one of `expansion` or `handler`.

Optional fields: `category`, `enabled_by_default`, `case_sensitive`, `file_extensions`.

### Dynamic abbreviation

A handler-based abbreviation declares a Python function instead of a fixed `expansion`. The manifest format accepts these, but **only declarative (`expansion`) abbreviations expand as you type today**: the bare-word expander cannot run a handler mid-keystroke, so handler entries are skipped when the contributed library is built. Reach dynamic content through a smart trigger or a contributed command instead (Smart Insert's `qbrf`, for example, is available as `=brftest()` and as Insert > Insert BRF Test Document).

```json
{
  "contributes": {
    "abbreviations": [
      {
        "trigger": "qbrf",
        "handler": "insert_brf_test",
        "description": "Insert a BRF test document via dynamic handler",
        "category": "Braille",
        "enabled_by_default": true
      }
    ]
  }
}
```

Dynamic abbreviations require `main` + `ui.command` in capabilities, just like handler-based commands.

## Smart trigger contributions

Smart triggers are `=name()` commands typed alone on the current line and activated with Enter. A Quillin contributes them by name; QUILL dispatches to the linked command when the trigger text matches.

```json
{
  "contributes": {
    "smart_triggers": [
      {
        "trigger": "bug",
        "command": "ext.smartinsert.bug",
        "syntax": "=bug()",
        "description": "Insert a bug report template.",
        "category": "Templates",
        "enabled_by_default": true
      },
      {
        "trigger": "rand",
        "command": "ext.smartinsert.rand",
        "syntax": "=rand(paragraphs, lines)",
        "description": "Insert readable sample text.",
        "category": "Sample Text",
        "enabled_by_default": true,
        "min_args": 0,
        "max_args": 2,
        "large_insert_threshold": 50
      }
    ]
  }
}
```

Required fields: `trigger`, `command`, `syntax`, `description`.

Optional fields: `category`, `enabled_by_default`, `min_args`, `max_args`, `large_insert_threshold`, `file_extensions`.

Rules:
- Trigger names do not include `=`. They must be lowercase.
- The `command` must reference a command contributed by this Quillin or a built-in command id.
- Triggers activate only when the exact text appears alone on the current line and Enter is pressed.
- Smart triggers from third-party Quillins require third-party Quillins to be enabled (the SEC-8 flag); bundled Quillins' triggers work whenever they are loaded. Each trigger also honours the Quillin's own `enable_<trigger>` setting.

## Preferences contributions

This is the headline new contribution type. A Quillin can declare its own preferences page, organized into tabs and sections, and QUILL renders them using accessible stock controls. The Quillin never touches `wx` directly.

### Minimal preferences page

```json
{
  "contributes": {
    "preferences": [
      {
        "id": "mytool",
        "title": "My Tool",
        "description": "Configure My Tool behavior.",
        "settings": [
          {
            "key": "enable_feature",
            "label": "Enable my feature",
            "type": "boolean",
            "default": true,
            "description": "Turn my feature on or off."
          }
        ]
      }
    ]
  }
}
```

### Full preferences page with tabs

For Quillins with several related setting groups, declare tabs. Each tab contains sections, and each section contains settings:

```json
{
  "contributes": {
    "preferences": [
      {
        "id": "smartinsert",
        "title": "Smart Insert",
        "parent": "Editing",
        "placement": "page",
        "description": "Configure Smart Insert triggers and log mode.",
        "tabs": [
          {
            "id": "general",
            "title": "General",
            "description": "General behavior.",
            "order": 10,
            "sections": [
              {
                "id": "general_behavior",
                "title": "General Behavior",
                "settings": [
                  {
                    "key": "confirm_large_insertions",
                    "label": "Confirm before large insertions",
                    "type": "boolean",
                    "default": true,
                    "description": "Ask before inserting generated text above the threshold."
                  },
                  {
                    "key": "large_insert_threshold",
                    "label": "Large insertion threshold (paragraphs)",
                    "type": "integer",
                    "default": 50,
                    "minimum": 1,
                    "maximum": 1000,
                    "description": "Ask for confirmation when inserting this many paragraphs."
                  }
                ]
              }
            ]
          },
          {
            "id": "log_mode",
            "title": "Log Mode",
            "description": "Configure .LOG file behavior and timestamp format.",
            "order": 20,
            "sections": [
              {
                "id": "log_mode_behavior",
                "title": "Log Mode Behavior",
                "settings": [
                  {
                    "key": "timestamp_format",
                    "label": "Timestamp format",
                    "type": "choice",
                    "default": "long",
                    "description": "Controls how timestamps are formatted.",
                    "choices": [
                      { "value": "long", "label": "Long date and time" },
                      { "value": "short", "label": "Short date and time" },
                      { "value": "iso", "label": "ISO 8601" },
                      { "value": "custom", "label": "Custom format" }
                    ]
                  },
                  {
                    "key": "custom_timestamp_format",
                    "label": "Custom timestamp pattern",
                    "type": "string",
                    "default": "",
                    "description": "Python strftime pattern when Timestamp format is Custom.",
                    "visible_when": { "setting": "timestamp_format", "equals": "custom" }
                  }
                ]
              }
            ]
          }
        ]
      }
    ]
  }
}
```

### Supported setting types

The types below are validated by the schema. Types marked **live** are rendered by `quillin_prefs_dialog.py` in 0.6.0. Types marked **planned** pass validation but are not yet rendered; they are reserved for future releases.

| Type | Control | Status | Notes |
| --- | --- | --- | --- |
| `boolean` | Checkbox | **live** | Self-labeling; no preceding StaticText needed |
| `choice` | Combo box | **live** | Requires `choices` array with `value` and `label` |
| `string` | Single-line text field | **live** | |
| `integer` | Numeric spinner | **live** | Supports `minimum`, `maximum` |
| `radio` | Radio button group | planned | Requires `choices` array |
| `text` | Multi-line text field | planned | |
| `number` | Decimal numeric field | planned | Supports `minimum`, `maximum`, `step` |
| `path` | File or folder picker | planned | |
| `password` | Masked text field | planned | Set `sensitive: true` |
| `list` | Editable list | planned | |
| `action` | Button | planned | |
| `info` | Read-only help text | planned | |

### Conditional visibility

A setting can declare `visible_when` or `enabled_when` to show or enable itself only when another setting in the same page has a specific value:

```json
{
  "key": "custom_timestamp_format",
  "visible_when": { "setting": "timestamp_format", "equals": "custom" }
}
```

### Placement

A preferences page may declare a preferred parent area (`parent`) and placement style (`placement`: `page`, `tab`, or `section`). In the current release, every enabled Quillin with a `preferences` contribution appears as a direct top-level entry in the Preferences hub (opened via Ctrl+Comma), named by the page's `title` field. The `parent` and `placement` fields are validated and stored but do not yet affect the rendered position.

### Required setting fields

Every setting must declare `key`, `label`, `type`, `default`, and `description`. No unlabeled controls are allowed. This is enforced at lint time.

## Settings storage and the Quillin API

Each Quillin's settings are stored at `%APPDATA%\Quill\quillin_settings\<quillin-id>.json`, written atomically. The Quillin can read and write its own settings through the API:

```python
def my_handler(api):
    fmt = api.get_setting("timestamp_format")     # "long", "short", "iso", ...
    api.set_setting("timestamp_format", "iso")
    api.reset_setting("timestamp_format")         # restores manifest default
```

Settings survive restarts, are retained when a Quillin is disabled, and can be reset to manifest defaults at any time from the preferences page. Uninstalling a Quillin prompts to keep or delete its data.

## New capabilities

| Capability | What it grants |
| --- | --- |
| `settings.own.read` | Read this Quillin's declared settings |
| `settings.own.write` | Write this Quillin's declared settings |
| `settings.core.read` | Read QUILL core settings (requires user review) |
| `settings.core.write` | Change a QUILL core setting (requires explicit user confirmation per change) |
| `document.directives` | Respond to top- or bottom-of-file document markers |
| `document.events` | Register handlers for document lifecycle events (open, save, close, etc.) |

Sensitive QUILL settings (AI credentials, network settings, security flags, third-party Quillin enablement) cannot be written by any Quillin regardless of capability.

## Bundled examples

Five bundled Quillins ship in 0.6.0 as reference implementations of these new features. All five have live settings dialogs reachable from the Preferences hub (Ctrl+Comma → navigate to the Quillin by name → Enter):

- **Smart Insert** (`com.quill.smartinsert`) — abbreviations, smart triggers, and a five-tab preferences page (General, Log Mode, Smart Triggers, Abbreviations, BRF Testing). Handler-based commands for `=bug()`, `=meeting()`, `=journal()`, `=todo()`, `=logentry()`, `=brftest()`, and `=rand()`. See `quill/quillins_bundled/smart-insert/`.
- **BRF Tools** (`com.quill.brftools`) — declarative preferences only, no handler code. Four-tab settings page (Translation, Page Handling, Status Bar, Advanced). See `quill/quillins_bundled/brf-tools/`.
- **Journal Stamp** (`com.quill.journalstamp`) — three-tab preferences page (Date Header, Word Count, Session Restore). Subscribes to `document.created`, `document.after_save`, `document.loaded_from_session`, `quillin.enabled`, and `settings.changed`. See `quill/quillins_bundled/journal-stamp/`.
- **Document Guardian** (`com.quill.docguardian`) — three-tab preferences page (Close Guard, Save Stamp, Save Confirmation). Subscribes to `document.before_close`, `document.before_save`, `document.after_save`, `quillin.enabled`, `quillin.disabled`, and `quill.shutdown`. See `quill/quillins_bundled/doc-guardian/`.
- **Status Scribe** (`com.quill.statusscribe`) — two-tab preferences page (Display, Announce). Contributes a live status bar cell; subscribes to `document.after_save`, `document.activated`, `quillin.enabled`, `quillin.disabled`, and `settings.changed`; uses `ui.log` developer logging and announcement priority. See `quill/quillins_bundled/status-scribe/`.

## Accessibility rules for Quillin Preferences

- The tab list must be keyboard-reachable and arrow-key navigable. The renderer uses a standard `wx.Notebook` so arrow keys switch tabs and tab names are announced.
- Every control must have a label. The lint gate rejects settings without `label`, `type`, `default`, and `description`.
- `StaticText` labels must be created before their associated controls in Windows child order. On Windows, JAWS finds the accessible name for a combo box or spin field by searching backward through the parent window's child list for the nearest `StaticText`. The renderer (`quillin_prefs_dialog.py`) always adds the label to the sizer before the control so Z-order is correct by construction. `boolean` settings use `wx.CheckBox` which carries its own label text and is exempt.
- Focus must return predictably after the page closes.
- No custom-drawn controls. No unlabeled controls. No mouse-only interactions.
- Screen readers must be able to review every preference without extra effort.

These rules are enforced at lint time, at load time, and at render time. A Quillin that violates them does not reach the preferences UI.

## Document event contributions

A Quillin can now respond to the things that happen to a document over its lifetime — when it opens, saves, closes, or is restored — by declaring `document_events` in its manifest. Each entry names one lifecycle event and one Python handler function.

### The ten available events

| Event name | When it fires |
| --- | --- |
| `document.opened` | A file was read from disk and loaded into an editor tab |
| `document.activated` | The user switched focus to this document tab |
| `document.before_save` | Immediately before a save; the document is still writable |
| `document.after_save` | After a successful save; the file is on disk |
| `document.before_close` | Before the tab is removed; the user can still cancel |
| `document.after_close` | After the tab is gone; use for cleanup only |
| `document.created` | A new, empty document was created (not opened from disk) |
| `document.loaded_from_session` | A document was restored from a crash or session file |
| `smart_trigger.entered` | Any smart trigger (`=name()`) was activated in any document |
| `abbreviation.expanded` | Any abbreviation was expanded in any document |

Note: `document.activated` fires every time focus changes. Do not perform expensive work there.

High-frequency events (text changed, cursor moved, key pressed) are not available in version 1.
They would allow a Quillin to observe every keystroke, which is both a performance hazard and a
privacy problem. They are excluded by design.

### Minimal example

```json
{
  "schema": "quill.extension/1",
  "id": "com.example.journal-stamp",
  "name": "Journal Stamp",
  "version": "1.0.0",
  "capabilities": ["document.events", "editor.write", "ui.announce"],
  "main": "extension.py",
  "contributes": {
    "document_events": [
      {
        "event": "document.created",
        "handler": "on_document_created",
        "title": "Insert journal header",
        "description": "Adds an ISO date line to every new document opened in the journal folder.",
        "conditions": {
          "file_path_pattern": "**/journal/**"
        }
      }
    ]
  }
}
```

```python
# extension.py
def on_document_created(api, event):
    from datetime import date
    api.editor_insert(f"{date.today().isoformat()}\n\n")
    api.announce("Journal header inserted.")
```

### Full document_events entry schema

```json
{
  "event": "document.opened",
  "handler": "my_handler_function",
  "title": "Short display name (shown in Quillin Manager)",
  "description": "What this handler does — shown in the event log and Quillin Manager.",
  "conditions": {
    "file_extension": ".log",
    "file_path_pattern": "**/logs/**",
    "content_pattern": "^\\.(LOG|log)"
  },
  "filter_extensions": [".txt", ".log"],
  "enabled_by_default": true
}
```

All fields except `event`, `handler`, `title`, and `description` are optional.

### Conditions and filtering

The `conditions` object narrows which documents trigger the handler. All specified conditions must match simultaneously (AND semantics).

| Field | Type | What it matches |
| --- | --- | --- |
| `file_extension` | string | Exact extension, e.g. `".txt"`, `".brf"` |
| `file_path_pattern` | string | Glob against the full file path |
| `content_pattern` | string | Regex matched against the first 4 KB of content |

`filter_extensions` is a shorthand list form of `file_extension` for matching multiple extensions at once (`[".txt", ".log"]` means either).

### The capability gate

`document.events` requires:
- `"document.events"` in `capabilities`
- A `"main"` entry module that defines the handler functions

Manifests that declare `document_events` without `document.events` fail validation and cannot be loaded. Manifests without a `main` module also fail. Both checks are enforced by `quillin_lint` and by the runtime loader.

### Event handler signature

Every event handler receives two arguments:

```python
def my_handler(api, event):
    # api: the QuillExtensionApi instance (same as command handlers)
    # event: dict with at minimum:
    #   event["event"] — the event name string
    #   event["document_id"] — opaque document identifier
    #   event["file_path"] — absolute path, or "" for unsaved documents
    #   event["title"] — display title of the document tab
    ...
```

For `document.before_save`, the handler may return `{"cancel": True, "reason": "..."}` to abort the save and show the reason in a notification. For all other events, the return value is ignored.

For `smart_trigger.entered`, `event` additionally contains `"trigger"` (the trigger name, without `=`) and `"args"` (a list of string arguments).

For `abbreviation.expanded`, `event` additionally contains `"trigger"` (the abbreviation text that was typed) and `"expansion"` (what it was replaced with).

### What events make possible

| Use case | Events to subscribe to |
| --- | --- |
| Auto-insert date headers in new journal files | `document.created` + `file_path_pattern` |
| Timestamp logs on open (`.LOG` compatibility) | `document.opened` + `content_pattern` |
| Word-count after every save | `document.after_save` |
| Warn before closing an empty log entry | `document.before_close` |
| Restore a status indicator when switching tabs | `document.activated` |
| Chain actions on abbreviation expand | `abbreviation.expanded` |
| React to any smart trigger globally | `smart_trigger.entered` |
| Insert a template in every newly created file | `document.created` |
| Check integrity after session restore | `document.loaded_from_session` |
| Initialize state when the Quillin activates | `quillin.enabled` |
| Release resources when the Quillin deactivates | `quillin.disabled` |
| Flush caches cleanly when QUILL closes | `quill.shutdown` |
| Hot-reload internal config when preferences change | `settings.changed` |

### Lifecycle events

Four events fire outside the document lifecycle and let a Quillin manage its own existence:

- **`quillin.enabled`** — fires once when the user enables the Quillin, or at startup if the Quillin was already enabled. Use it to announce activation, initialize caches, or register anything that requires the API to be live. The `event` dict carries `"quillin_id"` (the Quillin's own ID).
- **`quillin.disabled`** — fires when the user disables the Quillin in Quillin Manager. Use it to clean up resources and optionally announce deactivation. After this handler returns the Quillin's commands and event subscriptions are unregistered.
- **`quill.shutdown`** — fires when QUILL is about to exit. The handler should complete quickly (under 200ms); the host enforces this with a deadline and kills any Quillin that overruns it.
- **`settings.changed`** — fires when the user saves a change to any setting owned by this Quillin (i.e. any key registered in the Quillin's preferences contribution). The `event` dict carries `"key"` (the setting key), `"value"` (the new value), and `"old_value"` (the previous value). Use it to hot-reload internal config so preferences take effect without restarting the Quillin or QUILL.

### Accessibility rules for document event handlers

- Handlers must not block the UI thread. If a handler needs to do real work, use `api.run_in_background()` and announce the result on completion.
- Handlers that produce screen-reader output must call `api.announce()`. Silent mutations are confusing.
- Handlers that modify the document must call `api.announce()` describing the change so the user knows what happened without having to check.
- `document.before_save` handlers that cancel a save must provide a clear `"reason"` the user will understand.
- `document.activated` handlers must be fast and nearly silent; re-announcing the document title is the host's job, not the Quillin's.
- `quillin.enabled` / `quillin.disabled` handlers should use `priority="quiet"` when announcing activation to avoid interrupting the user's workflow.

---

## Timer events (schedule)

A Quillin can run a handler on a fixed background timer by declaring a `schedule` contribution. This is for periodic, low-frequency work — refreshing a status cell, polling a watched resource, or housekeeping — never for tight loops.

Each schedule entry names a unique `id`, an `interval_seconds` between 60 and 86400 (one minute to one day), and a `handler` function. The handler runs on a background thread so the editor never blocks, no matter how slow the work is.

A `schedule` contribution requires the `schedule` capability and a `main` module.

### Handler signature

```python
def on_tick(api, event: dict) -> None:
    #   event["timer_id"]        — the schedule entry id
    #   event["interval_seconds"] — the configured interval
    ...
```

### Context dict

| Key | Meaning |
| --- | --- |
| `timer_id` | The `id` of the schedule entry that fired |
| `interval_seconds` | The configured interval, in seconds |

### Use cases

- Refresh a status-bar cell so it never goes stale between saves.
- Periodically re-scan the document for a long-running metric.
- Flush an internal cache or write back accumulated state.

### Example manifest

```json
"capabilities": ["schedule", "ui.status", "editor.read"],
"main": "extension.py",
"contributes": {
  "schedule": [
    {
      "id": "refresh",
      "interval_seconds": 300,
      "handler": "on_timer_refresh",
      "description": "Recount the active document every five minutes."
    }
  ]
}
```

### Example extension.py

```python
def on_timer_refresh(api, event: dict) -> None:
    text = api.get_text()
    api.set_status(f"{len(text.split())} words")
    api.log(f"timer {event['timer_id']} every {event['interval_seconds']}s")
```

Timers start when the Quillin loads and are stopped when it is disabled, removed, or reloaded. Timers never run in Safe Mode.

---

## File-type contributions

A Quillin can declare which file extensions it handles. When a document with a matching extension opens, the Quillin's handler fires automatically — a specialized form of `document.opened` scoped to one or more extensions.

Each `file_types` entry lists `extensions` (lowercase, dot-prefixed, e.g. `.csv`, `.brf`), a `handler`, and an optional `description`. Because the handler runs the same out-of-process code as a document event, `file_types` reuses the `document.events` capability and requires a `main` module.

### Handler signature

```python
def on_file_opened(api, event: dict) -> None:
    #   event["file_path"]  — absolute path of the opened file
    #   event["extension"]  — the matched extension, lowercase (".csv")
    #   event["filename"]   — the file name with extension
    ...
```

### Context dict

| Key | Meaning |
| --- | --- |
| `file_path` | Absolute path of the opened file |
| `extension` | The matched extension, lowercase, with the dot |
| `filename` | The file name (with extension) |

### Use cases

- Announce the braille page count when a `.brf` or `.brl` file opens.
- Report the column headers when a `.csv` opens.
- Insert a timestamp when a `.log` file opens.

### Example

```json
"capabilities": ["document.events", "editor.read", "ui.announce"],
"main": "extension.py",
"contributes": {
  "file_types": [
    {
      "extensions": [".brf", ".brl"],
      "handler": "on_brf_opened",
      "description": "Announce the braille page count when a braille file opens."
    }
  ]
}
```

```python
def on_brf_opened(api, event: dict) -> None:
    text = api.get_text()
    pages = text.count("\x0c") + (0 if text.endswith("\x0c") else 1)
    api.announce(f"{event['extension']} file: {pages} braille pages.")
```

---

## Snippet gallery

A Quillin can contribute named, parameterized templates to a browseable gallery. Unlike `commands` or `abbreviations`, gallery snippets run no code — they are pure text expansion — so they require **no capability and no `main` module**.

Users open the gallery from **Insert → Snippet Gallery...**, pick a template, fill in any prompts, and the expanded text lands at the cursor (replacing any selection).

Each `snippet_gallery` entry has an `id` (unique within the Quillin), a `name`, a `body`, and optional `description`, `category`, and `params`. The body may contain `{param_name}` placeholders; each declared param's `name` must appear as a `{name}` placeholder in the body.

### Param syntax

Placeholders use single braces: `{title}`, `{date}`. Each param declares a `name` (matching the placeholder), a `label` (shown in the prompt), and an optional `default`. When the user inserts a snippet with params, QUILL prompts for each one in turn; cancelling any prompt cancels the insertion.

### Use cases

- A report header with title and date fields.
- A meeting invitation with subject, date, location, and agenda.
- A Markdown bug-report skeleton with title, build, and steps.

### Example manifest

```json
"contributes": {
  "snippet_gallery": [
    {
      "id": "report-header",
      "name": "Report Header",
      "category": "Reports",
      "description": "A titled report header with a date line.",
      "body": "# {title}\n\nDate: {date}\n\n---\n\n",
      "params": [
        { "name": "title", "label": "Report title", "default": "Status Report" },
        { "name": "date", "label": "Date", "default": "" }
      ]
    }
  ]
}
```

### How users access the gallery

Insert → Snippet Gallery... opens a list of every gallery snippet from every enabled Quillin, grouped by Quillin name. Selecting a snippet shows a read-only preview of its body; Insert expands it (prompting for params first) and Cancel closes the dialog.

---

## Categories

Quillins may optionally declare one or more category labels for the Quillins Manager filter. Categories are informational — they affect filtering but not validation, capability grants, or loading order.

Declare them as a JSON array at the top level of the manifest:

```json
"categories": ["writing", "accessibility"]
```

Valid categories: `accessibility`, `ai`, `braille`, `developer`, `education`, `formatting`, `integration`, `navigation`, `productivity`, `utilities`, `writing`.

---

## Quillin dependencies (`requires`)

A Quillin may declare that it depends on another Quillin being installed and enabled:

```json
"requires": [
  { "id": "com.quill.journalstamp", "min_version": "1.0.0" }
]
```

QUILL checks each dependency before loading the declaring Quillin. If a dependency is missing or too old, the Quillin fails to load with a clear error. `min_version` is optional; omit it to accept any installed version.

---

## Network host allowlist (`net_allowed_hosts`)

When a Quillin declares the `net` capability, it may optionally restrict which hosts it connects to:

```json
"capabilities": ["net"],
"net_allowed_hosts": ["api.openweathermap.org", "*.example.com"]
```

Each entry is a hostname or a wildcard `*.example.com` pattern. When the list is non-empty, QUILL blocks outbound connections to any host not on the list (even after the user has given blanket consent for `net`). When the list is omitted or empty, all outbound hosts are permitted with normal user consent.

---

## Status bar contributions

A Quillin may add live cells to the QUILL status bar. Each cell has a handler the host calls to get the current display string.

### Declaring a status bar cell

```json
"capabilities": ["ui.status", "ui.command"],
"main": "extension.py",
"contributes": {
  "status_bar": [
    {
      "id": "wordcount",
      "label": "Words: --",
      "handler": "get_word_count",
      "tooltip": "Current document word count",
      "width": 12
    }
  ]
}
```

- `id` — unique within the Quillin. Required.
- `label` — static fallback text before the first refresh. Required.
- `handler` — name of the Python function in `main` that returns the current cell string. Required.
- `tooltip` — description read to screen-reader users when the cell receives focus. Optional.
- `width` — suggested character-width hint (1-40). The host may ignore it. Optional; defaults to 10.

### Handler signature

```python
def get_word_count() -> str:
    """Called by the host to refresh the cell. No arguments."""
    return f"Words: {_current_count}"
```

The handler takes no arguments and must return a string. The host calls it on its schedule (on tab switch, after save, or on a timer). If the handler raises an exception, the host shows the last good value.

### Capability requirements

`contributes.status_bar` requires:
- `ui.status` capability (declared in `capabilities`)
- a `main` module (the handler function lives there)

Missing either causes validation to fail.

---

## Transcription providers (cloud speech-to-text)

A Quillin can add a **cloud transcription provider** to QUILL's speech engine — for example OpenAI Whisper — so it appears wherever you transcribe an audio or video file (Tools → Speech → Whisperer). This is a **host-mediated, declarative** contribution: your Quillin *declares* the provider, and QUILL's host performs the upload using its own network-egress-audited transcription path.

That design is deliberate. The sandbox never hands an extension raw audio bytes, an API key, or arbitrary network access, so a transcription-provider Quillin:

- ships **no code** (no `main`, no handlers), and
- needs **no `net` capability** (least privilege — it makes no calls itself).

Each `transcription_providers` entry declares:

- `id` — namespaced under `ext.` and unique across enabled Quillins.
- `display_name` — shown in the engine/model picker.
- `kind` — the host adapter that performs the call. Only host-vetted kinds are accepted; currently `openai_whisper`. (A manifest can therefore never point the host at an arbitrary endpoint.)
- `description` — optional, ≤400 chars.
- `credential` — optional credential-store label holding the API key. Empty uses the adapter's default (the OpenAI key configured in AI Hub).
- `max_file_mb` — optional upload-size ceiling override.

```json
{
  "schema": "quill.extension/1",
  "id": "com.example.whisper",
  "name": "OpenAI Whisper Transcription",
  "version": "1.0.0",
  "categories": ["ai", "integration", "accessibility"],
  "contributes": {
    "transcription_providers": [
      {
        "id": "ext.example.openai-whisper",
        "display_name": "OpenAI Whisper",
        "kind": "openai_whisper",
        "description": "Cloud speech-to-text via OpenAI's Whisper API.",
        "max_file_mb": 25
      }
    ]
  }
}
```

**Safety and behavior:**

- Cloud providers are **network-backed** and are **excluded from QUILL's offline paths** — the offline Watch Folder "Transcribe audio (offline)" action only ever uses on-device engines, so a cloud provider can never silently upload audio. Cloud transcription happens only through explicit, consented UI.
- A cloud provider is **unavailable in Safe Mode** and when no API key is configured.
- The bundled `openai-whisper-transcription` Quillin is the reference implementation.

### Capability requirements

`contributes.transcription_providers` requires **no** capability and **no** `main` module — it is purely declarative.

---

## Command descriptions

Commands may carry a human-readable `description` for display in the keyboard reference and command palette:

```json
{
  "id": "ext.myquillin.run",
  "title": "Run My Quillin",
  "description": "Processes the selected text and inserts the result below the cursor.",
  "run": { "handler": "run" }
}
```

`description` is optional, at most 400 characters. It is shown in the QUILL keyboard reference alongside the title and binding.

---

## Preferences — search keywords

Individual settings may carry extra words users might type to find the setting in the Preferences search box:

```json
{
  "key": "date_format",
  "label": "Date format",
  "type": "choice",
  "default": "long",
  "description": "How the date is written in the header.",
  "search_keywords": ["timestamp", "iso", "strftime", "header format"]
}
```

QUILL's preference search matches against `label`, `description`, and `search_keywords`. Adding synonyms and technical terms improves discoverability for users who may not know the setting's label.

---

## User control — capabilities, consent, and permissions

Understanding how users control Quillin behavior is essential for writing extensions that respect the user's expectations.

### Enable and disable

Users can enable or disable any Quillin at any time from **Tools → Quillins Manager**. Disabling stops all of a Quillin's event handlers, commands, and status bar cells immediately. The Quillin's settings data is preserved. The `quillin.disabled` event fires when this happens, giving the Quillin a chance to clean up gracefully before it goes quiet.

### Capability enforcement — two levels

**Level 1: declared capabilities.** A Quillin may only call API methods that correspond to capabilities it declared in its manifest. If it tries to call `get_text()` without `editor.read`, the host blocks the call with a `CapabilityError` and notifies the Quillin. This check happens at every API call, not just at install time.

**Level 2: consent-gated capabilities.** Four capabilities are additionally consent-gated — they prompt the user with a "Allow this action?" dialog on every individual use:

| Capability | Gated action |
| --- | --- |
| `fs.read` | Reading a file from disk |
| `fs.write` | Writing a file to disk |
| `net` | Making a network request |
| `settings.core.write` | Changing a QUILL-wide setting |

When a user says no, QUILL raises `ConsentDeniedError`. Your handler should catch this and respond gracefully — do not retry without another explicit user trigger. Saying no once does not revoke the capability permanently; it only denies the specific action.

The remaining capabilities (`editor.read/write`, `ui.announce/command/prompt/choices/status/log`, `clipboard.*`, `storage`, `document.*`, `settings.own.*`) are disclosed once at install time and do not prompt again.

### Per-event control (`enabled_by_default`)

Each document event subscription carries an `enabled_by_default` boolean. When `false`, QUILL registers the subscription but starts it inactive — the handler does not fire until the user turns it on. Use this for behaviors that are clearly optional or potentially disruptive, so users do not need to hunt for a setting to silence something they did not ask for.

A per-event toggle UI is available in the Quillins Manager (**Configure Events...**). Select a Quillin, click that button, and check or uncheck individual event subscriptions. The state is persisted per-Quillin in `state.json` and respected at dispatch time.

### Bundled vs. third-party Quillins

QUILL ships with trusted, first-party bundled Quillins (Tier C). Bundled Quillins have their non-consent capabilities pre-granted so they do not nag on first use. Consent-gated capabilities (`fs.*`, `net`, `settings.core.write`) are never pre-granted — even bundled Quillins must ask.

Third-party Quillins (user-installed from outside the install tree) are locked off until the `core.third_party_plugins` feature flag is enabled. This flag is `locked_off` for QUILL 1.0 and will unlock when the publishing and review process is ready. Third-party Quillins, when enabled, go through the same capability gate and consent flow as the runtime enforces — there is no shortcut for any code origin.

---

## Developer logging (`api.log`)

Quillins with the `ui.log` capability may call `api.log(message)` to write structured log lines to the QUILL Developer Console:

```python
api.log("Journal Stamp enabled — ready to stamp.")
api.log(f"Setting changed: {key} = {value!r}")
```

`api.log()` is a no-op when the Developer Console is closed or when `QUILL_DEV_BUILD` is not set; it never writes to files or to the screen reader. Declare the `ui.log` capability to use it:

```json
"capabilities": ["ui.log"]
```

`ui.log` requires no consent gate — it has no user-visible side effect and cannot exfiltrate data.

---

## Announcement priority

`api.announce()` accepts an optional `priority` keyword argument:

```python
api.announce("Saved.", priority="quiet")      # queued, does not interrupt
api.announce("Warning: TODO found.", priority="normal")
api.announce("Error: file not writable.", priority="urgent")  # interrupts
```

Valid priorities: `quiet`, `normal`, `urgent`. Default is `normal`. The host maps these to the screen reader's urgency channel (SSML priority, NVDA speak flags, etc.). Use `quiet` for informational messages that should queue behind ongoing speech; use `urgent` only for errors or warnings requiring immediate attention.

---

## Scaffold tool (`quillin_new`)

The scaffold tool generates a ready-to-edit Quillin directory from a single command:

```
python -m quill.tools.quillin_new com.example.myquillin "My Quillin" --out src/quillins/myquillin
```

Options:

| Flag | Description |
| --- | --- |
| `--layer1` | Generate a snippet-only extension (no Python entry module) |
| `--categories cat,...` | Add category labels (comma-separated) |
| `--doc-events` | Include sample `quillin.enabled`, `document.opened`, and `settings.changed` handlers |
| `--status-bar` | Include a sample status bar cell contribution |

After running the tool, edit `manifest.json` (fill in author, description, and exact capabilities needed) and `extension.py` (implement your logic), then lint with `python -m quill.tools.quillin_lint <dir> --strict`.
