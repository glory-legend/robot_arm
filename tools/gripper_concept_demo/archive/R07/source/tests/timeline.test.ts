import { describe, it, expect } from "vitest";
import { sampleCycle, DURATION } from "../src/timeline";
describe("cycle handoff and seeking", () => {
  it("keeps a holder on the bolt until it is seated", () => {
    for (let t = 5; t < 63; t += 0.025) {
      const s = sampleCycle(t);
      expect(
        Math.max(s.fingerClosed, s.chuckClosed),
        `unsupported at ${t}`,
      ).toBeGreaterThanOrEqual(0.99);
    }
  });
  it("closes the chuck before opening the shaft fingers", () => {
    expect(sampleCycle(15.9).fingerClosed).toBe(1);
    expect(sampleCycle(16).chuckClosed).toBe(1);
    expect(sampleCycle(18).fingerClosed).toBe(0);
  });
  it("does not turn the spindle until fingers are clear", () => {
    for (let t = 0; t <= DURATION; t += 0.05) {
      const s = sampleCycle(t);
      if (s.spindle > 0) expect(s.fingerClosed).toBe(0);
    }
    expect(sampleCycle(27).spindle).toBeGreaterThan(0);
  });
  it("seeking backwards produces the same phase and exact transforms", () => {
    const before = sampleCycle(13.5);
    sampleCycle(33);
    sampleCycle(1);
    expect(sampleCycle(13.5)).toEqual(before);
    expect(before.align).toBeGreaterThan(0.8);
  });
  it("clamps playback at both ends", () => {
    expect(sampleCycle(-100).time).toBe(0);
    expect(sampleCycle(100).time).toBe(DURATION);
    expect(sampleCycle(DURATION).finished).toBe(true);
  });
});
