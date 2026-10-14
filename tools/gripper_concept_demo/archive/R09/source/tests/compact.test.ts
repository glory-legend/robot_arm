import { describe, expect, test } from "vitest";
import { Box3, Mesh, Quaternion, Vector3 } from "three";
import { OBB } from "three/addons/math/OBB.js";
import { makeCompactGripper } from "../src/compact-model";
import { PRESETS } from "../src/timeline";
import { ROBOT_DATA } from "../src/kinematics";
import {
  BODY,
  CHUCK,
  DRAW_IN,
  GRASP,
  NOSE,
  TWEEZER,
  THUMB,
  compactBoltWorld,
  compactJoints,
  compactPose,
  tweezerPoints,
  thumbPose,
} from "../src/compact-kinematics";

type Gripper = ReturnType<typeof makeCompactGripper>;
const TIMES = [0, 4, 9, 12, 15, 17, 19.8, 21, 23.5, 40, 64, 66, 67.5, 69.3, 70];

function meshBoxes(root: Gripper["root"]) {
  root.position.set(0, 0, 0);
  root.scale.setScalar(1); // test in millimetres
  root.updateMatrixWorld(true);
  const out: { name: string; box: Box3; obb: OBB }[] = [];
  root.traverse((o) => {
    if (!(o instanceof Mesh)) return;
    o.geometry.computeBoundingBox();
    const bb = o.geometry.boundingBox!;
    const obb = new OBB().fromBox3(bb).applyMatrix4(o.matrixWorld);
    // OBB.applyMatrix4 only translates the centre; rotate an off-origin centre ourselves.
    obb.center.copy(bb.getCenter(new Vector3()).applyMatrix4(o.matrixWorld));
    out.push({ name: o.name, box: new Box3().setFromObject(o), obb });
  });
  return out;
}
const isCover = (g: Gripper, name: string) =>
  g.parts.shell.getObjectByName(name) !== undefined;
/** Names of meshes not linked to the first frame part through touching oriented boxes (0.3 mm). Cover excluded. */
function floatingParts(g: Gripper) {
  const parts = meshBoxes(g.root).filter((p) => !isCover(g, p.name));
  parts.forEach((p) => p.obb.halfSize.addScalar(0.15));
  const seen = new Set([0]),
    queue = [0];
  while (queue.length) {
    const a = parts[queue.pop()!].obb;
    parts.forEach((p, j) => {
      if (!seen.has(j) && a.intersectsOBB(p.obb)) {
        seen.add(j);
        queue.push(j);
      }
    });
  }
  return parts.filter((_, i) => !seen.has(i)).map((p) => p.name);
}
function segmentDistance(a0: Vector3, a1: Vector3, b0: Vector3, b1: Vector3) {
  let best = Infinity;
  for (let u = 0; u <= 1; u += 0.02)
    for (let v = 0; v <= 1; v += 0.02)
      best = Math.min(
        best,
        a0.clone().lerp(a1, u).distanceTo(b0.clone().lerp(b1, v)),
      );
  return best;
}

describe("R09 compact gripper", () => {
  test("every part touches the assembly: no floating components at any phase", () => {
    for (const spec of PRESETS) {
      const g = makeCompactGripper(spec);
      for (const t of TIMES) {
        g.update({ time: t }, spec);
        expect(floatingParts(g), `${spec.id} t=${t}`).toEqual([]);
      }
    }
  });
  test("the connection check catches a detached part (negative control)", () => {
    const g = makeCompactGripper(PRESETS[1]);
    g.update({ time: 12 }, PRESETS[1]);
    g.root.getObjectByName("bolt-roller")!.position.y += 40;
    g.root.getObjectByName("passive-pad")!.position.z += 8;
    expect(floatingParts(g)).toEqual(
      expect.arrayContaining(["bolt-roller", "passive-pad"]),
    );
  });

  test("while picking, only the tweezer tips reach the bolt; the thumb stays above them", () => {
    for (const spec of PRESETS) {
      const g = makeCompactGripper(spec);
      const boltTop = GRASP + DRAW_IN - spec.diameter * 500; // horizontal bolt, tool side
      for (const t of [0, 2, 3, 4, 5, 69.5, 70]) {
        g.update({ time: t }, spec);
        const parts = meshBoxes(g.root);
        const tips = parts.filter((p) =>
          /tweezer-blade|passive-pad/.test(p.name),
        );
        const rest = parts.filter(
          (p) => !/tweezer-blade/.test(p.name) && p.name !== "passive-pad",
        );
        const deepest = Math.max(...rest.map((p) => p.box.max.z));
        expect(
          Math.min(...tips.map((p) => p.box.max.z)),
        ).toBeGreaterThanOrEqual(GRASP + DRAW_IN);
        expect(deepest, `${spec.id} t=${t}`).toBeLessThan(boltTop - 1);
        const thumb = rest.filter((p) => /thumb|roller/.test(p.name));
        expect(Math.max(...thumb.map((p) => p.box.max.z))).toBeLessThan(
          GRASP + DRAW_IN - 6,
        );
      }
    }
  });

  test("body envelope is a fraction of R08 and nothing leaves the face while fastening", () => {
    const g = makeCompactGripper(PRESETS[2]);
    g.update({ time: 40 }, PRESETS[2]);
    const all = new Box3();
    meshBoxes(g.root).forEach((p) => all.union(p.box));
    const size = all.getSize(new Vector3());
    expect(size.x).toBeLessThanOrEqual(BODY.width + 0.01);
    expect(size.y).toBeLessThanOrEqual(BODY.height + 1.01); // cover screw heads
    expect(size.z).toBeLessThanOrEqual(BODY.length + 0.01);
    expect(all.max.z).toBeLessThanOrEqual(0.01); // only the bolt projects past the face
    expect(
      (BODY.width * BODY.height * BODY.length) / (152 * 144 * 250),
    ).toBeLessThan(0.065);
  });

  test("keeps R08 interlocks: hold before release, release before stow, stow before spin", () => {
    for (const spec of PRESETS)
      for (let t = 0; t <= 70; t += 0.05) {
        const s = compactPose(t, spec);
        if (s.release > 0 && t < 63) expect(s.clamp).toBe(1);
        if (s.stow > 0 && t < 65) expect(s.release * s.thumbPark).toBe(1);
        if (s.spin > 0 && t < 65) expect(s.stow).toBe(1);
        if (s.feed > 0 && t < 65) expect(s.align * s.thumbPark).toBe(1);
      }
  });

  test("tool returns to its start state for the next pick", () => {
    for (const spec of PRESETS) {
      const a = compactPose(0, spec),
        b = compactPose(70, spec);
      for (const k of ["carriageZ", "gap", "stow", "engaged", "clamp"] as const)
        expect(b[k], k).toBeCloseTo(a[k], 6);
    }
  });

  test("chuck stays at its axial datum; tweezer blades never cut into the nose", () => {
    const corner = (x: number, w: number) =>
      Math.hypot(Math.abs(x) - TWEEZER.thick, w);
    for (const spec of PRESETS) {
      const g = makeCompactGripper(spec);
      for (const t of TIMES) {
        g.update({ time: t }, spec);
        expect(g.parts.rotor.position.length()).toBe(0);
      }
      for (let t = 0; t <= 70; t += 0.05) {
        const s = compactPose(t, spec);
        const { knee, bend } = tweezerPoints(s, 1);
        expect(corner(knee.x, TWEEZER.width)).toBeGreaterThan(
          NOSE.radius + 0.3,
        );
        // Any blade point level with the nose or chuck must be outside the nose.
        for (let u = 0; u <= 1; u += 0.05) {
          const p = knee.clone().lerp(bend, u);
          if (p.z < 0.5)
            expect(Math.abs(p.x) - TWEEZER.thick).toBeGreaterThan(NOSE.radius);
        }
        if (bend.z < 0.5)
          expect(Math.abs(bend.x) - TWEEZER.tipThick).toBeGreaterThan(
            NOSE.radius,
          );
      }
    }
  });

  test("while fastening, only the slim nose is level with neighbouring bolt heads", () => {
    for (const spec of PRESETS) {
      const g = makeCompactGripper(spec);
      const band = -(spec.headHeight * 1000 + 3); // neighbour head height + clearance
      for (const t of [33, 40, 50, 61, 63]) {
        g.update({ time: t }, spec);
        g.root.position.set(0, 0, 0);
        g.root.scale.setScalar(1);
        g.root.updateMatrixWorld(true);
        const v = new Vector3();
        g.root.traverse((o) => {
          if (!(o instanceof Mesh)) return;
          const pos = o.geometry.attributes.position;
          for (let i = 0; i < pos.count; i++) {
            v.fromBufferAttribute(pos, i).applyMatrix4(o.matrixWorld);
            if (v.z > band)
              expect(Math.hypot(v.x, v.y), o.name).toBeLessThanOrEqual(
                NOSE.radius + 0.01,
              );
          }
        });
      }
    }
  });

  test("thumb keeps its link lengths, parks inside the body and never touches a chopstick", () => {
    for (const spec of PRESETS)
      for (let t = 0; t <= 70; t += 0.1) {
        const s = compactPose(t, spec);
        const { base, elbow, tip } = thumbPose(s, spec);
        expect(base.distanceTo(elbow)).toBeCloseTo(THUMB.links[0], 6);
        expect(elbow.distanceTo(tip)).toBeCloseTo(THUMB.links[1], 6);
        for (const [a, b] of [
          [base, elbow],
          [elbow, tip],
        ])
          for (let u = 0; u <= 1; u += 0.05) {
            const p = a.clone().lerp(b, u);
            if (p.z < 0) {
              expect(Math.hypot(p.x, p.y)).toBeGreaterThan(NOSE.radius + 1);
            }
            if (p.z < -NOSE.length) {
              expect(p.y + 3.5).toBeLessThan(BODY.height / 2 - 1.2);
              expect(p.y - 3.5).toBeGreaterThan(16.5); // thumb port floor
            }
          }
        if (s.engaged > 0 && Math.round(t * 10) % 5 === 0) {
          const k = tweezerPoints(s, -1);
          for (const [a, b, r] of [
            [base, elbow, 2.2],
            [elbow, tip, 1.8],
          ] as const)
            for (const [c, d, w] of [
              [k.root, k.knee, TWEEZER.width],
              [k.knee, k.bend, TWEEZER.width],
              [k.bend, k.tip, TWEEZER.tipWidth],
            ] as const)
              expect(segmentDistance(a, b, c, d)).toBeGreaterThan(r + w);
        }
      }
  });

  test("FR3 path respects joint limits and the bolt never jumps", () => {
    for (const spec of PRESETS) {
      for (let t = 0; t <= 70; t += 0.1)
        compactJoints(t, spec.id).forEach((q, i) => {
          expect(q).toBeGreaterThanOrEqual(ROBOT_DATA[i].lower!);
          expect(q).toBeLessThanOrEqual(ROBOT_DATA[i].upper!);
        });
      for (const t of [5, 10, 14, 15.5, 19, 25, 33, 61, 63, 65]) {
        const a = compactBoltWorld(t - 1e-5, spec),
          b = compactBoltWorld(t + 1e-5, spec);
        expect(
          new Vector3()
            .setFromMatrixPosition(a)
            .distanceTo(new Vector3().setFromMatrixPosition(b)),
        ).toBeLessThan(2e-5);
        expect(
          new Quaternion()
            .setFromRotationMatrix(a)
            .angleTo(new Quaternion().setFromRotationMatrix(b)),
        ).toBeLessThan(1e-3);
      }
      const seated = compactBoltWorld(63, spec);
      expect(new Vector3().setFromMatrixPosition(seated).z).toBeCloseTo(
        0.026,
        3,
      );
      expect(compactBoltWorld(69, spec).elements).toEqual(seated.elements);
      expect(
        new Vector3().setFromMatrixPosition(compactBoltWorld(0, spec)).z,
      ).toBeCloseTo(0.04, 3);
      const m = compactBoltWorld(40, spec);
      const head = new Vector3().setFromMatrixPosition(m),
        end = new Vector3(0, 0, spec.length).applyMatrix4(m);
      expect(head.z - end.z).toBeCloseTo(spec.length, 4);
    }
  });
});
