"""Diagnostic bundles that exclude credentials and private content (PRD 31.4).

A diagnostic bundle helps support without leaking the user's data. Per PRD 31.4
it must: exclude credentials and private content by default, show the files it
includes, offer redaction, and carry versions, capabilities, and error codes so
a problem can be diagnosed. This module builds that bundle purely; opening it in
QUILL before sending is the UI's job.

The bundle is assembled from a plain ``info`` dict so the caller controls what
is offered. Credentials are ALWAYS dropped -- there is no flag to include them.
Files or content marked private are dropped unless ``include_private`` is set,
and secret-looking text is redacted via ``security.credentials.redact``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from quill_social.security.credentials import redact


@dataclass
class DiagnosticFile:
    """One file offered for the bundle."""

    name: str = ""
    content: str = ""
    private: bool = False
    contains_secrets: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> DiagnosticFile:
        return cls(
            name=d.get("name", ""),
            content=d.get("content", ""),
            private=bool(d.get("private", False)),
            contains_secrets=bool(d.get("contains_secrets", False)),
        )


@dataclass
class DiagnosticBundle:
    """An assembled, privacy-filtered diagnostic bundle (PRD 31.4)."""

    versions: dict = field(default_factory=dict)
    capabilities: dict = field(default_factory=dict)
    error_codes: list = field(default_factory=list)
    files: list[DiagnosticFile] = field(default_factory=list)
    included_files: list[str] = field(default_factory=list)
    excluded: list[dict] = field(default_factory=list)  # {"name", "reason"}
    include_private: bool = False
    redacted: bool = True

    def to_dict(self) -> dict:
        # Note: there is intentionally no ``credentials`` key -- credentials are
        # never part of a diagnostic bundle (PRD 31.4).
        return {
            "versions": dict(self.versions),
            "capabilities": dict(self.capabilities),
            "error_codes": list(self.error_codes),
            "files": [
                {"name": f.name, "content": f.content} for f in self.files
            ],
            "included_files": list(self.included_files),
            "excluded": list(self.excluded),
            "include_private": self.include_private,
            "redacted": self.redacted,
        }


def build_bundle(
    info: dict,
    *,
    include_private: bool = False,
    redact_secrets: bool = True,
) -> DiagnosticBundle:
    """Assemble a diagnostic bundle from ``info`` (PRD 31.4).

    ``info`` may contain ``versions``, ``capabilities``, ``error_codes``, and a
    ``files`` list of dicts (``name``, ``content``, ``private``,
    ``contains_secrets``). Any ``credentials`` key is dropped unconditionally.
    Private files/content are dropped unless ``include_private`` is set. When
    ``redact_secrets`` is on, included content and any file flagged
    ``contains_secrets`` is passed through :func:`redact`.
    """
    bundle = DiagnosticBundle(
        versions=dict(info.get("versions", {})),
        capabilities=dict(info.get("capabilities", {})),
        error_codes=list(info.get("error_codes", [])),
        include_private=include_private,
        redacted=redact_secrets,
    )

    # Credentials are never included, with no override (PRD 31.4).
    if info.get("credentials"):
        bundle.excluded.append(
            {"name": "credentials", "reason": "credentials are never included"}
        )

    # A dedicated private-content blob is excluded unless explicitly opted in.
    if info.get("private_content") and not include_private:
        bundle.excluded.append(
            {"name": "private_content", "reason": "private by default (PRD 31.4)"}
        )

    for raw in info.get("files", []):
        f = DiagnosticFile.from_dict(raw)
        if f.private and not include_private:
            bundle.excluded.append(
                {"name": f.name, "reason": "private by default (PRD 31.4)"}
            )
            continue
        content = f.content
        if redact_secrets:
            content = redact(content)
        bundle.files.append(
            DiagnosticFile(
                name=f.name,
                content=content,
                private=f.private,
                contains_secrets=f.contains_secrets,
            )
        )
        bundle.included_files.append(f.name)

    return bundle
