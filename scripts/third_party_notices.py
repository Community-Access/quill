from __future__ import annotations

import argparse
from pathlib import Path

from quill.core.compliance import (
    build_dependency_notices,
    render_full_third_party_notices,
)

DEFAULT_ALLOWED_LICENSES = {
    "Apache-2.0",
    "Apache-2.0 AND CNRI-Python",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "ISC",
    "LGPL",
    "LGPL-2.1-or-later",
    "MIT",
    "MPL-2.0",
    "PSF-2.0",
    "wxWindows",
    "wxWindows Library License (https://opensource.org/licenses/wxwindows.php)",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate third-party notices and enforce license gate."
    )
    parser.add_argument("--pyproject", type=Path, default=Path("pyproject.toml"))
    parser.add_argument("--output", type=Path, default=Path("docs/legal/THIRD_PARTY_NOTICES.txt"))
    parser.add_argument("--project-root", type=Path, default=Path("."))
    args = parser.parse_args()

    notices = render_full_third_party_notices(
        args.pyproject,
        args.project_root,
    )
    args.output.write_text(notices, encoding="utf-8")
    dependency_rows = build_dependency_notices(
        args.pyproject,
        include_optional=True,
        include_dev=True,
        include_build=True,
    )
    violations = [
        row["dependency"]
        for row in dependency_rows
        if not row["license"].strip() or row["license"].strip() not in DEFAULT_ALLOWED_LICENSES
    ]
    if violations:
        print(f"License gate failed for: {', '.join(violations)}")
        return 1
    print(f"Wrote {args.output} ({len(dependency_rows)} dependencies)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
