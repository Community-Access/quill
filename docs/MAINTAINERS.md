# QUILL Maintainers

This file describes maintainer responsibilities and operational expectations.

## Named maintainers

| Role | Name | Contact |
|---|---|---|
| Code Maintainer | Jeff Bishop | jeff@jeffbishop.com |

## Maintainer team

- Community Access maintainers (`@Community-Access`)

## Responsibilities

1. Triage issues and guide contributors to the right template/workflow.
2. Review pull requests for correctness, accessibility, and maintainability.
3. Keep release process and documentation current.
4. Enforce `CODE_OF_CONDUCT.md` and `SECURITY.md`.
5. Protect user trust: no silent network behavior, no unsafe defaults.

## Triage and labeling standards

Maintainers should apply both a **type** and an **area** label:

- Type: `bug`, `feature`, `documentation`, `security`
- Area: `accessibility`, `ai`, `intake`, `snippets`, `dictation`, `performance`, `stability`

Priority labels:

- `p0`: release blocker (launch crash, data loss, severe accessibility break)
- `p1`: major workflow break

Triage target: new issues receive an initial maintainer response within 5 business days.

## Review expectations

Maintainers should request changes when a PR:

- introduces accessibility regressions,
- bypasses architecture boundaries from `docs/QUILL-PRD.md`,
- weakens security/privacy constraints,
- omits required tests/checks for changed behavior.

## Availability and handoff

If a maintainer is unavailable, another maintainer should take ownership of:

1. Security reports
2. Release-blocking regressions
3. Accessibility regressions

## Role descriptions

**Code Maintainer** — Reviews and merges pull requests, triages bug reports
and feature requests, cuts releases, enforces code quality gates and CI
requirements, and sets technical direction for the project.

## Related docs

- `CONTRIBUTING.md`
- `GOVERNANCE.md`
- `SECURITY.md`
- `release/RELEASE.md`
