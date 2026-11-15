import {
  defineSettingsPanel,
  defineActivityComponents,
  initialize,
} from "./index.js";
export const accessKit = typeof document === "undefined" ? null : initialize();
if (accessKit) {
  defineSettingsPanel({ store: accessKit.store });
  defineActivityComponents();
}
