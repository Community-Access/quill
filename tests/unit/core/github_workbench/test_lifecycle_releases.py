"""Releases and their files, end to end over recorded answers (complete.md 1.3, verify row).

The lifecycle the Workbench offers: list, open, Properties, create, change, publish a
draft and delete a release; upload, rename, label, download and delete a file. Most
of the single writes were proved by earlier waves (test_github_wave4_actions.py: find,
edit and publish, upload and delete an asset; test_github_row_admin.py: delete a
release; test_github_repo_admin.py: create one). This file proves the rest, and the
refusals: no permission, Read Only and not found.

The tests found that a **draft** could not be opened, published from its sheet,
or deleted: GitHub's by-tag read answers 404 for a draft, and a draft's files name
it ``untagged-...``. ``release_admin.release_data`` finds both in the list.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github import release_admin
from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.items_provider import GitHubRelease, GitHubReleaseAsset
from quill.core.github.permissions import AccessLevel, ViewerContext, WriteTier
from quill.core.github.release_admin import GitHubReleaseAdmin, release_data
from quill.core.github.rest_transport import GitHubRestError, RestResponse
from quill.core.github.row_admin import RowAdminError, delete_release
from quill.core.github.sheet_catalog import SHEETS, target_for
from quill.core.github.sheet_engine import load, locked_fields, plan, save
from quill.core.github.sheets_releases import RELEASE, RELEASE_ASSET
from quill.core.github.write_gate import command_refusal, gated_tier
from quill.core.workbench.properties import FieldChange
from tests.github_api_fake import FakeGitHubApi

REPO = "o/r"
_P = "github.workbench."


def _asset(**more: Any) -> dict[str, Any]:
    return {
        "id": 31,
        "name": "app.zip",
        "label": "",
        "size": 4096,
        "download_count": 12,
        "content_type": "application/zip",
        "updated_at": "2026-11-01T10:00:00Z",
        "browser_download_url": "https://github.com/o/r/releases/download/v1.0/app.zip",
        **more,
    }


def _release(**more: Any) -> dict[str, Any]:
    return {
        "id": 5,
        "tag_name": "v1.0",
        "target_commitish": "main",
        "name": "One",
        "body": "Notes",
        "draft": False,
        "prerelease": False,
        "author": {"login": "jeff"},
        "published_at": "2026-11-01T10:00:00Z",
        "html_url": "https://github.com/o/r/releases/tag/v1.0",
        "assets": [_asset()],
        **more,
    }


def _draft() -> dict[str, Any]:
    untagged = "https://github.com/o/r/releases/download/untagged-ab12/app.zip"
    return _release(
        id=6,
        tag_name="v2.0",
        name="Two",
        draft=True,
        published_at=None,
        html_url="https://github.com/o/r/releases/tag/untagged-ab12",
        assets=[_asset(id=41, browser_download_url=untagged)],
    )


@pytest.fixture
def github() -> FakeGitHubApi:
    """A repository with one published release and one draft, which GitHub changes on write."""
    fake = FakeGitHubApi()
    held = {"v1.0": _release(), "v2.0": _draft()}

    def by_id(release_id: int) -> dict[str, Any]:
        return next(r for r in held.values() if r["id"] == release_id)

    def on_write(method: str, path: str, body: Any) -> None:
        if method == "PATCH" and path.startswith("/repos/o/r/releases/assets/"):
            asset_id = int(path.rsplit("/", 1)[1])
            for release in held.values():
                for asset in release["assets"]:
                    if asset["id"] == asset_id:
                        asset.update(body or {})
        elif method == "PATCH" and path.startswith("/repos/o/r/releases/"):
            release = by_id(int(path.rsplit("/", 1)[1]))
            changes = dict(body or {})
            changes.pop("make_latest", None)
            if "draft" in changes and not changes["draft"]:
                changes["html_url"] = f"https://github.com/o/r/releases/tag/{release['tag_name']}"
            release.update(changes)
        elif method == "DELETE" and path.startswith("/repos/o/r/releases/"):
            gone = by_id(int(path.rsplit("/", 1)[1]))
            held.pop(gone["tag_name"])

    def by_tag(tag: str) -> Any:
        def read() -> Any:
            found = held.get(tag)
            if found is None or found["draft"]:  # GitHub cannot see a draft by its tag
                raise GitHubRestError("Not Found", status=404)
            return found

        return read

    fake.on_write = on_write
    for tag in ("v1.0", "v2.0", "untagged-ab12"):
        fake.answer("GET", f"/repos/o/r/releases/tags/{tag}", by_tag(tag))
    fake.answer("GET", "/repos/o/r/releases", lambda: list(held.values()))
    fake.answer("GET", "/repos/o/r/releases/latest", lambda: held.get("v1.0") or {})
    fake.held = held  # type: ignore[attr-defined]
    return fake


# -- list and open -------------------------------------------------------------------


def test_every_release_and_file_row_opens_its_own_sheet() -> None:
    asset = GitHubReleaseAsset("app.zip", 12, 4096, _asset()["browser_download_url"])
    release = GitHubRelease("v1.0", "One", assets=(asset,))
    assert target_for(release, REPO).ident == {"repo": REPO, "tag": "v1.0"}
    assert target_for(asset, REPO).ident == {"repo": REPO, "name": "app.zip", "tag": "v1.0"}
    assert SHEETS["release"] is RELEASE and SHEETS["release_asset"] is RELEASE_ASSET


def test_a_published_release_opens_with_its_files_and_latest(github: FakeGitHubApi) -> None:
    values = load(github, RELEASE, {"repo": REPO, "tag": "v1.0"}).values
    assert (values["name"], values["tag"], values["draft"], values["latest"]) == (
        "One",
        "v1.0",
        False,
        True,
    )
    assert values["assets"] == ("app.zip, 4 KB, 12 downloads",)
    assert values["id"] == "5"


def test_a_draft_opens_although_github_cannot_read_it_by_tag(github: FakeGitHubApi) -> None:
    values = load(github, RELEASE, {"repo": REPO, "tag": "v2.0"}).values
    assert (values["name"], values["draft"], values["latest"]) == ("Two", True, False)


def test_a_drafts_file_opens_from_its_untagged_address(github: FakeGitHubApi) -> None:
    asset = GitHubReleaseAsset("app.zip", 12, 4096, _draft()["assets"][0]["browser_download_url"])
    target = target_for(asset, REPO)
    assert target is not None and target.ident["tag"] == "untagged-ab12"
    values = load(github, RELEASE_ASSET, target.ident).values
    assert (values["asset_id"], values["name"]) == ("41", "app.zip")


def test_release_data_says_not_found_after_looking_everywhere(github: FakeGitHubApi) -> None:
    with pytest.raises(GitHubRestError) as caught:
        release_data(github, REPO, "v9.9")
    assert caught.value.status == 404
    assert ("GET", "/repos/o/r/releases", None) in github.calls


def test_release_data_does_not_hide_a_refusal_as_not_found() -> None:
    fake = FakeGitHubApi()
    fake.answer("GET", "/repos/o/r/releases/tags/v1.0", GitHubRestError("no", status=403))
    with pytest.raises(GitHubRestError) as caught:
        release_data(fake, REPO, "v1.0")
    assert caught.value.status == 403


# -- Properties: change, publish, rename, label --------------------------------------


def _saved(github: FakeGitHubApi, sheet: Any, ident: dict[str, str], *changes: FieldChange) -> Any:
    loaded = load(github, sheet, ident).values
    return save(github, sheet, ident, list(changes), loaded=loaded)


def test_the_sheet_changes_title_notes_and_prerelease_in_one_request(
    github: FakeGitHubApi,
) -> None:
    ident = {"repo": REPO, "tag": "v1.0"}
    outcome = _saved(
        github,
        RELEASE,
        ident,
        FieldChange("name", "Title", "One", "One point oh"),
        FieldChange("notes", "Release notes", "Notes", "Better notes"),
        FieldChange("prerelease", "Pre-release", False, True),
    )
    assert github.writes() == [
        (
            "PATCH",
            "/repos/o/r/releases/5",
            {"name": "One point oh", "body": "Better notes", "prerelease": True},
        )
    ]
    assert not outcome.failed and outcome.after["name"] == "One point oh"


def test_publishing_a_draft_from_its_sheet_clears_draft_and_reads_it_back(
    github: FakeGitHubApi,
) -> None:
    outcome = _saved(
        github, RELEASE, {"repo": REPO, "tag": "v2.0"}, FieldChange("draft", "Draft", True, False)
    )
    assert github.writes() == [("PATCH", "/repos/o/r/releases/6", {"draft": False})]
    assert not outcome.failed and outcome.after["draft"] is False


def test_making_a_release_latest_sends_githubs_string(github: FakeGitHubApi) -> None:
    requests = plan(
        RELEASE,
        {"repo": REPO, "tag": "v2.0", "id": "6"},
        [FieldChange("latest", "Latest release", False, True)],
    )
    assert [(r.method, r.path, r.body) for r in requests] == [
        ("PATCH", "/repos/o/r/releases/6", {"make_latest": "true"})
    ]


def test_renaming_the_tag_moves_the_sheet_to_the_new_tag(github: FakeGitHubApi) -> None:
    outcome = _saved(
        github, RELEASE, {"repo": REPO, "tag": "v1.0"}, FieldChange("tag", "Tag", "v1.0", "v1.0.1")
    )
    assert github.writes()[-1] == ("PATCH", "/repos/o/r/releases/5", {"tag_name": "v1.0.1"})
    assert RELEASE.ident_after({"repo": REPO, "tag": "v1.0"}, [outcome.done[0]])["tag"] == (
        "v1.0.1"
    )


def test_a_file_is_renamed_and_labelled_on_its_sheet(github: FakeGitHubApi) -> None:
    ident = {"repo": REPO, "tag": "v1.0", "name": "app.zip"}
    outcome = _saved(
        github,
        RELEASE_ASSET,
        ident,
        FieldChange("name", "File name", "app.zip", "app-1.0.zip"),
        FieldChange("label", "Label", "", "Windows build"),
    )
    assert github.writes() == [
        (
            "PATCH",
            "/repos/o/r/releases/assets/31",
            {"name": "app-1.0.zip", "label": "Windows build"},
        )
    ]
    assert outcome.after["name"] == "app-1.0.zip" and outcome.after["label"] == "Windows build"


def test_a_change_github_refuses_is_reported_against_its_field(github: FakeGitHubApi) -> None:
    github.answer("PATCH", "/repos/o/r/releases/5", GitHubRestError("Forbidden", status=403))
    outcome = _saved(
        github, RELEASE, {"repo": REPO, "tag": "v1.0"}, FieldChange("name", "Title", "One", "Uno")
    )
    assert [change.key for change, _why in outcome.failed] == ["name"]


# -- create and the single commands ----------------------------------------------------


def _on(monkeypatch: pytest.MonkeyPatch, replies: dict[tuple[str, str], Any]) -> list[Any]:
    sent: list[Any] = []

    def request(_token: Any, method: str, path: str, *, body: Any = None, **_kw: Any) -> Any:
        sent.append((method, path, body))
        reply = replies.get((method, path), RestResponse(200, {}, None))
        if isinstance(reply, BaseException):
            raise reply
        return reply

    monkeypatch.setattr(release_admin, "request_json", request)
    return sent


def test_editing_without_permission_is_said_plainly(monkeypatch: pytest.MonkeyPatch) -> None:
    _on(monkeypatch, {("PATCH", "/repos/o/r/releases/5"): GitHubRestError("no", status=403)})
    record = release_admin.parse_release(_release())
    with pytest.raises(GitHubItemsError, match="Could not edit release v1.0. Access denied"):
        GitHubReleaseAdmin("tok").edit_release(
            REPO, record, name="One", body="", draft=False, prerelease=False
        )


def test_a_release_deleted_meanwhile_is_said_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    _on(monkeypatch, {("GET", "/repos/o/r/releases"): RestResponse(200, {}, [])})
    with pytest.raises(GitHubItemsError, match="no release tagged v1.0 in o/r"):
        GitHubReleaseAdmin("tok").find_release(REPO, "v1.0")


def test_signed_out_writes_are_refused_before_anything_is_sent(tmp_path: Any) -> None:
    admin = GitHubReleaseAdmin(None)
    record = release_admin.parse_release(_release())
    with pytest.raises(GitHubItemsError, match="signed-in GitHub account"):
        admin.edit_release(REPO, record, name="", body="", draft=False, prerelease=False)
    with pytest.raises(GitHubItemsError, match="signed-in GitHub account"):
        admin.delete_asset(REPO, record.assets[0])
    source = tmp_path / "x.bin"
    source.write_bytes(b"x")
    with pytest.raises(GitHubItemsError, match="signed-in GitHub account"):
        admin.upload_release_asset(REPO, record, source, opener=object())


def test_an_empty_file_is_refused_before_the_upload(tmp_path: Any) -> None:
    source = tmp_path / "empty.bin"
    source.write_bytes(b"")
    record = release_admin.parse_release(_release())
    with pytest.raises(GitHubItemsError, match="empty"):
        GitHubReleaseAdmin("tok").upload_release_asset(REPO, record, source, opener=object())


def test_an_upload_without_permission_is_said_plainly(tmp_path: Any) -> None:
    import io
    from email.message import Message
    from urllib.error import HTTPError

    source = tmp_path / "a.bin"
    source.write_bytes(b"x")

    class Refusing:
        def open(self, request: Any, timeout: int) -> Any:
            raise HTTPError(
                request.full_url, 403, "no", Message(), io.BytesIO(b'{"message": "Forbidden"}')
            )

    with pytest.raises(GitHubItemsError, match="Could not upload a.bin. Access denied"):
        GitHubReleaseAdmin("tok").upload_release_asset(
            REPO, release_admin.ReleaseRecord(id=5, tag="v1"), source, opener=Refusing()
        )


def test_deleting_a_file_already_gone_is_said_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    gone = GitHubRestError("Not Found", status=404)
    _on(monkeypatch, {("DELETE", "/repos/o/r/releases/assets/31"): gone})
    record = release_admin.parse_release(_release())
    with pytest.raises(GitHubItemsError, match="delete app.zip. GitHub could not find it"):
        GitHubReleaseAdmin("tok").delete_asset(REPO, record.assets[0])


def test_a_draft_is_deleted_and_no_tag_is_claimed(github: FakeGitHubApi) -> None:
    said = delete_release(github, REPO, "v2.0", delete_tag=True)
    assert said == "Deleted the draft release v2.0. A draft has no tag yet, so none was deleted."
    assert github.writes() == [("DELETE", "/repos/o/r/releases/6", None)]


def test_deleting_a_release_without_permission_or_after_it_went(github: FakeGitHubApi) -> None:
    github.answer("DELETE", "/repos/o/r/releases/5", GitHubRestError("no", status=403))
    with pytest.raises(RowAdminError, match="needs more access"):
        delete_release(github, REPO, "v1.0")
    with pytest.raises(RowAdminError, match="found nothing to find the release v9"):
        delete_release(github, REPO, "v9")


# -- Read Only, Organize and the role GitHub gives -------------------------------------

_RELEASE_WRITES = (
    f"{_P}edit_release",
    f"{_P}upload_asset",
    f"{_P}delete_asset",
    f"{_P}delete_release",
    "github.create_release",
)


@pytest.mark.parametrize("command_id", _RELEASE_WRITES)
def test_every_release_write_is_refused_at_read_only(
    command_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    said = command_refusal(command_id, lambda: AccessLevel.READ_ONLY)
    assert said.startswith("Cannot run ") and "this account is Read Only" in said
    assert command_refusal(command_id, lambda: AccessLevel.FULL) == ""


def test_deletes_need_full_and_edits_and_uploads_only_organize(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    assert gated_tier(f"{_P}delete_release") == WriteTier.DESTRUCTIVE
    assert gated_tier(f"{_P}delete_asset") == WriteTier.DESTRUCTIVE
    assert "needs Full" in command_refusal(f"{_P}delete_asset", lambda: AccessLevel.ORGANIZE)
    for command_id in (f"{_P}edit_release", f"{_P}upload_asset", "github.create_release"):
        assert command_refusal(command_id, lambda: AccessLevel.ORGANIZE) == ""


@pytest.mark.parametrize("sheet", [RELEASE, RELEASE_ASSET])
def test_every_field_locks_at_read_only_and_for_a_reader(sheet: Any) -> None:
    editable = set(sheet.editable_keys()) - {"reactions"}
    read_only = locked_fields(sheet, ViewerContext(repo_role="admin", level=AccessLevel.READ_ONLY))
    assert editable <= set(read_only)
    assert all("read only in the Workbench" in why for why in read_only.values())
    reader = locked_fields(sheet, ViewerContext(repo_role="read", where=REPO))
    assert editable <= set(reader)
    assert all("write access" in reader[key] for key in editable)
    assert not set(locked_fields(sheet, ViewerContext(repo_role="write", where=REPO))) & editable
