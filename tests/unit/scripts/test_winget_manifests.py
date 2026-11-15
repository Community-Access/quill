"""WinGet package templates keep the first-party updater safeguards."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from scripts.winget.manifests import (
    build_manifest_draft,
    load_catalog,
    validate_manifest_files,
    validate_templates,
)
from scripts.winget.submit import _branch_name

REPO_ROOT = Path(__file__).resolve().parents[3]


def _release(*, tag: str = "quill-radio-v3.0.4", version: str = "3.0.4") -> dict[str, object]:
    return {
        "tag_name": tag,
        "draft": False,
        "prerelease": False,
        "html_url": f"https://github.com/Community-Access/quill/releases/tag/{tag}",
        "assets": [
            {
                "name": f"Quill-Radio-Setup-Shared-{version}.exe",
                "browser_download_url": (
                    f"https://github.com/Community-Access/quill/releases/download/{tag}/"
                    f"Quill-Radio-Setup-Shared-{version}.exe"
                ),
                "digest": "sha256:" + "a" * 64,
            }
        ],
    }


def test_templates_keep_schema_and_updater_guards() -> None:
    validate_templates()


def test_stable_release_renders_one_consistent_three_file_set() -> None:
    draft = build_manifest_draft(_release(), "radio")

    assert draft.package_id == "CommunityAccess.QuillRadio"
    assert draft.package_version == "3.0.4"
    assert set(draft.files) == {
        "manifests/c/CommunityAccess/QuillRadio/3.0.4/CommunityAccess.QuillRadio.version.yaml",
        "manifests/c/CommunityAccess/QuillRadio/3.0.4/CommunityAccess.QuillRadio.locale.en-US.yaml",
        "manifests/c/CommunityAccess/QuillRadio/3.0.4/CommunityAccess.QuillRadio.installer.yaml",
    }
    validate_manifest_files(
        draft.files,
        package_id=draft.package_id,
        package_version=draft.package_version,
    )
    installer = next(text for text in draft.files.values() if "ManifestType: installer" in text)
    assert "RequireExplicitUpgrade: true" in installer
    assert "AppsAndFeaturesEntries:" in installer
    assert "ProductCode:" not in installer
    assert "UpgradeCode:" not in installer


def test_rebuild_uses_apps_and_features_version_not_build_number() -> None:
    release = _release(
        tag="quill-radio-v3.2.0-build.5",
        version="3.2.0",
    )
    draft = build_manifest_draft(release, "radio")

    assert draft.package_version == "3.2.0"
    assert draft.asset_name == "Quill-Radio-Setup-Shared-3.2.0.exe"


@pytest.mark.parametrize(
    "change",
    [
        {"draft": True},
        {"prerelease": True},
    ],
)
def test_non_stable_release_cannot_create_a_package(change: dict[str, object]) -> None:
    release = {**_release(), **change}
    with pytest.raises(ValueError, match="Stable"):
        build_manifest_draft(release, "radio")


def test_release_tag_must_name_requested_app() -> None:
    with pytest.raises(ValueError, match="does not identify"):
        build_manifest_draft(_release(tag="quill-lite-v1.1.2", version="1.1.2"), "radio")


def test_wrong_or_missing_setup_asset_fails_closed() -> None:
    release = deepcopy(_release())
    release["assets"] = []
    with pytest.raises(ValueError, match="Expected one"):
        build_manifest_draft(release, "radio")


def test_inno_package_does_not_gain_msi_matching_fields() -> None:
    draft = build_manifest_draft(_release(), "radio")
    files = dict(draft.files)
    installer_path = next(path for path in files if path.endswith("installer.yaml"))
    files[installer_path] += "ProductCode: {bad-installer-id}\n"

    with pytest.raises(ValueError, match="must not add MSI"):
        validate_manifest_files(
            files,
            package_id=draft.package_id,
            package_version=draft.package_version,
        )


def test_catalog_package_ids_and_monikers_are_unique() -> None:
    apps = load_catalog()["apps"]
    package_ids = [entry["package_id"].casefold() for entry in apps.values()]
    monikers = [entry["moniker"].casefold() for entry in apps.values()]

    assert len(package_ids) == len(set(package_ids))
    assert len(monikers) == len(set(monikers))


def test_new_app_requires_a_verified_https_product_page() -> None:
    catalog = load_catalog()
    catalog["apps"]["radio"]["package_url_verified"] = False

    with pytest.raises(ValueError, match="Confirm the official product page"):
        build_manifest_draft(_release(), "radio", catalog=catalog)


def test_submission_branch_is_stable_and_version_specific() -> None:
    assert _branch_name("CommunityAccess.QuillRadio", "3.0.4") == (
        "quill-communityaccess-quillradio-3-0-4"
    )


def test_workflow_keeps_public_submission_behind_reviewable_gates() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "winget-submit.yml").read_text(
        encoding="utf-8"
    )

    assert "environment:" in workflow
    assert "winget-submission" in workflow
    assert "WINGET_SUBMISSION_ENABLED == 'true'" in workflow
    assert "inputs.submit == true" in workflow
    assert "secrets.WINGET_SUBMIT_TOKEN" in workflow
