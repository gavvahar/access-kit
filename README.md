# access-kit

Shared backend and Web Components for **ClearRead** and **SoundSight**.
Only code both applications use belongs here.

| Package | Location | Status | Tags |
| --- | --- | --- | --- |
| `access-kit` / `access_kit` | `python/` | Settings and health implemented | `py-vX.Y.Z` |
| `@gavvahar/access-kit-ui` | `web/` | Package scaffold | `web-vX.Y.Z` |

Both packages use the MIT license and are versioned independently.
Development versions are not stable releases. Nothing is published to PyPI or npm.

## Start developing

Requires Python 3.12+ and Node 22+.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e './python[dev]'
npm ci
pytest
mypy
tox -e github
pre-commit install
```

The existing conda workflow is also available through `environment.yml`.
The root `pyproject.toml` owns shared tooling; `python/pyproject.toml` owns the
installable Python package. Web package metadata lives in `web/package.json`.

## Use the Python core

```python
from fastapi import FastAPI
from access_kit.health import health_router
from access_kit.settings import AccessKitSettings

# Apps subclass AccessKitSettings to add their own configuration.
# Required environment: APP_NAME, PUBLIC_BASE_URL, REDIS_URL,
# SESSION_SECRET (32+ characters), IP_HASH_SALT (32+ characters).
settings = AccessKitSettings()
app = FastAPI(title=settings.app_name)
app.include_router(health_router())
```

`GET /healthz` returns 200 for liveness. Supply named async checks returning
`True` to use it for readiness; failed or timed-out checks return 503.
See [Python usage](python/README.md) for an example.

## Releases and next steps

Apps will pin independent git tags after their first validated releases:

```toml
dependencies = [
  "access-kit @ git+https://github.com/gavvahar/access-kit@py-v0.1.0#subdirectory=python",
]
```

`py-v0.1.0` is a planned tag, not an existing release. For local development use
`python -m pip install -e ../access-kit/python`.

Tag workflows build downloadable CI artifacts; they do not publish packages or
create releases automatically. Set each package's version before tagging.

See the [roadmap](docs/roadmap.md), [contributing guide](CONTRIBUTING.md), and
[security policy](SECURITY.md). Release acceptance requires integration in the
consuming apps, not only this repo's tests.
