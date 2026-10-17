"""The wx-free halves of 2026-10-15's hosted-AI work.

Answer delivery's vocabulary, saved conversations in a chosen folder, the
Prompt Library's one fill function, and web search as the client reads it from
``/v1/config`` and ``/v1/quota`` -- including from a server that predates it,
which must read as "off", never as an error.
"""

from __future__ import annotations

from quill.core.ai import answer_delivery as delivery
from quill.core.ai import sessions
from quill.core.ai.gateway_client import GatewayClient, GatewayLimits, GatewayQuota
from quill.core.ai.gateway_quota_text import WEB_SEARCH_OFF, describe_quota, describe_web_searches
from quill.core.prompt_fill import fill_prompt

# --------------------------------------------------------------------------- #
# Answer delivery
# --------------------------------------------------------------------------- #


def test_the_window_is_the_default_and_anything_unknown_is_the_window():
    assert delivery.DEFAULT == delivery.WINDOW == delivery.DELIVERY_MODES[0]
    assert delivery.normalise("CURSOR ") == "cursor"
    assert delivery.normalise("clipboard") == "clipboard"
    assert delivery.normalise("") == "window"
    assert delivery.normalise("speakers") == "window"
    assert set(delivery.DELIVERY_LABELS) == set(delivery.DELIVERY_MODES)


def test_both_editors_store_the_mode_under_one_name():
    from quill.core.lite.settings import Settings as LiteSettings
    from quill.core.settings import Settings as QuillSettings

    assert LiteSettings().ai_answer_delivery == "window"
    assert QuillSettings().ai_answer_delivery == "window"


# --------------------------------------------------------------------------- #
# Saved conversations
# --------------------------------------------------------------------------- #


def test_an_exchange_is_saved_in_the_folder_it_is_given(tmp_path):
    folder = tmp_path / "ai-sessions"
    session = sessions.record_exchange(None, "What is a haiku?", "A short poem.", directory=folder)
    session = sessions.record_exchange(session, "And a tanka?", "A longer one.", directory=folder)

    listed = sessions.list_sessions(directory=folder)
    assert [row.title for row in listed] == ["What is a haiku?"]
    assert listed[0].turn_count == 4
    loaded = sessions.load_session(session.session_id, directory=folder)
    assert [turn.text for turn in sessions.current_path(loaded)] == [
        "What is a haiku?",
        "A short poem.",
        "And a tanka?",
        "A longer one.",
    ]
    assert sessions.delete_session(session.session_id, directory=folder)
    assert sessions.list_sessions(directory=folder) == ()


def test_an_empty_side_records_nothing(tmp_path):
    assert sessions.record_exchange(None, "", "answer", directory=tmp_path) is None
    assert sessions.list_sessions(directory=tmp_path) == ()


def test_without_a_folder_it_is_quills_own(tmp_path, monkeypatch):
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    assert sessions.sessions_dir().name == sessions.SESSIONS_FOLDER


# --------------------------------------------------------------------------- #
# The Prompt Library's fill
# --------------------------------------------------------------------------- #


def test_a_prompt_is_filled_the_same_way_on_either_ai():
    text = "Title {title}. Fix: {selection}. Whole: {document}"
    assert fill_prompt(text, selection="abc", document="abc def", title="Notes") == (
        "Title Notes. Fix: abc. Whole: abc def"
    )
    # No document: the input stands in for it, as it always has.
    assert fill_prompt("{document}", selection="abc") == "abc"


# --------------------------------------------------------------------------- #
# Web search, as the client reads it
# --------------------------------------------------------------------------- #


def test_limits_read_the_web_search_entry():
    limits = GatewayLimits.from_json({"web_search": {"enabled": True, "monthly_cap": 10}})
    assert limits.web_search_enabled is True
    assert limits.web_search_monthly_cap == 10


def test_a_server_without_web_search_reads_as_off():
    assert GatewayLimits.from_json({}).web_search_enabled is False
    assert GatewayLimits.from_json({"web_search": "yes"}).web_search_monthly_cap == 0
    quota = GatewayQuota.from_json({"monthly_request_cap": 100})
    assert quota.web_search_cap == 0
    assert quota.web_searches_left == 0


def test_quota_reads_the_searches_used():
    quota = GatewayQuota.from_json({"web_search_monthly_cap": 10, "web_searches_used": "4"})
    assert quota.web_searches_left == 6
    assert GatewayQuota.from_json({"web_searches_used": None}).web_searches_used == 0


def test_the_count_in_words():
    quota = GatewayQuota(web_search_cap=10, web_searches_used=9, reset_at="2026-11-01T00:00:00")
    assert describe_web_searches(True, quota) == (
        "1 of 10 web search left this month. They start again 2026-11-01."
    )
    used_up = GatewayQuota(web_search_cap=10, web_searches_used=12)
    assert describe_web_searches(True, used_up).startswith("No web searches left")
    assert describe_web_searches(False, quota) == WEB_SEARCH_OFF
    assert describe_web_searches(True, None) == WEB_SEARCH_OFF


def test_usage_shows_web_searches_only_when_there_are_any():
    with_searches = GatewayQuota(monthly_cap=100, web_search_cap=10, web_searches_used=2)
    assert "Web searches\n8 of 10" in describe_quota(with_searches)
    assert "Web searches" not in describe_quota(GatewayQuota(monthly_cap=100))


def test_the_client_fetches_both_through_its_one_seam():
    seen = []

    def opener(url, *, token="", body=None, method=""):
        seen.append(url)
        if url.endswith("/v1/config"):
            return {"web_search": {"enabled": True, "monthly_cap": 10}}
        return {"web_search_monthly_cap": 10, "web_searches_used": 1}

    client = GatewayClient("https://example.invalid", "t", opener=opener)
    assert client.fetch_limits().web_search_enabled
    assert client.fetch_quota().web_searches_left == 9
    assert seen == ["https://example.invalid/v1/config", "https://example.invalid/v1/quota"]
