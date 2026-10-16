"""The two release-channel workflows, checked without running them.

``dev-builds.yml`` and ``promote-release.yml`` had never run (2026-10-15), and
the first real run should not be how a typo or a missing secret is found. CI's
``workflow-lint`` job runs actionlint over them; this pins what actionlint
cannot know:

* they name only the secrets and the Environment the owner sets up
  (docs/release/RELEASE.md);
* no ``${{ }}`` value is pasted into a script -- inputs, versions and SHAs
  reach the shell through ``env:``;
* every Dev build job builds and labels the one commit ``decide`` chose, so
  "has main changed since the last Dev build?" compares like with like;
* Stable promotion waits for the ``stable-promotion`` Environment's approval;
* neither runs in a fork.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

REPO = Path(__file__).resolve().parents[3]
WORKFLOWS = REPO / ".github" / "workflows"

#: The secrets these workflows may name: the Dev publishing token and Cast's
#: Podcast Index credentials. Signing keys never live in CI.
ALLOWED_SECRETS = {"DEV_BUILDS_TOKEN", "QUILL_PODCAST_INDEX_KEY", "QUILL_PODCAST_INDEX_SECRET"}


def _load(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def _steps(workflow: dict):
    for job_name, job in workflow["jobs"].items():
        for step in job.get("steps", []):
            yield job_name, step


@pytest.mark.parametrize("name", ["dev-builds.yml", "promote-release.yml"])
def test_only_the_expected_secrets_are_named(name: str) -> None:
    text = (WORKFLOWS / name).read_text(encoding="utf-8")
    named = set(re.findall(r"secrets\.([A-Z0-9_]+)", text))
    assert named <= ALLOWED_SECRETS, named - ALLOWED_SECRETS
    assert "FEED_SIGNING" not in text and "AZURE" not in text


@pytest.mark.parametrize("name", ["dev-builds.yml", "promote-release.yml"])
def test_no_expression_is_pasted_into_a_script(name: str) -> None:
    for job_name, step in _steps(_load(name)):
        script = step.get("run", "")
        assert "${{" not in script, f"{name} {job_name}: {step.get('name', '')}"


@pytest.mark.parametrize("name", ["dev-builds.yml", "promote-release.yml"])
def test_it_never_runs_in_a_fork(name: str) -> None:
    workflow = _load(name)
    first = next(iter(workflow["jobs"].values()))
    assert first.get("if") == "github.repository == 'Community-Access/quill'"


def test_dev_builds_build_and_label_the_commit_decide_chose() -> None:
    workflow = _load("dev-builds.yml")
    jobs = workflow["jobs"]
    assert jobs["decide"]["outputs"]["sha"] == "${{ steps.head.outputs.sha }}"
    checkout = next(s for s in jobs["build"]["steps"] if "checkout" in s.get("uses", ""))
    assert checkout["with"]["ref"] == "${{ needs.decide.outputs.sha }}"
    publish = next(s for s in jobs["publish"]["steps"] if s.get("name", "").startswith("Publish"))
    assert publish["env"]["SHA"] == "${{ needs.decide.outputs.sha }}"
    assert "Community-Access/quill@%s" in publish["run"] and '"$SHA"' in publish["run"]
    # Never to the main repository, whose first 30 releases installed copies read.
    assert workflow["env"]["DEV_REPO"] == "Community-Access/quillville-dev-builds"
    assert "--prerelease" in publish["run"] and "--latest=false" in publish["run"]


def test_dev_builds_stop_at_once_without_their_token() -> None:
    steps = _load("dev-builds.yml")["jobs"]["decide"]["steps"]
    names = [s.get("name", "") for s in steps]
    check = names.index("Check the dev-builds token is set")
    assert check < names.index("Decide whether today's Dev build runs")
    assert 'if [ -z "$GH_TOKEN" ]' in steps[check]["run"]


def test_only_radio_is_asked_to_skip_its_catalog() -> None:
    """-SkipCatalog is a switch only Quill Radio's build_release.ps1 declares."""
    build = next(
        s
        for s in _load("dev-builds.yml")["jobs"]["build"]["steps"]
        if s.get("name", "").startswith("Build a sibling")
    )
    assert "$env:APP -eq 'radio'" in build["run"]
    call = next(line for line in build["run"].splitlines() if "build_release.ps1" in line)
    assert "-SkipCatalog" not in call and "@extra" in call
    for app in ("quilllite", "cast"):
        script = (REPO / "standalone" / app / "scripts" / "build_release.ps1").read_text("utf-8")
        assert "$DevVersion" in script and "$SkipPublishedCheck" in script


def test_stable_promotion_waits_for_the_owners_approval() -> None:
    jobs = _load("promote-release.yml")["jobs"]
    assert jobs["promote-stable"]["environment"] == "stable-promotion"
    assert "environment" not in jobs["checks"]
    for job in ("promote-beta", "promote-stable"):
        assert jobs[job]["needs"] == "checks"
        run = "\n".join(s.get("run", "") for s in jobs[job]["steps"])
        assert "--no-sign" in run
        assert "docs/release/promotions.log" in run


def test_the_promotion_log_path_is_the_one_the_script_writes() -> None:
    source = (REPO / "quill" / "tools" / "release_feed.py").read_text(encoding="utf-8")
    assert 'root / "docs" / "release" / "promotions.log"' in source
