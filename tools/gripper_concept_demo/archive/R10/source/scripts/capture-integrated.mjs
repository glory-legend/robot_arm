import { chromium } from "playwright-core";
import { mkdir } from "node:fs/promises";
const folder = "archive/R08";
await mkdir(`${folder}/screenshots`, { recursive: true });
const browser = await chromium.launch({
  headless: true,
  args: ["--no-sandbox", "--enable-unsafe-swiftshader"],
});
const page = await browser.newPage({ viewport: { width: 1600, height: 1100 } });
const faults = [];
page.on("pageerror", (e) => faults.push(e.message));
page.on("response", (r) => {
  if (r.status() >= 400) faults.push(`${r.status()} ${r.url()}`);
});
await page.goto("http://127.0.0.1:5173/integrated.html");
await page.locator("canvas").waitFor();
for (const [name, t, view, transparent, open] of [
  ["integrated-whole", 8, "whole", false, false],
  ["pickup", 8, "detail", false, false],
  ["righting", 25, "detail", false, false],
  ["draw-in", 45, "detail", true, false],
  ["handoff", 60, "detail", true, false],
  ["fold", 77, "detail", true, false],
  ["stowed", 93, "whole", false, false],
  ["internal-drive", 97, "detail", true, false],
  ["internal-layout", 93, "whole", true, true],
]) {
  await page.locator("#motion").fill(String(t));
  await page.locator(`[data-view="${view}"]`).click();
  await page.locator("#transparent").setChecked(transparent);
  await page.locator("#explode").setChecked(open);
  await page.waitForTimeout(350);
  await page.screenshot({ path: `${folder}/screenshots/${name}.png` });
}
await page.locator("#explode").uncheck();
await page.locator("#transparent").uncheck();
await page.locator("#motion").fill("60");
for (const size of ["m6", "m8", "m10"]) {
  await page.locator("#bolt").selectOption(size);
  const pending = page.waitForEvent("download");
  await page.locator("#export-model").click();
  await (await pending).saveAs(`${folder}/${size}-integrated-review.glb`);
}
const pending = page.waitForEvent("download");
await page.locator("#export-bom").click();
await (await pending).saveAs(`${folder}/component-review.csv`);
await browser.close();
if (faults.length) throw new Error(faults.join("\n"));
console.log(
  "R08: 9 screenshots, 3 GLB files and CSV saved; no browser errors.",
);
