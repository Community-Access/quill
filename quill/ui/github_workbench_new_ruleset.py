"""New Ruleset: Ctrl+N in a repository's Settings > Rulesets (GitHub PRD 18.3.1; GH-R-151).

A few plain questions, each its own small dialog: the name, branches or tags,
which ones, the rules (a check list), the approvals a pull request needs when
that rule is checked, and on or off. Then one question that says the whole
ruleset in words before anything is sent; the result is said from GitHub's
answer. Every other rule and setting is on the ruleset's sheet (Alt+Enter).
The engine is :mod:`quill.core.github.ruleset_new`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = ["NEW_RULESET_REASONS", "NEW_RULESET_VERBS", "GitHubWorkbenchNewRulesetMixin"]

NEW_RULESET_VERBS: dict[str, frozenset[str]] = {"new_ruleset": frozenset({"view"})}
NEW_RULESET_REASONS: dict[str, str] = {
    "new_ruleset": "New Here in a repository's Rulesets makes one, for its administrators.",
}


class GitHubWorkbenchNewRulesetMixin:
    frame: Any
    signed_in: bool
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _choose: Callable[[str, str, list[str]], int]
    _confirm: Callable[[str, str], bool]
    _ask_text: Callable[..., str]

    def github_api(self) -> Any:
        raise NotImplementedError

    def _fits_new_ruleset(self, _row: object) -> bool:
        current = getattr(self.frame, "current", None)
        return self.signed_in and getattr(current, "key", "") == "repo_rulesets"

    def _check_rules(
        self, title: str, prompt: str, labels: list[str], checked: list[int]
    ) -> list[int] | None:
        from quill.ui.dialog_contract import show_modal_dialog
        from quill.ui.wordpress_workbench_dialogs import ask_checks

        return ask_checks(
            self.frame.frame,
            show_modal_dialog,
            title=title,
            prompt=prompt,
            rows=labels,
            checked=checked,
            help_text="The rules the new ruleset starts with. More are on its sheet afterwards.",
        )

    def _do_new_ruleset(self, ref: Any, _row: object) -> None:
        from quill.core.github.ruleset_new import (
            BRANCH_ONLY,
            ENFORCEMENT_CHOICES,
            NEW_RULES,
            REF_CHOICES,
            RulesetRefused,
            create_ruleset,
            ruleset_request,
        )
        from quill.core.github.rulesets import summary

        title = "New Ruleset"
        name = self._ask_text(title, "Name of the new ruleset, such as Protect main:")
        if not name:
            return
        target_index = self._choose(title, f"What does {name} guard?", ["Branches", "Tags"])
        if target_index < 0:
            return
        target = ("branch", "tag")[target_index]
        plural = "tags" if target == "tag" else "branches"
        choices = [
            (key, f"Every {target}" if key == "~ALL" else words)
            for key, words in REF_CHOICES
            if not (target == "tag" and key == "~DEFAULT_BRANCH")
        ]
        which = self._choose(
            title, f"Which {plural} does {name} guard?", [words for _key, words in choices]
        )
        if which < 0:
            return
        include = choices[which][0]
        if include == "pattern":
            example = "v*" if target == "tag" else "release/*"
            include = self._ask_text(
                title, f"The names it guards, with * for any part, such as {example}:"
            )
            if not include:
                return
        offered = [(k, w) for k, w in NEW_RULES if not (target == "tag" and k in BRANCH_ONLY)]
        first = (
            0
            if target == "branch"
            else next(i for i, (k, _w) in enumerate(offered) if k == "deletion")
        )
        checked = self._check_rules(title, "Rules:", [w for _k, w in offered], [first])
        if checked is None:
            return
        if not checked:
            self._say("Check at least one rule. Nothing was made.")
            return
        rules = [offered[i][0] for i in checked]
        approvals = 0
        if "pull_request" in rules:
            answer = self._ask_text(
                title, "Approvals each pull request needs before merging, 0 to 10:", value="1"
            )
            if not answer:
                return
            if not answer.isdigit() or int(answer) > 10:
                self._say("Approvals are a whole number, 0 to 10. Nothing was made.")
                return
            approvals = int(answer)
        on = self._choose(title, f"Is {name} on?", [words for _key, words in ENFORCEMENT_CHOICES])
        if on < 0:
            return
        try:
            body = ruleset_request(
                name,
                target,
                include,
                rules,
                approvals=approvals,
                enforcement=ENFORCEMENT_CHOICES[on][0],
            )
        except RulesetRefused as exc:
            self._say(str(exc))
            return
        repository = ref.instance
        question = f"The ruleset {name} in {repository}. {summary(body)} Make it now?"
        if not self._confirm(title, question):
            return
        api = self.github_api()
        self._background(
            f"make the ruleset {name}",
            lambda: create_ruleset(api, repository, body),
            lambda said: (self._say(str(said)), self.frame.reload()),
        )
