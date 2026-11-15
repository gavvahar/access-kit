# Package release readiness

The existing `.github/workflows/release.yml` continues creating repository
snapshot releases from Conventional Commits. Do not repurpose it for package
publishing. Independent Python/web package tags are acceptance milestones.
No credentials are embedded in source or built artifacts.

## Local review

1. Run `tox -e all` and the real Redis load check described in
   [protection tests](protection.md#repeat-the-real-redis-load-check).
2. Build Python with `python -m build python --outdir /tmp/access-kit-dist`.
   Inspect both source and wheel archives, metadata, license and `py.typed`.
3. Run `npm pack --workspace web --dry-run` to inspect the browser artifact.
   The prepack hook builds ESM, CSS, fonts and their OFL licenses. Generated
   artifacts include no demo files, tests or user documents.
4. Install reviewed artifacts in the actual ClearRead/SoundSight screens and
   workers. Exercise authorization, provider bounds, progress reconnects and
   settings persistence. Record the exact package revision and results.
5. Select independent package versions, review the API inventory and release
   notes, and obtain owner approval before changing visibility or publishing.

## Owner-controlled publication

Publication remains pending; this repository session does not upload packages,
change visibility, or create package tags. The workspace currently lacks the
consuming application pipelines/screens needed for acceptance. Existing manifest
versions and web `private: true` deliberately prevent an accidental stable claim.

After acceptance, update the selected package's version. Refresh the npm lockfile
when the web version changes. Review the resulting archives again. For public npm
publication remove web `private: true` only in the approved release change and
use scoped public access. Confirm ownership/name availability for `access-kit`
on PyPI and `@gavvahar/access-kit-ui` on npm before upload; availability is not
assumed. If either name must change, update install docs and consumer manifests.

Publish exactly the reviewed Python distributions through the owner's configured
PyPI credentials/trusted publishing and the reviewed npm tarball through the
owner's npm account. Registry authentication and repository security settings
remain outside package code. Tag the accepted revisions `py-vX.Y.Z` and
`web-vX.Y.Z`; apps upgrade one package/app at a time. Never overwrite an existing
published version. A failed upload must be inspected before retrying.

GitHub private vulnerability reporting, secret scanning and alerts still need
the owner to verify/enable them. The local secret scan and Dependabot workflow
do not substitute for those repository settings.
