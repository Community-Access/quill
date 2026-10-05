"""The optional speech models: every one pinned, CPU only, honest, and in order."""

from __future__ import annotations

import re

import pytest

from quill.core.windows_dictation import engines
from quill.core.windows_dictation.model_catalog import (
    CATALOGUE,
    CPU_ONLY,
    GROUPS,
    catalogue_ids,
    downloadable,
    megabytes,
)

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


@pytest.mark.parametrize("model", CATALOGUE, ids=lambda m: m.id)
def test_every_model_is_pinned_to_a_commit_a_size_and_a_checksum(model) -> None:
    assert _HEX40.match(model.commit), "a moving ref (main) would change under us"
    assert model.files, "a model with no files"
    for item in model.files:
        assert _HEX64.match(item.sha256), item.name
        assert item.size > 0, item.name
        url = model.url(item)
        assert url.startswith("https://huggingface.co/")
        assert f"/resolve/{model.commit}/" in url
        assert "/main/" not in url
    roles = {item.role for item in model.files}
    assert {"encoder", "decoder", "tokens"} <= roles
    if model.kind in {"nemotron", "nemo_transducer"}:
        assert "joiner" in roles


@pytest.mark.parametrize("model", CATALOGUE, ids=lambda m: m.id)
def test_every_model_says_cpu_only_and_names_its_licence_and_sources(model) -> None:
    assert CPU_ONLY in model.description
    assert model.licence and model.licence_url.startswith("https://")
    assert model.source
    assert set(model.languages) <= {"en", "es"} and "en" in model.languages
    assert model.group in GROUPS
    assert model.good_for and model.works_best_on
    # Every accuracy figure names where it was published.
    assert any(site in model.accuracy for site in ("arxiv.org", "huggingface.co", "github.com"))
    assert model.cost_factor > 0


def test_ids_and_folders_are_unique_and_never_a_built_in_engine() -> None:
    ids = catalogue_ids()
    assert len(ids) == len(set(ids))
    assert len({m.folder for m in CATALOGUE}) == len(CATALOGUE)
    assert not set(ids) & {engine.id for engine in engines.ENGINES}


def test_the_vs_code_models_come_first_in_the_owners_order() -> None:
    assert [m.id for m in CATALOGUE[:5]] == [
        "nemotron",
        "parakeet_unified",
        "parakeet",
        "whisper_small",
        "whisper_base",
    ]
    assert [m.id for m in CATALOGUE if m.suggested] == ["nemotron"]
    groups = [m.group for m in CATALOGUE]
    assert groups == sorted(groups, key=GROUPS.index), "groups stay together, in order"


def test_english_only_whisper_is_english_and_many_languages_includes_spanish() -> None:
    for model in CATALOGUE:
        if model.group == "Whisper, English only":
            assert model.languages == ("en",)
        if model.group == "Whisper, many languages":
            assert "es" in model.languages


def test_a_downloaded_model_is_a_valid_engine_that_punctuates() -> None:
    from quill.core.windows_dictation.preferences import DictationPreferences

    assert engines.coerce_engine("NEMOTRON") == "nemotron"
    assert engines.is_model_engine("whisper_small")
    assert not engines.is_model_engine("windows")
    assert DictationPreferences(engine="parakeet").engine_punctuates
    assert engines.engine_info("nemotron").label.endswith("(downloaded)")


def test_spanish_goes_to_the_model_when_it_knows_spanish_and_to_whisper_when_not() -> None:
    assert engines.model_for("whisper_small", "es").id == "whisper_small"
    assert engines.model_for("moonshine_base", "es").id == "whisper_multilingual"
    assert engines.model_for("nemotron", "en").id == "nemotron"


def test_sizes_read_as_people_expect() -> None:
    assert megabytes(682_215_474) == "682 MB"
    assert megabytes(1_775_753_918) == "1.8 GB"
    assert downloadable("nemotron") is CATALOGUE[0]
    assert downloadable("dragon") is None
