/** JSON storage that degrades to caller-owned memory when browser storage fails. */
export function createStorage(options = {}) {
  let backend = null;
  try {
    backend = Object.hasOwn(options, "storage") ? options.storage : globalThis.localStorage;
  } catch { /* Browsers can deny even access to the localStorage getter. */ }
  let available = Boolean(backend);
  return {
    get available() { return available; },
    read(key, fallback = null) {
      try {
        if (!backend) return fallback;
        const raw = backend.getItem(key);
        available = true;
        return raw === null ? fallback : JSON.parse(raw);
      } catch {
        // Invalid JSON is also handled by falling back; never trust stored data.
        return fallback;
      }
    },
    write(key, value) {
      try {
        if (!backend) return false;
        backend.setItem(key, JSON.stringify(value));
        available = true;
        return true;
      } catch { available = false; return false; }
    },
    remove(key) {
      try {
        if (!backend) return false;
        backend.removeItem(key);
        available = true;
        return true;
      } catch { available = false; return false; }
    },
  };
}
