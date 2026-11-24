"""FUX-11: the shared honesty around a sample (``quill.core.rehearsal``)."""

from __future__ import annotations

from quill.core.rehearsal import (
    SampleResult,
    estimate_sentence,
    fingerprint,
    limits_sentence,
    scale,
    stale_sentence,
    wait_phrase,
)


def _result(**over: object) -> SampleResult:
    values: dict[str, object] = {
        "fingerprint": fingerprint({"voice": "a"}),
        "covered": "the first 80 words of one.docx",
        "sample_units": 80.0,
        "total_units": 8000.0,
        "elapsed_seconds": 12.0,
        "output_bytes": 500_000,
        "output_seconds": 30.0,
    }
    values.update(over)
    return SampleResult(**values)  # type: ignore[arg-type]


def test_fingerprint_ignores_key_order_and_sees_every_value() -> None:
    assert fingerprint({"a": 1, "b": [2]}) == fingerprint({"b": [2], "a": 1})
    assert fingerprint({"a": 1}) != fingerprint({"a": 2})


def test_scale_is_linear_in_the_job_length() -> None:
    est = scale(
        sample_units=80, total_units=8000, elapsed_seconds=12, output_bytes=10, output_seconds=30
    )
    assert est.seconds == 1200
    assert est.output_bytes == 1000
    assert est.output_seconds == 3000


def test_scale_refuses_to_guess_from_nothing() -> None:
    assert scale(sample_units=0, total_units=10, elapsed_seconds=5).seconds is None
    assert scale(sample_units=10, total_units=0, elapsed_seconds=5).seconds is None


def test_the_estimate_says_what_was_measured_and_that_it_is_an_estimate() -> None:
    text = estimate_sentence(_result(), job="all 3 documents")
    assert text.startswith("The sample took 12 seconds to make.")
    assert "all 3 documents should take about 20 minutes" in text
    assert "play for about 50 minutes" in text
    assert "be about" in text and "MB" in text
    assert text.endswith("This is an estimate.")


def test_the_estimate_leaves_out_what_was_not_measured() -> None:
    text = estimate_sentence(_result(output_bytes=None, output_seconds=None))
    assert "play for" not in text and "be about" not in text
    assert "the whole job should take about 20 minutes on this computer" in text


def test_no_estimate_when_the_job_length_is_unknown() -> None:
    text = estimate_sentence(_result(total_units=0))
    assert "There is no estimate" in text


def test_limits_and_staleness_are_said_plainly() -> None:
    assert "the first 80 words of one.docx only" in limits_sentence(
        "the first 80 words of one.docx"
    )
    assert "does not prove the rest" in limits_sentence("x")
    assert stale_sentence().startswith("Out of date:")
    result = _result()
    assert result.is_current(fingerprint({"voice": "a"}))
    assert not result.is_current(fingerprint({"voice": "b"}))


def test_short_waits_are_not_given_false_precision() -> None:
    assert wait_phrase(20) == "under a minute"
    assert wait_phrase(3900) == "about 1 hour 5 minutes"
