"""Every quick command, and the tables the Workbench reads from them.

:data:`QUICK` is :mod:`quick_table_actions`, :mod:`quick_table_repo` and
:mod:`quick_table_org`, :mod:`quick_table_discuss`, :mod:`quick_table_projects`,
:mod:`quick_table_agents`, :mod:`quick_table_security`, :mod:`quick_table_copilot`
and :mod:`quick_table_you` together. From it come the menu rows
(:data:`QUICK_ROWS`, merged into ``item_actions``), what each write needs
(:data:`QUICK_REQUIREMENTS`, merged into ``write_requirements``), the live
run's reasons (:data:`QUICK_LIVE`) and the API coverage rows each answers
(:data:`QUICK_ENDPOINTS`). wx-free and strict-typed.
"""

from __future__ import annotations

from quill.core.github.permissions import WriteTier
from quill.core.github.quick_actions import Quick
from quill.core.github.quick_table_actions import ACTIONS_QUICK
from quill.core.github.quick_table_agents import AGENT_QUICK
from quill.core.github.quick_table_copilot import COPILOT_QUICK
from quill.core.github.quick_table_discuss import DISCUSS_QUICK
from quill.core.github.quick_table_org import ORG_QUICK
from quill.core.github.quick_table_projects import PROJECT_QUICK
from quill.core.github.quick_table_repo import REPO_QUICK
from quill.core.github.quick_table_security import SECURITY_QUICK
from quill.core.github.quick_table_you import YOU_QUICK
from quill.core.workbench.actions import ActionRow, Tier

__all__ = ["QUICK", "QUICK_ENDPOINTS", "QUICK_LIVE", "QUICK_REQUIREMENTS", "QUICK_ROWS"]

QUICK: tuple[Quick, ...] = (
    *ACTIONS_QUICK,
    *REPO_QUICK,
    *ORG_QUICK,
    *DISCUSS_QUICK,
    *PROJECT_QUICK,
    *AGENT_QUICK,
    *SECURITY_QUICK,
    *COPILOT_QUICK,
    *YOU_QUICK,
)

_P = "github.workbench."
_MENU_TIER = {"": Tier.READ, "O": Tier.ORGANIZE, "V": Tier.WRITE, "A": Tier.WRITE}
_WRITE_TIER = {
    "O": WriteTier.ORGANIZING,
    "V": WriteTier.VISIBLE,
    "A": WriteTier.ACCESS,
    "D": WriteTier.DESTRUCTIVE,
}
#: write_requirements' needs, in the menu's shorter words.
_MENU_NEED = {"repo:admin": "admin", "repo:write": "push", "repo:triage": "triage"}


def _menu_row(q: Quick) -> ActionRow:
    need = _MENU_NEED.get(q.need, "sign_in" if q.writes else "")
    return ActionRow(
        f"{_P}{q.verb}", q.label, _MENU_TIER.get(q.tier, Tier.DESTRUCTIVE), need, q.help
    )


def _rows() -> dict[str, tuple[ActionRow, ...]]:
    out: dict[str, list[ActionRow]] = {}
    for q in QUICK:
        for row_type in q.menu:
            out.setdefault(row_type, []).append(_menu_row(q))
    return {row_type: tuple(rows) for row_type, rows in out.items()}


QUICK_ROWS: dict[str, tuple[ActionRow, ...]] = _rows()
QUICK_REQUIREMENTS: dict[str, tuple[str, WriteTier]] = {
    f"{_P}{q.verb}": (q.need or "sign_in", _WRITE_TIER[q.tier]) for q in QUICK if q.writes
}
QUICK_LIVE: dict[str, str] = {q.verb: q.live for q in QUICK if q.writes}
#: Coverage rows by their table key: "GET /path" for REST, the bare name for GraphQL.
QUICK_ENDPOINTS: dict[str, str] = {
    endpoint.removeprefix("graphql:"): f"command:{_P}{q.verb}"
    for q in QUICK
    for endpoint in q.endpoints
}
