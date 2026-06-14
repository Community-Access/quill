"""py2app build configuration for the macOS Quill app.

Usage (run from the repository root):
    pip install -e ".[ui,macos]"
    python scripts/setup_macos.py py2app
    ./scripts/build_macos.sh          # sign + notarize + DMG

Produces dist/Quill.app.
"""

import sys
from pathlib import Path

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
    # in build_macos.sh reaches them.
    "packages": ["quill", "PIL"],
    "includes": ["wx"],
    "plist": {
        "CFBundleName": APP_DISPLAY_NAME,
        "CFBundleDisplayName": APP_DISPLAY_NAME,
        "CFBundleIdentifier": BUNDLE_IDENTIFIER,
        "CFBundleShortVersionString": __version__,
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
