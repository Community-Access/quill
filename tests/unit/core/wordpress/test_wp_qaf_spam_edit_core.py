"""Changing QUILL Accessible Forms' spam settings from the Workbench, wx-free (complete.md WP-C).

The fake site below answers as QAF's own routes do (``S:\\code\\qaf``
includes/spam/class-qaf-spam-rest.php: ``update``, the question bank and
``weeks``), so CI needs no QAF. The PHP side has its own suite
(tests/unit/Spam/SpamSettingsWriteTest.php there).
"""

from __future__ import annotations

import copy
import hashlib
from typing import Any

import pytest

from quill.core.wordpress import workbench_qaf_spam_edit as edit
from quill.core.wordpress.api import WordPressApiError
from quill.core.workbench.properties import FieldChange, SheetSpec

KEY = "secret-oopspam-key-123"


def _state() -> dict[str, Any]:
    return {
        "providers": [{"id": pid, "label": label, "enabled": pid in ("honeypot", "challenge")}
                      for pid, label in edit.PROVIDERS.items()],
        "limits": {"min_seconds": 3, "max_links": 3, "oopspam_threshold": 3,
                   "altcha_max_number": 50000, "use_disallowed": True, "use_moderation": True},
        "questions": {"mode": "auto", "form_modes": {}, "send_anyway_after": 3,
                      "kinds": {"sense": True, "instruction": True, "choice": True,
                                "order": True, "maths": False},
                      "site_questions": 1,
                      "this_week": {"week": "2026-W46", "asked": 0}},
        "oopspam_key_saved": False,
        "revision": "r1",
        "can_edit": True,
    }  # fmt: skip


class Site:
    """QAF's spam routes, in memory, keeping every request it was sent."""

    def __init__(self) -> None:
        self.state = _state()
        self.key = ""
        self.sent: list[tuple[str, str, Any]] = []
        self.bank = [{"id": "aaaaaaaaaaaa", "question": "What do cows say?", "answers": ["moo"]}]
        self.weeks = [
            {"week": "2026-W46", "asked": 2, "passed": 1, "failed": 1, "sent_anyway": 0},
            {"week": "2026-W45", "asked": 40, "passed": 31, "failed": 7, "sent_anyway": 2},
            {"week": "2026-W44", "asked": 25, "passed": 20, "failed": 5, "sent_anyway": 0},
        ]
        self.somebody_else_saves = False
        self.ignore_writes = False

    def _bump(self) -> None:
        self.state["revision"] = "r" + str(int(self.state["revision"][1:]) + 1)

    def get(self, route: str, **params: Any) -> Any:
        if route == "qaf/v1/spam":
            if self.somebody_else_saves:
                self._bump()
                self.somebody_else_saves = False
            return copy.deepcopy(self.state)
        if route == "qaf/v1/spam/questions":
            return {"questions": copy.deepcopy(self.bank), "max": 200, "revision": "x"}
        if route == "qaf/v1/spam/weeks":
            return {"weeks": self.weeks[: int(params.get("weeks", 12))], "kept_days": 100}
        raise WordPressApiError("No route was found.", status=404)

    def post(self, route: str, body: Any = None, **_p: Any) -> Any:
        self.sent.append(("POST", route, body))
        if route == "qaf/v1/spam":
            if body.get("if_revision") != self.state["revision"]:
                raise WordPressApiError("changed", status=409)
            if self.ignore_writes:
                return self.state
            for pid, on in (body.get("providers") or {}).items():
                for p in self.state["providers"]:
                    if p["id"] == pid:
                        p["enabled"] = on
            for k in ("min_seconds", "max_links", "oopspam_threshold", "altcha_max_number",
                      "use_disallowed", "use_moderation"):  # fmt: skip
                if k in body:
                    self.state["limits"][k] = body[k]
            q = self.state["questions"]
            if "challenge_mode" in body:
                q["mode"] = body["challenge_mode"]
            if "send_anyway_after" in body:
                q["send_anyway_after"] = body["send_anyway_after"]
            q["kinds"].update(body.get("challenge_kinds") or {})
            if "oopspam_api_key" in body:
                self.key = body["oopspam_api_key"]
            if body.get("oopspam_api_key_clear"):
                self.key = ""
            self.state["oopspam_key_saved"] = bool(self.key)
            self._bump()
            return self.state
        if route == "qaf/v1/spam/questions":
            item = {"id": _qid(body), **body}
            self.bank.append(item)
            return item
        qid = route.rsplit("/", 1)[1]
        for i, q in enumerate(self.bank):
            if q["id"] == qid:
                new = {**q, **body}
                new["id"] = _qid(new)
                self.bank[i] = new
                return {**new, "replaces": qid}
        raise WordPressApiError("That question is not in the bank.", status=404)

    def delete(self, route: str, **_p: Any) -> Any:
        self.sent.append(("DELETE", route, None))
        qid = route.rsplit("/", 1)[1]
        self.bank = [q for q in self.bank if q["id"] != qid]
        return {"deleted": True}


def _qid(q: dict[str, Any]) -> str:
    return hashlib.sha1((q["question"] + "|" + "|".join(q["answers"])).encode()).hexdigest()[:12]


def _change(key: str, after: Any, before: Any = None) -> FieldChange:
    return FieldChange(key, key, before, after)


# -- which namespace, and who may write -------------------------------------------------------


def test_the_site_says_which_plugin_it_runs_and_why_it_cannot_be_changed() -> None:
    assert edit.namespace_note("qaf/v1") == "This site runs QUILL Accessible Forms (qaf/v1)."
    assert "older BITS Accessible Forms (baf/v1)" in edit.namespace_note("baf/v1")
    assert edit.write_refusal("qaf/v1", _state()) == ""
    assert "older BITS Accessible Forms" in edit.write_refusal("baf/v1", _state())
    old = {k: v for k, v in _state().items() if k not in ("revision", "can_edit")}
    assert "older than the route" in edit.write_refusal("qaf/v1", old)
    assert "Manage Options" in edit.write_refusal("qaf/v1", {**_state(), "can_edit": False})
    assert "does not show" in edit.write_refusal("qaf/v1", None)


# -- the Spam page ------------------------------------------------------------------------------


def test_the_spam_page_gets_a_field_for_every_setting_each_with_help() -> None:
    from quill.core.wordpress.workbench_sheets import SITE_SHEET

    sheet = edit.with_spam_fields(SITE_SHEET)
    assert isinstance(sheet, SheetSpec)
    spam = next(p for p in sheet.pages if p.key == "spam")
    added = [f for f in spam.fields if f.key.startswith("qaf_")]
    assert len(added) == len(edit.spam_fields()) == 14 + 4 + 2 + 1 + 5 + 1 + 2
    assert all(f.help and not f.readonly for f in added)
    assert [p.key for p in sheet.pages] == [p.key for p in SITE_SHEET.pages], "no page moved"
    values = edit.spam_values(_state())
    assert values["qaf_provider_honeypot"] is True and values["qaf_provider_akismet"] is False
    assert values["qaf_max_links"] == "3"
    assert values["qaf_challenge_mode"] == "Only when the other checks are unsure"
    assert values["qaf_oopspam_key"] == "", "the saved key is never put in the field"
    assert set(values) == {f.key for f in added}


def test_only_what_changed_is_sent_under_qafs_names() -> None:
    body = edit.spam_body([
        _change("qaf_provider_akismet", True),
        _change("qaf_max_links", "5"),
        _change("qaf_challenge_mode", "On every form"),
        _change("qaf_kind_maths", True),
        _change("qaf_send_anyway_after", " 2 "),
        _change("qaf_use_moderation", False),
        _change("comment_moderation", "x"),  # the page's own read-only lines are never sent
    ])  # fmt: skip
    assert body == {
        "providers": {"akismet": True},
        "max_links": 5,
        "challenge_mode": "always",
        "challenge_kinds": {"maths": True},
        "send_anyway_after": 2,
        "use_moderation": False,
    }
    with pytest.raises(WordPressApiError, match="from 0 to 50"):
        edit.spam_body([_change("qaf_max_links", "51")])
    with pytest.raises(WordPressApiError, match="from 1 to 10"):
        edit.spam_body([_change("qaf_send_anyway_after", "none")])
    assert edit.spam_body([_change("qaf_oopspam_key", "   ")]) == {}, "an empty key field keeps it"
    with pytest.raises(WordPressApiError, match="not both"):
        edit.spam_body([_change("qaf_oopspam_key", KEY), _change("qaf_oopspam_key_clear", True)])


def test_the_preview_names_every_change_and_never_the_key() -> None:
    body = {"providers": {"akismet": True}, "max_links": 5, "oopspam_api_key": KEY}
    lines = edit.spam_preview(body, "Radio")
    assert lines[0] == "Akismet (sends what visitors type to Akismet): turned on."
    assert "Most links in an answer: 5." in lines
    assert "The OOPSpam key: replaced with the new key you typed." in lines
    assert KEY not in " ".join(lines)


def test_a_save_reads_again_sends_and_verifies() -> None:
    site = Site()
    body = {"providers": {"akismet": True}, "max_links": 5, "oopspam_api_key": KEY}
    said, after = edit.save_spam_settings(site, "qaf/v1", "r1", body)
    assert said == "Saved 3 spam settings, and read them back from the site."
    assert KEY not in said
    assert after["oopspam_key_saved"] is True and after["limits"]["max_links"] == 5
    assert site.sent == [("POST", "qaf/v1/spam", {**body, "if_revision": "r1"})]


def test_a_change_made_elsewhere_since_reading_sends_nothing() -> None:
    site = Site()
    site.somebody_else_saves = True
    with pytest.raises(edit.SpamConflict, match="nothing was sent"):
        edit.save_spam_settings(site, "qaf/v1", "r1", {"max_links": 5})
    assert site.sent == []
    assert issubclass(edit.SpamConflict, WordPressApiError) and edit.SpamConflict.code


def test_a_change_the_site_did_not_keep_is_said() -> None:
    site = Site()
    site.ignore_writes = True
    said, _after = edit.save_spam_settings(site, "qaf/v1", "r1", {"max_links": 5})
    assert said.startswith("Saved 1 spam setting, but reading them back, max links is 3.")


# -- the question bank ------------------------------------------------------------------------


def test_questions_are_listed_added_changed_and_removed_with_a_check_each_time() -> None:
    site = Site()
    found = edit.read_questions(site, "qaf/v1")
    assert edit.question_line(found[0]) == "What do cows say? Right answer: moo."
    assert edit.parse_answers(" snow ; Snow;; snow ") == ["snow", "Snow"]

    said = edit.add_question(site, "qaf/v1", "Which is colder, snow or soup?", ["snow"])
    assert said.startswith("Added the question.")
    new_id = site.bank[-1]["id"]
    assert edit.edit_question(site, "qaf/v1", new_id, answers=["snow", "ice"]) == (
        "Changed the question, and read it back from the site."
    )
    changed_id = site.bank[-1]["id"]
    assert changed_id != new_id
    assert edit.delete_question(site, "qaf/v1", changed_id).startswith("Removed the question")
    assert [q["question"] for q in site.bank] == ["What do cows say?"]
    with pytest.raises(WordPressApiError):
        edit.edit_question(site, "qaf/v1", new_id, question="stale")


# -- past weeks and the weekly Watch ------------------------------------------------------------


def test_past_weeks_read_newest_first() -> None:
    weeks = edit.read_weeks(Site(), "qaf/v1")
    text = edit.weeks_text(weeks)
    assert text.splitlines()[0].startswith("This week, 2026-W46: 2 asked")
    assert "2026-W45: 40 asked, 31 answered, 7 answered wrongly, 2 sent anyway." in text
    assert "older than spam/weeks" in edit.weeks_text(edit.read_weeks(_Older(), "qaf/v1"))


class _Older:
    def get(self, route: str, **_p: Any) -> Any:
        raise WordPressApiError("No route was found.", status=404)


def test_the_weekly_watch_speaks_once_a_week_and_never_on_its_first_look() -> None:
    site = Site()
    week, said = edit.weekly_watch("Radio", site, ["wp/v2", "qaf/v1"], "")
    assert (week, said) == ("2026-W46", []), "the first look only learns"
    assert edit.weekly_watch("Radio", site, ["qaf/v1"], "2026-W46") == ("2026-W46", [])
    week, said = edit.weekly_watch("Radio", site, ["qaf/v1"], "2026-W45")
    assert week == "2026-W46"
    assert said == [
        "Form spam questions on Radio, week 2026-W45: 40 asked, 31 answered, 7 answered "
        "wrongly, 2 sent anyway. Up from 25 asked the week before."
    ]
    assert edit.weekly_watch("Radio", _Older(), ["qaf/v1"], "2026-W40") == ("2026-W40", [])
    assert edit.weekly_watch("Radio", site, ["wp/v2"], "2026-W40") == ("2026-W40", [])


# -- every new command: help, and a key or its reason -------------------------------------------


def test_every_spam_command_has_help_and_a_reason_for_having_no_key() -> None:
    from quill.core.wordpress.workbench_actions import WORDPRESS_ACTIONS, WORDPRESS_KEYS

    site_rows = {r.command_id for r in WORDPRESS_ACTIONS.rows_for("site")}
    for row in edit.QAF_SPAM_ROWS:
        assert row.help, row.command_id
        assert row.command_id in site_rows, row.command_id
        assert WORDPRESS_KEYS.get(row.command_id) or edit.KEYLESS.get(row.command_id)


def test_the_watch_is_offered_runs_in_a_round_and_remembers_its_week(tmp_path) -> None:
    from quill.core.wordpress import workbench_watches as watches

    assert "form_spam" in watches.KINDS, "offered in Workbench Options with the others"
    state = watches.WatchState()
    site = Site()
    assert watches.check([("Radio", site, ["qaf/v1"])], state, ["form_spam"]) == []
    assert state.spam_weeks == {"Radio": "2026-W46"}
    state.spam_weeks["Radio"] = "2026-W45"
    said = watches.check([("Radio", site, ["qaf/v1"])], state, ["form_spam"])
    assert said and said[0].startswith("Form spam questions on Radio, week 2026-W45")
    watches.save_state(state, tmp_path)
    assert watches.load_state(tmp_path).spam_weeks == {"Radio": "2026-W46"}
    assert watches.check([("Radio", site, ["qaf/v1"])], state, ["comment_x"]) == [], (
        "turned off, it asks nothing"
    )
