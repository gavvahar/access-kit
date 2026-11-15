import { createSessionTimer } from "./progress.js";

/** Register native, keyboard-friendly activity elements without server-side effects. */
export function defineActivityComponents({
  registry = globalThis.customElements,
  elementBase = globalThis.HTMLElement,
} = {}) {
  if (!registry || !elementBase) return false;
  if (!registry.get("ak-progress")) {
    class Progress extends elementBase {
      static observedAttributes = ["value", "max", "label"];
      connectedCallback() {
        this.render();
      }
      attributeChangedCallback() {
        if (this.isConnected) this.render();
      }
      render() {
        if (!this.firstElementChild) {
          this.innerHTML =
            '<label></label><progress></progress><span class="ak-progress-summary"></span>';
          const id = `ak-progress-${crypto.randomUUID()}`;
          this.querySelector("progress").id = id;
          this.querySelector("label").htmlFor = id;
        }
        const maximum = Number(this.getAttribute("max") ?? 100);
        const total = Number.isFinite(maximum) && maximum > 0 ? maximum : 100;
        const progress = this.querySelector("progress");
        progress.max = total;
        this.querySelector("label").textContent =
          this.getAttribute("label") || "Progress";
        const value = this.hasAttribute("value")
          ? Number(this.getAttribute("value"))
          : NaN;
        const summary = this.querySelector(".ak-progress-summary");
        if (Number.isFinite(value)) {
          progress.value = Math.max(0, Math.min(total, value));
          summary.textContent = `${Math.max(0, value)} of ${total}`;
        } else {
          progress.removeAttribute("value");
          summary.textContent = "In progress";
        }
      }
    }
    registry.define("ak-progress", Progress);
  }
  if (!registry.get("ak-session")) {
    class Session extends elementBase {
      #timer;
      #interval;
      #abort;
      #completed = false;
      connectedCallback() {
        if (!this.firstElementChild)
          this.innerHTML =
            '<p class="ak-session-label"></p><span role="timer" aria-label="Time remaining"></span><p class="ak-session-status" role="status"></p><div class="ak-session-actions"><button type="button" data-start>Start</button><button type="button" data-pause disabled>Pause</button><button type="button" data-reset>Start over</button></div>';
        const minutes = Number(this.getAttribute("minutes") ?? 5);
        const seconds = Math.max(
          1,
          Math.min(
            3600,
            Number.isFinite(minutes) && minutes > 0 ? minutes * 60 : 300,
          ),
        );
        this.#timer ??= createSessionTimer({ seconds });
        this.#abort?.abort();
        this.#abort = new AbortController();
        const { signal } = this.#abort;
        this.querySelector("[data-start]").addEventListener(
          "click",
          () => {
            this.#timer.start();
            clearInterval(this.#interval);
            this.#interval = setInterval(() => this.render(), 250);
            this.render();
          },
          { signal },
        );
        this.querySelector("[data-pause]").addEventListener(
          "click",
          () => this.pause(),
          { signal },
        );
        this.querySelector("[data-reset]").addEventListener(
          "click",
          () => {
            clearInterval(this.#interval);
            this.#timer.reset();
            this.#completed = false;
            this.render();
          },
          { signal },
        );
        this.ownerDocument.addEventListener(
          "visibilitychange",
          () => {
            if (this.ownerDocument.hidden) this.pause();
          },
          { signal },
        );
        this.render();
      }
      pause() {
        this.#timer?.pause();
        clearInterval(this.#interval);
        this.render();
      }
      disconnectedCallback() {
        this.#timer?.pause();
        clearInterval(this.#interval);
        this.#abort?.abort();
      }
      render() {
        if (!this.#timer) return;
        const state = this.#timer.get();
        this.querySelector(".ak-session-label").textContent =
          this.getAttribute("label") || "A short session";
        this.querySelector('[role="timer"]').textContent =
          `${Math.floor(state.remaining / 60)}:${String(state.remaining % 60).padStart(2, "0")}`;
        this.querySelector("[data-start]").disabled =
          state.status === "running" || state.status === "complete";
        this.querySelector("[data-start]").textContent =
          state.status === "paused" ? "Continue" : "Start";
        this.querySelector("[data-pause]").disabled =
          state.status !== "running";
        const words = {
          idle: "One small step is enough.",
          running: "Take it at your own pace.",
          paused: "Paused. What you’ve done still counts.",
          complete: "Session complete. That counts.",
        };
        const status = this.querySelector(".ak-session-status");
        if (status.textContent !== words[state.status])
          status.textContent = words[state.status];
        if (state.status === "complete") {
          clearInterval(this.#interval);
          if (!this.#completed) {
            this.#completed = true;
            this.dispatchEvent(
              new CustomEvent("ak-session-complete", {
                bubbles: true,
                detail: state,
              }),
            );
          }
        }
      }
    }
    registry.define("ak-session", Session);
  }
  if (!registry.get("ak-celebrate")) {
    class Celebrate extends elementBase {
      connectedCallback() {
        if (!this.firstElementChild)
          this.innerHTML =
            '<span class="ak-celebrate-mark" aria-hidden="true">✓</span><span role="status" aria-atomic="true"></span>';
        this.classList.toggle(
          "ak-celebrate-visible",
          Boolean(this.querySelector('[role="status"]').textContent),
        );
      }
      celebrate(message = "That counts. Nice work.") {
        if (
          typeof message !== "string" ||
          !message.trim() ||
          message.length > 180
        )
          throw new TypeError("Use a short celebration message");
        if (!this.firstElementChild) this.connectedCallback();
        this.querySelector('[role="status"]').textContent = message;
        this.classList.add("ak-celebrate-visible");
      }
      clear() {
        if (this.firstElementChild)
          this.querySelector('[role="status"]').textContent = "";
        this.classList.remove("ak-celebrate-visible");
      }
    }
    registry.define("ak-celebrate", Celebrate);
  }
  return true;
}
