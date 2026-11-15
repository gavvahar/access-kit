# Security policy

This project is in development. No stable releases are supported yet.

Report vulnerabilities privately through
[GitHub private vulnerability reporting](https://github.com/gavvahar/access-kit/security/advisories/new).
Do not include secrets or exploit details in public issues. If reporting is
unavailable, ask @gavvahar to enable it without disclosing vulnerability details.
The repository owner must enable private reporting in GitHub settings.

Security requirements:

1. Secrets and application `.env` examples stay in the consuming apps.
2. Log scrubbing must be enabled by default when logging is implemented.
3. Every `safe_fetch` change must add regression tests. Connect-time IP pinning
   and the SSRF case suite are required before that module ships.
4. Secret scanning and Dependabot alerts must be enabled by the repository owner.

No SSRF-safe fetcher is implemented in this scaffold.
