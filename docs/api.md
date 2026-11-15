# Public API and compatibility

This inventory defines the intended v1 contract. Current manifests remain
`0.1.0.dev0` (Python) and `0.1.0-dev.0` (web); they are not accepted v1 releases.
Package initializers stay empty. Import the defining Python module, not the
package root. Underscore modules and undocumented helpers are internal.

## Python surface

| Module               | Supported exports                                                                                    | Guide                                                          |
| -------------------- | ---------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| `settings`           | `AccessKitSettings`                                                                                  | [Core usage](../python/README.md#settings)                     |
| `health`             | `health_router`                                                                                      | [Readiness](../python/README.md#health)                        |
| `logging`            | `setup_logging`, `scrub_logs`, `request_id_middleware`, `get_request_id`                             | [Logging](../python/README.md#logging-and-request-ids)         |
| `privacy`            | `canonical_ip`, `client_ip`, `hash_ip`                                                               | [Privacy](../python/README.md#privacy-and-anonymous-sessions)  |
| `session`            | `sign_session`, `verify_session`, `session_middleware`, `get_session_id`, `rotate_session`           | [Sessions](../python/README.md#privacy-and-anonymous-sessions) |
| `safe_fetch.fetcher` | `make_fetcher`, `FetchResult`                                                                        | [Safe fetching](../python/README.md#safe-fetching)             |
| `safe_fetch.errors`  | `FetchError`, `BlockedDestination`, `TooLarge`, `BadContentType`, `TooManyRedirects`, `FetchTimeout` | Same guide                                                     |
| `llm.factory`        | `provider_from_settings`                                                                             | [LLM usage](../python/README.md#llm-providers-and-strict-json) |
| `llm.providers`      | `anthropic_provider`, `openai_compat_provider`                                                       | Same guide                                                     |
| `llm.core`           | `build_provider`, `with_fallback`                                                                    | Same guide                                                     |
| `llm.types`          | `Usage`, `usage`, `add_usage`, `LLMProvider`, `LLMError`, `LLMValidationError`, `LLMFallbackError`   | Same guide                                                     |
| `ratelimit`          | `make_limiter`, `rate_limit_dependency`, `Limiter`, `LimitResult`                                    | [Protections](protection.md#weighted-rate-limits)              |
| `turnstile`          | `make_turnstile_verifier`, `require_turnstile`                                                       | [Bot checks](protection.md#turnstile)                          |
| `budget`             | `make_budget`, `Budget`, `Reservation`, `BudgetState`, `BudgetExceeded`, `BudgetOverrun`             | [Accounting](protection.md#daily-budgets)                      |
| `notify`             | `Notifier`, `ntfy_notifier`, `webhook_notifier`, `email_notifier`, `combine_notifiers`               | [Delivery](protection.md#notifications)                        |
| `jobs`               | `make_jobs`, `job_response`, `Jobs`, `Job`                                                           | [Progress](jobs.md)                                            |
| `errors`             | `StorageUnavailable`, `ServiceUnavailable`                                                           | Sanitized boundary exceptions; fail closed on admission errors |
| `testing.fakes`      | `fake_llm`, `LLMCall`                                                                                | [Testing helpers](../python/README.md#consumer-test-helpers)   |
| `testing.fixtures`   | pytest plugin: `fake_redis`                                                                          | Same guide; install `[testing]`, which includes Lua support    |
| `testing.ssrf_cases` | `SSRF_CASES`                                                                                         | Same guide                                                     |

Provider results, usage accounting, reservation receipts and job snapshots are
part of the contract. `Reservation` is data, not a bearer credential: only trusted
worker code should load/use it. No factory authorizes a user's operation.

## Browser surface

The main ESM entry exports `createSettingsStore`, `defaultSettings`,
`getSettingsStore`, `initialize`, `SETTINGS_KEY`, `defineSettingsPanel`,
`fontStacks`, `themes`, `createStorage`, `announce`, `createWakeLock`, `vibrate`,
`createProgress`, `createSessionTimer`, and `defineActivityComponents`.

The `/auto` entry bootstraps preferences and registers components in a browser.
`/styles.css` includes generated theme tokens, component CSS and local font
references. `/fonts/*` exposes bundled assets. The package also exports its
`/package.json`. See [web usage](../web/README.md) for configuration and lifecycle.

The public elements are `ak-settings-panel`, `ak-progress`, `ak-session`, and
`ak-celebrate`. Documented attributes, methods, event names and snapshot shapes
are supported. Internal DOM nesting, private fields and build chunk filenames
are not extension points. Use package export paths, not generated chunk URLs.

## Version policy

Python and web versions are independent. For accepted v1+ package releases:

1. Patch: compatible corrections, including stricter rejection of unsafe input.
2. Minor: additive exports and optional configuration with compatible defaults.
3. Major: removed/renamed exports, incompatible signatures, return/event shapes,
   persisted settings formats, or changed required configuration.

Deprecations identify the replacement and remain until a major release. Security
fixes may reject formerly accepted unsafe input in a patch. Each accepted release
records consumer test evidence and artifact checks before a package tag is made.
Repository snapshot `vX.Y.Z` tags do not declare package compatibility.
