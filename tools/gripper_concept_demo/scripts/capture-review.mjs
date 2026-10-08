import { chromium } from "playwright-core";
import { mkdir } from "node:fs/promises";
const browser = await chromium.launch({
  headless: true,
  args: ["--no-sandbox", "--enable-unsafe-swiftshader"],
});
const page = await browser.newPage({ viewport: { width: 1600, height: 1100 } });
const faults = [];
page.on("pageerror", (e) => faults.push(String(e)));
page.on("response", (r) => {
  if (r.status() >= 400) faults.push(`${r.status()} ${r.url()}`);
});
for (const version of ["R06", "R07"]) {
  const folder = `archive/${version}/screenshots`;
  await mkdir(folder, { recursive: true });
  for (const v of ["a", "b"]) {
    if (version === "R06") {
      await page.goto(
        `http://127.0.0.1:5173/concept.html?variant=${v}&view=detail&time=5`,
      );
      await page.waitForFunction(
        () => !document.querySelector("#play").disabled,
      );
      await page.locator("#labels").uncheck();
      for (const [t, label] of [
        [5, "pickup"],
        [12, "righting"],
        [18, "handoff"],
        [40, "drive"],
      ]) {
        await page.locator("#timeline").fill(String(t));
        if (t === 40) await page.locator("#transparent").check();
        await page.waitForTimeout(500);
        await page.screenshot({ path: `${folder}/${v}-${label}.png` });
      }
    } else {
      await page.goto(`http://127.0.0.1:5173/engineering.html?variant=${v}`);
      await page.locator("canvas").waitFor();
      await page.locator("#labels").uncheck();
      for (const [t, label] of [
        [8, "pickup"],
        [28, "righting"],
        [50, "handoff"],
        [75, "retracted"],
        [90, "drive"],
      ]) {
        await page.locator("#motion").fill(String(t));
        if (t === 90) await page.locator("#transparent").check();
        await page.waitForTimeout(500);
        await page.screenshot({ path: `${folder}/${v}-${label}.png` });
      }
      await page.locator('[data-view="whole"]').click();
      await page.waitForTimeout(400);
      await page.screenshot({ path: `${folder}/${v}-whole.png` });
      await page.locator("#motion").fill("50");
      const modelDownload = page.waitForEvent("download");
      await page.locator("#export-model").click();
      await (
        await modelDownload
      ).saveAs(`archive/R07/${v}-assembly-review.glb`);
      const bomDownload = page.waitForEvent("download");
      await page.locator("#export-bom").click();
      await (await bomDownload).saveAs("archive/R07/component-review.csv");
    }
  }
}
await browser.close();
if (faults.length) throw new Error(faults.join("\n"));
console.log("Saved R06/R07 assembly screenshots; no browser errors.");
