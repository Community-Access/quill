from __future__ import annotations

from pathlib import Path

from quill.core import brf_validator as v
from quill.core.brf_validator import ValidatorOptions, validate_brf

_CORPUS = Path(__file__).resolve().parents[2] / "corpus" / "braille" / "one_crazy_night.brf"


def _kinds(text: str, **opts: object) -> set[str]:
    return {w.kind for w in validate_brf(text, ValidatorOptions(**opts))}  # type: ignore[arg-type]


def test_clean_document_has_no_warnings() -> None:
    page = "\n".join(["ab"] * 6)
    text = page + "\f" + page + "\n"
    assert validate_brf(text) == []


def test_line_too_long() -> None:
    text = "\n".join(["ab"] * 6 + ["x" * 41])
    assert v.KIND_LINE_TOO_LONG in _kinds(text)


def test_page_too_long() -> None:
    text = "\n".join(["ab"] * 26)
    assert v.KIND_PAGE_TOO_LONG in _kinds(text)


def test_page_too_short() -> None:
    text = "ab\f" + "\n".join(["ab"] * 6)
    assert v.KIND_PAGE_TOO_SHORT in _kinds(text)


def test_missing_form_feeds() -> None:
    text = "\n".join(["ab"] * 30)  # long, no form feeds
    assert v.KIND_MISSING_FORM_FEEDS in _kinds(text)


def test_mixed_line_endings_detected_not_corrected() -> None:
    text = "line one\r\nline two\nline three\r\n"
    warnings = validate_brf(text)
    assert any(w.kind == v.KIND_MIXED_LINE_ENDINGS for w in warnings)
    # Read-only: the validator does not return modified text, and the input is
    # unchanged (str is immutable, but assert the contract explicitly).
    assert "\r\n" in text and "\nline three" in text


def test_non_brf_ascii() -> None:
    text = "café time"  # é is U+00E9, outside NABCC
    assert v.KIND_NON_BRF_ASCII in _kinds(text)


def test_unicode_braille_as_brf() -> None:
    text = "⠁⠃ hello"  # U+2801..U+2803 braille block
    kinds = _kinds(text)
    assert v.KIND_UNICODE_BRAILLE in kinds


def test_unicode_braille_allowed_when_not_nabcc() -> None:
    text = "⠁⠃"
    assert v.KIND_UNICODE_BRAILLE not in _kinds(text, nabcc_mode=False)


def test_page_indicator_malformed() -> None:
    text = "-----\n" + "\n".join(["ab"] * 6)
    assert v.KIND_PAGE_INDICATOR in _kinds(text)


def test_page_numbering_gap() -> None:
    text = "--------#1\nab\f--------#3\nab"
    assert v.KIND_PAGE_NUMBERING in _kinds(text)


def test_page_numbering_duplicate() -> None:
    text = "--------#2\nab\f--------#2\nab"
    assert v.KIND_PAGE_NUMBERING in _kinds(text)


def test_running_head_inconsistency() -> None:
    text = "Story #1\nab\fStory #2\nab\fOther #3\nab"
    assert v.KIND_RUNNING_HEAD in _kinds(text)


def test_warning_describe_is_speakable() -> None:
    warning = validate_brf("x" * 41)[0]
    described = warning.describe()
    assert described.startswith("Warning on braille page 1, line 1:")


def test_corpus_sample_has_no_errors() -> None:
    if not _CORPUS.exists():
        return
    text = _CORPUS.read_text(encoding="utf-8", errors="replace")
    warnings = validate_brf(text)
    # The bundled sample is well-formed NABCC; it must not produce error-severity
    # findings (the strongest baseline guarantee we can assert content-free).
    assert [w for w in warnings if w.severity == v.SEVERITY_ERROR] == []
