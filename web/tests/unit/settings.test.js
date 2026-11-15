import assert from "node:assert/strict";
import { test } from "node:test";
import { createSettingsStore, defaultSettings, SETTINGS_KEY } from "../../src/settings.js";
import { createStorage } from "../../src/utilities/storage.js";
import { defineSettingsPanel } from "../../src/settings-panel.js";

function memory() {
  const values = new Map();
  return { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key), values };
}
function setup(backend = memory()) {
  const target = new EventTarget();
  const store = createSettingsStore({ storage: createStorage({ storage: backend }), eventTarget: target });
  return { store, target, backend };
}
function external(target, value, key = SETTINGS_KEY) {
  const event = new Event("storage");
  Object.assign(event, { key, newValue: value });
  target.dispatchEvent(event);
}

test("settings persist validated preferences and return immutable snapshots", () => {
  const { store, backend } = setup();
  assert.deepEqual(store.get(), defaultSettings);
  store.update({ theme: "sepia", font: "atkinson", textScale: 1.5 });
  assert.equal(store.get().theme, "sepia");
  assert.ok(Object.isFrozen(store.get()));
  assert.equal(JSON.parse(backend.getItem(SETTINGS_KEY)).version, 1);
  assert.equal(setup(backend).store.get().textScale, 1.5);
  store.reset();
  assert.deepEqual(store.get(), defaultSettings);
  assert.equal(backend.getItem(SETTINGS_KEY), null);
});

for (const payload of ["broken", "null", '{"version":2,"settings":{"theme":"dark"}}', JSON.stringify({ version: 1, settings: { theme: "url(evil)", font: "untrusted", textScale: 100, vibration: "true", extra: "discard" } })]) {
  test(`corrupt or unsupported stored preferences are discarded: ${payload.slice(0, 40)}`, () => {
    const backend = memory();
    backend.setItem(SETTINGS_KEY, payload);
    assert.deepEqual(setup(backend).store.get(), defaultSettings);
  });
}

for (const patch of [null, [], { theme: "pink" }, { textScale: NaN }, { textScale: 1.1 }, { textScale: 4 }, { lineHeight: 0 }, { vibration: 1 }, { unknown: "x" }, JSON.parse('{"__proto__":{"polluted":true}}')]) {
  test(`invalid updates cannot change state: ${JSON.stringify(patch)}`, () => {
    const { store } = setup();
    assert.throws(() => store.update(patch), TypeError);
    assert.deepEqual(store.get(), defaultSettings);
    assert.equal({}.polluted, undefined);
  });
}

test("denied storage still applies settings in memory", () => {
  const backend = { getItem() { throw new Error("denied"); }, setItem() { throw new Error("quota"); }, removeItem() { throw new Error("denied"); } };
  const { store } = setup(backend);
  assert.equal(store.persisted, false);
  store.update({ theme: "dark" });
  assert.equal(store.get().theme, "dark");
  assert.equal(store.persisted, false);
  store.reset();
  assert.equal(store.get().theme, "system");
});

test("cross-tab changes validate, notify once and never write back", () => {
  const { store, target, backend } = setup();
  const sources = [];
  const stop = store.subscribe((_, meta) => sources.push(meta.source));
  external(target, JSON.stringify({ version: 1, settings: { theme: "contrast" } }));
  assert.equal(store.get().theme, "contrast");
  assert.equal(backend.values.size, 0);
  external(target, "invalid", "unrelated:key");
  assert.equal(sources.length, 2);
  external(target, null);
  assert.equal(store.get().theme, "system");
  stop();
  store.update({ theme: "calm" });
  assert.deepEqual(sources, ["initial", "external", "external"]);
  store.destroy();
  external(target, null);
  assert.equal(store.get().theme, "calm");
  assert.throws(() => store.update({ theme: "light" }), /destroyed/);
});

test("JSON storage tolerates unavailable backends and serialization failures", () => {
  const storage = createStorage({ storage: null });
  assert.equal(storage.read("key", "fallback"), "fallback");
  assert.equal(storage.write("key", {}), false);
  assert.equal(storage.remove("key"), false);
  const working = createStorage({ storage: memory() });
  const circular = {}; circular.self = circular;
  assert.equal(working.write("key", circular), false);
});

test("module import and element registration do not require a DOM", () => {
  assert.equal(defineSettingsPanel({ registry: null, elementBase: null }), false);
});
