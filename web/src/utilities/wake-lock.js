/** Explicit screen wake-lock intent with lifecycle cleanup and visibility recovery. */
export function createWakeLock({ navigator = globalThis.navigator, document = globalThis.document } = {}) {
  let wanted = false;
  let disposed = false;
  let lock = null;
  let pending = null;
  const supported = typeof navigator?.wakeLock?.request === "function" && Boolean(document);
  async function releaseSentinel(sentinel) { try { await sentinel.release(); } catch { /* Already released or denied by the platform. */ } }
  async function acquire() {
    if (disposed || !wanted || !supported || document.visibilityState !== "visible") return false;
    if (lock && !lock.released) return true;
    if (pending) return pending;
    pending = (async () => {
      try {
        const sentinel = await navigator.wakeLock.request("screen");
        if (disposed || !wanted || document.visibilityState !== "visible") { await releaseSentinel(sentinel); return false; }
        lock = sentinel;
        sentinel.addEventListener("release", () => { if (lock === sentinel) lock = null; }, { once: true });
        return true;
      } catch { return false; }
      finally { pending = null; }
    })();
    return pending;
  }
  async function release() {
    wanted = false;
    const previous = lock;
    lock = null;
    if (previous) await releaseSentinel(previous);
    if (pending) await pending;
  }
  const onVisibility = () => { if (wanted && document.visibilityState === "visible") void acquire(); };
  const onPageHide = () => { void release(); };
  document?.addEventListener("visibilitychange", onVisibility);
  document?.defaultView?.addEventListener("pagehide", onPageHide);
  return {
    supported,
    get active() { return Boolean(lock && !lock.released); },
    request() { wanted = true; return acquire(); },
    release,
    async destroy() {
      disposed = true;
      document?.removeEventListener("visibilitychange", onVisibility);
      document?.defaultView?.removeEventListener("pagehide", onPageHide);
      await release();
    },
  };
}
