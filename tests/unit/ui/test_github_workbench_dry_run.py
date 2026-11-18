"""Tools > Dry Run in the GitHub Workbench, and how a failure is said (PRD 22.8)."""

from __future__ import annotations

from quill.core.github.dry_run import DRY_RUN, DryRunStop
from quill.core.github.merge_readiness import MergeReadinessError
from quill.ui.github_workbench_development import DEVELOPMENT_VERBS
from quill.ui.github_workbench_dry_run import GitHubWorkbenchDryRunMixin, failure_sentence


class _Window(GitHubWorkbenchDryRunMixin):
    def __init__(self) -> None:
        self.said: list[str] = []

    def _say(self, text: str) -> None:
        self.said.append(text)


def test_the_switch_turns_on_and_off_and_says_so() -> None:
    assert "dry_run" in DEVELOPMENT_VERBS
    window = _Window()
    try:
        window._do_dry_run(None, None)
        assert DRY_RUN.on and window.said[-1].startswith("Dry Run is on.")
        window._do_dry_run(None, None)
        assert not DRY_RUN.on and window.said[-1] == "Dry Run is off. Writes go to GitHub again."
    finally:
        DRY_RUN.set(False)


def test_a_stop_is_said_as_itself_and_a_failure_without_its_code() -> None:
    stop = DryRunStop("Dry run: QUILL would send DELETE /x. Nothing was changed.")
    assert failure_sentence("delete it", stop) == stop.sentence
    error = MergeReadinessError("Somebody pushed.")
    assert str(error).startswith("[QUILL-")
    assert failure_sentence("merge", error) == "Could not merge: Somebody pushed."
    assert failure_sentence("x", RuntimeError()) == "Could not x: no reason was given"
