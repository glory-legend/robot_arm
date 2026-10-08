import { Matrix4, Vector3 } from "three";
import type { BoltSpec, CycleState } from "./timeline";
import type { Variant } from "./variants";
export const GRASP_POINT = new Vector3(0, 0, 0.4);
export const GRASP_DISTANCE = 0.014;
export const HEAD_EXTENSION = 0;
export const HEAD_STROKE = 0;
export const RETRACT = new Vector3(0, 0.052, -0.02);
export const TIP_HALF_WIDTH = 0.0008;
export const HEAD_OPEN_RADIUS = 0.024;
export const HEAD_CLOCKING = 0;
export const THUMB_LENGTHS = [0.025, 0.025] as const;
export const THUMB_BASE = new Vector3(0, 0.033, GRASP_POINT.z - 0.01);
export const ROLLER_RADIUS = 0.003;
export const THUMB_PARK = new Vector3(0, 0.032, GRASP_POINT.z - 0.031);
export function boltLocalMatrix(s: CycleState) {
  return new Matrix4()
    .makeTranslation(0, 0, GRASP_POINT.z + HEAD_EXTENSION * s.clear)
    .multiply(new Matrix4().makeRotationX((-Math.PI / 2) * (1 - s.align)))
    .multiply(new Matrix4().makeTranslation(0, 0, -GRASP_DISTANCE))
    .multiply(new Matrix4().makeRotationZ(s.spindle + HEAD_CLOCKING));
}
// Identical sharp blades across sizes. A stores the entire pair; B retracts only shaft tips.
export function fingerOffset(variant: Variant) {
  return variant === "a" ? RETRACT.clone() : new Vector3(0, 0, -0.024);
}
export function thumbOffset(variant: Variant) {
  return variant === "a" ? RETRACT.clone() : new Vector3(0, 0.018, -0.02);
}
export function fingerVector(side: number, variant: Variant) {
  return variant === "a"
    ? new Vector3(0, 0.052, -0.02)
    : new Vector3(side * 0.02, side * 0.016, -0.035);
}
export function mainFingerPose(
  side: number,
  s: CycleState,
  spec: BoltSpec,
  variant: Variant = "a",
) {
  const x =
    side *
    (spec.diameter / 2 +
      TIP_HALF_WIDTH +
      (variant === "b" ? 0.006 : 0.004) * (1 - s.fingerClosed));
  const offset = fingerOffset(variant).multiplyScalar(s.clear);
  const contact = new Vector3(x, 0, GRASP_POINT.z).add(offset);
  const root = contact.clone().add(fingerVector(side, variant));
  if (variant === "b") {
    root.applyAxisAngle(new Vector3(0, 0, 1), s.spindle);
    contact.applyAxisAngle(new Vector3(0, 0, 1), s.spindle);
  }
  return {
    root,
    contact,
    points: [root, contact],
    tipLength: root.distanceTo(contact),
  };
}
/** Two rotational joints form an auxiliary thumb, separate from the two main fingers. */
export function rodPose(s: CycleState, spec: BoltSpec, variant: Variant = "a") {
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
  // Approach the long bolt from outside before lowering the contact roller.
  if (spec.id === "m10") target.y += 0.02 * Math.sin(Math.PI * s.rodEngaged);
  const dy = target.y - THUMB_BASE.y,
    dz = target.z - THUMB_BASE.z,
    [a, b] = THUMB_LENGTHS;
  const q2 =
    (spec.id === "m10" ? 1 : -1) *
    Math.acos(
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
  const offset = thumbOffset(variant).multiplyScalar(s.clear);
  return {
    base: THUMB_BASE.clone().add(offset),
    elbow: elbow.add(offset),
    tip: tip.add(offset),
    angles: [q1, q2],
    contact,
  };
}
