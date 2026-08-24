"""11.2: a dimmed verb must say which state dimmed it.

Both apps dim on purpose -- Mark All as Played with nothing unheard, Remove
All Downloads with nothing downloaded, Analyse Chapters on an episode whose
bytes are not here. A dimmed item teaches that state only if it *says* the
state, so the rule is: every action built with ``enabled=False`` carries a
``reason``.

The check is a source scan rather than a live build, because both action
tables are big, state-dependent and built against a live dialog: the scan
sees every branch, including the ones a fixture would have to conjure a show
with no feed address to reach.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from quill.core import dimmed_reason
from quill.core.radio.row_actions import RowAction
from quill.ui.podcasts.manager_menus import ResolvedAction

REPO = Path(__file__).resolve().parents[3]

#: Where dimmable actions are constructed, and the constructor to look for.
_TABLES: tuple[tuple[str, str], ...] = (
    ("quill/core/radio/row_actions.py", "RowAction"),
    ("quill/ui/podcasts/manager_menus.py", "action"),
)


def _dimmable_calls(path: Path, func_name: str) -> list[ast.Call]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
        if name != func_name:
            continue
        if any(kw.arg == "enabled" for kw in node.keywords):
            out.append(node)
    return out


@pytest.mark.parametrize(("module", "func_name"), _TABLES)
def test_every_conditionally_enabled_action_carries_a_reason(module: str, func_name: str) -> None:
    path = REPO / module
    offenders = []
    for call in _dimmable_calls(path, func_name):
        enabled = next(kw for kw in call.keywords if kw.arg == "enabled")
        # `enabled=True` is not a dimmable site -- it is a default spelled out.
        if isinstance(enabled.value, ast.Constant) and enabled.value.value is True:
            continue
        if not any(kw.arg == "reason" for kw in call.keywords):
            offenders.append(f"{module}:{call.lineno}")
    assert offenders == [], (
        "These actions can dim with nothing to say. Give each a reason from "
        "quill.core.dimmed_reason: " + ", ".join(offenders)
    )


def test_explain_reads_as_one_sentence() -> None:
    assert (
        dimmed_reason.explain(
            "Download All 40 Episo&des...\tCtrl+3", dimmed_reason.nothing_to_download(40)
        )
        == "Download All 40 Episodes: nothing to download, all 40 are already here."
    )


def test_explain_has_an_honest_floor_with_no_reason() -> None:
    assert dimmed_reason.explain("&Unsubscribe", "") == "Unsubscribe is not available right now."
    assert dimmed_reason.explain("", "") == "This command is not available right now."


def test_reasons_are_lower_case_clauses_without_a_full_stop() -> None:
    """The wording rule, enforced: explain() supplies the capital and the stop."""
    builders = [
        dimmed_reason.nothing_unheard(3),
        dimmed_reason.nothing_unheard(),
        dimmed_reason.nothing_to_download(40),
        dimmed_reason.nothing_to_download(0),
        dimmed_reason.no_episodes_yet(),
        dimmed_reason.nothing_downloaded(),
        dimmed_reason.already_downloaded(),
        dimmed_reason.download_in_flight(),
        dimmed_reason.not_downloaded("analyse"),
        dimmed_reason.no_show_notes(),
        dimmed_reason.no_chapters(),
        dimmed_reason.no_feed_address(),
        dimmed_reason.not_routed_to_inbox(),
        dimmed_reason.safe_mode(),
    ]
    for reason in builders:
        assert reason, "a reason may not be empty"
        assert not reason.endswith("."), reason
        first = reason.split()[0]
        assert first == first.lower() or first in ("Safe",), reason


def test_both_action_types_can_say_why_they_are_dimmed() -> None:
    row = RowAction("download.all", "Download All Episo&des...", enabled=False, reason="x y")
    assert row.unavailable_sentence() == "Download All Episodes: x y."
    resolved = ResolvedAction("download", "&Download Episode", False, lambda: None, "z")
    assert resolved.unavailable_sentence() == "Download Episode: z."


def test_an_enabled_action_still_answers_without_crashing() -> None:
    row = RowAction("play", "&Play")
    assert row.unavailable_sentence() == "Play is not available right now."
