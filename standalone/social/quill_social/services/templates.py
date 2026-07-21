"""Saved replies and templates (PRD 13.5).

Pure, wx-free rendering for reusable replies and post templates. A ``Template``
carries a body with ``{variable}`` placeholders, per-network body variants, an
optional signature, campaign tags, an accessibility reminder, and optional AI
transformation instructions (PRD 13.5). ``render`` substitutes known variables,
leaves unknown placeholders visibly flagged, selects a network variant when one
exists, and appends the signature. ``missing_variables`` reports what a caller
still has to supply.

``TemplateLibrary`` persists templates through the store's generic document API
(kind ``template``), so saved replies survive with the rest of the local data.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from quill_social.model import new_id, now_ms

_PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z0-9_]+)\}")


@dataclass
class Template:
    """A saved reply or post template (PRD 13.5)."""

    template_id: str = field(default_factory=lambda: new_id("tmpl"))
    name: str = ""
    body: str = ""
    variables: list[str] = field(default_factory=list)
    network_variants: dict[str, str] = field(default_factory=dict)
    signature: str = ""
    campaign_tags: list[str] = field(default_factory=list)
    accessibility_reminder: str = ""
    ai_instructions: str = ""
    created: int = field(default_factory=now_ms)

    def to_dict(self) -> dict:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "body": self.body,
            "variables": list(self.variables),
            "network_variants": dict(self.network_variants),
            "signature": self.signature,
            "campaign_tags": list(self.campaign_tags),
            "accessibility_reminder": self.accessibility_reminder,
            "ai_instructions": self.ai_instructions,
            "created": self.created,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Template:
        return cls(
            template_id=d.get("template_id") or new_id("tmpl"),
            name=d.get("name", ""),
            body=d.get("body", ""),
            variables=list(d.get("variables", [])),
            network_variants=dict(d.get("network_variants", {})),
            signature=d.get("signature", ""),
            campaign_tags=list(d.get("campaign_tags", [])),
            accessibility_reminder=d.get("accessibility_reminder", ""),
            ai_instructions=d.get("ai_instructions", ""),
            created=int(d.get("created", 0) or 0),
        )


def _body_for(template: Template, network: str) -> str:
    """The network variant body when present, else the base body (PRD 13.5)."""
    if network and network in template.network_variants:
        return template.network_variants[network]
    return template.body


def render(template: Template, values: dict[str, str], network: str = "") -> str:
    """Render a template into final text (PRD 13.5).

    Known ``{variable}`` placeholders are replaced by their value; unknown ones
    are left as ``{variable}`` so they remain visibly flagged rather than
    silently vanishing. When a ``network`` variant exists it is used as the body,
    and a non-empty signature is appended.
    """
    body = _body_for(template, network)

    def _sub(match: re.Match) -> str:
        name = match.group(1)
        if name in values:
            return str(values[name])
        return match.group(0)  # leave unknown placeholder flagged

    rendered = _PLACEHOLDER_RE.sub(_sub, body)
    if template.signature:
        rendered = f"{rendered}\n\n{template.signature}"
    return rendered


def missing_variables(template: Template, values: dict[str, str]) -> list[str]:
    """Declared or referenced variables not present in ``values`` (PRD 13.5).

    Combines the template's declared ``variables`` with any ``{placeholder}``
    found in the base body and every network variant, so nothing a render could
    need goes unreported.
    """
    needed: list[str] = list(template.variables)
    bodies = [template.body, *template.network_variants.values()]
    for text in bodies:
        for name in _PLACEHOLDER_RE.findall(text):
            if name not in needed:
                needed.append(name)
    return [name for name in needed if name not in values]


class TemplateLibrary:
    """Persistent template store backed by the document API (kind ``template``)."""

    KIND = "template"

    def __init__(self, store) -> None:
        self.store = store

    def add(self, template: Template) -> Template:
        self.store.put_document(
            self.KIND, template.template_id, template.to_dict(), ordinal=template.created
        )
        return template

    def get(self, template_id: str) -> Template | None:
        d = self.store.get_document(self.KIND, template_id)
        return Template.from_dict(d) if d else None

    def list(self) -> list[Template]:
        return [Template.from_dict(d) for d in self.store.list_documents(self.KIND)]

    def delete(self, template_id: str) -> None:
        self.store.delete_document(self.KIND, template_id)
