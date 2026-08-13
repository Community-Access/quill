"""Quick Actions ordering, repair, and persistence (1.1.0).

Repair is the part worth testing hardest: the saved file outlives the build
that wrote it, so an order naming an action this build removed, or missing
one this build added, must still produce a complete, usable menu.
"""

from __future__ import annotations

from quill.core.podcasts import quick_actions as qa


class TestDefaults:
    def test_every_context_has_actions(self) -> None:
        for context in qa.CONTEXTS:
            assert qa.default_order(context)

    def test_action_ids_are_unique_within_a_context(self) -> None:
        for context, actions in qa.CONTEXTS.items():
            ids = [action.id for action in actions]
            assert len(ids) == len(set(ids)), context

    def test_every_action_carries_words_for_the_listener(self) -> None:
        for actions in qa.CONTEXTS.values():
            for action in actions:
                assert action.label.strip()
                assert action.description.strip()

    def test_the_shipped_episode_default_is_play(self) -> None:
        # The upgrade must not change what Enter does until somebody asks.
        assert qa.QuickActionOrders().default_action("episode") == "play"

    def test_the_shipped_show_default_plays_the_next_episode(self) -> None:
        assert qa.QuickActionOrders().default_action("show") == "play_next_episode"

    def test_every_context_label_names_a_real_context(self) -> None:
        assert {cid for cid, _label in qa.CONTEXT_LABELS} == set(qa.CONTEXTS)


class TestRepair:
    def test_an_unknown_action_is_dropped(self) -> None:
        repaired = qa.repair_order("episode", ["play", "from-the-future"])

        assert "from-the-future" not in repaired

    def test_a_missing_action_is_appended_rather_than_lost(self) -> None:
        repaired = qa.repair_order("episode", ["play"])

        assert repaired[0] == "play"
        assert set(repaired) == set(qa.default_order("episode"))

    def test_duplicates_collapse_to_the_first_appearance(self) -> None:
        repaired = qa.repair_order("episode", ["download", "play", "download"])

        assert repaired[:2] == ["download", "play"]
        assert repaired.count("download") == 1

    def test_an_empty_order_becomes_the_shipped_order(self) -> None:
        assert qa.repair_order("episode", []) == qa.default_order("episode")

    def test_an_unknown_context_repairs_to_nothing(self) -> None:
        assert qa.repair_order("nope", ["play"]) == []

    def test_a_menu_is_never_shorter_than_the_builds_action_set(self) -> None:
        for context in qa.CONTEXTS:
            assert len(qa.repair_order(context, ["nonsense"])) == len(qa.CONTEXTS[context])


class TestOrders:
    def test_setting_an_order_repairs_it(self) -> None:
        orders = qa.QuickActionOrders()

        orders.set_order("episode", ["download", "nonsense"])

        assert orders.default_action("episode") == "download"
        assert "nonsense" not in orders.order("episode")

    def test_actions_resolve_to_real_records_in_order(self) -> None:
        orders = qa.QuickActionOrders()
        orders.set_order("episode", ["add_to_queue", "play"])

        actions = orders.actions("episode")

        assert [a.id for a in actions[:2]] == ["add_to_queue", "play"]
        assert all(isinstance(a, qa.QuickAction) for a in actions)

    def test_reset_returns_the_shipped_order(self) -> None:
        orders = qa.QuickActionOrders()
        orders.set_order("episode", ["download"])

        orders.reset("episode")

        assert orders.order("episode") == qa.default_order("episode")

    def test_round_trips_through_a_dict(self) -> None:
        orders = qa.QuickActionOrders()
        orders.set_order("show", ["unsubscribe", "refresh"])

        restored = qa.QuickActionOrders.from_dict(orders.to_dict())

        assert restored.order("show") == orders.order("show")

    def test_garbage_input_reads_as_the_default(self) -> None:
        restored = qa.QuickActionOrders.from_dict("not a dict")

        assert restored.order("episode") == qa.default_order("episode")

    def test_a_partial_dict_only_changes_what_it_names(self) -> None:
        restored = qa.QuickActionOrders.from_dict({"episode": ["download"]})

        assert restored.default_action("episode") == "download"
        assert restored.order("show") == qa.default_order("show")


class TestStore:
    def test_round_trips_through_disk(self, tmp_path) -> None:
        orders = qa.QuickActionOrders()
        orders.set_order("queue", ["remove", "play"])

        qa.save_quick_actions(tmp_path, orders)

        assert qa.load_quick_actions(tmp_path).order("queue")[:2] == ["remove", "play"]

    def test_a_missing_file_reads_as_the_default(self, tmp_path) -> None:
        loaded = qa.load_quick_actions(tmp_path / "nowhere")

        assert loaded.order("episode") == qa.default_order("episode")

    def test_a_corrupt_file_reads_as_the_default(self, tmp_path) -> None:
        (tmp_path / "podcast_quick_actions.json").write_text("{ broken", encoding="utf-8")

        assert qa.load_quick_actions(tmp_path).order("episode") == qa.default_order("episode")
