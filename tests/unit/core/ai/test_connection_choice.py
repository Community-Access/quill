"""The stored choice (codex.md 10A.6), its migration, the rows and the sentences of 10A.5."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from quill.core.ai import connection_choice as choice
from quill.core.ai import connection_usage as usage
from quill.core.ai.chatgpt_usage import LocalCount, local_count, record_request, usage_path
from quill.core.ai.connection_choice import ConnectionFacts
from quill.core.ai.text_only import FAMILY_INSTRUCTION, as_text, with_family_instruction

# -- settings and migration ------------------------------------------------------ #


def test_the_loader_keeps_the_five_values_and_drops_anything_else() -> None:
    assert choice.load_connection_fields({"ai_connection": " ChatGPT "})["ai_connection"] == (
        "chatgpt"
    )
    assert choice.load_connection_fields({"ai_connection": "claude"})["ai_connection"] == ""
    assert choice.load_connection_fields({}) == {
        "ai_connection": "",
        "ai_copilot_model": "",
        "ai_codex_model": "",
    }


def test_both_editors_have_the_same_three_fields() -> None:
    from quill.core.lite.settings import Settings as LiteSettings
    from quill.core.settings import Settings

    for name in ("ai_connection", "ai_copilot_model", "ai_codex_model"):
        assert getattr(Settings(), name) == ""
        assert getattr(LiteSettings(), name) == ""
    assert LiteSettings(ai_connection="Nonsense").normalized().ai_connection == ""


def test_the_first_read_stores_what_the_old_precedence_chose_and_saves_once() -> None:
    saved: list[str] = []
    settings = SimpleNamespace(ai_connection="")

    def save() -> None:
        saved.append(settings.ai_connection)

    got = choice.migrate_choice(
        settings, chatgpt_signed_in=lambda: False, own_key_ready=lambda: True, save=save
    )
    assert got == "own_key" and settings.ai_connection == "own_key" and saved == ["own_key"]
    # Afterwards the stored choice stands, whatever is signed in.
    again = choice.migrate_choice(
        settings, chatgpt_signed_in=lambda: True, own_key_ready=lambda: True, save=save
    )
    assert again == "own_key" and saved == ["own_key"]


def test_migration_order_is_chatgpt_then_key_then_free() -> None:
    def run(gpt: bool, key: bool) -> str:
        s = SimpleNamespace(ai_connection="")
        return choice.migrate_choice(s, chatgpt_signed_in=lambda: gpt, own_key_ready=lambda: key)

    assert run(True, True) == "chatgpt"
    assert run(False, True) == "own_key"
    assert run(False, False) == "free"


def test_a_settings_object_without_the_field_gets_the_old_precedence_live() -> None:
    old = SimpleNamespace()
    assert (
        choice.migrate_choice(old, chatgpt_signed_in=lambda: True, own_key_ready=lambda: False)
        == "chatgpt"
    )
    assert not hasattr(old, "ai_connection")


# -- readiness, rows and sentences ------------------------------------------------ #


def test_rows_read_name_then_state() -> None:
    facts = ConnectionFacts(
        stored="chatgpt", chatgpt_signed_in=True, own_key_ready=True, own_key_provider="openai"
    )
    assert [row.text for row in choice.row_states(facts)] == [
        "QUILL's free AI, not set up",
        "My ChatGPT plan, in use",
        "My GitHub Copilot, not available yet",
        "Codex, for tasks, not available yet",
        "My own key, OpenAI, signed in",
    ]


def test_signing_out_of_the_row_in_use_leaves_no_ai_in_use() -> None:
    facts = ConnectionFacts(stored="own_key", own_key_ready=False, free_connected=True)
    assert choice.in_use(facts) == ""
    assert choice.not_ready_sentence(facts) == "No AI is in use. Choose one."
    assert all(row.state != choice.IN_USE for row in choice.row_states(facts))


def test_a_revoked_plan_says_who_ended_it_and_never_falls_through() -> None:
    facts = ConnectionFacts(stored="chatgpt", chatgpt_ended=True, own_key_ready=True)
    assert choice.not_ready_sentence(facts) == (
        "Your ChatGPT plan sign-in has ended. Nothing was sent. "
        "Press Ctrl+4 to sign in again or choose another."
    )
    rows = {row.connection: row for row in choice.row_states(facts)}
    assert rows["chatgpt"].text == "My ChatGPT plan, signed out by OpenAI"
    assert choice.in_use(facts) == ""


def test_copilot_and_codex_are_not_available_yet_even_when_stored() -> None:
    facts = ConnectionFacts(stored="codex", chatgpt_signed_in=True)
    assert choice.not_ready_sentence(facts).startswith("Codex is not available yet.")
    assert choice.request_route("codex") == "chatgpt"  # decision 21, once available
    ready_codex = ConnectionFacts(stored="codex", chatgpt_signed_in=True, codex_available=True)
    assert choice.not_ready_sentence(ready_codex) == ""


def test_the_free_ai_is_always_ready_to_be_chosen() -> None:
    facts = ConnectionFacts(stored="free")
    assert choice.in_use(facts) == "free"
    assert choice.not_ready_sentence(facts) == ""


def test_the_limit_sentence_names_the_app() -> None:
    assert choice.limit_sentence("chatgpt", "QUILL") == (
        "Your ChatGPT plan's limit for QUILL is reached. Nothing was sent. "
        "Manage usage is in the Usage window."
    )


# -- the local ChatGPT count ------------------------------------------------------- #


def test_the_local_count_is_per_app_today_and_this_week(tmp_path) -> None:
    monday = datetime(2026, 10, 26, 9)
    friday = datetime(2026, 10, 30, 9)
    record_request(tmp_path, "quill", input_tokens=10, output_tokens=4, now=monday)
    record_request(tmp_path, "quill", input_tokens=5, output_tokens=1, now=friday)
    record_request(tmp_path, "quill", input_tokens=1, output_tokens=1, now=friday)
    record_request(tmp_path, "quill-lite", now=friday)
    count = local_count(tmp_path, "quill", now=friday)
    assert count == LocalCount(
        requests_today=2,
        requests_this_week=3,
        input_tokens_today=6,
        output_tokens_today=2,
        input_tokens_this_week=16,
        output_tokens_this_week=6,
    )
    assert local_count(tmp_path, "quill-lite", now=friday).requests_today == 1
    # Next Monday starts a new week.
    assert local_count(tmp_path, "quill", now=datetime(2026, 11, 2)).requests_this_week == 0


def test_a_corrupt_count_file_reads_as_zero_and_is_rewritten(tmp_path) -> None:
    path = usage_path(tmp_path, "quill")
    path.parent.mkdir(parents=True)
    path.write_text("{not json", encoding="utf-8")
    assert local_count(tmp_path, "quill") == LocalCount()
    record_request(tmp_path, "quill")
    assert local_count(tmp_path, "quill").requests_today == 1


# -- usage sentences and Ctrl+8 ----------------------------------------------------- #


def test_usage_rows_say_whose_number_each_is() -> None:
    quota = SimpleNamespace(daily_cap=50, daily_used=14, monthly_cap=0, monthly_used=0)
    snapshot = usage.RateLimitSnapshot(remaining_requests=480)
    facts = ConnectionFacts(stored="free", chatgpt_signed_in=True, own_key_ready=True)
    rows = usage.usage_rows(
        facts,
        app_name="QUILL",
        free_quota=quota,
        chatgpt_count=LocalCount(requests_today=23, requests_this_week=40),
        own_key_limits=snapshot,
    )
    assert [row.sentence for row in rows] == [
        "QUILL's free AI: 14 of 50 requests today, by QUILL's count. Resets at midnight.",
        "My ChatGPT plan: 23 requests today from QUILL, counted on this computer. "
        "OpenAI sets the limits; Manage usage opens them.",
        "My GitHub Copilot: not available yet.",
        "My own key, OpenAI: 480 requests left this minute, from OpenAI's last answer. "
        "Your bill is on OpenAI's page.",
    ]
    assert "counted on this computer" in rows[1].detail.lower()
    assert rows[1].manage_url.startswith("https://chatgpt.com/")


def test_rate_limit_headers_are_kept_only_when_present() -> None:
    usage.clear_rate_limits()
    usage.remember_rate_limits("openai", {"content-type": "application/json"})
    assert usage.last_rate_limits("openai") is None
    usage.remember_rate_limits(
        "openai", {"X-RateLimit-Remaining-Requests": "59", "x-ratelimit-limit-requests": "60"}
    )
    snap = usage.last_rate_limits("openai")
    assert snap is not None and snap.remaining_requests == 59 and snap.limit_requests == 60
    usage.clear_rate_limits()


def test_which_ai_speaks_connection_model_and_one_clause() -> None:
    plan = ConnectionFacts(stored="chatgpt", chatgpt_signed_in=True)
    assert usage.which_ai_sentence(
        plan, model="gpt-6", chatgpt_count=LocalCount(requests_today=1)
    ) == ("My ChatGPT plan, gpt-6. 1 request today from QUILL, counted on this computer.")
    codex = ConnectionFacts(stored="codex", chatgpt_signed_in=True, codex_available=True)
    assert usage.which_ai_sentence(codex).startswith(
        "Codex, on your ChatGPT plan. Single requests go to the plan directly."
    )
    none = ConnectionFacts(stored="own_key")
    assert usage.which_ai_sentence(none) == "No AI is in use. Choose one."
    assert usage.status_cell_text(plan) == "AI: ChatGPT plan"
    assert usage.status_cell_text(none) == "AI: none"


# -- everything is text ------------------------------------------------------------- #


def test_the_family_line_is_appended_once_and_never_edits_the_prompt() -> None:
    once = with_family_instruction("Summarize the following text.")
    assert once.startswith("Summarize the following text.")
    assert once.endswith(FAMILY_INSTRUCTION)
    assert with_family_instruction(once) == once


def test_chart_like_answers_are_shown_as_the_text_they_are() -> None:
    answer = "Here:\n```mermaid\ngraph TD; A-->B\n```\n![Sales chart](https://x.test/c.png)\n"
    shown = as_text(answer)
    assert "```mermaid" not in shown and "```text" in shown and "A-->B" in shown
    assert "![" not in shown and "(picture link: Sales chart, https://x.test/c.png)" in shown
    assert as_text("Bars: ##### 50%") == "Bars: ##### 50%"
