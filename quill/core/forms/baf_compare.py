"""Where BAF's older BFL parser and the BFL 1 reader disagree, in sentences.

BAF's Structure Mode and REST ``/bfl/parse`` still use the older parser
(``includes/bfl``, ported exactly in :mod:`baf_parser`). It drops the first
choice of an indented list, the field after an indented ``if``, the inside of
indented ``columns``, and every BFL 1 spelling. Check This Form uses this to
warn before a form is sent somewhere that still reads it the old way.
"""

from __future__ import annotations

from typing import Any

from quill.core.forms import model as M
from quill.core.forms.baf_parser import baf_parse
from quill.core.forms.bfl_read import read


def _old_fields(config: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for f in config["form"]["fields"]:
        if f.get("type") == "columns":
            for column in f.get("columns", []):
                out.extend(column)
        elif f.get("type") != "section":
            out.append(f)
    return out


def divergences(text: str) -> list[str]:
    """Sentences saying what the older parser would make differently of ``text``."""
    model = read(text).model
    old = _old_fields(baf_parse(text))
    by_id = {f["id"]: f for f in old}
    out: list[str] = []
    for fid, item in M.fields(model).items():
        name = item.get("label") or fid
        theirs = by_id.get(fid)
        if theirs is None and fid.startswith("field_"):
            theirs = next(
                (
                    f
                    for f in old
                    if f.get("label", "") == item.get("label", "") and f["type"] == item["type"]
                ),
                None,
            )
        if theirs is None:
            out.append(f"The older reader skips {name} ({item['type']}).")
            continue
        labels = [c.get("label") for c in theirs.get("choices", []) if isinstance(c, dict)]
        dropped = [c["label"] for c in item.get("choices") or [] if c["label"] not in labels]
        if dropped and not (item["type"] == "checkbox" and dropped == ["Yes"]):
            out.append(f"The older reader drops {', '.join(dropped)} from {name}.")
        if "when" in item and not theirs.get("conditional_logic"):
            out.append(f"The older reader shows {name} every time: it does not read the condition.")
        if item.get("required") and not theirs.get("required"):
            out.append(f"The older reader does not make {name} required.")
    return out
