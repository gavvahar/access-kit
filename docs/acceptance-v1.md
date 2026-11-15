# v1 consumer acceptance evidence

Library source is pinned by independent `py-v1.0.0` and `web-v1.0.0` tags at
`625fbf9a9d71a93edab49e86325c33e30db69a1d`. The Python package was installed from
that public tag in the consumer test environment, not imported from an editable
access-kit checkout. Both vendored browser builds were compared byte-for-byte
with the reviewed UI artifact; each records its source tag/commit and font licenses.

## ClearRead

[Integration PR #6](https://github.com/gavvahar/ClearRead/pull/6) implements the
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
Postgres history/cache, long-document chunking and public deployment belong to
ClearRead's remaining product roadmap, not this shared-library acceptance slice.

## SoundSight

[Integration PR #4](https://github.com/gavvahar/SoundSight/pull/4) implements a
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

The minute cap counts imported caption duration. Cloud STT is not enabled and no
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
No Python package was uploaded. npm is not authenticated locally and its initial
package does not exist, so no npm upload was attempted. Follow the
[account setup instructions](releasing-packages.md#first-time-account-setup).
