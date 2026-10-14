import { test, expect } from "@playwright/test";
test("assembly variants keep the compared state, cover all sizes, and export review artifacts", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/engineering.html?variant=b&progress=50");
  await expect(page.locator("#variant-b")).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await expect(page.locator("#axis-count")).toHaveText("5");
  await expect(page.locator("#phase-title")).toHaveText("내부 척으로 인계");
  for (const variant of ["a", "b"]) {
    await page.locator("#variant-" + variant).click();
    await expect(page.locator("#motion")).toHaveValue("50");
    for (const spec of ["m6", "m8", "m10"]) {
      await page.locator("#bolt").selectOption(spec);
      for (const t of [0, 28, 50, 75, 90])
        await page.locator("#motion").fill(String(t));
      await expect(page.locator("#phase-title")).toHaveText(
        "고정 외장 안에서 회전",
      );
      await page.locator("#motion").fill("50");
    }
  }
  await page.locator("#transparent").check();
  await page.locator("#explode").check();
  await page.locator("#play").click();
  await expect(page.locator("#explode")).not.toBeChecked();
  await page.locator("#reset").click();
  await expect(page.locator("#motion")).toHaveValue("0");
  const csvPromise = page.waitForEvent("download");
  await page.locator("#export-bom").click();
  const csv = await csvPromise;
  expect(csv.suggestedFilename()).toBe("R07-component-review.csv");
  const glbPromise = page.waitForEvent("download");
  await page.locator("#export-model").click();
  const glb = await glbPromise;
  expect(glb.suggestedFilename()).toContain("R07-b-m10");
  await expect(page.locator("#export-status")).toContainText("저장했습니다");
  expect(errors).toEqual([]);
});
test("assembly controls remain usable on a narrow screen", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/engineering.html");
  await expect(page.locator("canvas")).toBeVisible();
  await page.locator("#variant-b").click();
  await expect(page.locator("#axis-count")).toHaveText("5");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBe(true);
});
