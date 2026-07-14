"""The verbosity templates library (§19).

A flat, named collection of reusable announcement templates from three sources:
built-in starters, the user's own saved templates, and templates installed from
QVP packs. The library supports the v1 CRUD set (save, rename, delete) and the
cross-verb *apply* behavior: applying a template to a verb that does not track
all of its tokens auto-strips the unknown tokens and reports which were removed,
e.g. "Applied template Concise. Removed 2 tokens because this verb does not track
them: cell, region."

Pure and wx-free; the UI (sub-PR 1.4) and the storage layer own persistence and
presentation.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.verbosity.parser import parse
from quill.core.verbosity.verbs import VerbSpec

__all__ = ["TemplateSource", "LibraryTemplate", "ApplyResult", "TemplateLibrary"]


class TemplateSource:
    """Where a library template came from."""

    BUILTIN = "builtin"
    USER = "user"
    QVP = "qvp"


@dataclass(frozen=True, slots=True)
class LibraryTemplate:
    """One named template in the library."""

    name: str
    template: str
    source: str = TemplateSource.USER
    pack: str | None = None

    @property
    def editable(self) -> bool:
        """Built-in and QVP templates are read-only until copied as user ones."""
        return self.source == TemplateSource.USER


@dataclass(frozen=True, slots=True)
class ApplyResult:
    """The outcome of applying a template to a specific verb."""

    template: str
    removed_tokens: tuple[str, ...]

    @property
    def message(self) -> str:
        if not self.removed_tokens:
            return "Applied template."
        joined = ", ".join(self.removed_tokens)
        count = len(self.removed_tokens)
        return (
            f"Applied template. Removed {count} token{'s' if count != 1 else ''} "
            f"because this verb does not track them: {joined}."
        )


#: A couple of safe starter templates so the library is never empty.
_BUILTINS: tuple[LibraryTemplate, ...] = (
    LibraryTemplate("Default line", "Line {line}", TemplateSource.BUILTIN),
    LibraryTemplate("Line of total", "Line {line} of {total}", TemplateSource.BUILTIN),
)


class TemplateLibrary:
    """A flat, named template collection across built-in, user, and QVP sources."""

    def __init__(self) -> None:
        self._templates: dict[str, LibraryTemplate] = {tpl.name: tpl for tpl in _BUILTINS}

    def all(self) -> tuple[LibraryTemplate, ...]:
        """Every template, sorted by name."""
        return tuple(self._templates[key] for key in sorted(self._templates))

    def get(self, name: str) -> LibraryTemplate | None:
        return self._templates.get(name)

    def save(self, name: str, template: str) -> LibraryTemplate:
        """Create or replace a *user* template. Returns the saved entry.

        Refuses to overwrite a read-only (built-in or QVP) entry of the same name.
        """
        existing = self._templates.get(name)
        if existing is not None and not existing.editable:
            raise ValueError(f"'{name}' is a read-only template; copy it under a new name")
        entry = LibraryTemplate(name, template, TemplateSource.USER)
        self._templates[name] = entry
        return entry

    def rename(self, old_name: str, new_name: str) -> LibraryTemplate:
        """Rename a user template, keeping its body. Raises on conflicts."""
        entry = self._templates.get(old_name)
        if entry is None:
            raise KeyError(old_name)
        if not entry.editable:
            raise ValueError(f"'{old_name}' is read-only and cannot be renamed")
        if new_name in self._templates:
            raise ValueError(f"'{new_name}' already exists")
        del self._templates[old_name]
        renamed = LibraryTemplate(new_name, entry.template, TemplateSource.USER)
        self._templates[new_name] = renamed
        return renamed

    def delete(self, name: str) -> None:
        """Delete a user template. Raises for read-only or missing entries."""
        entry = self._templates.get(name)
        if entry is None:
            raise KeyError(name)
        if not entry.editable:
            raise ValueError(f"'{name}' is read-only and cannot be deleted")
        del self._templates[name]

    def install_from_pack(self, name: str, template: str, pack: str) -> LibraryTemplate:
        """Add a QVP-installed (read-only) template."""
        entry = LibraryTemplate(name, template, TemplateSource.QVP, pack=pack)
        self._templates[name] = entry
        return entry

    def apply(self, name: str, verb: VerbSpec) -> ApplyResult:
        """Apply the named template to ``verb``, stripping tokens it can't track.

        The template text is reduced to the tokens the verb supports; any token
        the verb does not track is removed from the rendered output and reported.
        """
        entry = self._templates.get(name)
        if entry is None:
            raise KeyError(name)
        return apply_template_to_verb(entry.template, verb)


def apply_template_to_verb(template: str, verb: VerbSpec) -> ApplyResult:
    """Return ``template`` with verb-unsupported tokens removed, plus their names."""
    supported = {tok.name for tok in verb.supported_tokens}
    parsed = parse(template)
    removed: list[str] = []
    out: list[str] = []
    for segment in parsed.segments:
        token_name = getattr(segment, "name", None)
        if token_name is None:
            out.append(getattr(segment, "text", ""))
            continue
        if token_name in supported:
            out.append(getattr(segment, "raw", ""))
        elif token_name not in removed:
            removed.append(token_name)
    cleaned = "".join(out)
    # Collapse the double spaces a removed token can leave behind.
    while "  " in cleaned:
        cleaned = cleaned.replace("  ", " ")
    return ApplyResult(template=cleaned.strip(), removed_tokens=tuple(removed))
