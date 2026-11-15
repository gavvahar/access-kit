/** Forgiving goal progress: target changes and pauses never erase completed work. */
export function createProgress({ target = 5, completed = 0 } = {}) {
  const valid = (value) =>
    Number.isSafeInteger(value) && value >= 0 && value <= 1_000_000;
  if (!valid(target) || target === 0 || !valid(completed))
    throw new TypeError("Use bounded whole-number progress");
  const snapshot = () =>
    Object.freeze({
      target,
      completed,
      remaining: Math.max(0, target - completed),
      complete: completed >= target,
    });
  return {
    get: snapshot,
    add(amount = 1) {
      if (!valid(amount) || !valid(completed + amount))
        throw new TypeError("Progress must be a nonnegative whole number");
      completed += amount;
      return snapshot();
    },
    setTarget(value) {
      if (!valid(value) || value === 0)
        throw new TypeError("Target must be positive");
      target = value;
      return snapshot();
    },
    reset() {
      completed = 0;
      return snapshot();
    },
  };
}

/** Clock-based timer; interval throttling does not accumulate drift. */
export function createSessionTimer({
  seconds = 300,
  now = () => performance.now(),
} = {}) {
  if (!Number.isFinite(seconds) || seconds < 1 || seconds > 3600)
    throw new TypeError("Session duration must be 1..3600 seconds");
  let elapsed = 0;
  let started = 0;
  let status = "idle";
  function get() {
    const total = Math.min(
      seconds * 1000,
      elapsed + (status === "running" ? Math.max(0, now() - started) : 0),
    );
    if (total >= seconds * 1000) {
      elapsed = total;
      status = "complete";
    }
    return Object.freeze({
      status,
      seconds,
      elapsed: total / 1000,
      remaining: Math.max(0, Math.ceil(seconds - total / 1000)),
    });
  }
  return {
    get,
    start() {
      get();
      if (status === "idle" || status === "paused") {
        started = now();
        status = "running";
      }
      return get();
    },
    pause() {
      const current = get();
      if (status === "running") {
        elapsed = current.elapsed * 1000;
        status = "paused";
      }
      return get();
    },
    reset() {
      elapsed = 0;
      status = "idle";
      return get();
    },
  };
}
