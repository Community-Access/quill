"""Tests 123 to 126 of the live WordPress run: building Gravity Forms forms in QUILL.

Loaded by ``docs/qa/wordpress-live-run.py`` (``_load_workbench_checks``), which
passes itself to :func:`register`. Each test goes through the same core
functions New Gravity Form, Edit Form and the two Copy commands call
(``quill/core/wordpress/gravity_build*.py`` and ``gravity_qaf.py``).

Gravity Forms is a licensed plugin and the test site does not have it, so every
test here is "skipped: Gravity Forms not installed" until a site with ``gf/v2``
in its REST index is used; that is never a failure. Forms made here are titled
"QUILL live test" and deleted afterwards (``DELETE gf/v2/forms/{id}?force=1``);
no test reads or writes an entry.
"""

from __future__ import annotations

import copy
from typing import Any

#: The harness module, set by :func:`register`.
H: Any = None

AREA = "Workbench, plugins and WordPress.org (10B.3)"
NS = "gf/v2"


def register(harness: Any) -> None:
    """Put tests 123 to 126 on the harness's list."""
    global H
    H = harness
    for ref, name, fn, who, writes in _TESTS:
        harness.check(AREA, ref, name, who=getattr(harness, who), writes=writes)(fn)


def _need(ctx: Any) -> None:
    if ctx.index is None or NS not in set(ctx.index.namespaces):
        raise H.NotRun("skipped: Gravity Forms not installed")


def _built(ctx: Any, words: str) -> dict[str, Any]:
    """A form with every field family QUILL builds, made and deleted afterwards."""
    from quill.core.wordpress import gravity_build as gb
    from quill.core.wordpress import gravity_build_save as gs

    api = ctx.api(H.ADMIN)
    form = gb.new_form(ctx.title(words))
    for kind in gb.FIELD_TYPES:
        values: dict[str, Any] = {"label": f"{kind} question", "description": "Live test"}
        if kind in gb.CHOICE_TYPES:
            values["choices"] = "One\nTwo = 2"
        if kind == "page":
            values["label"] = ""
        gb.add_field(form, kind, values)
    gb.set_condition(form["fields"][1], gb.Condition("show", "1", "is", "yes"))
    saved = gs.create(api, form)
    route = saved.route
    ctx.later(f"delete Gravity Forms form {saved.form_id}", lambda: api.delete(route, force=1))
    H.expect(not saved.problems, "; ".join(saved.problems))
    return {"saved": saved, "sent": form}


def _build(ctx: Any) -> str:
    _need(ctx)
    made = _built(ctx, "gravity build")
    stored = made["saved"].stored
    kinds = [f.get("type") for f in stored.get("fields", [])]
    said = ", ".join(map(str, kinds))
    return f"form {made['saved'].form_id}: {len(kinds)} fields read back as sent ({said})"


def _edit(ctx: Any) -> str:
    from quill.core.wordpress import gravity_build as gb
    from quill.core.wordpress import gravity_build_save as gs

    _need(ctx)
    api = ctx.api(H.ADMIN)
    saved = _built(ctx, "gravity edit")["saved"]
    opened = api.get(saved.route)
    edited = copy.deepcopy(opened)
    gb.edit_field(edited["fields"][0], {"label": "Edited in QUILL", "isRequired": True})
    gb.move_field(edited, 0, 2)
    after = gs.update(api, saved.route, opened, edited)
    H.expect(not after.problems, "; ".join(after.problems))
    try:  # the conflict check: the copy opened before is stale now
        gs.update(api, saved.route, opened, edited)
    except gs.FormChanged:
        refused = True
    else:
        refused = False
    H.expect(refused, "a stale copy was saved over the newer form")
    back = gs.put_back(api, saved.route, after.stored, opened)
    labels = [f.get("label") for f in back.get("fields", [])][:3]
    H.expect(labels[0] == opened["fields"][0]["label"], f"undo left {labels}")
    return f"edited, conflict refused, put back ({', '.join(map(str, labels))})"


def _checks_and_qaf(ctx: Any) -> str:
    from quill.core.forms import model as M
    from quill.core.wordpress.gravity_build_checks import check_form
    from quill.core.wordpress.gravity_qaf import to_gravity, to_qaf
    from quill.core.wordpress.workbench_gravity import gravity_forms

    _need(ctx)
    api = ctx.api(H.ADMIN)
    forms = gravity_forms(api)
    if not forms:
        raise H.NotRun("Gravity Forms has no forms on the site")
    form = api.get(f"{NS}/forms/{next(iter(forms))}")
    findings = check_form(form)
    qaf = to_qaf(form)
    problems = M.validate(qaf.form)
    H.expect(not problems, f"the QAF model is not valid: {problems[:1]}")
    back = to_gravity(qaf.form)
    return (
        f"{form.get('title')}: {len(findings)} findings, {len(qaf.lost)} things QAF cannot carry, "
        f"{len(back.form['fields'])} fields back"
    )


def _contributor(ctx: Any) -> str:
    from quill.core.wordpress import gravity_build as gb
    from quill.core.wordpress import gravity_build_save as gs

    _need(ctx)
    api = ctx.api(H.CONTRIBUTOR)
    error = H.refused(lambda: gs.create(api, gb.new_form(ctx.title("gravity refused"))))
    return f"{error.status}: {error.plain}"


_TESTS: tuple[tuple[str, str, Any, str, bool], ...] = (
    ("123", "Gravity Forms: build every field family, read it back", _build, "ADMIN", True),
    ("124", "Gravity Forms: edit, conflict refused, put back", _edit, "ADMIN", True),
    ("125", "Gravity Forms: checks, to QAF and back", _checks_and_qaf, "ADMIN", False),
    ("126", "Gravity Forms: a contributor cannot build a form", _contributor, "CONTRIBUTOR", True),
)
