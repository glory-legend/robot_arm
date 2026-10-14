import { it, expect } from "vitest";
import { Vector3, Quaternion } from "three";
import { PRESETS } from "../src/timeline";
import { jointsAt, ROBOT_DATA, boltWorldAt, flangeAt } from "../src/kinematics";
it("all precomputed motion obeys joint limits for each bolt", () => {
  for (const spec of PRESETS)
    for (let t = 0; t <= 70; t += 0.1) {
      jointsAt(t, spec.id).forEach((q, i) => {
        expect(q).toBeGreaterThanOrEqual(ROBOT_DATA[i].lower!);
        expect(q).toBeLessThanOrEqual(ROBOT_DATA[i].upper!);
      });
    }
});
it("bolt has no discontinuity at either handoff or seating", () => {
  for (const spec of PRESETS)
    for (const t of [5, 10, 14, 16, 18, 23, 61, 63, 65]) {
      const a = boltWorldAt(t - 1e-5, spec),
        b = boltWorldAt(t + 1e-5, spec);
      expect(
        new Vector3()
          .setFromMatrixPosition(a)
          .distanceTo(new Vector3().setFromMatrixPosition(b)),
      ).toBeLessThan(0.00002);
      expect(
        new Quaternion()
          .setFromRotationMatrix(a)
          .angleTo(new Quaternion().setFromRotationMatrix(b)),
      ).toBeLessThan(0.001);
    }
});
it("seated head remains on the plate while the robot retreats", () => {
  for (const spec of PRESETS) {
    const seated = boltWorldAt(63, spec);
    expect(new Vector3().setFromMatrixPosition(seated).z).toBeCloseTo(0.026, 3);
    expect(boltWorldAt(69, spec).elements).toEqual(seated.elements);
    expect(
      new Vector3().setFromMatrixPosition(flangeAt(69, spec.id)).z,
    ).toBeGreaterThan(0.4);
  }
});

it("the rod leaves the head above the threaded end in world coordinates", () => {
  for (const spec of PRESETS)
    for (const t of [14, 16, 18, 23, 28]) {
      const m = boltWorldAt(t, spec),
        head = new Vector3().setFromMatrixPosition(m),
        end = new Vector3(0, 0, spec.length).applyMatrix4(m);
      expect(head.z - end.z).toBeCloseTo(spec.length, 4);
    }
});
