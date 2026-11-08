"""Create, edit, star and delete gists, for Explore's gists view.

Every call goes through :func:`~quill.core.github.rest_transport.request_json`
(api.github.com only, no redirects followed). The editing model is
:class:`GistDraft`: the dialog changes a local copy (description, file text,
added, renamed and deleted files) and :meth:`GistDraft.changes` turns the
difference into the one ``PATCH /gists/{id}`` body GitHub expects, where a
deleted file is ``null`` and a renamed one carries ``filename``. Nothing is
reported as saved until GitHub's reply shows the files the draft asked for.

A file GitHub truncated (over about a megabyte) is never sent back: its text in
the draft is only the first part, and saving it would cut the file short.

No ``wx`` imports; strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.rest_transport import GitHubRestError, request_json, rest_failure_message

_MAX_FILES = 300


@dataclass(frozen=True, slots=True)
class GistFile:
    name: str
    content: str = ""
    language: str = ""
    size: int = 0
    truncated: bool = False


@dataclass(frozen=True, slots=True)
class Gist:
    """One gist as GitHub returned it."""

    id: str
    description: str = ""
    public: bool = False
    url: str = ""
    files: tuple[GistFile, ...] = ()

    @property
    def visibility(self) -> str:
        return "public" if self.public else "secret"

    def file(self, name: str) -> GistFile | None:
        return next((item for item in self.files if item.name == name), None)


def _gist_id(gist_id: str) -> str:
    value = gist_id.strip()
    if not value or not value.isalnum():
        raise GitHubItemsError("Choose a gist first.")
    return value


def _check_name(name: str) -> str:
    value = name.strip()
    if not value:
        raise GitHubItemsError("A gist file needs a name, such as notes.md.")
    if "/" in value or "\\" in value:
        raise GitHubItemsError(f"{value} has a slash in it; a gist file name cannot.")
    if value.casefold().startswith("gistfile") and value[8:].isdigit():
        raise GitHubItemsError(f"GitHub reserves names like {value}; choose another.")
    return value


def parse_gist(data: object) -> Gist:
    """A REST gist object as a :class:`Gist`, or an error when it is not one."""
    if not isinstance(data, Mapping) or not data.get("id"):
        raise GitHubItemsError("GitHub returned no gist.")
    raw_files = data.get("files")
    files: list[GistFile] = []
    for key, row in raw_files.items() if isinstance(raw_files, Mapping) else ():
        if not isinstance(row, Mapping):
            continue
        size = row.get("size")
        files.append(
            GistFile(
                name=str(row.get("filename") or key),
                content=str(row.get("content") or ""),
                language=str(row.get("language") or ""),
                size=size if isinstance(size, int) and not isinstance(size, bool) else 0,
                truncated=bool(row.get("truncated")),
            )
        )
    return Gist(
        id=str(data["id"]),
        description=str(data.get("description") or ""),
        public=bool(data.get("public")),
        url=str(data.get("html_url") or ""),
        files=tuple(files),
    )


@dataclass(slots=True)
class GistDraft:
    """A local, editable copy of a gist's description and files.

    ``files`` maps each current name to its text; ``origins`` maps a current
    name to the name the file had on GitHub (missing for a new file).
    """

    description: str = ""
    files: dict[str, str] = field(default_factory=dict)
    origins: dict[str, str] = field(default_factory=dict)
    truncated: frozenset[str] = frozenset()
    original: Gist | None = None

    @classmethod
    def from_gist(cls, gist: Gist) -> GistDraft:
        return cls(
            description=gist.description,
            files={item.name: item.content for item in gist.files},
            origins={item.name: item.name for item in gist.files},
            truncated=frozenset(item.name for item in gist.files if item.truncated),
            original=gist,
        )

    @classmethod
    def new(cls, name: str, content: str, description: str = "") -> GistDraft:
        draft = cls(description=description)
        draft.add_file(name or "notes.txt", content)
        return draft

    def names(self) -> list[str]:
        return list(self.files)

    def is_truncated(self, name: str) -> bool:
        return self.origins.get(name, "") in self.truncated

    def add_file(self, name: str, content: str = "") -> str:
        value = _check_name(name)
        if value in self.files:
            raise GitHubItemsError(f"This gist already has a file named {value}.")
        if self.original is not None and self.original.file(value) is not None:
            raise GitHubItemsError(
                f"{value} was renamed or deleted in this edit. Save first, then add a "
                "new file with that name."
            )
        if len(self.files) >= _MAX_FILES:
            raise GitHubItemsError(f"A gist holds at most {_MAX_FILES} files.")
        self.files[value] = content
        return value

    def rename_file(self, old: str, new: str) -> str:
        value = _check_name(new)
        if old not in self.files:
            raise GitHubItemsError(f"There is no file named {old} in this gist.")
        if value == old:
            return value
        if value in self.files:
            raise GitHubItemsError(f"This gist already has a file named {value}.")
        if (
            self.original is not None
            and self.original.file(value) is not None
            and self.origins.get(old) != value
        ):
            raise GitHubItemsError(
                f"{value} was renamed or deleted in this edit. Save first, then use that name."
            )
        # Keep the order the files are listed in.
        self.files = {value if key == old else key: text for key, text in self.files.items()}
        if old in self.origins:
            self.origins[value] = self.origins.pop(old)
        return value

    def delete_file(self, name: str) -> None:
        if name not in self.files:
            raise GitHubItemsError(f"There is no file named {name} in this gist.")
        if len(self.files) == 1:
            raise GitHubItemsError("A gist needs at least one file. Delete the whole gist instead.")
        del self.files[name]
        self.origins.pop(name, None)

    def set_content(self, name: str, content: str) -> None:
        if name not in self.files:
            raise GitHubItemsError(f"There is no file named {name} in this gist.")
        if self.is_truncated(name) and content != self.files[name]:
            raise GitHubItemsError(
                f"{name} is too large for GitHub to send whole, so QUILL cannot save "
                "changes to it. Edit it on GitHub instead."
            )
        self.files[name] = content

    def _validate(self) -> None:
        if not self.files:
            raise GitHubItemsError("A gist needs at least one file.")
        empty = [name for name, text in self.files.items() if not text.strip()]
        if empty:
            raise GitHubItemsError(f"{empty[0]} is empty. GitHub does not keep an empty file.")

    def create_payload(self, *, public: bool) -> dict[str, object]:
        """The ``POST /gists`` body for a new gist."""
        self._validate()
        return {
            "description": self.description,
            "public": bool(public),
            "files": {name: {"content": text} for name, text in self.files.items()},
        }

    def changes(self) -> dict[str, object]:
        """The ``PATCH /gists/{id}`` body, or ``{}`` when nothing changed."""
        self._validate()
        original = self.original
        if original is None:
            raise GitHubItemsError("Only a gist loaded from GitHub can be edited.")
        files: dict[str, object] = {}
        kept = set(self.origins.values())
        for item in original.files:
            if item.name not in kept:
                files[item.name] = None
        for name, text in self.files.items():
            source = self.origins.get(name)
            if source is None:
                files[name] = {"content": text}
                continue
            change: dict[str, str] = {}
            if name != source:
                change["filename"] = name
            before = original.file(source)
            if before is not None and text != before.content and source not in self.truncated:
                change["content"] = text
            if change:
                files[source] = change
        payload: dict[str, object] = {}
        if self.description != original.description:
            payload["description"] = self.description
        if files:
            payload["files"] = files
        return payload

    def summary(self) -> str:
        """What saving would do, in one sentence, or "No changes."."""
        payload = self.changes()
        if not payload:
            return "No changes."
        parts: list[str] = []
        if "description" in payload:
            parts.append("change the description")
        files = payload.get("files")
        for source, change in files.items() if isinstance(files, dict) else ():
            if change is None:
                parts.append(f"delete {source}")
            elif isinstance(change, dict) and "filename" in change:
                parts.append(f"rename {source} to {change['filename']}")
                if "content" in change:
                    parts.append(f"change the text of {change['filename']}")
            elif self.origins.get(source) is None and source in self.files:
                parts.append(f"add {source}")
            else:
                parts.append(f"change the text of {source}")
        return "Save will " + ", ".join(parts) + "."

    def confirmed_by(self, gist: Gist) -> bool:
        """Whether GitHub's reply holds exactly the files and description asked for."""
        return gist.description == self.description and {item.name for item in gist.files} == set(
            self.files
        )


class _GistAccess(Protocol):
    @property
    def _gist_token(self) -> str | None: ...


def _call(
    token: str | None,
    action: str,
    method: str,
    path: str,
    expect: tuple[int, ...],
    body: dict[str, object] | None = None,
) -> Any:
    if not token:
        raise GitHubItemsError(f"To {action} you need a signed-in GitHub account.")
    try:
        response = request_json(token, method, path, body=body)
    except GitHubRestError as exc:
        raise GitHubItemsError(rest_failure_message(action, exc)) from exc
    if response.status not in expect:
        raise GitHubItemsError(
            f"Could not {action}. GitHub answered HTTP {response.status} without confirming it."
        )
    return response.data


class GitHubGistsMixin:
    """Gist reads and writes for :class:`~quill.core.github.explore.GitHubExploreClient`."""

    @property
    def _gist_token(self) -> str | None:
        provider = getattr(self, "_provider", None)
        return getattr(provider, "token", None)

    def fetch_gist(self: _GistAccess, gist_id: str) -> Gist:
        return parse_gist(
            _call(self._gist_token, "read the gist", "GET", f"/gists/{_gist_id(gist_id)}", (200,))
        )

    def create_gist(self: _GistAccess, draft: GistDraft, *, public: bool) -> Gist:
        """Create a gist from *draft*; the gist GitHub stored."""
        payload = draft.create_payload(public=public)
        gist = parse_gist(
            _call(self._gist_token, "create the gist", "POST", "/gists", (201,), payload)
        )
        if not draft.confirmed_by(gist) or gist.public != bool(public):
            raise GitHubItemsError("GitHub did not confirm the gist as it was written.")
        return gist

    def update_gist(self: _GistAccess, gist_id: str, draft: GistDraft) -> Gist | None:
        """Send *draft*'s changes; the gist GitHub stored, or None when nothing changed."""
        payload = draft.changes()
        if not payload:
            return None
        path = f"/gists/{_gist_id(gist_id)}"
        gist = parse_gist(_call(self._gist_token, "save the gist", "PATCH", path, (200,), payload))
        if not draft.confirmed_by(gist):
            raise GitHubItemsError(
                "GitHub saved the gist, but its files are not the ones QUILL sent. "
                "Load it again to see what it holds now."
            )
        return gist

    def delete_gist(self: _GistAccess, gist_id: str) -> None:
        _call(self._gist_token, "delete the gist", "DELETE", f"/gists/{_gist_id(gist_id)}", (204,))

    def is_gist_starred(self: _GistAccess, gist_id: str) -> bool:
        token = self._gist_token
        if not token:
            raise GitHubItemsError("Sign in to GitHub to star gists.")
        try:
            request_json(token, "GET", f"/gists/{_gist_id(gist_id)}/star")
        except GitHubRestError as exc:
            if exc.status == 404:
                return False
            raise GitHubItemsError(rest_failure_message("read the gist's star", exc)) from exc
        return True

    def set_gist_starred(self: _GistAccess, gist_id: str, starred: bool) -> None:
        verb = "star" if starred else "unstar"
        _call(
            self._gist_token,
            f"{verb} the gist",
            "PUT" if starred else "DELETE",
            f"/gists/{_gist_id(gist_id)}/star",
            (204,),
        )


__all__ = ["Gist", "GistDraft", "GistFile", "GitHubGistsMixin", "parse_gist"]
