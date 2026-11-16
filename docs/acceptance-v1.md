# v1 consumer acceptance evidence

Library source is pinned by independent `py-v1.0.0` and `web-v1.0.0` tags at
`625fbf9a9d71a93edab49e86325c33e30db69a1d`. The Python package was installed from
that public tag in the consumer test environment, not imported from an editable
access-kit checkout. Both vendored browser builds were compared byte-for-byte
with the reviewed UI artifact; each records its source tag/commit and font licenses.

## ClearRead

[Merged integration PR #6](https://github.com/gavvahar/ClearRead/pull/6) implements the
core article pipeline and shared reader. Public URL input uses the actual safe
fetcher, trafilatura/readability extraction and strict provider output validation.
Pasted text shares the same provider/budget path. The browser submits an
asynchronous job, follows owner-bound SSE and opens the reading view.

1. 58 backend tests pass, including every shared SSRF case through the actual
   endpoint, extraction, known/unknown usage, provider accounting breaches,
   origins/size limits, session ownership and terminal background progress.
2. 8 browser tests pass: real form submission to the reader; all five themes with
   axe at 320px; shared session pause/completion; 300% text with RTL.
3. Fifty fresh anonymous sessions cannot reset exhausted/held daily token
   capacity. Provider dispatch stays at one call in that flood regression.
4. `tox -e all`, zero npm audit findings and the latest-Python Docker image build
   pass. The original repository snapshot release workflow is unchanged.

Upstream DNS/model replies are controlled fixtures, not paid provider calls.
The production code uses the real adapters and requires explicit model settings.
The integration merged as `2db2777c89a98c1e11d4c7529624ddba685feb13` after GitHub
quality, browser and secret checks passed.
Postgres history/cache, long-document chunking and public deployment belong to
ClearRead's remaining product roadmap, not this shared-library acceptance slice.

## SoundSight

[Merged integration PR #4](https://github.com/gavvahar/SoundSight/pull/4) implements a
shared first screen, explicitly started browser captions, typed replies, and a
working WebVTT import workflow. Real imports publish Redis job progress and
return owner-bound, expiring transcript data. No audio is sent to SoundSight;
browser speech-provider privacy is explained before microphone access.

1. 9 backend tests pass: valid/invalid captions, origins and ingress bounds,
   owner isolation, terminal SSE and the global minute cap.
2. 9 browser tests pass: explicit speech intent, text-only recognized output,
   actual caption import/live progress, all five themes with axe at 320px,
   shared session pause/completion, and enlarged captions with RTL at 300% text.
3. Fifty fresh anonymous sessions cannot bypass exhausted daily minute capacity.
4. `tox -e all`, zero npm audit findings, the Vite build and the latest-Node/Python
   multi-stage Docker image build pass. Snapshot release behavior is unchanged.

The integration merged as `fe58169db27bcdcecb0714d49eb2b09ef9178b5f` after GitHub
quality, browser and secret checks passed. The minute cap counts imported caption duration. Cloud STT is not enabled and no
paid transcription is claimed. Browser tests use a stub speech engine and request
no microphone permission. Whisper, YAMNet, pairing, ASL content and public launch
remain separate SoundSight product work.

## Library and publication

The library passes 309 Python tests, 28 web unit tests and 18 browser tests.
Security modules retain 100% line and branch coverage. Real Redis CI subjects
both token/minute budgets to 1,000 requests across four clients, verifies exact
micro-unit precision and checks owner-bound terminal replay.

The [publisher dry run](https://github.com/gavvahar/access-kit/actions/runs/43772976046)
passed quality, real Redis and artifact builds. The
[Python upload attempt](https://github.com/gavvahar/access-kit/actions/runs/43773898238)
passed the same checks but PyPI rejected OIDC with `invalid-publisher`: no
registered publisher matched the repository/workflow/environment identity.
No Python package was uploaded in that attempt. The owner subsequently created
a PyPI account and configured a pending publisher for `gavvahar-access-kit`: PyPI
rejected the original distribution name as too similar to an existing project.
Python 1.0.1 corrects the distribution name while preserving `access_kit` imports.

## Published browser package: 1.0.1

The authenticated npm account is `exchange2302`. The initial attempted
`@gavvahar` package could not publish because that npm scope was unavailable.
With owner approval, the package was renamed to
[`@exchange2302/access-kit-ui@1.0.1`](https://www.npmjs.com/package/@exchange2302/access-kit-ui).
The original web-v1.0.0 tag was preserved; web-v1.0.1 identifies the corrected
package at `fa2cae3e0e838bee6f90901bd56142e184f1186f`.

npm accepted the browser-approved upload, public registry metadata exposed the
exact version/integrity, and an anonymous install into a fresh directory passed.
The installed package's ESM exports, DOM-free progress/timer controllers, CSS,
and local font licenses were verified. No install-time scripts were executed.

[ClearRead #7](https://github.com/gavvahar/ClearRead/pull/7) and
[SoundSight #5](https://github.com/gavvahar/SoundSight/pull/5) are merged updates
to the same reviewed web-v1.0.1 package. All consumer CI checks pass, with the
same 8 and 9 real browser tests. JavaScript APIs and behavior are unchanged.
Both registry uploads are now complete; see the Python publication evidence below.

## Published Python package: 1.0.1

PyPI accepted the owner-configured pending publisher for `gavvahar-access-kit`.
The original py-v1.0.0 tag remains unchanged; py-v1.0.1 points to
`08ce7233266af91205fa18819aa9d4d67725ff32`.
The [Python-only publication run](https://github.com/gavvahar/access-kit/actions/runs/43786013724)
passed quality, real Redis, artifact builds and the OIDC PyPI upload.

Public [PyPI version metadata](https://pypi.org/pypi/gavvahar-access-kit/1.0.1/json)
confirms version 1.0.1 and these SHA-256 distribution digests:

1. Wheel: `07651b4bced07613717cb1c13498be5e9b64dca75d9730bd290a8fea3e78864d`.
2. Source archive: `48eab57d537cec27028b5ec0eabe3d689c3c0c21f885f6d1cbabfe2bfa50a32b`.

A fresh Python 3.15.2 environment installed `gavvahar-access-kit==1.0.1` from
`https://pypi.org/simple` using isolated pip with no cache or account credentials.
Installed metadata, core/protection/job imports, the health route, and empty
package initializers were verified outside the source checkout. Distribution
identity changed; Python imports and the v1 API remain unchanged.

[ClearRead #8](https://github.com/gavvahar/ClearRead/pull/8) and
[SoundSight #6](https://github.com/gavvahar/SoundSight/pull/6) are merged updates
from the original Git dependency to exact PyPI `gavvahar-access-kit==1.0.1`.
Both local `tox -e all` chains and all GitHub quality, browser and secret checks
passed. Consumer acceptance counts remain 58 backend/8 browser tests in ClearRead
and 9 backend/9 browser tests in SoundSight.
