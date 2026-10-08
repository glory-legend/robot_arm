import { expect, it } from "vitest";
import { sampleCycle } from "../src/timeline";
it("keeps the internal fastening head at a fixed axial position throughout capture and drive", () => {
  for (const t of [0, 10, 14, 15, 16, 18, 23, 40, 62, 65, 70])
    expect(sampleCycle(t).headAdvance).toBe(0);
});

import { PRESETS } from "../src/timeline";
import { mainFingerPose, rodPose } from "../src/rod-kinematics";
for (const variant of ["a", "b"] as const) {
  it(`${variant}: keeps identical rigid blades across sizes and clears the seating plane`, () => {
    for (const spec of PRESETS)
      for (const side of [-1, 1])
        for (let t = 0; t <= 70; t += 0.1) {
          const state = sampleCycle(t, spec),
            p = mainFingerPose(side, state, spec, variant);
          expect(p.root.distanceTo(p.contact)).toBeCloseTo(
            variant === "a"
              ? Math.hypot(0.052, 0.02)
              : Math.hypot(0.02, 0.016, 0.035),
            8,
          );
          if (t >= 18) {
            expect(Math.max(p.root.z, p.contact.z) + 0.003).toBeLessThan(0.386);
            const thumb = rodPose(state, spec, variant);
            expect(
              Math.max(thumb.base.z, thumb.elbow.z, thumb.tip.z) + 0.004,
            ).toBeLessThan(0.386);
          }
          if (t >= 5 && t <= 16)
            expect(Math.abs(p.contact.x) - 0.0008).toBeCloseTo(
              spec.diameter / 2,
              8,
            );
        }
  });
}
