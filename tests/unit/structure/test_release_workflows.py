"""The release-channel workflows, checked without running them.

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

#: The secrets these workflows may name: Cast's Podcast Index credentials, plus
#: the feed seed in protected signing jobs. No personal token: Dev builds are
#: published to this repository with the workflow's own token.
ALLOWED_SECRETS = {
    "QUILL_FEED_SIGNING_KEY",
    "QUILL_PODCAST_INDEX_KEY",
    "QUILL_PODCAST_INDEX_SECRET",
}


def _load(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def _steps(workflow: dict):
    for job_name, job in workflow["jobs"].items():
        for step in job.get("steps", []):
            yield job_name, step


@pytest.mark.parametrize(
    "name",
    ["dev-builds.yml", "promote-release.yml", "release-feeds.yml", "release-feed-batch.yml"],
)
def test_only_the_expected_secrets_are_named(name: str) -> None:
    text = (WORKFLOWS / name).read_text(encoding="utf-8")
    named = set(re.findall(r"secrets\.([A-Z0-9_]+)", text))
    assert named <= ALLOWED_SECRETS, named - ALLOWED_SECRETS
    assert "AZURE" not in text


@pytest.mark.parametrize(
    "name",
    ["dev-builds.yml", "promote-release.yml", "release-feeds.yml", "release-feed-batch.yml"],
)
def test_no_expression_is_pasted_into_a_script(name: str) -> None:
    for job_name, step in _steps(_load(name)):
        script = step.get("run", "")
        assert "${{" not in script, f"{name} {job_name}: {step.get('name', '')}"


@pytest.mark.parametrize(
    "name",
    ["dev-builds.yml", "promote-release.yml", "release-feeds.yml", "release-feed-batch.yml"],
)
def test_it_never_runs_in_a_fork(name: str) -> None:
    workflow = _load(name)
    first = next(iter(workflow["jobs"].values()))
    assert "github.repository == 'Community-Access/quill'" in first.get("if", "")


def test_every_feed_signing_job_waits_for_owner_approval() -> None:
    expected = {
        "release-feeds.yml": {("sign", "release-feed-signing")},
        "promote-release.yml": {
            ("promote-beta", "release-feed-signing"),
            ("promote-stable", "stable-promotion"),
        },
        "release-feed-batch.yml": {("promote", "release-feed-signing")},
        "windows-release.yml": {("release", "release-feed-signing")},
    }
    found: dict[str, set[tuple[str, str]]] = {}
    for name, jobs in expected.items():
        workflow = _load(name)
        for job_name, environment in jobs:
            job = workflow["jobs"][job_name]
            assert job.get("environment") == environment
            uses_secret = any(
                "QUILL_FEED_SIGNING_KEY" in str(step.get("env", {}))
                for step in job.get("steps", [])
            )
            assert uses_secret, f"{name} {job_name} does not use its protected seed"
            found.setdefault(name, set()).add((job_name, environment))
    assert found == expected


def test_no_other_workflow_can_receive_the_feed_seed() -> None:
    allowed = {
        "release-feeds.yml",
        "release-feed-batch.yml",
        "promote-release.yml",
        "windows-release.yml",
    }
    named = {
        path.name
        for path in WORKFLOWS.glob("*.yml")
        if "secrets.QUILL_FEED_SIGNING_KEY" in path.read_text(encoding="utf-8")
    }
    assert named == allowed


def test_dev_builds_build_the_commit_decide_chose_and_record_it() -> None:
    workflow = _load("dev-builds.yml")
    jobs = workflow["jobs"]
    assert jobs["decide"]["outputs"]["sha"] == "${{ steps.head.outputs.sha }}"
    checkout = next(s for s in jobs["build"]["steps"] if "checkout" in s.get("uses", ""))
    assert checkout["with"]["ref"] == "${{ needs.decide.outputs.sha }}"
    # The commit each build came from is written into the release notes, once, by
    # the job that runs after every upload.
    finalize = jobs["finalize"]
    record = next(s for s in finalize["steps"] if s.get("name", "").startswith("Record"))
    assert record["env"]["SHA"] == "${{ needs.decide.outputs.sha }}"
    assert "scripts/dev_release_finalize.py" in record["run"] and '"$SHA"' in record["run"]
    assert set(finalize["needs"]) == {"decide", "publish"}
    assert "always()" in finalize["if"] and "needs.decide.outputs.build" in finalize["if"]


def test_dev_builds_are_files_in_one_rolling_release_of_this_repository() -> None:
    """One release, so one place on the page installed Radio 3.0.4 and Lite 1.1.2 read."""
    workflow = _load("dev-builds.yml")
    text = str(workflow)
    assert "quillville-dev-builds" not in text and "DEV_BUILDS_TOKEN" not in text
    assert "DEV_REPO" not in text
    upload = next(
        s for s in workflow["jobs"]["publish"]["steps"] if s.get("name", "").startswith("Upload")
    )
    assert "gh release upload dev-builds" in upload["run"]
    assert '"$GITHUB_REPOSITORY"' in upload["run"] and "--clobber" in upload["run"]
    # No build is a release of its own: that is the thing that would push the
    # Stable releases off the first page.
    assert "gh release create" not in upload["run"]
    assert upload["env"]["GH_TOKEN"] == "${{ github.token }}"


def test_dev_builds_use_only_the_workflows_own_token_and_write_only_where_needed() -> None:
    workflow = _load("dev-builds.yml")
    assert workflow["permissions"] == {"contents": "read"}
    jobs = workflow["jobs"]
    assert "permissions" not in jobs["build"]  # compiling needs no write access
    for name in ("decide", "publish", "finalize"):
        assert jobs[name]["permissions"] == {"contents": "write"}, name
    for name, job in jobs.items():
        for step in job["steps"]:
            token = str(step.get("env", {}).get("GH_TOKEN", ""))
            assert token in ("", "${{ github.token }}"), (name, step.get("name"))
    ensure = next(s for s in jobs["decide"]["steps"] if "exists" in s.get("name", ""))
    assert "--ensure" in ensure["run"]  # made once, before eleven uploads race to make it
    names = [s.get("name", "") for s in jobs["decide"]["steps"]]
    assert names.index(ensure["name"]) < names.index("Decide whether today's Dev build runs")


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
    for job in jobs.values():
        checkout = next(step for step in job["steps"] if "checkout" in step.get("uses", ""))
        assert checkout["with"]["ref"] == "main"
    for job in ("promote-beta", "promote-stable"):
        assert jobs[job]["needs"] == "checks"
        run = "\n".join(s.get("run", "") for s in jobs[job]["steps"])
        assert "--no-sign" not in run
        assert "scripts/feed_tool.py verify" in run
        assert "docs/release/promotions.log" in run


def test_feed_bootstrap_is_main_only_and_verifies_before_opening_a_pr() -> None:
    workflow = _load("release-feeds.yml")
    preflight = workflow["jobs"]["preflight"]
    assert "github.ref == 'refs/heads/main'" in preflight["if"]
    checkout = next(s for s in preflight["steps"] if "checkout" in s.get("uses", ""))
    assert checkout["with"]["ref"] == "main"
    sign = workflow["jobs"]["sign"]
    names = [step.get("name", "") for step in sign["steps"]]
    assert names.index("Verify every feed and the signed index") < names.index(
        "Open the signed feed pull request"
    )
    assert "bootstrap_release_feeds.py" in "\n".join(step.get("run", "") for step in sign["steps"])
    pr_step = next(
        step for step in sign["steps"] if step.get("name") == "Open the signed feed pull request"
    )
    assert "git status --porcelain -- docs/site/updates/v2" in pr_step["run"]


def test_batch_promotion_has_one_unprotected_preflight_and_one_signed_pr() -> None:
    workflow = _load("release-feed-batch.yml")
    preflight = workflow["jobs"]["preflight"]
    promote = workflow["jobs"]["promote"]
    assert "environment" not in preflight
    assert "QUILL_FEED_SIGNING_KEY" not in str(preflight)
    assert preflight["env"]["SOURCE_SHA"] == "${{ inputs.sha }}"
    assert preflight["env"]["SKIP_SOAK"] == "${{ inputs.skip_soak }}"
    assert "--dry-run" in "\n".join(step.get("run", "") for step in preflight["steps"])
    assert promote["environment"] == "release-feed-signing"
    assert promote["needs"] == "preflight"
    batch_step = next(
        step
        for step in promote["steps"]
        if step.get("name") == "List and promote every Dev app, sequentially"
    )
    assert batch_step["env"]["GH_TOKEN"] == "${{ github.token }}"
    runs = [step.get("run", "") for step in promote["steps"]]
    assert all("QUILL_FEED_SIGNING_KEY" not in run for run in runs)
    assert "--key-file" not in "\n".join(runs)
    assert "QUILL_FEED_KEY_FILE" not in str(workflow)
    assert sum("gh pr create" in run for run in runs) == 1
    names = [step.get("name", "") for step in promote["steps"]]
    assert names.index("Verify every signed feed and the signed index") < names.index(
        "Open one signed batch-feed pull request"
    )
    pr_run = runs[names.index("Open one signed batch-feed pull request")]
    assert "docs/site/updates/v2 docs/release/promotions.log" in pr_run
    assert "git add" in pr_run
    artifacts = [
        step
        for step in workflow["jobs"].values()
        for step in step["steps"]
        if "upload-artifact" in step.get("uses", "")
    ]
    assert len(artifacts) == 2
    assert {artifact["with"]["name"] for artifact in artifacts} == {"release-feed-batch-audit"}
    assert any("inputs.dry_run" in str(step.get("if")) for step in preflight["steps"])


def test_the_promotion_log_path_is_the_one_the_script_writes() -> None:
    source = (REPO / "quill" / "tools" / "release_feed.py").read_text(encoding="utf-8")
    assert 'root / "docs" / "release" / "promotions.log"' in source
