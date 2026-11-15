/** JSON storage that degrades to caller-owned memory when browser storage fails. */
export function createStorage(options = {}) {
  let backend = null;
  try {
    backend = Object.hasOwn(options, "storage")
      ? options.storage
      : globalThis.localStorage;
  } catch {
    /* Browsers can deny even access to the localStorage getter. */
  }
  let available = Boolean(backend);
  return {
    get available() {
      return available;
    },
    read(key, fallback = null) {
      if (!backend) return fallback;
      let raw;
      try {
        raw = backend.getItem(key);
        available = true;
      } catch {
        available = false;
        return fallback;
      }
      if (typeof raw !== "string" || raw.length > 65_536) return fallback;
      try {
        return JSON.parse(raw);
      } catch {
        return fallback;
      }
    },
    write(key, value) {
      try {
        if (!backend) return false;
        const serialized = JSON.stringify(value);
        if (typeof serialized !== "string" || serialized.length > 65_536)
          return false;
        backend.setItem(key, serialized);
        available = true;
        return true;
      } catch {
        available = false;
        return false;
      }
    },
    remove(key) {
      try {
        if (!backend) return false;
        backend.removeItem(key);
        available = true;
        return true;
      } catch {
        available = false;
        return false;
      }
    },
  };
}
