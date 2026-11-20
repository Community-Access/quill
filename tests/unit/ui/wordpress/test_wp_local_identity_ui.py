"""Confirmed WordPress interaction failures (plan.md, 2026-11-20), editor half.

The real shared commands, through each editor's real host adapter, over a
fake text control, a fake site and scripted dialogs:

3. Properties renamed a draft, and Open Local Draft then opened an empty
   editor on a file that did not exist;
4. an uploaded picture's site address reached the file but not the open
   editor, so the next ordinary save put the ``file:`` address back;
5. Restore kept the file on disk in Previous Versions, not the unsaved
   writing it replaced.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.apps.lite_window_wordpress_host import LiteWordPressHost
from quill.core.wordpress import local as lc
from quill.core.wordpress import sites as st
from quill.ui import wordpress_item_dialogs as idlg
from quill.ui.main_frame_wordpress import QuillWordPressHost

API = "/wp-json/wp/v2"
UPLOADS = "https://radio.example/wp-content/uploads/2026/11"
EDITOR = {
    "id": 7,
    "name": "Jeff",
    "slug": "jeff",
    "roles": ["editor"],
    "capabilities": {"publish_posts": True, "publish_pages": True, "edit_posts": True},
}


class _Control:
    """Enough of a wx text control for both adapters."""

    def __init__(self) -> None:
        self.value = ""
        self.caret = 0
        self.selection = (0, 0)
        self.modified = False
        self.focused = 0

    def GetValue(self) -> str:  # noqa: N802 - wx's names
        return self.value

    def GetLastPosition(self) -> int:  # noqa: N802
        return len(self.value)

    def SetSelection(self, start: int, end: int) -> None:  # noqa: N802
        self.selection = (start, end)

    def WriteText(self, text: str) -> None:  # noqa: N802
        start, end = self.selection if self.selection[0] != self.selection[1] else (self.caret,) * 2
        self.value = self.value[:start] + text + self.value[end:]
        self.caret = start + len(text)
        self.selection = (self.caret, self.caret)
        self.modified = True

    def GetStringSelection(self) -> str:  # noqa: N802
        return self.value[self.selection[0] : self.selection[1]]

    def GetInsertionPoint(self) -> int:  # noqa: N802
        return self.caret

    def SetInsertionPoint(self, offset: int) -> None:  # noqa: N802
        self.caret = offset
        self.selection = (offset, offset)

    def ShowPosition(self, _offset: int) -> None:  # noqa: N802
        return None

    def SetFocus(self) -> None:  # noqa: N802
        self.focused += 1

    def IsModified(self) -> bool:  # noqa: N802
        return self.modified


class _Editor:
    """One editor window: a path, a control, open and save. ``type`` is the person."""

    def __init__(self) -> None:
        self.control = _Control()
        self.path: Path | None = None
        self.announced: list[str] = []

    def open(self, path: Path) -> None:
        self.path = Path(path)
        self.control.value = path.read_text(encoding="utf-8") if path.exists() else ""
        self.control.caret = 0
        self.control.modified = False

    def save(self) -> None:
        if self.path is not None:
            self.path.write_text(self.control.value, encoding="utf-8", newline="")
        self.control.modified = False

    def close(self) -> None:
        self.path = None
        self.control.value = ""

    def type(self, text: str) -> None:
        self.control.SetInsertionPoint(len(self.control.value))
        self.control.WriteText(text)


def _sync(func: Any, on_success: Any, on_failure: Any) -> None:
    try:
        result = func()
    except BaseException as exc:  # noqa: BLE001 - the host hands every failure back
        on_failure(exc)
        return
    on_success(result)


def _quill_host(editor: _Editor) -> Any:
    """QUILL's adapter over a fake main frame."""
    frame = SimpleNamespace(
        frame=None,
        editor=editor.control,
        document=SimpleNamespace(path=None, modified=False),
        _announce=editor.announced.append,
        _show_modal_dialog=lambda _d, _label: 0,
    )

    def open_file(path: Path) -> None:
        editor.open(path)
        frame.document.path = str(path)

    def save_file() -> None:
        editor.save()
        frame.document.modified = False

    frame.open_file = open_file
    frame.save_file = save_file

    class Host(QuillWordPressHost):
        def run_task(self, _name: str, func: Any, on_success: Any, on_failure: Any) -> None:
            _sync(func, on_success, on_failure)

        def start_repeating(self, _seconds: float, _callback: Any) -> Any:
            return lambda: None

        def current_path(self) -> Path | None:
            frame.document.path = str(editor.path) if editor.path else None
            return super().current_path()

    return Host(frame)


def _lite_host(editor: _Editor) -> Any:
    """QUILL Lite's adapter over a fake document window."""
    window = SimpleNamespace(control=editor.control, _announce=editor.announced.append)
    window.app = SimpleNamespace(open_path=editor.open)
    window.cmd_save = editor.save

    class Host(LiteWordPressHost):
        def run_task(self, _name: str, func: Any, on_success: Any, on_failure: Any) -> None:
            _sync(func, on_success, on_failure)

        def start_repeating(self, _seconds: float, _callback: Any) -> Any:
            return lambda: None

        def current_path(self) -> Path | None:
            window.path = editor.path
            return super().current_path()

    return Host(window)


HOSTS = {"QUILL": _quill_host, "QUILL Lite": _lite_host}


def _commands(host: Any, tmp_path: Path, wp_site: Any) -> Any:
    from quill.ui.wordpress_commands import WordPressCommands

    return WordPressCommands(host, data_dir=tmp_path, opener=wp_site)


@pytest.fixture
def connected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(st, "_load_secret", lambda _site_id: "abcd efgh ijkl mnop qrst uvwx")
    monkeypatch.setattr(st, "_import_publishing_connections", lambda: st.SiteStore())
    profile = st.SiteProfile(
        id="radio",
        name="Community Radio",
        site_url="https://radio.example",
        username="jeff",
        role="Editor",
        announce_waiting_comments=False,
        announce_new_responses=False,
    )
    st.save_sites(st.SiteStore([profile], "radio"), tmp_path)
    return tmp_path


def _saved_page(request: Any, _query: Any) -> dict[str, Any]:
    return {
        "id": 41,
        "type": "page",
        "title": {"raw": "Renamed"},
        "content": {"raw": "<p>Hi</p>"},
        "status": "draft",
        "link": "https://radio.example/?page_id=41",
        "modified_gmt": "2026-11-20T10:00:00",
    }


def _rename(wp_dialogs: Any, title: str) -> None:
    wp_dialogs.answer(
        "ask_properties",
        idlg.PropertiesAnswer(
            title=title,
            slug="our-schedule",
            status="draft",
            excerpt="",
            category_ids=[],
            tag_ids=[],
            comments_open=True,
            sticky=False,
        ),
    )


# --------------------------------------------------------------------------- #
# 3. the draft's identity survives rename, send, close and reopen, and restart


@pytest.mark.parametrize("make_host", HOSTS.values(), ids=HOSTS.keys())
def test_a_renamed_draft_reopens_with_its_writing(
    make_host: Any, connected: Path, wp_site: Any, wp_dialogs: Any
) -> None:
    editor = _Editor()
    wp = _commands(make_host(editor), connected, wp_site)
    wp_dialogs.answer(
        "ask_new_item",
        idlg.NewItemAnswer(
            site_index=0,
            title="Our Schedule",
            slug="our-schedule",
            text_format="markdown",
            category_ids=[],
            tag_ids=[],
        ),
    )
    wp.cmd_new_page()
    first = editor.path
    editor.type("The learner's writing.\n")
    editor.save()

    _rename(wp_dialogs, "Our Autumn Schedule")
    wp.cmd_properties()
    editor.close()
    wp_dialogs.answer("ask_choice", 0)
    wp.cmd_open_local_draft()
    assert editor.path == first and editor.path.exists()
    assert editor.control.value == "The learner's writing.\n"

    # Send it, rename it again, close it, then open it from the site's list.
    wp_site.on("GET", f"{API}/users/me", EDITOR).on("POST", f"{API}/pages", _saved_page)
    wp.cmd_save_draft()
    assert "Draft saved to Community Radio" in editor.announced[-1]
    _rename(wp_dialogs, "Renamed Again")
    wp.cmd_properties()
    editor.close()
    profile = wp.sites().get("radio")
    wp.open_item(profile, "page", 41)
    assert editor.path == first
    assert editor.control.value == "The learner's writing.\n"
    assert wp_site.sent("GET", f"{API}/pages/41") == [], "it fetched instead of reopening"

    # A restart: a new editor and new commands over the same data folder.
    editor.close()
    later = _Editor()
    again = _commands(make_host(later), connected, wp_site)
    wp_dialogs.answer("ask_choice", 0)
    again.cmd_open_local_draft()
    assert later.path == first
    assert later.control.value == "The learner's writing.\n"
    assert len(list(first.parent.glob("*.md"))) == 1


# --------------------------------------------------------------------------- #
# 4. an uploaded picture's address reaches the open editor


def _with_picture(wp: Any, editor: _Editor, tmp_path: Path) -> tuple[str, str]:
    picture = tmp_path / "fair.png"
    picture.write_bytes(b"\x89PNG fake")
    copy = lc.WorkingCopy(
        site_id="radio",
        kind="page",
        local_id=lc.new_local_id(),
        remote_id=41,
        title="Our Schedule",
        text=f"Intro.\n\n![The stall]({picture.as_uri()})\n",
        base_modified_gmt="2026-11-20T09:00:00",
        pending_uploads=[{"path": str(picture), "alt": "The stall"}],
    )
    wp.host.open_path(wp.local.write_document(copy))
    editor.control.SetInsertionPoint(len("Intro."))
    return picture.as_uri(), f"{UPLOADS}/fair.png"


def _site_for_upload(wp_site: Any, during_upload: Any = None) -> None:
    def uploaded(_request: Any, _query: Any) -> dict[str, Any]:
        if during_upload is not None:
            during_upload()
        return {"id": 9, "source_url": f"{UPLOADS}/fair.png", "media_type": "image"}

    page = dict(_saved_page(None, None), modified_gmt="2026-11-20T09:00:00")
    wp_site.on("GET", f"{API}/users/me", EDITOR)
    wp_site.on("GET", f"{API}/pages/41", page)
    wp_site.on("POST", f"{API}/media", uploaded)
    wp_site.on("POST", f"{API}/media/9", {"id": 9, "source_url": f"{UPLOADS}/fair.png"})
    wp_site.on("POST", f"{API}/pages/41", _saved_page)


@pytest.mark.parametrize("make_host", HOSTS.values(), ids=HOSTS.keys())
def test_an_uploaded_picture_is_not_put_back_by_the_next_save(
    make_host: Any, connected: Path, wp_site: Any, wp_dialogs: Any, tmp_path: Path
) -> None:
    editor = _Editor()
    wp = _commands(make_host(editor), connected, wp_site)
    local_uri, site_url = _with_picture(wp, editor, tmp_path)

    def typing() -> None:  # then back up to the end of the first line
        editor.type("Typed while sending.\n")
        editor.control.SetInsertionPoint(len("Intro."))

    _site_for_upload(wp_site, during_upload=typing)
    wp.cmd_save_draft()

    sent = wp_site.body(wp_site.sent("POST", f"{API}/pages/41")[0])
    assert site_url in str(sent) and local_uri not in str(sent)
    assert site_url in editor.control.value and local_uri not in editor.control.value
    assert editor.control.value.endswith("Typed while sending.\n"), "a newer edit was lost"
    assert editor.control.caret == len("Intro."), "the caret moved"
    assert editor.control.focused == 0, "focus moved"
    assert local_uri not in editor.path.read_text(encoding="utf-8")

    editor.save()  # the next ordinary save
    on_disk = editor.path.read_text(encoding="utf-8")
    assert site_url in on_disk and local_uri not in on_disk
    assert "Typed while sending." in on_disk
    copy = wp.local.copy_for_path(editor.path)
    assert copy.pending_uploads == []


def test_a_file_address_saved_back_is_swapped_again_on_the_next_send(
    connected: Path, wp_site: Any, wp_dialogs: Any, tmp_path: Path
) -> None:
    """An editor that saved its older text (a second window, say) cannot undo an upload."""
    editor = _Editor()
    wp = _commands(_quill_host(editor), connected, wp_site)
    local_uri, site_url = _with_picture(wp, editor, tmp_path)
    _site_for_upload(wp_site)
    wp.cmd_save_draft()
    editor.path.write_text(f"Older.\n\n![The stall]({local_uri})\n", encoding="utf-8")
    editor.open(editor.path)
    wp.cmd_save_draft()
    second = wp_site.body(wp_site.sent("POST", f"{API}/pages/41")[1])
    assert site_url in str(second) and local_uri not in str(second)
    assert len(wp_site.sent("POST", f"{API}/media")) == 1, "it uploaded the picture twice"
    assert local_uri not in editor.control.value


def test_a_picture_sent_from_another_document_leaves_this_editor_alone(
    connected: Path, wp_site: Any, wp_dialogs: Any, tmp_path: Path
) -> None:
    editor = _Editor()
    wp = _commands(_quill_host(editor), connected, wp_site)
    local_uri, site_url = _with_picture(wp, editor, tmp_path)
    picture_page = editor.path
    other = tmp_path / "notes.txt"
    other.write_text(f"My notes mention {local_uri}\n", encoding="utf-8")

    def switch() -> None:
        editor.open(other)

    _site_for_upload(wp_site, during_upload=switch)
    wp.cmd_save_draft()
    assert editor.control.value == f"My notes mention {local_uri}\n"
    assert site_url in picture_page.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# 5. Restore keeps the writing it replaces


def _page_with_history(wp: Any, editor: _Editor, wp_site: Any) -> Path:
    copy = lc.WorkingCopy(
        site_id="radio",
        kind="page",
        local_id=lc.new_local_id(),
        remote_id=41,
        title="Our Schedule",
        text="Last saved text\n",
    )
    path = wp.local.write_document(copy)
    wp.local.add_version(copy, lc.REASON_OPENED, text="The first version\n")
    wp.host.open_path(path)
    editor.control.SetSelection(0, editor.control.GetLastPosition())
    editor.control.WriteText("New unsaved writing\n")
    wp_site.on("GET", f"{API}/pages/41/revisions", [])
    wp_site.on("GET", f"{API}/pages/41/autosaves", [])
    return path


@pytest.mark.parametrize("make_host", HOSTS.values(), ids=HOSTS.keys())
def test_restore_keeps_the_unsaved_writing_it_replaces(
    make_host: Any, connected: Path, wp_site: Any, wp_dialogs: Any
) -> None:
    editor = _Editor()
    wp = _commands(make_host(editor), connected, wp_site)
    path = _page_with_history(wp, editor, wp_site)
    wp.cmd_versions()
    wp_dialogs.press("&Restore", 0)
    assert editor.control.value == "The first version\n"
    key = wp.local.copy_for_path(path).key
    kept = wp.local.versions(key)[0]
    assert kept.reason == lc.REASON_BEFORE_RESTORE
    assert kept.text == "New unsaved writing\n"
    assert "your text before is in Previous Versions" in editor.announced[-1]


def test_closing_previous_versions_changes_nothing(
    connected: Path, wp_site: Any, wp_dialogs: Any
) -> None:
    editor = _Editor()
    wp = _commands(_lite_host(editor), connected, wp_site)
    path = _page_with_history(wp, editor, wp_site)
    before = wp.local.versions(wp.local.copy_for_path(path).key)
    wp.cmd_versions()  # shown, then closed without choosing Restore
    assert editor.control.value == "New unsaved writing\n"
    assert wp.local.versions(wp.local.copy_for_path(path).key) == before


def test_a_document_switch_while_the_history_loads_restores_nothing(
    connected: Path, wp_site: Any, wp_dialogs: Any, tmp_path: Path
) -> None:
    editor = _Editor()
    wp = _commands(_quill_host(editor), connected, wp_site)
    path = _page_with_history(wp, editor, wp_site)
    other = tmp_path / "letter.txt"
    other.write_text("A letter\n", encoding="utf-8")

    def switch(_request: Any, _query: Any) -> list[Any]:
        editor.open(other)
        return []

    wp_site.on("GET", f"{API}/pages/41/revisions", switch)
    wp.cmd_versions()
    assert wp_dialogs.list_windows == []
    assert editor.control.value == "A letter\n"
    assert "no longer the document in front" in editor.announced[-1]

    # Back in front, and switched away again before pressing Restore.
    editor.open(path)
    wp_site.on("GET", f"{API}/pages/41/revisions", [])
    wp.cmd_versions()
    editor.open(other)
    wp_dialogs.press("&Restore", 0)
    assert editor.control.value == "A letter\n"
    assert "nothing was restored" in editor.announced[-1]
