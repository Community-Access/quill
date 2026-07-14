"""Publish a single vault note (Accessible Vault, Phase 7) — wx-free, GATED.

Publishing is the *send* path, which QUILL gates behind ``future.publishing``
(``locked_off``). This module makes that gate explicit and testable: it only ever
produces a payload when the caller passes ``feature_enabled=True`` (i.e.
``features.is_enabled("future.publishing")``); otherwise it returns ``None`` and nothing
can be sent. The HTML is produced by the same resolver the static-site export uses
(:func:`quill.core.vault.site_export.note_to_html_fragment`), so a published note has its
`[[links]]` and `![[embeds]]` resolved to real HTML. The actual POST goes through QUILL's
existing, network-egress-audited publishing framework — this module never touches the
network itself.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from quill.core.vault.resolve import Resolver
from quill.core.vault.site_export import MarkdownToHtml, note_to_html_fragment
from quill.core.vault.vault import Vault


@dataclass(frozen=True, slots=True)
class PublishPayload:
    """A note ready to hand to the publishing framework."""

    path: str
    title: str
    html: str


def prepare_note_publish(
    vault: Vault,
    resolver: Resolver,
    note_path: str,
    *,
    markdown_to_html: MarkdownToHtml,
    feature_enabled: bool,
    url_for: Callable[[str, str], str] | None = None,
) -> PublishPayload | None:
    """Build the publish payload for ``note_path``, or ``None`` when gated off/missing.

    Returns ``None`` unless ``feature_enabled`` is true (the ``future.publishing`` gate)
    and the note exists — so a caller can never accidentally send when publishing is
    locked. ``url_for`` lets the caller map links to absolute site URLs for the target
    (defaults to same-directory ``.html`` anchors).
    """
    if not feature_enabled:
        return None
    info = vault.notes.get(note_path)
    if info is None:
        return None
    body = note_to_html_fragment(
        vault, resolver, note_path, markdown_to_html=markdown_to_html, url_for=url_for
    )
    return PublishPayload(path=note_path, title=info.title, html=body)
