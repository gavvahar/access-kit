# Independent package publication

The existing `.github/workflows/release.yml` still creates repository snapshot
releases from Conventional Commits. Its contents and triggers are unchanged.
Package publication is a separate, manually dispatched workflow:
`.github/workflows/publish-packages.yml`. Snapshot releases never publish to
PyPI or npm automatically.

## Prepared release

Python and web target `1.0.1`; the public surface is frozen in
[the API inventory](api.md). Python wheel/source distributions and the browser
tarball are built independently. Publication is not complete until the registries
accept the uploads. Neither a manifest version nor a git tag proves that an
upload succeeded. Both actual app integrations are merged and pass their
acceptance suites; see [the roadmap](roadmap.md).

## Current publication status

`@exchange2302/access-kit-ui@1.0.1` is published on npm and verified by an
anonymous install. The matching app updates are merged. Python [`gavvahar-access-kit@1.0.1`](https://pypi.org/project/gavvahar-access-kit/1.0.1/)
is published through GitHub trusted publishing and verified by a fresh public
install. The original `access-kit` name was rejected by PyPI as too similar to an
existing project; imports remain `access_kit`. Both registry uploads are complete.

## First-time account setup

Create a [PyPI account](https://pypi.org/account/register/) if needed, verify its
email address and enable two-factor authentication. The username need not match
GitHub or npm. PyPI supports creating a new project from a pending publisher. At
[PyPI publishing settings](https://pypi.org/manage/account/publishing/), register:

| Field              | Value                  |
| ------------------ | ---------------------- |
| PyPI project       | `gavvahar-access-kit`  |
| Owner              | `gavvahar`             |
| Repository         | `access-kit`           |
| Workflow filename  | `publish-packages.yml` |
| GitHub environment | `pypi`                 |

No PyPI API token is needed with this setup. See the official
[pending publisher instructions](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/).
A name is not reserved until the first successful upload.

For npm, sign into the account owning the `exchange2302` npm scope with `npm login`.
Bootstrap the first package upload from a reviewed tarball with
`npm publish /path/to/exchange2302-access-kit-ui-1.0.1.tgz --access public --ignore-scripts`.
Complete any browser/2FA challenge directly; never paste a token into chat or
commit it. Once the npm package exists, configure its trusted publisher with
owner `gavvahar`, repository `access-kit`, workflow `publish-packages.yml`, and
environment `npm`. Later uploads can use the workflow's OIDC identity without
long-lived credentials. See [npm trusted publishing](https://docs.npmjs.com/trusted-publishers/).

## Review and build

Run `tox -e all`; the workflow repeats the full GitHub check chain. Its build job
also runs the real Redis concurrency/precision/replay test before packaging.
Python uses the latest available Python 3; browser builds use current Node.

The build job runs `python -m build` and strict Twine metadata checks, then npm
prepack builds ESM/CSS/fonts into the web tarball. It uploads one run-scoped
`public-packages` artifact with `python/` and `web/` subdirectories. The two publish
jobs download that exact artifact rather than rebuilding with elevated identity.
Only publish jobs have `id-token: write`; they do not check out or execute source.
Python uses PyPI trusted publishing, and npm publishes the tarball with provenance
and lifecycle scripts disabled.

Dispatch with `publish=false` first to review artifacts without registry writes:

```bash
gh workflow run publish-packages.yml --repo gavvahar/access-kit -f package=both -F publish=false
```

## Publish

Once accounts and reviewed artifacts are ready, dispatch the selected package
with `publish=true`. Use `python` for the initial PyPI upload if npm's first
upload has already been bootstrapped locally. Registry uploads are independent;
a successful upload is not rolled back because the other registry failed.
Never overwrite a published version or silently skip an unexpected collision.

Create each independent package tag against its reviewed commit, then verify
registry metadata and install each package from its registry. Existing tags
`py-v1.0.1` and `web-v1.0.1` already identify the prepared releases. Package
tags are git tags, not additional GitHub Releases: the existing snapshot release
workflow continues selecting its own latest repository release.

Consumer apps pin a package tag/version and upgrade one app at a time. Actual
ClearRead and SoundSight screen/pipeline acceptance must be recorded separately;
a package smoke test does not replace it.

The first npm publication uses `@exchange2302/access-kit-ui`. The earlier
`web-v1.0.0` tag retains the original unpublished `@gavvahar` name; it is never
overwritten. `web-v1.0.1` corrects package ownership without changing JavaScript
exports, preferences, components, or browser behavior. GitHub/PyPI publisher
owner and repository remain `gavvahar/access-kit`; npm identity is independent.

The original `py-v1.0.0` tag is preserved. `py-v1.0.1` corrects the Python
distribution name to match the accepted pending publisher; it keeps the v1 API.
