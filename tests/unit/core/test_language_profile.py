"""Unit tests for quill.core.language_profile (issue #181)."""

from __future__ import annotations

from pathlib import Path

from quill.core.language_profile import (
    PLAIN_PROFILE,
    all_profiles,
    get_profile_by_name,
    get_profile_for_path,
)


class TestGetProfileForPath:
    def test_python_extension(self) -> None:
        profile = get_profile_for_path(Path("script.py"))
        assert profile.name == "Python"

    def test_python_pyw(self) -> None:
        assert get_profile_for_path(Path("app.pyw")).name == "Python"

    def test_javascript(self) -> None:
        assert get_profile_for_path(Path("index.js")).name == "JavaScript"

    def test_typescript_tsx(self) -> None:
        assert get_profile_for_path(Path("app.tsx")).name == "TypeScript"

    def test_html(self) -> None:
        assert get_profile_for_path(Path("page.html")).name == "HTML"

    def test_css(self) -> None:
        assert get_profile_for_path(Path("style.css")).name == "CSS"

    def test_scss(self) -> None:
        assert get_profile_for_path(Path("style.scss")).name == "CSS"

    def test_yaml(self) -> None:
        assert get_profile_for_path(Path("config.yml")).name == "YAML"

    def test_go(self) -> None:
        assert get_profile_for_path(Path("main.go")).name == "Go"

    def test_rust(self) -> None:
        assert get_profile_for_path(Path("lib.rs")).name == "Rust"

    def test_kotlin(self) -> None:
        assert get_profile_for_path(Path("Main.kt")).name == "Kotlin"

    def test_shell(self) -> None:
        assert get_profile_for_path(Path("run.sh")).name == "Shell"

    def test_markdown(self) -> None:
        assert get_profile_for_path(Path("README.md")).name == "Markdown"

    def test_json(self) -> None:
        assert get_profile_for_path(Path("package.json")).name == "JSON"

    def test_toml(self) -> None:
        assert get_profile_for_path(Path("pyproject.toml")).name == "TOML"

    def test_sql(self) -> None:
        assert get_profile_for_path(Path("query.sql")).name == "SQL"

    def test_unknown_extension_returns_plain(self) -> None:
        assert get_profile_for_path(Path("file.xyz")) is PLAIN_PROFILE

    def test_none_path_returns_plain(self) -> None:
        assert get_profile_for_path(None) is PLAIN_PROFILE

    def test_case_insensitive_extension(self) -> None:
        assert get_profile_for_path(Path("Script.PY")).name == "Python"

    def test_no_extension_returns_plain(self) -> None:
        assert get_profile_for_path(Path("Makefile")) is PLAIN_PROFILE


class TestGetProfileByName:
    def test_exact_match(self) -> None:
        profile = get_profile_by_name("Python")
        assert profile is not None
        assert profile.name == "Python"

    def test_case_insensitive(self) -> None:
        assert get_profile_by_name("python") is not None
        assert get_profile_by_name("PYTHON") is not None

    def test_not_found_returns_none(self) -> None:
        assert get_profile_by_name("Cobol") is None

    def test_kotlin(self) -> None:
        profile = get_profile_by_name("Kotlin")
        assert profile is not None
        assert ".kt" in profile.extensions


class TestAllProfiles:
    def test_returns_list(self) -> None:
        profiles = all_profiles()
        assert isinstance(profiles, list)
        assert len(profiles) > 0

    def test_sorted_by_name(self) -> None:
        profiles = all_profiles()
        names = [p.name for p in profiles]
        assert names == sorted(names)

    def test_includes_python(self) -> None:
        names = [p.name for p in all_profiles()]
        assert "Python" in names

    def test_includes_kotlin(self) -> None:
        names = [p.name for p in all_profiles()]
        assert "Kotlin" in names


class TestProfileAttributes:
    def test_python_comment_prefix(self) -> None:
        profile = get_profile_for_path(Path("x.py"))
        assert profile.comment_prefix == "# "

    def test_javascript_block_comment(self) -> None:
        profile = get_profile_for_path(Path("x.js"))
        assert profile.block_comment_start == "/*"
        assert profile.block_comment_end == "*/"

    def test_go_uses_tabs(self) -> None:
        profile = get_profile_for_path(Path("x.go"))
        assert profile.uses_tabs is True

    def test_python_has_keywords(self) -> None:
        profile = get_profile_for_path(Path("x.py"))
        assert "def" in profile.keywords
        assert "class" in profile.keywords
        assert "return" in profile.keywords

    def test_kotlin_has_keywords(self) -> None:
        profile = get_profile_for_path(Path("x.kt"))
        assert "fun" in profile.keywords
        assert "val" in profile.keywords
        assert "when" in profile.keywords
