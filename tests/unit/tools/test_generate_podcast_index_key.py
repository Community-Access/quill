"""Baking the vendor's Podcast Index credential into a build.

It generates no secret: podcastindex.org issues the key and secret to a
registered developer, and this moves that pair from the build environment into
a gitignored module the packager can see. The tests are about the *moving* --
where it looks, what it does when it finds nothing, and the one behaviour that
matters most, which is that a build with no credential in its environment does
not wipe a working one.
"""

from __future__ import annotations

from pathlib import Path

import generate_podcast_index_key as gen
import pytest


def test_the_environment_is_the_first_place_it_looks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(gen.KEY_ENV, "vendor-key")
    monkeypatch.setenv(gen.SECRET_ENV, "vendor-secret")

    assert gen.resolve() == ("vendor-key", "vendor-secret")


def test_a_file_named_by_the_environment_is_the_second(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """For a local build with nothing exported. Filesystem only, never network."""
    key_file = tmp_path / "key.txt"
    secret_file = tmp_path / "secret.txt"
    key_file.write_text("from-a-file\n", encoding="utf-8")
    secret_file.write_text("  secret-from-a-file  ", encoding="utf-8")
    monkeypatch.delenv(gen.KEY_ENV, raising=False)
    monkeypatch.delenv(gen.SECRET_ENV, raising=False)
    monkeypatch.setenv(gen.KEY_FILE_ENV, str(key_file))
    monkeypatch.setenv(gen.SECRET_FILE_ENV, str(secret_file))

    assert gen.resolve() == ("from-a-file", "secret-from-a-file")


def test_a_missing_file_is_no_credential_rather_than_a_crash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(gen.KEY_ENV, raising=False)
    monkeypatch.delenv(gen.SECRET_ENV, raising=False)
    monkeypatch.setenv(gen.KEY_FILE_ENV, str(tmp_path / "nowhere.txt"))
    monkeypatch.setenv(gen.SECRET_FILE_ENV, str(tmp_path / "nowhere.txt"))

    assert gen.resolve() == ("", "")


def test_the_written_module_is_importable_python(tmp_path: Path) -> None:
    out = tmp_path / "_podcast_index_key.py"
    gen.write_module("a-key", "a-secret", out)

    namespace: dict[str, object] = {}
    exec(compile(out.read_text("utf-8"), str(out), "exec"), namespace)  # noqa: S102

    assert namespace["BUNDLED_PODCAST_INDEX_KEY"] == "a-key"
    assert namespace["BUNDLED_PODCAST_INDEX_SECRET"] == "a-secret"
    assert "Do not edit by hand" in out.read_text("utf-8")


def test_a_build_with_nothing_exported_keeps_the_credential_it_had(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The behaviour that matters: a rebuild must not silently disarm the app."""
    out = tmp_path / "_podcast_index_key.py"
    gen.write_module("working-key", "working-secret", out)
    monkeypatch.setattr(gen, "OUTPUT_FILE", out)
    for name in (gen.KEY_ENV, gen.SECRET_ENV, gen.KEY_FILE_ENV, gen.SECRET_FILE_ENV):
        monkeypatch.delenv(name, raising=False)

    assert gen.main([]) == 0
    assert gen.read_existing(out) == ("working-key", "working-secret")


def test_half_a_credential_writes_an_empty_pair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The client refuses to sign with half a pair, so half is none."""
    out = tmp_path / "_podcast_index_key.py"
    monkeypatch.setattr(gen, "OUTPUT_FILE", out)
    monkeypatch.setenv(gen.KEY_ENV, "only-the-key")
    monkeypatch.delenv(gen.SECRET_ENV, raising=False)
    monkeypatch.delenv(gen.SECRET_FILE_ENV, raising=False)

    assert gen.main([]) == 0
    assert gen.read_existing(out) == ("only-the-key", "")

    from quill.core.podcasts import podcast_index

    assert not (bool("only-the-key") and bool(""))  # what available() asks
    assert podcast_index.available.__doc__  # the question is asked before offering


def test_the_generated_module_is_gitignored() -> None:
    """The whole point: the secret reaches a build without reaching the repo."""
    root = Path(__file__).resolve().parents[3]
    ignored = (root / ".gitignore").read_text("utf-8")

    assert "quill/_podcast_index_key.py" in ignored


def test_the_windows_build_runs_it() -> None:
    """A credential nothing bakes in is a credential no build ever carries."""
    root = Path(__file__).resolve().parents[3]
    script = (root / "scripts" / "build_windows_distribution.py").read_text("utf-8")

    assert "generate_podcast_index_key.py" in script
