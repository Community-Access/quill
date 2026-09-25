"""`--rich` and `--plain` start a document in that kind (bad.md A7, P2.16).

QUILL Lite has had both since it shipped. The row looked like a one-liner and
was not: QUILL had no "start a document in this kind" seam at all -- `new_file`
made a document in whatever `default_new_document_format` said, and the only
way to another kind was the switcher afterwards. `new_document_in_format`
(P1.13) is that seam, and this flag is its second caller.
"""

from __future__ import annotations

import pytest

from quill.__main__ import _parse_cli_arguments


def test_no_flag_means_no_opinion() -> None:
    assert _parse_cli_arguments([]).document_kind is None


def test_rich_asks_for_a_rich_document() -> None:
    assert _parse_cli_arguments(["--rich"]).document_kind == "rtf"


def test_plain_asks_for_a_plain_one() -> None:
    assert _parse_cli_arguments(["--plain"]).document_kind == "plain"


def test_both_at_once_is_refused_rather_than_guessed() -> None:
    # argparse says which two options conflict, which is a better sentence than
    # anything we would write for a flag combination with no sensible answer.
    with pytest.raises(SystemExit):
        _parse_cli_arguments(["--rich", "--plain"])


def test_the_kind_is_one_the_switcher_knows() -> None:
    from quill.ui.main_frame_rich_mode import DOCUMENT_FORMATS

    for flag, expected in (("--rich", "rtf"), ("--plain", "plain")):
        assert _parse_cli_arguments([flag]).document_kind == expected
        assert expected in DOCUMENT_FORMATS


def test_run_app_takes_the_kind_and_only_uses_it_for_an_empty_launch() -> None:
    """A file named on the command line arrives in its own kind.

    Converting it because of a flag would be the flag editing the file.
    """
    import inspect

    from quill.ui.main_frame import run_app

    assert "document_kind" in inspect.signature(run_app).parameters
    source = inspect.getsource(run_app)
    assert "if not (startup_requests or []):" in source
    assert "frame.new_document_in_format(document_kind)" in source
