from __future__ import annotations

from pathlib import Path

from generate_feedback_token import write_module


def test_write_module_with_token(tmp_path: Path) -> None:
    output = tmp_path / "_feedback_token.py"
    write_module("github_pat_example123", output)
    text = output.read_text(encoding="utf-8")
    assert "BUNDLED_TOKEN = 'github_pat_example123'" in text


def test_write_module_without_token_writes_empty_string(tmp_path: Path) -> None:
    output = tmp_path / "_feedback_token.py"
    write_module("", output)
    text = output.read_text(encoding="utf-8")
    assert "BUNDLED_TOKEN = ''" in text


def test_main_never_fails_without_env_var(monkeypatch, tmp_path: Path) -> None:
    import generate_feedback_token as gen

    monkeypatch.delenv("QUILL_FEEDBACK_GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(gen, "OUTPUT_FILE", tmp_path / "_feedback_token.py")
    assert gen.main([]) == 0
    assert (tmp_path / "_feedback_token.py").exists()


def test_require_token_fails_loudly_when_env_var_missing(monkeypatch, tmp_path: Path) -> None:
    # Release/beta packaging passes --require-token so a distributable can never
    # silently ship with an empty bundled token (the "No token" field regression).
    import generate_feedback_token as gen

    monkeypatch.delenv("QUILL_FEEDBACK_GITHUB_TOKEN", raising=False)
    output = tmp_path / "_feedback_token.py"
    monkeypatch.setattr(gen, "OUTPUT_FILE", output)
    assert gen.main(["--require-token"]) == 2
    # And it must NOT have written an empty token to be shipped.
    assert not output.exists()


def test_require_token_succeeds_when_env_var_present(monkeypatch, tmp_path: Path) -> None:
    import generate_feedback_token as gen

    monkeypatch.setenv("QUILL_FEEDBACK_GITHUB_TOKEN", "github_pat_example123")
    output = tmp_path / "_feedback_token.py"
    monkeypatch.setattr(gen, "OUTPUT_FILE", output)
    assert gen.main(["--require-token"]) == 0
    assert "github_pat_example123" in output.read_text(encoding="utf-8")


def test_missing_env_preserves_an_existing_bundled_token(monkeypatch, tmp_path: Path) -> None:
    # A dev/test rebuild with no env token must NOT wipe a working token that was
    # set up earlier -- it keeps the bug reporter consistent across rebuilds.
    import generate_feedback_token as gen

    output = tmp_path / "_feedback_token.py"
    gen.write_module("github_pat_previously_set", output)
    monkeypatch.delenv("QUILL_FEEDBACK_GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(gen, "OUTPUT_FILE", output)
    assert gen.main([]) == 0
    assert "github_pat_previously_set" in output.read_text(encoding="utf-8")


def test_env_token_overwrites_an_existing_bundled_token(monkeypatch, tmp_path: Path) -> None:
    import generate_feedback_token as gen

    output = tmp_path / "_feedback_token.py"
    gen.write_module("github_pat_old", output)
    monkeypatch.setenv("QUILL_FEEDBACK_GITHUB_TOKEN", "github_pat_new")
    monkeypatch.setattr(gen, "OUTPUT_FILE", output)
    assert gen.main([]) == 0
    text = output.read_text(encoding="utf-8")
    assert "github_pat_new" in text and "github_pat_old" not in text


def _no_ambient_token_sources(monkeypatch, gen) -> None:
    """Isolate from whatever this machine happens to have configured."""
    monkeypatch.delenv("QUILL_FEEDBACK_GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("QUILL_FEEDBACK_TOKEN_FILE", raising=False)
    monkeypatch.setattr(gen, "_read_credential_manager", lambda target: "")


def test_require_token_accepts_a_previously_bundled_token(monkeypatch, tmp_path: Path) -> None:
    """A machine that has built once can rebuild without re-supplying the secret.

    ``--require-token`` is mandatory for every packaged build (#919), and this
    is the source that makes that survivable: a token already bundled by this
    machine's last build. Without it, a developer holding a perfectly good
    ``_feedback_token.py`` still could not build.

    This does not weaken #919, whose point is that a build never ships a
    *tokenless* bug reporter -- a previously bundled token is not tokenless.
    """
    import generate_feedback_token as gen

    output = tmp_path / "_feedback_token.py"
    gen.write_module("github_pat_from_last_build", output)
    _no_ambient_token_sources(monkeypatch, gen)
    monkeypatch.setattr(gen, "OUTPUT_FILE", output)
    assert gen.main(["--require-token"]) == 0
    assert "github_pat_from_last_build" in output.read_text(encoding="utf-8")


def test_require_token_still_fails_when_nothing_is_bundled(monkeypatch, tmp_path: Path) -> None:
    """The #919 guard is intact: no source anywhere still hard-fails."""
    import generate_feedback_token as gen

    output = tmp_path / "_feedback_token.py"
    _no_ambient_token_sources(monkeypatch, gen)
    monkeypatch.setattr(gen, "OUTPUT_FILE", output)
    assert gen.main(["--require-token"]) == 2
    assert not output.exists()


def test_require_token_rejects_an_empty_bundled_token(monkeypatch, tmp_path: Path) -> None:
    """An empty bundled token is tokenless, not a token -- it must not satisfy
    the guard, or a build that once shipped ``BUNDLED_TOKEN = ''`` would keep
    reproducing exactly the "No token" regression #919 closed.
    """
    import generate_feedback_token as gen

    output = tmp_path / "_feedback_token.py"
    gen.write_module("", output)
    _no_ambient_token_sources(monkeypatch, gen)
    monkeypatch.setattr(gen, "OUTPUT_FILE", output)
    assert gen.main(["--require-token"]) == 2
