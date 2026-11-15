import assert from "node:assert/strict";
import { test } from "node:test";
import { createProgress, createSessionTimer } from "../../src/progress.js";
import { defineActivityComponents } from "../../src/activity-components.js";

test("earned progress survives target changes and resets only explicitly", () => {
  const goal = createProgress({ target: 3 });
  assert.equal(goal.add(2).completed, 2);
  assert.equal(goal.setTarget(1).complete, true);
  assert.equal(goal.setTarget(4).completed, 2);
  assert.equal(goal.add(3).completed, 5);
  assert.equal(goal.get().remaining, 0);
  assert.ok(Object.isFrozen(goal.get()));
  for (const amount of [-1, NaN, Infinity, 0.5, 1_000_001])
    assert.throws(() => goal.add(amount));
  assert.throws(() => goal.setTarget(0));
  assert.equal(goal.get().completed, 5);
  assert.equal(goal.reset().completed, 0);
});

test("session pauses preserve work and background clock jumps do not drift", () => {
  let clock = 0;
  const timer = createSessionTimer({ seconds: 60, now: () => clock });
  assert.equal(timer.get().status, "idle");
  timer.start();
  clock = 12_000;
  assert.equal(timer.pause().remaining, 48);
  clock = 900_000;
  assert.equal(timer.get().remaining, 48);
  timer.start();
  clock += 50_000;
  assert.equal(timer.get().status, "complete");
  assert.equal(timer.start().status, "complete");
  assert.equal(timer.reset().status, "idle");
  assert.throws(() => createSessionTimer({ seconds: 0 }));
  assert.equal(defineActivityComponents(), false);
});
