from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from quill.core.compliance import (
    ComplianceConfigError,
    build_dependency_notices,
    bundled_component_notices,
    dependency_names_from_pyproject,
    dependency_requirements_from_pyproject,
    evaluate_license_gate,
    normalize_requirement_name,
    render_dependency_notice_table,
    render_full_third_party_notices,
    render_third_party_notices,
)


def test_normalize_requirement_name() -> None:
    assert normalize_requirement_name("wxPython>=4.2.2") == "wxpython"
    assert normalize_requirement_name("pytest-xdist>=3.6 ; extra == 'dev'") == "pytest-xdist"


def test_html_to_text_notice_identifies_pypi_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "quill.core.compliance._distribution_metadata", lambda _name: ("unknown", "", "")
    )
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\ndependencies = ["html_to_text>=1.0.0"]\n', encoding="utf-8")
    rows = build_dependency_notices(pyproject, include_optional=False, include_build=False)
    assert len(rows) == 1
    assert "emludei" in rows[0]["notes"]
    assert "AccessibleApps" in rows[0]["notes"]
    assert rows[0]["license"] == "Apache-2.0"
    assert rows[0]["homepage"] == "https://github.com/emludei/html_to_text"


def test_social_metadata_has_unique_authors() -> None:
    root = Path(__file__).resolve().parents[3]
    with (root / "standalone" / "social" / "pyproject.toml").open("rb") as source:
        authors = tomllib.load(source)["project"]["authors"]
    names = [author["name"] for author in authors]
    assert len(names) == len(set(names))
    assert "Jeff Bishop" in names
    assert "Community Access" in names


def test_dependency_names_from_pyproject(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
dependencies = ["requests>=2", "rich==13"]
[project.optional-dependencies]
dev = ["pytest>=8"]
""".strip(),
        encoding="utf-8",
    )

    runtime = dependency_names_from_pyproject(pyproject, include_optional=False)
    all_dependencies = dependency_names_from_pyproject(pyproject, include_optional=True)

    assert runtime == ["requests", "rich"]
    assert all_dependencies == ["pytest", "requests", "rich"]


def test_evaluate_license_gate_and_render_notices() -> None:
    licenses = {"requests": "Apache-2.0", "wxpython": "UNKNOWN"}
    violations = evaluate_license_gate(licenses, {"MIT", "Apache-2.0"})
    assert violations == ["wxpython"]
    notices = render_third_party_notices(licenses)
    assert "| requests | Apache-2.0 |" in notices
    assert "| wxpython | UNKNOWN |" in notices


def test_dependency_requirements_include_build_and_optional(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[build-system]
requires = ["hatchling>=1.0"]

[project]
dependencies = ["requests>=2"]

[project.optional-dependencies]
dev = ["pytest>=9"]
ui = ["wxPython>=4.2.5"]
""".strip(),
        encoding="utf-8",
    )
    rows = dependency_requirements_from_pyproject(pyproject)
    names = {row["dependency"]: row for row in rows}
    assert "hatchling" in names
    assert "requests" in names
    assert "pytest" in names
    assert "wxpython" in names


def test_build_dependency_notices_and_render_table(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
dependencies = ["requests>=2"]
""".strip(),
        encoding="utf-8",
    )
    rows = build_dependency_notices(pyproject, include_optional=False, include_build=False)
    assert rows[0]["dependency"] == "requests"
    table = render_dependency_notice_table(rows)
    assert "| Dependency | Scope | Version | License | Link | Declared requirement |" in table
    assert "requests" in table


def test_dependency_table_cells_stay_single_line_and_bounded() -> None:
    # A package whose metadata exposes its full license text (newlines + pipes)
    # must not break the GFM table: cells are collapsed to one line, pipe-escaped,
    # and length-capped. (Regression: the About table shattered at platform_utils.)
    rows = [
        {
            "name": "platform_utils",
            "scope": "runtime",
            "version": "1.6.2",
            "license": "MIT\n\nfoo | bar\nbaz",
            "homepage": "https://example.com/a/very/long/path/that/exceeds/the/license/cap/easily",
            "declared": "platform_utils>=1.6",
        }
    ]
    table = render_dependency_notice_table(rows)
    body_line = table.splitlines()[2]
    assert body_line.startswith("| platform_utils |") and body_line.endswith(" |")
    # Exactly the 6 column separators on a single physical line (no row break).
    assert body_line.count(" | ") == 5
    assert "\n" not in body_line
    # The license pipe is escaped (not left to split the row), whitespace collapsed.
    assert "MIT foo \\| bar baz" in body_line
    # The Markdown link cell is NOT truncated, so it stays a valid [text](url) link.
    expected_link = (
        "[upstream](https://example.com/a/very/long/path/that/exceeds/the/license/cap/easily)"
    )
    assert expected_link in body_line


def test_render_full_third_party_notices_includes_bundled_sources(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
dependencies = ["requests>=2"]
""".strip(),
        encoding="utf-8",
    )
    data_dir = tmp_path / "quill" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    for name in (
        "words_alpha.LICENSE.txt",
        "th_en_US_LICENSE.txt",
        "th_en_US_WordNet_LICENSE.txt",
    ):
        (data_dir / name).write_text(f"{name} license text", encoding="utf-8")

    rendered = render_full_third_party_notices(pyproject, tmp_path)
    assert "# Third-Party Notices" in rendered
    assert "## Bundled components and data sources" in rendered
    assert "## Bundled license texts" in rendered
    assert "words_alpha.LICENSE.txt license text" in rendered


def test_bundled_component_notices_has_license_sources() -> None:
    rows = bundled_component_notices()
    assert any(row["source"] for row in rows)


def test_corrupt_pyproject_raises_clear_error(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("this is = not valid = toml ][", encoding="utf-8")

    with pytest.raises(ComplianceConfigError) as names_exc:
        dependency_names_from_pyproject(pyproject)
    assert str(pyproject) in str(names_exc.value)

    with pytest.raises(ComplianceConfigError) as rows_exc:
        dependency_requirements_from_pyproject(pyproject)
    assert str(pyproject) in str(rows_exc.value)


def test_missing_pyproject_still_raises_file_not_found(tmp_path: Path) -> None:
    missing = tmp_path / "pyproject.toml"
    with pytest.raises(FileNotFoundError):
        dependency_names_from_pyproject(missing)
