const documents = new WeakMap();
/** Announce text without moving focus. Repeated calls replace pending messages. */
export function announce(message, { priority = "polite", document = globalThis.document } = {}) {
  if (typeof message !== "string" || !message.trim() || !document?.body) return false;
  if (!["polite", "assertive"].includes(priority)) throw new TypeError("Invalid announcement priority");
  let regions = documents.get(document);
  if (!regions) { regions = {}; documents.set(document, regions); }
  let state = regions[priority];
  if (!state?.element.isConnected) {
    const element = document.createElement("div");
    element.className = "ak-sr-only";
    element.setAttribute("aria-live", priority);
    element.setAttribute("aria-atomic", "true");
    document.body.append(element);
    state = regions[priority] = { element, timer: null };
  }
  clearTimeout(state.timer);
  state.element.textContent = "";
  state.timer = setTimeout(() => { state.element.textContent = message; }, 50);
  return true;
}
