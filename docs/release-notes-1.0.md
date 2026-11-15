# Initial public API: 1.0.0

Python and browser packages have independent `1.0.0` manifests. This document
describes their reviewed contents; check the roadmap/registries for upload status.

## Python

Typed settings, health checks, scrubbed request logging, IP privacy and signed
anonymous sessions are available through defining modules. The fetcher validates
DNS and connects to pinned public IPs with bounded redirects, bytes and time.
LLM providers support explicit models, strict JSON validation, retries and
accumulated known/unknown usage.

Bounded ASGI request bodies reject oversized JSON before parsing. Settings-based
provider construction accepts explicit input/output and retry limits.

Redis-backed protections provide weighted sliding limits, daily reservation and
settlement, threshold snapshots, and fail-closed dependencies. Turnstile validates
hostname/action against Cloudflare. ntfy, signed webhooks and TLS SMTP deliver
explicit operator alerts. Owner-bound jobs provide monotonic state, bounded
streams, reconnect snapshots and an SSE response helper. Testing fixtures include
Lua-enabled fakeredis and a deterministic LLM provider.

Import defining modules directly; all package initializers are empty. Python
requires 3.15 or newer and CI selects the latest available Python 3. Provider
bounds, storage durability, authorization and actual task execution remain the
consumer application's responsibilities. See the protection and jobs guides.

## Browser

The ESM package includes five accessible themes, self-hosted OFL fonts, validated
preferences and a settings panel. Utilities cover text announcements, safe
storage, opt-in vibration and explicitly requested wake locks. Progress,
micro-sessions and static celebrations preserve completed work across pauses,
reconnection and target changes. Imports support server-side environments.

Both automatic plain-HTML integration and explicit Vite integration use the same
package exports. Generated chunks and fonts must be copied together. No hardware
permission, audio capture, paid service or alert delivery starts on import.

## Compatibility and acceptance

The API inventory defines v1 compatibility. Breaking changes require a major
version; optional additions use minor versions and compatible fixes use patches.
Original repository snapshot release automation remains unchanged.

Automated consumer contracts cover core processing, session ownership, rejection
before provider dispatch, token/minute caps under concurrent calls, and terminal
SSE delivery. Actual ClearRead and SoundSight implementations are still templates,
so their product acceptance checks remain open. This release does not claim that
either application is launched, deployed, or validated with real users.
