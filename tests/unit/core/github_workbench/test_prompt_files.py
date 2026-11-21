"""GitHub Models prompt files found and read as structure (complete.md 1.3)."""

from __future__ import annotations

import base64
from typing import Any

from quill.core.github import prompt_files as pf
from quill.core.github.rest_transport import RestResponse

GOOD = """
name: Summarize
description: Short summaries
model: openai/gpt-4o-mini
modelParameters:
  temperature: 0.2
messages:
  - role: system
    content: You summarize.
  - role: user
    content: |
      Summarize {{text}}
      in {{words}} words.
testData:
  - text: one
    words: 5
  - text: two
evaluators:
  - name: short
    string:
      contains: summary
"""


class FakeApi:
    def __init__(self, routes: dict[str, Any]) -> None:
        self.routes, self.asked = routes, []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        assert method == "GET"
        self.asked.append((path, query))
        return RestResponse(200, {}, self.routes[path])

    def graphql(self, query: str, variables: Any) -> dict[str, Any]:
        raise AssertionError


def test_prompt_files_are_found_on_the_default_branch_in_one_tree_read() -> None:
    api = FakeApi({
        "/repos/o/r": {"default_branch": "main"},
        "/repos/o/r/git/trees/main": {
            "truncated": True,
            "tree": [
                {"path": "prompts/b.prompt.yml", "type": "blob"},
                {"path": "a.prompt.yaml", "type": "blob"},
                {"path": "x.prompt.yml", "type": "tree"},
                {"path": "readme.md", "type": "blob"},
            ],
        },
    })
    found = pf.find_prompt_files(api, "o/r")
    assert found.paths == ("a.prompt.yaml", "prompts/b.prompt.yml")
    assert api.asked[-1] == ("/repos/o/r/git/trees/main", {"recursive": "1"})
    assert found.sentence == (
        "2 prompt files on main. GitHub listed only part of this large repository."
    )


def test_none_found_is_said() -> None:
    found = pf.PromptFiles("main", ())
    assert found.sentence == "No prompt files (.prompt.yml) on main."


def test_a_prompt_file_reads_as_its_parts_and_names_a_missing_variable() -> None:
    read = pf.describe(GOOD)
    assert read.model == "openai/gpt-4o-mini" and read.test_rows == 2
    assert read.parameters == (("temperature", "0.2"),)
    assert [role for role, _c in read.messages] == ["system", "user"]
    assert read.evaluators == ("short",)
    assert read.problems == ("The variable words is missing from 1 test rows.",)
    lines = read.lines("p.prompt.yml")
    assert lines[0] == "File: p.prompt.yml"
    assert "  2. user: Summarize {{text}} ..." in lines
    assert lines[-1] == pf.RUN_ELSEWHERE


def test_the_problems_github_models_would_trip_on_are_said() -> None:
    read = pf.describe("messages:\n  - role: robot\n    content: '{{x}}'\n")
    assert read.problems == (
        "It names no model.",
        "Message 1 has the role robot, which is not known.",
        "The variable x is used, but there is no test data to fill it.",
    )
    assert pf.describe("model: m\n").problems == ("It has no messages.",)
    assert pf.describe("a: [").problems[0].startswith("It is not valid YAML at line")
    assert pf.describe("- 1\n").problems[0].startswith("It is not a prompt file")


def test_the_file_text_is_read_at_the_ref() -> None:
    content = base64.b64encode(GOOD.encode()).decode()
    api = FakeApi({"/repos/o/r/contents/p.prompt.yml": {"content": content}})
    assert pf.read_prompt_file(api, "o/r", "p.prompt.yml", "main") == GOOD
    assert api.asked == [("/repos/o/r/contents/p.prompt.yml", {"ref": "main"})]
