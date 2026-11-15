"""Read safe Markdown issue templates without executing remote content."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class GitHubIssueTemplate:
    """A Markdown issue template or a link-only issue form."""

    name: str
    filename: str
    about: str = ""
    title: str = ""
    body: str = ""
    labels: tuple[str, ...] = ()
    assignees: tuple[str, ...] = ()
    url: str = ""
    supported: bool = True
    body_truncated: bool = False
    #: The parsed YAML issue form (quill.core.github.issue_forms.IssueForm), if any.
    form: Any = None


def _value(text: str) -> str:
    value = text.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return value.strip()


def _list_value(value: str | list[str]) -> tuple[str, ...]:
    if isinstance(value, list):
        values = value[:20]
    else:
        raw = value.strip()
        if raw.startswith("[") and raw.endswith("]"):
            raw = raw[1:-1]
        values = raw.split(",")[:20]
    return tuple(item[:100] for item in (_value(part) for part in values) if item)


def _front_matter(body: str) -> tuple[dict[str, str | list[str]], str]:
    lines = body.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, body
    end = next((index for index, line in enumerate(lines[1:], 1) if line.strip() == "---"), -1)
    if end < 0:
        return {}, body
    metadata: dict[str, str | list[str]] = {}
    list_key = ""
    for line in lines[1:end]:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("-") and list_key in {"labels", "assignees"}:
            current = metadata.setdefault(list_key, [])
            if isinstance(current, list):
                current.append(_value(stripped[1:]))
            continue
        key, separator, raw_value = stripped.partition(":")
        if not separator:
            list_key = ""
            continue
        key = key.strip().casefold()
        if key in {"labels", "assignees"} and not raw_value.strip():
            metadata[key] = []
            list_key = key
        elif key in {"name", "about", "title", "labels", "assignees"}:
            metadata[key] = _value(raw_value)
            list_key = ""
        else:
            list_key = ""
    content = "\n".join(lines[end + 1 :]).lstrip("\r\n")
    return metadata, content


def list_issue_templates(repo: Any, *, limit: int = 20) -> tuple[GitHubIssueTemplate, ...]:
    """Return at most *limit* Markdown templates and link-only form entries."""
    if limit < 1 or limit > 100:
        raise ValueError("Choose an issue-template limit between 1 and 100.")
    try:
        entries = repo.get_contents(".github/ISSUE_TEMPLATE")
    except Exception as exc:  # noqa: BLE001 - no template directory is a normal state
        if getattr(exc, "status", None) == 404:
            return ()
        raise
    if not isinstance(entries, list):
        entries = [entries]
    templates: list[GitHubIssueTemplate] = []
    for entry in entries:
        if _safe(entry, "type") != "file":
            continue
        filename = _safe(entry, "name")
        lowered = filename.casefold()
        if lowered == "config.yml":
            continue
        url = _safe(entry, "html_url")
        if lowered.endswith((".yml", ".yaml")):
            templates.append(_issue_form_template(entry, filename, url))
        elif lowered.endswith((".md", ".markdown")):
            try:
                declared_size = int(getattr(entry, "size", 0) or 0)
            except (TypeError, ValueError):
                declared_size = 0
            truncated = declared_size > 50_000
            metadata: dict[str, str | list[str]]
            if truncated:
                metadata, body = {}, ""
            else:
                raw = getattr(entry, "decoded_content", b"")
                content = (
                    raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
                )
                metadata, body = _front_matter(content)
                truncated = len(body) > 50_000
                body = body[:50_000]
            name = (_metadata(metadata, "name") or filename.rsplit(".", 1)[0])[:128]
            labels = _list_value(metadata.get("labels", ""))
            assignees = _list_value(metadata.get("assignees", ""))
            templates.append(
                GitHubIssueTemplate(
                    name=name,
                    filename=filename,
                    about=_metadata(metadata, "about"),
                    title=_metadata(metadata, "title"),
                    body=body,
                    labels=labels,
                    assignees=assignees,
                    url=url,
                    body_truncated=truncated,
                )
            )
        if len(templates) >= limit:
            break
    return tuple(templates)


def _issue_form_template(entry: Any, filename: str, url: str) -> GitHubIssueTemplate:
    """A YAML issue form, read so QUILL can fill it (quill.core.github.issue_forms)."""
    from quill.core.github.issue_forms import parse_issue_form

    try:
        declared_size = int(getattr(entry, "size", 0) or 0)
    except (TypeError, ValueError):
        declared_size = 0
    fallback = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()
    if declared_size > 50_000:
        return GitHubIssueTemplate(
            name=fallback or "GitHub issue form",
            filename=filename,
            about="An issue form too large for QUILL to fill; open it on GitHub.",
            url=url,
            supported=False,
            body_truncated=True,
        )
    raw = getattr(entry, "decoded_content", b"")
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
    form = parse_issue_form(text, filename)
    return GitHubIssueTemplate(
        name=form.name[:128],
        filename=filename,
        about=form.unsupported or form.description or "An issue form.",
        title=form.title,
        labels=form.labels,
        assignees=form.assignees,
        url=url,
        supported=not form.unsupported,
        form=form,
    )


def _safe(row: Any, name: str) -> str:
    try:
        value = getattr(row, name, "")
        return str(value or "")
    except Exception:  # noqa: BLE001 - malformed content metadata stays local
        return ""


def _metadata(metadata: dict[str, str | list[str]], key: str) -> str:
    value = metadata.get(key, "")
    return value[:500] if isinstance(value, str) else ""


__all__ = ["GitHubIssueTemplate", "list_issue_templates"]
