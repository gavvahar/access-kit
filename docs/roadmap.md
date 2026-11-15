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
2. [x] Logging with default scrubbing and request IDs.
3. [x] Privacy helpers and signed anonymous sessions.
4. [x] SSRF-safe fetcher with connect-time IP pinning and regression suite.
5. [x] LLM providers, JSON retry, usage accounting, and reusable testing fakes.

The Phase B library implementation is complete. A consumer-style ASGI test
exercises fetching, typed LLM JSON output, sessions, privacy, request IDs, and
health without live services. All package initializers are empty.

Integration acceptance remains pending: the sibling ClearRead repository is
still a template and has no Phase 1 pipeline to validate. Phase B is accepted
only after ClearRead installs `py-v0.1.0` and runs its
Phase 1 pipeline. The current development version is not that release. No package tag is created
by this implementation.

## Phase C: Web v0.1

1. [x] Shared design tokens, five themes, self-hosted fonts, and base CSS.
2. [x] Validated settings store and `<ak-settings-panel>` with native controls.
3. [x] Announcements, wake locks, opt-in vibration, and safe storage utilities.
4. [x] Demo, unit tests, browser keyboard/mobile tests, and axe checks in CI.
5. [ ] Consuming-app acceptance: SoundSight's first screen and ClearRead's reader
       must use the same package. Those screens are not present in the current
       workspace; the existing ClearRead checkout remains a template.

Phase C library implementation is complete; app integration acceptance is pending.
No `web-v0.1.0` tag is created. See [web usage](../web/README.md).

## Later phases

1. Phase D: rate limits, Turnstile, budgets, and notifications.
2. Phase E: job progress, SSE, and ADHD components.
3. Phase F: stable APIs, complete module docs, and public package publishing.
