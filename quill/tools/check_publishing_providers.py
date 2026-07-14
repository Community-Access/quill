"""Publishing provider/client contract gate.

This tool keeps provider metadata and provider clients synchronized while the
publishing framework is still in-tree. It intentionally validates only the
registered in-process providers; it does not load third-party Quillins or expose
publishing provider extension loading.
"""

from __future__ import annotations

from collections.abc import Iterable

from quill.core.publishing_validation import (
    PublishingProviderValidationIssue,
    validate_registered_publishing_provider_clients,
)


def format_validation_issues(
    issues: Iterable[PublishingProviderValidationIssue],
) -> str:
    rows = tuple(issues)
    if not rows:
        return "Publishing provider/client registry is valid."
    lines = ["Publishing provider/client registry has validation issues:"]
    lines.extend(f"- {issue.provider_id}: {issue.message}" for issue in rows)
    return "\n".join(lines)


def main() -> int:
    issues = validate_registered_publishing_provider_clients()
    print(format_validation_issues(issues))
    return 1 if issues else 0


if __name__ == "__main__":  # pragma: no cover - exercised through main()
    raise SystemExit(main())
