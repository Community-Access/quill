from __future__ import annotations

import quill.core.publishing_clients as publishing_clients
from quill.core.publishing_providers import (
    AUTH_METHOD_APP_PASSWORD,
    PUBLISHING_OPERATION_VERIFY,
    PublishingProviderDefinition,
    register_publishing_provider,
    unregister_publishing_provider,
)
from quill.core.publishing_validation import PublishingProviderValidationIssue
from quill.tools import check_publishing_providers as gate


class _VerifyOnlyClient:
    provider_id = "verifyonly"

    def verify_connection(self, *_args, **_kwargs):
        return True, "Verified."


def _register_verify_only_provider() -> None:
    register_publishing_provider(
        PublishingProviderDefinition(
            id="verifyonly",
            name="Verify Only",
            help_text="Provider gate fixture.",
            default_content_format="html",
            supported_auth_methods=(AUTH_METHOD_APP_PASSWORD,),
            implemented_auth_methods=(AUTH_METHOD_APP_PASSWORD,),
            supported_content_kinds=("article",),
            implemented_content_kinds=("article",),
            supported_operations=(PUBLISHING_OPERATION_VERIFY,),
            implemented_operations=(PUBLISHING_OPERATION_VERIFY,),
            content_kind_labels={"article": "Article"},
            content_kind_plural_labels={"article": "Articles"},
        )
    )


def test_format_validation_issues_reports_clean_registry() -> None:
    assert gate.format_validation_issues(()) == "Publishing provider/client registry is valid."


def test_format_validation_issues_lists_provider_messages() -> None:
    text = gate.format_validation_issues((
        PublishingProviderValidationIssue("example", "Example issue."),
    ))

    assert text.splitlines() == [
        "Publishing provider/client registry has validation issues:",
        "- example: Example issue.",
    ]


def test_main_returns_zero_for_builtin_registry(capsys) -> None:
    assert gate.main() == 0
    assert "registry is valid" in capsys.readouterr().out


def test_main_returns_nonzero_for_provider_without_client(capsys) -> None:
    _register_verify_only_provider()
    try:
        result = gate.main()
    finally:
        unregister_publishing_provider("verifyonly")

    assert result == 1
    assert "Verify Only publishing provider has no registered client" in capsys.readouterr().out


def test_main_returns_nonzero_for_client_without_provider(capsys) -> None:
    publishing_clients.register_publishing_provider_client(_VerifyOnlyClient())
    try:
        result = gate.main()
    finally:
        publishing_clients.unregister_publishing_provider_client("verifyonly")

    assert result == 1
    assert (
        "verifyonly publishing client has no registered provider definition"
        in capsys.readouterr().out
    )
