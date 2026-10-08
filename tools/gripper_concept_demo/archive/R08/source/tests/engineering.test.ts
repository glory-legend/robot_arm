import { expect, it } from "vitest";
import { Vector3 } from "three";
import {
  assemblyPose,
  DESIGN,
  gripTransform,
  boltTransform,
} from "../src/engineering-kinematics";
import { PRESETS } from "../src/timeline";

it("B reorients the entire rigid pickup cassette about its supported axis", () => {
  for (let t = 0; t <= 100; t += 0.25) {
    const s = assemblyPose(t);
    const tr = gripTransform("b", s);
    const contact = DESIGN.grasp.clone().applyMatrix4(tr);
    const pivot = DESIGN.pivot.clone().applyMatrix4(tr);
    expect(contact.distanceTo(pivot)).toBeCloseTo(
      DESIGN.grasp.distanceTo(DESIGN.pivot),
      9,
    );
    if (t <= 50) {
      const boltContact = new Vector3(0, 0, 14).applyMatrix4(
        boltTransform("b", s),
      );
      expect(boltContact.distanceTo(contact)).toBeLessThan(1e-8);
    }
  }
});
it("both mechanisms hand over before opening, retract before spinning, and keep the chuck axially fixed", () => {
  for (const variant of ["a", "b"] as const)
    for (const spec of PRESETS)
      for (let t = 0; t <= 100; t += 0.25) {
        const s = assemblyPose(t);
        if (s.release > 0) expect(s.clamp).toBe(1);
        if (s.spin > 0) {
          expect(s.retract).toBe(1);
          expect(s.clamp).toBe(1);
          const p = DESIGN.grasp
            .clone()
            .applyMatrix4(gripTransform(variant, s));
          expect(p.z + DESIGN.tipDepth / 2).toBeLessThan(
            -spec.headHeight * 1000,
          );
        }
        expect(s.chuckAxial).toBe(0);
      }
});
it("places the head on the same fixed chuck datum after righting in A and B", () => {
  const s = assemblyPose(45);
  for (const v of ["a", "b"] as const) {
    const m = boltTransform(v, s);
    expect(new Vector3().applyMatrix4(m).length()).toBeLessThan(1e-8);
    expect(
      new Vector3(0, 0, 1)
        .transformDirection(m)
        .distanceTo(new Vector3(0, 0, 1)),
    ).toBeLessThan(1e-8);
  }
});

import { Box3 } from "three";
import { makeEngineeringAssembly } from "../src/engineering-model";
it("the rendered A roller follows the same bolt rotation without double easing", () => {
  for (const spec of PRESETS) {
    const a = makeEngineeringAssembly("a", spec);
    const roller = a.root.getObjectByName("thumb-contact-roller")!;
    for (let t = 15; t <= 40; t += 0.5) {
      a.update(t);
      const p = roller
        .getWorldPosition(new Vector3())
        .applyMatrix4(boltTransform("a", assemblyPose(t)).invert());
      expect(Math.hypot(p.x, p.y)).toBeCloseTo(spec.diameter * 500 + 3, 6);
      expect(p.z).toBeCloseTo(spec.length * 1000 - 3, 6);
    }
  }
});
it("separates both A tendon motor envelopes from the pickup module", () => {
  const a = makeEngineeringAssembly("a");
  for (const t of [0, 30, 60, 75]) {
    a.update(t);
    const moduleBox = new Box3().setFromObject(
      a.root.getObjectByName("05-GRIPPER-INSTALLATION-ENVELOPE-NOT-SELECTED")!,
    );
    for (const motor of a.root.getObjectsByProperty(
      "name",
      "08A-tendon-drive-envelope",
    ))
      expect(moduleBox.intersectsBox(new Box3().setFromObject(motor))).toBe(
        false,
      );
  }
});
