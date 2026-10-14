import { test, expect } from "@playwright/test";
test("integrated view presents the complete transfer and exports the current assembly", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(page.locator("h1")).toContainText("하나의 몸체");
  for (const id of ["m6", "m8", "m10"]) {
    await page.locator("#bolt").selectOption(id);
    for (const t of [8, 25, 45, 60, 77, 90, 97])
      await page.locator("#motion").fill(String(t));
    await expect(page.locator("#phase-title")).toHaveText(
      "몸체 안에서 체결 회전",
    );
  }
  await page.locator("#transparent").check();
  await page.locator("#explode").check();
  await page.locator("#play").click();
  await page.locator("#play").click();
  await expect(page.locator("#explode")).toBeChecked();
  const download = page.waitForEvent("download");
  await page.locator("#export-model").click();
  expect((await download).suggestedFilename()).toBe(
    "R08-m10-integrated-review.glb",
  );
  await page.locator("#reset").click();
  await expect(page.locator("#motion")).toHaveValue("0");
  await expect(page.getByRole("link", { name: /이전 R07/ })).toHaveAttribute(
    "href",
    "./engineering.html",
  );
  expect(errors).toEqual([]);
});
test("integrated controls fit a narrow viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/integrated.html");
  await expect(page.locator("canvas")).toBeVisible();
  await page.locator("#motion").fill("97");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBe(true);
});
