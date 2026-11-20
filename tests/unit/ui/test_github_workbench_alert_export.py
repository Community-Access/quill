"""Export List on a security alert list writes no secret, token or sensitive field (GX11).

A real frame over fakes, background work inline, the Save dialog replaced.
GitHub's answers here carry everything a careless export could leak: the
secret scanning alert's ``secret`` value, a token quoted in a code scanning
message, a token in a dismissal comment, and ``user:password@`` in a link.
Every file format is checked, and so is every alert list the Workbench has.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.github.alert_export import ALERT_LISTS, safe_rows  # noqa: E402
from quill.core.github.notifications import list_security_alerts  # noqa: E402
from quill.core.github.rest_transport import RestResponse  # noqa: E402
from quill.ui.github_workbench_window import GitHubWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402

REPO = "owner/repo"
EXPORT = "github.workbench.export_list"
SECRET = "ghp_" + "S3cr3tValueNobodyMaySee0123456789ab"
QUOTED = "github_pat_" + "11AAQuotedInAMessage0123456789abcdefgh"
COMMENT = "AKIA" + "IOSFODNN7EXAMPLEKEY12"
WITH_PASSWORD = "https://alice:hunter2@example.com/a"
LEAKS = (SECRET, QUOTED, COMMENT, "hunter2")


def _rows(found: list[Any], _limit: int) -> list[Any]:
    return found


class _Repo:
    """PyGithub's repository, as list_security_alerts reads it."""

    def get_dependabot_alerts(self, **_kw: Any) -> list[Any]:
        return [
            SimpleNamespace(
                number=1,
                state="open",
                html_url=WITH_PASSWORD,
                created_at=None,
                security_advisory=SimpleNamespace(severity="high", summary="Prototype pollution"),
                dependency=SimpleNamespace(package=SimpleNamespace(name="lodash")),
            )
        ]

    def get_codescan_alerts(self, **_kw: Any) -> list[Any]:
        instance = SimpleNamespace(
            message=SimpleNamespace(text=f"The hard-coded value {QUOTED} reaches a sink."),
            location=SimpleNamespace(path="app.py", start_line=3, end_line=3),
        )
        return [
            SimpleNamespace(
                number=2,
                state="open",
                html_url="",
                created_at=None,
                rule=SimpleNamespace(severity="error", name="", id="py/hardcoded", description=""),
                tool=SimpleNamespace(name="CodeQL"),
                most_recent_instance=instance,
            )
        ]

    def get_secret_scanning_alerts(self, **kw: Any) -> list[Any]:
        assert kw.get("hide_secret") is True  # the value is never asked for
        return [
            SimpleNamespace(
                number=3,
                state="open",
                html_url="",
                created_at=None,
                secret=SECRET,  # what GitHub would send if asked
                secret_type="github_personal_access_token",
                secret_type_display_name="GitHub Personal Access Token",
            )
        ]


class _Items:
    is_authenticated = True
    token = "test-token-not-real"
    _gh = None

    def _repo(self, _name: str) -> _Repo:
        return _Repo()

    def fetch_security_alerts(self, _repo: str, **_kw: Any) -> list[Any]:
        return list_security_alerts(_Repo(), limit=30, take=_rows)

    def fetch_issues(self, _repo: str, **_kw: Any) -> list[Any]:
        return []

    def fetch_pulls(self, _repo: str, **_kw: Any) -> list[Any]:
        return []

    def close(self) -> None:
        pass


def _inline(_name: str, work: Any, done: Any, failed: Any) -> None:
    try:
        result = work()
    except Exception as exc:  # noqa: BLE001
        failed(exc)
        return
    done(result)


@pytest.fixture
def bench(wx_session_app, quill_data_dir, monkeypatch):
    monkeypatch.setattr("quill.core.github.consent.load_github_consent_complete", lambda: True)
    said: list[str] = []
    provider = GitHubWorkbenchProvider(_Items(), REPO, announce=said.append)
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    yield frame
    provider.stop_watch_timer()
    frame.frame.Destroy()


def _save_to(monkeypatch, path: Path) -> None:
    class Dialog:
        def __init__(self, *_a: Any, **_k: Any) -> None:
            pass

        def __enter__(self) -> Dialog:
            return self

        def __exit__(self, *_exc: object) -> None:
            pass

        def GetPath(self) -> str:  # noqa: N802 - wx's name
            return str(path)

    monkeypatch.setattr(wx, "FileDialog", Dialog)
    monkeypatch.setattr(
        "quill.ui.github_workbench_export_list.show_modal_dialog", lambda _d, _t: wx.ID_OK
    )
    monkeypatch.setattr(
        "quill.ui.github_workbench_actions.GitHubWorkbenchActionsMixin._confirm",
        lambda _s, _t, _q: False,
    )


def _show(frame: WorkbenchFrame, ref: NodeRef) -> None:
    if ref.template == "organization":
        frame.provider.add_instance("organization", ref.instance)
        frame.rebuild_tree()
    assert frame.select(ref)
    if frame.current != ref:
        frame._show_node(ref, remember=True)
    assert frame.rows


def _exported(path: Path) -> str:
    if path.suffix == ".xlsx":
        from openpyxl import load_workbook

        sheet = load_workbook(path).active
        return "\n".join(
            " ".join(str(c or "") for c in row) for row in sheet.iter_rows(values_only=True)
        )
    return path.read_text(encoding="utf-8-sig")


@pytest.mark.parametrize("suffix", [".csv", ".md", ".xlsx"])
def test_a_repositorys_alerts_export_without_a_secret_or_a_token(
    bench, monkeypatch, tmp_path: Path, suffix: str
) -> None:
    _show(bench, NodeRef("repository", "alerts", REPO))
    shown = " ".join(" ".join(bench.provider.cells(r, ("result",))) for r in bench.rows)
    assert QUOTED in shown  # the list shows what GitHub wrote; the file does not
    target = tmp_path / f"alerts{suffix}"
    _save_to(monkeypatch, target)
    bench.run(EXPORT)
    text = _exported(target)
    assert "lodash" in text and "GitHub Personal Access Token" in text and "[TOKEN]" in text
    for leak in LEAKS:
        assert leak not in text, leak
    assert (
        bench.said[-1] == "Exported 3 rows to " + target.name + ". Held back: 1 value like a token."
    )


def test_an_organizations_secret_alerts_export_without_the_secret(
    bench, monkeypatch, tmp_path: Path
) -> None:
    asked: list[dict[str, str]] = []

    def reply(_token: Any, method: str, path: str, **kw: Any) -> RestResponse:
        asked.append(dict(kw.get("query") or {}))
        alert = {
            "number": 7,
            "state": "resolved",
            "secret": SECRET,
            "secret_type_display_name": "GitHub Personal Access Token",
            "resolution_comment": f"rotated {COMMENT}",
            "repository": {"full_name": "acme/web"},
            "html_url": WITH_PASSWORD,
        }
        return RestResponse(200, {}, [alert] if path == "/orgs/acme/secret-scanning/alerts" else [])

    monkeypatch.setattr("quill.core.github.workbench_api.request_json", reply)
    _show(bench, NodeRef("organization", "org_secret_alerts", "acme"))
    assert asked[-1].get("hide_secret") == "true"
    target = tmp_path / "secrets.csv"
    _save_to(monkeypatch, target)
    bench.run(EXPORT)
    text = _exported(target)
    assert "acme/web: GitHub Personal Access Token" in text
    for leak in LEAKS:
        assert leak not in text, leak


def test_every_alert_list_is_redacted_and_no_other_list_is() -> None:
    from quill.core.github.workbench_tree import GITHUB_TREE

    every = [
        *GITHUB_TREE._nodes.values(),
        *(n for name in GITHUB_TREE._templates for n in GITHUB_TREE.template(name)),
    ]
    raw = [[f"note {SECRET}", f"see {WITH_PASSWORD}"]]
    for loader in ALERT_LISTS:
        cells = safe_rows(loader, raw)[0]
        assert SECRET not in cells[0] and "hunter2" not in cells[1], loader
    sha = "0123456789abcdef0123456789abcdef01234567"
    assert safe_rows("items:commits", [[sha]]) == [[sha]]  # a commit list keeps its SHAs
    alertish = {
        node.loader
        for node in every
        if node.loader and (node.row_type == "security_alert" or node.loader.endswith("alerts"))
    }
    assert "explore:security" in alertish
    assert alertish <= ALERT_LISTS, alertish - ALERT_LISTS
