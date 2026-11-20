"""Test This Form for Gravity Forms, through its REST API v2 (complete.md 10B.3).

Split from :mod:`quill.core.wordpress.workbench_gravity` (GATE-11). Test values
QUILL can fill for each common field (:func:`sample_inputs`), read back from
the ``input_1: value`` lines the person edits (:func:`parse_inputs`), checked
by ``POST gf/v2/forms/{id}/submissions/validation`` -- which saves nothing --
and then sent by ``POST gf/v2/forms/{id}/submissions`` (:func:`submit`).
Gravity Forms answers a refused submission with HTTP 400 and its
``validation_messages``; :class:`~quill.core.wordpress.api.WordPressApiError`
keeps that body, so each refused field is named. Wx-free.
"""

from __future__ import annotations

import re
import time
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Any
from urllib.parse import urlsplit

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.workbench_gravity import NS, _text, truthy

__all__ = [
    "SubmitAnswer",
    "TestInput",
    "is_practice_site",
    "parse_inputs",
    "sample_inputs",
    "submit",
]


@dataclass(frozen=True)
class TestInput:
    name: str
    label: str
    value: str


@dataclass(frozen=True)
class SubmitAnswer:
    valid: bool
    messages: dict[str, str] = field(default_factory=dict)
    entry_id: str = ""
    confirmation: str = ""
    problem: str = ""

    def lines(self, labels: Mapping[str, str]) -> list[str]:
        found = [f"{labels.get(k, 'Field ' + k)}: {_text(v)}" for k, v in self.messages.items()]
        if self.problem:
            found.append(self.problem)
        return found or ["Gravity Forms did not say which field it refused."]


def _date_sample(spec: Mapping[str, Any]) -> str:
    now = time.localtime()
    fmt = str(spec.get("dateFormat", "") or "mdy")
    y, m, d = f"{now.tm_year:04d}", f"{now.tm_mon:02d}", f"{now.tm_mday:02d}"
    sep = "-" if fmt.endswith("dash") else "." if fmt.endswith("dot") else "/"
    if fmt.startswith("dmy"):
        return sep.join((d, m, y))
    if fmt.startswith("ymd"):
        return sep.join((y, m, d))
    return sep.join((m, d, y))


_SAMPLES = {
    "text": "QUILL test",
    "hidden": "QUILL test",
    "textarea": "A test submission sent from QUILL's WordPress Workbench.",
    # Not example.com: Gravity Forms 2.9.15 and later reject an address at example.com or
    # domain.com as spam ("The email address entered is invalid", seen on the test site,
    # Gravity Forms 3.2.3.1, 2026-11-20). example.org is reserved as well and is not refused.
    "email": "quill-test@example.org",
    "phone": "555-0100",
    "website": "https://example.com",
    "number": "1",
}
_ADDRESS = {"1": "1 Test Street", "3": "Testville", "4": "Test State", "5": "12345"}
_SKIP = frozenset({"html", "section", "page", "captcha", "fileupload", "post_image", "signature"})


def sample_inputs(form: Mapping[str, Any]) -> tuple[list[TestInput], list[str]]:
    """Test values for each field QUILL can fill, and the labels of those it cannot."""
    found: list[TestInput] = []
    skipped: list[str] = []
    for spec in form.get("fields") or []:
        if not isinstance(spec, dict):
            continue
        kind = str(spec.get("inputType", "") or spec.get("type", ""))
        fid = str(spec.get("id", ""))
        label = str(spec.get("label", "") or f"Field {fid}")
        if kind in _SKIP or str(spec.get("visibility", "")) == "administrative":
            if kind not in ("html", "section", "page"):
                skipped.append(label)
            continue
        inputs = [
            i for i in spec.get("inputs") or [] if isinstance(i, dict) and not i.get("isHidden")
        ]
        choices = [c for c in spec.get("choices") or [] if isinstance(c, dict)]
        first = str(choices[0].get("value", "") or choices[0].get("text", "")) if choices else ""
        if kind == "checkbox" and inputs:
            name = "input_" + str(inputs[0].get("id", f"{fid}.1")).replace(".", "_")
            found.append(TestInput(name, f"{label}, {inputs[0].get('label', '')}", first or "1"))
        elif kind == "consent":
            found.append(TestInput(f"input_{fid}_1", label, "1"))
        elif kind in ("select", "radio", "multiselect", "poll", "survey", "quiz") and first:
            found.append(TestInput(f"input_{fid}", label, first))
        elif kind in ("name", "address") and inputs:
            for sub in inputs:
                part = str(sub.get("id", "")).partition(".")[2]
                value = _ADDRESS.get(part, "United States" if part == "6" else "")
                if kind == "name":
                    value = {"3": "Quill", "6": "Tester"}.get(part, "")
                if value:
                    name = "input_" + str(sub.get("id", "")).replace(".", "_")
                    found.append(TestInput(name, f"{label}, {sub.get('label', '')}", value))
        elif kind == "email" and inputs:
            for sub in inputs:
                name = "input_" + str(sub.get("id", "")).replace(".", "_")
                found.append(TestInput(name, f"{label}, {sub.get('label', '')}", _SAMPLES["email"]))
        elif kind == "time":
            # One string, not its three inputs: input_N_1..3 are refused with no message,
            # while "10:30 am" is stored as given (live, Gravity Forms 3.2.3.1, 2026-11-20).
            clock = "10:30" if str(spec.get("timeFormat", "") or "12") == "24" else "10:30 am"
            found.append(TestInput(f"input_{fid}", label, clock))
        elif kind == "date":
            found.append(TestInput(f"input_{fid}", label, _date_sample(spec)))
        elif kind == "phone" and str(spec.get("phoneFormat", "") or "standard") == "standard":
            # Gravity Forms' default phone format refuses "555-0100" ("Phone format:
            # (###) ###-####", live on the test site, 3.2.3.1, 2026-11-20).
            found.append(TestInput(f"input_{fid}", label, "(555) 555-0100"))
        elif kind == "number" and spec.get("rangeMin") not in (None, ""):
            found.append(TestInput(f"input_{fid}", label, str(spec["rangeMin"])))
        elif kind in _SAMPLES:
            found.append(TestInput(f"input_{fid}", label, _SAMPLES[kind]))
        elif spec.get("isRequired"):
            skipped.append(label)
    return found, skipped


def parse_inputs(text: str) -> dict[str, str]:
    """``input_1: value`` lines back into the body Gravity Forms takes."""
    values: dict[str, str] = {}
    for line in text.splitlines():
        name, sep, value = line.partition(":")
        name = name.strip()
        if sep and re.fullmatch(r"input_\d+(_\d+)?", name):
            values[name] = value.strip()
    return values


def _answer(payload: Any, problem: str = "") -> SubmitAnswer:
    data = payload if isinstance(payload, dict) else {}
    messages = data.get("validation_messages") or {}
    messages = messages if isinstance(messages, dict) else {}
    valid = truthy(data.get("is_valid", False)) and not problem
    return SubmitAnswer(
        valid,
        {str(k): str(v) for k, v in messages.items()},
        str(data.get("entry_id", "") or ""),
        _text(data.get("confirmation_message", "")),
        problem,
    )


def _newest_entry(api: Any, form_id: str) -> int:
    """The form's newest entry id, or 0 (none, or the entries cannot be read)."""
    params = {"sorting[key]": "id", "sorting[direction]": "DESC", "paging[page_size]": 1}
    try:
        found = api.get(f"{NS}/forms/{form_id}/entries", **params, _field_ids="id")
    except WordPressApiError:
        return 0
    rows = found.get("entries") if isinstance(found, Mapping) else found
    first = rows[0] if isinstance(rows, list) and rows and isinstance(rows[0], Mapping) else {}
    text = str(first.get("id", "") or "")
    return int(text) if text.isdigit() else 0


def submit(
    api: Any, form_id: str, values: Mapping[str, str], *, validate_only: bool
) -> SubmitAnswer:
    """Validate (no entry is made) or submit *values*; a refusal comes back as the answer.

    Gravity Forms' submissions route does not say which entry it made (3.2.3.1 on
    the test site answers ``is_valid`` and the confirmation, no ``entry_id``), so a
    real submission reads the form's newest entry before and after: the new one is
    the entry Ctrl+Z moves to the Trash.
    """
    route = f"{NS}/forms/{form_id}/submissions" + ("/validation" if validate_only else "")
    before = 0 if validate_only else _newest_entry(api, form_id)
    try:
        answer = _answer(api.post(route, dict(values)))
    except WordPressApiError as exc:
        if exc.status == 400 and isinstance(exc.body, dict):
            return _answer(exc.body)
        if exc.status == 400:
            return _answer({}, exc.plain)
        raise
    if validate_only or not answer.valid or answer.entry_id:
        return answer
    after = _newest_entry(api, form_id)
    return replace(answer, entry_id=str(after)) if after > before else answer


def is_practice_site(url: str, name: str = "") -> bool:
    """A site on this computer, or the Practice Site, where a test entry costs nothing."""
    from quill.core.wordpress.workbench_practice import PRACTICE_NAME

    host = (urlsplit(url).hostname or "").lower()
    return (
        name == PRACTICE_NAME
        or host in ("localhost", "127.0.0.1", "::1")
        or host.endswith((".localhost", ".test"))
    )
