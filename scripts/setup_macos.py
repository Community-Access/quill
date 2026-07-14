"""py2app build configuration for the macOS Quill app.

Usage (run from the repository root):
    pip install -e ".[ui,macos]"
    python scripts/setup_macos.py py2app
    ./scripts/build_macos.sh          # sign + notarize + DMG

Produces dist/Quill.app.
"""

import sys
from pathlib import Path

# py2app bundles whatever interpreter runs this build, so the build Python *is*
# the app's Python. QUILL's source uses PEP 695 generics (e.g. ``def name[T]``
# in quill/core/storage.py and versioned_store.py) that only parse on 3.12+, and
# pyproject requires >=3.12. Building on 3.11 produced a bundle that raised a
# SyntaxError on the first QUILL import and hung on py2app's error screen (#755).
# Abort loudly here so a too-old interpreter can never ship that bundle again.
# noqa rationale: UP036 assumes the running Python is >= the project's 3.12
# target, but this guards the *build* interpreter, which can be an older 3.11.
if sys.version_info < (3, 12):  # noqa: UP036
    raise SystemExit(
        "QUILL's macOS app must be built with Python 3.12 or newer "
        f"(py2app bundles the interpreter it runs under; this is "
        f"{sys.version_info.major}.{sys.version_info.minor}). QUILL's source uses "
        "PEP 695 generics a 3.11 bundle cannot parse, so the app would crash on "
        "launch (#755). Re-run with Python 3.12+."
    )

# This build script lives in scripts/ (build tooling, deliberately outside the
# bundled `quill` package), yet it imports the first-party `quill` package and
# points py2app at the in-package macOS entry point. Running it as
# `python scripts/setup_macos.py py2app` puts scripts/ — not the repo root — on
# sys.path[0], so add the repo root explicitly to keep `import quill` resolving
# regardless of the working directory.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# py2app's finalize_options aborts the build if the distribution carries
# install_requires, which modern setuptools auto-populates from pyproject.toml's
# [project.dependencies]. The .app bundles its own dependencies, so clear it
# right before py2app's own check runs. (Also build with setuptools < 80.)
import py2app.build_app as _py2app_build_app
from setuptools import setup

from quill import __version__
from quill.build_info import get_short_version

_orig_py2app_finalize = _py2app_build_app.py2app.finalize_options


def _py2app_finalize_no_install_requires(self):  # type: ignore[no-untyped-def]
    self.distribution.install_requires = None
    _orig_py2app_finalize(self)


_py2app_build_app.py2app.finalize_options = _py2app_finalize_no_install_requires

from quill.platform.macos.shell_integration import (
    APP_DISPLAY_NAME,
    BUNDLE_IDENTIFIER,
    document_types_plist,
)

APP = [str(_REPO_ROOT / "quill" / "platform" / "macos" / "macos_app.py")]

OPTIONS = {
    "argv_emulation": False,
    # Packages listed here are copied into the bundle as real directory trees
    # rather than packed into python311.zip. Pillow (PIL) ships native
    # ``.dylibs`` (libjpeg, libfreetype, libwebp, ...); inside the zip those
    # dylibs cannot be code-signed, which fails notarization. Keeping PIL
    # unzipped puts them in ``PIL/.dylibs/`` where the inside-out signing pass
    # in build_macos.sh reaches them. protobuf ships the native
    # ``google/_upb/_message.abi3.so`` for the same reason, but ``google`` is a
    # PEP 420 namespace package (no ``__init__.py``) that py2app's package
    # finder cannot resolve, so it cannot be listed here. build_macos.sh instead
    # lifts any native binary out of python311.zip before signing.
    "packages": ["quill", "PIL"],
    # nacl (PyNaCl) is imported lazily/function-locally by quill.tools.signing
    # (and under TYPE_CHECKING only), so py2app's import tracer can miss it --
    # list it explicitly so the macOS build bundles Quillin signature
    # verification (see pyproject [ui] / requirements.txt). nacl ships a
    # native libsodium binding (cffi); if notarization fails on its .so,
    # build_macos.sh's native-binary-out-of-zip lift (the protobuf path)
    # should cover it -- verify on a real build.
    # PyObjC (objc + AppKit/Foundation) is imported lazily too -- inside
    # _AppKitBridge.__init__ (quill/ui/nstextview_rtf_surface.py, the macOS
    # rich text bridge), _pin_macos_editor_accessibility_role (the #616
    # VoiceOver role pin), and the macOS clipboard-collector change counter --
    # so the tracer misses all of it. List it explicitly so rich RTF/Word
    # editing works out of the box on the Mac with nothing for the user to
    # install (and so the VoiceOver role pin actually ships; a missed AppKit
    # made it a silent no-op in the .app). The pyobjc wheel is installed by
    # macos-release.yml via the [macos] extra.
    # feedback_hub is imported lazily/function-locally by
    # quill.core.issue_submit / quill.core.feedback_token / main_frame.report_bug,
    # so the tracer misses it too -- list it explicitly so the macOS build
    # bundles the Report-a-Bug direct-submission dialog (#11; the [feedback]
    # extra is installed in macos-release.yml). Without this, a Mac .app falls
    # back to the bare web-link path even though the bundled token is present.
    # PyGithub (top-level module `github`) is imported function-locally by
    # quill.core.github.github_provider, guarded by require_pygithub(). The
    # File > Open > GitHub Repository... menu item is always shown, so without
    # bundling PyGithub the shipped .app raises GitHubDependencyError ("pip
    # install quill[github]") -- useless advice inside a packaged app. List it
    # explicitly and install the [github] extra in macos-release.yml so the
    # feature actually works in the DMG.
    "includes": ["wx", "nacl", "github", "feedback_hub", "objc", "AppKit", "Foundation"],
    "plist": {
        "CFBundleName": APP_DISPLAY_NAME,
        "CFBundleDisplayName": APP_DISPLAY_NAME,
        "CFBundleIdentifier": BUNDLE_IDENTIFIER,
        "CFBundleShortVersionString": get_short_version(),
        "CFBundleVersion": __version__,
        "LSMinimumSystemVersion": "12.0",
        "NSHighResolutionCapable": True,
        "CFBundleDocumentTypes": document_types_plist(),
        "NSMicrophoneUsageDescription": "Quill uses the microphone for dictation.",
    },
}

setup(
    app=APP,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
