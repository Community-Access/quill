# QAF form model conformance suite

These files are the contract between every program that reads or writes the
QAF form model: QAF itself (PHP) and QUILL's form windows (Python, in
`quill/core/forms/`). They are plain JSON and QAF form language text, so any language can
run them. `manifest.json` lists every case; a reader that runs the manifest
runs the whole suite.

QAF runs it with `tests/unit/Model/ConformanceManifestTest.php`, and runs the
`expressions` and `behaviour` suites against the JavaScript copy used on
published forms with `node tests/js/run-conformance.js`.

## Rules for comparing

- **Models** are JSON. Two models are the same when objects have the same
  keys and values (key order does not matter), arrays have the same items in
  the same order, text matches exactly, numbers are equal, and true, false
  and null are not numbers (in Python, `True == 1`; do not let that pass).
- **the QAF form language** is compared byte for byte. Every file here uses LF line ends and
  UTF-8 without a byte order mark (`.gitattributes` keeps it that way); a
  reader must still accept CRLF and a byte order mark in its input.
- **Errors** are compared by where they are (a JSON pointer, a QAF form language line
  number, or, for an expression error that gives an `offset`, the offset in
  UTF-8 bytes from the start of the text). Wording is free.
- **Canonical expression text** must read back to itself.

## The suites

| Kind | Files | What a reader must do |
| --- | --- | --- |
| `schema` | `../../schema/form.schema.json` | Validate models with this schema (JSON Schema 2020-12). The format `qaf-expression` means "parses as an expression". |
| `expressions` | `expressions/cases.json`, `expressions/php-edges.json` | Parse each text to its canonical text (and AST where given), render its sentence with the file's labels, reject each error case, and evaluate each case in the file's context. |
| `valid-models` | `models/valid/*.json` | Accept: no schema errors and no errors from the rules in `docs/form-model.md` ("Rules beyond the schema"). |
| `invalid-models` | `models/invalid/cases.json` | Reject each model with an error at the given path. |
| `behaviour` | `models/behaviour.json` | Score answers, choose the quiz outcome, and decide which items are shown. |
| `qaf-canonical` | `qaf/canonical/*.qaf` with a model | Model to QAF form language gives the `.qaf` byte for byte; the `.qaf` reads to the model with no errors or warnings. |
| `qaf-legacy` | `qaf/legacy/*.qaf` | Older QAF form language reads to the `.json` model with no errors, and that model writes as the `.canonical.qaf`. |
| `qaf-errors` | `qaf/errors.json` | Each text gives an error on the given line. |
| `builder` | `builder/*` | QAF only: its stored form shape and the migration of forms saved before the model. |
| `imports` | `imports/<source>/*` | QAF only: each source file converts to the `.model.json`, with the `.report.json`. |
| `exports` | `exports/*` | QAF only: each model exports to the builder's format byte for byte, with the `.report.json`, and reads back through the importer. |

Every model in `qaf-canonical`, `qaf-legacy`, `builder` and `imports` is also
valid. The models in `valid-models` and the canonical edge cases together use
every field type, every rule action, every operator and function of the
expression language, every block of the QAF form language, translations, scoring, settings,
confirmations, notifications and extensions.

## Adding a case

Add the files, list them in `manifest.json`, and run QAF's tests. A file in
these folders that the manifest does not list fails the suite, so nothing
goes unchecked.
