# QUILL Governance

This document defines how project-level decisions are made for QUILL.

## Governance model

QUILL uses a maintainer-led model with community input:

1. Contributors propose changes through issues and pull requests.
2. Maintainers review for architecture, accessibility, safety, and release fit.
3. Maintainers make final merge and roadmap decisions.

## Decision priorities

When trade-offs are necessary, QUILL prioritizes:

1. Accessibility and reliability
2. User safety and data protection
3. Predictable keyboard-first workflows
4. Maintainability and testability
5. Feature depth

## Roles

- **Maintainers**: approve/reject changes, manage releases, enforce quality bars.
- **Contributors**: propose and implement changes following repository standards.
- **Users/reporters**: provide issues, diagnostics, and workflow feedback.

## Proposals and design changes

Use a GitHub issue for non-trivial changes and include:

1. Problem statement and user impact
2. Proposed behavior
3. Accessibility impact
4. Risks and migration concerns

Large cross-cutting changes should be discussed before implementation.

## Review and approval

- Every PR requires maintainer review.
- Changes touching accessibility-critical areas should include explicit accessibility notes.
- Security-sensitive changes should reference `SECURITY.md`.
- `main` is branch-protected with required checks and review gates; admin bypass is retained for emergency operations.

## Conflict resolution

Maintainers aim for consensus through issue discussion. When consensus is not
reached, maintainers make a final call aligned with QUILL's product direction.

## Conduct and enforcement

Community behavior is governed by `CODE_OF_CONDUCT.md`.
