import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

for (const theme of ["light", "dark", "sepia", "contrast", "calm"]) {
  test(`${theme} theme passes axe including color contrast`, async ({
    page,
  }) => {
    await page.goto("/");
    await page.getByLabel("Theme", { exact: true }).selectOption(theme);
    await expect(page.locator("html")).toHaveAttribute("data-ak-theme", theme);
    const results = await new AxeBuilder({ page }).analyze();
    expect(results.violations).toEqual([]);
  });
}

test("native keyboard controls keep focus and survive reload", async ({
  page,
}) => {
  await page.goto("/");
  const theme = page.getByLabel("Theme", { exact: true });
  await theme.focus();
  await page.keyboard.press("End");
  await expect(theme).toHaveValue("calm");
  await page.keyboard.press("Tab");
  await expect(page.getByLabel("Font", { exact: true })).toBeFocused();
  const slider = page.getByRole("slider", { name: /Text size/ });
  await slider.focus();
  await page.keyboard.press("ArrowRight");
  await expect(slider).toHaveAttribute("aria-valuetext", "113 percent");
  await expect(slider).toBeFocused();
  await page.reload();
  await expect(theme).toHaveValue("calm");
  await expect(slider).toHaveValue("1.125");
  await page.getByRole("button", { name: "Reset preferences" }).click();
  await expect(theme).toHaveValue("system");
  await expect(slider).toHaveValue("1");
});

test("device color and motion preferences remain respected", async ({
  page,
}) => {
  await page.emulateMedia({ colorScheme: "dark", reducedMotion: "reduce" });
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("data-ak-theme", "dark");
  await expect(page.locator("html")).toHaveAttribute(
    "data-ak-motion",
    "reduce",
  );
  await page.getByLabel("Theme", { exact: true }).selectOption("sepia");
  await page.emulateMedia({ colorScheme: "light", reducedMotion: "reduce" });
  await expect(page.locator("html")).toHaveAttribute("data-ak-theme", "sepia");
  await expect(page.locator("html")).toHaveAttribute(
    "data-ak-motion",
    "reduce",
  );
});

test("two panels synchronize and reconnect without duplicate subscriptions", async ({
  page,
}) => {
  await page.goto("/");
  await page.evaluate(() => {
    const panel = document.createElement("ak-settings-panel");
    document.querySelector("#preferences").append(panel);
    panel.remove();
    document.querySelector("#preferences").append(panel);
    window.settingsEvents = 0;
    document.addEventListener(
      "ak-settings-change",
      () => window.settingsEvents++,
    );
  });
  const panels = page.locator("ak-settings-panel");
  await panels.nth(1).getByLabel("Theme", { exact: true }).selectOption("dark");
  await expect(panels.nth(0).getByLabel("Theme", { exact: true })).toHaveValue(
    "dark",
  );
  expect(await page.evaluate(() => window.settingsEvents)).toBe(1);
});

test("settings synchronize between tabs", async ({ page, context }) => {
  await page.goto("/");
  const second = await context.newPage();
  await second.goto("/");
  await page.getByLabel("Theme", { exact: true }).selectOption("contrast");
  await expect(second.locator("html")).toHaveAttribute(
    "data-ak-theme",
    "contrast",
  );
  await page.getByRole("button", { name: "Reset preferences" }).click();
  await expect(second.getByLabel("Theme", { exact: true })).toHaveValue(
    "system",
  );
});

test("storage denial is visible and changes still work", async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(window, "localStorage", {
      get() {
        throw new DOMException("Denied", "SecurityError");
      },
    });
  });
  await page.goto("/");
  await page.getByLabel("Theme", { exact: true }).selectOption("dark");
  await expect(page.locator("html")).toHaveAttribute("data-ak-theme", "dark");
  await expect(
    page.getByText(
      "Preferences apply for this visit. Browser storage is unavailable.",
    ),
  ).toBeVisible();
});

test("fonts load only from the same origin", async ({ page }) => {
  const remote = [];
  page.on("request", (request) => {
    if (new URL(request.url()).origin !== "http://127.0.0.1:4173")
      remote.push(request.url());
  });
  await page.goto("/");
  for (const [value, family] of [
    ["atkinson", "AK Atkinson"],
    ["noto", "AK Noto Sans"],
  ]) {
    await page.getByLabel("Font", { exact: true }).selectOption(value);
    expect(
      await page.evaluate(async (family) => {
        await document.fonts.load(`18px "${family}"`);
        return document.fonts.check(`18px "${family}"`);
      }, family),
    ).toBe(true);
  }
  expect(remote).toEqual([]);
});

for (const direction of ["ltr", "rtl"]) {
  test(`320px mobile layout at 300% text size, ${direction}`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: 320, height: 800 });
    await page.goto("/");
    await page.evaluate((direction) => {
      document.documentElement.dir = direction;
    }, direction);
    await page.getByRole("slider", { name: /Text size/ }).fill("3");
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  });
}

test("announcements are text-only, repeatable and preserve focus", async ({
  page,
}) => {
  await page.goto("/");
  const button = page.getByRole("button", {
    name: "Test screen reader message",
  });
  await button.click();
  await expect(page.locator('[aria-live="polite"]')).toHaveText(
    "This is your space. Take it at your own pace.",
  );
  await expect(button).toBeFocused();
  await page.evaluate(async () => {
    const { announce } = await import("/dist/access-kit.js");
    announce("<img src=x onerror=alert(1)>");
  });
  await expect(page.locator('[aria-live="polite"]')).toHaveText(
    "<img src=x onerror=alert(1)>",
  );
  await expect(page.locator('[aria-live="polite"] img')).toHaveCount(0);
});

test("unsupported hardware is explained without starting it automatically", async ({
  page,
}) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "wakeLock", { value: undefined });
    Object.defineProperty(navigator, "vibrate", { value: undefined });
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Keep screen awake" }).click();
  await expect(page.locator("#utility-status")).toContainText("unavailable");
  await page.getByRole("button", { name: "Try gentle vibration" }).click();
  await expect(page.locator("#utility-status")).toContainText(
    "Enable gentle vibration",
  );
  await page.getByLabel("Allow gentle vibration").check();
  await page.getByRole("button", { name: "Try gentle vibration" }).click();
  await expect(page.locator("#utility-status")).toContainText("unavailable");
});

test("back-forward cache lifecycle keeps preference application alive", async ({
  page,
}) => {
  await page.goto("/");
  await page.evaluate(() =>
    window.dispatchEvent(
      new PageTransitionEvent("pagehide", { persisted: true }),
    ),
  );
  await page.getByLabel("Theme", { exact: true }).selectOption("calm");
  await expect(page.locator("html")).toHaveAttribute("data-ak-theme", "calm");
});

test("earned progress and celebrations are accessible and text-only", async ({
  page,
}) => {
  await page.goto("/");
  const progress = page.getByRole("progressbar", { name: "Small steps today" });
  await page
    .getByRole("button", { name: "Add one step" })
    .click({ clickCount: 5 });
  await expect(progress).toHaveAttribute("value", "5");
  await expect(page.locator("ak-celebrate")).toContainText("Five small steps");
  await page
    .locator("#demo-goal")
    .evaluate((element) => element.setAttribute("max", "2"));
  await expect(page.locator("#demo-goal")).toContainText("5 of 2");
  await page
    .locator("ak-celebrate")
    .evaluate((element) => element.celebrate('<img src=x onerror="alert(1)">'));
  await expect(page.locator("ak-celebrate img")).toHaveCount(0);
  await expect(page.locator("ak-celebrate")).toContainText("<img");
  await page.getByRole("button", { name: "Reset step count" }).click();
  await expect(progress).toHaveAttribute("value", "0");
});

test("micro-sessions require intent, preserve pauses and clean up on reconnect", async ({
  page,
}) => {
  await page.clock.install();
  await page.goto("/");
  const session = page.locator("ak-session");
  await expect(session.getByRole("timer")).toHaveText("5:00");
  await page.clock.fastForward(60_000);
  await expect(session.getByRole("timer")).toHaveText("5:00");
  await session.getByRole("button", { name: "Start", exact: true }).click();
  await page.clock.fastForward(30_000);
  await session.getByRole("button", { name: "Pause", exact: true }).click();
  await expect(session.getByRole("timer")).toHaveText("4:30");
  await page.clock.fastForward(60_000);
  await expect(session.getByRole("timer")).toHaveText("4:30");
  await session.evaluate((element) => {
    const parent = element.parentNode;
    element.remove();
    parent.append(element);
  });
  await session.getByRole("button", { name: "Continue" }).click();
  await page.clock.fastForward(270_000);
  await expect(session).toContainText("Session complete");
  await expect(page.locator("ak-celebrate")).toContainText("small step");
  await session.getByRole("button", { name: "Start over" }).click();
  await expect(session.getByRole("timer")).toHaveText("5:00");
});
