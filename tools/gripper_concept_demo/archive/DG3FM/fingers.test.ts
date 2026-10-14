import { describe, it, expect } from "vitest";
import { Vector3 } from "three";
import {
  fingerPose,
  palmDrawMatrix,
  HAND_DATA,
  PAD_RADIUS,
} from "../src/finger-kinematics";
import { PRESETS, sampleCycle } from "../src/timeline";
describe("DG3FM articulated hand", () => {
  it("keeps upstream knuckles fixed and every joint within URDF limits", () => {
    for (const spec of PRESETS)
      for (let i = 0; i < 3; i++)
        for (let t = 0; t <= 36; t += 0.13) {
          const p = fingerPose(i, spec, sampleCycle(t));
          const js = HAND_DATA.joints.filter(
            (j) => j.name.startsWith(`j_dg_${i + 1}_`) && j.axis,
          );
          expect(
            p.root.distanceTo(
              new Vector3(...(js[0].xyz as [number, number, number])).add(
                new Vector3(0, 0, 0.004),
              ),
            ),
          ).toBeLessThan(1e-9);
          p.angles.forEach((q, k) => {
            expect(q).toBeGreaterThanOrEqual(js[k].lower!);
            expect(q).toBeLessThanOrEqual(js[k].upper!);
          });
          expect(p.points[2].distanceTo(p.points[3])).toBeCloseTo(0.0434, 8);
          expect(p.points[3].distanceTo(p.points[4])).toBeCloseTo(0.0313, 8);
        }
  });
  it("keeps all three custom contact pads against the bolt during the draw", () => {
    for (const spec of PRESETS)
      for (let t = 5; t <= 16; t += 0.037) {
        const state = sampleCycle(t),
          m = palmDrawMatrix(state.retract);
        for (let i = 0; i < 3; i++) {
          const a = [0, (2 * Math.PI) / 3, (-2 * Math.PI) / 3][i],
            r = spec.diameter / 2 + PAD_RADIUS;
          const target = new Vector3(
            r * Math.cos(a),
            r * Math.sin(a),
            0.014,
          ).applyMatrix4(m);
          expect(
            fingerPose(i, spec, state).tip.distanceTo(target),
          ).toBeLessThan(0.0001);
        }
      }
  });
  it("curls distal joints to draw the bolt into the palm with fixed roots", () => {
    for (let i = 0; i < 3; i++) {
      const a = fingerPose(i, PRESETS[1], sampleCycle(10)),
        b = fingerPose(i, PRESETS[1], sampleCycle(14));
      expect(b.angles[3] - a.angles[3]).toBeGreaterThan(0.25);
      expect(b.tip.z).toBeLessThan(a.tip.z - 0.02);
      expect(b.root).toEqual(a.root);
    }
  });
  it("opens and folds the fingertips clear before fastening", () => {
    for (const spec of PRESETS)
      for (let i = 0; i < 3; i++) {
        const p = fingerPose(i, spec, sampleCycle(23));
        expect(
          Math.max(...p.points.map((v) => v.z), p.tip.z) + 0.012,
        ).toBeLessThan(0.17);
        expect(Math.hypot(p.tip.x, p.tip.y)).toBeGreaterThan(0.07);
      }
  });
});
