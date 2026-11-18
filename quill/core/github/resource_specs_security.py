"""Security lists for the resource engine: code scanning's analyses and databases, and an
organization's code scanning alerts.

Split from :mod:`quill.core.github.resource_specs` to keep each module under the size
budget; that module adds these to ``RESOURCE_SPECS``. wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.resource_engine import ResourceSpec
from quill.core.github.sheet_fields import dig

__all__ = ["SECURITY_SPECS"]

_REPO_SETTINGS = "https://github.com/{target}"


def _day(raw: Mapping[str, Any], key: str) -> str:
    return str(raw.get(key) or "")[:10]


def _count(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def _size(size: int) -> str:
    amount = float(size)
    for unit in ("bytes", "KB", "MB"):
        if amount < 1024:
            return f"{int(amount)} bytes" if unit == "bytes" else f"{amount:.1f} {unit}"
        amount /= 1024
    return f"{amount:.1f} GB"


def _severity(raw: Mapping[str, Any]) -> str:
    rule = raw.get("rule")
    if not isinstance(rule, Mapping):
        return "no severity"
    return str(rule.get("security_severity_level") or rule.get("severity") or "no severity")


SECURITY_SPECS: tuple[ResourceSpec, ...] = (
    ResourceSpec(
        key="code_scanning_analyses",
        label="Code Scanning Analyses",
        scope="repository",
        parent="security",
        noun="analysis",
        list_path="{base}/code-scanning/analyses",
        id_field="id",
        id_param="{analysis_id}",
        sentence=lambda raw: (
            f"{dig(raw, 'tool', 'name') or 'A tool'} on {raw.get('ref') or 'a branch'}, "
            f"{_day(raw, 'created_at') or 'at an unknown time'}: "
            f"{_count(int(raw.get('results_count') or 0), 'result', 'results')}"
            + (f", {raw.get('error')}" if raw.get("error") else "")
            + "."
        ),
        help=(
            "Code Scanning Analyses: each upload of results, newest first. Deleting one "
            "removes its results; GitHub refuses the last analysis of a tool unless asked."
        ),
        page=f"{_REPO_SETTINGS}/security/code-scanning",
    ),
    ResourceSpec(
        key="codeql_databases",
        label="CodeQL Databases",
        scope="repository",
        parent="security",
        noun="database",
        list_path="{base}/code-scanning/codeql/databases",
        id_field="language",
        id_param="{language}",
        sentence=lambda raw: (
            f"{raw.get('language')}: built {_day(raw, 'created_at') or 'at an unknown time'}, "
            f"{_size(int(raw.get('size') or 0))}."
        ),
        help="CodeQL Databases: the databases code scanning built, one per language.",
        page=f"{_REPO_SETTINGS}/security/code-scanning",
    ),
    ResourceSpec(
        key="org_code_scanning_alerts",
        label="Code Scanning Alerts",
        scope="organization",
        parent="organization",
        noun="alert",
        list_path="{base}/code-scanning/alerts",
        id_field="number",
        id_param="{alert_number}",
        sentence=lambda raw: (
            f"{dig(raw, 'repository', 'full_name') or 'A repository'}: "
            f"{dig(raw, 'rule', 'description') or dig(raw, 'rule', 'id') or 'an alert'}, "
            f"{_severity(raw)}, "
            f"{raw.get('state') or 'open'}."
        ),
        help=(
            "Code Scanning Alerts: every repository's code scanning alerts in one list. "
            "Open a repository's Alerts to dismiss one."
        ),
        page="https://github.com/orgs/{target}/security/alerts/code-scanning",
        delete=False,
    ),
)
