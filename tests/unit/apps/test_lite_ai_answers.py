"""Tools > AI, 2026-10-15: where answers go, Review Changes, the Chat Key, the
Prompt Library on the free AI, and Web Searches Left.

Every handler is **called** in a lambda, never named in a parametrized string:
``quill.tools.lite_command_coverage`` finds coverage by walking the AST for real
calls (tests/unit/apps/test_lite_ai.py says why that matters). The windows are
patched where the shared mixin looks them up -- ``quill.ui.hosted_ai_pad`` for
the pad and the result window, ``quill.ui.prompt_library_dialog`` for the
library, ``quill.ui.ai_diff_review_dialog`` for the review -- and the clipboard
is the mixin's own seam, so nothing here touches the real one.
"""

from __future__ import annotations

import pytest


class _Recorder:
    """Records how a window was built, and pretends to be one."""

    last: dict | None = None

    def __init__(self, *args, **kwargs):
        type(self).last = {"args": args, "kwargs": kwargs}

    def Show(self):  # noqa: N802 - wx API shape
        pass

    def Raise(self):  # noqa: N802 - wx API shape
        pass

    def SetFocus(self):  # noqa: N802 - wx API shape
        pass

    def Bind(self, *_args, **_kwargs):  # noqa: N802 - wx API shape
        pass


@pytest.fixture
def frames(monkeypatch):
    import quill.ui.hosted_ai_pad as pad

    made = {}
    for name in ("AiPadFrame", "AiResultFrame"):
        cls = type(name, (_Recorder,), {"last": None})
        monkeypatch.setattr(pad, name, cls)
        made[name] = cls
    return made


class _Quota:
    monthly_cap = 90
    daily_cap = 19


class _Service:
    """Connected to the free AI, agreement accepted (patched below)."""

    signed_in = True
    own_key_active = False
    direct = False

    class limits:  # noqa: N801 - the attribute the mixin reads
        max_input_tokens = 3000
        max_chunks_per_request = 3

    def __init__(self):
        self.asked: list[tuple] = []
        self.searches = None

    def refresh_limits(self, on_done=None):
        pass

    def unavailable_reason(self, feature=""):
        return ""

    def ask(self, feature, prompt, chunks, *, on_done, on_error, **_kw):
        self.asked.append((feature, prompt, chunks))
        on_done("The answer.", _Quota())

    def fetch_web_searches(self, *, on_done, on_error):
        if isinstance(self.searches, str):
            on_error(self.searches)
        else:
            on_done(*self.searches)


@pytest.fixture
def connected(monkeypatch):
    from quill.ui.hosted_ai_commands import HostedAiMixin

    monkeypatch.setattr(HostedAiMixin, "_ai_privacy_accepted", lambda _self: True)
    return _Service()


# --------------------------------------------------------------------------- #
# The Chat Key
# --------------------------------------------------------------------------- #


def test_the_chat_key_opens_the_pad_on_a_general_question_ready_to_type(
    lite_window, frames, monkeypatch, connected
):
    win = lite_window("Some text.")
    monkeypatch.setattr(win, "_ai_service", lambda: connected)

    (lambda w: w.cmd_ai_chat_key())(win)

    built = frames["AiPadFrame"].last["kwargs"]
    assert built["initial_action"] == "ask"
    assert built["focus_prompt"] is True
    # The editor can remember a delivery choice, so the pad offers it.
    assert built["delivery"] == "window"
    assert callable(built["on_delivery"])


def test_the_chat_key_offers_the_way_in_when_not_connected(lite_window, frames, monkeypatch):
    from quill.ui.hosted_ai_commands import HostedAiMixin

    monkeypatch.setattr(HostedAiMixin, "_ai_privacy_accepted", lambda _self: True)
    win = lite_window("text")
    signed_out = _Service()
    signed_out.signed_in = False
    monkeypatch.setattr(win, "_ai_service", lambda: signed_out)
    monkeypatch.setattr(win, "cmd_ai_sign_in", lambda: None)

    (lambda w: w.cmd_ai_chat_key())(win)

    assert frames["AiPadFrame"].last is None
    assert any("not connected" in said for said in win.announcements)


# --------------------------------------------------------------------------- #
# Where answers go
# --------------------------------------------------------------------------- #


def test_choosing_a_delivery_mode_is_remembered(lite_window):
    win = lite_window("text")
    win._set_ai_delivery("clipboard")
    assert win.app.settings.ai_answer_delivery == "clipboard"
    assert win.app.saved_settings == 1
    assert win._ai_delivery() == "clipboard"
    win._set_ai_delivery("nonsense")
    assert win._ai_delivery() == "window"


def test_the_window_is_the_default_and_offers_review_beside_replace(
    lite_window, frames, monkeypatch, connected
):
    win = lite_window("The quick brown fox.")
    monkeypatch.setattr(win, "_ai_service", lambda: connected)

    win._show_ai_result("rewrite", "The fast brown fox.", "", 0, 20, "The quick brown fox.", "")

    built = frames["AiResultFrame"].last["kwargs"]
    assert built["on_replace"] is not None
    assert built["on_review"] is not None
    assert win.control.GetValue() == "The quick brown fox."


def test_no_review_when_there_is_nothing_to_replace(lite_window, frames, monkeypatch, connected):
    win = lite_window("Different text now.")
    monkeypatch.setattr(win, "_ai_service", lambda: connected)

    win._show_ai_result("rewrite", "Answer.", "", 0, 9, "Original.", "")

    built = frames["AiResultFrame"].last["kwargs"]
    assert built["on_replace"] is None
    assert built["on_review"] is None


def test_at_the_cursor_the_answer_goes_in_as_one_edit_and_is_said(lite_window, frames):
    win = lite_window("Hello world.", cursor=5)
    win.app.settings.ai_answer_delivery = "cursor"

    win._show_ai_result("ask", " there", "", 0, 0, "", "ask")

    assert win.control.GetValue() == "Hello there world."
    assert frames["AiResultFrame"].last is None
    assert any("inserted at the cursor" in said for said in win.announcements)


def test_on_the_clipboard_the_document_is_untouched(lite_window, frames, monkeypatch):
    win = lite_window("Hello.")
    win.app.settings.ai_answer_delivery = "clipboard"
    copied: list[str] = []
    monkeypatch.setattr(win, "_ai_copy_to_clipboard", lambda text: copied.append(text) or True)

    win._show_ai_result("ask", "An answer.", "", 0, 0, "", "ask")

    assert copied == ["An answer."]
    assert win.control.GetValue() == "Hello."
    assert frames["AiResultFrame"].last is None
    assert any("copied to the clipboard" in said for said in win.announcements)


def test_a_busy_clipboard_falls_back_to_the_window(lite_window, frames, monkeypatch):
    win = lite_window("Hello.")
    win.app.settings.ai_answer_delivery = "clipboard"
    monkeypatch.setattr(win, "_ai_copy_to_clipboard", lambda _text: False)

    win._show_ai_result("ask", "An answer.", "", 0, 0, "", "ask")

    assert frames["AiResultFrame"].last is not None


# --------------------------------------------------------------------------- #
# Review Changes
# --------------------------------------------------------------------------- #


def test_review_changes_applies_only_what_was_accepted_as_one_edit(lite_window, monkeypatch):
    import quill.ui.ai_diff_review_dialog as review

    seen = {}

    class FakeReview:
        def __init__(self, _parent, *, title, original_text, revised_text, on_apply, announce):
            seen.update(title=title, original=original_text, revised=revised_text)
            self._apply = on_apply

        def show_modal(self):
            self._apply("The rapid brown fox.")

    monkeypatch.setattr(review, "DiffReviewDialog", FakeReview)
    win = lite_window("The quick brown fox. Next.")

    win._review_ai_answer(0, 20, "The quick brown fox.", "The fast brown fox.")

    assert seen["title"] == "Review AI Changes"
    assert seen["original"] == "The quick brown fox."
    assert win.control.GetValue() == "The rapid brown fox. Next."


def test_review_refuses_when_the_text_moved(lite_window, monkeypatch):
    import quill.ui.ai_diff_review_dialog as review

    monkeypatch.setattr(review, "DiffReviewDialog", None)  # must not be reached
    win = lite_window("Something else entirely.")

    win._review_ai_answer(0, 9, "Original.", "Answer.")

    assert win.control.GetValue() == "Something else entirely."
    assert any("has changed" in said for said in win.announcements)


# --------------------------------------------------------------------------- #
# The Prompt Library, on the free AI
# --------------------------------------------------------------------------- #


def _fake_library_dialog(monkeypatch, chosen):
    import quill.ui.dialog_contract as contract
    import quill.ui.prompt_library_dialog as pld

    seen = {}

    class FakeDialog:
        def __init__(self, _parent, library, _settings, **kwargs):
            seen.update(library=library, **kwargs)
            self.dialog = object()
            self.chosen = chosen

        def close(self):
            seen["closed"] = True

    monkeypatch.setattr(pld, "PromptLibraryDialog", FakeDialog)
    monkeypatch.setattr(contract, "show_modal_dialog", lambda *_a, **_k: 5101)
    return seen


def test_the_prompt_library_runs_the_chosen_prompt_on_the_free_ai(
    lite_window, frames, monkeypatch, connected
):
    seen = _fake_library_dialog(monkeypatch, ("Make Concise", "Shorten this: Hello there."))
    win = lite_window("Hello there. More.")
    win.control.SetSelection(0, 12)
    monkeypatch.setattr(win, "_ai_service", lambda: connected)

    (lambda w: w.cmd_ai_prompt_library())(win)

    assert seen["hosted"] is True
    assert seen["selection"] == "Hello there."
    assert seen["closed"] is True
    # The library is the editor's own prompts.json, QUILL's format.
    assert str(seen["library"]._path).endswith("prompts.json")
    assert connected.asked == [("ask", "Shorten this: Hello there.", None)]
    built = frames["AiResultFrame"].last["kwargs"]
    assert built["text"] == "The answer."
    # The selection is still there, so the answer can replace it -- or be reviewed.
    assert built["on_replace"] is not None
    assert built["on_review"] is not None


def test_closing_the_library_sends_nothing(lite_window, frames, monkeypatch, connected):
    _fake_library_dialog(monkeypatch, None)
    win = lite_window("text")
    monkeypatch.setattr(win, "_ai_service", lambda: connected)

    (lambda w: w.cmd_ai_prompt_library())(win)

    assert connected.asked == []
    assert frames["AiResultFrame"].last is None


def test_an_oversized_prompt_is_refused_before_sending(lite_window, monkeypatch, connected):
    _fake_library_dialog(monkeypatch, ("Big", "word " * 20000))
    win = lite_window("text")
    monkeypatch.setattr(win, "_ai_service", lambda: connected)

    (lambda w: w.cmd_ai_prompt_library())(win)

    assert connected.asked == []
    assert any("Nothing was sent" in said for said in win.announcements)


# --------------------------------------------------------------------------- #
# Web Searches Left
# --------------------------------------------------------------------------- #


def test_web_searches_left_says_the_count(lite_window, monkeypatch, connected):
    from quill.core.ai.gateway_client import GatewayQuota

    connected.searches = (
        True,
        GatewayQuota(web_search_cap=10, web_searches_used=3, reset_at="2026-11-01T00:00:00"),
    )
    win = lite_window("text")
    monkeypatch.setattr(win, "_ai_service", lambda: connected)

    (lambda w: w.cmd_ai_web_searches())(win)

    assert win.announcements[-1].startswith("7 of 10 web searches left this month.")


def test_web_searches_left_says_when_the_service_has_none(lite_window, monkeypatch, connected):
    connected.searches = (False, None)
    win = lite_window("text")
    monkeypatch.setattr(win, "_ai_service", lambda: connected)

    (lambda w: w.cmd_ai_web_searches())(win)

    assert "not offering web search" in win.announcements[-1]


def test_web_searches_left_says_a_failure(lite_window, monkeypatch, connected):
    connected.searches = "The service is not answering."
    win = lite_window("text")
    monkeypatch.setattr(win, "_ai_service", lambda: connected)

    (lambda w: w.cmd_ai_web_searches())(win)

    assert win.announcements[-1].startswith("Web searches could not be checked")


def test_web_searches_on_an_own_key_say_it_is_the_free_services(lite_window, monkeypatch):
    win = lite_window("text")
    monkeypatch.setattr(win, "_ai_direct", lambda: True)

    (lambda w: w.cmd_ai_web_searches())(win)

    assert "part of QUILL's free AI" in win.announcements[-1]


def test_web_searches_refuse_when_the_area_is_off(lite_window, monkeypatch):
    win = lite_window("text")
    monkeypatch.setattr(win.app, "feature_enabled", lambda area: area != "hosted_ai")

    (lambda w: w.cmd_ai_web_searches())(win)

    assert "switched off" in win.announcements[-1]
