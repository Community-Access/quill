"""Every Workbench write is held to the account's level, once, before anything is read or sent.

GitHub PRD 18.3.1 and 18.4 (GH-R-060 to GH-R-066), complete.md's "Verify
per-account Read Only/Organize/Full, Safe Mode, tiers, typed confirmations,
self-lockout prevention and permission explanations". The check is
quill.core.github.write_gate, asked by ``GitHubWorkbenchProvider.run`` (the
one dispatcher every menu row, context-menu row, key, Do Something and
Command Key reach), by ``_run_editor`` (editor commands the Workbench runs),
by a sheet list's buttons and by a Properties sheet's save.

These tests run the real provider with everything after the check replaced by
recorders, and with a GitHub that fails if anything touches it: a refusal
proves nothing was read or sent, and an allowed command proves it went on.
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

pytest.importorskip("wx")

from quill.core.github.item_actions import GITHUB_ACTIONS  # noqa: E402
from quill.core.github.permissions import AccessLevel, AccessStore, WriteTier  # noqa: E402
from quill.core.github.sheet_catalog import Target  # noqa: E402
from quill.core.github.workbench_window_menu import WINDOW_MENU  # noqa: E402
from quill.core.github.write_gate import gated_commands  # noqa: E402
from quill.core.github.write_requirements import EDITOR_READS, EDITOR_REQUIREMENTS  # noqa: E402
from quill.core.workbench.menus import all_rows  # noqa: E402
from quill.core.workbench.properties import FieldChange  # noqa: E402
from quill.ui.github_workbench_window import GitHubWorkbenchProvider  # noqa: E402

_P = "github.workbench."
REF = SimpleNamespace(template="repository", key="issues", instance="o/r")
GATED = gated_commands()
FULL_ONLY = sorted(c for c, tier in GATED.items() if tier > WriteTier.VISIBLE)
ORGANIZE_OK = sorted(c for c, tier in GATED.items() if tier <= WriteTier.VISIBLE)


class _Untouchable:
    """GitHub, as the provider sees it: reading or sending anything fails the test."""

    is_authenticated = True
    token = "test-token"

    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"{name} reached GitHub")


class _Items:
    is_authenticated = True
    token = "test-token"

    def close(self) -> None:
        pass


@pytest.fixture(autouse=True)
def _no_safe_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    monkeypatch.setattr(AccessStore, "load", classmethod(lambda cls, path=None: cls(path)))


def _provider(level: AccessLevel | None) -> tuple[GitHubWorkbenchProvider, list[str], list[str]]:
    """The real dispatcher; *level* None keeps the stored level (Full), so Safe Mode decides."""
    said: list[str] = []
    reached: list[str] = []
    provider = GitHubWorkbenchProvider(_Items(), "o/r", announce=said.append)
    provider.frame = SimpleNamespace()
    provider.items = _Untouchable()
    provider.api = _Untouchable()
    provider._say = said.append  # type: ignore[method-assign]
    provider.account_name = lambda: "me"  # type: ignore[method-assign]
    if level is not None:
        provider.access_level = lambda: level  # type: ignore[method-assign]

    def onward(name: str) -> Any:
        return lambda *args, **_kw: reached.append(name) or True

    provider.run_view = onward("view")  # type: ignore[method-assign]
    provider.run_tool = onward("tool")  # type: ignore[method-assign]
    provider.run_action = onward("action")  # type: ignore[method-assign]
    provider.open_sheet_at = onward("sheet")  # type: ignore[method-assign]
    return provider, said, reached


@pytest.mark.parametrize("command_id", sorted(c for c in GATED if c.startswith(_P)))
def test_every_declared_write_is_refused_at_read_only_and_nothing_is_sent(
    command_id: str,
) -> None:
    provider, said, reached = _provider(AccessLevel.READ_ONLY)
    assert provider.run(command_id, REF, None) is True
    assert reached == []
    assert len(said) == 1
    assert said[0].startswith("Cannot run ") and "this account is Read Only" in said[0]


@pytest.mark.parametrize("command_id", [c for c in FULL_ONLY if c.startswith(_P)])
def test_a_full_only_write_is_refused_at_organize(command_id: str) -> None:
    provider, said, reached = _provider(AccessLevel.ORGANIZE)
    assert provider.run(command_id, REF, None) is True
    assert reached == []
    assert len(said) == 1 and "it needs Full in the Workbench" in said[0]


@pytest.mark.parametrize("command_id", [c for c in ORGANIZE_OK if c.startswith(_P)])
def test_an_organizing_or_visible_write_runs_at_organize(command_id: str) -> None:
    provider, said, reached = _provider(AccessLevel.ORGANIZE)
    provider.run(command_id, REF, None)
    assert said == [] and reached


@pytest.mark.parametrize("command_id", sorted(c for c in GATED if c.startswith(_P)))
def test_every_declared_write_goes_on_at_full(command_id: str) -> None:
    provider, said, reached = _provider(AccessLevel.FULL)
    provider.run(command_id, REF, None)
    assert said == [] and reached


def test_safe_mode_refuses_a_full_account_and_names_safe_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    provider, said, reached = _provider(None)  # stored level Full; Safe Mode overrides it
    provider.run(f"{_P}unlink_branch", REF, None)
    assert reached == []
    assert said == [
        "Cannot run Unlink Branch: it needs Organize in the Workbench, and QUILL is in Safe "
        "Mode, which keeps every account Read Only until QUILL is started normally."
    ]


def test_commands_that_only_read_are_never_refused_even_in_safe_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    every = {row.command_id for _m, row in all_rows(WINDOW_MENU)} | GITHUB_ACTIONS.commands()
    for command_id in sorted(every - set(GATED)):
        provider, said, _reached = _provider(None)
        provider.run(command_id, REF, None)
        assert not any(s.startswith("Cannot run ") for s in said), command_id


def test_an_editor_command_the_workbench_runs_is_held_to_the_level_too() -> None:
    provider, said, _reached = _provider(AccessLevel.ORGANIZE)
    ran: list[str] = []
    provider._editor_command = lambda command_id: ran.append(command_id) or True
    provider._run_editor("github.change_repository_visibility")
    provider._run_editor("github.browse_organization")
    assert ran == ["github.browse_organization"]
    assert said == [
        "Cannot run Change Visibility: it needs Full in the Workbench, and this account is "
        "Organize; Account, Roles and Access, Workbench Level for This Account changes it."
    ]


def test_every_editor_command_the_workbench_offers_is_declared() -> None:
    from quill.ui.github_workbench_actions import _EDITOR_VERBS, REPOSITORY_ACTIONS
    from quill.ui.github_workbench_loaders import ADMIN_ACTIONS

    offered = {c for _label, c in REPOSITORY_ACTIONS if not c.startswith(_P)}
    offered |= {c for rows in ADMIN_ACTIONS.values() for c, _label, _what in rows}
    offered |= set(_EDITOR_VERBS.values())
    undeclared = offered - set(EDITOR_REQUIREMENTS) - EDITOR_READS
    assert undeclared == set()


# -- the doors that do not pass the dispatcher ----------------------------------------


def _sheet_list(rows: tuple[str, ...]) -> dict[str, Any]:
    loaded = SimpleNamespace(values={"collaborators": rows})
    return {"ident": {"repo": "o/r"}, "loaded": loaded}


_REPO = SimpleNamespace(kind="repository", title=lambda: "o/r")


@pytest.mark.parametrize(
    ("key", "verb", "level"),
    [
        ("collaborators", "add", AccessLevel.ORGANIZE),
        ("collaborators", "remove", AccessLevel.ORGANIZE),
        ("branches", "add", AccessLevel.READ_ONLY),
        ("branches", "remove", AccessLevel.READ_ONLY),
    ],
)
def test_a_sheet_lists_buttons_are_held_to_the_level(
    key: str, verb: str, level: AccessLevel
) -> None:
    provider, said, _reached = _provider(level)
    provider._ask_text = lambda *_a, **_k: pytest.fail("asked before the level check")  # type: ignore[method-assign]
    provider._unlink_from = lambda *_a, **_k: pytest.fail("unlinked")  # type: ignore[method-assign]
    provider._create_branch_for = lambda *_a, **_k: pytest.fail("made a branch")  # type: ignore[method-assign]
    act = provider.table_action(
        _REPO if key != "branches" else SimpleNamespace(kind="issue"),
        {
            **_sheet_list(("me, person, admin, direct",)),
            "ident": {"repo": "o/r", "number": "7"},
        },
    )
    act(SimpleNamespace(key=key), verb, "me, person, admin, direct")
    assert len(said) == 1 and said[0].startswith("Cannot run ")


def test_a_properties_save_is_held_to_the_level() -> None:
    provider, said, _reached = _provider(AccessLevel.READ_ONLY)
    provider.confirm_tier = lambda *_a: pytest.fail("previewed before the level check")  # type: ignore[method-assign]
    target = Target("issue", {"repo": "o/r", "number": "42"})
    change = FieldChange("title", "Title", "Old", "New")
    provider._apply_one(target, {}, [change], {}, None, False)
    assert len(said) == 1
    assert said[0].startswith("Cannot save ") and "this account is Read Only" in said[0]


# -- typed confirmation and self-lockout (18.4) --------------------------------------------


class _Dialog:
    def __init__(self, *_a: Any, **_k: Any) -> None:
        pass

    def __enter__(self) -> _Dialog:
        return self

    def __exit__(self, *_a: Any) -> bool:
        return False


class _Api:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def rest(self, method: str, path: str, **_kw: Any) -> Any:
        self.sent.append((method, path))
        return SimpleNamespace(data={})


def _full_provider_with_dialogs(
    monkeypatch: pytest.MonkeyPatch, typed: str
) -> tuple[GitHubWorkbenchProvider, list[str], _Api]:
    import quill.ui.dialog_contract as contract

    provider, said, _reached = _provider(AccessLevel.FULL)
    fake_wx = SimpleNamespace(MessageDialog=_Dialog, OK=4, CANCEL=16, ICON_WARNING=256, ID_OK=5100)
    provider.frame = SimpleNamespace(_wx=fake_wx, frame=None)
    monkeypatch.setattr(contract, "show_modal_dialog", lambda _d, _t: 5100)
    provider._ask_text = lambda *_a, **_k: typed  # type: ignore[method-assign]
    provider._background = lambda _n, work, done: done(work())  # type: ignore[method-assign]
    provider.change_log = lambda: SimpleNamespace(record=lambda **_k: None)  # type: ignore[method-assign]
    api = _Api()
    provider.api = api
    return provider, said, api


_TWO_ADMINS = ("me, person, admin, direct", "bob, person, admin, direct")


@pytest.mark.parametrize(("typed", "sent"), [("1", 1), ("one", 0), ("", 0)])
def test_removing_an_admin_needs_the_count_typed(
    monkeypatch: pytest.MonkeyPatch, typed: str, sent: int
) -> None:
    provider, said, api = _full_provider_with_dialogs(monkeypatch, typed)
    act = provider.table_action(_REPO, _sheet_list(_TWO_ADMINS))
    act(SimpleNamespace(key="collaborators"), "remove", "bob, person, admin, direct")
    assert len(api.sent) == sent
    if typed == "one":
        assert said == ["The name did not match. Nothing changed."]
    elif sent:
        assert said == ["1 done, 0 failed."]


def test_removing_your_own_admin_access_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    provider, said, api = _full_provider_with_dialogs(monkeypatch, "1")
    act = provider.table_action(_REPO, _sheet_list(_TWO_ADMINS))
    act(SimpleNamespace(key="collaborators"), "remove", "me, person, admin, direct")
    assert api.sent == []
    assert said == ["That removes your own admin access. Ask bob to do it if it is what you want."]


def test_lowering_the_last_admin_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    provider, said, api = _full_provider_with_dialogs(monkeypatch, "1")
    provider._choose = lambda *_a: 0  # type: ignore[method-assign]  # "read"
    act = provider.table_action(_REPO, _sheet_list(("me, person, admin, direct",)))
    act(SimpleNamespace(key="collaborators"), "change", "me, person, admin, direct")
    assert api.sent == []
    assert said[0].startswith("That would leave nobody who can manage it, you included.")


# -- a new way round the check fails here ----------------------------------------------------

_UI = Path(__file__).resolve().parents[3] / "quill" / "ui"


def _handler_calls() -> list[tuple[str, str]]:
    """Every direct call of a gated command's ``_do_<verb>`` or ``_tool_<verb>`` in the UI."""
    gated = {c.removeprefix(_P) for c in GATED if c.startswith(_P)}
    found: list[tuple[str, str]] = []
    for path in sorted(_UI.glob("*workbench*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                name = node.func.attr
                for prefix in ("_do_", "_tool_"):
                    if name.startswith(prefix) and name.removeprefix(prefix) in gated:
                        found.append((path.name, name))
    return found


def test_no_write_handler_is_called_except_through_the_checked_dispatcher() -> None:
    assert _handler_calls() == []


def test_the_dispatcher_is_the_only_caller_of_the_providers_run() -> None:
    callers = []
    for path in sorted(_UI.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "provider.run(" in text:
            callers.append(path.name)
    assert callers == ["workbench_frame_commands.py"]
