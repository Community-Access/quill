"""Account > Roles and Access > Access Templates and Apply Access Template (GH-R-068).

Access Templates... makes, changes, renames and deletes this account's named
sets of access (:mod:`quill.core.github.access_templates`); nothing is sent
to GitHub. Apply Access Template... gives one person everything a template
holds, as one batch through the same path as an Access page's Add... and
Bulk Access Changes: the write gate has already held the command to the
account's level, the whole batch is previewed in words and confirmed at the
access tier, and each change reports its own result and is recorded in
Change History.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = ["GitHubWorkbenchAccessTemplatesMixin"]

_TITLE = "Access Templates"
_GRANT_HELP = (
    "One a line: write on owner/name (read, triage, write, maintain or admin), "
    "member of org/team or maintainer of org/team, member of org or owner of org."
)


def _templates_for(items: Any) -> Any:
    """The signed-in account's templates (read from disk each time)."""
    from quill.core.github.access_templates import AccessTemplates
    from quill.core.github.navigation_state import account_key_for_token

    return AccessTemplates.load(account_key_for_token(getattr(items, "token", None)))


class GitHubWorkbenchAccessTemplatesMixin:
    items: Any
    _say: Callable[[str], None]
    _ask_text: Callable[..., str]
    _choose: Callable[[str, str, list[str]], int]
    _confirm: Callable[[str, str], bool]
    _run_changes: Callable[[list[Any], str], None]

    def _tool_access_templates(self) -> None:
        templates = _templates_for(self.items)
        names = templates.names()
        rows = ["New Template...", *(templates.describe(name) for name in names)]
        index = self._choose(_TITLE, "Choose a template, or make a new one:", rows)
        if index < 0:
            return
        if index == 0:
            self._edit_template(templates, "")
            return
        name = names[index - 1]
        verbs = ["Change Its Access...", "Rename...", "Delete"]
        verb = self._choose(_TITLE, f"{name}:", verbs)
        if verb == 0:
            self._edit_template(templates, name)
        elif verb == 1:
            new = self._ask_text(_TITLE, f"New name for {name}:", value=name)
            problem = templates.rename(name, new) if new else "skip"
            if problem == "skip":
                return
            if problem:
                self._say(problem)
                return
            templates.save()
            self._say(f"Renamed to {' '.join(new.split())}.")
        elif verb == 2 and self._confirm(_TITLE, f"Delete the template {name}?"):
            templates.delete(name)
            templates.save()
            self._say(f"Deleted {name}. Nobody's access changed.")

    def _edit_template(self, templates: Any, name: str) -> None:
        if not name:
            name = self._ask_text(_TITLE, "Name, such as Contributor:")
            if not name:
                return
        text = self._ask_text(
            _TITLE, f"Access in {name}. {_GRANT_HELP}", multiline=True, value=templates.text(name)
        )
        if not text:
            return
        problem, rejected = templates.set_template(name, text)
        if problem:
            self._say(problem + (f" Not understood: {rejected[0]}" if rejected else ""))
            return
        from quill.core.github.access_templates import parse_grants

        templates.save()
        kept = len(parse_grants(text)[0])
        said = f"Saved {' '.join(name.split())}: {kept} {'place' if kept == 1 else 'places'}."
        if rejected:
            said += f" Left out, not understood: {'; '.join(rejected[:3])}."
        self._say(said)

    def _tool_apply_access_template(self) -> None:
        from quill.core.github.access_templates import template_plan

        templates = _templates_for(self.items)
        names = templates.names()
        if not names:
            self._say("There are no access templates yet. Access Templates... makes one.")
            return
        index = self._choose(
            "Apply Access Template", "Template:", [templates.describe(n) for n in names]
        )
        if index < 0:
            return
        name = names[index]
        who = self._ask_text("Apply Access Template", f"Give {name} to, by login:")
        who = who.strip().lstrip("@")
        if not who:
            return
        # The batch's preview names the person, every place and every role (18.4).
        self._run_changes(template_plan(templates.grants(name), who), f"{name} for {who}")
