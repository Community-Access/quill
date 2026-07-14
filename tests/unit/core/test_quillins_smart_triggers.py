"""Unit tests for the wx-free smart-trigger parser and index (=name(args))."""

from __future__ import annotations

from quill.core.quillins.smart_triggers import (
    SmartTriggerDef,
    SmartTriggerResolution,
    build_smart_trigger_index,
    parse_smart_trigger_line,
    resolve_smart_trigger,
    smart_trigger_def_from_dict,
)


class TestParseSmartTriggerLine:
    def test_no_args(self) -> None:
        match = parse_smart_trigger_line("=bug()")
        assert match is not None
        assert match.name == "bug"
        assert match.args == []

    def test_with_args(self) -> None:
        match = parse_smart_trigger_line("=rand(10, 10)")
        assert match is not None
        assert match.name == "rand"
        assert match.args == ["10", "10"]

    def test_surrounding_whitespace_allowed(self) -> None:
        match = parse_smart_trigger_line("   =todo(3)  ")
        assert match is not None
        assert match.name == "todo"
        assert match.args == ["3"]

    def test_plain_text_is_not_a_trigger(self) -> None:
        assert parse_smart_trigger_line("just some text") is None

    def test_trigger_with_leading_text_is_rejected(self) -> None:
        # Must be the whole line, not embedded — otherwise typing prose that
        # happens to contain =foo() would fire.
        assert parse_smart_trigger_line("see =rand(2, 2) here") is None

    def test_missing_parens_is_rejected(self) -> None:
        assert parse_smart_trigger_line("=rand") is None

    def test_equation_like_math_is_not_a_trigger(self) -> None:
        # A bare "=5" or "=a+b" must not look like a trigger.
        assert parse_smart_trigger_line("=5") is None
        assert parse_smart_trigger_line("=a + b") is None

    def test_empty_args_are_dropped(self) -> None:
        # "=rand(10,)" yields a single meaningful arg, not ["10", ""].
        match = parse_smart_trigger_line("=rand(10,)")
        assert match is not None
        assert match.args == ["10"]


class TestSmartTriggerDefFromDict:
    def test_minimal_dict(self) -> None:
        d = smart_trigger_def_from_dict(
            {"trigger": "bug", "command": "ext.smartinsert.bug"}, "com.quill.smartinsert"
        )
        assert d == SmartTriggerDef(
            name="bug",
            command_id="ext.smartinsert.bug",
            quillin_id="com.quill.smartinsert",
            enabled_by_default=True,
            min_args=None,
            max_args=None,
        )

    def test_reads_arg_bounds_and_default(self) -> None:
        d = smart_trigger_def_from_dict(
            {
                "trigger": "rand",
                "command": "ext.smartinsert.rand",
                "enabled_by_default": False,
                "min_args": 0,
                "max_args": 2,
            },
            "com.quill.smartinsert",
        )
        assert d is not None
        assert d.min_args == 0
        assert d.max_args == 2
        assert d.enabled_by_default is False

    def test_missing_trigger_or_command_returns_none(self) -> None:
        assert smart_trigger_def_from_dict({"command": "x"}, "q") is None
        assert smart_trigger_def_from_dict({"trigger": "x"}, "q") is None

    def test_non_dict_returns_none(self) -> None:
        assert smart_trigger_def_from_dict("nope", "q") is None


class TestArgBounds:
    def test_within_bounds(self) -> None:
        d = SmartTriggerDef("rand", "c", "q", min_args=0, max_args=2)
        assert d.accepts_arg_count(0)
        assert d.accepts_arg_count(2)

    def test_too_many_args(self) -> None:
        d = SmartTriggerDef("rand", "c", "q", min_args=0, max_args=2)
        assert not d.accepts_arg_count(3)

    def test_too_few_args(self) -> None:
        d = SmartTriggerDef("x", "c", "q", min_args=1, max_args=1)
        assert not d.accepts_arg_count(0)

    def test_no_bounds_accepts_anything(self) -> None:
        d = SmartTriggerDef("x", "c", "q")
        assert d.accepts_arg_count(0)
        assert d.accepts_arg_count(5)


class TestBuildSmartTriggerIndex:
    def test_indexes_by_name_across_manifests(self) -> None:
        triggers_a = [
            {"trigger": "bug", "command": "a.bug"},
            {"trigger": "rand", "command": "a.rand", "min_args": 0, "max_args": 2},
        ]
        triggers_b = [{"trigger": "note", "command": "b.note"}]
        index = build_smart_trigger_index([("com.a", triggers_a), ("com.b", triggers_b)])
        assert set(index) == {"bug", "rand", "note"}
        assert index["rand"].command_id == "a.rand"
        assert index["note"].quillin_id == "com.b"

    def test_first_definition_wins_on_collision(self) -> None:
        index = build_smart_trigger_index([
            ("com.a", [{"trigger": "dup", "command": "a.dup"}]),
            ("com.b", [{"trigger": "dup", "command": "b.dup"}]),
        ])
        assert index["dup"].command_id == "a.dup"

    def test_skips_malformed_entries(self) -> None:
        index = build_smart_trigger_index([
            ("com.a", [{"trigger": "ok", "command": "a.ok"}, {"bad": True}, "junk"])
        ])
        assert set(index) == {"ok"}


class TestResolveSmartTrigger:
    def _index(self) -> dict[str, SmartTriggerDef]:
        return {"rand": SmartTriggerDef("rand", "c.rand", "q", min_args=0, max_args=2)}

    def test_resolves_when_enabled_and_in_bounds(self) -> None:
        match = parse_smart_trigger_line("=rand(2, 3)")
        assert match is not None
        result = resolve_smart_trigger(match, self._index(), is_enabled=lambda d: True)
        assert result == SmartTriggerResolution(self._index()["rand"], ["2", "3"])

    def test_unknown_name_returns_none(self) -> None:
        match = parse_smart_trigger_line("=nope()")
        assert match is not None
        assert resolve_smart_trigger(match, self._index(), is_enabled=lambda d: True) is None

    def test_disabled_trigger_returns_none(self) -> None:
        match = parse_smart_trigger_line("=rand()")
        assert match is not None
        assert resolve_smart_trigger(match, self._index(), is_enabled=lambda d: False) is None

    def test_out_of_bounds_returns_none(self) -> None:
        match = parse_smart_trigger_line("=rand(1, 2, 3)")
        assert match is not None
        assert resolve_smart_trigger(match, self._index(), is_enabled=lambda d: True) is None
