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

## 006: Stable contracts require consumer evidence

Accepted. The documented API inventory is the intended v1 surface. Development
versions remain clearly marked until real ClearRead and SoundSight integration
passes. After independent v1 tags, incompatible signatures, return shapes,
settings storage or event contracts require a major version; additive optional
behavior uses minor versions and compatible fixes use patch versions. Public
visibility and registry publication follow artifact review and owner approval.
