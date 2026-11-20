"""A release's files through the Workbench's own doors (complete.md 1.3, verify row).

Upload Asset, Delete Asset and the Assets window (Download, Properties, Delete) on
a release row, with GitHub replaced by a recorded admin and background work run
inline. The wave 4 tests proved the same writes in the classic GitHub Items window;
these prove the Workbench's, and that a file's sheet (rename, label) is reachable.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.github.items_provider import GitHubRelease, GitHubReleaseAsset  # noqa: E402
from quill.core.github.permissions import AccessLevel  # noqa: E402
from quill.core.github.release_admin import ReleaseAssetRecord, ReleaseRecord  # noqa: E402
from quill.ui.github_workbench_window import GitHubWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402

REPO = "owner/repo"
_P = "github.workbench."
_URL = "https://github.com/owner/repo/releases/download/v1.0/app.zip"


class _Items:
    is_authenticated = True
    token = "test-token"

    def fetch_releases(self, _repo: str, **_kw: Any) -> list[GitHubRelease]:
        asset = GitHubReleaseAsset("app.zip", 12, 2048, _URL)
        return [GitHubRelease("v1.0", "One", assets=(asset,))]

    def close(self) -> None:
        pass


class _Admin:
    """GitHubReleaseAdmin, recorded."""

    calls: list[tuple[Any, ...]] = []

    def __init__(self, token: str) -> None:
        assert token == "test-token"

    def find_release(self, repo: str, tag: str) -> ReleaseRecord:
        return ReleaseRecord(5, tag, assets=(ReleaseAssetRecord(31, "app.zip", 2048),))

    def upload_release_asset(self, repo: str, record: ReleaseRecord, path: str) -> Any:
        type(self).calls.append(("upload", repo, record.id, path))
        return ReleaseAssetRecord(77, "notes.txt", 4)

    def delete_asset(self, repo: str, asset: ReleaseAssetRecord) -> None:
        type(self).calls.append(("delete", repo, asset.id))


def _inline(_name: str, work: Any, done: Any, failed: Any) -> None:
    try:
        result = work()
    except Exception as exc:  # noqa: BLE001
        failed(exc)
        return
    done(result)


@pytest.fixture
def bench(wx_session_app, quill_data_dir, monkeypatch):
    monkeypatch.setattr("quill.core.github.release_admin.GitHubReleaseAdmin", _Admin)
    _Admin.calls = []
    said: list[str] = []
    provider = GitHubWorkbenchProvider(_Items(), REPO, announce=said.append)
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    ref = NodeRef("repository", "releases", REPO)
    assert frame.select(ref)
    if frame.current != ref:
        frame._show_node(ref, remember=True)
    frame.list.Select(0)
    frame.reload = lambda *_a, **_k: None  # type: ignore[method-assign]
    yield frame
    frame.frame.Destroy()


def test_upload_asset_asks_with_the_size_then_says_what_github_stored(
    bench, monkeypatch, tmp_path
) -> None:
    source = tmp_path / "notes.txt"
    source.write_text("abcd")

    class _Files:
        def __init__(self, *_a: Any, **_k: Any) -> None:
            pass

        def __enter__(self) -> Any:
            return self

        def __exit__(self, *_a: Any) -> None:
            return None

        def GetPath(self) -> str:  # noqa: N802 - wx's name
            return str(source)

    monkeypatch.setattr(wx, "FileDialog", _Files)
    monkeypatch.setattr("quill.ui.dialog_contract.show_modal_dialog", lambda *_a: wx.ID_OK)
    asked: list[str] = []
    monkeypatch.setattr(bench.provider, "_confirm", lambda _t, q: asked.append(q) or True)
    bench.run(f"{_P}upload_asset")
    assert asked == [f"Upload notes.txt (4 bytes) to release v1.0 in {REPO}?"]
    assert _Admin.calls == [("upload", REPO, 5, str(source))]
    assert bench.said[-1] == "Uploaded notes.txt (4 bytes) to release v1.0."


def test_delete_asset_names_the_file_and_release_and_sends_once(bench, monkeypatch) -> None:
    monkeypatch.setattr(bench.provider, "_choose", lambda *_a: 0)
    asked: list[str] = []
    monkeypatch.setattr(bench.provider, "_confirm", lambda _t, q: asked.append(q) or True)
    bench.run(f"{_P}delete_asset")
    assert asked[0].startswith(f"Delete app.zip from release v1.0 in {REPO}?")
    assert _Admin.calls == [("delete", REPO, 31)]
    assert bench.said[-1] == "Deleted app.zip from release v1.0."


def test_declining_the_delete_sends_nothing(bench, monkeypatch) -> None:
    monkeypatch.setattr(bench.provider, "_choose", lambda *_a: 0)
    monkeypatch.setattr(bench.provider, "_confirm", lambda *_a: False)
    bench.run(f"{_P}delete_asset")
    assert _Admin.calls == []


def _assets_window(bench, monkeypatch) -> dict[str, Any]:
    shown: dict[str, Any] = {}

    class _List:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            shown["actions"] = {label: act for label, _help, act in kwargs["actions"]}

        def show(self) -> None:
            pass

        def set_rows(self, _rows: list[str]) -> None:
            pass

    monkeypatch.setattr("quill.ui.github_workbench_list_dialog.WorkbenchListDialog", _List)
    bench.run(f"{_P}assets")
    return shown["actions"]


def test_the_assets_window_downloads_in_the_browser(bench, monkeypatch) -> None:
    opened: list[str] = []
    monkeypatch.setattr("webbrowser.open", lambda url, new=0: opened.append(url) or True)
    _assets_window(bench, monkeypatch)["&Download"](0)
    assert opened == [_URL]


def test_the_assets_window_opens_the_files_sheet_to_rename_or_label_it(bench, monkeypatch) -> None:
    actions = _assets_window(bench, monkeypatch)
    assert list(actions) == ["&Download", "Copy &Link", "&Properties...", "Dele&te..."]
    opened: list[Any] = []
    monkeypatch.setattr(bench.provider, "_open_one", lambda target, *_a: opened.append(target))
    actions["&Properties..."](0)
    assert opened[0].kind == "release_asset"
    assert dict(opened[0].ident) == {"repo": REPO, "tag": "v1.0", "name": "app.zip"}
    assert {"name", "label"} <= set(opened[0].sheet.editable_keys())


def test_read_only_refuses_upload_and_delete_before_anything_is_asked(bench, monkeypatch) -> None:
    monkeypatch.setattr(bench.provider, "access_level", lambda: AccessLevel.READ_ONLY)
    monkeypatch.setattr(bench.provider, "_choose", lambda *_a: pytest.fail("asked"))
    monkeypatch.setattr(bench.provider, "_confirm", lambda *_a: pytest.fail("asked"))
    for verb in ("upload_asset", "delete_asset", "edit_release", "delete_release"):
        bench.run(f"{_P}{verb}")
        assert "this account is Read Only" in bench.said[-1], verb
    assert _Admin.calls == []
