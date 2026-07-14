"""Tests for quill.tools.error_code_audit (GATE-EC, #873 follow-up sweep)."""

from __future__ import annotations

from quill.tools.error_code_audit import find_violations, find_violations_in_source


def test_clean_class_passes() -> None:
    src = (
        "from quill.core.error_codes import CodedError\n\n\n"
        "class FooError(CodedError):\n"
        '    code = "QUILL-FOO-BAR-BAZ"\n'
    )
    assert find_violations_in_source(src, "quill/core/foo.py") == []


def test_missing_coded_error_base_is_flagged() -> None:
    src = "class FooError(Exception):\n    pass\n"
    errors = find_violations_in_source(src, "quill/core/foo.py")
    assert any("FooError" in e and "CodedError" in e for e in errors)


def test_coded_error_base_without_own_code_is_flagged() -> None:
    src = (
        "from quill.core.error_codes import CodedError\n\n\nclass FooError(CodedError):\n    pass\n"
    )
    errors = find_violations_in_source(src, "quill/core/foo.py")
    assert any("FooError" in e and "code" in e for e in errors)


def test_malformed_code_format_is_flagged() -> None:
    src = (
        "from quill.core.error_codes import CodedError\n\n\n"
        "class FooError(CodedError):\n"
        '    code = "not-the-right-shape"\n'
    )
    errors = find_violations_in_source(src, "quill/core/foo.py")
    assert any("FooError" in e and "QUILL-" in e for e in errors)


def test_duplicate_codes_across_classes_are_flagged() -> None:
    src = (
        "from quill.core.error_codes import CodedError\n\n\n"
        "class FooError(CodedError):\n"
        '    code = "QUILL-FOO-BAR-BAZ"\n\n\n'
        "class OtherError(CodedError):\n"
        '    code = "QUILL-FOO-BAR-BAZ"\n'
    )
    errors = find_violations_in_source(src, "quill/core/foo.py")
    assert any("duplicate" in e.lower() for e in errors)


def test_non_exception_classes_are_ignored() -> None:
    src = "class Foo:\n    pass\n\n\nclass Bar(SomeOtherBase):\n    pass\n"
    assert find_violations_in_source(src, "quill/core/foo.py") == []


def test_subclass_of_a_coded_error_does_not_need_its_own_code() -> None:
    """A subclass of an already-migrated custom error (e.g.
    SpeechCancelledError(SpeechError)) inherits its parent's code and is not
    itself a direct Exception/CodedError subclass, so this gate does not
    require it to redeclare one."""
    src = (
        "from quill.core.error_codes import CodedError\n\n\n"
        "class FooError(CodedError):\n"
        '    code = "QUILL-FOO-BAR-BAZ"\n\n\n'
        "class FooCancelledError(FooError):\n"
        "    pass\n"
    )
    assert find_violations_in_source(src, "quill/core/foo.py") == []


def test_not_yet_migrated_class_is_flagged_even_if_named_like_one() -> None:
    """A plain class X(Exception): with no CodedError mixin at all must still
    be caught -- this is the main future-regression case the gate exists for."""
    src = "class FooError(Exception):\n    pass\n"
    assert find_violations_in_source(src, "quill/core/foo.py") != []


def test_no_uncoded_exception_classes_in_the_live_tree() -> None:
    assert find_violations() == []
