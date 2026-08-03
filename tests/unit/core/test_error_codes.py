from __future__ import annotations

from quill.core.error_codes import CodedError


class _SampleCodedError(CodedError):
    code = "QUILL-TEST-SAMPLE-CODE"


def test_str_prefixes_the_code() -> None:
    assert str(_SampleCodedError("something broke")) == "[QUILL-TEST-SAMPLE-CODE] something broke"


def test_str_without_a_code_has_no_brackets() -> None:
    class _Uncoded(CodedError):
        pass

    assert str(_Uncoded("plain message")) == "plain message"


# -- user-facing messages (the error-specificity programme) --------------------


def test_user_message_appends_the_hint_for_a_known_code() -> None:
    from quill.core import error_codes

    class _Hinted(CodedError):
        code = "QUILL-TEST-HINTED"

    error_codes.USER_HINTS["QUILL-TEST-HINTED"] = "Do the specific thing."
    try:
        message = _Hinted("The exact failure.").user_message()
    finally:
        error_codes.USER_HINTS.pop("QUILL-TEST-HINTED", None)

    assert message == "[QUILL-TEST-HINTED] The exact failure. Do the specific thing."


def test_class_level_user_hint_overrides_the_table() -> None:
    class _Custom(CodedError):
        code = "QUILL-TEST-CUSTOM"
        user_hint = "Use the class hint."

    assert _Custom("Broke.").user_message().endswith("Broke. Use the class hint.")


def test_user_message_without_a_hint_is_just_the_coded_message() -> None:
    assert (
        _SampleCodedError("something broke").user_message()
        == "[QUILL-TEST-SAMPLE-CODE] something broke"
    )


def test_user_message_does_not_duplicate_a_hint_already_present() -> None:
    class _Hinted(CodedError):
        code = "QUILL-TEST-NODUP"
        user_hint = "Check the cable."

    message = _Hinted("Failed. Check the cable.").user_message()
    assert message.count("Check the cable.") == 1


def test_user_facing_message_falls_back_for_plain_exceptions() -> None:
    from quill.core.error_codes import user_facing_message

    assert user_facing_message(ValueError("bad value")) == "bad value"


def test_user_facing_message_never_returns_an_empty_string() -> None:
    from quill.core.error_codes import user_facing_message

    # A blank error is indistinguishable from a crash for a blind user; the
    # class name is the last-resort diagnosis.
    assert user_facing_message(RuntimeError()) == "RuntimeError"


def test_shipped_hints_are_complete_sentences() -> None:
    from quill.core.error_codes import USER_HINTS

    for code, hint in USER_HINTS.items():
        assert hint.strip().endswith("."), f"{code} hint must be a full sentence"
        assert len(hint) > 20, f"{code} hint must name a concrete next step"
