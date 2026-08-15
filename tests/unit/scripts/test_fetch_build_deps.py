"""Layout checks for the build-dependency staging cache (no network).

``fetch_build_deps`` used to map components with a two-way ternary, so any name
that was not ``ffmpeg`` silently resolved to the libmpv directory. It is a dict
now, and these tests keep the dict and the advertised component list in step --
a component that is offered on the command line but has no layout entry would
otherwise fail with a bare ``KeyError`` partway through a build.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_module():
    path = _REPO_ROOT / "scripts" / "fetch_build_deps.py"
    spec = importlib.util.spec_from_file_location("fetch_build_deps", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["fetch_build_deps"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def fbd():
    return _load_module()


def test_every_component_has_a_layout_entry(fbd) -> None:
    for component in fbd.COMPONENTS:
        assert component in fbd._LAYOUT, component
        subdir, sentinel = fbd._LAYOUT[component]
        assert subdir and sentinel


def test_no_orphan_layout_entries(fbd) -> None:
    assert set(fbd._LAYOUT) == set(fbd.COMPONENTS)


def test_components_stage_into_distinct_directories(fbd) -> None:
    dirs = [fbd.component_dir(c) for c in fbd.COMPONENTS]
    assert len(set(dirs)) == len(dirs)


def test_piper_is_offered_and_staged_under_its_own_dir(fbd) -> None:
    # gen_voice_previews.py's documented invocation points at this exact path.
    assert "piper" in fbd.COMPONENTS
    assert fbd.component_dir("piper").name == "piper"
    assert fbd._sentinel("piper") == "piper.exe"


def test_deps_root_honours_the_env_override(fbd, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QUILL_BUILD_DEPS_DIR", str(tmp_path))
    assert fbd.deps_root() == tmp_path
    assert fbd.component_dir("piper") == tmp_path / "piper"


def test_is_staged_is_false_for_an_empty_cache(fbd, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QUILL_BUILD_DEPS_DIR", str(tmp_path))
    for component in fbd.COMPONENTS:
        assert fbd.is_staged(component) is False
