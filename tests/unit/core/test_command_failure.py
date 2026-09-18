"""A failed command says what failed (bad.md P0.9).

"Command failed: file.save" named the command the person had just pressed and
nothing else, so a full disk, a read-only folder, a character the encoding
cannot hold and a bug inside a Quillin were one sentence. A listener cannot
open a log to find the rest.
"""

from __future__ import annotations

from quill.core.command_failure import describe_command_failure
from quill.core.error_codes import CodedError


def test_the_command_is_still_named_because_a_bug_report_needs_it() -> None:
    assert describe_command_failure("file.save", OSError("nope")).startswith("file.save failed")


def test_the_class_name_survives_when_it_carries_information() -> None:
    message = describe_command_failure("file.save", OSError(28, "No space left on device"))
    assert "OSError" in message
    assert "No space left on device" in message


def test_a_class_name_that_says_nothing_is_left_out() -> None:
    """ "ValueError: bad regular expression" is noise in front of the sentence."""
    assert describe_command_failure("edit.find", ValueError("bad regular expression")) == (
        "edit.find failed -- bad regular expression"
    )


def test_an_exception_with_no_message_falls_back_to_its_type() -> None:
    assert describe_command_failure("x.y", RuntimeError()) == "x.y failed -- RuntimeError"


def test_a_quill_error_code_is_carried_through() -> None:
    """QUILL's own errors have a code, and the code is what a report needs."""

    class _Boom(CodedError):
        code = "QUILL-TEST-THING-BROKE"

    message = describe_command_failure("tools.thing", _Boom("it broke"))
    assert "QUILL-TEST-THING-BROKE" in message
    assert "it broke" in message


def test_the_editor_uses_it() -> None:
    import inspect

    from quill.ui.main_frame import MainFrame

    source = inspect.getsource(MainFrame._run_command)
    assert "describe_command_failure(command_id, error)" in source
    # The old sentence survives only inside the docstring that explains why it
    # went; nothing sets it as a status any more.
    assert 'f"Command failed: {command_id}"' not in source
