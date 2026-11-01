"""The capability registry (codex.md 10A.7) and the one-key switch sentences (10A.8)."""

from __future__ import annotations

import pytest

from quill.core.ai import connection_caps as caps


@pytest.fixture(autouse=True)
def _no_overrides():
    caps.clear_model_capabilities()
    yield
    caps.clear_model_capabilities()


def test_every_connection_claims_every_capability_with_a_source() -> None:
    for provider in ("openai", "gemini"):
        for record in caps.all_records(own_key_provider=provider, web_search_enabled=True):
            assert set(record.claims) == set(caps.CAPABILITIES), record.connection
            for capability, claim in record.claims.items():
                assert claim.source.strip(), (record.connection, capability)


def test_the_table_of_10a7() -> None:
    free = caps.record_for("free")
    assert caps.can(free, "text") and not caps.can(free, "pictures")
    assert not caps.can(free, "web_search")
    assert caps.can(caps.record_for("free", web_search_enabled=True), "web_search")
    plan = caps.record_for("chatgpt")
    assert caps.can(plan, "pictures") and caps.can(plan, "streaming")
    assert not caps.can(plan, "agent_tools") and not caps.can(plan, "image_generation")
    assert caps.can(caps.record_for("own_key", own_key_provider="gemini"), "pictures")
    assert not caps.can(caps.record_for("own_key", own_key_provider="openai"), "pictures")
    assert caps.can(caps.record_for("own_key"), "image_generation")


def test_copilot_and_codex_are_not_available_yet_and_so_can_do_nothing() -> None:
    for name in ("copilot", "codex"):
        record = caps.record_for(name)
        assert not record.available
        assert record.claim("agent_tools").supported  # what it will do
        assert not caps.can(record, "text")  # what it can do in this build


def test_require_raises_a_coded_sentence_naming_the_missing_capability() -> None:
    caps.require(caps.record_for("chatgpt"), "text", "pictures")
    with pytest.raises(caps.CapabilityMissing) as raised:
        caps.require(caps.record_for("free"), "text", "pictures")
    assert raised.value.code == "QUILL-AI-CAPS-MISSING"
    assert raised.value.capability == "pictures"
    assert str(raised.value.args[0]) == "Pictures need a connection that can see. Nothing was sent."
    with pytest.raises(ValueError):
        caps.require(caps.record_for("free"), "telepathy")


def test_a_model_override_needs_a_source_and_wins_for_that_model_only() -> None:
    with pytest.raises(ValueError):
        caps.set_model_capabilities("chatgpt", "gpt-text", {"pictures": False}, source=" ")
    caps.set_model_capabilities(
        "chatgpt", "gpt-text", {"pictures": False}, source="the plan's /models metadata"
    )
    assert not caps.can(caps.record_for("chatgpt", model="gpt-text"), "pictures")
    assert caps.record_for("chatgpt", model="gpt-text").claim("pictures").source
    assert caps.can(caps.record_for("chatgpt", model="gpt-6"), "pictures")


def test_the_switch_offer_names_a_set_up_connection_that_can() -> None:
    offer = caps.switch_offer("pictures", set_up=["free", "chatgpt"], in_use="free")
    assert offer.sentence == (
        "Pictures need a connection that can see. My ChatGPT plan can. Switch to it and ask?"
    )
    assert offer.target == "chatgpt"


def test_the_offer_lists_who_could_when_nothing_set_up_can() -> None:
    offer = caps.switch_offer("pictures", set_up=["free"], in_use="free")
    assert offer.sentence == (
        "Pictures need My ChatGPT plan, My GitHub Copilot, Codex or a Gemini key. Choose one now?"
    )
    assert offer.target == "" and offer.open_row == "chatgpt"
    tasks = caps.switch_offer("agent_tools", set_up=["free"], in_use="free")
    assert tasks.sentence == "Agent tasks need My GitHub Copilot or Codex. Choose one now?"


def test_an_openai_key_does_not_count_as_seeing_but_a_gemini_key_does() -> None:
    openai = caps.switch_offer("pictures", set_up=["own_key"], in_use="free")
    assert openai.target == ""
    gemini = caps.switch_offer(
        "pictures", set_up=["own_key"], in_use="free", own_key_provider="gemini"
    )
    assert gemini.target == "own_key"
    assert gemini.sentence.startswith("Pictures need a connection that can see. A Gemini key")


def test_menu_labels_say_what_a_command_needs() -> None:
    assert caps.needs_label("pictures") == "(needs a connection that sees)"
    assert caps.needs_label("agent_tools") == "(needs Copilot or Codex)"
