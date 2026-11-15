# Graph Report - access-kit  (2026-11-15)

## Corpus Check
- Corpus is ~29,785 words - fits in a single context window. You may not need a graph.

## Summary
- 834 nodes · 1461 edges · 39 communities (29 shown, 10 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 122 edges (avg confidence: 0.89)
- Token cost: 167,168 input · 0 output

## Community Hubs (Navigation)
- LLM Provider Core
- Safe Fetch Errors & Transport
- IP Privacy & Sessions
- Python Core Plan
- Web Settings Store
- Contributing & Roadmap Policy
- Web Package Dependencies
- Settings & Test Fixtures
- Python Core Design Spec
- Release Workflow
- Health Endpoint
- Reusable Tox Workflow
- Cascade Merge Workflow
- Root Lint Tooling
- Package Contract Tests
- Dependabot Config
- Log Scrubbing
- Web Build Script
- Request ID Middleware
- Cascade Merge Script
- Security CI Scripts
- Zizmor Workflow
- Duplicate Code Workflow
- Tests Workflow
- Pre-commit Hooks
- Web Demo
- Docs & Release Notes Rendering
- Pinned Transport Tests
- Conda Environment
- Logging Plan Items
- Health Redis Check
- Fake Notifier
- Fake Turnstile
- Purge Before Cutoff
- Access Kit Project

## God Nodes (most connected - your core abstractions)
1. `make_fetcher()` - 38 edges
2. `LLMError` - 33 edges
3. `usage()` - 24 edges
4. `stream_response()` - 22 edges
5. `openai_compat_provider()` - 19 edges
6. `anthropic_provider()` - 17 edges
7. `BlockedDestination` - 16 edges
8. `fake_llm()` - 16 edges
9. `build_provider()` - 15 edges
10. `with_fallback()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `Zero-Classes Constraint (py-no-classes check)` --semantically_similar_to--> `Prefer Functions and Closures`  [INFERRED] [semantically similar]
  docs/superpowers/specs/2026-09-28-access-kit-python-core-design.md → CONTRIBUTING.md
- `Independent py-vX.Y.Z / web-vX.Y.Z Tags` --semantically_similar_to--> `Consuming-App Integration Acceptance`  [INFERRED] [semantically similar]
  CONTRIBUTING.md → docs/roadmap.md
- `make_fetcher (closure-based safe_fetch)` --semantically_similar_to--> `access_kit.safe_fetch.fetcher`  [INFERRED] [semantically similar]
  docs/superpowers/specs/2026-09-28-access-kit-python-core-design.md → SECURITY.md
- `make_fetcher (safe_fetch.fetcher)` --semantically_similar_to--> `access_kit.safe_fetch.fetcher`  [INFERRED] [semantically similar]
  python/README.md → SECURITY.md
- `SSRF_CASES shared list` --semantically_similar_to--> `SSRF Case Suite`  [INFERRED] [semantically similar]
  docs/superpowers/specs/2026-09-28-access-kit-python-core-design.md → SECURITY.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **SSRF defense: fetcher, IP pinning, SSRF case suite** — security_safe_fetch_fetcher, security_connect_time_ip_pinning, security_ssrf_case_suite, docs_superpowers_specs_2026_09_28_access_kit_python_core_design_connecttimepinnedtransport, docs_superpowers_specs_2026_09_28_access_kit_python_core_design_ipcheck, python_readme_make_fetcher [INFERRED 0.85]
- **Python v0.1 core modules** — docs_superpowers_specs_2026_09_28_access_kit_python_core_design_accesskitsettings, docs_superpowers_specs_2026_09_28_access_kit_python_core_design_logging_module, docs_superpowers_specs_2026_09_28_access_kit_python_core_design_health_router, docs_superpowers_specs_2026_09_28_access_kit_python_core_design_privacy_module, docs_superpowers_specs_2026_09_28_access_kit_python_core_design_session_module, docs_superpowers_specs_2026_09_28_access_kit_python_core_design_make_fetcher, docs_superpowers_specs_2026_09_28_access_kit_python_core_design_llmprovider_typeddict, docs_superpowers_specs_2026_09_28_access_kit_python_core_design_testing_fakes [EXTRACTED 1.00]
- **Web browser utilities** — web_readme_announce, web_readme_createwakelock, web_readme_vibrate, web_readme_createstorage [EXTRACTED 1.00]
- **LLM providers implementing LLMProvider closures dict** — docs_superpowers_plans_2026_09_28_access_kit_python_core_plan_anthropic_provider, docs_superpowers_plans_2026_09_28_access_kit_python_core_plan_openai_compat_provider, docs_superpowers_plans_2026_09_28_access_kit_python_core_plan_fake_llm, docs_superpowers_plans_2026_09_28_access_kit_python_core_plan_llmprovider [EXTRACTED 1.00]
- **Safe fetch SSRF defense pipeline** — docs_superpowers_plans_2026_09_28_access_kit_python_core_plan_make_fetcher, docs_superpowers_plans_2026_09_28_access_kit_python_core_plan_resolve_safe, docs_superpowers_plans_2026_09_28_access_kit_python_core_plan_is_blocked_ip, docs_superpowers_plans_2026_09_28_access_kit_python_core_plan_pinned_request, docs_superpowers_plans_2026_09_28_access_kit_python_core_plan_check_size, docs_superpowers_plans_2026_09_28_access_kit_python_core_plan_check_content_type [EXTRACTED 1.00]
- **HMAC session cookie lifecycle** — docs_superpowers_plans_2026_09_28_access_kit_python_core_plan_new_session_id, docs_superpowers_plans_2026_09_28_access_kit_python_core_plan_sign_session_id, docs_superpowers_plans_2026_09_28_access_kit_python_core_plan_set_session_cookie, docs_superpowers_plans_2026_09_28_access_kit_python_core_plan_get_session_id, docs_superpowers_plans_2026_09_28_access_kit_python_core_plan_rotate_session [EXTRACTED 1.00]

## Communities (39 total, 10 thin omitted)

### Community 0 - "LLM Provider Core"
Cohesion: 0.07
Nodes (51): build_provider(), complete_json(), with_fallback(), call(), complete_json(), complete_text(), provider_from_settings(), check_input() (+43 more)

### Community 1 - "Safe Fetch Errors & Transport"
Cohesion: 0.06
Nodes (46): BadContentType, BlockedDestination, FetchError, FetchTimeout, TooLarge, TooManyRedirects, Download, Fetch (+38 more)

### Community 2 - "IP Privacy & Sessions"
Cohesion: 0.06
Nodes (34): canonical_ip(), client_ip(), hash_ip(), _check_secret(), get_session_id(), rotate_session(), session_middleware(), middleware() (+26 more)

### Community 3 - "Python Core Plan"
Cohesion: 0.05
Nodes (38): AccessKitSettings, anthropic_provider, Blocked V4/V6 Network Lists, check_content_type, check_size, ClearRead, client_ip, complete_json_with_retry (+30 more)

### Community 4 - "Web Settings Store"
Cohesion: 0.09
Nodes (25): accessKit, choices, createSettingsStore(), notify(), onStorage(), decode(), defaultSettings, getSettingsStore() (+17 more)

### Community 5 - "Contributing & Roadmap Policy"
Cohesion: 0.07
Nodes (38): Contributing Guide, Conventional Commits Versioning, Independent py-vX.Y.Z / web-vX.Y.Z Tags, tox -e github check suite, Phase A: Scaffold, Phase B: Python v0.1, Phase C: Web v0.1, Phase D: rate limits, Turnstile, budgets, notifications (+30 more)

### Community 6 - "Web Package Dependencies"
Cohesion: 0.05
Nodes (38): @axe-core/playwright, esbuild, @fontsource/atkinson-hyperlegible, @fontsource/noto-sans, @playwright/test, description, devDependencies, @axe-core/playwright@^4.14.0 (+30 more)

### Community 7 - "Settings & Test Fixtures"
Cohesion: 0.07
Nodes (17): AccessKitSettings, fake_redis(), Chunks, client_for(), create(), kit_settings(), patch_fetch_http(), create() (+9 more)

### Community 8 - "Python Core Design Spec"
Cohesion: 0.07
Nodes (35): AccessKitError hierarchy, AccessKitSettings (BaseSettings), anthropic_provider, ConnectTimePinnedTransport, health_router, ipcheck (blocked_networks, validate_ip), LLMProvider TypedDict (dict of closures), logging.py (setup_logging, request_id_middleware, scrub_logs) (+27 more)

### Community 9 - "Release Workflow"
Cohesion: 0.07
Nodes (26): GH_TOKEN, GITHUB_TOKEN, STEPS_VERSION_OUTPUTS_BASE, STEPS_VERSION_OUTPUTS_PREV, STEPS_VERSION_OUTPUTS_TAG, jobs, release, name (+18 more)

### Community 10 - "Health Endpoint"
Cohesion: 0.11
Nodes (11): health_router(), healthz(), run_check(), get_health(), test_check_result(), check(), test_checks_run_concurrently(), test_errors_do_not_expose_secrets() (+3 more)

### Community 11 - "Reusable Tox Workflow"
Cohesion: 0.08
Nodes (25): INPUTS_TOX_ENV, tox_env, jobs, quality, name, on, workflow_call, runs-on (+17 more)

### Community 12 - "Cascade Merge Workflow"
Cohesion: 0.09
Nodes (21): permissions, runs-on, steps, GH_TOKEN, SOURCE_BRANCH, jobs, cascade, name (+13 more)

### Community 13 - "Root Lint Tooling"
Cohesion: 0.12
Nodes (21): dependencies, prettier@^3.9.8, devDependencies, jscpd@^5.3.3, @taplo/cli@^0.7.0, textlint@^15.8.0, textlint-rule-common-misspellings@^1.0.1, textlint-rule-write-good@^2.0.0 (+13 more)

### Community 14 - "Package Contract Tests"
Cohesion: 0.12
Nodes (5): test_security_coverage_gate_rejects_missing_lines_branches_and_exclusions(), historical_finding(), scanner(), test_missing_docker_fails(), test_scanner_fails_closed()

### Community 15 - "Dependabot Config"
Cohesion: 0.11
Nodes (17): default-days, patterns, github-actions, npm, pip, python, patterns, patterns (+9 more)

### Community 16 - "Log Scrubbing"
Cohesion: 0.17
Nodes (8): scrub_logs(), setup_logging(), scrub_record(), log_output(), test_freeform_event_is_redacted(), test_log_arguments_and_exceptions_are_not_formatted(), test_only_allowlisted_fields_survive(), test_untrusted_values_are_dropped()

### Community 17 - "Web Build Script"
Cohesion: 0.14
Nodes (10): declarations(), dist, fonts, palettes, require, root, port, root (+2 more)

### Community 18 - "Request ID Middleware"
Cohesion: 0.16
Nodes (9): get_request_id(), request_id_middleware(), middleware(), test_error_response_has_id_and_context_resets(), test_existing_response_id_is_replaced(), test_non_http_scope_passes_through(), app(), test_request_ids_are_isolated_and_untrusted_headers_ignored() (+1 more)

### Community 19 - "Cascade Merge Script"
Cohesion: 0.29
Nodes (9): collect_conflicts(), ensure_label(), get_login_for_sha(), gh_api_get(), gh_api_post(), main(), open_conflict_issue(), run() (+1 more)

### Community 20 - "Security CI Scripts"
Cohesion: 0.24
Nodes (4): coverage_gaps(), main(), is_historical_fixture(), main()

### Community 21 - "Zizmor Workflow"
Cohesion: 0.15
Nodes (12): jobs, quality, name, on, push, workflow_dispatch, contents, branches (+4 more)

### Community 22 - "Duplicate Code Workflow"
Cohesion: 0.17
Nodes (11): jobs, quality, name, on, pull_request, push, contents, permissions (+3 more)

### Community 23 - "Tests Workflow"
Cohesion: 0.17
Nodes (11): jobs, quality, name, on, pull_request, push, contents, permissions (+3 more)

### Community 24 - "Pre-commit Hooks"
Cohesion: 0.18
Nodes (10): entry, id, language, name, pass_filenames, types, types_or, repos (+2 more)

### Community 25 - "Web Demo"
Cohesion: 0.18
Nodes (4): runtime, status, wake, wakeButton

### Community 26 - "Docs & Release Notes Rendering"
Cohesion: 0.27
Nodes (4): find_templates(), load_dotenv(), main(), render()

### Community 29 - "Conda Environment"
Cohesion: 0.50
Nodes (3): channels, dependencies, pip

### Community 30 - "Logging Plan Items"
Cohesion: 0.67
Nodes (3): request_id_var ContextVar, ScrubbingJSONFormatter, setup_logging

## Knowledge Gaps
- **38 isolated node(s):** `access-kit`, `Conventional Commits Versioning`, `MIT License`, `GitHub Private Vulnerability Reporting`, `scripts/scan_secrets.py history allowlist` (+33 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 331 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **10 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `test_application_pipeline()` connect `Safe Fetch Errors & Transport` to `IP Privacy & Sessions`, `LLM Provider Core`, `Health Endpoint`, `Request ID Middleware`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `make_fetcher()` (e.g. with `download()` and `fetch()`) actually correct?**
  _`make_fetcher()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `access-kit`, `Conventional Commits Versioning`, `MIT License` to the rest of the system?**
  _38 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `LLM Provider Core` be split into smaller, more focused modules?**
  _Cohesion score 0.07066167290886392 - nodes in this community are weakly interconnected._
- **Why does `make_fetcher()` connect `Safe Fetch Errors & Transport` to `Pinned Transport Tests`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `LLMError` (e.g. with `with_fallback()` and `test_explicit_fallback_keeps_known_failed_usage()`) actually correct?**
  _`LLMError` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Should `Safe Fetch Errors & Transport` be split into smaller, more focused modules?**
  _Cohesion score 0.05802469135802469 - nodes in this community are weakly interconnected._