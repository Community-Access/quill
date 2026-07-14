"""Unit tests for the free/low-cost model catalog and classifier."""

from __future__ import annotations

import pytest

from quill.core.ai import free_models as fm


class TestFreeDetection:
    def test_free_suffix_is_free(self) -> None:
        assert fm.is_free_model("meta-llama/llama-3.3-70b-instruct:free")

    def test_free_suffix_case_insensitive(self) -> None:
        assert fm.has_free_suffix("Some/Model:FREE")

    def test_zero_pricing_is_free(self) -> None:
        assert fm.is_free_model("x/y", {"prompt": "0", "completion": "0"})

    def test_zero_pricing_numeric(self) -> None:
        assert fm.is_free_pricing({"prompt": 0, "completion": 0.0})

    def test_nonzero_pricing_not_free(self) -> None:
        pricing = {"prompt": "0.0000005", "completion": "0.0000015"}
        assert not fm.is_free_model("x/y", pricing)

    def test_missing_pricing_not_free(self) -> None:
        assert not fm.is_free_pricing(None)
        assert not fm.is_free_pricing({})
        assert not fm.is_free_pricing({"prompt": "0"})  # completion missing

    def test_bool_pricing_rejected(self) -> None:
        # bool is an int subclass; must not be read as a 0/1 price
        assert not fm.is_free_pricing({"prompt": False, "completion": False})


class TestCostTier:
    def test_free_tier(self) -> None:
        assert fm.cost_tier_for("a/b:free") == fm.TIER_FREE

    def test_low_tier_from_pricing(self) -> None:
        pricing = {"prompt": "0.0000005", "completion": "0.0000005"}
        assert fm.cost_tier_for("x/y", pricing) == fm.TIER_LOW

    def test_flagship_from_pricing(self) -> None:
        pricing = {"prompt": "0.00001", "completion": "0.00003"}
        assert fm.cost_tier_for("x/y", pricing) == fm.TIER_FLAGSHIP

    def test_low_tier_by_name_hint(self) -> None:
        assert fm.cost_tier_for("gpt-4o-mini") == fm.TIER_LOW
        assert fm.cost_tier_for("claude-haiku-4-5") == fm.TIER_LOW
        assert fm.cost_tier_for("gemini-2.5-flash") == fm.TIER_LOW

    def test_flagship_by_name_hint(self) -> None:
        assert fm.cost_tier_for("claude-sonnet-4-6") == fm.TIER_FLAGSHIP
        assert fm.cost_tier_for("gemini-2.5-pro") == fm.TIER_FLAGSHIP


class TestToolUse:
    def test_tiny_models_flagged_unreliable(self) -> None:
        assert not fm.supports_tool_use("meta-llama/llama-3.2-1b-instruct")
        assert not fm.supports_tool_use("qwen2.5:1.5b-instruct")
        assert not fm.supports_tool_use("some-3b-model")

    def test_strong_families_pass(self) -> None:
        assert fm.supports_tool_use("meta-llama/llama-3.3-70b-instruct:free")
        assert fm.supports_tool_use("gpt-4o-mini")
        assert fm.supports_tool_use("claude-haiku-4-5")

    def test_unknown_size_defaults_true(self) -> None:
        assert fm.supports_tool_use("some/mystery-model")


class TestWritingQuality:
    def test_bigger_ranks_higher(self) -> None:
        assert fm.writing_quality("x/70b") > fm.writing_quality("x/7b")
        assert fm.writing_quality("x/7b") > fm.writing_quality("x/1b")

    def test_unknown_size_is_capable(self) -> None:
        assert fm.writing_quality("gpt-4o-mini") >= 45


class TestRankingAndDefaults:
    def test_free_sorts_before_paid(self) -> None:
        paid_pricing = {"prompt": "0.001", "completion": "0.001"}
        models = [
            fm.classify_model("paid/big-70b", "openrouter", paid_pricing),
            fm.classify_model("free/small-7b:free", "openrouter"),
        ]
        ranked = fm.rank_models(models)
        assert ranked[0].id == "free/small-7b:free"

    def test_free_models_filter(self) -> None:
        models = [
            fm.classify_model("a:free", "openrouter"),
            fm.classify_model("b", "openrouter", {"prompt": "0.001", "completion": "0.001"}),
        ]
        assert [m.id for m in fm.free_models(models)] == ["a:free"]

    def test_best_free_offline_default(self) -> None:
        assert fm.best_free_writing_model("openrouter") == fm.PREFERRED_FREE_MODELS["openrouter"][0]

    def test_best_free_prefers_available_curated(self) -> None:
        available = ["z/other:free", "google/gemma-2-9b-it:free"]
        assert fm.best_free_writing_model("openrouter", available) == "google/gemma-2-9b-it:free"

    def test_best_free_ranks_when_no_curated(self) -> None:
        available = ["x/small-7b:free", "x/big-70b:free", "x/paid"]
        assert fm.best_free_writing_model("openrouter", available) == "x/big-70b:free"

    def test_best_free_none_when_no_free(self) -> None:
        assert fm.best_free_writing_model("openrouter", ["x/paid", "y/paid"]) is None

    def test_unknown_provider_offline_none(self) -> None:
        assert fm.best_free_writing_model("nope") is None


class TestFreePathAdvice:
    def test_two_paths_best_first(self) -> None:
        paths = fm.recommended_free_paths()
        assert [p.rank for p in paths] == [1, 2]
        assert paths[0].provider == "openrouter"
        assert paths[0].needs_key is True
        assert paths[1].provider == "ollama"
        assert paths[1].needs_key is False

    def test_advice_names_a_concrete_free_model(self) -> None:
        best = fm.recommended_free_paths()[0]
        assert fm.has_free_suffix(best.model)


class TestStrongerModelHint:
    def test_hint_for_toolloop_agent_on_small_model(self) -> None:
        assert fm.stronger_model_hint(True, "llama3.2:1b")

    def test_no_hint_for_single_shot_agent(self) -> None:
        assert fm.stronger_model_hint(False, "llama3.2:1b") == ""

    def test_no_hint_on_capable_model(self) -> None:
        assert fm.stronger_model_hint(True, "claude-haiku-4-5") == ""


class TestTaskRouting:
    def _models(self) -> list[fm.ModelInfo]:
        paid = {"prompt": "0.001", "completion": "0.001"}
        return [
            fm.classify_model("x/free-70b:free", "openrouter"),
            fm.classify_model("x/tiny-1b:free", "openrouter"),
            fm.classify_model("x/paid-70b", "openrouter", paid),
        ]

    def test_light_task_picks_cheapest_ranked(self) -> None:
        chosen = fm.resolve_model_for_task("rewrite", self._models())
        assert chosen is not None and chosen.id == "x/free-70b:free"

    def test_heavy_task_prefers_tool_capable(self) -> None:
        # tiny-1b is free but not tool-capable; the free 70b is both free and capable.
        chosen = fm.resolve_model_for_task("research", self._models())
        assert chosen is not None and chosen.tool_use and chosen.id == "x/free-70b:free"

    def test_empty_returns_none(self) -> None:
        assert fm.resolve_model_for_task("rewrite", []) is None


class TestFetchClassified:
    def test_fetch_uses_ai_chat_raw(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload = [
            {"id": "a/big-70b:free", "name": "Big"},
            {
                "id": "b/mini",
                "name": "Mini",
                "pricing": {"prompt": "0.0000005", "completion": "0.0000005"},
            },
            {"id": ""},  # skipped
        ]

        def fake_raw(provider_id: str, api_key: str = "", base_url: str = "") -> list[dict]:
            assert provider_id == "openrouter"
            return payload

        from quill.core import ai_chat

        monkeypatch.setattr(ai_chat, "list_models_raw", fake_raw)
        result = fm.fetch_classified_models("openrouter", api_key="k")
        ids = [m.id for m in result]
        assert ids == ["a/big-70b:free", "b/mini"]  # free first
        assert result[0].cost_tier == fm.TIER_FREE
        assert result[1].cost_tier == fm.TIER_LOW
