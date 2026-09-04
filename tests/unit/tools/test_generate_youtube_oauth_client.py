"""Baking QUILL's YouTube OAuth client into a build.

Same shape as ``test_generate_podcast_index_key.py``: the pair is issued to a
registered Google Cloud developer outside this repository, and this only moves
it from the build environment into a gitignored module the packager can see.
The behaviour that matters most is that a build with nothing in its
environment does not silently wipe a working credential.
"""

from __future__ import annotations

from pathlib import Path

import generate_youtube_oauth_client as gen
import pytest


def test_the_environment_is_the_first_place_it_looks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(gen.CLIENT_ID_ENV, "vendor-client-id")
    monkeypatch.setenv(gen.CLIENT_SECRET_ENV, "vendor-client-secret")

    assert gen.resolve() == ("vendor-client-id", "vendor-client-secret")


def test_a_file_named_by_the_environment_is_the_second(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    id_file = tmp_path / "id.txt"
    secret_file = tmp_path / "secret.txt"
    id_file.write_text("from-a-file\n", encoding="utf-8")
    secret_file.write_text("  secret-from-a-file  ", encoding="utf-8")
    monkeypatch.delenv(gen.CLIENT_ID_ENV, raising=False)
    monkeypatch.delenv(gen.CLIENT_SECRET_ENV, raising=False)
    monkeypatch.setenv(gen.CLIENT_ID_FILE_ENV, str(id_file))
    monkeypatch.setenv(gen.CLIENT_SECRET_FILE_ENV, str(secret_file))

    assert gen.resolve() == ("from-a-file", "secret-from-a-file")


def test_the_written_module_is_importable_python(tmp_path: Path) -> None:
    out = tmp_path / "_youtube_oauth_client.py"
    gen.write_module("an-id", "a-secret", out)

    namespace: dict[str, object] = {}
    exec(compile(out.read_text("utf-8"), str(out), "exec"), namespace)  # noqa: S102

    assert namespace["BUNDLED_YOUTUBE_OAUTH_CLIENT_ID"] == "an-id"
    assert namespace["BUNDLED_YOUTUBE_OAUTH_CLIENT_SECRET"] == "a-secret"
    assert "Do not edit by hand" in out.read_text("utf-8")


def test_a_build_with_nothing_exported_keeps_the_credential_it_had(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "_youtube_oauth_client.py"
    gen.write_module("working-id", "working-secret", out)
    monkeypatch.setattr(gen, "OUTPUT_FILE", out)
    for name in (
        gen.CLIENT_ID_ENV,
        gen.CLIENT_SECRET_ENV,
        gen.CLIENT_ID_FILE_ENV,
        gen.CLIENT_SECRET_FILE_ENV,
    ):
        monkeypatch.delenv(name, raising=False)

    assert gen.main([]) == 0
    assert gen.read_existing(out) == ("working-id", "working-secret")


def test_half_a_credential_writes_an_empty_pair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "_youtube_oauth_client.py"
    monkeypatch.setattr(gen, "OUTPUT_FILE", out)
    monkeypatch.setenv(gen.CLIENT_ID_ENV, "only-the-id")
    monkeypatch.delenv(gen.CLIENT_SECRET_ENV, raising=False)
    monkeypatch.delenv(gen.CLIENT_SECRET_FILE_ENV, raising=False)

    assert gen.main([]) == 0
    assert gen.read_existing(out) == ("only-the-id", "")


def test_the_generated_module_is_gitignored() -> None:
    root = Path(__file__).resolve().parents[3]
    ignored = (root / ".gitignore").read_text("utf-8")

    assert "quill/_youtube_oauth_client.py" in ignored
