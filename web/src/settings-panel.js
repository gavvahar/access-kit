import { getSettingsStore } from "./settings.js";
import { themes } from "./themes.js";

/** Explicit registration is safe to import during server rendering. */
export function defineSettingsPanel({
  store = getSettingsStore(),
  registry = globalThis.customElements,
  elementBase = globalThis.HTMLElement,
} = {}) {
  if (!registry || !elementBase) return false;
  if (registry.get("ak-settings-panel"))
    return registry.get("ak-settings-panel");
  let nextId = 0;
  class SettingsPanel extends elementBase {
    #unsubscribe;
    #abort;
    #rendered = false;
    connectedCallback() {
      if (!this.#rendered) {
        // Static markup only: user values are assigned with DOM properties below.
        this.innerHTML = `<form aria-label="Display settings">
          <fieldset><legend>Appearance</legend>
            <label><span>Theme</span><select name="theme"><option value="system">Follow device</option>${Object.entries(
              themes,
            )
              .map(
                ([value, theme]) =>
                  `<option value="${value}">${theme.label}</option>`,
              )
              .join("")}</select></label>
            <label><span>Font</span><select name="font"><option value="system">Device default</option><option value="atkinson">Atkinson Hyperlegible</option><option value="noto">Noto Sans</option></select></label>
          </fieldset>
          <fieldset><legend>Reading</legend>
            <label><span>Text size <output name="scale" aria-hidden="true">100%</output></span><input name="textScale" type="range" min="0.875" max="3" step="0.125" value="1"></label>
            <label><span>Line spacing</span><select name="lineHeight"><option value="1.5">Comfortable</option><option value="1.7">Roomy</option><option value="2">Extra roomy</option></select></label>
            <label><span>Letter spacing</span><select name="letterSpacing"><option value="normal">Standard</option><option value="wide">Wider</option></select></label>
          </fieldset>
          <fieldset><legend>Motion & feedback</legend>
            <label><span>Animation</span><select name="reducedMotion"><option value="system">Follow device</option><option value="reduce">Reduce motion</option></select></label>
            <label class="ak-check"><input type="checkbox" name="vibration"><span>Allow gentle vibration</span></label>
          </fieldset>
          <p class="ak-settings-note">Changes apply as you go. Preferences stay in this browser.</p>
          <p class="ak-settings-storage" role="status"></p>
          <button type="button" data-ak-reset>Reset preferences</button>
        </form>`;
        const prefix = `ak-settings-${globalThis.crypto?.randomUUID?.() ?? ++nextId}`;
        for (const label of this.querySelectorAll("label")) {
          const control = label.querySelector("select, input");
          control.id = `${prefix}-${control.name}`;
          label.htmlFor = control.id;
          const field = this.ownerDocument.createElement("div");
          field.className = "ak-field";
          label.before(field);
          if (label.classList.contains("ak-check")) {
            field.classList.add("ak-check");
            label.classList.remove("ak-check");
            field.append(control, label);
          } else field.append(label, control);
        }
        this.#rendered = true;
      }
      this.#unsubscribe?.();
      this.#abort?.abort();
      this.#abort = new AbortController();
      const { signal } = this.#abort;
      const form = this.querySelector("form");
      form.addEventListener("submit", (event) => event.preventDefault(), {
        signal,
      });
      const change = (event) => {
        const input = event.target;
        if (!input.name || input.tagName === "OUTPUT") return;
        const value =
          input.type === "checkbox"
            ? input.checked
            : ["textScale", "lineHeight"].includes(input.name)
              ? Number(input.value)
              : input.value;
        if (store.get()[input.name] === value) return;
        const settings = store.update({ [input.name]: value });
        this.dispatchEvent(
          new CustomEvent("ak-settings-change", {
            bubbles: true,
            detail: { settings, persisted: store.persisted },
          }),
        );
      };
      form.addEventListener("change", change, { signal });
      form.addEventListener(
        "input",
        (event) => {
          if (event.target.name === "textScale") change(event);
        },
        { signal },
      );
      form.querySelector("[data-ak-reset]").addEventListener(
        "click",
        () => {
          const settings = store.reset();
          this.dispatchEvent(
            new CustomEvent("ak-settings-change", {
              bubbles: true,
              detail: { settings, persisted: store.persisted },
            }),
          );
        },
        { signal },
      );
      this.#unsubscribe = store.subscribe((settings) => {
        for (const [key, value] of Object.entries(settings)) {
          const control = form.elements.namedItem(key);
          if (control.type === "checkbox") control.checked = value;
          else control.value = String(value);
        }
        form.elements.namedItem("scale").value =
          `${Math.round(settings.textScale * 100)}%`;
        form.elements
          .namedItem("textScale")
          .setAttribute(
            "aria-valuetext",
            `${Math.round(settings.textScale * 100)} percent`,
          );
        form.querySelector(".ak-settings-storage").textContent = store.persisted
          ? ""
          : "Preferences apply for this visit. Browser storage is unavailable.";
      });
    }
    disconnectedCallback() {
      this.#unsubscribe?.();
      this.#abort?.abort();
    }
  }
  registry.define("ak-settings-panel", SettingsPanel);
  return SettingsPanel;
}
