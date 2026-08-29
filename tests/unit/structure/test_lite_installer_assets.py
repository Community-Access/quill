"""Every Lite installer names a runtime asset that can actually exist.

The seven "-Lite" installers ship a ~3 MB app and download the shared
QuillVille Runtime installer from a GitHub release URL baked into each
``standalone/*/installer/*-lite.iss``. For months that URL said
``releases/latest/download/`` -- but ``latest`` follows the repository's newest
non-prerelease release, which is owned by the editor's release train and
carried no runtime asset, so the download was a 404 for every Lite user of
every app in the family. The 2026-08-18 runtime retrospective had already named
the lesson ("when a promise depends on an asset, gate the asset") and the gate
was never written. This is that gate.

The rules it enforces, offline (it compares declarations, it never makes a
request -- the same posture as the network egress audit):

* every Lite installer's ``RuntimeUrl`` points at a tag in the allowlist below,
  never at ``releases/latest`` (which will drift away from the runtime again);
* the filename each installer downloads is the one the runtime installer build
  actually emits (``OutputBaseFilename`` in ``quillville-runtime.iss``), so a
  rename on either side fails here rather than in a user's download;
* the native launcher's compiled-in default (the app-side "offer the runtime
  on first launch" path) names the same URL, so the two download routes cannot
  disagree.

An opt-in live check (``QUILL_CHECK_RELEASE_ASSETS=1``) confirms the asset is
really published -- for the release runbook, not for CI.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]

#: Release tags a runtime download may name. ``runtime-latest`` is a dedicated
#: moving tag republished by ``build_runtime_installer.ps1 -Publish``; it exists
#: so the runtime's cadence is not hostage to the editor's release train.
_ALLOWED_TAGS = {"runtime-latest"}

_URL_RE = re.compile(
    r"^https://github\.com/Community-Access/quill/releases/download/"
    r"(?P<tag>[^/]+)/(?P<file>[^/\"]+)$"
)


def _lite_installers() -> list[Path]:
    found = sorted((_REPO_ROOT / "standalone").glob("*/installer/*-lite.iss"))
    # Seven apps ship a Lite edition today; fewer means the glob broke, not
    # that the family shrank overnight.
    assert len(found) >= 7, f"expected at least 7 Lite installers, found {len(found)}: {found}"
    return found


def _runtime_url(iss_text: str, source: Path) -> str:
    match = re.search(r'#define RuntimeUrl "([^"]+)"', iss_text)
    assert match, f"{source}: no '#define RuntimeUrl' -- the Lite download contract moved?"
    return match.group(1)


def _emitted_setup_filename() -> str:
    """The filename the runtime installer build actually produces."""
    iss = _REPO_ROOT / "standalone" / "runtime" / "installer" / "quillville-runtime.iss"
    match = re.search(r"^OutputBaseFilename=(\S+)", iss.read_text(encoding="utf-8"), re.MULTILINE)
    assert match, f"{iss}: no OutputBaseFilename -- cannot learn the emitted setup name"
    return match.group(1) + ".exe"


def test_every_lite_installer_names_a_real_tag_and_the_emitted_filename() -> None:
    emitted = _emitted_setup_filename()
    for iss_path in _lite_installers():
        text = iss_path.read_text(encoding="utf-8")
        url = _runtime_url(text, iss_path)
        match = _URL_RE.match(url)
        assert match, (
            f"{iss_path}: RuntimeUrl is {url!r}. It must be a "
            "releases/download/<tag>/<file> URL -- releases/latest follows the "
            "editor's release train and served a 404 to every Lite user."
        )
        assert match.group("tag") in _ALLOWED_TAGS, (
            f"{iss_path}: tag {match.group('tag')!r} is not in the allowlist "
            f"{sorted(_ALLOWED_TAGS)}. Publish the runtime there first, then widen this."
        )
        assert match.group("file") == emitted, (
            f"{iss_path}: downloads {match.group('file')!r} but the runtime build "
            f"emits {emitted!r} -- one side was renamed without the other."
        )


def test_every_lite_installer_saves_the_download_under_the_same_name() -> None:
    emitted = _emitted_setup_filename()
    for iss_path in _lite_installers():
        text = iss_path.read_text(encoding="utf-8")
        adds = re.findall(r"DownloadPage\.Add\('\{#RuntimeUrl\}',\s*'([^']+)'", text)
        assert adds, f"{iss_path}: no DownloadPage.Add('{{#RuntimeUrl}}', ...) call"
        for saved_as in adds:
            assert saved_as == emitted, (
                f"{iss_path}: saves the runtime download as {saved_as!r} but the "
                f"build emits {emitted!r}; the Exec that follows would miss it."
            )


def test_the_native_launcher_defaults_to_the_same_url() -> None:
    """The app-side download route must not disagree with the installer-side one.

    The self-healing launcher compiles PRODUCT_RUNTIME_URL in (CMakeLists
    default) and offers the runtime download on first launch when the Lite
    install was declined or interrupted. Two routes, one truth.
    """
    cmake = _REPO_ROOT / "quill" / "native" / "launcher" / "CMakeLists.txt"
    match = re.search(r'set\(PRODUCT_RUNTIME_URL\s+"([^"]+)"\)', cmake.read_text(encoding="utf-8"))
    assert match, f"{cmake}: no default PRODUCT_RUNTIME_URL"
    launcher_url = match.group(1)
    first_iss = _lite_installers()[0]
    iss_url = _runtime_url(first_iss.read_text(encoding="utf-8"), first_iss)
    assert launcher_url == iss_url, (
        f"native launcher downloads {launcher_url!r} but the Lite installers "
        f"download {iss_url!r} -- the two runtime-download routes drifted."
    )


@pytest.mark.skipif(
    os.environ.get("QUILL_CHECK_RELEASE_ASSETS") != "1",
    reason="live release-asset check is opt-in (QUILL_CHECK_RELEASE_ASSETS=1); "
    "the offline tests above are the gate",
)
def test_the_published_asset_actually_resolves() -> None:
    import urllib.request

    first_iss = _lite_installers()[0]
    url = _runtime_url(first_iss.read_text(encoding="utf-8"), first_iss)
    request = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - https URL from the gate above
        assert response.status == 200
