"""Importing quill must undo package-dir sys.path shadowing of the stdlib.

When ``quill/__main__.py`` is run as a script (a relaunch that reused
``sys.argv[0]``, a manual ``python quill/__main__.py``), Python puts the
package directory itself at ``sys.path[0]``. There, ``quill/platform``
shadows the stdlib ``platform`` module, and the app dies in ``_build_menu``
with ``AttributeError: module 'platform' has no attribute 'system'``.
``quill/__init__`` repairs the path entry so stdlib names resolve normally.
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_quill_import_recovers_stdlib_platform_when_package_dir_leads_sys_path() -> None:
    code = (
        "import sys\n"
        f"sys.path.insert(0, {str(REPO_ROOT / 'quill')!r})\n"
        "import quill\n"
        "import platform\n"
        "print(platform.system())\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip(), "platform.system() returned nothing"
