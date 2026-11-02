"""The family prompt store, its migration, and the catalogue of shared prompts."""

from __future__ import annotations

import json
from pathlib import Path

from quill.core.ai import family_prompt_catalogue as cat
from quill.core.ai import family_prompts as fp
from quill.core.ai.connection_caps import PICTURES, TEXT
from quill.core.prompt_library import PromptLibrary


def _store(tmp_path: Path) -> fp.FamilyPromptStore:
    return fp.FamilyPromptStore(tmp_path / "prompts.json")


# -- the store, in the Prompt Library's shape -------------------------------- #


def test_added_prompt_is_seen_by_quills_prompt_library(tmp_path: Path) -> None:
    store = _store(tmp_path)
    prompt = store.add("Describe chart", "Describe the chart in {context}", needs=["pictures"])
    library = PromptLibrary(tmp_path / "prompts.json")
    found = library.find_by_id(prompt.id)
    assert found is not None and found.name == "Describe chart"
    assert store.find(prompt.id) == prompt
    assert prompt.needs == ("pictures",)


def test_needs_survive_the_prompt_library_rewriting_its_file(tmp_path: Path) -> None:
    store = _store(tmp_path)
    prompt = store.add("See", "Look at this", needs=["pictures", "bogus"])
    PromptLibrary(tmp_path / "prompts.json").add("Other", "text", "Custom")  # rewrites the file
    again = store.find(prompt.id)
    assert again is not None and again.needs == ("pictures",)


def test_writes_keep_keys_and_fields_the_store_does_not_own(tmp_path: Path) -> None:
    path = tmp_path / "prompts.json"
    path.write_text(
        json.dumps({
            "user_prompts": [{"id": "a", "name": "A", "text": "t", "future": 1}],
            "builtin_overrides": {"grammar": {"enabled": False}},
            "later_key": True,
        }),
        encoding="utf-8",
    )
    store = fp.FamilyPromptStore(path)
    store.add("B", "u")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["later_key"] is True
    assert data["builtin_overrides"] == {"grammar": {"enabled": False}}
    assert data["user_prompts"][0]["future"] == 1
    assert [p.name for p in store.prompts()] == ["A", "B"]


def test_remove(tmp_path: Path) -> None:
    store = _store(tmp_path)
    prompt = store.add("A", "t", needs=["tools"])
    assert store.remove(prompt.id)
    assert not store.remove(prompt.id)
    assert store.prompts() == []


def test_fill_family_prompt_fills_context_and_the_old_fields() -> None:
    text = "Q about {title}: {selection} | {document} | {context}"
    filled = fp.fill_family_prompt(
        text, selection="sel", document="doc", context="Station: KUAZ", title="T"
    )
    assert filled == "Q about T: sel | doc | Station: KUAZ"


# -- the migration ----------------------------------------------------------- #


def _sources(tmp_path: Path) -> list[fp.MigrationSource]:
    lite = tmp_path / "lite" / "prompts.json"
    lite.parent.mkdir()
    lite.write_text(
        json.dumps({
            "user_prompts": [
                {"id": "l1", "name": "Tighten", "text": "Make it tight: {selection}"},
                {"id": "l2", "name": "Shared", "text": "Same text"},
            ]
        }),
        encoding="utf-8",
    )
    studio = tmp_path / "ai" / "assistant-prompts.json"
    studio.parent.mkdir()
    studio.write_text(
        json.dumps({
            "prompts": [
                {"id": "s1", "title": "Tighten", "template": "Different: {selection}"},
                {"id": "s2", "title": "Shared", "template": "Same   text"},
            ]
        }),
        encoding="utf-8",
    )
    return [
        fp.read_library_file(lite, "QUILL Lite"),
        fp.read_assistant_prompts(studio),
        fp.read_vision_prompts([{"id": "v1", "title": "Chart", "prompt": "Describe the chart"}]),
    ]


def test_migration_merges_duplicates_and_names_the_second_by_its_store(tmp_path: Path) -> None:
    store = _store(tmp_path)
    report = fp.migrate(store, _sources(tmp_path))
    names = sorted(p.name for p in store.prompts())
    assert names == ["Chart", "Shared", "Tighten", "Tighten (from Prompt Studio)"]
    assert report.merged == ["Shared"]
    assert report.renamed == ["Tighten (from Prompt Studio)"]
    chart = next(p for p in store.prompts() if p.name == "Chart")
    assert chart.needs == ("pictures",)
    assert report.sentence() == (
        "4 prompts brought into one list; 1 already there; "
        "1 renamed after the store they came from."
    )


def test_migration_is_idempotent_and_never_touches_old_files(tmp_path: Path) -> None:
    store = _store(tmp_path)
    sources = _sources(tmp_path)
    before = {s.path: s.path.read_bytes() for s in sources if s.path}
    fp.migrate(store, sources)
    second = fp.migrate(store, sources)
    assert second.added == []
    assert len(store.prompts()) == 4
    assert {s.path: s.path.read_bytes() for s in sources if s.path} == before


def test_retiring_needs_a_check_and_a_later_release(tmp_path: Path) -> None:
    store = _store(tmp_path)
    sources = _sources(tmp_path)
    assert fp.check_migration(store, sources, release="3.0") != []  # nothing migrated yet
    assert fp.stores_ready_to_retire(store, sources, release="3.1") == []
    fp.migrate(store, sources)
    assert fp.check_migration(store, sources, release="3.0") == []
    assert store.meta()["migration"]["checked_release"] == "3.0"
    assert fp.stores_ready_to_retire(store, sources, release="3.0") == []  # same release
    ready = fp.stores_ready_to_retire(store, sources, release="3.1")
    assert sorted(p.name for p in ready) == ["assistant-prompts.json", "prompts.json"]


# -- the catalogue ----------------------------------------------------------- #


def test_every_app_gets_the_family_prompts_first() -> None:
    for app in cat.FAMILY_APPS:
        prompts = cat.quick_prompts_for(app)
        assert prompts[: len(cat.FAMILY_PROMPTS)] == cat.FAMILY_PROMPTS
    labels = [p.label for p in cat.quick_prompts_for("weather")]
    assert "Do I need a coat at 5?" in labels
    assert "What did I miss in this episode?" in [p.label for p in cat.quick_prompts_for("cast")]


def test_prompt_ids_are_unique_and_text_prompts_carry_context() -> None:
    every = list(cat.FAMILY_PROMPTS) + [p for ps in cat.APP_QUICK_PROMPTS.values() for p in ps]
    assert len({p.id for p in every}) == len(every)
    for prompt in every:
        assert prompt.local or "{context}" in prompt.text


def test_labelled_names_what_the_connection_lacks() -> None:
    assert cat.labelled("Describe", ["pictures"], [TEXT]) == (
        "Describe (needs a connection that sees)"
    )
    assert cat.labelled("Describe", ["pictures"], [TEXT, PICTURES]) == "Describe"
    assert cat.labelled("Organise", ["tools"], [TEXT]).endswith("(needs Copilot or Codex)")


def test_what_can_i_do_here_is_answered_from_f1() -> None:
    answer = cat.what_can_i_do_here(
        "The station list.",
        accessible_name="Stations",
        help_text="Every station you saved.",
        usage="A list.",
        commands=[("Play", "Enter"), ("Record", "Ctrl+R"), ("Details", "")],
    )
    assert answer.startswith("The station list.")
    assert "Every station you saved." in answer
    assert "- Record, Ctrl+R" in answer and "- Details" in answer
    assert cat.what_can_i_do_here("") != ""
