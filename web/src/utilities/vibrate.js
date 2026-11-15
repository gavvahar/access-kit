/** Haptics require explicit opt-in. Unsupported/denied hardware returns false. */
export function vibrate(pattern = 20, { enabled = false, navigator = globalThis.navigator } = {}) {
  if (!enabled || typeof navigator?.vibrate !== "function") return false;
  const values = Array.isArray(pattern) ? pattern : [pattern];
  if (!values.length || values.length > 9 || values.some(value => !Number.isInteger(value) || value < 0 || value > 200) || values.reduce((sum, value) => sum + value, 0) > 1000) return false;
  try { return navigator.vibrate(pattern); } catch { return false; }
}
