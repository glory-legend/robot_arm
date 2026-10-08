import { test, expect, type Page } from "@playwright/test";
async function ready(page: Page) {
  await page.goto("/concept.html");
  await expect(page.locator("#play")).toBeEnabled({ timeout: 60000 });
}
async function seek(page: Page, time: number) {
  await page.locator("#timeline").fill(String(time));
}
test("full scene, phase seeking, camera controls and head handoff", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await ready(page);
  await expect(page.locator("canvas")).toBeVisible();
  await page.screenshot({ path: "test-results/whole.png" });
  await seek(page, 13);
  await expect(page.locator("#phase-title")).toHaveText("보조 엄지로 세우기");
  await page.getByRole("button", { name: "그리퍼 확대", exact: true }).click();
  await expect(page.locator("#current-time")).toHaveText("13.0");
  await page.screenshot({ path: "test-results/alignment.png" });
  await seek(page, 16);
  await page.screenshot({ path: "test-results/handoff.png" });
  await page.locator("#exploded").check();
  await expect(
    page.getByRole("button", { name: "재생", exact: true }),
  ).toBeVisible();
  await page.screenshot({ path: "test-results/exploded.png" });
  await page.getByRole("button", { name: "재생", exact: true }).click();
  await expect(page.locator("#exploded")).not.toBeChecked();
  await page.getByRole("button", { name: "일시정지", exact: true }).click();
  await page.locator("#transparent").uncheck();
  await page.locator("#transparent").check();
  await seek(page, 27);
  await page.screenshot({ path: "test-results/fastening.png" });
  for (const id of ["m6", "m8", "m10"]) {
    await page.locator("#bolt").selectOption(id);
    await expect(page.locator("#current-time")).toHaveText("00.0");
    for (const time of [5, 13, 16, 18, 40, 63, 70]) await seek(page, time);
  }
  await page.getByRole("button", { name: "처음으로", exact: true }).click();
  await expect(page.locator("#timeline")).toHaveValue("0");
  expect(errors).toEqual([]);
});
test("playback reaches the endpoint and stays stopped", async ({ page }) => {
  await ready(page);
  await seek(page, 68);
  await page.locator("#speed").selectOption("2");
  await page.getByRole("button", { name: "재생", exact: true }).click();
  await expect(page.locator("#current-time")).toHaveText("70.0", {
    timeout: 15000,
  });
  await expect(
    page.getByRole("button", { name: "재생", exact: true }),
  ).toBeVisible();
  await expect(page.locator("#app-status")).toContainText("사이클 완료");
});
test("narrow screen, keyboard controls, reduced motion and native select", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await ready(page);
  await page.screenshot({ path: "test-results/mobile.png", fullPage: true });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.locator("#timeline").focus();
  await page.keyboard.press("End");
  await expect(page.locator("#current-time")).toHaveText("70.0");
  await page.locator("#bolt").focus();
  await page.keyboard.press("Home");
  await page.keyboard.press("Enter");
  await expect(page.locator("#bolt")).toHaveValue("m6");
  await page.getByRole("button", { name: "시점 왼쪽으로 회전" }).click();
});
test("asset failure displays a retry action and disables playback", async ({
  page,
}) => {
  await page.route("**/fr3/link0.dae", (r) => r.abort());
  await page.goto("/concept.html");
  await expect(page.getByRole("button", { name: "다시 불러오기" })).toBeVisible(
    { timeout: 15000 },
  );
  await expect(page.locator("#play")).toBeDisabled();
});
test("WebGL initialization failure displays a useful error", async ({
  page,
}) => {
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (
      this: HTMLCanvasElement,
      type: string,
      ...args: unknown[]
    ) {
      if (
        type === "webgl2" ||
        type === "webgl" ||
        type === "experimental-webgl"
      )
        return null;
      return original.apply(this, [type, ...args] as never);
    } as typeof original;
  });
  await page.goto("/concept.html");
  await expect(
    page.getByRole("button", { name: "다시 불러오기" }),
  ).toBeVisible();
  await expect(page.locator("#loading")).toContainText("WebGL");
});

test("loaded interface has no automated WCAG A/AA violations", async ({
  page,
}) => {
  await ready(page);
  const { default: AxeBuilder } = await import("@axe-core/playwright");
  const result = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(
    result.violations.map((v) => ({
      id: v.id,
      nodes: v.nodes.map((n) => n.target),
    })),
  ).toEqual([]);
});

test("complete continuous cycle runs with the full arm visible", async ({
  page,
}) => {
  await ready(page);
  await page.locator("#speed").selectOption("2");
  await page.getByRole("button", { name: "재생", exact: true }).click();
  await expect(page.locator("#current-time")).toHaveText("70.0", {
    timeout: 60000,
  });
  await expect(page.locator("#app-status")).toContainText("사이클 완료");
  await page.screenshot({ path: "test-results/completed.png" });
});

test("cached-page lifecycle retains live rendering and resize controls", async ({
  page,
}) => {
  await ready(page);
  await page.evaluate(() =>
    window.dispatchEvent(
      new PageTransitionEvent("pagehide", { persisted: true }),
    ),
  );
  await page.setViewportSize({ width: 1200, height: 900 });
  await expect
    .poll(() =>
      page.locator("canvas").evaluate((canvas) => {
        const c = canvas as HTMLCanvasElement;
        return (
          Math.abs(
            c.width -
              document.getElementById("viewport")!.clientWidth *
                Math.min(window.devicePixelRatio, 1.75),
          ) < 2
        );
      }),
    )
    .toBe(true);
  await page.getByRole("button", { name: "그리퍼 확대", exact: true }).click();
  await seek(page, 14);
  await expect(page.locator("#phase-title")).toHaveText("헤드 척 닫기");
});

test("R05 detail link opens righting and includes local provenance", async ({
  page,
}) => {
  await page.goto("/concept.html?view=detail&time=10");
  await expect(page.locator("#play")).toBeEnabled({ timeout: 60000 });
  await expect(page.locator('[data-view="detail"]')).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await expect(page.locator("#current-time")).toHaveText("10.0");
  await expect(page.locator("#transparent")).not.toBeChecked();
  await expect(page.locator("#phase-description")).toContainText("보조 엄지");
  const notice = await page.request.get("/fr3/NOTICE");
  expect(notice.ok()).toBe(true);
  expect(await notice.text()).toContain("Franka");
  const gripperNotice = await page.request.get("/robotiq-2f85/NOTICE");
  expect(gripperNotice.ok()).toBe(true);
  expect(await gripperNotice.text()).toContain("PickNik");
  const mesh = await page.request.get("/robotiq-2f85/meshes/robotiq_base.dae");
  expect(mesh.ok()).toBe(true);
  expect(await mesh.text()).toContain("COLLADA");
});

test("shows the main fingers and auxiliary thumb with the pivot-pad state", async ({
  page,
}) => {
  await ready(page);
  await page.getByRole("button", { name: "그리퍼 확대", exact: true }).click();
  await seek(page, 12);
  await expect(
    page.getByText("A · 날렵한 수납 팁", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("보조 엄지 · 50mm", { exact: true }),
  ).toBeVisible();
  await expect(page.locator("#grip-state")).toContainText("회전 패드");
  await seek(page, 15);
  await expect(page.locator("#grip-state")).toContainText("몸통 파지 유지");
});

test("two designs preserve the compared phase and expose their distinct mechanisms", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/concept.html?view=detail&variant=b&time=18");
  await expect(page.locator("#play")).toBeEnabled({ timeout: 60000 });
  await expect(page.locator("#variant-b")).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await expect(page.locator("#variant-structure")).toContainText("2단 접촉면");
  await page.locator("#variant-a").click();
  await expect(page.locator("#current-time")).toHaveText("18.0");
  await expect(page.locator("#variant-structure")).toContainText("6조 척");
  for (const variant of ["a", "b"]) {
    await page.locator("#variant-" + variant).click();
    for (const spec of ["m6", "m8", "m10"]) {
      await page.locator("#bolt").selectOption(spec);
      for (const t of [5, 12, 16, 18, 40, 62, 65, 70]) await seek(page, t);
    }
    await page.locator("#compare-handoff").click();
    await expect(page.locator("#current-time")).toHaveText("17.8");
    await page.screenshot({ path: `test-results/r06-${variant}.png` });
  }
  expect(errors).toEqual([]);
});
