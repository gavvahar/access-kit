import { fontStacks, themes } from "./themes.js";
import { createStorage } from "./utilities/storage.js";

export const SETTINGS_KEY = "access-kit:settings:v1";
export const defaultSettings = Object.freeze({
  theme: "system",
  font: "system",
  textScale: 1,
  lineHeight: 1.7,
  letterSpacing: "normal",
  reducedMotion: "system",
  vibration: false,
});
const choices = {
  theme: ["system", ...Object.keys(themes)],
  font: Object.keys(fontStacks),
  letterSpacing: ["normal", "wide"],
  reducedMotion: ["system", "reduce"],
};
function valid(key, value) {
  if (key === "textScale")
    return (
      typeof value === "number" &&
      Number.isFinite(value) &&
      value >= 0.875 &&
      value <= 3 &&
      Number.isInteger(value * 8)
    );
  if (key === "lineHeight") return [1.5, 1.7, 2].includes(value);
  if (key === "vibration") return typeof value === "boolean";
  return Object.hasOwn(choices, key) && choices[key].includes(value);
}
function decode(payload) {
  if (
    payload?.version !== 1 ||
    !payload.settings ||
    typeof payload.settings !== "object"
  )
    return { ...defaultSettings };
  return Object.fromEntries(
    Object.entries(defaultSettings).map(([key, value]) => [
      key,
      valid(key, payload.settings[key]) ? payload.settings[key] : value,
    ]),
  );
}

/** App-scoped store. Only validated display preferences are persisted. */
export function createSettingsStore({
  storage = createStorage(),
  eventTarget = globalThis.window,
} = {}) {
  let current = Object.freeze(decode(storage.read(SETTINGS_KEY)));
  let persisted = storage.available;
  let destroyed = false;
  const listeners = new Set();
  function notify(source) {
    for (const listener of [...listeners])
      listener(current, { source, persisted });
    return current;
  }
  function assertLive() {
    if (destroyed) throw new Error("Settings store has been destroyed");
  }
  function onStorage(event) {
    if (event.storageArea && storage.matchesArea?.(event.storageArea) === false)
      return;
    if (event.key !== SETTINGS_KEY && event.key !== null) return;
    let payload = null;
    try {
      payload =
        event.key === null
          ? storage.read(SETTINGS_KEY)
          : JSON.parse(event.newValue);
    } catch {
      /* Validate corrupt external changes too. */
    }
    current = Object.freeze(decode(payload));
    persisted = storage.available;
    notify("external");
  }
  eventTarget?.addEventListener("storage", onStorage);
  return {
    get: () => current,
    get persisted() {
      return persisted;
    },
    update(patch) {
      assertLive();
      if (!patch || typeof patch !== "object" || Array.isArray(patch))
        throw new TypeError("Settings update must be an object");
      for (const [key, value] of Object.entries(patch)) {
        if (!Object.hasOwn(defaultSettings, key) || !valid(key, value))
          throw new TypeError(`Invalid setting: ${key}`);
      }
      current = Object.freeze({ ...current, ...patch });
      persisted = storage.write(SETTINGS_KEY, {
        version: 1,
        settings: current,
      });
      return notify("local");
    },
    reset() {
      assertLive();
      current = Object.freeze({ ...defaultSettings });
      persisted = storage.remove(SETTINGS_KEY);
      return notify("reset");
    },
    subscribe(listener) {
      assertLive();
      listeners.add(listener);
      listener(current, { source: "initial", persisted });
      return () => listeners.delete(listener);
    },
    destroy() {
      destroyed = true;
      listeners.clear();
      eventTarget?.removeEventListener("storage", onStorage);
    },
  };
}
let sharedStore;
export function getSettingsStore() {
  return (sharedStore ??= createSettingsStore());
}

/** Apply preferences to a document root; return cleanup for SPA lifecycles. */
export function initialize({
  store = getSettingsStore(),
  root = globalThis.document?.documentElement,
  window = globalThis.window,
} = {}) {
  if (!root) throw new Error("A document root is required");
  root.classList.add("ak-ui");
  const dark = window?.matchMedia?.("(prefers-color-scheme: dark)");
  const motion = window?.matchMedia?.("(prefers-reduced-motion: reduce)");
  function apply(settings = store.get()) {
    root.dataset.akTheme =
      settings.theme === "system"
        ? dark?.matches
          ? "dark"
          : "light"
        : settings.theme;
    root.dataset.akMotion =
      settings.reducedMotion === "reduce" || motion?.matches
        ? "reduce"
        : "normal";
    root.style.setProperty("--ak-font-family", fontStacks[settings.font]);
    root.style.setProperty("--ak-text-scale", String(settings.textScale));
    root.style.setProperty("--ak-line-height", String(settings.lineHeight));
    root.style.setProperty(
      "--ak-letter-spacing",
      settings.letterSpacing === "wide" ? "0.04em" : "normal",
    );
  }
  const refresh = () => apply();
  const unsubscribe = store.subscribe(apply);
  for (const media of [dark, motion])
    media?.addEventListener("change", refresh);
  return {
    store,
    destroy() {
      unsubscribe();
      for (const media of [dark, motion])
        media?.removeEventListener("change", refresh);
    },
  };
}
