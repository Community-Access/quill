"""fill_path checks the values a path uses, and only those."""

from __future__ import annotations

import pytest

from quill.core.github.workbench_api import fill_path


def test_values_are_put_in_and_encoded() -> None:
    path = fill_path("/repos/{repo}/labels/{name}", {"repo": "o/r", "name": "good first issue"})
    assert path == "/repos/o/r/labels/good%20first%20issue"


@pytest.mark.parametrize("bad", ["../x", "a\\b", "/o/r", "o/r/"])
def test_a_value_that_could_steer_the_path_is_refused(bad: str) -> None:
    with pytest.raises(ValueError, match="repo"):
        fill_path("/repos/{repo}/issues", {"repo": bad})


def test_a_value_the_path_does_not_use_is_not_checked() -> None:
    # A secret's base64 public key travels in the identity and starts with
    # "/" one time in 64; it never goes in a path, so it must not be refused.
    ident = {"repo": "o/r", "name": "TOKEN", "public_key": "/abc+def=="}
    assert fill_path("/repos/{repo}/actions/secrets/{name}", ident) == (
        "/repos/o/r/actions/secrets/TOKEN"
    )


def test_a_missing_value_is_an_error() -> None:
    with pytest.raises(ValueError, match="needs a value"):
        fill_path("/repos/{repo}/issues/{number}", {"repo": "o/r"})
