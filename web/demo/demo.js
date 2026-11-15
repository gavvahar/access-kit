import {
  announce,
  createProgress,
  defineActivityComponents,
  createWakeLock,
  defineSettingsPanel,
  initialize,
  vibrate,
} from "../dist/access-kit.js";

const runtime = initialize();
defineSettingsPanel({ store: runtime.store });
const wake = createWakeLock();
const status = document.querySelector("#utility-status");
const wakeButton = document.querySelector('[data-action="wake"]');
document
  .querySelector('[data-action="announce"]')
  .addEventListener("click", () => {
    announce("This is your space. Take it at your own pace.");
    status.textContent =
      "A message was sent to the screen reader. Your focus stays here.";
  });
wake.subscribe(({ active }) => {
  wakeButton.setAttribute("aria-pressed", String(active));
  wakeButton.textContent = active ? "Let screen sleep" : "Keep screen awake";
});
wakeButton.addEventListener("click", async () => {
  if (wake.active) {
    await wake.release();
    wakeButton.setAttribute("aria-pressed", "false");
    wakeButton.textContent = "Keep screen awake";
    status.textContent = "Screen wake lock released.";
  } else {
    const active = await wake.request();
    wakeButton.setAttribute("aria-pressed", String(active));
    wakeButton.textContent = active ? "Let screen sleep" : "Keep screen awake";
    status.textContent = active
      ? "This screen can stay awake while the page is visible."
      : "Screen wake lock is unavailable or was declined. This page still works.";
  }
});
document
  .querySelector('[data-action="vibrate"]')
  .addEventListener("click", () => {
    const enabled = runtime.store.get().vibration;
    const accepted = vibrate(30, { enabled });
    status.textContent = !enabled
      ? "Enable gentle vibration in display settings first."
      : accepted
        ? "Vibration requested. Some devices may not provide feedback."
        : "Vibration is unavailable or was declined on this device.";
  });
window.addEventListener("pagehide", (event) => {
  if (!event.persisted) {
    void wake.destroy();
    runtime.destroy();
  }
});

defineActivityComponents();
const goal = createProgress({ target: 5 });
const goalElement = document.querySelector("#demo-goal");
const celebration = document.querySelector("ak-celebrate");
document.querySelector("[data-add-step]").addEventListener("click", () => {
  const state = goal.add();
  goalElement.setAttribute("value", state.completed);
  if (state.complete) celebration.celebrate("Five small steps. That counts.");
});
document.querySelector("[data-reset-goal]").addEventListener("click", () => {
  goal.reset();
  goalElement.setAttribute("value", 0);
  celebration.clear();
});
document
  .querySelector("ak-session")
  .addEventListener("ak-session-complete", () =>
    celebration.celebrate("You made time for a small step. That counts."),
  );
