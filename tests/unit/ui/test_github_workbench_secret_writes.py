"""A secret typed in the GitHub Workbench is masked, previewed as hidden, sent once, then gone.

The Properties sheet's New value box (an Actions secret), the preview before a
save, and New Here / Change on a secrets list (the resource engine). The core
half, sealing and visibility, is in
``tests/unit/core/github_workbench/test_secrets_write_only.py``.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.github.sheet_catalog import SHEETS, Target  # noqa: E402
from quill.core.workbench.properties import FieldChange  # noqa: E402
from quill.ui.github_workbench_properties import GitHubWorkbenchPropertiesMixin  # noqa: E402
from quill.ui.spoken_name import spoken_name  # noqa: E402
from quill.ui.workbench_properties_sheet import PropertiesSheet  # noqa: E402
from tests.unit.ui.test_github_workbench_resources import REF, _Window  # noqa: E402

VALUE = "hunter2-do-not-say"


def _sheet(applied: list[Any]) -> PropertiesSheet:
    frame = wx.Frame(None)
    return PropertiesSheet(
        frame,
        SHEETS["secret"].sheet,
        {"name": "TOKEN", "created": "2026-11-01", "secret_value": VALUE},
        title="Secret TOKEN Properties - o/r",
        copy_text=lambda _t: None,
        on_apply=lambda changes, close: applied.append(list(changes)),
    )


def test_the_new_value_box_is_masked_empty_and_named_hidden(wx_session_app) -> None:
    sheet = _sheet([])
    box = sheet.controls["secret_value"]
    assert box.GetWindowStyleFlag() & wx.TE_PASSWORD
    assert box.GetValue() == ""  # never filled in, even from a value it was handed
    assert spoken_name(box) == "New value, hidden as you type"
    assert "New value: hidden" in sheet.text() and VALUE not in sheet.text()
    sheet.dialog.GetParent().Destroy()


def test_a_saved_value_leaves_the_box_and_the_sheet(wx_session_app) -> None:
    applied: list[Any] = []
    sheet = _sheet(applied)
    sheet.controls["secret_value"].ChangeValue(VALUE)
    sheet.apply(close=False)
    assert [(c.key, c.after) for c in applied[0]] == [("secret_value", VALUE)]
    sheet.saved(
        {"name": "TOKEN", "secret_value": ""}, "Secret TOKEN: new value (set).", close=False
    )
    assert sheet.controls["secret_value"].GetValue() == ""
    assert "secret_value" not in sheet.state.loaded
    assert sheet.pending() == []  # nothing left to send again
    sheet.dialog.GetParent().Destroy()


def test_the_preview_before_saving_says_hidden_never_the_value() -> None:
    previews: list[str] = []
    host = SimpleNamespace(
        tier_of=lambda target, changes: GitHubWorkbenchPropertiesMixin.tier_of(
            host, target, changes
        ),
        confirm_tier=lambda tier, words, name: previews.append(words) or False,
        _say=lambda _t: None,
    )
    target = Target("secret", {"repo": "o/r", "name": "TOKEN"})
    changes = [FieldChange("secret_value", "New value", "", VALUE)]
    GitHubWorkbenchPropertiesMixin._apply_one(host, target, {}, changes, {}, None, False)  # type: ignore[arg-type]
    assert previews and VALUE not in previews[0] and "New value to (hidden)" in previews[0]


def test_a_batch_preview_of_secrets_says_hidden(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.github.batch import BatchItem

    previews: list[str] = []
    host = SimpleNamespace(
        tier_of=lambda target, changes: GitHubWorkbenchPropertiesMixin.tier_of(
            host, target, changes
        ),
        confirm_tier=lambda tier, words, name: previews.append(words) or False,
    )
    items = [BatchItem("TOKEN", {"repo": "o/r", "name": n}, {}) for n in ("A", "B")]
    changes = [FieldChange("secret_value", "New value", "", VALUE)]
    GitHubWorkbenchPropertiesMixin._apply_many(  # type: ignore[arg-type]
        host, "secret", "secrets", items, changes, {}, None, False
    )
    assert previews and VALUE not in previews[0] and "(hidden)" in previews[0]


def test_new_here_drops_the_typed_value_once_it_is_sent(monkeypatch) -> None:
    from quill.core.github import resource_engine

    seen: list[dict[str, str]] = []
    real = resource_engine.create

    def create(api: Any, spec: Any, target: str, answers: dict[str, str]) -> str:
        seen.append(answers)
        return real(api, spec, target, answers)

    monkeypatch.setattr(resource_engine, "create", create)
    window = _Window("actions_secrets", [], ["TOKEN"], secret=VALUE)
    window._do_resource_new(REF, None)
    assert window.api.sent[-1][1] == "/repos/o/r/actions/secrets/TOKEN"
    assert seen and "value" not in seen[0] and seen[0]["name"] == "TOKEN"
    assert all(VALUE not in said for said in window.said)


def test_change_on_an_organization_secret_can_keep_its_value(monkeypatch) -> None:
    from quill.core.github.resource_engine import fetch
    from quill.core.github.resource_specs import spec_for

    window = _Window("org_actions_secrets", [2], [], secret="")
    window.api.data = {"secrets": [{"name": "TOKEN", "visibility": "all"}]}
    row = fetch(window.api, spec_for("org_actions_secrets"), "acme")[0]
    assert window._fits_resource_edit(row)
    window._do_resource_edit(SimpleNamespace(instance="acme"), row)
    assert window.api.sent[-1] == (
        "PUT",
        "/orgs/acme/actions/secrets/TOKEN",
        {"visibility": "selected"},
    )


def test_change_on_a_repository_secret_needs_a_value() -> None:
    from quill.core.github.resource_engine import fetch
    from quill.core.github.resource_specs import spec_for

    window = _Window("actions_secrets", [], [], secret="")
    window.api.data = {"secrets": [{"name": "TOKEN"}]}
    row = fetch(window.api, spec_for("actions_secrets"), "o/r")[0]
    sent = len(window.api.sent)
    window._do_resource_edit(REF, row)
    assert len(window.api.sent) == sent  # an empty password box is a cancel here
