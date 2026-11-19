"""Release and deployment evidence: what a release is, and what vouches for it (GX10).

Release Evidence... on a release's row reads, for that release:

- whether it is a draft, and whether GitHub has made it **immutable** (an
  immutable release's tag and files cannot change after publishing);
- the **commit** its tag points at;
- the **checks** on that commit, by name: which passed, which failed, which
  are still running (:func:`~quill.core.github.run_actions.combine_check_status`,
  the fold Combined Check Status uses);
- the **deployments** of that commit: which environment, and the latest state;
- for each file, its **digest** and GitHub's **artifact attestations** for it
  (``GET /repos/{o}/{r}/attestations/{digest}``): how many, and what kind.

Everything is read; nothing is changed. QUILL reads GitHub's attestation
records but does not check their signatures, and says so: ``gh attestation
verify`` does that. A part GitHub would not answer is said as unreadable, not
as none, so a missing permission never reads as missing evidence.

:func:`environment_deployments` is the same deployment reading for one
environment (an environment's Deployments...). wx-free and strict-typed.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

from quill.core.github.rest_transport import GitHubRestError
from quill.core.github.run_actions import CombinedCheckStatus, combine_check_status
from quill.core.github.workbench_api import GitHubApi

__all__ = [
    "AssetEvidence",
    "DeploymentEvidence",
    "VERIFY_NOTE",
    "ReleaseEvidence",
    "asset_attestations",
    "attestations_for_asset",
    "environment_deployments",
    "load_release_evidence",
]

#: Predicate types GitHub's attest actions write, in words.
_PREDICATES = {
    "https://slsa.dev/provenance/v1": "build provenance",
    "https://spdx.dev/Document/v2.3": "software bill of materials (SPDX)",
    "https://cyclonedx.org/bom": "software bill of materials (CycloneDX)",
}

VERIFY_NOTE = (
    "QUILL reads GitHub's attestation records; it does not check their signatures. "
    "gh attestation verify does."
)


@dataclass(frozen=True)
class DeploymentEvidence:
    deployment_id: int
    environment: str
    state: str
    """The latest status's state, ``no status yet``, or ``status unreadable``."""
    when: str
    sha: str = ""
    ref: str = ""
    creator: str = ""

    def line(self) -> str:
        made = f" by {self.creator}" if self.creator else ""
        at = f" ({self.ref}, commit {self.sha[:7]})" if self.ref or self.sha else ""
        return f"{self.environment}: {self.state}, {self.when}{made}{at}."


@dataclass(frozen=True)
class AssetEvidence:
    name: str
    digest: str
    attestations: int | None
    """How many; None when GitHub would not say."""
    kinds: tuple[str, ...] = ()
    note: str = ""

    def line(self) -> str:
        if not self.digest:
            return self.note or (
                f"{self.name}: GitHub gives no digest for it, so attestations cannot be looked up."
            )
        short = self.digest.split(":", 1)[-1][:12]
        if self.attestations is None:
            return f"{self.name} (digest {short}): attestations unreadable. {self.note}".strip()
        if not self.attestations:
            return f"{self.name} (digest {short}): no attestations."
        kinds = f": {', '.join(self.kinds)}" if self.kinds else ""
        many = "attestation" if self.attestations == 1 else "attestations"
        return f"{self.name} (digest {short}): {self.attestations} {many}{kinds}."


@dataclass(frozen=True)
class ReleaseEvidence:
    repository: str
    tag: str
    name: str = ""
    draft: bool = False
    prerelease: bool = False
    immutable: bool | None = None
    published: str = ""
    sha: str = ""
    checks: CombinedCheckStatus | None = None
    deployments: tuple[DeploymentEvidence, ...] = ()
    assets: tuple[AssetEvidence, ...] = ()
    unreadable: tuple[str, ...] = field(default_factory=tuple)

    @property
    def immutable_words(self) -> str:
        if self.immutable is None:
            return "GitHub did not say whether it is immutable."
        if self.immutable:
            return "Immutable: its tag and files cannot change."
        return "Not immutable: its tag and files can still change."

    def _check_lines(self) -> list[str]:
        if self.checks is None:
            return []
        out = [f"Checks: {self.checks.one_line()}"]
        for word, state in (("Passed", "pass"), ("Failed", "fail"), ("Still running", "pending")):
            names = [c.name for c in self.checks.checks if c.state == state]
            if names:
                out.append(f"{word}: {', '.join(names)}.")
        return out

    def lines(self) -> list[str]:
        kind = "draft" if self.draft else "pre-release" if self.prerelease else "release"
        out = [f"{self.name or self.tag}: {kind} {self.tag} in {self.repository}."]
        if self.published:
            out.append(f"Published {self.published}.")
        out.append(self.immutable_words)
        out.append(f"Commit: {self.sha}." if self.sha else "Commit: the tag is not on GitHub yet.")
        out.extend(self._check_lines())
        if self.deployments:
            out.append(f"Deployments of this commit: {len(self.deployments)}.")
            out.extend(d.line() for d in self.deployments)
        elif self.sha and "deployments" not in self.unreadable:
            out.append("Deployments of this commit: none.")
        if self.assets:
            out.append(f"Files: {len(self.assets)}.")
            out.extend(a.line() for a in self.assets)
            if any(a.attestations for a in self.assets):
                out.append(VERIFY_NOTE)
        else:
            out.append("Files: none.")
        out.extend(f"Could not read the {part}." for part in self.unreadable)
        return out

    @property
    def sentence(self) -> str:
        """The one line said when the evidence opens."""
        parts = [self.immutable_words.split(":", 1)[0].split(".", 1)[0]]
        if self.checks is not None:
            parts.append(self.checks.one_line().rstrip("."))
        parts.append(f"{len(self.deployments)} deployments")
        attested = sum(1 for a in self.assets if a.attestations)
        parts.append(f"{attested} of {len(self.assets)} files attested")
        return f"{self.tag}: " + "; ".join(parts) + "."


def _get(api: GitHubApi, path: str, query: Mapping[str, str] | None = None) -> Any:
    return api.rest("GET", path, query=dict(query) if query else None).data


def _when(value: object) -> str:
    return str(value or "")[:16].replace("T", " ")


def _deployments(api: GitHubApi, repo: str, query: Mapping[str, str]) -> list[DeploymentEvidence]:
    rows = _get(api, f"/repos/{repo}/deployments", query)
    found: list[DeploymentEvidence] = []
    for raw in rows if isinstance(rows, list) else ():
        if not isinstance(raw, Mapping):
            continue
        ident = int(raw.get("id") or 0)
        try:
            statuses = _get(api, f"/repos/{repo}/deployments/{ident}/statuses", {"per_page": "1"})
            latest = statuses[0] if isinstance(statuses, list) and statuses else None
            state = str(latest.get("state") or "") if isinstance(latest, Mapping) else ""
            state = state or "no status yet"
            when = _when(latest.get("created_at")) if isinstance(latest, Mapping) else ""
        except GitHubRestError:
            state, when = "status unreadable", ""
        creator = raw.get("creator")
        found.append(
            DeploymentEvidence(
                ident,
                str(raw.get("environment") or "no environment"),
                state,
                when or _when(raw.get("created_at")),
                str(raw.get("sha") or ""),
                str(raw.get("ref") or ""),
                str(creator.get("login") or "") if isinstance(creator, Mapping) else "",
            )
        )
    return found


def environment_deployments(
    api: GitHubApi, repo: str, environment: str, *, limit: int = 30
) -> list[DeploymentEvidence]:
    """The newest deployments to *environment*, each with its latest status."""
    query = {"environment": environment, "per_page": str(max(1, min(limit, 100)))}
    return _deployments(api, repo, query)


def _kind(attestation: Mapping[str, Any]) -> str:
    bundle = attestation.get("bundle")
    envelope = bundle.get("dsseEnvelope") if isinstance(bundle, Mapping) else None
    payload = envelope.get("payload") if isinstance(envelope, Mapping) else None
    if not isinstance(payload, str):
        return ""
    try:
        statement = json.loads(base64.b64decode(payload))
    except (ValueError, TypeError):
        return ""
    predicate = str(statement.get("predicateType") or "") if isinstance(statement, dict) else ""
    return _PREDICATES.get(predicate, predicate)


def asset_attestations(api: GitHubApi, repo: str, name: str, digest: str) -> AssetEvidence:
    """GitHub's attestations for one file, found by its digest."""
    if not digest:
        return AssetEvidence(name, "", None)
    path = f"/repos/{repo}/attestations/{quote(digest, safe=':')}"
    try:
        data = _get(api, path, {"per_page": "100"})
    except GitHubRestError as exc:
        if exc.status == 404:
            return AssetEvidence(name, digest, 0)
        note = "It needs read access to the repository's attestations."
        return AssetEvidence(name, digest, None, note=note if exc.status in (401, 403) else "")
    rows = data.get("attestations") if isinstance(data, Mapping) else None
    found = [row for row in rows or () if isinstance(row, Mapping)]
    kinds = tuple(dict.fromkeys(kind for kind in map(_kind, found) if kind))
    return AssetEvidence(name, digest, len(found), kinds)


def attestations_for_asset(api: GitHubApi, repo: str, tag: str, name: str) -> AssetEvidence:
    """One file of the release tagged *tag*: its digest, then its attestations."""
    release = _get(api, f"/repos/{repo}/releases/tags/{quote(tag, safe='')}")
    for asset in release.get("assets") or () if isinstance(release, Mapping) else ():
        if isinstance(asset, Mapping) and asset.get("name") == name:
            return asset_attestations(api, repo, name, str(asset.get("digest") or ""))
    return AssetEvidence(name, "", None, note=f"{tag} has no file called {name} now.")


def _commit(api: GitHubApi, repo: str, tag: str) -> str:
    data = _get(api, f"/repos/{repo}/commits/{quote(tag, safe='')}")
    return str(data.get("sha") or "") if isinstance(data, Mapping) else ""


def _checks(api: GitHubApi, repo: str, sha: str) -> CombinedCheckStatus:
    base = f"/repos/{repo}/commits/{sha}"
    status = _get(api, f"{base}/status")
    runs = _get(api, f"{base}/check-runs", {"per_page": "100"})
    return combine_check_status(sha, status, runs)


def load_release_evidence(api: GitHubApi, repo: str, tag: str) -> ReleaseEvidence:
    """Read everything that vouches for the release tagged *tag*; nothing is changed."""
    release = _get(api, f"/repos/{repo}/releases/tags/{quote(tag, safe='')}")
    if not isinstance(release, Mapping):
        release = {}
    unreadable: list[str] = []
    sha = ""
    checks: CombinedCheckStatus | None = None
    deployments: list[DeploymentEvidence] = []
    if not release.get("draft"):
        try:
            sha = _commit(api, repo, tag)
        except GitHubRestError:
            unreadable.append("commit")
    if sha:
        try:
            checks = _checks(api, repo, sha)
        except GitHubRestError:
            unreadable.append("checks")
        try:
            deployments = _deployments(api, repo, {"sha": sha, "per_page": "30"})
        except GitHubRestError:
            unreadable.append("deployments")
    assets = tuple(
        asset_attestations(api, repo, str(a.get("name") or ""), str(a.get("digest") or ""))
        for a in release.get("assets") or ()
        if isinstance(a, Mapping)
    )
    immutable = release.get("immutable")
    return ReleaseEvidence(
        repository=repo,
        tag=tag,
        name=str(release.get("name") or ""),
        draft=bool(release.get("draft")),
        prerelease=bool(release.get("prerelease")),
        immutable=immutable if isinstance(immutable, bool) else None,
        published=_when(release.get("published_at")),
        sha=sha,
        checks=checks,
        deployments=tuple(deployments),
        assets=assets,
        unreadable=tuple(unreadable),
    )
