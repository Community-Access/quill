# Security Policy

## Supported versions

Security fixes are prioritized on the latest release line in `main`.

| Version line | Security support |
| --- | --- |
| Current release (`main`) | Supported |
| Older releases | Best effort only |

## Reporting a vulnerability

Please report suspected vulnerabilities privately. Do **not** open a public
issue for security problems.

- Email: <support@communityaccess.org>
- Subject: `QUILL security report`

If your report includes sensitive details, note that in the subject/body and we
will coordinate a safer exchange path.

Include the following details:

1. A description of the issue and impact.
2. Reproduction steps or proof of concept.
3. Affected version/commit.
4. Any suggested mitigation.
5. Whether you believe this is remotely exploitable or local-only.

## Response expectations

Target response windows:

- Acknowledgement: within 3 business days.
- Initial triage: within 7 business days.
- Follow-up cadence: at least weekly until resolution or mitigation.
- Coordinated disclosure: agreed after fix readiness.

Please do not disclose the issue publicly until maintainers confirm a fix and
disclosure plan.

## Scope guidance

Security reports are most useful when they involve:

- Unauthorized access to protected data
- Privilege escalation
- Remote code execution paths
- Unsafe network or update trust behavior
- Secret exposure in logs, diagnostics, or crash artifacts

Out-of-scope examples (generally):

- Purely theoretical findings without a plausible exploit path
- Reports that require unrealistic local setup not used by QUILL users
- Best-practice suggestions without a concrete vulnerability

## Safe harbor for good-faith research

We support good-faith security research intended to improve user safety.
Please:

1. Avoid privacy violations, destructive testing, or service disruption.
2. Test only what is necessary to demonstrate the issue.
3. Keep findings private until coordinated disclosure is agreed.

If you follow these expectations in good faith, we will treat your research as
authorized for this policy's purposes.

## Security expectations for contributors

All contributors should follow these baseline practices:

1. Never commit secrets, tokens, credentials, or private keys.
2. Avoid logging document content or sensitive user data.
3. Keep networked behavior explicit and user-initiated.
4. Validate external input and fail safely.
5. Use dependency updates intentionally and review changelogs for risk.
6. Keep cloud endpoints on HTTPS; allow HTTP only for local-only runtimes.
7. Ensure diagnostics and logs redact API keys, bearer tokens, and equivalent secrets.

Related project docs:

- `CONTRIBUTING.md`
- `CODE_OF_CONDUCT.md`
- `PRIVACY.md`
- `RESPONSIBLE_AI_USE.md`

## Secret handling baseline

QUILL stores AI API keys in Windows Credential Manager when available. If
Credential Manager is unavailable, QUILL falls back to DPAPI-encrypted local
storage. Plaintext API key storage is not permitted.

## Security automation baseline

- `.github/workflows/security-ci.yml` runs dependency audit, secret scanning, and SBOM generation.
- `.github/workflows/windows-release.yml` publishes release metadata plus SBOM artifacts.
