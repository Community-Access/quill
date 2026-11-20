"""dependabot.yml as a sheet, Dependabot's commands, and CODEOWNERS as a table (PRD 21.8, 22.1)."""

from __future__ import annotations

from typing import Any

from quill.core.github.codeowners_table import (
    CodeownersLines,
    codeowners_errors,
    owner_problem,
    pattern_problem,
    read_codeowners,
    who_owns,
)
from quill.core.github.dependabot_config import (
    COMMANDS,
    check_config,
    dump_config,
    entry_summary,
    is_dependabot,
    load_config,
)
from quill.core.github.rest_transport import GitHubRestError, RestResponse

DEPENDABOT = """# Keep things fresh.
version: 2
updates:
  - package-ecosystem: pip
    directory: /
    schedule:
      interval: weekly
      day: monday
      time: "09:00"
    open-pull-requests-limit: 5
    labels: [dependencies]
    groups:
      minor:
        update-types: [minor, patch]
  - package-ecosystem: github-actions
    directories: [/, /tools]
    schedule: {interval: monthly}
"""


def test_entries_read_as_rows_and_an_unchanged_file_is_kept_as_it_was() -> None:
    draft = load_config(DEPENDABOT)
    assert [entry_summary(e) for e in draft.entries] == [
        "pip in /, weekly on Monday at 09:00, up to 5 pull requests, labels dependencies, 1 group",
        "github-actions in / and /tools, monthly",
    ]
    assert check_config(draft) == []
    assert dump_config(draft) == DEPENDABOT
    draft.entries[1]["open-pull-requests-limit"] = 0
    text = dump_config(draft)
    assert text.startswith("# Keep things fresh.\n\nversion: 2\n")
    assert "update-types:" in text and "open-pull-requests-limit: 0" in text
    assert "version updates off (limit 0)" in entry_summary(draft.entries[1])


def test_a_missing_file_starts_as_version_two_with_no_entries() -> None:
    draft = load_config("")
    assert draft.data == {"version": 2, "updates": []}
    assert check_config(draft) == ["Updates: there are none, so Dependabot checks nothing."]


def test_what_dependabot_refuses_is_found_first() -> None:
    draft = load_config(
        """version: 1
colour: red
updates:
  - package-ecosystem: pipx
    schedule: {interval: fortnightly, day: someday, time: "9am", when: now}
    open-pull-requests-limit: -1
    reviewers: [jeff]
  - package-ecosystem: npm
    directory: /
    directories: [/web]
    schedule: {interval: cron}
  - package-ecosystem: npm
    directory: /
    schedule: {interval: daily}
  - package-ecosystem: npm
    directory: /
    schedule: {interval: daily}
"""
    )
    said = check_config(draft)
    for expected in (
        "The file: version must be 2.",
        "The file: colour is not something dependabot.yml has.",
        "Entry 1: pipx is not a package ecosystem Dependabot has.",
        "Entry 1: it has no directory; / is the repository's root.",
        "Entry 1: when is not something a schedule has.",
        "Entry 1: someday is not a day of the week.",
        "Entry 1: the time 9am is not hh:mm in 24 hours, such as 09:00.",
        "Entry 1: the pull request limit must be a whole number, 0 or more.",
        "Entry 2: use directory or directories, not both.",
        "Entry 2: a cron interval needs a cronjob.",
        "Entry 4: entry 3 already updates npm in /; Dependabot refuses the file with both.",
    ):
        assert expected in said, expected
    assert any(line.startswith("Entry 1: fortnightly is not an interval") for line in said)


def test_the_commands_are_dependabot_s_own_and_only_on_its_pull_requests() -> None:
    comments = [c.comment for c in COMMANDS]
    assert comments[:4] == [
        "@dependabot rebase",
        "@dependabot recreate",
        "@dependabot merge",
        "@dependabot squash and merge",
    ]
    assert "@dependabot ignore this major version" in comments
    assert all(c.help.endswith(".") for c in COMMANDS)
    assert len({c.key for c in COMMANDS}) == len(COMMANDS)
    assert is_dependabot("dependabot[bot]") and is_dependabot("app/dependabot")
    assert not is_dependabot("jeff")


# -- CODEOWNERS -------------------------------------------------------------------------

OWNERS = """# Everyone reviews everything.
* @org/everyone

/docs/ @writers # the docs team
*.js @web
docs/api/ @api
"""


def test_the_table_edits_one_line_and_keeps_every_note() -> None:
    lines = CodeownersLines(OWNERS)
    rows = lines.rows()
    assert [r.text() for r in rows] == [
        "Line 2: *, @org/everyone",
        "Line 4: /docs/, @writers",
        "Line 5: *.js, @web",
        "Line 6: docs/api/, @api",
    ]
    lines.set_rule(rows[1], "/docs/", ["@writers", "@editors"])
    assert "/docs/ @writers @editors # the docs team\n" in lines.text()
    assert lines.move_rule(lines.rows()[3], -1)
    assert lines.text().splitlines()[4:6] == ["docs/api/ @api", "*.js @web"]
    assert not lines.move_rule(lines.rows()[0], -1)
    made = lines.add_rule("/src/", ["@coders"])
    assert made.line == 7 and lines.text().endswith("/src/ @coders\n")
    lines.remove_rule(lines.rows()[0])
    assert lines.text().startswith("# Everyone reviews everything.\n\n/docs/")


def test_shapes_github_skips_are_said() -> None:
    assert pattern_problem("!docs/").startswith("CODEOWNERS has no !")
    assert pattern_problem("[ab].md") == "CODEOWNERS does not take [ ] character ranges."
    assert pattern_problem("docs/") == ""
    assert owner_problem("writers").startswith("writers is not an owner")
    assert owner_problem("@org/team/extra").endswith("is not @person or @organization/team.")
    assert owner_problem("a@b.org") == "" and owner_problem("@jeff") == ""
    assert CodeownersLines("[x] @a\n/y/ nobody\n").problems() == [
        "Line 1: CODEOWNERS does not take [ ] character ranges.",
        "Line 2: nobody is not an owner: start a person or team with @, or give an email address.",
    ]


def test_who_owns_this_is_the_last_matching_rule_as_github_decides() -> None:
    said = who_owns(".github/CODEOWNERS", OWNERS, "docs/api/index.md")
    assert said == (
        "@api own docs/api/index.md: line 6 of .github/CODEOWNERS, docs/api/, the last rule "
        "that matches. It wins over 2 earlier matching rules."
    )
    assert who_owns(".github/CODEOWNERS", OWNERS, "src/app.js").startswith("@web own src/app.js")
    assert who_owns(".github/CODEOWNERS", "/docs/ @w\n", "src/x.py") == (
        "No rule in .github/CODEOWNERS matches src/x.py, so nobody is asked to review it."
    )
    assert who_owns("", "", "a.md").startswith("This repository has no CODEOWNERS file")
    assert "names no owners" in who_owns("CODEOWNERS", "* @a\n/vendor/\n", "vendor/x")


class _Missing(Exception):
    status = 404


class _File:
    def __init__(self, text: str) -> None:
        self.decoded_content = text.encode()


class _Repo:
    def __init__(self, files: dict[str, str]) -> None:
        self.files = files
        self.asked: list[str] = []

    def get_contents(self, path: str) -> Any:
        self.asked.append(path)
        if path not in self.files:
            raise _Missing(path)
        return _File(self.files[path])


def test_the_file_github_uses_is_the_first_it_finds() -> None:
    repo = _Repo({"CODEOWNERS": "* @root\n", "docs/CODEOWNERS": "* @docs\n"})
    assert read_codeowners(repo) == ("CODEOWNERS", "* @root\n")
    assert repo.asked == [".github/CODEOWNERS", "CODEOWNERS"]
    assert read_codeowners(_Repo({})) == ("", "")


class _Api:
    def __init__(self, answer: Any) -> None:
        self.answer = answer
        self.sent: list[tuple[str, str, Any]] = []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        self.sent.append((method, path, query))
        if isinstance(self.answer, Exception):
            raise self.answer
        return RestResponse(200, {}, self.answer)

    def graphql(self, query: str, variables: Any) -> dict[str, Any]:
        raise AssertionError("no GraphQL here")


def test_github_s_own_codeowners_problems_are_sentences() -> None:
    api = _Api({
        "errors": [
            {
                "line": 3,
                "column": 1,
                "kind": "Unknown owner",
                "source": "*.rb @ghost\n",
                "suggestion": "make sure @ghost exists and has write access to the repository",
                "message": "Unknown owner on line 3",
                "path": ".github/CODEOWNERS",
            },
            {"line": 5, "kind": "Invalid pattern", "message": "Invalid pattern on line 5\n..."},
        ]
    })
    assert codeowners_errors(api, "o/r") == [
        "Line 3, column 1: Unknown owner. The line is: *.rb @ghost GitHub suggests: make sure "
        "@ghost exists and has write access to the repository",
        "Line 5: Invalid pattern. Invalid pattern on line 5",
    ]
    assert api.sent == [("GET", "/repos/o/r/codeowners/errors", None)]
    assert codeowners_errors(_Api({"errors": []}), "o/r") == []
    missing = _Api(GitHubRestError("not found", status=404))
    assert codeowners_errors(missing, "o/r") == [
        "GitHub found no CODEOWNERS file on the default branch to check."
    ]
