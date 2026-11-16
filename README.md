# access-kit

Shared backend and Web Components for **ClearRead** and **SoundSight**.
Only code both applications use belongs here.

| Package                              | Location  | Status                                      | Tags         |
| ------------------------------------ | --------- | ------------------------------------------- | ------------ |
| `gavvahar-access-kit` / `access_kit` | `python/` | Core, protections and jobs implemented      | `py-vX.Y.Z`  |
| `@exchange2302/access-kit-ui`        | `web/`    | Themes, settings and activities implemented | `web-vX.Y.Z` |

Both packages use the MIT license and are versioned independently.
Both packages target `1.0.1`, with the public API frozen in the API
inventory. Publication status and remaining app acceptance are recorded in
[the roadmap](docs/roadmap.md).

## Start developing

Use the latest stable Python 3 release and Node 22+.

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

## Try the shared web UI

```bash
npm ci
npm run demo
```

Open `http://127.0.0.1:4173` for the five themes, local fonts, settings panel,
browser utilities, and forgiving progress/session components. See [web integration and tests](web/README.md).

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
  "gavvahar-access-kit @ git+https://github.com/gavvahar/access-kit@py-v1.0.1#subdirectory=python",
]
```

The `py-v1.0.1` package tag identifies the corrected PyPI distribution name. Imports remain `access_kit`. For local development use
`python -m pip install -e ../access-kit/python`.

Pushes to `main` create repository releases (`vX.Y.Z`) from Conventional Commits,
using the original release workflow. Package builds run in CI; package registry
publishing uses the separate manual `publish-packages.yml` workflow. Validated Python and web releases will use independent
package tags. Repository snapshot tags do not replace consuming-app validation.

See the [roadmap](docs/roadmap.md), [contributing guide](CONTRIBUTING.md), and
[security policy](SECURITY.md). Release acceptance requires integration in the
consuming apps, not only this repo's tests.

The remaining library modules are implemented. Start with the
[protection guide](docs/protection.md), [job/SSE guide](docs/jobs.md), and
[public API inventory](docs/api.md). [Architecture decisions](docs/decisions.md)
and [package release readiness](docs/releasing-packages.md) describe the v1
acceptance steps. Consumer acceptance now passes in both real app integrations. Python publication on PyPI remains pending; see [the acceptance record](docs/acceptance-v1.md).

The browser package is published as `@exchange2302/access-kit-ui@1.0.1`:

```bash
npm install @exchange2302/access-kit-ui@1.0.1
```
