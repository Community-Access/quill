"""GitHub-native registry sync.

Scans the QUILL repository for every artifact type the Hub publishes --
Quillins, AI agents, and skill packs -- and syncs them into the Hub
database as Verified artifacts (if it landed on main, it passed the
Quillin Verify workflow).

Requires ``GITHUB_TOKEN`` in the environment; the worker uses the
GitHub Contents API to enumerate the repo. Without a token, every
API call returns 401 immediately and no artifacts are synced.

Run as a cron job or worker::

    GITHUB_TOKEN=... python worker/sync_to_pages.py
"""

import json
import os
import re

from app import db
from app.models.database import Artifact
from github import Github

_REPO = "Community-Access/quill"

# Match the 'key id:' line in a minisig-shaped sidecar. We use a
# permissive match (whitespace, any non-empty key id) so that a
# future minisig variant or a manually-edited sidecar still parses.
_SIG_KEY_ID_RE = re.compile(r"^key id:\s*(\S+)", re.MULTILINE)

# Roots scanned for Quillin directories (manifest.json per child directory).
_QUILLIN_ROOTS = ("quill/quillins_bundled",)
# Root scanned for single-file AI agents (.md / .json).
_AGENT_ROOT = "quill/core/ai/agents"


def _read_signer_key_id(repo, sidecar_path: str) -> str | None:
    """Return the signer key id from a minisig-shaped sidecar, or None.

    The Hub does not enforce the presence of a sidecar; it just records
    the signer key id when one is found. Bundled Quillin directories
    don't have a sidecar (the sidecar convention is <file>.minisig);
    single-file artifacts (agents, packs) do.
    """
    try:
        content = repo.get_contents(sidecar_path)
    except Exception:  # noqa: BLE001 - missing sidecar is normal
        return None
    text = content.decoded_content.decode("utf-8", errors="replace")
    match = _SIG_KEY_ID_RE.search(text)
    return match.group(1) if match else None


def _upsert(
    manifest_id,
    artifact_type,
    name,
    version,
    description,
    download_url,
    signer_key_id=None,
):
    artifact = Artifact.query.filter_by(manifest_id=manifest_id).first()
    if not artifact:
        artifact = Artifact(manifest_id=manifest_id)
    artifact.artifact_type = artifact_type
    artifact.name = name
    artifact.version = version or "0.0.0"
    artifact.description = description or ""
    artifact.status = "Verified"  # main is post-review by definition
    artifact.download_url = download_url
    artifact.signer_key_id = signer_key_id
    db.session.add(artifact)
    db.session.commit()


def _sync_quillins(repo, repo_name):
    for root in _QUILLIN_ROOTS:
        try:
            contents = repo.get_contents(root)
        except Exception as exc:  # noqa: BLE001 - a missing root is not fatal
            print(f"Skipping {root}: {exc}")
            continue
        for content_file in contents:
            if content_file.type != "dir":
                continue
            manifest_path = f"{content_file.path}/manifest.json"
            try:
                manifest_content = repo.get_contents(manifest_path)
                manifest = json.loads(manifest_content.decoded_content)
                _upsert(
                    manifest_id=manifest["id"],
                    artifact_type="quillin",
                    name=manifest["name"],
                    version=manifest.get("version", "0.0.0"),
                    description=manifest.get("description", ""),
                    download_url=(f"https://github.com/{repo_name}/tree/main/{content_file.path}"),
                )
                _sync_skill_packs_in(repo, repo_name, content_file.path)
            except Exception as exc:  # noqa: BLE001
                print(f"Error syncing quillin {content_file.path}: {exc}")


def _sync_skill_packs_in(repo, repo_name, directory):
    """Skill packs (.sqp) shipped inside a Quillin are also listed standalone."""
    try:
        contents = repo.get_contents(directory)
    except Exception:  # noqa: BLE001
        return
    for content_file in contents:
        if content_file.type != "file" or not content_file.name.endswith(".sqp"):
            continue
        try:
            source = content_file.decoded_content.decode("utf-8")
            front = _front_matter(source)
            name = front.get("name", content_file.name)
            signer = _read_signer_key_id(repo, f"{content_file.path}.minisig")
            _upsert(
                manifest_id=f"sqp:{content_file.name[: -len('.sqp')]}",
                artifact_type="skill-pack",
                name=name,
                version=front.get("version", "0.0.0"),
                description=front.get("description", ""),
                download_url=f"https://github.com/{repo_name}/raw/main/{content_file.path}",
                signer_key_id=signer,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"Error syncing skill pack {content_file.path}: {exc}")


def _sync_agents(repo, repo_name):
    try:
        contents = repo.get_contents(_AGENT_ROOT)
    except Exception as exc:  # noqa: BLE001
        print(f"Skipping {_AGENT_ROOT}: {exc}")
        return
    for content_file in contents:
        if content_file.type != "file":
            continue
        if not content_file.name.endswith((".md", ".json")):
            continue
        if content_file.name.lower().startswith(("readme", "_", ".")):
            continue
        try:
            source = content_file.decoded_content.decode("utf-8")
            if content_file.name.endswith(".json"):
                data = json.loads(source)
                agent_id = data.get("id", content_file.name)
                name = data.get("display_name", agent_id)
                description = data.get("description", "")
                version = data.get("version", "0.0.0")
            else:
                front = _front_matter(source)
                agent_id = front.get("id", content_file.name[: -len(".md")])
                name = front.get("display_name", agent_id)
                description = front.get("description", "")
                version = front.get("version", "0.0.0")
            signer = _read_signer_key_id(repo, f"{content_file.path}.minisig")
            _upsert(
                manifest_id=f"agent:{agent_id}",
                artifact_type="agent",
                name=name,
                version=version,
                description=description,
                download_url=f"https://github.com/{repo_name}/raw/main/{content_file.path}",
                signer_key_id=signer,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"Error syncing agent {content_file.path}: {exc}")


def _front_matter(source):
    """Minimal front matter reader: 'key: value' lines between --- fences."""
    fields = {}
    lines = source.splitlines()
    if not lines or lines[0].strip() != "---":
        return fields
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            break
        if ":" in stripped and not stripped.startswith(("-", "#")):
            key, _, value = stripped.partition(":")
            fields[key.strip()] = value.strip()
    return fields


def sync_from_github(token, repo_name=_REPO):
    """Scan the GitHub repository for artifacts and sync them to the local DB."""
    g = Github(token)
    repo = g.get_repo(repo_name)
    _sync_quillins(repo, repo_name)
    _sync_agents(repo, repo_name)


if __name__ == "__main__":
    # This would typically be run as a cron job or worker.
    from app import create_app

    app = create_app()
    with app.app_context():
        sync_from_github(os.environ.get("GITHUB_TOKEN"))
