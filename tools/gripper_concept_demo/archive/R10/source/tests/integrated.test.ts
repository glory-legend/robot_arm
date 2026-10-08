import { describe, expect, test } from "vitest";
import { Vector3, Raycaster, Mesh } from "three";
import { makeIntegratedAssembly } from "../src/integrated-model";
import { PRESETS } from "../src/timeline";
import {
  integratedPose,
  boltMatrix,
  thumbPoints,
  fingerMatrix,
} from "../src/integrated-kinematics";

describe("R08 integrated mechanism", () => {
  test("rendered chuck has radial slots and keeps its axial datum", () => {
    const a = makeIntegratedAssembly();
    const webs: Mesh[] = [];
    a.root.traverse((o) => {
      if (o instanceof Mesh && o.name.startsWith("chuck-web-between-slots"))
        webs.push(o);
    });
    expect(webs).toHaveLength(6);
    a.update(0, false, false);
    for (let i = 0; i < 6; i++) {
      const angle = (i * Math.PI) / 3;
      const ray = new Raycaster(
        new Vector3(0, 0, -15),
        new Vector3(Math.cos(angle), Math.sin(angle), 0),
        0,
        29,
      );
      expect(ray.intersectObjects(webs)).toHaveLength(0);
    }
    const rotor = a.root.getObjectByName("fixed-axial-internal-rotor")!;
    for (const t of [0, 25, 50, 60, 77, 90, 99]) {
      a.update(t, true, false);
      expect(rotor.getWorldPosition(new Vector3()).length()).toBe(0);
    }
  });
  test("maintains retention and retracts only after the fingers fold", () => {
    for (let t = 8; t <= 100; t += 0.25) {
      const s = integratedPose(t);
      if (s.release > 0) expect(s.clamp).toBe(1);
      if (s.stow > 0) {
        expect(s.fold).toBe(1);
        expect(s.thumbPark).toBe(1);
      }
      if (s.spin > 0) expect(s.stow).toBe(1);
      expect(s.chuckAxial).toBe(0);
    }
  });
  test("pulls the aligned bolt into the fixed chuck and leaves it there", () => {
    expect(
      new Vector3(0, 0, 14).applyMatrix4(boltMatrix(integratedPose(10))).z,
    ).toBeCloseTo(64);
    for (let t = 52; t <= 100; t++)
      expect(
        new Vector3().applyMatrix4(boltMatrix(integratedPose(t))).length(),
      ).toBeCloseTo(0);
  });
  test("keeps both thumb links at their actual length for all bolt sizes", () => {
    for (const spec of PRESETS)
      for (let t = 0; t <= 100; t += 0.5) {
        const [base, elbow, tip] = thumbPoints(integratedPose(t), spec);
        expect(base.distanceTo(elbow)).toBeCloseTo(38, 6);
        expect(elbow.distanceTo(tip)).toBeCloseTo(38, 6);
        expect(tip.toArray().every(Number.isFinite)).toBe(true);
      }
  });
  test("stowed fingers clear the work face and fit side pockets", () => {
    for (const spec of PRESETS)
      for (const side of [-1, 1]) {
        const m = fingerMatrix(integratedPose(95), spec, side);
        for (let u = 0; u <= 1; u += 0.1) {
          const p = new Vector3(-side * 38 * u, 0, 14 * u).applyMatrix4(m);
          expect(p.z).toBeLessThan(-20);
          expect(Math.abs(p.x)).toBeGreaterThan(30);
          expect(Math.abs(p.x)).toBeLessThan(73);
        }
      }
  });
  test("thumb links clear the bolt shaft and the parked joints clear the cover", () => {
    for (const spec of PRESETS)
      for (let t = 14; t <= 60; t += 1) {
        const s = integratedPose(t),
          pts = thumbPoints(s, spec),
          m = boltMatrix(s);
        const a = new Vector3().applyMatrix4(m),
          b = new Vector3(0, 0, spec.length * 1000).applyMatrix4(m),
          axis = b.clone().sub(a);
        for (let i = 0; i < 2; i++)
          for (let u = 0; u <= 1; u += 0.025) {
            const p = pts[i].clone().lerp(pts[i + 1], u);
            const q = a
              .clone()
              .addScaledVector(
                axis,
                Math.max(
                  0,
                  Math.min(1, p.clone().sub(a).dot(axis) / axis.lengthSq()),
                ),
              );
            expect(p.distanceTo(q)).toBeGreaterThan(
              spec.diameter * 500 + (i === 0 ? 3 : 2.5),
            );
          }
      }
    for (const p of thumbPoints(integratedPose(95), PRESETS[1]))
      expect(p.y + 5).toBeLessThan(69);
  });
});
