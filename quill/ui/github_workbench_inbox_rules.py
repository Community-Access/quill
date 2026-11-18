"""Inbox Rules...: make, list and delete rules for notifications (GitHub PRD 22.12).

Item > Inbox Rules... lists the rules, each as the sentence it is ("When a
notification is from octo/*, about a pull request: mark it done."), and
offers New Rule.... A new rule is asked for one question at a time -- what to
do, then which repository, why, about what, and words in the title, each of
which can be left as "any" -- and before it is saved QUILL says what it would
do to the notifications loaded today. A rule with no condition is refused.

The rules run when Notifications loads (:mod:`quill.core.github.explore_notifications`);
the rules themselves are :mod:`quill.core.github.inbox_rules`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = ["INBOX_RULE_REASONS", "INBOX_RULE_VERBS", "GitHubWorkbenchInboxRulesMixin"]

INBOX_RULE_VERBS: dict[str, frozenset[str]] = {"inbox_rules": frozenset({"view"})}

INBOX_RULE_REASONS: dict[str, str] = {
    "inbox_rules": "Inbox rules are for your notifications, while you are signed in.",
}


class GitHubWorkbenchInboxRulesMixin:
    frame: Any
    signed_in: bool
    _say: Callable[[str], None]
    _choose: Callable[[str, str, list[str]], int]
    _ask_text: Callable[..., str]
    _confirm: Callable[[str, str], bool]

    def _explore_client(self) -> Any:
        raise NotImplementedError

    def _fits_inbox_rules(self, _row: object) -> bool:
        return self.signed_in

    def _do_inbox_rules(self, _ref: Any, _row: object) -> None:
        from quill.core.github.inbox_rules import load_rules, save_rules

        rules = load_rules()
        labels = [rule.sentence for rule in rules] + ["New Rule..."]
        count = f"{len(rules)} rule{'s' if len(rules) != 1 else ''}" if rules else "No rules yet"
        picked = self._choose(
            "Inbox Rules",
            f"{count}. Rules run each time Notifications loads, the first that fits deciding. "
            "Choose a rule to delete it, or New Rule...",
            labels,
        )
        if picked < 0:
            return
        if picked == len(rules):
            self._new_inbox_rule(rules)
            return
        rule = rules[picked]
        if not self._confirm("Inbox Rules", f"Delete this rule? {rule.sentence}"):
            return
        try:
            save_rules([kept for kept in rules if kept is not rule])
        except OSError as exc:
            self._say(f"Could not save the rules: {exc}")
            return
        self._say("Deleted the rule.")

    def _seed_note(self) -> Any:
        """The selected notification, to suggest its repository; or None."""
        row = self.frame.selected_row() if self.frame is not None else None
        if getattr(row, "kind", "") != "notification":
            return None
        notes = self._loaded_notes()
        return next((note for note in notes if note.id == getattr(row, "key", "")), None)

    def _loaded_notes(self) -> list[Any]:
        loaded = getattr(self._explore_client(), "loaded_notifications", None)
        return list(loaded()) if callable(loaded) else []

    def _new_inbox_rule(self, rules: list[Any]) -> None:
        from quill.core.github.inbox_rules import ACTIONS, SUBJECTS, InboxRule, preview, save_rules
        from quill.core.github.notification_triage import REASON_WORDS, subject_in_words

        title = "New Inbox Rule"
        actions = list(ACTIONS)
        action = self._choose(
            title, "What should the rule do?", [ACTIONS[a].capitalize() for a in actions]
        )
        if action < 0:
            return
        seed = self._seed_note()
        repository = self._ask_text(
            title,
            "From which repository? owner/name; a * matches any part, as in octo/*; blank for any:",
            value=seed.repository if seed is not None else "",
        )
        reasons = list(REASON_WORDS)
        reason = self._choose(
            title,
            "Why it came to you:",
            ["Any reason"] + [REASON_WORDS[code].capitalize() for code in reasons],
        )
        if reason < 0:
            return
        subject = self._choose(
            title,
            "What it is about:",
            ["Anything"] + [subject_in_words(code).capitalize() for code in SUBJECTS],
        )
        if subject < 0:
            return
        words = self._ask_text(title, "Words its title must contain, or blank for any:")
        rule = InboxRule(
            action=actions[action],
            repository=repository.strip(),
            reason=reasons[reason - 1] if reason > 0 else "",
            subject=SUBJECTS[subject - 1] if subject > 0 else "",
            title_contains=words.strip(),
        )
        if not rule.has_condition:
            self._say(
                "A rule with no condition would act on every notification, so nothing was saved."
            )
            return
        if not self._confirm(
            title,
            f"{rule.sentence}\n\n{preview(rule, self._loaded_notes())}\n\n"
            "Save this rule? It runs each time Notifications loads, before you see the list.",
        ):
            return
        try:
            save_rules([*rules, rule])
        except OSError as exc:
            self._say(f"Could not save the rule: {exc}")
            return
        self._say(f"Saved. {rule.sentence} It runs the next time Notifications loads.")
