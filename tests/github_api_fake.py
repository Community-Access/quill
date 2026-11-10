"""A recorded GitHub API for Workbench tests: answers by method and path, records every call.

The Workbench's sheets, batches and access pages talk to GitHub through
``quill.core.github.workbench_api.GitHubApi``; tests hand them this instead,
so no test ever reaches GitHub. Answers are set per ``(method, path)``;
a GET answer may be a callable so a test can change what GitHub "has" after
a write (the verify-after-save re-read). GraphQL answers are matched by a
substring of the query.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from quill.core.github.rest_transport import GitHubRestError, RestResponse


class FakeGitHubApi:
    def __init__(self) -> None:
        self.answers: dict[tuple[str, str], Any] = {}
        self.graphql_answers: list[tuple[str, Any]] = []
        self.calls: list[tuple[str, str, Any]] = []
        self.graphql_calls: list[tuple[str, dict[str, Any]]] = []
        self.on_write: Callable[[str, str, Any], None] | None = None

    def answer(self, method: str, path: str, data: Any) -> None:
        self.answers[(method, path)] = data

    def answer_graphql(self, fragment: str, data: Any) -> None:
        self.graphql_answers.append((fragment, data))

    def rest(
        self,
        method: str,
        path: str,
        *,
        body: Mapping[str, object] | None = None,
        query: Mapping[str, str] | None = None,
    ) -> RestResponse:
        self.calls.append((method, path, dict(body) if body is not None else None))
        if method != "GET" and self.on_write is not None:
            self.on_write(method, path, body)
        data = self.answers.get((method, path))
        if data is None and method != "GET":
            return RestResponse(200, {}, {})
        if data is None:
            raise GitHubRestError("Not Found", status=404)
        if isinstance(data, BaseException):
            raise data
        value = data() if callable(data) else data
        return RestResponse(200, {}, value)

    def graphql(self, query: str, variables: Mapping[str, object]) -> dict[str, Any]:
        self.graphql_calls.append((query, dict(variables)))
        for fragment, data in self.graphql_answers:
            if fragment in query:
                if isinstance(data, BaseException):
                    raise data
                return data() if callable(data) else data
        if query.lstrip().startswith("mutation"):
            return {}
        raise GitHubRestError("No recorded GraphQL answer", status=404)

    def writes(self) -> list[tuple[str, str, Any]]:
        return [call for call in self.calls if call[0] != "GET"]
