# Contributing

Only share code needed by both ClearRead and SoundSight. Keep application-specific
prompts, detection logic, and content in those repositories.

## Local checks

Use the latest stable Python 3 release. CI uses `3.x` with `check-latest: true`
and type checking follows its running interpreter. Package metadata declares a
minimum supported version, not an interpreter pin.

```bash
python -m pip install -e './python[dev]'
npm ci
pre-commit install
tox -e github
```

`tox -e github` runs linting, text and document formatting checks, TOML checks,
duplication detection, Python tests with at least 85% branch-aware coverage,
strict Python type checks, Python package builds, and web package checks (Node tests, Chromium, and axe).
Install the browser once with `npm exec --workspace web -- playwright install chromium`.
`tox -e format` applies formatting. Pre-commit requires the activated environment
and installed Node tooling.

Prefer functions and closures; use classes for settings and required third-party
interfaces. Test observable behavior. Every security fix needs a regression test.

## Versioning

Use Conventional Commits, for example `feat(settings): add configuration`.
Python metadata and its version live in `python/pyproject.toml`.
Keep every Python `__init__.py` empty; import APIs from their named modules. Web metadata lives in `web/package.json`;
update it together with `web/src/index.js`.

Use `py-vX.Y.Z` and `web-vX.Y.Z` tags independently after integration validation.
Package builds run in CI. Registry publishing is deferred to v1.0.
Pushes to `main` also create repository snapshot releases (`vX.Y.Z`) using the
existing Conventional Commit versioning script. Snapshot releases do not establish
that either package has passed its consuming-app integration checks.
