"""tools/generate_lastfm_api_key.py: moves a pair from the environment, invents nothing."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))

import generate_lastfm_api_key as gen  # noqa: E402


def _clear(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (gen.KEY_ENV, gen.SECRET_ENV, gen.KEY_FILE_ENV, gen.SECRET_FILE_ENV):
        monkeypatch.delenv(name, raising=False)


def test_the_pair_comes_from_the_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _clear(monkeypatch)
    monkeypatch.setenv(gen.KEY_ENV, "KEY")
    monkeypatch.setenv(gen.SECRET_ENV, "SECRET")
    out = tmp_path / "_lastfm_api_key.py"
    assert gen.main(output=out) == 0
    assert gen.read_existing(out) == ("KEY", "SECRET")


def test_nothing_set_writes_an_empty_module_and_keeps_an_old_pair(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _clear(monkeypatch)
    out = tmp_path / "_lastfm_api_key.py"
    gen.main(output=out)
    assert gen.read_existing(out) == ("", "")
    gen.write_module("OLD", "OLDSECRET", out)
    gen.main(output=out)
    assert gen.read_existing(out) == ("OLD", "OLDSECRET")
