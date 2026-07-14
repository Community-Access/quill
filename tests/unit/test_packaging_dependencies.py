"""Packaging-dependency invariants.

These guard a class of "green tests, broken build" bugs where a package that a
*default* feature needs at runtime is declared only in an optional extra (or the
dev extra). Dev and CI install those extras, so import-based tests pass -- but the
shipped runtime, which installs only the base dependencies, is missing the package
and the feature fails at first use. See the beta-2 speech-engine fixes:

- huggingface_hub: the default whisper.cpp speech-to-text engine downloads its
  GGML models via huggingface_hub.hf_hub_download, so it must be a base dep.
- Babel: the Kokoro ONNX voice chain (kokoro-onnx -> phonemizer -> segments ->
  csvw -> babel.numbers) needs it; it must ride with the [kokoro] extra, not only
  [dev].
"""

from __future__ import annotations

import pathlib
import tomllib

import pytest

_PYPROJECT = pathlib.Path(__file__).resolve().parents[2] / "pyproject.toml"


@pytest.fixture(scope="module")
def project() -> dict:
    return tomllib.loads(_PYPROJECT.read_text("utf-8"))["project"]


def _names(requirements: list[str]) -> set[str]:
    """Distribution names from PEP 508 requirement strings, lowercased.

    Normalizes '-'/'_' so 'huggingface_hub' and 'huggingface-hub' compare equal.
    """
    out: set[str] = set()
    for req in requirements:
        head = req.split(";", 1)[0].strip()
        for sep in ("==", ">=", "<=", "~=", ">", "<", "!=", "[", " "):
            head = head.split(sep, 1)[0]
        out.add(head.strip().lower().replace("_", "-"))
    return out


def test_huggingface_hub_is_a_base_runtime_dependency(project: dict) -> None:
    """The default whisper.cpp downloader needs huggingface_hub on a clean install.

    It must be in [project].dependencies -- not only the optional [fasterwhisper]
    extra -- so speech-to-text model downloads work without opting into Faster
    Whisper. Regression guard for QUILL-SPEECH-PROVIDER-FAILED "needs the
    'huggingface_hub' package" on a fresh install.
    """
    assert "huggingface-hub" in _names(project["dependencies"])


def test_pynacl_is_bundled_in_the_ui_extra_for_quillin_signature_verification(
    project: dict,
) -> None:
    """End users must be able to verify publisher-signed Quillins (#919 follow-up).

    PyNaCl was previously dev/CI-only (the [signing]/[dev] extras), so every
    real shipping build -- which installs [ui] -- shipped without it and the
    Quillins Manager always reported "PyNaCl is not installed" instead of
    "verified". The [ui] extra is one of the Windows build's
    DEFAULT_BUNDLED_DEPENDENCY_GROUPS and is installed by the macOS build
    (``pip install -e ".[ui,macos]"``), so listing PyNaCl there is what gets it
    into both shipping builds. Keep it unmarked (no ``sys_platform`` marker) so
    signature verification ships on Windows and macOS alike.
    """
    ui_reqs = project["optional-dependencies"]["ui"]
    assert "pynacl" in _names(ui_reqs)
    # Must NOT carry a win32-only marker -- macOS users verify Quillins too.
    assert not any("win32" in req for req in ui_reqs if "pynacl" in req.lower())


def test_babel_rides_with_the_kokoro_extra(project: dict) -> None:
    """The Kokoro ONNX voice chain imports babel.numbers transitively via csvw.

    Declaring Babel in the [kokoro] extra keeps that runtime chain self-contained
    so a pruned/partial install can't leave the ONNX voice path failing with
    ModuleNotFoundError: No module named 'babel'.
    """
    assert "babel" in _names(project["optional-dependencies"]["kokoro"])


@pytest.mark.parametrize("dist", ["markitdown", "pdfplumber", "pypdf"])
def test_free_import_pipeline_is_the_pdf_ocr_extra(project: dict, dist: str) -> None:
    """The free-first PDF/Office text extractor lives in one named extra.

    #909's original bug was that these packages lived *nowhere* the shipping
    build actually installed -- not in a base dependency, not in the extra a
    clean install pulled. The fix that shipped first made them a base
    dependency (present on every install, whether or not it ever touches a
    PDF); the fix here instead makes the promise "one click away, every
    install" via `quill/core/pdf_ocr_install.py` and Help > Download Optional
    Components, which needs the packages named in exactly one place so the
    installer and the manifest can never drift apart. If this ever fails
    because the packages moved elsewhere, update pdf_ocr_install.py's
    ``_PDF_OCR_REQUIREMENTS`` (and this test's group name) to match.
    """
    assert dist in _names(project["optional-dependencies"]["pdf-ocr"])


def test_free_import_pipeline_is_not_forced_on_every_install(project: dict) -> None:
    """The pdf-ocr packages must NOT be a base dependency (the opposite of #909).

    They are pure-Python and downloadable in one click from Help > Download
    Optional Components (quill/core/pdf_ocr_install.py), so forcing them onto
    every install -- including ones that never touch a PDF or Office
    document -- is no longer the fix; being one click away is.
    """
    base_names = _names(project["dependencies"])
    for dist in ("markitdown", "pdfplumber", "pypdf"):
        assert dist not in base_names


def test_free_import_pipeline_installer_requirements_match_the_extra(project: dict) -> None:
    """quill/core/pdf_ocr_install.py's pinned requirements must track the extra.

    The on-demand installer pins its own requirement strings (so a pip
    install works even if this repo's manifest changes later); this guards
    against the two silently drifting apart.
    """
    from quill.core.pdf_ocr_install import _PDF_OCR_REQUIREMENTS

    extra_names = _names(project["optional-dependencies"]["pdf-ocr"])
    installer_names = _names(list(_PDF_OCR_REQUIREMENTS))
    assert installer_names == extra_names


def test_free_import_pipeline_imports_under_the_shipping_set() -> None:
    """Beyond the manifest, the packages must actually import in the test env.

    Complements the manifest check above: catches the case where a dependency is
    declared but broken/uninstallable on this platform. Skips (rather than fails)
    if the environment genuinely lacks them, so the manifest test stays the hard
    guard while this one confirms real availability where present.
    """
    import importlib.util

    names = ("markitdown", "pdfplumber", "pypdf")
    missing = [m for m in names if importlib.util.find_spec(m) is None]
    if missing:
        pytest.skip(f"not installed in this environment: {', '.join(missing)}")
    import markitdown  # noqa: F401
    import pdfplumber  # noqa: F401
    import pypdf  # noqa: F401


def _marker(req: str) -> str:
    """Return the PEP 508 environment-marker portion of *req* (after ';'), or ''."""
    if ";" in req:
        return req.split(";", 1)[1].strip()
    return ""


def _requirement_strings(project: dict, extra: str | None) -> list[str]:
    """All requirement strings in a named extra, or base dependencies if None."""
    if extra is None:
        return list(project["dependencies"])
    return list(project["optional-dependencies"][extra])


@pytest.mark.parametrize("dist", ["pyobjc", "py2app", "apple-fm-sdk"])
def test_macos_packaging_deps_are_platform_marked_for_darwin(project: dict, dist: str) -> None:
    """macOS-only packaging/runtime deps must carry a `sys_platform == 'darwin'`
    marker so a `pip install .[macos]` on Windows/Linux doesn't pull them.

    Regression guard for the class of drift where py2app/setuptools<83/pyobjc
    were declared bare in the [macos] extra and got installed on every platform,
    polluting non-Mac environments with macOS-only build tooling.
    """
    macos_reqs = _requirement_strings(project, "macos")
    matches = [r for r in macos_reqs if _names([r]) == {dist}]
    assert matches, f"{dist} is not declared in the [macos] extra"
    for req in matches:
        marker = _marker(req)
        assert "darwin" in marker, f"{dist} in [macos] lacks a darwin platform marker: {req!r}"


@pytest.mark.parametrize("dist", ["comtypes", "prismatoid", "accessible-output2"])
def test_windows_only_deps_are_excluded_from_macos_install(project: dict, dist: str) -> None:
    """Windows-only runtime deps must carry a `sys_platform == 'win32'` marker
    (and never appear in the [macos] extra), so a Mac install never pulls them.

    The beta-2 add.md drift bug: Windows-only deps declared without a marker get
    installed on macOS where they're useless (and sometimes fail to build),
    exactly the failure mode this file exists to catch.
    """
    # They must never appear unmarked in the macos extra.
    macos_reqs = _requirement_strings(project, "macos")
    for req in macos_reqs:
        assert _names([r for r in [req]]) != {dist}, (
            f"Windows-only {dist} leaked into the [macos] extra: {req!r}"
        )
    # Wherever they are declared (base or any extra), they must be win32-marked.
    all_reqs: list[str] = list(project["dependencies"])
    for group in project["optional-dependencies"].values():
        all_reqs.extend(group)
    matches = [r for r in all_reqs if _names([r]) == {dist}]
    assert matches, f"{dist} is not declared anywhere in the manifest"
    for req in matches:
        marker = _marker(req)
        assert "win32" in marker, f"Windows-only {dist} is declared without a win32 marker: {req!r}"


def _macos_bundle_includes() -> list[str]:
    """The ``OPTIONS["includes"]`` list from ``scripts/setup_macos.py``, parsed
    statically (the module executes ``setup()`` at import, so it cannot be
    imported in a test)."""
    import ast

    setup_path = pathlib.Path(__file__).resolve().parents[2] / "scripts" / "setup_macos.py"
    tree = ast.parse(setup_path.read_text("utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "OPTIONS":
                assert isinstance(node.value, ast.Dict)
                for key, value in zip(node.value.keys, node.value.values, strict=True):
                    if isinstance(key, ast.Constant) and key.value == "includes":
                        assert isinstance(value, ast.List)
                        return [
                            elt.value
                            for elt in value.elts
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                        ]
    return []


def test_macos_bundle_includes_feedback_hub_for_report_a_bug() -> None:
    """#11: ``feedback_hub`` is imported lazily (function-local) by
    ``quill.core.issue_submit`` / ``quill.core.feedback_token`` /
    ``main_frame.report_bug``, so py2app's import tracer cannot discover it. It
    must be listed explicitly in ``setup_macos.py OPTIONS["includes"]`` or the
    macOS ``.app`` ships without the Report-a-Bug direct-submission dialog -- the
    bundled issues-only token is present, but the library that consumes it is
    absent, so Report a Bug silently falls back to the bare web-link path."""
    includes = _macos_bundle_includes()
    assert "feedback_hub" in includes, (
        "feedback_hub must be in setup_macos.py OPTIONS['includes'] so the macOS "
        ".app bundles the Report-a-Bug dialog (#11); it is imported lazily so "
        "py2app's import tracer cannot find it."
    )
    # nacl is the precedent (same lazy-import reason); keep it as a regression
    # anchor so a future edit doesn't drop either explicit include.
    assert "nacl" in includes


def test_macos_release_workflow_installs_the_feedback_extra() -> None:
    """#11: the ``[feedback]`` extra (``feedback-hub``) must be installed in the
    macOS build and test jobs, or there is nothing for py2app to trace/include."""
    yml = (
        pathlib.Path(__file__).resolve().parents[2] / ".github" / "workflows" / "macos-release.yml"
    ).read_text("utf-8")
    assert ".[ui,spellcheck,macos,feedback,github]" in yml, (
        "macos-release.yml build job must install the [feedback] extra (#11)"
    )
    assert ".[ui,spellcheck,macos,dev,feedback,github]" in yml, (
        "macos-release.yml test job must install the [feedback] extra (#11)"
    )


def test_macos_bundle_includes_github_for_open_from_github() -> None:
    """PyGithub (top-level module ``github``) is imported function-locally by
    ``quill.core.github.github_provider`` (guarded by ``require_pygithub``), so
    py2app's import tracer cannot discover it -- exactly like ``feedback_hub``.
    The File > Open > GitHub Repository... / GitHub File URL... menu items are
    added unconditionally, so without ``github`` in ``OPTIONS["includes"]`` the
    shipped ``.app`` raises ``GitHubDependencyError`` ("pip install
    quill[github]") -- advice that cannot be acted on inside a packaged app."""
    includes = _macos_bundle_includes()
    assert "github" in includes, (
        "github (PyGithub) must be in setup_macos.py OPTIONS['includes'] so the "
        "macOS .app bundles the Open-from-GitHub feature; it is imported lazily "
        "so py2app's import tracer cannot find it."
    )


def test_macos_release_workflow_installs_the_github_extra() -> None:
    """The [github] extra (PyGithub) must be installed in the macOS build and
    test jobs, or there is nothing for py2app to trace/include and the shipped
    .app cannot open documents from GitHub."""
    yml = (
        pathlib.Path(__file__).resolve().parents[2] / ".github" / "workflows" / "macos-release.yml"
    ).read_text("utf-8")
    # Both the build and test install specs end in ",github]".
    assert yml.count(",github]") >= 2, (
        "macos-release.yml build and test jobs must both install the [github] "
        "extra so PyGithub is bundled into the .app"
    )


def test_github_extra_is_bundled_in_the_windows_installer() -> None:
    """The Windows installer pip-installs
    ``DEFAULT_BUNDLED_DEPENDENCY_GROUPS`` into the embedded runtime. ``github``
    must be among them or the installer ships without PyGithub and the
    Open-from-GitHub menu items die the same way the macOS .app did."""
    distribution_script = (
        pathlib.Path(__file__).resolve().parents[2] / "scripts" / "build_windows_distribution.py"
    )
    src = distribution_script.read_text("utf-8")
    groups_line = src.split("DEFAULT_BUNDLED_DEPENDENCY_GROUPS", 1)[1].split(")", 1)[0]
    assert '"github"' in groups_line, (
        "build_windows_distribution.py DEFAULT_BUNDLED_DEPENDENCY_GROUPS must "
        "include 'github' so PyGithub ships in the Windows installer"
    )
