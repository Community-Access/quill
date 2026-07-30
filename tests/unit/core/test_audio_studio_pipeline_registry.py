"""Tests for the Quillin audio-pipeline registry and its use by the filter graph."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from quill.core.audio_enhance import build_filter_graph
from quill.core.audio_studio import pipeline_registry


@pytest.fixture(autouse=True)
def _clear() -> Iterator[None]:
    pipeline_registry.clear_steps()
    yield
    pipeline_registry.clear_steps()


def test_fragments_for_matching_stage() -> None:
    pipeline_registry.register_step("ext.s", "master", "S", lambda _stage: "loudnorm")
    assert pipeline_registry.filters_for_stage("master") == ["loudnorm"]
    assert pipeline_registry.filters_for_stage("pre") == []


def test_blank_fragment_skipped() -> None:
    pipeline_registry.register_step("ext.s", "master", "S", lambda _stage: "   ")
    assert pipeline_registry.filters_for_stage("master") == []


def test_faulty_step_skipped() -> None:
    def _boom(_stage: str) -> str:
        raise RuntimeError("boom")

    pipeline_registry.register_step("ext.bad", "master", "Bad", _boom)
    pipeline_registry.register_step("ext.good", "master", "Good", lambda _s: "aformat")
    assert pipeline_registry.filters_for_stage("master") == ["aformat"]


def test_register_replaces_by_id() -> None:
    pipeline_registry.register_step("ext.s", "master", "One", lambda _s: "")
    pipeline_registry.register_step("ext.s", "post", "Two", lambda _s: "")
    assert pipeline_registry.registered_step_ids() == ("ext.s",)


def test_build_filter_graph_appends_pipeline_stage() -> None:
    pipeline_registry.register_step("ext.s", "master", "S", lambda _s: "loudnorm=I=-16")
    graph = build_filter_graph(0, 0, 0, compressor_enabled=False, pipeline_stage="master")
    assert "loudnorm=I=-16" in graph


def test_build_filter_graph_ignores_pipeline_without_stage() -> None:
    # A radio-style caller passes no stage; contributed steps never apply.
    pipeline_registry.register_step("ext.s", "master", "S", lambda _s: "loudnorm")
    assert build_filter_graph(0, 0, 0, compressor_enabled=False) == ""


def test_build_filter_graph_pipeline_after_builtin_filters() -> None:
    pipeline_registry.register_step("ext.s", "post", "S", lambda _s: "aresample=48000")
    graph = build_filter_graph(6.0, 0, 0, compressor_enabled=True, pipeline_stage="post")
    # The contributed fragment comes last, after EQ + compressor.
    assert graph.split(",")[-1] == "aresample=48000"
