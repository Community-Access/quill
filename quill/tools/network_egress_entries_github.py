"""Reviewed direct HTTP calls for the shared QUILL/Lite GitHub workbench."""

from __future__ import annotations

GITHUB_WORKBENCH_EGRESS: dict[str, str] = {
    "core/github/discussions.py::_request": (
        "Explore's Repository Discussions view reads a bounded page of discussion "
        "titles, categories, authors, answered state, and capped plain-text bodies "
        "from the explicitly selected repository using GitHub GraphQL. The signed-in "
        "account token is sent to the fixed api.github.com/graphql endpoint; no local "
        "document content is sent. Results are limited to 100, with visible partial "
        "page status. The read occurs only after the user opens Explore and loads the "
        "Discussions view; redirects are refused, verified TLS and 20-second timeouts "
        "apply, and Safe Mode blocks the entry."
    ),
    "core/github/explore.py::_api_get": (
        "Explore GitHub's Pages view: reads the selected repository's Pages site "
        "and build history from api.github.com after an explicit view/load action. "
        "Sends the repository path and, when signed in, the user's GitHub bearer "
        "token in the Authorization header; receives site metadata and build "
        "status JSON. No document content is sent. This child view is reachable "
        "only from the GitHub Items entry point, after its shared network consent "
        "and Safe Mode refusal. HTTPS with the system-store verified TLS context "
        "and a 20-second timeout. No launch-time or scheduled requests."
    ),
    "core/github/review_graphql.py::_request": (
        "The PR review outline reads paginated thread state when a user opens or "
        "refreshes a PR; Resolve/Reopen changes one selected review thread only "
        "after the review action's confirmation. Sends a GraphQL query/mutation "
        "and owner/repository/PR number, page cursor, or thread node ID to the "
        "fixed api.github.com/graphql endpoint, with the signed-in user's token "
        "in the Authorization header. Receives resolution/permission/line state, "
        "merge-queue and auto-merge status, and the exact pull request head SHA; "
        "confirms the mutation result and sends no document content. Reachable "
        "through the GitHub viewer's shared network consent and Safe Mode gate, "
        "never at launch or on a schedule. HTTPS over the system-store verified "
        "TLS context with a 20-second timeout."
    ),
    "core/github/project_transport.py::request_graphql": (
        "The GitHub Items Projects and Dependencies dialog reads repository Projects v2 boards, "
        "project fields/items, issue blockers, and sub-issues only after the user opens or "
        "refreshes that dialog. Explicitly confirmed field and issue-relationship changes send "
        "only the selected project/issue IDs and field value to the fixed api.github.com/graphql "
        "endpoint. The signed-in token is sent in the Authorization header. HTTPS uses verified "
        "system-store TLS, 20-second timeouts, and redirects are refused so credentials cannot "
        "be forwarded. No local document content is sent; no background or scheduled requests."
    ),
    "core/github/workflow_job_logs.py::fetch_job_log": (
        "Workflow Jobs' explicit Load Log button or job double-click downloads "
        "the selected job's plain-text log. Sends owner/repository/job ID to "
        "api.github.com and an optional signed-in bearer token in the header. "
        "The first request refuses automatic redirects; a returned signed HTTPS "
        "log URL is fetched separately with no Authorization header, so GitHub "
        "credentials do not travel to its other-host redirect target. Receives "
        "UTF-8 text, bounded to 4 MB and visibly marked if truncated. No local "
        "document or file content is sent. The dialog is reached only through "
        "the GitHub viewer after network consent and Safe Mode refusal. Verified "
        "system-store TLS, 30-second timeouts; no silent polling or scheduling."
    ),
}
