"""Opening a subscription list by double-clicking it.

An OPML file is how one podcast app hands its whole subscription list to
another, and Cast could only receive one through a file picker inside a dialog
inside a menu. The command-line half is small; the ways it could go wrong are
what these cover.
"""

from __future__ import annotations

import pytest

from quill.core.podcasts.opml_cli import (
    OPML_SUFFIXES,
    describe_opened_file,
    looks_like_opml_path,
    opml_path_from_argv,
    opml_progid,
)


@pytest.mark.parametrize("switch", ["--safe-mode", "-s", "--data-dir=x.opml"])
def test_a_switch_is_never_mistaken_for_a_file(switch: str) -> None:
    # Switches share the argument list, and a leading dash is the one reliable
    # way to tell them apart.
    assert looks_like_opml_path(switch) is False


def test_an_xml_export_still_counts() -> None:
    # Plenty of apps export OPML with an .xml extension, and refusing those
    # would fail the exact hand-off this exists for.
    assert ".xml" in OPML_SUFFIXES
    assert looks_like_opml_path("subscriptions.xml") is True


def test_only_a_file_that_exists_opens_the_import(tmp_path) -> None:
    real = tmp_path / "subs.opml"
    real.write_text("<opml/>", encoding="utf-8")
    assert opml_path_from_argv(["--safe-mode", str(real)]) == real
    # A path typed wrongly, or one whose file has moved, opens the app
    # normally rather than an import flow for something that is not there.
    assert opml_path_from_argv([str(tmp_path / "gone.opml")]) is None


def test_the_first_real_one_wins(tmp_path) -> None:
    second = tmp_path / "b.opml"
    second.write_text("<opml/>", encoding="utf-8")
    assert opml_path_from_argv([str(tmp_path / "a.opml"), str(second)]) == second


def test_a_quoted_path_from_a_shell_still_resolves(tmp_path) -> None:
    real = tmp_path / "subs.opml"
    real.write_text("<opml/>", encoding="utf-8")
    assert opml_path_from_argv([f'"{real}"']) == real


@pytest.mark.parametrize("argv", [[], ["--safe-mode"], ["book.epub"], [""]])
def test_an_ordinary_launch_finds_nothing(argv: list[str]) -> None:
    assert opml_path_from_argv(argv) is None


def test_the_progid_has_one_source() -> None:
    # An app that registers QUILLCast.opml and an uninstaller that removes
    # QUILLCast.OPML would leave a broken association behind.
    assert opml_progid() == "QUILLCast.opml"
    assert opml_progid("QUILL") == "QUILL.opml"


def test_opening_from_explorer_says_why_a_window_appeared(tmp_path) -> None:
    said = describe_opened_file(tmp_path / "My Podcasts.opml")
    assert "My Podcasts.opml" in said
    assert said.endswith(".")
