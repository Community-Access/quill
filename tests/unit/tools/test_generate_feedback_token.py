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
