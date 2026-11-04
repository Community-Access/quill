"""Forms: the wx-free core QUILL and QUILL Lite share (wordpress.md 17a, 17a.15).

- :mod:`model` and :mod:`model_json`: the form model, the one definition of a
  form, and its JSON (versioned, with migrations); :mod:`schema_check` checks
  JSON against ``schema/form.schema.json``.
- :mod:`expr`, :mod:`expr_eval`, :mod:`expr_sentence`: the one expression
  language for conditions, calculations, scoring and smart defaults.
- :mod:`rules`: what a form shows, works out and scores for some answers.
- :mod:`bfl_read`, :mod:`bfl_write`: BFL in and out, keeping every byte, with
  islands for what QUILL cannot read; :mod:`bfl_spelling` lists the new
  spellings.
- :mod:`baf_parser`, :mod:`baf_format`, :mod:`baf_compare`: exact ports of
  BAF's PHP parser and formatter, and where they disagree with QUILL.
- :mod:`libraries`: BAF's 124 choice libraries.
- :mod:`translate`, :mod:`summary`: translations, and spoken summaries.
- :mod:`interop_surveyjs`, :mod:`interop_xlsform`, :mod:`interop_html`:
  imports and exports that run on the computer.
"""

from __future__ import annotations

from quill.core.forms.bfl_read import BflDocument, read_bfl, read_form
from quill.core.forms.bfl_write import to_bfl, write_bfl
from quill.core.forms.model import (
    MODEL_VERSION,
    Choice,
    Columns,
    Field,
    Form,
    Island,
    Page,
    Section,
)
from quill.core.forms.model_json import dumps, from_dict, loads, to_dict

__all__ = [
    "MODEL_VERSION",
    "BflDocument",
    "Choice",
    "Columns",
    "Field",
    "Form",
    "Island",
    "Page",
    "Section",
    "dumps",
    "from_dict",
    "loads",
    "read_bfl",
    "read_form",
    "to_bfl",
    "to_dict",
    "write_bfl",
]
