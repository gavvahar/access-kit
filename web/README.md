# @gavvahar/access-kit-ui

Shared Web Components and display preferences for ClearRead and SoundSight.
The Phase C implementation includes five themes, local fonts, a settings panel,
and browser utilities. The package is framework-independent and remains private
until consuming-app integration is validated. Python and web releases are independent.

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
import "@gavvahar/access-kit-ui/styles.css";
import { defineSettingsPanel, initialize } from "@gavvahar/access-kit-ui";

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
not yet a validated `web-v0.1.0` release. Phase D work is not included.
