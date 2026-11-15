"""QUILL Accessible Forms' spam settings in the Workbench window: every new command, called.

The real provider and frame over a fake site answering as QAF's spam routes do
(``S:\\code\\qaf`` includes/spam/class-qaf-spam-rest.php); dialogs answer from
queues and background work runs inline. Each change is previewed, read again
before it is sent, and read back after; the OOPSpam key is never said or shown.
"""

from __future__ import annotations

import copy
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress import site_taxonomies as tx  # noqa: E402
from quill.core.wordpress.api import WordPressApiError  # noqa: E402
from quill.core.wordpress.sites import SiteProfile, SiteStore  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui import wordpress_workbench_dialogs as wdlg  # noqa: E402
from quill.ui import workbench_sheet_editor as editor  # noqa: E402
from quill.ui.wordpress_workbench_window import WordPressWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402

SITE = "Community Radio"
KEY = "secret-oopspam-key-123"
PROVIDERS = (
    "honeypot", "time", "links", "patterns", "blocklist", "rate_limit", "token",
    "captcha", "akismet", "oopspam", "cleantalk", "shield", "altcha", "challenge",
)  # fmt: skip


class _Address:
    is_wpcom = False
    wpcom_site = ""
    site_url = "https://radio.example"


class _Auth:
    kind = "app_password"
    username = "jeff"


class FakeApi:
    def __init__(self, namespace: str = "qaf/v1") -> None:
        self.site_name = SITE
        self.address = _Address()
        self.auth = _Auth()
        self.namespace = namespace
        self.sent: list[tuple[str, str, Any]] = []
        self.reads: list[str] = []
        self.key = ""
        self.revision = 1
        self.changed_elsewhere = False
        self.state = {
            "providers": [{"id": p, "label": p, "enabled": p == "honeypot"} for p in PROVIDERS],
            "limits": {"min_seconds": 3, "max_links": 3, "oopspam_threshold": 3,
                       "altcha_max_number": 50000, "use_disallowed": True,
                       "use_moderation": True},
            "questions": {"mode": "auto", "form_modes": {}, "send_anyway_after": 3,
                          "kinds": {"sense": True, "maths": False}, "site_questions": 1,
                          "this_week": {"week": "2026-W46", "asked": 1}},
        }  # fmt: skip
        self.bank = [{"id": "aaaaaaaaaaaa", "question": "What do cows say?", "answers": ["moo"]}]

    def _spam(self) -> dict[str, Any]:
        if self.changed_elsewhere:
            self.revision += 1
            self.changed_elsewhere = False
        return {
            **copy.deepcopy(self.state),
            "oopspam_key_saved": bool(self.key),
            "revision": f"r{self.revision}",
            "can_edit": True,
        }

    def get(self, route: str, **_p: Any) -> Any:
        self.reads.append(route)
        if route == "wp/v2/users/me":
            caps = {"manage_options": True, "edit_posts": True}
            return {"id": 1, "name": "Jeff", "roles": ["administrator"], "capabilities": caps}
        if route == "":
            return {"name": SITE, "namespaces": ["wp/v2", self.namespace]}
        if route == f"{self.namespace}/spam":
            return self._spam()
        if route == f"{self.namespace}/spam/weeks":
            return {"weeks": [{"week": "2026-W46", "asked": 1}, {"week": "2026-W45", "asked": 9,
                                                                 "failed": 2}]}  # fmt: skip
        if route == f"{self.namespace}/spam/questions":
            return {"questions": copy.deepcopy(self.bank)}
        if route == "wp/v2/settings":
            return {"default_comment_status": "open"}
        return []

    def iter_collection(self, *_a: Any, **_k: Any):
        yield from ()

    def post(self, route: str, body: Any = None, **_p: Any) -> Any:
        self.sent.append(("POST", route, body))
        if route == "qaf/v1/spam":
            if body.get("if_revision") != f"r{self.revision}":
                raise WordPressApiError("changed", status=409)
            for p in self.state["providers"]:
                if p["id"] in (body.get("providers") or {}):
                    p["enabled"] = body["providers"][p["id"]]
            for k in ("max_links", "min_seconds"):
                if k in body:
                    self.state["limits"][k] = body[k]
            if "oopspam_api_key" in body:
                self.key = body["oopspam_api_key"]
            self.revision += 1
            return self._spam()
        if route == "qaf/v1/spam/questions":
            item = {"id": "bbbbbbbbbbbb", **body}
            self.bank.append(item)
            return item
        qid = route.rsplit("/", 1)[1]
        for i, q in enumerate(self.bank):
            if q["id"] == qid:
                self.bank[i] = {**q, **body, "id": "cccccccccccc"}
                return self.bank[i]
        raise WordPressApiError("That question is not in the bank.", status=404)

    def delete(self, route: str, **_p: Any) -> Any:
        self.sent.append(("DELETE", route, None))
        qid = route.rsplit("/", 1)[1]
        self.bank = [q for q in self.bank if q["id"] != qid]
        return {"deleted": True}


class _Host:
    def __init__(self, said: list[str]) -> None:
        self.said = said
        self.parent = None

    def announce(self, text: str) -> None:
        self.said.append(text)

    def open_in_browser(self, url: str) -> None:
        pass


class _Commands:
    def __init__(self, said: list[str]) -> None:
        self.host = _Host(said)

    def sites(self) -> SiteStore:
        return SiteStore([SiteProfile("s1", SITE, "https://radio.example", "jeff")], "s1")


def _inline(_name: str, work: Any, done: Any, failed: Any) -> None:
    try:
        result = work()
    except Exception as exc:  # noqa: BLE001
        failed(exc)
        return
    done(result)


class Answers:
    def __init__(self) -> None:
        self.texts: list[str | None] = []
        self.choices: list[int | None] = []
        self.previews: list[dict[str, Any]] = []
        self.reports: list[dict[str, Any]] = []
        self.sheets: list[Any] = []
        self.yes = True


def _make(monkeypatch, tmp_path, api: FakeApi):
    tx.clear_cache()
    said: list[str] = []
    answers = Answers()
    monkeypatch.setattr(dlg, "ask_text", lambda *_a, **_k: answers.texts.pop(0))
    monkeypatch.setattr(dlg, "ask_choice", lambda *_a, **_k: answers.choices.pop(0))
    monkeypatch.setattr(dlg, "show_report", lambda *_a, **k: answers.reports.append(k))
    monkeypatch.setattr(
        wdlg, "ask_preview", lambda *_a, **k: answers.previews.append(k) or answers.yes
    )
    monkeypatch.setattr(
        editor.WorkbenchSheetEditor, "show", lambda self: answers.sheets.append(self) or 0
    )
    provider = WordPressWorkbenchProvider(
        _Commands(said), announce=said.append, data_dir=tmp_path, api_for=lambda _p: api
    )
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said, frame.api, frame.answers = said, api, answers  # type: ignore[attr-defined]
    return frame


@pytest.fixture
def bench(wx_session_app, tmp_path, monkeypatch):
    frame = _make(monkeypatch, tmp_path, FakeApi())
    yield frame
    frame.frame.Destroy()
    tx.clear_cache()


@pytest.fixture
def old_bench(wx_session_app, tmp_path, monkeypatch):
    frame = _make(monkeypatch, tmp_path, FakeApi("baf/v1"))
    yield frame
    frame.frame.Destroy()
    tx.clear_cache()


REF = NodeRef("site", "overview", SITE)


def _open_spam_page(bench) -> Any:
    bench.provider.do_site_sheet(REF, None)
    assert bench.answers.sheets, bench.said
    return bench.answers.sheets[-1]


def test_the_spam_page_is_editable_and_says_which_plugin_the_site_runs(bench) -> None:
    sheet = _open_spam_page(bench)
    spam = next(p for p in sheet.sheet.pages if p.key == "spam")
    keys = [f.key for f in spam.fields]
    assert "qaf_provider_akismet" in keys and "qaf_oopspam_key" in keys and "spam_weeks" in keys
    assert sheet.editable(sheet.sheet.field("qaf_max_links"))
    assert sheet.state.loaded["form_spam"].startswith(
        "This site runs QUILL Accessible Forms (qaf/v1)."
    )
    assert "2026-W45: 9 asked" in sheet.state.loaded["spam_weeks"]
    assert sheet.state.loaded["qaf_oopspam_key"] == ""
    assert "never shows, speaks or keeps" in sheet._help(sheet.sheet.field("qaf_oopspam_key"))


def test_saving_the_spam_page_previews_rereads_sends_and_verifies(bench) -> None:
    sheet = _open_spam_page(bench)
    sheet.state.edited.update({
        "qaf_provider_akismet": True,
        "qaf_max_links": "5",
        "qaf_oopspam_key": KEY,
    })
    assert sheet._on_save(sheet.state) is True
    preview = bench.answers.previews[-1]
    assert "Most links in an answer: 5." in preview["lines"]
    assert all(KEY not in line for line in preview["lines"])
    posted = [s for s in bench.api.sent if s[1] == "qaf/v1/spam"]
    sent = {"providers": {"akismet": True}, "max_links": 5, "oopspam_api_key": KEY}
    assert posted == [("POST", "qaf/v1/spam", {**sent, "if_revision": "r1"})]
    assert bench.api.reads.count("qaf/v1/spam") == 3, "read for the page, again, and back"
    assert bench.said[-1] == "Saved 3 spam settings, and read them back from the site."
    assert all(KEY not in line for line in bench.said)
    assert sheet.state.edited["qaf_oopspam_key"] == "", "the key leaves the sheet's values"


def test_a_change_made_on_the_site_since_reading_sends_nothing(bench) -> None:
    sheet = _open_spam_page(bench)
    bench.api.changed_elsewhere = True
    sheet.state.edited["qaf_max_links"] = "7"
    sheet._on_save(sheet.state)
    assert [s for s in bench.api.sent if s[1] == "qaf/v1/spam"] == []
    assert "nothing was sent" in bench.said[-1]


def test_a_declined_preview_or_a_bad_number_sends_nothing(bench) -> None:
    sheet = _open_spam_page(bench)
    sheet.state.edited["qaf_max_links"] = "99"
    assert sheet._on_save(sheet.state) is False
    assert "from 0 to 50" in bench.said[-1]
    sheet.state.edited["qaf_max_links"] = "4"
    bench.answers.yes = False
    assert sheet._on_save(sheet.state) is False
    assert bench.api.sent == []


def test_a_site_on_the_old_name_shows_the_settings_read_only_with_why(old_bench) -> None:
    sheet = _open_spam_page(old_bench)
    assert sheet._on_save is None
    help_text = sheet._help(sheet.sheet.field("qaf_max_links"))
    assert "older BITS Accessible Forms (baf/v1)" in help_text
    assert sheet.state.loaded["form_spam"].startswith("This site runs the older BITS")
    old_bench.provider.do_spam_questions(REF, None)
    assert "older BITS Accessible Forms" in old_bench.said[-1]
    assert old_bench.api.sent == []


def test_spam_questions_add_change_and_remove_after_previews(bench) -> None:
    a, api = bench.answers, bench.api
    a.choices += [0]
    a.texts += ["Which is colder, snow or soup?", "snow; Snow"]
    bench.provider.do_spam_questions(REF, None)
    assert api.sent[-1] == ("POST", "qaf/v1/spam/questions",
                            {"question": "Which is colder, snow or soup?",
                             "answers": ["snow", "Snow"]})  # fmt: skip
    assert bench.said[-1].startswith("Added the question.")

    a.choices += [1, 1]  # the first question; change its answers
    a.texts += ["moo; moo moo"]
    bench.provider.do_spam_questions(REF, None)
    assert api.sent[-1] == ("POST", "qaf/v1/spam/questions/aaaaaaaaaaaa",
                            {"answers": ["moo", "moo moo"]})  # fmt: skip
    assert "Was: What do cows say? Right answer: moo." in a.previews[-1]["lines"]
    assert bench.said[-1] == "Changed the question, and read it back from the site."

    a.choices += [1, 2]  # that question again; remove it
    bench.provider.do_spam_questions(REF, None)
    assert api.sent[-1] == ("DELETE", "qaf/v1/spam/questions/cccccccccccc", None)
    assert bench.said[-1].startswith("Removed the question")

    a.choices += [None]
    before = len(api.sent)
    bench.provider.do_spam_questions(REF, None)
    assert len(api.sent) == before, "Cancel changes nothing"


def test_spam_by_week_reads_the_weeks(bench) -> None:
    bench.provider.do_spam_weeks(REF, None)
    report = bench.answers.reports[-1]
    assert report["text"].startswith("This site runs QUILL Accessible Forms (qaf/v1).")
    assert "2026-W45: 9 asked, 0 answered, 2 answered wrongly" in report["text"]
    assert report["help_text"]
