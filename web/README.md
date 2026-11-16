# @exchange2302/access-kit-ui

Shared Web Components and display preferences for ClearRead and SoundSight.
The implementation includes five themes, local fonts, a settings panel,
browser utilities, progress, micro-sessions and celebrations. The package is framework-independent. Its v1 public API is frozen; actual app
integration remains separately tracked. Python and web releases are independent.

## Run the demo

From the repository root, using Node 22 or newer:

```bash
npm ci
npm run demo
```

Open `http://127.0.0.1:4173`. The demo includes a reading sample and a caption
sample; it does not access the microphone, call a model, or store content.
Only validated display preferences are saved in this browser's local storage.

## Plain HTML, Jinja, and HTMX

Build the package with `npm run build --workspace web`. Copy the **entire**
`web/dist/` directory into your app's static assets, including shared JavaScript
chunks, font files, and font licenses. For a consuming app, pin the reviewed web
tag before copying its build. Do not copy only the entry JavaScript file.

```html
<link rel="stylesheet" href="/static/vendor/access-kit/access-kit.css" />
<script type="module" src="/static/vendor/access-kit/auto.js"></script>
<ak-settings-panel></ak-settings-panel>
```

`auto.js` applies preferences to the document root and registers the component.
Settings survive HTMX component removal/reconnection; listeners are detached when
a panel is removed. The panel is an inline form, so it can also sit inside an
app-owned native dialog. Load the shared CSS for controls and live-region hiding.

## Vite or explicit initialization

```js
import "@exchange2302/access-kit-ui/styles.css";
import { defineSettingsPanel, initialize } from "@exchange2302/access-kit-ui";

const runtime = initialize();
defineSettingsPanel({ store: runtime.store });
// On app teardown: runtime.destroy();
```

Choose auto initialization or explicit initialization once per page. Component
registration is idempotent; the first registration establishes its app-scoped
store. No DOM or hardware access happens merely by importing the main entry.

## Settings and themes

The named themes are `light`, `dark`, `sepia`, `contrast`, and `calm`.
`theme: "system"` follows the device's color preference and is the default.
CSS variables use the `--ak-` prefix. Color tokens include `--ak-color-background`,
`surface`, `raised`, `text`, `muted`, `accent`, `on-accent`, `border`, and `focus`.
Spacing, radius, readable width, typography, and motion tokens are shared too.
Styles are scoped to the `ak-ui` root class added by initialization and to the
`ak-settings-panel` custom element. Applications can override tokens in their CSS.

| Preference      | Values                       | Default  |
| --------------- | ---------------------------- | -------- |
| `theme`         | `system` or a named theme    | `system` |
| `font`          | `system`, `atkinson`, `noto` | `system` |
| `textScale`     | 0.875–3 in steps of 0.125    | 1        |
| `lineHeight`    | 1.5, 1.7, 2                  | 1.7      |
| `letterSpacing` | `normal`, `wide`             | `normal` |
| `reducedMotion` | `system`, `reduce`           | `system` |
| `vibration`     | Boolean                      | false    |

Text scaling multiplies a base of 1.125 rem, respecting browser font defaults.
Device reduced-motion preferences always take priority; a setting cannot enable
motion against the device preference. Forced colors retain native control borders
and visible focus outlines. The demo supports both text directions and reflows
at a 320px viewport with maximum text scaling.

`getSettingsStore()` returns the default store. `createSettingsStore()` creates an
isolated store with `get`, `update`, `reset`, `subscribe`, and `destroy` methods.
Snapshots are immutable. Invalid updates throw a TypeError. Corrupt or unsupported
stored values fall back to defaults; unknown stored properties are discarded.

The key is `access-kit:settings:v1`, with a versioned JSON envelope. Storage-denied
and quota failures retain working in-memory preferences and expose
`store.persisted === false`; the panel displays that limitation. Same-origin tabs
synchronize using storage events without writing changes back in a loop. Separate
app origins do not share storage. Reset removes only this package's preference key.

The panel emits a bubbling `ak-settings-change` event for user changes and resets.
`event.detail` contains `{ settings, persisted }`. Store subscriptions also receive
`{ source, persisted }`, where source is initial, local, external, or reset.
Unsubscribe using the function returned from `subscribe`.

## Local font assets

Atkinson Hyperlegible and Noto Sans, in regular and bold weights, are bundled
from the locked Fontsource packages. The CSS loads subset files from `dist/fonts/`
on the same origin; it does not request a third-party font service. Fontsource's
script subsets and browser fallback fonts cover characters absent from a selected
font. This package does not promise coverage for every writing system.

Both font licenses are included in `dist/fonts/*.LICENSE` and must remain with
redistributed assets. The font binaries are unchanged. Font choice is a user
preference, not a claim of a reading or medical benefit.

## Browser utilities

1. `announce(text, { priority: "polite" })` sends a text-only live-region message
   without moving focus. Use `assertive` only for urgent information. Repeated
   pending messages coalesce; separate polite and assertive regions are supported.
2. `createWakeLock()` returns `request`, `release`, `subscribe`, and `destroy`,
   plus `supported` and `active`. Nothing is acquired until `request()` is called.
   It recovers a requested lock when the page becomes visible, releases on page
   hide, handles cancellation during acquisition, and reports denial as false.
   Call `destroy()` when the owning feature ends. A wake lock is best effort and
   requires a supported secure context; it does not keep background audio running.
3. `vibrate(pattern, { enabled: true })` requests bounded haptic feedback after
   explicit opt-in. The helper does not silently enable itself from preferences:
   pass `getSettingsStore().get().vibration` as `enabled` when appropriate.
   Unsupported or denied hardware returns false. No vibration call guarantees
   that a device will actually vibrate.
4. `createStorage()` wraps JSON storage with safe fallback values and Boolean
   write/remove results. A custom backend can be injected for tests. Preferences
   never contain transcripts, documents, authentication, or server secrets.

Wake-lock and vibration behavior follows the browser APIs documented by
[MDN wake locks](https://developer.mozilla.org/en-US/docs/Web/API/Screen_Wake_Lock_API)
and [MDN vibration](https://developer.mozilla.org/en-US/docs/Web/API/Vibration_API).

## Build, tests, and packaging

```bash
npm exec --workspace web -- playwright install chromium
npm run check --workspace web
npm pack --workspace web
```

`check` builds the distribution, runs Node unit tests, installs the matching
Chromium binary if missing (without sudo), and runs browser tests with axe.
The first check needs network access for that one-time browser download. CI installs Chromium and its OS dependencies. A fresh Linux development
machine may also need `playwright install --with-deps chromium`.

The package archive includes ESM entries, their shared chunks, CSS, font assets,
font licenses, and this guide. Generated output is excluded from duplication and
formatting checks; authored source remains subject to both. The release workflow
is unchanged. No registry publication or package tag is created by this phase.

Automated checks cover common accessibility problems; they do not replace screen
reader testing or testing with users. See
[Playwright's accessibility guidance](https://playwright.dev/docs/accessibility-testing).

## Acceptance status

The library implementation and demo are complete. Final Phase C acceptance still
requires SoundSight's first screen and ClearRead's reader to consume the same
package. Those application screens are not present in this workspace, so this is
not yet a consuming-app-validated release. Progress and session components are
implemented; actual ClearRead and SoundSight screen integration remains pending.

## Progress, micro-sessions, and celebrations

Import `defineActivityComponents` and call it once to register all three elements.
The `/auto` entry point registers them alongside the settings panel. Registration
is idempotent; importing the explicit entry point does not require a DOM.

```html
<ak-progress value="2" max="5" label="Small steps today"></ak-progress>
<ak-session minutes="5" label="A little reading time"></ak-session>
<ak-celebrate></ak-celebrate>
```

`ak-progress` renders a labelled native progress element. Omit `value` for an
indeterminate state. `max` defaults to 100; invalid maxima use that default.
Values are visually clamped to the bar while the summary preserves earned work,
including completion beyond the target. Change attributes to apply job snapshots.
Labels are text, never HTML. The host app owns the data and persistence.

`createProgress({target=5, completed=0})` is a DOM-free goal controller.
`get()` returns a frozen snapshot; `add(amount=1)` preserves cumulative completed
work; `setTarget(value)` changes only the goal; `reset()` explicitly clears it.
Targets/counts are bounded whole numbers up to one million, and targets must be
positive. Progress is intentionally independent of streaks, deadlines or penalties.

`ak-session` starts idle. Native Start, Pause/Continue and Start over buttons
control it. Hidden tabs and disconnected elements pause; reconnecting retains
elapsed work and requires explicit intent to resume. Minutes are read at first
connection (default five; duration bounded from one second to one hour).
Countdown ticks are not live announcements. Status changes announce once;
completion dispatches bubbling `ak-session-complete` with the timer snapshot in
`event.detail`. Use one event listener per host lifecycle and remove it on teardown.

`createSessionTimer({seconds=300, now})` provides the same DOM-free clock logic:
`start()`, `pause()`, `reset()`, `get()`. `now` is an optional monotonic millisecond
clock; performance.now is the default. Snapshots have status, seconds, elapsed
seconds and remaining whole seconds. Timer state is in memory; reload clears it.

Call `element.celebrate("That counts.")` on `ak-celebrate`, and `clear()` to
remove its message. It accepts text up to 180 characters, displays a static check
mark, and uses a polite status region. It does not trigger sound, movement,
vibration, storage writes or focus changes. Persisting progress and selecting
when to celebrate belong to the application.

## Connect job progress

Listen to the backend's named SSE events, apply each snapshot directly to
`ak-progress`, and use `textContent` for labels. Discard lower sequences and close
the EventSource on complete, failed or cancelled. Handle unavailable/reconnect
with bounded backoff and the app's session authorization. The backend contract
and retention behavior are documented in [job progress](https://github.com/gavvahar/access-kit/blob/main/docs/jobs.md).
