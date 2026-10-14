import { test, expect } from "@playwright/test";
test("R11 showcase scrolls through the cycle and mounts the FR3 cell", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/r11.html");
  await expect(page.locator("h1")).toContainText("그 자리에서 조입니다");
  await expect(page.locator("#parts li")).toHaveCount(9);
  await expect(page.locator("#rail button")).toHaveCount(11);
  // The stage ruler scrolls the pinned chapter; the panel follows the scroll position.
  await page.locator("#rail button").nth(8).click();
  await expect(page.locator("#stage-name")).toHaveText("회전하며 체결");
  await expect(page.locator("#stage-no")).toHaveText("09");
  await page.locator("#rail button").nth(6).click();
  await expect(page.locator("#stage-name")).toHaveText(/정지 인계/);
  await expect(page.locator("#bars .row")).toHaveCount(5);
  await expect(page.locator("#bars")).toContainText("−27.69%");
  await page.locator("#cell").scrollIntoViewIfNeeded();
  await expect(page.locator("#cell-play")).toBeEnabled({ timeout: 60000 });
  await page.getByRole("button", { name: "M10 × 50" }).click();
  await page.locator("#cell-time").fill("50");
  await expect(page.locator("#cell-stage")).toContainText("회전하며 체결");
  await expect(page.locator("#cell-clock")).toHaveText("50.0초");
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
  expect(errors).toEqual([]);
});
