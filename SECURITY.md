# Security policy

The supported public API line is v1.0. Package publication status is tracked
in [the roadmap](docs/roadmap.md); development snapshots are not package releases.

Report vulnerabilities privately through
[GitHub private vulnerability reporting](https://github.com/gavvahar/access-kit/security/advisories/new).
Do not include secrets or exploit details in public issues. If reporting is
unavailable, ask @gavvahar to enable it without disclosing vulnerability details.
Private reporting is enabled for this public repository.

Security requirements:

1. Secrets and application `.env` examples stay in the consuming apps.
2. Log scrubbing must be enabled by default when logging is implemented.
3. Every `safe_fetch` change must add regression tests. Connect-time IP pinning
   and the SSRF case suite are required before that module ships.
4. GitHub secret scanning, push protection and Dependabot alerts are enabled.

The fetcher in `access_kit.safe_fetch.fetcher` validates every DNS answer and
connects to the validated numeric IP while preserving TLS SNI and Host. It
revalidates redirects, refuses HTTPS downgrades and ambient proxies, and bounds
response bytes and time. CI requires 100% line and branch coverage for fetching,
session handling, privacy, log scrubbing, Redis admission, budgets, and Turnstile
validation. Coverage establishes regression
coverage; it does not substitute for security review.

## Historical test fixtures

The local full-history scan recognizes exactly three fake URI fixtures in immutable
commits: `8afedc4` (`test_logging.py`), `bf5200e` (`testing/ssrf_cases.py`), and `39859b6`
(`test_delivery.py`).
`scripts/scan_secrets.py` matches commit, file, detector, exact dummy value, and
unverified status. Verified results, other values, other files, and newer commits
always fail. No detector or path is skipped, and Git history is not rewritten.
Current test fixtures assemble those URLs at runtime, so new commits avoid the
false positives. The GitHub push/PR scanner configuration is unchanged.
