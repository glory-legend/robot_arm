import { expect, it } from "vitest";
import { PRESETS, sampleCycle } from "../src/timeline";
import { THUMB_LENGTHS, rodPose, boltLocalMatrix } from "../src/rod-kinematics";

it("uses a thumb under 50 mm with reachable contact throughout all three righting paths", () => {
  expect(THUMB_LENGTHS[0] + THUMB_LENGTHS[1]).toBeLessThanOrEqual(0.05);
  for (const spec of PRESETS)
    for (let t = 10; t <= 14; t += 0.02) {
      const state = sampleCycle(t),
        pose = rodPose(state, spec);
      const contact = pose.tip
        .clone()
        .applyMatrix4(boltLocalMatrix(state).invert());
      expect(contact.z).toBeCloseTo(spec.length - 0.003, 7);
      expect(Math.hypot(contact.x, contact.y)).toBeCloseTo(
        spec.diameter / 2 + 0.003,
        7,
      );
    }
});

it("keeps the thumb joints and both link bodies outside the bolt during approach, pivot and withdrawal", () => {
  const distanceToCylinder = (
    p: { x: number; y: number; z: number },
    radius: number,
    minZ: number,
    maxZ: number,
  ) =>
    Math.hypot(
      Math.max(0, Math.hypot(p.x, p.y) - radius),
      Math.max(0, minZ - p.z, p.z - maxZ),
    );
  for (const spec of PRESETS)
    for (let t = 5; t <= 18; t += 0.04) {
      const state = sampleCycle(t, spec),
        p = rodPose(state, spec),
        inverse = boltLocalMatrix(state).invert();
      const clearance = (point: typeof p.base, r: number) => {
        const local = point.clone().applyMatrix4(inverse);
        return (
          Math.min(
            distanceToCylinder(local, spec.diameter / 2, 0, spec.length),
            distanceToCylinder(
              local,
              spec.headWidth / Math.sqrt(3),
              -spec.headHeight,
              0,
            ),
          ) - r
        );
      };
      expect(
        clearance(p.base, 0.0035),
        `${spec.id} base at ${t}`,
      ).toBeGreaterThanOrEqual(-1e-7);
      expect(
        clearance(p.elbow, 0.003),
        `${spec.id} elbow at ${t}`,
      ).toBeGreaterThanOrEqual(-1e-7);
      for (let f = 0; f <= 1; f += 0.05) {
        expect(
          clearance(p.base.clone().lerp(p.elbow, f), 0.002),
          `${spec.id} proximal at ${t}`,
        ).toBeGreaterThanOrEqual(-1e-7);
        expect(
          clearance(p.elbow.clone().lerp(p.tip, f), 0.0015),
          `${spec.id} distal at ${t}`,
        ).toBeGreaterThanOrEqual(-1e-7);
      }
    }
});

it("feeds one pitch per turn below 90 rpm and drives only after docking", () => {
  for (const spec of PRESETS) {
    for (let t = 23.01; t <= 61; t += 0.1) {
      const before = sampleCycle(t - 0.01, spec),
        after = sampleCycle(t, spec);
      const turns = (after.spindle - before.spindle) / (2 * Math.PI);
      expect(turns * spec.pitch).toBeCloseTo(
        (after.inserted - before.inserted) * spec.length,
        9,
      );
      expect((turns / 0.01) * 60).toBeLessThanOrEqual(90);
      expect(after.docked).toBe(true);
      expect(after.clear).toBe(1);
      expect(after.chuckClosed).toBe(1);
    }
    expect(sampleCycle(62, spec).torquePhase).toBe(true);
    expect(sampleCycle(62, spec).owner).toBe("chuck");
  }
});
