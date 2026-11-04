"""Forms: the wx-free core QUILL and QUILL Lite share (wordpress.md 17a, 17a.15).

BAF (BITS Accessible Forms) is the home of the form model and its languages;
this package is QUILL's port of it, checked against BAF's own conformance
suite (``tests/conformance`` in BAF), and keeps one schema with it.

- :mod:`model`, :mod:`model_json`, :mod:`schema_check`: the model is BAF's JSON
  (plain dicts), ``schema/form.schema.json`` is BAF's schema, unchanged.
- :mod:`expr`, :mod:`expr_eval`, :mod:`expr_sentence`: the expression language.
- :mod:`rules`: scores, the quiz outcome, what is shown, for Fill It In Yourself.
- :mod:`bfl_read` (with :mod:`bfl_lex`, :mod:`bfl_read_parts`) and
  :mod:`bfl_write`: BFL 1 in and out, as BAF reads and writes it;
  :mod:`bfl_document` keeps every untouched byte of a person's own document,
  and the lines BAF skips (islands).
- :mod:`baf_parser`, :mod:`baf_format`, :mod:`baf_compare`: BAF's older BFL
  parser and formatter, still used by its Structure Mode, and where they differ.
- :mod:`libraries`: BAF's 124 built-in choice libraries.
- :mod:`translate`, :mod:`summary`: translations side by side; spoken summaries.
- :mod:`interop_surveyjs`, :mod:`interop_xlsform`, :mod:`interop_html`.
- :mod:`menu` (the UI helper's): where every Forms command lives.

Import submodules directly; this package imports nothing so ``menu`` stays light.
"""

from __future__ import annotations
