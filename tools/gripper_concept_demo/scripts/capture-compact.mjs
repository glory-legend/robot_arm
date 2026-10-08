import { chromium } from "playwright-core";
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
const folder = "archive/R11";
await mkdir(`${folder}/screenshots`, { recursive: true });
const browser = await chromium.launch({
  headless: true,
  args: ["--no-sandbox", "--enable-unsafe-swiftshader"],
});
const page = await browser.newPage({ viewport: { width: 1600, height: 1100 } });
const faults = [],
  captures = [];
page.on("pageerror", (e) => faults.push(e.message));
page.on("response", (r) => {
  if (r.status() >= 400) faults.push(`${r.status()} ${r.url()}`);
});
try {
  for (const design of ["c2", "r11"]) {
    await page.goto(`http://127.0.0.1:5173/?design=${design}`);
    await page.locator("#play:not([disabled])").waitFor({ timeout: 60000 });
    assert.match(
      await page.locator(".scene-id").innerText(),
      design === "r11" ? /R11/ : /R10/,
    );
    for (const [name, time, internal] of [
      ["whole", 0, false],
      ["pick", 5, false],
      ["righting", 12, false],
      ["handoff", 21, true],
      ["stowed", 26, false],
      ["fastening", 50, false],
      ["internal", 40, true],
    ]) {
      if (design === "c2" && !["stowed", "internal"].includes(name)) continue;
      await page.locator("#timeline").fill(String(time));
      await page
        .locator(`[data-view="${name === "whole" ? "whole" : "detail"}"]`)
        .click();
      if (name !== "whole")
        for (let i = 0; i < 2; i++) await page.locator("#zoom-in").click();
      await page.locator("#transparent").setChecked(internal);
      await page.locator("#labels").uncheck();
      await page.locator(".sidebar").evaluate((el) => {
        el.scrollTop = 0;
      });
      await page.waitForTimeout(350);
      const file = `screenshots/${design === "c2" ? "r10-reproduced" : "r11"}-${name}.png`;
      await page.screenshot({ path: `${folder}/${file}` });
      captures.push({
        file,
        design,
        time,
        bolt: "m8",
        internal,
        provenance:
          design === "c2"
            ? "R10 preserved design reproduced on 2026-10-02, not an original historical screenshot"
            : "R11 original implementation screenshot on 2026-10-02",
      });
    }
  }
  for (const id of ["m6", "m10"]) {
    await page.locator("#bolt").selectOption(id);
    await page.locator("#timeline").fill("50");
    await page.locator('[data-view="detail"]').click();
    for (let i = 0; i < 2; i++) await page.locator("#zoom-in").click();
    await page.locator("#transparent").uncheck();
    await page.waitForTimeout(350);
    const file = `screenshots/r11-${id}-fastening.png`;
    await page.screenshot({ path: `${folder}/${file}` });
    captures.push({
      file,
      design: "r11",
      time: 50,
      bolt: id,
      provenance: "R11 original implementation screenshot on 2026-10-02",
    });
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: `${folder}/screenshots/r11-mobile.png`,
    fullPage: true,
  });
  if (faults.length) throw new Error(faults.join("\n"));
  await writeFile(
    `${folder}/screenshot-manifest.json`,
    JSON.stringify(
      { date: "2026-10-02", captures, browser_errors: faults },
      null,
      2,
    ) + "\n",
  );
  console.log(
    `${captures.length} model screenshots + mobile capture; no page or HTTP errors.`,
  );
} finally {
  await browser.close();
}
