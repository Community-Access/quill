"""Every template a repository has, and those it inherits (GitHub PRD 21.2, 21.3, 21.8).

Repository > Templates lists, one row each:

- issue forms (``.github/ISSUE_TEMPLATE/*.yml``) and Markdown issue templates
  (``*.md``) and the chooser (``config.yml``);
- pull request templates (``pull_request_template.md`` in the root, ``docs``
  or ``.github``, and every file in ``.github/PULL_REQUEST_TEMPLATE/``);
- discussion category forms (``.github/DISCUSSION_TEMPLATE/<category>.yml``);
- the community health files (CODE_OF_CONDUCT, CONTRIBUTING, SECURITY,
  SUPPORT, GOVERNANCE, FUNDING.yml, CITATION.cff, CODEOWNERS), present,
  inherited or missing.

What the repository lacks and its owner's ``.github`` repository has is
listed too, marked "inherited from owner/.github" -- GitHub uses those
defaults only for a kind the repository has none of, so a kind the
repository has is never listed twice.

Reads are directory listings plus the small template files themselves
(``GET /repos/{owner}/{repo}/contents/{path}``, already covered); nothing is
executed and a file over 50 KB is listed without being read. ``repo_for`` is
any callable returning a PyGithub-shaped repository object, so tests pass a
fake. No ``wx`` imports; strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

__all__ = [
    "COMMUNITY_FILES",
    "KIND_NAMES",
    "TemplateEntry",
    "list_templates",
    "pull_request_templates",
    "read_entry_text",
]

#: Template kind -> how a row names it.
KIND_NAMES: dict[str, str] = {
    "issue_form": "issue form",
    "issue_template": "Markdown issue template",
    "chooser": "template chooser",
    "pull_request_template": "pull request template",
    "discussion_form": "discussion category form",
    "community_file": "community file",
}

#: The community health files GitHub reads, by upper-cased stem (or name).
COMMUNITY_FILES: tuple[tuple[str, str], ...] = (
    ("CODE_OF_CONDUCT", "CODE_OF_CONDUCT.md"),
    ("CONTRIBUTING", "CONTRIBUTING.md"),
    ("SECURITY", "SECURITY.md"),
    ("SUPPORT", "SUPPORT.md"),
    ("GOVERNANCE", "GOVERNANCE.md"),
    ("FUNDING", "FUNDING.yml"),
    ("CITATION", "CITATION.cff"),
    ("CODEOWNERS", "CODEOWNERS"),
)
_MAX_READ = 50_000
_MAX_FILES = 40


@dataclass(frozen=True, slots=True)
class TemplateEntry:
    """One row of Repository > Templates."""

    kind: str
    path: str
    #: The repository the file is in (the owner's ``.github`` when inherited).
    source: str
    name: str = ""
    inherited: bool = False
    #: A community file neither the repository nor its owner has.
    missing: bool = False
    size: int = 0
    sha: str = ""
    url: str = ""
    text: str = ""
    #: Why the file was not read, or cannot be built here ("" when fine).
    problem: str = ""
    summary: str = ""

    @property
    def key(self) -> str:
        """``source:path``, what the Workbench row keeps to find it again."""
        return f"{self.source}:{self.path}"

    @property
    def is_form(self) -> bool:
        return self.kind in ("issue_form", "discussion_form")

    @property
    def category(self) -> str:
        """A discussion form's category slug (its file name)."""
        if self.kind != "discussion_form":
            return ""
        return self.path.rsplit("/", 1)[-1].rsplit(".", 1)[0]

    def label(self) -> str:
        """The row: "Bug report, issue form, adds bug, 3 fields, 1 required"."""
        if self.missing:
            return f"{self.name}, missing"
        parts = [self.name or self.path, KIND_NAMES.get(self.kind, self.kind)]
        if self.summary:
            parts.append(self.summary)
        if self.problem:
            parts.append(self.problem)
        if self.inherited:
            parts.append(f"inherited from {self.source}")
        return ", ".join(parts)

    def detail(self) -> str:
        lines = [self.label(), f"File: {self.path} in {self.source}."]
        if self.missing:
            lines.append("Enter starts one from a starter; Save commits it.")
        elif self.inherited:
            lines.append(
                "GitHub uses this default because the repository has none of its own. "
                "Saving it changes the organization's default for every repository using it."
            )
        return "\n".join(lines)


def _safe(row: Any, name: str) -> str:
    try:
        return str(getattr(row, name, "") or "")
    except Exception:  # noqa: BLE001 - malformed content metadata stays local
        return ""


def _size(row: Any) -> int:
    try:
        return int(getattr(row, "size", 0) or 0)
    except (TypeError, ValueError):
        return 0


def _listing(repo: Any, path: str) -> list[Any]:
    try:
        found = repo.get_contents(path)
    except Exception as exc:  # noqa: BLE001 - a folder that is not there is a normal state
        if getattr(exc, "status", None) == 404:
            return []
        raise
    return list(found) if isinstance(found, list) else [found]


def read_entry_text(repo: Any, path: str) -> tuple[str, str]:
    """``(text, sha)`` of one file; raises when GitHub cannot be read."""
    found = repo.get_contents(path)
    if isinstance(found, list):
        raise ValueError(f"{path} is a folder, not a file.")
    raw = getattr(found, "decoded_content", b"")
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
    return text, _safe(found, "sha")


def _summarise(kind: str, text: str, filename: str) -> tuple[str, str, str]:
    """``(name, summary, problem)`` from a template's own text."""
    stem = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").strip()
    if kind in ("issue_form", "discussion_form"):
        from quill.core.github.issue_forms import parse_issue_form

        form = parse_issue_form(text, filename)
        fields = [f for f in form.fields if f.answers]
        required = sum(1 for f in fields if f.required)
        bits = []
        if form.labels:
            bits.append("adds " + " and ".join(form.labels))
        bits.append(f"{len(fields)} field{'s' if len(fields) != 1 else ''}, {required} required")
        problem = "cannot be filled here, see its checks" if form.unsupported else ""
        name = form.name if kind == "issue_form" else stem.title()
        return name, ", ".join(bits), problem
    if kind == "issue_template":
        from quill.core.github.issue_templates import _front_matter

        metadata, _body = _front_matter(text)
        declared = metadata.get("name")
        title = declared if isinstance(declared, str) and declared else stem.title()
        return title, "", ""
    if kind == "chooser":
        import yaml  # type: ignore[import-untyped]

        try:
            data = yaml.safe_load(text) or {}
        except yaml.YAMLError:
            return "Template chooser", "", "not valid YAML"
        if not isinstance(data, dict):
            return "Template chooser", "", "not a set of keys"
        blank = data.get("blank_issues_enabled", True)
        links = data.get("contact_links") or []
        count = len(links) if isinstance(links, list) else 0
        summary = (
            f"blank issues {'allowed' if blank is not False else 'not allowed'}, "
            f"{count} contact link{'s' if count != 1 else ''}"
        )
        return "Template chooser", summary, ""
    return stem.title() or filename, "", ""


class _Scan:
    """One repository's template files, read with as few calls as possible."""

    def __init__(self, repo: Any, full_name: str) -> None:
        self.repo = repo
        self.full_name = full_name
        self.entries: list[TemplateEntry] = []
        self.read_count = 0
        self.community: dict[str, Any] = {}

    def add(self, kind: str, entry: Any, *, inherited: bool, read: bool = True) -> None:
        path = _safe(entry, "path") or _safe(entry, "name")
        filename = path.rsplit("/", 1)[-1]
        size = _size(entry)
        text, problem = "", ""
        if read and size > _MAX_READ:
            problem = "too large to build here; edit its source"
        elif read and self.read_count < _MAX_FILES:
            self.read_count += 1
            raw = getattr(entry, "decoded_content", None)
            try:
                if raw is None:
                    text, _sha = read_entry_text(self.repo, path)
                else:
                    text = (
                        raw.decode("utf-8", errors="replace")
                        if isinstance(raw, bytes)
                        else str(raw)
                    )
            except Exception:  # noqa: BLE001 - one unreadable file must not hide the rest
                problem = "could not be read"
        name, summary, found = _summarise(kind, text, filename) if text else ("", "", "")
        stem = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").strip()
        self.entries.append(
            TemplateEntry(
                kind=kind,
                path=path,
                source=self.full_name,
                name=name or stem.title() or filename,
                inherited=inherited,
                size=size,
                sha=_safe(entry, "sha"),
                url=_safe(entry, "html_url"),
                text=text,
                problem=problem or found,
                summary=summary,
            )
        )

    def run(self, *, inherited: bool) -> None:
        listings = {where: _listing(self.repo, where) for where in ("", ".github", "docs")}
        github_names = {_safe(e, "name").casefold(): e for e in listings[".github"]}
        for kind, folder in (
            ("issue", "issue_template"),
            ("pull_request_template", "pull_request_template"),
            ("discussion_form", "discussion_template"),
        ):
            folder_entry = github_names.get(folder)
            if folder_entry is None or _safe(folder_entry, "type") != "dir":
                continue
            for entry in _listing(self.repo, _safe(folder_entry, "path")):
                if _safe(entry, "type") != "file":
                    continue
                lowered = _safe(entry, "name").casefold()
                if kind == "issue":
                    if lowered == "config.yml" or lowered == "config.yaml":
                        self.add("chooser", entry, inherited=inherited)
                    elif lowered.endswith((".yml", ".yaml")):
                        self.add("issue_form", entry, inherited=inherited)
                    elif lowered.endswith((".md", ".markdown")):
                        self.add("issue_template", entry, inherited=inherited)
                elif kind == "discussion_form":
                    if lowered.endswith((".yml", ".yaml")):
                        self.add("discussion_form", entry, inherited=inherited)
                elif lowered.endswith((".md", ".markdown", ".txt")):
                    self.add("pull_request_template", entry, inherited=inherited)
        for where in ("", "docs", ".github"):
            for entry in listings[where]:
                if _safe(entry, "type") != "file":
                    continue
                lowered = _safe(entry, "name").casefold()
                if lowered.rsplit(".", 1)[0] == "pull_request_template":
                    self.add("pull_request_template", entry, inherited=inherited)
        self.community.update(_community(listings))


def _community(listings: dict[str, list[Any]]) -> dict[str, Any]:
    """Upper-cased community stem -> its first file, looking in .github, root, docs."""
    found: dict[str, Any] = {}
    wanted = {stem for stem, _name in COMMUNITY_FILES}
    for where in (".github", "", "docs"):
        for entry in listings[where]:
            if _safe(entry, "type") != "file":
                continue
            stem = _safe(entry, "name").rsplit(".", 1)[0].upper()
            if _safe(entry, "name") == "CODEOWNERS":
                stem = "CODEOWNERS"
            if stem in wanted and stem not in found:
                found[stem] = entry
    return found


def _owner_defaults_name(full_name: str) -> str:
    owner = full_name.split("/", 1)[0]
    return f"{owner}/.github"


def list_templates(repo_for: Callable[[str], Any], full_name: str) -> tuple[TemplateEntry, ...]:
    """Every template and community file of *full_name*, and what it inherits."""
    own = _Scan(repo_for(full_name), full_name)
    own.run(inherited=False)
    entries = list(own.entries)
    defaults_name = _owner_defaults_name(full_name)
    defaults: _Scan | None = None
    if defaults_name.casefold() != full_name.casefold():
        try:
            defaults = _Scan(repo_for(defaults_name), defaults_name)
            defaults.run(inherited=True)
        except Exception:  # noqa: BLE001 - an owner without a .github repository is normal
            defaults = None
    if defaults is not None:
        own_kinds = {e.kind for e in entries}
        issue_kinds = {"issue_form", "issue_template", "chooser"}
        has_issue_folder = bool(own_kinds & issue_kinds)
        for entry in defaults.entries:
            if entry.kind in issue_kinds and has_issue_folder:
                continue
            if entry.kind not in issue_kinds and entry.kind in own_kinds:
                continue
            entries.append(entry)
    for stem, filename in COMMUNITY_FILES:
        mine = own.community.get(stem)
        theirs = defaults.community.get(stem) if defaults is not None else None
        name = filename.rsplit(".", 1)[0].replace("_", " ").title() if "." in filename else stem
        name = {"Code Of Conduct": "Code of Conduct", "Citation": "Citation"}.get(name, name)
        if mine is not None or theirs is not None:
            chosen = mine if mine is not None else theirs
            entries.append(
                TemplateEntry(
                    kind="community_file",
                    path=_safe(chosen, "path"),
                    source=full_name if mine is not None else defaults_name,
                    name=name,
                    inherited=mine is None,
                    size=_size(chosen),
                    sha=_safe(chosen, "sha"),
                    url=_safe(chosen, "html_url"),
                )
            )
        else:
            entries.append(
                TemplateEntry(
                    kind="community_file",
                    path=f".github/{filename}" if stem != "CODEOWNERS" else ".github/CODEOWNERS",
                    source=full_name,
                    name=name,
                    missing=True,
                )
            )
    return tuple(entries)


def pull_request_templates(repo: Any, full_name: str) -> list[tuple[str, str]]:
    """``(name, text)`` of each pull request template, for New Pull Request (PRD 21.7)."""
    scan = _Scan(repo, full_name)
    scan.run(inherited=False)
    return [
        (entry.name, entry.text)
        for entry in scan.entries
        if entry.kind == "pull_request_template" and entry.text
    ]
