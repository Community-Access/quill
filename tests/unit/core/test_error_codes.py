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
