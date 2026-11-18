"""Someone's public lists, GitHub's templates, and People and Topics search."""

from __future__ import annotations

from typing import Any

from quill.core.github import resource_engine as engine
from quill.core.github.resource_specs import spec_for
from quill.core.github.rest_transport import RestResponse
from quill.core.github.search_views import topic_row, user_row
from quill.core.github.workbench_tree import GITHUB_TREE


class _Api:
    def __init__(self, data: Any) -> None:
        self.data, self.sent = data, []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> RestResponse:
        self.sent.append((method, path))
        return RestResponse(200, {}, self.data)


def test_a_persons_lists_read_from_their_own_address() -> None:
    api = _Api([{"id": 4, "key": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIabcdefgh"}])
    rows = engine.fetch(api, spec_for("person_keys"), "octocat")
    assert api.sent == [("GET", "/users/octocat/keys")]
    assert rows[0].label == "SSH key 4, ending abcdefgh."
    gpg = spec_for("person_gpg_keys")
    assert (
        gpg.sentence({"key_id": "AB12", "emails": [{"email": "o@x.org"}]})
        == "GPG key AB12 for o@x.org."
    )
    assert {n.key for n in GITHUB_TREE.template("person")} >= {
        "person_keys",
        "person_gists",
        "person_feed",
    }


def test_a_list_of_plain_names_becomes_rows() -> None:
    rows = engine.fetch(_Api(["Python", "Node"]), spec_for("gitignore_templates"), "")
    assert [r.label for r in rows] == ["Python.", "Node."]
    assert (
        spec_for("licenses").sentence({"name": "MIT License", "spdx_id": "MIT"})
        == "MIT License (MIT)."
    )


def test_people_and_topic_results_read_plainly() -> None:
    assert user_row({"login": "acme", "type": "Organization"}).label == "acme, an organization"
    person = user_row({"login": "jeff", "type": "User"})
    assert person.kind == "person" and person.key == "jeff"
    topic = topic_row({
        "name": "a11y",
        "display_name": "Accessibility",
        "short_description": "For everyone",
        "featured": True,
    })
    assert topic.label == "Accessibility: For everyone (featured)"
