"""Unit tests for ``quill.core.about_info``.

The :class:`AboutInfo` dataclass is the structured data source for the
About Quill dialog. These tests pin its shape so future additions cannot
silently break the Overview / Dependencies / Links tab contract that
screen readers depend on (#260).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.about_info import (
    DependencyRow,
    Link,
    gather_about_info,
)

# ---------------------------------------------------------------------------
# Link validation
# ---------------------------------------------------------------------------


def test_link_rejects_empty_name() -> None:
    with pytest.raises(ValueError, match="name must not be empty"):
        Link(name="", url="https://example.com")


def test_link_rejects_empty_url() -> None:
    with pytest.raises(ValueError, match="has no URL"):
        Link(name="Example", url="")


def test_link_rejects_non_http_scheme() -> None:
    with pytest.raises(ValueError, match="must be http"):
        Link(name="Example", url="javascript:alert(1)")


def test_link_uniqueness_helper_drops_duplicates() -> None:
    seen: set[str] = set()
    out: list[Link] = []
    raw = (
        ("A", "https://a.example"),
        ("A again", "https://a.example"),
        ("B", "https://b.example"),
    )
    for name, url in raw:
        if url in seen:
            continue
        seen.add(url)
        out.append(Link(name=name, url=url))
    assert [link.url for link in out] == ["https://a.example", "https://b.example"]


# ---------------------------------------------------------------------------
# DependencyRow shape
# ---------------------------------------------------------------------------


def test_dependency_row_from_compliance_row_round_trip() -> None:
    sample = {
        "name": "pygments",
        "scope": "main",
        "declared": "pygments>=2.18",
        "version": "2.18.0",
        "license": "BSD-2-Clause",
        "homepage": "https://pygments.org",
        "notes": "syntax highlighting",
        "source": "",
    }
    row = DependencyRow.from_compliance_row(sample)
    assert row.name == "pygments"
    assert row.scope == "main"
    assert row.declared == "pygments>=2.18"
    assert row.version == "2.18.0"
    assert row.license == "BSD-2-Clause"
    assert row.homepage == "https://pygments.org"
    assert row.notes == "syntax highlighting"
    assert row.source == ""


# ---------------------------------------------------------------------------
# gather_about_info defaults and overrides
# ---------------------------------------------------------------------------


def test_gather_about_info_returns_real_version() -> None:
    info = gather_about_info()
    from quill import __version__

    assert info.version == __version__
    assert info.version  # not empty


def test_gather_about_info_default_channel_is_beta() -> None:
    info = gather_about_info()
    assert info.channel == "Beta"


def test_gather_about_info_link_rows_unique_and_https() -> None:
    info = gather_about_info()
    for link in info.org_links + info.github_links + info.contributors:
        assert link.url.startswith("https://")
    org_urls = [link.url for link in info.org_links]
    assert len(org_urls) == len(set(org_urls))


def test_gather_about_info_overrides_take_precedence() -> None:
    overrides = (Link(name="Custom", url="https://custom.example"),)
    info = gather_about_info(
        version="9.9.9",
        channel="RC",
        org_links=overrides,
        contributors=overrides,
        github_links=overrides,
    )
    assert info.version == "9.9.9"
    assert info.channel == "RC"
    assert info.org_links == overrides
    assert info.contributors == overrides
    assert info.github_links == overrides


def test_gather_about_info_missing_pyproject_marks_unavailable() -> None:
    info = gather_about_info(pyproject_path=Path("/nonexistent/pyproject.toml"))
    assert info.dependencies_available is False
    assert info.dependencies == ()


def test_gather_about_info_present_pyproject_marks_available() -> None:
    info = gather_about_info()
    assert info.dependencies_available is True


def test_gather_about_info_callbacks_are_invoked() -> None:
    deps_called: list[Path] = []
    bundle_called: list[int] = []

    def fake_deps(path: Path) -> tuple[DependencyRow, ...]:
        deps_called.append(path)
        return (
            DependencyRow(
                name="fake",
                scope="main",
                version="1.0",
                license="MIT",
                homepage="",
                declared="",
            ),
        )

    def fake_bundled() -> tuple[DependencyRow, ...]:
        bundle_called.append(1)
        return (
            DependencyRow(
                name="bundled-fake",
                scope="bundled",
                version="0.1",
                license="BSD",
                homepage="",
                declared="",
            ),
        )

    info = gather_about_info(
        pyproject_path=Path("/tmp/pyproject.toml"),
        dependency_loader=fake_deps,
        bundled_loader=fake_bundled,
        glow_summary="GLOW: test",
    )
    assert deps_called == [Path("/tmp/pyproject.toml")]
    assert bundle_called == [1]
    assert info.dependencies[0].name == "fake"
    assert info.bundled_components[0].name == "bundled-fake"
    assert info.glow_summary == "GLOW: test"


def test_gather_about_info_overview_headline_includes_version() -> None:
    info = gather_about_info(version="3.1.4", display_version="3.1.4")
    assert info.headline() == "QUILL for All 3.1.4"


def test_about_info_dataclass_is_frozen() -> None:
    info = gather_about_info(version="1.0")
    with pytest.raises((AttributeError, TypeError)):
        info.version = "2.0"  # type: ignore[misc]


def test_default_product_name_is_quill_for_all() -> None:
    info = gather_about_info()
    assert info.product_name == "QUILL for All"
    assert "QUILL for All" in info.headline()


def test_independence_notice_default_present() -> None:
    info = gather_about_info()
    assert info.independence_notice
    assert "independent open-source project" in info.independence_notice
    assert "Community Access" in info.independence_notice
    # Must name at least one similarly named third party so the user
    # understands the scope of the notice.
    assert "QuillBot" in info.independence_notice


def test_support_info_includes_product_and_build() -> None:
    info = gather_about_info(support_info="Product: QUILL for All\nBuild: 20260620.0\n")
    assert "QUILL for All" in info.support_info
    assert "20260620.0" in info.support_info


def test_copyright_and_license_defaults_use_branding() -> None:
    from quill.branding import APP_COPYRIGHT, APP_LICENSE_NAME

    info = gather_about_info()
    assert info.copyright == APP_COPYRIGHT
    assert info.license_name == APP_LICENSE_NAME
