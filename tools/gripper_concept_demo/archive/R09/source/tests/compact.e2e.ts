import { test, expect } from "@playwright/test";
test("R09 runs the FR3 bin-picking cycle for every bolt size", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(page.locator("#play")).toBeEnabled({ timeout: 60000 });
  await expect(page.locator(".scene-id")).toContainText("R09");
  await expect(page.locator("[data-stage]")).toHaveCount(14);
  await page.screenshot({ path: "test-results/r09-whole.png" });
  await page.getByRole("button", { name: "그리퍼 확대", exact: true }).click();
  for (const [t, name] of [
    [4, "pick"],
    [12, "righting"],
    [16, "draw-in"],
    [23.5, "stow"],
    [40, "fastening"],
  ] as const) {
    await page.locator("#timeline").fill(String(t));
    await page.screenshot({ path: `test-results/r09-${name}.png` });
  }
  await expect(page.locator("#phase-title")).toHaveText("회전하며 체결");
  await page.locator("#transparent").check();
  await page.locator("#timeline").fill("17");
  await page.screenshot({ path: "test-results/r09-internal.png" });
  for (const id of ["m6", "m8", "m10"]) {
    await page.locator("#bolt").selectOption(id);
    for (const t of [3, 9, 14, 19, 22, 26, 31, 50, 64, 67, 70])
      await page.locator("#timeline").fill(String(t));
  }
  await expect(page.locator("#step-count")).toHaveText("14 / 14");
  expect(errors).toEqual([]);
});
