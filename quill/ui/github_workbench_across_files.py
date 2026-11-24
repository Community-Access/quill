"""Files, people, repository settings and packages by name, in the Workbench (PRD 22.11).

The by-name commands for the places of
:mod:`quill.core.github.across_files` and
:mod:`quill.core.github.across_people_settings`, on top of the shared ones in
:mod:`quill.ui.github_workbench_across_names`:

- **Compare Configuration...** on a Workflows, Templates, Dependabot or
  CODEOWNERS by Name row: choose the version to compare from and the
  repository to compare with; the differences open in Compare Configuration's
  own window (#1959), whose Propose Update opens one pull request there.
- **Make Them the Same...** and **Add to Missing...** on those rows propose
  the winning version as one pull request in each repository, through the
  same preview and result per repository as every by-name change. Nothing is
  pushed; the results say how many pull requests wait for review.
- **Make Them the Same...** on a Repository Settings by Name row sets the
  winning value in each repository, with admin access, as the Repository
  sheet's field does in one.

People and packages are read only; the shared commands say why on their rows.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.across_files import FILE_KINDS
from quill.ui.github_workbench_across_more import kind_of

__all__ = ["FILES_REASONS", "FILES_VERBS", "GitHubWorkbenchAcrossFilesMixin"]

FILES_VERBS: dict[str, frozenset[str]] = {"across_compare_config": frozenset({"by_name"})}
FILES_REASONS: dict[str, str] = {
    "across_compare_config": (
        "Compare Configuration works on rows under Workflows by Name, Templates by Name, "
        "Dependabot by Name and CODEOWNERS by Name."
    ),
}
_PROPOSE = "Open Pull Requests"


def _repositories(count: int) -> str:
    return f"{count} repositor{'y' if count == 1 else 'ies'}"


class GitHubWorkbenchAcrossFilesMixin:
    """Compare Configuration on a file row, and the writes of the file and settings rows."""

    frame: Any
    _say: Callable[[str], None]
    _choose: Callable[[str, str, list[str]], int]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _survey_row: Callable[[object], tuple[Any, Any] | None]
    _run_plan: Callable[..., None]
    _compared: Callable[[str, str, list[Any]], None]
    _authoring_repo: Callable[[str], Any]

    def github_api(self) -> Any:
        raise NotImplementedError

    def _fits_across_compare_config(self, row: object) -> bool:
        return kind_of(row) in FILE_KINDS

    def _do_across_compare_config(self, _ref: Any, row: object) -> None:
        from quill.core.github.across_files import file_diff, source_copy

        pair = self._survey_row(row)
        if pair is None:
            return
        found, hit = pair
        title = "Compare Configuration"
        variants = hit.variants()
        index = 0
        if len(variants) > 1:
            labels = [
                f"Version {number}, in {_repositories(len(repos))}: {', '.join(repos)}"
                for number, (_props, repos) in enumerate(variants, start=1)
            ]
            index = self._choose(title, "Compare from which version?", labels)
            if index < 0:
                return
        winner = variants[index][0]
        source = source_copy(hit, winner)
        number = {props: n for n, (props, _r) in enumerate(variants, start=1)}
        differ = [c for c in hit.copies if c.props != tuple(winner)]
        others = [c.repository for c in differ] + list(hit.missing)
        labels = [f"{c.repository}, version {number[c.props]}" for c in differ]
        labels += [f"{repo}, does not have it" for repo in hit.missing]
        if not others:
            self._say(
                f"{hit.name} is the same in every repository that answered, so there is "
                "nothing to compare."
            )
            return
        index = self._choose(
            title, f"Compare {hit.name} from {source.repository} with which repository?", labels
        )
        if index < 0:
            return
        target = others[index]
        here = found.has(target, hit.name)
        api = self.github_api()

        def work() -> Any:
            return file_diff(api, found.kind, source, target, here)

        def done(diff: Any) -> None:
            self._compared(target, source.repository, [diff])

        self._background(f"compare {hit.name}", work, done)

    def _same_own_kind(self, found: Any, hit: Any, winner: Any) -> bool:
        """Make Them the Same for a file or a setting; False for the other kinds."""
        if found.kind in FILE_KINDS:
            from quill.core.github.across_files import plan_files

            self._run_plan("across_make_same", plan_files(found, hit, winner), _PROPOSE)
            return True
        if found.kind == "settings":
            from quill.core.github.across_people_settings import plan_settings_same

            plan = plan_settings_same(found, hit, winner)
            self._run_plan("across_make_same", plan, "Make the Same")
            return True
        return False

    def _add_own_kind(self, found: Any, hit: Any, winner: Any, targets: list[str]) -> bool:
        """Add to Missing for a file, as pull requests; False for the other kinds."""
        if found.kind not in FILE_KINDS:
            return False
        from quill.core.github.across_files import plan_files

        plan = plan_files(found, hit, winner, targets, missing=True)
        self._run_plan("across_add_missing", plan, _PROPOSE)
        return True

    def _own_work(self, api: Any, plan: Any) -> Callable[[], Any] | None:
        """The background run of a file or settings plan; None for the other kinds."""
        if plan.kind in FILE_KINDS:
            from quill.core.github.across_files import apply_files

            found = getattr(self, "_across_surveys", {})[plan.kind]
            source = found.has(plan.into, plan.name)
            return lambda: apply_files(api, plan, source, self._authoring_repo)
        if plan.kind == "settings":
            from quill.core.github.across_people_settings import apply_settings

            return lambda: apply_settings(api, plan)
        return None

    @staticmethod
    def _own_summary(plan: Any, results: Any) -> str:
        """The outcome of a file plan in pull requests; "" for the other kinds."""
        if plan.kind not in FILE_KINDS:
            return ""
        from quill.core.github.across_files import files_summary

        return files_summary(results)
