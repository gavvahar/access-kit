import assert from "node:assert/strict";
import { test } from "node:test";
import { createWakeLock } from "../../src/utilities/wake-lock.js";
import { announce } from "../../src/utilities/announce.js";
import { vibrate } from "../../src/utilities/vibrate.js";

class Sentinel extends EventTarget {
  released = false;
  async release() {
    this.released = true;
    this.dispatchEvent(new Event("release"));
  }
}
function hardware(request) {
  const document = new EventTarget();
  document.defaultView = new EventTarget();
  document.visibilityState = "visible";
  const locks = [];
  const manager = createWakeLock({
    document,
    navigator: {
      wakeLock: {
        request:
          request ??
          (async () => {
            const lock = new Sentinel();
            locks.push(lock);
            return lock;
          }),
      },
    },
  });
  return { manager, document, locks };
}

test("wake lock requires explicit intent and is released on cleanup", async () => {
  const { manager, locks } = hardware();
  assert.equal(locks.length, 0);
  assert.equal(await manager.request(), true);
  assert.equal(await manager.request(), true);
  assert.equal(locks.length, 1);
  await manager.destroy();
  assert.equal(locks[0].released, true);
  assert.equal(manager.active, false);
  assert.equal(await manager.request(), false);
});

test("wake lock re-acquires after the system releases it while hidden", async () => {
  const { manager, document, locks } = hardware();
  await manager.request();
  document.visibilityState = "hidden";
  await locks[0].release();
  document.dispatchEvent(new Event("visibilitychange"));
  assert.equal(locks.length, 1);
  document.visibilityState = "visible";
  document.dispatchEvent(new Event("visibilitychange"));
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(locks.length, 2);
  assert.equal(manager.active, true);
  await manager.release();
  document.dispatchEvent(new Event("visibilitychange"));
  assert.equal(locks.length, 2);
  await manager.destroy();
});

test("pending acquisition is released if the user cancels", async () => {
  let resolve;
  const sentinel = new Sentinel();
  const { manager } = hardware(
    () =>
      new Promise((ready) => {
        resolve = ready;
      }),
  );
  const requested = manager.request();
  await Promise.resolve();
  const released = manager.release();
  resolve(sentinel);
  assert.equal(await requested, false);
  await released;
  assert.equal(sentinel.released, true);
  assert.equal(manager.active, false);
});

test("denied hardware can retry; unsupported hardware is a safe no-op", async () => {
  let calls = 0;
  const { manager } = hardware(() => {
    if (++calls === 1) throw new Error("policy");
    return Promise.resolve(new Sentinel());
  });
  assert.equal(await manager.request(), false);
  assert.equal(await manager.request(), true);
  await manager.destroy();
  const unavailable = createWakeLock({ navigator: {}, document: null });
  assert.equal(unavailable.supported, false);
  assert.equal(await unavailable.request(), false);
  await unavailable.destroy();
});

test("haptics are opt-in and bounded", () => {
  const calls = [];
  const navigator = {
    vibrate: (value) => {
      calls.push(value);
      return true;
    },
  };
  assert.equal(vibrate(20, { navigator }), false);
  assert.equal(vibrate([20, 30, 20], { enabled: true, navigator }), true);
  for (const pattern of [
    -1,
    300,
    [],
    [NaN],
    [20.5],
    Array(10).fill(1),
    Array(9).fill(200),
  ])
    assert.equal(vibrate(pattern, { enabled: true, navigator }), false);
  assert.deepEqual(calls, [[20, 30, 20]]);
  assert.equal(vibrate(20, { enabled: true, navigator: {} }), false);
  assert.equal(
    vibrate(20, {
      enabled: true,
      navigator: {
        vibrate() {
          throw new Error("denied");
        },
      },
    }),
    false,
  );
});

test("announcements do not require a browser on import", () => {
  assert.equal(announce("message", { document: null }), false);
  assert.equal(announce("", { document: {} }), false);
});

test("wake lock subscribers observe automatic release", async () => {
  const { manager, locks } = hardware();
  const states = [];
  const stop = manager.subscribe((state) => states.push(state.active));
  await Promise.all([manager.request(), manager.request()]);
  assert.equal(locks.length, 1);
  await locks[0].release();
  assert.deepEqual(states, [false, true, false]);
  stop();
  await manager.destroy();
});
