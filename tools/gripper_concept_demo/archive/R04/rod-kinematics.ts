import { Matrix4, Vector3 } from "three";
import type { BoltSpec, CycleState } from "./timeline";
export const GRASP_POINT = new Vector3(0, 0, 0.16);
export const GRASP_DISTANCE = 0.014;
export const HEAD_EXTENSION = 0.07;
export const TIP_INSET = 0.02;
export const HEAD_OPEN_RADIUS = 0.024;
export const HEAD_CLOCKING = Math.PI / 6;
export const THUMB_LENGTHS = [0.055, 0.05] as const;
export const THUMB_BASE = new Vector3(0, 0.034, 0.095);
export const ROLLER_RADIUS = 0.003;
export const THUMB_PARK = new Vector3(0, 0.052, 0.1);
export function boltLocalMatrix(s: CycleState) {
  return new Matrix4()
    .makeTranslation(0, 0, GRASP_POINT.z + HEAD_EXTENSION * s.clear)
    .multiply(new Matrix4().makeRotationX((-Math.PI / 2) * (1 - s.align)))
    .multiply(new Matrix4().makeTranslation(0, 0, -GRASP_DISTANCE))
    .multiply(new Matrix4().makeRotationZ(s.spindle + HEAD_CLOCKING));
}
// Joint origins and mimic signs from the vendored Robotiq 2F-85 URDF.
// The stock wide fingertip is replaced by a rigid, size-specific narrow tip.
export function mainFingerPose(side: number, s: CycleState, spec: BoltSpec) {
  const root = new Vector3(side * 0.03060114, 0, 0.05490452);
  const a = 0.03152616 + 0.00563134,
    b = -0.00376347 + 0.04718515;
  const desiredX = spec.diameter / 2 + 0.003 + TIP_INSET;
  const held =
    Math.acos((desiredX - 0.03060114) / Math.hypot(a, b)) - Math.atan2(b, a);
  const q = 0.5 + (held - 0.5) * s.fingerClosed;
  const mountAt = (angle: number) =>
    new Vector3(
      side * (0.03060114 + a * Math.cos(angle) - b * Math.sin(angle)),
      0,
      root.z + a * Math.sin(angle) + b * Math.cos(angle),
    );
  // An exchangeable tip/shim per bolt preset keeps the explanatory grasp point fixed.
  const tipLength = GRASP_POINT.z - mountAt(held).z;
  const finger = root
    .clone()
    .add(
      new Vector3(side * 0.03152616, 0, -0.00376347).applyAxisAngle(
        new Vector3(0, 1, 0),
        -side * q,
      ),
    );
  const mount = mountAt(q);
  const contact = mount
    .clone()
    .add(new Vector3(-side * TIP_INSET, 0, tipLength));
  return {
    root,
    angles: [q, -q],
    points: [root, finger, mount, contact],
    tipLength,
  };
}
/** Two rotational joints form an auxiliary thumb, separate from the two main fingers. */
export function rodPose(s: CycleState, spec: BoltSpec) {
  const theta = (Math.PI / 2) * (1 - s.align),
    lever = spec.length - 0.003 - GRASP_DISTANCE,
    r = spec.diameter / 2 + ROLLER_RADIUS;
  const tangent = new Vector3(0, -Math.cos(theta), Math.sin(theta));
  const contact = GRASP_POINT.clone().add(
    new Vector3(0, Math.sin(theta) * lever, Math.cos(theta) * lever),
  );
  const target = THUMB_PARK.clone().lerp(
    contact.clone().addScaledVector(tangent, -r),
    s.rodEngaged,
  );
  const dy = target.y - THUMB_BASE.y,
    dz = target.z - THUMB_BASE.z,
    [a, b] = THUMB_LENGTHS;
  const q2 = Math.acos(
    Math.max(
      -1,
      Math.min(1, (dy * dy + dz * dz - a * a - b * b) / (2 * a * b)),
    ),
  );
  const q1 =
    Math.atan2(dz, dy) - Math.atan2(b * Math.sin(q2), a + b * Math.cos(q2));
  const elbow = THUMB_BASE.clone().add(
    new Vector3(0, a * Math.cos(q1), a * Math.sin(q1)),
  );
  const tip = elbow
    .clone()
    .add(new Vector3(0, b * Math.cos(q1 + q2), b * Math.sin(q1 + q2)));
  return { base: THUMB_BASE.clone(), elbow, tip, angles: [q1, q2], contact };
}
