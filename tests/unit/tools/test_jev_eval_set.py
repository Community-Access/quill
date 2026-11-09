"""The live Jev evaluation set is current, and every hand case names a real command.

A hand case that names an id the app does not offer would be counted as Jev's
miss when it is the test's mistake, so the ids are checked here, offline.
"""

from __future__ import annotations

from quill.core.command_catalogue import rows_for_app
from quill.tools import build_jev_eval_set as tool
from quill.tools.jev_eval_cases import cases_for


def test_the_eval_set_is_current() -> None:
    assert tool.main(["--check"]) == 0, "run: python -m quill.tools.build_jev_eval_set --write"


def test_every_hand_case_names_an_offered_command() -> None:
    for app in tool.APPS:
        offered = {spec.id for spec in rows_for_app(app) if spec.offered}
        for category, cases in cases_for(app).items():
            for case in cases:
                extra = case[2] if len(case) > 2 else {}  # type: ignore[misc]
                ids = [case[1], *extra.get("recent", ()), *extra.get("last_offer", ())]
                ids += list(extra.get("disabled", ()))
                unknown = [item for item in ids if item != "none" and item not in offered]
                assert not unknown, (app, category, case[0], unknown)
