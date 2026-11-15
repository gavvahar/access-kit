# Architecture decisions

## 001: Two independently versioned packages

Accepted. Python and browser consumers upgrade at different rates. Keep manifests
under `python/` and `web/`, with shared quality tooling at the repository root.
Only primitives required by both consuming apps belong here. Application
pipelines, prompts, authentication policy, worker execution, and results stay in
the apps. Existing repository snapshot releases retain their current behavior;
package tags and registry releases represent separately accepted artifacts.

## 002: Functions and explicit lifecycle ownership

Accepted. Prefer functions, closures and typed structural data. Required Pydantic
settings/models, TypedDict/NamedTuple structures, exceptions, and platform
interfaces are exceptions. Package initializers remain empty: import each
module's public API directly. Shared clients passed to factories are caller-owned;
helpers close clients they create. Nothing sends network traffic at import time.

## 003: Atomic admission, conservative accounting

Accepted. Redis Lua uses server time and colocated hash-slot keys so independent
workers serialize the same cap. Costs use fixed-point micro-units with upward
rounding. Reserve a true upper bound before dispatch; retain unknown usage.
Store idempotent settlement receipts against the admission day. Fail closed on
storage/configuration errors. An overrun records actual usage and blocks the day;
it cannot reverse charges. Redis durability and upstream bounds remain application
operating requirements. A durable billing ledger is outside the library.

## 004: Owner-bound progress, application-owned workers

Accepted. Redis state plus trimmed streams supports snapshots and reconnects
without choosing a queue framework. Verified owners partition every lookup.
Monotonic updates preserve work, terminal transitions are final, and stale
history yields current state. Connection lifetimes, history and labels are
bounded. At-least-once event delivery requires idempotent client rendering.

## 005: Native controls and forgiving progress

Accepted. Browser components use native controls and light DOM. Host applications
can theme them without a framework or shadow-root stylesheet. Timers begin only
on intent and pause when hidden or disconnected. Completed work survives pauses
and target changes; only an explicit reset erases it. Celebrations use text and
a static mark, with no surprise motion, vibration or sound. All five palettes
must pass axe, keyboard use and narrow-screen tests.

## 006: Library stability and application acceptance

Accepted, amended for the initial public package release. The documented API
inventory freezes the v1 library surface, backed by package tests and composed
FastAPI consumer contracts for core processing, protections and job progress.
Actual ClearRead and SoundSight acceptance remains a separate launch requirement;
fixtures do not count as deployed app evidence. Incompatible signatures, return
shapes, persisted settings or event contracts require a major version. Additive
optional behavior uses minor versions and compatible fixes use patch versions.
The owner requested completion of the planned public release. Registry access
still requires account authentication; it is never inferred from GitHub access.
