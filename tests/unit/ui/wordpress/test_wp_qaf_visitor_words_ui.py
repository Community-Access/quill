"""Visitor Words for Forms in the Workbench window (WP-R-050): every path of the command, called.

The fake site answers as the route QUILL asks QUILL Accessible Forms for
(``qaf/v1/visitor-words``); a site without it answers 404, as WordPress does
for a route nobody registered. Dialogs answer from queues; work runs inline.
"""

from __future__ import annotations

import copy
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress.api import WordPressApiError  # noqa: E402
from quill.core.wordpress.workbench_actions import WORDPRESS_ACTIONS, command  # noqa: E402
from tests.unit.ui.wordpress.test_wp_qaf_spam_ui import REF, FakeApi, _make  # noqa: E402

DEFAULTS = {
    "form_success": "Form submitted successfully!",
    "held_confirmation": "Thank you. A person will read it.",
}


class WordsApi(FakeApi):
    def __init__(self, *, has_route: bool = True) -> None:
        super().__init__()
        self.has_route = has_route
        self.by_language = {"en_US": {}, "fr_FR": {"form_success": "Merci."}}
        self.words_revision = 1

    def get(self, route: str, **params: Any) -> Any:
        if route == "qaf/v1/visitor-words":
            self.reads.append(route)
            if not self.has_route:
                raise WordPressApiError("No route was found.", status=404)
            language = params.get("language") or "en_US"
            return {
                "language": language,
                "languages": ["en_US", "fr_FR"],
                "words": copy.deepcopy(self.by_language[language]),
                "defaults": dict(DEFAULTS),
                "revision": f"w{self.words_revision}",
                "can_edit": True,
            }
        return super().get(route, **params)

    def post(self, route: str, body: Any = None, **params: Any) -> Any:
        if route != "qaf/v1/visitor-words":
            return super().post(route, body, **params)
        self.sent.append(("POST", route, body))
        if body["if_revision"] != f"w{self.words_revision}":
            raise WordPressApiError("changed", status=409)
        words = self.by_language[body["language"]]
        for key, text in body["words"].items():
            if text:
                words[key] = text
            else:
                words.pop(key, None)
        self.words_revision += 1
        return {"ok": True}


@pytest.fixture
def words_bench(wx_session_app, tmp_path, monkeypatch):
    frame = _make(monkeypatch, tmp_path, WordsApi())
    yield frame
    frame.frame.Destroy()


def test_the_command_is_on_every_sites_context_menu(words_bench) -> None:
    verbs = [r.command_id for r in WORDPRESS_ACTIONS.rows_for("site")]
    assert hasattr(words_bench.provider, "do_visitor_words")
    assert command("visitor_words") in verbs


def test_a_held_as_spam_confirmation_is_changed_after_a_preview_and_read_back(words_bench) -> None:
    a, api = words_bench.answers, words_bench.api
    a.choices += [0, 9]  # English; the Held as Spam confirmation
    a.texts += ["Thank you. A person reads every message held here, usually within a day."]
    words_bench.provider.do_visitor_words(REF, None)
    assert api.sent[-1] == (
        "POST",
        "qaf/v1/visitor-words",
        {
            "language": "en_US",
            "words": {
                "held_confirmation": "Thank you. A person reads every message held here, "
                "usually within a day."
            },
            "if_revision": "w1",
        },
    )
    assert "Was: Thank you. A person will read it." in a.previews[-1]["lines"]
    assert (
        words_bench.said[-1] == "Saved Held as Spam confirmation, and read it back from the site."
    )


def test_each_language_has_its_own_words_and_empty_puts_the_plugins_back(words_bench) -> None:
    a, api = words_bench.answers, words_bench.api
    a.choices += [1, 0]  # French; After a form is sent
    a.texts += [""]
    words_bench.provider.do_visitor_words(REF, None)
    assert api.sent[-1][2]["language"] == "fr_FR"
    assert api.sent[-1][2]["words"] == {"form_success": ""}
    assert api.by_language["fr_FR"] == {}
    assert words_bench.said[-1].startswith("After a form is sent is back to the plugin's own")


def test_markup_and_unchanged_words_send_nothing(words_bench) -> None:
    a, api = words_bench.answers, words_bench.api
    a.choices += [0, 0]
    a.texts += ["<b>Thanks</b>"]
    words_bench.provider.do_visitor_words(REF, None)
    assert words_bench.said[-1].startswith("Visitor words are plain text")
    a.choices += [0, 0]
    a.texts += ["Form submitted successfully!"]
    words_bench.provider.do_visitor_words(REF, None)
    assert words_bench.said[-1] == "That is how it is already. Nothing was changed."
    a.choices += [None]
    words_bench.provider.do_visitor_words(REF, None)
    assert not [s for s in api.sent if s[1] == "qaf/v1/visitor-words"]


def test_words_changed_on_the_site_meanwhile_are_not_overwritten(words_bench) -> None:
    from quill.core.wordpress import workbench_qaf_visitor_words as vw

    api = words_bench.api
    held = vw.read_words(api, "qaf/v1")
    api.words_revision += 1  # somebody saved in wp-admin
    with pytest.raises(vw.WordsConflict):
        vw.save_words(api, "qaf/v1", held, "form_success", "Thanks!")
    assert not [s for s in api.sent if s[1] == "qaf/v1/visitor-words"]


def test_a_qaf_without_the_route_says_so(wx_session_app, tmp_path, monkeypatch) -> None:
    frame = _make(monkeypatch, tmp_path, WordsApi(has_route=False))
    try:
        frame.provider.do_visitor_words(REF, None)
        assert "no route for visitor words yet (qaf/v1/visitor-words)" in frame.said[-1]
    finally:
        frame.frame.Destroy()
