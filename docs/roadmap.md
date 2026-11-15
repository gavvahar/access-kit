# Implementation status

Based on `/home/nihar.gavva/Nextcloud/access-kit-plan.md`.
The older Python design and implementation plan under `superpowers/` are reference
material; their scaffold paths and release workflow descriptions are superseded
by the current repository layout.

## Phase A: scaffold

1. [x] Independent `python/` and `web/` package manifests and source layouts.
2. [x] Test, type-check, formatting, build, and pre-commit configuration.
3. [x] README, MIT license, security policy, and contributor instructions.
4. [ ] Owner: enable private vulnerability reporting, secret scanning, and alerts.

## Phase B: Python v0.1

1. [x] Extensible validated settings; health endpoint with pluggable checks.
2. [ ] Logging with default scrubbing and request IDs.
3. [ ] Privacy helpers and signed anonymous sessions.
4. [ ] SSRF-safe fetcher with connect-time IP pinning and regression suite.
5. [ ] LLM providers, JSON retry, usage accounting, and reusable testing fakes.

Phase B is complete only after ClearRead installs `py-v0.1.0` and runs its
Phase 1 pipeline. The current development version is not that release.

## Later phases

1. Phase C: design tokens, five themes, self-hosted fonts, settings panel,
   utilities, demo, and axe checks.
2. Phase D: rate limits, Turnstile, budgets, and notifications.
3. Phase E: job progress, SSE, and ADHD components.
4. Phase F: stable APIs, complete module docs, and public package publishing.
