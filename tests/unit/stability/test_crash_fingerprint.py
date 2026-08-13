"""Crash fingerprints, QUILL's half (2026-08-13).

The 2026-08-12 triage closed eight issues that were two crashes: four from one
user three minutes apart, two more of the same crash weeks later, and a pair
26 seconds apart. ``feedback_hub`` owns the fingerprint definition; QUILL's job
is to hand it the right inputs from two different places -- a live exception in
the excepthook, and a saved ``crash-*.txt`` in the crash-recovery dialog.

**The property that makes the feature work is that those two agree.** A crash
reported live and the same crash reported later from its saved file have to
produce the same fingerprint, or they land on separate issues and nothing has
been fixed. That is ``test_the_live_and_saved_paths_agree`` below.
"""

from __future__ import annotations

import traceback

import pytest

from quill.core.crash_fingerprint import from_exception, from_traceback_text
from quill.core.issue_submit import fingerprint_for_traceback
from quill.stability.crash_submit import build_crash_report_payload, crash_fingerprint

feedback_hub = pytest.importorskip(
    "feedback_hub", reason="fingerprints come from the optional feedback_hub extra"
)
pytestmark = pytest.mark.skipif(
    not hasattr(feedback_hub, "compute_fingerprint"),
    reason="installed feedback_hub predates crash fingerprinting (< 1.1.0)",
)


def _raise(message: str = "something went wrong") -> BaseException:
    """Raise and return a real exception, with real frames."""

    def outer() -> None:
        inner()

    def inner() -> None:
        raise ValueError(message)

    try:
        outer()
    except ValueError as error:
        return error
    raise AssertionError("unreachable")


def _saved_text(error: BaseException) -> str:
    """Exactly what the excepthook writes to ``crash-<ts>.txt``."""
    return "".join(traceback.format_exception(type(error), error, error.__traceback__))


class TestOneDefinition:
    """Both callers must reach the same code, or they can drift apart."""

    def test_crash_submit_delegates_to_the_shared_module(self) -> None:
        assert crash_fingerprint is from_exception

    def test_issue_submit_delegates_to_the_shared_module(self) -> None:
        assert fingerprint_for_traceback is from_traceback_text


class TestTheTwoPathsAgree:
    def test_the_live_and_saved_paths_agree(self) -> None:
        # The whole feature rests on this. Break it and a crash reported live
        # and the same crash reported from its saved file file two issues.
        error = _raise()

        live = crash_fingerprint(type(error), error, error.__traceback__)
        from_file = fingerprint_for_traceback(_saved_text(error))

        assert live
        assert live == from_file

    def test_they_agree_across_different_exception_messages(self) -> None:
        # The same defect with a different value in the message is one crash.
        first, second = _raise("key 'a3f9' missing"), _raise("key 'b710' missing")

        assert crash_fingerprint(type(first), first, first.__traceback__) == (
            crash_fingerprint(type(second), second, second.__traceback__)
        )


class TestLivePath:
    def test_a_real_exception_yields_a_fingerprint(self) -> None:
        error = _raise()

        assert crash_fingerprint(type(error), error, error.__traceback__)

    def test_no_traceback_yields_empty_not_a_hash(self) -> None:
        # Empty means "do not deduplicate". A hash of nothing would collapse
        # every frameless report onto a single issue, which is far worse than
        # filing duplicates.
        assert crash_fingerprint(ValueError, ValueError("x"), None) == ""

    def test_a_broken_traceback_never_raises(self) -> None:
        assert crash_fingerprint(ValueError, ValueError("x"), object()) == ""

    def test_it_reaches_the_report_metadata(self) -> None:
        error = _raise()

        payload = build_crash_report_payload(
            exc_type=type(error),
            exc_value=error,
            exc_tb=error.__traceback__,
            local_crash_file=None,
            app_version="1.0.0",
            portable=False,
            screen_reader_name=None,
            recent_commands=None,
            active_document=None,
        )

        assert payload.metadata["fingerprint"] == crash_fingerprint(
            type(error), error, error.__traceback__
        )

    def test_a_frameless_crash_omits_the_key_entirely(self) -> None:
        # Absent rather than empty-string: the submit path tests truthiness,
        # and an empty value in the public issue metadata would just be noise.
        payload = build_crash_report_payload(
            exc_type=ValueError,
            exc_value=ValueError("x"),
            exc_tb=None,
            local_crash_file=None,
            app_version="1.0.0",
            portable=False,
            screen_reader_name=None,
            recent_commands=None,
            active_document=None,
        )

        assert "fingerprint" not in payload.metadata


class TestSavedTextPath:
    def test_empty_text_yields_empty(self) -> None:
        assert fingerprint_for_traceback("") == ""

    def test_log_only_text_yields_empty(self) -> None:
        # The crash-recovery offer can fire with no crash-*.txt at all, only a
        # log tail. A log tail is not a stable identity, so it must not
        # produce one -- two unrelated crashes merged into one issue is the
        # failure this prevents.
        assert fingerprint_for_traceback("2026-08-13 ERROR something happened") == ""

    def test_surrounding_report_text_does_not_change_it(self) -> None:
        error = _raise()
        bare = _saved_text(error)
        wrapped = f"Error evidence that triggered this offer:\n...\n\n{bare}\n\nNewest log: x"

        assert fingerprint_for_traceback(wrapped) == fingerprint_for_traceback(bare)


class TestItNeverBreaksReporting:
    def test_a_missing_feedback_hub_yields_empty_rather_than_raising(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import builtins

        real_import = builtins.__import__

        def refuse(name, *args, **kwargs):
            if name == "feedback_hub":
                raise ImportError("not installed")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", refuse)
        error = _raise()

        assert crash_fingerprint(type(error), error, error.__traceback__) == ""
        assert fingerprint_for_traceback(_saved_text(error)) == ""
