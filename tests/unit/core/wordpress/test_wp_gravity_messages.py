"""A Gravity Form's other notifications and confirmations (complete.md 2.3, Forms)."""

from __future__ import annotations

from copy import deepcopy

from quill.core.wordpress import gravity_messages as gm
from quill.core.wordpress.gravity_build import new_form
from quill.core.wordpress.gravity_build_save import change_lines


def _form() -> dict:
    form = new_form("Tickets")
    form["notifications"]["routed"] = {
        "id": "routed", "name": "By answer", "isActive": True, "toType": "routing",
        "routing": [{"fieldId": "3", "operator": "is", "value": "Yes", "email": "a@b.c"}],
    }  # fmt: skip
    return form


def test_the_others_leave_out_what_the_editor_changes() -> None:
    names = [m.name for m in gm.others(_form())]
    assert names == ["By answer"]  # not the Admin Notification, not the default confirmation


def test_add_change_toggle_and_remove_are_previewed_as_lines() -> None:
    before = _form()
    after = deepcopy(before)
    note = gm.add_notification(after, "Ticket email", "{Email:3}", "Your ticket", "{all_fields}")
    thanks = gm.add_confirmation(after, "Thanks for buying", "See you there.")
    routed = next(m for m in gm.others(after) if m.name == "By answer")
    assert (
        not routed.simple
        and gm.spoken(routed) == "By answer, notification, routed in Gravity Forms, on"
    )
    assert gm.toggle(routed) is False
    lines = change_lines(before, after)
    assert "Add the notification Ticket email." in lines
    assert "Add the confirmation Thanks for buying." in lines
    assert "Turn the notification By answer off." in lines
    assert gm.change(note, {"subject": "Your ticket is here"}) == ["subject"]
    gm.remove(after, thanks)
    assert [m.name for m in gm.others(after)] == ["By answer", "Ticket email"]
    assert routed.record["routing"]  # routing kept untouched


def test_a_list_kept_by_an_older_export_is_kept_by_id() -> None:
    form = new_form("Old")
    form["notifications"] = list(form["notifications"].values())
    gm.add_notification(form, "Second", "x@y.z", "Hi", "")
    assert isinstance(form["notifications"], dict) and len(form["notifications"]) == 2
