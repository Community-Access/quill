"""Tests 144 to 150 of the live WordPress run: the rest of Gravity Forms in QUILL.

Loaded by ``docs/qa/wordpress-live-run.py`` (``_load_workbench_checks``), which
passes itself to :func:`register`. Tests 104 to 108, 123 to 126 and 139 to
141 already build a form, edit it, save its messages and send one test entry;
these cover what they leave out, through the same core functions the
Workbench's commands call:

- 144, every field type QUILL builds with every property its editor sets, the
  form's own settings, and a removed field taking its logic with it
  (``gravity_build``, ``gravity_build_save``);
- 145, Test This Form on that form: an answer for every field it fills, and
  Ctrl+Z moving the entry to the Trash (``workbench_gravity_submit``);
- 146, an entry's answers changed and put back, a stale change refused,
  Spam and Not Spam, a note, Read and Unread (``workbench_gravity_answers``,
  ``workbench_forms.set_entry_spam``, ``workbench_gravity``);
- 147, notifications and confirmations changed, turned off and removed, and
  Resend Notifications to an address that cannot receive mail
  (``gravity_messages``, ``workbench_gravity.resend_notifications``);
- 148, Copy as a QUILL Accessible Form and Copy Old Entries into QAF, then the
  copies undone (``gravity_qaf``, ``gravity_qaf_entries``);
- 149, Copy as a Gravity Form from that QAF form (``gravity_qaf.to_gravity``);
- 150, Watch: a new Gravity Forms entry raises what the Watch compares, and
  the Watch says so once (``workbench_watches``).

Every form here is titled "QUILL live test" and deleted afterwards, with its
entries. A notification left on goes only to ``example.invalid``, which no
mail server delivers to, so nobody is emailed.
"""

from __future__ import annotations

import copy
from typing import Any

#: The harness module, set by :func:`register`.
H: Any = None

AREA = "Workbench, plugins and WordPress.org (10B.3)"
NS = "gf/v2"
#: Reserved by RFC 2606: no mail is ever delivered here.
NOWHERE = "quill-live-test@example.invalid"


def register(harness: Any) -> None:
    """Put tests 144 to 150 on the harness's list."""
    global H
    H = harness
    for ref, name, fn, who, writes in _TESTS:
        harness.check(AREA, ref, name, who=getattr(harness, who), writes=writes)(fn)


def _need(ctx: Any) -> None:
    if ctx.index is None or NS not in set(ctx.index.namespaces):
        raise H.NotRun("skipped: Gravity Forms not installed")


def _quiet(form: dict[str, Any]) -> None:
    """Every notification sent nowhere and turned off, so a submission emails nobody."""
    for note in (form.get("notifications") or {}).values():
        note["to"], note["toType"], note["isActive"] = NOWHERE, "email", False


def _full_form(ctx: Any) -> dict[str, Any]:
    """The form 144 builds and 145 to 150 use: made once a run, deleted afterwards."""
    if "gf_full" in ctx.state:
        return ctx.state["gf_full"]
    from quill.core.wordpress import gravity_build as gb
    from quill.core.wordpress import gravity_build_save as gs

    api = ctx.api(H.ADMIN)
    form = gb.new_form(ctx.title("gravity every field"))
    for kind in gb.FIELD_TYPES:
        values: dict[str, Any] = {
            "label": f"{kind} question",
            "description": f"About the {kind} question",
            "adminLabel": f"{kind}_admin",
            "cssClass": f"quill-{kind}",
        }
        if kind not in gb.DISPLAY_TYPES:
            values["isRequired"] = kind in ("text", "email", "radio")
        if kind in ("text", "textarea", "email", "phone", "number", "website"):
            values["placeholder"] = f"Your {kind}"
        if kind in ("text", "textarea"):
            values["defaultValue"] = f"Default {kind}"
        if kind in gb.CHOICE_TYPES:
            values["choices"] = "Red = r\nGreen = g\nBlue"
        if kind == "html":
            values["content"] = "<p>Read this first.</p>"
        if kind == "consent":
            values["checkboxLabel"] = "I agree to the test"
        if kind == "page":
            values["label"] = ""
        gb.add_field(form, kind, values)
    # A field shown only when the first is "yes", and one that is then removed.
    gb.set_condition(form["fields"][1], gb.Condition("show", "1", "is", "yes"))
    extra = gb.add_field(form, "text", {"label": "Removed before saving"})
    gb.set_condition(form["fields"][2], gb.Condition("show", str(extra["id"]), "is", "x"))
    gone = gb.remove_field(form, len(form["fields"]) - 1)
    H.expect(gone is not None and gone["id"] == extra["id"], "the extra field was not removed")
    H.expect(gb.condition_of(form["fields"][2]) is None, "its logic stayed behind")
    settings = gb.settings_of(form)
    gb.apply_settings(
        form,
        gb.Settings(
            title=settings.title,
            description="Every field QUILL builds",
            button="Send it",
            label_placement="left_label",
            confirmation="Thanks from the QUILL live test.",
            notify_to=NOWHERE,
            notify_subject="QUILL live test {form_title}",
        ),
    )
    _quiet(form)
    saved = gs.create(api, form)
    route = saved.route
    ctx.later(f"delete Gravity Forms form {saved.form_id}", lambda: api.delete(route, force=1))
    H.expect(not saved.problems, "; ".join(saved.problems))
    ctx.state["gf_full"] = {"saved": saved, "sent": form, "route": route}
    return ctx.state["gf_full"]


def _every_field(ctx: Any) -> str:
    from quill.core.wordpress import gravity_build as gb

    _need(ctx)
    made = _full_form(ctx)
    stored = ctx.api(H.ADMIN).get(made["route"])
    by_type = {str(f.get("type")): f for f in stored.get("fields", []) if isinstance(f, dict)}
    missing = [k for k in gb.FIELD_TYPES if k not in by_type]
    H.expect(not missing, f"not stored: {missing}")
    wrong = []
    for kind, field in by_type.items():
        if field.get("cssClass") != f"quill-{kind}":
            wrong.append(f"{kind} cssClass {field.get('cssClass')!r}")
        if kind != "page" and field.get("adminLabel") != f"{kind}_admin":
            wrong.append(f"{kind} adminLabel {field.get('adminLabel')!r}")
        if kind in ("text", "textarea", "email", "phone", "number", "website"):
            if field.get("placeholder") != f"Your {kind}":
                wrong.append(f"{kind} placeholder {field.get('placeholder')!r}")
        if kind in gb.CHOICE_TYPES:
            values = [str(c.get("value")) for c in field.get("choices") or []]
            if values != ["r", "g", "Blue"]:
                wrong.append(f"{kind} choices {values}")
    if by_type["consent"].get("checkboxLabel") != "I agree to the test":
        wrong.append(f"consent text {by_type['consent'].get('checkboxLabel')!r}")
    if "Read this first" not in str(by_type["html"].get("content")):
        wrong.append("html content")
    if not by_type["text"].get("isRequired") or by_type["textarea"].get("isRequired"):
        wrong.append("required flags")
    back = gb.settings_of(stored)
    if (back.button, back.label_placement, back.description) != (
        "Send it",
        "left_label",
        "Every field QUILL builds",
    ):
        wrong.append(f"settings {back}")
    if back.confirmation != "Thanks from the QUILL live test.":
        wrong.append(f"confirmation {back.confirmation!r}")
    if back.notify_to != NOWHERE:
        wrong.append(f"notification to {back.notify_to!r}")
    logic = gb.condition_of(stored["fields"][1])
    H.expect(isinstance(logic, gb.Condition), f"the condition did not survive: {logic!r}")
    H.expect(not wrong, "; ".join(wrong))
    return (
        f"form {made['saved'].form_id}: {len(by_type)} field types, each with label, "
        "description, admin label, CSS class and (where it has them) placeholder, default, "
        "required, choices with values, content and consent text; settings, confirmation and "
        "notification read back; a removed field took its logic with it"
    )


def _entry(api: Any, entry_id: str | int) -> dict[str, Any]:
    raw = api.get(f"{NS}/entries/{entry_id}")
    return raw if isinstance(raw, dict) else {}


def _sent_entry(ctx: Any) -> str:
    """A test entry to the full form, made once a run (Test This Form's path)."""
    if "gf_entry" in ctx.state:
        return ctx.state["gf_entry"]
    from quill.core.wordpress import workbench_gravity_submit as submitting

    api = ctx.api(H.ADMIN)
    made = _full_form(ctx)
    form = api.get(made["route"])
    inputs, skipped = submitting.sample_inputs(form)
    values = {i.name: i.value for i in inputs}
    first = next(f for f in form["fields"] if f.get("type") == "text")
    values[f"input_{first['id']}"] = "yes"  # so the field shown on "yes" is asked
    checked = submitting.submit(api, str(made["saved"].form_id), values, validate_only=True)
    H.expect(checked.valid, "validation refused: " + "; ".join(checked.lines({})))
    answer = submitting.submit(api, str(made["saved"].form_id), values, validate_only=False)
    H.expect(answer.valid and answer.entry_id, f"submitted: {answer}")
    entry_id = answer.entry_id
    ctx.later(f"delete entry {entry_id}", lambda: api.delete(f"{NS}/entries/{entry_id}", force=1))
    ctx.state["gf_entry"] = entry_id
    ctx.state["gf_entry_inputs"] = (values, skipped)
    return entry_id


def _test_form(ctx: Any) -> str:
    from quill.core.wordpress import workbench_gravity_answers as gfa

    _need(ctx)
    api = ctx.api(H.ADMIN)
    made = _full_form(ctx)
    entry_id = _sent_entry(ctx)
    values, skipped = ctx.state["gf_entry_inputs"]
    entry = _entry(api, entry_id)
    form = api.get(made["route"])
    labels = gfa.answer_labels(form)
    empty = [
        labels.get(name.removeprefix("input_").replace("_", "."), name)
        for name in values
        if not str(entry.get(name.removeprefix("input_").replace("_", "."), "") or "")
    ]
    H.expect(not empty, f"sent but not in the entry: {empty}")
    answered = {
        str(f.get("type"))
        for f in form["fields"]
        if any(str(k).split(".")[0] == str(f.get("id")) and entry.get(k) for k in entry)
    }
    unanswered = [
        str(f.get("type"))
        for f in form["fields"]
        if f.get("type") not in ("html", "section", "page") and str(f.get("type")) not in answered
    ]
    H.expect(not unanswered, f"Test This Form left these field types empty: {unanswered}")
    # Ctrl+Z, as Submit a Test Entry records it: the entry moves to the Trash.
    api.delete(f"{NS}/entries/{entry_id}")
    H.expect(_entry(api, entry_id).get("status") == "trash", "Ctrl+Z did not trash the entry")
    api.request("PUT", f"{NS}/entries/{entry_id}", json_body={**entry, "status": "active"})
    return (
        f"entry {entry_id}: {len(values)} inputs sent, every answerable field type answered "
        f"({len(answered)}), {len(skipped)} skipped; Ctrl+Z moved it to the Trash "
        "(brought back for 146)"
    )


def _entries(ctx: Any) -> str:
    from quill.core.wordpress import workbench_gravity as gravity
    from quill.core.wordpress import workbench_gravity_answers as gfa
    from quill.core.wordpress.workbench_edit import EditConflict
    from quill.core.wordpress.workbench_forms import load_forms, set_entry_spam

    _need(ctx)
    api = ctx.api(H.ADMIN)
    made = _full_form(ctx)
    entry_id = _sent_entry(ctx)
    route = f"{NS}/entries/{entry_id}"
    entry = _entry(api, entry_id)
    text_id = str(next(f["id"] for f in made["sent"]["fields"] if f.get("type") == "textarea"))
    old = str(entry.get(text_id, ""))
    was = gfa.set_answers(
        api,
        route,
        seen={text_id: old},
        changed={text_id: "Changed in QUILL"},
        seen_updated=str(entry.get("date_updated", "")),
    )
    H.expect(_entry(api, entry_id).get(text_id) == "Changed in QUILL", "the answer did not change")
    try:  # the same change from the copy read before is stale now
        gfa.set_answers(api, route, seen={text_id: old}, changed={text_id: "Again"})
        stale = False
    except EditConflict:
        stale = True
    H.expect(stale, "a stale change was sent over the newer answer")
    gfa.set_answers(api, route, seen={text_id: "Changed in QUILL"}, changed=was)
    H.expect(_entry(api, entry_id).get(text_id) == old, "Ctrl+Z did not put the answer back")
    site = _site_ctx(ctx)
    rows = [r for r in load_forms(site, "entries") if r.key == str(entry_id)]
    H.expect(rows, f"entry {entry_id} is not under Responses")
    H.expect(not set_entry_spam(site, rows, True), "Spam failed")
    H.expect(_entry(api, entry_id).get("status") == "spam", "not held as spam")
    held = [r for r in load_forms(site, "spam") if r.key == str(entry_id)]
    H.expect(held, "not under Held as Spam")
    H.expect(not set_entry_spam(site, held, False), "Not Spam failed")
    H.expect(_entry(api, entry_id).get("status") == "active", "Not Spam left it held")
    gravity.add_note(api, int(entry_id), f"{H.TAG} note", ctx.accounts.get(H.ADMIN))
    notes = gravity.read_notes(api, int(entry_id))
    H.expect(any(H.TAG in n.text for n in notes), f"notes: {gravity.note_lines(notes)}")
    was_read = gravity.set_entry_flag(api, route, "is_read", True)
    H.expect(gravity.truthy(_entry(api, entry_id).get("is_read")), "not marked read")
    gravity.set_entry_flag(api, route, "is_read", was_read)
    H.expect(gravity.truthy(_entry(api, entry_id).get("is_read")) == was_read, "Read not put back")
    after = _entry(api, entry_id)
    H.expect(after.get(text_id) == old, "another change lost the answer")
    return (
        f"entry {entry_id}: an answer changed, a stale change refused, put back; Spam and Not "
        f"Spam through the Workbench rows; {len(notes)} note added and read; Read and back"
    )


def _site_ctx(ctx: Any) -> Any:
    from quill.core.wordpress.site import load_account, load_site_info
    from quill.core.wordpress.workbench_load import SiteContext

    api = ctx.api(H.ADMIN)
    key = f"wb_info_{H.ADMIN}"
    if key not in ctx.state:
        ctx.state[key] = load_site_info(api)
    if H.ADMIN not in ctx.accounts:
        ctx.accounts[H.ADMIN] = load_account(api)
    return SiteContext(
        H.SITE_NAME, api, url=H.SITE_URL, account=ctx.accounts[H.ADMIN], info=ctx.state[key]
    )


def _messages(ctx: Any) -> str:
    from quill.core.wordpress import gravity_build_save as gs
    from quill.core.wordpress import gravity_messages as gm
    from quill.core.wordpress import workbench_gravity as gravity

    _need(ctx)
    api = ctx.api(H.ADMIN)
    made = _full_form(ctx)
    route = made["route"]
    opened = api.get(route)
    edited = copy.deepcopy(opened)
    note = gm.add_notification(edited, f"{H.TAG} notice", NOWHERE, "Test", "{all_fields}")
    thanks = gm.add_confirmation(edited, f"{H.TAG} thanks", "Thank you.")
    first = gs.update(api, route, opened, edited)
    H.expect(not first.problems, "; ".join(first.problems))
    opened = api.get(route)
    edited = copy.deepcopy(opened)
    mine = {m.name: m for m in gm.others(edited)}
    H.expect(note.name in mine and thanks.name in mine, f"added, then read back: {list(mine)}")
    changed = gm.change(mine[note.name], {"subject": "Changed subject"})
    changed += gm.change(mine[thanks.name], {"message": "Thank you, changed."})
    off = gm.toggle(mine[thanks.name])
    H.expect(changed == ["subject", "message"] and off is False, f"{changed}, on={off}")
    gs.update(api, route, opened, edited)
    stored = api.get(route)
    back = {m.name: m for m in gm.others(stored)}
    H.expect(back[note.name].record.get("subject") == "Changed subject", "subject not saved")
    H.expect(
        gravity.truthy(back[thanks.name].record.get("isActive", True)) is False,
        "the confirmation is still on",
    )
    said = gm.spoken(back[note.name])
    # Resend Notifications, to the address nobody receives at, then the record removed.
    entry_id = _sent_entry(ctx)
    entry = _entry(api, entry_id)
    listed = gravity.entry_notifications(stored, entry)
    target = [n for n in listed if n.name == note.name]
    H.expect(target and NOWHERE in target[0].recipients, f"preview: {[n.line for n in listed]}")
    sent = gravity.resend_notifications(api, int(entry_id), [target[0].id])
    opened = api.get(route)
    edited = copy.deepcopy(opened)
    for message in gm.others(edited):
        if message.name in (note.name, thanks.name):
            gm.remove(edited, message)
    gs.update(api, route, opened, edited)
    left = [m.name for m in gm.others(api.get(route))]
    H.expect(note.name not in left and thanks.name not in left, f"still there: {left}")
    return (
        f"added, changed, turned off and removed, each read back ({said}); Resend Notifications "
        f"previewed as {H.cell(target[0].line, 70)} and sent ({len(sent)} sent, to "
        "example.invalid)"
    )


def _to_qaf(ctx: Any) -> str:
    from quill.core.forms import model as M
    from quill.core.forms import qaf_site
    from quill.core.forms.bfl_write import to_bfl
    from quill.core.wordpress import gravity_qaf_entries as ge
    from quill.core.wordpress.gravity_qaf import to_qaf

    _need(ctx)
    if not qaf_site.supports_qaf(ctx.api(H.ADMIN)):
        raise H.NotRun("skipped: QUILL Accessible Forms not installed")
    api = ctx.api(H.ADMIN)
    made = _full_form(ctx)
    entry_id = _sent_entry(ctx)
    form = api.get(made["route"])
    converted = to_qaf(form)
    problems = M.validate(converted.form)
    H.expect(not problems, f"not a valid QAF model: {problems[:2]}")
    body = qaf_site.publish_body(converted.form, str(to_bfl(converted.form)), status="draft")
    namespace = qaf_site.site_namespace(api) or qaf_site.NAMESPACE
    answer = api.request("POST", f"{namespace}/forms", json_body=body).payload
    target = qaf_site.form_from_payload(answer)
    ctx.later(f"delete QAF form {target.id}", lambda: api.delete(f"{namespace}/forms/{target.id}"))
    ctx.state["gf_qaf"] = target.id
    site_copy = qaf_site.get_form(api, target.id)
    labels = list(site_copy.question_labels().values())
    asked = [
        f.get("label") for f in form["fields"] if f.get("type") not in ("html", "section", "page")
    ]
    lost_q = [q for q in asked if q not in labels]
    H.expect(not lost_q, f"questions not in the QAF draft: {lost_q} (have {labels})")
    entries = ge.read_gravity_entries(api, str(made["saved"].form_id))
    plan = ge.plan_copy(
        form, entries, target.id, site_copy.title, site_copy.model(), namespace=namespace
    )
    H.expect(plan.copies, "no entries planned")
    outcomes, copied = ge.send_copies(api, H.SITE_NAME, plan)
    for new_id in copied:
        ctx.later(
            f"delete QAF entry {new_id}", lambda n=new_id: api.delete(f"{namespace}/entries/{n}")
        )
    H.expect(copied and all(o.ok for o in outcomes), f"copies: {[o.words for o in outcomes]}")
    copy_back = qaf_site.response_from_payload(api.get(f"{namespace}/entries/{copied[0]}"))
    H.expect(len(copy_back.answers) >= 5, f"the copy has {len(copy_back.answers)} answers")
    for new_id in copied:  # Ctrl+Z on the copies: QAF's Trash
        api.delete(f"{namespace}/entries/{new_id}")
    return (
        f"QAF draft {target.id} from Gravity form {made['saved'].form_id}: {len(labels)} "
        f"questions, {len(converted.lost)} things QAF cannot carry; entry {entry_id} copied as "
        f"QAF entry {copied[0]} with {len(copy_back.answers)} answers"
        + (f" (left out: {', '.join(plan.copies[0].lost)})" if plan.copies[0].lost else "")
        + "; the copies undone"
    )


def _to_gravity(ctx: Any) -> str:
    from quill.core.forms import qaf_site
    from quill.core.wordpress import gravity_build as gb
    from quill.core.wordpress import gravity_build_save as gs
    from quill.core.wordpress.gravity_qaf import to_gravity

    _need(ctx)
    api = ctx.api(H.ADMIN)
    if "gf_qaf" not in ctx.state:
        _to_qaf(ctx)
    source = qaf_site.get_form(api, int(ctx.state["gf_qaf"]))
    model = source.model()
    H.expect(model is not None, "QAF did not send the form's model")
    converted = to_gravity(model)
    converted.form["title"] = ctx.title("copied back to Gravity Forms")
    _quiet(converted.form)
    saved = gs.create(api, converted.form)
    route = saved.route
    ctx.later(f"delete Gravity Forms form {saved.form_id}", lambda: api.delete(route, force=1))
    H.expect(not saved.problems, "; ".join(saved.problems))
    stored = api.get(route)
    asked = list(source.question_labels().values())
    have = [str(f.get("label")) for f in gb.fields_of(stored)]
    missing = [q for q in asked if q not in have]
    H.expect(not missing, f"not carried back: {missing}")
    return (
        f"Gravity form {saved.form_id} from QAF form {source.id}: {len(have)} fields, every QAF "
        f"question carried; {len(converted.lost)} things Gravity Forms cannot carry"
    )


def _watch(ctx: Any) -> str:
    from quill.core.wordpress import workbench_gravity_submit as submitting
    from quill.core.wordpress import workbench_watches as wt

    _need(ctx)
    api = ctx.api(H.ADMIN)
    made = _full_form(ctx)
    sites = [(H.SITE_NAME, api, list(ctx.index.namespaces))]
    state = wt.WatchState()
    first = wt.check(sites, state, ["form_response"], now=lambda: 1e9)
    H.expect(first == [], f"the first look spoke: {first}")
    before = wt._newest_entry(api, list(ctx.index.namespaces))
    form = api.get(made["route"])
    inputs, _skipped = submitting.sample_inputs(form)
    values = {i.name: i.value for i in inputs}
    answer = submitting.submit(api, str(made["saved"].form_id), values, validate_only=False)
    H.expect(answer.valid and answer.entry_id, f"submitted: {answer}")
    entry_id = answer.entry_id
    ctx.later(f"delete entry {entry_id}", lambda: api.delete(f"{NS}/entries/{entry_id}", force=1))
    after = wt._newest_entry(api, list(ctx.index.namespaces))
    H.expect(after > before, f"the number the Watch compares did not grow ({before} to {after})")
    news = wt.check(sites, state, ["form_response"], now=lambda: 1e9 + 1000)
    H.expect(any("new form response" in s for s in news), f"the Watch said: {news}")
    again = wt.check(sites, state, ["form_response"], now=lambda: 1e9 + 2000)
    H.expect(again == [], f"said twice: {again}")
    return f"first look silent; entry {entry_id} raised it {before} to {after}; then: {news[0]}"


_TESTS: tuple[tuple[str, str, Any, str, bool], ...] = (
    (
        "144",
        "Gravity Forms: every field type and property, settings, read back",
        _every_field,
        "ADMIN",
        True,
    ),
    ("145", "Gravity Forms: Test This Form answers every field; Ctrl+Z", _test_form, "ADMIN", True),
    (
        "146",
        "Gravity Forms: change an entry's answers, Spam, notes, Read",
        _entries,
        "ADMIN",
        True,
    ),
    (
        "147",
        "Gravity Forms: notifications and confirmations changed, off, removed; resend",
        _messages,
        "ADMIN",
        True,
    ),
    (
        "148",
        "Gravity Forms to QAF: Copy as a QAF form, Copy Old Entries, undone",
        _to_qaf,
        "ADMIN",
        True,
    ),
    ("149", "QAF to Gravity Forms: Copy as a Gravity Form", _to_gravity, "ADMIN", True),
    ("150", "Gravity Forms: Watch hears a new entry once", _watch, "ADMIN", True),
)
