"""What the app says when a part it ships with is missing (2026-11-23).

These sentences reach the screen reader, braille and message boxes. They used
to name build scripts, ``pip install`` and "this build"; nothing a person could
act on. Each now says what does not work and how to get a whole copy back.
"""

from __future__ import annotations

import builtins
from pathlib import Path

import pytest

from quill.core import missing_parts
from quill.core.missing_parts import REPAIR_SENTENCE, damaged_part, missing_part
from quill.core.wordpress.workbench_practice import PracticeTools, missing_words

#: Words a user of the app must never be asked to understand.
_JARGON = (
    "script",
    "fetch_build_deps",
    "--only",
    "pip",
    "build",
    "runtime",
    "in-process",
    "quill[",
)


def _plain(sentence: str) -> None:
    lowered = sentence.lower()
    for word in _JARGON:
        assert word not in lowered, (word, sentence)
    assert sentence.endswith(REPAIR_SENTENCE)
    # Sentences, not a colon: NVDA and JAWS do not speak a colon.
    assert ":" not in sentence


def test_the_shape_is_effect_then_cause_then_repair() -> None:
    assert missing_part("X cannot start", "Y is missing") == (
        f"X cannot start. Y is missing. {REPAIR_SENTENCE}"
    )
    assert (
        damaged_part("X cannot start")
        == f"X cannot start. A part it needs is damaged. {REPAIR_SENTENCE}"
    )
    assert "new folder" in REPAIR_SENTENCE  # unzipping over the old copy keeps the damage


def _core(tmp_path: Path) -> Path:
    core = tmp_path / "core"
    core.mkdir()
    (core / "wp-load.php").write_text("<?php", encoding="utf-8")
    return core


def test_the_practice_site_names_each_missing_part_plainly(tmp_path: Path) -> None:
    node, cli = tmp_path / "node.exe", tmp_path / "cli.js"
    cases = {
        "WordPress Playground": PracticeTools(node, None, _core(tmp_path)),
        "Node.js": PracticeTools(None, cli, tmp_path / "core"),
        "Its WordPress files": PracticeTools(node, cli),
    }
    for part, tools in cases.items():
        sentence = missing_words(tools)
        assert sentence.startswith("The Practice Site cannot start. "), sentence
        assert part in sentence
        _plain(sentence)
    assert missing_words(PracticeTools(node, cli, tmp_path / "core")) == ""


def test_the_practice_site_counts_the_wordpress_archive(tmp_path: Path) -> None:
    archive = tmp_path / "wordpress-7.1.4.zip"
    archive.write_bytes(b"PK")
    tools = PracticeTools(tmp_path / "node.exe", tmp_path / "cli.js", None, archive)
    assert tools.has_wordpress and tools.ready
    assert missing_words(tools) == ""


def test_github_says_what_to_do_without_pip(monkeypatch) -> None:
    from quill.core.github import github_provider

    real_import = builtins.__import__

    def no_github(name, *args, **kwargs):
        if name == "github":
            raise ImportError("no PyGithub")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_github)
    for call in (github_provider.require_pygithub, github_provider._get_gh_module):
        with pytest.raises(github_provider.GitHubDependencyError) as raised:
            call()
        sentence = raised.value.args[0]
        assert sentence.startswith("GitHub features are not available. ")
        _plain(sentence)


@pytest.mark.parametrize(
    "name", ["COPILOT_MISSING", "COPILOT_DAMAGED", "CODEX_MISSING", "LISTENING_FFMPEG_MISSING"]
)
def test_the_ai_engines_say_it_plainly(name: str) -> None:
    _plain(getattr(missing_parts, name))


def test_copilot_reports_a_missing_runtime_in_plain_words(monkeypatch) -> None:
    from quill.core.ai import copilot_runtime

    monkeypatch.setattr(copilot_runtime, "find_copilot_runtime", lambda: None)
    monkeypatch.delenv(copilot_runtime.SDK_RUNTIME_PATH_ENV, raising=False)
    with pytest.raises(copilot_runtime.CopilotRuntimeUnavailable) as raised:
        copilot_runtime.runtime_path_for_launch()
    assert raised.value.args[0] == missing_parts.COPILOT_MISSING
    assert copilot_runtime.CopilotRuntimeUnavailable.user_hint == REPAIR_SENTENCE
    assert copilot_runtime.CopilotRuntimeUnverified.user_hint == REPAIR_SENTENCE


def test_the_listening_version_names_ffmpeg_only_when_it_is_missing(monkeypatch) -> None:
    from quill.core.speech import ffmpeg
    from quill.core.wordpress import listen_engines

    monkeypatch.setattr(ffmpeg, "find_ffmpeg", lambda: "ffmpeg.exe")
    monkeypatch.setattr(ffmpeg, "find_ffprobe", lambda: "ffprobe.exe")
    assert listen_engines.speak_problem() == ""
    monkeypatch.setattr(ffmpeg, "find_ffprobe", lambda: None)
    sentence = listen_engines.speak_problem()
    assert sentence.startswith("Make a Listening Version cannot start. FFmpeg")
    _plain(sentence)
    assert listen_engines.default_engines().speak_problem is listen_engines.speak_problem
