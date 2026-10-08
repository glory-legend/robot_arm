import { it, expect } from "vitest";
import { Vector3 } from "three";
import { PRESETS, sampleCycle } from "../src/timeline";
import {
  boltLocalMatrix,
  rodPose,
  mainFingerPose,
  GRASP_POINT,
  GRASP_DISTANCE,
  THUMB_LENGTHS,
  ROLLER_RADIUS,
  HEAD_STROKE,
} from "../src/rod-kinematics";
it("rotates a horizontal bolt to vertical around the fixed main-finger contact", () => {
  for (const t of [5, 10, 11, 12, 13, 14, 16])
    expect(
      new Vector3(0, 0, GRASP_DISTANCE)
        .applyMatrix4(boltLocalMatrix(sampleCycle(t)))
        .distanceTo(GRASP_POINT),
    ).toBeLessThan(1e-8);
  const axis = (t: number) =>
    new Vector3(0, 0, 1).transformDirection(boltLocalMatrix(sampleCycle(t)));
  expect(Math.abs(axis(5).z)).toBeLessThan(1e-8);
  expect(axis(14).distanceTo(new Vector3(0, 0, 1))).toBeLessThan(1e-8);
});
it("uses two rigid thumb phalanges while its pad stays against the bolt end", () => {
  for (const spec of PRESETS)
    for (let t = 10; t <= 14; t += 0.031) {
      const s = sampleCycle(t),
        p = rodPose(s, spec);
      expect(p.base.distanceTo(p.elbow)).toBeCloseTo(THUMB_LENGTHS[0], 8);
      expect(p.elbow.distanceTo(p.tip)).toBeCloseTo(THUMB_LENGTHS[1], 8);
      const local = p.tip.clone().applyMatrix4(boltLocalMatrix(s).invert());
      expect(Math.hypot(local.x, local.y)).toBeCloseTo(
        spec.diameter / 2 + ROLLER_RADIUS,
        7,
      );
      expect(local.z).toBeCloseTo(spec.length - 0.003, 7);
    }
});
it("keeps the same straight fingers rigid for all sizes and all times", () => {
  for (const spec of PRESETS)
    for (const side of [-1, 1]) {
      for (let t = 0; t <= 70; t += 0.17) {
        const p = mainFingerPose(side, sampleCycle(t, spec), spec);
        expect(p.root.distanceTo(p.contact)).toBeCloseTo(
          Math.hypot(0.042, 0.04),
          8,
        );
        if (t >= 5 && t <= 16) {
          expect(p.contact.x).toBeCloseTo(
            side * (spec.diameter / 2 + 0.0015),
            8,
          );
          expect(p.contact.y).toBeCloseTo(0, 8);
          expect(p.contact.z).toBeCloseTo(GRASP_POINT.z, 8);
        }
      }
    }
});
it("keeps the entire swept head beyond the parked chuck mouth", () => {
  const headZ = GRASP_POINT.z - GRASP_DISTANCE;
  for (const spec of PRESETS)
    for (let t = 10; t <= 14; t += 0.02) {
      const transform = boltLocalMatrix(sampleCycle(t));
      for (const z of [-spec.headHeight, 0])
        for (let i = 0; i < 6; i++) {
          const angle = (i * Math.PI) / 3;
          const corner = new Vector3(
            (spec.headWidth / Math.sqrt(3)) * Math.cos(angle),
            (spec.headWidth / Math.sqrt(3)) * Math.sin(angle),
            z,
          ).applyMatrix4(transform);
          expect(corner.z).toBeGreaterThan(headZ - HEAD_STROKE - 0.0006);
        }
    }
});
it("clears all fingers and retains the head before fastening", () => {
  const head = new Vector3().setFromMatrixPosition(
    boltLocalMatrix(sampleCycle(18)),
  );
  for (const spec of PRESETS) {
    const thumb = rodPose(sampleCycle(18), spec);
    expect(
      Math.max(thumb.base.z, thumb.elbow.z, thumb.tip.z) + 0.01,
    ).toBeLessThan(head.z);
    for (const side of [-1, 1])
      expect(
        Math.max(
          ...mainFingerPose(side, sampleCycle(18), spec).points.map((p) => p.z),
        ) + 0.012,
      ).toBeLessThan(head.z);
  }
});
it("maintains pinch force while the passive pads rotate with the bolt", () => {
  expect(sampleCycle(10).rodEngaged).toBe(1);
  expect(sampleCycle(12).gripForce).toBe(1);
  expect(sampleCycle(16).gripForce).toBe(1);
  expect(sampleCycle(16).rodEngaged).toBe(1);
});
