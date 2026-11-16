# Implementation status

Based on `/home/nihar.gavva/Nextcloud/access-kit-plan.md`.
The older Python design and implementation plan under `superpowers/` are reference
material; their scaffold paths and release workflow descriptions are superseded
by the current repository layout.

## Phase A: scaffold

1. [x] Independent `python/` and `web/` package manifests and source layouts.
2. [x] Test, type-check, formatting, build, and pre-commit configuration.
3. [x] README, MIT license, security policy, and contributor instructions.
4. [x] Public repository with private vulnerability reporting, secret scanning,
       push protection, and Dependabot alerts enabled.

## Phase B: Python v0.1

1. [x] Extensible validated settings; health endpoint with pluggable checks.
2. [x] Logging with default scrubbing and request IDs.
3. [x] Privacy helpers and signed anonymous sessions.
4. [x] SSRF-safe fetcher with connect-time IP pinning and regression suite.
5. [x] LLM providers, JSON retry, usage accounting, and reusable testing fakes.

The Phase B library implementation is complete. A consumer-style ASGI test
exercises fetching, typed LLM JSON output, sessions, privacy, request IDs, and
health without live services. All package initializers are empty.

The ClearRead integration now implements a real extraction/provider/reader path
initially using `py-v1.0.0`, which supersedes the unreleased v0.1 milestone. The consuming
app tests cover the shared SSRF cases and actual endpoint composition. See
[consumer acceptance evidence](acceptance-v1.md). Both integration PRs are merged.

## Phase C: Web v0.1

1. [x] Shared design tokens, five themes, self-hosted fonts, and base CSS.
2. [x] Validated settings store and `<ak-settings-panel>` with native controls.
3. [x] Announcements, wake locks, opt-in vibration, and safe storage utilities.
4. [x] Demo, unit tests, browser keyboard/mobile tests, and axe checks in CI.
5. [x] Both real consumer screens use the exact same `web-v1.0.1` package,
       including themes, settings, fonts and shared activity components.

The browser acceptance suites pass in both consumer apps. The initial public
package tag is `web-v1.0.1`, superseding the unreleased v0.1 milestone. See [web usage](../web/README.md).

## Phase D: protection

1. [x] Redis Lua weighted sliding limits and fail-closed FastAPI dependency.
2. [x] Server-validated Turnstile with hostname/action binding.
3. [x] Atomic daily reserve/commit/release, idempotency and threshold snapshots.
4. [x] ntfy, signed webhooks and TLS email notifications.
5. [x] Real Redis load check: each of token/minute caps admits 33 of 1,000
       requests across four independent clients (99 used against a cap of 100).

The library load criterion passes. Application-wide enforcement still depends on
apps bounding every provider attempt and dispatching only after reservation.
See [protection contracts](protection.md); no live paid-provider load was run.

## Phase E: jobs and web activities

1. [x] Owner-scoped Redis progress, monotonic transitions and terminal states.
2. [x] SSE snapshots, bounded replay, Last-Event-ID, heartbeats and disconnects.
3. [x] `<ak-progress>`, `<ak-session>`, `<ak-celebrate>` and DOM-free controllers.
4. [x] Demo plus keyboard, timer, narrow-screen and five-theme axe coverage.
5. [x] Both apps display actual background-job progress and use the same session
       component; browser tests verify pause/completion in their real screens.

## Phase F: stable release

1. [x] Guides for every module and public API inventory.
2. [x] Architecture decisions and independent package version policy.
3. [x] Local package builds and publication review checklist.
4. [x] API review and independent v1 manifests; compatibility rules are now frozen.
5. [x] Registry uploads: npm `@exchange2302/access-kit-ui@1.0.1` and PyPI
       `gavvahar-access-kit@1.0.1` are public; fresh registry installs are verified.

All six phases of the shared-library plan are complete: implementation, consumer
acceptance, and verified public Python/npm publication.
The repository is public and v1 manifests identify Python and web `1.0.1`. A separate manual
publisher supports checked artifacts and trusted registry identities. Both registry
uploads are complete. Existing snapshot release
automation keeps its original behavior. See [release readiness](releasing-packages.md).

See [the acceptance record](acceptance-v1.md) for exact test counts, consumer PRs,
publication attempts and the boundaries of the app integration work.
