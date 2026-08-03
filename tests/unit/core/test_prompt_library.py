"""Unit tests for quill.core.prompt_library."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core.prompt_library import PromptLibrary


def _make_lib(tmp_path: Path) -> PromptLibrary:
    return PromptLibrary(tmp_path / "prompts.json")


class TestBuiltins:
    def test_builtins_present_on_fresh_library(self, tmp_path: Path) -> None:
        lib = _make_lib(tmp_path)
        names = {p.name for p in lib.all()}
        assert "Check Grammar" in names
        assert "Improve Clarity" in names
        assert "Summarize" in names

    def test_check_grammar_is_builtin(self, tmp_path: Path) -> None:
        lib = _make_lib(tmp_path)
        p = lib.find_by_id("builtin-check-grammar")
        assert p is not None
        assert p.is_builtin
        assert "{selection}" in p.text

    def test_builtin_cannot_be_removed(self, tmp_path: Path) -> None:
        lib = _make_lib(tmp_path)
        with pytest.raises(ValueError, match="Built-in"):
            lib.remove("builtin-check-grammar")

    def test_named_one_shot_writing_presets_ship_out_of_box(self, tmp_path: Path) -> None:
        # The named one-shot tools that were missing now ship
        # as built-in prompts.
        lib = _make_lib(tmp_path)
        names = {p.name for p in lib.all()}
        for expected in (
            "Generate FAQs",
            "Draft a Speech",
            "Summary Email",
            "Social Media Post",
            "Step-by-Step Instructions",
            "Paraphrase",
        ):
            assert expected in names, f"missing built-in preset: {expected}"

    def test_new_presets_are_builtin_and_use_selection(self, tmp_path: Path) -> None:
        lib = _make_lib(tmp_path)
        for prompt_id in (
            "builtin-generate-faqs",
            "builtin-speech-draft",
            "builtin-summary-email",
            "builtin-social-post",
            "builtin-step-by-step",
            "builtin-paraphrase",
        ):
            p = lib.find_by_id(prompt_id)
            assert p is not None, f"missing preset id: {prompt_id}"
            assert p.is_builtin
            assert "{selection}" in p.text

    def test_social_post_preset_mentions_the_character_limit(self, tmp_path: Path) -> None:
        lib = _make_lib(tmp_path)
        p = lib.find_by_id("builtin-social-post")
        assert p is not None
        assert "280" in p.text


class TestUserPrompts:
    def test_add_prompt(self, tmp_path: Path) -> None:
        lib = _make_lib(tmp_path)
        p = lib.add("My Prompt", "Do something with: {selection}", "Custom")
        assert lib.find_by_id(p.id) is not None
        assert lib.find_by_name("My Prompt") is not None

    def test_add_persists_across_reload(self, tmp_path: Path) -> None:
        lib = _make_lib(tmp_path)
        lib.add("Saved Prompt", "text {selection}", "Editing")
        lib2 = _make_lib(tmp_path)
        assert lib2.find_by_name("Saved Prompt") is not None

    def test_update_prompt(self, tmp_path: Path) -> None:
        lib = _make_lib(tmp_path)
        p = lib.add("Old Name", "text", "Custom")
        lib.update(p.id, name="New Name", text="new text")
        updated = lib.find_by_id(p.id)
        assert updated is not None
        assert updated.name == "New Name"

    def test_remove_user_prompt(self, tmp_path: Path) -> None:
        lib = _make_lib(tmp_path)
        p = lib.add("To Remove", "text", "Custom")
        lib.remove(p.id)
        assert lib.find_by_id(p.id) is None

    def test_enable_disable(self, tmp_path: Path) -> None:
        lib = _make_lib(tmp_path)
        p = lib.add("Togglable", "text", "Custom")
        lib.disable(p.id)
        assert not lib.find_by_id(p.id).enabled
        lib.enable(p.id)
        assert lib.find_by_id(p.id).enabled

    def test_disabled_excluded_from_enabled_only(self, tmp_path: Path) -> None:
        lib = _make_lib(tmp_path)
        p = lib.add("Disabled Prompt", "text", "Custom")
        lib.disable(p.id)
        enabled_ids = {q.id for q in lib.enabled_only()}
        assert p.id not in enabled_ids


class TestBuiltinOverride:
    def test_edit_builtin_text_persists(self, tmp_path: Path) -> None:
        lib = _make_lib(tmp_path)
        lib.update("builtin-check-grammar", text="Custom grammar text {selection}")
        lib2 = _make_lib(tmp_path)
        p = lib2.find_by_id("builtin-check-grammar")
        assert p is not None
        assert p.text == "Custom grammar text {selection}"

    def test_disable_builtin_persists(self, tmp_path: Path) -> None:
        lib = _make_lib(tmp_path)
        lib.disable("builtin-check-grammar")
        lib2 = _make_lib(tmp_path)
        p = lib2.find_by_id("builtin-check-grammar")
        assert p is not None
        assert not p.enabled


class TestQuillinPrompts:
    def test_load_quillin_prompts(self, tmp_path: Path) -> None:
        lib = _make_lib(tmp_path)
        pf = tmp_path / "prompts.json"
        pf.write_text(
            json.dumps([
                {"name": "Expand This", "text": "Expand: {selection}", "category": "Writing"}
            ]),
            encoding="utf-8",
        )
        lib.load_quillin_prompts(pf)
        names = {p.name for p in lib.all()}
        assert "Expand This" in names

    def test_quillin_prompts_not_persisted(self, tmp_path: Path) -> None:
        lib = _make_lib(tmp_path)
        pf = tmp_path / "quillin_prompts.json"
        pf.write_text(
            json.dumps([{"name": "Temporary", "text": "text", "category": "Custom"}]),
            encoding="utf-8",
        )
        lib.load_quillin_prompts(pf)
        lib2 = _make_lib(tmp_path)
        assert lib2.find_by_name("Temporary") is None

    def test_bundled_quillin_prompts_file_valid(self) -> None:
        pf = (
            Path(__file__).parent.parent.parent.parent
            / "quill"
            / "quillins_bundled"
            / "ai-writing-prompts"
            / "prompts.json"
        )
        assert pf.exists(), "ai-writing-prompts/prompts.json missing"
        items = json.loads(pf.read_text(encoding="utf-8"))
        assert isinstance(items, list) and len(items) > 0
        for item in items:
            assert "name" in item and "text" in item and "category" in item


class TestPQL:
    def test_export_import_roundtrip(self, tmp_path: Path) -> None:
        lib = _make_lib(tmp_path)
        lib.add("Export Test", "Some text {selection}", "Custom")
        pql_file = tmp_path / "pack.pqp"
        count = lib.export_pqp(pql_file)
        assert count > 0

        lib2 = _make_lib(tmp_path / "other")
        lib2._path.parent.mkdir(parents=True, exist_ok=True)
        added = lib2.import_pqp(pql_file)
        names_added = {p.name for p in added}
        assert "Export Test" in names_added

    def test_import_skips_duplicates(self, tmp_path: Path) -> None:
        lib = _make_lib(tmp_path)
        pql_file = tmp_path / "pack.pqp"
        lib.add("Unique Name", "text {selection}", "Custom")
        lib.export_pqp(pql_file)
        before = len(lib.all())
        lib.import_pqp(pql_file)
        assert len(lib.all()) == before
