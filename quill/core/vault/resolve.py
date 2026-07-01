"""Link resolution — turn a wikilink into a note and an offset (wx-free).

``build_resolver`` indexes every note by its title, aliases, filename stem, and
extension-less relative path (all normalized case- and whitespace-insensitively).
``resolve_link`` maps a :class:`~quill.core.vault.links.WikiLink` to a
:class:`LinkTarget` — the destination note's path plus the character offset of
its heading or block anchor. An unresolved target returns ``None`` (the UI can
offer to create the note); a name matching several notes is reported as
``ambiguous`` with the full candidate list so the UI can ask, never guess.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from quill.core.vault.links import WikiLink
from quill.core.vault.vault import Vault

__all__ = ["Resolver", "LinkTarget", "build_resolver", "resolve_link"]


@dataclass(frozen=True, slots=True)
class Resolver:
    """Normalized name -> sorted list of note paths that answer to it."""

    by_name: dict[str, list[str]]


@dataclass(frozen=True, slots=True)
class LinkTarget:
    """A resolved link: the destination note, an offset, and ambiguity info."""

    path: str
    offset: int
    ambiguous: bool
    candidates: tuple[str, ...]


def build_resolver(vault: Vault) -> Resolver:
    by_name: dict[str, list[str]] = {}
    for path, info in vault.notes.items():
        keys = {info.title, *info.aliases, PurePosixPath(path).stem, _strip_ext(path)}
        for key in keys:
            norm = _norm(key)
            if norm:
                by_name.setdefault(norm, [])
                if path not in by_name[norm]:
                    by_name[norm].append(path)
    for paths in by_name.values():
        paths.sort()
    return Resolver(by_name=by_name)


def resolve_link(
    vault: Vault, resolver: Resolver, link: WikiLink, source_path: str
) -> LinkTarget | None:
    candidates: tuple[str, ...]
    if link.target == "":
        path, ambiguous, candidates = source_path, False, (source_path,)
    else:
        matches = resolver.by_name.get(_norm(link.target))
        if not matches:
            return None
        path, ambiguous, candidates = matches[0], len(matches) > 1, tuple(matches)
    offset = _anchor_offset(vault, path, link)
    return LinkTarget(path=path, offset=offset, ambiguous=ambiguous, candidates=candidates)


def _anchor_offset(vault: Vault, path: str, link: WikiLink) -> int:
    info = vault.notes.get(path)
    if info is None:
        return 0
    if link.block is not None:
        return info.block_ids.get(link.block, 0)
    if link.heading is not None:
        wanted = _norm(link.heading)
        for heading in info.headings:
            if _norm(heading.title) == wanted:
                return heading.offset
    return 0


def _norm(value: str) -> str:
    return " ".join(value.split()).lower()


def _strip_ext(path: str) -> str:
    pure = PurePosixPath(path)
    return pure.with_suffix("").as_posix()
