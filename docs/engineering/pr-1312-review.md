# Review record — PR #1312 (environment API key fallback)

Reviewed 2026-08-07 against main `9810e81`. PR: external contribution from
`salorajan`, +131/-28 across 6 files, opened 2026-08-03.
Verdict: **request changes; not a 1.0.0 blocker — target 1.0.1.**

## What the PR does

Makes environment variables (`OPENAI_API_KEY`, `GEMINI_API_KEY` /
`GOOGLE_API_KEY`, `ANTHROPIC_API_KEY` / `CLAUDE_API_KEY`,
`OPENROUTER_API_KEY`, plus a generic `{PROVIDER}_API_KEY`) a last-resort key
source: `load_provider_api_key()` and `load_assistant_api_key()` consult the
credential store / DPAPI first and fall back to the environment only when
storage is empty. Migration (`consolidate_provider_keys`) is re-pointed at
storage-only internals so env keys are never migrated into persistent
storage, and an autouse test fixture clears the named env vars suite-wide.

The precedence design is sound, and isolating migration from env-sourced
keys is exactly the subtlety most contributions would miss.

## Defect (must fix)

- `quill/ui/assistant_tools.py:1353` prefills the editable key field with
  `load_provider_api_key(provider)`. With the fallback, an env-sourced key
  appears in that field and Save persists it to the credential store —
  defeating the migration guard by another road. Same risk at
  `ai_hub_dialog.py:143`. The load path must distinguish "stored" from
  "ambient" for UI purposes (a `provider_key_source()` helper, or prefill
  from `_cs_load` directly and label "using environment key").

## Policy decisions required (product-level)

- **Ambient authorization.** Key presence is treated as "configured"
  (`onboarding.py:417`, the setup wizard). An env var set by an unrelated
  tool would make a cloud provider silently ready to send data. Given
  QUILL's consent-first egress posture, gate the fallback behind an explicit
  setting, or at minimum announce "using OPENAI_API_KEY from the
  environment" in the AI Hub.
- **Harness cross-contamination.** `harness_credentials.
  apply_all_stored_keys()` exports agent-pack keys to `OPENAI_API_KEY` /
  `ANTHROPIC_API_KEY` at startup, so storing a key for the Claude Agent SDK
  pack would implicitly configure the claude chat provider too. A coupling
  nobody opted into.

## Correctness details

- Env values returned unstripped; stored keys are stripped everywhere else.
  Add `.strip()`.
- `load_assistant_api_key()` now falls through to env even when
  `assistant_secret_unlock_failed()` — partially masks the L-5
  wrong-Windows-user UX contract; should be a conscious choice.
- No guard for non-cloud providers: `provider="ollama"` picks up a stray
  `OLLAMA_API_KEY`; `"off"` looks up `OFF_API_KEY`. Restrict the fallback to
  `_CLOUD_PROVIDERS`.
- Alias branches ("google", "anthropic") are dead given
  `_SUPPORTED_PROVIDERS`; the generic lookup re-checks names the specific
  branch already checked. A dict table matching `harness_credentials.
  _ENV_VARS` convention would halve the function.

## Tests

- Present: precedence (env used when store empty; store wins once
  populated); suite-wide env clearing fixture.
- Missing: the key test — that `consolidate_provider_keys()` does NOT
  persist env keys; `load_keyed_provider_api_key` with env fallback; the
  unlock-failed + env case. The autouse fixture misses generic-pattern vars
  (e.g. `OLLAMA_CLOUD_API_KEY`); derive the list from the provider table.

## Mechanical

- `assistant_ai.py` / `key_migration.py` have not drifted since 08-03, but
  `module_size_budgets.json` has 6 commits since — the budget hunk will
  conflict and the 1459 -> 1513 number needs recomputing after rebase.
- The PR body cites #1197 (the UnicodeMath equation dialog PR) as the source
  of the concern — wrong reference.
- Crash-report redaction unaffected: crash bundles do not capture
  `os.environ`.
