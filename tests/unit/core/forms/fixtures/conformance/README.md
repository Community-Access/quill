# BAF form model conformance suite

These files are the contract between every program that reads or writes the
BAF form model: BAF itself (PHP) and QUILL's form windows (Python, in
`quill/core/forms/`). They are plain JSON and BFL text, so any language can
run them. `manifest.json` lists every case; a reader that runs the manifest
runs the whole suite.

BAF runs it with `tests/unit/Model/ConformanceManifestTest.php`, and runs the
`expressions` and `behaviour` suites against the JavaScript copy used on
published forms with `node tests/js/run-conformance.js`.

## Rules for comparing

- **Models** are JSON. Two models are the same when objects have the same
  keys and values (key order does not matter), arrays have the same items in
  the same order, text matches exactly, numbers are equal, and true, false
  and null are not numbers (in Python, `True == 1`; do not let that pass).
- **BFL** is compared byte for byte. Every file here uses LF line ends and
  UTF-8 without a byte order mark (`.gitattributes` keeps it that way); a
  reader must still accept CRLF and a byte order mark in its input.
- **Errors** are compared by where they are (a JSON pointer, a BFL line
  number, or, for an expression error that gives an `offset`, the offset in
  UTF-8 bytes from the start of the text). Wording is free.
- **Canonical expression text** must read back to itself.

## The suites

| Kind | Files | What a reader must do |
| --- | --- | --- |
| `schema` | `../../schema/form.schema.json` | Validate models with this schema (JSON Schema 2020-12). The format `baf-expression` means "parses as an expression". |
| `expressions` | `expressions/cases.json`, `expressions/php-edges.json` | Parse each text to its canonical text (and AST where given), render its sentence with the file's labels, reject each error case, and evaluate each case in the file's context. |
| `valid-models` | `models/valid/*.json` | Accept: no schema errors and no errors from the rules in `docs/form-model.md` ("Rules beyond the schema"). |
| `invalid-models` | `models/invalid/cases.json` | Reject each model with an error at the given path. |
| `behaviour` | `models/behaviour.json` | Score answers, choose the quiz outcome, and decide which items are shown. |
| `bfl-canonical` | `bfl/canonical/*.bfl` with a model | Model to BFL gives the `.bfl` byte for byte; the `.bfl` reads to the model with no errors or warnings. |
| `bfl-legacy` | `bfl/legacy/*.bfl` | Older BFL reads to the `.json` model with no errors, and that model writes as the `.canonical.bfl`. |
| `bfl-errors` | `bfl/errors.json` | Each text gives an error on the given line. |
| `builder` | `builder/*` | BAF only: its stored form shape and the migration of forms saved before the model. |
| `imports` | `imports/<source>/*` | BAF only: each source file converts to the `.model.json`, with the `.report.json`. |
| `exports` | `exports/*` | BAF only: each model exports to the builder's format byte for byte, with the `.report.json`, and reads back through the importer. |

Every model in `bfl-canonical`, `bfl-legacy`, `builder` and `imports` is also
valid. The models in `valid-models` and the canonical edge cases together use
every field type, every rule action, every operator and function of the
expression language, every block of BFL, translations, scoring, settings,
confirmations, notifications and extensions.

## Adding a case

Add the files, list them in `manifest.json`, and run BAF's tests. A file in
these folders that the manifest does not list fails the suite, so nothing
goes unchecked.
